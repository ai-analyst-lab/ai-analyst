"""Run complete-analysis evaluation cases in isolated Claude Code workspaces."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Callable

import yaml
from dotenv import load_dotenv

from .full_analysis import _copy_calculation_evidence, start_run
from .records import write_json
from .workspace import ClaudeCommand


PRIVATE_PATTERNS = (
    re.compile(r"accepted_final_answer", re.I),
    re.compile(r"reference_sql", re.I),
    re.compile(r"answer_key", re.I),
    re.compile(r"ground_truth", re.I),
    re.compile(r"judge_prompt", re.I),
)


def utc_now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_complete_suite(path: str | Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    suite_path = Path(path).resolve()
    payload = yaml.safe_load(suite_path.read_text(encoding="utf-8")) or {}
    cases = payload.get("cases") or []
    if not payload.get("suite_id") or not cases:
        raise ValueError("complete-analysis suite must contain suite_id and cases")
    ids = [str(case.get("case_id")) for case in cases]
    if len(ids) != len(set(ids)):
        raise ValueError("complete-analysis suite contains duplicate case IDs")
    for case in cases:
        if not case.get("path") or not case.get("case_version"):
            raise ValueError(f"suite case is missing path or version: {case}")
    return payload, cases


def _ignore_copy(directory: str, names: list[str]) -> set[str]:
    root = Path(directory)
    ignored: set[str] = set()
    for name in names:
        candidate = root / name
        if name in {".git", ".venv", ".env", ".mcp.json", "working", "outputs", "runs", "tests", "__pycache__"}:
            ignored.add(name)
        elif name.startswith('.env.') and name not in {'.env.example', '.env.template'}:
            ignored.add(name)
        elif name.endswith((".pyc", ".pyo")):
            ignored.add(name)
        elif candidate.parts[-3:] == ("evals", "focused", "working-references"):
            ignored.add(name)
        elif candidate.parts[-2:] == ("evals", "examples"):
            ignored.add(name)
        elif candidate.parts[-2:] in {(".knowledge", ".context-cache"), (".knowledge", "context-snapshot")}:
            ignored.add(name)
    return ignored


def build_isolated_workspace(project_root: Path, destination: Path) -> dict[str, Any]:
    # Reject links before copytree can follow them into an answer or secret store.
    for directory, dirs, names in os.walk(project_root, followlinks=False):
        ignored = _ignore_copy(directory, [*dirs, *names])
        dirs[:] = [name for name in dirs if name not in ignored]
        for name in [*dirs, *(name for name in names if name not in ignored)]:
            if (Path(directory) / name).is_symlink():
                raise ValueError(f'isolated workspace rejects symlink: {Path(directory) / name}')
    shutil.copytree(project_root, destination, ignore=_ignore_copy)
    violations = []
    files = []
    for path in sorted(candidate for candidate in destination.rglob("*") if candidate.is_file()):
        relative = str(path.relative_to(destination)).replace("\\", "/")
        files.append(relative)
        if relative.startswith("working/") or "/working-references/" in f"/{relative}":
            violations.append(f"forbidden path: {relative}")
        if path.suffix.lower() in {".yaml", ".yml", ".json", ".md", ".txt", ".sql"}:
            text = path.read_text(encoding="utf-8", errors="ignore")
            if relative.startswith("evals/cases/public/"):
                for pattern in PRIVATE_PATTERNS:
                    if pattern.search(text):
                        violations.append(f"private marker in public case: {relative}: {pattern.pattern}")
    if violations:
        raise ValueError("isolated workspace leak audit failed: " + "; ".join(violations[:20]))
    return {"file_count": len(files), "violations": []}


def build_sql_system_snapshot(project_root: Path, destination: Path, cases: list[dict[str, Any]]) -> dict[str, Any]:
    """SQL workers receive the runtime, selected public tasks and external context.

    Do not copy authoring scripts, lesson packets, unrelated cases or repository
    history. They can contain future treatments even without an answer-key name.
    Child working directories are still separately copied and context-snapshotted.
    """
    entries = ["CLAUDE.md", ".claude/skills", "agents", "helpers",
               "docs/CONNECTED-CONTEXT.md", "data_sources.yaml", ".knowledge/active.yaml"]
    entries += [str(case['path']) for case in cases]
    destination.mkdir(parents=True, exist_ok=False)
    for entry in entries:
        relative = Path(entry)
        if relative.is_absolute() or '..' in relative.parts:
            raise ValueError(f'unsafe SQL runtime entry: {entry}')
        source = project_root / relative
        if not source.exists():
            if entry in {str(case['path']) for case in cases}:
                raise ValueError(f'missing SQL public case: {entry}')
            continue
        if source.is_symlink() or any(p.is_symlink() for p in source.rglob('*')):
            raise ValueError(f'SQL runtime rejects symlink: {entry}')
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(source, target, ignore=_ignore_copy)
        else:
            shutil.copy2(source, target)
    for case in cases:
        directory = destination / str(case['path'])
        if not str(case['path']).startswith('evals/cases/public/'):
            raise ValueError('SQL case must be under evals/cases/public/')
        for file in directory.rglob('*'):
            if file.is_file() and file.suffix in {'.yaml', '.yml', '.json', '.md', '.sql', '.txt'}:
                for pattern in PRIVATE_PATTERNS:
                    if pattern.search(file.read_text()):
                        raise ValueError(f'private marker in SQL public case: {file.name}')
    files = [p for p in destination.rglob('*') if p.is_file()]
    return {'file_count': len(files), 'violations': [], 'policy': 'sql-runtime-allowlist-v1'}


def _copy_run(source: Path, destination_root: Path) -> Path:
    destination = destination_root / source.name
    if destination.exists():
        raise ValueError(f"run destination already exists: {destination}")
    shutil.copytree(source, destination)
    return destination


def _terminal_case_status(locked: bool, worker_result: dict[str, Any]) -> str:
    if locked:
        return 'locked'
    return 'error' if worker_result.get('status') == 'error' else 'invalid'


def _execute_case(
    *,
    project_root: Path,
    case: dict[str, Any],
    model: str,
    timeout: int,
    runs_root: Path,
    command_factory: Callable[..., ClaudeCommand] = ClaudeCommand,
    context_snapshot: Path | None = None,
    context_snapshot_digest: str | None = None,
    system_snapshot: Path | None = None,
    max_budget_usd: float | None = None,
    reference_roots: list[str | Path] | None = None,
) -> dict[str, Any]:
    started = time.monotonic()
    case_id = str(case["case_id"])
    with tempfile.TemporaryDirectory(prefix=f"ai-analyst-full-eval-{case_id}-") as temporary:
        workspace = Path(temporary) / "ai-analyst"
        audit = build_isolated_workspace(system_snapshot or project_root, workspace)
        if context_snapshot is not None:
            from helpers.knowledge.context_snapshot import install_snapshot
            audit["context_snapshot"] = install_snapshot(context_snapshot, workspace, context_snapshot_digest)
        case_path = workspace / str(case["path"])
        started_run = start_run(
            project_root=workspace,
            case_dir=case_path,
            runs_root=workspace / "working" / "evals" / "runs",
            model=model,
        )
        run_root = Path(started_run["run_root"])
        case_config = yaml.safe_load((case_path / "case.yaml").read_text())
        sql_only = case_config.get("evaluation_mode") == "sql_results"
        execution_instruction = (
            "This is a SQL/results evaluation: execute the query, save result.json, the result CSV and calculation.sql. "
            "Use one trace analysis ID and the logged Snowflake connection helper. Do not create reports, charts, "
            "findings or HTML traces; locking captures the SQL execution evidence. "
            if sql_only else
            "Create every required artifact and maintain one complete analysis trace. "
        )
        prompt = (
            f"Execute evaluation run {started_run['run_id']}. "
            "Read its RUN-INSTRUCTIONS.md and public case. Use the repository's trace skill "
            "and Snowflake connection helpers rather than creating trace files manually. Perform the analysis with the "
            "configured Snowflake connection. " + execution_instruction +
            "Inspect the work and lock the run. Do not use any "
            "incomplete-trace or snapshot-verification bypass. If required trace evidence is "
            "missing, repair the trace before locking. Work autonomously. "
            "Do not inspect parent directories or search for any evaluator, expected answer, "
            "reference query, or grader repository. Return the run ID and final lock status."
        )
        command_options = {}
        if max_budget_usd is not None:
            command_options['max_budget_usd'] = max_budget_usd
        if sql_only:
            from .isolation import sql_worker_settings
            command_options["capture_tool_events"] = True
            command_options["process_settings"] = sql_worker_settings([
                project_root.parent / "ai-analyst-course-evals",
                project_root.parent / "ai-analytics-for-builders",
                project_root / "working",
                project_root / "scripts",
                project_root / "evals" / "focused" / "working-references",
                *[Path(p) for p in (reference_roots or [])],
            ])
            prompt = (
                f"Complete the existing SQL/results run {started_run['run_id']}; do not start a second run. "
                f"Read {run_root / 'RUN-INSTRUCTIONS.md'} and follow its exact case and draft paths. "
                f"Use {sys.executable} for all Python commands; its dependencies are installed. "
                "Do not install packages or create a virtual environment. Use the logged Snowflake connection helper. "
                "Use the existing analysis ID in RUN-INSTRUCTIONS and follow its discovery steps for BOTH business-guide and connected "
                "calculation discovery. Execute an exactly matching eligible metric or reviewed query through the "
                "connected-context service; preserve its execution evidence. Generated or adapted SQL is allowed "
                "when no executable supports the requested scope and meaning is sufficient; label that path honestly. "
                "Save the three required files and lock this run. Once the lock succeeds, return the run ID "
                "and lock status immediately; do not perform additional work afterward. "
                "Do not use the full-analysis eval skill or create charts or reports. "
                "Do not read references, grading repositories, parent directories or earlier runs. "
                "Stop and report any blocker rather than changing configuration or disabling controls."
            )
        command = command_factory(
            model=model,
            timeout_seconds=timeout,
            allowed_tools=("Read", "Glob", "Grep", "Bash"),
            **command_options,
        )
        result = command.run(
            workspace,
            prompt,
            json_schema={
                "type": "object",
                "properties": {
                    "run_id": {"type": "string"},
                    "status": {"type": "string"},
                    "summary": {"type": "string"},
                },
                "required": ["run_id", "status"],
                "additionalProperties": True,
            },
        )
        write_json(run_root / "worker-response.json", result)
        write_json(run_root / "tool-events.json", result.get("tool_events", []))
        recovery = run_root / "execution-evidence"
        recovery.mkdir(exist_ok=True)
        for pattern in ("analysis_*.json", "query_log_*.jsonl", "action_log_*.jsonl", "context_loads_*.jsonl", "connected_context_*.jsonl"):
            for path in (workspace / "working").glob(pattern):
                shutil.copy2(path, recovery / path.name)
        _copy_calculation_evidence(workspace / "working", recovery, started_run.get("analysis_id"))
        write_json(run_root / "input-inventory.json", (result.get("execution_metadata") or {}).get("input_file_hashes", []))
        manifest_path = run_root / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        trial_roots = [path for path in (run_root / "trials").iterdir() if path.is_dir()]
        trace_manifest = {}
        if len(trial_roots) == 1 and (trial_roots[0] / "trace" / "manifest.json").is_file():
            trace_manifest = json.loads(
                (trial_roots[0] / "trace" / "manifest.json").read_text(encoding="utf-8")
            )
        copied = _copy_run(run_root, runs_root)
        locked = (
            manifest.get("status") == "locked"
            and trace_manifest.get("complete") is True
            and (manifest.get("data_fingerprint") or {}).get("status") == "verified"
        )
        metadata = result.get("execution_metadata") or {}
        return {
            "case_id": case_id,
            "case_version": str(case["case_version"]),
            "run_id": started_run["run_id"],
            "run_path": str(copied),
            "status": _terminal_case_status(locked, result),
            "worker_status": result.get('status'),
            "run_manifest_status": manifest.get("status"),
            "trace_complete": bool(trace_manifest.get("complete")),
            "data_fingerprint_status": (manifest.get("data_fingerprint") or {}).get("status"),
            "errors": result.get("errors") or [],
            "latency_seconds": round(time.monotonic() - started, 2),
            "cost_usd": result.get("cost_usd"),
            "evaluation_mode": case_config.get("evaluation_mode", "full_analysis"),
            "workspace_audit": audit,
            "execution_metadata": {
                key: metadata.get(key)
                for key in (
                    "command_sha256", "prompt_sha256", "json_schema_sha256",
                    "effective_process_tools", "started_at", "finished_at",
                )
            },
        }


def run_complete_suite(
    *,
    project_root: str | Path,
    suite_path: str | Path,
    model: str = "claude-opus-4-6",
    parallelism: int = 4,
    timeout: int = 1800,
    selected_case_ids: list[str] | None = None,
    command_factory: Callable[..., ClaudeCommand] = ClaudeCommand,
    context_store: str | Path | None = None,
    capability_files: dict[str, str | Path] | None = None,
    max_budget_usd: float | None = None,
    reference_roots: list[str | Path] | None = None,
) -> dict[str, Any]:
    project_root = Path(project_root).resolve()
    suite_path = Path(suite_path)
    if not suite_path.is_absolute():
        suite_path = project_root / suite_path
    suite, cases = load_complete_suite(suite_path)
    if selected_case_ids:
        selected = set(selected_case_ids)
        cases = [case for case in cases if case["case_id"] in selected]
        missing = selected - {case["case_id"] for case in cases}
        if missing:
            raise ValueError(f"unknown complete-analysis case IDs: {sorted(missing)}")
    if not cases:
        raise ValueError("no complete-analysis cases selected")
    if max_budget_usd is not None and max_budget_usd <= 0:
        raise ValueError('max_budget_usd must be positive')

    load_dotenv(project_root / ".env", override=False)
    suite_started = time.monotonic()
    suite_run_id = f"full-suite-{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}-{uuid.uuid4().hex[:8]}"
    suite_root = project_root / "working" / "evals" / "suites" / suite_run_id
    runs_root = project_root / "working" / "evals" / "runs"
    suite_root.mkdir(parents=True, exist_ok=False)
    runs_root.mkdir(parents=True, exist_ok=True)
    from helpers.knowledge.context_snapshot import snapshot_visible_context
    context_snapshot_path = suite_root / "context-snapshot"
    context_snapshot_record = snapshot_visible_context(project_root, context_snapshot_path,
        source_override=Path(context_store) if context_store is not None else None)
    # One system copy per suite, not a different live checkout for each queued case.
    system_snapshot_path = suite_root / "system-snapshot"
    sql_only_suite = suite.get('evaluation_mode') == 'sql_results' or all(
        (project_root / str(case['path']) / 'case.yaml').is_file() and
        (yaml.safe_load((project_root / str(case['path']) / 'case.yaml').read_text()) or {}).get('evaluation_mode') == 'sql_results'
        for case in cases
    )
    system_snapshot_audit = (build_sql_system_snapshot(project_root, system_snapshot_path, cases)
                             if sql_only_suite else build_isolated_workspace(project_root, system_snapshot_path))
    capability_records=[]
    for relative, source in (capability_files or {}).items():
        relative_path=Path(relative)
        if relative_path.is_absolute() or '..' in relative_path.parts or relative_path.parts[0] != 'helpers' or relative_path.suffix != '.py':
            raise ValueError('Capability additions must be Python files under helpers/')
        target=system_snapshot_path / relative_path
        source=Path(source)
        if target.exists() or source.is_symlink() or not source.is_file():
            raise ValueError('Capability addition cannot overwrite runtime files or follow links')
        content=source.read_bytes()
        compile(content,str(relative_path),'exec')
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(content)
        capability_records.append({'path':relative,'sha256':hashlib.sha256(content).hexdigest()})
    system_records = [
        {"path": str(path.relative_to(system_snapshot_path)), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        for path in sorted(system_snapshot_path.rglob('*'))
        if path.is_file() and path.relative_to(system_snapshot_path).parts[0] != '.knowledge'
    ]
    runtime_digest = hashlib.sha256(json.dumps(system_records, sort_keys=True).encode()).hexdigest()
    write_json(suite_root / 'system-inputs.json', system_records)
    requested_parallelism = max(1, parallelism)
    actual_parallelism = min(requested_parallelism, len(cases))
    manifest = {
        "schema_version": "1", "suite_run_id": suite_run_id,
        "suite_id": suite["suite_id"], "suite_version": str(suite.get("suite_version", "1")),
        "evaluation_mode": suite.get("evaluation_mode", "full_analysis"),
        "status": "running", "model": model, "created_at": utc_now(),
        "requested_case_count": len(cases), "requested_parallelism": requested_parallelism,
        "actual_parallelism": actual_parallelism, "cases": [],
        "max_budget_usd_per_worker": max_budget_usd,
        "timeout_seconds_per_worker": timeout,
        "additional_denied_read_roots": [str(Path(p).resolve()) for p in (reference_roots or [])],
        "context_snapshot": context_snapshot_record,
        "capability_additions": capability_records,
        "system_snapshot_path": str(system_snapshot_path),
        "system_snapshot_file_count": system_snapshot_audit["file_count"] + len(capability_records),
        "runtime_and_cases_digest": runtime_digest,
    }
    write_json(suite_root / "manifest.json", manifest)

    records = []
    with ThreadPoolExecutor(max_workers=actual_parallelism) as pool:
        futures = {
            pool.submit(
                _execute_case,
                project_root=project_root,
                case=case,
                model=model,
                timeout=timeout,
                runs_root=runs_root,
                command_factory=command_factory,
                context_snapshot=context_snapshot_path if context_snapshot_record is not None else None,
                context_snapshot_digest=context_snapshot_record['sha256'] if context_snapshot_record else None,
                system_snapshot=system_snapshot_path,
                max_budget_usd=max_budget_usd,
                reference_roots=reference_roots,
            ): case
            for case in cases
        }
        for future in as_completed(futures):
            case = futures[future]
            try:
                record = future.result()
            except Exception as exc:
                record = {
                    "case_id": case["case_id"], "case_version": str(case["case_version"]),
                    "status": "error", "errors": [{"type": type(exc).__name__, "detail": str(exc)}],
                }
            records.append(record)
            manifest["cases"] = sorted(records, key=lambda row: row["case_id"])
            partial_counts: dict[str, int] = {}
            for completed in records:
                partial_counts[completed["status"]] = partial_counts.get(completed["status"], 0) + 1
            manifest["status_counts"] = partial_counts
            manifest["completed_case_count"] = len(records)
            manifest["updated_at"] = utc_now()
            write_json(suite_root / "manifest.json", manifest)
            print(f"Complete case {record['case_id']}: {record['status']}", flush=True)

    records.sort(key=lambda row: row["case_id"])
    counts: dict[str, int] = {}
    for record in records:
        counts[record["status"]] = counts.get(record["status"], 0) + 1
    manifest.update({
        "status": "complete", "finished_at": utc_now(), "status_counts": counts,
        "elapsed_seconds": round(time.monotonic() - suite_started, 2), "cases": records,
    })
    write_json(suite_root / "manifest.json", manifest)
    return {"suite_run_id": suite_run_id, "suite_root": str(suite_root), **manifest}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run isolated complete-analysis evaluation cases")
    parser.add_argument("--suite", required=True)
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--model", default="claude-opus-4-6")
    parser.add_argument("--parallelism", type=int, default=4)
    parser.add_argument("--timeout", type=int, default=1800)
    parser.add_argument("--max-budget-usd", type=float, help="Optional per-worker model cost limit, not a suite total")
    parser.add_argument("--deny-read-root", action="append", default=[], help="Additional local reference/authoring directory excluded from SQL worker reads")
    parser.add_argument("--case-id", action="append", dest="case_ids")
    parser.add_argument("--context-store", help="Snapshot a context store for this run without changing project configuration")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    payload = run_complete_suite(
        project_root=args.project_root,
        suite_path=args.suite,
        model=args.model,
        parallelism=args.parallelism,
        timeout=args.timeout,
        selected_case_ids=args.case_ids,
        context_store=args.context_store,
        max_budget_usd=args.max_budget_usd,
        reference_roots=args.deny_read_root,
    )
    print(json.dumps({
        "suite_run_id": payload["suite_run_id"],
        "suite_root": payload["suite_root"],
        "requested_case_count": payload["requested_case_count"],
        "requested_parallelism": payload["requested_parallelism"],
        "actual_parallelism": payload["actual_parallelism"],
        "elapsed_seconds": payload["elapsed_seconds"],
        "status_counts": payload["status_counts"],
        "cases": [
            {
                "case_id": record["case_id"],
                "run_id": record.get("run_id"),
                "status": record["status"],
                "latency_seconds": record.get("latency_seconds"),
            }
            for record in payload["cases"]
        ],
    }, indent=2, sort_keys=True, default=str))


if __name__ == "__main__":
    main()
