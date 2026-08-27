"""
Business Rules Validation Helpers (DQ-3.3 -- Plausibility).

Validates analytical results against business plausibility: value ranges,
metric relationships, temporal consistency, segment coverage, non-negativity,
cardinality, and computed rates.

Usage:
    from helpers.validation.business_rules import (
        validate_ranges, validate_metric_relationships,
        validate_temporal_consistency, validate_segment_coverage,
        validate_no_negative, validate_cardinality,
        validate_business_rules, get_default_rules,
        validate_rates, validate_yoy_change,
    )

    # Check values fall within expected ranges
    rules = [
        {"column": "conversion_rate", "min": 0, "max": 1, "label": "Conversion Rate"},
    ]
    result = validate_ranges(df, rules)
    print(result["ok"], result["violations"])

    # Check metric relationships
    metrics = {"aov": 50, "orders": 200, "revenue": 10000}
    result = validate_metric_relationships(metrics)
    print(result["ok"])
"""

from __future__ import annotations

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Range validation
# ---------------------------------------------------------------------------

def validate_ranges(df: pd.DataFrame, rules: list[dict]) -> dict:
    """Check values against business-defined min/max ranges.

    For each rule, identifies rows where the column value falls outside the
    specified [min, max] range. NaN values are skipped (not counted as
    violations).

    Args:
        df: pandas.DataFrame to validate.
        rules: List of dicts, each with keys:
            column (str) -- column name to check,
            min (numeric, optional) -- minimum allowed value (inclusive),
            max (numeric, optional) -- maximum allowed value (inclusive),
            label (str, optional) -- human-readable rule label.
            Also accepts 'name' as alias for 'label' for backward compat.

    Returns:
        dict with keys:
            ok (bool) -- True if no violations found,
            valid (bool) -- alias for ok (backward compat),
            violations (list of dicts with column, value, rule, count,
                out_of_range_pct, min_seen, max_seen, severity)
    """
    if df is None or len(df) == 0:
        return {"ok": True, "valid": True, "violations": []}

    if not rules:
        return {"ok": True, "valid": True, "violations": []}

    violations = []
    for rule in rules:
        col = rule["column"]
        label = rule.get("label", rule.get("name", col))
        rule_min = rule.get("min")
        rule_max = rule.get("max")

        # Column does not exist -- skip with a warning-level entry
        if col not in df.columns:
            violations.append({
                "column": col,
                "value": None,
                "rule": label,
                "count": 0,
                "out_of_range_pct": 0.0,
                "min_seen": None,
                "max_seen": None,
                "severity": "WARNING",
                # Backward compat fields
                "rule_name": label,
                "out_of_range_count": 0,
            })
            continue

        series = df[col].dropna()
        n = len(series)

        if n == 0:
            violations.append({
                "column": col,
                "value": None,
                "rule": label,
                "count": 0,
                "out_of_range_pct": 0.0,
                "min_seen": None,
                "max_seen": None,
                "severity": "WARNING",
                "rule_name": label,
                "out_of_range_count": 0,
            })
            continue

        # Build out-of-range mask
        mask = pd.Series(False, index=series.index)
        if rule_min is not None:
            mask = mask | (series < rule_min)
        if rule_max is not None:
            mask = mask | (series > rule_max)

        out_count = int(mask.sum())
        out_pct = float(out_count / n)
        min_seen = float(series.min())
        max_seen = float(series.max())

        # Representative violating value (first found, or None)
        if out_count > 0:
            first_bad = series[mask].iloc[0]
            value = float(first_bad)
        else:
            value = None

        # Severity
        if out_pct > 0.05:
            severity = "BLOCKER"
        elif out_count > 0:
            severity = "WARNING"
        else:
            severity = "PASS"

        violations.append({
            "column": col,
            "value": value,
            "rule": label,
            "count": out_count,
            "out_of_range_pct": round(out_pct, 6),
            "min_seen": min_seen,
            "max_seen": max_seen,
            "severity": severity,
            # Backward compat
            "rule_name": label,
            "out_of_range_count": out_count,
        })

    any_fail = any(v["count"] > 0 for v in violations)
    any_warning = any(v["severity"] == "WARNING" and v["count"] == 0
                      for v in violations)
    ok = not any_fail and not any_warning

    return {"ok": ok, "valid": ok, "violations": violations}


