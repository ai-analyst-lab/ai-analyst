"""
Simpson's Paradox Scanner (DQ-3.5).

Scans analytical results for Simpson's Paradox -- where a trend that
appears in aggregated data reverses when the data is split into segments.
This is one of the most dangerous analytical errors because the aggregate
conclusion is literally the opposite of what each segment shows.

Provides five main capabilities:
1. check_simpsons_paradox -- single-dimension paradox detection
2. check_simpsons_multi_segment -- scan multiple dimensions at once
3. weighted_vs_unweighted -- detect weighting-induced paradoxes
4. generate_paradox_report -- markdown report from check results
5. suggest_segments_to_check -- heuristic ranking of likely confounders

Legacy aliases (scan_dimensions) preserved for backward compatibility.

Usage:
    from helpers.validation.simpsons_paradox import (
        check_simpsons_paradox, check_simpsons_multi_segment,
        weighted_vs_unweighted, generate_paradox_report,
        suggest_segments_to_check, scan_dimensions,
    )

    # Check a single dimension for reversal
    result = check_simpsons_paradox(
        df, metric_column="admitted",
        segment_column="department",
        comparison_column="group",
    )
    if result["paradox_detected"]:
        print(result["explanation"])

    # Scan multiple candidate dimensions
    result = check_simpsons_multi_segment(
        df, metric_column="admitted",
        segment_columns=["department", "region"],
        comparison_column="group",
    )
"""

from __future__ import annotations

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _determine_direction(value_a: float, value_b: float) -> str:
    """Compare two values and return a direction label.

    Args:
        value_a: Metric value for comparison group A.
        value_b: Metric value for comparison group B.

    Returns:
        "positive" if A > B, "negative" if A < B, "neutral" if equal.
    """
    if value_a > value_b:
        return "positive"
    elif value_a < value_b:
        return "negative"
    else:
        return "neutral"


def _compute_severity(n_reversals: int, n_total_segments: int) -> str:
    """Compute severity based on reversal ratio.

    Args:
        n_reversals: Number of segments that reverse aggregate direction.
        n_total_segments: Total non-neutral segments.

    Returns:
        "none", "low", "medium", or "high".
    """
    if n_total_segments == 0 or n_reversals == 0:
        return "none"
    ratio = n_reversals / n_total_segments
    if ratio <= 0.25:
        return "low"
    elif ratio <= 0.5:
        return "medium"
    else:
        return "high"


def _resolve_comparison_groups(series: pd.Series):
    """Identify the two comparison groups from a column.

    For categorical/object columns, takes the two most frequent values.
    For numeric columns, splits at the median into two groups.

    Args:
        series: The comparison column (with NaN dropped).

    Returns:
        Tuple of (label_a, label_b, mask_a, mask_b) where masks are boolean
        arrays aligned to the input series index.
    """
    if pd.api.types.is_numeric_dtype(series) and series.nunique() > 2:
        median_val = series.median()
        mask_a = series <= median_val
        mask_b = series > median_val
        label_a = f"<= {median_val}"
        label_b = f"> {median_val}"
        return label_a, label_b, mask_a, mask_b

    counts = series.value_counts()
    if len(counts) < 2:
        return None, None, None, None

    label_a = counts.index[0]
    label_b = counts.index[1]
    mask_a = series == label_a
    mask_b = series == label_b
    return label_a, label_b, mask_a, mask_b


def _empty_result(message: str) -> dict:
    """Return a default result dict for edge cases.

    Args:
        message: Explanation string for why the check could not run.

    Returns:
        dict with paradox_detected=False and the message as explanation.
    """
    return {
        "paradox_detected": False,
        "aggregate_direction": "neutral",
        "segment_results": [],
        "reversals": [],
        "explanation": message,
        "severity": "none",
    }


# ---------------------------------------------------------------------------
# Core paradox check
# ---------------------------------------------------------------------------

