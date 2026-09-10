"""Deterministic checks for structured analyst output."""

from __future__ import annotations

from typing import Any

from ..schema import EvaluationCase, GradeRecord


def _lookup(payload: dict[str, Any], dotted: str) -> tuple[bool, Any]:
    value: Any = payload
    for part in dotted.split("."):
        if not isinstance(value, dict) or part not in value:
            return False, None
        value = value[part]
    return True, value


def grade_structured(
    case: EvaluationCase,
    trial_id: str,
    run_id: str,
    observed: Any,
    *,
    required_fields: list[str] | None = None,
    forbidden_fields: list[str] | None = None,
    grader_id: str = "structured",
    role: str = "diagnostic",
) -> GradeRecord:
    if not isinstance(observed, dict):
        return GradeRecord(
            run_id=run_id,
            trial_id=trial_id,
            case_id=case.case_id,
            grader_id=grader_id,
            grader_version="1",
            criterion="structured output",
            status="fail",
            role=role,
            explanation="The result was not a structured object.",
        )
    required_fields = required_fields or []
    forbidden_fields = forbidden_fields or []
    missing = [field for field in required_fields if not _lookup(observed, field)[0]]
    present_forbidden = [field for field in forbidden_fields if _lookup(observed, field)[0]]
    passed = not missing and not present_forbidden
    details = []
    if missing:
        details.append(f"missing: {', '.join(missing)}")
    if present_forbidden:
        details.append(f"forbidden fields present: {', '.join(present_forbidden)}")
    return GradeRecord(
        run_id=run_id,
        trial_id=trial_id,
        case_id=case.case_id,
        grader_id=grader_id,
        grader_version="1",
        criterion="structured output",
        status="pass" if passed else "fail",
        role=role,
        value={"missing": missing, "forbidden_present": present_forbidden},
        explanation="Required structure is present." if passed else "; ".join(details),
    )
