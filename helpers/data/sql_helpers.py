"""
SQL sanity check helpers for validating query results.

All functions accept pandas DataFrames and return structured check results.
Each result is a dict with keys: status ("PASS", "WARN", "FAIL"),
message (human-readable), and details (dict with specifics).

Usage:
    from helpers.data.sql_helpers import (
        check_join_cardinality, check_percentages_sum,
        check_date_bounds, check_no_duplicates, warn_temporal_join,
        check_temporal_coverage, check_value_domain, check_monotonic,
    )

    result = check_join_cardinality(df_before, df_after, "LEFT")
    print(result["status"], result["message"])

    result = check_percentages_sum(df["market_share"])
    print(result["status"], result["message"])
"""

import re

import pandas as pd


# ---------------------------------------------------------------------------
# Join cardinality check
# ---------------------------------------------------------------------------

def check_join_cardinality(df_before_join, df_after_join, join_type,
                           expected="same"):
    """Check whether a join produced the expected number of rows.

    Compares row counts before and after a join to detect fan-outs
    (many-to-many joins) or unexpected row loss.

    Args:
        df_before_join: DataFrame before the join operation.
        df_after_join: DataFrame after the join operation.
        join_type: Type of join performed ("INNER", "LEFT", "RIGHT", "CROSS").
        expected: Expected row count relationship — "same", "more", or "fewer".

    Returns:
        dict with keys: status, message, details

    Examples:
        >>> orders = pd.DataFrame({"order_id": [1, 2, 3]})
        >>> joined = pd.DataFrame({"order_id": [1, 2, 3]})
        >>> result = check_join_cardinality(orders, joined, "LEFT")
        >>> result["status"]
        'PASS'

        >>> # Many-to-many fan-out
        >>> exploded = pd.DataFrame({"order_id": range(10)})
        >>> result = check_join_cardinality(orders, exploded, "LEFT")
        >>> result["status"]
        'FAIL'
    """
    before = len(df_before_join)
    after = len(df_after_join)
    ratio = after / before if before > 0 else float("inf")
    join_type_upper = join_type.upper().strip()

    details = {
        "rows_before": before,
        "rows_after": after,
        "ratio": round(ratio, 4),
        "join_type": join_type_upper,
        "expected": expected,
    }

    # Check for many-to-many fan-out (>2x rows for non-CROSS joins)
    if join_type_upper != "CROSS" and ratio > 2.0:
        return {
            "status": "FAIL",
            "message": (
                f"{join_type_upper} JOIN produced {after:,} rows from "
                f"{before:,} — {ratio:.1f}x fan-out suggests many-to-many."
            ),
            "details": details,
        }

    # Check against expectation
    if expected == "same":
        if before == after:
            return {
                "status": "PASS",
                "message": f"Row count unchanged after {join_type_upper} JOIN ({after:,} rows).",
                "details": details,
            }
        else:
            return {
                "status": "WARN",
                "message": (
                    f"Expected same row count but got {after:,} from "
                    f"{before:,} after {join_type_upper} JOIN ({ratio:.2f}x)."
                ),
                "details": details,
            }

    elif expected == "more":
        if after > before:
            return {
                "status": "PASS",
                "message": (
                    f"Row count increased as expected: {before:,} → {after:,} "
                    f"after {join_type_upper} JOIN."
                ),
                "details": details,
            }
        else:
            return {
                "status": "WARN",
                "message": (
                    f"Expected more rows but got {after:,} from {before:,} "
                    f"after {join_type_upper} JOIN."
                ),
                "details": details,
            }

    elif expected == "fewer":
        if after < before:
            return {
                "status": "PASS",
                "message": (
                    f"Row count decreased as expected: {before:,} → {after:,} "
                    f"after {join_type_upper} JOIN."
                ),
                "details": details,
            }
        else:
            return {
                "status": "WARN",
                "message": (
                    f"Expected fewer rows but got {after:,} from {before:,} "
                    f"after {join_type_upper} JOIN."
                ),
                "details": details,
            }

    else:
        return {
            "status": "WARN",
            "message": f"Unknown expected value '{expected}'; cannot evaluate.",
            "details": details,
        }


# ---------------------------------------------------------------------------
# Percentage sum check
# ---------------------------------------------------------------------------

