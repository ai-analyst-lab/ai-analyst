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

        # 2. value-match — a query whose scalar result equals the finding's value
        for q in query_entries:
            if _value_match(q.get("result_value"), f.get("value"), rel_tol):
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

    out = {"analysis_id": analysis_id, "findings": findings,
           "query_entries": entries, **rec}
    p = (Path(working_dir) if working_dir else Path("working")) / f"provenance_{analysis_id}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=2, default=str))
    return out
