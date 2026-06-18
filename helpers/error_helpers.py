"""
User-friendly error wrappers for AI Analyst.

Translates cryptic Python/SQL exceptions into plain-English messages with
actionable suggestions. Designed for users who are PMs,
designers, and engineers — not Python experts.

Usage:
    from helpers.error_helpers import friendly_error, safe_query

    # Wrap any exception for a friendly message
    try:
        df = conn.sql("SELECT * FROM nonexistent_table").df()
    except Exception as exc:
        result = friendly_error(exc, context="running SQL query")
        print(result["message"])
        print(result["suggestion"])

    # safe_query: execute SQL with automatic fallback
    df, info = safe_query(conn, "SELECT * FROM orders LIMIT 10",
                          fallback_csv="orders")
    print(info["source"])  # "duckdb" or "csv_fallback"
"""

import difflib
import traceback
from pathlib import Path

import pandas as pd

# DuckDB is optional — CSV fallback path works without it.
try:
    import duckdb

    _DUCKDB_AVAILABLE = True
except ImportError:
    _DUCKDB_AVAILABLE = False


# ---------------------------------------------------------------------------
# Common SQL mistake patterns
# ---------------------------------------------------------------------------

_SQL_HINTS = [
    {
        "pattern": "GROUP BY",
        "keywords": ["not an aggregate", "not in GROUP BY", "must appear in the GROUP BY"],
        "message": "You have columns in SELECT that are not in GROUP BY and not aggregated.",
        "suggestion": (
            "Every column in SELECT must either be in GROUP BY or wrapped in an "
            "aggregate function (COUNT, SUM, AVG, etc.).\n"
            "  Example: SELECT region, COUNT(*) FROM orders GROUP BY region"
        ),
    },
    {
        "pattern": "table",
        "keywords": ["Table with name", "does not exist", "Catalog Error", "table not found"],
        "message": "The table name in your query was not found.",
        "suggestion": (
            "Check the table name for typos. Check your active dataset schema\n"
            "for available table names:\n"
            "  Run /data to inspect the active schema, or\n"
            "  conn.sql(\"SHOW TABLES\").df() to list tables.\n"
            "If using MotherDuck: schema.TABLE\n"
            "If using local DuckDB: just TABLE (no schema prefix)"
        ),
    },
    {
        "pattern": "column",
        "keywords": ["Referenced column", "could not find", "not found in FROM", "has no column"],
        "message": "A column name in your query was not recognized.",
        "suggestion": (
            "Check column names for typos. Run this to see available columns:\n"
            "  conn.sql(\"DESCRIBE tablename\").df()\n"
            "Or use the Data Explorer agent to inspect the schema."
        ),
    },
    {
        "pattern": "syntax",
        "keywords": ["syntax error", "Parser Error", "unexpected token"],
        "message": "Your SQL has a syntax error.",
        "suggestion": (
            "Common SQL syntax mistakes:\n"
            "  - Missing comma between column names\n"
            "  - Using = instead of == (SQL uses single =)\n"
            "  - Forgetting quotes around string values: WHERE region = 'West'\n"
            "  - Missing closing parenthesis\n"
            "  - Using LIMIT before ORDER BY (LIMIT goes last)"
        ),
    },
    {
        "pattern": "type",
        "keywords": ["Conversion Error", "Could not convert", "type mismatch", "cannot cast"],
        "message": "There is a data type mismatch in your query.",
        "suggestion": (
            "A column has a different type than expected. Common fixes:\n"
            "  - Cast strings to dates: CAST(date_col AS DATE)\n"
            "  - Cast strings to numbers: CAST(col AS DOUBLE)\n"
            "  - Compare like types: WHERE date_col >= DATE '2024-01-01'"
        ),
    },
    {
        "pattern": "ambiguous",
        "keywords": ["ambiguous", "Ambiguous reference"],
        "message": "A column name exists in multiple tables and SQL cannot tell which one you mean.",
        "suggestion": (
            "Use table aliases to disambiguate:\n"
            "  SELECT o.user_id, u.region\n"
            "  FROM orders o JOIN users u ON o.user_id = u.user_id"
        ),
    },
]


