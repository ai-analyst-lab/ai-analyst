"""
Unit tests for helpers/validation/logical_validator.py — new ok-based API.

Tests cover all 8 public functions:
    validate_aggregation_consistency (new API path)
    validate_percentages_sum
    validate_monotonic
    validate_trend_consistency
    validate_ratio_bounds
    validate_group_balance
    validate_no_future_dates
    run_logical_checks

18 test cases across 7 test classes.
"""

import numpy as np
import pandas as pd
import pytest

from helpers.validation.logical_validator import (
    validate_aggregation_consistency,
    validate_percentages_sum,
    validate_monotonic,
    validate_trend_consistency,
    validate_ratio_bounds,
    validate_group_balance,
    validate_no_future_dates,
    run_logical_checks,
)


# ============================================================
# Aggregation Consistency (new API)
# ============================================================

class TestAggregationConsistency:
    """Validate that detail rows aggregate to match summary totals."""

    def test_matching_totals_pass(self):
        detail = pd.DataFrame({"amount": [10, 20, 30]})
        summary = pd.DataFrame({"amount": [60]})
        result = validate_aggregation_consistency(
            detail, summary, metric_column="amount",
        )
        assert result["ok"] is True
        assert result["expected_total"] == 60.0
        assert result["actual_total"] == 60.0
        assert result["difference"] == 0.0

    def test_mismatched_totals_fail(self):
        detail = pd.DataFrame({"amount": [10, 20, 30]})
        summary = pd.DataFrame({"amount": [100]})
        result = validate_aggregation_consistency(
            detail, summary, metric_column="amount",
        )
        assert result["ok"] is False
        assert result["expected_total"] == 60.0
        assert result["actual_total"] == 100.0
        assert result["difference"] == 40.0

    def test_grouped_aggregation(self):
        detail = pd.DataFrame({
            "region": ["A", "A", "B", "B"],
            "amount": [10, 20, 30, 40],
        })
        summary = pd.DataFrame({
            "region": ["A", "B"],
            "amount": [30, 70],
        })
        result = validate_aggregation_consistency(
            detail, summary,
            metric_column="amount", group_column="region",
        )
        assert result["ok"] is True
        assert result["expected_total"] == 100.0
        assert result["actual_total"] == 100.0

    def test_within_tolerance(self):
        detail = pd.DataFrame({"amount": [100.0]})
        # 0.5% off — within default 1% tolerance
        summary = pd.DataFrame({"amount": [100.5]})
        result = validate_aggregation_consistency(
            detail, summary, metric_column="amount", tolerance=0.01,
        )
        assert result["ok"] is True
        assert result["difference"] == pytest.approx(0.5, abs=0.01)


# ============================================================
# Percentages Sum
# ============================================================

class TestPercentagesSum:
    """Validate that percentage columns sum to ~100."""

    def test_valid_percentages(self):
        df = pd.DataFrame({"pct": [25.0, 25.0, 25.0, 25.0]})
        result = validate_percentages_sum(df, pct_column="pct")
        assert result["ok"] is True
        assert result["actual_sum"] == 100.0
        assert result["difference"] == 0.0

    def test_invalid_percentages(self):
        df = pd.DataFrame({"pct": [25.0, 25.0, 25.0]})
        result = validate_percentages_sum(df, pct_column="pct")
        assert result["ok"] is False
        assert result["actual_sum"] == 75.0
        assert result["difference"] == 25.0

    def test_grouped_percentages(self):
        df = pd.DataFrame({
            "group": ["A", "A", "B", "B"],
            "pct": [60.0, 40.0, 50.0, 50.0],
        })
        result = validate_percentages_sum(
            df, pct_column="pct", group_column="group",
        )
        assert result["ok"] is True
        assert result["difference"] == 0.0


# ============================================================
# Monotonic
# ============================================================

class TestMonotonic:
    """Validate monotonicity of a column."""

    def test_increasing_passes(self):
        df = pd.DataFrame({"val": [1, 2, 3, 4, 5]})
        result = validate_monotonic(df, column="val", direction="increasing")
        assert result["ok"] is True
        assert result["violations_count"] == 0
        assert result["first_violation_index"] is None

    def test_decreasing_passes(self):
        df = pd.DataFrame({"val": [5, 4, 3, 2, 1]})
        result = validate_monotonic(df, column="val", direction="decreasing")
        assert result["ok"] is True
        assert result["violations_count"] == 0

    def test_non_monotonic_fails(self):
        df = pd.DataFrame({"val": [1, 3, 2, 4, 5]})
        result = validate_monotonic(df, column="val", direction="increasing")
        assert result["ok"] is False
        assert result["violations_count"] >= 1
        assert result["first_violation_index"] == 2  # index where 2 < 3


