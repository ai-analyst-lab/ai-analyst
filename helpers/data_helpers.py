"""
Data Source Helpers — abstraction layer for local data access.

Provides unified access to dataset data via MotherDuck MCP, local DuckDB,
or CSV fallback. Reads ``.knowledge/active.yaml`` to determine the active
dataset and routes queries transparently.

Usage:
    from helpers.data_helpers import (
        get_local_connection, read_table, list_tables,
        get_data_source_info, detect_active_source, check_connection,
        get_connection_for_profiling, schema_to_markdown,
    )

    # Auto-detect active source
    source = detect_active_source()

    # DuckDB path
    conn = get_local_connection("path/to/your.duckdb")
    if conn:
        df = conn.sql("SELECT * FROM orders LIMIT 10").df()

    # CSV fallback
    df = read_table("orders", data_dir="data/your_dataset/")

    # Discovery
    tables = list_tables("data/your_dataset/")
    info = get_data_source_info()
"""

import os
from pathlib import Path

import pandas as pd

# Optional imports — CSV path works without these.
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


# ---------------------------------------------------------------------------
# Default paths (relative to project root)
# ---------------------------------------------------------------------------

_DEFAULT_DUCKDB_PATH = None  # Set via manifest.yaml or detect_active_source()
_DEFAULT_DATA_DIR = None  # Set via manifest.yaml or detect_active_source()


# ---------------------------------------------------------------------------
# DuckDB connection
# ---------------------------------------------------------------------------

def get_local_connection(duckdb_path=None):
    """Open a read-only connection to a local DuckDB file.

    Args:
        duckdb_path: Path to the DuckDB file, relative to the repo root.
            If None, attempts to resolve from the active dataset manifest.

    Returns:
        duckdb.Connection if the file exists and the connection succeeds,
        or ``None`` if DuckDB is not installed or the file is missing.
    """
    if not _DUCKDB_AVAILABLE:
        print(
            "[data_helpers] duckdb is not installed. "
            "Install it with: pip install duckdb"
        )
        return None

    if duckdb_path is None:
        # Try to resolve from active dataset
        source = detect_active_source()
        duckdb_path = source.get("duckdb_path")
        if duckdb_path is None:
            print("[data_helpers] No DuckDB path configured. Use /connect-data to set up a dataset.")
            return None

    path = Path(duckdb_path)
    if not path.exists():
        print(
            f"[data_helpers] DuckDB file not found: {path}\n"
            "  Tip: run the data setup notebook or use read_table() for CSV access."
        )
        return None

    try:
        conn = duckdb.connect(str(path), read_only=True)
        return conn
    except Exception as exc:
        print(
            f"[data_helpers] Could not connect to DuckDB at {path}: {exc}\n"
            "  Tip: the file may be corrupted. Re-download or use CSV fallback."
        )
        return None


# ---------------------------------------------------------------------------
# CSV table access
# ---------------------------------------------------------------------------

def read_table(table_name, data_dir=None):
    """Read a table from a CSV file in the data directory.

    Maps *table_name* to ``{data_dir}/{table_name}.csv`` and reads it into a
    pandas DataFrame with sensible defaults for encoding and mixed types.

    Args:
        table_name: Table name (e.g. ``"orders"``). Do not include the
            ``.csv`` extension.
        data_dir: Directory containing the CSV files. If None, resolves
            from the active dataset manifest.

    Returns:
        pandas.DataFrame

    Raises:
        FileNotFoundError: If the CSV file does not exist — includes a
            helpful message listing available tables.
    """
    if data_dir is None:
        source = detect_active_source()
        data_dir = source.get("csv_path")
        if data_dir is None:
            raise FileNotFoundError(
                f"Table '{table_name}' not found: no data directory configured.\n"
                "  Use /connect-data to set up a dataset."
            )

    csv_path = Path(data_dir) / f"{table_name}.csv"

    if not csv_path.exists():
        available = list_tables(data_dir)
        available_str = ", ".join(available) if available else "(none found)"
        raise FileNotFoundError(
            f"Table '{table_name}' not found at {csv_path}\n"
            f"  Available tables in {data_dir}: {available_str}"
        )

    return pd.read_csv(
        csv_path,
        encoding="utf-8",
        low_memory=False,  # avoid mixed-type warnings on large files
    )


