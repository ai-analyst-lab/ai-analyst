"""
Structural Validation Helpers (DQ-3.1 -- Layer 1).

Validates the STRUCTURE of data before analysis begins: schema conformance,
primary key integrity, completeness, date range coverage, referential
integrity, value domains, and row counts.

Each function accepts pandas DataFrames and returns a dict with an ``ok``
boolean.  Functions never raise exceptions for data issues -- problems are
reported in the return dict so callers can decide how to react.

Usage:
    from helpers.validation.structural_validator import (
        validate_schema, validate_primary_key,
        validate_completeness, validate_date_range,
        validate_referential_integrity, validate_value_domain,
        validate_row_count, run_structural_checks,
    )

    result = validate_schema(df, expected_columns=["user_id", "revenue"])
    if not result["ok"]:
        print(result["issues"])
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Set, Union

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Compatible dtype groups (for fuzzy type matching)
# ---------------------------------------------------------------------------

_NUMERIC_DTYPES: Set[str] = {
    "int8", "int16", "int32", "int64",
    "uint8", "uint16", "uint32", "uint64",
    "float16", "float32", "float64",
}
_DATETIME_DTYPES: Set[str] = {
    "datetime64[ns]", "datetime64[us]", "datetime64[ms]", "datetime64[s]",
}
_STRING_DTYPES: Set[str] = {"object", "string", "str"}


def _parse_date_column(col: pd.Series, name: str):
    """Parse a column to datetimes without silent numeric coercion.

    ``pd.to_datetime`` interprets raw integers as nanoseconds since epoch,
    which turns int-coded YYYYMMDD dates (e.g. 20240131) into 1970-01-01
    timestamps and lets garbage pass validation. This helper parses
    YYYYMMDD-looking integer columns with an explicit format and refuses
    any other numeric dtype outright.

    Returns
    -------
    tuple
        ``(parsed_or_None, warning_or_None, issue_or_None)``. When ``issue``
        is set the column is unusable as dates and the caller must fail.
        ``warning`` is set when the column parsed but is stored in a
        non-date dtype the caller should surface.
    """
    if pd.api.types.is_datetime64_any_dtype(col):
        return pd.to_datetime(col, errors="coerce"), None, None

    if pd.api.types.is_numeric_dtype(col):
        vals = col.dropna()
        looks_yyyymmdd = (
            len(vals) > 0
            and bool(((vals % 1) == 0).all())
            and bool(vals.between(10000101, 99991231).all())
        )
        if not looks_yyyymmdd:
            issue = (
                f"Column '{name}' has numeric dtype '{col.dtype}' that "
                f"cannot be interpreted as dates (values do not look like "
                f"YYYYMMDD integers). Convert the column to datetime "
                f"explicitly before validating."
            )
            return None, None, issue
        parsed = pd.to_datetime(
            vals.astype("int64").astype(str), format="%Y%m%d", errors="coerce"
        ).reindex(col.index)
        warning = (
            f"Column '{name}' stores dates as {col.dtype} YYYYMMDD integers, "
            f"not a datetime type; parsed with format='%Y%m%d'. Convert the "
            f"column to a proper date type."
        )
        return parsed, warning, None

    # Strings / object columns: normal coercing parse.
    return pd.to_datetime(col, errors="coerce"), None, None


def _dtypes_compatible(actual: str, expected: str) -> bool:
    """Return True if *actual* and *expected* dtype names are compatible.

    Allows int64/float64 to match (both numeric), various datetime
    precisions to match, and object/string to match.
    """
    actual_lower = str(actual).lower()
    expected_lower = str(expected).lower()

    if actual_lower == expected_lower:
        return True
    if actual_lower in _NUMERIC_DTYPES and expected_lower in _NUMERIC_DTYPES:
        return True
    if actual_lower in _DATETIME_DTYPES and expected_lower in _DATETIME_DTYPES:
        return True
    if actual_lower in _STRING_DTYPES and expected_lower in _STRING_DTYPES:
        return True
    return False


# ---------------------------------------------------------------------------
# 1. Schema validation
# ---------------------------------------------------------------------------

def validate_schema(
    df: pd.DataFrame,
    expected_columns: Optional[List[str]] = None,
    expected_types: Optional[Dict[str, str]] = None,
    # Legacy alias ---------------------------------------------------------
    expected_dtypes: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Check that *df* has the expected columns and types.

    Parameters
    ----------
    df : DataFrame
        The data to validate.
    expected_columns : list[str], optional
        Column names that must be present.  Extra columns are fine.
    expected_types : dict[str, str], optional
        Mapping of column name -> expected dtype string.  Compatible
        types (e.g. int64 and float64) are accepted.
    expected_dtypes : dict[str, str], optional
        Legacy alias for *expected_types* (for backward compatibility).

    Returns
    -------
    dict
        ``ok`` (bool), ``issues`` (list[str]), ``warnings`` (list[str]),
        ``missing_columns`` (list), ``dtype_mismatches`` (list of dicts),
        ``extra_columns`` (list), ``severity`` (str -- PASS/WARNING/BLOCKER),
        ``valid`` (bool -- same as ``ok``, kept for backward compat).
    """
    # Support legacy kwarg
    if expected_types is None and expected_dtypes is not None:
        expected_types = expected_dtypes

    issues: List[str] = []
    warnings: List[str] = []
    missing_columns: List[str] = []
    dtype_mismatches: List[Dict[str, str]] = []
    extra_columns: List[str] = []

    # Edge case: None or empty-column DataFrame
    if df is None or (isinstance(df, pd.DataFrame) and df.columns.empty):
        if expected_columns:
            missing_columns = list(expected_columns)
            issues.append(
                f"DataFrame has no columns; expected {expected_columns}"
            )
        return {
            "ok": len(issues) == 0,
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "missing_columns": missing_columns,
            "dtype_mismatches": dtype_mismatches,
            "extra_columns": extra_columns,
            "severity": "BLOCKER" if issues else "PASS",
        }

    actual_columns = set(df.columns.tolist())

    # --- Missing columns ---
    if expected_columns is not None:
        for col in expected_columns:
            if col not in actual_columns:
                missing_columns.append(col)
                issues.append(f"Missing required column: '{col}'")

    # --- Extra columns (informational) ---
    if expected_columns is not None:
        expected_set = set(expected_columns)
        extra_columns = sorted(actual_columns - expected_set)

    # --- Dtype mismatches ---
    if expected_types is not None:
        for col, expected_dtype in expected_types.items():
            if col not in actual_columns:
                continue  # already captured in missing_columns
            actual_dtype = str(df[col].dtype)
            if not _dtypes_compatible(actual_dtype, expected_dtype):
                dtype_mismatches.append({
                    "column": col,
                    "expected": str(expected_dtype),
                    "actual": actual_dtype,
                })
                warnings.append(
                    f"Column '{col}' has dtype '{actual_dtype}', "
                    f"expected '{expected_dtype}'"
                )

    # --- Severity ---
    if missing_columns:
        severity = "BLOCKER"
    elif dtype_mismatches:
        severity = "WARNING"
    else:
        severity = "PASS"

    ok = len(issues) == 0

    return {
        "ok": ok,
        "valid": ok,
        "issues": issues,
        "warnings": warnings,
        "missing_columns": missing_columns,
        "dtype_mismatches": dtype_mismatches,
        "extra_columns": extra_columns,
        "severity": severity,
    }


