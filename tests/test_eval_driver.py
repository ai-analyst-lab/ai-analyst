"""Tests for helpers/provenance/eval_driver.py (the live /eval driver plumbing, D4).

Hermetic: no warehouse, no network. A FakeConn returns a pinned value per SQL so grade() runs the
real harness end to end; context_state/git_sha are exercised directly or stubbed so the cross-repo
wiring and the run-record meta are proven without a live Snowflake or the git context sync."""
from __future__ import annotations

import os
import pytest
from pathlib import Path

import yaml

from helpers.provenance import eval_driver


def test_git_sha_shape():
    sha = eval_driver.git_sha()
    assert sha is None or (isinstance(sha, str) and 4 <= len(sha) <= 12)


def test_context_state_lists_defined_metrics(tmp_path):
    p = tmp_path / "index.yaml"
    p.write_text(yaml.safe_dump({"metrics": [{"metric": "total_revenue"},
                                             {"metric": "checkout_conversion"}]}))
    st = eval_driver.context_state(metrics_path=p)
    assert st["n"] == 2
    assert st["defined_metrics"] == ["checkout_conversion", "total_revenue"]  # sorted


def test_context_state_missing_file(tmp_path):
    st = eval_driver.context_state(metrics_path=tmp_path / "nope.yaml")
    assert st == {"defined_metrics": [], "n": 0}


class _Cur:
    def __init__(self, v): self._v = v
    def fetchone(self): return (self._v,)
    def fetchall(self): return [(self._v,)]


class FakeConn:
    """DuckDB-style conn (has .execute) returning a pinned value per known SQL."""
    def __init__(self, vals): self.vals = vals
    def execute(self, sql):
        k = sql.strip()
        if k not in self.vals:
            raise KeyError(k)
        return _Cur(self.vals[k])


def test_grade_wires_harness_and_writes_meta(tmp_path, monkeypatch):
    """grade() imports the sibling harness, scores the blind gold, and stamps the run record with
    git_sha + model + context_state + split (D4). context_state/git_sha stubbed for hermeticity."""
    gold = tmp_path / "gold.yaml"
    gold.write_text(yaml.safe_dump({"cases": [
        {"question": "What is total revenue?", "sql": "select 1",
         "approved_query": "select 1", "tables": ["orders"], "split": "train"},
    ]}))
    monkeypatch.setattr(eval_driver, "context_state",
                        lambda *a, **k: {"defined_metrics": ["total_revenue"], "n": 1})
    monkeypatch.setattr(eval_driver, "git_sha", lambda *a, **k: "deadbee")
    # External mode is opt-in: point the driver at the harness repo (skip if absent).
    harness = os.environ.get("AIEVALS_REPO")
    if not harness or not Path(harness).exists():
        pytest.skip("AIEVALS_REPO not set; external-harness mode not under test")
    monkeypatch.setattr(eval_driver, "EVALS_REPO", Path(harness))

    conn = FakeConn({"select 1": 42})
    pcr = [{"question": "What is total revenue?", "analyst_value": 42,
            "analyst_query": "select 1", "latency_ms": 500}]
    rec = eval_driver.grade(pcr, split="train", out_dir=tmp_path / "runs",
                            conn=conn, gold_path=gold, model="opus-4.8")

    assert rec["split"] == "train"
    assert rec["git_sha"] == "deadbee"
    assert rec["model"] == "opus-4.8"
    assert rec["context_state"]["n"] == 1
    assert rec["aggregate"]["total"] == 1 and rec["aggregate"]["passed"] == 1
    assert rec["cases"][0]["latency_ms"] == 500


def test_grade_local_uses_bundled_gold_and_tolerance(tmp_path):
    """Local mode: bundled gold, relative-tolerance grading, self-describing run record."""
    qs = eval_driver.load_questions("train")
    assert qs and "answer" not in qs[0]  # blind view
    gold = eval_driver.load_gold()
    cases = gold["cases"][:3]
    results = [{"id": cases[0]["id"], "answer": cases[0]["answer"]},          # exact
               {"id": cases[1]["id"], "answer": cases[1]["answer"] * 1.001},  # inside tolerance
               {"id": cases[2]["id"], "answer": cases[2]["answer"] * 2}]      # wrong
    rec = eval_driver.grade_local(results, "train", tmp_path / "runs", model="test")
    assert rec["n_cases"] == 3 and rec["n_correct"] == 2
    assert Path(rec["run_record"]).exists()
    assert rec["meta"]["model"] == "test"
