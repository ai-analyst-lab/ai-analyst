"""
Effect size calculations for experiment interpretation.

Separates statistical significance from practical significance.
"""

import math

import numpy as np
import pandas as pd


def cohens_d(control, treatment):
    """Compute Cohen's d (standardized mean difference) between two groups.

    Args:
        control: array-like of metric values for control group.
        treatment: array-like of metric values for treatment group.

    Returns:
        dict with: d, magnitude (Negligible/Small/Medium/Large), interpretation.
    """
    control = pd.Series(control).dropna()
    treatment = pd.Series(treatment).dropna()

    n_c, n_t = len(control), len(treatment)
    if n_c < 2 or n_t < 2:
        return {"d": 0.0, "magnitude": "Unknown", "interpretation": "Insufficient data."}

    var_c = float(control.var(ddof=1))
    var_t = float(treatment.var(ddof=1))
    pooled_std = math.sqrt(((n_c - 1) * var_c + (n_t - 1) * var_t) / (n_c + n_t - 2))

    if pooled_std == 0:
        return {"d": 0.0, "magnitude": "Unknown", "interpretation": "Zero variance in both groups."}

    d = float((treatment.mean() - control.mean()) / pooled_std)
    d_abs = abs(d)

    if d_abs < 0.2:
        magnitude = "Negligible"
    elif d_abs < 0.5:
        magnitude = "Small"
    elif d_abs < 0.8:
        magnitude = "Medium"
    else:
        magnitude = "Large"

    return {
        "d": d,
        "magnitude": magnitude,
        "interpretation": f"Cohen's d = {d:.3f} ({magnitude} effect).",
    }


def relative_lift(control_mean, treatment_mean):
    """Compute relative lift (percentage change) from control to treatment.

    Args:
        control_mean: mean of control group.
        treatment_mean: mean of treatment group.

    Returns:
        dict with: lift_pct, absolute_diff, interpretation.
    """
    diff = treatment_mean - control_mean

    if control_mean == 0:
        return {
            "lift_pct": float("inf") if diff != 0 else 0.0,
            "absolute_diff": float(diff),
            "interpretation": "Control mean is zero; relative lift is undefined.",
        }

    lift = diff / abs(control_mean) * 100

    direction = "increase" if lift > 0 else "decrease" if lift < 0 else "no change"
    return {
        "lift_pct": float(lift),
        "absolute_diff": float(diff),
        "interpretation": (
            f"{abs(lift):.2f}% {direction} from {control_mean:.4f} to {treatment_mean:.4f}."
        ),
    }
