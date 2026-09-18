"""Deterministic evaluation control plane."""

from __future__ import annotations

import time
import uuid
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Callable, Protocol

from .cases import join_public_and_private, load_suite
from .fingerprints import data_fingerprint, payload_digest, system_fingerprint
from .graders import grade_exact, grade_numeric, grade_structured
from .records import RunStore
from .schema import EvaluationCase, GradeRecord, RunManifest, TrialRecord, utc_now
from .workspace import SanitizedWorkspaceBuilder


class TrialRunner(Protocol):
    def __call__(self, workspace: Path, case: EvaluationCase, trial_number: int) -> dict[str, Any]: ...


def new_run_id(prefix: str = "eval") -> str:
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    return f"{prefix}-{stamp}-{uuid.uuid4().hex[:8]}"


def _validate_data_snapshot(declared: str | None, observed: dict[str, Any]) -> None:
    """Reject a frozen-suite run when its declared SHA-256 does not match its data."""
    if not declared or not declared.startswith("sha256:"):
        return
    files = observed.get("files") or []
    if not files:
        return
    missing = [record.get("path") for record in files if record.get("status") == "missing"]
    if missing:
        raise ValueError(f"evaluation data path is missing: {missing}")
    if len(files) == 1:
        actual = f"sha256:{files[0].get('sha256')}"
    else:
        actual = f"sha256:{observed.get('digest')}"
    if actual != declared:
        raise ValueError(
            "evaluation data snapshot mismatch: "
            f"manifest declares {declared}, observed {actual}"
        )


