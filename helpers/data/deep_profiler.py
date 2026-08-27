"""
Deep Profiler — advanced data quality and statistical profiling.

Builds on schema_profiler for deeper analysis: distribution shapes,
temporal patterns, correlations, and anomaly detection.

Usage:
    from helpers.data.deep_profiler import (
        profile_distributions, profile_temporal_patterns,
        profile_correlations, profile_completeness, profile_anomalies,
    )

    # Distribution shape analysis
    dist = profile_distributions(df)

    # Temporal coverage and trend analysis
    temporal = profile_temporal_patterns(df, "order_date", freq="D")

    # Significant correlations
    corrs = profile_correlations(df, threshold=0.5)

    # Completeness assessment
    comp = profile_completeness(df)

    # Rolling-window anomaly detection
    anom = profile_anomalies(df, date_col="order_date", window=14)
"""

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Distribution profiling
# ---------------------------------------------------------------------------

def profile_distributions(df, numeric_cols=None):
    """Profile distribution shape for all numeric columns.

    Computes descriptive statistics, percentiles, skewness, kurtosis,
    and suggests the most likely distribution shape and recommended
    transform for each numeric column.

    Args:
        df: DataFrame to profile.
        numeric_cols: Optional list of columns. If None, auto-detect numeric.

    Returns:
        list of dicts, one per column:
        [
            {
                "column": str,
                "n_values": int,
                "n_unique": int,
                "mean": float, "median": float, "std": float,
                "skewness": float, "kurtosis": float,
                "p1": float, "p5": float, "p25": float, "p75": float,
                "p95": float, "p99": float,
                "iqr": float,
                "n_outliers_iqr": int,
                "shape": str,
                "recommended_transform": str or None,
            }
        ]
    """
    if numeric_cols is None:
        numeric_cols = df.select_dtypes(include="number").columns.tolist()

    results = []
    for col in numeric_cols:
        if col not in df.columns:
            continue

        series = df[col].dropna()
        n_values = len(series)
        if n_values == 0:
            results.append({
                "column": col,
                "n_values": 0,
                "n_unique": 0,
                "mean": None, "median": None, "std": None,
                "skewness": None, "kurtosis": None,
                "p1": None, "p5": None, "p25": None, "p75": None,
                "p95": None, "p99": None,
                "iqr": None,
                "n_outliers_iqr": 0,
                "shape": "empty",
                "recommended_transform": None,
            })
            continue

        try:
            n_unique = int(series.nunique())
            mean = float(series.mean())
            median = float(series.median())
            std = float(series.std())
            skewness = float(series.skew())
            kurtosis = float(series.kurtosis())

            p1 = float(series.quantile(0.01))
            p5 = float(series.quantile(0.05))
            p25 = float(series.quantile(0.25))
            p75 = float(series.quantile(0.75))
            p95 = float(series.quantile(0.95))
            p99 = float(series.quantile(0.99))

            iqr = p75 - p25

            # Count IQR outliers
            lower_fence = p25 - 1.5 * iqr
            upper_fence = p75 + 1.5 * iqr
            n_outliers_iqr = int(((series < lower_fence) | (series > upper_fence)).sum())

            # Classify shape
            shape = _classify_shape(series, skewness, kurtosis, n_unique)

            # Recommend transform
            recommended_transform = _recommend_transform(series, skewness)

            results.append({
                "column": col,
                "n_values": n_values,
                "n_unique": n_unique,
                "mean": mean,
                "median": median,
                "std": std,
                "skewness": skewness,
                "kurtosis": kurtosis,
                "p1": p1, "p5": p5, "p25": p25, "p75": p75,
                "p95": p95, "p99": p99,
                "iqr": iqr,
                "n_outliers_iqr": n_outliers_iqr,
                "shape": shape,
                "recommended_transform": recommended_transform,
            })

        except Exception as exc:
            # Graceful degradation — return what we can
            results.append({
                "column": col,
                "n_values": n_values,
                "n_unique": 0,
                "mean": None, "median": None, "std": None,
                "skewness": None, "kurtosis": None,
                "p1": None, "p5": None, "p25": None, "p75": None,
                "p95": None, "p99": None,
                "iqr": None,
                "n_outliers_iqr": 0,
                "shape": "unknown",
                "recommended_transform": None,
            })

    return results


