from __future__ import annotations

import json

from helpers.knowledge.analysis_context import start_analysis
from helpers.knowledge.findings import record_finding
from helpers.provenance import query_log
from helpers.provenance.trace_viewer import build_trace


def test_trace_builds_receipt_and_shareable_html(tmp_path):
    aid = start_analysis(
        working_dir=tmp_path,
        question="How many completed orders were there?",
        intended_decision="Whether to investigate the change",
        dataset="novamart",
        output_dir=tmp_path / "shared",
    )
    query_log.set_log_dir(tmp_path)
    query_log.append_entry(
        "novamart",
        "2026-09-21",
        "connection_manager",
        0,
        "completed orders",
        "select count(*) from orders where status = 'completed'",
        analysis_id=aid,
        result_value=6048,
    )
    qid = query_log.read_log("novamart", "2026-09-21")[0]["query_id"]
    record_finding(6048, "Completed orders", [qid], aid, tmp_path)

    action = {
        "timestamp": "2026-09-21T10:00:00",
        "analysis_id": aid,
        "tool": "Bash",
        "summary": "Ran analysis",
    }
    (tmp_path / "action_log_2026-09-21.jsonl").write_text(json.dumps(action) + "\n")

    shared = tmp_path / "shared" / f"trace_{aid}.html"
    shared.parent.mkdir()
    result = build_trace(
        aid,
        "novamart",
        "2026-09-21",
        working_dir=tmp_path,
        out_path=shared,
    )

    assert result == str(shared)
    assert shared.exists()
    rendered = shared.read_text()
    assert "How many completed orders were there?" in rendered
    assert "Whether to investigate the change" in rendered
    assert "6048" in rendered
    receipt = json.loads((tmp_path / f"trace_receipt_{aid}.json").read_text())
    assert receipt["analysis_id"] == aid
    assert receipt["action_count"] == 1
    assert receipt["query_ids"] == [qid]
