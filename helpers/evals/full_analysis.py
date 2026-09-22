"""Lifecycle for versioned full-analysis development evaluation cases."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import struct
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from .controller import new_run_id
from .fingerprints import file_digest, payload_digest, system_fingerprint
from .records import write_json
from helpers.knowledge.analysis_context import start_analysis


SCHEMA_VERSION = "1"
REQUIRED_OUTPUTS = (
    "result.json",
    "monthly-results.csv",
    "brief.md",
    "chart.png",
    "chart-data.csv",
    "calculation.sql",
)
PRIVATE_FIELD_NAMES = frozenset(
    {
        "expected",
        "accepted",
        "reference",
        "reference_query",
        "answer",
        "answer_key",
        "ground_truth",
        "judge_prompt",
    }
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _read_yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a YAML mapping")
    return value


def _private_keys(value: Any, path: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else str(key)
            if str(key).lower() in PRIVATE_FIELD_NAMES:
                found.append(child_path)
            found.extend(_private_keys(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(_private_keys(child, f"{path}[{index}]"))
    return found


def load_public_case(case_dir: str | Path) -> tuple[Path, dict[str, Any], dict[str, Any]]:
    root = Path(case_dir).resolve()
    case_path = root / "case.yaml"
    schema_path = root / "result.schema.json"
    if not case_path.is_file() or not schema_path.is_file():
        raise ValueError(f"public case must contain case.yaml and result.schema.json: {root}")
    case = _read_yaml(case_path)
    result_schema = _read_json(schema_path)
    leaks = _private_keys(case)
    if leaks:
        raise ValueError(f"public case contains private fields: {leaks}")
    for field in ("case_id", "case_version", "task", "data_scope", "required_outputs"):
        if not case.get(field):
            raise ValueError(f"public case is missing {field}")
    if tuple(case["required_outputs"]) != REQUIRED_OUTPUTS:
        raise ValueError(
            f"required_outputs must be exactly {list(REQUIRED_OUTPUTS)} in that order"
        )
    if case.get("result_schema") != "result.schema.json":
        raise ValueError("result_schema must point to result.schema.json")
    return root, case, result_schema


def _compact_system_fingerprint(project_root: Path) -> dict[str, Any]:
    value = system_fingerprint(project_root)
    return {
        "system_digest": value["system_digest"],
        "file_count": value["tree"]["file_count"],
        "git": value["git"],
    }


def _verify_snowflake_snapshot(project_root: Path, data_scope: dict[str, Any]) -> dict[str, Any]:
    expected = (data_scope.get("snapshot_fingerprint") or {}).get("sha256")
    if not expected:
        raise ValueError("Snowflake case is missing an expected snapshot fingerprint")
    try:
        from dotenv import load_dotenv
        import snowflake.connector
    except ImportError as exc:
        raise ValueError("Snowflake snapshot verification dependencies are unavailable") from exc

    load_dotenv(project_root / ".env")
    required = (
        "SNOWFLAKE_ACCOUNT",
        "SNOWFLAKE_USER",
        "SNOWFLAKE_WAREHOUSE",
        "SNOWFLAKE_DATABASE",
        "SNOWFLAKE_ROLE",
    )
    missing = [name for name in required if not os.environ.get(name)]
    if missing:
        raise ValueError(f"Snowflake snapshot verification is missing environment variables: {missing}")
    kwargs = {
        "account": os.environ["SNOWFLAKE_ACCOUNT"],
        "user": os.environ["SNOWFLAKE_USER"],
        "warehouse": os.environ["SNOWFLAKE_WAREHOUSE"],
        "database": os.environ["SNOWFLAKE_DATABASE"],
        "role": os.environ["SNOWFLAKE_ROLE"],
        "schema": data_scope["schema"],
    }
    auth = os.environ.get("SNOWFLAKE_AUTHENTICATOR", "password").lower().replace("-", "_")
    if auth in {"programmatic_access_token", "pat"}:
        kwargs["authenticator"] = "PROGRAMMATIC_ACCESS_TOKEN"
        kwargs["token"] = os.environ.get("SNOWFLAKE_TOKEN")
    else:
        kwargs["password"] = os.environ.get("SNOWFLAKE_PASSWORD")
    if not kwargs.get("token") and not kwargs.get("password"):
        raise ValueError("Snowflake snapshot verification is missing its authentication credential")

    qualified = ".".join(
        str(data_scope[name]) for name in ("database", "schema", "table")
    )
    query = f"""
        SELECT COUNT(*), MIN(order_date), MAX(order_date),
               COUNT(DISTINCT order_id), ROUND(SUM(total_amount), 2)
        FROM {qualified}
    """
    with snowflake.connector.connect(**kwargs) as connection:
        with connection.cursor() as cursor:
            cursor.execute(query)
            values = cursor.fetchone()
    canonical = "|".join(str(value) for value in values)
    observed = hashlib.sha256(canonical.encode()).hexdigest()
    if observed != expected:
        raise ValueError(
            "Snowflake snapshot fingerprint does not match the case. "
            "Do not compare this run with the reviewed reference until the data is reconciled."
        )
    return {
        "status": "verified",
        "snapshot_id": data_scope.get("snapshot_id"),
        "method": data_scope["snapshot_fingerprint"]["method"],
        "sha256": observed,
        "verified_at": utc_now(),
    }


def _append_event(run_root: Path, event: str, **details: Any) -> None:
    payload = {"at": utc_now(), "event": event, **details}
    with (run_root / "events.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True, default=str) + "\n")


def _resolve_run(runs_root: str | Path, run_id: str) -> Path:
    root = Path(runs_root).resolve() / run_id
    if not (root / "manifest.json").is_file():
        raise ValueError(f"evaluation run does not exist: {run_id}")
    return root


def _only_trial(run_root: Path, trial_id: str | None = None) -> Path:
    trials_root = run_root / "trials"
    if trial_id:
        trial = trials_root / trial_id
        if not (trial / "trial.json").is_file():
            raise ValueError(f"trial does not exist in run: {trial_id}")
        return trial
    trials = sorted(path for path in trials_root.iterdir() if (path / "trial.json").is_file())
    if len(trials) != 1:
        raise ValueError("specify --trial-id when a run does not contain exactly one trial")
    return trials[0]


def start_run(
    *,
    project_root: str | Path,
    case_dir: str | Path,
    runs_root: str | Path = "working/evals/runs",
    baseline_run_id: str | None = None,
    intended_change: str | None = None,
    model: str = "claude-opus-4-6",
) -> dict[str, Any]:
    project_root = Path(project_root).resolve()
    runs_root = (
        Path(runs_root).resolve()
        if Path(runs_root).is_absolute()
        else (project_root / runs_root).resolve()
    )
    case_root, case, result_schema = load_public_case(case_dir)
    exposure = "development" if baseline_run_id else "blind"
    baseline_manifest = None
    if baseline_run_id:
        baseline_root = _resolve_run(runs_root, baseline_run_id)
        baseline_manifest = _read_json(baseline_root / "manifest.json")
        for field, observed in (
            ("case_id", case["case_id"]),
            ("case_version", str(case["case_version"])),
            ("data_snapshot", case["data_scope"].get("snapshot_id")),
        ):
            if str(baseline_manifest.get(field)) != str(observed):
                raise ValueError(
                    f"baseline is incompatible on {field}: "
                    f"{baseline_manifest.get(field)!r} != {observed!r}"
                )

    run_id = new_run_id("analysis-eval")
    trial_id = f"{case['case_id']}-t1-{uuid.uuid4().hex[:6]}"
    run_root = runs_root / run_id
    trial_root = run_root / "trials" / trial_id
    draft = trial_root / "draft"
    public_copy = trial_root / "public-case"
    draft.mkdir(parents=True)
    public_copy.mkdir(parents=True)
    for name in ("case.yaml", "result.schema.json", "README.md"):
        source = case_root / name
        if source.is_file():
            shutil.copy2(source, public_copy / name)

    analysis_id = start_analysis(
        working_dir=project_root / "working",
        question=case["task"],
        intended_decision=case.get("decision"),
        dataset="novamart",
        output_dir=draft,
    )

    public_files = [
        {
            "path": path.name,
            "sha256": file_digest(path),
            "bytes": path.stat().st_size,
        }
        for path in sorted(public_copy.iterdir())
        if path.is_file()
    ]
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "suite_id": "full-analysis-development",
        "status": "awaiting_submission",
        "exposure": exposure,
        "case_id": case["case_id"],
        "case_version": str(case["case_version"]),
        "data_snapshot": case["data_scope"].get("snapshot_id"),
        "data_scope": case["data_scope"],
        "baseline_run_id": baseline_run_id,
        "intended_change": intended_change,
        "model": model,
        "project_root": str(project_root),
        "runs_root": str(runs_root),
        "public_task_digest": payload_digest(case),
        "public_case_files": public_files,
        "system_fingerprint": _compact_system_fingerprint(project_root),
        "created_at": utc_now(),
        "trial_ids": [trial_id],
    }
    trial = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "trial_id": trial_id,
        "case_id": case["case_id"],
        "case_version": str(case["case_version"]),
        "status": "draft",
        "draft_path": str(draft),
        "analysis_id": analysis_id,
        "artifact_bundle_digest": None,
        "created_at": utc_now(),
    }
    write_json(run_root / "manifest.json", manifest)
    write_json(trial_root / "trial.json", trial)
    _append_event(run_root, "run_started", trial_id=trial_id, exposure=exposure)

    instructions = f"""# Run {run_id}