# ---------------------------------------------------------------------------
# Metric relationship validation
# ---------------------------------------------------------------------------

def validate_metric_relationships(
    metrics_dict: dict,
    rules: list[dict] | None = None,
) -> dict:
    """Check relationships between metrics.

    Evaluates arithmetic expressions involving metric names and compares
    left-side to right-side values. E.g., AOV * orders should equal revenue.

    Args:
        metrics_dict: Dict mapping metric names to their numeric values.
            E.g., {"aov": 50, "orders": 200, "revenue": 10000}.
        rules: Optional list of relationship rules. Each dict has:
            left (str) -- expression using metric names and operators,
            right (str) -- expression or metric name for expected value,
            tolerance (float) -- relative tolerance (default 0.05).
            If None, uses common defaults (aov * orders ~ revenue).

    Returns:
        dict with keys:
            ok (bool), violations (list of dicts with left_expr, right_expr,
                left_value, right_value, diff_pct, tolerance)
    """
    if rules is None:
        rules = _default_metric_relationships()

    if not rules or not metrics_dict:
        return {"ok": True, "violations": []}

    violations = []
    for rule in rules:
        left_expr = rule["left"]
        right_expr = rule["right"]
        tolerance = rule.get("tolerance", 0.05)

        try:
            left_val = _eval_metric_expr(left_expr, metrics_dict)
            right_val = _eval_metric_expr(right_expr, metrics_dict)
        except (KeyError, TypeError, ValueError, ZeroDivisionError):
            # If a metric referenced in the expression is missing, skip
            continue

        if left_val is None or right_val is None:
            continue

        # Compute relative difference
        denom = abs(right_val) if right_val != 0 else abs(left_val)
        if denom == 0:
            diff_pct = 0.0
        else:
            diff_pct = abs(left_val - right_val) / denom

        if diff_pct > tolerance:
            violations.append({
                "left_expr": left_expr,
                "right_expr": right_expr,
                "left_value": round(left_val, 6),
                "right_value": round(right_val, 6),
                "diff_pct": round(diff_pct, 6),
                "tolerance": tolerance,
            })

    return {"ok": len(violations) == 0, "violations": violations}


def _eval_metric_expr(expr: str, metrics: dict) -> float | None:
    """Safely evaluate a simple arithmetic expression with metric names.

    Supports: +, -, *, / operators and metric name references.
    Only allows known metric names and numeric literals. No builtins.
    """
    # Replace metric names with their values
    # Sort by length descending to avoid partial replacements
    safe_expr = expr.strip()
    sorted_names = sorted(metrics.keys(), key=len, reverse=True)
    for name in sorted_names:
        val = metrics[name]
        if val is None or (isinstance(val, float) and np.isnan(val)):
            return None
        safe_expr = safe_expr.replace(name, str(float(val)))

    # Validate: only digits, dots, spaces, and operators allowed
    allowed = set("0123456789.+-*/ ()")
    if not all(c in allowed for c in safe_expr):
        return None

    try:
        result = eval(safe_expr, {"__builtins__": {}}, {})  # noqa: S307
        return float(result)
    except Exception:
        return None


def _default_metric_relationships() -> list[dict]:
    """Return common metric relationship rules."""
    return [
        {"left": "aov * orders", "right": "revenue", "tolerance": 0.05},
    ]


# ---------------------------------------------------------------------------
# Temporal consistency (period-over-period)
# ---------------------------------------------------------------------------

