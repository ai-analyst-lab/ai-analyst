"""
Connection Manager — unified interface for multi-warehouse connections.

Manages connection lifecycle for different data warehouse backends:
MotherDuck/DuckDB (native), PostgreSQL, BigQuery, Snowflake, and local CSV
folders (served through an in-memory DuckDB so they are SQL-queryable and
provenance-logged exactly like a warehouse).

Usage:
    from helpers.data.connection_manager import ConnectionManager

    mgr = ConnectionManager()
    conn = mgr.connect()          # Uses active dataset config
    mgr.test_connection()          # Health check
    tables = mgr.list_tables()     # Enumerate tables
    mgr.close()                    # Cleanup

    # Or use as context manager:
    with ConnectionManager() as mgr:
        tables = mgr.list_tables()
"""

import os
import re
import time
from datetime import date
from pathlib import Path

import pandas as pd

# Optional imports — each warehouse backend is optional.
try:
    import duckdb
    _DUCKDB_AVAILABLE = True
except ImportError:
    _DUCKDB_AVAILABLE = False

try:
    import yaml
    _YAML_AVAILABLE = True
except ImportError:
    _YAML_AVAILABLE = False


# Supported connection types and their required packages.
SUPPORTED_TYPES = {
    "motherduck": {"package": "duckdb", "installed": _DUCKDB_AVAILABLE},
    "duckdb": {"package": "duckdb", "installed": _DUCKDB_AVAILABLE},
    "csv": {"package": "duckdb", "installed": _DUCKDB_AVAILABLE},
    "postgres": {"package": "psycopg2", "installed": False},
    "bigquery": {"package": "google-cloud-bigquery", "installed": False},
    "snowflake": {"package": "snowflake-connector-python", "installed": False},
}


