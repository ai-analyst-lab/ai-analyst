"""
Difference-in-Differences (DiD) for causal inference.

Compares the change in outcomes over time between a treatment group and
a control group. Stronger than pre-post because it controls for
time-invariant confounders and common trends.

Mandatory caveat: "Assumes the control group would have followed the
same trend. Plausible but unprovable."
"""

import numpy as np
import pandas as pd
import statsmodels.api as sm


CAVEAT = (
    "CAUSAL CAVEAT: DiD assumes the control group would have followed the "
    "same trend as the treatment group absent intervention (parallel trends). "
    "This assumption is plausible but unprovable. Examine the parallel trends "
    "test result and pre-period alignment."
)


def did_basic(df, outcome_col, treat_col, post_col, entity_col=None,
              covariates=None, alpha=0.05):
    """Basic 2x2 Difference-in-Differences estimator.

    Estimates: ATT = (Y_treat_post - Y_treat_pre) - (Y_ctrl_post - Y_ctrl_pre)

    Args:
        df: DataFrame with one row per observation.
        outcome_col: column name for the outcome variable.
        treat_col: column name for treatment group indicator (0/1).
        post_col: column name for post-period indicator (0/1).
        entity_col: optional column for entity (unit) fixed effects.
        covariates: optional list of covariate column names.
        alpha: significance level (default 0.05).

    Returns:
        dict with: estimate (DiD ATT), ci_lower, ci_upper, p_value,
        significant, group_means, caveat, interpretation.
    """
    required = [outcome_col, treat_col, post_col]
    missing = [c for c in required if c not in df.columns]
    if missing:
        return {
            "error": f"Missing columns: {missing}",
            "interpretation": f"Columns {missing} not found in DataFrame.",
        }

    df = df.dropna(subset=required).copy()
    df[treat_col] = df[treat_col].astype(int)
    df[post_col] = df[post_col].astype(int)

    # Group means for the 2x2 table
    means = df.groupby([treat_col, post_col])[outcome_col].mean()
    group_means = {}
    for (t, p), m in means.items():
        label = f"{'treat' if t else 'ctrl'}_{'post' if p else 'pre'}"
        group_means[label] = float(m)

    # OLS regression: Y = b0 + b1*treat + b2*post + b3*(treat*post) + covariates + e
    df["_interact"] = df[treat_col] * df[post_col]

    X_cols = [treat_col, post_col, "_interact"]
    if covariates:
        X_cols.extend([c for c in covariates if c in df.columns])

    X = sm.add_constant(df[X_cols].astype(float))
    y = df[outcome_col].astype(float)

    try:
        # Use HC1 (robust) standard errors
        model = sm.OLS(y, X).fit(cov_type="HC1")
    except Exception as e:
        return {
            "error": str(e),
            "interpretation": f"OLS failed: {e}",
        }

    estimate = float(model.params["_interact"])
    ci = model.conf_int(alpha=alpha).loc["_interact"]
    ci_lower, ci_upper = float(ci[0]), float(ci[1])
    p_value = float(model.pvalues["_interact"])
    significant = bool(p_value < alpha)

    sig_label = "significant" if significant else "not significant"
    interp = (
        f"DiD estimate (ATT) = {estimate:+.4f}, p = {p_value:.4f} ({sig_label}). "
        f"95% CI: [{ci_lower:+.4f}, {ci_upper:+.4f}]. "
        f"Group means: {group_means}. "
        f"{CAVEAT}"
    )

    return {
        "estimate": estimate,
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
        "p_value": p_value,
        "significant": significant,
        "group_means": group_means,
        "n": len(df),
        "r_squared": float(model.rsquared),
        "alpha": alpha,
        "method": "did_ols",
        "caveat": CAVEAT,
        "confidence_level": "MODERATE",
        "interpretation": interp,
    }


