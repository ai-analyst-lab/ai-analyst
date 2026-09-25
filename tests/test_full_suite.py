from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from helpers.evals.full_analysis import load_public_case
from helpers.evals.full_suite import build_isolated_workspace, load_complete_suite, run_complete_suite


ROOT = Path(__file__).resolve().parents[1]


def test_session6_complete_suite_contains_twenty_unique_cases():
    suite, cases = load_complete_suite(ROOT / "evals/suites/session-6-complete-analysis.yaml")
    assert suite["suite_id"] == "session-6-complete-analysis-development"
    assert len(cases) == 20
    assert len({case["case_id"] for case in cases}) == 20
    for case in cases:
        _, public_case, _ = load_public_case(ROOT / case["path"])
        assert public_case["grading_contract"]["reference_in_student_repository"] is False


def test_complete_suite_workspace_excludes_private_and_generated_material():
    with tempfile.TemporaryDirectory() as directory:
        destination = Path(directory) / "ai-analyst"
        audit = build_isolated_workspace(ROOT, destination)
        assert audit["violations"] == []
        assert not (destination / ".env").exists()
        assert not (destination / "working").exists()
        assert not (destination / "evals/focused/working-references").exists()


def test_complete_suite_rejects_duplicate_case_ids(tmp_path):
    suite = tmp_path / "suite.yaml"
    suite.write_text(
        "suite_id: duplicate\ncases:\n"
        "  - {case_id: same, case_version: '1', path: first}\n"
        "  - {case_id: same, case_version: '1', path: second}\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="duplicate"):
        load_complete_suite(suite)


def test_complete_suite_records_elapsed_time(tmp_path, monkeypatch):
    suite = tmp_path / "suite.yaml"
    suite.write_text(
        "suite_id: elapsed\ncases:\n"
        "  - {case_id: one, case_version: '1', path: first}\n",
        encoding="utf-8",
    )

    def fake_execute_case(**kwargs):
        return {
            "case_id": kwargs["case"]["case_id"],
            "case_version": "1",
            "run_id": "run-one",
            "status": "locked",
            "latency_seconds": 0.01,
        }

    monkeypatch.setattr("helpers.evals.full_suite._execute_case", fake_execute_case)
    result = run_complete_suite(project_root=tmp_path, suite_path=suite, parallelism=4)

    assert result["actual_parallelism"] == 1
    assert result["elapsed_seconds"] >= 0
    assert result["status_counts"] == {"locked": 1}
