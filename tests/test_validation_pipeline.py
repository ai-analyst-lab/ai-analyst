"""Validation pipeline integration tests -- cross-layer composition,
orchestrators, degradation resilience, and config-driven checks.
Complements test_validation_e2e.py which covers individual layers."""
from __future__ import annotations

import pandas as pd
import pytest


# ============================================================
# TestOrchestrators
# ============================================================
class TestOrchestrators:
    """Orchestrator functions dispatch correctly with config dicts."""

    def test_structural_orchestrator_full_config(self, synthetic_orders):
        from helpers.structural_validator import run_structural_checks
        config = {
            "expected_columns": ["order_id", "user_id", "amount"],
            "primary_key": ["order_id"],
            "required_columns": ["order_id", "user_id", "amount"],
            "completeness_threshold": 0.95,
            "min_rows": 10, "max_rows": 10000,
            "value_domain": {"column": "amount", "min_val": 0},
        }
        result = run_structural_checks(synthetic_orders, config)
        assert result["overall_ok"] is True
        assert result["checks_run"] >= 4
        assert result["checks_passed"] == result["checks_run"]
        for key in ("schema", "primary_key", "completeness", "row_count", "value_domain"):
            assert key in result["details"]

    def test_logical_orchestrator_full_config(self, synthetic_orders):
        from helpers.logical_validator import run_logical_checks
        summary = (synthetic_orders[["status", "amount"]]
                   .groupby("status")["amount"].sum().reset_index())
        config = {
            "metric_column": "amount", "group_column": "status",
            "tolerance": 0.01, "date_column": "order_date",
            "balance_column": "status",
        }
        result = run_logical_checks(
            detail_df=synthetic_orders, summary_df=summary, config=config,
        )
        assert result["ok"] is True
        assert result["checks_run"] >= 2
        assert "aggregation_consistency" in result["results"]

    def test_business_rules_orchestrator_full_config(self, synthetic_orders):
        from helpers.business_rules import validate_business_rules
        rules_config = {
            "ranges": [{"column": "amount", "min": 0, "max": 100000, "label": "Amount"}],
            "no_negative": ["amount"],
            "segment_coverage": {
                "segment_column": "status",
                "expected_segments": ["completed", "cancelled", "pending", "refunded"],
            },
            "cardinality": [{"column": "category", "expected_min": 2, "expected_max": 20}],
        }
        result = validate_business_rules(synthetic_orders, rules_config)
        assert result["ok"] is True
        for key in ("ranges", "no_negative", "segment_coverage", "cardinality_category"):
            assert key in result["results"]
        assert "passed" in result["summary"].lower()


# ============================================================
# TestCrossLayerPipeline
# ============================================================
class TestCrossLayerPipeline:
    """All 4 layers sequentially on same dataset -> confidence score."""

    def test_clean_data_produces_high_confidence(self, synthetic_orders, synthetic_users):
        from helpers.structural_validator import run_structural_checks
        from helpers.logical_validator import run_logical_checks
        from helpers.business_rules import validate_business_rules
        from helpers.simpsons_paradox import check_simpsons_multi_segment
        from helpers.confidence_scoring import score_confidence

        merged = synthetic_orders.merge(
            synthetic_users[["user_id", "device", "country"]], on="user_id", how="left",
        )
        # Layer 1
        struct = run_structural_checks(merged, {
            "expected_columns": ["order_id", "user_id", "amount", "status"],
            "primary_key": ["order_id"],
            "required_columns": ["order_id", "user_id", "amount"],
        })
        assert struct["overall_ok"] is True
        # Layer 2
        summary = (merged[["status", "amount"]]
                   .groupby("status")["amount"].sum().reset_index())
        logical = run_logical_checks(
            detail_df=merged, summary_df=summary,
            config={"metric_column": "amount", "group_column": "status"},
        )
        assert logical["ok"] is True
        # Layer 3
        biz = validate_business_rules(merged, {
            "ranges": [{"column": "amount", "min": 0, "max": 100000, "label": "Amount"}],
            "no_negative": ["amount"],
        })
        assert biz["ok"] is True
        # Layer 4
        simpsons = check_simpsons_multi_segment(
            merged, metric_column="amount",
            segment_columns=["device", "country"], comparison_column="status",
        )
        # Compose for confidence scorer
        validation_results = {
            "schema": struct["details"].get("schema"),
            "primary_key": struct["details"].get("primary_key"),
            "completeness": struct["details"].get("completeness"),
            "ranges": biz["results"].get("ranges"),
            "simpsons": simpsons,
        }
        confidence = score_confidence(validation_results, metadata={"row_count": len(merged)})
        assert confidence["score"] > 0
        assert confidence["grade"] in ("A", "B", "C")
        assert len(confidence["factors"]) == 9

    def test_dirty_data_produces_low_confidence(self, dirty_orders):
        from helpers.structural_validator import run_structural_checks
        from helpers.business_rules import validate_business_rules
        from helpers.confidence_scoring import score_confidence

        struct = run_structural_checks(dirty_orders, {
            "primary_key": ["order_id"],
            "required_columns": ["order_id", "user_id", "amount"],
        })
        assert struct["overall_ok"] is False
        biz = validate_business_rules(dirty_orders, {
            "ranges": [{"column": "amount", "min": 0, "max": 10000, "label": "Amount"}],
            "no_negative": ["amount"],
        })
        validation_results = {
            "primary_key": struct["details"].get("primary_key"),
            "completeness": struct["details"].get("completeness"),
            "ranges": biz["results"].get("ranges"),
        }
        confidence = score_confidence(validation_results, metadata={"row_count": len(dirty_orders)})
        assert len(confidence["blockers"]) > 0
        assert confidence["grade"] in ("C", "D", "F")


