"""
End-to-end integration test: Full validation pipeline on synthetic data.

Tests the complete chain:
1. Layer 1: Structural validation (schema, PK, RI, completeness)
2. Layer 2: Logical validation (aggregation, segment, temporal, trend)
3. Layer 3: Business rules (ranges, rates, YoY change)
4. Layer 4: Simpson's Paradox scan
5. Confidence scoring synthesis (7-factor -> score/grade/badge)
6. Lineage tracking (record -> chain -> save/load)

All tests use synthetic fixtures from conftest.py -- no external data
dependencies.
"""

import os
import tempfile

import numpy as np
import pandas as pd
import pytest


# ============================================================
# Layer 1: Structural Validation
# ============================================================

class TestStructuralValidation:
    """Layer 1: Schema, PK, RI, completeness on synthetic data."""

    def test_schema_passes_clean_data(self, synthetic_orders):
        from helpers.structural_validator import validate_schema
        result = validate_schema(
            synthetic_orders,
            expected_columns=["order_id", "user_id", "order_date",
                              "amount", "status", "category"],
        )
        assert result["valid"] is True
        assert result["severity"] == "PASS"
        assert len(result["missing_columns"]) == 0

    def test_schema_detects_missing_columns(self, synthetic_orders):
        from helpers.structural_validator import validate_schema
        result = validate_schema(
            synthetic_orders,
            expected_columns=["order_id", "nonexistent_col"],
        )
        assert result["valid"] is False
        assert result["severity"] == "BLOCKER"
        assert "nonexistent_col" in result["missing_columns"]

    def test_schema_detects_dtype_mismatch(self, synthetic_orders):
        from helpers.structural_validator import validate_schema
        result = validate_schema(
            synthetic_orders,
            expected_dtypes={"amount": "object"},
        )
        assert len(result["dtype_mismatches"]) > 0
        assert result["severity"] == "WARNING"

    def test_primary_key_valid_clean_data(self, synthetic_orders):
        from helpers.structural_validator import validate_primary_key
        result = validate_primary_key(synthetic_orders, key_columns=["order_id"])
        assert result["valid"] is True
        assert result["severity"] == "PASS"
        assert result["null_count"] == 0
        assert result["duplicate_count"] == 0

    def test_primary_key_detects_duplicates(self, dirty_orders):
        from helpers.structural_validator import validate_primary_key
        result = validate_primary_key(dirty_orders, key_columns=["order_id"])
        assert result["valid"] is False
        assert result["severity"] == "BLOCKER"
        assert result["duplicate_count"] > 0

    def test_referential_integrity_clean(self, synthetic_users, synthetic_orders):
        from helpers.structural_validator import validate_referential_integrity
        result = validate_referential_integrity(
            parent_df=synthetic_users, child_df=synthetic_orders,
            parent_key="user_id", child_key="user_id",
        )
        assert result["orphan_count"] == 0
        assert result["orphan_rate"] == 0.0
        assert result["severity"] == "PASS"

    def test_referential_integrity_detects_orphans(self, synthetic_users, dirty_orders):
        """dirty_orders has null user_ids which get dropped, but also IDs
        that may exceed the parent range -- validate orphan detection."""
        from helpers.structural_validator import validate_referential_integrity
        # Create a small parent set so orphans are guaranteed
        small_parent = synthetic_users.head(10)
        result = validate_referential_integrity(
            parent_df=small_parent, child_df=dirty_orders,
            parent_key="user_id", child_key="user_id",
        )
        assert result["orphan_count"] > 0
        assert result["severity"] in ("WARNING", "BLOCKER")

    def test_completeness_clean_data(self, synthetic_orders):
        from helpers.structural_validator import validate_completeness
        result = validate_completeness(
            synthetic_orders,
            required_columns=["order_id", "user_id", "order_date", "amount"],
        )
        assert result["overall_severity"] == "PASS"
        for col_info in result["columns"]:
            assert col_info["null_rate"] == 0.0

    def test_completeness_detects_nulls(self, dirty_orders):
        from helpers.structural_validator import validate_completeness
        result = validate_completeness(
            dirty_orders,
            required_columns=["order_id", "user_id", "order_date", "amount"],
        )
        # dirty_orders has 10% null user_ids and 10 null order_dates
        assert result["overall_severity"] in ("WARNING", "BLOCKER")
        user_col = next(c for c in result["columns"] if c["name"] == "user_id")
        assert user_col["null_rate"] > 0


