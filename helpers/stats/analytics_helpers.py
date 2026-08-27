"""
Analytics utilities for the AI Data Analyst.

Higher-level analytical functions that combine descriptive stats, segmentation,
statistical testing, impact scoring, process control, and narrative synthesis
into structured outputs with human-readable interpretations.

Usage:
    from helpers.stats.analytics_helpers import (
        rfm_analysis, concentration_analysis, compare_segments,
        score_findings, control_chart, synthesize_insights,
    )

    # RFM segmentation of customers
    result = rfm_analysis(
        orders_df,
        customer_col="customer_id",
        date_col="order_date",
        revenue_col="revenue",
    )
    print(result["interpretation"])
    print(result["segment_summary"])

    # Revenue concentration (Gini, Pareto)
    result = concentration_analysis(revenue_df, value_col="revenue", entity_col="customer_id")
    print(result["interpretation"])

    # Compare metric across segments with automatic test selection
    result = compare_segments(df, segment_col="plan_type", metric_col="revenue")
    print(result["interpretation"])

    # Rank analytical findings by business impact
    result = score_findings(findings_list)
    print(result["interpretation"])
    print(result["top_finding"]["description"])

    # Shewhart control chart with Western Electric rules
    result = control_chart(daily_metric_series, sigma=3)
    print(result["interpretation"])
    print(result["violations"])

    # Synthesize findings into a narrative-ready structure
    result = synthesize_insights(scored_findings, metadata={"dataset_name": "my_dataset"})
    print(result["headline"])
    print(result["narrative_flow"])
"""

import numpy as np
import pandas as pd
from scipy import stats


# ---------------------------------------------------------------------------
# RFM Analysis
# ---------------------------------------------------------------------------

def rfm_analysis(df, customer_col, date_col, revenue_col, reference_date=None):
    """Compute RFM (Recency, Frequency, Monetary) segmentation.

    Scores each customer on three dimensions (1-5 quintiles) and assigns
    a behavioral segment label. Useful for identifying high-value customers,
    at-risk churners, and reactivation targets.

    Args:
        df: DataFrame with transaction-level data (one row per order).
        customer_col: Column name for customer identifier.
        date_col: Column name for order/transaction date.
        revenue_col: Column name for revenue/amount.
        reference_date: Date to compute recency from. Defaults to one day
            after the max date in the dataset.

    Returns:
        dict with keys:
            df: Customer-level DataFrame with columns: customer, recency,
                frequency, monetary, R, F, M, RFM_Score, segment.
            segment_summary: DataFrame with segment, count, pct,
                avg_monetary, avg_frequency.
            interpretation: Human-readable summary string.
    """
    if df is None or len(df) == 0:
        return {
            "df": pd.DataFrame(),
            "segment_summary": pd.DataFrame(),
            "interpretation": "Empty dataset — cannot compute RFM analysis.",
        }

    data = df[[customer_col, date_col, revenue_col]].copy()
    data[date_col] = pd.to_datetime(data[date_col])

    if reference_date is None:
        reference_date = data[date_col].max() + pd.Timedelta(days=1)
    else:
        reference_date = pd.to_datetime(reference_date)

    # Aggregate to customer level
    rfm = data.groupby(customer_col).agg(
        recency=(date_col, lambda x: (reference_date - x.max()).days),
        frequency=(date_col, "count"),
        monetary=(revenue_col, "sum"),
    ).reset_index()
    rfm.columns = ["customer", "recency", "frequency", "monetary"]

    n_customers = len(rfm)

    # Single customer edge case — assign all scores to 3 (middle)
    if n_customers == 1:
        rfm["R"] = 3
        rfm["F"] = 3
        rfm["M"] = 3
        rfm["RFM_Score"] = "333"
        rfm["segment"] = "Other"

        segment_summary = pd.DataFrame([{
            "segment": "Other",
            "count": 1,
            "pct": 100.0,
            "avg_monetary": float(rfm["monetary"].iloc[0]),
            "avg_frequency": float(rfm["frequency"].iloc[0]),
        }])

        return {
            "df": rfm,
            "segment_summary": segment_summary,
            "interpretation": (
                "Only 1 customer in the dataset — RFM scoring requires "
                "multiple customers for meaningful quintile segmentation."
            ),
        }

    # Score each dimension 1-5 using quintiles
    # Recency: lower is better, so reverse the labels
    rfm["R"] = _safe_qcut(rfm["recency"], q=5, labels=[5, 4, 3, 2, 1])
    rfm["F"] = _safe_qcut(rfm["frequency"], q=5, labels=[1, 2, 3, 4, 5])
    rfm["M"] = _safe_qcut(rfm["monetary"], q=5, labels=[1, 2, 3, 4, 5])

    rfm["RFM_Score"] = (
        rfm["R"].astype(str) + rfm["F"].astype(str) + rfm["M"].astype(str)
    )

    # Assign segments based on score combinations
    rfm["segment"] = rfm.apply(_assign_rfm_segment, axis=1)

    # Build segment summary
    segment_summary = (
        rfm.groupby("segment")
        .agg(
            count=("customer", "count"),
            avg_monetary=("monetary", "mean"),
            avg_frequency=("frequency", "mean"),
        )
        .reset_index()
    )
    segment_summary["pct"] = (
        segment_summary["count"] / segment_summary["count"].sum() * 100
    ).round(1)
    segment_summary["avg_monetary"] = segment_summary["avg_monetary"].round(2)
    segment_summary["avg_frequency"] = segment_summary["avg_frequency"].round(2)
    segment_summary = segment_summary[
        ["segment", "count", "pct", "avg_monetary", "avg_frequency"]
    ].sort_values("count", ascending=False).reset_index(drop=True)

    # Build interpretation
    top_segment = segment_summary.iloc[0]
    champions = segment_summary[segment_summary["segment"] == "Champions"]
    at_risk = segment_summary[segment_summary["segment"] == "At Risk"]

    parts = [
        f"RFM analysis across {n_customers:,} customers identified "
        f"{len(segment_summary)} segments.",
        f"Largest segment: {top_segment['segment']} "
        f"({top_segment['count']:,} customers, {top_segment['pct']:.1f}%).",
    ]
    if len(champions) > 0:
        c = champions.iloc[0]
        parts.append(
            f"Champions: {c['count']:,} ({c['pct']:.1f}%) with avg revenue "
            f"${c['avg_monetary']:,.2f} and {c['avg_frequency']:.1f} orders."
        )
    if len(at_risk) > 0:
        r = at_risk.iloc[0]
        parts.append(
            f"At Risk: {r['count']:,} ({r['pct']:.1f}%) — previously active "
            f"customers showing declining recency."
        )

    return {
        "df": rfm,
        "segment_summary": segment_summary,
        "interpretation": " ".join(parts),
    }


