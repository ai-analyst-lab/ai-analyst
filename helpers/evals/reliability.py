"""Reliability measurement that preserves exact and tolerance agreement separately."""

from __future__ import annotations

import statistics
import re
from collections import Counter
from typing import Any

from .normalization import normalize_number, values_within_tolerance


_GENERIC_DEFINITION_TOKENS = {"definition", "metric", "rate", "retention"}


def _canonical_definition_key(value: Any) -> str | None:
    """Normalize cosmetic label differences without merging analytical choices."""
    if value is None:
        return None
    tokens = [
        token
        for token in re.split(r"[^a-z0-9]+", str(value).lower())
        if token and token not in _GENERIC_DEFINITION_TOKENS
    ]
    return "_".join(tokens) or None


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
        raw_definition_key = trial.get("definition_key")
        records.append(
            {
                "trial": trial.get("trial", index),
                "status": category,
                "raw": trial.get(value_field),
                "normalized": parsed.value,
                "unit": parsed.unit,
                "measured": trial.get("measured"),
                "definition_key": _canonical_definition_key(raw_definition_key),
                "definition_key_raw": raw_definition_key,
                "definition_source": trial.get("definition_source"),
                "chosen_population": trial.get("chosen_population"),
                "return_behavior": trial.get("return_behavior"),
                "time_window": trial.get("time_window"),
                "unit_of_analysis": trial.get("unit_of_analysis"),
                "exclusions": trial.get("exclusions"),
                "method": trial.get("method"),
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
    definition_groups = {}
    for record in completed:
        key = record.get("definition_key") or "unspecified"
        definition_groups.setdefault(key, []).append(record)
    definitions_differ = len(definition_groups) > 1 and "unspecified" not in definition_groups
    result: dict[str, Any] = {
        "claim": "This report measures repeated behavior, not correctness.",
        "requested_trials": len(trials),
        "successful_trials": len(values),
        "status_counts": dict(status_counts),
        "records": records,
        "definition_groups": {
            key: {
                "count": len(group),
                "values": [row["normalized"] for row in group],
            }
            for key, group in sorted(definition_groups.items())
        },
        "numerical_comparison_valid": not definitions_differ,
        "exact_agreement": {"count": exact_count, "rate": exact_rate},
        "tolerance_agreement": {
            "count": tolerance_count,
            "rate": tolerance_rate,
            "reference": tolerance_reference,
            "absolute": absolute_tolerance,
            "relative": relative_tolerance,
        },
    }
    if definitions_differ:
        result["exact_agreement"] = {
            "count": None,
            "rate": None,
            "reason": "Trials used materially different analytical definitions.",
        }
        result["tolerance_agreement"] = {
            "count": None,
            "rate": None,
            "reference": None,
            "absolute": absolute_tolerance,
            "relative": relative_tolerance,
            "reason": "Tolerance agreement is not computed across different quantities.",
        }
        result["distribution"] = None
    if values and not definitions_differ:
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
    if definitions_differ:
        result["verdict"] = "definitions_differ"
    elif not values:
        result["verdict"] = "unknown"
    elif exact_count == len(values) and len(values) == len(trials):
        result["verdict"] = "exactly_stable"
    elif tolerance_count == len(values) and len(values) == len(trials):
        result["verdict"] = "stable_within_tolerance"
    else:
        result["verdict"] = "variable"
    return result
