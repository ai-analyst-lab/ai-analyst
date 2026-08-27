"""
Schema Profiler — automated schema discovery and documentation.

Connects to the active data source (via data_helpers.get_connection_for_profiling())
and produces structured schema information for the Knowledge system.

Usage:
    from helpers.data.schema_profiler import (
        profile_source, compare_snapshots, discover_relationships,
        list_sources, get_table_reference,
    )

    # Full schema profile
    schema = profile_source()

    # Compare two snapshots
    diff = compare_snapshots(old_schema, new_schema)

    # Discover FK relationships
    rels = discover_relationships(schema)
"""

from datetime import datetime
from pathlib import Path

import pandas as pd

# Optional imports — CSV path works without these.
try:
    import duckdb
    _DUCKDB_AVAILABLE = True
except ImportError:
    _DUCKDB_AVAILABLE = False


# ---------------------------------------------------------------------------
# Date-column heuristics
# ---------------------------------------------------------------------------

_DATE_NAME_PATTERNS = (
    "date", "time", "created", "updated", "timestamp",
    "_at", "_on", "_dt",
)


def _looks_like_date_column(col_name):
    """Check if a column name suggests it holds date/time values."""
    lower = col_name.lower()
    return any(pat in lower for pat in _DATE_NAME_PATTERNS)


def _try_parse_dates(series, sample_size=100):
    """Try to parse a sample of a series as dates.

    Returns the parsed Series if >80% of non-null samples parse
    successfully, otherwise None.
    """
    sample = series.dropna().head(sample_size)
    if len(sample) == 0:
        return None
    try:
        parsed = pd.to_datetime(sample, errors="coerce")
        pct_valid = parsed.notna().sum() / len(sample)
        if pct_valid >= 0.8:
            return pd.to_datetime(series, errors="coerce")
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Column-level statistics
# ---------------------------------------------------------------------------

def _numeric_stats(series):
    """Compute descriptive stats for a numeric column."""
    try:
        return {
            "min": float(series.min()) if pd.notna(series.min()) else None,
            "max": float(series.max()) if pd.notna(series.max()) else None,
            "mean": float(series.mean()) if pd.notna(series.mean()) else None,
            "std": float(series.std()) if pd.notna(series.std()) else None,
        }
    except Exception:
        return None


def _string_stats(series):
    """Compute length stats for a string column."""
    try:
        lengths = series.dropna().astype(str).str.len()
        if len(lengths) == 0:
            return None
        return {
            "min_len": int(lengths.min()),
            "max_len": int(lengths.max()),
            "avg_len": round(float(lengths.mean()), 1),
        }
    except Exception:
        return None


def _profile_column(series, col_name):
    """Profile a single pandas Series and return a column dict."""
    total = len(series)
    null_count = int(series.isnull().sum())
    null_pct = round(100.0 * null_count / total, 2) if total > 0 else 0.0

    try:
        n_unique = int(series.nunique())
    except Exception:
        n_unique = 0

    # Sample values (up to 5, from non-null values)
    non_null = series.dropna()
    try:
        sample_values = non_null.head(5).tolist()
    except Exception:
        sample_values = []

    # Determine stats by dtype
    stats = None
    dtype_str = str(series.dtype)
    if pd.api.types.is_numeric_dtype(series):
        stats = _numeric_stats(series)
    elif pd.api.types.is_string_dtype(series) or pd.api.types.is_object_dtype(series):
        stats = _string_stats(series)

    return {
        "name": col_name,
        "type": dtype_str,
        "nullable": bool(null_count > 0),
        "null_count": null_count,
        "null_pct": null_pct,
        "n_unique": n_unique,
        "sample_values": sample_values,
        "description": "",
        "stats": stats,
    }


# ---------------------------------------------------------------------------
# Table-level profiling (DuckDB path)
# ---------------------------------------------------------------------------

