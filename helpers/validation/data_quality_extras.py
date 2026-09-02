"""Data quality utilities — source-agnostic DataFrame checks.

These functions operate on pandas DataFrames and are not tied to any
particular comparison paradigm. Use them directly (e.g. for null-concentration
and outlier checks); for cross-source verification see `cross_verification.py`.

Usage:
    from helpers.validation.data_quality_extras import (
        check_null_concentration,
        check_outliers,
        safe_check_outliers,
        sanity_check,
        anomaly_scan,
        freshness_check,
    )
"""

import math
from datetime import date, datetime

import numpy as np
import pandas as pd


def check_null_concentration(df, warn_threshold=0.05, fail_threshold=0.5):
    """Flag columns with high null concentrations.

    Severity follows the canonical null-severity table shared with
    ``structural_validator.validate_completeness``:

    - ``< 5%`` nulls: PASS
    - ``5-20%`` nulls: WARNING
    - ``> 20-50%`` nulls: SEVERE WARNING
    - ``> 50%`` nulls: BLOCKER

    ``status`` stays the coarse PASS/WARN/FAIL gate for existing callers
    (FAIL = BLOCKER band, WARN = either warning band); ``severity`` carries
    the canonical label.

    Args:
        df: pandas.DataFrame to check.
        warn_threshold: Fraction of nulls at or above which a column enters
            the WARNING band (default 0.05, the canonical table's edge).
        fail_threshold: Fraction of nulls above which a column is a
            BLOCKER/FAIL (default 0.5, the canonical table's edge).

    Returns:
        list of dicts with keys: column, null_count, null_pct, status,
        severity, detail
    """
    results = []
    n = len(df)
    if n == 0:
        return results

    for col in df.columns:
        null_count = int(df[col].isna().sum())
        null_pct = null_count / n

        if null_pct > fail_threshold:
            status, severity = "FAIL", "BLOCKER"
            detail = f"{null_pct:.1%} null — over half the values are missing"
        elif null_pct > 0.2:
            status, severity = "WARN", "SEVERE WARNING"
            detail = f"{null_pct:.1%} null: heavy null concentration"
        elif null_pct >= warn_threshold:
            status, severity = "WARN", "WARNING"
            detail = f"{null_pct:.1%} null: elevated null rate"
        else:
            status, severity = "PASS", "PASS"
            detail = f"{null_pct:.1%} null"

        results.append({
            "column": col,
            "null_count": null_count,
            "null_pct": round(null_pct, 4),
            "status": status,
            "severity": severity,
            "detail": detail,
        })

    return results


def check_outliers(series, method="iqr", iqr_multiplier=1.5, z_threshold=3.0):
    """Detect outliers in a numeric series using IQR or z-score method.

    Args:
        series: pandas.Series of numeric values.
        method: ``"iqr"`` (interquartile range) or ``"zscore"``.
        iqr_multiplier: Multiplier for IQR fences (default 1.5).
        z_threshold: Z-score threshold for outlier detection (default 3.0).

    Returns:
        dict with keys: method, n_outliers, n_total, outlier_pct, bounds,
        status, detail, outlier_indices
    """
    clean = series.dropna()
    n_total = len(clean)

    if n_total < 4:
        return {
            "method": method,
            "n_outliers": 0,
            "n_total": n_total,
            "outlier_pct": 0.0,
            "bounds": None,
            "status": "WARN",
            "detail": f"Too few non-null values ({n_total}) for outlier detection",
            "outlier_indices": [],
        }

    if method == "iqr":
        q1 = float(clean.quantile(0.25))
        q3 = float(clean.quantile(0.75))
        iqr = q3 - q1
        lower = q1 - iqr_multiplier * iqr
        upper = q3 + iqr_multiplier * iqr
        mask = (clean < lower) | (clean > upper)
        bounds = {"lower": round(lower, 4), "upper": round(upper, 4)}
    elif method == "zscore":
        mean = float(clean.mean())
        std = float(clean.std())
        if std == 0:
            return {
                "method": method,
                "n_outliers": 0,
                "n_total": n_total,
                "outlier_pct": 0.0,
                "bounds": None,
                "status": "PASS",
                "detail": "Zero variance — no outliers possible",
                "outlier_indices": [],
            }
        z_scores = (clean - mean) / std
        mask = z_scores.abs() > z_threshold
        bounds = {
            "lower": round(mean - z_threshold * std, 4),
            "upper": round(mean + z_threshold * std, 4),
        }
    else:
        raise ValueError(f"Unknown method: {method}. Use 'iqr' or 'zscore'.")

    outlier_indices = list(clean[mask].index)
    n_outliers = len(outlier_indices)
    outlier_pct = round(n_outliers / n_total, 4) if n_total > 0 else 0.0

    if n_outliers == 0:
        status, detail = "PASS", "No outliers detected"
    elif outlier_pct < 0.05:
        status = "PASS"
        detail = f"{n_outliers} outliers ({outlier_pct:.1%}) — within normal range"
    elif outlier_pct < 0.15:
        status = "WARN"
        detail = f"{n_outliers} outliers ({outlier_pct:.1%}) — elevated"
    else:
        status = "FAIL"
        detail = f"{n_outliers} outliers ({outlier_pct:.1%}) — unusually high"

    return {
        "method": method,
        "n_outliers": n_outliers,
        "n_total": n_total,
        "outlier_pct": outlier_pct,
        "bounds": bounds,
        "status": status,
        "detail": detail,
        "outlier_indices": outlier_indices[:20],  # cap for display
    }


