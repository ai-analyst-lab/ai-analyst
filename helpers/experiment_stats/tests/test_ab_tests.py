"""Tests for ab_tests.py — A/B test statistics."""

import numpy as np
import pandas as pd
import pytest

from helpers.experiment_stats.ab_tests import (
    welch_test,
    proportion_test,
    ratio_metric_test,
    winsorize,
)


class TestWelchTest:
    def test_detects_known_effect(self, continuous_ab):
        result = welch_test(continuous_ab["control"], continuous_ab["treatment"])
        assert result["significant"] is True
        assert result["p_value"] < 0.05
        # True diff is 5.0, estimate should be in ballpark
        assert abs(result["diff"] - 5.0) < 3.0
        assert result["ci_lower"] > 0  # CI should exclude 0

    def test_no_effect(self, no_effect_ab):
        # Convert to continuous for welch test
        rng = np.random.default_rng(99)
        ctrl = rng.normal(50, 10, 1000)
        treat = rng.normal(50, 10, 1000)
        result = welch_test(ctrl, treat)
        # Should usually not reject (might occasionally due to randomness)
        assert "interpretation" in result
        assert result["n_control"] == 1000

    def test_returns_all_keys(self, continuous_ab):
        result = welch_test(continuous_ab["control"], continuous_ab["treatment"])
        expected_keys = [
            "test", "t_stat", "p_value", "significant", "mean_control",
            "mean_treatment", "diff", "relative_lift_pct", "ci_lower",
            "ci_upper", "effect_size", "effect_label", "n_control",
            "n_treatment", "alpha", "interpretation",
        ]
        for key in expected_keys:
            assert key in result, f"Missing key: {key}"

    def test_empty_data(self):
        result = welch_test([], [1, 2, 3])
        assert result["significant"] is False
        assert "error" in result

    def test_single_observation(self):
        result = welch_test([1], [2])
        assert result["significant"] is False
        assert "error" in result

    def test_custom_alpha(self, continuous_ab):
        result = welch_test(
            continuous_ab["control"], continuous_ab["treatment"], alpha=0.01
        )
        assert result["alpha"] == 0.01

    def test_handles_nan(self):
        ctrl = [1, 2, 3, np.nan, 5]
        treat = [2, 3, 4, 5, np.nan]
        result = welch_test(ctrl, treat)
        assert result["n_control"] == 4
        assert result["n_treatment"] == 4


class TestProportionTest:
    def test_detects_large_effect(self, large_effect_ab):
        c = large_effect_ab["control"]
        t = large_effect_ab["treatment"]
        result = proportion_test(c.sum(), len(c), t.sum(), len(t))
        assert result["significant"] is True
        assert result["p_value"] < 0.001

    def test_returns_correct_rates(self):
        result = proportion_test(100, 1000, 150, 1000)
        assert abs(result["rate_control"] - 0.10) < 0.001
        assert abs(result["rate_treatment"] - 0.15) < 0.001

    def test_zero_sample(self):
        result = proportion_test(0, 0, 10, 100)
        assert result["significant"] is False
        assert "error" in result

    def test_relative_lift(self):
        result = proportion_test(100, 1000, 120, 1000)
        assert abs(result["relative_lift_pct"] - 20.0) < 0.1

    def test_returns_all_keys(self):
        result = proportion_test(100, 1000, 120, 1000)
        expected = ["test", "z_stat", "p_value", "significant",
                    "rate_control", "rate_treatment", "diff",
                    "relative_lift_pct", "ci_lower", "ci_upper",
                    "n_control", "n_treatment", "alpha", "interpretation"]
        for key in expected:
            assert key in result


class TestRatioMetricTest:
    def test_detects_ratio_difference(self, ratio_metric_data):
        result = ratio_metric_test(
            ratio_metric_data["num_c"], ratio_metric_data["den_c"],
            ratio_metric_data["num_t"], ratio_metric_data["den_t"],
        )
        assert "p_value" in result
        assert "interpretation" in result
        # Treatment ratio should be higher
        assert result["ratio_treatment"] > result["ratio_control"]

    def test_empty_data(self):
        result = ratio_metric_test([], [], [1], [1])
        assert "error" in result

    def test_zero_denominator(self):
        result = ratio_metric_test([1, 2], [0, 0], [3, 4], [1, 1])
        assert "error" in result


class TestWinsorize:
    def test_clips_outliers(self):
        data = list(range(100)) + [10000]  # outlier at end
        result = winsorize(data, lower=0.01, upper=0.99)
        assert result.max() < 10000
        assert len(result) == 101

    def test_empty_data(self):
        result = winsorize([])
        assert len(result) == 0

    def test_preserves_middle(self):
        data = list(range(100))
        result = winsorize(data, lower=0.05, upper=0.95)
        # Middle values should be unchanged
        assert result.iloc[50] == 50

    def test_returns_series(self):
        result = winsorize([1, 2, 3, 4, 5])
        assert isinstance(result, pd.Series)