def _classify_shape(series, skewness, kurtosis, n_unique):
    """Classify the distribution shape from summary statistics.

    Uses skewness, kurtosis, and a simple bimodality check to assign
    one of: normal, right-skewed, left-skewed, bimodal, uniform,
    heavy-tailed.
    """
    # Uniform: very low kurtosis and low skew
    if abs(skewness) < 0.5 and kurtosis < -1.0:
        return "uniform"

    # Heavy-tailed: high excess kurtosis
    if kurtosis > 3.0:
        return "heavy-tailed"

    # Bimodal heuristic: check if the histogram has two peaks
    # Use a simple test — if the dip between modes is deep
    if n_unique > 10:
        try:
            hist_counts, bin_edges = np.histogram(series, bins=min(50, n_unique))
            if _has_two_peaks(hist_counts):
                return "bimodal"
        except Exception:
            pass

    # Skewness-based classification
    if skewness > 1.0:
        return "right-skewed"
    elif skewness < -1.0:
        return "left-skewed"

    return "normal"


def _has_two_peaks(counts):
    """Simple peak detection for bimodality.

    Checks if the histogram counts have at least two local maxima
    with a valley between them that drops below 60% of the lower peak.
    """
    if len(counts) < 5:
        return False

    # Smooth with a 3-bin rolling mean to reduce noise
    smoothed = np.convolve(counts, np.ones(3) / 3, mode="same")

    peaks = []
    for i in range(1, len(smoothed) - 1):
        if smoothed[i] > smoothed[i - 1] and smoothed[i] > smoothed[i + 1]:
            peaks.append((i, smoothed[i]))

    if len(peaks) < 2:
        return False

    # Check if valley between two highest peaks is deep enough
    peaks_sorted = sorted(peaks, key=lambda p: p[1], reverse=True)[:2]
    left_idx = min(peaks_sorted[0][0], peaks_sorted[1][0])
    right_idx = max(peaks_sorted[0][0], peaks_sorted[1][0])
    valley = min(smoothed[left_idx:right_idx + 1])
    lower_peak = min(peaks_sorted[0][1], peaks_sorted[1][1])

    return valley < lower_peak * 0.6


def _recommend_transform(series, skewness):
    """Suggest a transform to normalise the distribution.

    Returns "log" for right-skewed with all positive values,
    "sqrt" for moderate right skew, or None.
    """
    if abs(skewness) < 1.0:
        return None

    if skewness > 1.0:
        # Log works for strictly positive data
        if series.min() > 0:
            return "log"
        # Sqrt works for non-negative data
        if series.min() >= 0:
            return "sqrt"

    return None


# ---------------------------------------------------------------------------
# Temporal pattern profiling
# ---------------------------------------------------------------------------

