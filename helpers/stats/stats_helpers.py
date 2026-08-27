"""
Statistical testing utilities for the AI Data Analyst.

All functions return structured dicts with results, p-values, and
human-readable interpretations.

Usage:
    from helpers.stats.stats_helpers import (
        two_sample_proportion_test, two_sample_mean_test,
        mann_whitney_test, confidence_interval, chi_squared_test,
        bootstrap_ci, format_significance, interpret_effect_size,
        adjust_pvalues, characterize_distribution, rank_dimensions,
        sample_size_proportion, sample_size_mean, detectable_effect,
    )

    # Compare conversion rates between two variants
    result = two_sample_proportion_test(
        successes_a=120, n_a=1000,
        successes_b=145, n_b=1000,
    )
    print(result["interpretation"])

    # Compare revenue distributions (skewed data)
    result = mann_whitney_test(control_revenue, treatment_revenue)
    print(result["interpretation"])
"""

import math

import numpy as np
import pandas as pd
from scipy import stats


# ---------------------------------------------------------------------------
# Human-readable formatting helpers
# ---------------------------------------------------------------------------

def format_significance(p_value, alpha=0.05):
    """Return a human-readable significance statement.

    Args:
        p_value: The p-value from a statistical test.
        alpha: Significance threshold (default 0.05).

    Returns:
        str: One of three forms:
            - "Highly significant (p<0.001)"
            - "Statistically significant (p=X.XXX)"
            - "Not statistically significant (p=X.XXX)"
    """
    if p_value < 0.001:
        return "Highly significant (p<0.001)"
    elif p_value < alpha:
        return f"Statistically significant (p={p_value:.3f})"
    else:
        return f"Not statistically significant (p={p_value:.3f})"


def interpret_effect_size(d, test_type="cohens_d"):
    """Translate a numeric effect size into a plain-English label.

    Uses Cohen's conventions so users can immediately understand
    what d=0.38 actually means in practice.

    Args:
        d: The effect-size value (always taken as absolute value).
        test_type: Currently supports "cohens_d". Extensible for other
            effect-size families later.

    Returns:
        str: e.g. "Small effect (d=0.15)" / "Medium effect (d=0.45)" /
            "Large effect (d=1.02)"
    """
    d_abs = abs(d)

    if test_type == "cohens_d":
        if d_abs < 0.2:
            label = "Small"
        elif d_abs <= 0.8:
            label = "Medium"
        else:
            label = "Large"
        return f"{label} effect (d={d_abs:.2f})"

    # Fallback for unknown test types
    return f"Effect size = {d_abs:.2f}"


# ---------------------------------------------------------------------------
# Proportion test (conversion rates, CTR, signup rates)
# ---------------------------------------------------------------------------

def two_sample_proportion_test(successes_a, n_a, successes_b, n_b, alpha=0.05):
    """Z-test for comparing conversion rates between two groups.

    Use this when you have counts (e.g. 120 out of 1000 converted) and want
    to know whether Group B's rate is meaningfully different from Group A's.

    Args:
        successes_a: Number of successes in group A.
        n_a: Total observations in group A.
        successes_b: Number of successes in group B.
        n_b: Total observations in group B.
        alpha: Significance threshold (default 0.05).

    Returns:
        dict with keys: test, p_value, z_stat, significant, prop_a, prop_b,
        diff, ci_lower, ci_upper, interpretation.
    """
    prop_a = successes_a / n_a
    prop_b = successes_b / n_b
    diff = prop_b - prop_a

    # Pooled proportion under the null
    pooled = (successes_a + successes_b) / (n_a + n_b)
    se_pooled = math.sqrt(pooled * (1 - pooled) * (1 / n_a + 1 / n_b))

    # Z-statistic
    z_stat = diff / se_pooled if se_pooled > 0 else 0.0
    p_value = 2 * (1 - stats.norm.cdf(abs(z_stat)))

    # Confidence interval for the difference (unpooled SE)
    se_diff = math.sqrt(prop_a * (1 - prop_a) / n_a + prop_b * (1 - prop_b) / n_b)
    z_crit = stats.norm.ppf(1 - alpha / 2)
    ci_lower = diff - z_crit * se_diff
    ci_upper = diff + z_crit * se_diff

    return {
        "test": "z-test proportions",
        "p_value": float(p_value),
        "z_stat": float(z_stat),
        "significant": bool(p_value < alpha),
        "prop_a": float(prop_a),
        "prop_b": float(prop_b),
        "diff": float(diff),
        "ci_lower": float(ci_lower),
        "ci_upper": float(ci_upper),
        "interpretation": format_significance(p_value, alpha),
    }


