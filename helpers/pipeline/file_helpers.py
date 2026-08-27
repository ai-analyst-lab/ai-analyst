"""File utility helpers for atomic writes, content hashing, and directory management."""

from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path

import yaml


def atomic_write(path: str | Path, content: str) -> None:
    """Write content to a file atomically via temp file + os.replace.

    Creates parent directories if they don't exist.
    Cleans up temp file on error.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    fd, tmp_path = tempfile.mkstemp(dir=path.parent, suffix='.tmp')
    try:
        with os.fdopen(fd, 'w') as f:
            f.write(content)
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def atomic_write_yaml(path: str | Path, data: dict) -> None:
    """Write a dict to a YAML file atomically."""
    content = yaml.dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True)
    atomic_write(path, content)


def content_hash(content: str) -> str:
    """Return SHA-256 hash of content (first 16 hex chars)."""
    return hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]


def has_content_changed(path: str | Path, new_content: str) -> bool:
    """Check if new content differs from the existing file.

    Returns True if the file doesn't exist or content has changed.
    """
    path = Path(path)
    if not path.exists():
        return True
    try:
        existing = path.read_text(encoding='utf-8')
        return content_hash(existing) != content_hash(new_content)
    except (OSError, UnicodeDecodeError):
        return True


def ensure_directory(path: str | Path) -> Path:
    """Create directory and all parents if they don't exist. Returns the Path."""
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def list_yaml_files(directory: str | Path) -> list[Path]:
    """List all .yaml and .yml files in a directory (non-recursive)."""
    directory = Path(directory)
    if not directory.is_dir():
        return []
    return sorted(
        [f for f in directory.iterdir() if f.suffix in ('.yaml', '.yml')],
        key=lambda p: p.name
    )


def safe_read_yaml(path: str | Path) -> dict | None:
    """Read a YAML file, returning None if it doesn't exist or fails to parse."""
    path = Path(path)
    if not path.exists():
        return None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    except (yaml.YAMLError, OSError):
        return None
