"""Lifecycle controls for proposed evaluation cases."""

from __future__ import annotations

from dataclasses import replace

from .schema import EvaluationCase, utc_now


def propose(case: EvaluationCase, author: str) -> EvaluationCase:
    if case.status not in {"proposed", "disputed"}:
        raise ValueError("only a proposed or disputed case can enter review")
    return replace(case, status="proposed", author=author, reviewed_by=None, verified_at=None)


def verify(
    case: EvaluationCase,
    *,
    reviewer: str,
    truth_basis: str,
    truth_evidence: str,
    data_snapshot: str,
    reproduction: str,
) -> EvaluationCase:
    if not case.success_criteria:
        raise ValueError("a case needs explicit success criteria before verification")
    if case.expected is None and not case.accepted and not any(
        grader.get("type") == "structured" for grader in case.graders
    ):
        raise ValueError("a case needs a reference or a deterministic structured grader")
    return replace(
        case,
        status="verified",
        reviewed_by=reviewer,
        truth_basis=truth_basis,
        truth_evidence=truth_evidence,
        data_snapshot=data_snapshot,
        reproduction=reproduction,
        verified_at=utc_now(),
    )


def dispute(case: EvaluationCase) -> EvaluationCase:
    return replace(case, status="disputed")


def retire(case: EvaluationCase) -> EvaluationCase:
    return replace(case, status="retired")
