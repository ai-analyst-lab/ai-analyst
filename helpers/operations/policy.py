"""Validate request boundaries before a run begins."""

from __future__ import annotations

from typing import Any


def validate_autonomy_policy(policy: dict[str, Any]) -> None:
    required = {"allowed_data_sources", "allowed_tools", "read_only", "prohibited_actions",
                "approval_required", "stop_conditions", "expansion_approver"}
    missing = sorted(required - set(policy))
    if missing:
        raise ValueError(f"Autonomy policy is missing: {', '.join(missing)}")
    if not policy["read_only"]:
        raise ValueError("The course operating policy must default to read-only business-data access")
    if not policy["expansion_approver"]:
        raise ValueError("Autonomy expansion requires a named role or owner")


def check_request(policy: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
    validate_autonomy_policy(policy)
    denied_sources = sorted(set(request.get("data_sources", [])) - set(policy["allowed_data_sources"]))
    denied_tools = sorted(set(request.get("tools", [])) - set(policy["allowed_tools"]))
    denied_actions = sorted(set(request.get("actions", [])) & set(policy["prohibited_actions"]))
    if denied_sources or denied_tools or denied_actions:
        return {"status": "blocked", "denied_sources": denied_sources,
                "denied_tools": denied_tools, "denied_actions": denied_actions}
    return {"status": "allowed", "requires_approval": sorted(
        set(request.get("actions", [])) & set(policy["approval_required"]))}
