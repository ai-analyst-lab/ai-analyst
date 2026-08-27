"""Findings manifest (provenance, 0.8b).

A reported number is a "finding". Recording it with a stable finding_id — and, when the agent knows
them, the query_ids it came from — is what lets the reconciler tie numbers back to the SQL that
produced them. Written to working/findings_{analysis_id}.jsonl. Two writers (defense in depth):
the analyst calls record_finding when it reports a number (the cited path), and a Stop-hook backstop
records any it missed. See PROVENANCE-IDS-SPEC.md.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from helpers.knowledge.analysis_context import current_analysis_id


def _path(analysis_id, working_dir=None) -> Path:
    base = Path(working_dir) if working_dir else Path("working")
    return base / f"findings_{analysis_id}.jsonl"


def read_findings(analysis_id, working_dir=None) -> list[dict]:
    """Read the findings recorded for an analysis (empty list if none)."""
    p = _path(analysis_id, working_dir)
    if not p.exists():
        return []
    out = []
    for line in p.read_text().splitlines():
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def record_finding(value, text, query_ids=None, analysis_id=None, working_dir=None) -> dict:
    """Append a finding with a stable finding_id ({analysis_id}.f{NN}, sequential within the analysis).

    value: the reported number. text: the claim in words. query_ids: the queries it came from, if the
    agent knows them (the cited, highest-confidence link). Returns the written entry."""
    if analysis_id is None:
        analysis_id = current_analysis_id(create=True, working_dir=working_dir)
    seq = len(read_findings(analysis_id, working_dir)) + 1
    entry = {
        "finding_id": f"{analysis_id}.f{seq:02d}",
        "analysis_id": analysis_id,
        "value": value,
        "text": text,
        "query_ids": query_ids or [],
        "timestamp": datetime.now().isoformat(),
    }
    p = _path(analysis_id, working_dir)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a") as f:
        f.write(json.dumps(entry) + "\n")
    return entry
