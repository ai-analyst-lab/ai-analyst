"""
Balance diagnostics for propensity score matching.

After matching, verify that treatment and control groups are balanced on
covariates. Key metric: Standardized Mean Difference (SMD) < 0.1.
"""

import math

import numpy as np
import pandas as pd


def balance_table(df, covariates, treat_col, matched=True):
    """Compute balance diagnostics for each covariate.

    Calculates Standardized Mean Difference (SMD) and variance ratio for
    each covariate between treatment and control groups.

    Args:
        df: DataFrame (matched or unmatched).
        covariates: list of covariate column names.
        treat_col: treatment indicator column (0/1).
        matched: whether this is a matched sample (affects interpretation).

    Returns:
        dict with: table (list of per-covariate dicts), balanced (bool),
        n_imbalanced, interpretation.
    """
    df = df.dropna(subset=[treat_col]).copy()
    treat = df[df[treat_col] == 1]
    ctrl = df[df[treat_col] == 0]

    rows = []
    n_imbalanced = 0

    for cov in covariates:
        if cov not in df.columns:
            continue

        t_vals = treat[cov].dropna().astype(float)
        c_vals = ctrl[cov].dropna().astype(float)

        if len(t_vals) < 2 or len(c_vals) < 2:
            rows.append({
                "covariate": cov,
                "mean_treatment": float(t_vals.mean()) if len(t_vals) > 0 else None,
                "mean_control": float(c_vals.mean()) if len(c_vals) > 0 else None,
                "smd": None,
                "variance_ratio": None,
                "balanced": None,
                "note": "Insufficient data",
            })
            continue

        mean_t = float(t_vals.mean())
        mean_c = float(c_vals.mean())
        var_t = float(t_vals.var(ddof=1))
        var_c = float(c_vals.var(ddof=1))

        # SMD = (mean_t - mean_c) / sqrt((var_t + var_c) / 2)
        pooled_sd = math.sqrt((var_t + var_c) / 2)
        smd = abs(mean_t - mean_c) / pooled_sd if pooled_sd > 0 else 0.0

        # Variance ratio (should be close to 1)
        var_ratio = var_t / var_c if var_c > 0 else float("inf")

        balanced = smd < 0.1
        if not balanced:
            n_imbalanced += 1

        rows.append({
            "covariate": cov,
            "mean_treatment": mean_t,
            "mean_control": mean_c,
            "smd": float(smd),
            "variance_ratio": float(var_ratio),
            "balanced": balanced,
        })

    all_balanced = n_imbalanced == 0
    sample_label = "matched" if matched else "unmatched"

    if all_balanced:
        interp = (
            f"All {len(rows)} covariates are balanced (SMD < 0.1) in the "
            f"{sample_label} sample. Good overlap between groups."
        )
    else:
        imbalanced = [r["covariate"] for r in rows if r.get("balanced") is False]
        interp = (
            f"{n_imbalanced} of {len(rows)} covariates are imbalanced (SMD >= 0.1) "
            f"in the {sample_label} sample: {', '.join(imbalanced)}. "
            f"Consider adjusting matching or including these as regression covariates."
        )

    return {
        "table": rows,
        "balanced": all_balanced,
        "n_imbalanced": n_imbalanced,
        "n_covariates": len(rows),
        "sample_type": sample_label,
        "interpretation": interp,
    }


def love_plot(balance_before, balance_after=None):
    """Generate Love plot data comparing balance before and after matching.

    A Love plot shows SMD for each covariate, with a vertical line at 0.1
    threshold. Points should move toward zero after matching.

    Args:
        balance_before: result from balance_table() on unmatched data.
        balance_after: result from balance_table() on matched data (optional).

    Returns:
        dict with: plot_data (list of dicts for plotting), improved (list
        of covariates that improved), worsened (list), interpretation.
    """
    plot_data = []
    improved = []
    worsened = []

    before_map = {r["covariate"]: r for r in balance_before["table"]}

    if balance_after:
        after_map = {r["covariate"]: r for r in balance_after["table"]}
    else:
        after_map = {}

    for cov, before in before_map.items():
        entry = {
            "covariate": cov,
            "smd_before": before.get("smd"),
        }

        if cov in after_map:
            after = after_map[cov]
            entry["smd_after"] = after.get("smd")

            if before.get("smd") is not None and after.get("smd") is not None:
                if after["smd"] < before["smd"]:
                    improved.append(cov)
                elif after["smd"] > before["smd"]:
                    worsened.append(cov)

        plot_data.append(entry)

    if balance_after:
        interp = (
            f"Love plot: {len(improved)} covariates improved, "
            f"{len(worsened)} worsened after matching. "
            f"Before: {balance_before['n_imbalanced']} imbalanced, "
            f"After: {balance_after['n_imbalanced']} imbalanced."
        )
    else:
        interp = (
            f"Love plot: {balance_before['n_imbalanced']} of "
            f"{balance_before['n_covariates']} covariates imbalanced (SMD >= 0.1)."
        )

    return {
        "plot_data": plot_data,
        "improved": improved,
        "worsened": worsened,
        "threshold": 0.1,
        "interpretation": interp,
    }
