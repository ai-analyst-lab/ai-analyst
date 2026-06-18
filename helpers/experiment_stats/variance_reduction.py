"""
Variance reduction techniques for A/B testing.

CUPED (Controlled-experiment Using Pre-Experiment Data) reduces metric variance
by adjusting for pre-experiment covariates, enabling faster experiments.
"""

import math

import numpy as np
import pandas as pd
from scipy import stats


def cuped_adjust(pre, post, treatment, alpha=0.05):
    """CUPED variance adjustment for experiment metrics.

    Adjusts post-experiment metric values using pre-experiment data as a
    covariate. Reduces variance by removing pre-existing user-level variation,
    producing tighter confidence intervals and faster experiments.

    Method: Y_adjusted = Y_post - theta * (X_pre - mean(X_pre))
    where theta = Cov(Y_post, X_pre) / Var(X_pre).

    Args:
        pre: array-like of pre-experiment metric values (one per user).
        post: array-like of post-experiment metric values (one per user).
        treatment: array-like of 0/1 treatment assignment (one per user).
        alpha: significance level (default 0.05).

    Returns:
        dict with: ate (average treatment effect), ci_lower, ci_upper, p_value,
        significant, variance_reduction_pct, theta, unadjusted_ate,
        unadjusted_se, adjusted_se, interpretation.
    """
    pre = np.asarray(pre, dtype=float)
    post = np.asarray(post, dtype=float)
    treatment = np.asarray(treatment, dtype=int)

    if len(pre) != len(post) or len(pre) != len(treatment):
        return {
            "error": "pre, post, and treatment must have the same length",
            "interpretation": "Array length mismatch.",
        }

    mask = ~(np.isnan(pre) | np.isnan(post))
    pre, post, treatment = pre[mask], post[mask], treatment[mask]

    n = len(pre)
    if n < 4:
        return {
            "error": "Need at least 4 observations",
            "interpretation": "Insufficient data for CUPED.",
        }

    # Compute theta = Cov(post, pre) / Var(pre)
    var_pre = np.var(pre, ddof=1)
    if var_pre == 0:
        return {
            "error": "Zero variance in pre-experiment data",
            "interpretation": "Pre-experiment metric is constant; CUPED cannot help.",
        }

    cov_pre_post = np.cov(pre, post, ddof=1)[0, 1]
    theta = cov_pre_post / var_pre

    # Adjust post values
    pre_mean = pre.mean()
    adjusted = post - theta * (pre - pre_mean)

    # Split by treatment
    ctrl_mask = treatment == 0
    treat_mask = treatment == 1
    adj_ctrl = adjusted[ctrl_mask]
    adj_treat = adjusted[treat_mask]

    n_c, n_t = len(adj_ctrl), len(adj_treat)
    if n_c < 2 or n_t < 2:
        return {
            "error": "Need at least 2 observations per group after CUPED",
            "interpretation": "Too few observations in one group.",
        }

    # CUPED-adjusted ATE
    ate = float(adj_treat.mean() - adj_ctrl.mean())
    se_adj = math.sqrt(np.var(adj_ctrl, ddof=1) / n_c + np.var(adj_treat, ddof=1) / n_t)

    # Unadjusted comparison
    unadj_ctrl = post[ctrl_mask]
    unadj_treat = post[treat_mask]
    unadj_ate = float(unadj_treat.mean() - unadj_ctrl.mean())
    unadj_se = math.sqrt(np.var(unadj_ctrl, ddof=1) / n_c + np.var(unadj_treat, ddof=1) / n_t)

    # Variance reduction
    var_reduction = 1 - (se_adj**2 / unadj_se**2) if unadj_se > 0 else 0.0
    var_reduction_pct = var_reduction * 100

    # Welch's t-test on adjusted values
    t_stat, p_value = stats.ttest_ind(adj_treat, adj_ctrl, equal_var=False)
    significant = bool(p_value < alpha)

    z_crit = stats.norm.ppf(1 - alpha / 2)
    ci_lower = ate - z_crit * se_adj
    ci_upper = ate + z_crit * se_adj

    sig_label = "significant" if significant else "not significant"
    interp = (
        f"CUPED-adjusted ATE = {ate:+.4f} (p = {p_value:.4f}, {sig_label}). "
        f"CI: [{ci_lower:+.4f}, {ci_upper:+.4f}]. "
        f"Variance reduced by {var_reduction_pct:.1f}% (theta = {theta:.3f}). "
        f"Unadjusted ATE was {unadj_ate:+.4f} ± {unadj_se:.4f}."
    )

    return {
        "ate": ate,
        "ci_lower": float(ci_lower),
        "ci_upper": float(ci_upper),
        "p_value": float(p_value),
        "t_stat": float(t_stat),
        "significant": significant,
        "theta": float(theta),
        "variance_reduction_pct": float(var_reduction_pct),
        "unadjusted_ate": unadj_ate,
        "unadjusted_se": float(unadj_se),
        "adjusted_se": float(se_adj),
        "n_control": n_c,
        "n_treatment": n_t,
        "alpha": alpha,
        "interpretation": interp,
    }


def cuped_adjusted_power(pre_post_correlation, original_n, baseline_rate=None,
                         baseline_std=None, mde_relative=0.05, alpha=0.05, power=0.80):
    """Estimate sample size savings from CUPED given pre-post correlation.

    Args:
        pre_post_correlation: Pearson correlation between pre and post metric.
        original_n: sample size per group without CUPED.
        baseline_rate: baseline conversion rate (for proportions).
        baseline_std: baseline standard deviation (for continuous).
        mde_relative: minimum detectable effect (relative).
        alpha: significance level.
        power: desired power.

    Returns:
        dict with: adjusted_n, original_n, savings_pct, variance_factor,
        interpretation.
    """
    rho = pre_post_correlation
    variance_factor = 1 - rho**2
    adjusted_n = math.ceil(original_n * variance_factor)

    savings_pct = (1 - variance_factor) * 100

    interp = (
        f"With pre-post correlation of {rho:.2f}, CUPED reduces required sample by "
        f"{savings_pct:.0f}%: from {original_n:,} to {adjusted_n:,} per group. "
        f"Variance factor = {variance_factor:.3f}."
    )

    return {
        "adjusted_n": adjusted_n,
        "original_n": original_n,
        "savings_pct": float(savings_pct),
        "variance_factor": float(variance_factor),
        "pre_post_correlation": float(rho),
        "interpretation": interp,
    }