# ============================================================
# Layer 2: Logical Validation
# ============================================================

class TestLogicalValidation:
    """Layer 2: Aggregation, segment, temporal, trend checks."""

    def test_aggregation_consistency_passes(self, synthetic_orders):
        from helpers.logical_validator import validate_aggregation_consistency
        detail = synthetic_orders[["status", "amount"]].copy()
        summary = detail.groupby("status")["amount"].sum().reset_index()
        result = validate_aggregation_consistency(
            detail, summary,
            group_col="status", metric_col="amount", agg="sum",
        )
        assert result["valid"] is True
        assert result["severity"] == "PASS"
        assert len(result["mismatches"]) == 0

    def test_aggregation_consistency_detects_mismatch(self, synthetic_orders):
        from helpers.logical_validator import validate_aggregation_consistency
        detail = synthetic_orders[["status", "amount"]].copy()
        summary = detail.groupby("status")["amount"].sum().reset_index()
        # Corrupt the summary to create mismatch
        summary.iloc[0, summary.columns.get_loc("amount")] *= 2.0
        result = validate_aggregation_consistency(
            detail, summary,
            group_col="status", metric_col="amount", agg="sum",
        )
        assert result["valid"] is False
        assert len(result["mismatches"]) > 0
        assert result["severity"] in ("WARNING", "BLOCKER")

    def test_segment_exhaustiveness_passes(self, synthetic_orders):
        from helpers.logical_validator import validate_segment_exhaustiveness
        working = synthetic_orders.copy()
        working["count"] = 1
        result = validate_segment_exhaustiveness(
            working, segment_col="status", metric_col="count",
        )
        assert result["severity"] == "PASS"
        assert result["missing_rows"] == 0
        assert result["diff_pct"] < 0.001

    def test_segment_exhaustiveness_detects_nulls(self):
        """DataFrame with null segment values should trigger BLOCKER."""
        from helpers.logical_validator import validate_segment_exhaustiveness
        df = pd.DataFrame({
            "segment": ["A", "B", None, "A", None],
            "value": [10, 20, 30, 40, 50],
        })
        result = validate_segment_exhaustiveness(df, "segment", "value")
        assert result["missing_rows"] == 2
        assert result["severity"] == "BLOCKER"

    def test_temporal_consistency_clean_daily(self, synthetic_orders):
        from helpers.logical_validator import validate_temporal_consistency
        # Build a continuous daily series from synthetic_orders
        orders_copy = synthetic_orders.copy()
        orders_copy["date"] = orders_copy["order_date"].dt.date
        daily = (
            orders_copy.groupby("date")
            .agg(order_count=("order_id", "count"))
            .reset_index()
            .rename(columns={"date": "order_date"})
        )
        result = validate_temporal_consistency(
            daily, date_col="order_date", metric_col="order_count",
            expected_freq="D",
        )
        assert result["severity"] in ("PASS", "WARNING")
        assert len(result["duplicate_dates"]) == 0

    def test_temporal_consistency_detects_gaps(self):
        """Series with missing dates should be detected."""
        from helpers.logical_validator import validate_temporal_consistency
        # Create a series with a gap
        dates = pd.date_range("2024-01-01", "2024-01-10", freq="D").tolist()
        dates.pop(5)  # Remove Jan 6
        df = pd.DataFrame({
            "date": dates,
            "metric": range(len(dates)),
        })
        result = validate_temporal_consistency(
            df, date_col="date", metric_col="metric", expected_freq="D",
        )
        assert len(result["missing_dates"]) >= 1
        assert result["severity"] in ("WARNING", "BLOCKER")

    def test_trend_continuity_smooth(self):
        from helpers.logical_validator import validate_trend_continuity
        # Smooth series with small variation
        series = pd.Series([100, 102, 105, 103, 107, 110, 108, 112])
        result = validate_trend_continuity(series, max_gap_pct=0.5)
        assert result["valid"] is True
        assert result["severity"] == "PASS"
        assert len(result["breaks"]) == 0

    def test_trend_continuity_detects_breaks(self):
        from helpers.logical_validator import validate_trend_continuity
        # Series with a sudden 10x jump
        series = pd.Series([100, 102, 105, 1050, 108, 112])
        result = validate_trend_continuity(series, max_gap_pct=0.5)
        assert result["valid"] is False
        assert len(result["breaks"]) > 0


