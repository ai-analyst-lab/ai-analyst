"""Run one narrow model judge inside an auditable file-limited workspace."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import time
from typing import Any, Callable

from .workspace import ClaudeCommand


FORBIDDEN_NAME_FRAGMENTS = (
    "human-label",
    "human_label",
    "answer-key",
    "answer_key",
    "captured-verdict",
    "captured_verdict",
    "prior-verdict",
    "prior_verdict",
)


def run_isolated_judge(
    *,
    charts: list[str | Path],
    rubric: str | Path,
    output_dir: str | Path,
    version: str,
    model: str = "claude-opus-4-6",
    timeout: int = 600,
    runner_factory: Callable[..., ClaudeCommand] = ClaudeCommand,
) -> dict[str, Any]:
    if not charts:
        raise ValueError("at least one chart is required")
    chart_paths = [Path(path).resolve() for path in charts]
    rubric_path = Path(rubric).resolve()
    sources = chart_paths + [rubric_path]
    if len({path.name for path in sources}) != len(sources):
        raise ValueError("judge input file names must be unique")
    for path in sources:
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"judge input is missing or unsafe: {path}")
        lowered = path.name.casefold()
        if any(fragment in lowered for fragment in FORBIDDEN_NAME_FRAGMENTS):
            raise ValueError(f"judge input name may expose review evidence: {path.name}")

    output = Path(output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    schema = {
        "type": "object",
        "properties": {
            "verdicts": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "chart": {"type": "string"},
                        "title_claim": {"type": "string"},
                        "visible_evidence": {"type": "string"},
                        "reason": {"type": "string"},
                        "verdict": {"type": "string", "enum": ["pass", "fail", "unknown"]},
                    },
                    "required": ["chart", "title_claim", "visible_evidence", "reason", "verdict"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["verdicts"],
        "additionalProperties": False,
    }

    run_started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix=f"ai-analyst-judge-{version}-") as temporary:
        workspace = Path(temporary).resolve()
        fresh_workspace_id = workspace.name
        for chart in chart_paths:
            shutil.copy2(chart, workspace / chart.name)
        shutil.copy2(rubric_path, workspace / "rubric.md")
        files = sorted(path.name for path in workspace.iterdir() if path.is_file())
        expected = sorted([path.name for path in chart_paths] + ["rubric.md"])
        if files != expected:
            raise ValueError(f"judge workspace contains unexpected files: {files}")

        prompt = (
            "Read rubric.md and evaluate every PNG file in this directory. "
            "Use only visible chart content and the rubric. Return one verdict record per chart. "
            "Do not infer hidden data, analytical methods, or human labels."
        )
        command = runner_factory(model=model, timeout_seconds=timeout, allowed_tools=("Read", "Glob"))
        prompt_sha256 = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        rubric_sha256 = hashlib.sha256((workspace / "rubric.md").read_bytes()).hexdigest()
        input_hashes = {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(workspace.iterdir())
            if path.is_file()
        }
        sanitized_argv = []
        command_sha256 = None
        if hasattr(command, "argv"):
            argv = command.argv(prompt, json_schema=schema)
            sanitized_argv = list(argv)
            if sanitized_argv:
                sanitized_argv[-1] = f"<prompt sha256:{prompt_sha256}>"
            if "--json-schema" in sanitized_argv:
                index = sanitized_argv.index("--json-schema") + 1
                schema_hash = hashlib.sha256(
                    json.dumps(schema, sort_keys=True, separators=(",", ":")).encode("utf-8")
                ).hexdigest()
                sanitized_argv[index] = f"<schema sha256:{schema_hash}>"
            command_sha256 = hashlib.sha256(
                json.dumps(sanitized_argv, separators=(",", ":")).encode("utf-8")
            ).hexdigest()
        result = command.run(workspace, prompt, json_schema=schema)
        duration_seconds = round(time.monotonic() - run_started, 3)

        execution_metadata = result.get("execution_metadata") or {}
        workspace_inventory = execution_metadata.get("workspace_inventory") or [
            {
                "path": name,
                "sha256": input_hashes[name],
                "bytes": (workspace / name).stat().st_size,
            }
            for name in expected
        ]

    structured_result = result.get("structured_result") or {}
    output_sha256 = hashlib.sha256(
        json.dumps(structured_result, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()

    isolation = {
        "version": version,
        "model": model,
        "allowed_files": expected,
        "allowed_tools": ["Read", "Glob"],
        "effective_process_tools": (
            (result.get("execution_metadata") or {}).get("effective_process_tools")
            or ["Read", "Glob"]
        ),
        "sanitized_argv": (
            (result.get("execution_metadata") or {}).get("sanitized_argv")
            or sanitized_argv
        ),
        "command_sha256": (
            (result.get("execution_metadata") or {}).get("command_sha256")
            or command_sha256
        ),
        "prompt_sha256": prompt_sha256,
        "rubric_sha256": rubric_sha256,
        "input_hashes": input_hashes,
        "workspace_inventory": workspace_inventory,
        "fresh_workspace_id": fresh_workspace_id,
        "forbidden_name_scan": {
            "status": "passed",
            "checked_files": expected,
            "forbidden_fragments": list(FORBIDDEN_NAME_FRAGMENTS),
        },
        "output_sha256": output_sha256,
        "duration_seconds": duration_seconds,
        "session_persistence": False,
        "human_labels_available": False,
        "prior_verdicts_available": False,
        "captured_verdicts_available": False,
        "status": result.get("status", "unknown"),
        "errors": result.get("errors", []),
    }
    (output / f"judge-{version}-isolation.json").write_text(
        json.dumps(isolation, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    verdicts = structured_result.get("verdicts", [])
    verdict_path = output / f"judge-{version}-verdicts.csv"
    with verdict_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["chart", "title_claim", "visible_evidence", "reason", "verdict"],
        )
        writer.writeheader()
        writer.writerows(verdicts)
    return {"isolation": isolation, "verdicts": verdicts, "verdict_path": str(verdict_path)}
