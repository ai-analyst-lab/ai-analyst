"""Dedicated unit tests for helpers/confidence_scoring.py."""
from __future__ import annotations
import pytest
from helpers.confidence_scoring import (
    score_confidence, format_confidence_badge, merge_confidence_scores,
    _grade_from_score, _recommendation_from_grade, _validators_present,
    _score_data_completeness, _score_structural_integrity,
    _score_aggregation_consistency, _score_temporal_consistency,
    _score_business_plausibility, _score_simpsons_paradox,
    _score_sample_size, _GRADE_THRESHOLDS_RANK,
)

class TestGradeHelpers:
    @pytest.mark.parametrize("score,expected", [
        (100, "A"), (85, "A"), (84, "B"), (70, "B"), (69, "C"),
        (55, "C"), (54, "D"), (40, "D"), (39, "F"), (0, "F"), (-1, "F"),
    ])
    def test_grade_boundaries(self, score, expected):
        assert _grade_from_score(score) == expected

    @pytest.mark.parametrize("grade", ["A", "B", "C", "D", "F"])
    def test_recommendation_exists(self, grade):
        assert isinstance(_recommendation_from_grade(grade), str)

    def test_recommendation_unknown_falls_back(self):
        assert _recommendation_from_grade("Z") == _recommendation_from_grade("F")

    @pytest.mark.parametrize("grade,rank", [
        ("A", 0), ("B", 1), ("C", 2), ("D", 3), ("F", 4),
    ])
    def test_rank_ordering(self, grade, rank):
        assert _GRADE_THRESHOLDS_RANK(grade) == rank

    def test_rank_unknown_defaults_worst(self):
        assert _GRADE_THRESHOLDS_RANK("X") == 4

class TestFactorScoring:
    def test_completeness_missing_and_empty(self):
        assert _score_data_completeness({})["status"] == "MISSING"
        assert _score_data_completeness({"completeness": {"columns": []}})["status"] == "MISSING"

    @pytest.mark.parametrize("null_rate,expected", [
        (0.005, 15), (0.03, 12), (0.08, 9), (0.15, 5), (0.25, 2),
    ])
    def test_completeness_tiers(self, null_rate, expected):
        assert _score_data_completeness({"completeness": {"columns": [{"null_rate": null_rate}]}})["score"] == expected

    def test_structural_missing(self):
        assert _score_structural_integrity({})["status"] == "MISSING"

    def test_structural_pass_and_blocker(self):
        assert _score_structural_integrity({"primary_key": {"severity": "PASS"}, "schema": {"severity": "PASS"}})["score"] == 15
        r = _score_structural_integrity({"primary_key": {"severity": "BLOCKER", "null_count": 5, "duplicate_count": 3}})
        assert r["score"] == 3 and r["status"] == "BLOCKER"

    def test_aggregation_missing_pass_blocker(self):
        assert _score_aggregation_consistency({})["status"] == "MISSING"
        assert _score_aggregation_consistency({"aggregation": {"severity": "PASS", "mismatches": []}})["score"] == 15
        r = _score_aggregation_consistency({"aggregation": {"severity": "WARNING", "mismatches": [{"diff_pct": 0.10}]}})
        assert r["score"] == 3 and r["status"] == "BLOCKER"

    def test_temporal_missing_pass_gap_break(self):
        assert _score_temporal_consistency({})["status"] == "MISSING"
        no_gap = {"temporal": {"missing_dates": [], "duplicate_dates": [], "zero_dates": []}}
        assert _score_temporal_consistency(no_gap)["score"] == 15
        minor = {"temporal": {"missing_dates": ["2024-01-05"], "duplicate_dates": [], "zero_dates": []}}
        assert _score_temporal_consistency(minor)["score"] == 10
        brk = {**no_gap, "trend_continuity": {"severity": "BLOCKER", "breaks": [{"idx": 3}]}}
        r = _score_temporal_consistency(brk)
        assert r["score"] == 3 and r["status"] == "BLOCKER"

    def test_business_missing_pass_fail(self):
        assert _score_business_plausibility({})["status"] == "MISSING"
        vr_pass = {"ranges": {"violations": [{"severity": "PASS"}]}, "rates": {"severity": "PASS"}}
        assert _score_business_plausibility(vr_pass)["score"] == 15
        r = _score_business_plausibility({"ranges": {"violations": [{"severity": "FAIL", "rule_name": "price"}]}})
        assert r["score"] == 5 and r["status"] == "BLOCKER"

    def test_simpsons_missing_no_paradox_core_noncore(self):
        assert _score_simpsons_paradox({})["status"] == "MISSING"
        assert _score_simpsons_paradox({"simpsons": {"paradox_detected": False, "paradoxes_found": 0}})["score"] == 15
        assert _score_simpsons_paradox({"simpsons": {"paradox_detected": True, "paradoxes_found": 1, "is_core_metric": True}})["score"] == 2
        assert _score_simpsons_paradox({"simpsons": {"paradox_detected": True, "paradoxes_found": 1, "is_core_metric": False}})["score"] == 8

    def test_simpsons_multi_dimension_scan(self):
        vr = {"simpsons": {"results": [{"paradox_detected": True}, {"paradox_detected": False}], "is_core_metric": False}}
        r = _score_simpsons_paradox(vr)
        assert r["score"] == 8 and r["status"] == "WARNING"

    def test_sample_size_missing(self):
        assert _score_sample_size(None)["status"] == "MISSING"
        assert _score_sample_size({})["status"] == "MISSING"

    @pytest.mark.parametrize("rows,expected", [
        (50000, 10), (5000, 8), (500, 5), (50, 3), (10, 1),
    ])
    def test_sample_size_tiers(self, rows, expected):
        assert _score_sample_size({"row_count": rows})["score"] == expected

