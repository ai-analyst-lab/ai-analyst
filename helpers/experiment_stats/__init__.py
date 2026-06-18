"""
Experiment statistics library for the AI Data Analyst.

Production-grade statistical functions for A/B testing and causal inference.
Extends the general-purpose stats_helpers.py with experiment-specific capabilities.

Usage:
    from helpers.experiment_stats import (
        # A/B testing
        welch_test, proportion_test, ratio_metric_test, winsorize,
        # Power analysis
        power_proportion, power_mean, detectable_effect, duration_estimate,
        power_sensitivity_table,
        # SRM detection
        srm_check, srm_diagnose,
        # Effect sizes
        cohens_d, relative_lift,
        # Multiple comparisons
        adjust_pvalues,
        # Variance reduction
        cuped_adjust,
        # Sequential testing
        confidence_sequence, always_valid_pvalue,
        # Bayesian
        bayesian_proportion, bayesian_mean, prob_best, expected_loss,
    )

    # Run a basic A/B test on conversion rates
    result = proportion_test(c_success=350, c_n=1000, t_success=385, t_n=1000)
    print(result["interpretation"])

    # Check for SRM before analyzing
    srm = srm_check(observed_counts=[4800, 5200], expected_ratios=[0.5, 0.5])
    if srm["verdict"] == "BLOCK":
        print("HALT: SRM detected —", srm["interpretation"])
"""

# A/B testing
from helpers.experiment_stats.ab_tests import (
    welch_test,
    proportion_test,
    ratio_metric_test,
    winsorize,
)

# Power analysis
from helpers.experiment_stats.power import (
    power_proportion,
    power_mean,
    detectable_effect,
    power_at_n,
    duration_estimate,
    power_sensitivity_table,
)

# SRM detection
from helpers.experiment_stats.srm import (
    srm_check,
    srm_diagnose,
)

# Effect sizes
from helpers.experiment_stats.effect_size import (
    cohens_d,
    relative_lift,
)

# Multiple comparisons
from helpers.experiment_stats.corrections import (
    adjust_pvalues,
)

# Variance reduction
from helpers.experiment_stats.variance_reduction import (
    cuped_adjust,
    cuped_adjusted_power,
)

# Sequential testing
from helpers.experiment_stats.sequential import (
    confidence_sequence,
    always_valid_pvalue,
)

# Bayesian
from helpers.experiment_stats.bayesian import (
    bayesian_proportion,
    bayesian_mean,
    prob_best,
    expected_loss,
)

__all__ = [
    # A/B testing
    "welch_test",
    "proportion_test",
    "ratio_metric_test",
    "winsorize",
    # Power analysis
    "power_proportion",
    "power_at_n",
    "power_mean",
    "detectable_effect",
    "duration_estimate",
    "power_sensitivity_table",
    # SRM detection
    "srm_check",
    "srm_diagnose",
    # Effect sizes
    "cohens_d",
    "relative_lift",
    # Multiple comparisons
    "adjust_pvalues",
    # Variance reduction
    "cuped_adjust",
    "cuped_adjusted_power",
    # Sequential testing
    "confidence_sequence",
    "always_valid_pvalue",
    # Bayesian
    "bayesian_proportion",
    "bayesian_mean",
    "prob_best",
    "expected_loss",
]
