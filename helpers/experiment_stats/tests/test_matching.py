"""Tests for causal/matching.py — Propensity Score Matching."""

import numpy as np
import pandas as pd
import pytest

from helpers.experiment_stats.causal.matching import propensity_match


class TestPropensityMatch:
    def test_matches_units(self, matching_data):
        result = propensity_match(
            matching_data, "treatment", ["tenure"], outcome_col="outcome"
        )
        assert result["n_matched"] > 0
        assert "att" in result
        assert "caveat" in result
        assert "interpretation" in result

    def test_recovers_approximate_effect(self, matching_data):
        result = propensity_match(
            matching_data, "treatment", ["tenure"], outcome_col="outcome"
        )
        # True effect is 5.0; matching should get in the ballpark
        if result["n_matched"] > 20:
            assert abs(result["att"] - 5.0) < 4.0

    def test_without_outcome(self, matching_data):
        result = propensity_match(
            matching_data, "treatment", ["tenure"]
        )
        assert result["n_matched"] > 0
        assert "att" not in result

    def test_missing_columns(self, matching_data):
        result = propensity_match(
            matching_data, "treatment", ["nonexistent"]
        )
        assert "error" in result

    def test_missing_treatment_col(self, matching_data):
        result = propensity_match(
            matching_data, "nonexistent", ["tenure"]
        )
        assert "error" in result

    def test_matched_df_returned(self, matching_data):
        result = propensity_match(
            matching_data, "treatment", ["tenure"], outcome_col="outcome"
        )
        assert "matched_df" in result
        assert isinstance(result["matched_df"], pd.DataFrame)
