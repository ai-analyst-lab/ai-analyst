"""Sanitized trial workspaces and the Claude Code command adapter."""

from __future__ import annotations

import json
import hashlib
import os
import signal
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .schema import EvaluationCase

DEFAULT_ALLOWED_ENTRIES = (
    "CLAUDE.md",
    ".claude/skills",
    "agents",
    "helpers",
    ".knowledge",
    "data_sources.yaml",
)
FORBIDDEN_PARTS = frozenset(
    {
        "ground_truth",
        "answer_key",
        "heldout_answers",
        "private_grader",
        "grader_credentials",
    }
)


def _is_forbidden(path: Path) -> bool:
    lowered = "/".join(path.parts).casefold()
    return any(part in lowered for part in FORBIDDEN_PARTS)


class SanitizedWorkspaceBuilder:
    def __init__(self, source_root: str | Path, allowed_entries=DEFAULT_ALLOWED_ENTRIES):
        self.source_root = Path(source_root).resolve()
        self.allowed_entries = tuple(allowed_entries)

    def build(
        self,
        destination: str | Path,
        case: EvaluationCase,
        data_paths: tuple[str | Path, ...] = (),
    ) -> Path:
        destination = Path(destination).resolve()
        destination.mkdir(parents=True, exist_ok=False)
        for entry in self.allowed_entries:
            source = (self.source_root / entry).resolve()
            if not source.exists() or _is_forbidden(Path(entry)):
                continue
            if self.source_root not in source.parents and source != self.source_root:
                raise ValueError(f"allowed entry escapes source root: {entry}")
            target = destination / entry
            if source.is_symlink():
                raise ValueError(f"symlink is not allowed in trial workspace: {entry}")
            if source.is_dir():
                shutil.copytree(
                    source,
                    target,
                    symlinks=False,
                    ignore=_copy_ignore,
                )
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)

        for entry in case.data_scope.get("workspace_files", []):
            relative = Path(entry)
            if relative.is_absolute() or ".." in relative.parts or _is_forbidden(relative):
                raise ValueError(f"invalid case workspace file: {entry}")
            source = (self.source_root / relative).resolve()
            if not source.is_file() or source.is_symlink():
                raise ValueError(f"case workspace file is missing or unsafe: {entry}")
            if self.source_root not in source.parents:
                raise ValueError(f"case workspace file escapes source root: {entry}")
            target = destination / "inputs" / relative.name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)

        for entry in case.data_scope.get("workspace_dirs", []):
            relative = Path(entry)
            if relative.is_absolute() or ".." in relative.parts or _is_forbidden(relative):
                raise ValueError(f"invalid case workspace directory: {entry}")
            source = (self.source_root / relative).resolve()
            if not source.is_dir() or source.is_symlink():
                raise ValueError(f"case workspace directory is missing or unsafe: {entry}")
            if self.source_root not in source.parents:
                raise ValueError(f"case workspace directory escapes source root: {entry}")
            for candidate in source.rglob("*"):
                if candidate.is_symlink() or _is_forbidden(candidate.relative_to(source)):
                    raise ValueError(f"case workspace directory contains an unsafe entry: {candidate}")
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(source, target, symlinks=False, ignore=_copy_ignore)

        for raw in data_paths:
            source = Path(raw).resolve()
            if not source.is_file() or source.is_symlink():
                raise ValueError(f"evaluation data file is missing or unsafe: {source}")
            try:
                relative = source.relative_to(self.source_root)
            except ValueError:
                relative = Path("inputs") / "data" / source.name
            if _is_forbidden(relative):
                raise ValueError(f"evaluation data path uses a forbidden name: {relative}")
            target = destination / relative
            if target.exists():
                if target.read_bytes() != source.read_bytes():
                    raise ValueError(f"evaluation data path collides with workspace file: {relative}")
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            target.chmod(0o444)

        task = case.to_dict(public=True)
        (destination / "eval_task.json").write_text(
            json.dumps(task, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8"
        )
        self.audit(destination)
        return destination

    def audit(self, workspace: str | Path) -> dict[str, Any]:
        workspace = Path(workspace).resolve()
        violations = []
        files = []
        for path in workspace.rglob("*"):
            if path.is_symlink():
                violations.append(f"symlink: {path.relative_to(workspace)}")
            if path.is_file():
                relative = path.relative_to(workspace)
                files.append(str(relative).replace("\\", "/"))
                if _is_forbidden(relative):
                    violations.append(f"forbidden name: {relative}")
        if violations:
            raise ValueError(f"workspace isolation audit failed: {violations}")
        return {"files": sorted(files), "file_count": len(files), "violations": []}


def _copy_ignore(directory: str, names: list[str]) -> set[str]:
    ignored = set()
    for name in names:
        candidate = Path(directory) / name
        if name in {".git", ".venv", "__pycache__", "working", "runs", "reliability"}:
            ignored.add(name)
        elif name.endswith((".pyc", ".pyo")) or _is_forbidden(candidate):
            ignored.add(name)
    return ignored


@dataclass
class ClaudeCommand:
    model: str = "claude-opus-4-6"
    timeout_seconds: int = 600
    allowed_tools: tuple[str, ...] = ("Read", "Glob", "Grep")

    def argv(self, prompt: str, json_schema: dict[str, Any] | None = None) -> list[str]:
        tools = ",".join(self.allowed_tools)
        schema = json.dumps(json_schema or {"type": "object", "additionalProperties": True})
        return [
            "claude",
            "--print",
            "--output-format",
            "json",
            "--json-schema",
            schema,
            "--model",
            self.model,
            "--restricted",
            "--strict-mcp-config",
            "--permission-mode",
            "dontAsk",
            "--permission-prompts",
            "none",
            "--no-session-persistence",
            f"--tools={tools}",
            f"--allowedTools={tools}",
            prompt,
        ]

    def run(
        self,
        workspace: str | Path,
        prompt: str,
        json_schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Run one noninteractive trial inside an already sanitized workspace."""
        argv = self.argv(prompt, json_schema=json_schema)
        input_inventory = _file_inventory(workspace)
        started_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(timespec="seconds")
        process = subprocess.Popen(
            argv,
            cwd=Path(workspace),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=_child_environment(),
            start_new_session=os.name != "nt",
            creationflags=(
                subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
            ),
        )
        try:
            stdout, stderr = process.communicate(timeout=self.timeout_seconds)
        except subprocess.TimeoutExpired:
            _terminate_process_tree(process)
            result = {
                "status": "error",
                "raw_output": "",
                "structured_result": {},
                "errors": [
                    {
                        "type": "timeout",
                        "timeout_seconds": self.timeout_seconds,
                    }
                ],
            }
            result["execution_metadata"] = self.execution_metadata(
                workspace, prompt, json_schema, argv, started_at, input_inventory
            )
            return result
        if process.returncode != 0:
            result = {
                "status": "error",
                "raw_output": stdout,
                "structured_result": {},
                "errors": [
                    {
                        "type": "claude_exit",
                        "returncode": process.returncode,
                        "stderr": stderr[-4000:],
                    }
                ],
            }
            result["execution_metadata"] = self.execution_metadata(
                workspace, prompt, json_schema, argv, started_at, input_inventory
            )
            return result
        try:
            envelope = json.loads(stdout)
        except json.JSONDecodeError as exc:
            result = {
                "status": "error",
                "raw_output": stdout,
                "structured_result": {},
                "errors": [{"type": "invalid_json", "detail": str(exc)}],
            }
            result["execution_metadata"] = self.execution_metadata(
                workspace, prompt, json_schema, argv, started_at, input_inventory
            )
            return result
        result = envelope.get("structured_output", envelope.get("result", envelope))
        structured = result if isinstance(result, dict) else {"answer": result}
        result = {
            "status": "completed",
            "raw_output": stdout,
            "structured_result": structured,
            "errors": [],
            "cost_usd": envelope.get("total_cost_usd"),
        }
        result["execution_metadata"] = self.execution_metadata(
            workspace, prompt, json_schema, argv, started_at, input_inventory
        )
        return result

    def execution_metadata(
        self,
        workspace: str | Path,
        prompt: str,
        json_schema: dict[str, Any] | None,
        argv: list[str],
        started_at: str,
        input_inventory: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Return a reconstructable record without storing the raw prompt in argv."""
        prompt_hash = _sha256_text(prompt)
        schema_text = json.dumps(json_schema or {}, sort_keys=True, separators=(",", ":"))
        sanitized = list(argv)
        if sanitized:
            sanitized[-1] = f"<prompt sha256:{prompt_hash}>"
        if "--json-schema" in sanitized:
            index = sanitized.index("--json-schema") + 1
            sanitized[index] = f"<schema sha256:{_sha256_text(schema_text)}>"
        final_inventory = _file_inventory(workspace)
        command_text = json.dumps(sanitized, separators=(",", ":"))
        return {
            "sanitized_argv": sanitized,
            "command_sha256": _sha256_text(command_text),
            "prompt_sha256": prompt_hash,
            "json_schema_sha256": _sha256_text(schema_text),
            "effective_process_tools": list(self.allowed_tools),
            "input_file_hashes": input_inventory,
            "workspace_inventory": final_inventory,
            "started_at": started_at,
            "finished_at": __import__("datetime").datetime.now(
                __import__("datetime").timezone.utc
            ).isoformat(timespec="seconds"),
        }


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _file_inventory(workspace: str | Path) -> list[dict[str, Any]]:
    root = Path(workspace).resolve()
    files = []
    for path in sorted(candidate for candidate in root.rglob("*") if candidate.is_file()):
        relative = str(path.relative_to(root)).replace("\\", "/")
        files.append(
            {
                "path": relative,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "bytes": path.stat().st_size,
            }
        )
    return files


def _terminate_process_tree(process: subprocess.Popen[str]) -> None:
    """Stop a timed-out command and descendants that may still hold output pipes."""
    if process.poll() is not None:
        process.communicate()
        return
    if os.name == "nt":
        process.kill()
    else:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    try:
        process.communicate(timeout=5)
        return
    except subprocess.TimeoutExpired:
        if os.name == "nt":
            process.kill()
        else:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        process.communicate()


def _child_environment() -> dict[str, str]:
    """Keep execution essentials and Claude login, but never pass grader secrets."""
    denied_fragments = ("GROUND_TRUTH", "ANSWER_KEY", "GRADER", "HELDOUT", "EVAL_SECRET")
    return {
        key: value
        for key, value in os.environ.items()
        if not any(fragment in key.upper() for fragment in denied_fragments)
    }


def output_schema_for_case(case: EvaluationCase) -> dict[str, Any]:
    """Build a public output contract without exposing the correct result."""
    properties: dict[str, Any] = {}
    required = set()
    for grader in case.graders:
        grader_type = grader.get("type")
        field = grader.get("field")
        if field:
            required.add(field)
            if grader_type == "numeric":
                properties[field] = {"type": ["number", "string"]}
            elif grader_type == "exact":
                properties[field] = {"type": "string"}
                if grader.get("allowed_values"):
                    properties[field]["enum"] = grader["allowed_values"]
            else:
                properties[field] = {}
        for required_field in grader.get("required_fields", []):
            required.add(required_field)
            properties.setdefault(required_field, {})
    properties.setdefault("explanation", {"type": "string"})
    return {
        "type": "object",
        "properties": properties,
        "required": sorted(required),
        "additionalProperties": True,
    }
