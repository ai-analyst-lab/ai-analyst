import json
import io
from pathlib import Path

import pytest
import yaml

from helpers.evals.cases import load_suite, publish_manifest
from helpers.evals.candidates import propose, verify
from helpers.evals.comparison import compare_engine_runs, compare_manifests
from helpers.evals.controller import EvaluationController
from helpers.evals.graders.numeric import grade_numeric
from helpers.evals.judges import evaluate_alignment, repeated_label_stability
from helpers.evals.normalization import normalize_number, values_within_tolerance
from helpers.evals.records import RunStore
from helpers.evals.remote import RemoteGraderClient
from helpers.evals.reliability import measure_reliability
from helpers.evals.schema import EvaluationCase, TrialRecord
from helpers.evals.scorecard import decide
from helpers.evals.triangulation import build_grid, compare_rounds
from helpers.evals.trace import inspect_receipt
from helpers.evals.workspace import SanitizedWorkspaceBuilder, output_schema_for_case


def verified_case(**overrides):
    values = {
        "case_id": "revenue-1",
        "task": "Report revenue.",
        "split": "working",
        "status": "verified",
        "truth_basis": "computed",
        "expected": 100,
        "tolerance": {"absolute": 0.5},
        "graders": [{"type": "numeric", "field": "answer"}],
        "data_snapshot": "nova-v1",
        "truth_evidence": "Independently recomputed and reviewed.",
        "reproduction": "private query",
        "reviewed_by": "reviewer",
        "verified_at": "2026-09-06T00:00:00+00:00",
    }
    values.update(overrides)
    return EvaluationCase(**values)


def write_suite(path: Path, case: EvaluationCase):
    path.write_text(
        yaml.safe_dump(
            {
                "suite_id": "nova",
                "suite_version": "1",
                "data_snapshot": "nova-v1",
                "cases": [case.to_dict()],
            },
            sort_keys=False,
        )
    )


def test_verified_case_requires_provenance():
    with pytest.raises(ValueError, match="verified case is missing"):
        EvaluationCase(case_id="x", task="Do x", status="verified", truth_basis="computed")


def test_public_manifest_strips_answer_and_reference(tmp_path):
    private = tmp_path / "private.yaml"
    public = tmp_path / "public.yaml"
    write_suite(private, verified_case())
    publish_manifest(private, public)
    text = public.read_text()
    assert "expected:" not in text
    assert "private query" not in text
    metadata, cases = load_suite(public)
    assert metadata["visibility"] == "public-task-manifest"
    assert cases[0].has_private_reference is True


def test_public_loader_rejects_answer_leak(tmp_path):
    path = tmp_path / "leak.yaml"
    write_suite(path, verified_case())
    with pytest.raises(ValueError, match="private reference"):
        load_suite(path)


def test_week5_engine_suite_is_public_and_matches_working_references():
    _, public_cases = load_suite("data/evals/public/week5-engine.yaml")
    _, private_cases = load_suite(
        "data/evals/working-references/week5-engine.yaml", allow_private=True
    )
    assert [case.case_id for case in public_cases] == [case.case_id for case in private_cases]
    assert len(public_cases) == 3
    assert all(case.split == "working" for case in public_cases)


@pytest.mark.parametrize(
    "raw,hint,expected",
    [("25%", "rate", 0.25), ("0.25", "rate", 0.25), ("$3.2 million", None, 3_200_000), ("1,500", None, 1500)],
)
def test_normalize_number(raw, hint, expected):
    assert normalize_number(raw, hint).value == expected


def test_absolute_tolerance_protects_zero():
    assert values_within_tolerance(0.01, 0, absolute=0.02)
    assert not values_within_tolerance(0.03, 0, absolute=0.02)


def test_numeric_grader_accepts_percent_and_fraction():
    case = verified_case(expected=0.25, tolerance={"absolute": 0.001})
    grade = grade_numeric(case, "trial", "run", "25%", unit_hint="rate")
    assert grade.status == "pass"


def test_reliability_separates_exact_tolerance_and_failures():
    result = measure_reliability(
        [
            {"headline": "25%", "status": "completed"},
            {"headline": "0.251", "status": "completed"},
            {"headline": "not available", "status": "completed"},
            {"status": "blocked"},
        ],
        unit_hint="rate",
        absolute_tolerance=0.002,
    )
    assert result["exact_agreement"]["count"] == 1
    assert result["tolerance_agreement"]["count"] == 2
    assert result["status_counts"] == {"completed": 2, "unparseable": 1, "blocked": 1}
    assert result["verdict"] == "variable"


