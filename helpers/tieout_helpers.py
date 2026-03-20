"""
Source Tie-Out Helpers — dual-path data integrity verification.

Reads source files via pandas and compares foundational metrics against
SQL-loaded versions to catch data loading errors before analysis begins.

Usage:
    from helpers.tieout_helpers import (
        read_source_direct, profile_dataframe, compare_profiles,
        format_tieout_table, overall_status,
    )

    source_df = read_source_direct("data/sales.csv")
    source_profile = profile_dataframe(source_df)
    sql_profile = profile_dataframe(sql_df)
    results = compare_profiles(source_profile, sql_profile)
    print(format_tieout_table(results))
    print(overall_status(results))
"""

import math
from pathlib import Path

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Read source files directly via pandas (no DuckDB)
# ---------------------------------------------------------------------------

def read_source_direct(path, dtype=None):
    """Read a data file via pandas only — no DuckDB in the code path.

    Supports CSV, Excel (.xlsx/.xls), Parquet, and JSON.

    Args:
        path: File path (str or Path).
        dtype: Optional dict of column name -> dtype for CSV files.
            Passed through to pd.read_csv(dtype=...) to avoid pandas
            type coercion mismatches (e.g., forcing an ID column to str
            instead of int64). Ignored for non-CSV formats.

    Returns:
        pandas.DataFrame

    Raises:
        ValueError: If the file extension is not supported.
        FileNotFoundError: If the file does not exist.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Source file not found: {path}")

    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path, dtype=dtype)
    elif suffix in (".xlsx", ".xls"):
        return pd.read_excel(path)
    elif suffix == ".parquet":
        return pd.read_parquet(path)
    elif suffix == ".json":
        return pd.read_json(path)
    else:
        raise ValueError(f"Unsupported file type: {suffix}")


# ---------------------------------------------------------------------------
# Profile a DataFrame
# ---------------------------------------------------------------------------

def profile_dataframe(df, label="source"):
    """Compute foundational metrics for a DataFrame.

    Args:
        df: pandas.DataFrame to profile.
        label: Human-readable label for this profile (e.g., "source", "duckdb").

    Returns:
        dict with keys:
            label, row_count, columns, null_counts, numeric_sums,
            distinct_counts, date_ranges
        If the DataFrame is empty (zero rows), the profile includes a
        ``"warning": "EMPTY_DATAFRAME"`` flag with zeroed-out metrics.
    """
    profile = {
        "label": label,
        "row_count": len(df),
        "columns": sorted(df.columns.tolist()),
        "null_counts": {},
        "numeric_sums": {},
        "distinct_counts": {},
        "date_ranges": {},
    }

    # Early exit for empty DataFrames — zeroed-out metrics + warning flag
    if len(df) == 0:
        for col in df.columns:
            profile["null_counts"][col] = 0
            profile["distinct_counts"][col] = 0
            if pd.api.types.is_numeric_dtype(df[col]):
                profile["numeric_sums"][col] = 0.0
        profile["warning"] = "EMPTY_DATAFRAME"
        return profile

    for col in df.columns:
        profile["null_counts"][col] = int(df[col].isna().sum())
        profile["distinct_counts"][col] = int(df[col].nunique())

        if pd.api.types.is_numeric_dtype(df[col]):
            profile["numeric_sums"][col] = float(df[col].sum())

        if pd.api.types.is_datetime64_any_dtype(df[col]):
            non_null = df[col].dropna()
            if len(non_null) > 0:
                profile["date_ranges"][col] = {
                    "min": str(non_null.min()),
                    "max": str(non_null.max()),
                }

    return profile


# ---------------------------------------------------------------------------
# Compare two profiles
# ---------------------------------------------------------------------------

_ROW_TOL = 0            # Row counts must match exactly
_NUMERIC_TOL = 0.0001   # 0.01% tolerance for numeric sums
_CLAIM_TOL = 0.001      # 0.1% tolerance for claim-level checks
_ABS_FLOOR = 0.01       # Absolute tolerance floor for near-zero values


def compare_profiles(source_profile, duckdb_profile):
    """Compare two profiles and return a list of check results.

    Handles empty-DataFrame warnings, asymmetric numeric columns
    (different type inference between pandas and DuckDB), and flexible
    date-string parsing for date-range comparisons.

    Args:
        source_profile: dict from profile_dataframe() for the pandas read.
        duckdb_profile: dict from profile_dataframe() for the DuckDB read.

    Returns:
        list of dicts, each with keys:
            check, metric, source_value, duckdb_value, status, detail
    """
    results = []
    src = source_profile
    db = duckdb_profile

    # --- Empty DataFrame guard ---
    src_empty = src.get("warning") == "EMPTY_DATAFRAME"
    db_empty = db.get("warning") == "EMPTY_DATAFRAME"
    if src_empty or db_empty:
        empty_labels = []
        if src_empty:
            empty_labels.append(src["label"])
        if db_empty:
            empty_labels.append(db["label"])
        results.append({
            "check": "Empty DataFrame",
            "metric": "row_count",
            "source_value": src["row_count"],
            "duckdb_value": db["row_count"],
            "status": "WARN",
            "detail": f"Empty DataFrame detected in: {', '.join(empty_labels)}",
        })

    # --- Tier 1: Structural integrity ---

    # Row count
    results.append(_compare_exact(
        "Row count", "rows",
        src["row_count"], db["row_count"],
    ))

    # Column names
    missing_in_db = set(src["columns"]) - set(db["columns"])
    missing_in_src = set(db["columns"]) - set(src["columns"])
    if not missing_in_db and not missing_in_src:
        results.append({
            "check": "Column names",
            "metric": "columns",
            "source_value": len(src["columns"]),
            "duckdb_value": len(db["columns"]),
            "status": "PASS",
            "detail": "All columns match",
        })
    else:
        detail_parts = []
        if missing_in_db:
            detail_parts.append(f"In source but not DuckDB: {sorted(missing_in_db)}")
        if missing_in_src:
            detail_parts.append(f"In DuckDB but not source: {sorted(missing_in_src)}")
        results.append({
            "check": "Column names",
            "metric": "columns",
            "source_value": len(src["columns"]),
            "duckdb_value": len(db["columns"]),
            "status": "FAIL",
            "detail": "; ".join(detail_parts),
        })

    # Null counts per column
    common_cols = set(src["columns"]) & set(db["columns"])
    for col in sorted(common_cols):
        src_nulls = src["null_counts"].get(col, 0)
        db_nulls = db["null_counts"].get(col, 0)
        results.append(_compare_exact(
            "Null count", col, src_nulls, db_nulls,
        ))

    # --- Tier 2: Aggregation integrity ---

    # Numeric sums — common columns
    common_numeric = set(src["numeric_sums"].keys()) & set(db["numeric_sums"].keys())
    for col in sorted(common_numeric):
        src_sum = src["numeric_sums"][col]
        db_sum = db["numeric_sums"][col]
        results.append(_compare_within_tolerance(
            "Numeric sum", col, src_sum, db_sum, _NUMERIC_TOL,
        ))

    # Asymmetric numeric columns — present in one profile but not the other
    # (common when pandas and DuckDB infer different dtypes for the same column)
    src_only_numeric = set(src["numeric_sums"].keys()) - set(db["numeric_sums"].keys())
    db_only_numeric = set(db["numeric_sums"].keys()) - set(src["numeric_sums"].keys())
    for col in sorted(src_only_numeric):
        results.append({
            "check": "Numeric sum",
            "metric": col,
            "source_value": src["numeric_sums"][col],
            "duckdb_value": "N/A (non-numeric)",
            "status": "WARN",
            "detail": f"Column '{col}' is numeric in source but not in DuckDB — possible type inference mismatch",
        })
    for col in sorted(db_only_numeric):
        results.append({
            "check": "Numeric sum",
            "metric": col,
            "source_value": "N/A (non-numeric)",
            "duckdb_value": db["numeric_sums"][col],
            "status": "WARN",
            "detail": f"Column '{col}' is numeric in DuckDB but not in source — possible type inference mismatch",
        })

    # Distinct counts
    for col in sorted(common_cols):
        src_dc = src["distinct_counts"].get(col, 0)
        db_dc = db["distinct_counts"].get(col, 0)
        results.append(_compare_exact(
            "Distinct count", col, src_dc, db_dc,
        ))

    # Date ranges — parse to datetime.date for flexible comparison
    common_dates = set(src["date_ranges"].keys()) & set(db["date_ranges"].keys())
    for col in sorted(common_dates):
        src_min = src["date_ranges"][col]["min"]
        db_min = db["date_ranges"][col]["min"]
        src_max = src["date_ranges"][col]["max"]
        db_max = db["date_ranges"][col]["max"]

        # Normalize date strings to date objects for comparison so that
        # "2024-01-01" matches "2024-01-01 00:00:00" etc.
        try:
            src_min_dt = pd.to_datetime(src_min).date()
            db_min_dt = pd.to_datetime(db_min).date()
            src_max_dt = pd.to_datetime(src_max).date()
            db_max_dt = pd.to_datetime(db_max).date()
            min_match = src_min_dt == db_min_dt
            max_match = src_max_dt == db_max_dt
        except (ValueError, TypeError):
            # Fall back to string equality if parsing fails
            min_match = src_min == db_min
            max_match = src_max == db_max

        status = "PASS" if (min_match and max_match) else "FAIL"
        results.append({
            "check": "Date range",
            "metric": col,
            "source_value": f"{src_min} to {src_max}",
            "duckdb_value": f"{db_min} to {db_max}",
            "status": status,
            "detail": "Range matches" if status == "PASS" else "Date range mismatch",
        })

    return results


def _compare_exact(check, metric, src_val, db_val):
    """Compare two values for exact equality."""
    status = "PASS" if src_val == db_val else "FAIL"
    detail = "Match" if status == "PASS" else f"Mismatch: {src_val} vs {db_val}"
    return {
        "check": check,
        "metric": metric,
        "source_value": src_val,
        "duckdb_value": db_val,
        "status": status,
        "detail": detail,
    }


def _compare_within_tolerance(check, metric, src_val, db_val, tolerance,
                              abs_floor=_ABS_FLOOR):
    """Compare two numeric values within a relative tolerance.

    Includes NaN handling and an absolute tolerance floor for near-zero
    values to prevent false FAILs on columns like "revenue from canceled
    orders" where both values are tiny but relative difference is large.

    Args:
        check: Check name (e.g., "Numeric sum").
        metric: Column name being compared.
        src_val: Source (pandas) value.
        db_val: DuckDB value.
        tolerance: Relative tolerance threshold (e.g., 0.0001 for 0.01%).
        abs_floor: Absolute value threshold below which absolute difference
            is used instead of relative difference. Default: 0.01.

    Returns:
        dict with check, metric, source_value, duckdb_value, status, detail.
    """
    # --- NaN guard ---
    src_nan = isinstance(src_val, float) and math.isnan(src_val)
    db_nan = isinstance(db_val, float) and math.isnan(db_val)
    if src_nan and db_nan:
        return {
            "check": check, "metric": metric,
            "source_value": src_val, "duckdb_value": db_val,
            "status": "WARN", "detail": "Both values are NaN",
        }
    if src_nan or db_nan:
        nan_side = "source" if src_nan else "duckdb"
        return {
            "check": check, "metric": metric,
            "source_value": src_val, "duckdb_value": db_val,
            "status": "FAIL",
            "detail": f"NaN in {nan_side} but not the other ({src_val} vs {db_val})",
        }

    # --- Both zero shortcut ---
    if src_val == 0 and db_val == 0:
        return {
            "check": check, "metric": metric,
            "source_value": src_val, "duckdb_value": db_val,
            "status": "PASS", "detail": "Both zero",
        }

    # --- Absolute floor for near-zero values ---
    # When both values are below the absolute floor, compute a scaled
    # difference using abs_floor as the denominator instead of the actual
    # values.  This prevents false FAILs when the relative difference is
    # large but the absolute difference is negligible (e.g., 0.005 vs 0.006).
    abs_diff = abs(src_val - db_val)
    if abs(src_val) < abs_floor and abs(db_val) < abs_floor:
        scaled_diff = abs_diff / abs_floor  # treat abs_floor as denominator
        if abs_diff == 0:
            status, detail = "PASS", "Exact match"
        elif scaled_diff <= tolerance:
            status, detail = "PASS", f"Within abs floor ({abs_diff:.6g} abs diff)"
        elif scaled_diff <= tolerance * 10:
            status, detail = "WARN", f"Near abs floor ({abs_diff:.6g} abs diff)"
        else:
            status, detail = "FAIL", f"Exceeds abs floor ({abs_diff:.6g} abs diff)"
        return {
            "check": check, "metric": metric,
            "source_value": src_val, "duckdb_value": db_val,
            "status": status, "detail": detail,
        }

    # --- Standard relative comparison ---
    denominator = abs(src_val) if src_val != 0 else abs(db_val)
    diff = abs_diff / denominator

    if diff == 0:
        status, detail = "PASS", "Exact match"
    elif diff <= tolerance:
        status, detail = "PASS", f"Within tolerance ({diff:.6%} diff)"
    elif diff <= tolerance * 10:
        status, detail = "WARN", f"Near tolerance ({diff:.4%} diff)"
    else:
        status, detail = "FAIL", f"Exceeds tolerance ({diff:.4%} diff)"

    return {
        "check": check, "metric": metric,
        "source_value": src_val, "duckdb_value": db_val,
        "status": status, "detail": detail,
    }


# ---------------------------------------------------------------------------
# Formatting and roll-up
# ---------------------------------------------------------------------------

def format_tieout_table(results):
    """Render comparison results as a markdown table.

    Args:
        results: list of dicts from compare_profiles().

    Returns:
        str: Markdown table.
    """
    lines = [
        "| Check | Metric | Source | DuckDB | Status | Detail |",
        "|-------|--------|--------|--------|--------|--------|",
    ]
    for r in results:
        status_badge = {
            "PASS": "PASS",
            "WARN": "**WARN**",
            "FAIL": "**FAIL**",
        }.get(r["status"], r["status"])
        lines.append(
            f"| {r['check']} | {r['metric']} | {r['source_value']} "
            f"| {r['duckdb_value']} | {status_badge} | {r['detail']} |"
        )
    return "\n".join(lines)


def overall_status(results):
    """Roll up individual check results to a single PASS/WARN/FAIL.

    Args:
        results: list of dicts from compare_profiles().

    Returns:
        str: "PASS", "WARN", or "FAIL"
    """
    statuses = {r["status"] for r in results}
    if "FAIL" in statuses:
        return "FAIL"
    if "WARN" in statuses:
        return "WARN"
    return "PASS"


# ---------------------------------------------------------------------------
# DQ-1.1: Data quality extensions
# ---------------------------------------------------------------------------

def check_null_concentration(df, warn_threshold=0.5, fail_threshold=0.95):
    """Flag columns with high null concentrations.

    Args:
        df: pandas.DataFrame to check.
        warn_threshold: Fraction of nulls above which a column triggers WARN.
        fail_threshold: Fraction of nulls above which a column triggers FAIL.

    Returns:
        list of dicts with keys: column, null_count, null_pct, status, detail
    """
    results = []
    n = len(df)
    if n == 0:
        return results

    for col in df.columns:
        null_count = int(df[col].isna().sum())
        null_pct = null_count / n

        if null_pct >= fail_threshold:
            status = "FAIL"
            detail = f"{null_pct:.1%} null — column is effectively empty"
        elif null_pct >= warn_threshold:
            status = "WARN"
            detail = f"{null_pct:.1%} null — over half the values are missing"
        else:
            status = "PASS"
            detail = f"{null_pct:.1%} null"

        results.append({
            "column": col,
            "null_count": null_count,
            "null_pct": round(null_pct, 4),
            "status": status,
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


def validate_profile_pair(source_profile, duckdb_profile):
    """Pre-validate two profiles before detailed comparison.

    Short-circuits when one side is empty and the other is not, or when
    column sets are completely disjoint. Use before ``compare_profiles()``
    to get a quick go/no-go.

    Args:
        source_profile: dict from profile_dataframe().
        duckdb_profile: dict from profile_dataframe().

    Returns:
        dict with keys: can_compare (bool), status, issues (list of str)
    """
    issues = []

    src_empty = source_profile.get("warning") == "EMPTY_DATAFRAME"
    db_empty = duckdb_profile.get("warning") == "EMPTY_DATAFRAME"

    if src_empty and db_empty:
        issues.append("Both DataFrames are empty — nothing to compare")
        return {"can_compare": False, "status": "FAIL", "issues": issues}

    if src_empty and not db_empty:
        issues.append(
            f"Source is empty but DuckDB has {duckdb_profile['row_count']:,} rows"
        )
        return {"can_compare": False, "status": "FAIL", "issues": issues}

    if db_empty and not src_empty:
        issues.append(
            f"DuckDB is empty but source has {source_profile['row_count']:,} rows"
        )
        return {"can_compare": False, "status": "FAIL", "issues": issues}

    # Check for completely disjoint columns
    src_cols = set(source_profile["columns"])
    db_cols = set(duckdb_profile["columns"])
    overlap = src_cols & db_cols

    if len(overlap) == 0:
        issues.append(
            f"Zero column overlap — source has {sorted(src_cols)}, "
            f"DuckDB has {sorted(db_cols)}"
        )
        return {"can_compare": False, "status": "FAIL", "issues": issues}

    if len(overlap) < len(src_cols) * 0.5:
        issues.append(
            f"Low column overlap: {len(overlap)}/{len(src_cols)} "
            f"source columns found in DuckDB"
        )

    return {
        "can_compare": True,
        "status": "WARN" if issues else "PASS",
        "issues": issues,
    }


# ---------------------------------------------------------------------------
# DQ-1.4: Student-friendly safe wrappers
# ---------------------------------------------------------------------------

def safe_profile(df, label="source"):
    """Student-safe wrapper around ``profile_dataframe()``.

    Never raises. Returns a profile dict on success, or a dict with
    ``error`` and ``suggestion`` keys on failure.
    """
    try:
        return profile_dataframe(df, label=label)
    except Exception as exc:
        return {
            "label": label,
            "error": str(exc),
            "suggestion": (
                "Check that the DataFrame is valid and non-empty. "
                "Common issue: passing a file path instead of a DataFrame."
            ),
            "row_count": 0,
            "columns": [],
        }


def safe_compare(source_profile, duckdb_profile):
    """Student-safe wrapper around ``compare_profiles()``.

    Pre-validates with ``validate_profile_pair()``, then runs comparison.
    Never raises — returns error context on failure.
    """
    try:
        validation = validate_profile_pair(source_profile, duckdb_profile)
        if not validation["can_compare"]:
            return [{
                "check": "Pre-validation",
                "metric": "profile_pair",
                "source_value": source_profile.get("row_count", "?"),
                "duckdb_value": duckdb_profile.get("row_count", "?"),
                "status": "FAIL",
                "detail": "; ".join(validation["issues"]),
            }]
        return compare_profiles(source_profile, duckdb_profile)
    except Exception as exc:
        return [{
            "check": "Comparison Error",
            "metric": "system",
            "source_value": "—",
            "duckdb_value": "—",
            "status": "FAIL",
            "detail": f"Error during comparison: {exc}",
        }]


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