def _safe_qcut(series, q, labels):
    """Quintile scoring that handles ties gracefully.

    When too many duplicate values prevent clean quintile splits, falls back
    to fewer bins or assigns a uniform middle score.

    Args:
        series: Numeric pandas Series to bin.
        q: Number of quantile bins (typically 5).
        labels: Labels to assign to each bin.

    Returns:
        Series of integer scores.
    """
    try:
        return pd.qcut(series, q=q, labels=labels, duplicates="drop").astype(int)
    except ValueError:
        # If qcut fails even with duplicates='drop' (e.g., all same values),
        # try fewer bins progressively
        for fewer_q in range(q - 1, 1, -1):
            try:
                fewer_labels = labels[:fewer_q]
                return pd.qcut(
                    series, q=fewer_q, labels=fewer_labels, duplicates="drop"
                ).astype(int)
            except ValueError:
                continue
        # Last resort: assign middle score to all
        return pd.Series([3] * len(series), index=series.index)


def _assign_rfm_segment(row):
    """Map RFM scores to a named segment.

    Args:
        row: DataFrame row with R, F, M integer scores (1-5).

    Returns:
        str: Segment name.
    """
    r, f, m = int(row["R"]), int(row["F"]), int(row["M"])

    if r >= 4 and f >= 4 and m >= 4:
        return "Champions"
    elif f >= 3 and m >= 3:
        return "Loyal"
    elif r <= 2 and f >= 3:
        return "At Risk"
    elif r <= 2 and f <= 2 and m <= 2:
        return "Lost"
    else:
        return "Other"


# ---------------------------------------------------------------------------
# Concentration Analysis (Gini, Pareto, Lorenz curve)
# ---------------------------------------------------------------------------

def concentration_analysis(df, value_col, entity_col=None):
    """Analyze how concentrated a distribution is across entities.

    Computes the Gini coefficient, top-N% share, Pareto ratio, and Lorenz
    curve data. Useful for answering questions like "Do our top 20% of
    customers account for 80% of revenue?"

    Args:
        df: DataFrame containing the values to analyze.
        value_col: Column name for the value to measure concentration of
            (e.g., revenue, orders).
        entity_col: Optional column name for the entity (e.g., customer_id).
            If provided, values are aggregated per entity first. If None,
            each row is treated as a separate entity.

    Returns:
        dict with keys:
            gini: Gini coefficient (0 = perfect equality, 1 = perfect
                concentration).
            top_10_pct_share: Share of total value held by top 10% of entities.
            top_20_pct_share: Share of total value held by top 20% of entities.
            top_50_pct_share: Share of total value held by top 50% of entities.
            pareto_ratio: Percentage of entities producing 80% of total value.
            interpretation: Human-readable summary string.
            lorenz_curve: Dict with 'x' (cumulative % of entities) and
                'y' (cumulative % of value) arrays for plotting.
    """
    if df is None or len(df) == 0:
        return {
            "gini": 0.0,
            "top_10_pct_share": 0.0,
            "top_20_pct_share": 0.0,
            "top_50_pct_share": 0.0,
            "pareto_ratio": 0.0,
            "interpretation": "Empty dataset — cannot compute concentration.",
            "lorenz_curve": {"x": [], "y": []},
        }

    # Aggregate per entity if entity_col is provided
    if entity_col is not None:
        values = (
            df.groupby(entity_col)[value_col]
            .sum()
            .values
            .astype(float)
        )
    else:
        values = df[value_col].dropna().values.astype(float)

    n = len(values)

    if n == 0:
        return {
            "gini": 0.0,
            "top_10_pct_share": 0.0,
            "top_20_pct_share": 0.0,
            "top_50_pct_share": 0.0,
            "pareto_ratio": 0.0,
            "interpretation": "No valid values — cannot compute concentration.",
            "lorenz_curve": {"x": [], "y": []},
        }

    # Sort ascending for Lorenz curve and Gini
    sorted_values = np.sort(values)
    total = float(np.sum(sorted_values))

    if total == 0:
        return {
            "gini": 0.0,
            "top_10_pct_share": 0.0,
            "top_20_pct_share": 0.0,
            "top_50_pct_share": 0.0,
            "pareto_ratio": 100.0,
            "interpretation": (
                "All values are zero — concentration is undefined."
            ),
            "lorenz_curve": {"x": [], "y": []},
        }

    # Gini coefficient via the area method
    cumulative = np.cumsum(sorted_values)
    gini = float(
        (2.0 * np.sum((np.arange(1, n + 1) * sorted_values)))
        / (n * total)
        - (n + 1) / n
    )
    gini = max(0.0, min(1.0, gini))  # clamp to [0, 1]

    # Top-N% shares (sorted descending for share computation)
    sorted_desc = np.sort(values)[::-1]
    cumsum_desc = np.cumsum(sorted_desc)

    def _top_pct_share(pct):
        """Share of total value held by the top pct% of entities."""
        k = max(1, int(np.ceil(n * pct / 100)))
        return float(cumsum_desc[min(k, n) - 1] / total)

    top_10 = _top_pct_share(10)
    top_20 = _top_pct_share(20)
    top_50 = _top_pct_share(50)

    # Pareto ratio: what % of entities produce 80% of value
    threshold_80 = total * 0.80
    pareto_idx = int(np.searchsorted(cumsum_desc, threshold_80, side="left")) + 1
    pareto_ratio = float(pareto_idx / n * 100)

    # Lorenz curve data (cumulative % of entities vs cumulative % of value)
    lorenz_y = np.concatenate([[0], cumulative / total])
    lorenz_x = np.linspace(0, 1, n + 1)

    # Interpretation
    if gini > 0.6:
        concentration_label = "highly concentrated"
    elif gini > 0.4:
        concentration_label = "moderately concentrated"
    else:
        concentration_label = "relatively evenly distributed"

    interpretation = (
        f"Distribution is {concentration_label} (Gini={gini:.3f}). "
        f"Top 10% of entities account for {top_10:.1%} of total value; "
        f"top 20% account for {top_20:.1%}. "
        f"{pareto_ratio:.1f}% of entities produce 80% of total value."
    )

    return {
        "gini": float(gini),
        "top_10_pct_share": float(top_10),
        "top_20_pct_share": float(top_20),
        "top_50_pct_share": float(top_50),
        "pareto_ratio": float(pareto_ratio),
        "interpretation": interpretation,
        "lorenz_curve": {
            "x": lorenz_x.tolist(),
            "y": lorenz_y.tolist(),
        },
    }


