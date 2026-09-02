"""Tests for scripts/build_receipt.py — deterministic assembly of receipt Sections 1-7."""

import json
from pathlib import Path

import pytest
import yaml

from scripts.build_receipt import (
    LARGE_LOG_KEEP,
    LARGE_LOG_THRESHOLD,
    ReceiptError,
    SECTION_8_PLACEHOLDER,
    build_receipt,
    discover_artifacts,
    main,
)

DATASET = "acme"
DATE = "2026-09-02"


# ---------------------------------------------------------------------------
# Fixture artifacts
# ---------------------------------------------------------------------------

def _entry(qid, agent, purpose, sql, tables, rows, ms, claim_ids=(), status="success", error=None):
    return {
        "query_id": qid, "analysis_id": "a1", "timestamp": "2026-09-02T10:00:00",
        "agent": agent, "pipeline_step": 5, "purpose": purpose, "sql": sql,
        "dialect": "duckdb", "connection_type": "duckdb", "tables_accessed": list(tables),
        "columns_accessed": [], "result_summary": f"{rows} rows", "result_value": None,
        "row_count": rows, "execution_ms": ms, "claim_ids": list(claim_ids),
        "approximate_functions_used": [], "warehouse_specific_syntax": [],
        "status": status, "error": error,
    }


def _write_query_log(root: Path, entries):
    p = root / "working" / f"query_log_{DATASET}_{DATE}.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(json.dumps(e) for e in entries) + "\n")
    return p


def _write_validation(root: Path):
    p = root / "outputs" / f"validation_{DATASET}_{DATE}.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        "# Validation Report: Revenue by segment\n\n"
        "## Overall Confidence: MEDIUM\n"
        "## Confidence Score: B (78/100)\n\n"
        "**Summary:** 2 claims checked, 2 passed, one segment has a small sample.\n\n"
        "---\n\n"
        "## Claim-by-Claim Validation\n\n| Claim ID | Statement |\n|---|---|\n| C1 | x |\n\n"
        "## Validation Layers\n\n"
        "| Layer | Status | Issues | Details |\n|-------|--------|--------|---------|\n"
        "| Structural (Layer 1) | PASS | 0 | ok |\n"
        "| **Confidence Score** | **B** | **78/100** | **completeness 15/15** |\n\n"
        "## Recommendations\n1. Re-check the SMB segment once March closes.\n\n"
        "## Analysis Source\n- **Code:** x\n"
    )
    return p


def _write_cv_yaml(root: Path):
    p = root / "working" / f"provenance_{DATASET}_{DATE}.yaml"
    p.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "dataset": DATASET, "date": DATE, "connection_type": "duckdb",
        "confidence_score": 13, "gate_decision": "PROCEED",
        "claims": [
            {
                "claim_id": "finding-1", "claim_text": "Enterprise drives 62% of revenue",
                "verification": {
                    "boundary": {"tier": "1a", "status": "PASS", "checks": ["percentage_bounds"]},
                    "parts_to_whole": {"status": "PASS", "diff_pct": 0.002, "effective_tolerance": 0.01},
                    "ratio_recompute": {"status": "N/A"},
                    "algebraic_identity": {"status": "N/A"},
                    "reproducibility": {"status": "PASS", "n_runs": 3, "variance": 0.0, "deterministic": True},
                },
                "confidence_contribution": 10, "query_log_refs": ["q_desc_1"],
            },
            {
                "claim_id": "finding-2", "claim_text": "SMB conversion is 2.3%",
                "verification": {
                    "boundary": {"tier": "1a", "status": "PASS", "checks": ["percentage_bounds"]},
                    "parts_to_whole": {"status": "N/A"},
                    "ratio_recompute": {"status": "WARN", "diff_pct": 0.0015, "effective_tolerance": 0.001},
                    "algebraic_identity": {"status": "N/A"},
                },
                "confidence_contribution": 7, "query_log_refs": [],
            },
        ],
    }
    p.write_text(yaml.safe_dump(data, sort_keys=False))
    return p


