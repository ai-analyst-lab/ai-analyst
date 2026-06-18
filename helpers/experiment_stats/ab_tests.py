"""
A/B test statistics for experiment analysis.

Core hypothesis tests for comparing treatment vs control groups in randomized
experiments: continuous metrics (Welch's t-test), proportions (Z-test),
ratio metrics (delta method), and winsorization for outlier-robust analysis.
"""

import math

import numpy as np
import pandas as pd
from scipy import stats


def welch_test(control, treatment, alpha=0.05):
    """Two-sample Welch's t-test for comparing means between experiment groups.

    Use for continuous metrics (revenue per user, session duration, pages per
    session). Does NOT assume equal variances.

    Args:
        control: array-like of metric values for control group.
        treatment: array-like of metric values for treatment group.
        alpha: significance threshold (default 0.05).

    Returns:
        dict with: t_stat, p_value, significant, mean_control, mean_treatment,
        diff, ci_lower, ci_upper, effect_size, effect_label, interpretation.
    """
    control = pd.Series(control).dropna()
    treatment = pd.Series(treatment).dropna()

    if len(control) < 2 or len(treatment) < 2:
        return {
            "test": "welch_t_test",
            "error": "Need at least 2 observations per group",
            "significant": False,
            "interpretation": "Insufficient data for hypothesis test.",
        }

    t_stat, p_value = stats.ttest_ind(control, treatment, equal_var=False)

    mean_c = float(control.mean())
    mean_t = float(treatment.mean())
    diff = mean_t - mean_c

    # Welch-Satterthwaite degrees of freedom for CI
    n_c, n_t = len(control), len(treatment)
    var_c, var_t = float(control.var(ddof=1)), float(treatment.var(ddof=1))
    se = math.sqrt(var_c / n_c + var_t / n_t)

    nu_num = (var_c / n_c + var_t / n_t) ** 2
    nu_den = (var_c / n_c) ** 2 / (n_c - 1) + (var_t / n_t) ** 2 / (n_t - 1)
    df = nu_num / nu_den if nu_den > 0 else min(n_c, n_t) - 1

    t_crit = stats.t.ppf(1 - alpha / 2, df)
    ci_lower = diff - t_crit * se
    ci_upper = diff + t_crit * se

    # Effect size (Cohen's d with pooled std)
    pooled_std = math.sqrt(
        ((n_c - 1) * var_c + (n_t - 1) * var_t) / (n_c + n_t - 2)
    )
    d = diff / pooled_std if pooled_std > 0 else 0.0
    d_abs = abs(d)
    if d_abs < 0.2:
        effect_label = "Negligible"
    elif d_abs < 0.5:
        effect_label = "Small"
    elif d_abs < 0.8:
        effect_label = "Medium"
    else:
        effect_label = "Large"

    significant = bool(p_value < alpha)
    rel_lift = diff / abs(mean_c) * 100 if mean_c != 0 else float("inf")

    if significant:
        direction = "higher" if diff > 0 else "lower"
        interp = (
            f"Treatment mean ({mean_t:.4f}) is significantly {direction} than "
            f"control ({mean_c:.4f}), diff = {diff:+.4f} ({rel_lift:+.1f}%), "
            f"p = {p_value:.4f}. {effect_label} effect (d = {d:.2f})."
        )
    else:
        interp = (
            f"No significant difference between treatment ({mean_t:.4f}) and "
            f"control ({mean_c:.4f}), diff = {diff:+.4f} ({rel_lift:+.1f}%), "
            f"p = {p_value:.4f}. Cannot reject the null hypothesis."
        )

    return {
        "test": "welch_t_test",
        "t_stat": float(t_stat),
        "p_value": float(p_value),
        "significant": significant,
        "mean_control": mean_c,
        "mean_treatment": mean_t,
        "diff": float(diff),
        "relative_lift_pct": float(rel_lift),
        "ci_lower": float(ci_lower),
        "ci_upper": float(ci_upper),
        "effect_size": float(d),
        "effect_label": effect_label,
        "n_control": n_c,
        "n_treatment": n_t,
        "alpha": alpha,
        "interpretation": interp,
    }