# ---------------------------------------------------------------------------
# Segment Comparison (auto test selection + pairwise)
# ---------------------------------------------------------------------------

def compare_segments(df, segment_col, metric_col, test="auto"):
    """Compare a metric across segments with automatic test selection.

    Groups by segment, computes summary stats, and runs pairwise statistical
    tests between all segment pairs. Automatically chooses between t-test and
    Mann-Whitney based on normality and sample size. Applies Bonferroni
    correction for multiple comparisons.

    Args:
        df: DataFrame with segment and metric columns.
        segment_col: Column name for the segment/group label.
        metric_col: Column name for the numeric metric to compare.
        test: Test selection strategy. 'auto' (default) uses Mann-Whitney if
            any group is non-normal (Shapiro p<0.05) or n<30, else Welch's
            t-test. 'mann-whitney' forces Mann-Whitney. 't-test' forces
            Welch's t-test.

    Returns:
        dict with keys:
            summary: DataFrame with segment, mean, median, std, count.
            pairwise: List of dicts, each with: seg_a, seg_b, test_used,
                stat, p_value, p_adjusted, significant, effect_size.
            interpretation: Human-readable summary string.
    """
    if df is None or len(df) == 0:
        return {
            "summary": pd.DataFrame(),
            "pairwise": [],
            "interpretation": "Empty dataset — cannot compare segments.",
        }

    data = df[[segment_col, metric_col]].dropna()
    groups = data.groupby(segment_col)[metric_col]

    # Build per-segment summary
    summary_rows = []
    group_data = {}
    for name, group_values in groups:
        vals = group_values.values.astype(float)
        if len(vals) == 0:
            continue
        group_data[name] = vals
        summary_rows.append({
            "segment": name,
            "mean": float(np.mean(vals)),
            "median": float(np.median(vals)),
            "std": float(np.std(vals, ddof=1)) if len(vals) > 1 else 0.0,
            "count": int(len(vals)),
        })

    summary = pd.DataFrame(summary_rows)

    if len(group_data) < 2:
        return {
            "summary": summary,
            "pairwise": [],
            "interpretation": (
                f"Only {len(group_data)} segment(s) found — need at least 2 "
                f"for pairwise comparison."
            ),
        }

    # Determine test type if auto
    if test == "auto":
        use_nonparametric = False
        for name, vals in group_data.items():
            if len(vals) < 30:
                use_nonparametric = True
                break
            if len(vals) >= 3:
                _, p_shapiro = stats.shapiro(vals[:5000])  # cap at 5000
                if p_shapiro < 0.05:
                    use_nonparametric = True
                    break
        selected_test = "mann-whitney" if use_nonparametric else "t-test"
    else:
        selected_test = test

    # Pairwise comparisons
    segment_names = list(group_data.keys())
    pairwise_results = []
    pairs = [
        (segment_names[i], segment_names[j])
        for i in range(len(segment_names))
        for j in range(i + 1, len(segment_names))
    ]
    n_comparisons = len(pairs)

    for seg_a, seg_b in pairs:
        vals_a = group_data[seg_a]
        vals_b = group_data[seg_b]

        if selected_test == "mann-whitney":
            try:
                stat_val, p_value = stats.mannwhitneyu(
                    vals_a, vals_b, alternative="two-sided"
                )
            except ValueError:
                # All values identical
                stat_val, p_value = 0.0, 1.0
            test_used = "mann-whitney"
        else:
            stat_val, p_value = stats.ttest_ind(
                vals_a, vals_b, equal_var=False
            )
            test_used = "welch-t"

        # Cohen's d effect size
        n_a, n_b = len(vals_a), len(vals_b)
        mean_diff = float(np.mean(vals_a) - np.mean(vals_b))
        var_a = float(np.var(vals_a, ddof=1)) if n_a > 1 else 0.0
        var_b = float(np.var(vals_b, ddof=1)) if n_b > 1 else 0.0
        pooled_std = np.sqrt(
            ((n_a - 1) * var_a + (n_b - 1) * var_b)
            / max(n_a + n_b - 2, 1)
        )
        effect_size = float(mean_diff / pooled_std) if pooled_std > 0 else 0.0

        # Bonferroni correction
        p_adjusted = min(float(p_value) * n_comparisons, 1.0)

        pairwise_results.append({
            "seg_a": seg_a,
            "seg_b": seg_b,
            "test_used": test_used,
            "stat": float(stat_val),
            "p_value": float(p_value),
            "p_adjusted": float(p_adjusted),
            "significant": bool(p_adjusted < 0.05),
            "effect_size": float(effect_size),
        })

    # Build interpretation
    n_significant = sum(1 for r in pairwise_results if r["significant"])
    interpretation_parts = [
        f"Compared {metric_col} across {len(group_data)} segments "
        f"using {selected_test} test ({n_comparisons} pairwise comparisons, "
        f"Bonferroni-corrected).",
    ]

    if n_significant == 0:
        interpretation_parts.append(
            "No statistically significant differences found after correction."
        )
    else:
        sig_pairs = [
            r for r in pairwise_results if r["significant"]
        ]
        interpretation_parts.append(
            f"{n_significant} of {n_comparisons} pairs show significant "
            f"differences (p_adjusted < 0.05)."
        )
        # Highlight the most significant pair
        best = min(sig_pairs, key=lambda r: r["p_adjusted"])
        mean_a = float(np.mean(group_data[best["seg_a"]]))
        mean_b = float(np.mean(group_data[best["seg_b"]]))
        interpretation_parts.append(
            f"Strongest difference: {best['seg_a']} (mean={mean_a:,.2f}) vs "
            f"{best['seg_b']} (mean={mean_b:,.2f}), "
            f"effect size d={abs(best['effect_size']):.2f}, "
            f"p_adjusted={best['p_adjusted']:.4f}."
        )

    return {
        "summary": summary,
        "pairwise": pairwise_results,
        "interpretation": " ".join(interpretation_parts),
    }


