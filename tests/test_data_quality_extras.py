"""Tests for helpers.validation.data_quality_extras — null concentration and outlier detection."""

import pytest
import numpy as np
import pandas as pd

from helpers.validation.data_quality_extras import (
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
            "b": [None, None, 3, 4, 5],  # 40% null — SEVERE WARNING band
        })
        results = check_null_concentration(df)
        b_result = next(r for r in results if r["column"] == "b")
        assert b_result["status"] == "WARN"
        assert b_result["severity"] == "SEVERE WARNING"
        assert b_result["null_pct"] == 0.4

    def test_over_half_null_is_blocker(self):
        df = pd.DataFrame({
            "b": [None, None, None, 4, 5],  # 60% null — BLOCKER band
        })
        results = check_null_concentration(df)
        assert results[0]["status"] == "FAIL"
        assert results[0]["severity"] == "BLOCKER"
        assert results[0]["null_pct"] == 0.6

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
        df = pd.DataFrame({"a": [None, 2, 3, 4, 5] * 5})  # 20% null
        # Default warn_threshold=0.05 puts 20% in the WARNING band
        results_default = check_null_concentration(df)
        assert results_default[0]["status"] == "WARN"
        assert results_default[0]["severity"] == "WARNING"
        # A tightened fail_threshold turns the same column into a FAIL
        results_custom = check_null_concentration(df, fail_threshold=0.1)
        assert results_custom[0]["status"] == "FAIL"
        # A loosened warn_threshold lets it PASS the coarse gate, but the
        # canonical severity table still labels the band
        results_loose = check_null_concentration(df, warn_threshold=0.25)
        assert results_loose[0]["status"] == "PASS"


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


# ---------------------------------------------------------------------------
# sanity_check / anomaly_scan / freshness_check (moved from the
# data-quality-check skill)
# ---------------------------------------------------------------------------

from datetime import date

from helpers.validation.data_quality_extras import (  # noqa: E402
    anomaly_scan,
    freshness_check,
    sanity_check,
)


class TestSanityCheck:
    def test_normal_column_has_stats_and_no_issues(self):
        df = pd.DataFrame({"revenue": [10.0, 12.0, 11.0, 13.0, 12.5, 11.5]})
        stats, issues = sanity_check(df, "revenue")
        assert set(stats) == {"mean", "median", "std", "min", "max", "p1", "p99", "skew"}
        assert stats["min"] == 10.0 and stats["max"] == 13.0
        assert issues == []

    def test_bounded_rate_outside_unit_interval_is_blocker(self):
        df = pd.DataFrame({"conversion_rate": [0.1, 0.5, 1.4, 0.3]})
        _, issues = sanity_check(df, "conversion_rate")
        assert issues and issues[0][0] == "BLOCKER"
        assert "outside [0,1]" in issues[0][1]

    def test_highly_skewed_column_is_warning(self):
        df = pd.DataFrame({"amount": [1.0] * 30 + [10_000.0]})
        _, issues = sanity_check(df, "amount")
        assert ("WARNING" in {s for s, _ in issues})
        assert any("skewed" in m for _, m in issues)

    def test_empty_column_returns_nan_stats_and_warning(self):
        df = pd.DataFrame({"x": [None, None]})
        stats, issues = sanity_check(df, "x")
        assert all(np.isnan(v) for v in stats.values())
        assert issues == [("WARNING", "x has no numeric values to check")]


class TestAnomalyScan:
    @staticmethod
    def _series(values):
        return pd.DataFrame({
            "date": pd.date_range("2025-01-01", periods=len(values), freq="D"),
            "orders": values,
        })

    def test_flat_series_has_no_anomalies(self):
        df = self._series([100 + (i % 3) for i in range(30)])
        result = anomaly_scan(df, "date", "orders", window=7)
        assert result["anomalies"] == []
        assert result["summary"] == "0 anomalies in orders"

    def test_spike_beyond_threshold_is_detected_with_direction(self):
        values = [100 + (i % 3) for i in range(30)]
        values[20] = 400
        result = anomaly_scan(self._series(values), "date", "orders", window=7, threshold=2.0)
        spikes = [a for a in result["anomalies"] if a["direction"] == "spike"]
        assert len(spikes) == 1
        assert spikes[0]["value"] == 400
        assert spikes[0]["pct_above_normal"] > 100

    def test_threshold_controls_sensitivity(self):
        values = [100 + (i % 3) for i in range(30)]
        values[15] = 106  # mild bump: ~2.5 std above the tiny rolling std
        df = self._series(values)
        loose = anomaly_scan(df, "date", "orders", window=7, threshold=6.0)
        tight = anomaly_scan(df, "date", "orders", window=7, threshold=1.0)
        assert len(loose["anomalies"]) <= len(tight["anomalies"])
        assert len(loose["anomalies"]) == 0

    def test_empty_frame(self):
        df = pd.DataFrame({"date": pd.to_datetime([]), "orders": []})
        result = anomaly_scan(df, "date", "orders")
        assert result["anomalies"] == []
        assert "no rows" in result["summary"]


class TestFreshnessCheck:
    def test_daily_data_refreshed_yesterday_is_ok(self):
        df = pd.DataFrame({"d": pd.date_range("2026-01-01", periods=20, freq="D")})
        out = freshness_check(df, "d", current_date=date(2026, 1, 21))
        assert out["cadence"] == "daily"
        assert out["status"] == "OK"
        assert out["days_ago"] == 1

    def test_daily_data_five_days_old_is_stale(self):
        df = pd.DataFrame({"d": pd.date_range("2026-01-01", periods=20, freq="D")})
        out = freshness_check(df, "d", current_date=date(2026, 1, 25))
        assert out["status"] == "WARNING"
        assert "expected daily refresh" in out["note"]

    def test_weekly_cadence_inferred(self):
        df = pd.DataFrame({"d": pd.date_range("2026-01-05", periods=8, freq="7D")})
        out = freshness_check(df, "d", current_date=date(2026, 3, 1))
        assert out["cadence"] == "weekly"
        assert out["status"] == "OK"

    def test_old_data_is_historical_not_stale(self):
        df = pd.DataFrame({"d": pd.date_range("2024-01-01", periods=30, freq="D")})
        out = freshness_check(df, "d", current_date=date(2026, 1, 1))
        assert out["cadence"] == "static/historical"
        assert out["status"] == "OK"
        assert out["max_date"] == "2024-01-30"

    def test_no_parseable_dates(self):
        df = pd.DataFrame({"d": ["not a date", None]})
        out = freshness_check(df, "d", current_date=date(2026, 1, 1))
        assert out["status"] == "WARNING"
        assert out["max_date"] is None