def profile_temporal_patterns(df, date_col, metric_cols=None, freq="D"):
    """Analyze temporal patterns in the data.

    Checks date coverage, detects gaps, day-of-week and monthly patterns,
    trend direction, and basic seasonality.

    Args:
        df: DataFrame with date column.
        date_col: Name of the date column.
        metric_cols: Optional list of metric columns. If None, auto-detect numeric.
        freq: Expected frequency ("D" daily, "W" weekly, "M" monthly).

    Returns:
        dict:
        {
            "date_range": {"min": str, "max": str},
            "expected_periods": int,
            "actual_periods": int,
            "coverage_pct": float,
            "gaps": [{"start": str, "end": str, "n_missing": int}],
            "day_of_week_pattern": dict (mean by day of week, for daily data),
            "monthly_pattern": dict (mean by month),
            "trend": str ("increasing", "decreasing", "stable", "volatile"),
            "seasonality_detected": bool,
        }
    """
    if date_col not in df.columns:
        return {
            "date_range": None,
            "expected_periods": 0,
            "actual_periods": 0,
            "coverage_pct": 0.0,
            "gaps": [],
            "day_of_week_pattern": {},
            "monthly_pattern": {},
            "trend": "unknown",
            "seasonality_detected": False,
        }

    if metric_cols is None:
        metric_cols = df.select_dtypes(include="number").columns.tolist()

    # Parse dates
    dates = pd.to_datetime(df[date_col], errors="coerce")
    valid_mask = dates.notna()
    dates = dates[valid_mask]
    data = df.loc[valid_mask].copy()
    data["_parsed_date"] = dates

    if len(dates) == 0:
        return {
            "date_range": None,
            "expected_periods": 0,
            "actual_periods": 0,
            "coverage_pct": 0.0,
            "gaps": [],
            "day_of_week_pattern": {},
            "monthly_pattern": {},
            "trend": "unknown",
            "seasonality_detected": False,
        }

    date_min = dates.min()
    date_max = dates.max()
    date_range = {
        "min": str(date_min.date()) if hasattr(date_min, "date") else str(date_min),
        "max": str(date_max.date()) if hasattr(date_max, "date") else str(date_max),
    }

    # Build expected date spine
    try:
        expected = pd.date_range(start=date_min, end=date_max, freq=freq)
        expected_periods = len(expected)
    except Exception:
        expected_periods = 0
        expected = pd.DatetimeIndex([])

    # Actual distinct periods
    if freq == "D":
        actual_dates = dates.dt.date.unique()
    elif freq == "W":
        actual_dates = dates.dt.to_period("W").unique()
    elif freq == "M":
        actual_dates = dates.dt.to_period("M").unique()
    else:
        actual_dates = dates.dt.date.unique()

    actual_periods = len(actual_dates)
    coverage_pct = round(
        100.0 * actual_periods / expected_periods, 2
    ) if expected_periods > 0 else 0.0

    # Find gaps (only for daily frequency — most useful case)
    gaps = []
    if freq == "D" and expected_periods > 0:
        try:
            expected_set = set(expected.date)
            actual_set = set(pd.to_datetime(pd.Series(list(actual_dates))).dt.date)
            missing = sorted(expected_set - actual_set)
            gaps = _group_consecutive_dates(missing)
        except Exception:
            pass

    # Day-of-week pattern (for daily data)
    day_of_week_pattern = {}
    if freq == "D" and metric_cols:
        primary_metric = metric_cols[0]
        if primary_metric in data.columns:
            try:
                dow = data.copy()
                dow["_dow"] = data["_parsed_date"].dt.day_name()
                dow_means = dow.groupby("_dow")[primary_metric].mean()
                day_of_week_pattern = {
                    str(k): round(float(v), 4) for k, v in dow_means.items()
                }
            except Exception:
                pass

    # Monthly pattern
    monthly_pattern = {}
    if metric_cols:
        primary_metric = metric_cols[0]
        if primary_metric in data.columns:
            try:
                data_m = data.copy()
                data_m["_month"] = data["_parsed_date"].dt.month
                month_means = data_m.groupby("_month")[primary_metric].mean()
                day_names = {
                    1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr",
                    5: "May", 6: "Jun", 7: "Jul", 8: "Aug",
                    9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec",
                }
                monthly_pattern = {
                    day_names.get(int(k), str(k)): round(float(v), 4)
                    for k, v in month_means.items()
                }
            except Exception:
                pass

    # Trend detection
    trend = _detect_trend(data, date_col="_parsed_date", metric_cols=metric_cols)

    # Seasonality detection (simple: check if monthly pattern varies >20%)
    seasonality_detected = _detect_seasonality(monthly_pattern)

    return {
        "date_range": date_range,
        "expected_periods": expected_periods,
        "actual_periods": actual_periods,
        "coverage_pct": coverage_pct,
        "gaps": gaps,
        "day_of_week_pattern": day_of_week_pattern,
        "monthly_pattern": monthly_pattern,
        "trend": trend,
        "seasonality_detected": seasonality_detected,
    }