def proportion_test(c_success, c_n, t_success, t_n, alpha=0.05):
    """Z-test for comparing conversion rates between experiment groups.

    Use for binary metrics (converted/not, clicked/not, signed up/not).

    Args:
        c_success: number of successes in control.
        c_n: total observations in control.
        t_success: number of successes in treatment.
        t_n: total observations in treatment.
        alpha: significance threshold (default 0.05).

    Returns:
        dict with: z_stat, p_value, significant, rate_control, rate_treatment,
        diff, ci_lower, ci_upper, relative_lift_pct, interpretation.
    """
    if c_n == 0 or t_n == 0:
        return {
            "test": "proportion_z_test",
            "error": "Sample sizes must be > 0",
            "significant": False,
            "interpretation": "Insufficient data for proportion test.",
        }

    rate_c = c_success / c_n
    rate_t = t_success / t_n
    diff = rate_t - rate_c

    # Pooled proportion for test statistic
    pooled = (c_success + t_success) / (c_n + t_n)
    se_test = math.sqrt(pooled * (1 - pooled) * (1 / c_n + 1 / t_n))

    if se_test == 0:
        z_stat = 0.0
        p_value = 1.0
    else:
        z_stat = diff / se_test
        p_value = 2 * (1 - stats.norm.cdf(abs(z_stat)))

    # Unpooled SE for confidence interval (Agresti-Caffo approach)
    se_ci = math.sqrt(rate_c * (1 - rate_c) / c_n + rate_t * (1 - rate_t) / t_n)
    z_crit = stats.norm.ppf(1 - alpha / 2)
    ci_lower = diff - z_crit * se_ci
    ci_upper = diff + z_crit * se_ci

    significant = bool(p_value < alpha)
    rel_lift = diff / rate_c * 100 if rate_c > 0 else float("inf")

    if significant:
        direction = "higher" if diff > 0 else "lower"
        interp = (
            f"Treatment rate ({rate_t:.4f}) is significantly {direction} than "
            f"control ({rate_c:.4f}), diff = {diff:+.4f} ({rel_lift:+.1f}%), "
            f"p = {p_value:.4f}."
        )
    else:
        interp = (
            f"No significant difference between treatment ({rate_t:.4f}) and "
            f"control ({rate_c:.4f}), diff = {diff:+.4f} ({rel_lift:+.1f}%), "
            f"p = {p_value:.4f}."
        )

    return {
        "test": "proportion_z_test",
        "z_stat": float(z_stat),
        "p_value": float(p_value),
        "significant": significant,
        "rate_control": float(rate_c),
        "rate_treatment": float(rate_t),
        "diff": float(diff),
        "relative_lift_pct": float(rel_lift),
        "ci_lower": float(ci_lower),
        "ci_upper": float(ci_upper),
        "n_control": c_n,
        "n_treatment": t_n,
        "alpha": alpha,
        "interpretation": interp,
    }