# ---------------------------------------------------------------------------
# Friendly error translator
# ---------------------------------------------------------------------------

def friendly_error(exception, context=None):
    """Translate a Python exception into a student-friendly error message.

    Takes any exception and uses pattern matching on the exception type and
    message to provide specific, actionable guidance. Designed for AI Analyst
    students who may not be experienced Python developers.

    Args:
        exception: Any Python exception instance.
        context: Optional string describing what was happening when the
            error occurred (e.g., "loading CSV file", "running SQL query").

    Returns:
        dict with keys:
            error_type (str): Short category label (e.g., "connection_error").
            message (str): Plain-English explanation of what went wrong.
            suggestion (str): What the student should try next.
            technical (str): Original traceback for debugging.
    """
    exc_type = type(exception).__name__
    exc_msg = str(exception)
    tb = traceback.format_exception(type(exception), exception, exception.__traceback__)
    technical = "".join(tb)

    context_prefix = f"While {context}: " if context else ""

    # --- Exact isinstance checks first (most specific) ---

    # Empty data file (pd.errors.EmptyDataError — file exists but has no data)
    if isinstance(exception, pd.errors.EmptyDataError):
        return {
            "error_type": "empty_file",
            "message": (
                f"{context_prefix}The data file appears to be empty."
            ),
            "suggestion": (
                "The file exists but contains no data. Check that:\n"
                "  - The file was fully downloaded (not a partial download)\n"
                "  - The file is not corrupted (try opening in a text editor)\n"
                "  - You are pointing to the correct file path"
            ),
            "technical": technical,
        }

    # Import errors
    if isinstance(exception, (ImportError, ModuleNotFoundError)):
        module_name = _extract_module_name(exc_msg)
        pip_cmd = f"pip install {module_name}" if module_name else "pip install <package>"
        return {
            "error_type": "import_error",
            "message": (
                f"{context_prefix}A required Python package is not installed: {exc_msg}"
            ),
            "suggestion": (
                f"Install the missing package:\n"
                f"  {pip_cmd}\n"
                f"\n"
                f"Common packages:\n"
                f"  pip install duckdb pandas matplotlib scipy numpy"
            ),
            "technical": technical,
        }

    # File not found
    if isinstance(exception, FileNotFoundError):
        return {
            "error_type": "file_not_found",
            "message": (
                f"{context_prefix}File not found: {exc_msg}"
            ),
            "suggestion": (
                "Check the file path and name. Common data locations:\n"
                "  - data/hero/ — Hero dataset\n"
                "  - data/examples/ — Example datasets\n"
                "Use /connect-data to add a new dataset, or:\n"
                "  from helpers.data_helpers import list_tables\n"
                "  print(list_tables())  # see available tables"
            ),
            "technical": technical,
        }

    # Permission errors
    if isinstance(exception, PermissionError):
        return {
            "error_type": "permission_error",
            "message": (
                f"{context_prefix}Permission denied: {exc_msg}"
            ),
            "suggestion": (
                "The file or database is locked or you do not have permission to access it.\n"
                "  - Close any other programs that may have the file open\n"
                "  - Check file permissions\n"
                "  - For DuckDB: only one process can write at a time"
            ),
            "technical": technical,
        }

    # Unsupported file type
    if isinstance(exception, ValueError) and "unsupported file type" in exc_msg.lower():
        return {
            "error_type": "unsupported_file",
            "message": (
                f"{context_prefix}This file format is not supported: {exc_msg}"
            ),
            "suggestion": (
                "Supported formats: CSV (.csv), Excel (.xlsx, .xls), "
                "Parquet (.parquet), JSON (.json).\n"
                "If your file is in another format, convert it to CSV first."
            ),
            "technical": technical,
        }

    # --- Pattern-based checks (message inspection) ---

    # SQL syntax / query errors (most common student errors)
    sql_hint = _match_sql_hint(exc_msg)
    if sql_hint:
        return {
            "error_type": "sql_error",
            "message": f"{context_prefix}{sql_hint['message']}",
            "suggestion": sql_hint["suggestion"],
            "technical": technical,
        }

    # Missing column errors
    if _is_missing_column_error(exception):
        col_name = _extract_column_name(exc_msg)
        available = _extract_available_columns(exc_msg)
        closest = _suggest_closest_column(col_name, available) if col_name and available else None

        suggestion_parts = []
        if closest:
            suggestion_parts.append(f"Did you mean '{closest}'?")
        if available:
            suggestion_parts.append(f"Available columns: {', '.join(available[:20])}")
        else:
            suggestion_parts.append(
                "Run conn.sql(\"DESCRIBE tablename\").df() to see available columns."
            )
        suggestion_parts.append(
            "Tip: Column names are case-sensitive in DuckDB."
        )

        return {
            "error_type": "missing_column",
            "message": (
                f"{context_prefix}Column '{col_name or '?'}' was not found in the data."
            ),
            "suggestion": "\n".join(suggestion_parts),
            "technical": technical,
        }

    # Empty DataFrame warnings (keyword-based — for generic exceptions)
    if _is_empty_dataframe_error(exception):
        return {
            "error_type": "empty_dataframe",
            "message": (
                f"{context_prefix}The query returned zero rows (empty DataFrame)."
            ),
            "suggestion": (
                "Common reasons for empty results:\n"
                "  - WHERE clause is too restrictive — try removing filters one at a time\n"
                "  - Date range might not match the data — check min/max dates first:\n"
                "    conn.sql(\"SELECT MIN(date_col), MAX(date_col) FROM table\").df()\n"
                "  - INNER JOIN dropped all rows — check join keys match between tables\n"
                "  - Table might actually be empty — check row count:\n"
                "    conn.sql(\"SELECT COUNT(*) FROM table\").df()"
            ),
            "technical": technical,
        }

    # --- DuckDB connection failures ---
    if _is_duckdb_connection_error(exception):
        return {
            "error_type": "connection_error",
            "message": (
                f"{context_prefix}Could not connect to DuckDB. "
                "The database file may be missing, corrupted, or locked by another process."
            ),
            "suggestion": (
                "Try these steps:\n"
                "  1. Check that the .duckdb file exists in your active dataset directory\n"
                "  2. Close any other programs using the database\n"
                "  3. Fall back to CSV: from helpers.data_helpers import read_table\n"
                "     df = read_table('orders')\n"
                "  4. If DuckDB is not installed: pip install duckdb"
            ),
            "technical": technical,
        }

    # --- MCP / MotherDuck connection failures ---
    if _is_mcp_connection_error(exception):
        return {
            "error_type": "mcp_connection_error",
            "message": (
                f"{context_prefix}Could not connect to MotherDuck via MCP. "
                "This usually means the MCP server is not running or your token is invalid."
            ),
            "suggestion": (
                "Try these steps:\n"
                "  1. Check that your MOTHERDUCK_TOKEN is set in the environment\n"
                "  2. Verify the MCP server is running (check .claude/mcp.json)\n"
                "  3. Fall back to local DuckDB:\n"
                "     from helpers.data_helpers import get_local_connection\n"
                "     conn = get_local_connection()\n"
                "  4. Or fall back to CSV:\n"
                "     from helpers.data_helpers import read_table\n"
                "     df = read_table('orders')"
            ),
            "technical": technical,
        }

    # --- Generic fallback ---
    return {
        "error_type": "unknown_error",
        "message": (
            f"{context_prefix}An unexpected error occurred: {exc_type}: {exc_msg}"
        ),
        "suggestion": (
            "This error was not recognized. Things to try:\n"
            "  - Read the error message above for clues\n"
            "  - Check your code for typos\n"
            "  - Restart your Python kernel and try again\n"
            "  - Ask the AI Analyst for help by pasting the error message"
        ),
        "technical": technical,
    }


