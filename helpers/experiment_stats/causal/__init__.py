"""
Causal inference methods for observational studies.

When experiments aren't possible, these methods estimate causal effects
from observational data with explicit assumption checking and mandatory caveats.

Methods (ordered by causal credibility):
1. DiD (Difference-in-Differences) — strongest when parallel trends hold
2. PSM (Propensity Score Matching) — controls for observed confounders
3. Regression Adjustment — OLS with covariates
4. Pre-Post — weakest; assumes nothing else changed

Usage:
    from helpers.experiment_stats.causal import (
        pre_post_analysis, pre_post_timeseries,
        did_basic, parallel_trends_test,
        propensity_match, balance_table, love_plot,
        regression_adjust,
        rosenbaum_bounds, e_value,
        check_parallel_trends, check_common_support,
    )
"""

from helpers.experiment_stats.causal.pre_post import pre_post_analysis, pre_post_timeseries
from helpers.experiment_stats.causal.did import (
    did_basic,
    parallel_trends_test,
    event_study,
)
from helpers.experiment_stats.causal.matching import propensity_match
from helpers.experiment_stats.causal.balance import balance_table, love_plot
from helpers.experiment_stats.causal.regression import regression_adjust
from helpers.experiment_stats.causal.sensitivity import rosenbaum_bounds, e_value
from helpers.experiment_stats.causal.assumptions import (
    check_parallel_trends,
    check_common_support,
)

__all__ = [
    "pre_post_analysis",
    "pre_post_timeseries",
    "did_basic",
    "parallel_trends_test",
    "event_study",
    "propensity_match",
    "balance_table",
    "love_plot",
    "regression_adjust",
    "rosenbaum_bounds",
    "e_value",
    "check_parallel_trends",
    "check_common_support",
]