# ---------------------------------------------------------------------------
# Mean comparison (Welch's t-test — does NOT assume equal variance)
# ---------------------------------------------------------------------------

def two_sample_mean_test(series_a, series_b, alpha=0.05):
    """Welch's t-test for comparing means between two groups.

    Use Welch's t-test (not Student's) because it does not assume equal
    variance, which is safer for real-world product data where group
    variances almost always differ.

    Args:
        series_a: Array-like of values for group A.
        series_b: Array-like of values for group B.
        alpha: Significance threshold (default 0.05).

    Returns:
        dict with keys: test, p_value, t_stat, significant, mean_a, mean_b,
        diff, effect_size, effect_label, interpretation.
    """
    a = np.asarray(series_a, dtype=float)
    b = np.asarray(series_b, dtype=float)

    t_stat, p_value = stats.ttest_ind(a, b, equal_var=False)

    mean_a = float(np.mean(a))
    mean_b = float(np.mean(b))
    diff = mean_b - mean_a

    # Cohen's d (pooled standard deviation)
    n_a, n_b = len(a), len(b)
    var_a, var_b = float(np.var(a, ddof=1)), float(np.var(b, ddof=1))
    pooled_std = math.sqrt(((n_a - 1) * var_a + (n_b - 1) * var_b) / (n_a + n_b - 2))
    cohens_d = diff / pooled_std if pooled_std > 0 else 0.0

    return {
        "test": "welch_t",
        "p_value": float(p_value),
        "t_stat": float(t_stat),
        "significant": bool(p_value < alpha),
        "mean_a": mean_a,
        "mean_b": mean_b,
        "diff": float(diff),
        "effect_size": float(cohens_d),
        "effect_label": interpret_effect_size(cohens_d),
        "interpretation": format_significance(p_value, alpha),
    }


# ---------------------------------------------------------------------------
# Non-parametric comparison (skewed data — revenue, session duration)
# ---------------------------------------------------------------------------

def mann_whitney_test(series_a, series_b, alpha=0.05):
    """Mann-Whitney U test for comparing distributions.

    Use this when data is skewed (e.g. revenue, session duration, order
    totals) and the t-test's normality assumption is questionable.

    Args:
        series_a: Array-like of values for group A.
        series_b: Array-like of values for group B.
        alpha: Significance threshold (default 0.05).

    Returns:
        dict with keys: test, p_value, u_stat, significant, median_a,
        median_b, rank_biserial, interpretation.
    """
    a = np.asarray(series_a, dtype=float)
    b = np.asarray(series_b, dtype=float)

    u_stat, p_value = stats.mannwhitneyu(a, b, alternative="two-sided")

    # Rank-biserial correlation: effect-size measure for Mann-Whitney
    # r = 1 - (2U) / (n1 * n2)
    n_a, n_b = len(a), len(b)
    rank_biserial = 1 - (2 * u_stat) / (n_a * n_b) if (n_a * n_b) > 0 else 0.0

    return {
        "test": "mann_whitney_u",
        "p_value": float(p_value),
        "u_stat": float(u_stat),
        "significant": bool(p_value < alpha),
        "median_a": float(np.median(a)),
        "median_b": float(np.median(b)),
        "rank_biserial": float(rank_biserial),
        "interpretation": format_significance(p_value, alpha),
    }


