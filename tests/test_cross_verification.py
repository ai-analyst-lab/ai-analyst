"""Tests for helpers.cross_verification — Type A-D checks, scoring, provenance."""

import pytest

from helpers.cross_verification import (
    TOLERANCE_TYPE_A,
    TOLERANCE_TYPE_B,
    TOLERANCE_TYPE_C,
    TOLERANCE_TYPE_D,
    resolve_tolerance,
    run_boundary_checks,
    run_parts_to_whole,
    run_ratio_recompute,
    run_algebraic_identity,
    score_cross_verification,
    score_reproducibility,
    overall_status,
    safe_run_verification,
    build_raw_provenance,
    format_verification_table,
)
from helpers.tolerance_config import ToleranceConfig


# =====================================================================
# Tolerance resolution
# =====================================================================

class TestResolveTolerance:
    def test_boundary_base_is_zero(self):
        assert resolve_tolerance("boundary") == TOLERANCE_TYPE_A

    def test_parts_to_whole_base(self):
        assert resolve_tolerance("parts_to_whole") == TOLERANCE_TYPE_B

    def test_ratio_base(self):
        assert resolve_tolerance("ratio_consistency") == TOLERANCE_TYPE_C

    def test_algebraic_identity_base(self):
        assert resolve_tolerance("algebraic_identity") == TOLERANCE_TYPE_D

    def test_snowflake_distinct_count_adds_adjustment(self):
        config = ToleranceConfig.for_connection_type("snowflake")
        effective = resolve_tolerance("distinct_count", config)
        assert effective == pytest.approx(0.02)  # 0% base + 2% adjustment

    def test_csv_no_adjustments(self):
        config = ToleranceConfig.for_connection_type("csv")
        effective = resolve_tolerance("parts_to_whole", config)
        assert effective == TOLERANCE_TYPE_B  # No adjustment

    def test_unknown_check_type_returns_zero(self):
        assert resolve_tolerance("invented_check_type") == 0.0


# =====================================================================
# Type A: Boundary checks
# =====================================================================

class TestBoundaryChecks:
    def test_positive_revenue_passes(self):
        claims = [{"claim_id": "c1", "value": 1000.0, "metric_type": "revenue"}]
        results = run_boundary_checks(claims)
        assert any(r["check"] == "non_negative_monetary" and r["status"] == "PASS"
                    for r in results)

    def test_negative_revenue_fails(self):
        claims = [{"claim_id": "c2", "value": -50.0, "metric_type": "revenue"}]
        results = run_boundary_checks(claims)
        assert any(r["check"] == "non_negative_monetary" and r["status"] == "FAIL"
                    for r in results)

    def test_percentage_in_bounds_passes(self):
        claims = [{"claim_id": "c3", "value": 42.5, "metric_type": "percentage"}]
        results = run_boundary_checks(claims)
        assert any(r["check"] == "percentage_bounds" and r["status"] == "PASS"
                    for r in results)

    def test_percentage_over_100_fails(self):
        claims = [{"claim_id": "c4", "value": 105.0, "metric_type": "percentage"}]
        results = run_boundary_checks(claims)
        assert any(r["check"] == "percentage_bounds" and r["status"] == "FAIL"
                    for r in results)

    def test_percentage_negative_fails(self):
        claims = [{"claim_id": "c5", "value": -5.0, "metric_type": "pct"}]
        results = run_boundary_checks(claims)
        assert any(r["status"] == "FAIL" for r in results)

    def test_future_date_fails(self):
        claims = [{"claim_id": "c6", "value": "2099-01-01", "metric_type": "date"}]
        results = run_boundary_checks(claims)
        assert any(r["check"] == "no_future_dates" and r["status"] == "FAIL"
                    for r in results)

    def test_past_date_passes(self):
        claims = [{"claim_id": "c7", "value": "2024-06-15", "metric_type": "date"}]
        results = run_boundary_checks(claims)
        assert any(r["check"] == "no_future_dates" and r["status"] == "PASS"
                    for r in results)

    def test_zero_denominator_fails(self):
        claims = [{
            "claim_id": "c8", "value": 0.5,
            "metric_type": "ratio", "denominator": 0,
        }]
        results = run_boundary_checks(claims)
        assert any(r["check"] == "zero_denominator" and r["status"] == "FAIL"
                    for r in results)

    def test_nonzero_denominator_passes(self):
        claims = [{
            "claim_id": "c9", "value": 0.5,
            "metric_type": "ratio", "denominator": 100,
        }]
        results = run_boundary_checks(claims)
        assert any(r["check"] == "zero_denominator" and r["status"] == "PASS"
                    for r in results)

    def test_missing_source_table_flags(self):
        claims = [{"claim_id": "c10", "value": 100, "metric_type": "count"}]
        results = run_boundary_checks(claims)
        assert any(r["check"] == "source_citation" and r["tier"] == "1b"
                    for r in results)

    def test_source_table_present_no_flag(self):
        claims = [{
            "claim_id": "c11", "value": 100,
            "metric_type": "count", "source_table": "orders",
        }]
        results = run_boundary_checks(claims)
        assert not any(r["check"] == "source_citation" for r in results)

    def test_none_value_skipped(self):
        claims = [{"claim_id": "c12", "value": None, "metric_type": "revenue"}]
        results = run_boundary_checks(claims)
        assert results == []

    def test_empty_claims_returns_empty(self):
        assert run_boundary_checks([]) == []


