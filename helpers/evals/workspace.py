"""Sanitized trial workspaces and the Claude Code command adapter."""

from __future__ import annotations

import json
import os
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

    def build(self, destination: str | Path, case: EvaluationCase) -> Path:
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
            prompt,
        ]

    def run(
        self,
        workspace: str | Path,
        prompt: str,
        json_schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Run one noninteractive trial inside an already sanitized workspace."""
        completed = subprocess.run(
            self.argv(prompt, json_schema=json_schema),
            cwd=Path(workspace),
            text=True,
            capture_output=True,
            timeout=self.timeout_seconds,
            env=_child_environment(),
            check=False,
        )
        if completed.returncode != 0:
            return {
                "status": "error",
                "raw_output": completed.stdout,
                "structured_result": {},
                "errors": [
                    {
                        "type": "claude_exit",
                        "returncode": completed.returncode,
                        "stderr": completed.stderr[-4000:],
                    }
                ],
            }
        try:
            envelope = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            return {
                "status": "error",
                "raw_output": completed.stdout,
                "structured_result": {},
                "errors": [{"type": "invalid_json", "detail": str(exc)}],
            }
        result = envelope.get("structured_output", envelope.get("result", envelope))
        structured = result if isinstance(result, dict) else {"answer": result}
        return {
            "status": "completed",
            "raw_output": completed.stdout,
            "structured_result": structured,
            "errors": [],
            "cost_usd": envelope.get("total_cost_usd"),
        }


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