# ---------------------------------------------------------------------------
# Table discovery
# ---------------------------------------------------------------------------

def list_tables(data_dir=None):
    """List available table names from CSV files in *data_dir*.

    Args:
        data_dir: Directory to scan. If None, resolves from active dataset.

    Returns:
        Sorted list of table names (filenames without the ``.csv`` extension).
        Returns an empty list if the directory does not exist.
    """
    if data_dir is None:
        source = detect_active_source()
        data_dir = source.get("csv_path")
        if data_dir is None:
            return []

    dir_path = Path(data_dir)
    if not dir_path.is_dir():
        return []

    return sorted(p.stem for p in dir_path.glob("*.csv"))


# ---------------------------------------------------------------------------
# Data source info
# ---------------------------------------------------------------------------

def get_data_source_info(
    duckdb_path=None,
    data_dir=None,
):
    """Return a dict describing the current data source status.

    Checks whether DuckDB is available, whether CSV files are present, and
    enumerates the tables that can be found.

    Args:
        duckdb_path: Path to the local DuckDB file.
        data_dir: Directory containing CSV files.

    Returns:
        dict with keys:
            duckdb_available (bool), duckdb_path (str),
            csv_available (bool), csv_dir (str),
            tables (list of str)
    """
    csv_tables = list_tables(data_dir)

    duckdb_ok = _DUCKDB_AVAILABLE and duckdb_path is not None and Path(duckdb_path).exists()

    return {
        "duckdb_available": duckdb_ok,
        "duckdb_path": str(duckdb_path),
        "csv_available": len(csv_tables) > 0,
        "csv_dir": str(data_dir),
        "tables": csv_tables,
    }


# ---------------------------------------------------------------------------
# Active source detection
# ---------------------------------------------------------------------------

_KNOWLEDGE_DIR = Path(".knowledge")
_ACTIVE_YAML = _KNOWLEDGE_DIR / "active.yaml"


def detect_active_source():
    """Detect which data source is currently active.

    Reads ``.knowledge/active.yaml`` to find the active dataset, then loads
    the dataset's ``manifest.yaml`` for connection details. Falls back
    gracefully if YAML is unavailable or files are missing.

    Returns:
        dict with keys:
            source (str): Dataset ID (e.g., "my_dataset").
            display_name (str): Human-readable name.
            type (str): "motherduck", "duckdb", or "csv".
            schema_prefix (str): SQL schema prefix for queries.
            duckdb_path (str|None): Path to local DuckDB file.
            csv_path (str|None): Path to local CSV directory.
            connection (dict): Raw connection config from manifest.
    """
    # --- Read active.yaml ---
    active_dataset = _read_active_dataset()
    if active_dataset is None:
        return _fallback_source("(no active dataset)")

    # --- Load manifest ---
    manifest = _read_manifest(active_dataset)
    if manifest is None:
        return _fallback_source(active_dataset)

    # --- Extract connection info ---
    conn = manifest.get("connection", {})
    local_data = manifest.get("local_data", {})

    # Expand "$ENV_VAR" placeholders in the connection block (e.g. credentials).
    def _expand_env(value):
        if isinstance(value, str) and value.startswith("$"):
            return os.environ.get(value[1:], "")
        return value
    conn = {k: _expand_env(v) for k, v in conn.items()}

    # A remote source can be declared at the manifest top level
    # ("connection_type: snowflake") or inside the connection block ("type: ...").
    # It is only used when opted into via AAP_USE_REMOTE, so the default/offline
    # path stays on the local DuckDB file (unchanged behaviour for students).
    declared_type = str(manifest.get("connection_type") or conn.get("type") or "").lower()
    use_remote = os.environ.get("AAP_USE_REMOTE", "").lower() in ("1", "true", "yes")

    source_info = {
        "source": active_dataset,
        "display_name": manifest.get("display_name", active_dataset),
        "type": conn.get("type", "csv"),
        "schema_prefix": conn.get("schema_prefix", ""),
        "duckdb_path": local_data.get("duckdb"),
        "csv_path": local_data.get("path"),
        "connection": conn,
    }

    # --- Determine best available connection type ---
    # Opted-in remote (snowflake/postgres/bigquery/motherduck) > local duckdb > csv
    if declared_type in ("snowflake", "postgres", "bigquery") and use_remote:
        source_info["type"] = declared_type
        source_info["schema_prefix"] = conn.get("schema", "") or manifest.get("schema_prefix", "")
    elif conn.get("type") == "motherduck" or (declared_type == "motherduck" and use_remote):
        source_info["type"] = "motherduck"
    elif source_info["duckdb_path"] and Path(source_info["duckdb_path"]).exists():
        source_info["type"] = "duckdb"
    elif source_info["csv_path"] and Path(source_info["csv_path"]).is_dir():
        source_info["type"] = "csv"
    else:
        source_info["type"] = "none"

    return source_info