def validate_temporal_consistency(
    df: pd.DataFrame,
    date_column: str,
    metric_column: str,
    max_period_change_pct: float = 200,
) -> dict:
    """Check that period-over-period changes are not implausibly large.

    Computes the percentage change between consecutive periods and flags
    any change exceeding the threshold.

    Args:
        df: pandas.DataFrame with date and metric columns.
        date_column: Column containing date/datetime values.
        metric_column: Column containing the metric to check.
        max_period_change_pct: Maximum allowed period-over-period change
            as a percentage (default 200 = 200%).

    Returns:
        dict with keys:
            ok (bool), large_changes (list of dicts with date, previous,
                current, change_pct)
    """
    if df is None or len(df) < 2:
        return {"ok": True, "large_changes": []}

    if date_column not in df.columns or metric_column not in df.columns:
        return {"ok": True, "large_changes": []}

    working = df[[date_column, metric_column]].dropna().copy()
    if len(working) < 2:
        return {"ok": True, "large_changes": []}

    working = working.sort_values(date_column).reset_index(drop=True)

    large_changes = []
    values = working[metric_column].values
    dates = working[date_column].values

    for i in range(1, len(values)):
        prev = float(values[i - 1])
        curr = float(values[i])

        # Skip if previous is zero (infinite change)
        if prev == 0:
            if curr != 0:
                large_changes.append({
                    "date": _format_date(dates[i]),
                    "previous": prev,
                    "current": curr,
                    "change_pct": float("inf"),
                })
            continue

        change_pct = abs((curr - prev) / prev) * 100
        if change_pct > max_period_change_pct:
            large_changes.append({
                "date": _format_date(dates[i]),
                "previous": round(prev, 6),
                "current": round(curr, 6),
                "change_pct": round(change_pct, 2),
            })

    return {"ok": len(large_changes) == 0, "large_changes": large_changes}


def _format_date(val) -> str:
    """Convert a date-like value to string."""
    if hasattr(val, "isoformat"):
        return val.isoformat()
    if isinstance(val, np.datetime64):
        ts = pd.Timestamp(val)
        return ts.isoformat()
    return str(val)


# ---------------------------------------------------------------------------
# Segment coverage
# ---------------------------------------------------------------------------

def validate_segment_coverage(
    df: pd.DataFrame,
    segment_column: str,
    expected_segments: list[str] | None = None,
    allow_other: bool = True,
) -> dict:
    """Check that expected segments are present in the data.

    Args:
        df: pandas.DataFrame to validate.
        segment_column: Column containing segment values.
        expected_segments: List of segment values expected to be present.
            If None, only checks for non-empty segments.
        allow_other: If True, unexpected segments are noted but not treated
            as violations. If False, unexpected segments are violations.

    Returns:
        dict with keys:
            ok (bool), missing_segments (list), unexpected_segments (list)
    """
    if df is None or len(df) == 0:
        missing = list(expected_segments) if expected_segments else []
        return {
            "ok": len(missing) == 0,
            "missing_segments": missing,
            "unexpected_segments": [],
        }

    if segment_column not in df.columns:
        missing = list(expected_segments) if expected_segments else []
        return {
            "ok": len(missing) == 0,
            "missing_segments": missing,
            "unexpected_segments": [],
        }

    actual = set(df[segment_column].dropna().unique())

    if expected_segments is None:
        return {
            "ok": True,
            "missing_segments": [],
            "unexpected_segments": [],
        }

    expected_set = set(expected_segments)
    missing = sorted(expected_set - actual)
    unexpected = sorted(actual - expected_set)

    if allow_other:
        ok = len(missing) == 0
    else:
        ok = len(missing) == 0 and len(unexpected) == 0

    return {
        "ok": ok,
        "missing_segments": missing,
        "unexpected_segments": unexpected,
    }


# ---------------------------------------------------------------------------
# Non-negative validation
# ---------------------------------------------------------------------------

def validate_no_negative(
    df: pd.DataFrame,
    columns: list[str],
) -> dict:
    """Check that specified columns contain no negative values.

    Useful for columns like revenue, order counts, and session counts
    that should never be negative.

    Args:
        df: pandas.DataFrame to validate.
        columns: List of column names to check.

    Returns:
        dict with keys:
            ok (bool), violations (list of dicts with column, negative_count,
                min_value)
    """
    if df is None or len(df) == 0:
        return {"ok": True, "violations": []}

    if not columns:
        return {"ok": True, "violations": []}

    violations = []
    for col in columns:
        if col not in df.columns:
            continue

        series = df[col].dropna()
        if len(series) == 0:
            continue

        neg_mask = series < 0
        neg_count = int(neg_mask.sum())

        if neg_count > 0:
            min_val = float(series.min())
            violations.append({
                "column": col,
                "negative_count": neg_count,
                "min_value": min_val,
            })

    return {"ok": len(violations) == 0, "violations": violations}