# =====================================================================
# Type B: Parts-to-whole
# =====================================================================

class TestPartsToWhole:
    def test_exact_match_passes(self):
        result = run_parts_to_whole(100.0, [60.0, 40.0])
        assert result["status"] == "PASS"
        assert result["diff_pct"] == 0.0

    def test_within_tolerance_passes(self):
        # 100 vs 100.5 = 0.5% diff, within 1% tolerance
        result = run_parts_to_whole(100.0, [60.0, 40.5])
        assert result["status"] == "PASS"

    def test_exceeds_tolerance_fails(self):
        # 100 vs 120 = 20% diff
        result = run_parts_to_whole(100.0, [60.0, 60.0])
        assert result["status"] == "FAIL"

    def test_both_zero_passes(self):
        result = run_parts_to_whole(0.0, [0.0, 0.0])
        assert result["status"] == "PASS"

    def test_snowflake_tolerance_applied(self):
        config = ToleranceConfig.for_connection_type("snowflake")
        result = run_parts_to_whole(100.0, [60.0, 40.0], tolerance_config=config)
        assert result["status"] == "PASS"

    def test_claim_id_passed_through(self):
        result = run_parts_to_whole(100.0, [50.0, 50.0], claim_id="rev-1")
        assert result["claim_id"] == "rev-1"


# =====================================================================
# Type C: Ratio recompute
# =====================================================================

class TestRatioRecompute:
    def test_exact_ratio_passes(self):
        result = run_ratio_recompute(0.5, 50.0, 100.0)
        assert result["status"] == "PASS"

    def test_close_ratio_passes(self):
        # 0.500 vs 0.5005 = 0.1% diff, at the tolerance boundary
        result = run_ratio_recompute(0.5, 50.05, 100.0)
        assert result["status"] == "PASS"

    def test_divergent_ratio_fails(self):
        # 0.5 vs 0.8 = 60% diff
        result = run_ratio_recompute(0.5, 80.0, 100.0)
        assert result["status"] == "FAIL"

    def test_zero_denominator_fails(self):
        result = run_ratio_recompute(0.5, 50.0, 0.0)
        assert result["status"] == "FAIL"
        assert "Zero denominator" in result["detail"]

    def test_both_zero_passes(self):
        result = run_ratio_recompute(0.0, 0.0, 100.0)
        assert result["status"] == "PASS"


# =====================================================================
# Type D: Algebraic identity
# =====================================================================

class TestAlgebraicIdentity:
    def test_exact_match_passes(self):
        result = run_algebraic_identity(1000.0, 1000.0, "revenue check")
        assert result["status"] == "PASS"

    def test_tiny_diff_passes(self):
        # 1000 vs 1000.005 = 0.0005% diff, within 0.01%
        result = run_algebraic_identity(1000.0, 1000.005)
        assert result["status"] == "PASS"

    def test_large_diff_fails(self):
        result = run_algebraic_identity(1000.0, 1200.0)
        assert result["status"] == "FAIL"

    def test_both_zero_passes(self):
        result = run_algebraic_identity(0.0, 0.0)
        assert result["status"] == "PASS"

    def test_identity_description_in_detail(self):
        result = run_algebraic_identity(100.0, 100.0, "qty * price = revenue")
        assert "qty * price = revenue" in result["detail"]


# =====================================================================
# Scoring
# =====================================================================

