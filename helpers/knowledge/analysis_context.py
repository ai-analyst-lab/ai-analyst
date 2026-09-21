"""Current-analysis context.

A small, stable id for the analysis in flight, persisted to
``working/current-analysis.json`` so every logged query and action can be
stamped with the same provenance grouping key.  Starting an analysis also
writes an immutable ``working/analysis_<id>.json`` record.  The latter keeps
the question and decision available after another analysis becomes current.
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


def current_analysis(working_dir=None) -> dict | None:
    """Return the current analysis record, or ``None`` when none is active."""
    p = _path(working_dir)
    if not p.exists():
        return None
    try:
        value = json.loads(p.read_text())
        return value if isinstance(value, dict) else None
    except Exception:
        return None


def analysis_record(analysis_id, working_dir=None) -> dict | None:
    """Return the durable record for ``analysis_id`` when it exists."""
    base = Path(working_dir) if working_dir else Path("working")
    p = base / f"analysis_{analysis_id}.json"
    if not p.exists():
        current = current_analysis(working_dir)
        if current and current.get("analysis_id") == analysis_id:
            return current
        return None
    try:
        value = json.loads(p.read_text())
        return value if isinstance(value, dict) else None
    except Exception:
        return None


def start_analysis(
    working_dir=None,
    *,
    question=None,
    intended_decision=None,
    dataset=None,
    output_dir=None,
):
    """Begin a fresh analysis and persist its identity and framing.

    Calling this function always creates a new id.  It must be called at the
    start of a distinct analytical task rather than relying on an id left by a
    previous conversation.
    """
    aid = f"an_{datetime.now().strftime('%Y%m%d')}_{uuid.uuid4().hex[:4]}"
    p = _path(working_dir)
    p.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "analysis_id": aid,
        "started_at": datetime.now().isoformat(),
        "question": question,
        "intended_decision": intended_decision,
        "dataset": dataset,
        "output_dir": str(output_dir) if output_dir else None,
    }
    p.write_text(json.dumps(record, indent=2, default=str) + "\n")
    (p.parent / f"analysis_{aid}.json").write_text(
        json.dumps(record, indent=2, default=str) + "\n"
    )
    return aid


def clear_analysis(working_dir=None):
    """Remove the current-analysis marker (end of an analysis)."""
    p = _path(working_dir)
    if p.exists():
        p.unlink()