def _read_active_dataset():
    """Read the active dataset ID from .knowledge/active.yaml."""
    if not _YAML_AVAILABLE:
        return None
    if not _ACTIVE_YAML.exists():
        return None
    try:
        with open(_ACTIVE_YAML) as f:
            data = yaml.safe_load(f)
        return data.get("active_dataset") if isinstance(data, dict) else None
    except Exception:
        return None


def _read_manifest(dataset_id):
    """Read a dataset's manifest.yaml from .knowledge/datasets/{id}/."""
    if not _YAML_AVAILABLE:
        return None
    manifest_path = _KNOWLEDGE_DIR / "datasets" / dataset_id / "manifest.yaml"
    if not manifest_path.exists():
        return None
    try:
        with open(manifest_path) as f:
            return yaml.safe_load(f)
    except Exception:
        return None


def _fallback_source(dataset_id):
    """Return a fallback source config when detection fails."""
    return {
        "source": dataset_id,
        "display_name": dataset_id,
        "type": "none",
        "schema_prefix": "",
        "duckdb_path": None,
        "csv_path": None,
        "connection": {},
    }


# ---------------------------------------------------------------------------
# Connection health check
# ---------------------------------------------------------------------------


def check_connection(source_info=None):
    """Verify connectivity to the active data source.

    Runs a lightweight probe against the detected (or provided) source.
    For MotherDuck this is a no-op (MCP handles connectivity). For local
    DuckDB it opens a read-only connection and runs ``SELECT 1``. For CSV
    it checks that the data directory exists and contains files.

    Args:
        source_info: Optional dict from :func:`detect_active_source`. If
            ``None``, calls ``detect_active_source()`` internally.

    Returns:
        dict with keys:
            ok (bool): True if the source is reachable.
            source (str): Dataset ID.
            type (str): Connection type that was checked.
            message (str): Human-readable status.
    """
    if source_info is None:
        source_info = detect_active_source()

    src_type = source_info.get("type", "csv")
    src_name = source_info.get("source", "unknown")

    # --- MotherDuck: connectivity is managed by MCP, we can't probe it here.
    if src_type == "motherduck":
        return {
            "ok": True,
            "source": src_name,
            "type": "motherduck",
            "message": (
                "MotherDuck connection is managed by MCP. "
                "Run a simple query (SELECT 1) to verify."
            ),
        }

    # --- Local DuckDB ---
    if src_type == "duckdb":
        db_path = source_info.get("duckdb_path")
        if not db_path or not Path(db_path).exists():
            return {
                "ok": False,
                "source": src_name,
                "type": "duckdb",
                "message": f"DuckDB file not found: {db_path}",
            }
        if not _DUCKDB_AVAILABLE:
            return {
                "ok": False,
                "source": src_name,
                "type": "duckdb",
                "message": "duckdb package not installed. pip install duckdb",
            }
        try:
            conn = duckdb.connect(str(db_path), read_only=True)
            conn.sql("SELECT 1").fetchone()
            conn.close()
            return {
                "ok": True,
                "source": src_name,
                "type": "duckdb",
                "message": f"Connected to local DuckDB: {db_path}",
            }
        except Exception as exc:
            return {
                "ok": False,
                "source": src_name,
                "type": "duckdb",
                "message": f"DuckDB connection failed: {exc}",
            }

    # --- CSV fallback ---
    csv_path = source_info.get("csv_path")
    if not csv_path:
        return {
            "ok": False,
            "source": src_name,
            "type": "csv",
            "message": "No data directory configured. Use /connect-data to set up a dataset.",
        }
    dir_path = Path(csv_path)
    if not dir_path.is_dir():
        return {
            "ok": False,
            "source": src_name,
            "type": "csv",
            "message": f"CSV directory not found: {csv_path}",
        }
    csv_count = len(list(dir_path.glob("*.csv")))
    if csv_count == 0:
        return {
            "ok": False,
            "source": src_name,
            "type": "csv",
            "message": f"No CSV files found in: {csv_path}",
        }
    return {
        "ok": True,
        "source": src_name,
        "type": "csv",
        "message": f"CSV fallback ready: {csv_count} tables in {csv_path}",
    }