def _profile_table_duckdb(conn, table_name, schema_prefix=""):
    """Profile a single table via DuckDB connection."""
    qualified = f"{schema_prefix}.{table_name}" if schema_prefix else table_name

    # Row count
    try:
        row_count = int(conn.sql(f"SELECT COUNT(*) AS n FROM {qualified}").fetchone()[0])
    except Exception:
        row_count = 0

    # Load into DataFrame for profiling (limit to 50k rows for speed)
    try:
        if row_count > 50_000:
            df = conn.sql(
                f"SELECT * FROM {qualified} USING SAMPLE 50000"
            ).df()
        else:
            df = conn.sql(f"SELECT * FROM {qualified}").df()
    except Exception:
        # Fallback: try without sampling syntax
        try:
            df = conn.sql(f"SELECT * FROM {qualified} LIMIT 50000").df()
        except Exception:
            return {
                "name": table_name,
                "row_count": row_count,
                "description": "",
                "columns": [],
                "date_columns": [],
                "date_range": None,
            }

    # Get SQL types from DESCRIBE
    sql_types = {}
    try:
        desc_df = conn.sql(f"DESCRIBE {qualified}").df()
        for _, row in desc_df.iterrows():
            sql_types[row["column_name"]] = row["column_type"]
    except Exception:
        pass

    return _profile_table_from_df(df, table_name, row_count, sql_types)


# ---------------------------------------------------------------------------
# Table-level profiling (CSV path)
# ---------------------------------------------------------------------------

def _profile_table_csv(csv_dir, table_name):
    """Profile a single table from a CSV file."""
    csv_path = Path(csv_dir) / f"{table_name}.csv"
    if not csv_path.exists():
        return {
            "name": table_name,
            "row_count": 0,
            "description": "",
            "columns": [],
            "date_columns": [],
            "date_range": None,
        }

    try:
        df = pd.read_csv(csv_path, encoding="utf-8", low_memory=False)
    except Exception:
        return {
            "name": table_name,
            "row_count": 0,
            "description": "",
            "columns": [],
            "date_columns": [],
            "date_range": None,
        }

    return _profile_table_from_df(df, table_name, len(df), sql_types={})


# ---------------------------------------------------------------------------
# Shared DataFrame-to-table-profile logic
# ---------------------------------------------------------------------------

def _profile_table_from_df(df, table_name, row_count, sql_types=None):
    """Build a table profile dict from a pandas DataFrame.

    Args:
        df: DataFrame loaded from the table.
        table_name: Name of the table.
        row_count: Actual row count (may differ from len(df) if sampled).
        sql_types: Optional mapping of column name -> SQL type string.

    Returns:
        dict matching the table schema in profile_source() output.
    """
    if sql_types is None:
        sql_types = {}

    columns = []
    date_columns = []
    date_min = None
    date_max = None

    for col_name in df.columns:
        col_info = _profile_column(df[col_name], col_name)

        # Override type with SQL type if available
        if col_name in sql_types:
            col_info["type"] = sql_types[col_name]

        columns.append(col_info)

        # Date detection: check name pattern first, then try parsing
        is_date = False
        if _looks_like_date_column(col_name):
            parsed = _try_parse_dates(df[col_name])
            if parsed is not None:
                is_date = True
        elif pd.api.types.is_datetime64_any_dtype(df[col_name]):
            parsed = df[col_name]
            is_date = True
        else:
            # Try parsing if dtype is object (might be date strings)
            if pd.api.types.is_object_dtype(df[col_name]):
                parsed = _try_parse_dates(df[col_name])
                if parsed is not None:
                    is_date = True

        if is_date:
            date_columns.append(col_name)
            try:
                col_min = parsed.min()
                col_max = parsed.max()
                if pd.notna(col_min):
                    if date_min is None or col_min < date_min:
                        date_min = col_min
                if pd.notna(col_max):
                    if date_max is None or col_max > date_max:
                        date_max = col_max
            except Exception:
                pass

    date_range = None
    if date_min is not None and date_max is not None:
        date_range = {
            "min": str(date_min.date()) if hasattr(date_min, "date") else str(date_min),
            "max": str(date_max.date()) if hasattr(date_max, "date") else str(date_max),
        }

    return {
        "name": table_name,
        "row_count": row_count,
        "description": "",
        "columns": columns,
        "date_columns": date_columns,
        "date_range": date_range,
    }