class TestScoring:
    def test_all_pass_returns_10(self):
        results = [
            {"status": "PASS", "type": "B"},
            {"status": "PASS", "type": "C"},
            {"status": "PASS", "type": "D"},
        ]
        assert score_cross_verification(results) == 10

    def test_type_a_fail_returns_0(self):
        results = [
            {"status": "FAIL", "tier": "1a"},
            {"status": "PASS", "type": "B"},
        ]
        assert score_cross_verification(results) == 0

    def test_type_b_fail_returns_2(self):
        results = [
            {"status": "FAIL", "type": "B"},
            {"status": "PASS", "type": "C"},
        ]
        assert score_cross_verification(results) == 2

    def test_type_cd_fail_returns_4(self):
        results = [
            {"status": "PASS", "type": "B"},
            {"status": "FAIL", "type": "C"},
        ]
        assert score_cross_verification(results) == 4

    def test_type_b_warn_returns_6(self):
        results = [
            {"status": "WARN", "type": "B"},
            {"status": "PASS", "type": "C"},
        ]
        assert score_cross_verification(results) == 6

    def test_type_cd_warn_returns_8(self):
        results = [
            {"status": "PASS", "type": "B"},
            {"status": "WARN", "type": "D"},
        ]
        assert score_cross_verification(results) == 8

    def test_empty_results_returns_5(self):
        assert score_cross_verification([]) == 5

    def test_repro_pass_returns_5(self):
        assert score_reproducibility({"status": "PASS"}) == 5

    def test_repro_skipped_returns_5(self):
        assert score_reproducibility({"status": "SKIPPED"}) == 5

    def test_repro_warn_returns_3(self):
        assert score_reproducibility({"status": "WARN"}) == 3

    def test_repro_fail_returns_0(self):
        assert score_reproducibility({"status": "FAIL"}) == 0


# =====================================================================
# Overall status
# =====================================================================

class TestOverallStatus:
    def test_all_pass(self):
        assert overall_status([{"status": "PASS"}, {"status": "PASS"}]) == "PASS"

    def test_any_fail(self):
        assert overall_status([{"status": "PASS"}, {"status": "FAIL"}]) == "FAIL"

    def test_warn_without_fail(self):
        assert overall_status([{"status": "PASS"}, {"status": "WARN"}]) == "WARN"

    def test_flag_counts_as_warn(self):
        assert overall_status([{"status": "PASS"}, {"status": "FLAG"}]) == "WARN"


# =====================================================================
# Safe wrapper
# =====================================================================

class TestSafeRunVerification:
    def test_returns_result_on_success(self):
        result = safe_run_verification(
            run_parts_to_whole, 100.0, [50.0, 50.0]
        )
        assert result["status"] == "PASS"

    def test_returns_error_on_exception(self):
        def broken_fn():
            raise ValueError("boom")
        result = safe_run_verification(broken_fn)
        assert result["status"] == "ERROR"
        assert "boom" in result["detail"]


# =====================================================================
# Provenance builder
# =====================================================================

class TestBuildRawProvenance:
    def test_basic_provenance(self):
        boundary = [{"claim_id": "c1", "check": "non_negative_monetary",
                      "tier": "1a", "status": "PASS", "detail": "ok"}]
        ptw = run_parts_to_whole(100.0, [60.0, 40.0], claim_id="c1")
        prov = build_raw_provenance(
            claim_id="c1",
            claim_text="Revenue was $100",
            boundary_results=boundary,
            parts_to_whole_result=ptw,
        )
        assert prov["claim_id"] == "c1"
        assert prov["verification"]["boundary"]["status"] == "PASS"
        assert prov["verification"]["parts_to_whole"]["status"] == "PASS"
        assert prov["confidence_contribution"] == 10

    def test_no_checks_produces_na(self):
        prov = build_raw_provenance(
            claim_id="c2",
            claim_text="Some claim",
        )
        assert prov["verification"]["parts_to_whole"]["status"] == "N/A"
        assert prov["verification"]["ratio_recompute"]["status"] == "N/A"

    def test_query_log_refs_passthrough(self):
        prov = build_raw_provenance(
            claim_id="c3",
            claim_text="test",
            query_log_refs=["q1", "q2"],
        )
        assert prov["query_log_refs"] == ["q1", "q2"]


# =====================================================================
# Format table
# =====================================================================

class TestFormatVerificationTable:
    def test_empty_results(self):
        assert "No verification" in format_verification_table([])

    def test_renders_markdown_table(self):
        results = [
            {"claim_id": "c1", "check": "boundary", "type": "A",
             "status": "PASS", "detail": "ok"},
        ]
        table = format_verification_table(results)
        assert "| c1 |" in table
        assert "| PASS |" in table
        assert "Claim" in table  # header