def _write_state(root: Path):
    p = root / "working" / "pipeline_state.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({
        "schema_version": 2,
        "run_id": f"{DATE}_{DATASET}_why-revenue-shifted",
        "dataset": DATASET, "question": "Why did revenue shift toward enterprise?",
        "started_at": "2026-09-02T09:30:00Z", "updated_at": "2026-09-02T09:45:30Z",
        "status": "completed",
        "validation_tier": {"selected": "tier_3", "timestamp": "2026-09-02T09:40:00Z", "preference_count": 1},
        "agents": {
            "question-framing": {"status": "complete", "started_at": "2026-09-02T09:30:00Z",
                                 "completed_at": "2026-09-02T09:31:15Z", "output_file": "outputs/question_brief.md"},
            "opportunity-sizer": {"status": "degraded", "started_at": "2026-09-02T09:40:00Z",
                                  "completed_at": "2026-09-02T09:41:00Z", "error": "Insufficient data for sensitivity analysis"},
        },
    }))
    return p


def _write_manifest(root: Path):
    p = root / ".knowledge" / "datasets" / DATASET / "manifest.yaml"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(yaml.safe_dump({"name": DATASET, "connection_type": "duckdb",
                                 "connection": {"type": "duckdb", "database": "data/acme.duckdb"}}))
    return p


