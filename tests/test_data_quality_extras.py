"""Tests for helpers.data_quality_extras — null concentration and outlier detection."""

import pytest
import numpy as np
import pandas as pd

from helpers.data_quality_extras import (
    check_null_concentration,
    check_outliers,
    safe_check_outliers,
)


# =====================================================================
# Null concentration
# =====================================================================

class TestCheckNullConcentration:
    def test_no_nulls_all_pass(self, synthetic_orders):
        results = check_null_concentration(synthetic_orders)
        assert all(r["status"] == "PASS" for r in results)
        assert all(r["null_pct"] == 0.0 for r in results)

    def test_high_null_column_warns(self):
        df = pd.DataFrame({
            "a": [1, 2, 3, 4, 5],
            "b": [None, None, None, 4, 5],  # 60% null
        })
        results = check_null_concentration(df)
        b_result = next(r for r in results if r["column"] == "b")
        assert b_result["status"] == "WARN"
        assert b_result["null_pct"] == 0.6

    def test_nearly_empty_column_fails(self):
        df = pd.DataFrame({
            "a": [None] * 96 + [1, 2, 3, 4],
        })
        results = check_null_concentration(df)
        assert results[0]["status"] == "FAIL"
        assert results[0]["null_pct"] == 0.96

    def test_empty_dataframe_returns_empty(self):
        df = pd.DataFrame({"a": pd.Series(dtype=float)})
        results = check_null_concentration(df)
        assert results == []

    def test_custom_thresholds(self):
        df = pd.DataFrame({"a": [None, None, 3, 4, 5]})  # 40% null
        # Default warn_threshold=0.5 means 40% should PASS
        results_default = check_null_concentration(df)
        assert results_default[0]["status"] == "PASS"
        # With lower threshold, should WARN
        results_custom = check_null_concentration(df, warn_threshold=0.3)
        assert results_custom[0]["status"] == "WARN"


# =====================================================================
# Outlier detection — IQR method
# =====================================================================

class TestCheckOutliersIQR:
    def test_normal_data_no_outliers(self):
        np.random.seed(42)
        series = pd.Series(np.random.normal(100, 10, 1000))
        result = check_outliers(series, method="iqr")
        assert result["method"] == "iqr"
        assert result["status"] == "PASS"
        assert result["n_total"] == 1000

    def test_outlier_detected(self):
        data = list(range(100)) + [10000]
        series = pd.Series(data)
        result = check_outliers(series, method="iqr")
        assert result["n_outliers"] >= 1
        assert 10000 in [series[i] for i in result["outlier_indices"]]

    def test_too_few_values_warns(self):
        series = pd.Series([1, 2, 3])
        result = check_outliers(series, method="iqr")
        assert result["status"] == "WARN"
        assert "Too few" in result["detail"]

    def test_all_null_series_warns(self):
        series = pd.Series([None, None, None])
        result = check_outliers(series, method="iqr")
        assert result["status"] == "WARN"

    def test_bounds_returned(self):
        series = pd.Series(range(100))
        result = check_outliers(series, method="iqr")
        assert result["bounds"] is not None
        assert "lower" in result["bounds"]
        assert "upper" in result["bounds"]

    def test_custom_multiplier(self):
        data = list(range(100)) + [200]
        series = pd.Series(data)
        # Tight multiplier catches more
        result_tight = check_outliers(series, method="iqr", iqr_multiplier=0.5)
        result_loose = check_outliers(series, method="iqr", iqr_multiplier=3.0)
        assert result_tight["n_outliers"] >= result_loose["n_outliers"]


# =====================================================================
# Outlier detection — z-score method
# =====================================================================

class TestCheckOutliersZScore:
    def test_normal_data(self):
        np.random.seed(42)
        series = pd.Series(np.random.normal(0, 1, 1000))
        result = check_outliers(series, method="zscore")
        assert result["method"] == "zscore"
        assert result["status"] == "PASS"

    def test_zero_variance_passes(self):
        series = pd.Series([5.0] * 100)
        result = check_outliers(series, method="zscore")
        assert result["status"] == "PASS"
        assert "Zero variance" in result["detail"]

    def test_custom_threshold(self):
        np.random.seed(42)
        series = pd.Series(np.random.normal(0, 1, 1000))
        result_tight = check_outliers(series, method="zscore", z_threshold=1.0)
        result_loose = check_outliers(series, method="zscore", z_threshold=5.0)
        assert result_tight["n_outliers"] >= result_loose["n_outliers"]


# =====================================================================
# Unknown method
# =====================================================================

class TestCheckOutliersUnknown:
    def test_unknown_method_raises(self):
        series = pd.Series(range(100))
        with pytest.raises(ValueError, match="Unknown method"):
            check_outliers(series, method="invalid")


# =====================================================================
# Safe wrapper
# =====================================================================

class TestSafeCheckOutliers:
    def test_returns_result_on_success(self):
        series = pd.Series(range(100))
        result = safe_check_outliers(series)
        assert result["status"] in ("PASS", "WARN", "FAIL")

    def test_returns_warn_on_error(self):
        result = safe_check_outliers("not a series")
        assert result["status"] == "WARN"
        assert "Could not check" in result["detail"]

    def test_preserves_method_kwarg(self):
        series = pd.Series(range(100))
        result = safe_check_outliers(series, method="zscore")
        assert result["method"] == "zscore"
