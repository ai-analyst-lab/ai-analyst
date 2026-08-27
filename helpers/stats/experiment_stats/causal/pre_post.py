"""
Pre-post analysis for causal inference.

Simplest quasi-experimental method. Compares outcomes before and after
an intervention. WEAK causal evidence — assumes nothing else changed.

Mandatory caveat: "Assumes nothing else changed during this period.
Any concurrent event could explain this result."
"""

import numpy as np
import pandas as pd
import statsmodels.api as sm


CAVEAT = (
    "CAUSAL CAVEAT: Pre-post analysis assumes nothing else changed during "
    "this period. Any concurrent event (seasonality, other product changes, "
    "external factors) could explain this result. This is the weakest form "
    "of causal evidence."
)


def pre_post_analysis(pre, post, covariates=None, alpha=0.05):
    """Pre-post comparison with optional covariate adjustment via OLS.

    Compares metric values before vs after an intervention. Optionally
    controls for covariates using regression adjustment.

    Args:
        pre: array-like of pre-period metric values (one per unit).
        post: array-like of post-period metric values (one per unit).
        covariates: optional DataFrame of covariates (aligned with pre/post).
            If provided, estimates the pre-post change controlling for these.
        alpha: significance level (default 0.05).

    Returns:
        dict with: estimate (change), ci_lower, ci_upper, p_value,
        significant, pre_mean, post_mean, method, caveat, interpretation.
    """
    pre = np.asarray(pre, dtype=float)
    post = np.asarray(post, dtype=float)

    mask = ~(np.isnan(pre) | np.isnan(post))
    pre, post = pre[mask], post[mask]

    if len(pre) < 2:
        return {
            "error": "Need at least 2 observations",
            "interpretation": "Insufficient data.",
        }

    pre_mean = float(pre.mean())
    post_mean = float(post.mean())

    if covariates is not None and len(covariates) > 0:
        # Regression-adjusted pre-post
        # Stack pre and post, add treatment indicator
        n = len(pre)
        y = np.concatenate([pre, post])
        treat = np.concatenate([np.zeros(n), np.ones(n)])

        cov_df = pd.DataFrame(covariates)
        # Stack covariates for pre and post (same units, repeated)
        cov_stacked = pd.concat([cov_df.iloc[:n].reset_index(drop=True),
                                  cov_df.iloc[:n].reset_index(drop=True)],
                                 ignore_index=True)

        X = sm.add_constant(pd.concat([
            pd.DataFrame({"post": treat}),
            cov_stacked,
        ], axis=1))

        model = sm.OLS(y, X).fit()
        estimate = float(model.params["post"])
        ci = model.conf_int(alpha=alpha).loc["post"]
        ci_lower, ci_upper = float(ci[0]), float(ci[1])
        p_value = float(model.pvalues["post"])
        method = "regression_adjusted_pre_post"
    else:
        # Simple paired pre-post (paired t-test)
        diff = post - pre
        from scipy import stats as sp_stats

        t_stat, p_value = sp_stats.ttest_rel(post, pre)
        estimate = float(diff.mean())
        se = float(diff.std(ddof=1) / np.sqrt(len(diff)))
        t_crit = sp_stats.t.ppf(1 - alpha / 2, len(diff) - 1)
        ci_lower = estimate - t_crit * se
        ci_upper = estimate + t_crit * se
        p_value = float(p_value)
        method = "paired_pre_post"

    significant = bool(p_value < alpha)
    rel_change = estimate / abs(pre_mean) * 100 if pre_mean != 0 else float("inf")

    sig_label = "significant" if significant else "not significant"
    interp = (
        f"Pre-post change: {estimate:+.4f} ({rel_change:+.1f}%), "
        f"p = {p_value:.4f} ({sig_label}). "
        f"Pre-mean = {pre_mean:.4f}, post-mean = {post_mean:.4f}. "
        f"95% CI: [{ci_lower:+.4f}, {ci_upper:+.4f}]. "
        f"Method: {method}. {CAVEAT}"
    )

    return {
        "estimate": estimate,
        "ci_lower": float(ci_lower),
        "ci_upper": float(ci_upper),
        "p_value": p_value,
        "significant": significant,
        "pre_mean": pre_mean,
        "post_mean": post_mean,
        "relative_change_pct": float(rel_change),
        "method": method,
        "n": len(pre),
        "alpha": alpha,
        "caveat": CAVEAT,
        "confidence_level": "LOW",
        "interpretation": interp,
    }


