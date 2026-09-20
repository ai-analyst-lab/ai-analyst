"""Validate student-authored evaluation cases and proposed suites.

These checks establish structure and preserve review status. They do not decide
whether an analytical reference is correct or whether a set is representative.
Those decisions still require a person.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from .cases import load_suite


def validate_proposed_case(path: str | Path) -> dict[str, Any]:
    metadata, cases = load_suite(path, allow_private=False)
    if len(cases) != 1:
        raise ValueError("a proposed-case file must contain exactly one case")
    case = cases[0]
    if case.status != "proposed":
        raise ValueError("a student-authored case must remain proposed until independent review")

    required_text = {
        "intended_user": case.intended_user,
        "decision": case.decision,
        "consequence_if_wrong": case.consequence_if_wrong,
        "human_review_boundary": case.human_review_boundary,
        "truth_evidence": case.truth_evidence,
    }
    missing = [name for name, value in required_text.items() if not value]
    if not case.success_criteria:
        missing.append("success_criteria")
    if not case.graders:
        missing.append("graders")
    if not case.slices.get("task"):
        missing.append("slices.task")
    if not case.slices.get("risk"):
        missing.append("slices.risk")
    if missing:
        raise ValueError(f"proposed case is missing design decisions: {', '.join(missing)}")

    grader_criteria = [grader.get("criterion") for grader in case.graders]
    if any(not criterion for criterion in grader_criteria):
        raise ValueError("every proposed-case grader must name the criterion it evaluates")
    if any(not grader.get("reason") for grader in case.graders):
        raise ValueError("every proposed-case grader must explain why it is appropriate")

    return {
        "valid": True,
        "case_id": case.case_id,
        "status": case.status,
        "criterion_count": len(case.success_criteria),
        "grader_count": len(case.graders),
        "task_slice": case.slices.get("task"),
        "risk_slice": case.slices.get("risk"),
        "human_review_required": case.human_review_required,
        "reference_status": "planned_not_verified",
        "limitations": [
            "Structural validation does not verify the analytical reference.",
            "The case remains proposed until an independent reviewer approves it.",
        ],
        "suite_id": metadata.get("suite_id"),
    }


def validate_proposed_suite(
    path: str | Path,
    *,
    candidate_pool: str | Path,
) -> dict[str, Any]:
    metadata, cases = load_suite(path, allow_private=False)
    pool_metadata, pool_cases = load_suite(candidate_pool, allow_private=False)
    pool_by_id = {case.case_id: case for case in pool_cases}
    selected_ids = [case.case_id for case in cases]
    unknown = sorted(set(selected_ids) - set(pool_by_id))
    if unknown:
        raise ValueError(f"proposed set contains cases outside the candidate pool: {unknown}")
    if len(cases) < 3:
        raise ValueError("a proposed set must select at least three cases")

    selection = metadata.get("selection") or {}
    rejected = selection.get("rejected") or []
    missing_coverage = selection.get("missing_coverage") or []
    if not isinstance(rejected, list) or not rejected:
        raise ValueError("a proposed set must reject at least one candidate with a reason")
    rejected_ids = []
    for record in rejected:
        if not isinstance(record, dict) or not record.get("case_id") or not record.get("reason"):
            raise ValueError("every rejected candidate needs case_id and reason")
        rejected_ids.append(record["case_id"])
    if set(rejected_ids) & set(selected_ids):
        raise ValueError("a candidate cannot be both selected and rejected")
    unknown_rejected = sorted(set(rejected_ids) - set(pool_by_id))
    if unknown_rejected:
        raise ValueError(f"rejected cases are outside the candidate pool: {unknown_rejected}")
    if not isinstance(missing_coverage, list) or not any(str(item).strip() for item in missing_coverage):
        raise ValueError("a proposed set must name at least one missing coverage area")

    task_counts = Counter(case.slices.get("task", "unclassified") for case in cases)
    risk_counts = Counter(case.slices.get("risk", "unclassified") for case in cases)
    if len(task_counts) < 2:
        raise ValueError("a proposed set must cover at least two task slices")
    if len(risk_counts) < 2:
        raise ValueError("a proposed set must cover at least two risk slices")

    return {
        "valid": True,
        "suite_id": metadata.get("suite_id"),
        "candidate_pool_id": pool_metadata.get("suite_id"),
        "selected_case_ids": selected_ids,
        "rejected": rejected,
        "missing_coverage": missing_coverage,
        "case_count": len(cases),
        "task_slices": dict(sorted(task_counts.items())),
        "risk_slices": dict(sorted(risk_counts.items())),
        "case_statuses": dict(sorted(Counter(case.status for case in cases).items())),
        "limitations": [
            "Structural validation does not prove the selected set is representative.",
            "Proposed cases require independent reference and grader review before baseline use.",
        ],
    }