def check_percentages_sum(series, expected_total=100.0, tolerance=1.0):
    """Check if a percentage column sums to the expected total.

    Useful for verifying funnel step percentages, market share breakdowns,
    or any column that should represent parts of a whole.

    Args:
        series: pandas Series of percentage values.
        expected_total: Expected sum (default 100.0).
        tolerance: Acceptable deviation from expected_total (default 1.0).
            PASS if within tolerance, WARN if within 2x tolerance, FAIL otherwise.

    Returns:
        dict with keys: status, message, details

    Examples:
        >>> shares = pd.Series([40.0, 30.0, 20.0, 10.0])
        >>> result = check_percentages_sum(shares)
        >>> result["status"]
        'PASS'

        >>> bad_shares = pd.Series([40.0, 30.0, 20.0])
        >>> result = check_percentages_sum(bad_shares)
        >>> result["status"]
        'FAIL'
    """
    actual_sum = float(series.sum())
    diff = abs(actual_sum - expected_total)

    details = {
        "actual_sum": round(actual_sum, 6),
        "expected_total": expected_total,
        "difference": round(diff, 6),
        "tolerance": tolerance,
        "n_values": len(series),
    }

    if diff <= tolerance:
        return {
            "status": "PASS",
            "message": (
                f"Percentages sum to {actual_sum:.2f} "
                f"(expected {expected_total}, within ±{tolerance})."
            ),
            "details": details,
        }
    elif diff <= tolerance * 2:
        return {
            "status": "WARN",
            "message": (
                f"Percentages sum to {actual_sum:.2f} — off by {diff:.2f} "
                f"from {expected_total} (outside ±{tolerance} but within "
                f"±{tolerance * 2})."
            ),
            "details": details,
        }
    else:
        return {
            "status": "FAIL",
            "message": (
                f"Percentages sum to {actual_sum:.2f} — off by {diff:.2f} "
                f"from {expected_total} (exceeds ±{tolerance * 2} tolerance)."
            ),
            "details": details,
        }


# ---------------------------------------------------------------------------
# Date bounds check
# ---------------------------------------------------------------------------

def check_date_bounds(df, date_col, expected_min=None, expected_max=None):
    """Check if dates in a column fall within an expected range.

    Handles both string dates (parsed via pd.to_datetime) and datetime
    objects. Returns count and percentage of out-of-range rows.

    Args:
        df: DataFrame containing the date column.
        date_col: Name of the column to check.
        expected_min: Earliest allowed date (str or datetime, optional).
        expected_max: Latest allowed date (str or datetime, optional).

    Returns:
        dict with keys: status, message, details

    Examples:
        >>> df = pd.DataFrame({"order_date": ["2024-01-01", "2024-06-15", "2024-12-31"]})
        >>> result = check_date_bounds(df, "order_date",
        ...     expected_min="2024-01-01", expected_max="2024-12-31")
        >>> result["status"]
        'PASS'

        >>> result = check_date_bounds(df, "order_date",
        ...     expected_min="2024-03-01", expected_max="2024-09-30")
        >>> result["status"]
        'WARN'
    """
    dates = pd.to_datetime(df[date_col], errors="coerce")
    non_null = dates.dropna()
    total_rows = len(df)

    if len(non_null) == 0:
        return {
            "status": "WARN",
            "message": f"Column '{date_col}' has no valid dates to check.",
            "details": {
                "date_col": date_col,
                "total_rows": total_rows,
                "valid_dates": 0,
                "null_dates": total_rows,
            },
        }

    actual_min = non_null.min()
    actual_max = non_null.max()

    out_of_range = pd.Series([False] * len(dates), index=dates.index)
    parsed_expected_min = None
    parsed_expected_max = None

    if expected_min is not None:
        parsed_expected_min = pd.to_datetime(expected_min)
        out_of_range = out_of_range | (dates < parsed_expected_min)

    if expected_max is not None:
        parsed_expected_max = pd.to_datetime(expected_max)
        out_of_range = out_of_range | (dates > parsed_expected_max)

    # Exclude nulls from out-of-range count
    out_of_range = out_of_range & dates.notna()
    n_out = int(out_of_range.sum())
    pct_out = round(100 * n_out / total_rows, 2) if total_rows > 0 else 0.0

    details = {
        "date_col": date_col,
        "total_rows": total_rows,
        "valid_dates": len(non_null),
        "actual_min": str(actual_min),
        "actual_max": str(actual_max),
        "expected_min": str(expected_min) if expected_min else None,
        "expected_max": str(expected_max) if expected_max else None,
        "out_of_range_count": n_out,
        "out_of_range_pct": pct_out,
    }

    if n_out == 0:
        return {
            "status": "PASS",
            "message": (
                f"All dates in '{date_col}' are within bounds "
                f"({actual_min.date()} to {actual_max.date()})."
            ),
            "details": details,
        }
    else:
        return {
            "status": "WARN",
            "message": (
                f"{n_out:,} rows ({pct_out}%) in '{date_col}' fall outside "
                f"expected range. Actual: {actual_min.date()} to "
                f"{actual_max.date()}."
            ),
            "details": details,
        }


