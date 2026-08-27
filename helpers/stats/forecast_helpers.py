"""
Time-series forecasting utilities for the AI Data Analyst.

Simple, interpretable forecasting methods that product analysts can understand
and explain to stakeholders. All functions return structured dicts with
forecasts, diagnostics, and human-readable interpretations.

Usage:
    from helpers.stats.forecast_helpers import (
        naive_forecast, detect_seasonality, exponential_smoothing,
    )

    # Quick baseline forecast using last observed value
    result = naive_forecast(daily_revenue, periods=14, method='last')
    print(result["interpretation"])

    # Check for weekly or monthly seasonality
    result = detect_seasonality(daily_signups)
    print(result["interpretation"])

    # Fit exponential smoothing with auto-tuned alpha
    result = exponential_smoothing(daily_revenue)
    print(f"Optimized alpha: {result['alpha']:.3f}")
    print(result["interpretation"])

    # Fit AND produce future values (holt-style continuation)
    result = exponential_smoothing(daily_revenue, forecast_periods=14)
    print(result["forecast"])  # Series with future DatetimeIndex
"""

import numpy as np
import pandas as pd
from scipy import optimize


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _prepare_series(series):
    """Clean a time series for forecasting: forward-fill NaN, drop leading NaN.

    Args:
        series: pandas Series (ideally with DatetimeIndex).

    Returns:
        pd.Series: Cleaned series with no NaN values.

    Raises:
        ValueError: If series is empty after cleaning.
    """
    s = series.copy()

    # Forward-fill interior gaps, then drop any remaining leading NaN
    s = s.ffill()
    s = s.dropna()

    if len(s) == 0:
        raise ValueError("Series is empty after cleaning (all NaN or no data).")

    return s


def _infer_freq(series):
    """Infer the frequency of a DatetimeIndex as a pd.DateOffset.

    Falls back to the median difference between consecutive timestamps.

    Args:
        series: pandas Series with DatetimeIndex.

    Returns:
        pd.DateOffset: Inferred frequency.
    """
    if hasattr(series.index, 'freq') and series.index.freq is not None:
        return series.index.freq

    if len(series) < 2:
        return pd.DateOffset(days=1)

    diffs = pd.Series(series.index).diff().dropna()
    median_diff = diffs.median()
    return median_diff


# ---------------------------------------------------------------------------
# Naive forecast (baseline methods)
# ---------------------------------------------------------------------------