# ---------------------------------------------------------------------------
# Safe query executor with CSV fallback
# ---------------------------------------------------------------------------

def safe_query(conn, sql, fallback_csv=None):
    """Execute a SQL query with friendly errors and optional CSV fallback.

    Tries to execute the query via DuckDB. If it fails and a CSV fallback
    table name is provided, automatically loads the data from CSV instead.

    Args:
        conn: DuckDB connection (or None if connection failed).
        sql: SQL query string to execute.
        fallback_csv: Optional table name for CSV fallback (e.g., "orders").
            If the SQL query fails and this is provided, the function will
            load the corresponding CSV from the active dataset's data directory.

    Returns:
        tuple of (DataFrame, source_info) where source_info is a dict with:
            source (str): "duckdb" or "csv_fallback"
            query (str): The original SQL or CSV path used
            status (str): "ok" or "fallback"
            error (dict or None): friendly_error output if fallback was used
    """
    # --- Handle missing connection ---
    if conn is None:
        if fallback_csv:
            return _csv_fallback(
                fallback_csv,
                error_info=friendly_error(
                    ConnectionError("No DuckDB connection available"),
                    context="executing SQL query",
                ),
            )
        return (
            pd.DataFrame(),
            {
                "source": "none",
                "query": sql,
                "status": "error",
                "error": friendly_error(
                    ConnectionError("No DuckDB connection available"),
                    context="executing SQL query",
                ),
            },
        )

    # --- Try the SQL query ---
    try:
        df = conn.sql(sql).df()

        # Warn on empty results (not an error, but worth noting)
        source_info = {
            "source": "duckdb",
            "query": sql,
            "status": "ok",
            "error": None,
        }
        if len(df) == 0:
            source_info["warning"] = (
                "Query returned 0 rows. Check your WHERE clause and "
                "date ranges if this is unexpected."
            )

        return (df, source_info)

    except Exception as exc:
        error_info = friendly_error(exc, context="executing SQL query")

        # --- Attempt CSV fallback ---
        if fallback_csv:
            return _csv_fallback(fallback_csv, error_info=error_info)

        return (
            pd.DataFrame(),
            {
                "source": "duckdb",
                "query": sql,
                "status": "error",
                "error": error_info,
            },
        )