# ---------------------------------------------------------------------------
# Public API: profile_source
# ---------------------------------------------------------------------------

def _profile_source_inner(connection_info=None):
    """Profile the active data source, returning structured schema information.

    Uses data_helpers.get_connection_for_profiling() to get a connection,
    then introspects all tables: column names, types, nullability, row counts,
    sample values, and basic statistics.

    Args:
        connection_info: Optional dict from get_connection_for_profiling().
            If None, calls it internally.

    Returns:
        dict matching the schema_to_markdown() input format:
        {
            "dataset": str,
            "profiled_at": ISO datetime str,
            "tables": [
                {
                    "name": str,
                    "row_count": int,
                    "description": str (empty initially),
                    "columns": [
                        {
                            "name": str,
                            "type": str (pandas dtype or SQL type),
                            "nullable": bool,
                            "null_count": int,
                            "null_pct": float,
                            "n_unique": int,
                            "sample_values": list (up to 5),
                            "description": str (empty initially),
                            "stats": dict or None (min, max, mean, std for numeric;
                                                   min_len, max_len, avg_len for string),
                        }
                    ],
                    "date_columns": list of column names that appear to be dates,
                    "date_range": {"min": str, "max": str} or None,
                }
            ]
        }
    """
    # Lazy import to avoid circular dependency
    from helpers.data.data_helpers import get_connection_for_profiling

    if connection_info is None:
        connection_info = get_connection_for_profiling()

    src_type = connection_info.get("type", "csv")
    tables_list = connection_info.get("tables", [])
    schema_prefix = connection_info.get("schema_prefix", "")

    profiled_tables = []

    if src_type == "duckdb" and connection_info.get("connection") is not None:
        conn = connection_info["connection"]
        for table_name in tables_list:
            try:
                table_profile = _profile_table_duckdb(conn, table_name, schema_prefix)
                profiled_tables.append(table_profile)
            except Exception as exc:
                print(
                    f"[schema_profiler] Warning: could not profile table "
                    f"'{table_name}' via DuckDB: {exc}"
                )
                profiled_tables.append({
                    "name": table_name,
                    "row_count": 0,
                    "description": "",
                    "columns": [],
                    "date_columns": [],
                    "date_range": None,
                })
    else:
        # CSV path
        csv_dir = connection_info.get("csv_dir", "data/")
        for table_name in tables_list:
            try:
                table_profile = _profile_table_csv(csv_dir, table_name)
                profiled_tables.append(table_profile)
            except Exception as exc:
                print(
                    f"[schema_profiler] Warning: could not profile table "
                    f"'{table_name}' from CSV: {exc}"
                )
                profiled_tables.append({
                    "name": table_name,
                    "row_count": 0,
                    "description": "",
                    "columns": [],
                    "date_columns": [],
                    "date_range": None,
                })

    return {
        "dataset": connection_info.get("schema_prefix", "unknown") or "local",
        "profiled_at": datetime.utcnow().isoformat() + "Z",
        "tables": profiled_tables,
    }


# ---------------------------------------------------------------------------
# Public API: compare_snapshots
# ---------------------------------------------------------------------------