# ---------------------------------------------------------------------------
# 2. Primary key validation
# ---------------------------------------------------------------------------

def validate_primary_key(
    df: pd.DataFrame,
    key_columns: List[str],
) -> Dict[str, Any]:
    """Check that *key_columns* form a unique, non-null primary key.

    Parameters
    ----------
    df : DataFrame
        The data to validate.
    key_columns : list[str]
        Column names forming the composite primary key.

    Returns
    -------
    dict
        ``ok`` (bool), ``duplicate_count`` (int),
        ``duplicate_sample`` (DataFrame -- first 5 duplicate rows),
        ``null_count`` (int), ``severity`` (str), ``valid`` (bool).
    """
    # Edge case: empty DataFrame
    if len(df) == 0:
        return {
            "ok": True,
            "valid": True,
            "duplicate_count": 0,
            "duplicate_sample": pd.DataFrame(),
            "duplicate_examples": pd.DataFrame(),
            "null_count": 0,
            "severity": "PASS",
        }

    # --- Null check ---
    null_mask = df[key_columns].isna().any(axis=1)
    null_count = int(null_mask.sum())

    # --- Duplicate check ---
    dup_mask = df.duplicated(subset=key_columns, keep=False)
    duplicate_rows = df[dup_mask]
    duplicate_count = int(
        duplicate_rows.drop_duplicates(subset=key_columns).shape[0]
    )
    duplicate_sample = duplicate_rows.head(5).copy()

    # --- Severity ---
    if null_count > 0 or duplicate_count > 0:
        severity = "BLOCKER"
    else:
        severity = "PASS"

    ok = severity == "PASS"

    return {
        "ok": ok,
        "valid": ok,
        "duplicate_count": duplicate_count,
        "duplicate_sample": duplicate_sample,
        "duplicate_examples": duplicate_sample,  # legacy alias
        "null_count": null_count,
        "severity": severity,
    }


