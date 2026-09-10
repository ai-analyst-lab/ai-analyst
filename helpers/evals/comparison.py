"""Compare compatible evaluation runs without moving the measuring stick."""

from __future__ import annotations

from statistics import median
from typing import Any


def compare_manifests(baseline: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    compatibility_fields = ("suite_id", "suite_version", "split", "data_snapshot")
    differences = {
        field: {"baseline": baseline.get(field), "candidate": candidate.get(field)}
        for field in compatibility_fields
        if baseline.get(field) != candidate.get(field)
    }
    base_config = baseline.get("configuration", {})
    candidate_config = candidate.get("configuration", {})
    controlled_change = candidate_config.get("intended_change")
    uncontrolled = {}
    allowed_engine_changes = {"model", "runner"} if controlled_change == "engine" else set()
    for field in (
        "model", "trials_per_case", "data_fingerprint", "context_fingerprint",
        "tool_configuration", "slice", "runner",
    ):
        if field in allowed_engine_changes:
            continue
        if base_config.get(field) != candidate_config.get(field):
            uncontrolled[field] = {
                "baseline": base_config.get(field),
                "candidate": candidate_config.get(field),
            }

    evaluator_fields = ("controller", "public_manifest_digest", "private_suite_digest")
    baseline_evaluator = baseline.get("evaluator_fingerprint", {})
    candidate_evaluator = candidate.get("evaluator_fingerprint", {})
    evaluator_differences = {
        field: {"baseline": baseline_evaluator.get(field), "candidate": candidate_evaluator.get(field)}
        for field in evaluator_fields
        if baseline_evaluator.get(field) != candidate_evaluator.get(field)
    }

    baseline_files = (
        baseline.get("system_fingerprint", {}).get("tree", {}).get("files", {}) or {}
    )
    candidate_files = (
        candidate.get("system_fingerprint", {}).get("tree", {}).get("files", {}) or {}
    )
    changed_system_paths = sorted(
        path
        for path in set(baseline_files) | set(candidate_files)
        if baseline_files.get(path) != candidate_files.get(path)
    )
    allowed_changed_paths = set(candidate_config.get("allowed_changed_paths") or [])
    unapproved_system_changes = sorted(set(changed_system_paths) - allowed_changed_paths)
    if changed_system_paths and controlled_change is None:
        unapproved_system_changes = changed_system_paths

    comparable = (
        not differences
        and not uncontrolled
        and not evaluator_differences
        and not unapproved_system_changes
    )
    return {
        "comparable": comparable,
        "suite_differences": differences,
        "uncontrolled_configuration_changes": uncontrolled,
        "evaluator_differences": evaluator_differences,
        "changed_system_paths": changed_system_paths,
        "allowed_changed_paths": sorted(allowed_changed_paths),
        "unapproved_system_changes": unapproved_system_changes,
        "intended_change": controlled_change,
        "baseline_status_counts": baseline.get("configuration", {}).get("grade_status_counts", {}),
        "candidate_status_counts": candidate.get("configuration", {}).get("grade_status_counts", {}),
        "claim": "Score movement can be attributed only when the suite, data, evaluator, and other system settings remain fixed.",
    }


def compare_engine_runs(
    baseline_manifest: dict[str, Any],
    candidate_manifest: dict[str, Any],
    baseline_trials: list[dict[str, Any]],
    candidate_trials: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compare two controlled engine runs and expose practical tradeoffs."""
    compatibility = compare_manifests(baseline_manifest, candidate_manifest)
    base = _trials_by_case(baseline_trials)
    candidate = _trials_by_case(candidate_trials)
    case_ids = sorted(set(base) | set(candidate))
    case_changes = []
    disagreements = []
    for case_id in case_ids:
        before = base.get(case_id, [])
        after = candidate.get(case_id, [])
        before_status = [row.get("status") for row in before]
        after_status = [row.get("status") for row in after]
        before_grades = [_evaluation_status(row) for row in before]
        after_grades = [_evaluation_status(row) for row in after]
        before_outputs = [row.get("output_digest") for row in before]
        after_outputs = [row.get("output_digest") for row in after]
        changed = (
            before_status != after_status
            or before_grades != after_grades
            or before_outputs != after_outputs
        )
        item = {
            "case_id": case_id,
            "baseline_statuses": before_status,
            "candidate_statuses": after_status,
            "baseline_evaluation_statuses": before_grades,
            "candidate_evaluation_statuses": after_grades,
            "output_changed": before_outputs != after_outputs,
            "status_changed": changed,
        }
        case_changes.append(item)
        if changed:
            disagreements.append(item)
    return {
        **compatibility,
        "baseline_engine": baseline_manifest.get("engine_fingerprint", {}),
        "candidate_engine": candidate_manifest.get("engine_fingerprint", {}),
        "completion_rate": {
            "baseline": _completion_rate(baseline_trials),
            "candidate": _completion_rate(candidate_trials),
        },
        "evaluation_pass_rate": {
            "baseline": _evaluation_pass_rate(baseline_trials),
            "candidate": _evaluation_pass_rate(candidate_trials),
        },
        "latency_ms": {
            "baseline_median": _median_known(baseline_trials, "latency_ms"),
            "candidate_median": _median_known(candidate_trials, "latency_ms"),
        },
        "cost_usd": {
            "baseline_known_total": _sum_known(baseline_trials, "cost_usd"),
            "candidate_known_total": _sum_known(candidate_trials, "cost_usd"),
            "warning": "A missing cost component is unknown, not zero.",
        },
        "case_changes": case_changes,
        "disagreements_requiring_review": disagreements,
        "new_errors": _new_errors(baseline_trials, candidate_trials),
    }


def _trials_by_case(trials: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}
    for row in trials:
        result.setdefault(str(row.get("case_id")), []).append(row)
    return result


def _completion_rate(trials: list[dict[str, Any]]) -> float | None:
    if not trials:
        return None
    return sum(row.get("status") == "completed" for row in trials) / len(trials)


def _evaluation_status(row: dict[str, Any]) -> str | None:
    return row.get("evaluation_status") or row.get("grade_status")


def _evaluation_pass_rate(trials: list[dict[str, Any]]) -> float | None:
    values = [_evaluation_status(row) for row in trials]
    known = [value for value in values if value is not None]
    if not known:
        return None
    return sum(value == "pass" for value in known) / len(known)


def _median_known(trials: list[dict[str, Any]], field: str) -> float | None:
    values = [float(row[field]) for row in trials if row.get(field) is not None]
    return median(values) if values else None


def _sum_known(trials: list[dict[str, Any]], field: str) -> float | None:
    values = [float(row[field]) for row in trials if row.get(field) is not None]
    return sum(values) if len(values) == len(trials) and values else None


def _new_errors(baseline: list[dict[str, Any]], candidate: list[dict[str, Any]]) -> list[str]:
    before = {str(error.get("type")) for row in baseline for error in row.get("errors", [])}
    after = {str(error.get("type")) for row in candidate for error in row.get("errors", [])}
    return sorted(after - before)