# ============================================================
# Layer 3: Business Rules
# ============================================================

class TestBusinessRules:
    """Layer 3: Range validation, rate validation, YoY change."""

    def test_price_ranges_clean(self, synthetic_products):
        from helpers.business_rules import validate_ranges
        rules = [
            {"column": "price", "min": 0, "max": 500, "name": "product_price"},
        ]
        result = validate_ranges(synthetic_products, rules)
        assert result["valid"] is True
        for v in result["violations"]:
            assert v["severity"] == "PASS"
            assert v["out_of_range_count"] == 0

    def test_amount_ranges_detect_violations(self, dirty_orders):
        from helpers.business_rules import validate_ranges
        rules = [
            {"column": "amount", "min": 0, "max": 10000,
             "name": "order_amount"},
        ]
        result = validate_ranges(dirty_orders, rules)
        # dirty_orders has a negative amount (-10.0) and an extreme outlier (1e7)
        violation = result["violations"][0]
        assert violation["out_of_range_count"] > 0
        assert violation["min_seen"] < 0

    def test_rate_validation_clean(self, synthetic_orders):
        from helpers.business_rules import validate_rates
        # Create a rate dataset: each row is a "session" with 0/1 conversion
        working = synthetic_orders.copy()
        working["converted"] = (working["status"] == "completed").astype(int)
        working["session_count"] = 1
        result = validate_rates(
            working, numerator_col="converted",
            denominator_col="session_count",
            expected_range=(0, 1), name="conversion_rate",
        )
        assert result["severity"] == "PASS"
        assert result["rate_stats"]["min"] >= 0
        assert result["rate_stats"]["max"] <= 1

    def test_rate_validation_flags_zero_denominator(self):
        from helpers.business_rules import validate_rates
        df = pd.DataFrame({
            "numerator": [5, 3, 0, 2],
            "denominator": [10, 0, 5, 8],
        })
        result = validate_rates(
            df, numerator_col="numerator",
            denominator_col="denominator",
            expected_range=(0, 1), name="test_rate",
        )
        assert result["zero_denominator_count"] == 1
        assert result["severity"] in ("WARNING", "BLOCKER")

    def test_yoy_change_plausible(self):
        from helpers.business_rules import validate_yoy_change
        result = validate_yoy_change(120, 100, max_change_pct=2.0,
                                     metric_name="revenue")
        assert result["valid"] is True
        assert result["severity"] == "PASS"
        assert result["direction"] == "up"
        assert abs(result["change_pct"] - 0.2) < 0.01

    def test_yoy_change_implausible(self):
        from helpers.business_rules import validate_yoy_change
        result = validate_yoy_change(600, 100, max_change_pct=2.0,
                                     metric_name="revenue")
        assert result["valid"] is False
        assert result["severity"] == "BLOCKER"
        assert result["change_pct"] == 5.0

    def test_yoy_change_decline(self):
        from helpers.business_rules import validate_yoy_change
        result = validate_yoy_change(80, 100, max_change_pct=2.0,
                                     metric_name="revenue")
        assert result["direction"] == "down"
        assert result["severity"] == "PASS"


# ============================================================
# Layer 4: Simpson's Paradox
# ============================================================