# ---------------------------------------------------------------------------
# Confidence interval (single sample)
# ---------------------------------------------------------------------------

def confidence_interval(series, confidence=0.95):
    """Compute a confidence interval for the mean of a single sample.

    Args:
        series: Array-like of numeric values.
        confidence: Confidence level (default 0.95 for a 95% CI).

    Returns:
        dict with keys: mean, ci_lower, ci_upper, std, n, confidence.
    """
    a = np.asarray(series, dtype=float)
    n = len(a)
    mean = float(np.mean(a))
    std = float(np.std(a, ddof=1))
    se = std / math.sqrt(n)

    # Use t-distribution for small samples
    t_crit = stats.t.ppf((1 + confidence) / 2, df=n - 1)
    margin = t_crit * se

    return {
        "mean": mean,
        "ci_lower": float(mean - margin),
        "ci_upper": float(mean + margin),
        "std": std,
        "n": n,
        "confidence": confidence,
    }


# ---------------------------------------------------------------------------
# Chi-squared test (contingency tables)
# ---------------------------------------------------------------------------

def chi_squared_test(observed_table, alpha=0.05):
    """Chi-squared test of independence for a contingency table.

    Use this for categorical vs. categorical comparisons, e.g. "Does
    acquisition channel affect plan choice?"

    Args:
        observed_table: 2D array-like or pandas DataFrame of observed counts.
        alpha: Significance threshold (default 0.05).

    Returns:
        dict with keys: test, p_value, chi2_stat, significant, dof,
        expected, interpretation.
    """
    observed = np.asarray(observed_table)
    chi2_stat, p_value, dof, expected = stats.chi2_contingency(observed)

    return {
        "test": "chi_squared",
        "p_value": float(p_value),
        "chi2_stat": float(chi2_stat),
        "significant": bool(p_value < alpha),
        "dof": int(dof),
        "expected": expected,
        "interpretation": format_significance(p_value, alpha),
    }


# ---------------------------------------------------------------------------
# Bootstrap confidence interval (non-parametric)
# ---------------------------------------------------------------------------

def bootstrap_ci(series, stat_func=None, n_bootstrap=1000, confidence=0.95):
    """Non-parametric confidence interval via bootstrapping.

    Useful when you cannot assume a distribution shape — e.g. median
    revenue, 90th-percentile latency, or any custom statistic.

    Args:
        series: Array-like of numeric values.
        stat_func: Callable that takes an array and returns a scalar.
            Defaults to np.mean if None.
        n_bootstrap: Number of bootstrap resamples (default 1000).
        confidence: Confidence level (default 0.95).

    Returns:
        dict with keys: stat, ci_lower, ci_upper, n_bootstrap, confidence.
    """
    if stat_func is None:
        stat_func = np.mean

    a = np.asarray(series, dtype=float)
    observed_stat = float(stat_func(a))

    # Bootstrap resampling
    rng = np.random.default_rng()
    boot_stats = np.array([
        stat_func(rng.choice(a, size=len(a), replace=True))
        for _ in range(n_bootstrap)
    ])

    # Percentile method
    alpha_half = (1 - confidence) / 2
    ci_lower = float(np.percentile(boot_stats, 100 * alpha_half))
    ci_upper = float(np.percentile(boot_stats, 100 * (1 - alpha_half)))

    return {
        "stat": observed_stat,
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
        "n_bootstrap": n_bootstrap,
        "confidence": confidence,
    }


# ---------------------------------------------------------------------------
# Multiple-testing correction
# ---------------------------------------------------------------------------

