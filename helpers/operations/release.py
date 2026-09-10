"""Deterministic release, review, or revert decisions."""

from __future__ import annotations

from typing import Any


def decide_release(candidate: dict[str, Any], prior: dict[str, Any] | None,
                   policy: dict[str, Any]) -> dict[str, Any]:
    reasons: list[str] = []
    status_counts = candidate.get("status_counts", {})
    if candidate.get("completed_trials", 0) < candidate.get("requested_trials", 0):
        reasons.append("required evaluation trials are incomplete")
    for status in policy.get("blocking_statuses", ["fail", "error", "blocked"]):
        if status_counts.get(status, 0):
            reasons.append(f"blocking evaluation status present: {status}")
    required_cases = set(policy.get("required_cases", []))
    passing_cases = {case_id for case_id, result in candidate.get("case_summary", {}).items()
                     if result.get("blocking_pass")}
    missing = sorted(required_cases - passing_cases)
    if missing:
        reasons.append("required cases did not pass: " + ", ".join(missing))
    approved = set(policy.get("approved_changed_paths", []))
    changed = set(candidate.get("configuration", {}).get("allowed_changed_paths", []))
    if changed - approved:
        reasons.append("candidate includes unapproved changed paths")
    reviewer = candidate.get("configuration", {}).get("reviewer")
    if policy.get("reviewer_required", True) and not reviewer:
        reasons.append("reviewer is not recorded")
    prior_released = bool(prior and prior.get("release_status") == "released")
    if reasons:
        action = "revert" if prior_released and any("blocking" in reason or "did not pass" in reason for reason in reasons) else "review"
    else:
        action = "release"
    return {"decision": action, "candidate_version": candidate.get("candidate_version"),
            "prior_version": prior.get("candidate_version") if prior else None,
            "reasons": reasons or ["all declared release criteria passed"],
            "known_limitations": candidate.get("limitations", [])}