# ---------------------------------------------------------------------------
# 3. Completeness validation
# ---------------------------------------------------------------------------

def validate_completeness(
    df: pd.DataFrame,
    required_columns: Optional[List[str]] = None,
    threshold: float = 0.95,
) -> Dict[str, Any]:
    """Check null rates across columns.

    Parameters
    ----------
    df : DataFrame
        The data to validate.
    required_columns : list[str], optional
        Columns to inspect.  If None, all columns are checked.
    threshold : float
        Minimum non-null fraction required to pass (default 0.95, meaning
        at most 5 % nulls).  A column passes when its *completeness rate*
        (1 - null_rate) >= threshold.  ``threshold`` controls only
        ``ok``/``passes_threshold``; the ``severity`` labels always follow
        the canonical null-severity table shared with ``dq_extras`` and the
        data-quality-check skill text:

        - ``< 5%`` nulls: PASS
        - ``5-20%`` nulls: WARNING
        - ``> 20-50%`` nulls: SEVERE WARNING
        - ``> 50%`` nulls: BLOCKER

    Returns
    -------
    dict
        ``ok`` (bool), ``column_stats`` (list of dicts with name,
        null_count, null_rate, passes_threshold), ``columns`` (list --
        legacy alias), ``overall_severity`` (str), ``summary_text`` (str).
    """
    columns_to_check = (
        required_columns if required_columns else df.columns.tolist()
    )
    n = len(df)

    # Edge case: empty DataFrame
    if n == 0:
        column_stats = [
            {
                "name": col,
                "null_count": 0,
                "null_rate": 0.0,
                "passes_threshold": True,
                "severity": "PASS",
            }
            for col in columns_to_check
        ]
        return {
            "ok": True,
            "column_stats": column_stats,
            "columns": column_stats,
            "overall_severity": "WARNING",
            "summary_text": "DataFrame is empty -- no data to assess completeness.",
        }

    # Convert threshold from "completeness" (0.95) to max acceptable
    # null rate (0.05).
    max_null_rate = 1.0 - threshold

    column_stats: List[Dict[str, Any]] = []
    for col in columns_to_check:
        if col not in df.columns:
            column_stats.append({
                "name": col,
                "null_count": n,
                "null_rate": 1.0,
                "passes_threshold": False,
                "severity": "BLOCKER",
            })
            continue

        null_count = int(df[col].isna().sum())
        null_rate = float(null_count / n)
        passes = null_rate <= max_null_rate

        # Canonical null-severity table (single source of truth, mirrored in
        # dq_extras.check_null_concentration and the skill text):
        # <5% PASS, 5-20% WARNING, >20-50% SEVERE WARNING, >50% BLOCKER.
        if null_rate > 0.5:
            severity = "BLOCKER"
        elif null_rate > 0.2:
            severity = "SEVERE WARNING"
        elif null_rate >= 0.05:
            severity = "WARNING"
        else:
            severity = "PASS"
        # A caller-tightened threshold can still fail a column the canonical
        # table would pass; surface that as a WARNING rather than PASS.
        if not passes and severity == "PASS":
            severity = "WARNING"

        column_stats.append({
            "name": col,
            "null_count": null_count,
            "null_rate": round(null_rate, 6),
            "passes_threshold": passes,
            "severity": severity,
        })

    # --- Roll up severity ---
    severities = {c["severity"] for c in column_stats}
    if "BLOCKER" in severities:
        overall_severity = "BLOCKER"
    elif "SEVERE WARNING" in severities:
        overall_severity = "SEVERE WARNING"
    elif "WARNING" in severities:
        overall_severity = "WARNING"
    else:
        overall_severity = "PASS"

    ok = all(c["passes_threshold"] for c in column_stats)

    # --- Summary text ---
    blocker_cols = [c["name"] for c in column_stats if c["severity"] == "BLOCKER"]
    severe_cols = [c["name"] for c in column_stats if c["severity"] == "SEVERE WARNING"]
    warning_cols = [c["name"] for c in column_stats if c["severity"] == "WARNING"]

    parts: List[str] = []
    if blocker_cols:
        parts.append(f"{len(blocker_cols)} column(s) with >50% nulls: {blocker_cols}")
    if severe_cols:
        parts.append(f"{len(severe_cols)} column(s) with >20-50% nulls: {severe_cols}")
    if warning_cols:
        parts.append(f"{len(warning_cols)} column(s) with elevated nulls: {warning_cols}")
    if not parts:
        parts.append(
            f"All {len(column_stats)} column(s) within acceptable null thresholds."
        )

    summary_text = " ".join(parts)

    return {
        "ok": ok,
        "column_stats": column_stats,
        "columns": column_stats,  # legacy alias
        "overall_severity": overall_severity,
        "summary_text": summary_text,
    }