def adjust_pvalues(pvalues, method="benjamini-hochberg"):
    """Adjust p-values for multiple comparisons.

    When running many statistical tests at once (e.g. comparing 10 segments),
    some will appear significant by chance. This function corrects for that.

    Args:
        pvalues: List or array of raw p-values.
        method: "benjamini-hochberg" (default, controls FDR),
                "bonferroni" (controls FWER, most conservative),
                "holm" (step-down Bonferroni, less conservative).

    Returns:
        dict with keys: adjusted, method, n_significant_raw,
        n_significant_adjusted, interpretation.
    """
    pvals = np.asarray(pvalues, dtype=float)
    n = len(pvals)

    if n == 0:
        return {
            "adjusted": [],
            "method": method,
            "n_significant_raw": 0,
            "n_significant_adjusted": 0,
            "interpretation": "No p-values provided.",
        }

    if method == "bonferroni":
        adjusted = np.minimum(pvals * n, 1.0)

    elif method == "holm":
        # Sort ascending, apply step-down correction, then unsort
        order = np.argsort(pvals)
        sorted_pvals = pvals[order]
        adjusted_sorted = np.zeros(n)
        for i in range(n):
            adjusted_sorted[i] = sorted_pvals[i] * (n - i)
        # Enforce monotonicity (each value >= previous)
        for i in range(1, n):
            adjusted_sorted[i] = max(adjusted_sorted[i], adjusted_sorted[i - 1])
        adjusted_sorted = np.minimum(adjusted_sorted, 1.0)
        # Unsort back to original order
        adjusted = np.zeros(n)
        adjusted[order] = adjusted_sorted

    elif method == "benjamini-hochberg":
        # Sort ascending by p-value
        order = np.argsort(pvals)
        sorted_pvals = pvals[order]
        adjusted_sorted = np.zeros(n)
        for i in range(n):
            rank = i + 1
            adjusted_sorted[i] = sorted_pvals[i] * n / rank
        # Enforce monotonicity (step down from the largest rank)
        for i in range(n - 2, -1, -1):
            adjusted_sorted[i] = min(adjusted_sorted[i], adjusted_sorted[i + 1])
        adjusted_sorted = np.minimum(adjusted_sorted, 1.0)
        # Unsort back to original order
        adjusted = np.zeros(n)
        adjusted[order] = adjusted_sorted

    else:
        raise ValueError(
            f"Unknown method '{method}'. "
            "Choose 'benjamini-hochberg', 'bonferroni', or 'holm'."
        )

    n_sig_raw = int(np.sum(pvals < 0.05))
    n_sig_adj = int(np.sum(adjusted < 0.05))

    interpretation = (
        f"{n_sig_raw} of {n} tests significant before correction; "
        f"{n_sig_adj} after {method} correction."
    )
    if n_sig_raw > n_sig_adj:
        interpretation += (
            f" {n_sig_raw - n_sig_adj} result(s) were likely false positives."
        )

    return {
        "adjusted": [float(p) for p in adjusted],
        "method": method,
        "n_significant_raw": n_sig_raw,
        "n_significant_adjusted": n_sig_adj,
        "interpretation": interpretation,
    }


# ---------------------------------------------------------------------------
# Distribution characterization
# ---------------------------------------------------------------------------