def naive_forecast(series, periods=7, method='last', window=7,
                   seasonal_period=None):
    """Generate a simple baseline forecast using naive methods.

    These are intentionally simple -- use them as benchmarks to compare
    against more sophisticated approaches. If a fancy model cannot beat a
    naive forecast, it is not adding value.

    Args:
        series: pandas Series with DatetimeIndex.
        periods: Number of future periods to forecast (default 7).
        method: Forecasting method. One of:
            - 'last': Repeat the last observed value.
            - 'mean': Repeat the rolling mean of the last ``window`` values.
            - 'drift': Last value + average change per period * step.
            - 'seasonal_naive': Repeat the last full seasonal cycle. The
              cycle length comes from ``seasonal_period`` if given, otherwise
              it is inferred from the data's autocorrelation. If neither
              yields a cycle, a ValueError is raised -- there is no silent
              default, because a fabricated cycle produces a wrong forecast
              with no warning.
        window: Window size for the 'mean' method (default 7).
        seasonal_period: Seasonal cycle length for 'seasonal_naive'
            (e.g. 12 for annual seasonality on monthly data). Pass the
            ``dominant_period`` from ``detect_seasonality()``.

    Returns:
        dict with keys: forecast (Series with future DatetimeIndex), method,
        periods, seasonal_period (int or None -- the cycle actually used),
        interpretation.

    Raises:
        ValueError: For 'seasonal_naive' when no seasonal cycle is given or
            inferable, or when the cycle is longer than the series.
    """
    s = _prepare_series(series)
    freq = _infer_freq(s)
    n = len(s)
    used_cycle = None

    # Build future index
    last_idx = s.index[-1]
    future_index = pd.date_range(start=last_idx + freq, periods=periods, freq=freq)

    if method == 'last':
        last_val = float(s.iloc[-1])
        forecast_vals = np.full(periods, last_val)
        desc = (
            f"Naive 'last value' forecast: repeating {last_val:,.2f} "
            f"for {periods} periods. This assumes no trend or seasonality."
        )

    elif method == 'mean':
        effective_window = min(window, n)
        mean_val = float(s.iloc[-effective_window:].mean())
        forecast_vals = np.full(periods, mean_val)
        desc = (
            f"Naive 'mean' forecast: repeating rolling mean {mean_val:,.2f} "
            f"(window={effective_window}) for {periods} periods. "
            f"This smooths out recent noise but assumes no trend."
        )

    elif method == 'drift':
        first_val = float(s.iloc[0])
        last_val = float(s.iloc[-1])
        if n < 2:
            avg_change = 0.0
        else:
            avg_change = (last_val - first_val) / (n - 1)
        forecast_vals = np.array([
            last_val + avg_change * (i + 1) for i in range(periods)
        ])
        desc = (
            f"Naive 'drift' forecast: starting from {last_val:,.2f} "
            f"with average change of {avg_change:+,.4f} per period. "
            f"This extrapolates the overall trend linearly."
        )

    elif method == 'seasonal_naive':
        # Use the caller-provided cycle, else infer it from autocorrelation.
        # NO hardcoded fallback: a silently fabricated cycle (the old
        # default of 7 assumed daily grain) produces a wrong forecast with
        # no warning on any other grain.
        if seasonal_period is not None:
            cycle_len = int(seasonal_period)
        else:
            cycle_len = _infer_seasonal_cycle(s)
        if cycle_len is None or cycle_len < 2:
            raise ValueError(
                "seasonal_naive needs a seasonal cycle, but none was given "
                "and none could be inferred from the data. Run "
                "detect_seasonality() and pass "
                "seasonal_period=<dominant_period>, or use method='last', "
                "'mean', or 'drift' if the series is not seasonal."
            )
        if cycle_len > n:
            raise ValueError(
                f"seasonal_period={cycle_len} is longer than the series "
                f"({n} points). Need at least one full cycle of history."
            )
        used_cycle = cycle_len

        # Repeat the last full cycle
        last_cycle = s.iloc[-cycle_len:].values
        repeats = int(np.ceil(periods / cycle_len))
        tiled = np.tile(last_cycle, repeats)[:periods]
        forecast_vals = tiled
        desc = (
            f"Seasonal naive forecast: repeating the last {cycle_len}-period "
            f"cycle for {periods} periods. Assumes the pattern repeats exactly."
        )

    else:
        raise ValueError(
            f"Unknown method '{method}'. "
            "Choose 'last', 'mean', 'drift', or 'seasonal_naive'."
        )

    forecast = pd.Series(forecast_vals, index=future_index, name="forecast")

    return {
        "forecast": forecast,
        "method": method,
        "periods": periods,
        "seasonal_period": used_cycle,
        "interpretation": desc,
    }


