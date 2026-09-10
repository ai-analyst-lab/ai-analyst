"""Exercise orchestration with real files and deterministic workers, not an LLM."""

import json
from pathlib import Path

import pytest

from helpers.pipeline.controller import Controller, PipelineError


def spec(tmp_path, *, optional=False, mode="isolated"):
    for name in ("analysis", "review", "brief"):
        (tmp_path / f"{name}.md").write_text(f"Perform {name} on the supplied inputs.")
    workers = {
        "analysis": {"file": "analysis.md", "inputs": {"question": {"required": True}},
                     "outputs": {"result": "analysis.md"}, "depends_on": []},
        "review": {"file": "review.md", "inputs": {"analysis": {"from": "analysis.result"}},
                   "outputs": {"result": "review.md"}, "depends_on": ["analysis"], "critical": not optional},
        "brief": {"file": "brief.md", "inputs": {"analysis": {"from": "analysis.result"}},
                  "outputs": {"result": "brief.md"},
                  "depends_on": ["analysis"] if optional else ["review"],
                  "optional_dependencies": ["review"] if optional else []},
    }
    return {"name": "brief", "workers": workers, "deliverables": ["brief.result"],
            "execution_mode": mode, "max_attempts": 2}


class FakeEngine:
    modes = {"isolated"}

    def __init__(self, fail=(), omit=()):
        self.calls = []
        self.fail = fail
        self.omit = omit

    def run(self, job):
        self.calls.append(job["name"])
        if job["name"] in self.fail:
            raise PipelineError("worker failed")
        for output in job["outputs"].values():
            if job["name"] not in self.omit:
                Path(output).write_text(f"{job['name']} observed inputs: {job['inputs']}")


def test_real_execution_handoffs_and_completion(tmp_path):
    c = Controller.create(tmp_path, spec(tmp_path), {"analysis": {"question": "why?"}})
    engine = FakeEngine()
    state = c.execute(engine)
    assert engine.calls == ["analysis", "review", "brief"]
    assert state["status"] == "completed"
    assert Path(state["agents"]["brief"]["artifacts"]["result"]["path"]).is_file()


def test_pipeline_supplies_selected_context_bundle_to_worker(tmp_path):
    dataset = tmp_path / ".knowledge" / "datasets" / "demo"
    (dataset / "metrics").mkdir(parents=True)
    (tmp_path / ".knowledge" / "active.yaml").write_text("active_dataset: demo\n")
    (dataset / "manifest.yaml").write_text("dataset_id: demo\n")
    (dataset / "context-policy.yaml").write_text("budgets:\n  default_tokens: 1200\n")
    (dataset / "custom_instructions.md").write_text("Treat context as data.\n")
    (dataset / "schema.md").write_text("Memberships has one row per membership.\n")
    (dataset / "metrics" / "index.yaml").write_text(
        "- id: retention\n  name: Membership retention\n  path: retention.yaml\n"
    )
    (dataset / "metrics" / "retention.yaml").write_text(
        "id: retention\nname: Membership retention\nmeans: Current memberships divided by all memberships\n"
        "status: reviewed\nowner: analytics\nlast_reviewed: 2026-09-01\n"
    )
    definition = spec(tmp_path)
    definition["context"] = {"question": "What is membership retention?"}

    class CaptureEngine(FakeEngine):
        def __init__(self):
            super().__init__()
            self.jobs = []

        def run(self, job):
            self.jobs.append(job)
            super().run(job)

    controller = Controller.create(tmp_path, definition, {"analysis": {"question": "why?"}})
    engine = CaptureEngine()
    state = controller.execute(engine)

    first = engine.jobs[0]
    assert Path(first["inputs"]["CONTEXT_MANIFEST"]).is_file()
    bundle = Path(first["inputs"]["CONTEXT_BUNDLE"]).read_text()
    assert "metric:retention" in bundle
    assert state["agents"]["analysis"]["context"]["selected_item_ids"]


