"""Alignment checks for narrow model graders."""

from __future__ import annotations

from collections import Counter
from typing import Any

LABELS = ("pass", "fail", "unknown")


def evaluate_alignment(labels: list[dict[str, Any]]) -> dict[str, Any]:
    """Compare frozen human labels with grader labels.

    This is an alignment check. Small classroom samples are not calibration.
    """
    matrix = {human: {model: 0 for model in LABELS} for human in LABELS}
    disagreements = []
    for row in labels:
        human = row.get("human")
        grader = row.get("grader")
        if human not in LABELS or grader not in LABELS:
            raise ValueError("human and grader labels must be pass, fail, or unknown")
        matrix[human][grader] += 1
        if human != grader:
            disagreements.append(dict(row))
    total = len(labels)
    agreements = total - len(disagreements)
    human_counts = Counter(row["human"] for row in labels)
    grader_counts = Counter(row["grader"] for row in labels)
    return {
        "total": total,
        "agreements": agreements,
        "agreement_rate": agreements / total if total else None,
        "confusion_matrix": matrix,
        "human_label_counts": dict(human_counts),
        "grader_label_counts": dict(grader_counts),
        "disagreements": disagreements,
        "claim": "This is an alignment check, not completed calibration.",
    }


def repeated_label_stability(rows: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[str]] = {}
    for row in rows:
        label = row.get("grader")
        if label not in LABELS:
            raise ValueError("grader labels must be pass, fail, or unknown")
        grouped.setdefault(str(row["example_id"]), []).append(label)
    unstable = {
        example_id: labels for example_id, labels in grouped.items() if len(set(labels)) > 1
    }
    return {
        "examples": len(grouped),
        "unstable_examples": unstable,
        "stable": not unstable,
        "claim": "Repeated labels measure scoring stability, not agreement with human judgment.",
    }
