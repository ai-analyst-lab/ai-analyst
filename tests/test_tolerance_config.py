"""Tests for helpers.tolerance_config — warehouse-specific tolerances."""

import pytest

from helpers.tolerance_config import (
    BASE_TOLERANCES,
    ToleranceConfig,
    detect_cost_sensitivity,
    get_query_budget,
    QUERY_BUDGETS,
)


# =====================================================================
# ToleranceConfig basics
# =====================================================================

class TestToleranceConfig:
    def test_default_adjustments_are_empty(self):
        config = ToleranceConfig()
        assert config.adjustments == {}

    def test_get_adjustment_unknown_returns_zero(self):
        config = ToleranceConfig()
        assert config.get_adjustment("unknown_check") == 0.0

    def test_effective_tolerance_base_only(self):
        config = ToleranceConfig()
        assert config.effective_tolerance("parts_to_whole") == BASE_TOLERANCES["parts_to_whole"]

    def test_effective_tolerance_with_adjustment(self):
        config = ToleranceConfig(adjustments={"distinct_count": 0.02})
        expected = BASE_TOLERANCES["distinct_count"] + 0.02
        assert config.effective_tolerance("distinct_count") == expected

    def test_merge_with_base_defaults(self):
        config = ToleranceConfig(adjustments={"row_count": 0.001})
        merged = config.merge_with_base()
        assert merged["row_count"] == BASE_TOLERANCES["row_count"] + 0.001

    def test_merge_with_custom_base(self):
        config = ToleranceConfig(adjustments={"custom": 0.01})
        merged = config.merge_with_base({"custom": 0.05})
        assert merged["custom"] == pytest.approx(0.06)


# =====================================================================
# Factory methods
# =====================================================================

class TestFactoryMethods:
    def test_snowflake_has_distinct_count_adjustment(self):
        config = ToleranceConfig.for_connection_type("snowflake")
        assert config.connection_type == "snowflake"
        assert config.get_adjustment("distinct_count") == 0.02
        assert "distinct_count" in config.approximate_checks

    def test_bigquery_has_row_count_adjustment(self):
        config = ToleranceConfig.for_connection_type("bigquery")
        assert config.get_adjustment("row_count") == 0.001

    def test_postgres_all_zeros(self):
        config = ToleranceConfig.for_connection_type("postgres")
        for check_type in BASE_TOLERANCES:
            assert config.get_adjustment(check_type) == 0.0

    def test_csv_all_zeros(self):
        config = ToleranceConfig.for_connection_type("csv")
        assert config.adjustments == {}

    def test_duckdb_maps_to_csv(self):
        config = ToleranceConfig.for_connection_type("duckdb")
        assert config.adjustments == {}

    def test_motherduck_maps_to_csv(self):
        config = ToleranceConfig.for_connection_type("motherduck")
        assert config.adjustments == {}

    def test_unknown_type_falls_back_to_csv(self):
        config = ToleranceConfig.for_connection_type("oracle")
        assert config.adjustments == {}

    def test_cost_sensitivity_passthrough(self):
        config = ToleranceConfig.for_connection_type("snowflake", cost_sensitivity="high")
        assert config.cost_sensitivity == "high"


# =====================================================================
# Cost sensitivity detection
# =====================================================================

class TestCostSensitivity:
    def test_no_metadata_returns_normal(self):
        assert detect_cost_sensitivity("snowflake") == "normal"

    def test_snowflake_trial_returns_high(self):
        meta = {"edition": "standard", "is_trial": True}
        assert detect_cost_sensitivity("snowflake", meta) == "high"

    def test_snowflake_low_credits_returns_high(self):
        meta = {"credits_remaining": 5}
        assert detect_cost_sensitivity("snowflake", meta) == "high"

    def test_bigquery_sandbox_returns_high(self):
        meta = {"is_sandbox": True}
        assert detect_cost_sensitivity("bigquery", meta) == "high"

    def test_normal_metadata_returns_normal(self):
        meta = {"edition": "enterprise", "credits_remaining": 1000}
        assert detect_cost_sensitivity("snowflake", meta) == "normal"


# =====================================================================
# Query budgets
# =====================================================================

class TestQueryBudgets:
    def test_tier1_always_zero(self):
        for sensitivity in ("low", "normal", "high"):
            assert get_query_budget(1, sensitivity) == 0

    def test_tier2_normal(self):
        assert get_query_budget(2, "normal") == 20

    def test_tier3_high_sensitivity_limited(self):
        assert get_query_budget(3, "high") == 10

    def test_unknown_tier_returns_zero(self):
        assert get_query_budget(99) == 0