def check_simpsons_paradox(
    df: pd.DataFrame,
    metric_column: str | None = None,
    segment_column: str | None = None,
    comparison_column: str | None = None,
    agg_func: str = "mean",
    # Legacy parameter names (backward compat)
    metric_col: str | None = None,
    group_col: str | None = None,
    segment_col: str | None = None,
) -> dict:
    """Check for Simpson's Paradox across a single segmentation dimension.

    Compares the metric direction (group A vs group B) at the aggregate
    level versus within each segment. A paradox is detected when the
    aggregate direction differs from the majority of segment-level
    directions.

    Supports both the new API (metric_column, segment_column,
    comparison_column) and the legacy API (metric_col, group_col,
    segment_col) for backward compatibility.

    Args:
        df: DataFrame containing the data.
        metric_column: Column name of the numeric metric to compare.
        segment_column: Column to segment by (e.g., "department").
        comparison_column: Binary/categorical grouping column (e.g.,
            "group" with "A"/"B", or "period" with "before"/"after").
            For numeric columns with >2 unique values, splits at median.
        agg_func: Aggregation function -- "mean" or "sum".
        metric_col: Legacy alias for metric_column.
        group_col: Legacy alias for comparison_column.
        segment_col: Legacy alias for segment_column.

    Returns:
        dict with keys:
            paradox_detected (bool),
            aggregate_direction ("positive"|"negative"|"neutral"),
            segment_results (list of dicts with segment/direction/
                value_a/value_b),
            reversals (list of segment names where direction reversed),
            explanation (str -- human-readable interpretation),
            severity ("none"|"low"|"medium"|"high")

        Legacy callers also get: segment_directions, reversal_segments,
            and severity mapped to PASS/INFO/BLOCKER.
    """
    # Resolve legacy vs new parameter names
    _metric = metric_column or metric_col
    _comparison = comparison_column or group_col
    _segment = segment_column or segment_col
    _is_legacy = metric_col is not None or group_col is not None

    if _metric is None or _comparison is None or _segment is None:
        return _empty_result(
            "Missing required parameters: metric_column, comparison_column, "
            "and segment_column are all required."
        )

    # Edge case: empty DataFrame
    if len(df) == 0:
        return _empty_result("DataFrame is empty -- cannot check for paradox.")

    # Drop rows with nulls in any of the three key columns
    working = df.dropna(subset=[_metric, _comparison, _segment])
    if len(working) < 2:
        return _empty_result(
            "Insufficient non-null data to check for paradox."
        )

    # Identify the two comparison groups
    label_a, label_b, mask_a, mask_b = _resolve_comparison_groups(
        working[_comparison]
    )
    if label_a is None:
        return _empty_result(
            f"Only one group found in '{_comparison}' -- need at least two."
        )

    subset = working[mask_a | mask_b].copy()

    # Choose aggregation function
    agg_fn = np.mean if agg_func == "mean" else np.sum

    # --- Aggregate comparison ---
    agg_a = float(agg_fn(subset.loc[mask_a[subset.index], _metric]))
    agg_b = float(agg_fn(subset.loc[mask_b[subset.index], _metric]))
    aggregate_direction = _determine_direction(agg_a, agg_b)

    # --- Segment-level comparison ---
    segment_results = []
    for segment_value, seg_df in subset.groupby(_segment):
        seg_mask_a = seg_df[_comparison] == label_a if not isinstance(label_a, str) or "<=" not in str(label_a) else mask_a[seg_df.index]
        seg_mask_b = seg_df[_comparison] == label_b if not isinstance(label_b, str) or ">" not in str(label_b) else mask_b[seg_df.index]

        # Handle median-split groups using the original masks
        if isinstance(label_a, str) and ("<=" in label_a or ">" in label_a):
            seg_mask_a = mask_a[seg_df.index]
            seg_mask_b = mask_b[seg_df.index]

        vals_a = seg_df.loc[seg_mask_a, _metric]
        vals_b = seg_df.loc[seg_mask_b, _metric]

        # Skip segments where one group is empty
        if len(vals_a) == 0 or len(vals_b) == 0:
            continue

        seg_val_a = float(agg_fn(vals_a))
        seg_val_b = float(agg_fn(vals_b))
        seg_direction = _determine_direction(seg_val_a, seg_val_b)

        segment_results.append({
            "segment": segment_value,
            "direction": seg_direction,
            "value_a": round(seg_val_a, 6),
            "value_b": round(seg_val_b, 6),
        })

    # --- Detect paradox ---
    non_neutral = [s for s in segment_results if s["direction"] != "neutral"]

    if len(non_neutral) == 0 or aggregate_direction == "neutral":
        result = {
            "paradox_detected": False,
            "aggregate_direction": aggregate_direction,
            "segment_results": segment_results,
            "reversals": [],
            "explanation": (
                f"No directional comparison possible -- "
                f"aggregate is '{aggregate_direction}', "
                f"{len(non_neutral)} segments have a clear direction."
            ),
            "severity": "none",
        }
        if _is_legacy:
            result.update(_legacy_fields(result))
        return result

    # Count reversals (segments with opposite direction from aggregate)
    reversals = [
        s["segment"] for s in non_neutral
        if s["direction"] != aggregate_direction
    ]
    agree_count = len(non_neutral) - len(reversals)
    paradox_detected = len(reversals) > agree_count
    severity = _compute_severity(len(reversals), len(non_neutral))

    # --- Build explanation ---
    if paradox_detected:
        explanation = (
            f"Simpson's Paradox detected on '{_segment}'. "
            f"Aggregate: {label_a} {'>' if aggregate_direction == 'positive' else '<'} "
            f"{label_b} ({agg_func} {_metric}: {agg_a:.4f} vs {agg_b:.4f}). "
            f"But in {len(reversals)} of {len(non_neutral)} segments, "
            f"the direction reverses. "
            f"Reversing segments: {reversals}. "
            f"The aggregate result is misleading -- segment-level analysis "
            f"is required."
        )
    else:
        explanation = (
            f"No paradox on '{_segment}'. "
            f"Aggregate: {label_a} {'>' if aggregate_direction == 'positive' else '<'} "
            f"{label_b}. "
            f"{agree_count} of {len(non_neutral)} segments agree with "
            f"aggregate direction."
        )
        if len(reversals) > 0:
            explanation += (
                f" Note: {len(reversals)} segment(s) show reversal: "
                f"{reversals} -- worth investigating."
            )

    result = {
        "paradox_detected": paradox_detected,
        "aggregate_direction": aggregate_direction,
        "segment_results": segment_results,
        "reversals": reversals,
        "explanation": explanation,
        "severity": severity,
    }

    # Add legacy-compatible fields if called with old parameter names
    if _is_legacy:
        result.update(_legacy_fields(result))

    return result