# ---------------------------------------------------------------------------
# Impact Scoring (Finding Prioritization)
# ---------------------------------------------------------------------------

def score_findings(findings):
    """Rank analytical findings by business impact for prioritized storytelling.

    Implements a 4-factor scoring model:
    1. Magnitude (0-25): How large is the effect? (absolute & relative)
    2. Breadth (0-25): What % of users/revenue is affected?
    3. Actionability (0-25): Can we do something about it?
    4. Confidence (0-25): How confident are we in the finding?

    Args:
        findings: List of dicts, each with keys:
            - description (str): What was found
            - metric_value (float): The observed metric value
            - baseline_value (float): Expected/comparison value
            - affected_pct (float): % of population affected (0-1)
            - actionable (bool): Whether the team can act on this
            - confidence (float): Statistical confidence (0-1)
            - p_value (float, optional): p-value if available
            - effect_size (float, optional): Cohen's d if available

    Returns:
        dict with keys:
            ranked_findings: List of original findings + score/rank/factors
            top_finding: The highest-ranked finding
            interpretation: Summary string
    """
    if not findings:
        return {
            "ranked_findings": [],
            "top_finding": None,
            "interpretation": "No findings to score.",
        }

    scored = []
    for finding in findings:
        factors = _score_single_finding(finding)
        total = sum(factors.values())
        scored.append({
            **finding,
            "factors": factors,
            "score": total,
        })

    # Sort descending by score, stable sort preserves original order for ties
    scored.sort(key=lambda f: f["score"], reverse=True)

    # Assign rank (1-based)
    for i, item in enumerate(scored):
        item["rank"] = i + 1

    top = scored[0]

    # Build interpretation
    n = len(scored)
    if n == 1:
        interpretation = (
            f"1 finding scored {top['score']}/100. "
            f"Top finding: {top['description']} "
            f"(Magnitude={top['factors']['magnitude']}, "
            f"Breadth={top['factors']['breadth']}, "
            f"Actionability={top['factors']['actionability']}, "
            f"Confidence={top['factors']['confidence']})."
        )
    else:
        runner_up = scored[1]
        gap = top["score"] - runner_up["score"]
        interpretation = (
            f"{n} findings scored. Top finding: {top['description']} "
            f"(score={top['score']}/100). "
            f"Runner-up: {runner_up['description']} "
            f"(score={runner_up['score']}/100, gap={gap} pts). "
            f"Top factors: Magnitude={top['factors']['magnitude']}, "
            f"Breadth={top['factors']['breadth']}, "
            f"Actionability={top['factors']['actionability']}, "
            f"Confidence={top['factors']['confidence']}."
        )

    return {
        "ranked_findings": scored,
        "top_finding": top,
        "interpretation": interpretation,
    }


def _score_single_finding(finding):
    """Compute the 4-factor impact score for a single finding.

    Args:
        finding: Dict with required and optional keys (see score_findings).

    Returns:
        Dict with keys: magnitude, breadth, actionability, confidence.
        Each value is an int in [0, 25].
    """
    # --- Magnitude (0-25) ---
    baseline = finding.get("baseline_value", 0)
    metric = finding.get("metric_value", 0)

    if baseline == 0:
        # Cannot compute relative change; use a fallback based on whether
        # the metric itself is non-zero
        magnitude = 15 if metric != 0 else 5
    else:
        pct_change = abs(metric - baseline) / abs(baseline)
        if pct_change > 0.50:
            magnitude = 25
        elif pct_change > 0.20:
            magnitude = 20
        elif pct_change > 0.10:
            magnitude = 15
        elif pct_change > 0.05:
            magnitude = 10
        else:
            magnitude = 5

    # --- Breadth (0-25) ---
    affected_pct = finding.get("affected_pct", 0)
    if affected_pct > 0.50:
        breadth = 25
    elif affected_pct > 0.30:
        breadth = 20
    elif affected_pct > 0.10:
        breadth = 15
    elif affected_pct > 0.05:
        breadth = 10
    else:
        breadth = 5

    # --- Actionability (0-25) ---
    actionable = finding.get("actionable", False)
    if actionable:
        actionability = 25
    else:
        actionability = 5
    # Bonus for large effect size (if provided)
    effect_size = finding.get("effect_size")
    if effect_size is not None and effect_size > 0.5:
        actionability = min(actionability + 5, 25)

    # --- Confidence (0-25) ---
    conf = finding.get("confidence", 0)
    confidence_score = int(round(conf * 25))
    # Bonus for statistical significance (if p_value provided)
    p_value = finding.get("p_value")
    if p_value is not None and p_value < 0.05:
        confidence_score = min(confidence_score + 5, 25)
    # Clamp to [0, 25]
    confidence_score = max(0, min(25, confidence_score))

    return {
        "magnitude": magnitude,
        "breadth": breadth,
        "actionability": actionability,
        "confidence": confidence_score,
    }


# ---------------------------------------------------------------------------
# Control Chart (Shewhart SPC with Western Electric Rules)
# ---------------------------------------------------------------------------

