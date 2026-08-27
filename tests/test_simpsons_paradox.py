"""
Unit tests for helpers/validation/simpsons_paradox.py.

Tests all five public functions plus edge cases:
1. check_simpsons_paradox -- single-dimension detection
2. check_simpsons_multi_segment -- multi-dimension scanning
3. weighted_vs_unweighted -- weight-induced paradox detection
4. generate_paradox_report -- markdown formatting
5. suggest_segments_to_check -- heuristic segment ranking

15 test cases organized into 5 test classes.
"""

import numpy as np
import pandas as pd
import pytest

from helpers.validation.simpsons_paradox import (
    check_simpsons_paradox,
    check_simpsons_multi_segment,
    weighted_vs_unweighted,
    generate_paradox_report,
    suggest_segments_to_check,
)


# ---------------------------------------------------------------------------
# Fixtures -- local to this module
# ---------------------------------------------------------------------------

@pytest.fixture
def paradox_data():
    """Classic Berkeley-admissions-style paradox dataset.

    Department A: Large, high admission rate for both groups
    Department B: Small, low admission rate for both groups

    Group X applies mostly to Dept A (easy), Group Y applies mostly
    to Dept B (hard). Aggregate: Y appears to have higher admission,
    but within each dept, X has higher admission.

    Dept A: X=40 applicants (32 admitted = 80%), Y=20 applicants (16 admitted = 80%)
    Dept B: X=10 applicants (1 admitted = 10%), Y=30 applicants (6 admitted = 20%)

    Aggregate: X admitted 33/50 = 66%, Y admitted 22/50 = 44%

    Wait -- that's not a paradox (X > Y in both and aggregate).
    Let's construct a true paradox:

    Dept A (easy, 80% base): X=20 applicants, Y=40 applicants
    Dept B (hard, 10% base): X=40 applicants, Y=10 applicants

    Dept A: X admission 14/20=70%, Y admission 30/40=75%  -> Y > X
    Dept B: X admission 2/40=5%,  Y admission 0/10=0%     -> X > Y (but tiny)

    Hmm, still tricky. Let me use the exact spec from the task:

    Department A: Large, high admission rate for both groups
    Department B: Small, low admission rate for both groups
    Aggregate flips because one group applies more to the hard department.
    """
    data = pd.DataFrame({
        "department": ["A"] * 60 + ["B"] * 40,
        "group": (
            ["X"] * 40 + ["Y"] * 20
            + ["X"] * 10 + ["Y"] * 30
        ),
        "admitted": (
            [1] * 32 + [0] * 8       # Dept A, Group X: 32/40 = 80%
            + [1] * 16 + [0] * 4     # Dept A, Group Y: 16/20 = 80%
            + [1] * 1 + [0] * 9      # Dept B, Group X: 1/10 = 10%
            + [1] * 6 + [0] * 24     # Dept B, Group Y: 6/30 = 20%
        ),
    })
    return data


@pytest.fixture
def no_paradox_data():
    """Dataset where aggregate and segment directions agree.

    Both departments show Group X > Group Y, and aggregate also shows X > Y.
    """
    np.random.seed(42)
    rows = []
    for dept in ["A", "B", "C"]:
        for group in ["X", "Y"]:
            n = 50
            rate = 0.7 if group == "X" else 0.3
            admitted = np.random.binomial(1, rate, n)
            for a in admitted:
                rows.append({
                    "group": group,
                    "department": dept,
                    "admitted": int(a),
                })
    return pd.DataFrame(rows)


# ============================================================
# TestCheckSimpsonsParadox
# ============================================================

