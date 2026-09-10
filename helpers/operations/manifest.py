"""System manifest loading and consistency checks."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


REQUIRED = {
    "schema_version", "name", "version", "purpose", "supported_uses", "prohibited_uses",
    "owner", "reviewers", "data_dependencies", "tool_dependencies", "context",
    "workflows", "engine_config", "routing_policy", "evaluation", "invocation",
    "outputs", "monitoring", "last_release", "next_review",
}


def load_manifest(path: str | Path) -> dict[str, Any]:
    file = Path(path).resolve()
    value = yaml.safe_load(file.read_text(encoding="utf-8")) or {}
    missing = sorted(REQUIRED - set(value))
    if missing:
        raise ValueError(f"System manifest is missing: {', '.join(missing)}")
    if value["schema_version"] != 1:
        raise ValueError("Only system manifest schema version 1 is supported")
    if not isinstance(value["workflows"], dict) or not value["workflows"]:
        raise ValueError("System manifest needs at least one named workflow")
    root = file.parent
    for key in ("engine_config", "routing_policy"):
        target = (root / value[key]).resolve()
        if not target.is_relative_to(root) or not target.is_file():
            raise ValueError(f"Manifest reference is missing or unsafe: {key}")
    return value
