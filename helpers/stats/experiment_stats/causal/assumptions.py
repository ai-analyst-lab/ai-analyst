"""
Assumption checking utilities for causal inference methods.

Each causal method has specific assumptions that must hold for the estimate
to be valid. These functions test those assumptions quantitatively.
"""

import numpy as np
import pandas as pd
import statsmodels.api as sm


def check_parallel_trends(df, outcome_col, treat_col, time_col,
                          intervention_time, alpha=0.05):
    """Check the parallel trends assumption for DiD.

    Tests whether treatment and control groups had similar outcome trends
    in the pre-intervention period. This is the key assumption for DiD.

    Args:
        df: DataFrame with panel data.
        outcome_col: outcome variable column.
        treat_col: treatment indicator column (0/1).
        time_col: time period column.
        intervention_time: time when intervention occurred.
        alpha: significance level.

    Returns:
        dict with: verdict (PASS/WARNING/FAIL), p_value,
        pre_trend_difference, interpretation.
    """
    pre_df = df[df[time_col] < intervention_time].copy()

    if len(pre_df) < 4:
        return {
            "assumption": "parallel_trends",
            "verdict": "INSUFFICIENT_DATA",
            "interpretation": "Not enough pre-period observations to assess.",
        }

    # Numeric time
    if pd.api.types.is_datetime64_any_dtype(pre_df[time_col]):
        min_t = pre_df[time_col].min()
        pre_df["_time_num"] = (pre_df[time_col] - min_t).dt.days.astype(float)
    else:
        pre_df["_time_num"] = pre_df[time_col].astype(float)

    pre_df["_interact"] = pre_df[treat_col].astype(float) * pre_df["_time_num"]

    X = sm.add_constant(pre_df[[treat_col, "_time_num", "_interact"]].astype(float))
    y = pre_df[outcome_col].astype(float)

    try:
        model = sm.OLS(y, X).fit(cov_type="HC1")
    except Exception as e:
        return {
            "assumption": "parallel_trends",
            "verdict": "ERROR",
            "interpretation": f"Regression failed: {e}",
        }

    p_interact = float(model.pvalues["_interact"])
    trend_diff = float(model.params["_interact"])

    if p_interact > 0.10:
        verdict = "PASS"
        note = "Pre-period trends are parallel. DiD assumption is supported."
    elif p_interact > alpha:
        verdict = "WARNING"
        note = "Marginal evidence of trend divergence. Interpret DiD with caution."
    else:
        verdict = "FAIL"
        note = (
            "Significant pre-period trend divergence. Parallel trends assumption "
            "is likely violated. DiD estimates may be biased."
        )

    return {
        "assumption": "parallel_trends",
        "verdict": verdict,
        "p_value": p_interact,
        "pre_trend_difference": trend_diff,
        "n_pre_observations": len(pre_df),
        "interpretation": f"Parallel trends: {note} (p = {p_interact:.4f}).",
    }


def check_common_support(propensity_scores, treatment, threshold=0.05):
    """Check the common support (overlap) assumption for PSM.

    Verifies that treatment and control groups have overlapping propensity
    score distributions. Without overlap, matching is extrapolating.

    Args:
        propensity_scores: array-like of estimated propensity scores.
        treatment: array-like of treatment indicators (0/1).
        threshold: proportion of units outside overlap region that triggers
            a warning (default 0.05 = 5%).

    Returns:
        dict with: verdict (PASS/WARNING/FAIL), overlap_region,
        n_outside_support, pct_outside, interpretation.
    """
    ps = np.asarray(propensity_scores, dtype=float)
    treat = np.asarray(treatment, dtype=int)

    ps_treat = ps[treat == 1]
    ps_ctrl = ps[treat == 0]

    if len(ps_treat) < 2 or len(ps_ctrl) < 2:
        return {
            "assumption": "common_support",
            "verdict": "INSUFFICIENT_DATA",
            "interpretation": "Not enough observations to assess overlap.",
        }

    # Overlap region
    overlap_min = max(ps_treat.min(), ps_ctrl.min())
    overlap_max = min(ps_treat.max(), ps_ctrl.max())

    if overlap_min >= overlap_max:
        return {
            "assumption": "common_support",
            "verdict": "FAIL",
            "overlap_region": None,
            "interpretation": "No overlap in propensity scores. Matching is impossible.",
        }

    # Count units outside overlap
    n_treat_outside = int(((ps_treat < overlap_min) | (ps_treat > overlap_max)).sum())
    n_ctrl_outside = int(((ps_ctrl < overlap_min) | (ps_ctrl > overlap_max)).sum())
    n_total = len(ps)
    n_outside = n_treat_outside + n_ctrl_outside
    pct_outside = n_outside / n_total

    if pct_outside <= threshold:
        verdict = "PASS"
        note = "Good overlap in propensity scores."
    elif pct_outside <= 0.20:
        verdict = "WARNING"
        note = (
            f"{pct_outside:.1%} of units are outside the overlap region. "
            f"Consider trimming these units before matching."
        )
    else:
        verdict = "FAIL"
        note = (
            f"{pct_outside:.1%} of units are outside the overlap region. "
            f"Poor overlap — matching will rely heavily on extrapolation."
        )

    return {
        "assumption": "common_support",
        "verdict": verdict,
        "overlap_region": [float(overlap_min), float(overlap_max)],
        "n_treat_outside": n_treat_outside,
        "n_ctrl_outside": n_ctrl_outside,
        "pct_outside": float(pct_outside),
        "ps_treat_range": [float(ps_treat.min()), float(ps_treat.max())],
        "ps_ctrl_range": [float(ps_ctrl.min()), float(ps_ctrl.max())],
        "interpretation": f"Common support: {note}",
    }
