"""Run complete-analysis evaluation cases in isolated Claude Code workspaces."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import tempfile
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Callable

import yaml
from dotenv import load_dotenv

from .full_analysis import start_run
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
        elif name.endswith((".pyc", ".pyo")):
            ignored.add(name)
        elif candidate.parts[-3:] == ("evals", "focused", "working-references"):
            ignored.add(name)
        elif candidate.parts[-2:] == ("evals", "examples"):
            ignored.add(name)
        elif candidate.parts[-2:] == (".knowledge", ".context-cache"):
            ignored.add(name)
    return ignored


def build_isolated_workspace(project_root: Path, destination: Path) -> dict[str, Any]:
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


def _copy_run(source: Path, destination_root: Path) -> Path:
    destination = destination_root / source.name
    if destination.exists():
        raise ValueError(f"run destination already exists: {destination}")
    shutil.copytree(source, destination)
    return destination


def _execute_case(
    *,
    project_root: Path,
    case: dict[str, Any],
    model: str,
    timeout: int,
    runs_root: Path,
    command_factory: Callable[..., ClaudeCommand] = ClaudeCommand,
) -> dict[str, Any]:
    started = time.monotonic()
    case_id = str(case["case_id"])
    with tempfile.TemporaryDirectory(prefix=f"ai-analyst-full-eval-{case_id}-") as temporary:
        workspace = Path(temporary) / "ai-analyst"
        audit = build_isolated_workspace(project_root, workspace)
        case_path = workspace / str(case["path"])
        started_run = start_run(
            project_root=workspace,
            case_dir=case_path,
            runs_root=workspace / "working" / "evals" / "runs",
            model=model,
        )
        run_root = Path(started_run["run_root"])
        prompt = (
            f"Execute the complete evaluation run {started_run['run_id']}. "
            "Read its RUN-INSTRUCTIONS.md and public case. Use the repository's trace skill "
            "and Snowflake connection helpers rather than creating trace files manually. Perform the analysis with the "
            "configured Snowflake connection, create every required artifact, maintain one "
            "complete analysis trace, inspect the work, and lock the run. Do not use any "
            "incomplete-trace or snapshot-verification bypass. If required trace evidence is "
            "missing, repair the trace before locking. Work autonomously. "
            "Do not inspect parent directories or search for any evaluator, expected answer, "
            "reference query, or grader repository. Return the run ID and final lock status."
        )
        command = command_factory(
            model=model,
            timeout_seconds=timeout,
            allowed_tools=("Read", "Glob", "Grep", "Bash"),
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
            "status": "locked" if locked else "invalid",
            "run_manifest_status": manifest.get("status"),
            "trace_complete": bool(trace_manifest.get("complete")),
            "data_fingerprint_status": (manifest.get("data_fingerprint") or {}).get("status"),
            "errors": result.get("errors") or [],
            "latency_seconds": round(time.monotonic() - started, 2),
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

    load_dotenv(project_root / ".env", override=False)
    suite_started = time.monotonic()
    suite_run_id = f"full-suite-{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}-{uuid.uuid4().hex[:8]}"
    suite_root = project_root / "working" / "evals" / "suites" / suite_run_id
    runs_root = project_root / "working" / "evals" / "runs"
    suite_root.mkdir(parents=True, exist_ok=False)
    runs_root.mkdir(parents=True, exist_ok=True)
    requested_parallelism = max(1, parallelism)
    actual_parallelism = min(requested_parallelism, len(cases))
    manifest = {
        "schema_version": "1", "suite_run_id": suite_run_id,
        "suite_id": suite["suite_id"], "suite_version": str(suite.get("suite_version", "1")),
        "status": "running", "model": model, "created_at": utc_now(),
        "requested_case_count": len(cases), "requested_parallelism": requested_parallelism,
        "actual_parallelism": actual_parallelism, "cases": [],
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
    parser.add_argument("--case-id", action="append", dest="case_ids")
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
