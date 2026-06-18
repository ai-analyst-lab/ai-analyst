"""Tests for helpers.query_log — JSONL query logging, matching, coverage."""

import json
import pytest
from pathlib import Path
from unittest.mock import patch

from helpers.query_log import (
    _log_path,
    append_entry,
    read_log,
    match_claims,
    backfill_entry,
    to_markdown,
    coverage_report,
)


# =====================================================================
# Fixtures
# =====================================================================

@pytest.fixture
def tmp_working(tmp_path, monkeypatch):
    """Redirect the query log working directory to a temp path."""
    import helpers.query_log as ql_mod
    monkeypatch.setattr(ql_mod, "_WORKING_DIR", tmp_path / "working")
    return tmp_path / "working"


@pytest.fixture
def sample_entries(tmp_working):
    """Write 3 sample entries and return them."""
    entries = []
    for i in range(3):
        e = append_entry(
            dataset_name="test-ds",
            date="2026-04-04",
            agent="descriptive-analytics",
            pipeline_step=5,
            purpose=f"Query {i+1}",
            sql=f"SELECT col{i+1} FROM orders",
            tables_accessed=["orders"],
            result_summary=f"{i+1} rows",
            result_value=float((i + 1) * 100),
            row_count=i + 1,
            execution_ms=50.0 + i * 10,
        )
        entries.append(e)
    return entries


# =====================================================================
# Log path
# =====================================================================

class TestLogPath:
    def test_path_format(self, tmp_working):
        path = _log_path("my-dataset", "2026-04-04")
        assert path.name == "query_log_my-dataset_2026-04-04.jsonl"


# =====================================================================
# Append and read
# =====================================================================

class TestAppendAndRead:
    def test_append_creates_file(self, tmp_working):
        append_entry(
            dataset_name="ds1", date="2026-04-04",
            agent="test", pipeline_step=1,
            purpose="test query", sql="SELECT 1",
        )
        path = _log_path("ds1", "2026-04-04")
        assert path.exists()

    def test_append_returns_entry_with_query_id(self, tmp_working):
        entry = append_entry(
            dataset_name="ds1", date="2026-04-04",
            agent="test", pipeline_step=1,
            purpose="test", sql="SELECT 1",
        )
        assert "query_id" in entry
        assert entry["agent"] == "test"

    def test_explicit_query_id(self, tmp_working):
        entry = append_entry(
            dataset_name="ds1", date="2026-04-04",
            agent="test", pipeline_step=1,
            purpose="test", sql="SELECT 1",
            query_id="custom_id",
        )
        assert entry["query_id"] == "custom_id"

    def test_read_returns_all_entries(self, sample_entries):
        entries = read_log("test-ds", "2026-04-04")
        assert len(entries) == 3
        assert entries[0]["purpose"] == "Query 1"

    def test_read_nonexistent_returns_empty(self, tmp_working):
        entries = read_log("nonexistent", "2026-01-01")
        assert entries == []

    def test_entries_are_valid_json(self, tmp_working):
        append_entry(
            dataset_name="ds1", date="2026-04-04",
            agent="test", pipeline_step=1,
            purpose="test", sql="SELECT 'hello world'",
        )
        path = _log_path("ds1", "2026-04-04")
        with path.open() as f:
            for line in f:
                json.loads(line)  # Should not raise


# =====================================================================
# Match claims
# =====================================================================

class TestMatchClaims:
    def test_explicit_claim_ids(self, tmp_working):
        append_entry(
            dataset_name="ds1", date="2026-04-04",
            agent="test", pipeline_step=1,
            purpose="revenue", sql="SELECT SUM(rev) FROM orders",
            claim_ids=["claim-1"],
            query_id="q1",
        )
        entries = read_log("ds1", "2026-04-04")
        claims = [{"claim_id": "claim-1", "value": 1000}]
        matches = match_claims(entries, claims)
        assert "q1" in matches["claim-1"]

    def test_fuzzy_value_match(self, sample_entries):
        entries = read_log("test-ds", "2026-04-04")
        # sample_entries[0] has result_value=100.0
        claims = [{"claim_id": "c1", "value": 100.0}]
        matches = match_claims(entries, claims)
        assert len(matches["c1"]) >= 1

    def test_unmatched_claim(self, sample_entries):
        entries = read_log("test-ds", "2026-04-04")
        claims = [{"claim_id": "c99", "value": 999999}]
        matches = match_claims(entries, claims)
        assert matches["c99"] == []


# =====================================================================
# Backfill
# =====================================================================

class TestBackfill:
    def test_backfill_marks_purpose(self, tmp_working):
        entry = backfill_entry(
            dataset_name="ds1", date="2026-04-04",
            agent="validation", pipeline_step=6.5,
            purpose="Revenue total", sql="SELECT SUM(revenue) FROM orders",
            claim_ids=["c1"],
        )
        assert "[BACKFILLED]" in entry["purpose"]
        assert entry["query_id"].startswith("backfill_")


# =====================================================================
# Rendering
# =====================================================================

class TestToMarkdown:
    def test_empty_entries(self):
        assert "No queries" in to_markdown([])

    def test_renders_table(self, sample_entries):
        entries = read_log("test-ds", "2026-04-04")
        md = to_markdown(entries)
        assert "| Agent |" in md
        assert "descriptive-analytics" in md
        assert "orders" in md


# =====================================================================
# Coverage report
# =====================================================================

class TestCoverageReport:
    def test_full_coverage(self, sample_entries):
        entries = read_log("test-ds", "2026-04-04")
        claims = [{"claim_id": "c1", "value": 100.0}]
        report = coverage_report(entries, claims)
        assert report["total_claims"] == 1
        assert report["matched_claims"] == 1
        assert report["coverage_pct"] == 1.0
        assert report["status"] == "PASS"

    def test_zero_coverage(self, sample_entries):
        entries = read_log("test-ds", "2026-04-04")
        claims = [{"claim_id": "c99", "value": 999999}]
        report = coverage_report(entries, claims)
        assert report["matched_claims"] == 0
        assert report["coverage_pct"] == 0.0
        assert report["status"] == "WARN"

    def test_empty_claims(self, tmp_working):
        report = coverage_report([], [])
        assert report["total_claims"] == 0
        assert report["coverage_pct"] == 1.0
        assert report["status"] == "PASS"
