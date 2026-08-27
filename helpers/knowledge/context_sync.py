"""Resolve where the analyst reads its context from: local (in this tool) or a communal git repo.

Reads .knowledge/context-source.yaml. If source is 'git', clone (or pull) the communal context repo into a
local cache and return the dataset directory inside it. If 'local' (or no config), return the in-repo
dataset directory. knowledge-bootstrap calls this BEFORE loading the semantic layer, so the same loader
works whether context lives in the tool (the C0-C2 individual setup) or in the team's repo (the C3 team
setup). The team curates the context repo via PRs; each analyst points at it and pulls.

Only context is synced here (semantic layer + metric defs). The gold/answer-key is never in the context
repo; it stays hidden with the eval harness.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any, List, Optional


def _git(*args: str) -> int:
    return subprocess.run(["git", *args], capture_output=True, text=True).returncode


def check_schema_drift(context_dir: str | Path, conn: Any) -> List[dict]:
    """Run the schema-diff guard over a resolved context dir and warn on drift.

    Recomputes each table-backed definition's live schema and compares to its known-good snapshot.
    Any definition whose table changed shape is quarantined (marked, never deleted) so the agent will
    not trust it until a human re-verifies. Prints a warning per quarantined definition and returns
    the quarantine list. A clean context returns []."""
    from helpers.data.schema_guard import guard_context

    quarantined = guard_context(conn, context_dir)
    for q in quarantined:
        print(
            f"[schema-guard] QUARANTINED definition '{q['name']}' (table {q['table']}): "
            f"live schema no longer matches the verified snapshot "
            f"(stored {q['stored_checksum']} != current {q['current_checksum']}). "
            f"The agent will not use it until it is re-verified.",
            file=sys.stderr,
        )
    return quarantined


def resolve_context_dir(
    active_dataset: str,
    project_root: str | Path = ".",
    conn: Optional[Any] = None,
) -> tuple[Path, str]:
    """Return (dataset_context_dir, source) where source is 'local' or 'git'.

    dataset_context_dir is the directory that holds this dataset's semantic/ and metrics/ - either the
    in-repo .knowledge/datasets/{active}/ (local) or the synced communal repo's dataset path (git).

    When a live connection (conn) is supplied, the schema-diff guard runs over the resolved context
    before it is trusted: every table-backed definition is checked against its verified schema
    snapshot, and a definition whose table changed shape is quarantined and warned about. This is the
    load-time drift check; with no conn the guard is skipped (the 2-tuple contract is unchanged)."""
    root = Path(project_root)
    local_dir = root / ".knowledge" / "datasets" / active_dataset
    cfg_path = root / ".knowledge" / "context-source.yaml"
    if not cfg_path.exists():
        if conn is not None:
            check_schema_drift(local_dir, conn)
        return local_dir, "local"

    import yaml
    cfg = yaml.safe_load(cfg_path.read_text()) or {}
    if cfg.get("source", "local") != "git":
        if conn is not None:
            check_schema_drift(local_dir, conn)
        return local_dir, "local"

    repo = cfg["repo"]
    ref = str(cfg.get("ref", "main"))
    dataset_path = cfg.get("dataset_path", f"datasets/{active_dataset}")
    cache = root / cfg.get("cache", ".knowledge/.context-cache")

    if (cache / ".git").exists():
        # Already cloned: fetch + checkout + pull the ref (latest team context, or a pinned commit).
        _git("-C", str(cache), "fetch", "--quiet", "origin", ref)
        _git("-C", str(cache), "checkout", "--quiet", ref)
        _git("-C", str(cache), "pull", "--quiet", "origin", ref)
    else:
        cache.parent.mkdir(parents=True, exist_ok=True)
        _git("clone", "--quiet", repo, str(cache))
        _git("-C", str(cache), "checkout", "--quiet", ref)

    resolved = cache / dataset_path
    if conn is not None:
        check_schema_drift(resolved, conn)
    return resolved, "git"
