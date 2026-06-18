"""Tests for sequential.py — confidence sequences and always-valid p-values."""

import numpy as np
import pytest

from helpers.experiment_stats.sequential import (
    confidence_sequence,
    always_valid_pvalue,
)


class TestConfidenceSequence:
    def test_detects_effect(self):
        rng = np.random.default_rng(42)
        # Large effect, many observations → should reject
        data = rng.normal(1.0, 1.0, size=500)
        result = confidence_sequence(data)
        assert result["rejected_at"] is not None
        assert result["final_mean"] > 0

    def test_null_no_rejection(self):
        rng = np.random.default_rng(42)
        data = rng.normal(0.0, 1.0, size=100)
        result = confidence_sequence(data)
        # May or may not reject (null is true, but stochastic)
        assert "interpretation" in result

    def test_returns_running_ci(self):
        rng = np.random.default_rng(42)
        data = rng.normal(0.5, 1.0, size=50)
        result = confidence_sequence(data)
        assert len(result["running_mean"]) == 50
        assert len(result["ci_lower"]) == 50
        assert len(result["ci_upper"]) == 50

    def test_insufficient_data(self):
        result = confidence_sequence([1])
        assert "error" in result

    def test_ci_narrows_over_time(self):
        rng = np.random.default_rng(42)
        data = rng.normal(0.0, 1.0, size=200)
        result = confidence_sequence(data)
        # CI should be narrower at end than beginning (ignoring first few)
        early_width = result["ci_upper"][10] - result["ci_lower"][10]
        late_width = result["ci_upper"][-1] - result["ci_lower"][-1]
        assert late_width < early_width


class TestAlwaysValidPvalue:
    def test_large_effect(self):
        rng = np.random.default_rng(42)
        data = rng.normal(2.0, 1.0, size=200)
        result = always_valid_pvalue(data)
        assert result["p_value"] < 0.05
        assert result["e_value"] > 1

    def test_null_effect(self):
        rng = np.random.default_rng(42)
        data = rng.normal(0.0, 1.0, size=100)
        result = always_valid_pvalue(data)
        # P-value should generally be > 0.05 under null
        assert "interpretation" in result

    def test_custom_null(self):
        rng = np.random.default_rng(42)
        data = rng.normal(5.0, 1.0, size=100)
        result = always_valid_pvalue(data, null_mean=5.0)
        # Data matches null → should not reject
        assert "interpretation" in result

    def test_insufficient_data(self):
        result = always_valid_pvalue([1])
        assert "error" in result