def compare_snapshots(old_schema, new_schema):
    """Compare two schema snapshots and report differences.

    Useful for detecting schema drift (new tables, dropped columns,
    type changes, significant row count changes).

    Args:
        old_schema: Previous profile_source() output.
        new_schema: Current profile_source() output.

    Returns:
        dict:
        {
            "tables_added": [str],
            "tables_removed": [str],
            "tables_modified": [
                {
                    "name": str,
                    "columns_added": [str],
                    "columns_removed": [str],
                    "type_changes": [{"column": str, "old_type": str, "new_type": str}],
                    "row_count_change": {"old": int, "new": int, "pct_change": float},
                }
            ],
            "is_breaking": bool (true if any tables removed or critical columns dropped),
            "summary": str (human-readable),
        }
    """
    old_tables = {t["name"]: t for t in old_schema.get("tables", [])}
    new_tables = {t["name"]: t for t in new_schema.get("tables", [])}

    old_names = set(old_tables.keys())
    new_names = set(new_tables.keys())

    tables_added = sorted(new_names - old_names)
    tables_removed = sorted(old_names - new_names)

    tables_modified = []
    for name in sorted(old_names & new_names):
        old_t = old_tables[name]
        new_t = new_tables[name]

        old_cols = {c["name"]: c for c in old_t.get("columns", [])}
        new_cols = {c["name"]: c for c in new_t.get("columns", [])}

        old_col_names = set(old_cols.keys())
        new_col_names = set(new_cols.keys())

        columns_added = sorted(new_col_names - old_col_names)
        columns_removed = sorted(old_col_names - new_col_names)

        # Type changes
        type_changes = []
        for col_name in sorted(old_col_names & new_col_names):
            old_type = str(old_cols[col_name].get("type", ""))
            new_type = str(new_cols[col_name].get("type", ""))
            if old_type != new_type:
                type_changes.append({
                    "column": col_name,
                    "old_type": old_type,
                    "new_type": new_type,
                })

        # Row count change
        old_rows = old_t.get("row_count", 0)
        new_rows = new_t.get("row_count", 0)
        if old_rows > 0:
            pct_change = round(100.0 * (new_rows - old_rows) / old_rows, 2)
        else:
            pct_change = 100.0 if new_rows > 0 else 0.0

        row_count_change = {
            "old": old_rows,
            "new": new_rows,
            "pct_change": pct_change,
        }

        # Only include if something actually changed
        if columns_added or columns_removed or type_changes or old_rows != new_rows:
            tables_modified.append({
                "name": name,
                "columns_added": columns_added,
                "columns_removed": columns_removed,
                "type_changes": type_changes,
                "row_count_change": row_count_change,
            })

    # Breaking change detection
    is_breaking = len(tables_removed) > 0 or any(
        len(m["columns_removed"]) > 0 for m in tables_modified
    )

    # Human-readable summary
    parts = []
    if tables_added:
        parts.append(f"{len(tables_added)} table(s) added: {', '.join(tables_added)}")
    if tables_removed:
        parts.append(f"{len(tables_removed)} table(s) removed: {', '.join(tables_removed)}")
    if tables_modified:
        parts.append(f"{len(tables_modified)} table(s) modified")
    if not parts:
        parts.append("No schema changes detected.")
    if is_breaking:
        parts.insert(0, "BREAKING CHANGES DETECTED.")

    return {
        "tables_added": tables_added,
        "tables_removed": tables_removed,
        "tables_modified": tables_modified,
        "is_breaking": is_breaking,
        "summary": " ".join(parts),
    }


# ---------------------------------------------------------------------------
# Public API: discover_relationships
# ---------------------------------------------------------------------------

