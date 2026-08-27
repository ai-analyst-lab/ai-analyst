"""
Sequential testing for experiments with continuous monitoring.

Implements confidence sequences (always-valid confidence intervals) that
maintain coverage at any stopping time. Unlike fixed-horizon tests,
sequential methods let you peek at results without inflating Type I error.

Based on: Waudby-Smith & Ramdas (2021) — "Estimating Means of Bounded
Random Variables by Betting."
"""

import math

import numpy as np
import pandas as pd
from scipy import stats


def confidence_sequence(data, alpha=0.05, method="normal_mixture"):
    """Compute a confidence sequence (always-valid CI) at each time point.

    The CI is valid at ANY stopping time, not just a pre-specified one.
    Width shrinks as more data arrives but always maintains coverage.

    Args:
        data: array-like of sequential observations (e.g., per-user metric
            differences treatment - control, in order of arrival).
        alpha: significance level (default 0.05). CI has (1-alpha) coverage
            at EVERY time point simultaneously.
        method: "normal_mixture" (default) — uses conjugate normal mixture
            martingale. Good for most experiment metrics.

    Returns:
        dict with: running_mean (list), ci_lower (list), ci_upper (list),
        rejected_at (first index where CI excludes 0, or None),
        final_mean, final_ci, interpretation.
    """
    data = np.asarray(data, dtype=float)
    data = data[~np.isnan(data)]
    n = len(data)

    if n < 2:
        return {
            "error": "Need at least 2 observations",
            "interpretation": "Insufficient data for confidence sequence.",
        }

    running_mean = []
    ci_lower = []
    ci_upper = []
    rejected_at = None

    cumsum = 0.0
    cumsum_sq = 0.0

    for t in range(1, n + 1):
        cumsum += data[t - 1]
        cumsum_sq += data[t - 1] ** 2
        mean_t = cumsum / t

        if t < 2:
            # Not enough data for variance estimate yet
            running_mean.append(float(mean_t))
            ci_lower.append(float("-inf"))
            ci_upper.append(float("inf"))
            continue

        # Variance estimate
        var_t = (cumsum_sq - cumsum**2 / t) / (t - 1)
        std_t = math.sqrt(max(var_t, 1e-12))

        # Normal mixture confidence sequence width
        # w(t) = sqrt(2 * var * (log(log(2t)) + 0.72 * log(5.2/alpha)) / t)
        # This is the Robbins / Darling-Robbins form
        log_log_term = math.log(max(math.log(2 * t), 1e-10))
        boundary = math.sqrt(
            2 * var_t * (log_log_term + 0.72 * math.log(5.2 / alpha)) / t
        )

        running_mean.append(float(mean_t))
        ci_lower.append(float(mean_t - boundary))
        ci_upper.append(float(mean_t + boundary))

        if rejected_at is None and (mean_t - boundary > 0 or mean_t + boundary < 0):
            rejected_at = t

    final_mean = running_mean[-1]
    final_lower = ci_lower[-1]
    final_upper = ci_upper[-1]

    if rejected_at is not None:
        interp = (
            f"Confidence sequence rejected null at observation {rejected_at} of {n}. "
            f"Final mean = {final_mean:.4f}, always-valid CI = [{final_lower:.4f}, {final_upper:.4f}]."
        )
    else:
        interp = (
            f"Confidence sequence has not rejected null after {n} observations. "
            f"Final mean = {final_mean:.4f}, always-valid CI = [{final_lower:.4f}, {final_upper:.4f}]. "
            f"CI still includes 0."
        )

    return {
        "running_mean": running_mean,
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
        "rejected_at": rejected_at,
        "n_observations": n,
        "final_mean": float(final_mean),
        "final_ci_lower": float(final_lower),
        "final_ci_upper": float(final_upper),
        "alpha": alpha,
        "method": method,
        "interpretation": interp,
    }


def always_valid_pvalue(data, null_mean=0.0):
    """Compute an always-valid p-value (e-value based) for sequential testing.

    Unlike fixed-horizon p-values, this p-value is valid at ANY stopping time.
    It will NOT be inflated by peeking.

    Uses the mixture martingale approach: the e-value is the running product
    of likelihood ratios under a mixture alternative.

    Args:
        data: array-like of sequential observations (e.g., treatment - control
            differences, in arrival order).
        null_mean: the null hypothesis value (default 0.0).

    Returns:
        dict with: p_value (always-valid), e_value (evidence against null),
        n_observations, sample_mean, interpretation.
    """
    data = np.asarray(data, dtype=float)
    data = data[~np.isnan(data)]
    n = len(data)

    if n < 2:
        return {
            "error": "Need at least 2 observations",
            "interpretation": "Insufficient data.",
        }

    centered = data - null_mean
    mean = float(centered.mean())
    var = float(centered.var(ddof=1))

    if var == 0:
        return {
            "p_value": 0.0 if mean != 0 else 1.0,
            "e_value": float("inf") if mean != 0 else 1.0,
            "n_observations": n,
            "sample_mean": float(data.mean()),
            "interpretation": "Zero variance — all values identical.",
        }

    # Compute running e-value using normal likelihood ratio with mixing
    # E_t = prod_{i=1}^{t} (1 + lambda * (X_i - mu_0))
    # where lambda is chosen adaptively from past data
    log_e = 0.0
    running_sum = 0.0
    running_ss = 0.0

    for t in range(n):
        x = centered[t]

        if t == 0:
            # No past data yet — use conservative lambda
            lam = 0.0
        else:
            # Adaptive lambda = past_mean / past_variance (plug-in)
            past_mean = running_sum / t
            past_var = (running_ss / t - past_mean**2) if t > 1 else 1.0
            past_var = max(past_var, 1e-10)
            # Clip lambda to prevent explosion
            lam = min(past_mean / past_var, 1.0 / math.sqrt(past_var))
            lam = max(lam, -1.0 / math.sqrt(past_var))

        running_sum += x
        running_ss += x**2

        increment = 1 + lam * x
        if increment > 0:
            log_e += math.log(increment)
        else:
            # Clip at a small positive value to avoid log(0)
            log_e += math.log(1e-10)

    e_value = math.exp(min(log_e, 500))  # cap to prevent overflow
    p_value = min(1.0 / max(e_value, 1e-10), 1.0)

    sample_mean = float(data.mean())
    if p_value < 0.05:
        interp = (
            f"Always-valid p-value = {p_value:.4f} (e-value = {e_value:.2f}). "
            f"Evidence against null (mean = {null_mean}) after {n} observations. "
            f"Sample mean = {sample_mean:.4f}. This p-value is valid regardless "
            f"of when you stopped collecting data."
        )
    else:
        interp = (
            f"Always-valid p-value = {p_value:.4f} (e-value = {e_value:.2f}). "
            f"Insufficient evidence against null (mean = {null_mean}) after {n} "
            f"observations. Sample mean = {sample_mean:.4f}."
        )

    return {
        "p_value": float(p_value),
        "e_value": float(e_value),
        "n_observations": n,
        "sample_mean": sample_mean,
        "null_mean": null_mean,
        "interpretation": interp,
    }