def test_trial_lock_detects_tampering(tmp_path):
    store = RunStore(tmp_path, "run")
    trial = TrialRecord(
        run_id="run", trial_id="trial", case_id="case", case_version="1", trial_number=1,
        status="completed", structured_result={"answer": 1},
    )
    path = store.lock_trial(trial)
    path.chmod(0o644)
    payload = json.loads(path.read_text())
    payload["structured_result"]["answer"] = 2
    path.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="output lock failed"):
        store.load_locked_trial("trial")


def test_sanitized_workspace_excludes_answer_files_and_history(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "CLAUDE.md").write_text("instructions")
    knowledge = source / ".knowledge"
    knowledge.mkdir()
    (knowledge / "context.md").write_text("safe")
    (knowledge / "ground_truth.yaml").write_text("answer: 42")
    reliability = knowledge / "reliability"
    reliability.mkdir()
    (reliability / "past.json").write_text("{}")
    workspace = tmp_path / "workspace"
    SanitizedWorkspaceBuilder(source).build(workspace, verified_case())
    assert (workspace / "CLAUDE.md").exists()
    assert (workspace / ".knowledge" / "context.md").exists()
    assert not (workspace / ".knowledge" / "ground_truth.yaml").exists()
    assert not (workspace / ".knowledge" / "reliability").exists()
    assert "expected" not in (workspace / "eval_task.json").read_text()


def test_sanitized_workspace_copies_only_declared_case_fixture(tmp_path):
    source = tmp_path / "source"
    fixture = source / "data" / "evals" / "examples" / "note.md"
    fixture.parent.mkdir(parents=True)
    fixture.write_text("business note")
    (source / "CLAUDE.md").write_text("instructions")
    case = verified_case(data_scope={"workspace_files": ["data/evals/examples/note.md"]})
    workspace = tmp_path / "workspace"
    SanitizedWorkspaceBuilder(source).build(workspace, case)
    assert (workspace / "inputs" / "note.md").read_text() == "business note"


def test_sanitized_workspace_copies_declared_working_directory(tmp_path):
    source = tmp_path / "source"
    fixture = source / "working" / "context-store" / "metrics" / "retention.yaml"
    fixture.parent.mkdir(parents=True)
    fixture.write_text("id: retention\n")
    (source / "CLAUDE.md").write_text("instructions")
    case = verified_case(data_scope={"workspace_dirs": ["working/context-store"]})
    workspace = tmp_path / "workspace"

    SanitizedWorkspaceBuilder(source).build(workspace, case)

    assert (workspace / "working" / "context-store" / "metrics" / "retention.yaml").exists()


def test_sanitized_workspace_rejects_private_file_in_declared_directory(tmp_path):
    source = tmp_path / "source"
    fixture = source / "working" / "context-store" / "ground_truth.yaml"
    fixture.parent.mkdir(parents=True)
    fixture.write_text("answer: 42\n")
    (source / "CLAUDE.md").write_text("instructions")
    case = verified_case(data_scope={"workspace_dirs": ["working/context-store"]})

    with pytest.raises(ValueError, match="unsafe entry"):
        SanitizedWorkspaceBuilder(source).build(tmp_path / "workspace", case)


def test_sanitized_workspace_rejects_case_path_traversal(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "CLAUDE.md").write_text("instructions")
    case = verified_case(data_scope={"workspace_files": ["../answer.txt"]})
    with pytest.raises(ValueError, match="invalid case workspace file"):
        SanitizedWorkspaceBuilder(source).build(tmp_path / "workspace", case)


def test_case_output_schema_constrains_label_without_revealing_correct_one():
    case = verified_case(
        graders=[{
            "type": "exact",
            "field": "action",
            "allowed_values": ["continue", "follow", "abstain"],
        }]
    )
    schema = output_schema_for_case(case)
    assert schema["properties"]["action"]["enum"] == ["continue", "follow", "abstain"]
    assert "expected" not in json.dumps(schema)