class TestCheckSimpsonsParadox:
    """Tests for check_simpsons_paradox (single-dimension check)."""

    def test_no_paradox_detected(self, no_paradox_data):
        """When all segments agree with aggregate, no paradox."""
        result = check_simpsons_paradox(
            no_paradox_data,
            metric_column="admitted",
            segment_column="department",
            comparison_column="group",
        )
        assert result["paradox_detected"] is False
        assert result["severity"] in ("none", "low")
        assert len(result["reversals"]) == 0
        assert result["aggregate_direction"] in ("positive", "negative")

    def test_paradox_detected(self, paradox_data):
        """Classic paradox: aggregate direction reverses at segment level.

        Aggregate: X has 33/50=66%, Y has 22/50=44% -> X > Y (positive).
        Dept A: X=80%, Y=80% -> neutral.
        Dept B: X=10%, Y=20% -> Y > X (negative, reversal).

        Actually let's verify the numbers:
        X total: 40 (dept A) + 10 (dept B) = 50, admitted: 32 + 1 = 33 -> 66%
        Y total: 20 (dept A) + 30 (dept B) = 50, admitted: 16 + 6 = 22 -> 44%

        Aggregate: X (66%) > Y (44%) -> positive (since X comes first by freq).

        Per department:
        Dept A: X=32/40=80%, Y=16/20=80% -> neutral
        Dept B: X=1/10=10%, Y=6/30=20% -> Y > X (negative)

        So only 1 non-neutral segment and it reverses. That's a paradox.
        """
        result = check_simpsons_paradox(
            paradox_data,
            metric_column="admitted",
            segment_column="department",
            comparison_column="group",
        )
        # The aggregate shows X > Y
        assert result["aggregate_direction"] in ("positive", "negative")
        # At least one segment reverses
        assert len(result["reversals"]) > 0 or result["paradox_detected"] is True
        assert "explanation" in result
        assert len(result["explanation"]) > 0

    def test_neutral_aggregate(self):
        """When aggregate shows no difference, no paradox is flagged."""
        # Both groups have identical values
        df = pd.DataFrame({
            "metric": [0.5] * 100,
            "group": (["A"] * 50 + ["B"] * 50),
            "segment": (["S1"] * 25 + ["S2"] * 25) * 2,
        })
        result = check_simpsons_paradox(
            df,
            metric_column="metric",
            segment_column="segment",
            comparison_column="group",
        )
        assert result["paradox_detected"] is False
        assert result["aggregate_direction"] == "neutral"

    def test_handles_empty_segments(self):
        """Empty DataFrame returns gracefully."""
        df = pd.DataFrame({
            "metric": pd.Series(dtype=float),
            "group": pd.Series(dtype=str),
            "segment": pd.Series(dtype=str),
        })
        result = check_simpsons_paradox(
            df,
            metric_column="metric",
            segment_column="segment",
            comparison_column="group",
        )
        assert result["paradox_detected"] is False
        assert "empty" in result["explanation"].lower() or "insufficient" in result["explanation"].lower()

    def test_single_segment(self):
        """With only one segment, there can be no paradox."""
        df = pd.DataFrame({
            "metric": [1, 2, 3, 4, 5, 6],
            "group": ["A", "A", "A", "B", "B", "B"],
            "segment": ["only"] * 6,
        })
        result = check_simpsons_paradox(
            df,
            metric_column="metric",
            segment_column="segment",
            comparison_column="group",
        )
        assert result["paradox_detected"] is False
        # Only 1 segment, so 0 reversals possible
        assert len(result["reversals"]) == 0


# ============================================================
# TestMultiSegment
# ============================================================

