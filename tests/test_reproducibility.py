"""Tests for helpers.reproducibility — same-query-N-times checks."""

import pytest

from helpers.reproducibility import (
    reproducibility_check,
    diagnose_variance,
    VARIANCE_SOURCES,
)


# =====================================================================
# Deterministic sources skip
# =====================================================================

class TestDeterministicSkip:
    def test_csv_skipped(self):
        result = reproducibility_check(
            run_query_fn=lambda sql: [(1,)],
            sql="SELECT 1",
            connection_type="csv",
        )
        assert result["status"] == "SKIPPED"
        assert result["deterministic"] is True
        assert result["n_runs"] == 0

    def test_duckdb_skipped(self):
        result = reproducibility_check(
            run_query_fn=lambda sql: [(1,)],
            sql="SELECT 1",
            connection_type="duckdb",
        )
        assert result["status"] == "SKIPPED"

    def test_motherduck_skipped(self):
        result = reproducibility_check(
            run_query_fn=lambda sql: [(1,)],
            sql="SELECT 1",
            connection_type="motherduck",
        )
        assert result["status"] == "SKIPPED"


# =====================================================================
# Non-deterministic sources run
# =====================================================================

class TestNonDeterministicRun:
    def test_consistent_results_pass(self):
        result = reproducibility_check(
            run_query_fn=lambda sql: [(42,)],
            sql="SELECT 42",
            n_runs=3,
            connection_type="snowflake",
            delay_seconds=0,  # No delay for tests
        )
        assert result["status"] == "PASS"
        assert result["deterministic"] is True
        assert result["variance"] == 0.0
        assert len(result["runs"]) == 3

    def test_varying_results_detected(self):
        counter = {"n": 0}
        def varying_query(sql):
            counter["n"] += 1
            return [(i,) for i in range(counter["n"])]

        result = reproducibility_check(
            run_query_fn=varying_query,
            sql="SELECT *",
            n_runs=3,
            connection_type="postgres",
            delay_seconds=0,
        )
        assert result["deterministic"] is False
        assert result["variance"] > 0

    def test_query_failures_tracked(self):
        call_count = {"n": 0}
        def failing_query(sql):
            call_count["n"] += 1
            if call_count["n"] == 2:
                raise RuntimeError("Connection lost")
            return [(1,)]

        result = reproducibility_check(
            run_query_fn=failing_query,
            sql="SELECT 1",
            n_runs=3,
            connection_type="snowflake",
            delay_seconds=0,
        )
        # 2 successful runs, should still have enough for comparison
        assert len(result["runs"]) == 3
        assert any(r["error"] is not None for r in result["runs"])

    def test_all_failures_returns_fail(self):
        def always_fail(sql):
            raise RuntimeError("broken")

        result = reproducibility_check(
            run_query_fn=always_fail,
            sql="SELECT 1",
            n_runs=3,
            connection_type="snowflake",
            delay_seconds=0,
        )
        assert result["status"] == "FAIL"
        assert result["deterministic"] is False


# =====================================================================
# Variance diagnosis
# =====================================================================

class TestDiagnoseVariance:
    def test_approx_function_detected(self):
        runs = [{"row_count": 100, "checksum": "abc"}]
        source = diagnose_variance(
            runs, "SELECT APPROX_COUNT_DISTINCT(user_id) FROM events", "snowflake"
        )
        assert source == "APPROX_FUNCTION"

    def test_live_ingestion_detected(self):
        runs = [
            {"row_count": 100, "checksum": "abc"},
            {"row_count": 105, "checksum": "def"},
        ]
        source = diagnose_variance(runs, "SELECT COUNT(*) FROM events", "snowflake")
        assert source == "LIVE_INGESTION"

    def test_bigquery_streaming_buffer(self):
        runs = [
            {"row_count": 100, "checksum": "abc"},
            {"row_count": 100, "checksum": "def"},
        ]
        source = diagnose_variance(runs, "SELECT * FROM events", "bigquery")
        assert source == "STREAMING_BUFFER"

    def test_postgres_mvcc(self):
        runs = [
            {"row_count": 100, "checksum": "abc"},
            {"row_count": 100, "checksum": "def"},
        ]
        source = diagnose_variance(runs, "SELECT * FROM events", "postgres")
        assert source == "MVCC_SNAPSHOT"

    def test_unknown_source(self):
        runs = [
            {"row_count": 100, "checksum": "abc"},
            {"row_count": 100, "checksum": "def"},
        ]
        source = diagnose_variance(runs, "SELECT * FROM events", "snowflake")
        assert source == "UNKNOWN"