def discover_relationships(schema, sample_size=1000):
    """Heuristically discover foreign key relationships between tables.

    Uses column name matching (e.g., orders.customer_id -> customers.id),
    value overlap analysis, and cardinality checks to suggest relationships.

    Args:
        schema: Output from profile_source().
        sample_size: Number of rows to sample for value overlap analysis.

    Returns:
        list of dicts:
        [
            {
                "from_table": str,
                "from_column": str,
                "to_table": str,
                "to_column": str,
                "confidence": float (0-1),
                "method": str ("name_match" | "value_overlap" | "both"),
                "cardinality": str ("many-to-one" | "one-to-one" | "many-to-many"),
            }
        ]
    """
    tables = schema.get("tables", [])
    if not tables:
        return []

    # Build lookup structures
    table_columns = {}  # table_name -> {col_name: col_info}
    table_samples = {}  # table_name -> {col_name: set of sample values}

    for table in tables:
        t_name = table["name"]
        cols = {}
        samples = {}
        for col in table.get("columns", []):
            c_name = col["name"]
            cols[c_name] = col
            # Use sample_values for overlap checking
            sv = col.get("sample_values", [])
            if sv:
                samples[c_name] = set(sv)
        table_columns[t_name] = cols
        table_samples[t_name] = samples

    relationships = []
    seen = set()  # Avoid duplicate pairs

    for table in tables:
        from_table = table["name"]
        for col in table.get("columns", []):
            from_col = col["name"]

            # --- Strategy 1: Name matching ---
            # If column ends with _id, look for a target table
            candidates = _find_name_match_candidates(
                from_table, from_col, table_columns,
            )

            for to_table, to_col, name_confidence in candidates:
                pair_key = (from_table, from_col, to_table, to_col)
                reverse_key = (to_table, to_col, from_table, from_col)
                if pair_key in seen or reverse_key in seen:
                    continue
                seen.add(pair_key)

                # --- Strategy 2: Value overlap ---
                overlap_confidence = _check_value_overlap(
                    table_samples.get(from_table, {}).get(from_col, set()),
                    table_samples.get(to_table, {}).get(to_col, set()),
                )

                # Combine confidences
                if name_confidence > 0 and overlap_confidence > 0:
                    combined = min(1.0, (name_confidence + overlap_confidence) / 2 + 0.1)
                    method = "both"
                elif name_confidence > 0:
                    combined = name_confidence
                    method = "name_match"
                else:
                    combined = overlap_confidence
                    method = "value_overlap"

                # Estimate cardinality
                cardinality = _estimate_cardinality(
                    col, table_columns.get(to_table, {}).get(to_col, {}),
                )

                if combined >= 0.3:
                    relationships.append({
                        "from_table": from_table,
                        "from_column": from_col,
                        "to_table": to_table,
                        "to_column": to_col,
                        "confidence": round(combined, 2),
                        "method": method,
                        "cardinality": cardinality,
                    })

    # Sort by confidence descending
    relationships.sort(key=lambda r: r["confidence"], reverse=True)
    return relationships


# ---------------------------------------------------------------------------
# Relationship discovery helpers
# ---------------------------------------------------------------------------

def _find_name_match_candidates(from_table, from_col, table_columns):
    """Find candidate FK targets by column naming conventions.

    Returns a list of (to_table, to_column, confidence) tuples.
    """
    candidates = []
    lower_col = from_col.lower()

    # Pattern: column ends with _id (e.g., customer_id -> customers.id)
    if lower_col.endswith("_id"):
        prefix = lower_col[:-3]  # "customer"

        for other_table, other_cols in table_columns.items():
            if other_table == from_table:
                continue

            other_lower = other_table.lower()

            # Exact match: customer_id -> customer.id or customers.id
            if other_lower == prefix or other_lower == prefix + "s":
                # Check for "id" column in target table
                for target_col in ("id", from_col, f"{prefix}_id"):
                    if target_col in other_cols:
                        candidates.append((other_table, target_col, 0.8))
                        break

            # Partial match: the table name contains the prefix
            elif prefix in other_lower:
                for target_col in ("id", from_col, f"{prefix}_id"):
                    if target_col in other_cols:
                        candidates.append((other_table, target_col, 0.5))
                        break

    # Pattern: column name matches a table name (e.g., "category" col + "categories" table)
    for other_table, other_cols in table_columns.items():
        if other_table == from_table:
            continue
        other_lower = other_table.lower()
        if (
            lower_col == other_lower
            or lower_col + "s" == other_lower
            or lower_col == other_lower.rstrip("s")
        ):
            # Look for an id-like column in the target
            for target_col in ("id", f"{lower_col}_id", f"{other_lower}_id"):
                if target_col in other_cols:
                    candidates.append((other_table, target_col, 0.4))
                    break

    return candidates