# ---------------------------------------------------------------------------
# Empty DataFrame checker
# ---------------------------------------------------------------------------

def check_empty_dataframe(df, label="result"):
    """Check if a DataFrame is empty and return a structured warning.

    Useful as a post-query sanity check. Returns a PASS/WARN result dict
    matching the sql_helpers convention.

    Args:
        df: pandas DataFrame to check.
        label: Human-readable label for the data (e.g., "orders query").

    Returns:
        dict with keys: status, message, details
    """
    if len(df) == 0:
        return {
            "status": "WARN",
            "message": (
                f"'{label}' returned 0 rows. The data may be filtered too "
                "aggressively, or the table may be empty."
            ),
            "details": {
                "label": label,
                "row_count": 0,
                "columns": list(df.columns) if hasattr(df, "columns") else [],
            },
        }

    return {
        "status": "PASS",
        "message": f"'{label}' returned {len(df):,} rows.",
        "details": {
            "label": label,
            "row_count": len(df),
            "columns": list(df.columns),
        },
    }


# ---------------------------------------------------------------------------
# Column suggestion helper
# ---------------------------------------------------------------------------

def suggest_column(target, available_columns, n=3):
    """Suggest the closest matching column names for a misspelled column.

    Uses difflib's sequence matcher to find close matches. Useful for
    building better error messages when a column name is not found.

    Args:
        target: The column name that was not found.
        available_columns: List of valid column names.
        n: Maximum number of suggestions to return (default 3).

    Returns:
        dict with keys:
            target (str): The original column name.
            suggestions (list of str): Closest matching column names.
            best_match (str or None): The single best match, or None.
    """
    matches = difflib.get_close_matches(target, available_columns, n=n, cutoff=0.4)

    return {
        "target": target,
        "suggestions": matches,
        "best_match": matches[0] if matches else None,
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _is_duckdb_connection_error(exc):
    """Check if an exception is a DuckDB connection failure."""
    exc_msg = str(exc).lower()
    exc_type = type(exc).__name__

    # Direct connection errors
    if isinstance(exc, (ConnectionError, OSError)):
        return "duckdb" in exc_msg or "database" in exc_msg

    # DuckDB-specific errors
    if _DUCKDB_AVAILABLE and isinstance(exc, duckdb.Error):
        connection_keywords = ["connection", "database", "locked", "cannot open"]
        return any(kw in exc_msg for kw in connection_keywords)

    # Generic errors that look like connection issues
    if exc_type in ("IOException", "InvalidInputException"):
        return True

    return False


def _is_mcp_connection_error(exc):
    """Check if an exception is an MCP/MotherDuck connection failure."""
    exc_msg = str(exc).lower()

    # Exclude SQL parse/query errors that happen to contain "token"
    # (e.g., "unexpected token" is a SQL syntax error, not an MCP issue)
    sql_noise = ["syntax error", "parser error", "unexpected token", "parse error"]
    if any(kw in exc_msg for kw in sql_noise):
        return False

    mcp_keywords = [
        "mcp", "motherduck", "md:", "authentication",
        "unauthorized", "could not connect to remote",
        "motherduck_token", "invalid token",
    ]
    return any(kw in exc_msg for kw in mcp_keywords)


def _is_missing_column_error(exc):
    """Check if an exception is a missing column error."""
    exc_msg = str(exc).lower()

    column_keywords = [
        "column", "not found", "has no column", "referenced column",
        "could not find", "keyerror", "not in index",
    ]

    if isinstance(exc, KeyError):
        return True

    return any(kw in exc_msg for kw in column_keywords)


def _is_empty_dataframe_error(exc):
    """Check if an exception relates to an empty DataFrame."""
    exc_msg = str(exc).lower()

    return (
        "empty" in exc_msg
        and ("dataframe" in exc_msg or "data frame" in exc_msg or "result" in exc_msg)
    ) or isinstance(exc, pd.errors.EmptyDataError)


def _extract_column_name(exc_msg):
    """Try to extract the column name from an error message."""
    import re

    # Pattern: "column X not found" or "Referenced column 'X'"
    patterns = [
        r"[Cc]olumn\s+[\"']([^\"']+)[\"']",
        r"[Rr]eferenced column\s+[\"']([^\"']+)[\"']",
        r"KeyError:\s+[\"']([^\"']+)[\"']",
        r"not in index.*\[([^\]]+)\]",
    ]
    for pattern in patterns:
        match = re.search(pattern, exc_msg)
        if match:
            return match.group(1)

    # KeyError often has the column name as the entire message
    if "keyerror" in exc_msg.lower():
        cleaned = exc_msg.strip("'\" ")
        if len(cleaned) < 64:
            return cleaned

    return None


def _extract_available_columns(exc_msg):
    """Try to extract a list of available columns from an error message."""
    import re

    # DuckDB includes candidates: "Did you mean: col1, col2, col3"
    match = re.search(r"[Dd]id you mean[:\s]+([^\n]+)", exc_msg)
    if match:
        candidates = [c.strip().strip("'\"") for c in match.group(1).split(",")]
        return [c for c in candidates if c]

    # Some errors include "Candidates: col1, col2"
    match = re.search(r"[Cc]andidates?[:\s]+([^\n]+)", exc_msg)
    if match:
        candidates = [c.strip().strip("'\"") for c in match.group(1).split(",")]
        return [c for c in candidates if c]

    return []


def _suggest_closest_column(target, available):
    """Find the closest matching column name."""
    if not target or not available:
        return None
    matches = difflib.get_close_matches(target, available, n=1, cutoff=0.4)
    return matches[0] if matches else None


def _extract_module_name(exc_msg):
    """Extract the module name from an ImportError message."""
    import re

    # "No module named 'duckdb'" or "No module named 'scipy.stats'"
    match = re.search(r"No module named ['\"]([^'\"]+)['\"]", exc_msg)
    if match:
        module = match.group(1)
        # Return the top-level package for pip install
        return module.split(".")[0]

    return None


def _match_sql_hint(exc_msg):
    """Match an error message against known SQL mistake patterns."""
    exc_lower = exc_msg.lower()
    for hint in _SQL_HINTS:
        if any(kw.lower() in exc_lower for kw in hint["keywords"]):
            return hint
    return None


def _csv_fallback(table_name, error_info, data_dir=None):
    """Attempt to load data from CSV as a fallback.

    Args:
        table_name: Table name (e.g., "orders") — maps to {data_dir}/{table}.csv.
        error_info: The friendly_error dict from the original failure.
        data_dir: Directory containing the CSV files. If None, attempts to
            resolve from the active dataset manifest.

    Returns:
        tuple of (DataFrame, source_info)
    """
    if data_dir is None:
        # Try to resolve from active dataset manifest
        try:
            from helpers.data_helpers import detect_active_source

            source_info = detect_active_source()
            data_dir = source_info.get("local_data", {}).get("path")
        except Exception:
            data_dir = None

    if data_dir is None:
        return (
            pd.DataFrame(),
            {
                "source": "csv_fallback",
                "query": table_name,
                "status": "error",
                "error": {
                    "error_type": "fallback_failed",
                    "message": (
                        "SQL query failed and no CSV data directory is configured. "
                        "Use /connect-data to set up a dataset."
                    ),
                    "suggestion": (
                        "No active dataset data directory found.\n"
                        "Run /connect-data to add a dataset, or pass data_dir explicitly."
                    ),
                    "technical": error_info.get("technical", ""),
                },
            },
        )

    csv_path = Path(data_dir) / f"{table_name}.csv"

    if not csv_path.exists():
        return (
            pd.DataFrame(),
            {
                "source": "csv_fallback",
                "query": str(csv_path),
                "status": "error",
                "error": {
                    "error_type": "fallback_failed",
                    "message": (
                        f"SQL query failed and CSV fallback also failed: "
                        f"{csv_path} not found."
                    ),
                    "suggestion": (
                        f"The CSV file for '{table_name}' was not found at "
                        f"{csv_path}.\n"
                        f"Check that the data files exist in {data_dir}.\n"
                        f"Original error: {error_info['message']}"
                    ),
                    "technical": error_info.get("technical", ""),
                },
            },
        )

    try:
        df = pd.read_csv(csv_path, encoding="utf-8", low_memory=False)
        return (
            df,
            {
                "source": "csv_fallback",
                "query": str(csv_path),
                "status": "fallback",
                "error": error_info,
                "note": (
                    f"SQL query failed — loaded {len(df):,} rows from "
                    f"{csv_path} instead. {error_info['message']}"
                ),
            },
        )
    except Exception as csv_exc:
        csv_error = friendly_error(csv_exc, context="loading CSV fallback")
        return (
            pd.DataFrame(),
            {
                "source": "csv_fallback",
                "query": str(csv_path),
                "status": "error",
                "error": {
                    "error_type": "fallback_failed",
                    "message": (
                        f"Both SQL and CSV fallback failed. "
                        f"SQL: {error_info['message']} | "
                        f"CSV: {csv_error['message']}"
                    ),
                    "suggestion": csv_error["suggestion"],
                    "technical": (
                        error_info.get("technical", "")
                        + "\n--- CSV fallback error ---\n"
                        + csv_error.get("technical", "")
                    ),
                },
            },
        )
