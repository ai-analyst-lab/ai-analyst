"""Decision scorecard for one analysis.

The scorecard never averages unlike evidence into one confidence number.
Blocking failures decide first. Missing evidence remains visible.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from .statuses import DECISIONS, GRADE_STATUSES, require_member


def decide(
    evidence: list[dict[str, Any]],
    *,
    proposed_decision: str | None = None,
    consequence: str = "moderate",
) -> dict[str, Any]:
    for item in evidence:
        require_member(item.get("status", "unknown"), GRADE_STATUSES, "evidence status")
        if item.get("role", "diagnostic") not in {"blocking", "diagnostic"}:
            raise ValueError("evidence role must be blocking or diagnostic")

    blocking = [item for item in evidence if item.get("role") == "blocking"]
    blocking_failures = [item for item in blocking if item["status"] in {"fail", "error"}]
    unresolved_blocking = [
        item for item in blocking if item["status"] in {"unknown", "blocked", "not_applicable"}
    ]
    diagnostic_flags = [item for item in evidence if item["status"] == "flag"]

    if not evidence:
        recommendation = "incomplete"
    elif blocking_failures:
        recommendation = "abstain"
    elif unresolved_blocking or diagnostic_flags:
        recommendation = "investigate"
    else:
        recommendation = "act"

    if proposed_decision is not None:
        require_member(proposed_decision, DECISIONS, "proposed decision")
    status_counts = Counter(item["status"] for item in evidence)
    return {
        "recommendation": recommendation,
        "proposed_decision": proposed_decision,
        "decision_matches_evidence": proposed_decision in {None, recommendation},
        "consequence": consequence,
        "status_counts": dict(status_counts),
        "blocking_failures": blocking_failures,
        "unresolved_blocking": unresolved_blocking,
        "diagnostic_flags": diagnostic_flags,
        "evidence": evidence,
        "claim": "Evidence dimensions remain separate. One strong signal cannot cancel a critical failure.",
    }