def _check_value_overlap(from_values, to_values):
    """Check what fraction of from_values appear in to_values.

    Returns a confidence score between 0 and 1.
    """
    if not from_values or not to_values:
        return 0.0

    try:
        overlap = len(from_values & to_values)
        pct = overlap / len(from_values) if len(from_values) > 0 else 0.0
        return round(min(pct, 1.0), 2)
    except Exception:
        return 0.0


def _estimate_cardinality(from_col_info, to_col_info):
    """Estimate the relationship cardinality from column statistics.

    Uses n_unique and row_count heuristics to guess the join type.
    """
    from_unique = from_col_info.get("n_unique", 0)
    to_unique = to_col_info.get("n_unique", 0)

    if from_unique == 0 or to_unique == 0:
        return "many-to-one"

    # If the FK column has many more values than uniques in target,
    # it is likely many-to-one
    if from_unique > to_unique * 0.9:
        return "one-to-one"

    return "many-to-one"


# ---------------------------------------------------------------------------
# Public API: list_sources
# ---------------------------------------------------------------------------

def list_sources():
    """List all configured data sources from .knowledge/datasets/.

    Scans the datasets directory for subdirectories containing a
    manifest.yaml, and returns basic info about each one.

    Returns:
        list of dicts:
        [
            {
                "dataset_id": str,
                "display_name": str,
                "is_active": bool,
                "domain": str,
                "table_count": int,
                "connection_type": str,
                "is_seed": bool,
            }
        ]
    """
    knowledge_dir = Path(".knowledge")
    datasets_dir = knowledge_dir / "datasets"
    active_yaml = knowledge_dir / "active.yaml"

    if not datasets_dir.is_dir():
        return []

    # Read active dataset
    active_id = None
    try:
        import yaml
        if active_yaml.exists():
            with open(active_yaml) as f:
                data = yaml.safe_load(f)
            if isinstance(data, dict):
                active_id = data.get("active_dataset")
    except Exception:
        pass

    sources = []
    for entry in sorted(datasets_dir.iterdir()):
        if not entry.is_dir():
            continue
        manifest_path = entry / "manifest.yaml"
        if not manifest_path.exists():
            continue

        try:
            import yaml
            with open(manifest_path) as f:
                manifest = yaml.safe_load(f)
            if not isinstance(manifest, dict):
                continue
        except Exception:
            continue

        dataset_id = manifest.get("dataset_id", entry.name)
        conn = manifest.get("connection", {})
        summary = manifest.get("summary", {})

        sources.append({
            "dataset_id": dataset_id,
            "display_name": manifest.get("display_name", dataset_id),
            "is_active": dataset_id == active_id,
            "domain": manifest.get("domain", "unknown"),
            "table_count": summary.get("table_count", 0),
            "connection_type": conn.get("type", "csv"),
            "is_seed": manifest.get("is_seed", False),
        })

    return sources


# ---------------------------------------------------------------------------
# Public API: get_table_reference
# ---------------------------------------------------------------------------

def get_table_reference(table_name, schema=None):
    """Get the qualified table reference for SQL queries.

    Resolves the correct schema prefix from the active dataset's manifest
    and returns a properly qualified table name for use in SQL queries.

    Args:
        table_name: Unqualified table name (e.g., "orders").
        schema: Optional schema override. If None, reads from active
            dataset manifest.

    Returns:
        dict:
        {
            "qualified_name": str (e.g., "my_dataset.orders"),
            "schema": str (e.g., "my_dataset"),
            "table": str (e.g., "orders"),
            "connection_type": str (e.g., "motherduck"),
            "exists": bool (True if table is in the dataset's known tables),
        }
    """
    # Lazy import to avoid circular dependency
    from helpers.data.data_helpers import detect_active_source

    source_info = detect_active_source()

    if schema is None:
        schema = source_info.get("schema_prefix", "")

    # Check if table is in known tables (honor the manifest's files: list so
    # datasets sharing a folder don't bleed into each other's inventory)
    csv_tables = []
    try:
        from helpers.data.data_helpers import list_tables
        csv_path = source_info.get("csv_path")
        files = source_info.get("files")
        if csv_path or files:
            csv_tables = list_tables(csv_path, files=files)
    except Exception:
        pass

    # Build qualified name
    if schema:
        qualified_name = f"{schema}.{table_name}"
    else:
        qualified_name = table_name

    return {
        "qualified_name": qualified_name,
        "schema": schema or "",
        "table": table_name,
        "connection_type": source_info.get("type", "csv"),
        "exists": table_name in csv_tables,
    }