def _infer_seasonal_cycle(series, max_period=None):
    """Infer the dominant seasonal cycle length from autocorrelation peaks.

    Args:
        series: pandas Series of numeric values.
        max_period: Maximum lag to check. Defaults to min(len(series)//2, 365).

    Returns:
        int or None: Dominant cycle length, or None if no clear seasonality.
    """
    n = len(series)
    if max_period is None:
        max_period = min(n // 2, 365)
    if max_period < 2 or n < 4:
        return None

    vals = series.values.astype(float)
    mean = np.mean(vals)
    var = np.var(vals)

    if var == 0:
        return None

    # Compute ACF for lags 1..max_period
    acf_vals = []
    for lag in range(1, max_period + 1):
        if lag >= n:
            break
        c = np.mean((vals[:n - lag] - mean) * (vals[lag:] - mean)) / var
        acf_vals.append(c)

    if len(acf_vals) == 0:
        return None

    acf_arr = np.array(acf_vals)
    threshold = 2.0 / np.sqrt(n)

    # Find peaks above threshold
    best_lag = None
    best_acf = threshold
    for i in range(1, len(acf_arr) - 1):
        if (acf_arr[i] > acf_arr[i - 1]
                and acf_arr[i] > acf_arr[i + 1]
                and acf_arr[i] > best_acf):
            best_acf = acf_arr[i]
            best_lag = i + 1  # lag is 1-indexed

    # The last computable lag can also be the dominant cycle (e.g. an annual
    # cycle on ~2 years of monthly data, where lag 12 is the final lag). An
    # interior-only scan can never crown it, so check the endpoint: it counts
    # as a peak when the ACF is still rising into it.
    last = len(acf_arr) - 1
    if (last >= 1
            and acf_arr[last] > acf_arr[last - 1]
            and acf_arr[last] > best_acf):
        best_acf = acf_arr[last]
        best_lag = last + 1

    return best_lag


# ---------------------------------------------------------------------------
# Seasonality detection (autocorrelation-based)
# ---------------------------------------------------------------------------

def detect_seasonality(series, max_period=365):
    """Detect seasonal patterns in a time series using autocorrelation.

    Computes the autocorrelation function (ACF) and looks for peaks above a
    significance threshold. Useful for determining whether weekly, monthly, or
    other cyclic patterns exist before choosing a forecasting method.

    Args:
        series: pandas Series with DatetimeIndex (daily or weekly data).
        max_period: Maximum lag to evaluate (default 365).

    Returns:
        dict with keys: has_seasonality (bool), dominant_period (int or None),
        acf_peaks (list of dicts with lag and acf_value), strength (float 0-1,
        max ACF peak value), interpretation (str).
    """
    s = _prepare_series(series)
    n = len(s)

    # Need enough data for meaningful autocorrelation
    if n < 4:
        return {
            "has_seasonality": False,
            "dominant_period": None,
            "acf_peaks": [],
            "strength": 0.0,
            "interpretation": (
                f"Series too short ({n} observations) for seasonality detection. "
                f"Need at least 4 data points."
            ),
        }

    vals = s.values.astype(float)
    mean = np.mean(vals)
    var = np.var(vals)

    # Constant series -- no seasonality
    if var == 0:
        return {
            "has_seasonality": False,
            "dominant_period": None,
            "acf_peaks": [],
            "strength": 0.0,
            "interpretation": "Series is constant -- no seasonality possible.",
        }

    effective_max = min(max_period, n // 2)

    # Compute ACF for each lag
    acf_vals = []
    for lag in range(1, effective_max + 1):
        c = np.mean((vals[:n - lag] - mean) * (vals[lag:] - mean)) / var
        acf_vals.append(c)

    if len(acf_vals) == 0:
        return {
            "has_seasonality": False,
            "dominant_period": None,
            "acf_peaks": [],
            "strength": 0.0,
            "interpretation": "Not enough data for the requested max_period.",
        }

    acf_arr = np.array(acf_vals)
    threshold = 2.0 / np.sqrt(n)

    # Find all peaks (local maxima) above significance threshold
    peaks = []
    for i in range(1, len(acf_arr) - 1):
        if (acf_arr[i] > acf_arr[i - 1]
                and acf_arr[i] > acf_arr[i + 1]
                and acf_arr[i] > threshold):
            peaks.append({
                "lag": i + 1,  # lag is 1-indexed
                "acf_value": float(acf_arr[i]),
            })

    # Include the final lag as a candidate peak. With n observations only
    # n//2 lags are computable, so the most common business cycle can land
    # exactly on the last lag (annual cycle on monthly data with n < ~26:
    # lag 12 IS the last element). An interior-only scan structurally cannot
    # return it, silently missing strong seasonality. The endpoint qualifies
    # when the ACF rises into it and clears the significance threshold.
    last = len(acf_arr) - 1
    if (last >= 1
            and acf_arr[last] > acf_arr[last - 1]
            and acf_arr[last] > threshold):
        peaks.append({
            "lag": last + 1,
            "acf_value": float(acf_arr[last]),
        })

    # Sort peaks by ACF value descending
    peaks.sort(key=lambda x: x["acf_value"], reverse=True)

    has_seasonality = len(peaks) > 0
    dominant_period = peaks[0]["lag"] if has_seasonality else None
    strength = float(peaks[0]["acf_value"]) if has_seasonality else 0.0

    # Build interpretation
    if not has_seasonality:
        desc = (
            f"No significant seasonal pattern detected (threshold={threshold:.3f}). "
            f"Analyzed {effective_max} lags on {n} observations."
        )
    else:
        top_peaks_str = ", ".join(
            f"lag {p['lag']} (ACF={p['acf_value']:.3f})"
            for p in peaks[:3]
        )
        strength_label = (
            "strong" if strength > 0.5
            else "moderate" if strength > 0.3
            else "weak"
        )
        desc = (
            f"Detected {strength_label} seasonality with dominant period of "
            f"{dominant_period} time steps (ACF={strength:.3f}). "
            f"Top peaks: {top_peaks_str}."
        )

    return {
        "has_seasonality": has_seasonality,
        "dominant_period": dominant_period,
        "acf_peaks": peaks,
        "strength": strength,
        "interpretation": desc,
    }


# ---------------------------------------------------------------------------
# Exponential smoothing (single, double, and Holt-Winters additive)
# ---------------------------------------------------------------------------

def exponential_smoothing(series, alpha=None, beta=None, seasonal_period=None,
                          forecast_periods=None):
    """Fit an exponential smoothing model to a time series.

    Implements three variants depending on the parameters provided:
    - **Simple (single)**: Only ``alpha`` -- smooths the level.
    - **Holt's linear trend (double)**: ``alpha`` + ``beta`` -- smooths level
      and trend.
    - **Holt-Winters additive**: ``alpha`` + ``beta`` + ``seasonal_period`` --
      smooths level, trend, and additive seasonal component.

    Implemented from scratch (no statsmodels) so students can see exactly
    what is happening at each step.

    Args:
        series: pandas Series with DatetimeIndex.
        alpha: Smoothing parameter for level (0-1). If None, optimized
            automatically by minimizing MSE.
        beta: Smoothing parameter for trend (0-1). If None and no
            seasonal_period, uses simple exponential smoothing. If provided,
            enables Holt's linear trend.
        seasonal_period: Length of the seasonal cycle. If provided along with
            beta, enables Holt-Winters additive seasonality.
        forecast_periods: If set (int >= 1), also produce future values by
            extrapolating from the final fitted state (holt-style
            continuation): flat at the last level for simple smoothing,
            level + trend * h for Holt, level + trend * h + the matching
            seasonal component for Holt-Winters.

    Returns:
        dict with keys: fitted (Series, same index as input), alpha (float),
        beta (float or None), seasonal_period (int or None), residuals
        (Series), mse (float), mae (float), interpretation (str),
        final_level (float), final_trend (float or None), and forecast
        (Series with future DatetimeIndex if ``forecast_periods`` was given,
        else None).
    """
    s = _prepare_series(series)
    vals = s.values.astype(float)
    n = len(s)

    if n < 2:
        raise ValueError(
            "Need at least 2 observations for exponential smoothing."
        )

    if seasonal_period is not None and beta is None:
        # Holt-Winters requires both beta and seasonal_period
        beta = 0.1  # default trend smoothing if only seasonal_period given

    # Determine which variant to use
    if seasonal_period is not None:
        variant = "holt_winters"
        if n < 2 * seasonal_period:
            raise ValueError(
                f"Need at least {2 * seasonal_period} observations for "
                f"Holt-Winters with seasonal_period={seasonal_period}, "
                f"but only have {n}."
            )
    elif beta is not None:
        variant = "holt"
    else:
        variant = "simple"

    # ---- Optimization or direct fit ----
    if alpha is None:
        alpha = _optimize_alpha(vals, variant, beta, seasonal_period)

    if beta is not None and variant in ("holt", "holt_winters"):
        # Optimize beta if a default was set
        pass  # keep the provided or defaulted beta

    # ---- Fit the model ----
    if variant == "simple":
        fitted_vals, state = _fit_simple(vals, alpha)
        model_name = "Simple Exponential Smoothing"

    elif variant == "holt":
        fitted_vals, state = _fit_holt(vals, alpha, beta)
        model_name = "Holt's Linear Trend"

    elif variant == "holt_winters":
        fitted_vals, state = _fit_holt_winters(vals, alpha, beta, seasonal_period)
        model_name = f"Holt-Winters Additive (period={seasonal_period})"

    fitted = pd.Series(fitted_vals, index=s.index, name="fitted")
    residuals = s - fitted
    mse = float(np.mean(residuals.values ** 2))
    mae = float(np.mean(np.abs(residuals.values)))

    # ---- Future values (holt-style continuation from the final state) ----
    forecast = None
    if forecast_periods is not None:
        h_total = int(forecast_periods)
        if h_total < 1:
            raise ValueError("forecast_periods must be a positive integer.")
        freq = _infer_freq(s)
        future_index = pd.date_range(
            start=s.index[-1] + freq, periods=h_total, freq=freq
        )
        level = state["level"]
        trend = state.get("trend", 0.0)
        future_vals = np.empty(h_total)
        for h in range(1, h_total + 1):
            val = level + trend * h
            if variant == "holt_winters":
                m = state["m"]
                season = state["season"]
                # season indices n-1 .. n+m-2 hold the latest estimate for
                # each of the m phases; wrap future steps back into that
                # window (subtracting m preserves the phase).
                idx = (n - 1) + h
                while idx > n + m - 2:
                    idx -= m
                val += season[idx]
            future_vals[h - 1] = val
        forecast = pd.Series(future_vals, index=future_index, name="forecast")

    desc = (
        f"{model_name} with alpha={alpha:.3f}"
        + (f", beta={beta:.3f}" if beta is not None else "")
        + (f", seasonal_period={seasonal_period}" if seasonal_period else "")
        + f". MSE={mse:,.4f}, MAE={mae:,.4f}."
        + (
            f" Forecast: {len(forecast)} future periods from the final "
            f"fitted state." if forecast is not None else ""
        )
    )

    return {
        "fitted": fitted,
        "alpha": float(alpha),
        "beta": float(beta) if beta is not None else None,
        "seasonal_period": int(seasonal_period) if seasonal_period else None,
        "residuals": residuals,
        "mse": mse,
        "mae": mae,
        "final_level": float(state["level"]),
        "final_trend": (
            float(state["trend"]) if "trend" in state else None
        ),
        "forecast": forecast,
        "interpretation": desc,
    }


# ---------------------------------------------------------------------------
# Exponential smoothing internals
# ---------------------------------------------------------------------------

def _fit_simple(vals, alpha):
    """Single exponential smoothing (level only).

    Args:
        vals: 1D numpy array of observed values.
        alpha: Smoothing parameter (0-1).

    Returns:
        tuple: (fitted values array, final state dict with ``level``).
    """
    n = len(vals)
    fitted = np.zeros(n)
    fitted[0] = vals[0]  # initialize level to first observation

    for t in range(1, n):
        fitted[t] = alpha * vals[t] + (1 - alpha) * fitted[t - 1]

    return fitted, {"level": fitted[-1]}


def _fit_holt(vals, alpha, beta):
    """Holt's linear trend (double exponential smoothing).

    Args:
        vals: 1D numpy array of observed values.
        alpha: Smoothing parameter for level (0-1).
        beta: Smoothing parameter for trend (0-1).

    Returns:
        tuple: (fitted values array, final state dict with ``level`` and
        ``trend``).
    """
    n = len(vals)
    level = np.zeros(n)
    trend = np.zeros(n)
    fitted = np.zeros(n)

    # Initialize
    level[0] = vals[0]
    trend[0] = vals[1] - vals[0] if n > 1 else 0.0
    fitted[0] = level[0]

    for t in range(1, n):
        level[t] = alpha * vals[t] + (1 - alpha) * (level[t - 1] + trend[t - 1])
        trend[t] = beta * (level[t] - level[t - 1]) + (1 - beta) * trend[t - 1]
        fitted[t] = level[t]

    return fitted, {"level": level[-1], "trend": trend[-1]}


def _fit_holt_winters(vals, alpha, beta, seasonal_period):
    """Holt-Winters additive seasonal smoothing.

    Args:
        vals: 1D numpy array of observed values.
        alpha: Smoothing parameter for level (0-1).
        beta: Smoothing parameter for trend (0-1).
        seasonal_period: Length of one seasonal cycle.

    Returns:
        tuple: (fitted values array, final state dict with ``level``,
        ``trend``, ``season`` array, and ``m``).
    """
    n = len(vals)
    m = seasonal_period

    level = np.zeros(n)
    trend = np.zeros(n)
    season = np.zeros(n + m)  # extra room for initialization
    fitted = np.zeros(n)

    # Initialize level and trend from the first cycle
    level[0] = np.mean(vals[:m])
    trend[0] = (np.mean(vals[m:2 * m]) - np.mean(vals[:m])) / m

    # Initialize seasonal components from first cycle
    for i in range(m):
        season[i] = vals[i] - level[0]

    fitted[0] = level[0] + season[0]

    for t in range(1, n):
        level[t] = alpha * (vals[t] - season[t - 1]) + (1 - alpha) * (level[t - 1] + trend[t - 1])
        trend[t] = beta * (level[t] - level[t - 1]) + (1 - beta) * trend[t - 1]

        # Seasonal index wraps around: update season[t + m - 1] using the
        # current deviation.  The "gamma" parameter is fixed at 0.1 to keep
        # the API simple (alpha + beta is already enough knobs for students).
        gamma = 0.1
        season[t + m - 1] = gamma * (vals[t] - level[t]) + (1 - gamma) * season[t - 1]

        fitted[t] = level[t] + season[t]

    return fitted, {
        "level": level[-1],
        "trend": trend[-1],
        "season": season,
        "m": m,
    }


def _optimize_alpha(vals, variant, beta=None, seasonal_period=None):
    """Find the alpha that minimizes MSE using bounded scalar optimization.

    Args:
        vals: 1D numpy array of observed values.
        variant: One of 'simple', 'holt', 'holt_winters'.
        beta: Trend smoothing parameter (for holt/holt_winters).
        seasonal_period: Seasonal cycle length (for holt_winters).

    Returns:
        float: Optimized alpha value.
    """
    def objective(alpha):
        try:
            if variant == "simple":
                fitted, _ = _fit_simple(vals, alpha)
            elif variant == "holt":
                fitted, _ = _fit_holt(vals, alpha, beta)
            elif variant == "holt_winters":
                fitted, _ = _fit_holt_winters(vals, alpha, beta, seasonal_period)
            else:
                return np.inf
            residuals = vals - fitted
            return float(np.mean(residuals ** 2))
        except Exception:
            return np.inf

    result = optimize.minimize_scalar(
        objective,
        bounds=(0.01, 0.99),
        method='bounded',
    )

    return float(result.x)
