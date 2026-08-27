"""
Unit tests for helpers/validation/business_rules.py -- Business Rules Validator.

Covers the 4-layer validation framework's business plausibility layer:
range checks, metric relationships, temporal consistency, segment coverage,
non-negativity, cardinality, and the orchestrator.
"""

import numpy as np
import pandas as pd
import pytest

from helpers.validation.business_rules import (
    validate_ranges,
    validate_metric_relationships,
    validate_temporal_consistency,
    validate_segment_coverage,
    validate_no_negative,
    validate_cardinality,
    validate_business_rules,
    get_default_rules,
)


# ============================================================
# validate_ranges
# ============================================================

class TestValidateRanges:

    def test_valid_ranges_pass(self):
        df = pd.DataFrame({"conversion_rate": [0.05, 0.12, 0.08, 0.20]})
        rules = [{"column": "conversion_rate", "min": 0, "max": 1,
                  "label": "Conversion Rate"}]
        result = validate_ranges(df, rules)
        assert result["ok"] is True
        assert len(result["violations"]) == 1
        assert result["violations"][0]["count"] == 0

    def test_out_of_range_fails(self):
        df = pd.DataFrame({"conversion_rate": [0.05, 1.5, 0.08, -0.1]})
        rules = [{"column": "conversion_rate", "min": 0, "max": 1,
                  "label": "Conversion Rate"}]
        result = validate_ranges(df, rules)
        assert result["ok"] is False
        violation = result["violations"][0]
        assert violation["count"] == 2
        assert violation["value"] is not None

    def test_multiple_rules(self):
        df = pd.DataFrame({
            "conversion_rate": [0.1, 0.2],
            "revenue": [100, 200],
        })
        rules = [
            {"column": "conversion_rate", "min": 0, "max": 1,
             "label": "Conversion Rate"},
            {"column": "revenue", "min": 0, "max": 10000,
             "label": "Revenue"},
        ]
        result = validate_ranges(df, rules)
        assert result["ok"] is True
        assert len(result["violations"]) == 2
        for v in result["violations"]:
            assert v["count"] == 0

    def test_nullable_values(self):
        df = pd.DataFrame({"rate": [0.1, np.nan, 0.3, None, 0.5]})
        rules = [{"column": "rate", "min": 0, "max": 1, "label": "Rate"}]
        result = validate_ranges(df, rules)
        assert result["ok"] is True
        # NaN values should be skipped, not counted as violations
        assert result["violations"][0]["count"] == 0


# ============================================================
# validate_metric_relationships
# ============================================================

class TestMetricRelationships:

    def test_consistent_metrics(self):
        metrics = {"aov": 50.0, "orders": 200, "revenue": 10000.0}
        rules = [{"left": "aov * orders", "right": "revenue",
                  "tolerance": 0.05}]
        result = validate_metric_relationships(metrics, rules)
        assert result["ok"] is True
        assert len(result["violations"]) == 0

    def test_inconsistent_metrics(self):
        metrics = {"aov": 50.0, "orders": 200, "revenue": 8000.0}
        rules = [{"left": "aov * orders", "right": "revenue",
                  "tolerance": 0.05}]
        result = validate_metric_relationships(metrics, rules)
        assert result["ok"] is False
        assert len(result["violations"]) == 1
        v = result["violations"][0]
        assert v["left_value"] == 10000.0
        assert v["right_value"] == 8000.0
        assert v["diff_pct"] > 0.05


# ============================================================
# validate_temporal_consistency
# ============================================================