Read `trials/{trial_id}/public-case/README.md` and `case.yaml`.

Complete the analysis with AI Analyst and save exactly these six files in:

`{draft}`

{chr(10).join(f'- `{name}`' for name in REQUIRED_OUTPUTS)}

After the analysis and trace are complete, lock the run:

```bash
python3 -m helpers.evals.full_analysis lock --run-id {run_id}
```

Do not place reference answers or grader files in this run directory.
"""
    (run_root / "RUN-INSTRUCTIONS.md").write_text(instructions, encoding="utf-8")
    return {
        "run_id": run_id,
        "trial_id": trial_id,
        "run_root": str(run_root),
        "draft_path": str(draft),
        "task_path": str(public_copy / "case.yaml"),
        "instructions_path": str(run_root / "RUN-INSTRUCTIONS.md"),
        "exposure": exposure,
        "analysis_id": analysis_id,
    }


def _validate_result_contract(draft: Path, case_id: str) -> dict[str, Any]:
    files = {path.name for path in draft.iterdir() if path.is_file() and not path.name.startswith(".")}
    missing = sorted(set(REQUIRED_OUTPUTS) - files)
    extra = sorted(files - set(REQUIRED_OUTPUTS))
    if missing or extra:
        raise ValueError(f"draft output mismatch: missing={missing}, extra={extra}")

    result = _read_json(draft / "result.json")
    required_sections = {
        "case_id",
        "period",
        "monthly_results",
        "october_to_december",
        "final_answer",
        "methodology",
        "artifacts",
    }
    absent = sorted(required_sections - set(result))
    if absent:
        raise ValueError(f"result.json is missing sections: {absent}")
    if result.get("case_id") != case_id:
        raise ValueError("result.json case_id does not match the run")
    if result.get("period") != {"start": "2024-10-01", "end_exclusive": "2025-01-01"}:
        raise ValueError("result.json period does not match the case")
    rows = result.get("monthly_results")
    if not isinstance(rows, list) or [row.get("month") for row in rows] != [
        "2024-10",
        "2024-11",
        "2024-12",
    ]:
        raise ValueError("monthly_results must contain October, November, and December in order")
    expected_artifacts = {
        "monthly_results": "monthly-results.csv",
        "brief": "brief.md",
        "chart": "chart.png",
        "chart_data": "chart-data.csv",
        "calculation": "calculation.sql",
    }
    if result.get("artifacts") != expected_artifacts:
        raise ValueError("result.json artifact paths do not match the required bundle")
    for section in ("final_answer", "methodology", "october_to_december"):
        if not isinstance(result.get(section), dict):
            raise ValueError(f"result.json {section} must be an object")

    required_columns = [
        "month",
        "completed_order_count",
        "completed_order_value",
        "average_completed_order_value",
    ]
    for name in ("monthly-results.csv", "chart-data.csv"):
        with (draft / name).open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            csv_rows = list(reader)
            if reader.fieldnames != required_columns:
                raise ValueError(f"{name} columns must be {required_columns}")
            if [row["month"] for row in csv_rows] != ["2024-10", "2024-11", "2024-12"]:
                raise ValueError(f"{name} must contain October, November, and December in order")

    brief = (draft / "brief.md").read_text(encoding="utf-8").strip()
    if len(brief) < 100:
        raise ValueError("brief.md is too short to contain the required operating review")
    sql = (draft / "calculation.sql").read_text(encoding="utf-8").strip()
    if not sql or re.search(r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|MERGE|TRUNCATE)\b", sql, re.I):
        raise ValueError("calculation.sql must contain read-only SQL")
    png = (draft / "chart.png").read_bytes()
    if len(png) < 24 or png[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("chart.png is not a readable PNG")
    width, height = struct.unpack(">II", png[16:24])
    if width < 400 or height < 250:
        raise ValueError(f"chart.png is too small: {width}x{height}")
    return result


def _copy_trace_evidence(
    *, project_root: Path, trial_root: Path, analysis_id: str | None
) -> dict[str, Any]:
    trace_root = trial_root / "trace"
    trace_root.mkdir(parents=True, exist_ok=True)
    working = project_root / "working"
    copied: list[Path] = []
    missing: list[str] = []
    if not analysis_id:
        missing = ["analysis_record", "query_log", "action_log", "trace_receipt", "provenance", "trace_html"]
    else:
        direct = {
            "analysis_record": working / f"analysis_{analysis_id}.json",
            "trace_receipt": working / f"trace_receipt_{analysis_id}.json",
            "provenance": working / f"provenance_{analysis_id}.json",
            "findings": working / f"findings_{analysis_id}.jsonl",
        }
        analysis_record = None
        for label, source in direct.items():
            if source.is_file():
                target = trace_root / source.name
                shutil.copy2(source, target)
                copied.append(target)
                if label == "analysis_record":
                    analysis_record = _read_json(source)
            elif label != "findings":
                missing.append(label)

        for label, pattern in (("query_log", "query_log_*.jsonl"), ("action_log", "action_log_*.jsonl")):
            matches: list[str] = []
            for source in sorted(working.glob(pattern)):
                for line in source.read_text(encoding="utf-8").splitlines():
                    try:
                        row = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if row.get("analysis_id") == analysis_id:
                        matches.append(json.dumps(row, sort_keys=True, default=str))
            if matches:
                target = trace_root / f"{label}_{analysis_id}.jsonl"
                target.write_text("\n".join(matches) + "\n", encoding="utf-8")
                copied.append(target)
            else:
                missing.append(label)

        trace_candidates = [working / f"trace_{analysis_id}.html"]
        if analysis_record and analysis_record.get("output_dir"):
            trace_candidates.append(
                Path(analysis_record["output_dir"]).expanduser() / f"trace_{analysis_id}.html"
            )
        trace_source = next((path for path in trace_candidates if path.is_file()), None)
        if trace_source:
            target = trace_root / f"trace_{analysis_id}.html"
            shutil.copy2(trace_source, target)
            copied.append(target)
        else:
            missing.append("trace_html")

    files = [
        {"path": path.name, "sha256": file_digest(path), "bytes": path.stat().st_size}
        for path in sorted(copied)
    ]
    manifest = {
        "analysis_id": analysis_id,
        "files": files,
        "missing": sorted(set(missing)),
        "complete": not missing,
        "captured_at": utc_now(),
    }
    write_json(trace_root / "manifest.json", manifest)
    return manifest


def lock_run(
    *,
    project_root: str | Path,
    runs_root: str | Path,
    run_id: str,
    trial_id: str | None = None,
    analysis_id: str | None = None,
    verify_data_snapshot: bool = True,
) -> dict[str, Any]:
    project_root = Path(project_root).resolve()
    runs_root = (
        Path(runs_root).resolve()
        if Path(runs_root).is_absolute()
        else (project_root / runs_root).resolve()
    )
    run_root = _resolve_run(runs_root, run_id)
    manifest = _read_json(run_root / "manifest.json")
    trial_root = _only_trial(run_root, trial_id)
    trial_path = trial_root / "trial.json"
    trial = _read_json(trial_path)
    if trial.get("status") != "draft":
        raise ValueError(f"trial cannot be locked from status {trial.get('status')}")
    analysis_id = analysis_id or trial.get("analysis_id")
    draft = trial_root / "draft"
    _validate_result_contract(draft, trial["case_id"])
    if verify_data_snapshot:
        data_fingerprint = _verify_snowflake_snapshot(project_root, manifest["data_scope"])
    else:
        data_fingerprint = {
            "status": "skipped",
            "snapshot_id": manifest.get("data_snapshot"),
            "reason": "explicit test-only or recovery bypass",
        }

    submission = trial_root / "submission"
    if submission.exists():
        raise ValueError("submission directory already exists; refusing to overwrite it")
    submission.mkdir()
    for name in REQUIRED_OUTPUTS:
        shutil.copy2(draft / name, submission / name)

    files = [
        {"path": name, "sha256": file_digest(submission / name), "bytes": (submission / name).stat().st_size}
        for name in REQUIRED_OUTPUTS
    ]
    bundle_digest = payload_digest(files)
    artifact_manifest = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "trial_id": trial["trial_id"],
        "case_id": trial["case_id"],
        "case_version": trial["case_version"],
        "locked_at": utc_now(),
        "files": files,
        "bundle_digest": bundle_digest,
    }
    artifact_manifest_path = trial_root / "artifact-manifest.json"
    write_json(artifact_manifest_path, artifact_manifest)
    for path in [*(submission / name for name in REQUIRED_OUTPUTS), artifact_manifest_path]:
        try:
            path.chmod(0o444)
        except OSError:
            pass

    trace_manifest = _copy_trace_evidence(
        project_root=project_root,
        trial_root=trial_root,
        analysis_id=analysis_id,
    )
    trial.update(
        {
            "status": "locked",
            "analysis_id": analysis_id,
            "artifact_bundle_digest": bundle_digest,
            "artifact_manifest": str(artifact_manifest_path),
            "trace_manifest": str(trial_root / "trace" / "manifest.json"),
            "locked_at": artifact_manifest["locked_at"],
        }
    )
    manifest["status"] = "locked"
    manifest["locked_at"] = artifact_manifest["locked_at"]
    manifest["data_fingerprint"] = data_fingerprint
    write_json(trial_path, trial)
    write_json(run_root / "manifest.json", manifest)
    _append_event(
        run_root,
        "submission_locked",
        trial_id=trial["trial_id"],
        bundle_digest=bundle_digest,
        trace_complete=trace_manifest["complete"],
        data_fingerprint_status=data_fingerprint["status"],
    )
    return {
        "run_id": run_id,
        "trial_id": trial["trial_id"],
        "bundle_digest": bundle_digest,
        "submission_path": str(submission),
        "trace_complete": trace_manifest["complete"],
        "missing_trace_evidence": trace_manifest["missing"],
        "data_fingerprint": data_fingerprint,
    }


def verify_locked_submission(run_root: str | Path, trial_id: str | None = None) -> dict[str, Any]:
    run_root = Path(run_root).resolve()
    trial_root = _only_trial(run_root, trial_id)
    trial = _read_json(trial_root / "trial.json")
    if trial.get("status") not in {"locked", "graded"}:
        raise ValueError(f"trial is not locked: {trial.get('status')}")
    artifact_manifest = _read_json(trial_root / "artifact-manifest.json")
    submission = trial_root / "submission"
    observed_names = sorted(path.name for path in submission.iterdir() if path.is_file())
    if observed_names != sorted(REQUIRED_OUTPUTS):
        raise ValueError(f"locked submission file set changed: {observed_names}")
    observed = []
    for record in artifact_manifest["files"]:
        path = submission / record["path"]
        if not path.is_file():
            raise ValueError(f"locked artifact is missing: {record['path']}")
        actual = file_digest(path)
        if actual != record["sha256"] or path.stat().st_size != record["bytes"]:
            raise ValueError(f"locked artifact changed: {record['path']}")
        observed.append({"path": record["path"], "sha256": actual, "bytes": path.stat().st_size})
    digest = payload_digest(observed)
    if digest != artifact_manifest["bundle_digest"] or digest != trial["artifact_bundle_digest"]:
        raise ValueError("locked artifact bundle digest does not match the trial record")
    return {
        "run_id": trial["run_id"],
        "trial_id": trial["trial_id"],
        "bundle_digest": digest,
        "submission_path": str(submission),
        "trial_root": str(trial_root),
    }


def compare_runs(
    *, runs_root: str | Path, before_run_id: str, after_run_id: str
) -> dict[str, Any]:
    runs_root = Path(runs_root).resolve()
    before_root = _resolve_run(runs_root, before_run_id)
    after_root = _resolve_run(runs_root, after_run_id)
    before_manifest = _read_json(before_root / "manifest.json")
    after_manifest = _read_json(after_root / "manifest.json")
    incompatibilities = []
    for field in ("case_id", "case_version", "data_snapshot"):
        if before_manifest.get(field) != after_manifest.get(field):
            incompatibilities.append(
                {"field": field, "before": before_manifest.get(field), "after": after_manifest.get(field)}
            )
    if incompatibilities:
        raise ValueError(f"runs are incompatible: {incompatibilities}")
    before_trial = _only_trial(before_root)
    after_trial = _only_trial(after_root)
    before_grade = _read_json(before_trial / "grades" / "summary.json")
    after_grade = _read_json(after_trial / "grades" / "summary.json")
    gates = {}
    for gate in ("output_contract", "deterministic_accuracy", "final_answer_judge", "case_pass"):
        gates[gate] = {"before": before_grade.get(gate), "after": after_grade.get(gate)}
    comparison = {
        "schema_version": SCHEMA_VERSION,
        "before_run_id": before_run_id,
        "after_run_id": after_run_id,
        "case_id": before_manifest["case_id"],
        "case_version": before_manifest["case_version"],
        "data_snapshot": before_manifest["data_snapshot"],
        "intended_change": after_manifest.get("intended_change"),
        "system_digest_changed": before_manifest["system_fingerprint"]["system_digest"]
        != after_manifest["system_fingerprint"]["system_digest"],
        "gates": gates,
        "created_at": utc_now(),
    }
    comparison_root = after_root / "comparisons"
    write_json(comparison_root / f"from-{before_run_id}.json", comparison)
    lines = [
        f"# Run comparison: {before_run_id} to {after_run_id}",
        "",
        f"**Case:** {comparison['case_id']} v{comparison['case_version']}",
        f"**Data snapshot:** {comparison['data_snapshot']}",
        f"**Intended change:** {comparison.get('intended_change') or 'Not recorded'}",
        f"**System fingerprint changed:** {'Yes' if comparison['system_digest_changed'] else 'No'}",
        "",
        "| Gate | Before | After |",
        "|---|---:|---:|",
    ]
    for gate, values in gates.items():
        lines.append(f"| {gate.replace('_', ' ')} | {values['before']} | {values['after']} |")
    (comparison_root / f"from-{before_run_id}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    _append_event(after_root, "runs_compared", before_run_id=before_run_id)
    return comparison


def _print(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True, default=str))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Full-analysis development evaluation lifecycle")
    sub = parser.add_subparsers(dest="command", required=True)

    start = sub.add_parser("start")
    start.add_argument("--case", required=True)
    start.add_argument("--project-root", default=".")
    start.add_argument("--runs-root", default="working/evals/runs")
    start.add_argument("--baseline-run-id")
    start.add_argument("--intended-change")
    start.add_argument("--model", default="claude-opus-4-6")

    lock = sub.add_parser("lock")
    lock.add_argument("--run-id", required=True)
    lock.add_argument("--trial-id")
    lock.add_argument("--analysis-id")
    lock.add_argument("--project-root", default=".")
    lock.add_argument("--runs-root", default="working/evals/runs")
    lock.add_argument(
        "--skip-data-snapshot-verification",
        action="store_true",
        help="Test and recovery use only. A skipped fingerprint is not eligible for trusted grading.",
    )

    verify = sub.add_parser("verify")
    verify.add_argument("--run-id", required=True)
    verify.add_argument("--trial-id")
    verify.add_argument("--project-root", default=".")
    verify.add_argument("--runs-root", default="working/evals/runs")

    compare = sub.add_parser("compare")
    compare.add_argument("--before-run-id", required=True)
    compare.add_argument("--after-run-id", required=True)
    compare.add_argument("--project-root", default=".")
    compare.add_argument("--runs-root", default="working/evals/runs")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    project_root = Path(args.project_root).resolve()
    runs_root = (
        Path(args.runs_root).resolve()
        if Path(args.runs_root).is_absolute()
        else (project_root / args.runs_root).resolve()
    )
    if args.command == "start":
        _print(
            start_run(
                project_root=project_root,
                case_dir=args.case,
                runs_root=runs_root,
                baseline_run_id=args.baseline_run_id,
                intended_change=args.intended_change,
                model=args.model,
            )
        )
    elif args.command == "lock":
        _print(
            lock_run(
                project_root=project_root,
                runs_root=runs_root,
                run_id=args.run_id,
                trial_id=args.trial_id,
                analysis_id=args.analysis_id,
                verify_data_snapshot=not args.skip_data_snapshot_verification,
            )
        )
    elif args.command == "verify":
        _print(verify_locked_submission(_resolve_run(runs_root, args.run_id), args.trial_id))
    elif args.command == "compare":
        _print(
            compare_runs(
                runs_root=runs_root,
                before_run_id=args.before_run_id,
                after_run_id=args.after_run_id,
            )
        )


if __name__ == "__main__":
    main()
