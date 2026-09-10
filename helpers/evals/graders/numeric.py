"""Known-answer numeric grader."""

from __future__ import annotations

from typing import Any

from ..normalization import normalize_number, values_within_tolerance
from ..schema import EvaluationCase, GradeRecord


def _candidate_values(case: EvaluationCase) -> list[Any]:
    values = list(case.accepted)
    if case.expected is not None:
        values.insert(0, case.expected)
    return values


def grade_numeric(
    case: EvaluationCase,
    trial_id: str,
    run_id: str,
    observed: Any,
    *,
    unit_hint: str | None = None,
    grader_id: str = "numeric",
) -> GradeRecord:
    """Compare a reported scalar with one or more acceptable references."""
    actual = normalize_number(observed, unit_hint=unit_hint)
    if actual.status != "parsed":
        return GradeRecord(
            run_id=run_id,
            trial_id=trial_id,
            case_id=case.case_id,
            grader_id=grader_id,
            grader_version="1",
            criterion="numeric result",
            status="unknown",
            role="blocking",
            explanation=f"Could not extract a numeric result: {actual.note}",
            needs_human_review=True,
        )

    references = _candidate_values(case)
    if not references:
        return GradeRecord(
            run_id=run_id,
            trial_id=trial_id,
            case_id=case.case_id,
            grader_id=grader_id,
            grader_version="1",
            criterion="numeric result",
            status="blocked",
            role="blocking",
            explanation="No expected or acceptable numeric result was supplied.",
            escalation_reason="missing reference",
        )

    normalized_refs = [normalize_number(value, unit_hint=unit_hint) for value in references]
    normalized_refs = [value for value in normalized_refs if value.status == "parsed"]
    if not normalized_refs:
        return GradeRecord(
            run_id=run_id,
            trial_id=trial_id,
            case_id=case.case_id,
            grader_id=grader_id,
            grader_version="1",
            criterion="numeric result",
            status="error",
            role="blocking",
            explanation="The case references could not be parsed.",
            needs_human_review=True,
        )

    absolute = case.tolerance.get("absolute")
    relative = case.tolerance.get("relative")
    matched = next(
        (
            ref
            for ref in normalized_refs
            if values_within_tolerance(
                actual.value, ref.value, absolute=absolute, relative=relative
            )
        ),
        None,
    )
    tolerance_text = f"absolute={absolute}, relative={relative}"
    return GradeRecord(
        run_id=run_id,
        trial_id=trial_id,
        case_id=case.case_id,
        grader_id=grader_id,
        grader_version="1",
        criterion="numeric result",
        status="pass" if matched else "fail",
        role="blocking",
        value=actual.value,
        explanation=(
            f"Observed {actual.value} matched an accepted result using {tolerance_text}."
            if matched
            else f"Observed {actual.value} did not match an accepted result using {tolerance_text}."
        ),
    )