# ---------------------------------------------------------------------------
# Cardinality validation
# ---------------------------------------------------------------------------

def validate_cardinality(
    df: pd.DataFrame,
    column: str,
    expected_min: int | None = None,
    expected_max: int | None = None,
) -> dict:
    """Check that distinct value count is within expected bounds.

    Useful for detecting data issues like a segment column with only 1
    unique value, or a user_id column with unreasonably high cardinality.

    Args:
        df: pandas.DataFrame to validate.
        column: Column name to check.
        expected_min: Minimum expected distinct count (inclusive).
        expected_max: Maximum expected distinct count (inclusive).

    Returns:
        dict with keys:
            ok (bool), actual_cardinality (int), message (str)
    """
    if df is None or len(df) == 0:
        return {
            "ok": True,
            "actual_cardinality": 0,
            "message": "Empty DataFrame, cardinality check skipped.",
        }

    if column not in df.columns:
        return {
            "ok": False,
            "actual_cardinality": 0,
            "message": f"Column '{column}' not found in DataFrame.",
        }

    cardinality = int(df[column].nunique())

    issues = []
    if expected_min is not None and cardinality < expected_min:
        issues.append(
            f"Cardinality {cardinality} is below expected minimum {expected_min}."
        )
    if expected_max is not None and cardinality > expected_max:
        issues.append(
            f"Cardinality {cardinality} exceeds expected maximum {expected_max}."
        )

    if issues:
        return {
            "ok": False,
            "actual_cardinality": cardinality,
            "message": " ".join(issues),
        }

    return {
        "ok": True,
        "actual_cardinality": cardinality,
        "message": f"Cardinality {cardinality} is within expected bounds.",
    }


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def validate_business_rules(
    df: pd.DataFrame,
    rules_config: dict,
) -> dict:
    """Run all applicable business rule validations.

    Orchestrates individual validation functions based on the provided
    configuration.

    Args:
        df: pandas.DataFrame to validate.
        rules_config: Dict specifying which checks to run. Supported keys:
            ranges (list of range rule dicts),
            no_negative (list of column names),
            segment_coverage (dict with segment_column, expected_segments,
                allow_other),
            temporal (dict with date_column, metric_column,
                max_period_change_pct),
            cardinality (list of dicts with column, expected_min,
                expected_max),
            metric_relationships (dict with metrics_dict, rules).

    Returns:
        dict with keys:
            ok (bool) -- True if all checks pass,
            results (dict) -- individual check results keyed by check name,
            summary (str) -- human-readable summary
    """
    results = {}
    all_ok = True

    # Range checks
    if "ranges" in rules_config:
        result = validate_ranges(df, rules_config["ranges"])
        results["ranges"] = result
        if not result["ok"]:
            all_ok = False

    # Non-negative checks
    if "no_negative" in rules_config:
        result = validate_no_negative(df, rules_config["no_negative"])
        results["no_negative"] = result
        if not result["ok"]:
            all_ok = False

    # Segment coverage
    if "segment_coverage" in rules_config:
        sc = rules_config["segment_coverage"]
        result = validate_segment_coverage(
            df,
            segment_column=sc["segment_column"],
            expected_segments=sc.get("expected_segments"),
            allow_other=sc.get("allow_other", True),
        )
        results["segment_coverage"] = result
        if not result["ok"]:
            all_ok = False

    # Temporal consistency
    if "temporal" in rules_config:
        tc = rules_config["temporal"]
        result = validate_temporal_consistency(
            df,
            date_column=tc["date_column"],
            metric_column=tc["metric_column"],
            max_period_change_pct=tc.get("max_period_change_pct", 200),
        )
        results["temporal"] = result
        if not result["ok"]:
            all_ok = False

    # Cardinality checks
    if "cardinality" in rules_config:
        for card_rule in rules_config["cardinality"]:
            col = card_rule["column"]
            result = validate_cardinality(
                df, col,
                expected_min=card_rule.get("expected_min"),
                expected_max=card_rule.get("expected_max"),
            )
            results[f"cardinality_{col}"] = result
            if not result["ok"]:
                all_ok = False

    # Metric relationships
    if "metric_relationships" in rules_config:
        mr = rules_config["metric_relationships"]
        result = validate_metric_relationships(
            mr.get("metrics_dict", {}),
            rules=mr.get("rules"),
        )
        results["metric_relationships"] = result
        if not result["ok"]:
            all_ok = False

    # Summary
    failed = [k for k, v in results.items() if not v.get("ok", True)]
    if failed:
        summary = f"Business rules: {len(failed)} check(s) failed -- {', '.join(failed)}."
    else:
        summary = f"Business rules: all {len(results)} check(s) passed."

    return {"ok": all_ok, "results": results, "summary": summary}