def characterize_distribution(series, name=None):
    """Profile a numeric series' distribution shape.

    Computes descriptive statistics, tests for normality, estimates modality,
    and produces a human-readable shape description.

    Args:
        series: pd.Series of numeric values.
        name: Optional label for the series.

    Returns:
        dict with keys: name, n, mean, median, std, min, max, p5, p25, p75,
        p95, skewness, kurtosis, normality_test, modality, shape_description.
    """
    s = pd.Series(series).dropna()
    label = name or getattr(series, "name", None) or "series"
    n = len(s)

    if n < 3:
        return {
            "name": label,
            "n": n,
            "mean": float(s.mean()) if n > 0 else None,
            "median": float(s.median()) if n > 0 else None,
            "std": None,
            "min": float(s.min()) if n > 0 else None,
            "max": float(s.max()) if n > 0 else None,
            "p5": None, "p25": None, "p75": None, "p95": None,
            "skewness": None,
            "kurtosis": None,
            "normality_test": None,
            "modality": "insufficient data",
            "shape_description": "Too few values to characterize.",
        }

    mean_val = float(s.mean())
    median_val = float(s.median())
    std_val = float(s.std())

    # Normality test — Shapiro-Wilk for small samples, D'Agostino for large
    if n < 5000:
        stat_val, p_norm = stats.shapiro(s.values)
    else:
        stat_val, p_norm = stats.normaltest(s.values)

    normality_test = {
        "statistic": float(stat_val),
        "p_value": float(p_norm),
        "is_normal": bool(p_norm >= 0.05),
    }

    # Skewness and kurtosis
    skewness = float(stats.skew(s.values))
    kurtosis = float(stats.kurtosis(s.values))  # excess kurtosis

    # Modality detection via histogram peak counting
    modality = _estimate_modality(s.values)

    # Human-readable shape description
    shape_parts = []
    if abs(skewness) < 0.5:
        shape_parts.append("approximately symmetric")
    elif skewness > 0:
        shape_parts.append("right-skewed")
    else:
        shape_parts.append("left-skewed")

    if kurtosis > 1:
        shape_parts.append("heavy-tailed")
    elif kurtosis < -1:
        shape_parts.append("light-tailed")

    if modality != "unimodal":
        shape_parts.append(modality)

    shape_description = ", ".join(shape_parts)

    return {
        "name": label,
        "n": n,
        "mean": mean_val,
        "median": median_val,
        "std": std_val,
        "min": float(s.min()),
        "max": float(s.max()),
        "p5": float(np.percentile(s.values, 5)),
        "p25": float(np.percentile(s.values, 25)),
        "p75": float(np.percentile(s.values, 75)),
        "p95": float(np.percentile(s.values, 95)),
        "skewness": skewness,
        "kurtosis": kurtosis,
        "normality_test": normality_test,
        "modality": modality,
        "shape_description": shape_description,
    }


def _estimate_modality(values):
    """Simple histogram-based modality estimate.

    Counts the number of peaks (local maxima) in a histogram of the data.
    Not meant to be rigorous — just a practical heuristic for EDA.

    Args:
        values: 1D numpy array of numeric values.

    Returns:
        str: "unimodal", "bimodal", or "multimodal".
    """
    n = len(values)
    n_bins = min(max(int(math.sqrt(n)), 10), 50)
    counts, _ = np.histogram(values, bins=n_bins)

    # Find local maxima: a bin is a peak if it is greater than both neighbors
    peaks = 0
    for i in range(1, len(counts) - 1):
        if counts[i] > counts[i - 1] and counts[i] > counts[i + 1]:
            peaks += 1

    # Edge cases: check first and last bins
    if len(counts) >= 2:
        if counts[0] > counts[1]:
            peaks += 1
        if counts[-1] > counts[-2]:
            peaks += 1

    if peaks <= 1:
        return "unimodal"
    elif peaks == 2:
        return "bimodal"
    else:
        return "multimodal"


# ---------------------------------------------------------------------------
# Dimension ranking (eta-squared / ANOVA)
# ---------------------------------------------------------------------------