class TestSimpsonsParadox:
    """Layer 4: Simpson's Paradox detection using dedicated fixtures."""

    def test_detects_paradox(self, simpsons_paradox_data):
        from helpers.simpsons_paradox import check_simpsons_paradox
        result = check_simpsons_paradox(
            simpsons_paradox_data,
            metric_col="admitted",
            group_col="group",
            segment_col="department",
        )
        assert result["paradox_detected"] is True
        assert result["severity"] == "BLOCKER"
        assert len(result["reversal_segments"]) > 0
        assert "explanation" in result

    def test_no_paradox_consistent_data(self, no_paradox_data):
        from helpers.simpsons_paradox import check_simpsons_paradox
        result = check_simpsons_paradox(
            no_paradox_data,
            metric_col="admitted",
            group_col="group",
            segment_col="department",
        )
        assert result["paradox_detected"] is False
        assert result["severity"] in ("PASS", "INFO")

    def test_scan_dimensions_multiple(self, synthetic_orders, synthetic_users):
        from helpers.simpsons_paradox import scan_dimensions
        merged = synthetic_orders.merge(
            synthetic_users[["user_id", "device", "country"]],
            on="user_id", how="left",
        )
        result = scan_dimensions(
            merged, metric_col="amount", group_col="status",
            candidate_segments=["device", "country"],
        )
        assert result["scanned"] == 2
        assert isinstance(result["paradoxes_found"], int)
        assert len(result["results"]) == 2
        for r in result["results"]:
            assert "paradox_detected" in r
            assert "aggregate_direction" in r
            assert "severity" in r

    def test_scan_dimensions_missing_column(self, synthetic_orders):
        from helpers.simpsons_paradox import scan_dimensions
        result = scan_dimensions(
            synthetic_orders, metric_col="amount", group_col="status",
            candidate_segments=["nonexistent_col"],
        )
        assert result["scanned"] == 1
        assert result["results"][0]["severity"] == "WARNING"


# ============================================================
# Confidence Scoring (Synthesis)
# ============================================================

