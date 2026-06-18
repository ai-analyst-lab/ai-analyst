"""Tests for causal/sensitivity.py — sensitivity analysis."""

import numpy as np
import pytest

from helpers.experiment_stats.causal.sensitivity import rosenbaum_bounds, e_value


class TestRosenbaumBounds:
    def test_strong_effect(self):
        rng = np.random.default_rng(42)
        n = 50
        treated = rng.normal(10, 2, n)
        control = rng.normal(5, 2, n)
        result = rosenbaum_bounds(treated, control)
        # With 5-unit difference, should be robust to moderate hidden bias
        assert result["gamma_table"][0]["significant"] is True  # gamma=1
        assert result["critical_gamma"] is None or result["critical_gamma"] > 1.5

    def test_weak_effect(self):
        rng = np.random.default_rng(42)
        n = 30
        treated = rng.normal(5.5, 3, n)
        control = rng.normal(5.0, 3, n)
        result = rosenbaum_bounds(treated, control)
        assert "interpretation" in result

    def test_mismatched_lengths(self):
        result = rosenbaum_bounds([1, 2, 3], [4, 5])
        assert "error" in result

    def test_custom_gammas(self):
        rng = np.random.default_rng(42)
        treated = rng.normal(10, 2, 50)
        control = rng.normal(5, 2, 50)
        result = rosenbaum_bounds(treated, control, gammas=[1, 2, 5, 10])
        assert len(result["gamma_table"]) == 4


class TestEValue:
    def test_strong_rr(self):
        result = e_value(3.0)
        assert result["e_value"] > 3
        assert "interpretation" in result

    def test_moderate_rr(self):
        result = e_value(1.5)
        assert result["e_value"] > 1
        assert result["e_value"] < 3

    def test_protective_rr(self):
        # RR < 1 should be flipped
        result = e_value(0.5)
        assert result["e_value"] > 1

    def test_with_ci(self):
        result = e_value(2.0, ci_lower=1.3)
        assert "e_value_ci" in result
        assert result["e_value_ci"] < result["e_value"]

    def test_invalid_rr(self):
        result = e_value(0)
        assert "error" in result

    def test_ci_crossing_null(self):
        result = e_value(1.5, ci_lower=0.8)
        assert result["e_value_ci"] == 1.0  # CI crosses null
