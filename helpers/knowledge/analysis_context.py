"""Current-analysis context (provenance infra, 0.8a).

A small, stable id for the analysis in flight, persisted to working/current-analysis.json so every
logged query and action can be stamped with it — the provenance grouping key — without any agent
bookkeeping. The query hook reads it at fire time (creating one on the first query of a session);
the reconciler later groups a run's queries and findings by it. See PROVENANCE-IDS-SPEC.md.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path

_FILENAME = "current-analysis.json"


def _path(working_dir=None) -> Path:
    base = Path(working_dir) if working_dir else Path("working")
    return base / _FILENAME


def current_analysis_id(create=True, working_dir=None):
    """Return the current analysis_id. Stable across calls because it is persisted to disk.
    Creates one if none exists and create=True; returns None if absent and create=False."""
    p = _path(working_dir)
    if p.exists():
        try:
            return (json.loads(p.read_text()) or {}).get("analysis_id")
        except Exception:
            pass
    return start_analysis(working_dir=working_dir) if create else None


def start_analysis(working_dir=None):
    """Begin a fresh analysis: mint a new id, persist it, return it."""
    aid = f"an_{datetime.now().strftime('%Y%m%d')}_{uuid.uuid4().hex[:4]}"
    p = _path(working_dir)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"analysis_id": aid, "started_at": datetime.now().isoformat()}))
    return aid


def clear_analysis(working_dir=None):
    """Remove the current-analysis marker (end of an analysis)."""
    p = _path(working_dir)
    if p.exists():
        p.unlink()