# ============================================================
# Trend Consistency
# ============================================================

class TestTrendConsistency:
    """Validate trend plausibility via rolling z-scores."""

    def test_stable_trend_passes(self):
        # Smooth series — no anomalies
        values = [100, 102, 101, 103, 104, 102, 105, 103, 106, 104]
        result = validate_trend_consistency(values, window=3, max_zscore=3.0)
        assert result["ok"] is True
        assert len(result["anomalies"]) == 0

    def test_spike_detected(self):
        # Inject a massive spike
        values = [100, 101, 102, 103, 104, 105, 1000, 107, 108]
        result = validate_trend_consistency(values, window=3, max_zscore=3.0)
        assert result["ok"] is False
        assert len(result["anomalies"]) >= 1
        # The spike at index 6 should be flagged
        spike_indices = [a["index"] for a in result["anomalies"]]
        assert 6 in spike_indices

    def test_short_series(self):
        # Series shorter than window — should pass trivially
        values = [100, 101]
        result = validate_trend_consistency(values, window=3)
        assert result["ok"] is True
        assert len(result["anomalies"]) == 0


# ============================================================
# Ratio Bounds
# ============================================================

class TestRatioBounds:
    """Validate computed ratios are within bounds."""

    def test_valid_ratios(self):
        df = pd.DataFrame({
            "conversions": [5, 10, 15],
            "sessions": [100, 200, 300],
        })
        result = validate_ratio_bounds(
            df, numerator_col="conversions", denominator_col="sessions",
            min_ratio=0.0, max_ratio=1.0,
        )
        assert result["ok"] is True
        assert result["out_of_bounds_count"] == 0

    def test_out_of_bounds(self):
        df = pd.DataFrame({
            "numerator": [150, 5, 10],
            "denominator": [100, 200, 300],
        })
        result = validate_ratio_bounds(
            df, numerator_col="numerator", denominator_col="denominator",
            min_ratio=0.0, max_ratio=1.0,
        )
        assert result["ok"] is False
        assert result["out_of_bounds_count"] == 1
        assert len(result["out_of_bounds_sample"]) == 1
        assert result["out_of_bounds_sample"][0]["ratio"] == pytest.approx(1.5, abs=0.01)


# ============================================================
# Group Balance
# ============================================================

class TestGroupBalance:
    """Validate group sizes are not extremely imbalanced."""

    def test_balanced_groups(self):
        df = pd.DataFrame({
            "group": ["A"] * 50 + ["B"] * 50,
            "value": range(100),
        })
        result = validate_group_balance(
            df, group_column="group",
            min_group_size=10, max_imbalance_ratio=100.0,
        )
        assert result["ok"] is True
        assert result["imbalance_ratio"] == pytest.approx(1.0, abs=0.01)
        assert result["group_sizes"]["A"] == 50
        assert result["group_sizes"]["B"] == 50

    def test_imbalanced_groups(self):
        df = pd.DataFrame({
            "group": ["A"] * 5 + ["B"] * 500,
            "value": range(505),
        })
        result = validate_group_balance(
            df, group_column="group",
            min_group_size=10, max_imbalance_ratio=100.0,
        )
        assert result["ok"] is False
        # Group A has only 5 rows (< min_group_size=10)
        assert result["group_sizes"]["A"] == 5
        assert result["imbalance_ratio"] == 100.0


# ============================================================
# Run Logical Checks (orchestrator)
# ============================================================

class TestRunLogicalChecks:
    """Validate the orchestrator combines checks correctly."""

    def test_orchestrator(self):
        detail = pd.DataFrame({
            "amount": [10, 20, 30],
            "pct": [33.33, 33.33, 33.34],
            "date": pd.date_range("2024-01-01", periods=3, freq="D"),
            "group": ["A", "A", "B"],
        })
        summary = pd.DataFrame({"amount": [60]})

        config = {
            "metric_column": "amount",
            "pct_column": "pct",
            "date_column": "date",
            "balance_column": "group",
            "trend_values": [10, 20, 30, 25, 35, 28, 32],
            "min_group_size": 1,
        }

        result = run_logical_checks(
            detail_df=detail, summary_df=summary, config=config,
        )

        assert isinstance(result["ok"], bool)
        assert result["checks_run"] >= 3  # aggregation, pct, dates, balance, trend
        assert result["checks_passed"] >= 1
        assert "aggregation_consistency" in result["results"]
        assert "percentages_sum" in result["results"]
        assert "no_future_dates" in result["results"]
        assert "group_balance" in result["results"]
        assert "trend_consistency" in result["results"]

        # Each sub-result has an "ok" key
        for name, sub_result in result["results"].items():
            assert "ok" in sub_result, f"Missing 'ok' in {name}"