def ratio_metric_test(num_c, den_c, num_t, den_t, alpha=0.05):
    """Delta method test for ratio metrics (e.g., revenue per user).

    Use when the metric is a ratio of two random variables (total revenue /
    total users) rather than a simple average. The delta method correctly
    estimates the variance of the ratio.

    Args:
        num_c: array-like of per-unit numerator values for control.
        den_c: array-like of per-unit denominator values for control.
        num_t: array-like of per-unit numerator values for treatment.
        den_t: array-like of per-unit denominator values for treatment.
        alpha: significance threshold (default 0.05).

    Returns:
        dict with: z_stat, p_value, significant, ratio_control, ratio_treatment,
        diff, ci_lower, ci_upper, interpretation.
    """
    num_c = np.asarray(num_c, dtype=float)
    den_c = np.asarray(den_c, dtype=float)
    num_t = np.asarray(num_t, dtype=float)
    den_t = np.asarray(den_t, dtype=float)

    n_c, n_t = len(num_c), len(num_t)
    if n_c < 2 or n_t < 2:
        return {
            "test": "ratio_delta_method",
            "error": "Need at least 2 observations per group",
            "significant": False,
            "interpretation": "Insufficient data for ratio metric test.",
        }

    sum_num_c, sum_den_c = num_c.sum(), den_c.sum()
    sum_num_t, sum_den_t = num_t.sum(), den_t.sum()

    if sum_den_c == 0 or sum_den_t == 0:
        return {
            "test": "ratio_delta_method",
            "error": "Denominator sums must be > 0",
            "significant": False,
            "interpretation": "Denominators sum to zero; cannot compute ratio.",
        }

    ratio_c = sum_num_c / sum_den_c
    ratio_t = sum_num_t / sum_den_t
    diff = ratio_t - ratio_c

    # Delta method variance: Var(R) ≈ (1/D^2) * [Var(N) - 2R*Cov(N,D) + R^2*Var(D)]
    def _delta_var(num, den, ratio, n):
        var_n = np.var(num, ddof=1)
        var_d = np.var(den, ddof=1)
        cov_nd = np.cov(num, den, ddof=1)[0, 1]
        mean_d = den.mean()
        return (var_n - 2 * ratio * cov_nd + ratio**2 * var_d) / (mean_d**2 * n)

    var_c = _delta_var(num_c, den_c, ratio_c, n_c)
    var_t = _delta_var(num_t, den_t, ratio_t, n_t)
    se = math.sqrt(var_c + var_t)

    if se == 0:
        z_stat = 0.0
        p_value = 1.0
    else:
        z_stat = diff / se
        p_value = 2 * (1 - stats.norm.cdf(abs(z_stat)))

    z_crit = stats.norm.ppf(1 - alpha / 2)
    ci_lower = diff - z_crit * se
    ci_upper = diff + z_crit * se

    significant = bool(p_value < alpha)
    rel_lift = diff / abs(ratio_c) * 100 if ratio_c != 0 else float("inf")

    if significant:
        direction = "higher" if diff > 0 else "lower"
        interp = (
            f"Treatment ratio ({ratio_t:.4f}) is significantly {direction} than "
            f"control ({ratio_c:.4f}), diff = {diff:+.4f} ({rel_lift:+.1f}%), "
            f"p = {p_value:.4f}."
        )
    else:
        interp = (
            f"No significant difference between treatment ratio ({ratio_t:.4f}) "
            f"and control ({ratio_c:.4f}), diff = {diff:+.4f} ({rel_lift:+.1f}%), "
            f"p = {p_value:.4f}."
        )

    return {
        "test": "ratio_delta_method",
        "z_stat": float(z_stat),
        "p_value": float(p_value),
        "significant": significant,
        "ratio_control": float(ratio_c),
        "ratio_treatment": float(ratio_t),
        "diff": float(diff),
        "relative_lift_pct": float(rel_lift),
        "ci_lower": float(ci_lower),
        "ci_upper": float(ci_upper),
        "n_control": n_c,
        "n_treatment": n_t,
        "alpha": alpha,
        "interpretation": interp,
    }


def winsorize(series, lower=0.01, upper=0.99):
    """Winsorize a series by clipping to quantile bounds.

    Use before A/B tests on revenue or other heavy-tailed metrics to reduce
    the impact of extreme outliers on treatment effect estimates.

    Args:
        series: array-like of numeric values.
        lower: lower quantile to clip at (default 0.01 = 1st percentile).
        upper: upper quantile to clip at (default 0.99 = 99th percentile).

    Returns:
        pd.Series with values clipped to [lower_bound, upper_bound].
    """
    s = pd.Series(series).dropna()
    if len(s) == 0:
        return s
    lower_bound = float(s.quantile(lower))
    upper_bound = float(s.quantile(upper))
    return s.clip(lower=lower_bound, upper=upper_bound)