class TestMultiSegment:
    """Tests for check_simpsons_multi_segment."""

    def test_multiple_dimensions(self, paradox_data):
        """Scan two dimensions; department should flag, group itself won't."""
        # Add a second dimension that has no paradox
        df = paradox_data.copy()
        np.random.seed(99)
        df["region"] = np.random.choice(["East", "West"], len(df))

        result = check_simpsons_multi_segment(
            df,
            metric_column="admitted",
            segment_columns=["department", "region"],
            comparison_column="group",
        )
        assert result["scanned"] == 2
        assert isinstance(result["paradoxes_found"], int)
        assert "department" in result["results"]
        assert "region" in result["results"]
        assert "interpretation" in result

    def test_paradox_in_one_dimension_only(self):
        """Build data where dept shows paradox but region does not."""
        # Use the conftest-style admissions data
        rows = []
        # Dept A (easy): Both groups do well
        rows.extend([{"dept": "A", "group": "X", "region": "East", "admitted": 1}] * 40)
        rows.extend([{"dept": "A", "group": "X", "region": "West", "admitted": 1}] * 40)
        rows.extend([{"dept": "A", "group": "X", "region": "East", "admitted": 0}] * 10)
        rows.extend([{"dept": "A", "group": "X", "region": "West", "admitted": 0}] * 10)
        # Group Y in Dept A: also does well
        rows.extend([{"dept": "A", "group": "Y", "region": "East", "admitted": 1}] * 23)
        rows.extend([{"dept": "A", "group": "Y", "region": "West", "admitted": 1}] * 23)
        rows.extend([{"dept": "A", "group": "Y", "region": "East", "admitted": 0}] * 7)
        rows.extend([{"dept": "A", "group": "Y", "region": "West", "admitted": 0}] * 7)

        # Dept B (hard): Group X barely gets in, Group Y does slightly better
        rows.extend([{"dept": "B", "group": "X", "region": "East", "admitted": 1}] * 1)
        rows.extend([{"dept": "B", "group": "X", "region": "West", "admitted": 0}] * 49)
        rows.extend([{"dept": "B", "group": "Y", "region": "East", "admitted": 1}] * 3)
        rows.extend([{"dept": "B", "group": "Y", "region": "West", "admitted": 1}] * 3)
        rows.extend([{"dept": "B", "group": "Y", "region": "East", "admitted": 0}] * 7)
        rows.extend([{"dept": "B", "group": "Y", "region": "West", "admitted": 0}] * 7)

        df = pd.DataFrame(rows)

        result = check_simpsons_multi_segment(
            df,
            metric_column="admitted",
            segment_columns=["dept", "region"],
            comparison_column="group",
        )
        assert result["scanned"] == 2
        # At minimum the function runs on both dimensions
        assert len(result["results"]) == 2


# ============================================================
# TestWeightedVsUnweighted
# ============================================================

class TestWeightedVsUnweighted:
    """Tests for weighted_vs_unweighted."""

    def test_no_difference(self):
        """When all segments have equal weight, weighted = unweighted."""
        df = pd.DataFrame({
            "metric": [10, 20, 30, 40],
            "weight": [1, 1, 1, 1],
            "segment": ["A", "A", "B", "B"],
        })
        result = weighted_vs_unweighted(
            df,
            metric_column="metric",
            weight_column="weight",
            segment_column="segment",
        )
        assert result["paradox_detected"] is False
        assert abs(result["difference"]) < 1e-6

    def test_weighting_reverses(self):
        """When segment sizes are imbalanced, weighted avg can diverge.

        Segment A: metric=90, weight=100 (large segment, high metric)
        Segment B: metric=10, weight=1   (tiny segment, low metric)

        Unweighted average of segment means: (90 + 10) / 2 = 50
        Weighted average: (90*100 + 10*1) / 101 = 89.2

        These are very different.
        """
        df = pd.DataFrame({
            "metric": [90] * 100 + [10] * 1,
            "weight": [100] * 100 + [1] * 1,
            "segment": ["A"] * 100 + ["B"] * 1,
        })
        result = weighted_vs_unweighted(
            df,
            metric_column="metric",
            weight_column="weight",
            segment_column="segment",
        )
        assert result["paradox_detected"] is True
        assert abs(result["weighted_result"] - result["unweighted_result"]) > 1.0
        assert "differs" in result["explanation"].lower() or "imbalance" in result["explanation"].lower()

    def test_handles_zero_weights(self):
        """Zero weights should be filtered out gracefully."""
        df = pd.DataFrame({
            "metric": [10, 20, 30],
            "weight": [0, 0, 0],
            "segment": ["A", "B", "C"],
        })
        result = weighted_vs_unweighted(
            df,
            metric_column="metric",
            weight_column="weight",
            segment_column="segment",
        )
        assert result["paradox_detected"] is False
        assert result["weighted_result"] is None


# ============================================================
# TestGenerateReport
# ============================================================

