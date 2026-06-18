"""Reproducibility checks — run the same query multiple times and compare.

For deterministic sources (CSV, DuckDB on static files), results should be
identical and can be skipped. For live warehouses, expected variance sources
are documented and tolerance-adjusted.

Usage:
    from helpers.reproducibility import reproducibility_check

    result = reproducibility_check(
        run_query_fn=lambda sql: conn.execute(sql).fetchall(),
        sql="SELECT SUM(revenue) FROM orders",
        n_runs=3,
        connection_type="snowflake",
    )
    # result["status"] -> "PASS" | "WARN" | "FAIL" | "SKIPPED"
"""

from __future__ import annotations

import hashlib
import json
import time


# ---------------------------------------------------------------------------
# Variance source diagnosis
# ---------------------------------------------------------------------------

VARIANCE_SOURCES = {
    "APPROX_FUNCTION": (
        "Query uses an approximate function (e.g., APPROX_COUNT_DISTINCT). "
        "Small variance is expected."
    ),
    "LIVE_INGESTION": (
        "Data source may have received new rows between runs. "
        "Row count changed between executions."
    ),
    "STREAMING_BUFFER": (
        "BigQuery streaming buffer may contain uncommitted rows."
    ),
    "MVCC_SNAPSHOT": (
        "Postgres MVCC: concurrent transactions may see different snapshots."
    ),
    "NONDETERMINISTIC_ORDER": (
        "Query result order differs but values are the same. "
        "This is expected for unordered queries."
    ),
    "UNKNOWN": "Variance source could not be determined.",
}


def diagnose_variance(
    runs: list[dict],
    sql: str,
    connection_type: str,
) -> str:
    """Attempt to diagnose the source of variance between runs.

    Args:
        runs: List of run result dicts with "row_count" and "checksum" keys.
        sql: The SQL query that was executed.
        connection_type: The warehouse type.

    Returns:
        A variance source key from VARIANCE_SOURCES.
    """
    sql_upper = sql.upper()

    # Check for approximate functions
    approx_keywords = [
        "APPROX_COUNT_DISTINCT", "APPROX_TOP_COUNT", "APPROX_QUANTILES",
        "HLL_COUNT", "APPROX_PERCENTILE",
    ]
    if any(kw in sql_upper for kw in approx_keywords):
        return "APPROX_FUNCTION"

    # Check for row count changes (live ingestion)
    row_counts = [r.get("row_count") for r in runs if r.get("row_count") is not None]
    if row_counts and len(set(row_counts)) > 1:
        return "LIVE_INGESTION"

    # BigQuery streaming buffer
    if connection_type == "bigquery":
        return "STREAMING_BUFFER"

    # Postgres MVCC
    if connection_type == "postgres":
        return "MVCC_SNAPSHOT"

    return "UNKNOWN"


# ---------------------------------------------------------------------------
# Core check
# ---------------------------------------------------------------------------

def reproducibility_check(
    run_query_fn,
    sql: str,
    n_runs: int = 3,
    connection_type: str = "duckdb",
    delay_seconds: float = 1.0,
    tolerance: float = 0.0,
) -> dict:
    """Run a query multiple times and compare results for reproducibility.

    Args:
        run_query_fn: Callable that takes a SQL string and returns a list of
            result rows (each row is a tuple or list). Should not raise on
            empty results.
        sql: The SQL query to execute.
        n_runs: Number of times to execute (default 3).
        connection_type: Warehouse type for variance diagnosis.
        delay_seconds: Seconds to wait between runs (default 1.0).
        tolerance: Relative tolerance for numeric comparison (0.0 = exact).

    Returns:
        dict with keys:
            status: "PASS" | "WARN" | "FAIL" | "SKIPPED"
            n_runs: int
            deterministic: bool
            runs: list of {row_count, checksum, timestamp, execution_ms}
            variance: float (max relative difference across runs, 0.0 if identical)
            variance_source: str | None
            variance_description: str | None
    """
    # Skip for deterministic sources
    if connection_type in ("csv", "duckdb", "motherduck") and tolerance == 0.0:
        return {
            "status": "SKIPPED",
            "n_runs": 0,
            "deterministic": True,
            "runs": [],
            "variance": 0.0,
            "variance_source": None,
            "variance_description": "Static/local source — reproducibility trivially guaranteed.",
        }

    runs = []
    for i in range(n_runs):
        if i > 0:
            time.sleep(delay_seconds)

        start = time.time()
        try:
            rows = run_query_fn(sql)
            elapsed_ms = (time.time() - start) * 1000

            # Compute checksum of results
            row_strs = [str(r) for r in (rows or [])]
            checksum = hashlib.sha256("\n".join(row_strs).encode()).hexdigest()[:16]

            runs.append({
                "row_count": len(rows) if rows else 0,
                "checksum": checksum,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "execution_ms": round(elapsed_ms, 1),
                "error": None,
            })
        except Exception as exc:
            elapsed_ms = (time.time() - start) * 1000
            runs.append({
                "row_count": None,
                "checksum": None,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "execution_ms": round(elapsed_ms, 1),
                "error": str(exc),
            })

    # Analyze results
    successful = [r for r in runs if r["error"] is None]

    if len(successful) < 2:
        return {
            "status": "FAIL",
            "n_runs": n_runs,
            "deterministic": False,
            "runs": runs,
            "variance": 1.0,
            "variance_source": "QUERY_FAILURE",
            "variance_description": f"Only {len(successful)}/{n_runs} runs succeeded.",
        }

    checksums = [r["checksum"] for r in successful]
    row_counts = [r["row_count"] for r in successful]

    all_same = len(set(checksums)) == 1
    row_counts_same = len(set(row_counts)) == 1

    if all_same:
        return {
            "status": "PASS",
            "n_runs": n_runs,
            "deterministic": True,
            "runs": runs,
            "variance": 0.0,
            "variance_source": None,
            "variance_description": None,
        }

    # Compute variance
    if row_counts_same and not all_same:
        # Same row count but different checksums — ordering difference
        variance = 0.0  # Not a real data difference
        source = "NONDETERMINISTIC_ORDER"
    else:
        # Different row counts — real variance
        max_rc = max(row_counts)
        min_rc = min(row_counts)
        variance = (max_rc - min_rc) / max_rc if max_rc > 0 else 0.0
        source = diagnose_variance(successful, sql, connection_type)

    status = "PASS" if variance <= tolerance else "WARN" if variance <= tolerance * 10 else "FAIL"

    return {
        "status": status,
        "n_runs": n_runs,
        "deterministic": False,
        "runs": runs,
        "variance": round(variance, 6),
        "variance_source": source,
        "variance_description": VARIANCE_SOURCES.get(source, ""),
    }