class ConnectionManager:
    """Unified connection manager for multi-warehouse data access.

    Reads connection config from the active dataset's manifest, connects
    to the appropriate backend, and provides a common interface for
    table listing, health checks, and query execution.

    Args:
        config: Optional connection config dict. If None, reads from
            the active dataset manifest via data_helpers.
        dataset_id: Optional dataset ID to connect to. If None, uses
            the active dataset.
    """

    def __init__(self, config=None, dataset_id=None):
        self._config = config
        self._dataset_id = dataset_id
        self._connection = None
        self._conn_type = None
        self._schema_prefix = ""
        self._csv_dir = None
        self._csv_files = None        # explicit manifest files: list (paths), when present
        self._csv_views = {}          # view name -> csv path registered on the DuckDB connection

        if config is None:
            self._config = self._load_config(dataset_id)

        self._conn_type = self._config.get("type", "csv")
        self._schema_prefix = self._config.get("schema_prefix", "")

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    # ------------------------------------------------------------------
    # Config loading
    # ------------------------------------------------------------------

    @staticmethod
    def _load_config(dataset_id=None):
        """Load connection config from the knowledge system.

        Reads .knowledge/active.yaml (or uses dataset_id) and loads the
        dataset's manifest.yaml for connection details.

        Returns:
            dict with connection configuration.
        """
        try:
            from helpers.data.data_helpers import detect_active_source
            source = detect_active_source()
            return {
                "type": source.get("type", "csv"),
                "dataset_id": source.get("source", "unknown"),
                "display_name": source.get("display_name", "Unknown"),
                "schema_prefix": source.get("schema_prefix", ""),
                "duckdb_path": source.get("duckdb_path"),
                "csv_path": source.get("csv_path"),
                "files": source.get("files"),
                "connection": source.get("connection", {}),
            }
        except Exception as exc:
            raise RuntimeError(
                "Failed to load dataset config — no active dataset found. "
                "Use /connect-data to configure a dataset, or pass a config dict "
                f"to ConnectionManager directly. Original error: {exc}"
            )

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    def connect(self):
        """Establish connection to the configured data source.

        Returns:
            self (for chaining).

        Raises:
            ConnectionError: If the connection cannot be established.
        """
        conn_type = self._conn_type

        if conn_type in ("motherduck", "duckdb"):
            self._connect_duckdb()
        elif conn_type == "postgres":
            self._connect_postgres()
        elif conn_type == "bigquery":
            self._connect_bigquery()
        elif conn_type == "snowflake":
            self._connect_snowflake()
        elif conn_type == "csv":
            self._connect_csv()
        else:
            raise ConnectionError(
                f"Unsupported connection type: {conn_type}. "
                f"Supported types: {list(SUPPORTED_TYPES.keys())}"
            )

        return self

    def close(self):
        """Close the active connection and release resources."""
        if self._connection is not None:
            try:
                if hasattr(self._connection, "close"):
                    self._connection.close()
            except Exception:
                pass
            self._connection = None
        self._csv_views = {}

    def test_connection(self):
        """Test connectivity with a lightweight probe.

        Returns:
            dict: {ok: bool, type: str, message: str}
        """
        try:
            if self._conn_type in ("motherduck", "duckdb"):
                if self._connection is None:
                    self.connect()
                self._connection.sql("SELECT 1").fetchone()
                return {"ok": True, "type": self._conn_type, "message": "Connected"}

            elif self._conn_type == "postgres":
                if self._connection is None:
                    self.connect()
                cur = self._connection.cursor()
                cur.execute("SELECT 1")
                cur.fetchone()
                cur.close()
                return {"ok": True, "type": "postgres", "message": "Connected"}

            elif self._conn_type == "csv":
                csv_dir = self._csv_dir or self._config.get("csv_path", "")
                if self._connection is None:
                    self.connect()  # registers the views; raises loudly on a missing file
                if self._connection is not None:
                    self._connection.sql("SELECT 1").fetchone()
                    count = len(self._csv_views)
                    return {"ok": count > 0, "type": "csv",
                            "message": f"{count} CSV files registered as DuckDB views"}
                if Path(csv_dir).is_dir():
                    count = len(list(Path(csv_dir).glob("*.csv")))
                    return {"ok": count > 0, "type": "csv", "message": f"{count} CSV files"}
                return {"ok": False, "type": "csv", "message": f"Directory not found: {csv_dir}"}

            else:
                return {"ok": False, "type": self._conn_type, "message": "Not yet implemented"}

        except Exception as exc:
            return {"ok": False, "type": self._conn_type, "message": str(exc)}

    # ------------------------------------------------------------------
    # Table operations
    # ------------------------------------------------------------------

    def list_tables(self):
        """List all available tables in the connected source.

        Returns:
            list[str]: Sorted table names.
        """
        if self._conn_type in ("motherduck", "duckdb") and self._connection:
            try:
                df = self._connection.sql("SHOW TABLES").df()
                return sorted(df["name"].tolist()) if "name" in df.columns else []
            except Exception:
                return []

        elif self._conn_type == "postgres" and self._connection:
            try:
                cur = self._connection.cursor()
                schema = self._schema_prefix or "public"
                cur.execute(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = %s ORDER BY table_name",
                    (schema,),
                )
                tables = [row[0] for row in cur.fetchall()]
                cur.close()
                return tables
            except Exception:
                return []

        elif self._conn_type == "csv":
            if self._csv_views:
                return sorted(self._csv_views)
            return sorted(p.stem for p in self._resolve_csv_files())

        return []

    def get_table_schema(self, table_name):
        """Get column names and types for a specific table.

        Args:
            table_name: Name of the table to inspect.

        Returns:
            list[dict]: Each dict has keys: name, type, nullable.
        """
        if self._conn_type in ("motherduck", "duckdb") and self._connection:
            try:
                df = self._connection.sql(f"DESCRIBE {table_name}").df()
                columns = []
                for _, row in df.iterrows():
                    columns.append({
                        "name": row.get("column_name", row.get("Field", "")),
                        "type": row.get("column_type", row.get("Type", "")),
                        "nullable": row.get("null", "YES") == "YES",
                    })
                return columns
            except Exception:
                return []

        elif self._conn_type == "csv":
            if self._connection is not None and table_name in self._csv_views:
                try:
                    df = self._connection.sql(f'DESCRIBE {self._quote_ident(table_name)}').df()
                    return [
                        {
                            "name": row.get("column_name", ""),
                            "type": row.get("column_type", ""),
                            "nullable": row.get("null", "YES") == "YES",
                        }
                        for _, row in df.iterrows()
                    ]
                except Exception:
                    pass
            csv_path = self._csv_path_for(table_name)
            if csv_path is not None and csv_path.exists():
                df = pd.read_csv(csv_path, nrows=5, low_memory=False)
                return [
                    {"name": col, "type": str(df[col].dtype), "nullable": True}
                    for col in df.columns
                ]
            return []

        return []

    def query(self, sql, log=True):
        """Execute a SQL query and return results as a DataFrame.

        Args:
            sql: SQL query string.
            log: When True (default), the query is logged to the query log at the moment it executes,
                with its SQL, the scalar result_value (when the result is a single cell), the tables it
                touched, and the current analysis_id. This is the provenance capture: the log records
                what actually ran on this connection, not what the analyst later says it ran. Pass
                False (or call query_log.set_autolog(False) process-wide) when a caller logs by hand.

        Returns:
            pandas.DataFrame with query results.

        Raises:
            RuntimeError: If no SQL-capable connection is available.
        """
        # Lazy-connect: open the connection on first use, the same way
        # test_connection() does. Without this, a fresh ConnectionManager().query()
        # falls through to the RuntimeError below even though the backend is SQL-capable.
        # For CSV sources this opens the in-memory DuckDB and registers the files as views.
        if self._connection is None:
            self.connect()

        start = time.perf_counter()
        if self._conn_type in ("motherduck", "duckdb", "csv") and self._connection:
            df = self._connection.sql(sql).df()
        elif self._conn_type == "postgres" and self._connection:
            df = pd.read_sql(sql, self._connection)
        elif self._conn_type == "snowflake" and self._connection:
            cur = self._connection.cursor()
            try:
                cur.execute(sql)
                df = cur.fetch_pandas_all() if cur.description else pd.DataFrame()
            finally:
                cur.close()
        else:
            raise RuntimeError(
                f"SQL queries not supported for connection type: {self._conn_type}. "
                + ("CSV mode needs the duckdb package (pip install duckdb); "
                   "read_table() still works without it."
                   if self._conn_type == "csv" else "")
            )
        execution_ms = (time.perf_counter() - start) * 1000.0

        if log:
            self._autolog_query(sql, df, execution_ms)
        return df

    def _autolog_query(self, sql, df, execution_ms):
        """Record this query to the query log at execution. Best-effort: a logging failure must never
        break the query, so everything here is wrapped and swallowed."""
        try:
            if os.environ.get("AAP_QUERY_AUTOLOG", "1") == "0":
                return
            from helpers.provenance import query_log
            if not query_log.autolog_enabled():
                return  # a caller (e.g. a pipeline) is logging by hand; do not double-log

            # The scalar result_value: only when the result is a single 1x1 cell (most metric queries).
            # This is what makes finding<->query value-matching reliable; None otherwise.
            result_value = None
            try:
                if df is not None and df.shape == (1, 1):
                    result_value = df.iloc[0, 0]
                    if hasattr(result_value, "item"):  # numpy scalar -> python scalar
                        result_value = result_value.item()
            except Exception:
                result_value = None

            tables = re.findall(r'(?:from|join)\s+([A-Za-z0-9_.]+)', sql or "", flags=re.IGNORECASE)

            analysis_id = None
            try:
                from helpers.knowledge.analysis_context import current_analysis_id
                analysis_id = current_analysis_id(create=True)
            except Exception:
                analysis_id = None

            query_log.append_entry(
                dataset_name=self.dataset_id,
                date=date.today().isoformat(),
                agent="connection_manager",
                pipeline_step=0.0,
                purpose="auto-logged at execution by the connection",
                sql=sql,
                dialect=("duckdb" if self._conn_type == "csv" else self._conn_type),
                connection_type=self._conn_type,
                tables_accessed=tables or None,
                result_summary=(f"{len(df)} rows returned" if df is not None else ""),
                result_value=result_value,
                row_count=(len(df) if df is not None else None),
                execution_ms=execution_ms,
                analysis_id=analysis_id,
            )
        except Exception:
            # Provenance logging is never allowed to take down a real query.
            pass

    def read_table(self, table_name):
        """Read an entire table as a DataFrame.

        Works for all connection types including CSV.

        Args:
            table_name: Name of the table to read.

        Returns:
            pandas.DataFrame
        """
        if self._conn_type in ("motherduck", "duckdb") and self._connection:
            return self._connection.sql(f"SELECT * FROM {table_name}").df()

        elif self._conn_type == "csv":
            csv_path = self._csv_path_for(table_name)
            if csv_path is not None and csv_path.exists():
                return pd.read_csv(csv_path, low_memory=False)
            raise FileNotFoundError(f"CSV file not found: {csv_path}")

        elif self._conn_type == "postgres" and self._connection:
            schema = self._schema_prefix or "public"
            return pd.read_sql(f"SELECT * FROM {schema}.{table_name}", self._connection)

        raise RuntimeError(f"Cannot read table for connection type: {self._conn_type}")

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def connection_type(self):
        """Return the active connection type string."""
        return self._conn_type

    @property
    def schema_prefix(self):
        """Return the SQL schema prefix for the active connection."""
        return self._schema_prefix

    @property
    def is_connected(self):
        """Return True if a connection is currently active."""
        if self._conn_type == "csv":
            csv_dir = self._csv_dir or self._config.get("csv_path", "")
            return Path(csv_dir).is_dir()
        return self._connection is not None

    @property
    def dataset_id(self):
        """Return the active dataset ID."""
        return self._config.get("dataset_id", self._dataset_id or "unknown")

    # ------------------------------------------------------------------
    # Backend-specific connectors (private)
    # ------------------------------------------------------------------

    def _connect_duckdb(self):
        """Connect to local DuckDB or MotherDuck fallback."""
        if not _DUCKDB_AVAILABLE:
            raise ConnectionError("duckdb package not installed. pip install duckdb")

        db_path = self._config.get("duckdb_path")
        if db_path and Path(db_path).exists():
            self._connection = duckdb.connect(str(db_path), read_only=True)
            self._conn_type = "duckdb"
        else:
            # Fallback to CSV
            self._conn_type = "csv"
            self._connect_csv()

    def _connect_csv(self):
        """Set up CSV-based access: an in-memory DuckDB with one view per CSV file.

        Each file becomes a view named after its file stem (``orders.csv`` -> ``orders``),
        read through DuckDB's ``read_csv_auto`` so headers and column types are inferred.
        When the manifest declares a ``files:`` list, exactly those files are registered;
        otherwise every ``*.csv`` in ``csv_path``. Registration is idempotent
        (``CREATE OR REPLACE VIEW``), so calling connect() twice is safe.

        Raises:
            ConnectionError: no csv_path/files configured, or a declared file is missing.
        """
        csv_path = self._config.get("csv_path")
        files = self._config.get("files")
        if not csv_path and not files:
            raise ConnectionError(
                "No csv_path configured for CSV connection. "
                "Set csv_path in the dataset manifest or pass it in the config dict."
            )
        self._csv_dir = csv_path
        self._csv_files = [str(f) for f in files] if files else None
        self._conn_type = "csv"

        if not _DUCKDB_AVAILABLE:
            # Degraded mode: read_table() still works via pandas; query() will explain.
            self._connection = None
            return

        resolved = self._resolve_csv_files(strict=True)
        if self._connection is None:
            self._connection = duckdb.connect(":memory:")
        self._csv_views = {}
        for path in resolved:
            view = path.stem
            literal = str(path).replace("'", "''")
            self._connection.execute(
                f"CREATE OR REPLACE VIEW {self._quote_ident(view)} AS "
                f"SELECT * FROM read_csv_auto('{literal}')"
            )
            self._csv_views[view] = path

    def _resolve_csv_files(self, strict=False):
        """Return the CSV files that make up this dataset, as Paths.

        Manifest ``files:`` entries may be absolute, relative to ``csv_path``, or relative
        to the working directory. With ``strict=True`` a missing declared file raises a
        ConnectionError that names the missing file and lists what was found instead.
        """
        csv_dir = Path(self._csv_dir or self._config.get("csv_path") or "")
        files = self._csv_files or self._config.get("files")
        if files:
            resolved, missing = [], []
            for f in files:
                candidate = Path(f)
                if not candidate.is_absolute():
                    in_dir = csv_dir / candidate if str(csv_dir) else candidate
                    candidate = in_dir if in_dir.exists() else candidate
                if candidate.exists():
                    resolved.append(candidate)
                else:
                    missing.append(str(f))
            if missing and strict:
                found = sorted(p.name for p in csv_dir.glob("*.csv")) if csv_dir.is_dir() else []
                raise ConnectionError(
                    f"CSV file(s) declared in the dataset manifest not found: {missing}. "
                    f"Looked in {csv_dir.resolve() if str(csv_dir) else Path.cwd()}; "
                    f"CSV files actually present there: {found or 'none'}. "
                    "Fix the manifest files: list or move the file into place."
                )
            return resolved
        if csv_dir.is_dir():
            return sorted(csv_dir.glob("*.csv"))
        return []

    def _csv_path_for(self, table_name):
        """Path of the CSV backing ``table_name``, honoring the manifest files: list."""
        if table_name in self._csv_views:
            return self._csv_views[table_name]
        for path in self._resolve_csv_files():
            if path.stem == table_name:
                return path
        csv_dir = self._csv_dir or self._config.get("csv_path", "")
        return Path(csv_dir) / f"{table_name}.csv"

    @staticmethod
    def _quote_ident(name):
        return '"' + str(name).replace('"', '""') + '"'

    def _connect_postgres(self):
        """Connect to PostgreSQL. Requires psycopg2."""
        try:
            import psycopg2
        except ImportError:
            raise ConnectionError(
                "psycopg2 not installed. Install with: pip install psycopg2-binary"
            )

        conn_config = self._config.get("connection", {})
        self._connection = psycopg2.connect(
            host=conn_config.get("host", "localhost"),
            port=conn_config.get("port", 5432),
            database=conn_config.get("database", ""),
            user=conn_config.get("user", ""),
            password=conn_config.get("password", ""),
        )
        self._schema_prefix = conn_config.get("schema", "public")

    def _connect_bigquery(self):
        """Connect to BigQuery. Requires google-cloud-bigquery."""
        try:
            from google.cloud import bigquery
        except ImportError:
            raise ConnectionError(
                "google-cloud-bigquery not installed. "
                "Install with: pip install google-cloud-bigquery"
            )

        conn_config = self._config.get("connection", {})
        project = conn_config.get("project")
        self._connection = bigquery.Client(project=project)
        self._schema_prefix = conn_config.get("dataset", "")
        self._conn_type = "bigquery"

    def _connect_snowflake(self):
        """Connect to Snowflake. Requires snowflake-connector-python."""
        try:
            import snowflake.connector
        except ImportError:
            raise ConnectionError(
                "snowflake-connector-python not installed. "
                "Install with: pip install snowflake-connector-python"
            )

        conn_config = self._config.get("connection", {})
        connect_kwargs = dict(
            account=conn_config.get("account", ""),
            user=conn_config.get("user", ""),
            password=conn_config.get("password", ""),
            warehouse=conn_config.get("warehouse", ""),
            database=conn_config.get("database", ""),
            schema=conn_config.get("schema", "public"),
        )
        if conn_config.get("role"):
            connect_kwargs["role"] = conn_config["role"]
        self._connection = snowflake.connector.connect(**connect_kwargs)
        self._schema_prefix = conn_config.get("schema", "public")
        self._conn_type = "snowflake"