def _group_consecutive_dates(missing_dates):
    """Group consecutive missing dates into gap ranges.

    Args:
        missing_dates: Sorted list of date objects.

    Returns:
        list of {"start": str, "end": str, "n_missing": int}
    """
    if not missing_dates:
        return []

    from datetime import timedelta

    gaps = []
    start = missing_dates[0]
    prev = missing_dates[0]

    for d in missing_dates[1:]:
        if (d - prev).days <= 1:
            prev = d
        else:
            gaps.append({
                "start": str(start),
                "end": str(prev),
                "n_missing": (prev - start).days + 1,
            })
            start = d
            prev = d

    # Final gap
    gaps.append({
        "start": str(start),
        "end": str(prev),
        "n_missing": (prev - start).days + 1,
    })

    return gaps


def _detect_trend(data, date_col, metric_cols):
    """Detect overall trend direction using a simple linear fit.

    Returns one of: "increasing", "decreasing", "stable", "volatile".
    """
    if not metric_cols:
        return "unknown"

    primary_metric = metric_cols[0]
    if primary_metric not in data.columns or date_col not in data.columns:
        return "unknown"

    try:
        sorted_data = data.sort_values(date_col).copy()
        values = sorted_data[primary_metric].dropna().values
        if len(values) < 5:
            return "unknown"

        # Simple linear regression via polyfit
        x = np.arange(len(values), dtype=float)
        coefficients = np.polyfit(x, values, 1)
        slope = coefficients[0]

        # Normalise slope by the mean to get a relative trend
        mean_val = np.mean(values)
        if mean_val == 0:
            return "stable"

        relative_slope = slope / abs(mean_val)

        # Check volatility: coefficient of variation of residuals
        fitted = np.polyval(coefficients, x)
        residuals = values - fitted
        cv = np.std(residuals) / abs(mean_val) if mean_val != 0 else 0

        if cv > 0.5:
            return "volatile"
        elif relative_slope > 0.01:
            return "increasing"
        elif relative_slope < -0.01:
            return "decreasing"
        else:
            return "stable"

    except Exception:
        return "unknown"


def _detect_seasonality(monthly_pattern):
    """Check if monthly pattern shows meaningful seasonal variation.

    Returns True if the coefficient of variation across months exceeds 20%.
    """
    if not monthly_pattern or len(monthly_pattern) < 3:
        return False

    try:
        values = list(monthly_pattern.values())
        mean_val = np.mean(values)
        if mean_val == 0:
            return False

        cv = np.std(values) / abs(mean_val)
        return cv > 0.2

    except Exception:
        return False


# ---------------------------------------------------------------------------
# Correlation profiling
# ---------------------------------------------------------------------------