def _legacy_fields(result: dict) -> dict:
    """Map new-style result keys to legacy field names.

    Args:
        result: A check result dict with new-style keys.

    Returns:
        dict with legacy keys: segment_directions, reversal_segments, severity.
    """
    # Map direction labels for legacy consumers
    direction_map = {
        "positive": "A>B",
        "negative": "B>A",
        "neutral": "equal",
    }

    legacy_segment_directions = []
    for seg in result.get("segment_results", []):
        legacy_segment_directions.append({
            "segment": seg["segment"],
            "direction": direction_map.get(seg["direction"], seg["direction"]),
            "group_a_val": seg["value_a"],
            "group_b_val": seg["value_b"],
        })

    # Map severity for legacy consumers
    severity_map = {
        "none": "PASS",
        "low": "INFO",
        "medium": "INFO",
        "high": "BLOCKER",
    }

    # Override severity for paradox_detected
    if result["paradox_detected"]:
        legacy_severity = "BLOCKER"
    elif len(result.get("reversals", [])) > 0:
        legacy_severity = "INFO"
    else:
        legacy_severity = "PASS"

    return {
        "aggregate_direction": direction_map.get(
            result["aggregate_direction"], result["aggregate_direction"]
        ),
        "segment_directions": legacy_segment_directions,
        "reversal_segments": result.get("reversals", []),
        "severity": legacy_severity,
    }


# ---------------------------------------------------------------------------
# Multi-segment scanner
# ---------------------------------------------------------------------------