def control_chart(series, sigma=3, window=None):
    """Shewhart control chart with Western Electric rules.

    Computes control limits (UCL, LCL, center line) and identifies
    out-of-control points using Western Electric rules.

    Args:
        series: pandas Series with DatetimeIndex or numeric index.
        sigma: Number of standard deviations for control limits (default 3).
        window: Optional rolling window size. If None, uses global mean/std.
            If specified, computes rolling center line and limits.

    Returns:
        dict with keys:
            center_line: float or Series (if window)
            ucl: float or Series (upper control limit)
            lcl: float or Series (lower control limit)
            violations: List of dicts with {index, value, rule, description}
            in_control: bool (True if no violations)
            rules_checked: List of rule names applied
            interpretation: str
    """
    if series is None or len(series) == 0:
        return {
            "center_line": np.nan,
            "ucl": np.nan,
            "lcl": np.nan,
            "violations": [],
            "in_control": True,
            "rules_checked": [],
            "interpretation": "Empty series — cannot compute control chart.",
        }

    values = series.dropna()
    if len(values) < 2:
        return {
            "center_line": float(values.iloc[0]) if len(values) == 1 else np.nan,
            "ucl": np.nan,
            "lcl": np.nan,
            "violations": [],
            "in_control": True,
            "rules_checked": [],
            "interpretation": (
                "Insufficient data (need at least 2 non-null points) "
                "for control chart computation."
            ),
        }

    # Compute center line and standard deviation
    if window is not None and window >= 2:
        center = values.rolling(window=window, min_periods=2).mean()
        std = values.rolling(window=window, min_periods=2).std(ddof=1)
    else:
        center = float(values.mean())
        std = float(values.std(ddof=1))

    # Compute control limits
    ucl = center + sigma * std
    lcl = center - sigma * std

    # For rule-checking, we need scalar or per-point center/std
    if window is not None and window >= 2:
        center_arr = center.values
        std_arr = std.values
    else:
        center_arr = np.full(len(values), center)
        std_arr = np.full(len(values), std)

    vals = values.values.astype(float)
    idx = values.index

    # Apply Western Electric rules
    violations = []
    rules_checked = [
        "Rule 1: Point beyond 3-sigma",
        "Rule 2: 2 of 3 consecutive points beyond 2-sigma (same side)",
        "Rule 3: 4 of 5 consecutive points beyond 1-sigma (same side)",
        "Rule 4: 8 consecutive points on same side of center line",
    ]

    # Pre-compute deviations from center in units of sigma
    with np.errstate(divide="ignore", invalid="ignore"):
        z_scores = np.where(std_arr > 0, (vals - center_arr) / std_arr, 0.0)

    seen = set()  # track (index_position, rule) to avoid duplicates

    # Rule 1: Any single point beyond ±3σ
    for i in range(len(vals)):
        if np.isnan(z_scores[i]):
            continue
        if abs(z_scores[i]) > sigma:
            key = (i, "Rule 1")
            if key not in seen:
                seen.add(key)
                violations.append({
                    "index": idx[i],
                    "value": float(vals[i]),
                    "rule": "Rule 1",
                    "description": (
                        f"Point at {idx[i]} = {vals[i]:.4f} is beyond "
                        f"{sigma}-sigma limit (z={z_scores[i]:.2f})."
                    ),
                })

    # Rule 2: 2 of 3 consecutive points beyond ±2σ (same side)
    for i in range(2, len(vals)):
        if any(np.isnan(z_scores[i - k]) for k in range(3)):
            continue
        # Check upper side
        above_2sigma = [z_scores[i - k] > 2 for k in range(3)]
        if sum(above_2sigma) >= 2:
            # Flag the most recent point in the run
            key = (i, "Rule 2")
            if key not in seen:
                seen.add(key)
                violations.append({
                    "index": idx[i],
                    "value": float(vals[i]),
                    "rule": "Rule 2",
                    "description": (
                        f"2 of 3 points ending at {idx[i]} are beyond "
                        f"+2-sigma on the same side."
                    ),
                })
        # Check lower side
        below_2sigma = [z_scores[i - k] < -2 for k in range(3)]
        if sum(below_2sigma) >= 2:
            key = (i, "Rule 2")
            if key not in seen:
                seen.add(key)
                violations.append({
                    "index": idx[i],
                    "value": float(vals[i]),
                    "rule": "Rule 2",
                    "description": (
                        f"2 of 3 points ending at {idx[i]} are beyond "
                        f"-2-sigma on the same side."
                    ),
                })

    # Rule 3: 4 of 5 consecutive points beyond ±1σ (same side)
    for i in range(4, len(vals)):
        if any(np.isnan(z_scores[i - k]) for k in range(5)):
            continue
        above_1sigma = [z_scores[i - k] > 1 for k in range(5)]
        if sum(above_1sigma) >= 4:
            key = (i, "Rule 3")
            if key not in seen:
                seen.add(key)
                violations.append({
                    "index": idx[i],
                    "value": float(vals[i]),
                    "rule": "Rule 3",
                    "description": (
                        f"4 of 5 points ending at {idx[i]} are beyond "
                        f"+1-sigma on the same side."
                    ),
                })
        below_1sigma = [z_scores[i - k] < -1 for k in range(5)]
        if sum(below_1sigma) >= 4:
            key = (i, "Rule 3")
            if key not in seen:
                seen.add(key)
                violations.append({
                    "index": idx[i],
                    "value": float(vals[i]),
                    "rule": "Rule 3",
                    "description": (
                        f"4 of 5 points ending at {idx[i]} are beyond "
                        f"-1-sigma on the same side."
                    ),
                })

    # Rule 4: 8 consecutive points on the same side of center line
    for i in range(7, len(vals)):
        if any(np.isnan(z_scores[i - k]) for k in range(8)):
            continue
        all_above = all(vals[i - k] > center_arr[i - k] for k in range(8))
        all_below = all(vals[i - k] < center_arr[i - k] for k in range(8))
        if all_above or all_below:
            key = (i, "Rule 4")
            if key not in seen:
                seen.add(key)
                side = "above" if all_above else "below"
                violations.append({
                    "index": idx[i],
                    "value": float(vals[i]),
                    "rule": "Rule 4",
                    "description": (
                        f"8 consecutive points ending at {idx[i]} are "
                        f"{side} the center line (run rule)."
                    ),
                })

    in_control = len(violations) == 0

    # Build interpretation
    n_points = len(vals)
    n_violations = len(violations)
    mode = "rolling" if (window is not None and window >= 2) else "global"

    if in_control:
        interpretation = (
            f"Control chart ({mode} limits, {sigma}-sigma) across "
            f"{n_points} points: process is IN CONTROL. "
            f"No Western Electric rule violations detected."
        )
    else:
        rule_counts = {}
        for v in violations:
            rule_counts[v["rule"]] = rule_counts.get(v["rule"], 0) + 1
        rule_summary = ", ".join(
            f"{rule}: {count}" for rule, count in sorted(rule_counts.items())
        )
        interpretation = (
            f"Control chart ({mode} limits, {sigma}-sigma) across "
            f"{n_points} points: process is OUT OF CONTROL. "
            f"{n_violations} violation(s) detected. "
            f"Breakdown: {rule_summary}."
        )

    return {
        "center_line": center,
        "ucl": ucl,
        "lcl": lcl,
        "violations": violations,
        "in_control": in_control,
        "rules_checked": rules_checked,
        "interpretation": interpretation,
    }