def safe_check_outliers(series, method="iqr", **kwargs):
    """Student-safe wrapper around ``check_outliers()``. Never raises."""
    try:
        return check_outliers(series, method=method, **kwargs)
    except Exception as exc:
        return {
            "method": method,
            "n_outliers": 0,
            "n_total": len(series) if hasattr(series, "__len__") else 0,
            "outlier_pct": 0.0,
            "bounds": None,
            "status": "WARN",
            "detail": f"Could not check outliers: {exc}",
            "outlier_indices": [],
        }


# Columns whose values must lie in [0, 1]; used by ``sanity_check``.
BOUNDED_RATE_COLUMNS = ("conversion_rate", "percentage", "rate", "pct", "ratio")


def sanity_check(df, column, bounded_columns=BOUNDED_RATE_COLUMNS, skew_threshold=3.0):
    """Summary statistics plus domain sanity issues for one numeric column.

    Args:
        df: pandas.DataFrame.
        column: Name of the numeric column to check.
        bounded_columns: Column names (exact match) whose values must lie in
            ``[0, 1]``; values outside that range are a BLOCKER.
        skew_threshold: Absolute skew above which the column is flagged
            WARNING as highly skewed (default 3.0).

    Returns:
        ``(stats, issues)`` where ``stats`` is a dict with mean, median, std,
        min, max, p1, p99, skew (NaN-safe floats) and ``issues`` is a list of
        ``(severity, message)`` tuples. An empty or all-null column returns
        NaN stats and a single WARNING issue.
    """
    series = pd.to_numeric(df[column], errors="coerce").dropna()
    if len(series) == 0:
        stats = {k: float("nan") for k in
                 ("mean", "median", "std", "min", "max", "p1", "p99", "skew")}
        return stats, [("WARNING", f"{column} has no numeric values to check")]

    stats = {
        "mean": float(series.mean()),
        "median": float(series.median()),
        "std": float(series.std()) if len(series) > 1 else 0.0,
        "min": float(series.min()),
        "max": float(series.max()),
        "p1": float(series.quantile(0.01)),
        "p99": float(series.quantile(0.99)),
        "skew": float(series.skew()) if len(series) > 2 else 0.0,
    }

    issues = []
    if column in bounded_columns and (stats["max"] > 1 or stats["min"] < 0):
        issues.append(("BLOCKER", f"{column} has values outside [0,1] range"))
    if not math.isnan(stats["skew"]) and abs(stats["skew"]) > skew_threshold:
        issues.append(("WARNING",
                       f"{column} is highly skewed (skew={stats['skew']:.1f})"))
    return stats, issues