def check_simpsons_multi_segment(
    df: pd.DataFrame,
    metric_column: str,
    segment_columns: list[str],
    comparison_column: str,
    agg_func: str = "mean",
) -> dict:
    """Run the paradox check across multiple segmentation dimensions.

    Args:
        df: DataFrame containing the data.
        metric_column: Column name of the numeric metric.
        segment_columns: List of column names to check as segments.
        comparison_column: Binary/categorical grouping column.
        agg_func: Aggregation function -- "mean" or "sum".

    Returns:
        dict with keys per segment_column, each containing a
        check_simpsons_paradox result. Also includes summary keys:
            scanned (int), paradoxes_found (int), interpretation (str).
    """
    if not segment_columns:
        return {
            "scanned": 0,
            "paradoxes_found": 0,
            "results": {},
            "interpretation": "No segment columns provided -- nothing to scan.",
        }

    results = {}
    paradox_count = 0

    for seg_col in segment_columns:
        if seg_col not in df.columns:
            results[seg_col] = _empty_result(
                f"Column '{seg_col}' not found in DataFrame."
            )
            continue

        result = check_simpsons_paradox(
            df,
            metric_column=metric_column,
            segment_column=seg_col,
            comparison_column=comparison_column,
            agg_func=agg_func,
        )
        results[seg_col] = result
        if result["paradox_detected"]:
            paradox_count += 1

    # Build interpretation
    if paradox_count == 0:
        interpretation = (
            f"Scanned {len(segment_columns)} dimension(s) for Simpson's "
            f"Paradox -- none detected. Aggregate results are consistent "
            f"with segment-level patterns."
        )
    else:
        paradox_dims = [
            col for col in segment_columns
            if results.get(col, {}).get("paradox_detected", False)
        ]
        interpretation = (
            f"Simpson's Paradox detected in {paradox_count} of "
            f"{len(segment_columns)} dimension(s): {paradox_dims}. "
            f"Aggregate conclusions may be misleading -- segment-level "
            f"analysis is required before drawing conclusions."
        )

    return {
        "scanned": len(segment_columns),
        "paradoxes_found": paradox_count,
        "results": results,
        "interpretation": interpretation,
    }


# ---------------------------------------------------------------------------
# Weighted vs unweighted comparison
# ---------------------------------------------------------------------------

def weighted_vs_unweighted(
    df: pd.DataFrame,
    metric_column: str,
    weight_column: str,
    segment_column: str,
) -> dict:
    """Compare weighted average vs unweighted average per segment.

    A common source of Simpson's Paradox is when segments have vastly
    different sizes. The weighted average (by segment size) can disagree
    with the simple unweighted average across segments.

    Args:
        df: DataFrame containing the data.
        metric_column: Column with the metric values.
        weight_column: Column with the weights (e.g., group size, revenue).
        segment_column: Column defining the segments.

    Returns:
        dict with keys:
            paradox_detected (bool),
            weighted_result (float),
            unweighted_result (float),
            difference (float),
            segment_details (list of dicts per segment),
            explanation (str)
    """
    working = df.dropna(subset=[metric_column, weight_column, segment_column])

    if len(working) == 0:
        return {
            "paradox_detected": False,
            "weighted_result": None,
            "unweighted_result": None,
            "difference": 0.0,
            "segment_details": [],
            "explanation": "No valid data after dropping nulls.",
        }

    # Filter out zero and negative weights
    valid_weights = working[working[weight_column] > 0].copy()

    if len(valid_weights) == 0:
        return {
            "paradox_detected": False,
            "weighted_result": None,
            "unweighted_result": None,
            "difference": 0.0,
            "segment_details": [],
            "explanation": "All weights are zero or negative.",
        }

    # Compute per-segment metrics
    segment_details = []
    segment_means = []

    for seg_val, seg_df in valid_weights.groupby(segment_column):
        seg_mean = float(seg_df[metric_column].mean())
        seg_weight_sum = float(seg_df[weight_column].sum())
        seg_weighted_mean = float(
            np.average(seg_df[metric_column], weights=seg_df[weight_column])
        )
        segment_details.append({
            "segment": seg_val,
            "mean": seg_mean,
            "weighted_mean": seg_weighted_mean,
            "total_weight": seg_weight_sum,
            "count": len(seg_df),
        })
        segment_means.append(seg_mean)

    # Overall weighted average
    weighted_result = float(
        np.average(
            valid_weights[metric_column],
            weights=valid_weights[weight_column],
        )
    )

    # Overall unweighted average (mean of segment means)
    unweighted_result = float(np.mean(segment_means))

    difference = weighted_result - unweighted_result

    # A paradox exists if the direction flips (one is positive relative to
    # some reference and the other is negative, but more practically: if
    # they disagree on which side of the midpoint they fall)
    paradox_detected = (
        (weighted_result > unweighted_result and difference != 0)
        or (weighted_result < unweighted_result and difference != 0)
    ) and (
        # Only flag if the sign of difference from overall mean differs
        # meaningfully -- use a threshold of the magnitude
        abs(difference) > 0.01 * max(abs(weighted_result), abs(unweighted_result), 1e-9)
    )

    if paradox_detected:
        explanation = (
            f"Weighted average ({weighted_result:.4f}) differs from "
            f"unweighted segment average ({unweighted_result:.4f}) by "
            f"{difference:.4f}. This suggests segment size imbalance is "
            f"influencing aggregate results -- a potential Simpson's Paradox."
        )
    else:
        explanation = (
            f"Weighted ({weighted_result:.4f}) and unweighted "
            f"({unweighted_result:.4f}) averages are consistent "
            f"(diff={difference:.4f})."
        )

    return {
        "paradox_detected": paradox_detected,
        "weighted_result": weighted_result,
        "unweighted_result": unweighted_result,
        "difference": difference,
        "segment_details": segment_details,
        "explanation": explanation,
    }