class TestTemporalConsistency:

    def test_stable_growth(self):
        dates = pd.date_range("2024-01-01", periods=6, freq="MS")
        df = pd.DataFrame({
            "month": dates,
            "revenue": [100, 105, 110, 115, 120, 125],
        })
        result = validate_temporal_consistency(df, "month", "revenue",
                                               max_period_change_pct=200)
        assert result["ok"] is True
        assert len(result["large_changes"]) == 0

    def test_implausible_spike(self):
        dates = pd.date_range("2024-01-01", periods=5, freq="MS")
        df = pd.DataFrame({
            "month": dates,
            "revenue": [100, 110, 105, 1500, 120],
        })
        result = validate_temporal_consistency(df, "month", "revenue",
                                               max_period_change_pct=200)
        assert result["ok"] is False
        assert len(result["large_changes"]) >= 1
        # The spike from 105 -> 1500 is ~1328%, well over 200%
        spike = result["large_changes"][0]
        assert spike["change_pct"] > 200

    def test_handles_zeros(self):
        dates = pd.date_range("2024-01-01", periods=4, freq="MS")
        df = pd.DataFrame({
            "month": dates,
            "revenue": [0, 100, 110, 105],
        })
        result = validate_temporal_consistency(df, "month", "revenue",
                                               max_period_change_pct=200)
        # 0 -> 100 produces infinite change, should be flagged
        assert result["ok"] is False
        assert any(c["change_pct"] == float("inf")
                   for c in result["large_changes"])


# ============================================================
# validate_segment_coverage
# ============================================================

class TestSegmentCoverage:

    def test_all_segments_present(self):
        df = pd.DataFrame({
            "device": ["desktop", "mobile", "tablet", "desktop"],
            "sessions": [100, 200, 50, 150],
        })
        result = validate_segment_coverage(
            df, "device",
            expected_segments=["desktop", "mobile", "tablet"],
        )
        assert result["ok"] is True
        assert len(result["missing_segments"]) == 0

    def test_missing_segment(self):
        df = pd.DataFrame({
            "device": ["desktop", "mobile", "desktop"],
            "sessions": [100, 200, 150],
        })
        result = validate_segment_coverage(
            df, "device",
            expected_segments=["desktop", "mobile", "tablet"],
        )
        assert result["ok"] is False
        assert "tablet" in result["missing_segments"]

    def test_unexpected_segment_allowed(self):
        df = pd.DataFrame({
            "device": ["desktop", "mobile", "smart_tv"],
            "sessions": [100, 200, 10],
        })
        result = validate_segment_coverage(
            df, "device",
            expected_segments=["desktop", "mobile"],
            allow_other=True,
        )
        assert result["ok"] is True
        assert "smart_tv" in result["unexpected_segments"]


# ============================================================
# validate_no_negative
# ============================================================

class TestNoNegative:

    def test_all_positive(self):
        df = pd.DataFrame({
            "revenue": [100, 200, 300],
            "orders": [10, 20, 30],
        })
        result = validate_no_negative(df, ["revenue", "orders"])
        assert result["ok"] is True
        assert len(result["violations"]) == 0

    def test_negative_found(self):
        df = pd.DataFrame({
            "revenue": [100, -50, 300],
            "orders": [10, 20, 30],
        })
        result = validate_no_negative(df, ["revenue", "orders"])
        assert result["ok"] is False
        assert len(result["violations"]) == 1
        v = result["violations"][0]
        assert v["column"] == "revenue"
        assert v["negative_count"] == 1
        assert v["min_value"] == -50


# ============================================================
# validate_business_rules (orchestrator) & get_default_rules
# ============================================================

class TestBusinessRules:

    def test_orchestrator(self):
        df = pd.DataFrame({
            "conversion_rate": [0.05, 0.12, 0.08],
            "revenue": [100, 200, 300],
            "device": ["desktop", "mobile", "tablet"],
        })
        config = {
            "ranges": [
                {"column": "conversion_rate", "min": 0, "max": 1,
                 "label": "Conversion Rate"},
            ],
            "no_negative": ["revenue"],
            "segment_coverage": {
                "segment_column": "device",
                "expected_segments": ["desktop", "mobile", "tablet"],
            },
        }
        result = validate_business_rules(df, config)
        assert result["ok"] is True
        assert "ranges" in result["results"]
        assert "no_negative" in result["results"]
        assert "segment_coverage" in result["results"]
        assert "passed" in result["summary"]

    def test_default_rules_exist(self):
        defaults = get_default_rules()
        assert "ranges" in defaults
        assert "no_negative" in defaults
        assert isinstance(defaults["ranges"], list)
        assert len(defaults["ranges"]) > 0
        # Each range rule should have required keys
        for rule in defaults["ranges"]:
            assert "column" in rule
            assert "min" in rule
            assert "max" in rule
            assert "label" in rule
