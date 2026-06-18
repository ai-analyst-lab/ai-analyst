#!/usr/bin/env python3
"""CLI wrapper for query logging — the bridge between agent instructions and helpers/query_log.py.

Agents are prompt templates that Claude reads as instructions. Claude runs SQL through
MCP tools, not through a running Python process. This script lets agents log queries
via Bash after every SQL execution:

    python3 scripts/log_query.py \
        --dataset snowflake-tpch \
        --date 2026-04-04 \
        --agent descriptive-analytics \
        --step 5 \
        --purpose "Revenue by segment" \
        --sql "SELECT segment, SUM(revenue) FROM orders GROUP BY segment" \
        --dialect snowflake \
        --tables ORDERS \
        --result "5 rows, revenue by segment" \
        --rows 5

All flags except --dataset, --date, --agent, --purpose, and --sql are optional.
The --sql flag accepts the query text directly or reads from stdin if set to "-".

Exit codes:
    0 — entry logged successfully
    1 — missing required arguments
    2 — write error
"""

import argparse
import sys
from pathlib import Path

# Add project root to path so helpers/ is importable
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from helpers.query_log import append_entry


def _detect_defaults():
    """Auto-detect dialect and connection type from the active dataset manifest.

    Falls back to 'unknown' (not 'duckdb') so bad defaults are obvious.
    """
    dialect = "unknown"
    connection = "unknown"
    try:
        import yaml
        active_path = project_root / ".knowledge" / "active.yaml"
        if active_path.exists():
            with open(active_path) as f:
                active = yaml.safe_load(f) or {}
            dataset_id = active.get("dataset_id") or active.get("active", "")
            manifest_path = project_root / ".knowledge" / "datasets" / dataset_id / "manifest.yaml"
            if manifest_path.exists():
                with open(manifest_path) as f:
                    manifest = yaml.safe_load(f) or {}
                conn_type = manifest.get("connection_type", "")
                if "snowflake" in conn_type.lower():
                    dialect = "snowflake"
                    connection = conn_type
                elif "postgres" in conn_type.lower():
                    dialect = "postgres"
                    connection = conn_type
                elif "bigquery" in conn_type.lower():
                    dialect = "bigquery"
                    connection = conn_type
                elif "duckdb" in conn_type.lower() or "motherduck" in conn_type.lower():
                    dialect = "duckdb"
                    connection = conn_type
                elif "csv" in conn_type.lower():
                    dialect = "duckdb"
                    connection = "csv"
    except Exception:
        pass  # If detection fails, use 'unknown' — better than wrong
    return dialect, connection


def main():
    detected_dialect, detected_connection = _detect_defaults()

    parser = argparse.ArgumentParser(
        description="Log a SQL query to the JSONL query log."
    )

    # Required
    parser.add_argument("--dataset", required=True, help="Dataset name (e.g., snowflake-tpch)")
    parser.add_argument("--date", required=True, help="Analysis date YYYY-MM-DD")
    parser.add_argument("--agent", required=True, help="Agent name (e.g., descriptive-analytics)")
    parser.add_argument("--purpose", required=True, help="Why this query was run")
    parser.add_argument("--sql", required=True, help="SQL query text, or '-' to read from stdin")

    # Optional — defaults auto-detected from active dataset
    parser.add_argument("--step", type=float, default=0, help="Pipeline step number")
    parser.add_argument("--dialect", default=detected_dialect, help=f"SQL dialect (auto-detected: {detected_dialect})")
    parser.add_argument("--connection", default=detected_connection, help=f"Connection type (auto-detected: {detected_connection})")
    parser.add_argument("--tables", nargs="*", default=[], help="Tables accessed")
    parser.add_argument("--columns", nargs="*", default=[], help="Columns accessed")
    parser.add_argument("--result", default="", help="Brief result summary")
    parser.add_argument("--result-value", default=None, help="Key numeric result")
    parser.add_argument("--rows", type=int, default=None, help="Row count returned")
    parser.add_argument("--time-ms", type=float, default=0.0, help="Execution time in ms")
    parser.add_argument("--claims", nargs="*", default=[], help="Claim IDs this query supports")
    parser.add_argument("--status", default="success", choices=["success", "error"], help="Query status")
    parser.add_argument("--error", default=None, help="Error message if status=error")
    parser.add_argument("--log-path", default=None, help="Explicit log file path (overrides default)")

    args = parser.parse_args()

    # Read SQL from stdin if "-"
    sql = args.sql
    if sql == "-":
        sql = sys.stdin.read().strip()
        if not sql:
            print("ERROR: No SQL provided on stdin", file=sys.stderr)
            sys.exit(1)

    # Parse result_value
    result_value = args.result_value
    if result_value is not None:
        try:
            result_value = float(result_value)
        except ValueError:
            pass  # keep as string

    # Override log path if specified
    if args.log_path:
        import helpers.query_log as ql
        ql._WORKING_DIR = Path(args.log_path).parent
        # Monkey-patch the path function to use the explicit path
        explicit_path = Path(args.log_path)
        ql._log_path = lambda d, dt: explicit_path

    try:
        entry = append_entry(
            dataset_name=args.dataset,
            date=args.date,
            agent=args.agent,
            pipeline_step=args.step,
            purpose=args.purpose,
            sql=sql,
            dialect=args.dialect,
            connection_type=args.connection,
            tables_accessed=args.tables,
            columns_accessed=args.columns,
            result_summary=args.result,
            result_value=result_value,
            row_count=args.rows,
            execution_ms=args.time_ms,
            claim_ids=args.claims,
            status=args.status,
            error=args.error,
        )
        print(f"Logged: {entry['query_id']} ({args.agent}, step {args.step})")
    except Exception as e:
        print(f"ERROR: Failed to log query: {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