def profile_correlations(df, numeric_cols=None, threshold=0.5):
    """Find significant correlations between numeric columns.

    Computes the Pearson correlation matrix and returns pairs whose
    absolute correlation exceeds the threshold, sorted by strength.

    Args:
        df: DataFrame.
        numeric_cols: Optional list. If None, auto-detect.
        threshold: Minimum absolute correlation to report (default 0.5).

    Returns:
        list of dicts, sorted by abs correlation descending:
        [
            {
                "col_a": str, "col_b": str,
                "correlation": float, "abs_correlation": float,
                "strength": str ("weak", "moderate", "strong", "very_strong"),
                "direction": str ("positive", "negative"),
            }
        ]
    """
    if numeric_cols is None:
        numeric_cols = df.select_dtypes(include="number").columns.tolist()

    if len(numeric_cols) < 2:
        return []

    try:
        corr_matrix = df[numeric_cols].corr()
    except Exception:
        return []

    results = []
    seen = set()

    for i, col_a in enumerate(numeric_cols):
        for j, col_b in enumerate(numeric_cols):
            if i >= j:
                continue  # Skip diagonal and lower triangle
            pair_key = (col_a, col_b)
            if pair_key in seen:
                continue
            seen.add(pair_key)

            try:
                corr_val = float(corr_matrix.loc[col_a, col_b])
            except Exception:
                continue

            if pd.isna(corr_val):
                continue

            abs_corr = abs(corr_val)
            if abs_corr < threshold:
                continue

            # Classify strength
            if abs_corr >= 0.9:
                strength = "very_strong"
            elif abs_corr >= 0.7:
                strength = "strong"
            elif abs_corr >= 0.5:
                strength = "moderate"
            else:
                strength = "weak"

            direction = "positive" if corr_val > 0 else "negative"

            results.append({
                "col_a": col_a,
                "col_b": col_b,
                "correlation": round(corr_val, 4),
                "abs_correlation": round(abs_corr, 4),
                "strength": strength,
                "direction": direction,
            })

    results.sort(key=lambda r: r["abs_correlation"], reverse=True)
    return results


# ---------------------------------------------------------------------------
# Completeness profiling
# ---------------------------------------------------------------------------

def profile_completeness(df):
    """Assess completeness of each column.

    For every column in the DataFrame, counts nulls, zeros (numeric),
    empty strings (object/string), and flags constant columns.

    Args:
        df: DataFrame.

    Returns:
        list of dicts:
        [
            {
                "column": str,
                "total_rows": int,
                "non_null": int,
                "null_count": int,
                "null_pct": float,
                "status": str ("COMPLETE", "GOOD", "WARNING", "CRITICAL"),
                "zero_count": int (for numeric),
                "empty_string_count": int (for string),
                "constant": bool,
            }
        ]
    """
    total_rows = len(df)
    results = []

    for col in df.columns:
        series = df[col]
        null_count = int(series.isnull().sum())
        non_null = total_rows - null_count
        null_pct = round(100.0 * null_count / total_rows, 2) if total_rows > 0 else 0.0

        # Classify status
        if null_pct == 0:
            status = "COMPLETE"
        elif null_pct < 5:
            status = "GOOD"
        elif null_pct < 50:
            status = "WARNING"
        else:
            status = "CRITICAL"

        # Zero count (numeric only)
        zero_count = 0
        if pd.api.types.is_numeric_dtype(series):
            try:
                zero_count = int((series == 0).sum())
            except Exception:
                pass

        # Empty string count (string/object only)
        empty_string_count = 0
        if pd.api.types.is_string_dtype(series) or pd.api.types.is_object_dtype(series):
            try:
                empty_string_count = int(
                    series.dropna().astype(str).str.strip().eq("").sum()
                )
            except Exception:
                pass

        # Constant check
        try:
            constant = bool(series.dropna().nunique() <= 1) if non_null > 0 else True
        except Exception:
            constant = False

        results.append({
            "column": col,
            "total_rows": total_rows,
            "non_null": non_null,
            "null_count": null_count,
            "null_pct": null_pct,
            "status": status,
            "zero_count": zero_count,
            "empty_string_count": empty_string_count,
            "constant": constant,
        })

    return results


# ---------------------------------------------------------------------------
# Anomaly profiling
# ---------------------------------------------------------------------------

