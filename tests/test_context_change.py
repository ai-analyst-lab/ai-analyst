from __future__ import annotations

from helpers.knowledge.context_change import (
    build_context_change_receipt,
    render_context_change_receipt,
)


def _run(run_id, cases, *, suite="context-course", version="1", model="claude-opus-4-6"):
    return {
        "run_id": run_id,
        "suite_id": suite,
        "suite_version": version,
        "exposure": "working",
        "purpose": None,
        "data_snapshot": "snapshot-1",
        "case_summary": {
            case_id: {"blocking_pass": passed} for case_id, passed in cases.items()
        },
        "configuration": {
            "model": model,
            "trials_per_case": 1,
            "grade_status_counts": {
                "pass": sum(bool(value) for value in cases.values()),
                "fail": sum(not bool(value) for value in cases.values()),
            },
            "intended_change": "context",
        },
    }


def test_accepts_improvement_without_regression():
    baseline = _run("before", {"retention": False, "revenue": True})
    candidate = _run("after", {"retention": True, "revenue": True})
    receipt = build_context_change_receipt(
        baseline,
        candidate,
        changed_paths=["metrics/membership_retention.yaml"],
        change_summary="Clarify membership retention.",
        context_before="a",
        context_after="b",
    )
    assert receipt["decision"] == "accept"
    assert receipt["decision_reason"].startswith("At least one failing case improved")
    assert receipt["improved_cases"] == ["retention"]
    assert receipt["regressed_cases"] == []


def test_reverts_when_a_case_regresses():
    baseline = _run("before", {"retention": False, "revenue": True})
    candidate = _run("after", {"retention": True, "revenue": False})
    receipt = build_context_change_receipt(
        baseline,
        candidate,
        changed_paths=["metrics/membership_retention.yaml"],
        change_summary="Clarify membership retention.",
    )
    assert receipt["decision"] == "revert"
    assert receipt["regressed_cases"] == ["revenue"]


def test_noncomparable_run_requires_revision():
    baseline = _run("before", {"retention": False})
    candidate = _run("after", {"retention": True}, version="2")
    receipt = build_context_change_receipt(
        baseline,
        candidate,
        changed_paths=["metrics/membership_retention.yaml"],
        change_summary="Clarify membership retention.",
    )
    assert receipt["decision"] == "revise"
    assert receipt["comparison"]["comparable"] is False


def test_markdown_names_decision_and_cases():
    receipt = build_context_change_receipt(
        _run("before", {"retention": False}),
        _run("after", {"retention": True}),
        changed_paths=["metrics/membership_retention.yaml"],
        change_summary="Clarify membership retention.",
    )
    rendered = render_context_change_receipt(receipt)
    assert "**ACCEPT**" in rendered
    assert "`retention`" in rendered


def test_named_target_must_improve_even_when_another_case_improves():
    receipt = build_context_change_receipt(
        _run("before", {"target": False, "other": False}),
        _run("after", {"target": False, "other": True}),
        changed_paths=["context.yaml"],
        change_summary="Change context.",
        target_case_ids=["target"],
    )
    assert receipt["decision"] == "revise"
    assert receipt["all_target_cases_improved"] is False


def test_named_target_acceptance_names_target_evidence():
    receipt = build_context_change_receipt(
        _run("before", {"target": False, "regression": True}),
        _run("after", {"target": True, "regression": True}),
        changed_paths=["context.yaml"],
        change_summary="Change context.",
        target_case_ids=["target"],
    )
    assert receipt["decision"] == "accept"
    assert receipt["decision_reason"].startswith("Target cases improved")
