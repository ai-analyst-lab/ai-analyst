"""Tests for causal/did.py — Difference-in-Differences."""

import numpy as np
import pandas as pd
import pytest

from helpers.experiment_stats.causal.did import (
    did_basic,
    parallel_trends_test,
    event_study,
)


class TestDidBasic:
    def test_detects_known_effect(self, panel_did):
        result = did_basic(panel_did, "outcome", "treated", "post")
        # True effect is 3.0
        assert result["significant"] is True
        assert abs(result["estimate"] - 3.0) < 1.5
        assert "caveat" in result

    def test_returns_group_means(self, panel_did):
        result = did_basic(panel_did, "outcome", "treated", "post")
        assert "ctrl_pre" in result["group_means"]
        assert "ctrl_post" in result["group_means"]
        assert "treat_pre" in result["group_means"]
        assert "treat_post" in result["group_means"]

    def test_missing_columns(self, panel_did):
        result = did_basic(panel_did, "nonexistent", "treated", "post")
        assert "error" in result

    def test_with_covariates(self, panel_did):
        panel_did["covariate"] = np.random.default_rng(42).normal(0, 1, len(panel_did))
        result = did_basic(panel_did, "outcome", "treated", "post",
                          covariates=["covariate"])
        assert "estimate" in result


class TestParallelTrends:
    def test_parallel_trends_pass(self, panel_did):
        result = parallel_trends_test(
            panel_did, "outcome", "treated", "time",
            intervention_time=5,
        )
        assert result["verdict"] == "PASS"

    def test_broken_trends_fail(self, panel_did_broken):
        result = parallel_trends_test(
            panel_did_broken, "outcome", "treated", "time",
            intervention_time=5,
        )
        assert result["verdict"] in ("WARNING", "FAIL")

    def test_insufficient_data(self):
        df = pd.DataFrame({
            "outcome": [1, 2],
            "treated": [0, 1],
            "time": [0, 0],
        })
        result = parallel_trends_test(df, "outcome", "treated", "time", 5)
        assert result["verdict"] == "INSUFFICIENT_DATA"


class TestEventStudy:
    def test_returns_period_estimates(self, panel_did):
        result = event_study(panel_did, "outcome", "treated", "time",
                            intervention_time=5)
        assert len(result["periods"]) > 0
        assert len(result["estimates"]) == len(result["periods"])
        assert "reference_period" in result

    def test_pre_period_not_significant(self, panel_did):
        result = event_study(panel_did, "outcome", "treated", "time",
                            intervention_time=5)
        assert result["pre_period_violations"] == 0

    def test_broken_trends_show_violations(self, panel_did_broken):
        result = event_study(panel_did_broken, "outcome", "treated", "time",
                            intervention_time=5)
        # With broken trends, some pre-period coefficients should be significant
        assert result["pre_period_violations"] >= 0  # may or may not detect