# ---------------------------------------------------------------------------
# 4. Date range validation
# ---------------------------------------------------------------------------

def validate_date_range(
    df: pd.DataFrame,
    date_column: str,
    expected_start: Optional[str] = None,
    expected_end: Optional[str] = None,
    max_gap_days: Optional[int] = None,
) -> Dict[str, Any]:
    """Check temporal coverage of a date column.

    Parameters
    ----------
    df : DataFrame
        The data to validate.
    date_column : str
        Name of the date/datetime column.
    expected_start : str, optional
        Earliest expected date (ISO format).
    expected_end : str, optional
        Latest expected date (ISO format).
    max_gap_days : int, optional
        Maximum allowed gap in days between consecutive dates.

    Date columns stored as YYYYMMDD integers are parsed with an explicit
    ``%Y%m%d`` format (and flagged in ``warnings``); any other numeric
    dtype fails loudly instead of being silently coerced to
    nanoseconds-since-epoch.

    Returns
    -------
    dict
        ``ok`` (bool), ``actual_start`` (str), ``actual_end`` (str),
        ``gaps`` (list of dicts with start/end/gap_days), ``issues``
        (list[str]), ``warnings`` (list[str]), ``severity`` (str).
    """
    issues: List[str] = []
    warnings: List[str] = []
    gaps: List[Dict[str, Any]] = []

    # Edge case: empty DataFrame
    if len(df) == 0:
        return {
            "ok": True,
            "actual_start": None,
            "actual_end": None,
            "gaps": [],
            "issues": issues,
            "warnings": warnings,
            "severity": "PASS",
        }

    # Edge case: column not present
    if date_column not in df.columns:
        issues.append(f"Date column '{date_column}' not found in DataFrame")
        return {
            "ok": False,
            "actual_start": None,
            "actual_end": None,
            "gaps": [],
            "issues": issues,
            "warnings": warnings,
            "severity": "BLOCKER",
        }

    parsed, dtype_warning, dtype_issue = _parse_date_column(
        df[date_column], date_column
    )
    if dtype_issue is not None:
        issues.append(dtype_issue)
        return {
            "ok": False,
            "actual_start": None,
            "actual_end": None,
            "gaps": [],
            "issues": issues,
            "warnings": warnings,
            "severity": "BLOCKER",
        }
    if dtype_warning is not None:
        warnings.append(dtype_warning)

    dates = parsed.dropna().sort_values()

    if len(dates) == 0:
        issues.append(f"No valid dates in column '{date_column}'")
        return {
            "ok": False,
            "actual_start": None,
            "actual_end": None,
            "gaps": [],
            "issues": issues,
            "warnings": warnings,
            "severity": "BLOCKER",
        }

    actual_start = dates.min()
    actual_end = dates.max()
    actual_start_str = str(actual_start.date())
    actual_end_str = str(actual_end.date())

    # --- Check expected boundaries ---
    if expected_start is not None:
        expected_start_dt = pd.to_datetime(expected_start)
        if actual_start > expected_start_dt:
            issues.append(
                f"Data starts at {actual_start_str}, "
                f"expected start {expected_start}"
            )
        elif actual_start < expected_start_dt:
            issues.append(
                f"Data starts at {actual_start_str}, "
                f"before expected start {expected_start}"
            )

    if expected_end is not None:
        expected_end_dt = pd.to_datetime(expected_end)
        if actual_end < expected_end_dt:
            issues.append(
                f"Data ends at {actual_end_str}, "
                f"expected end {expected_end}"
            )
        elif actual_end > expected_end_dt:
            issues.append(
                f"Data ends at {actual_end_str}, "
                f"after expected end {expected_end}"
            )

    # --- Gap detection ---
    if max_gap_days is not None and len(dates) >= 2:
        unique_dates = dates.dt.normalize().drop_duplicates().sort_values()
        diffs = unique_dates.diff().dropna()
        for idx, diff in diffs.items():
            gap_days = diff.days
            if gap_days > max_gap_days:
                gap_end_date = unique_dates.loc[idx]
                gap_start_date = gap_end_date - diff
                gaps.append({
                    "start": str(gap_start_date.date()),
                    "end": str(gap_end_date.date()),
                    "gap_days": gap_days,
                })
        if gaps:
            issues.append(
                f"Found {len(gaps)} gap(s) exceeding {max_gap_days} day(s)"
            )

    ok = len(issues) == 0
    severity = "BLOCKER" if issues else ("WARNING" if warnings else "PASS")

    return {
        "ok": ok,
        "actual_start": actual_start_str,
        "actual_end": actual_end_str,
        "gaps": gaps,
        "issues": issues,
        "warnings": warnings,
        "severity": severity,
    }


