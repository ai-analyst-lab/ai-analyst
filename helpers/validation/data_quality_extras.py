"""Data quality utilities — source-agnostic DataFrame checks.

These functions operate on pandas DataFrames and are not tied to any
particular comparison paradigm. Use them directly (e.g. for null-concentration
and outlier checks); for cross-source verification see `cross_verification.py`.

Usage:
    from helpers.validation.data_quality_extras import (
        check_null_concentration,
        check_outliers,
        safe_check_outliers,
    )
"""

import math

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