def anomaly_scan(df, date_col, metric_col, window=14, threshold=2.0):
    """Detect time-series anomalies using rolling mean +/- std bands.

    Aggregate to daily or weekly granularity first; this is not meant for
    raw event rows.

    Args:
        df: DataFrame with date and metric columns (pre-aggregated).
        date_col: Name of the date column.
        metric_col: Name of the metric column.
        window: Rolling window size in periods (default 14).
        threshold: Standard deviations for the anomaly band (default 2.0).

    Returns:
        dict with ``anomalies`` (list of dicts: date, value, direction, and
        pct_above_normal or pct_below_normal) and ``summary`` (str).
    """
    if len(df) == 0:
        return {"anomalies": [], "summary": f"0 anomalies in {metric_col} (no rows)"}

    ts = df.sort_values(date_col).copy()
    ts["rolling_mean"] = ts[metric_col].rolling(window, min_periods=3).mean()
    ts["rolling_std"] = ts[metric_col].rolling(window, min_periods=3).std()
    ts["upper"] = ts["rolling_mean"] + threshold * ts["rolling_std"]
    ts["lower"] = ts["rolling_mean"] - threshold * ts["rolling_std"]

    anomalies = []
    for _, row in ts.iterrows():
        mean = row["rolling_mean"]
        value = row[metric_col]
        if pd.notna(row["upper"]) and value > row["upper"]:
            pct = ((value - mean) / mean) * 100 if mean else float("inf")
            anomalies.append({
                "date": row[date_col], "value": value,
                "direction": "spike", "pct_above_normal": round(pct, 1),
            })
        elif pd.notna(row["lower"]) and value < row["lower"]:
            pct = ((mean - value) / mean) * 100 if mean else float("inf")
            anomalies.append({
                "date": row[date_col], "value": value,
                "direction": "drop", "pct_below_normal": round(pct, 1),
            })
    return {"anomalies": anomalies,
            "summary": f"{len(anomalies)} anomalies in {metric_col}"}


def freshness_check(df, date_col, current_date=None):
    """Check data freshness and infer data cadence.

    Args:
        df: DataFrame with a date column.
        date_col: Name of the date/timestamp column.
        current_date: ``datetime.date`` override (for testing). Default: today.

    Returns:
        dict with ``max_date`` (str), ``days_ago`` (int or None),
        ``cadence`` (daily / weekly / static/historical / unknown),
        ``status`` (OK / WARNING) and ``note``.
    """
    if isinstance(current_date, datetime):
        current_date = current_date.date()
    current_date = current_date or datetime.now().date()

    dates = pd.to_datetime(df[date_col], errors="coerce").dt.date.dropna()
    if len(dates) == 0:
        return {"max_date": None, "days_ago": None, "cadence": "unknown",
                "status": "WARNING", "note": f"No parseable dates in {date_col}"}

    max_date = dates.max()
    days_ago = (current_date - max_date).days

    # Infer cadence from the median gap between consecutive distinct dates.
    distinct_dates = sorted(dates.unique())
    stale_threshold = None
    if len(distinct_dates) >= 2:
        gaps = [(distinct_dates[i + 1] - distinct_dates[i]).days
                for i in range(len(distinct_dates) - 1)]
        median_gap = sorted(gaps)[len(gaps) // 2]
        if median_gap <= 1.5:
            cadence, stale_threshold = "daily", 2
        elif median_gap <= 8:
            cadence, stale_threshold = "weekly", 10
        else:
            cadence = "static/historical"
    else:
        cadence = "unknown"

    if days_ago > 90:
        cadence = "static/historical"
        status = "OK"
        note = f"Historical dataset, date range ends {max_date}"
    elif stale_threshold and days_ago > stale_threshold:
        status = "WARNING"
        note = f"Data is {days_ago} days old (expected {cadence} refresh)"
    else:
        status = "OK"
        note = f"Data is {days_ago} days old"

    return {"max_date": str(max_date), "days_ago": days_ago,
            "cadence": cadence, "status": status, "note": note}
