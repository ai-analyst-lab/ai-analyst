"""Reliability measurement that preserves exact and tolerance agreement separately."""

from __future__ import annotations

import statistics
from collections import Counter
from typing import Any

from .normalization import normalize_number, values_within_tolerance


def measure_reliability(
    trials: list[dict[str, Any]],
    *,
    value_field: str = "headline",
    unit_hint: str | None = None,
    absolute_tolerance: float | None = None,
    relative_tolerance: float | None = None,
) -> dict[str, Any]:
    """Measure repeated behavior without claiming correctness."""
    records = []
    for index, trial in enumerate(trials, start=1):
        trial_status = trial.get("status", "completed")
        parsed = normalize_number(trial.get(value_field), unit_hint=unit_hint)
        category = trial_status
        if trial_status == "completed" and parsed.status != "parsed":
            category = "unparseable"
        records.append(
            {
                "trial": trial.get("trial", index),
                "status": category,
                "raw": trial.get(value_field),
                "normalized": parsed.value,
                "unit": parsed.unit,
                "measured": trial.get("measured"),
                "definition_source": trial.get("definition_source"),
            }
        )

    completed = [r for r in records if r["status"] == "completed" and r["normalized"] is not None]
    values = [float(r["normalized"]) for r in completed]
    counts = Counter(round(value, 12) for value in values)
    exact_count = counts.most_common(1)[0][1] if counts else 0
    exact_rate = exact_count / len(values) if values else None

    tolerance_count = 0
    tolerance_reference = statistics.median(values) if values else None
    if tolerance_reference is not None:
        tolerance_count = sum(
            values_within_tolerance(
                value,
                tolerance_reference,
                absolute=absolute_tolerance,
                relative=relative_tolerance,
            )
            for value in values
        )
    tolerance_rate = tolerance_count / len(values) if values else None

    status_counts = Counter(record["status"] for record in records)
    result: dict[str, Any] = {
        "claim": "This report measures repeated behavior, not correctness.",
        "requested_trials": len(trials),
        "successful_trials": len(values),
        "status_counts": dict(status_counts),
        "records": records,
        "exact_agreement": {"count": exact_count, "rate": exact_rate},
        "tolerance_agreement": {
            "count": tolerance_count,
            "rate": tolerance_rate,
            "reference": tolerance_reference,
            "absolute": absolute_tolerance,
            "relative": relative_tolerance,
        },
    }
    if values:
        mean = statistics.fmean(values)
        result["distribution"] = {
            "distinct": sorted(set(values)),
            "minimum": min(values),
            "maximum": max(values),
            "range": max(values) - min(values),
            "mean": mean,
            "stdev": statistics.pstdev(values) if len(values) > 1 else 0.0,
            "cv": (statistics.pstdev(values) / abs(mean)) if len(values) > 1 and mean else None,
        }
    else:
        result["distribution"] = None
    if not values:
        result["verdict"] = "unknown"
    elif exact_count == len(values) and len(values) == len(trials):
        result["verdict"] = "exactly_stable"
    elif tolerance_count == len(values) and len(values) == len(trials):
        result["verdict"] = "stable_within_tolerance"
    else:
        result["verdict"] = "variable"
    return result