# ---------------------------------------------------------------------------
# Insight Synthesis (Narrative-ready grouping, contradictions, story flow)
# ---------------------------------------------------------------------------

def synthesize_insights(findings, metadata=None):
    """Group findings into themes, detect contradictions, and produce a
    structured synthesis ready for storytelling.

    Combines scored findings with thematic grouping, contradiction detection,
    narrative ordering (Context-Tension-Resolution), meta-insight extraction,
    and action item generation.

    Args:
        findings: List of dicts, each with keys:
            - description (str, required): What was found.
            - metric_value (float, required): The observed metric value.
            - baseline_value (float, required): Expected/comparison value.
            - affected_pct (float, required): Fraction of population affected
              (0-1).
            - actionable (bool, required): Whether the team can act on this.
            - confidence (float, required): Statistical confidence (0-1).
            - category (str, optional): e.g. "funnel", "segment", "trend",
              "anomaly", "engagement".
            - direction (str, optional): "up", "down", or "flat".
            - metric_name (str, optional): Name of the metric.
            - p_value (float, optional): p-value if available.
            - effect_size (float, optional): Cohen's d if available.
        metadata: Optional dict with contextual information:
            - dataset_name (str): Name of the dataset.
            - date_range (str): Time period covered.
            - question (str): The business question being answered.

    Returns:
        dict with keys:
            headline: str — single most important insight as an
                action-oriented sentence.
            theme_groups: list of dicts with theme, findings, summary.
            contradictions: list of dicts with finding_a, finding_b,
                nature, resolution_hint.
            narrative_flow: list of str — presentation beats
                (Context -> Tension -> Resolution).
            meta_insights: list of str — higher-order observations.
            action_items: list of dicts with action, priority, metric.
            interpretation: str — full paragraph summarizing all findings.
    """
    if metadata is None:
        metadata = {}

    # -- Edge case: empty findings --
    if not findings:
        return {
            "headline": "No findings to synthesize.",
            "theme_groups": [],
            "contradictions": [],
            "narrative_flow": [],
            "meta_insights": [],
            "action_items": [],
            "interpretation": "No findings were provided for synthesis.",
        }

    # ------------------------------------------------------------------
    # 1. Score and rank findings
    # ------------------------------------------------------------------
    scored_result = score_findings(findings)
    ranked = scored_result["ranked_findings"]

    # ------------------------------------------------------------------
    # 2. Group by theme
    # ------------------------------------------------------------------
    theme_groups = _group_by_theme(ranked)

    # ------------------------------------------------------------------
    # 3. Detect contradictions
    # ------------------------------------------------------------------
    contradictions = _detect_contradictions(ranked)

    # ------------------------------------------------------------------
    # 4. Generate narrative flow
    # ------------------------------------------------------------------
    narrative_flow = _build_narrative_flow(theme_groups, contradictions, ranked)

    # ------------------------------------------------------------------
    # 5. Extract meta-insights
    # ------------------------------------------------------------------
    meta_insights = _extract_meta_insights(ranked, theme_groups)

    # ------------------------------------------------------------------
    # 6. Generate action items
    # ------------------------------------------------------------------
    action_items = _generate_action_items(ranked)

    # ------------------------------------------------------------------
    # 7. Build headline and interpretation
    # ------------------------------------------------------------------
    headline = _build_headline(ranked, metadata)
    interpretation = _build_interpretation(
        ranked, theme_groups, contradictions, action_items, metadata,
    )

    return {
        "headline": headline,
        "theme_groups": theme_groups,
        "contradictions": contradictions,
        "narrative_flow": narrative_flow,
        "meta_insights": meta_insights,
        "action_items": action_items,
        "interpretation": interpretation,
    }


# ---------------------------------------------------------------------------
# synthesize_insights — private helpers
# ---------------------------------------------------------------------------

# Keyword-to-theme mapping for category inference
_THEME_KEYWORDS = {
    "Funnel": [
        "funnel", "conversion", "drop-off", "dropout", "drop off",
        "checkout", "cart",
    ],
    "Segment": [
        "segment", "cohort", "group", "mobile", "desktop", "ios",
        "android", "plan", "tier",
    ],
    "Trend": [
        "trend", "growth", "decline", "mom", "wow", "yoy",
        "month-over-month", "week-over-week", "year-over-year",
        "increasing", "decreasing",
    ],
    "Anomaly": [
        "anomaly", "spike", "dip", "unusual", "outlier", "unexpected",
        "sudden",
    ],
    "Engagement": [
        "retention", "churn", "engagement", "active", "session",
        "dau", "wau", "mau", "stickiness",
    ],
}


def _infer_theme(description):
    """Infer a theme from the finding description using keyword matching.

    Args:
        description: Finding description string.

    Returns:
        str: Theme label.
    """
    desc_lower = description.lower()
    for theme, keywords in _THEME_KEYWORDS.items():
        for kw in keywords:
            if kw in desc_lower:
                return theme
    return "Other"


def _group_by_theme(ranked_findings):
    """Group ranked findings by category/theme.

    Args:
        ranked_findings: List of scored finding dicts (from score_findings).

    Returns:
        List of theme-group dicts, each with theme, findings, summary.
    """
    groups = {}
    for finding in ranked_findings:
        raw_cat = finding.get("category", "")
        if raw_cat:
            theme = raw_cat.capitalize()
        else:
            theme = _infer_theme(finding.get("description", ""))

        if theme not in groups:
            groups[theme] = []
        groups[theme].append(finding)

    # Sort findings within each group by score descending
    theme_groups = []
    for theme in sorted(groups.keys()):
        findings_in_group = sorted(
            groups[theme], key=lambda f: f.get("score", 0), reverse=True,
        )
        summary = _summarize_theme(theme, findings_in_group)
        theme_groups.append({
            "theme": theme,
            "findings": findings_in_group,
            "summary": summary,
        })

    # Sort groups by max score in each group (most impactful theme first)
    theme_groups.sort(
        key=lambda g: max(f.get("score", 0) for f in g["findings"]),
        reverse=True,
    )
    return theme_groups


