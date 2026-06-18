"""
Propensity Score Matching (PSM) for causal inference.

Estimates causal effects by matching treatment units to similar control units
based on propensity scores (probability of receiving treatment).

Mandatory caveat: "Controls for observed confounders only. Unmeasured factors
could bias this estimate."
"""

import math

import numpy as np
import pandas as pd
from scipy.spatial import KDTree
from sklearn.linear_model import LogisticRegression


CAVEAT = (
    "CAUSAL CAVEAT: Propensity score matching controls for observed confounders "
    "only. Any unmeasured factor that influences both treatment assignment and "
    "the outcome could bias this estimate. Check sensitivity analysis for how "
    "large an unmeasured confounder would need to be to overturn the result."
)


def propensity_match(df, treat_col, covariates, outcome_col=None,
                     method="nearest", caliper=0.2, replacement=False,
                     alpha=0.05):
    """Full propensity score matching pipeline.

    Steps: (1) estimate propensity scores via logistic regression,
    (2) match treatment to control units, (3) estimate treatment effect.

    Args:
        df: DataFrame with treatment indicator, covariates, and outcome.
        treat_col: column name for treatment indicator (0/1).
        covariates: list of covariate column names to match on.
        outcome_col: column for outcome variable. If provided, estimates ATT.
        method: matching method — "nearest" (default).
        caliper: maximum propensity score distance for a match (default 0.2
            standard deviations of the logit propensity score).
        replacement: allow matching with replacement (default False).
        alpha: significance level.

    Returns:
        dict with: matched_df (DataFrame of matched pairs), n_matched,
        n_unmatched_treatment, propensity_model_accuracy,
        ate (if outcome provided), ci_lower, ci_upper, p_value,
        caveat, interpretation.
    """
    missing_cols = [c for c in covariates if c not in df.columns]
    if missing_cols:
        return {"error": f"Missing covariates: {missing_cols}",
                "interpretation": f"Columns {missing_cols} not found."}

    if treat_col not in df.columns:
        return {"error": f"Treatment column '{treat_col}' not found",
                "interpretation": f"Column '{treat_col}' not found."}

    df = df.dropna(subset=[treat_col] + covariates).copy()
    df[treat_col] = df[treat_col].astype(int)

    treated = df[df[treat_col] == 1]
    control = df[df[treat_col] == 0]

    if len(treated) < 2 or len(control) < 2:
        return {"error": "Need at least 2 observations per group",
                "interpretation": "Insufficient data for matching."}

    # Step 1: Estimate propensity scores
    X = df[covariates].astype(float)
    y = df[treat_col]

    lr = LogisticRegression(max_iter=1000, random_state=42)
    lr.fit(X, y)

    df = df.copy()
    df["_propensity"] = lr.predict_proba(X)[:, 1]
    accuracy = float(lr.score(X, y))

    # Logit transform for matching (better distance properties)
    df["_logit_ps"] = np.log(df["_propensity"].clip(0.001, 0.999) /
                             (1 - df["_propensity"].clip(0.001, 0.999)))

    # Caliper in logit-PS standard deviations
    logit_std = df["_logit_ps"].std()
    caliper_abs = caliper * logit_std if logit_std > 0 else caliper

    # Step 2: Match
    treated_df = df[df[treat_col] == 1].copy()
    control_df = df[df[treat_col] == 0].copy()

    control_tree = KDTree(control_df[["_logit_ps"]].values)

    matched_treat_idx = []
    matched_ctrl_idx = []
    used_controls = set()

    for idx, row in treated_df.iterrows():
        dist, nearest_idx = control_tree.query([row["_logit_ps"]], k=min(10, len(control_df)))

        if np.isscalar(dist):
            dist = [dist]
            nearest_idx = [nearest_idx]

        found = False
        for d, ci in zip(dist, nearest_idx):
            ctrl_idx = control_df.index[ci]
            if d <= caliper_abs and (replacement or ctrl_idx not in used_controls):
                matched_treat_idx.append(idx)
                matched_ctrl_idx.append(ctrl_idx)
                used_controls.add(ctrl_idx)
                found = True
                break

    n_matched = len(matched_treat_idx)
    n_unmatched = len(treated_df) - n_matched
    attrition_pct = (n_unmatched / len(treated_df) * 100) if len(treated_df) > 0 else 0.0

    # Attrition warning: PSM silently dropping a large share of treated units
    # changes *who* the ATT describes. Flag it loudly for lesson use.
    if attrition_pct > 30:
        attrition_warning = (
            f"HIGH ATTRITION: PSM dropped {n_unmatched}/{len(treated_df)} treated "
            f"units ({attrition_pct:.1f}%) due to caliper={caliper}. The ATT now "
            f"describes only the {n_matched} treated units that had a close control "
            f"match, NOT the original treated population. Consider (a) relaxing the "
            f"caliper, (b) using a different method (regression_adjust, DiD), or "
            f"(c) reporting the ATT only for the sub-population with common support."
        )
    else:
        attrition_warning = None

    # Build matched DataFrame
    matched_treat = df.loc[matched_treat_idx].copy()
    matched_ctrl = df.loc[matched_ctrl_idx].copy()
    matched_treat["_match_id"] = range(n_matched)
    matched_ctrl["_match_id"] = range(n_matched)
    matched_df = pd.concat([matched_treat, matched_ctrl], ignore_index=True)

    result = {
        "matched_df": matched_df,
        "n_treated": len(treated_df),
        "n_control": len(control_df),
        "n_matched": n_matched,
        "n_unmatched_treatment": n_unmatched,
        "attrition_pct": round(attrition_pct, 2),
        "attrition_warning": attrition_warning,
        "propensity_model_accuracy": accuracy,
        "caliper": caliper,
        "caliper_absolute": float(caliper_abs),
        "method": method,
        "caveat": CAVEAT,
        "confidence_level": "MODERATE",
    }

    # Step 3: Estimate ATT if outcome provided
    if outcome_col and outcome_col in df.columns:
        treat_outcomes = df.loc[matched_treat_idx, outcome_col].values.astype(float)
        ctrl_outcomes = df.loc[matched_ctrl_idx, outcome_col].values.astype(float)

        diffs = treat_outcomes - ctrl_outcomes
        att = float(diffs.mean())
        se = float(diffs.std(ddof=1) / math.sqrt(n_matched)) if n_matched > 1 else float("inf")

        from scipy import stats as sp_stats
        t_stat = att / se if se > 0 else 0.0
        p_value = float(2 * (1 - sp_stats.t.cdf(abs(t_stat), n_matched - 1))) if n_matched > 1 else 1.0
        t_crit = sp_stats.t.ppf(1 - alpha / 2, n_matched - 1) if n_matched > 1 else float("inf")
        ci_lower = att - t_crit * se
        ci_upper = att + t_crit * se
        significant = bool(p_value < alpha)

        sig_label = "significant" if significant else "not significant"
        result.update({
            "att": att,
            "ci_lower": float(ci_lower),
            "ci_upper": float(ci_upper),
            "p_value": p_value,
            "t_stat": float(t_stat),
            "significant": significant,
        })

        interp = (
            f"PSM ATT = {att:+.4f}, p = {p_value:.4f} ({sig_label}). "
            f"95% CI: [{ci_lower:+.4f}, {ci_upper:+.4f}]. "
            f"Matched {n_matched}/{len(treated_df)} treated units "
            f"({n_unmatched} unmatched). "
            f"Model accuracy: {accuracy:.1%}. {CAVEAT}"
        )
    else:
        interp = (
            f"Matched {n_matched}/{len(treated_df)} treated units "
            f"({n_unmatched} unmatched, caliper = {caliper}). "
            f"Model accuracy: {accuracy:.1%}. "
            f"Provide outcome_col to estimate treatment effect."
        )

    result["interpretation"] = interp
    return result