class TestConfidenceScoring:
    """Confidence scoring on synthetic validation results."""

    def test_full_pipeline_confidence_clean_data(
        self, synthetic_users, synthetic_orders, synthetic_products,
    ):
        """Run all 4 layers on clean data and compute confidence score."""
        from helpers.structural_validator import (
            validate_schema, validate_primary_key,
            validate_referential_integrity, validate_completeness,
        )
        from helpers.logical_validator import (
            validate_aggregation_consistency,
            validate_segment_exhaustiveness,
        )
        from helpers.business_rules import validate_ranges
        from helpers.simpsons_paradox import scan_dimensions
        from helpers.confidence_scoring import (
            score_confidence, format_confidence_badge,
        )

        # --- Layer 1: Structural ---
        schema_result = validate_schema(
            synthetic_orders,
            expected_columns=["order_id", "user_id", "order_date",
                              "amount", "status"],
        )
        pk_result = validate_primary_key(synthetic_orders, ["order_id"])
        ri_result = validate_referential_integrity(
            synthetic_users, synthetic_orders, "user_id", "user_id",
        )
        completeness_result = validate_completeness(
            synthetic_orders,
            required_columns=["order_id", "user_id", "order_date", "amount"],
        )

        # --- Layer 2: Logical ---
        detail = synthetic_orders[["status", "amount"]].copy()
        summary = detail.groupby("status")["amount"].sum().reset_index()
        agg_result = validate_aggregation_consistency(
            detail, summary, "status", "amount",
        )
        working = synthetic_orders.copy()
        working["count"] = 1
        seg_result = validate_segment_exhaustiveness(
            working, "status", "count",
        )

        # --- Layer 3: Business rules ---
        range_result = validate_ranges(synthetic_orders, [
            {"column": "amount", "min": 0, "max": 50000,
             "name": "order_amount"},
        ])

        # --- Layer 4: Simpson's ---
        merged = synthetic_orders.merge(
            synthetic_users[["user_id", "device", "country"]],
            on="user_id", how="left",
        )
        simpsons_result = scan_dimensions(
            merged, "amount", "status",
            ["device", "country"],
        )

        # --- Synthesize ---
        validation_results = {
            "schema": schema_result,
            "primary_key": pk_result,
            "referential_integrity": ri_result,
            "completeness": completeness_result,
            "aggregation": agg_result,
            "segment_exhaustiveness": seg_result,
            "ranges": range_result,
            "simpsons": simpsons_result,
        }
        confidence = score_confidence(
            validation_results,
            metadata={"row_count": len(synthetic_orders)},
        )

        # --- Assertions ---
        assert isinstance(confidence["score"], int)
        assert 0 <= confidence["score"] <= 100
        assert confidence["grade"] in ("A", "B", "C", "D", "F")
        assert isinstance(confidence["factors"], dict)
        assert len(confidence["factors"]) == 9
        assert isinstance(confidence["blockers"], list)
        assert isinstance(confidence["interpretation"], str)
        assert isinstance(confidence["recommendation"], str)

        # Clean synthetic data should achieve a reasonable grade
        assert confidence["grade"] in ("A", "B", "C"), \
            f"Expected passing grade, got {confidence['grade']}: {confidence['interpretation']}"

        # --- Badge formatting ---
        badge = format_confidence_badge(confidence)
        assert "Confidence:" in badge
        assert confidence["grade"] in badge
        assert str(confidence["score"]) in badge

    def test_empty_results_returns_f(self):
        from helpers.confidence_scoring import score_confidence
        result = score_confidence({})
        assert result["score"] == 0
        assert result["grade"] == "F"

    def test_partial_results_caps_at_c(self, synthetic_orders):
        """With only one validator layer, grade should be capped at C."""
        from helpers.structural_validator import validate_primary_key
        from helpers.confidence_scoring import score_confidence

        pk = validate_primary_key(synthetic_orders, ["order_id"])
        result = score_confidence(
            {"primary_key": pk},
            metadata={"row_count": len(synthetic_orders)},
        )
        assert result["grade"] in ("C", "D", "F")

    def test_dirty_data_lowers_confidence(self, dirty_orders, synthetic_users):
        """Dirty data should produce a lower confidence score."""
        from helpers.structural_validator import (
            validate_primary_key, validate_completeness,
            validate_referential_integrity,
        )
        from helpers.business_rules import validate_ranges
        from helpers.confidence_scoring import score_confidence

        pk = validate_primary_key(dirty_orders, ["order_id"])
        comp = validate_completeness(
            dirty_orders, ["order_id", "user_id", "order_date", "amount"],
        )
        ri = validate_referential_integrity(
            synthetic_users, dirty_orders, "user_id", "user_id",
        )
        ranges = validate_ranges(dirty_orders, [
            {"column": "amount", "min": 0, "max": 10000, "name": "order_amount"},
        ])

        result = score_confidence(
            {
                "primary_key": pk,
                "completeness": comp,
                "referential_integrity": ri,
                "ranges": ranges,
            },
            metadata={"row_count": len(dirty_orders)},
        )
        # Dirty data has PK issues and null columns -> should have blockers
        assert len(result["blockers"]) > 0
        assert result["grade"] in ("C", "D", "F")

    def test_merge_confidence_scores(self, synthetic_users, synthetic_orders):
        """Test merging scores from two analysis steps."""
        from helpers.structural_validator import (
            validate_primary_key, validate_completeness,
        )
        from helpers.confidence_scoring import (
            score_confidence, merge_confidence_scores,
        )

        # Step 1: orders validation
        pk1 = validate_primary_key(synthetic_orders, ["order_id"])
        comp1 = validate_completeness(synthetic_orders, ["order_id", "user_id"])
        s1 = score_confidence(
            {"primary_key": pk1, "completeness": comp1},
            metadata={"row_count": len(synthetic_orders)},
        )

        # Step 2: users validation
        pk2 = validate_primary_key(synthetic_users, ["user_id"])
        comp2 = validate_completeness(synthetic_users, ["user_id", "signup_date"])
        s2 = score_confidence(
            {"primary_key": pk2, "completeness": comp2},
            metadata={"row_count": len(synthetic_users)},
        )

        merged = merge_confidence_scores([s1, s2])
        assert isinstance(merged["score"], int)
        assert 0 <= merged["score"] <= 100
        assert merged["grade"] in ("A", "B", "C", "D", "F")