def _summarize_theme(theme, findings):
    """Generate a one-sentence summary for a theme group.

    Args:
        theme: Theme label string.
        findings: Sorted list of findings in this theme.

    Returns:
        str: One-sentence summary.
    """
    n = len(findings)
    top = findings[0]
    top_desc = top.get("description", "Unknown finding")

    if n == 1:
        return f"{theme}: {top_desc}"

    actionable_count = sum(1 for f in findings if f.get("actionable", False))
    if actionable_count > 0:
        return (
            f"{theme} ({n} findings, {actionable_count} actionable): "
            f"led by {top_desc}"
        )
    return f"{theme} ({n} findings): led by {top_desc}"


def _detect_contradictions(ranked_findings):
    """Find pairs of findings that potentially contradict each other.

    Checks for:
    - Same metric, opposite directions
    - Overall improvement vs. large-segment decline (Simpson's paradox)
    - High-confidence findings contradicting each other

    Args:
        ranked_findings: List of scored finding dicts.

    Returns:
        List of contradiction dicts.
    """
    contradictions = []
    n = len(ranked_findings)

    for i in range(n):
        for j in range(i + 1, n):
            fa = ranked_findings[i]
            fb = ranked_findings[j]

            contradiction = _check_pair_contradiction(fa, fb)
            if contradiction is not None:
                contradictions.append(contradiction)

    return contradictions


def _check_pair_contradiction(fa, fb):
    """Check whether two findings contradict each other.

    Args:
        fa: First finding dict.
        fb: Second finding dict.

    Returns:
        Contradiction dict or None.
    """
    dir_a = fa.get("direction", "")
    dir_b = fb.get("direction", "")
    metric_a = fa.get("metric_name", "")
    metric_b = fb.get("metric_name", "")
    conf_a = fa.get("confidence", 0)
    conf_b = fb.get("confidence", 0)
    desc_a = fa.get("description", "")
    desc_b = fb.get("description", "")

    # Case 1: Same metric, opposite directions
    if (
        metric_a
        and metric_b
        and metric_a.lower() == metric_b.lower()
        and dir_a in ("up", "down")
        and dir_b in ("up", "down")
        and dir_a != dir_b
    ):
        return {
            "finding_a": desc_a,
            "finding_b": desc_b,
            "nature": (
                f"'{metric_a}' is reported as '{dir_a}' in one finding "
                f"and '{dir_b}' in another."
            ),
            "resolution_hint": (
                "Check if the overall improvement is driven by mix shift "
                "rather than true improvement (Simpson's paradox). "
                "Break down by segment to isolate the real trend."
            ),
        }

    # Case 2: Overall improving but a large segment declining
    aff_a = fa.get("affected_pct", 0)
    aff_b = fb.get("affected_pct", 0)

    if dir_a == "up" and dir_b == "down" and aff_b > 0.20:
        return {
            "finding_a": desc_a,
            "finding_b": desc_b,
            "nature": (
                "Overall metric is improving, but a segment covering "
                f"{aff_b:.0%} of the population is declining."
            ),
            "resolution_hint": (
                "This could indicate Simpson's paradox — the aggregate "
                "improvement may mask a real decline in a major segment. "
                "Investigate whether composition changes are driving the "
                "overall number."
            ),
        }
    if dir_b == "up" and dir_a == "down" and aff_a > 0.20:
        return {
            "finding_a": desc_a,
            "finding_b": desc_b,
            "nature": (
                "Overall metric is improving, but a segment covering "
                f"{aff_a:.0%} of the population is declining."
            ),
            "resolution_hint": (
                "This could indicate Simpson's paradox — the aggregate "
                "improvement may mask a real decline in a major segment. "
                "Investigate whether composition changes are driving the "
                "overall number."
            ),
        }

    # Case 3: Two high-confidence findings with opposite directions
    if (
        conf_a >= 0.8
        and conf_b >= 0.8
        and dir_a in ("up", "down")
        and dir_b in ("up", "down")
        and dir_a != dir_b
    ):
        return {
            "finding_a": desc_a,
            "finding_b": desc_b,
            "nature": (
                f"Two high-confidence findings (conf={conf_a:.0%} and "
                f"{conf_b:.0%}) point in opposite directions "
                f"('{dir_a}' vs '{dir_b}')."
            ),
            "resolution_hint": (
                "Verify that both findings cover the same time period "
                "and population. Check if different metrics or segments "
                "explain the divergence."
            ),
        }

    return None


def _build_narrative_flow(theme_groups, contradictions, ranked_findings):
    """Suggest a Context -> Tension -> Resolution narrative.

    Args:
        theme_groups: List of theme-group dicts.
        contradictions: List of contradiction dicts.
        ranked_findings: List of scored finding dicts.

    Returns:
        List of narrative beat strings.
    """
    beats = []

    # --- Context beats: background / setup ---
    trend_group = None
    for tg in theme_groups:
        if tg["theme"] in ("Trend", "Other"):
            trend_group = tg
            break

    if trend_group:
        top_trend = trend_group["findings"][0]
        beats.append(
            f"[Context] Set the scene: {top_trend.get('description', 'baseline context')}"
        )
    else:
        beats.append(
            "[Context] Establish baseline performance and recent trajectory."
        )

    # --- Tension beats: problems, anomalies, contradictions ---
    high_impact = [
        f for f in ranked_findings if f.get("score", 0) >= 50
    ]
    tension_added = False

    for finding in high_impact[:3]:
        category = finding.get("category", "")
        theme = category.capitalize() if category else _infer_theme(
            finding.get("description", ""),
        )
        if theme in ("Anomaly", "Funnel", "Segment", "Engagement"):
            beats.append(
                f"[Tension] Highlight problem: {finding.get('description', '')}"
            )
            tension_added = True

    if contradictions:
        c = contradictions[0]
        beats.append(
            f"[Tension] Apparent contradiction: {c['nature']}"
        )
        tension_added = True

    if not tension_added:
        # Use the top finding as the tension point
        top = ranked_findings[0]
        beats.append(
            f"[Tension] Key finding: {top.get('description', '')}"
        )

    # --- Resolution beats: actionable findings with clear next steps ---
    actionable = [f for f in ranked_findings if f.get("actionable", False)]
    if actionable:
        for finding in actionable[:2]:
            beats.append(
                f"[Resolution] Recommended action based on: "
                f"{finding.get('description', '')}"
            )
    else:
        beats.append(
            "[Resolution] Summarize findings and outline areas for "
            "further investigation."
        )

    return beats