# ---------------------------------------------------------------------------
# 5. Referential integrity validation
# ---------------------------------------------------------------------------

def validate_referential_integrity(
    # Positional args use the *legacy* order: parent first, child second.
    # This keeps backward compatibility with the old API:
    #   validate_referential_integrity(parent_df, child_df, parent_key, child_key)
    # The new recommended API uses keyword args:
    #   validate_referential_integrity(df_child=..., df_parent=..., ...)
    _pos_arg1: Optional[pd.DataFrame] = None,
    _pos_arg2: Optional[pd.DataFrame] = None,
    _pos_arg3: str = "",
    _pos_arg4: str = "",
    *,
    df_child: Optional[pd.DataFrame] = None,
    df_parent: Optional[pd.DataFrame] = None,
    child_key: str = "",
    parent_key: str = "",
    parent_df: Optional[pd.DataFrame] = None,
    child_df: Optional[pd.DataFrame] = None,
) -> Dict[str, Any]:
    """Check that all *child_key* values exist in *parent_key*.

    Parameters
    ----------
    df_child : DataFrame
        Child (fact) table.
    df_parent : DataFrame
        Parent (lookup) table.
    child_key : str
        Column name in *df_child*.
    parent_key : str
        Column name in *df_parent*.

    Also accepts the legacy positional order
    ``(parent_df, child_df, parent_key, child_key)`` and the legacy
    keyword aliases ``parent_df=`` / ``child_df=``.

    Returns
    -------
    dict
        ``ok`` (bool), ``orphan_count`` (int), ``orphan_sample`` (list),
        ``orphan_rate`` (float), ``orphan_examples`` (list -- legacy alias),
        ``severity`` (str), ``valid`` (bool).
    """
    # --- Resolve arguments (support old and new calling conventions) ---
    # Priority: explicit keyword > legacy keyword > positional
    resolved_parent = df_parent if df_parent is not None else parent_df
    resolved_child = df_child if df_child is not None else child_df
    resolved_parent_key = parent_key
    resolved_child_key = child_key

    # Positional: (parent, child, parent_key, child_key)
    if _pos_arg1 is not None and resolved_parent is None:
        resolved_parent = _pos_arg1
    if _pos_arg2 is not None and resolved_child is None:
        resolved_child = _pos_arg2
    if _pos_arg3 and not resolved_parent_key:
        resolved_parent_key = _pos_arg3
    if _pos_arg4 and not resolved_child_key:
        resolved_child_key = _pos_arg4

    # Safety: ensure we have DataFrames
    if resolved_child is None or resolved_parent is None:
        return {
            "ok": False,
            "valid": False,
            "orphan_count": 0,
            "orphan_sample": [],
            "orphan_examples": [],
            "orphan_rate": 0.0,
            "severity": "BLOCKER",
        }

    # Edge case: empty child DataFrame
    if len(resolved_child) == 0:
        return {
            "ok": True,
            "valid": True,
            "orphan_count": 0,
            "orphan_sample": [],
            "orphan_examples": [],
            "orphan_rate": 0.0,
            "severity": "PASS",
        }

    parent_values = set(resolved_parent[resolved_parent_key].dropna().unique())
    child_values = resolved_child[resolved_child_key].dropna()

    orphan_mask = ~child_values.isin(parent_values)
    orphan_count = int(orphan_mask.sum())
    orphan_rate = (
        float(orphan_count / len(resolved_child))
        if len(resolved_child) > 0
        else 0.0
    )
    orphan_sample = child_values[orphan_mask].unique().tolist()[:10]

    # --- Severity ---
    if orphan_rate > 0.05:
        severity = "BLOCKER"
    elif orphan_rate > 0:
        severity = "WARNING"
    else:
        severity = "PASS"

    ok = orphan_count == 0

    return {
        "ok": ok,
        "valid": severity == "PASS",
        "orphan_count": orphan_count,
        "orphan_sample": orphan_sample,
        "orphan_examples": orphan_sample,  # legacy alias
        "orphan_rate": round(orphan_rate, 6),
        "severity": severity,
    }


