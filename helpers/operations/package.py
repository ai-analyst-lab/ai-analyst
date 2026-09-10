"""Scaffold and validate the inspectable Analyst v1 package."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from helpers.operations.manifest import load_manifest


REQUIRED_FILES = {
    "README.md", "OPERATOR-GUIDE.md", "system-manifest.yaml", "evaluation-scorecard.md",
    "context-inventory.md", "engine-decision.md", "routing-policy.yaml", "autonomy-policy.yaml",
    "LIMITATIONS.md", "release-and-rollback.md", "value-scorecard.md", "30-day-plan.md",
}


def validate_package(directory: str | Path) -> dict[str, Any]:
    root = Path(directory).resolve()
    missing = sorted(name for name in REQUIRED_FILES if not (root / name).is_file())
    manifest_error = None
    if not missing or "system-manifest.yaml" not in missing:
        try:
            load_manifest(root / "system-manifest.yaml")
        except (OSError, ValueError) as exc:
            manifest_error = str(exc)
    return {
        "status": "complete" if not missing and not manifest_error else "incomplete",
        "directory": str(root), "missing": missing, "manifest_error": manifest_error,
        "claim": "This checks package presence and internal references, not analytical truth.",
    }