class TestValidatorsPresent:
    def test_empty_and_full(self):
        assert not any(_validators_present({}).values())
        assert all(_validators_present({
            "completeness": {}, "aggregation": {}, "ranges": {}, "simpsons": {},
            "cross_verification": {}, "reproducibility": {},
        }).values())

_ALL_PASS_VR = {
    "completeness": {"columns": [{"null_rate": 0.0}]},
    "primary_key": {"severity": "PASS"},
    "aggregation": {"severity": "PASS", "mismatches": []},
    "temporal": {"missing_dates": [], "duplicate_dates": [], "zero_dates": []},
    "ranges": {"violations": [{"severity": "PASS"}]},
    "simpsons": {"paradox_detected": False, "paradoxes_found": 0},
    "cross_verification": {"overall_score": 1.0, "checks": [{"status": "PASS"}]},
    "reproducibility": {"deterministic": True, "variance": 0.0},
}

class TestScoreConfidence:
    def test_empty_returns_f(self):
        r = score_confidence({})
        assert r["score"] == 0 and r["grade"] == "F"
        assert "No validation results" in r["blockers"][0]

    def test_perfect_score_gets_a(self):
        r = score_confidence(_ALL_PASS_VR, metadata={"row_count": 100000})
        assert r["grade"] == "A" and r["score"] >= 85

    def test_partial_results_cap_at_c(self):
        r = score_confidence({"primary_key": {"severity": "PASS"}}, metadata={"row_count": 100000})
        assert r["grade"] in ("C", "D", "F")

    def test_blockers_listed(self):
        vr = {**_ALL_PASS_VR, "primary_key": {"severity": "BLOCKER", "null_count": 10, "duplicate_count": 5}}
        r = score_confidence(vr, metadata={"row_count": 500})
        assert len(r["blockers"]) > 0
        assert any("structural_integrity" in b for b in r["blockers"])

class TestFormatBadge:
    def test_badge_score_and_grade(self):
        r = score_confidence(_ALL_PASS_VR, metadata={"row_count": 100000})
        badge = format_confidence_badge(r)
        assert f"{r['score']}/100" in badge and r["grade"] in badge

    def test_badge_blockers_and_missing(self):
        r1 = score_confidence({"primary_key": {"severity": "BLOCKER", "null_count": 1, "duplicate_count": 2}})
        assert "BLOCKER" in format_confidence_badge(r1)
        r2 = score_confidence({"primary_key": {"severity": "PASS"}})
        assert "Missing" in format_confidence_badge(r2)

    def test_badge_empty_result(self):
        assert "0/100" in format_confidence_badge({"score": 0, "grade": "F", "factors": {}, "blockers": []})

class TestMergeScores:
    def test_empty_list_returns_f(self):
        r = merge_confidence_scores([])
        assert r["score"] == 0 and r["grade"] == "F"

    def test_single_item_passthrough(self):
        orig = score_confidence({"primary_key": {"severity": "PASS"}}, metadata={"row_count": 5000})
        assert merge_confidence_scores([orig]) is orig

    def test_two_scores_averaged(self):
        s1 = {"score": 80, "grade": "B", "factors": {}, "blockers": []}
        s2 = {"score": 60, "grade": "C", "factors": {}, "blockers": []}
        assert merge_confidence_scores([s1, s2])["score"] == 70

    def test_blocker_union(self):
        s1 = {"score": 50, "grade": "C", "factors": {}, "blockers": ["issue A"]}
        s2 = {"score": 50, "grade": "C", "factors": {}, "blockers": ["issue B"]}
        m = merge_confidence_scores([s1, s2])
        assert "issue A" in m["blockers"] and "issue B" in m["blockers"]

    def test_worst_individual_d_caps_at_c(self):
        s1 = {"score": 90, "grade": "A", "factors": {}, "blockers": []}
        s2 = {"score": 30, "grade": "D", "factors": {}, "blockers": []}
        assert merge_confidence_scores([s1, s2])["grade"] in ("C", "D", "F")

    def test_merged_factors_take_worst(self):
        f_ok = {"score": 15, "max": 15, "status": "PASS", "detail": "ok"}
        f_bad = {"score": 3, "max": 15, "status": "BLOCKER", "detail": "bad"}
        s1 = {"score": 80, "grade": "B", "factors": {"data_completeness": f_ok}, "blockers": []}
        s2 = {"score": 40, "grade": "D", "factors": {"data_completeness": f_bad}, "blockers": []}
        mf = merge_confidence_scores([s1, s2])["factors"]["data_completeness"]
        assert mf["score"] == 3 and mf["status"] == "BLOCKER"
