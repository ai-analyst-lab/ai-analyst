"""Tests for helpers/data/freshness.py.

Deterministic: every test passes a fixed `today` in, so no test ever reads the real clock.
"""
from __future__ import annotations

from datetime import date

import yaml

from helpers.data.freshness import (
    COLOR_GREEN,
    COLOR_MISSING,
    COLOR_RED,
    COLOR_YELLOW,
    GREEN_MAX_DAYS,
    YELLOW_MAX_DAYS,
    freshness,
    freshness_report,
)


# ── freshness: the three thresholds ──────────────────────────────────────

class TestFreshnessThresholds:
    def test_fresh_is_green(self):
        age, color = freshness("2026-06-25", "2026-06-26")
        assert age == 1
        assert color == COLOR_GREEN

    def test_just_under_green_boundary(self):
        # 29 days is still green (boundary is < 30).
        age, color = freshness("2026-01-02", "2026-01-31")
        assert age == 29
        assert color == COLOR_GREEN

    def test_green_boundary_is_yellow(self):
        # Exactly GREEN_MAX_DAYS (30) tips into yellow.
        age, color = freshness("2026-01-01", "2026-01-31")
        assert age == GREEN_MAX_DAYS
        assert color == COLOR_YELLOW

    def test_mid_yellow(self):
        age, color = freshness("2026-04-01", "2026-06-01")
        assert age == 61
        assert color == COLOR_YELLOW

    def test_yellow_boundary_is_still_yellow(self):
        # Exactly YELLOW_MAX_DAYS (90) is the last yellow day.
        age, color = freshness("2026-01-01", "2026-04-01")
        assert age == YELLOW_MAX_DAYS
        assert color == COLOR_YELLOW

    def test_just_over_yellow_is_red(self):
        age, color = freshness("2026-01-01", "2026-04-02")
        assert age == 91
        assert color == COLOR_RED

    def test_old_is_red(self):
        age, color = freshness("2025-06-01", "2026-06-26")
        assert age == 390
        assert color == COLOR_RED


# ── freshness: missing ───────────────────────────────────────────────────

class TestFreshnessMissing:
    def test_none_is_missing(self):
        age, color = freshness(None, "2026-06-26")
        assert age is None
        assert color == COLOR_MISSING

    def test_empty_string_is_missing(self):
        age, color = freshness("", "2026-06-26")
        assert age is None
        assert color == COLOR_MISSING

    def test_accepts_date_objects(self):
        age, color = freshness(date(2026, 6, 25), date(2026, 6, 26))
        assert age == 1
        assert color == COLOR_GREEN


# ── freshness_report: reddest-first sorting ──────────────────────────────

class TestFreshnessReport:
    def _write_context(self, tmp_path, metrics, verified_queries=None):
        (tmp_path / "metrics").mkdir(parents=True, exist_ok=True)
        (tmp_path / "semantic").mkdir(parents=True, exist_ok=True)
        (tmp_path / "metrics" / "index.yaml").write_text(
            yaml.safe_dump({"metrics": metrics})
        )
        if verified_queries is not None:
            (tmp_path / "semantic" / "verified_queries.yaml").write_text(
                yaml.safe_dump({"verified_queries": verified_queries})
            )
        return tmp_path

    def test_sorts_reddest_first(self, tmp_path):
        ctx = self._write_context(
            tmp_path,
            metrics=[
                {"metric": "fresh_one", "last_verified": "2026-06-20"},   # green
                {"metric": "old_one", "last_verified": "2026-01-01"},     # red
                {"metric": "aging_one", "last_verified": "2026-05-01"},   # yellow
                {"metric": "no_date"},                                    # missing
            ],
        )
        report = freshness_report(ctx, "2026-06-26")
        colors = [row[3] for row in report]
        assert colors == [COLOR_MISSING, COLOR_RED, COLOR_YELLOW, COLOR_GREEN]
        # First column is the name; reddest definition (after missing) is the old one.
        assert report[0][0] == "no_date"
        assert report[1][0] == "old_one"

    def test_oldest_first_within_red(self, tmp_path):
        ctx = self._write_context(
            tmp_path,
            metrics=[
                {"metric": "red_newer", "last_verified": "2026-02-01"},
                {"metric": "red_older", "last_verified": "2025-06-01"},
            ],
        )
        report = freshness_report(ctx, "2026-06-26")
        names = [row[0] for row in report]
        assert names == ["red_older", "red_newer"]

    def test_includes_verified_queries(self, tmp_path):
        ctx = self._write_context(
            tmp_path,
            metrics=[{"metric": "m1", "last_verified": "2026-06-25"}],
            verified_queries=[{"name": "q1", "last_verified": "2026-01-01"}],
        )
        report = freshness_report(ctx, "2026-06-26")
        names = {row[0] for row in report}
        assert names == {"m1", "q1"}
        # The stale query sorts above the fresh metric.
        assert report[0][0] == "q1"

    def test_report_rows_carry_age_and_date(self, tmp_path):
        ctx = self._write_context(
            tmp_path,
            metrics=[{"metric": "m1", "last_verified": "2026-06-25"}],
        )
        report = freshness_report(ctx, "2026-06-26")
        name, last_verified, age_days, color = report[0]
        assert name == "m1"
        assert str(last_verified) == "2026-06-25"
        assert age_days == 1
        assert color == COLOR_GREEN

    def test_empty_context_is_empty_report(self, tmp_path):
        (tmp_path / "metrics").mkdir(parents=True, exist_ok=True)
        report = freshness_report(tmp_path, "2026-06-26")
        assert report == []