# ---------------------------------------------------------------------------
# 6. Value domain validation
# ---------------------------------------------------------------------------

def validate_value_domain(
    df: pd.DataFrame,
    column: str,
    valid_values: Optional[Sequence[Any]] = None,
    min_val: Optional[Union[int, float]] = None,
    max_val: Optional[Union[int, float]] = None,
) -> Dict[str, Any]:
    """Check that values in *column* fall within an expected domain.

    Supports both categorical (``valid_values``) and numeric
    (``min_val``/``max_val``) checks.

    Parameters
    ----------
    df : DataFrame
        The data to validate.
    column : str
        Column to inspect.
    valid_values : sequence, optional
        Set of allowed categorical values.
    min_val : numeric, optional
        Minimum allowed value (inclusive).
    max_val : numeric, optional
        Maximum allowed value (inclusive).

    Returns
    -------
    dict
        ``ok`` (bool), ``out_of_range_count`` (int),
        ``unexpected_values`` (list).
    """
    issues: List[str] = []
    out_of_range_count = 0
    unexpected_values: List[Any] = []

    if column not in df.columns:
        issues.append(f"Column '{column}' not found in DataFrame")
        return {
            "ok": False,
            "out_of_range_count": 0,
            "unexpected_values": [],
            "issues": issues,
        }

    series = df[column].dropna()

    # Categorical check
    if valid_values is not None:
        valid_set = set(valid_values)
        actual_set = set(series.unique())
        unexpected = actual_set - valid_set
        if unexpected:
            unexpected_values = sorted(str(v) for v in unexpected)
            mask = series.isin(unexpected)
            out_of_range_count += int(mask.sum())
            issues.append(
                f"Found {len(unexpected)} unexpected value(s) in '{column}': "
                f"{unexpected_values[:5]}"
            )

    # Numeric range check
    if min_val is not None:
        below = series[series < min_val]
        if len(below) > 0:
            out_of_range_count += len(below)
            issues.append(
                f"{len(below)} value(s) in '{column}' below minimum {min_val}"
            )

    if max_val is not None:
        above = series[series > max_val]
        if len(above) > 0:
            out_of_range_count += len(above)
            issues.append(
                f"{len(above)} value(s) in '{column}' above maximum {max_val}"
            )

    ok = len(issues) == 0

    return {
        "ok": ok,
        "out_of_range_count": out_of_range_count,
        "unexpected_values": unexpected_values,
        "issues": issues,
    }


# ---------------------------------------------------------------------------
# 7. Row count validation
# ---------------------------------------------------------------------------

def validate_row_count(
    df: pd.DataFrame,
    min_rows: int = 1,
    max_rows: Optional[int] = None,
) -> Dict[str, Any]:
    """Check that *df* has an acceptable number of rows.

    Parameters
    ----------
    df : DataFrame
        The data to validate.
    min_rows : int
        Minimum required row count (default 1).
    max_rows : int, optional
        Maximum allowed row count.

    Returns
    -------
    dict
        ``ok`` (bool), ``row_count`` (int), ``message`` (str).
    """
    row_count = len(df)
    issues: List[str] = []

    if row_count < min_rows:
        issues.append(
            f"Row count {row_count:,} is below minimum {min_rows:,}"
        )

    if max_rows is not None and row_count > max_rows:
        issues.append(
            f"Row count {row_count:,} exceeds maximum {max_rows:,}"
        )

    ok = len(issues) == 0
    message = (
        f"Row count: {row_count:,}"
        if ok
        else "; ".join(issues)
    )

    return {
        "ok": ok,
        "row_count": row_count,
        "message": message,
    }


