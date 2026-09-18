"""Narrow client contract for a course-controlled held-out grader."""

from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class RemoteGraderClient:
    endpoint: str
    course_token: str
    timeout_seconds: int = 60
    opener: Callable[..., Any] = urllib.request.urlopen

    def grade(self, run_manifest: dict[str, Any], locked_trials: list[dict[str, Any]]) -> dict[str, Any]:
        """Submit locked outputs without sending or receiving an answer key."""
        payload = {
            "protocol_version": "1",
            "run": {
                "run_id": run_manifest["run_id"],
                "suite_id": run_manifest["suite_id"],
                "suite_version": run_manifest["suite_version"],
                "exposure": run_manifest["exposure"],
                "purpose": run_manifest.get("purpose"),
                "system_fingerprint": run_manifest["system_fingerprint"],
                "data_snapshot": run_manifest.get("data_snapshot"),
            },
            "trials": [
                {
                    "trial_id": row["trial_id"],
                    "case_id": row["case_id"],
                    "case_version": row["case_version"],
                    "output_digest": row["output_digest"],
                    "structured_result": row.get("structured_result", {}),
                }
                for row in locked_trials
            ],
        }
        request = urllib.request.Request(
            self.endpoint,
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers={
                "Authorization": f"Bearer {self.course_token}",
                "Content-Type": "application/json",
            },
        )
        with self.opener(request, timeout=self.timeout_seconds) as response:
            result = json.loads(response.read().decode("utf-8"))
        forbidden = {"expected", "accepted", "reference_query", "answer_key", "ground_truth"}
        leaked = forbidden.intersection(_all_keys(result))
        if leaked:
            raise ValueError(f"grader response exposed private reference fields: {sorted(leaked)}")
        if result.get("run_id") != run_manifest["run_id"]:
            raise ValueError("grader response run_id does not match the submitted run")
        return result


def _all_keys(value: Any) -> set[str]:
    keys = set()
    if isinstance(value, dict):
        for key, child in value.items():
            keys.add(str(key).casefold())
            keys.update(_all_keys(child))
    elif isinstance(value, list):
        for child in value:
            keys.update(_all_keys(child))
    return keys