@pytest.fixture
def full_run(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    entries = [
        _entry("q_desc_1", "descriptive-analytics", "Revenue by segment",
               "SELECT segment, SUM(revenue) AS rev\nFROM orders\nGROUP BY segment", ["orders"], 3, 120.0, ["finding-1"]),
        _entry("q_desc_2", "descriptive-analytics", "Conversion by segment",
               "SELECT segment, AVG(converted) FROM sessions GROUP BY segment", ["sessions"], 3, 80.0,
               status="error", error="column converted not found"),
    ]
    _write_query_log(tmp_path, entries)
    _write_validation(tmp_path)
    _write_cv_yaml(tmp_path)
    _write_state(tmp_path)
    _write_manifest(tmp_path)
    return tmp_path


# ---------------------------------------------------------------------------
# Full run
# ---------------------------------------------------------------------------

def test_full_run_has_all_sections(full_run):
    md, facts = build_receipt(DATASET, DATE)
    for heading in ("## 1. Environment", "## 2. Findings Provenance", "## 3. Validation Summary",
                    "## 4. Full Query Log", "## 5. Cross-Verification Detail", "## 6. Pipeline Execution",
                    "## 7. Reproducibility Instructions", "## 8. Caveats and Limitations"):
        assert heading in md
    assert facts["findings"] == 2 and facts["queries"] == 2 and facts["cv_claims"] == 2


def test_header_from_pipeline_state(full_run):
    md, _ = build_receipt(DATASET, DATE)
    assert f"**Run ID:** {DATE}_{DATASET}_why-revenue-shifted" in md
    assert "**Question:** Why did revenue shift toward enterprise?" in md
    assert "**Validation Tier:** 3 (Deep)" in md


def test_environment_from_manifest_and_log(full_run):
    md, _ = build_receipt(DATASET, DATE)
    assert "| Connection type | duckdb |" in md
    assert "| Database | data/acme.duckdb |" in md
    assert "| Tables accessed | orders, sessions |" in md


def test_findings_carry_full_sql_and_cv(full_run):
    md, _ = build_receipt(DATASET, DATE)
    # Full, untruncated SQL for the linked query
    assert "```sql\nSELECT segment, SUM(revenue) AS rev\nFROM orders\nGROUP BY segment\n```" in md
    assert "### F1: finding-1 — Enterprise drives 62% of revenue" in md
    assert "- Method: Type B: Parts-to-whole" in md
    assert "- Runs: 3" in md
    # Unlinked claim says so instead of inventing a query
    assert "### F2: finding-2 — SMB conversion is 2.3%" in md
    assert "no query in the log is linked to this claim" in md
    assert "- Method: Type C: Ratio recompute" in md and "- Result: WARN" in md


def test_validation_summary_parsed(full_run):
    md, facts = build_receipt(DATASET, DATE)
    assert "**Overall confidence:** MEDIUM" in md
    assert "**Score:** 78/100 (B)" in md
    assert "| Structural (Layer 1) | PASS | 0 | ok |" in md
    assert "1. Re-check the SMB segment once March closes." in md
    assert facts["grade"] == "B" and facts["score"] == 78


def test_query_log_section_includes_errors_and_coverage(full_run):
    md, _ = build_receipt(DATASET, DATE)
    assert "| q_desc_2 |" not in md  # to_markdown numbers rows; ids appear in Section 2
    assert "| 2 | descriptive-analytics | 5 | Conversion by segment | sessions | 3 | 80 | error |" in md
    assert "**Coverage:** 50% of claims have backing queries (1/2)" in md
    assert "**Total queries:** 2 (1 errored, 0 backfilled)" in md
    assert "**Total execution time:** 200ms" in md


def test_cross_verification_table(full_run):
    md, _ = build_receipt(DATASET, DATE)
    assert "**Gate decision:** PROCEED" in md
    assert "| finding-1: Enterprise drives 62% of revenue | PASS | PASS | N/A | N/A | PASS | Verified |" in md
    assert "| finding-2: SMB conversion is 2.3% | PASS | N/A | WARN | N/A | N/A | Partial |" in md


def test_pipeline_section(full_run):
    md, _ = build_receipt(DATASET, DATE)
    assert "| question-framing | complete | 2026-09-02T09:30:00Z | 1m 15s | outputs/question_brief.md |" in md
    assert "**Total pipeline time:** 15m 30s" in md
    assert "**Agents completed:** 1 / 2" in md
    assert "**Degraded:** opportunity-sizer" in md


def test_reproduce_and_seeded_caveats(full_run):
    md, facts = build_receipt(DATASET, DATE)
    assert "5. **Tolerance:** For duckdb, reproduction should be exact" in md
    sec8 = md.split("## 8. Caveats and Limitations")[1]
    assert SECTION_8_PLACEHOLDER in sec8
    assert "finding-2: ratio_recompute returned WARN." in sec8
    assert "Agent opportunity-sizer degraded: Insufficient data for sensitivity analysis." in sec8
    assert "Query log coverage 50%: 1 claim(s) have no backing query." in sec8
    assert "1 logged query(ies) errored" in sec8
    assert "Validation recommendation: 1. Re-check the SMB segment once March closes." in sec8
    assert facts["seeds"] >= 5


def test_every_section_names_its_source(full_run):
    md, _ = build_receipt(DATASET, DATE)
    assert md.count("_Source: `") >= 5  # manifest, cv yaml, validation, query log, cv detail, state


# ---------------------------------------------------------------------------
# Degradation
# ---------------------------------------------------------------------------

def test_only_query_log_present(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_query_log(tmp_path, [_entry("q1", "data-explorer", "Row count", "SELECT COUNT(*) FROM t", ["t"], 1, 5.0)])
    md, facts = build_receipt(DATASET, DATE)
    assert "## 5. Cross-Verification Detail" not in md
    assert "## 6. Pipeline Execution" not in md
    assert "_Not available._ Validation not performed." in md
    assert "_Not available._ No provenance record" in md
    assert "**Run ID:** not recorded" in md and "**Validation Tier:** not recorded" in md
    assert "**Coverage:** no claims to match" in md
    sec8 = md.split("## 8. Caveats and Limitations")[1]
    assert "Validation report not available" in sec8
    assert "Cross-verification not performed for this analysis." in sec8
    assert "Pipeline state not available" in sec8
    assert facts["artifacts"]["validation"] is None and facts["artifacts"]["state"] is None


def test_missing_query_log_is_the_one_hard_error(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ReceiptError, match="Query log not found"):
        build_receipt(DATASET, DATE)
    assert main(["--dataset", DATASET, "--date", DATE]) == 1
    assert "Query log not found. Receipt requires a query log." in capsys.readouterr().err


def test_malformed_optional_artifacts_do_not_crash(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_query_log(tmp_path, [_entry("q1", "data-explorer", "Row count", "SELECT 1", ["t"], 1, 5.0)])
    (tmp_path / "working" / f"provenance_{DATASET}_{DATE}.yaml").write_text(": not: valid: yaml: [")
    (tmp_path / "working" / "pipeline_state.json").write_text("{not json")
    md, _ = build_receipt(DATASET, DATE)
    assert "## 5. Cross-Verification Detail" not in md
    assert "## 6. Pipeline Execution" not in md
    assert "## 7. Reproducibility Instructions" in md


def test_large_log_truncates_to_slowest(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    n = LARGE_LOG_THRESHOLD + 20
    entries = [_entry(f"q{i}", "a", f"purpose {i}", "SELECT 1", ["t"], 1, float(i)) for i in range(n)]
    _write_query_log(tmp_path, entries)
    md, _ = build_receipt(DATASET, DATE)
    sec4 = md.split("## 4. Full Query Log")[1].split("## 7.")[0]
    assert f"Showing the {LARGE_LOG_KEEP} slowest of {n} queries" in sec4
    assert "purpose 119" in sec4 and "purpose 0 |" not in sec4
    assert f"**Total queries:** {n}" in sec4


# ---------------------------------------------------------------------------
# Discovery and CLI
# ---------------------------------------------------------------------------

def test_discovery_prefers_run_dir_and_newest_date(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    old = tmp_path / "working" / f"query_log_{DATASET}_2026-01-01.jsonl"
    old.parent.mkdir(parents=True)
    old.write_text(json.dumps(_entry("old", "a", "p", "SELECT 0", [], 0, 1.0)) + "\n")
    newer = tmp_path / "working" / f"query_log_{DATASET}_2026-03-01.jsonl"
    newer.write_text(json.dumps(_entry("newer", "a", "p", "SELECT 0", [], 0, 1.0)) + "\n")
    assert discover_artifacts(DATASET, "2026-05-05")["query_log"].resolve() == newer.resolve()  # no exact match: newest by suffix

    run_dir = tmp_path / "working" / "runs" / "r1"
    run_log = run_dir / "working" / f"query_log_{DATASET}_{DATE}.jsonl"
    run_log.parent.mkdir(parents=True)
    run_log.write_text(json.dumps(_entry("run", "a", "p", "SELECT 0", [], 0, 1.0)) + "\n")
    state = run_dir / "pipeline_state.json"
    state.write_text(json.dumps({"run_id": "r1", "agents": {}}))
    art = discover_artifacts(DATASET, DATE, run_dir=run_dir)
    assert art["query_log"].resolve() == run_log.resolve() and art["state"].resolve() == state.resolve()


def test_cli_writes_default_output_and_reports(full_run, capsys):
    assert main(["--dataset", DATASET, "--date", DATE]) == 0
    out = full_run / "outputs" / f"analysis_receipt_{DATASET}_{DATE}.md"
    assert out.is_file() and "# Analysis Receipt" in out.read_text()
    printed = capsys.readouterr().out
    assert f"Receipt skeleton written: outputs/analysis_receipt_{DATASET}_{DATE}.md" in printed
    assert "Findings documented: 2" in printed and "Queries logged: 2" in printed


def test_cli_explicit_paths_and_out(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    log = tmp_path / "elsewhere" / "log.jsonl"
    log.parent.mkdir()
    log.write_text(json.dumps(_entry("q1", "a", "p", "SELECT 1", ["t"], 1, 1.0)) + "\n")
    out = tmp_path / "custom" / "receipt.md"
    assert main(["--dataset", DATASET, "--date", DATE, "--query-log", str(log), "--out", str(out)]) == 0
    assert out.is_file()
    assert "Artifacts not available: validation, cv_yaml, cv_md, state, manifest" in capsys.readouterr().out


def test_cli_rejects_bad_date(capsys):
    assert main(["--dataset", DATASET, "--date", "yesterday"]) == 1
    assert "--date must be YYYY-MM-DD" in capsys.readouterr().err