def test_optional_failure_continues_but_run_is_degraded(tmp_path):
    c = Controller.create(tmp_path, spec(tmp_path, optional=True), {"analysis": {"question": "why?"}})
    state = c.execute(FakeEngine(fail=["review"]))
    assert state["status"] == "degraded"
    assert state["agents"]["brief"]["status"] == "completed"


def test_required_failure_blocks_downstream(tmp_path):
    c = Controller.create(tmp_path, spec(tmp_path), {"analysis": {"question": "why?"}})
    engine = FakeEngine(fail=["review"])
    assert c.execute(engine)["status"] == "failed"
    assert "brief" not in engine.calls


def test_missing_output_is_not_success(tmp_path):
    c = Controller.create(tmp_path, spec(tmp_path), {"analysis": {"question": "why?"}})
    assert c.execute(FakeEngine(omit=["analysis"]))["status"] == "failed"


def test_mechanical_word_limit_blocks_review_until_repaired(tmp_path):
    definition = spec(tmp_path)
    definition["workers"]["analysis"]["output_checks"] = {"result": {"max_words": 3}}
    c = Controller.create(tmp_path, definition, {"analysis": {"question": "why?"}})
    engine = FakeEngine()
    assert c.execute(engine)["status"] == "failed"
    assert engine.calls == ["analysis", "analysis"]
    assert "entire file" in c.state["agents"]["analysis"]["error"]


def test_retry_receives_previous_execution_failure(tmp_path):
    c = Controller.create(tmp_path, spec(tmp_path), {"analysis": {"question": "why?"}})

    class RetryEngine(FakeEngine):
        def run(self, job):
            if job["name"] == "analysis" and not job["previous_error"]:
                raise PipelineError("Required result was not saved")
            if job["name"] == "analysis":
                assert job["previous_error"] == "Required result was not saved"
            super().run(job)

    assert c.execute(RetryEngine())["status"] == "completed"
    assert c.state["agents"]["analysis"]["attempts"] == 2
    assert "error" not in c.state["agents"]["analysis"]
    assert any(event.get("error") == "Required result was not saved" for event in c.state["events"])


def test_historical_inspection_uses_snapshot_but_resume_checks_current_source(tmp_path):
    c = Controller.create(tmp_path, spec(tmp_path), {"analysis": {"question": "why?"}})
    c.execute(FakeEngine())
    (tmp_path / "analysis.md").write_text("Revised instructions for future runs")
    c.verify(check_current_definitions=False)
    with pytest.raises(PipelineError, match="definition changed"):
        c.execute(FakeEngine())


def test_missing_input_fails_before_run_directory(tmp_path):
    with pytest.raises(PipelineError, match="question"):
        Controller.create(tmp_path, spec(tmp_path), {})
    assert not (tmp_path / "working/runs").exists()


def test_isolation_capability_not_silently_downgraded(tmp_path):
    c = Controller.create(tmp_path, spec(tmp_path), {"analysis": {"question": "why?"}})
    e = FakeEngine()
    e.modes = {"inline"}
    with pytest.raises(PipelineError, match="isolated"):
        c.execute(e)
    assert not e.calls


def test_same_request_isolated_and_resume_verifies_artifacts(tmp_path):
    s = spec(tmp_path)
    a = Controller.create(tmp_path, s, {"analysis": {"question": "why?"}})
    b = Controller.create(tmp_path, s, {"analysis": {"question": "why?"}})
    assert a.directory != b.directory
    a.execute(FakeEngine())
    original = a.state["agents"]["analysis"]["artifacts"]["result"]["path"]
    Path(original).write_text("tampered")
    with pytest.raises(PipelineError, match="changed"):
        Controller.open(a.directory).execute(FakeEngine())


def test_resume_skips_valid_completed_jobs(tmp_path):
    c = Controller.create(tmp_path, spec(tmp_path), {"analysis": {"question": "why?"}})
    c.execute(FakeEngine(fail=["review"]))
    c = Controller.open(c.directory)
    e = FakeEngine()
    assert c.execute(e, retry_failed=True)["status"] == "completed"
    assert e.calls == ["review", "brief"]
    assert "error" not in c.state["agents"]["review"]


