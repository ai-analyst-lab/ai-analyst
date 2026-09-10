"""Method-diverse triangulation records and disagreement analysis."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

VALID_DIRECTIONS = {"yes", "no", "unclear"}


def build_grid(paths: list[dict[str, Any]]) -> dict[str, Any]:
    """Build a comparable grid while preserving why methods disagree."""
    seen = set()
    records = []
    for path in paths:
        required = ("path_id", "method", "source", "population", "assumptions", "direction", "basis")
        missing = [field for field in required if field not in path]
        if missing:
            raise ValueError(f"triangulation path is missing: {', '.join(missing)}")
        if path["path_id"] in seen:
            raise ValueError(f"duplicate path_id: {path['path_id']}")
        if path["direction"] not in VALID_DIRECTIONS:
            raise ValueError("direction must be yes, no, or unclear")
        seen.add(path["path_id"])
        records.append(dict(path))
    directions = Counter(path["direction"] for path in records)
    decided = {direction for direction in directions if direction != "unclear"}
    return {
        "paths": records,
        "direction_counts": dict(directions),
        "disagreement": len(decided) > 1,
        "convergence": len(decided) == 1 and directions.get("unclear", 0) == 0,
        "claim": "Agreement among correlated paths is weak evidence. Method and source independence must be inspected.",
    }


def compare_rounds(first: dict[str, Any], second: dict[str, Any]) -> dict[str, Any]:
    by_path = defaultdict(dict)
    for round_name, grid in (("first", first), ("second", second)):
        for path in grid.get("paths", []):
            by_path[path["path_id"]][round_name] = path
    comparisons = []
    for path_id, rounds in sorted(by_path.items()):
        first_path = rounds.get("first")
        second_path = rounds.get("second")
        persistent = bool(
            first_path and second_path and first_path["direction"] == second_path["direction"]
        )
        comparisons.append(
            {
                "path_id": path_id,
                "first": first_path and first_path["direction"],
                "second": second_path and second_path["direction"],
                "persistent": persistent,
            }
        )
    changed = [item for item in comparisons if not item["persistent"]]
    return {
        "paths": comparisons,
        "run_noise_detected": bool(changed),
        "persistent_disagreement": first.get("disagreement", False)
        and second.get("disagreement", False),
        "next_step": "reconcile assumptions, populations, sources, and counterfactuals"
        if first.get("disagreement") or second.get("disagreement")
        else "record convergence and identify remaining correctness evidence",
    }
