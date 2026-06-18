"""Tests for srm.py — Sample Ratio Mismatch detection."""

import numpy as np
import pandas as pd
import pytest

from helpers.experiment_stats.srm import srm_check, srm_diagnose


class TestSrmCheck:
    def test_clean_split_passes(self, srm_clean):
        result = srm_check(srm_clean)
        assert result["verdict"] == "PASS"
        assert result["p_value"] > 0.05

    def test_violation_blocks(self, srm_violation):
        result = srm_check(srm_violation)
        assert result["verdict"] in ("WARNING", "BLOCK")
        assert result["p_value"] < 0.05

    def test_custom_ratios(self):
        # 70/30 split, clean
        result = srm_check([7000, 3000], expected_ratios=[0.7, 0.3])
        assert result["verdict"] == "PASS"

    def test_three_way_split(self):
        result = srm_check([3333, 3334, 3333])
        assert result["verdict"] == "PASS"
        assert len(result["observed_ratios"]) == 3

    def test_empty_data(self):
        result = srm_check([0, 0])
        assert result["verdict"] == "BLOCK"

    def test_returns_all_keys(self, srm_clean):
        result = srm_check(srm_clean)
        expected = ["test", "chi2_stat", "p_value", "verdict",
                    "observed_counts", "expected_counts", "observed_ratios",
                    "expected_ratios", "total", "threshold", "interpretation"]
        for key in expected:
            assert key in result

    def test_microsoft_threshold(self, srm_violation):
        # With Microsoft's strict threshold of 0.0005
        result = srm_check(srm_violation, threshold=0.0005)
        assert "verdict" in result


class TestSrmDiagnose:
    def test_clean_data(self, rng):
        df = pd.DataFrame({
            "variant": rng.choice(["control", "treatment"], size=10000),
            "platform": rng.choice(["ios", "android", "web"], size=10000),
            "country": rng.choice(["US", "UK", "DE"], size=10000),
        })
        result = srm_diagnose(df, group_col="variant")
        assert "overall_srm" in result
        assert "segment_results" in result

    def test_missing_column(self):
        df = pd.DataFrame({"x": [1, 2, 3]})
        result = srm_diagnose(df, group_col="variant")
        assert "error" in result

    def test_detects_segment_srm(self):
        # Create data where SRM only exists in one segment
        rng = np.random.default_rng(42)
        n = 5000
        platform = np.array(["ios"] * n + ["android"] * n)
        # iOS has clean split, Android has SRM
        variant = np.concatenate([
            rng.choice(["control", "treatment"], size=n),  # ios clean
            np.array(["control"] * 3000 + ["treatment"] * 2000),  # android SRM
        ])
        df = pd.DataFrame({"variant": variant, "platform": platform})
        result = srm_diagnose(df, group_col="variant", segments=["platform"])
        assert len(result["flagged_segments"]) > 0