def rank_dimensions(df, metric_col, dimension_cols):
    """Rank categorical dimensions by their explanatory power for a metric.

    Uses eta-squared (one-way ANOVA) to measure how much variance each
    dimension explains in the metric. Useful for identifying which segments
    matter most before deep-diving.

    Args:
        df: DataFrame with metric and dimension columns.
        metric_col: Name of the numeric metric column.
        dimension_cols: List of categorical dimension column names.

    Returns:
        list of dicts, sorted by eta_squared descending:
            [{"dimension": str, "eta_squared": float, "n_groups": int,
              "f_statistic": float, "p_value": float, "rank": int,
              "interpretation": str}]
    """
    results = []
    data = df.dropna(subset=[metric_col])

    for dim in dimension_cols:
        subset = data.dropna(subset=[dim])
        groups = [
            group[metric_col].values
            for _, group in subset.groupby(dim)
            if len(group) >= 2
        ]

        if len(groups) < 2:
            results.append({
                "dimension": dim,
                "eta_squared": 0.0,
                "n_groups": len(groups),
                "f_statistic": 0.0,
                "p_value": 1.0,
                "rank": 0,
                "interpretation": f"'{dim}' has fewer than 2 valid groups — cannot compute.",
            })
            continue

        f_stat, p_value = stats.f_oneway(*groups)

        # Eta-squared = SS_between / SS_total
        grand_mean = subset[metric_col].mean()
        ss_total = float(np.sum((subset[metric_col].values - grand_mean) ** 2))
        ss_between = sum(
            len(g) * (np.mean(g) - grand_mean) ** 2 for g in groups
        )
        eta_sq = float(ss_between / ss_total) if ss_total > 0 else 0.0

        # Effect size label
        if eta_sq < 0.01:
            effect_label = "negligible"
        elif eta_sq < 0.06:
            effect_label = "small"
        elif eta_sq < 0.14:
            effect_label = "medium"
        else:
            effect_label = "large"

        results.append({
            "dimension": dim,
            "eta_squared": eta_sq,
            "n_groups": len(groups),
            "f_statistic": float(f_stat),
            "p_value": float(p_value),
            "rank": 0,  # will be set after sorting
            "interpretation": (
                f"'{dim}' explains {eta_sq:.1%} of variance in {metric_col} "
                f"({effect_label} effect). "
                f"{format_significance(p_value)}"
            ),
        })

    # Sort by eta_squared descending and assign ranks
    results.sort(key=lambda x: x["eta_squared"], reverse=True)
    for i, r in enumerate(results):
        r["rank"] = i + 1

    return results


# ---------------------------------------------------------------------------
# Power analysis: sample size and detectable effect
# ---------------------------------------------------------------------------

def sample_size_proportion(baseline_rate, mde, alpha=0.05, power=0.80):
    """Calculate required sample size per group for a proportion test.

    Use this when planning an A/B test on a conversion rate, CTR, or any
    binary outcome. Answers: "How many users do I need per group?"

    Args:
        baseline_rate: Current conversion rate (e.g. 0.10 for 10%).
        mde: Minimum detectable effect as relative change (e.g. 0.05 for 5% lift).
        alpha: Significance level (default 0.05).
        power: Statistical power (default 0.80).

    Returns:
        dict with keys: sample_size_per_group, total_sample_size,
        baseline_rate, expected_rate, absolute_difference, interpretation.
    """
    p1 = baseline_rate
    p2 = p1 * (1 + mde)
    delta = abs(p2 - p1)

    if delta == 0:
        return {
            "sample_size_per_group": float("inf"),
            "total_sample_size": float("inf"),
            "baseline_rate": p1,
            "expected_rate": p2,
            "absolute_difference": 0.0,
            "interpretation": "MDE is zero — infinite sample required.",
        }

    z_alpha = stats.norm.ppf(1 - alpha / 2)
    z_beta = stats.norm.ppf(power)

    n = (z_alpha + z_beta) ** 2 * (p1 * (1 - p1) + p2 * (1 - p2)) / delta ** 2
    n_per_group = int(math.ceil(n))

    return {
        "sample_size_per_group": n_per_group,
        "total_sample_size": n_per_group * 2,
        "baseline_rate": float(p1),
        "expected_rate": float(p2),
        "absolute_difference": float(delta),
        "interpretation": (
            f"Need {n_per_group:,} users per group ({n_per_group * 2:,} total) "
            f"to detect a {mde:.1%} relative lift from {p1:.2%} to {p2:.2%} "
            f"with {power:.0%} power at alpha={alpha}."
        ),
    }