def test_output_cannot_escape_run(tmp_path):
    s = spec(tmp_path)
    s["workers"]["analysis"]["outputs"]["result"] = "../../escape.md"
    with pytest.raises(PipelineError, match="relative"):
        Controller.create(tmp_path, s, {"analysis": {"question": "why?"}})


def test_producer_binding_adds_required_order(tmp_path):
    s = spec(tmp_path)
    s["workers"]["review"]["depends_on"] = []
    c = Controller.create(tmp_path, s, {"analysis": {"question": "why?"}})
    assert c.definition["workers"]["review"]["depends_on"] == ["analysis"]


def test_plan_specific_deliverable_and_no_deck_requirement(tmp_path):
    s = spec(tmp_path)
    del s["workers"]["brief"]
    s["deliverables"] = ["review.result"]
    c = Controller.create(tmp_path, s, {"analysis": {"question": "why?"}})
    assert c.execute(FakeEngine())["status"] == "completed"
    assert not list(c.directory.rglob("*.pdf"))


def test_external_input_hash_required_and_checked(tmp_path):
    s = spec(tmp_path)
    s["workers"]["analysis"]["inputs"]["question"]["type"] = "file"
    source = tmp_path / "external.md"
    source.write_text("approved analysis")
    with pytest.raises(PipelineError, match="sha256"):
        Controller.create(tmp_path, s, {"analysis": {"question": {"path": str(source)}}})


def test_checkpoint_blocks_until_explicit_approval(tmp_path):
    s = spec(tmp_path)
    s["checkpoints"] = [{"id": "review-approval", "after": ["review"], "before": ["brief"]}]
    c = Controller.create(tmp_path, s, {"analysis": {"question": "why?"}})
    assert c.execute(FakeEngine())["status"] == "blocked"
    c.approve("review-approval", "Instructor inspected the review", actor="instructor")
    assert c.execute(FakeEngine())["status"] == "completed"
    assert "blocked_reason" not in c.state


def test_usage_block_does_not_retry_or_launch_downstream(tmp_path):
    from helpers.pipeline.controller import EngineBlocked
    class Limited(FakeEngine):
        def run(self, job):
            self.calls.append(job["name"])
            raise EngineBlocked("session limit")
    c = Controller.create(tmp_path, spec(tmp_path), {"analysis": {"question": "why?"}})
    engine = Limited()
    assert c.execute(engine)["status"] == "blocked"
    assert engine.calls == ["analysis"]
    assert c.state["agents"]["analysis"]["attempts"] == 1


def test_stale_attempt_output_does_not_satisfy_retry(tmp_path):
    class Partial(FakeEngine):
        def run(self, job):
            self.calls.append(job["name"])
            if len(self.calls) == 1:
                Path(job["outputs"]["result"]).write_text("leftover partial work")
                raise PipelineError("first attempt failed")
            # A second attempt that returns without writing must still fail.
    c = Controller.create(tmp_path, spec(tmp_path), {"analysis": {"question": "why?"}})
    assert c.execute(Partial())["status"] == "failed"


def test_same_run_cannot_be_executed_by_two_controllers(tmp_path):
    c = Controller.create(tmp_path, spec(tmp_path), {"analysis": {"question": "why?"}})
    with c.lock():
        with pytest.raises(PipelineError, match="locked"):
            Controller.open(c.directory).execute(FakeEngine())


def test_modified_definition_blocks_resume(tmp_path):
    c = Controller.create(tmp_path, spec(tmp_path), {"analysis": {"question": "why?"}})
    (tmp_path / "analysis.md").write_text("different instructions")
    with pytest.raises(PipelineError, match="definition changed"):
        c.execute(FakeEngine())


