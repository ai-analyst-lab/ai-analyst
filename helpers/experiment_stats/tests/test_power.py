"""Tests for power.py — power analysis and sample size calculations."""

import pytest

from helpers.experiment_stats.power import (
    power_proportion,
    power_mean,
    detectable_effect,
    duration_estimate,
)


class TestPowerProportion:
    def test_standard_case(self):
        # 10% baseline, 5% relative lift, standard alpha/power
        result = power_proportion(0.10, 0.05)
        assert result["sample_size_per_group"] > 0
        assert result["total_sample_size"] == result["sample_size_per_group"] * 2
        assert "interpretation" in result

    def test_larger_effect_needs_fewer_samples(self):
        small_effect = power_proportion(0.10, 0.05)
        large_effect = power_proportion(0.10, 0.20)
        assert large_effect["sample_size_per_group"] < small_effect["sample_size_per_group"]

    def test_higher_power_needs_more_samples(self):
        low_power = power_proportion(0.10, 0.10, power=0.80)
        high_power = power_proportion(0.10, 0.10, power=0.95)
        assert high_power["sample_size_per_group"] > low_power["sample_size_per_group"]

    def test_invalid_baseline(self):
        result = power_proportion(0.0, 0.05)
        assert "error" in result

    def test_known_answer(self):
        # For 10% baseline, 10% relative MDE (1pp), ~14k per group is expected
        result = power_proportion(0.10, 0.10)
        assert 10_000 < result["sample_size_per_group"] < 25_000


class TestPowerMean:
    def test_standard_case(self):
        result = power_mean(50, 20, 0.05)
        assert result["sample_size_per_group"] > 0
        assert result["cohens_d"] > 0

    def test_zero_std(self):
        result = power_mean(50, 0, 0.05)
        assert "error" in result

    def test_smaller_effect_needs_more(self):
        small = power_mean(50, 20, 0.02)
        large = power_mean(50, 20, 0.10)
        assert small["sample_size_per_group"] > large["sample_size_per_group"]


class TestDetectableEffect:
    def test_proportion(self):
        result = detectable_effect(5000, baseline_rate=0.10)
        assert result["mde_relative"] > 0
        assert result["mde_absolute"] > 0
        assert "interpretation" in result

    def test_mean(self):
        result = detectable_effect(5000, baseline_std=20.0)
        assert result["mde_absolute"] > 0
        assert result["cohens_d"] > 0

    def test_no_baseline(self):
        result = detectable_effect(5000)
        assert "error" in result

    def test_small_n(self):
        result = detectable_effect(1)
        assert "error" in result

    def test_more_samples_smaller_mde(self):
        small_n = detectable_effect(1000, baseline_rate=0.10)
        large_n = detectable_effect(10000, baseline_rate=0.10)
        assert large_n["mde_relative"] < small_n["mde_relative"]


class TestDurationEstimate:
    def test_standard_case(self):
        result = duration_estimate(10000, 500)
        assert result["days"] == 20
        assert result["viable"] == "VIABLE"

    def test_marginal(self):
        result = duration_estimate(10000, 200)
        assert result["days"] == 50
        assert result["viable"] == "MARGINAL"

    def test_not_viable(self):
        result = duration_estimate(10000, 50)
        assert result["days"] == 200
        assert result["viable"] == "NOT_VIABLE"

    def test_allocation(self):
        full = duration_estimate(10000, 1000, allocation=1.0)
        half = duration_estimate(10000, 1000, allocation=0.5)
        assert half["days"] == full["days"] * 2

    def test_zero_traffic(self):
        result = duration_estimate(10000, 0)
        assert "error" in result