# ---------------------------------------------------------------------------
# Duplicate check
# ---------------------------------------------------------------------------

def check_no_duplicates(df, key_cols):
    """Check for duplicate rows based on key columns.

    Args:
        df: DataFrame to check.
        key_cols: Column name (str) or list of column names that should
            form a unique key.

    Returns:
        dict with keys: status, message, details

    Examples:
        >>> df = pd.DataFrame({"order_id": [1, 2, 3], "item": ["a", "b", "c"]})
        >>> result = check_no_duplicates(df, "order_id")
        >>> result["status"]
        'PASS'

        >>> df_dup = pd.DataFrame({"order_id": [1, 2, 2], "item": ["a", "b", "c"]})
        >>> result = check_no_duplicates(df_dup, "order_id")
        >>> result["status"]
        'FAIL'
    """
    if isinstance(key_cols, str):
        key_cols = [key_cols]

    duplicated_mask = df.duplicated(subset=key_cols, keep=False)
    n_duplicates = int(duplicated_mask.sum())

    details = {
        "key_cols": key_cols,
        "total_rows": len(df),
        "duplicate_rows": n_duplicates,
    }

    if n_duplicates == 0:
        return {
            "status": "PASS",
            "message": (
                f"No duplicates found on key {key_cols} "
                f"({len(df):,} rows checked)."
            ),
            "details": details,
        }
    else:
        # Find the duplicate key combinations and sample up to 5
        dup_rows = df.loc[duplicated_mask, key_cols].drop_duplicates()
        sample_keys = dup_rows.head(5).to_dict(orient="records")
        n_unique_dup_keys = len(dup_rows)

        details["unique_duplicate_keys"] = n_unique_dup_keys
        details["sample_duplicate_keys"] = sample_keys

        return {
            "status": "FAIL",
            "message": (
                f"Found {n_duplicates:,} duplicate rows across "
                f"{n_unique_dup_keys:,} duplicate key(s) on {key_cols}."
            ),
            "details": details,
        }


# ---------------------------------------------------------------------------
# Temporal join warning
# ---------------------------------------------------------------------------

# Common temporal column name patterns
_TEMPORAL_COLS = re.compile(
    r"\b(started_at|ended_at|valid_from|valid_to|effective_from|effective_to"
    r"|start_date|end_date|created_at|updated_at|expired_at)\b",
    re.IGNORECASE,
)

# Temporal condition patterns (BETWEEN, >=, <=, >, <)
_TEMPORAL_CONDITIONS = re.compile(
    r"\bBETWEEN\b|>=|<=|>\s|<\s",
    re.IGNORECASE,
)