# ---------------------------------------------------------------------------
# Report generator
# ---------------------------------------------------------------------------

def generate_paradox_report(check_result: dict) -> str:
    """Format a check result into a human-readable markdown report.

    Accepts the output of check_simpsons_paradox or
    check_simpsons_multi_segment.

    Args:
        check_result: Dict returned by check_simpsons_paradox (or
            check_simpsons_multi_segment with results nested per column).

    Returns:
        str: Markdown-formatted report.
    """
    lines = ["## Simpson's Paradox Check", ""]

    # Multi-segment result (has 'scanned' key)
    if "scanned" in check_result:
        lines.append(
            f"**Dimensions scanned:** {check_result['scanned']}"
        )
        lines.append(
            f"**Paradoxes found:** {check_result['paradoxes_found']}"
        )
        lines.append("")
        lines.append(check_result.get("interpretation", ""))
        lines.append("")

        results = check_result.get("results", {})
        if isinstance(results, dict):
            for col_name, res in results.items():
                lines.append(f"### Segment: {col_name}")
                lines.append("")
                lines.append(_format_single_result(res))
                lines.append("")
        elif isinstance(results, list):
            for i, res in enumerate(results):
                lines.append(f"### Dimension {i + 1}")
                lines.append("")
                lines.append(_format_single_result(res))
                lines.append("")
        return "\n".join(lines)

    # Single-dimension result
    lines.append(_format_single_result(check_result))
    return "\n".join(lines)


