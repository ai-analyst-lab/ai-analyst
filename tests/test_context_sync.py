from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml

from helpers.knowledge.context_sync import ContextSyncError, resolve_context_dir, resolved_commit


def _git(cwd: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)
    return result.stdout.strip()


def _source_repo(tmp_path: Path) -> Path:
    source = tmp_path / "source"
    source.mkdir()
    _git(source, "init", "-b", "main")
    _git(source, "config", "user.email", "course@example.com")
    _git(source, "config", "user.name", "Course Test")
    dataset = source / "datasets" / "novamart"
    dataset.mkdir(parents=True)
    (dataset / "marker.txt").write_text("one\n")
    _git(source, "add", ".")
    _git(source, "commit", "-m", "first")
    return source


def _project(tmp_path: Path, source: Path) -> Path:
    project = tmp_path / "project"
    knowledge = project / ".knowledge"
    knowledge.mkdir(parents=True)
    (knowledge / "context-source.yaml").write_text(
        yaml.safe_dump(
            {
                "source": "git",
                "repo": str(source),
                "ref": "main",
                "dataset_path": "datasets/novamart",
                "cache": ".knowledge/.context-cache",
            }
        )
    )
    return project


def test_resolver_picks_up_a_second_committed_change(tmp_path):
    source = _source_repo(tmp_path)
    project = _project(tmp_path, source)
    resolved, kind = resolve_context_dir("novamart", project)
    first = resolved_commit(project / ".knowledge" / ".context-cache")
    assert kind == "git"
    assert (resolved / "marker.txt").read_text() == "one\n"

    (source / "datasets" / "novamart" / "marker.txt").write_text("two\n")
    _git(source, "add", ".")
    _git(source, "commit", "-m", "second")

    resolved_again, _ = resolve_context_dir("novamart", project)
    second = resolved_commit(project / ".knowledge" / ".context-cache")
    assert second != first
    assert (resolved_again / "marker.txt").read_text() == "two\n"


def test_missing_dataset_path_fails_clearly(tmp_path):
    source = _source_repo(tmp_path)
    project = _project(tmp_path, source)
    config_path = project / ".knowledge" / "context-source.yaml"
    config = yaml.safe_load(config_path.read_text())
    config["dataset_path"] = "datasets/missing"
    config_path.write_text(yaml.safe_dump(config))
    with pytest.raises(ContextSyncError, match="dataset path does not exist"):
        resolve_context_dir("novamart", project)


def test_invalid_repository_fails_instead_of_returning_stale_path(tmp_path):
    project = _project(tmp_path, tmp_path / "does-not-exist")
    with pytest.raises(ContextSyncError, match="git clone"):
        resolve_context_dir("novamart", project)