def profile_anomalies(df, date_col=None, metric_cols=None, window=14, threshold=2.0):
    """Detect anomalies across multiple metrics using rolling statistics.

    Wraps the anomaly_scan logic from the data-quality-check skill into
    a reusable function that handles multiple metrics.

    IMPORTANT: The input DataFrame should be pre-aggregated to
    daily/weekly granularity. Do NOT run on raw event rows.

    Args:
        df: DataFrame (pre-aggregated to daily/weekly).
        date_col: Date column name (required for time-series anomaly detection).
        metric_cols: List of metric columns. If None, auto-detect numeric.
        window: Rolling window size.
        threshold: Number of std devs for anomaly band.

    Returns:
        dict:
        {
            "metrics_scanned": int,
            "total_anomalies": int,
            "by_metric": [
                {
                    "metric": str,
                    "n_anomalies": int,
                    "spikes": [{"date": str, "value": float, "pct_above": float}],
                    "drops": [{"date": str, "value": float, "pct_below": float}],
                }
            ],
            "summary": str,
        }
    """
    if metric_cols is None:
        metric_cols = df.select_dtypes(include="number").columns.tolist()

    if date_col is None or date_col not in df.columns:
        return {
            "metrics_scanned": 0,
            "total_anomalies": 0,
            "by_metric": [],
            "summary": "No date column provided or found; cannot run anomaly detection.",
        }

    # Parse and sort by date
    try:
        ts = df.copy()
        ts[date_col] = pd.to_datetime(ts[date_col], errors="coerce")
        ts = ts.dropna(subset=[date_col]).sort_values(date_col)
    except Exception:
        return {
            "metrics_scanned": 0,
            "total_anomalies": 0,
            "by_metric": [],
            "summary": "Could not parse date column for anomaly detection.",
        }

    by_metric = []
    total_anomalies = 0

    for metric in metric_cols:
        if metric not in ts.columns:
            continue

        try:
            result = _scan_single_metric(ts, date_col, metric, window, threshold)
            by_metric.append(result)
            total_anomalies += result["n_anomalies"]
        except Exception:
            by_metric.append({
                "metric": metric,
                "n_anomalies": 0,
                "spikes": [],
                "drops": [],
            })

    # Build summary
    metrics_scanned = len(by_metric)
    if total_anomalies == 0:
        summary = (
            f"Scanned {metrics_scanned} metric(s). "
            "No anomalies detected — all metrics appear stable."
        )
    else:
        anomaly_parts = []
        for m in by_metric:
            if m["n_anomalies"] > 0:
                anomaly_parts.append(
                    f"{m['metric']}: {len(m['spikes'])} spike(s), "
                    f"{len(m['drops'])} drop(s)"
                )
        summary = (
            f"Scanned {metrics_scanned} metric(s), "
            f"found {total_anomalies} anomalie(s). "
            + "; ".join(anomaly_parts)
        )

    return {
        "metrics_scanned": metrics_scanned,
        "total_anomalies": total_anomalies,
        "by_metric": by_metric,
        "summary": summary,
    }


def _scan_single_metric(ts, date_col, metric_col, window, threshold):
    """Run anomaly detection on a single metric column.

    Uses rolling mean +/- (threshold * rolling std) bands.
    """
    rolling_mean = ts[metric_col].rolling(window, min_periods=3).mean()
    rolling_std = ts[metric_col].rolling(window, min_periods=3).std()
    upper = rolling_mean + threshold * rolling_std
    lower = rolling_mean - threshold * rolling_std

    spikes = []
    drops = []

    for idx in ts.index:
        val = ts.loc[idx, metric_col]
        mean_val = rolling_mean.loc[idx]
        upper_val = upper.loc[idx]
        lower_val = lower.loc[idx]
        date_val = ts.loc[idx, date_col]

        if pd.isna(upper_val) or pd.isna(val):
            continue

        date_str = (
            str(date_val.date()) if hasattr(date_val, "date") else str(date_val)
        )

        if val > upper_val and mean_val != 0:
            pct_above = round(
                100.0 * (val - mean_val) / abs(mean_val), 1
            )
            spikes.append({
                "date": date_str,
                "value": round(float(val), 4),
                "pct_above": pct_above,
            })
        elif val < lower_val and mean_val != 0:
            pct_below = round(
                100.0 * (mean_val - val) / abs(mean_val), 1
            )
            drops.append({
                "date": date_str,
                "value": round(float(val), 4),
                "pct_below": pct_below,
            })

    return {
        "metric": metric_col,
        "n_anomalies": len(spikes) + len(drops),
        "spikes": spikes,
        "drops": drops,
    }