# ---------------------------------------------------------------------------
# Profiling connection interface (DP-1.2 — for DQ-2 schema_profiler)
# ---------------------------------------------------------------------------


def get_connection_for_profiling(source_info=None):
    """Return a connection suitable for schema profiling.

    Bridges ``data_helpers`` → ``schema_profiler`` (DQ-2). Returns a dict
    with the connection type and either an open DuckDB connection or a
    CSV directory path, so the profiler can introspect tables without
    knowing the underlying source.

    Args:
        source_info: Optional dict from :func:`detect_active_source`.

    Returns:
        dict with keys:
            type (str): "duckdb" or "csv"
            connection: duckdb.Connection or None
            csv_dir (str|None): Path to CSV directory
            schema_prefix (str): SQL schema prefix
            tables (list[str]): Available table names
    """
    if source_info is None:
        source_info = detect_active_source()

    src_type = source_info.get("type", "csv")
    result = {
        "type": src_type,
        "connection": None,
        "csv_dir": source_info.get("csv_path"),
        "schema_prefix": source_info.get("schema_prefix", ""),
        "tables": [],
    }

    # Try DuckDB first (covers motherduck fallback to local duckdb too)
    if src_type in ("duckdb", "motherduck"):
        db_path = source_info.get("duckdb_path")
        if db_path and Path(db_path).exists() and _DUCKDB_AVAILABLE:
            try:
                conn = duckdb.connect(str(db_path), read_only=True)
                # Discover tables
                tables_df = conn.sql("SHOW TABLES").df()
                result["connection"] = conn
                result["type"] = "duckdb"
                result["tables"] = tables_df["name"].tolist() if "name" in tables_df.columns else []
                return result
            except Exception:
                pass  # Fall through to CSV

    # CSV fallback
    csv_dir = source_info.get("csv_path")
    result["type"] = "csv"
    result["csv_dir"] = csv_dir
    result["tables"] = list_tables(csv_dir)
    return result


# ---------------------------------------------------------------------------
# Schema-to-Markdown rendering (DP-1.3 — for K-2 knowledge system)
# ---------------------------------------------------------------------------


def schema_to_markdown(schema_dict):
    """Render a schema dictionary as Markdown for ``.knowledge/datasets/{name}/schema.md``.

    Converts a structured schema definition (from YAML or profiling output) into
    human-readable Markdown that the Knowledge Bootstrap system loads into context.

    Args:
        schema_dict: Dict with structure::

            {
                "dataset": "my_dataset",
                "tables": [
                    {
                        "name": "orders",
                        "description": "Customer orders",
                        "row_count": 50000,
                        "columns": [
                            {"name": "order_id", "type": "INTEGER", "description": "Primary key", "nullable": False},
                            {"name": "customer_id", "type": "INTEGER", "description": "FK to customers", "nullable": False},
                            ...
                        ]
                    },
                    ...
                ]
            }

    Returns:
        str: Markdown string ready to write to schema.md.
    """
    lines = [f"# Schema: {schema_dict.get('dataset', 'Unknown')}", ""]

    for table in schema_dict.get("tables", []):
        name = table.get("name", "unknown")
        desc = table.get("description", "")
        row_count = table.get("row_count")

        lines.append(f"## {name}")
        if desc:
            lines.append(f"_{desc}_")
        if row_count is not None:
            lines.append(f"**Rows:** {row_count:,}")
        lines.append("")

        # Column table
        lines.append("| Column | Type | Nullable | Description |")
        lines.append("|--------|------|----------|-------------|")
        for col in table.get("columns", []):
            nullable = "Yes" if col.get("nullable", True) else "No"
            lines.append(
                f"| `{col.get('name', '')}` "
                f"| {col.get('type', '')} "
                f"| {nullable} "
                f"| {col.get('description', '')} |"
            )
        lines.append("")

    return "\n".join(lines)