def warn_temporal_join(sql_text):
    """Scan SQL text for JOINs on temporal tables without temporal conditions.

    This is a text-based heuristic using regex — not a full SQL parser.
    It looks for JOIN clauses that reference tables with temporal columns
    (started_at, ended_at, valid_from, valid_to, etc.) and warns if no
    temporal condition (BETWEEN, >=, <=) appears nearby in the ON clause.

    Args:
        sql_text: SQL query string to scan.

    Returns:
        dict with keys: status, message, details

    Examples:
        >>> sql = '''
        ... SELECT *
        ... FROM orders o
        ... JOIN memberships m ON o.user_id = m.user_id
        ...     AND o.order_date BETWEEN m.started_at AND m.ended_at
        ... '''
        >>> result = warn_temporal_join(sql)
        >>> result["status"]
        'PASS'

        >>> sql_bad = '''
        ... SELECT *
        ... FROM orders o
        ... JOIN memberships m ON o.user_id = m.user_id
        ... '''
        >>> result = warn_temporal_join(sql_bad)
        >>> result["status"]
        'PASS'
    """
    warnings = []

    # Split SQL into JOIN clauses — look for JOIN ... ON ... patterns
    # We split on JOIN keywords to analyze each join independently
    join_pattern = re.compile(
        r"\bJOIN\b\s+([\w.]+)\s+(?:AS\s+)?(\w+)?\s*\bON\b\s+(.*?)(?=\bJOIN\b|\bWHERE\b|\bGROUP\b|\bORDER\b|\bLIMIT\b|\bUNION\b|;|\Z)",
        re.IGNORECASE | re.DOTALL,
    )

    for match in join_pattern.finditer(sql_text):
        table_name = match.group(1)
        alias = match.group(2) or table_name
        on_clause = match.group(3)

        # Check if the ON clause references any temporal columns
        temporal_cols_found = _TEMPORAL_COLS.findall(on_clause)

        if not temporal_cols_found:
            # No temporal columns in ON clause — nothing to warn about
            # for this join. Even if temporal columns appear elsewhere in
            # the query (e.g., WHERE clause), that is fine.
            continue

        # Temporal columns ARE in the ON clause — check for temporal conditions
        has_temporal_condition = bool(_TEMPORAL_CONDITIONS.search(on_clause))
        if not has_temporal_condition:
            warnings.append({
                "table": table_name,
                "alias": alias,
                "temporal_cols": temporal_cols_found,
                "issue": "JOIN references temporal columns but lacks BETWEEN/>=/<= condition.",
            })

    details = {
        "sql_length": len(sql_text),
        "joins_scanned": len(join_pattern.findall(sql_text)),
        "warnings": warnings,
    }

    if not warnings:
        return {
            "status": "PASS",
            "message": "No temporal join issues detected.",
            "details": details,
        }
    else:
        table_list = ", ".join(w["table"] for w in warnings)
        return {
            "status": "WARN",
            "message": (
                f"Potential temporal join issue on: {table_list}. "
                f"JOINs reference temporal columns without BETWEEN/>=/<= "
                f"conditions — rows may match across time boundaries."
            ),
            "details": details,
        }


# ---------------------------------------------------------------------------
# DQ-1.2: Temporal coverage check
# ---------------------------------------------------------------------------