# ---------------------------------------------------------------------------
# Default rules
# ---------------------------------------------------------------------------

def get_default_rules() -> dict:
    """Return common-sense default rules for typical product analytics.

    Returns a rules_config dict suitable for passing to
    validate_business_rules().

    Returns:
        dict with keys: ranges, no_negative, segment_coverage, cardinality.
    """
    return {
        "ranges": [
            {"column": "conversion_rate", "min": 0, "max": 1,
             "label": "Conversion Rate"},
            {"column": "bounce_rate", "min": 0, "max": 1,
             "label": "Bounce Rate"},
            {"column": "click_through_rate", "min": 0, "max": 1,
             "label": "Click-Through Rate"},
            {"column": "retention_rate", "min": 0, "max": 1,
             "label": "Retention Rate"},
            {"column": "churn_rate", "min": 0, "max": 1,
             "label": "Churn Rate"},
            {"column": "nps_score", "min": -100, "max": 100,
             "label": "NPS Score"},
        ],
        "no_negative": [
            "revenue", "orders", "sessions", "users",
            "page_views", "transactions", "quantity",
        ],
        "cardinality": [
            {"column": "device", "expected_min": 2, "expected_max": 10},
            {"column": "country", "expected_min": 1, "expected_max": 300},
        ],
    }


# ---------------------------------------------------------------------------
# Rate validation (preserved from v1 for backward compatibility)
# ---------------------------------------------------------------------------

def validate_rates(df, numerator_col, denominator_col, expected_range=(0, 1),
                   name="rate"):
    """Validate a computed rate (numerator / denominator).

    Checks that the rate falls within the expected range, and flags
    zero-denominator cases.

    Args:
        df: pandas.DataFrame containing numerator and denominator columns.
        numerator_col: Column name for the numerator.
        denominator_col: Column name for the denominator.
        expected_range: Tuple (min, max) for the expected rate range.
            Default is (0, 1) for typical conversion rates.
        name: Human-readable name for the rate (default 'rate').

    Returns:
        dict with keys:
            valid (bool), out_of_range_count (int),
            zero_denominator_count (int),
            rate_stats (dict with mean/median/min/max),
            severity ('PASS'|'WARNING'|'BLOCKER')
    """
    if len(df) == 0:
        return {
            "valid": True,
            "out_of_range_count": 0,
            "zero_denominator_count": 0,
            "rate_stats": {"mean": None, "median": None,
                           "min": None, "max": None},
            "severity": "PASS",
        }

    denom = df[denominator_col]
    zero_denom_mask = (denom == 0) | denom.isna()
    zero_denominator_count = int(zero_denom_mask.sum())

    valid_mask = ~zero_denom_mask
    if valid_mask.sum() == 0:
        return {
            "valid": False,
            "out_of_range_count": 0,
            "zero_denominator_count": zero_denominator_count,
            "rate_stats": {"mean": None, "median": None,
                           "min": None, "max": None},
            "severity": "BLOCKER",
        }

    rates = df.loc[valid_mask, numerator_col] / df.loc[valid_mask, denominator_col]
    rates = rates.dropna()

    range_min, range_max = expected_range
    out_of_range_mask = (rates < range_min) | (rates > range_max)
    out_of_range_count = int(out_of_range_mask.sum())

    rate_stats = {
        "mean": round(float(rates.mean()), 6),
        "median": round(float(rates.median()), 6),
        "min": round(float(rates.min()), 6),
        "max": round(float(rates.max()), 6),
    }

    out_of_range_pct = (
        out_of_range_count / len(rates) if len(rates) > 0 else 0.0
    )
    if zero_denominator_count > 0 and out_of_range_pct > 0.05:
        severity = "BLOCKER"
    elif out_of_range_count > 0 or zero_denominator_count > 0:
        severity = "WARNING"
    else:
        severity = "PASS"

    valid = severity == "PASS"

    return {
        "valid": valid,
        "out_of_range_count": out_of_range_count,
        "zero_denominator_count": zero_denominator_count,
        "rate_stats": rate_stats,
        "severity": severity,
    }