class EvaluationController:
    def __init__(self, project_root: str | Path, runs_root: str | Path | None = None):
        self.project_root = Path(project_root).resolve()
        self.runs_root = Path(runs_root or self.project_root / "working" / "evals" / "runs")

    def run_public_suite(
        self,
        manifest_path: str | Path,
        runner: TrialRunner,
        *,
        exposure: str = "working",
        purpose: str | None = None,
        case_ids: list[str] | None = None,
        trials_per_case: int = 1,
        model: str = "claude-opus-4-6",
        data_paths: list[str | Path] | None = None,
        suite_slice: dict[str, str] | None = None,
        intended_change: str | None = None,
        allowed_changed_paths: list[str] | None = None,
        runner_name: str = "claude",
        engine_fingerprint: dict[str, Any] | None = None,
    ) -> RunManifest:
        metadata, all_cases = load_suite(manifest_path, allow_private=False)
        cases = [case for case in all_cases if case.exposure == exposure]
        if purpose:
            cases = [case for case in cases if case.purpose == purpose]
        if case_ids:
            selected_ids = set(case_ids)
            cases = [case for case in cases if case.case_id in selected_ids]
            missing_ids = selected_ids - {case.case_id for case in cases}
            if missing_ids:
                raise ValueError(
                    "selected case IDs are unavailable under the requested exposure and purpose: "
                    f"{sorted(missing_ids)}"
                )
        if suite_slice:
            cases = [
                case for case in cases if all(case.slices.get(k) == v for k, v in suite_slice.items())
            ]
        if not cases:
            qualifier = f" and purpose {purpose}" if purpose else ""
            raise ValueError(f"no public cases selected for exposure {exposure}{qualifier}")

        resolved_data_paths = tuple(
            (
                Path(raw).expanduser()
                if Path(raw).expanduser().is_absolute()
                else self.project_root / Path(raw).expanduser()
            ).resolve()
            for raw in (data_paths or [])
        )
        system = system_fingerprint(self.project_root)
        data = data_fingerprint(resolved_data_paths)
        _validate_data_snapshot(metadata.get("data_snapshot"), data)
        run_id = new_run_id()
        store = RunStore(self.runs_root, run_id)
        requested = len(cases) * trials_per_case
        manifest = RunManifest(
            run_id=run_id,
            suite_id=metadata.get("suite_id", Path(manifest_path).stem),
            suite_version=str(metadata.get("suite_version", "1")),
            exposure=exposure,
            purpose=purpose,
            requested_trials=requested,
            system_fingerprint=system,
            evaluator_fingerprint={
                "controller": "helpers.evals.controller@1",
                "public_manifest_digest": payload_digest(metadata | {"cases": [c.to_dict(public=True) for c in cases]}),
            },
            engine_fingerprint=engine_fingerprint or {},
            data_snapshot=metadata.get("data_snapshot"),
            configuration={
                "model": model,
                "trials_per_case": trials_per_case,
                "slice": suite_slice or {},
                "selected_case_ids": sorted(case.case_id for case in cases),
                "data_fingerprint": data,
                "intended_change": intended_change,
                "allowed_changed_paths": sorted(allowed_changed_paths or []),
                "runner": runner_name,
            },
        )
        store.save_manifest(manifest)
        store.event("run_started", requested_trials=requested)
        status_counts: Counter[str] = Counter()

        for case in cases:
            for trial_number in range(1, trials_per_case + 1):
                trial_id = f"{case.case_id}-t{trial_number}-{uuid.uuid4().hex[:6]}"
                workspace = store.root / "workspaces" / trial_id
                SanitizedWorkspaceBuilder(self.project_root).build(
                    workspace, case, data_paths=resolved_data_paths
                )
                trial = TrialRecord(
                    run_id=run_id,
                    trial_id=trial_id,
                    case_id=case.case_id,
                    case_version=case.case_version,
                    trial_number=trial_number,
                    status="running",
                    model=model,
                    engine_fingerprint=engine_fingerprint or {},
                    system_fingerprint=system,
                    data_fingerprint=data,
                    tools=case.allowed_tools,
                    started_at=utc_now(),
                )
                store.event("trial_started", trial_id=trial_id, case_id=case.case_id)
                started = time.monotonic()
                try:
                    result = runner(workspace, case, trial_number) or {}
                    trial.status = result.get("status", "completed")
                    trial.raw_output = result.get("raw_output")
                    trial.structured_result = result.get("structured_result") or {}
                    trial.errors = result.get("errors") or []
                    trial.cost_usd = result.get("cost_usd")
                    trial.usage = result.get("usage") or {}
                    trial.engine_fingerprint = result.get("engine_fingerprint") or trial.engine_fingerprint
                    trial.receipt_paths = result.get("receipt_paths") or []
                    trial.trace_paths = result.get("trace_paths") or []
                    trial.artifact_paths = result.get("artifact_paths") or []
                except Exception as exc:
                    trial.status = "error"
                    trial.errors = [{"type": type(exc).__name__, "detail": str(exc)}]
                trial.finished_at = utc_now()
                trial.latency_ms = round((time.monotonic() - started) * 1000)
                store.lock_trial(trial)
                status_counts[trial.status] += 1

        manifest.completed_trials = sum(status_counts.values())
        manifest.status_counts = dict(status_counts)
        manifest.finished_at = utc_now()
        store.save_manifest(manifest)
        store.event("run_completed", status_counts=dict(status_counts))
        return manifest

    def grade_run(
        self,
        run_id: str,
        public_manifest_path: str | Path,
        private_suite_path: str | Path,
    ) -> RunManifest:
        """Grade locked outputs. The private suite enters only after trial execution."""
        _, public_cases = load_suite(public_manifest_path, allow_private=False)
        _, private_cases = load_suite(private_suite_path, allow_private=True)
        pairs = join_public_and_private(public_cases, private_cases)
        private_by_id = {private.case_id: private for _, private in pairs}
        store = RunStore(self.runs_root, run_id)
        manifest = RunManifest.from_dict(__import__("json").loads(store.manifest_path.read_text()))
        grade_counts: Counter[str] = Counter()
        case_grades: dict[str, list[str]] = defaultdict(list)
        slice_grades: dict[str, Counter[str]] = defaultdict(Counter)

        for path in sorted(store.trials_dir.glob("*.json")):
            trial = store.load_locked_trial(path.stem)
            case = private_by_id.get(trial.case_id)
            if case is None:
                continue
            if trial.status != "completed":
                continue
            result = trial.structured_result
            grader_specs = case.graders or [{"type": "numeric", "field": "answer"}]
            for spec in grader_specs:
                grader_type = spec.get("type")
                field = spec.get("field", "answer")
                observed = _field(result, field)
                if grader_type == "numeric":
                    grade = grade_numeric(
                        case,
                        trial.trial_id,
                        run_id,
                        observed,
                        unit_hint=spec.get("unit"),
                        grader_id=spec.get("id", "numeric"),
                    )
                elif grader_type == "exact":
                    grade = grade_exact(
                        case,
                        trial.trial_id,
                        run_id,
                        observed,
                        case_sensitive=bool(spec.get("case_sensitive", False)),
                        grader_id=spec.get("id", "exact"),
                    )
                elif grader_type == "structured":
                    grade = grade_structured(
                        case,
                        trial.trial_id,
                        run_id,
                        result,
                        required_fields=spec.get("required_fields"),
                        forbidden_fields=spec.get("forbidden_fields"),
                        grader_id=spec.get("id", "structured"),
                        role=spec.get("role", "diagnostic"),
                    )
                else:
                    raise ValueError(f"unsupported grader type {grader_type!r}")
                store.save_grade(grade)
                grade_counts[grade.status] += 1
                case_grades[case.case_id].append(grade.status)
                for dimension, value in case.slices.items():
                    slice_grades[f"{dimension}:{value}"][grade.status] += 1

        manifest.case_summary = {
            case_id: {
                "grades": statuses,
                "blocking_pass": "fail" not in statuses and "error" not in statuses and "blocked" not in statuses,
                "human_review_required": private_by_id[case_id].human_review_required,
                "final_status": (
                    "failed"
                    if "fail" in statuses or "error" in statuses or "blocked" in statuses
                    else "review_required"
                    if private_by_id[case_id].human_review_required
                    else "passed"
                ),
            }
            for case_id, statuses in sorted(case_grades.items())
        }
        manifest.configuration["grade_status_counts"] = dict(grade_counts)
        manifest.slice_summary = {
            name: dict(counts) for name, counts in sorted(slice_grades.items())
        }
        manifest.evaluator_fingerprint["private_suite_digest"] = payload_digest(
            [case.to_dict() for case in private_cases]
        )
        store.save_manifest(manifest)
        store.event("run_graded", grade_status_counts=dict(grade_counts))
        return manifest

    def grade_remote(self, run_id: str, client) -> RunManifest:
        """Grade locked outputs through a course-controlled boundary."""
        store = RunStore(self.runs_root, run_id)
        manifest = RunManifest.from_dict(__import__("json").loads(store.manifest_path.read_text()))
        locked_trials = [
            store.load_locked_trial(path.stem).to_dict()
            for path in sorted(store.trials_dir.glob("*.json"))
        ]
        response = client.grade(manifest.to_dict(), locked_trials)
        counts: Counter[str] = Counter()
        case_grades: dict[str, list[str]] = defaultdict(list)
        for raw in response.get("grades", []):
            grade = GradeRecord(
                run_id=run_id,
                trial_id=raw["trial_id"],
                case_id=raw["case_id"],
                grader_id=raw["grader_id"],
                grader_version=str(raw.get("grader_version", "remote-1")),
                criterion=raw["criterion"],
                status=raw["status"],
                role=raw.get("role", "diagnostic"),
                value=raw.get("value"),
                explanation=raw.get("explanation", ""),
                evidence=raw.get("evidence", []),
                needs_human_review=bool(raw.get("needs_human_review", False)),
                escalation_reason=raw.get("escalation_reason"),
            )
            store.save_grade(grade)
            counts[grade.status] += 1
            case_grades[grade.case_id].append(grade.status)
        manifest.configuration["grade_status_counts"] = dict(counts)
        manifest.configuration["grading_boundary"] = "course-controlled"
        manifest.case_summary = {
            case_id: {
                "grades": statuses,
                "blocking_pass": "fail" not in statuses and "error" not in statuses and "blocked" not in statuses,
            }
            for case_id, statuses in sorted(case_grades.items())
        }
        store.save_manifest(manifest)
        store.event("run_graded_remote", grade_status_counts=dict(counts))
        return manifest


def _field(payload: dict[str, Any], dotted: str) -> Any:
    value: Any = payload
    for part in dotted.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value
