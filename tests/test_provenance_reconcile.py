"""Tests for the findings manifest + reconciler (provenance, 0.8b)."""
from __future__ import annotations

import json
from pathlib import Path

from helpers.knowledge.findings import record_finding, read_findings
from helpers.provenance.reconcile_provenance import reconcile, reconcile_analysis


def test_findings_manifest_stable_ids_and_roundtrip(tmp_path):
    e1 = record_finding(100, "revenue", query_ids=["q1"], analysis_id="an_x", working_dir=tmp_path)
    e2 = record_finding(0.25, "retention", analysis_id="an_x", working_dir=tmp_path)
    assert e1["finding_id"] == "an_x.f01" and e2["finding_id"] == "an_x.f02"  # sequential
    assert e1["query_ids"] == ["q1"]
    got = read_findings("an_x", working_dir=tmp_path)
    assert [f["finding_id"] for f in got] == ["an_x.f01", "an_x.f02"]


FINDINGS = [
    {"finding_id": "a.f01", "value": 100, "query_ids": ["q1"], "timestamp": "2026-06-27T10:00:00"},
    {"finding_id": "a.f02", "value": 0.25, "query_ids": [], "timestamp": "2026-06-27T10:05:00"},
    {"finding_id": "a.f03", "value": 999, "query_ids": [], "timestamp": "2026-06-27T10:10:00"},
    {"finding_id": "a.f04", "value": 777, "query_ids": [], "timestamp": "2026-06-27T08:00:00"},
]
QUERIES = [
    {"query_id": "q1", "result_value": 100, "timestamp": "2026-06-27T09:59:00"},
    {"query_id": "q2", "result_value": 0.25, "timestamp": "2026-06-27T10:04:00"},
    {"query_id": "q3", "result_value": 42, "timestamp": "2026-06-27T10:09:00"},
    {"query_id": "q5", "result_value": 5, "timestamp": "2026-06-27T11:00:00"},
]


def test_reconcile_confidence_tiers_and_leftovers():
    rec = reconcile(FINDINGS, QUERIES)
    by_f = {l["finding_id"]: l for l in rec["links"]}
    assert by_f["a.f01"] == {"finding_id": "a.f01", "query_id": "q1", "confidence": "cited"}
    assert by_f["a.f02"]["query_id"] == "q2" and by_f["a.f02"]["confidence"] == "value-match"
    assert by_f["a.f03"]["query_id"] == "q3" and by_f["a.f03"]["confidence"] == "inferred"
    assert rec["unmatched_findings"] == ["a.f04"]      # no value, no preceding query
    assert rec["orphan_queries"] == ["q5"]             # nothing links to it


def test_cited_beats_value_match():
    # f cites q1; q9 also matches by value — cited wins, q9 is left orphan.
    findings = [{"finding_id": "x.f01", "value": 50, "query_ids": ["q1"], "timestamp": "t2"}]
    queries = [{"query_id": "q1", "result_value": 50, "timestamp": "t1"},
               {"query_id": "q9", "result_value": 50, "timestamp": "t1"}]
    rec = reconcile(findings, queries)
    assert rec["links"] == [{"finding_id": "x.f01", "query_id": "q1", "confidence": "cited"}]
    assert rec["orphan_queries"] == ["q9"]


def test_reconcile_analysis_writes_provenance_file(tmp_path):
    from helpers.provenance import query_log as ql
    ql.set_log_dir(tmp_path)
    record_finding(3150899.34, "completed revenue", analysis_id="an_io", working_dir=tmp_path)
    ql.append_entry("ds", "2026-06-27", "auto-hook", 0, "p",
                    "select sum(total_amount) from orders where status='completed'",
                    analysis_id="an_io", result_value=3150899.34)
    ql.append_entry("ds", "2026-06-27", "auto-hook", 0, "p", "select 1",
                    analysis_id="other", result_value=1)  # different analysis, must be ignored

    out = reconcile_analysis("an_io", "ds", "2026-06-27", working_dir=tmp_path)
    assert (tmp_path / "provenance_an_io.json").exists()
    assert len(out["query_entries"]) == 1                      # only an_io's query
    assert len(out["links"]) == 1 and out["links"][0]["confidence"] == "value-match"
    assert out["unmatched_findings"] == [] and out["orphan_queries"] == []