def parallel_trends_test(df, outcome_col, treat_col, time_col,
                         intervention_time, alpha=0.05):
    """Test the parallel trends assumption using pre-period data.

    Checks whether treatment and control groups had similar trends before
    the intervention. A significant interaction in the pre-period suggests
    the parallel trends assumption may be violated.

    Args:
        df: DataFrame with panel data.
        outcome_col: outcome variable column.
        treat_col: treatment indicator column (0/1).
        time_col: time period column (numeric or datetime).
        intervention_time: value of time_col when intervention occurs.
        alpha: significance level.

    Returns:
        dict with: verdict (PASS/WARNING/FAIL), p_value, slope_control,
        slope_treatment, interpretation.
    """
    # Filter to pre-period
    pre_df = df[df[time_col] < intervention_time].copy()

    if len(pre_df) < 4:
        return {
            "verdict": "INSUFFICIENT_DATA",
            "interpretation": "Not enough pre-period data to test parallel trends.",
        }

    # Convert time to numeric if needed
    if pd.api.types.is_datetime64_any_dtype(pre_df[time_col]):
        min_time = pre_df[time_col].min()
        pre_df["_time_numeric"] = (pre_df[time_col] - min_time).dt.days
    else:
        pre_df["_time_numeric"] = pre_df[time_col].astype(float)

    pre_df["_interact"] = pre_df[treat_col].astype(float) * pre_df["_time_numeric"]

    X = sm.add_constant(pre_df[[treat_col, "_time_numeric", "_interact"]].astype(float))
    y = pre_df[outcome_col].astype(float)

    try:
        model = sm.OLS(y, X).fit(cov_type="HC1")
    except Exception as e:
        return {"verdict": "ERROR", "interpretation": f"OLS failed: {e}"}

    p_interact = float(model.pvalues["_interact"])

    # Separate slopes
    ctrl = pre_df[pre_df[treat_col] == 0]
    treat = pre_df[pre_df[treat_col] == 1]

    def _slope(subset):
        if len(subset) < 2:
            return 0.0
        X_s = sm.add_constant(subset["_time_numeric"].astype(float))
        m = sm.OLS(subset[outcome_col].astype(float), X_s).fit()
        return float(m.params.iloc[1]) if len(m.params) > 1 else 0.0

    slope_c = _slope(ctrl)
    slope_t = _slope(treat)

    if p_interact > 0.10:
        verdict = "PASS"
        note = "No significant difference in pre-period trends."
    elif p_interact > alpha:
        verdict = "WARNING"
        note = "Marginal difference in pre-period trends. Interpret DiD results with caution."
    else:
        verdict = "FAIL"
        note = (
            "Significant difference in pre-period trends. The parallel trends "
            "assumption is likely violated. DiD results may be biased."
        )

    interp = (
        f"Parallel trends test: p = {p_interact:.4f}, verdict = {verdict}. "
        f"Pre-period slopes: control = {slope_c:.4f}, treatment = {slope_t:.4f}. "
        f"{note}"
    )

    return {
        "verdict": verdict,
        "p_value": float(p_interact),
        "slope_control": slope_c,
        "slope_treatment": slope_t,
        "n_pre_period": len(pre_df),
        "alpha": alpha,
        "interpretation": interp,
    }


def event_study(df, outcome_col, treat_col, time_col, intervention_time,
                alpha=0.05):
    """Event study plot data — period-by-period treatment effects.

    Estimates treatment effect for each time period relative to intervention,
    providing visual evidence for parallel trends (pre) and dynamic effects (post).

    Args:
        df: DataFrame with panel data.
        outcome_col: outcome variable.
        treat_col: treatment indicator (0/1).
        time_col: time period column.
        intervention_time: value of time_col when intervention occurs.
        alpha: significance level.

    Returns:
        dict with: periods (list), estimates (list), ci_lower (list),
        ci_upper (list), interpretation.
    """
    df = df.copy()

    # Create relative time
    if pd.api.types.is_datetime64_any_dtype(df[time_col]):
        time_vals = df[time_col].unique()
        time_vals = np.sort(time_vals)
        time_map = {t: i for i, t in enumerate(time_vals)}
        intervention_idx = time_map.get(intervention_time)
        if intervention_idx is None:
            # Find closest
            intervention_idx = np.searchsorted(time_vals, intervention_time)
        df["_rel_time"] = df[time_col].map(time_map) - intervention_idx
    else:
        df["_rel_time"] = df[time_col].astype(float) - float(intervention_time)

    # Drop the reference period (t = -1)
    periods = sorted(df["_rel_time"].unique())
    ref_period = -1
    if ref_period not in periods:
        # Use the last pre-period as reference
        pre_periods = [p for p in periods if p < 0]
        ref_period = max(pre_periods) if pre_periods else periods[0]

    # Create period dummies interacted with treatment
    results = []
    for period in periods:
        if period == ref_period:
            results.append({
                "period": int(period),
                "estimate": 0.0,
                "ci_lower": 0.0,
                "ci_upper": 0.0,
                "p_value": 1.0,
            })
            continue

        period_df = df[df["_rel_time"].isin([ref_period, period])].copy()
        period_df["_is_period"] = (period_df["_rel_time"] == period).astype(int)
        period_df["_interact"] = period_df[treat_col].astype(int) * period_df["_is_period"]

        X = sm.add_constant(
            period_df[[treat_col, "_is_period", "_interact"]].astype(float)
        )
        y = period_df[outcome_col].astype(float)

        try:
            model = sm.OLS(y, X).fit(cov_type="HC1")
            est = float(model.params["_interact"])
            ci = model.conf_int(alpha=alpha).loc["_interact"]
            results.append({
                "period": int(period),
                "estimate": est,
                "ci_lower": float(ci[0]),
                "ci_upper": float(ci[1]),
                "p_value": float(model.pvalues["_interact"]),
            })
        except Exception:
            results.append({
                "period": int(period),
                "estimate": float("nan"),
                "ci_lower": float("nan"),
                "ci_upper": float("nan"),
                "p_value": float("nan"),
            })

    periods_out = [r["period"] for r in results]
    estimates = [r["estimate"] for r in results]
    ci_lower = [r["ci_lower"] for r in results]
    ci_upper = [r["ci_upper"] for r in results]

    # Check pre-period: any significant effects suggest parallel trends violation
    pre_sig = [r for r in results if r["period"] < 0 and r["p_value"] < alpha]

    if pre_sig:
        interp = (
            f"Event study: {len(pre_sig)} pre-period coefficient(s) are significant, "
            f"suggesting possible parallel trends violation. Interpret with caution."
        )
    else:
        interp = (
            f"Event study: no significant pre-period effects (parallel trends look OK). "
            f"Reference period = {ref_period}."
        )

    return {
        "periods": periods_out,
        "estimates": estimates,
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
        "reference_period": int(ref_period),
        "pre_period_violations": len(pre_sig),
        "results": results,
        "interpretation": interp,
    }