def _format_single_result(result: dict) -> str:
    """Format a single paradox check result as markdown.

    Args:
        result: Dict from check_simpsons_paradox.

    Returns:
        str: Markdown block.
    """
    lines = []
    detected = result.get("paradox_detected", False)
    status = "DETECTED" if detected else "NOT DETECTED"
    severity = result.get("severity", "none")

    lines.append(f"**Status:** {status}")
    lines.append(f"**Severity:** {severity}")
    lines.append(
        f"**Aggregate direction:** {result.get('aggregate_direction', 'N/A')}"
    )
    lines.append("")

    segment_results = result.get("segment_results", [])
    if segment_results:
        lines.append("| Segment | Direction | Value A | Value B |")
        lines.append("|---------|-----------|---------|---------|")
        for seg in segment_results:
            lines.append(
                f"| {seg['segment']} | {seg['direction']} "
                f"| {seg['value_a']:.4f} | {seg['value_b']:.4f} |"
            )
        lines.append("")

    reversals = result.get("reversals", [])
    if reversals:
        lines.append(f"**Reversals:** {', '.join(str(r) for r in reversals)}")
        lines.append("")

    explanation = result.get("explanation", "")
    if explanation:
        lines.append(f"> {explanation}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Segment suggestion heuristic
# ---------------------------------------------------------------------------

def suggest_segments_to_check(
    df: pd.DataFrame,
    metric_column: str,
    categorical_columns: list[str] | None = None,
    max_segments: int = 5,
) -> list[str]:
    """Identify which segment columns are most likely to reveal paradoxes.

    Ranks candidates by variance in group sizes -- large imbalances in
    segment sizes are the primary mechanism behind Simpson's Paradox.
    Also considers the number of distinct values (too many segments
    dilute the check).

    Args:
        df: DataFrame to analyze.
        metric_column: The metric column (must exist in df).
        categorical_columns: Explicit list of columns to consider. If
            None, auto-detects object/category columns.
        max_segments: Maximum number of suggestions to return.

    Returns:
        List of column names ranked by likelihood of revealing a paradox,
        most likely first. Returns empty list if no suitable columns found.
    """
    if metric_column not in df.columns:
        return []

    # Auto-detect categorical columns if not provided
    if categorical_columns is None:
        candidates = [
            col for col in df.columns
            if col != metric_column
            and (
                pd.api.types.is_object_dtype(df[col])
                or pd.api.types.is_string_dtype(df[col])
                or isinstance(df[col].dtype, pd.CategoricalDtype)
                or pd.api.types.is_bool_dtype(df[col])
            )
        ]
    else:
        candidates = [
            col for col in categorical_columns
            if col in df.columns and col != metric_column
        ]

    if not candidates:
        return []

    # Score each candidate
    scored = []
    for col in candidates:
        non_null = df[col].dropna()
        if len(non_null) == 0:
            continue

        n_unique = non_null.nunique()

        # Skip if only 1 value or too many values (> 50)
        if n_unique < 2 or n_unique > 50:
            continue

        # Compute coefficient of variation of group sizes
        group_sizes = non_null.value_counts().values
        cv = float(np.std(group_sizes) / np.mean(group_sizes)) if np.mean(group_sizes) > 0 else 0.0

        # Penalize very high cardinality (diminishing returns past ~10)
        cardinality_penalty = 1.0 / (1.0 + max(0, n_unique - 10) * 0.1)

        score = cv * cardinality_penalty
        scored.append((col, score))

    # Sort by score descending and return top max_segments
    scored.sort(key=lambda x: x[1], reverse=True)
    return [col for col, _ in scored[:max_segments]]


# ---------------------------------------------------------------------------
# Legacy API: scan_dimensions (backward compatibility)
# ---------------------------------------------------------------------------

def scan_dimensions(
    df: pd.DataFrame,
    metric_col: str,
    group_col: str,
    candidate_segments: list[str],
) -> dict:
    """Scan multiple candidate segment columns for Simpson's Paradox.

    Legacy wrapper around check_simpsons_multi_segment that preserves
    the original return format (list-based results instead of dict-based).

    Args:
        df: DataFrame containing the data.
        metric_col: Column name of the metric to compare (numeric).
        group_col: Column name defining the two groups.
        candidate_segments: List of column names to scan.

    Returns:
        dict with keys: scanned, paradoxes_found, results (list),
        interpretation.
    """
    if not candidate_segments:
        return {
            "scanned": 0,
            "paradoxes_found": 0,
            "results": [],
            "interpretation": "No candidate segments provided -- nothing to scan.",
        }

    results = []
    paradox_count = 0

    for seg_col in candidate_segments:
        if seg_col not in df.columns:
            results.append({
                "paradox_detected": False,
                "aggregate_direction": "equal",
                "segment_directions": [],
                "reversal_segments": [],
                "explanation": f"Column '{seg_col}' not found in DataFrame.",
                "severity": "WARNING",
            })
            continue

        result = check_simpsons_paradox(
            df,
            metric_col=metric_col,
            group_col=group_col,
            segment_col=seg_col,
        )
        results.append(result)
        if result["paradox_detected"]:
            paradox_count += 1

    # Interpretation
    if paradox_count == 0:
        interpretation = (
            f"Scanned {len(candidate_segments)} dimension(s) for Simpson's "
            f"Paradox -- none detected. Aggregate results are consistent "
            f"with segment-level patterns."
        )
    else:
        paradox_dims = [
            candidate_segments[i]
            for i, r in enumerate(results)
            if r.get("paradox_detected", False)
        ]
        interpretation = (
            f"Simpson's Paradox detected in {paradox_count} of "
            f"{len(candidate_segments)} dimension(s): {paradox_dims}. "
            f"Aggregate conclusions may be misleading -- segment-level "
            f"analysis is required before drawing conclusions."
        )

    return {
        "scanned": len(candidate_segments),
        "paradoxes_found": paradox_count,
        "results": results,
        "interpretation": interpretation,
    }