# ============================================================
# TestDegradation
# ============================================================
class TestDegradation:
    """Confidence scoring works when layers are missing or empty."""

    def test_only_structural_layer(self, synthetic_orders):
        from helpers.structural_validator import validate_completeness, validate_primary_key
        from helpers.confidence_scoring import score_confidence

        pk = validate_primary_key(synthetic_orders, ["order_id"])
        comp = validate_completeness(synthetic_orders, ["order_id", "amount"])
        result = score_confidence(
            {"primary_key": pk, "completeness": comp},
            metadata={"row_count": len(synthetic_orders)},
        )
        assert result["score"] > 0
        assert result["grade"] in ("C", "D", "F")
        missing = [n for n, f in result["factors"].items() if f["status"] == "MISSING"]
        assert len(missing) >= 3

    def test_only_simpsons_layer(self, no_paradox_data):
        from helpers.simpsons_paradox import check_simpsons_paradox
        from helpers.confidence_scoring import score_confidence

        sp = check_simpsons_paradox(
            no_paradox_data, metric_column="admitted",
            segment_column="department", comparison_column="group",
        )
        result = score_confidence({"simpsons": sp})
        assert result["score"] > 0
        assert result["grade"] in ("C", "D", "F")

    def test_empty_validation_results(self):
        from helpers.confidence_scoring import score_confidence
        result = score_confidence({})
        assert result["score"] == 0
        assert result["grade"] == "F"
        assert len(result["blockers"]) > 0

    def test_none_metadata(self, synthetic_orders):
        from helpers.structural_validator import validate_primary_key
        from helpers.confidence_scoring import score_confidence

        pk = validate_primary_key(synthetic_orders, ["order_id"])
        result = score_confidence({"primary_key": pk}, metadata=None)
        assert isinstance(result["score"], int)
        assert result["factors"]["sample_size"]["status"] == "MISSING"


# ============================================================
# TestConfigDriven
# ============================================================
class TestConfigDriven:
    """Config dicts control which checks execute in orchestrators."""

    def test_structural_empty_config_uses_defaults(self, synthetic_orders):
        from helpers.structural_validator import run_structural_checks
        result = run_structural_checks(synthetic_orders, config={})
        assert result["checks_run"] == 3
        for key in ("schema", "completeness", "row_count"):
            assert key in result["details"]

    def test_structural_only_pk(self, synthetic_orders):
        from helpers.structural_validator import run_structural_checks
        result = run_structural_checks(synthetic_orders, config={"primary_key": ["order_id"]})
        assert result["checks_run"] == 1
        assert "primary_key" in result["details"]
        assert "schema" not in result["details"]

    def test_logical_no_checks_when_empty_config(self):
        from helpers.logical_validator import run_logical_checks
        result = run_logical_checks(detail_df=pd.DataFrame({"a": [1, 2, 3]}), config={})
        assert result["checks_run"] == 0
        assert result["ok"] is False

    def test_logical_only_trend(self):
        from helpers.logical_validator import run_logical_checks
        result = run_logical_checks(
            detail_df=None, config={"trend_values": [10, 11, 12, 13, 14, 15, 16]},
        )
        assert result["checks_run"] == 1
        assert "trend_consistency" in result["results"]
        assert result["results"]["trend_consistency"]["ok"] is True

    def test_business_rules_only_ranges(self, synthetic_orders):
        from helpers.business_rules import validate_business_rules
        result = validate_business_rules(synthetic_orders, {
            "ranges": [{"column": "amount", "min": 0, "max": 999999, "label": "amt"}],
        })
        assert "ranges" in result["results"]
        assert len(result["results"]) == 1
        assert result["ok"] is True