def check_temporal_coverage(df, date_col, freq="D", max_gap_tolerance=1):
    """Check for gaps in a time series.

    Computes the expected date range at the given frequency and identifies
    missing periods. Useful for detecting data ingestion failures or
    incomplete time ranges.

    Args:
        df: DataFrame containing the date column.
        date_col: Name of the date/datetime column.
        freq: Expected frequency — ``"D"`` (daily), ``"W"`` (weekly),
            ``"M"`` (monthly), ``"H"`` (hourly).
        max_gap_tolerance: Number of consecutive missing periods before
            a gap is flagged. Default 1 (flag any single missing period).

    Date columns stored as YYYYMMDD integers are parsed with an explicit
    ``%Y%m%d`` format (noted in the message); any other numeric dtype
    returns FAIL instead of being silently coerced to
    nanoseconds-since-epoch.

    Returns:
        dict with keys: status, message, details
    """
    col = df[date_col]
    dtype_note = None

    if pd.api.types.is_numeric_dtype(col):
        vals = col.dropna()
        looks_yyyymmdd = (
            len(vals) > 0
            and bool(((vals % 1) == 0).all())
            and bool(vals.between(10000101, 99991231).all())
        )
        if not looks_yyyymmdd:
            return {
                "status": "FAIL",
                "message": (
                    f"Column '{date_col}' has numeric dtype '{col.dtype}' "
                    f"that cannot be interpreted as dates (values do not "
                    f"look like YYYYMMDD integers). Convert the column to "
                    f"datetime explicitly before checking coverage."
                ),
                "details": {"date_col": date_col, "dtype": str(col.dtype)},
            }
        dates = pd.to_datetime(
            vals.astype("int64").astype(str), format="%Y%m%d", errors="coerce"
        ).dropna()
        dtype_note = (
            f"Note: '{date_col}' stores dates as {col.dtype} YYYYMMDD "
            f"integers; parsed with format='%Y%m%d'."
        )
    else:
        dates = pd.to_datetime(col, errors="coerce").dropna()

    if len(dates) < 2:
        return {
            "status": "WARN",
            "message": f"Too few dates in '{date_col}' to check coverage.",
            "details": {"date_col": date_col, "valid_dates": len(dates)},
        }

    date_min = dates.min()
    date_max = dates.max()

    # Generate expected date range
    expected = pd.date_range(start=date_min, end=date_max, freq=freq)
    actual_periods = set(dates.dt.to_period(freq))
    expected_periods = set(expected.to_period(freq))
    missing = sorted(expected_periods - actual_periods)

    # Group consecutive missing periods into gaps
    gaps = []
    if missing:
        gap_start = missing[0]
        gap_end = missing[0]
        for period in missing[1:]:
            if period.ordinal - gap_end.ordinal <= 1:
                gap_end = period
            else:
                gap_len = gap_end.ordinal - gap_start.ordinal + 1
                if gap_len > max_gap_tolerance:
                    gaps.append({
                        "start": str(gap_start),
                        "end": str(gap_end),
                        "missing_periods": gap_len,
                    })
                gap_start = period
                gap_end = period
        # Final gap
        gap_len = gap_end.ordinal - gap_start.ordinal + 1
        if gap_len > max_gap_tolerance:
            gaps.append({
                "start": str(gap_start),
                "end": str(gap_end),
                "missing_periods": gap_len,
            })

    n_missing = len(missing)
    n_expected = len(expected_periods)
    coverage_pct = round(100 * (1 - n_missing / n_expected), 2) if n_expected > 0 else 100.0

    details = {
        "date_col": date_col,
        "freq": freq,
        "range": f"{date_min.date()} to {date_max.date()}",
        "expected_periods": n_expected,
        "actual_periods": n_expected - n_missing,
        "missing_periods": n_missing,
        "coverage_pct": coverage_pct,
        "gaps": gaps[:10],  # cap display
    }
    if dtype_note:
        details["dtype_note"] = dtype_note

    def _msg(text):
        return f"{text} {dtype_note}" if dtype_note else text

    if n_missing == 0:
        return {
            "status": "PASS",
            "message": _msg(
                f"Full temporal coverage for '{date_col}' ({coverage_pct}%)."
            ),
            "details": details,
        }
    elif coverage_pct >= 95:
        return {
            "status": "WARN",
            "message": _msg(
                f"Minor gaps in '{date_col}': {n_missing} missing {freq} "
                f"periods ({coverage_pct}% coverage)."
            ),
            "details": details,
        }
    else:
        return {
            "status": "FAIL",
            "message": _msg(
                f"Significant gaps in '{date_col}': {n_missing} missing {freq} "
                f"periods ({coverage_pct}% coverage). {len(gaps)} gap(s) found."
            ),
            "details": details,
        }


# ---------------------------------------------------------------------------
# DQ-1.2: Value domain check
# ---------------------------------------------------------------------------

def check_value_domain(series, expected_values, allow_null=True):
    """Check that a categorical column contains only expected values.

    Args:
        series: pandas.Series of categorical values.
        expected_values: Set or list of allowed values.
        allow_null: If True, NaN/None values are ignored. If False,
            nulls count as unexpected values.

    Returns:
        dict with keys: status, message, details
    """
    expected = set(expected_values)
    actual = set(series.dropna().unique()) if allow_null else set(series.unique())
    unexpected = actual - expected
    missing_expected = expected - actual

    details = {
        "expected_values": sorted(str(v) for v in expected),
        "actual_values": sorted(str(v) for v in actual),
        "unexpected_values": sorted(str(v) for v in unexpected),
        "missing_expected": sorted(str(v) for v in missing_expected),
        "n_unexpected_rows": 0,
    }

    if unexpected:
        unexpected_mask = series.isin(unexpected)
        details["n_unexpected_rows"] = int(unexpected_mask.sum())

    if not unexpected and not missing_expected:
        return {
            "status": "PASS",
            "message": f"All values match expected domain ({len(expected)} values).",
            "details": details,
        }
    elif unexpected:
        return {
            "status": "FAIL",
            "message": (
                f"Found {len(unexpected)} unexpected value(s): "
                f"{sorted(str(v) for v in list(unexpected)[:5])}. "
                f"{details['n_unexpected_rows']:,} rows affected."
            ),
            "details": details,
        }
    else:
        # Only missing_expected (no unexpected) — domain is a subset
        return {
            "status": "WARN",
            "message": (
                f"Data covers {len(actual)}/{len(expected)} expected values. "
                f"Missing: {sorted(str(v) for v in list(missing_expected)[:5])}."
            ),
            "details": details,
        }


