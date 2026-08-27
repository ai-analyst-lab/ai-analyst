"""
Unit tests for helpers/knowledge/miss_rate_logger.py -- Miss Rate Logger.

Covers miss logging, summary aggregation, rolling-window rate
calculation, and log clearing.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta

import pytest

from helpers.knowledge.miss_rate_logger import (
    log_miss,
    get_miss_summary,
    get_miss_rate,
    clear_miss_log,
    _log_path,
)


# ============================================================
# TestLogMiss
# ============================================================

class TestLogMiss:

    def test_creates_file_with_entry(self, tmp_path):
        log_dir = str(tmp_path / "logs")
        log_miss("data_gap", "missing column revenue", log_dir=log_dir)
        path = _log_path(log_dir)
        assert path.exists()
        entry = json.loads(path.read_text().strip())
        assert entry["type"] == "data_gap"
        assert entry["description"] == "missing column revenue"
        assert "timestamp" in entry

    def test_invalid_type_coerced_to_other(self, tmp_path):
        log_dir = str(tmp_path / "logs")
        log_miss("totally_bogus", "bad type test", log_dir=log_dir)
        entry = json.loads(_log_path(log_dir).read_text().strip())
        assert entry["type"] == "other"

    def test_context_preserved(self, tmp_path):
        log_dir = str(tmp_path / "logs")
        ctx = {"table": "orders", "column": "total"}
        log_miss("column_not_found", "col missing", context=ctx, log_dir=log_dir)
        entry = json.loads(_log_path(log_dir).read_text().strip())
        assert entry["context"] == ctx

    def test_never_raises_on_unwritable_path(self, tmp_path):
        # A path nested under a file (not a directory) cannot be created
        blocker = tmp_path / "blocker"
        blocker.write_text("I am a file")
        bad_dir = str(blocker / "sub" / "logs")
        # Should silently swallow the error
        log_miss("data_gap", "should not raise", log_dir=bad_dir)


# ============================================================
# TestGetMissSummary
# ============================================================

class TestGetMissSummary:

    def test_empty_log_returns_zeros(self, tmp_path):
        summary = get_miss_summary(log_dir=str(tmp_path / "empty"))
        assert summary == {
            "total": 0, "by_type": {}, "recent": [], "top_descriptions": [],
        }

    def test_multiple_entries(self, tmp_path):
        log_dir = str(tmp_path / "logs")
        log_miss("data_gap", "gap A", log_dir=log_dir)
        log_miss("data_gap", "gap A", log_dir=log_dir)
        log_miss("query_failed", "timeout", log_dir=log_dir)
        log_miss("column_not_found", "col X", log_dir=log_dir)
        log_miss("data_gap", "gap A", log_dir=log_dir)
        log_miss("query_failed", "syntax", log_dir=log_dir)

        summary = get_miss_summary(log_dir=log_dir)
        assert summary["total"] == 6
        assert summary["by_type"]["data_gap"] == 3
        assert summary["by_type"]["query_failed"] == 2
        assert summary["by_type"]["column_not_found"] == 1
        assert len(summary["recent"]) == 5  # last 5 entries
        assert summary["top_descriptions"][0] == "gap A"  # most common

    def test_single_entry(self, tmp_path):
        log_dir = str(tmp_path / "logs")
        log_miss("metric_undefined", "undefined CR", log_dir=log_dir)

        summary = get_miss_summary(log_dir=log_dir)
        assert summary["total"] == 1
        assert summary["by_type"] == {"metric_undefined": 1}
        assert len(summary["recent"]) == 1
        assert summary["top_descriptions"] == ["undefined CR"]


# ============================================================
# TestGetMissRate
# ============================================================

class TestGetMissRate:

    def test_empty_log_returns_zeros(self, tmp_path):
        rate = get_miss_rate(window_days=7, log_dir=str(tmp_path / "empty"))
        assert rate["total_misses"] == 0
        assert rate["misses_per_day"] == 0.0
        assert rate["most_common_type"] is None

    def test_rate_calculation(self, tmp_path):
        log_dir = str(tmp_path / "logs")
        log_miss("data_gap", "g1", log_dir=log_dir)
        log_miss("data_gap", "g2", log_dir=log_dir)
        log_miss("query_failed", "q1", log_dir=log_dir)

        rate = get_miss_rate(window_days=7, log_dir=log_dir)
        assert rate["total_misses"] == 3
        assert rate["misses_per_day"] == round(3 / 7, 2)
        assert rate["most_common_type"] == "data_gap"

    def test_window_excludes_old_entries(self, tmp_path):
        log_dir = str(tmp_path / "logs")
        # Write an old entry directly (15 days ago)
        old_ts = (datetime.now(timezone.utc) - timedelta(days=15)).isoformat()
        old_entry = json.dumps({
            "timestamp": old_ts,
            "type": "data_gap",
            "description": "old",
            "context": None,
        })
        path = _log_path(log_dir)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(old_entry + "\n")

        # Add a recent entry via the public API
        log_miss("query_failed", "recent", log_dir=log_dir)

        rate = get_miss_rate(window_days=7, log_dir=log_dir)
        assert rate["total_misses"] == 1
        assert rate["most_common_type"] == "query_failed"


# ============================================================
# TestClearMissLog
# ============================================================

class TestClearMissLog:

    def test_clear_returns_count(self, tmp_path):
        log_dir = str(tmp_path / "logs")
        log_miss("data_gap", "a", log_dir=log_dir)
        log_miss("data_gap", "b", log_dir=log_dir)
        log_miss("query_failed", "c", log_dir=log_dir)

        count = clear_miss_log(log_dir=log_dir)
        assert count == 3
        assert not _log_path(log_dir).exists()

    def test_clear_missing_file_returns_zero(self, tmp_path):
        count = clear_miss_log(log_dir=str(tmp_path / "nonexistent"))
        assert count == 0
