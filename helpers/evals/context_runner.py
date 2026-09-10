"""Deterministic runner for context-selection and metric-route working cases."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from helpers.data.metric_router import route
from helpers.knowledge.context_manifest import build_context_manifest
from helpers.knowledge.context_workshop import validate_context_store


def _selection_label(selected: set[str], current: str, legacy: str) -> str:
    has_current = current in selected
    has_legacy = legacy in selected
    if has_current and has_legacy:
        return "current_and_legacy"
    if has_current:
        return "current_only"
    if has_legacy:
        return "legacy_only"
    return "neither"


def run_context_policy_case(workspace: Path, case: Any, trial_number: int) -> dict[str, Any]:
    """Evaluate the declared policy mechanism without an LLM in the scoring path."""
    spec = case.data_scope.get("context_policy_test") or {}
    test_type = spec.get("type")
    dataset = str(spec.get("dataset") or "novamart")
    declared_context_dir = spec.get("context_dir")
    context_dir = (
        workspace / str(declared_context_dir)
        if declared_context_dir
        else workspace / ".knowledge" / "datasets" / dataset
    )

    if test_type == "selection":
        manifest = build_context_manifest(
            context_dir,
            str(spec["question"]),
            today=spec.get("today"),
        )
        selected = {row["item_id"] for row in manifest["selected"]}
        current = str(spec["current_item"])
        legacy = str(spec["legacy_item"])
        return {
            "status": "completed",
            "structured_result": {
                "selection_status": _selection_label(selected, current, legacy),
                "selected_item_ids": sorted(selected),
                "context_fingerprint": manifest["context_fingerprint"],
            },
            "trace_paths": [],
        }

    if test_type == "metric-route":
        routed = route(dataset, str(spec["metric"]), context_dir=context_dir)
        return {
            "status": "completed",
            "structured_result": {
                "route": routed.get("mode") if isinstance(routed, dict) else routed
            },
        }

    if test_type == "context-structure":
        result = validate_context_store(context_dir)
        return {
            "status": "completed",
            "structured_result": {
                "structure_status": "pass" if result["valid"] else "fail",
                "counts": result["counts"],
                "errors": result["errors"],
                "warnings": result["warnings"],
            },
        }

    if test_type == "metric-contract":
        metric_id = str(spec["metric"])
        metric_path = context_dir / "metrics" / f"{metric_id}.yaml"
        metric = yaml.safe_load(metric_path.read_text(encoding="utf-8")) if metric_path.exists() else {}
        checks: list[dict[str, Any]] = []
        for field, expected in (spec.get("expected_fields") or {}).items():
            actual = metric.get(field)
            if isinstance(expected, list):
                actual_values = actual if isinstance(actual, list) else []
                passed = all(
                    any(str(want).casefold() in str(value).casefold() for value in actual_values)
                    for want in expected
                )
            else:
                passed = str(expected).casefold() in str(actual).casefold()
            checks.append({"field": field, "passed": passed, "actual": actual})
        return {
            "status": "completed",
            "structured_result": {
                "contract_status": "pass" if checks and all(row["passed"] for row in checks) else "fail",
                "checks": checks,
            },
        }

    raise ValueError(f"unsupported context policy test type: {test_type!r}")
