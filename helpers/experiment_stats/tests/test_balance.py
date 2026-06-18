"""Tests for causal/balance.py — balance diagnostics."""

import numpy as np
import pandas as pd
import pytest

from helpers.experiment_stats.causal.balance import balance_table, love_plot


class TestBalanceTable:
    def test_balanced_data(self):
        rng = np.random.default_rng(42)
        n = 5000
        df = pd.DataFrame({
            "treatment": [0] * n + [1] * n,
            "age": rng.normal(35, 5, 2 * n),
            "income": rng.normal(50000, 10000, 2 * n),
        })
        result = balance_table(df, ["age", "income"], "treatment")
        assert result["balanced"] is True
        assert result["n_imbalanced"] == 0

    def test_imbalanced_data(self):
        rng = np.random.default_rng(42)
        n = 500
        df = pd.DataFrame({
            "treatment": [0] * n + [1] * n,
            "age": np.concatenate([rng.normal(30, 5, n), rng.normal(45, 5, n)]),
            "income": rng.normal(50000, 10000, 2 * n),
        })
        result = balance_table(df, ["age", "income"], "treatment")
        assert result["n_imbalanced"] >= 1
        # Age should be the imbalanced one
        age_row = [r for r in result["table"] if r["covariate"] == "age"][0]
        assert age_row["smd"] > 0.1

    def test_returns_smd(self):
        rng = np.random.default_rng(42)
        df = pd.DataFrame({
            "treatment": [0, 0, 0, 1, 1, 1],
            "x": [1, 2, 3, 4, 5, 6],
        })
        result = balance_table(df, ["x"], "treatment")
        assert result["table"][0]["smd"] is not None


class TestLovePlot:
    def test_before_only(self):
        before = {
            "table": [
                {"covariate": "age", "smd": 0.5},
                {"covariate": "income", "smd": 0.08},
            ],
            "n_imbalanced": 1,
            "n_covariates": 2,
        }
        result = love_plot(before)
        assert len(result["plot_data"]) == 2
        assert result["threshold"] == 0.1

    def test_before_after(self):
        before = {
            "table": [
                {"covariate": "age", "smd": 0.5},
                {"covariate": "income", "smd": 0.3},
            ],
            "n_imbalanced": 2,
            "n_covariates": 2,
        }
        after = {
            "table": [
                {"covariate": "age", "smd": 0.08},
                {"covariate": "income", "smd": 0.05},
            ],
            "n_imbalanced": 0,
            "n_covariates": 2,
        }
        result = love_plot(before, after)
        assert len(result["improved"]) == 2
        assert len(result["worsened"]) == 0
