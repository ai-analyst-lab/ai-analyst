"""Reproducible fingerprints for systems, evaluators, and data."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Iterable

DEFAULT_SYSTEM_PATHS = (
    ".claude/skills",
    ".claude/agents",
    "agents",
    "helpers",
    ".knowledge",
    "workflows",
    "data_sources.yaml",
    "CLAUDE.md",
)


def file_digest(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def payload_digest(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(encoded).hexdigest()


def _iter_files(root: Path, entries: Iterable[str]) -> list[Path]:
    files = []
    for entry in entries:
        path = root / entry
        if path.is_file() and not path.is_symlink():
            files.append(path)
        elif path.is_dir():
            files.extend(
                candidate
                for candidate in path.rglob("*")
                if candidate.is_file()
                and not candidate.is_symlink()
                and "__pycache__" not in candidate.parts
                and candidate.suffix not in {".pyc", ".pyo"}
            )
    return sorted(set(files))


def tree_fingerprint(root: str | Path, entries: Iterable[str] = DEFAULT_SYSTEM_PATHS) -> dict:
    root = Path(root).resolve()
    file_map = {
        str(path.relative_to(root)).replace("\\", "/"): file_digest(path)
        for path in _iter_files(root, entries)
    }
    return {"digest": payload_digest(file_map), "file_count": len(file_map), "files": file_map}


def git_identity(root: str | Path) -> dict:
    root = Path(root)

    def git(*args: str) -> str | None:
        try:
            return subprocess.check_output(
                ["git", "-C", str(root), *args], text=True, stderr=subprocess.DEVNULL
            ).strip()
        except (OSError, subprocess.CalledProcessError):
            return None

    status = git("status", "--porcelain=v1")
    return {
        "commit": git("rev-parse", "HEAD"),
        "branch": git("branch", "--show-current"),
        "dirty": bool(status),
        "status_digest": payload_digest(status or ""),
    }


def system_fingerprint(root: str | Path) -> dict:
    tree = tree_fingerprint(root)
    return {"system_digest": tree["digest"], "tree": tree, "git": git_identity(root)}


def data_fingerprint(paths: Iterable[str | Path]) -> dict:
    records = []
    for raw in paths:
        path = Path(raw).resolve()
        if not path.exists() or not path.is_file():
            records.append({"path": str(path), "status": "missing"})
            continue
        records.append(
            {"path": str(path), "bytes": path.stat().st_size, "sha256": file_digest(path)}
        )
    return {"digest": payload_digest(records), "files": records}