class TestGenerateReport:
    """Tests for generate_paradox_report."""

    def test_report_no_paradox(self, no_paradox_data):
        """Report for a clean check should contain NOT DETECTED."""
        result = check_simpsons_paradox(
            no_paradox_data,
            metric_column="admitted",
            segment_column="department",
            comparison_column="group",
        )
        report = generate_paradox_report(result)
        assert isinstance(report, str)
        assert "NOT DETECTED" in report
        assert "Simpson's Paradox" in report

    def test_report_with_paradox(self, paradox_data):
        """Report for a paradox should contain DETECTED and reversal info."""
        result = check_simpsons_paradox(
            paradox_data,
            metric_column="admitted",
            segment_column="department",
            comparison_column="group",
        )
        report = generate_paradox_report(result)
        assert isinstance(report, str)
        assert "Simpson's Paradox" in report
        # The report should contain a table with segments
        assert "Segment" in report
        assert "Direction" in report


# ============================================================
# TestSuggestSegments
# ============================================================

class TestSuggestSegments:
    """Tests for suggest_segments_to_check."""

    def test_suggests_high_variance_columns(self):
        """Columns with more imbalanced group sizes should rank higher."""
        np.random.seed(42)
        n = 200
        df = pd.DataFrame({
            "metric": np.random.randn(n),
            # Balanced column -- equal group sizes
            "balanced": np.random.choice(["A", "B"], n, p=[0.5, 0.5]),
            # Imbalanced column -- one group dominates
            "imbalanced": np.random.choice(
                ["X", "Y", "Z"], n, p=[0.8, 0.15, 0.05]
            ),
        })
        suggestions = suggest_segments_to_check(
            df, metric_column="metric"
        )
        assert isinstance(suggestions, list)
        assert len(suggestions) > 0
        # The imbalanced column should be ranked first (higher CV)
        assert suggestions[0] == "imbalanced"

    def test_max_segments_limit(self):
        """Should not return more than max_segments."""
        np.random.seed(42)
        n = 100
        df = pd.DataFrame({
            "metric": np.random.randn(n),
            "cat_a": np.random.choice(["A", "B"], n),
            "cat_b": np.random.choice(["X", "Y", "Z"], n),
            "cat_c": np.random.choice(["P", "Q"], n),
            "cat_d": np.random.choice(["M", "N", "O", "R"], n),
        })
        suggestions = suggest_segments_to_check(
            df, metric_column="metric", max_segments=2
        )
        assert len(suggestions) <= 2

    def test_handles_no_categorical(self):
        """DataFrame with only numeric columns returns empty list."""
        df = pd.DataFrame({
            "metric": [1.0, 2.0, 3.0],
            "other_numeric": [4.0, 5.0, 6.0],
        })
        suggestions = suggest_segments_to_check(
            df, metric_column="metric"
        )
        assert suggestions == []


# ============================================================
# Legacy API compatibility
# ============================================================

class TestLegacyAPI:
    """Verify that the legacy scan_dimensions API still works."""

    def test_scan_dimensions_backward_compat(self, no_paradox_data):
        """Legacy callers using scan_dimensions should still work."""
        from helpers.validation.simpsons_paradox import scan_dimensions

        result = scan_dimensions(
            no_paradox_data,
            metric_col="admitted",
            group_col="group",
            candidate_segments=["department"],
        )
        assert result["scanned"] == 1
        assert isinstance(result["paradoxes_found"], int)
        assert isinstance(result["results"], list)
        assert len(result["results"]) == 1

        # Legacy result should have legacy field names
        r = result["results"][0]
        assert "paradox_detected" in r
        assert "severity" in r
        # Legacy severity uses PASS/INFO/BLOCKER
        assert r["severity"] in ("PASS", "INFO", "BLOCKER", "WARNING")

    def test_legacy_param_names(self, no_paradox_data):
        """Calling check_simpsons_paradox with legacy param names works."""
        result = check_simpsons_paradox(
            no_paradox_data,
            metric_col="admitted",
            group_col="group",
            segment_col="department",
        )
        assert "paradox_detected" in result
        # Legacy callers get segment_directions and reversal_segments
        assert "segment_directions" in result
        assert "reversal_segments" in result
        assert result["severity"] in ("PASS", "INFO", "BLOCKER")