# ---------------------------------------------------------------------------
# DQ-1.2: Monotonic check
# ---------------------------------------------------------------------------

def check_monotonic(series, direction="increasing", strict=False):
    """Check if a series is monotonically increasing or decreasing.

    Useful for verifying sequential IDs, timestamps, or cumulative metrics.

    Args:
        series: pandas.Series to check.
        direction: ``"increasing"`` or ``"decreasing"``.
        strict: If True, requires strictly monotonic (no equal consecutive values).

    Returns:
        dict with keys: status, message, details
    """
    clean = series.dropna()

    if len(clean) < 2:
        return {
            "status": "WARN",
            "message": "Too few non-null values for monotonic check.",
            "details": {"n_values": len(clean)},
        }

    if direction == "increasing":
        is_monotonic = clean.is_monotonic_increasing if not strict else (
            clean.diff().dropna() > 0
        ).all()
    elif direction == "decreasing":
        is_monotonic = clean.is_monotonic_decreasing if not strict else (
            clean.diff().dropna() < 0
        ).all()
    else:
        raise ValueError(f"Unknown direction: {direction}. Use 'increasing' or 'decreasing'.")

    # Count violations
    if direction == "increasing":
        diffs = clean.diff().dropna()
        violations = diffs[diffs < 0] if not strict else diffs[diffs <= 0]
    else:
        diffs = clean.diff().dropna()
        violations = diffs[diffs > 0] if not strict else diffs[diffs >= 0]

    n_violations = len(violations)

    details = {
        "direction": direction,
        "strict": strict,
        "n_values": len(clean),
        "n_violations": n_violations,
        "first_violation_index": int(violations.index[0]) if n_violations > 0 else None,
    }

    if is_monotonic:
        return {
            "status": "PASS",
            "message": (
                f"Series is {'strictly ' if strict else ''}monotonically "
                f"{direction} ({len(clean):,} values)."
            ),
            "details": details,
        }
    else:
        return {
            "status": "FAIL",
            "message": (
                f"Series is NOT monotonically {direction}: "
                f"{n_violations:,} violation(s) found."
            ),
            "details": details,
        }


# ---------------------------------------------------------------------------
# Safe wrappers — student-friendly, never raise
# ---------------------------------------------------------------------------


def safe_check_temporal_coverage(df, date_col, freq="D", max_gap_tolerance=1):
    """Never-raise wrapper around check_temporal_coverage().

    Returns:
        dict: On success, the normal result dict. On error, a dict with
        status="ERROR", message describing what went wrong, and details=None.
    """
    try:
        return check_temporal_coverage(df, date_col, freq=freq,
                                       max_gap_tolerance=max_gap_tolerance)
    except Exception as e:
        return {
            "status": "ERROR",
            "message": f"Temporal coverage check failed: {e}",
            "details": None,
        }


def safe_check_value_domain(series, expected_values, allow_null=True):
    """Never-raise wrapper around check_value_domain().

    Returns:
        dict: On success, the normal result dict. On error, a dict with
        status="ERROR", message describing what went wrong, and details=None.
    """
    try:
        return check_value_domain(series, expected_values,
                                  allow_null=allow_null)
    except Exception as e:
        return {
            "status": "ERROR",
            "message": f"Value domain check failed: {e}",
            "details": None,
        }


def safe_check_monotonic(series, direction="increasing", strict=False):
    """Never-raise wrapper around check_monotonic().

    Returns:
        dict: On success, the normal result dict. On error, a dict with
        status="ERROR", message describing what went wrong, and details=None.
    """
    try:
        return check_monotonic(series, direction=direction, strict=strict)
    except Exception as e:
        return {
            "status": "ERROR",
            "message": f"Monotonic check failed: {e}",
            "details": None,
        }