# ---------------------------------------------------------------------------
# 8. Orchestrator
# ---------------------------------------------------------------------------

def run_structural_checks(
    df: pd.DataFrame,
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Run all applicable structural checks based on *config*.

    Parameters
    ----------
    df : DataFrame
        The data to validate.
    config : dict, optional
        Keys control which checks to run and their parameters:

        - ``expected_columns`` (list[str]) -- triggers schema check
        - ``expected_types`` (dict) -- passed to schema check
        - ``primary_key`` (list[str]) -- triggers PK check
        - ``required_columns`` (list[str]) -- triggers completeness check
        - ``completeness_threshold`` (float) -- default 0.95
        - ``date_column`` (str) -- triggers date range check
        - ``expected_start`` (str) -- for date range check
        - ``expected_end`` (str) -- for date range check
        - ``max_gap_days`` (int) -- for date range check
        - ``parent_df`` (DataFrame) -- triggers RI check
        - ``child_key`` (str) -- for RI check
        - ``parent_key`` (str) -- for RI check
        - ``value_domain`` (dict) -- triggers value domain check
          with keys ``column``, ``valid_values``, ``min_val``, ``max_val``
        - ``min_rows`` (int) -- triggers row count check
        - ``max_rows`` (int) -- for row count check

        If *config* is None, runs schema (all columns), completeness
        (all columns), and row count (min_rows=1) as defaults.

    Returns
    -------
    dict
        ``overall_ok`` (bool), ``checks_run`` (int),
        ``checks_passed`` (int), ``checks_failed`` (int),
        ``details`` (dict mapping check name -> result dict).
    """
    if config is None:
        config = {}

    details: Dict[str, Dict[str, Any]] = {}

    # --- Schema check ---
    if "expected_columns" in config or "expected_types" in config:
        details["schema"] = validate_schema(
            df,
            expected_columns=config.get("expected_columns"),
            expected_types=config.get("expected_types"),
        )

    # --- Primary key check ---
    if "primary_key" in config:
        details["primary_key"] = validate_primary_key(
            df,
            key_columns=config["primary_key"],
        )

    # --- Completeness check ---
    if "required_columns" in config:
        details["completeness"] = validate_completeness(
            df,
            required_columns=config["required_columns"],
            threshold=config.get("completeness_threshold", 0.95),
        )

    # --- Date range check ---
    if "date_column" in config:
        details["date_range"] = validate_date_range(
            df,
            date_column=config["date_column"],
            expected_start=config.get("expected_start"),
            expected_end=config.get("expected_end"),
            max_gap_days=config.get("max_gap_days"),
        )

    # --- Referential integrity check ---
    if "parent_df" in config:
        details["referential_integrity"] = validate_referential_integrity(
            df_child=df,
            df_parent=config["parent_df"],
            child_key=config.get("child_key", ""),
            parent_key=config.get("parent_key", ""),
        )

    # --- Value domain check ---
    if "value_domain" in config:
        vd = config["value_domain"]
        details["value_domain"] = validate_value_domain(
            df,
            column=vd.get("column", ""),
            valid_values=vd.get("valid_values"),
            min_val=vd.get("min_val"),
            max_val=vd.get("max_val"),
        )

    # --- Row count check ---
    min_rows = config.get("min_rows")
    max_rows = config.get("max_rows")
    if min_rows is not None or max_rows is not None:
        details["row_count"] = validate_row_count(
            df,
            min_rows=min_rows if min_rows is not None else 1,
            max_rows=max_rows,
        )

    # If no checks were configured, run sensible defaults
    if not details:
        details["schema"] = validate_schema(df)
        details["completeness"] = validate_completeness(df)
        details["row_count"] = validate_row_count(df, min_rows=1)

    # --- Summarise ---
    checks_run = len(details)
    checks_passed = sum(1 for r in details.values() if r.get("ok", False))
    checks_failed = checks_run - checks_passed
    overall_ok = checks_failed == 0

    return {
        "overall_ok": overall_ok,
        "checks_run": checks_run,
        "checks_passed": checks_passed,
        "checks_failed": checks_failed,
        "details": details,
    }
