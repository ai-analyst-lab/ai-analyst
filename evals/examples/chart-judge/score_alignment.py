#!/usr/bin/env python3
"""Compare chart-judge verdicts with frozen human labels."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

ALLOWED = {"pass", "fail", "unknown"}


def load_labels(path: Path, label_column: str) -> dict[str, str]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    labels: dict[str, str] = {}
    for row in rows:
        chart = (row.get("chart") or "").strip()
        label = (row.get(label_column) or "").strip().lower()
        if not chart:
            raise ValueError(f"Missing chart name in {path}")
        if label not in ALLOWED:
            raise ValueError(
                f"Invalid {label_column} label for {chart}: {label!r}. "
                "Use pass, fail, or unknown."
            )
        if chart in labels:
            raise ValueError(f"Duplicate chart in {path}: {chart}")
        labels[chart] = label
    return labels


def divide(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def score(human: dict[str, str], grader: dict[str, str]) -> dict[str, object]:
    missing = sorted(set(human) - set(grader))
    extra = sorted(set(grader) - set(human))
    if missing or extra:
        raise ValueError(f"Label sets differ. Missing: {missing}. Extra: {extra}.")

    tp = fp = fn = tn = unknown = 0
    disagreements: list[dict[str, str]] = []
    for chart in sorted(human):
        h_label = human[chart]
        g_label = grader[chart]
        if g_label == "unknown" or h_label == "unknown":
            unknown += 1
        elif g_label == "pass" and h_label == "pass":
            tp += 1
        elif g_label == "pass" and h_label == "fail":
            fp += 1
        elif g_label == "fail" and h_label == "pass":
            fn += 1
        else:
            tn += 1
        if h_label != g_label:
            disagreements.append(
                {"chart": chart, "human": h_label, "grader": g_label}
            )

    total = len(human)
    scorable = total - unknown
    result: dict[str, object] = {
        "total": total,
        "scorable": scorable,
        "unknown": unknown,
        "confusion": {"tp": tp, "fp": fp, "fn": fn, "tn": tn},
        "accuracy": {
            "numerator": tp + tn,
            "denominator": scorable,
            "value": divide(tp + tn, scorable),
        },
        "precision": {
            "numerator": tp,
            "denominator": tp + fp,
            "value": divide(tp, tp + fp),
        },
        "recall": {
            "numerator": tp,
            "denominator": tp + fn,
            "value": divide(tp, tp + fn),
        },
        "disagreements": disagreements,
        "claim": "Alignment on this reviewed set, not completed calibration.",
    }
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--human", required=True, type=Path)
    parser.add_argument("--grader", required=True, type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    result = score(
        load_labels(args.human, "human"),
        load_labels(args.grader, "grader"),
    )
    rendered = json.dumps(result, indent=2)
    print(rendered)
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(rendered + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