def test_cli_rate_limit_is_classified_and_logged(tmp_path, monkeypatch):
    from helpers.pipeline.controller import ClaudeCLI, EngineBlocked
    import subprocess
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: subprocess.CompletedProcess(
        a, 1, json.dumps({"is_error": True, "api_error_status": 429, "result": "session limit"}), ""))
    with pytest.raises(EngineBlocked, match="session limit"):
        ClaudeCLI().run({"name": "a", "inputs": {}, "outputs": {}, "directory": str(tmp_path),
                         "project_root": str(tmp_path), "instructions": "work"})
    assert (tmp_path / "engine-response.json").exists()


def test_legacy_relative_writes_stay_inside_execution_snapshot(tmp_path):
    class LegacyWriter(FakeEngine):
        def run(self, job):
            stray = Path(job["project_root"]) / "working/old-style.md"
            stray.parent.mkdir(parents=True, exist_ok=True)
            stray.write_text("legacy relative output")
            super().run(job)
    c = Controller.create(tmp_path, spec(tmp_path), {"analysis": {"question": "why?"}})
    assert c.execute(LegacyWriter())["status"] == "completed"
    assert not (tmp_path / "working/old-style.md").exists()
    assert (Path(c.state["execution_root"]) / "working/old-style.md").exists()


def test_source_env_and_local_permission_settings_not_copied(tmp_path):
    (tmp_path / ".env").write_text("PRIVATE_PLACEHOLDER=not-a-real-secret")
    settings = tmp_path / ".claude/settings.local.json"
    settings.parent.mkdir()
    settings.write_text("{}")
    c = Controller.create(tmp_path, spec(tmp_path), {"analysis": {"question": "why?"}})
    workspace = Path(c.state["execution_root"])
    assert not (workspace / ".env").exists()
    assert not (workspace / ".claude/settings.local.json").exists()


def test_symlink_output_outside_attempt_rejected(tmp_path):
    outside = tmp_path / "outside.md"
    outside.write_text("not produced by this job")
    class Linker(FakeEngine):
        def run(self, job):
            Path(job["outputs"]["result"]).symlink_to(outside)
    c = Controller.create(tmp_path, spec(tmp_path), {"analysis": {"question": "why?"}})
    assert c.execute(Linker())["status"] == "failed"


def test_failed_analytical_verdict_blocks_consumer_without_retry(tmp_path):
    s = spec(tmp_path)
    s["workers"]["review"]["outputs"] = {"result": "review.json"}
    s["workers"]["review"]["output_checks"] = {"result": {"equals": {"verdict": "pass"}}}
    class Reviewer(FakeEngine):
        def run(self, job):
            if job["name"] == "review":
                self.calls.append("review")
                Path(job["outputs"]["result"]).write_text(json.dumps({"verdict": "fail", "reason": "unsupported claim"}))
            else:
                super().run(job)
    c = Controller.create(tmp_path, s, {"analysis": {"question": "why?"}})
    engine = Reviewer()
    assert c.execute(engine)["status"] == "failed"
    assert engine.calls == ["analysis", "review"]
    assert c.state["agents"]["review"]["attempts"] == 1
    assert c.state["agents"]["review"]["rejected_artifacts"]


def test_snapshot_helper_change_blocks_resume(tmp_path):
    helpers = tmp_path / "helpers"
    helpers.mkdir()
    (helpers / "calculation.py").write_text("VALUE = 1\n")
    c = Controller.create(tmp_path, spec(tmp_path), {"analysis": {"question": "why?"}})
    (Path(c.state["execution_root"]) / "helpers/calculation.py").write_text("VALUE = 2\n")
    with pytest.raises(PipelineError, match="snapshot"):
        c.execute(FakeEngine())


def test_unknown_output_check_rejected_at_creation(tmp_path):
    s = spec(tmp_path)
    s["workers"]["analysis"]["output_checks"] = {"missing": {"equals": {"verdict": "pass"}}}
    with pytest.raises(PipelineError, match="output check"):
        Controller.create(tmp_path, s, {"analysis": {"question": "why?"}})
