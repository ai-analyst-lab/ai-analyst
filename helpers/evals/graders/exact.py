"""Exact and categorical grader."""

from __future__ import annotations

from typing import Any

from ..schema import EvaluationCase, GradeRecord


def _canonical(value: Any, case_sensitive: bool) -> Any:
    if isinstance(value, str):
        value = " ".join(value.split())
        return value if case_sensitive else value.casefold()
    return value


def grade_exact(
    case: EvaluationCase,
    trial_id: str,
    run_id: str,
    observed: Any,
    *,
    case_sensitive: bool = False,
    grader_id: str = "exact",
) -> GradeRecord:
    references = list(case.accepted)
    if case.expected is not None:
        references.insert(0, case.expected)
    if not references:
        return GradeRecord(
            run_id=run_id,
            trial_id=trial_id,
            case_id=case.case_id,
            grader_id=grader_id,
            grader_version="1",
            criterion="exact result",
            status="blocked",
            role="blocking",
            explanation="No expected or acceptable result was supplied.",
            escalation_reason="missing reference",
        )
    actual = _canonical(observed, case_sensitive)
    passed = any(actual == _canonical(value, case_sensitive) for value in references)
    return GradeRecord(
        run_id=run_id,
        trial_id=trial_id,
        case_id=case.case_id,
        grader_id=grader_id,
        grader_version="1",
        criterion="exact result",
        status="pass" if passed else "fail",
        role="blocking",
        value=observed,
        explanation="Observed result matched an accepted result." if passed else "Observed result did not match an accepted result.",
    )