# ---------------------------------------------------------------------------
# Year-over-year change validation (preserved from v1)
# ---------------------------------------------------------------------------

def validate_yoy_change(current_value, prior_value, max_change_pct=2.0,
                        metric_name="metric"):
    """Flag implausible year-over-year changes.

    Computes the relative change and flags it if the absolute change
    exceeds max_change_pct (as a fraction, e.g. 2.0 = 200%).

    Args:
        current_value: Current period value (numeric).
        prior_value: Prior period value (numeric).
        max_change_pct: Maximum allowed relative change as a fraction
            (default 2.0 = 200%).
        metric_name: Human-readable name for the metric (default 'metric').

    Returns:
        dict with keys:
            valid (bool), change_pct (float), direction ('up'|'down'|'flat'),
            severity ('PASS'|'WARNING'|'BLOCKER'), interpretation (str)
    """
    if current_value is None or prior_value is None:
        return {
            "valid": False,
            "change_pct": None,
            "direction": "flat",
            "severity": "WARNING",
            "interpretation": (
                f"Cannot compute YoY change for {metric_name} "
                f"-- missing value(s)."
            ),
        }

    current_value = float(current_value)
    prior_value = float(prior_value)

    if np.isnan(current_value) or np.isnan(prior_value):
        return {
            "valid": False,
            "change_pct": None,
            "direction": "flat",
            "severity": "WARNING",
            "interpretation": (
                f"Cannot compute YoY change for {metric_name} "
                f"-- NaN value(s)."
            ),
        }

    if prior_value == 0:
        if current_value == 0:
            return {
                "valid": True,
                "change_pct": 0.0,
                "direction": "flat",
                "severity": "PASS",
                "interpretation": (
                    f"{metric_name}: no change (both periods are zero)."
                ),
            }
        return {
            "valid": False,
            "change_pct": float("inf"),
            "direction": "up" if current_value > 0 else "down",
            "severity": "BLOCKER",
            "interpretation": (
                f"{metric_name}: prior value is zero, current is "
                f"{current_value:,.2f} -- infinite change. Verify data."
            ),
        }

    change = (current_value - prior_value) / abs(prior_value)
    change_pct = round(abs(change), 6)

    if change > 0:
        direction = "up"
    elif change < 0:
        direction = "down"
    else:
        direction = "flat"

    if change_pct > max_change_pct:
        severity = "BLOCKER"
        interpretation = (
            f"{metric_name}: {direction} {change_pct:.1%} YoY "
            f"({prior_value:,.2f} -> {current_value:,.2f}). "
            f"Exceeds {max_change_pct:.0%} threshold -- verify this is real."
        )
    elif change_pct > max_change_pct * 0.5:
        severity = "WARNING"
        interpretation = (
            f"{metric_name}: {direction} {change_pct:.1%} YoY "
            f"({prior_value:,.2f} -> {current_value:,.2f}). "
            f"Large change -- worth investigating."
        )
    else:
        severity = "PASS"
        interpretation = (
            f"{metric_name}: {direction} {change_pct:.1%} YoY "
            f"({prior_value:,.2f} -> {current_value:,.2f}). "
            f"Within expected range."
        )

    valid = severity == "PASS"

    return {
        "valid": valid,
        "change_pct": change_pct,
        "direction": direction,
        "severity": severity,
        "interpretation": interpretation,
    }