def _extract_meta_insights(ranked_findings, theme_groups):
    """Look across all findings for higher-order patterns.

    Args:
        ranked_findings: List of scored finding dicts.
        theme_groups: List of theme-group dicts.

    Returns:
        List of meta-insight strings.
    """
    meta = []

    # --- Repeated dimension mentions ---
    dimension_counts = {}
    dimension_keywords = [
        "mobile", "desktop", "ios", "android", "new user", "returning",
        "enterprise", "smb", "free", "paid", "web", "app",
    ]
    for finding in ranked_findings:
        desc_lower = finding.get("description", "").lower()
        for dim in dimension_keywords:
            if dim in desc_lower:
                dimension_counts[dim] = dimension_counts.get(dim, 0) + 1

    for dim, count in dimension_counts.items():
        if count >= 2:
            meta.append(
                f"'{dim.title()}' appears across {count} findings — it may "
                f"be a systemic factor worth dedicated investigation."
            )

    # --- Directional alignment ---
    directions = [
        f.get("direction", "") for f in ranked_findings if f.get("direction")
    ]
    if directions:
        up_count = sum(1 for d in directions if d == "up")
        down_count = sum(1 for d in directions if d == "down")
        total = len(directions)

        if up_count == total and total >= 2:
            meta.append(
                "All findings with a direction are trending upward — "
                "this suggests broad positive momentum."
            )
        elif down_count == total and total >= 2:
            meta.append(
                "All findings with a direction are trending downward — "
                "this warrants urgent attention."
            )
        elif up_count >= 2 and down_count >= 2:
            meta.append(
                f"Mixed signals: {up_count} findings trending up and "
                f"{down_count} trending down — look for divergence across "
                f"segments or metrics."
            )

    # --- Theme concentration ---
    for tg in theme_groups:
        high_impact_in_theme = [
            f for f in tg["findings"] if f.get("score", 0) >= 60
        ]
        if len(high_impact_in_theme) >= 2:
            meta.append(
                f"{len(high_impact_in_theme)} high-impact findings "
                f"cluster in the '{tg['theme']}' theme — this is a "
                f"critical area."
            )

    return meta


def _generate_action_items(ranked_findings):
    """Extract concrete action items from actionable findings.

    Args:
        ranked_findings: List of scored finding dicts.

    Returns:
        List of action-item dicts with action, priority, metric.
    """
    items = []
    for finding in ranked_findings:
        if not finding.get("actionable", False):
            continue

        score = finding.get("score", 0)
        if score >= 70:
            priority = "high"
        elif score >= 40:
            priority = "medium"
        else:
            priority = "low"

        metric = finding.get("metric_name", "")
        description = finding.get("description", "")

        # Build action sentence
        direction = finding.get("direction", "")
        if direction == "down":
            action = f"Investigate and address: {description}"
        elif direction == "up":
            action = f"Capitalize on momentum: {description}"
        else:
            action = f"Act on finding: {description}"

        items.append({
            "action": action,
            "priority": priority,
            "metric": metric if metric else "unspecified",
        })

    return items


def _build_headline(ranked_findings, metadata):
    """Build the single most important insight as an action-oriented sentence.

    Args:
        ranked_findings: List of scored finding dicts.
        metadata: Metadata dict.

    Returns:
        str: Headline sentence.
    """
    if len(ranked_findings) == 1:
        finding = ranked_findings[0]
        return finding.get("description", "One finding identified.")

    top = ranked_findings[0]
    desc = top.get("description", "")
    direction = top.get("direction", "")
    metric_name = top.get("metric_name", "")

    # Make it action-oriented
    if direction == "down" and top.get("actionable", False):
        headline = f"Urgent: {desc}"
    elif direction == "up" and top.get("actionable", False):
        headline = f"Opportunity: {desc}"
    elif top.get("actionable", False):
        headline = f"Action needed: {desc}"
    else:
        headline = f"Key insight: {desc}"

    if metric_name:
        headline += f" ({metric_name})"

    return headline


def _build_interpretation(
    ranked_findings, theme_groups, contradictions, action_items, metadata,
):
    """Build a full-paragraph interpretation of all findings.

    Args:
        ranked_findings: List of scored finding dicts.
        theme_groups: List of theme-group dicts.
        contradictions: List of contradiction dicts.
        action_items: List of action-item dicts.
        metadata: Metadata dict.

    Returns:
        str: Interpretation paragraph.
    """
    parts = []

    # Opening context
    dataset = metadata.get("dataset_name", "the dataset")
    date_range = metadata.get("date_range", "")
    question = metadata.get("question", "")

    n_findings = len(ranked_findings)
    n_themes = len(theme_groups)

    opener = f"Analysis of {dataset}"
    if date_range:
        opener += f" ({date_range})"
    opener += f" produced {n_findings} finding(s) across {n_themes} theme(s)."
    parts.append(opener)

    if question:
        parts.append(f"Business question: {question}")

    # Top finding
    top = ranked_findings[0]
    parts.append(
        f"The highest-impact finding (score {top.get('score', 0)}/100): "
        f"{top.get('description', '')}."
    )

    # Theme summary
    theme_names = [tg["theme"] for tg in theme_groups]
    if len(theme_names) > 1:
        parts.append(
            f"Findings span {', '.join(theme_names)} themes."
        )

    # Contradictions
    if contradictions:
        parts.append(
            f"{len(contradictions)} potential contradiction(s) detected "
            f"that warrant further investigation."
        )

    # Action items
    high_actions = [a for a in action_items if a["priority"] == "high"]
    if high_actions:
        parts.append(
            f"{len(high_actions)} high-priority action(s) identified."
        )
    elif not action_items:
        parts.append(
            "No immediately actionable findings — consider deeper "
            "investigation or additional data collection."
        )

    return " ".join(parts)