def pre_post_timeseries(df, date_col, outcome_col, post_col, covariates=None, alpha=0.05):
    """Time-series pre-post analysis for daily/weekly aggregates.

    Unlike `pre_post_analysis`, this is designed for time-series data where
    each row is a time period (not a paired unit). Fits OLS with a post-
    intervention indicator and optional covariates (e.g., day-of-week dummies
    for seasonality control).

    Args:
        df: DataFrame with one row per time period.
        date_col: column name for date/period (used for sorting only).
        outcome_col: column name for the metric to analyze.
        post_col: column name for the 0/1 post-intervention indicator.
        covariates: list of column names to include as controls. String
            columns are one-hot-encoded (drop_first=True). Numeric columns
            are passed through. None for a simple pre-post with no controls.
        alpha: significance level (default 0.05).

    Returns:
        dict with: estimate (effect of post), ci_lower, ci_upper, p_value,
        significant, pre_mean, post_mean, relative_change_pct, method (always
        "timeseries_ols"), covariates_used, n, alpha, caveat, confidence_level,
        interpretation.
    """
    df = df.sort_values(date_col).reset_index(drop=True)

    y = df[outcome_col].astype(float).values
    post = df[post_col].astype(float).values

    pre_mask = post == 0
    post_mask = post == 1
    if pre_mask.sum() < 2 or post_mask.sum() < 2:
        return {
            "error": "Need at least 2 pre and 2 post observations",
            "interpretation": "Insufficient data for pre-post timeseries.",
        }

    X_parts = [pd.DataFrame({"post": post})]
    covariates_used = []
    if covariates:
        for col in covariates:
            if col not in df.columns:
                return {
                    "error": f"Covariate column not found: {col}",
                    "interpretation": f"Column '{col}' not in dataframe.",
                }
            series = df[col]
            if series.dtype == "object" or str(series.dtype).startswith("category"):
                dummies = pd.get_dummies(series, prefix=col, drop_first=True).astype(float)
                X_parts.append(dummies.reset_index(drop=True))
                covariates_used.extend(dummies.columns.tolist())
            else:
                X_parts.append(series.astype(float).reset_index(drop=True).to_frame(col))
                covariates_used.append(col)

    X = sm.add_constant(pd.concat(X_parts, axis=1))
    model = sm.OLS(y, X).fit()

    estimate = float(model.params["post"])
    ci = model.conf_int(alpha=alpha).loc["post"]
    ci_lower, ci_upper = float(ci[0]), float(ci[1])
    p_value = float(model.pvalues["post"])
    significant = bool(p_value < alpha)

    pre_mean = float(y[pre_mask].mean())
    post_mean = float(y[post_mask].mean())
    rel_change = estimate / abs(pre_mean) * 100 if pre_mean != 0 else float("inf")

    sig_label = "significant" if significant else "not significant"
    cov_label = f" (controlling for {', '.join(covariates)})" if covariates else ""
    interp = (
        f"Pre-post timeseries change{cov_label}: {estimate:+.4f} "
        f"({rel_change:+.1f}%), p = {p_value:.4f} ({sig_label}). "
        f"Pre-mean = {pre_mean:.4f}, post-mean = {post_mean:.4f}. "
        f"95% CI: [{ci_lower:+.4f}, {ci_upper:+.4f}]. "
        f"Method: timeseries_ols. {CAVEAT}"
    )

    return {
        "estimate": estimate,
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
        "p_value": p_value,
        "significant": significant,
        "pre_mean": pre_mean,
        "post_mean": post_mean,
        "relative_change_pct": float(rel_change),
        "method": "timeseries_ols",
        "covariates_used": covariates_used,
        "n": int(len(df)),
        "n_pre": int(pre_mask.sum()),
        "n_post": int(post_mask.sum()),
        "alpha": alpha,
        "caveat": CAVEAT,
        "confidence_level": "LOW",
        "interpretation": interp,
    }