# ---------------------------------------------------------------------------
# Public API: profile_external_warehouse
# ---------------------------------------------------------------------------

def profile_external_warehouse(connection_config):
    """Profile an external warehouse using ConnectionManager.

    Supports PostgreSQL, BigQuery, Snowflake, and DuckDB connections.
    Uses the SQL dialect system for warehouse-specific introspection queries.

    Args:
        connection_config: Dict with connection details matching
            ConnectionManager expectations (type, host, port, database,
            schema, user, etc.) or a path to a manifest.yaml.

    Returns:
        Same schema dict as profile_source(), suitable for
        schema_to_markdown().
    """
    from helpers.data.connection_manager import ConnectionManager

    with ConnectionManager(connection_config) as cm:
        tables = cm.list_tables()
        profiled_tables = []

        for table_name in tables:
            try:
                # Get schema info from ConnectionManager
                columns_info = cm.get_table_schema(table_name)

                # Sample rows for profiling
                try:
                    sample_df = cm.query(
                        f"SELECT * FROM {cm.schema_prefix + '.' + table_name if cm.schema_prefix else table_name} LIMIT 5000"
                    )
                except Exception:
                    sample_df = pd.DataFrame()

                # Get row count
                try:
                    count_result = cm.query(
                        f"SELECT COUNT(*) AS n FROM {cm.schema_prefix + '.' + table_name if cm.schema_prefix else table_name}"
                    )
                    row_count = int(count_result.iloc[0, 0]) if len(count_result) > 0 else 0
                except Exception:
                    row_count = len(sample_df)

                if len(sample_df) > 0:
                    # Use shared profiling logic
                    sql_types = {}
                    for col in columns_info:
                        sql_types[col["name"]] = col.get("type", "unknown")

                    table_profile = _profile_table_from_df(
                        sample_df, table_name, row_count, sql_types
                    )
                else:
                    # Fallback: use column info without data profiling
                    columns = []
                    for col in columns_info:
                        columns.append({
                            "name": col["name"],
                            "type": col.get("type", "unknown"),
                            "nullable": col.get("nullable", True),
                            "null_count": 0,
                            "null_pct": 0.0,
                            "n_unique": 0,
                            "sample_values": [],
                            "description": "",
                            "stats": None,
                        })
                    table_profile = {
                        "name": table_name,
                        "row_count": row_count,
                        "description": "",
                        "columns": columns,
                        "date_columns": [],
                        "date_range": None,
                    }

                profiled_tables.append(table_profile)

            except Exception as exc:
                print(
                    f"[schema_profiler] Warning: could not profile table "
                    f"'{table_name}' via external warehouse: {exc}"
                )
                profiled_tables.append({
                    "name": table_name,
                    "row_count": 0,
                    "description": "",
                    "columns": [],
                    "date_columns": [],
                    "date_range": None,
                })

    dataset_label = connection_config.get("schema", "") or connection_config.get("database", "external")
    return {
        "dataset": dataset_label,
        "profiled_at": datetime.utcnow().isoformat() + "Z",
        "tables": profiled_tables,
    }


def profile_source(*args, **kwargs):
    """Wrapper: loud failure when no tables resolve (silent-empty guard, 2026-08-25)."""
    result = _profile_source_inner(*args, **kwargs)
    try:
        tables = result.get("tables") if isinstance(result, dict) else None
        if not tables:
            print("WARNING: profile_source resolved ZERO TABLES. The dataset manifest likely "
                  "lacks a local_data/connection block this reader understands. Check "
                  ".knowledge/datasets/<id>/manifest.yaml before trusting any profile output.")
    except Exception:
        pass
    return result