def sample_size_mean(baseline_mean, baseline_std, mde, alpha=0.05, power=0.80):
    """Calculate required sample size per group for a mean comparison test.

    Use this when planning an A/B test on a continuous metric (revenue per
    user, session duration, etc.). Answers: "How many users do I need?"

    Args:
        baseline_mean: Current mean value.
        baseline_std: Standard deviation of the metric.
        mde: Minimum detectable effect as absolute difference.
        alpha: Significance level (default 0.05).
        power: Statistical power (default 0.80).

    Returns:
        dict with keys: sample_size_per_group, total_sample_size,
        effect_size_d, interpretation.
    """
    if mde == 0:
        return {
            "sample_size_per_group": float("inf"),
            "total_sample_size": float("inf"),
            "effect_size_d": 0.0,
            "interpretation": "MDE is zero — infinite sample required.",
        }

    z_alpha = stats.norm.ppf(1 - alpha / 2)
    z_beta = stats.norm.ppf(power)

    n = (z_alpha + z_beta) ** 2 * 2 * baseline_std ** 2 / mde ** 2
    n_per_group = int(math.ceil(n))
    effect_d = float(mde / baseline_std) if baseline_std > 0 else 0.0

    return {
        "sample_size_per_group": n_per_group,
        "total_sample_size": n_per_group * 2,
        "effect_size_d": effect_d,
        "interpretation": (
            f"Need {n_per_group:,} observations per group ({n_per_group * 2:,} total) "
            f"to detect a difference of {mde:,.2f} (Cohen's d={effect_d:.2f}) "
            f"with {power:.0%} power at alpha={alpha}."
        ),
    }


def detectable_effect(n_per_group, baseline_rate=None, baseline_std=None,
                      alpha=0.05, power=0.80):
    """Given a fixed sample size, calculate the minimum detectable effect.

    Use this when sample size is constrained (e.g. "We only have 5,000 users
    in the test — what effect can we actually detect?"). Provide either
    baseline_rate (proportion test) or baseline_std (mean test), not both.

    Args:
        n_per_group: Available sample size per group.
        baseline_rate: If provided, calculates MDE for a proportion test.
        baseline_std: If provided, calculates MDE for a mean test.
        alpha: Significance level (default 0.05).
        power: Statistical power (default 0.80).

    Returns:
        dict with keys: mde_absolute, mde_relative (if proportion),
        interpretation.
    """
    if baseline_rate is None and baseline_std is None:
        raise ValueError("Provide either baseline_rate or baseline_std.")

    z_alpha = stats.norm.ppf(1 - alpha / 2)
    z_beta = stats.norm.ppf(power)

    if baseline_rate is not None:
        # Proportion test: solve for delta
        # Approximate: assume p2 ≈ p1 for variance term, then
        # delta = (z_alpha + z_beta) * sqrt(2 * p * (1-p) / n)
        p = baseline_rate
        mde_abs = (z_alpha + z_beta) * math.sqrt(2 * p * (1 - p) / n_per_group)
        mde_rel = float(mde_abs / p) if p > 0 else 0.0

        return {
            "mde_absolute": float(mde_abs),
            "mde_relative": mde_rel,
            "interpretation": (
                f"With {n_per_group:,} users per group, the smallest detectable "
                f"change is {mde_abs:.4f} ({mde_rel:.1%} relative) from a "
                f"baseline rate of {p:.2%} at {power:.0%} power."
            ),
        }
    else:
        # Mean test: delta = (z_alpha + z_beta) * std * sqrt(2/n)
        mde_abs = (z_alpha + z_beta) * baseline_std * math.sqrt(2 / n_per_group)
        effect_d = float(mde_abs / baseline_std) if baseline_std > 0 else 0.0

        return {
            "mde_absolute": float(mde_abs),
            "interpretation": (
                f"With {n_per_group:,} observations per group, the smallest "
                f"detectable difference is {mde_abs:,.2f} "
                f"(Cohen's d={effect_d:.2f}) at {power:.0%} power."
            ),
        }
