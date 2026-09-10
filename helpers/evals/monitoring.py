"""Evaluation history and operational change detection."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_history(runs_root: str | Path) -> list[dict[str, Any]]:
    records = []
    for path in Path(runs_root).glob("*/manifest.json"):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        record["manifest_path"] = str(path)
        records.append(record)
    return sorted(records, key=lambda row: row.get("started_at", ""))


def classify_changes(history: list[dict[str, Any]]) -> list[dict[str, Any]]:
    changes = []
    for previous, current in zip(history, history[1:]):
        kinds = []
        if previous.get("system_fingerprint", {}).get("system_digest") != current.get(
            "system_fingerprint", {}
        ).get("system_digest"):
            kinds.append("system")
        if previous.get("data_snapshot") != current.get("data_snapshot"):
            kinds.append("data")
        if previous.get("suite_version") != current.get("suite_version"):
            kinds.append("task_mix")
        if previous.get("evaluator_fingerprint") != current.get("evaluator_fingerprint"):
            kinds.append("evaluator")
        changes.append(
            {
                "from": previous.get("run_id"),
                "to": current.get("run_id"),
                "change_types": kinds or ["none_detected"],
                "requires_investigation": len(kinds) > 1,
            }
        )
    return changes
