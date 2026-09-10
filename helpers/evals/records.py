"""Atomic run records and output locking."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from .fingerprints import payload_digest
from .schema import GradeRecord, RunManifest, TrialRecord, utc_now


def write_json(path: str | Path, payload: Any) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=target.parent, delete=False, suffix=".tmp"
    ) as handle:
        json.dump(payload, handle, indent=2, sort_keys=True, default=str)
        handle.write("\n")
        temp_path = Path(handle.name)
    os.replace(temp_path, target)
    return target


class RunStore:
    def __init__(self, root: str | Path, run_id: str):
        self.root = Path(root) / run_id
        self.trials_dir = self.root / "trials"
        self.grades_dir = self.root / "grades"
        self.root.mkdir(parents=True, exist_ok=True)

    @property
    def manifest_path(self) -> Path:
        return self.root / "manifest.json"

    @property
    def events_path(self) -> Path:
        return self.root / "events.jsonl"

    def save_manifest(self, manifest: RunManifest) -> Path:
        return write_json(self.manifest_path, manifest.to_dict())

    def event(self, event: str, **details: Any) -> None:
        payload = {"at": utc_now(), "event": event, **details}
        with self.events_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, sort_keys=True, default=str) + "\n")

    def lock_trial(self, trial: TrialRecord) -> Path:
        if trial.status not in {"completed", "failed", "blocked", "error", "invalid", "unknown"}:
            raise ValueError(f"cannot lock trial in status {trial.status}")
        if trial.locked_at or trial.output_digest:
            raise ValueError("trial is already locked")
        trial.locked_at = utc_now()
        trial.output_digest = payload_digest(
            {"raw_output": trial.raw_output, "structured_result": trial.structured_result}
        )
        path = self.trials_dir / f"{trial.trial_id}.json"
        write_json(path, trial.to_dict())
        try:
            path.chmod(0o444)
        except OSError:
            pass
        self.event("trial_locked", trial_id=trial.trial_id, digest=trial.output_digest)
        return path

    def load_locked_trial(self, trial_id: str) -> TrialRecord:
        path = self.trials_dir / f"{trial_id}.json"
        raw = json.loads(path.read_text(encoding="utf-8"))
        trial = TrialRecord.from_dict(raw)
        expected = payload_digest(
            {"raw_output": trial.raw_output, "structured_result": trial.structured_result}
        )
        if not trial.locked_at or trial.output_digest != expected:
            raise ValueError(f"trial output lock failed for {trial_id}")
        return trial

    def save_grade(self, grade: GradeRecord) -> Path:
        self.load_locked_trial(grade.trial_id)
        path = self.grades_dir / f"{grade.trial_id}--{grade.grader_id}.json"
        write_json(path, grade.to_dict())
        self.event(
            "trial_graded",
            trial_id=grade.trial_id,
            grader_id=grade.grader_id,
            status=grade.status,
        )
        return path
