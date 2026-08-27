"""
Logical Validation Helpers (DQ-3.2 — Layer 2).

Validates LOGICAL consistency of analytical results: aggregation integrity,
trend continuity, segment exhaustiveness, temporal consistency, percentage
sums, monotonicity, ratio bounds, group balance, and future-date detection.

Usage (new API — ok-based returns):
    from helpers.validation.logical_validator import (
        validate_aggregation_consistency,
        validate_percentages_sum,
        validate_monotonic,
        validate_trend_consistency,
        validate_ratio_bounds,
        validate_group_balance,
        validate_no_future_dates,
        run_logical_checks,
    )

Legacy API (severity-based returns — used by confidence_scoring and
validation_e2e):
    from helpers.validation.logical_validator import (
        validate_aggregation_consistency_legacy,
        validate_trend_continuity,
        validate_segment_exhaustiveness,
        validate_temporal_consistency,
    )
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import numpy as np
import pandas as pd


# ===================================================================
# NEW API — consistent ok-based return dicts
# ===================================================================

# ---------------------------------------------------------------------------
# 1. Aggregation consistency
# ---------------------------------------------------------------------------

def validate_aggregation_consistency(
    detail_df: pd.DataFrame,
    summary_df: pd.DataFrame,
    *args,
    **kwargs,
) -> dict:
    """Check that detail-level data aggregates to match summary totals.

    Supports two calling conventions:

    **New API** (ok-based return)::

        validate_aggregation_consistency(
            detail_df, summary_df,
            metric_column="amount", group_column="region", tolerance=0.01,
        )

    **Legacy API** (severity-based return -- used by e2e tests and
    confidence_scoring)::

        validate_aggregation_consistency(
            detail_df, summary_df,
            group_col="region", metric_col="amount", agg="sum",
            tolerance=0.01,
        )

    The function auto-detects which API is intended based on keyword
    argument names.  When legacy keywords (``group_col``, ``metric_col``,
    ``agg``) are present, or when exactly two positional strings are
    passed (old positional order: group_col, metric_col), the legacy
    code path is used.
    """
    # --- Detect legacy call pattern ---
    legacy_keywords = {"group_col", "metric_col", "agg"}
    if legacy_keywords & set(kwargs.keys()):
        return _aggregation_consistency_legacy(detail_df, summary_df, *args, **kwargs)

    # Positional fallback: old API passes (group_col, metric_col) as 3rd, 4th positional.
    # New API passes (metric_column) as 3rd positional.
    # Distinguish: if there are exactly 2 positional str args AND neither "metric_column"
    # nor "group_column" is in kwargs, assume legacy positional call.
    if (
        len(args) >= 2
        and isinstance(args[0], str)
        and isinstance(args[1], str)
        and "metric_column" not in kwargs
        and "group_column" not in kwargs
    ):
        legacy_kw = {k: v for k, v in kwargs.items() if k not in ("agg",)}
        if len(args) > 2:
            legacy_kw["agg"] = args[2]
        return _aggregation_consistency_legacy(
            detail_df, summary_df, group_col=args[0], metric_col=args[1],
            **legacy_kw,
        )

    # --- New API ---
    return _aggregation_consistency_new(detail_df, summary_df, *args, **kwargs)


def _aggregation_consistency_new(
    detail_df: pd.DataFrame,
    summary_df: pd.DataFrame,
    metric_column: str | None = None,
    group_column: str | None = None,
    tolerance: float = 0.01,
) -> dict:
    """New ok-based aggregation consistency check (internal).

    Args:
        detail_df: Row-level detail DataFrame.
        summary_df: Pre-aggregated summary DataFrame.
        metric_column: Column to aggregate (must be numeric).
        group_column: Optional grouping column.
        tolerance: Maximum allowed relative difference (default 0.01 = 1%).

    Returns:
        dict with keys: ok, expected_total, actual_total, difference, tolerance.
    """
    try:
        if detail_df is None or summary_df is None:
            return {
                "ok": False,
                "expected_total": 0.0,
                "actual_total": 0.0,
                "difference": 0.0,
                "tolerance": tolerance,
            }

        if len(detail_df) == 0 and len(summary_df) == 0:
            return {
                "ok": True,
                "expected_total": 0.0,
                "actual_total": 0.0,
                "difference": 0.0,
                "tolerance": tolerance,
            }

        if group_column is not None:
            detail_agg = detail_df.groupby(group_column)[metric_column].sum()
            summary_agg = (
                summary_df.set_index(group_column)[metric_column]
                if group_column in summary_df.columns
                else pd.Series(dtype=float)
            )
            expected_total = float(detail_agg.sum())
            actual_total = float(summary_agg.sum()) if len(summary_agg) > 0 else 0.0
        else:
            expected_total = float(detail_df[metric_column].sum())
            actual_total = float(summary_df[metric_column].sum())

        difference = abs(expected_total - actual_total)
        denominator = abs(expected_total) if expected_total != 0 else abs(actual_total)
        relative_diff = difference / denominator if denominator != 0 else 0.0

        return {
            "ok": relative_diff <= tolerance,
            "expected_total": round(expected_total, 6),
            "actual_total": round(actual_total, 6),
            "difference": round(difference, 6),
            "tolerance": tolerance,
        }
    except Exception:
        return {
            "ok": False,
            "expected_total": 0.0,
            "actual_total": 0.0,
            "difference": 0.0,
            "tolerance": tolerance,
        }


def _aggregation_consistency_legacy(
    detail_df, summary_df, group_col=None, metric_col=None,
    agg="sum", tolerance=0.01,
) -> dict:
    """Legacy severity-based aggregation consistency check (internal)."""
    if len(detail_df) == 0 and len(summary_df) == 0:
        return {"valid": True, "mismatches": [], "severity": "PASS"}

    if len(detail_df) == 0 or len(summary_df) == 0:
        return {"valid": False, "mismatches": [], "severity": "BLOCKER"}

    re_agg = detail_df.groupby(group_col)[metric_col].agg(agg).reset_index()
    re_agg.columns = [group_col, "expected"]

    summary_subset = summary_df[[group_col, metric_col]].copy()
    summary_subset.columns = [group_col, "actual"]

    merged = pd.merge(re_agg, summary_subset, on=group_col, how="outer")

    mismatches = []
    for _, row in merged.iterrows():
        expected = row.get("expected")
        actual = row.get("actual")

        if pd.isna(expected) or pd.isna(actual):
            mismatches.append({
                "group": row[group_col],
                "expected": None if pd.isna(expected) else float(expected),
                "actual": None if pd.isna(actual) else float(actual),
                "diff_pct": None,
            })
            continue

        expected = float(expected)
        actual = float(actual)
        denominator = abs(expected) if expected != 0 else abs(actual)
        diff_pct = abs(actual - expected) / denominator if denominator != 0 else 0.0

        if diff_pct > tolerance:
            mismatches.append({
                "group": row[group_col],
                "expected": expected,
                "actual": actual,
                "diff_pct": round(diff_pct, 6),
            })

    if len(mismatches) == 0:
        severity = "PASS"
    elif any(m["diff_pct"] is None or m["diff_pct"] > 0.05 for m in mismatches):
        severity = "BLOCKER"
    else:
        severity = "WARNING"

    return {"valid": severity == "PASS", "mismatches": mismatches, "severity": severity}


# ---------------------------------------------------------------------------
# 2. Percentages sum
# ---------------------------------------------------------------------------

def validate_percentages_sum(
    df: pd.DataFrame,
    pct_column: str,
    group_column: str | None = None,
    expected_sum: float = 100.0,
    tolerance: float = 1.0,
) -> dict:
    """Check that a percentage column sums to the expected total.

    When ``group_column`` is provided, the check is applied within each
    group independently and the result reflects the worst-case group.

    Args:
        df: DataFrame containing the percentage column.
        pct_column: Column holding percentage values.
        group_column: Optional column for within-group checks.
        expected_sum: Expected total (default 100.0).
        tolerance: Allowed absolute deviation (default 1.0).

    Returns:
        dict with keys:
            ok (bool),
            actual_sum (float) — overall or worst-case group sum,
            difference (float) — absolute deviation from expected.
    """
    try:
        if df is None or len(df) == 0:
            return {"ok": True, "actual_sum": 0.0, "difference": 0.0}

        if group_column is not None:
            worst_diff = 0.0
            worst_sum = expected_sum
            for _name, grp in df.groupby(group_column):
                grp_sum = float(grp[pct_column].sum())
                diff = abs(grp_sum - expected_sum)
                if diff > worst_diff:
                    worst_diff = diff
                    worst_sum = grp_sum
            return {
                "ok": worst_diff <= tolerance,
                "actual_sum": round(worst_sum, 6),
                "difference": round(worst_diff, 6),
            }
        else:
            actual_sum = float(df[pct_column].sum())
            difference = abs(actual_sum - expected_sum)
            return {
                "ok": difference <= tolerance,
                "actual_sum": round(actual_sum, 6),
                "difference": round(difference, 6),
            }
    except Exception:
        return {"ok": False, "actual_sum": 0.0, "difference": 0.0}


# ---------------------------------------------------------------------------
# 3. Monotonic check
# ---------------------------------------------------------------------------

def validate_monotonic(
    df: pd.DataFrame,
    column: str,
    direction: str = "increasing",
    strict: bool = False,
) -> dict:
    """Check that a column is monotonically increasing or decreasing.

    Args:
        df: DataFrame containing the column to check.
        column: Column name to validate.
        direction: ``'increasing'`` or ``'decreasing'``.
        strict: If True, consecutive equal values are counted as
            violations.

    Returns:
        dict with keys:
            ok (bool),
            violations_count (int),
            first_violation_index — index label of the first violation,
                or None.
    """
    try:
        if df is None or len(df) < 2:
            return {"ok": True, "violations_count": 0, "first_violation_index": None}

        series = df[column].dropna()
        if len(series) < 2:
            return {"ok": True, "violations_count": 0, "first_violation_index": None}

        values = series.values
        indices = series.index.tolist()

        violations_count = 0
        first_violation_index = None

        for i in range(1, len(values)):
            prev_val = values[i - 1]
            curr_val = values[i]

            if direction == "increasing":
                violation = (curr_val < prev_val) if not strict else (curr_val <= prev_val)
            else:  # decreasing
                violation = (curr_val > prev_val) if not strict else (curr_val >= prev_val)

            if violation:
                violations_count += 1
                if first_violation_index is None:
                    first_violation_index = indices[i]

        return {
            "ok": violations_count == 0,
            "violations_count": violations_count,
            "first_violation_index": first_violation_index,
        }
    except Exception:
        return {"ok": False, "violations_count": 0, "first_violation_index": None}


# ---------------------------------------------------------------------------
# 4. Trend consistency (rolling z-score)
# ---------------------------------------------------------------------------

def validate_trend_consistency(
    values: Union[list, np.ndarray, pd.Series],
    window: int = 3,
    max_zscore: float = 3.0,
) -> dict:
    """Check for implausible spikes or drops in a series via rolling z-scores.

    Computes a rolling mean and standard deviation over ``window`` periods,
    then flags any point whose z-score (relative to the rolling stats)
    exceeds ``max_zscore``.

    Args:
        values: Ordered numeric sequence (list, array, or Series).
        window: Rolling window size (default 3).
        max_zscore: Threshold above which a point is anomalous
            (default 3.0).

    Returns:
        dict with keys:
            ok (bool),
            anomalies (list of dicts with index, value, zscore).
    """
    try:
        s = pd.Series(values, dtype=float).dropna().reset_index(drop=True)

        if len(s) <= window:
            return {"ok": True, "anomalies": []}

        rolling_mean = s.rolling(window=window, min_periods=window).mean()
        rolling_std = s.rolling(window=window, min_periods=window).std()

        anomalies: list[dict] = []
        for i in range(window, len(s)):
            rm = rolling_mean.iloc[i - 1]
            rs = rolling_std.iloc[i - 1]
            if rs is None or pd.isna(rs) or rs == 0:
                continue
            zscore = abs(s.iloc[i] - rm) / rs
            if zscore > max_zscore:
                anomalies.append({
                    "index": int(i),
                    "value": float(s.iloc[i]),
                    "zscore": round(float(zscore), 4),
                })

        return {"ok": len(anomalies) == 0, "anomalies": anomalies}
    except Exception:
        return {"ok": False, "anomalies": []}


# ---------------------------------------------------------------------------
# 5. Ratio bounds
# ---------------------------------------------------------------------------

def validate_ratio_bounds(
    df: pd.DataFrame,
    numerator_col: str,
    denominator_col: str,
    min_ratio: float = 0.0,
    max_ratio: float = 1.0,
) -> dict:
    """Check that computed ratios fall within the given bounds.

    Rows where the denominator is zero or NaN are excluded from the
    count but are not treated as violations.

    Args:
        df: DataFrame with numerator and denominator columns.
        numerator_col: Column name for the numerator.
        denominator_col: Column name for the denominator.
        min_ratio: Minimum acceptable ratio (inclusive, default 0.0).
        max_ratio: Maximum acceptable ratio (inclusive, default 1.0).

    Returns:
        dict with keys:
            ok (bool),
            out_of_bounds_count (int),
            out_of_bounds_sample (list of dicts with index, ratio).
    """
    try:
        if df is None or len(df) == 0:
            return {"ok": True, "out_of_bounds_count": 0, "out_of_bounds_sample": []}

        denom = df[denominator_col]
        numer = df[numerator_col]

        valid_mask = (denom != 0) & denom.notna() & numer.notna()
        if valid_mask.sum() == 0:
            return {"ok": True, "out_of_bounds_count": 0, "out_of_bounds_sample": []}

        ratios = numer[valid_mask] / denom[valid_mask]
        oob_mask = (ratios < min_ratio) | (ratios > max_ratio)
        oob_count = int(oob_mask.sum())

        sample: list[dict] = []
        for idx in ratios[oob_mask].head(5).index:
            sample.append({
                "index": idx if not isinstance(idx, (np.integer,)) else int(idx),
                "ratio": round(float(ratios.loc[idx]), 6),
            })

        return {
            "ok": oob_count == 0,
            "out_of_bounds_count": oob_count,
            "out_of_bounds_sample": sample,
        }
    except Exception:
        return {"ok": False, "out_of_bounds_count": 0, "out_of_bounds_sample": []}


# ---------------------------------------------------------------------------
# 6. Group balance
# ---------------------------------------------------------------------------

def validate_group_balance(
    df: pd.DataFrame,
    group_column: str,
    min_group_size: int = 10,
    max_imbalance_ratio: float = 100.0,
) -> dict:
    """Check that groups are not extremely imbalanced.

    Computes the ratio of the largest group to the smallest group and
    flags when any group is below ``min_group_size`` or the imbalance
    ratio exceeds ``max_imbalance_ratio``.

    Args:
        df: DataFrame containing the grouping column.
        group_column: Column defining the groups.
        min_group_size: Minimum acceptable size per group (default 10).
        max_imbalance_ratio: Maximum allowed ratio of largest to smallest
            group (default 100.0).

    Returns:
        dict with keys:
            ok (bool),
            group_sizes (dict mapping group name -> count),
            imbalance_ratio (float).
    """
    try:
        if df is None or len(df) == 0:
            return {"ok": True, "group_sizes": {}, "imbalance_ratio": 0.0}

        counts = df[group_column].value_counts()
        group_sizes = {str(k): int(v) for k, v in counts.items()}

        if len(counts) == 0:
            return {"ok": True, "group_sizes": group_sizes, "imbalance_ratio": 0.0}

        max_size = int(counts.max())
        min_size = int(counts.min())

        if min_size == 0:
            imbalance_ratio = float("inf")
        else:
            imbalance_ratio = float(max_size) / float(min_size)

        too_small = any(v < min_group_size for v in counts.values)
        too_imbalanced = imbalance_ratio > max_imbalance_ratio

        return {
            "ok": not too_small and not too_imbalanced,
            "group_sizes": group_sizes,
            "imbalance_ratio": round(imbalance_ratio, 4),
        }
    except Exception:
        return {"ok": False, "group_sizes": {}, "imbalance_ratio": 0.0}


# ---------------------------------------------------------------------------
# 7. No future dates
# ---------------------------------------------------------------------------

def validate_no_future_dates(
    df: pd.DataFrame,
    date_column: str,
    reference_date: Optional[Union[str, datetime, pd.Timestamp]] = None,
) -> dict:
    """Check for dates that are in the future.

    Args:
        df: DataFrame containing a date/datetime column.
        date_column: Column name with date values.
        reference_date: The "now" to compare against.  Defaults to
            ``pd.Timestamp.now()``.

    Returns:
        dict with keys:
            ok (bool),
            future_count (int),
            max_date (str or None).
    """
    try:
        if df is None or len(df) == 0:
            return {"ok": True, "future_count": 0, "max_date": None}

        dates = pd.to_datetime(df[date_column], errors="coerce")
        ref = pd.Timestamp(reference_date) if reference_date is not None else pd.Timestamp.now()

        future_mask = dates > ref
        future_count = int(future_mask.sum())
        max_date = str(dates.max()) if dates.notna().any() else None

        return {
            "ok": future_count == 0,
            "future_count": future_count,
            "max_date": max_date,
        }
    except Exception:
        return {"ok": False, "future_count": 0, "max_date": None}


# ---------------------------------------------------------------------------
# 8. Orchestrator
# ---------------------------------------------------------------------------

def run_logical_checks(
    detail_df: Optional[pd.DataFrame] = None,
    summary_df: Optional[pd.DataFrame] = None,
    config: Optional[dict] = None,
) -> dict:
    """Orchestrate a set of logical validation checks.

    Runs whichever checks are applicable given the inputs and config.
    ``config`` may contain keys such as:

    - ``metric_column`` (str): column to aggregate
    - ``group_column`` (str | None): optional grouping column
    - ``tolerance`` (float): aggregation tolerance
    - ``pct_column`` (str): percentage column for sum check
    - ``monotonic_column`` (str): column for monotonicity check
    - ``monotonic_direction`` (str): 'increasing' or 'decreasing'
    - ``trend_values`` (list): values for trend consistency
    - ``trend_window`` (int): rolling window size
    - ``trend_max_zscore`` (float): z-score threshold
    - ``numerator_col`` (str): ratio numerator column
    - ``denominator_col`` (str): ratio denominator column
    - ``date_column`` (str): date column for future-date check
    - ``balance_column`` (str): column for group balance check

    Args:
        detail_df: Optional detail-level DataFrame.
        summary_df: Optional summary-level DataFrame.
        config: Optional configuration dict.

    Returns:
        dict with keys:
            ok (bool) — True when all executed checks passed,
            checks_run (int),
            checks_passed (int),
            results (dict mapping check name -> individual result dict).
    """
    cfg = config or {}
    results: Dict[str, Any] = {}

    # --- Aggregation consistency ---
    metric_col = cfg.get("metric_column")
    if detail_df is not None and summary_df is not None and metric_col:
        results["aggregation_consistency"] = validate_aggregation_consistency(
            detail_df,
            summary_df,
            metric_column=metric_col,
            group_column=cfg.get("group_column"),
            tolerance=cfg.get("tolerance", 0.01),
        )

    # --- Percentages sum ---
    pct_col = cfg.get("pct_column")
    working_df = detail_df if detail_df is not None else summary_df
    if working_df is not None and pct_col and pct_col in working_df.columns:
        results["percentages_sum"] = validate_percentages_sum(
            working_df,
            pct_column=pct_col,
            group_column=cfg.get("group_column"),
        )

    # --- Monotonic ---
    mono_col = cfg.get("monotonic_column")
    if working_df is not None and mono_col and mono_col in working_df.columns:
        results["monotonic"] = validate_monotonic(
            working_df,
            column=mono_col,
            direction=cfg.get("monotonic_direction", "increasing"),
        )

    # --- Trend consistency ---
    trend_vals = cfg.get("trend_values")
    if trend_vals is not None:
        results["trend_consistency"] = validate_trend_consistency(
            trend_vals,
            window=cfg.get("trend_window", 3),
            max_zscore=cfg.get("trend_max_zscore", 3.0),
        )

    # --- Ratio bounds ---
    num_col = cfg.get("numerator_col")
    den_col = cfg.get("denominator_col")
    if working_df is not None and num_col and den_col:
        if num_col in working_df.columns and den_col in working_df.columns:
            results["ratio_bounds"] = validate_ratio_bounds(
                working_df,
                numerator_col=num_col,
                denominator_col=den_col,
                min_ratio=cfg.get("min_ratio", 0.0),
                max_ratio=cfg.get("max_ratio", 1.0),
            )

    # --- Group balance ---
    bal_col = cfg.get("balance_column")
    if working_df is not None and bal_col and bal_col in working_df.columns:
        results["group_balance"] = validate_group_balance(
            working_df,
            group_column=bal_col,
            min_group_size=cfg.get("min_group_size", 10),
            max_imbalance_ratio=cfg.get("max_imbalance_ratio", 100.0),
        )

    # --- No future dates ---
    date_col = cfg.get("date_column")
    if working_df is not None and date_col and date_col in working_df.columns:
        results["no_future_dates"] = validate_no_future_dates(
            working_df,
            date_column=date_col,
            reference_date=cfg.get("reference_date"),
        )

    checks_run = len(results)
    checks_passed = sum(1 for r in results.values() if r.get("ok", False))

    return {
        "ok": checks_run > 0 and checks_passed == checks_run,
        "checks_run": checks_run,
        "checks_passed": checks_passed,
        "results": results,
    }


# ===================================================================
# LEGACY API — preserved for backward compatibility with
# confidence_scoring.py, validation_e2e, and agent templates.
# These functions use the severity-based return format.
# ===================================================================

# Explicit alias so callers can import the legacy name directly.
validate_aggregation_consistency_legacy = _aggregation_consistency_legacy


# ---------------------------------------------------------------------------
# Trend continuity (legacy)
# ---------------------------------------------------------------------------

def validate_trend_continuity(series, max_gap_pct=0.5):
    """Check for sudden jumps in a numeric series (legacy API).

    Returns:
        dict with keys: valid, breaks, severity.
    """
    s = pd.Series(series).dropna()

    if len(s) < 2:
        return {"valid": True, "breaks": [], "severity": "PASS"}

    breaks = []
    values = s.values
    indices = s.index.tolist()

    for i in range(1, len(values)):
        prev_val = float(values[i - 1])
        curr_val = float(values[i])

        if prev_val == 0:
            if curr_val != 0:
                breaks.append({
                    "index": indices[i],
                    "prev_value": prev_val,
                    "curr_value": curr_val,
                    "change_pct": float("inf"),
                })
            continue

        change_pct = abs(curr_val - prev_val) / abs(prev_val)
        if change_pct > max_gap_pct:
            breaks.append({
                "index": indices[i],
                "prev_value": prev_val,
                "curr_value": curr_val,
                "change_pct": round(change_pct, 6),
            })

    if len(breaks) == 0:
        severity = "PASS"
    elif len(breaks) <= 2:
        severity = "WARNING"
    else:
        severity = "BLOCKER"

    return {"valid": severity == "PASS", "breaks": breaks, "severity": severity}


# ---------------------------------------------------------------------------
# Segment exhaustiveness (legacy)
# ---------------------------------------------------------------------------

def validate_segment_exhaustiveness(df, segment_col, metric_col):
    """Verify segments are mutually exclusive and collectively exhaustive (legacy API).

    Returns:
        dict with keys: valid, segment_sum, total, diff_pct, missing_rows, severity.
    """
    if len(df) == 0:
        return {
            "valid": True, "segment_sum": 0.0, "total": 0.0,
            "diff_pct": 0.0, "missing_rows": 0, "severity": "PASS",
        }

    total = float(df[metric_col].sum())
    segment_sum = float(df.groupby(segment_col)[metric_col].sum().sum())

    denominator = abs(total) if total != 0 else abs(segment_sum)
    if denominator == 0:
        diff_pct = 0.0
    else:
        diff_pct = abs(segment_sum - total) / denominator

    null_segment_mask = df[segment_col].isna()
    missing_rows = int(null_segment_mask.sum())

    tolerance = 0.001
    if diff_pct > 0.01 or missing_rows > 0:
        severity = "BLOCKER"
    elif diff_pct > tolerance:
        severity = "WARNING"
    else:
        severity = "PASS"

    return {
        "valid": severity == "PASS",
        "segment_sum": round(segment_sum, 6),
        "total": round(total, 6),
        "diff_pct": round(diff_pct, 6),
        "missing_rows": missing_rows,
        "severity": severity,
    }


# ---------------------------------------------------------------------------
# Temporal consistency (legacy)
# ---------------------------------------------------------------------------

def validate_temporal_consistency(df, date_col, metric_col, expected_freq="D"):
    """Check for missing dates, duplicate dates, and zero-value gaps (legacy API).

    Returns:
        dict with keys: valid, missing_dates, duplicate_dates, zero_dates, severity.
    """
    if len(df) == 0:
        return {
            "valid": True, "missing_dates": [], "duplicate_dates": [],
            "zero_dates": [], "severity": "PASS",
        }

    dates = pd.to_datetime(df[date_col])

    date_counts = dates.value_counts()
    duplicate_dates = sorted(
        str(d.date()) if hasattr(d, "date") else str(d)
        for d in date_counts[date_counts > 1].index
    )

    min_date = dates.min()
    max_date = dates.max()

    if min_date == max_date:
        return {
            "valid": len(duplicate_dates) == 0,
            "missing_dates": [],
            "duplicate_dates": duplicate_dates,
            "zero_dates": [],
            "severity": "WARNING" if duplicate_dates else "PASS",
        }

    expected_range = pd.date_range(start=min_date, end=max_date, freq=expected_freq)
    actual_dates = set(dates.dt.normalize())
    expected_dates = set(expected_range.normalize())
    missing = sorted(expected_dates - actual_dates)
    missing_dates = [str(d.date()) for d in missing]

    working = df.copy()
    working["_parsed_date"] = dates
    working = working.sort_values("_parsed_date")

    inner = working.iloc[1:-1] if len(working) > 2 else pd.DataFrame()
    zero_dates = []
    if len(inner) > 0:
        zero_mask = inner[metric_col].isna() | (inner[metric_col] == 0)
        zero_dates = sorted(
            str(d.date()) if hasattr(d, "date") else str(d)
            for d in inner.loc[zero_mask, "_parsed_date"]
        )

    n_issues = len(missing_dates) + len(duplicate_dates) + len(zero_dates)
    total_expected = len(expected_range)
    issue_rate = n_issues / total_expected if total_expected > 0 else 0.0

    if len(duplicate_dates) > 0 or issue_rate > 0.1:
        severity = "BLOCKER"
    elif n_issues > 0:
        severity = "WARNING"
    else:
        severity = "PASS"

    return {
        "valid": severity == "PASS",
        "missing_dates": missing_dates,
        "duplicate_dates": duplicate_dates,
        "zero_dates": zero_dates,
        "severity": severity,
    }