def test_controller_runs_public_then_grades_locked_output(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    (project / "CLAUDE.md").write_text("answer carefully")
    private = tmp_path / "private.yaml"
    public = tmp_path / "public.yaml"
    write_suite(private, verified_case())
    publish_manifest(private, public)

    seen_task = {}

    def runner(workspace, case, trial_number):
        seen_task.update(json.loads((workspace / "eval_task.json").read_text()))
        return {"status": "completed", "structured_result": {"answer": 100}}

    controller = EvaluationController(project, tmp_path / "runs")
    manifest = controller.run_public_suite(public, runner)
    assert "expected" not in seen_task
    graded = controller.grade_run(manifest.run_id, public, private)
    assert graded.configuration["grade_status_counts"] == {"pass": 1}
    assert graded.case_summary["revenue-1"]["blocking_pass"]


def test_scorecard_blocking_failure_cannot_be_averaged_away():
    result = decide(
        [
            {"criterion": "receipt", "status": "pass", "role": "diagnostic"},
            {"criterion": "correct number", "status": "fail", "role": "blocking"},
        ]
    )
    assert result["recommendation"] == "abstain"


def path(path_id, direction):
    return {
        "path_id": path_id,
        "method": f"method-{path_id}",
        "source": f"source-{path_id}",
        "population": "customers",
        "assumptions": ["one"],
        "direction": direction,
        "basis": "observed comparison",
    }


def test_triangulation_preserves_disagreement_and_noise():
    first = build_grid([path("a", "yes"), path("b", "no")])
    second = build_grid([path("a", "yes"), path("b", "unclear")])
    comparison = compare_rounds(first, second)
    assert first["disagreement"]
    assert comparison["run_noise_detected"]


def test_judge_alignment_keeps_unknown_and_disagreements():
    result = evaluate_alignment(
        [
            {"example_id": "a", "human": "pass", "grader": "pass"},
            {"example_id": "b", "human": "fail", "grader": "unknown"},
        ]
    )
    assert result["agreement_rate"] == 0.5
    assert result["confusion_matrix"]["fail"]["unknown"] == 1
    stability = repeated_label_stability(
        [
            {"example_id": "a", "grader": "pass"},
            {"example_id": "a", "grader": "unknown"},
        ]
    )
    assert not stability["stable"]


def test_run_comparison_rejects_moving_suite():
    baseline = {"suite_id": "a", "suite_version": "1", "split": "working", "data_snapshot": "1", "configuration": {"model": "x", "trials_per_case": 1}}
    candidate = {**baseline, "suite_version": "2"}
    assert not compare_manifests(baseline, candidate)["comparable"]


def test_run_comparison_rejects_unapproved_system_change():
    baseline = {
        "suite_id": "a", "suite_version": "1", "split": "working", "data_snapshot": "1",
        "configuration": {"model": "x", "trials_per_case": 1, "runner": "context-policy"},
        "system_fingerprint": {"tree": {"files": {"context.yaml": "before", "CLAUDE.md": "same"}}},
    }
    candidate = {
        **baseline,
        "configuration": {
            **baseline["configuration"],
            "intended_change": "context",
            "allowed_changed_paths": ["context.yaml"],
        },
        "system_fingerprint": {"tree": {"files": {"context.yaml": "after", "CLAUDE.md": "changed"}}},
    }
    comparison = compare_manifests(baseline, candidate)
    assert comparison["comparable"] is False
    assert comparison["unapproved_system_changes"] == ["CLAUDE.md"]


def test_controlled_engine_comparison_allows_only_engine_change_and_keeps_unknown_cost():
    baseline = {
        "suite_id": "a", "suite_version": "1", "split": "working", "data_snapshot": "1",
        "configuration": {"model": "a", "trials_per_case": 1, "runner": "a",
                          "data_fingerprint": {"x": 1}, "context_fingerprint": "same",
                          "tool_configuration": {"read": True}},
        "evaluator_fingerprint": {"controller": "1", "public_manifest_digest": "x"},
        "system_fingerprint": {"tree": {"files": {"CLAUDE.md": "same"}}},
        "engine_fingerprint": {"model": "a"},
    }
    candidate = {
        **baseline,
        "configuration": {**baseline["configuration"], "model": "b", "runner": "b",
                          "intended_change": "engine"},
        "engine_fingerprint": {"model": "b"},
    }
    before = [{"case_id": "one", "status": "completed", "latency_ms": 100, "cost_usd": None}]
    after = [{"case_id": "one", "status": "error", "latency_ms": 200, "cost_usd": 0.2,
              "errors": [{"type": "SchemaError"}]}]
    result = compare_engine_runs(baseline, candidate, before, after)
    assert result["comparable"]
    assert result["completion_rate"] == {"baseline": 1.0, "candidate": 0.0}
    assert result["cost_usd"]["baseline_known_total"] is None
    assert result["new_errors"] == ["SchemaError"]


def test_engine_comparison_reports_score_movement_even_when_both_runs_complete():
    baseline = {
        "suite_id": "a", "suite_version": "1", "split": "working", "data_snapshot": "1",
        "configuration": {"model": "a", "runner": "a", "trials_per_case": 1},
        "evaluator_fingerprint": {"controller": "1", "public_manifest_digest": "x"},
        "system_fingerprint": {"tree": {"files": {"CLAUDE.md": "same"}}},
    }
    candidate = {
        **baseline,
        "configuration": {**baseline["configuration"], "model": "b", "runner": "b",
                          "intended_change": "engine"},
    }
    before = [{"case_id": "one", "status": "completed", "evaluation_status": "pass",
               "output_digest": "a"}]
    after = [{"case_id": "one", "status": "completed", "evaluation_status": "fail",
              "output_digest": "b"}]
    result = compare_engine_runs(baseline, candidate, before, after)
    assert result["comparable"]
    assert result["completion_rate"] == {"baseline": 1.0, "candidate": 1.0}
    assert result["evaluation_pass_rate"] == {"baseline": 1.0, "candidate": 0.0}
    assert result["disagreements_requiring_review"][0]["case_id"] == "one"


def test_trace_flags_join_aggregation_risk():
    receipt = {
        "analysis_id": "a",
        "claim": "Revenue is 10",
        "source": "orders",
        "data_snapshot": "one",
        "query": "SELECT sum(o.total) FROM orders o JOIN items i USING (order_id)",
    }
    result = inspect_receipt(receipt)
    assert result["receipt_complete"]
    assert any("fan-out" in risk for risk in result["risks"])


def test_candidate_requires_review_before_verification():
    candidate = EvaluationCase(
        case_id="new", task="Return a count", success_criteria=[{"type": "numeric"}],
        expected=5, graders=[{"type": "numeric"}],
    )
    candidate = propose(candidate, "student")
    verified = verify(
        candidate,
        reviewer="instructor",
        truth_basis="computed",
        truth_evidence="independent query",
        data_snapshot="v1",
        reproduction="SELECT 5",
    )
    assert verified.status == "verified"
    assert verified.reviewed_by == "instructor"


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def test_remote_grader_contract_does_not_return_answers():
    captured = {}

    def opener(request, timeout):
        captured.update(json.loads(request.data))
        return FakeResponse(json.dumps({"run_id": "run", "grades": [{"status": "pass"}]}).encode())

    client = RemoteGraderClient("https://grader.example", "token", opener=opener)
    result = client.grade(
        {"run_id": "run", "suite_id": "s", "suite_version": "1", "split": "heldout", "system_fingerprint": {}, "data_snapshot": "v1"},
        [{"trial_id": "t", "case_id": "c", "case_version": "1", "output_digest": "d", "structured_result": {"answer": 5}}],
    )
    assert result["grades"][0]["status"] == "pass"
    assert "expected" not in json.dumps(captured)


def test_remote_grader_rejects_answer_leak():
    def opener(request, timeout):
        return FakeResponse(json.dumps({"run_id": "run", "ground_truth": 5}).encode())

    client = RemoteGraderClient("https://grader.example", "token", opener=opener)
    with pytest.raises(ValueError, match="exposed private"):
        client.grade(
            {"run_id": "run", "suite_id": "s", "suite_version": "1", "split": "heldout", "system_fingerprint": {}, "data_snapshot": "v1"},
            [],
        )


def test_controller_persists_remote_grades(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    (project / "CLAUDE.md").write_text("instructions")
    private = tmp_path / "private.yaml"
    public = tmp_path / "public.yaml"
    case = verified_case(split="heldout")
    write_suite(private, case)
    publish_manifest(private, public)
    controller = EvaluationController(project, tmp_path / "runs")
    manifest = controller.run_public_suite(
        public,
        lambda workspace, public_case, trial: {"status": "completed", "structured_result": {"answer": 100}},
        split="heldout",
    )

    class Client:
        def grade(self, manifest_payload, trials):
            return {
                "run_id": manifest_payload["run_id"],
                "grades": [{
                    "trial_id": trials[0]["trial_id"],
                    "case_id": trials[0]["case_id"],
                    "grader_id": "remote-numeric",
                    "criterion": "numeric result",
                    "status": "pass",
                    "role": "blocking",
                }],
            }

    graded = controller.grade_remote(manifest.run_id, Client())
    assert graded.configuration["grading_boundary"] == "course-controlled"
    assert graded.configuration["grade_status_counts"] == {"pass": 1}