# ============================================================
# Lineage Tracking
# ============================================================

class TestLineageTracking:
    """Lineage tracking integration with synthetic pipeline."""

    def test_pipeline_lineage_chain(self):
        """Simulate a 3-step pipeline and verify lineage chain."""
        from helpers.lineage_tracker import LineageTracker

        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = LineageTracker(output_dir=tmpdir)

            # Step 1: Data Explorer
            tracker.record(
                step=4, agent="data-explorer",
                inputs=["data/synthetic/orders.csv",
                        "data/synthetic/users.csv"],
                outputs=["working/data_inventory.md"],
                metadata={"tables_profiled": 2},
            )

            # Step 2: Descriptive Analytics
            tracker.record(
                step=5, agent="descriptive-analytics",
                inputs=["working/data_inventory.md",
                        "data/synthetic/orders.csv"],
                outputs=["working/analysis_report.md"],
                metadata={"tables_used": 2, "findings_count": 5},
            )

            # Step 3: Validation
            tracker.record(
                step=7, agent="validation",
                inputs=["working/analysis_report.md"],
                outputs=["working/validation_report.md"],
                metadata={"layers_run": 4, "confidence_grade": "B"},
            )

            # --- Verify chain ---
            lineage = tracker.get_lineage()
            assert len(lineage) == 3

            # Step 2 should have Step 1 as parent
            assert lineage[1]["parent_ids"] == ["lin_001"]

            # Step 3 should have Step 2 as parent
            assert lineage[2]["parent_ids"] == ["lin_002"]

            # Trace ancestry of the validation report
            chain = tracker.get_lineage_for_output(
                "working/validation_report.md"
            )
            assert len(chain) == 3
            agents_in_chain = [e["agent"] for e in chain]
            assert "validation" in agents_in_chain
            assert "descriptive-analytics" in agents_in_chain
            assert "data-explorer" in agents_in_chain

    def test_lineage_save_load_roundtrip(self):
        """Save lineage to disk and reload it."""
        from helpers.lineage_tracker import LineageTracker

        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = LineageTracker(output_dir=tmpdir)
            tracker.record(
                step=1, agent="test-agent",
                inputs=["input.csv"], outputs=["output.md"],
            )
            tracker.save()

            assert os.path.isfile(os.path.join(tmpdir, "lineage.json"))

            tracker2 = LineageTracker(output_dir=tmpdir)
            tracker2.load()
            loaded = tracker2.get_lineage()
            assert len(loaded) == 1
            assert loaded[0]["agent"] == "test-agent"
            assert loaded[0]["step"] == 1

    def test_singleton_track_function(self):
        """Test the module-level track() convenience function."""
        from helpers.lineage_tracker import track, get_tracker

        # Reset singleton
        import helpers.lineage_tracker as lt
        lt._singleton_tracker = None

        track(step=1, agent="singleton-test",
              inputs=["a.csv"], outputs=["b.md"])

        tracker = get_tracker()
        entries = tracker.get_lineage()
        assert len(entries) >= 1
        last = entries[-1]
        assert last["agent"] == "singleton-test"

        # Cleanup
        tracker.clear()


# ============================================================
# Full Pipeline Chain (capstone)
# ============================================================

