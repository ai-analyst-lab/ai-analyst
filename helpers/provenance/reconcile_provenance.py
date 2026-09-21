"""Reconcile findings to the queries that produced them, labeled by confidence (provenance, 0.8b).

Per finding, in priority order:
  cited        — the finding named the query_ids explicitly (highest confidence)
  value-match  — a query's result_value equals the finding's value (within rel tol); reliable now that
                 the hook captures result_value for scalar results
  inferred     — temporal proximity: the most recent query at/before the finding (lowest confidence)
Unmatched findings and orphan queries are surfaced, never hidden (the "no silent caps" rule). The
output feeds the /trace viewer (0.9); the confidence label is itself honest provenance.
"""
from __future__ import annotations

import json
from pathlib import Path


def _num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _value_match(query_value, finding_value, rel_tol):
    a, b = _num(query_value), _num(finding_value)
    if a is None or b is None:
        return False
    if b == 0:
        return abs(a) < rel_tol
    return abs(a - b) / abs(b) < rel_tol


def _preview_value_match(query, finding_value, rel_tol):
    """Return true when a bounded structured query result contains the value."""
    for row in query.get("result_preview") or []:
        if not isinstance(row, dict):
            continue
        for value in row.values():
            if _value_match(value, finding_value, rel_tol):
                return True
    return False


def reconcile(findings, query_entries, rel_tol=0.001):
    """Link findings to queries by confidence. Pure: no IO. Returns
    {links: [{finding_id, query_id, confidence}], unmatched_findings: [...], orphan_queries: [...]}."""
    known_qids = {q.get("query_id") for q in query_entries}
    links, matched_q, unmatched = [], set(), []

    for f in findings:
        fid = f.get("finding_id")
        hit = False

        # 1. cited — explicit query_ids the agent recorded
        for qid in (f.get("query_ids") or []):
            if qid in known_qids:
                links.append({"finding_id": fid, "query_id": qid, "confidence": "cited"})
                matched_q.add(qid)
                hit = True
        if hit:
            continue

        # 2. value-match: a scalar or bounded structured result contains the value
        for q in query_entries:
            if (_value_match(q.get("result_value"), f.get("value"), rel_tol)
                    or _preview_value_match(q, f.get("value"), rel_tol)):
                links.append({"finding_id": fid, "query_id": q.get("query_id"), "confidence": "value-match"})
                matched_q.add(q.get("query_id"))
                hit = True
        if hit:
            continue

        # 3. inferred — the most recent query at/before the finding's timestamp
        ft = f.get("timestamp")
        cand = [q for q in query_entries
                if q.get("timestamp") and (ft is None or q["timestamp"] <= ft)]
        if cand:
            q = max(cand, key=lambda q: q["timestamp"])
            links.append({"finding_id": fid, "query_id": q.get("query_id"), "confidence": "inferred"})
            matched_q.add(q.get("query_id"))
            hit = True

        if not hit:
            unmatched.append(fid)

    orphans = [q.get("query_id") for q in query_entries if q.get("query_id") not in matched_q]
    return {"links": links, "unmatched_findings": unmatched, "orphan_queries": orphans}


def reconcile_analysis(analysis_id, dataset, date, working_dir=None, rel_tol=0.001):
    """IO wrapper: load this analysis's findings + query-log entries, reconcile, write
    working/provenance_{analysis_id}.json (the canonical linkage the /trace viewer reads). Returns
    the written dict. Does not mutate the query log."""
    from helpers.knowledge.findings import read_findings
    from helpers.provenance import query_log as ql

    if working_dir is not None:
        ql.set_log_dir(working_dir)
    findings = read_findings(analysis_id, working_dir)
    entries = [e for e in ql.read_log(dataset, date) if e.get("analysis_id") == analysis_id]
    rec = reconcile(findings, entries, rel_tol)

    base = Path(working_dir) if working_dir else Path("working")
    from helpers.knowledge.analysis_context import analysis_record
    analysis = analysis_record(analysis_id, working_dir=working_dir) or {"analysis_id": analysis_id}

    actions = []
    action_path = base / f"action_log_{date}.jsonl"
    if action_path.exists():
        for line in action_path.read_text().splitlines():
            try:
                action = json.loads(line)
            except json.JSONDecodeError:
                continue
            if action.get("analysis_id") == analysis_id:
                actions.append(action)

    identities = [e.get("connection_identity") for e in entries if e.get("connection_identity")]
    source = {
        "dataset": dataset,
        "tables": sorted({table for entry in entries for table in (entry.get("tables_accessed") or [])}),
        "connection": identities[-1] if identities else {},
    }
    receipt = {
        "analysis_id": analysis_id,
        "question": analysis.get("question"),
        "intended_decision": analysis.get("intended_decision"),
        "claim": [f.get("text") for f in findings if f.get("text")],
        "source": source,
        "data_snapshot": {
            "first_query_at": entries[0].get("timestamp") if entries else None,
            "last_query_at": entries[-1].get("timestamp") if entries else None,
            "source_freshness": "not recorded",
        },
        "query": [e.get("sql") for e in entries if e.get("sql")],
        "query_ids": [e.get("query_id") for e in entries if e.get("query_id")],
        "finding_ids": [f.get("finding_id") for f in findings if f.get("finding_id")],
        "action_count": len(actions),
    }
    receipt_path = base / f"trace_receipt_{analysis_id}.json"
    receipt_path.write_text(json.dumps(receipt, indent=2, default=str) + "\n")

    out = {"analysis_id": analysis_id, "analysis": analysis, "receipt": receipt,
           "receipt_path": str(receipt_path), "findings": findings,
           "query_entries": entries, "actions": actions, **rec}
    p = base / f"provenance_{analysis_id}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=2, default=str))
    return out
