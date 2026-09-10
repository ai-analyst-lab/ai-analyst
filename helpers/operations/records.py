"""Append-only local operating and incident records."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from helpers.engines.schema import utc_now


def append_record(path: str | Path, record: dict[str, Any]) -> dict[str, Any]:
    value = {"recorded_at": utc_now(), **record}
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(value, sort_keys=True) + "\n")
    return value


def correction_record(*, problem: str, run_id: str, evidence: list[str],
                      failure_class: str, target_component: str, owner: str,
                      evaluation_cases: list[str]) -> dict[str, Any]:
    return {
        "observed_problem": problem, "affected_run": run_id, "evidence": evidence,
        "suspected_failure_class": failure_class, "proposed_target_component": target_component,
        "owner": owner, "review_status": "proposed", "evaluation_cases": evaluation_cases,
    }