class TestFullPipelineChain:
    """Capstone: Run the entire validation pipeline end-to-end."""

    @pytest.mark.slow
    def test_capstone_e2e(
        self, synthetic_users, synthetic_orders, synthetic_products,
        simpsons_paradox_data,
    ):
        """Full chain: 4 layers -> confidence -> lineage, all on synthetic data."""
        from helpers.structural_validator import (
            validate_schema, validate_primary_key,
            validate_referential_integrity, validate_completeness,
        )
        from helpers.logical_validator import (
            validate_aggregation_consistency,
            validate_segment_exhaustiveness,
            validate_temporal_consistency,
        )
        from helpers.business_rules import validate_ranges, validate_rates
        from helpers.simpsons_paradox import scan_dimensions
        from helpers.confidence_scoring import (
            score_confidence, format_confidence_badge,
        )
        from helpers.lineage_tracker import LineageTracker

        # === LAYER 1: Structural ===
        schema = validate_schema(
            synthetic_orders,
            expected_columns=["order_id", "user_id", "order_date",
                              "amount", "status"],
        )
        pk = validate_primary_key(synthetic_orders, ["order_id"])
        ri = validate_referential_integrity(
            synthetic_users, synthetic_orders, "user_id", "user_id",
        )
        comp = validate_completeness(
            synthetic_orders, ["order_id", "user_id", "order_date", "amount"],
        )

        # === LAYER 2: Logical ===
        detail = synthetic_orders[["status", "amount"]].copy()
        summary = detail.groupby("status")["amount"].sum().reset_index()
        agg = validate_aggregation_consistency(
            detail, summary, "status", "amount",
        )

        working = synthetic_orders.copy()
        working["count"] = 1
        seg = validate_segment_exhaustiveness(working, "status", "count")

        orders_copy = synthetic_orders.copy()
        orders_copy["date"] = orders_copy["order_date"].dt.date
        daily = (
            orders_copy.groupby("date")
            .agg(order_count=("order_id", "count"))
            .reset_index()
            .rename(columns={"date": "order_date"})
        )
        temporal = validate_temporal_consistency(
            daily, "order_date", "order_count", expected_freq="D",
        )

        # === LAYER 3: Business Rules ===
        ranges = validate_ranges(synthetic_orders, [
            {"column": "amount", "min": 0, "max": 50000,
             "name": "order_amount"},
        ])

        # === LAYER 4: Simpson's ===
        merged = synthetic_orders.merge(
            synthetic_users[["user_id", "device", "country"]],
            on="user_id", how="left",
        )
        simpsons = scan_dimensions(
            merged, "amount", "status",
            ["device", "country"],
        )

        # === CONFIDENCE SCORING ===
        validation_results = {
            "schema": schema,
            "primary_key": pk,
            "referential_integrity": ri,
            "completeness": comp,
            "aggregation": agg,
            "segment_exhaustiveness": seg,
            "temporal": temporal,
            "ranges": ranges,
            "simpsons": simpsons,
        }
        confidence = score_confidence(
            validation_results,
            metadata={"row_count": len(synthetic_orders)},
        )

        # Score is computed and reasonable
        assert isinstance(confidence["score"], int)
        assert confidence["score"] > 0, "Score should be >0 for clean data"
        assert confidence["grade"] in ("A", "B", "C")

        # Badge is formatted
        badge = format_confidence_badge(confidence)
        assert len(badge) > 0

        # All 7 factors are present
        assert len(confidence["factors"]) == 9
        for factor_name, factor in confidence["factors"].items():
            assert "score" in factor
            assert "max" in factor
            assert "status" in factor
            assert "detail" in factor

        # === LINEAGE TRACKING ===
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = LineageTracker(output_dir=tmpdir)

            tracker.record(
                step=4, agent="data-explorer",
                inputs=["data/synthetic/orders.csv"],
                outputs=["working/data_inventory.md"],
                metadata={"tables_profiled": 3},
            )
            tracker.record(
                step=5, agent="descriptive-analytics",
                inputs=["working/data_inventory.md"],
                outputs=["working/analysis_report.md"],
                metadata={"findings": 3},
            )
            tracker.record(
                step=7, agent="validation",
                inputs=["working/analysis_report.md"],
                outputs=["working/validation_report.md"],
                metadata={
                    "confidence_score": confidence["score"],
                    "confidence_grade": confidence["grade"],
                },
            )

            tracker.save()

            # Reload and verify
            tracker2 = LineageTracker(output_dir=tmpdir)
            tracker2.load()
            chain = tracker2.get_lineage_for_output(
                "working/validation_report.md"
            )
            assert len(chain) == 3
            assert chain[0]["agent"] == "validation"

            # Metadata carries through
            assert chain[0]["metadata"]["confidence_score"] == confidence["score"]
