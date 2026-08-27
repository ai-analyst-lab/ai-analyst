"""
Regression adjustment for causal inference.

Estimates treatment effects by including treatment indicator and covariates
in an OLS regression. Simpler than matching but stronger assumptions.

Mandatory caveat: "Assumes all relevant confounders are included and the
model is correctly specified."
"""

import numpy as np
import pandas as pd
import statsmodels.api as sm


CAVEAT = (
    "CAUSAL CAVEAT: Regression adjustment assumes all relevant confounders "
    "are included in the model and the relationship between covariates and "
    "outcome is correctly specified (linear). Omitted variable bias is the "
    "primary threat."
)


def regression_adjust(df, outcome_col, treatment_col, covariates, alpha=0.05):
    """Estimate treatment effect via OLS regression adjustment.

    Model: Y = b0 + b1*treatment + b2*X1 + b3*X2 + ... + e
    The coefficient b1 is the average treatment effect conditional on covariates.

    Args:
        df: DataFrame with outcome, treatment, and covariates.
        outcome_col: column name for outcome variable.
        treatment_col: column name for treatment indicator (0/1).
        covariates: list of covariate column names.
        alpha: significance level (default 0.05).

    Returns:
        dict with: estimate, ci_lower, ci_upper, p_value, significant,
        r_squared, covariate_effects, caveat, interpretation.
    """
    all_cols = [outcome_col, treatment_col] + covariates
    missing = [c for c in all_cols if c not in df.columns]
    if missing:
        return {"error": f"Missing columns: {missing}",
                "interpretation": f"Columns {missing} not found."}

    df = df.dropna(subset=all_cols).copy()

    if len(df) < len(covariates) + 3:
        return {"error": "Too few observations for this many covariates",
                "interpretation": "Need more data than parameters."}

    y = df[outcome_col].astype(float)

    # Build X: numeric covariates pass through, string/categorical covariates
    # are one-hot encoded (drop_first=True to avoid collinearity).
    X_parts = [df[[treatment_col]].astype(float).reset_index(drop=True)]
    expanded_cov_names = []
    cov_source_map = {}  # expanded name -> original covariate name
    for cov in covariates:
        series = df[cov]
        if series.dtype == "object" or str(series.dtype).startswith("category"):
            dummies = pd.get_dummies(series, prefix=cov, drop_first=True).astype(float)
            X_parts.append(dummies.reset_index(drop=True))
            for dummy_col in dummies.columns:
                expanded_cov_names.append(dummy_col)
                cov_source_map[dummy_col] = cov
        else:
            X_parts.append(series.astype(float).reset_index(drop=True).to_frame(cov))
            expanded_cov_names.append(cov)
            cov_source_map[cov] = cov

    X = sm.add_constant(pd.concat(X_parts, axis=1))

    try:
        model = sm.OLS(y.reset_index(drop=True), X).fit(cov_type="HC1")
    except Exception as e:
        return {"error": str(e), "interpretation": f"OLS failed: {e}"}

    estimate = float(model.params[treatment_col])
    ci = model.conf_int(alpha=alpha).loc[treatment_col]
    ci_lower, ci_upper = float(ci[0]), float(ci[1])
    p_value = float(model.pvalues[treatment_col])
    significant = bool(p_value < alpha)

    # Covariate effects summary (expanded form, one row per dummy/numeric)
    cov_effects = []
    for expanded in expanded_cov_names:
        cov_effects.append({
            "covariate": expanded,
            "source": cov_source_map[expanded],
            "coefficient": float(model.params[expanded]),
            "p_value": float(model.pvalues[expanded]),
            "significant": bool(model.pvalues[expanded] < alpha),
        })

    sig_label = "significant" if significant else "not significant"
    interp = (
        f"Regression-adjusted treatment effect = {estimate:+.4f}, "
        f"p = {p_value:.4f} ({sig_label}). "
        f"95% CI: [{ci_lower:+.4f}, {ci_upper:+.4f}]. "
        f"R² = {model.rsquared:.3f}. "
        f"Controlled for {len(covariates)} covariate(s). "
        f"{CAVEAT}"
    )

    return {
        "estimate": estimate,
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
        "p_value": p_value,
        "significant": significant,
        "r_squared": float(model.rsquared),
        "adj_r_squared": float(model.rsquared_adj),
        "n": len(df),
        "covariate_effects": cov_effects,
        "method": "ols_regression_adjustment",
        "alpha": alpha,
        "caveat": CAVEAT,
        "confidence_level": "LOW_MODERATE",
        "interpretation": interp,
    }
