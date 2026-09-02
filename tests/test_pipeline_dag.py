"""Tests for helpers/pipeline/dag.py -- plan resolution, gates, run init, metrics."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from helpers.pipeline.dag import (
    DagError,
    init_run,
    is_deadlocked,
    load_plans,
    load_registry,
    plan_warnings,
    ready_set,
    record_metrics,
    resolve_plan,
    slugify,
    validate_registry,
    write_metrics,
)


def _agent(name, depends_on=None, depends_on_any=None, step=None, critical=True, file=None):
    return {
        "name": name,
        "file": file or f"agents/pipeline/{name}.md",
        "pipeline_step": step,
        "critical": critical,
        "depends_on": list(depends_on or []),
        "depends_on_any": list(depends_on_any or []),
    }


@pytest.fixture
def registry():
    return {
        "framing": _agent("framing", step=1),
        "explorer": _agent("explorer", step=2),
        "hypothesis": _agent("hypothesis", ["framing"], step=3),
        "descriptive": _agent("descriptive", ["explorer"], step=5),
        "overtime": _agent("overtime", ["explorer"], step=5),
        "cohort": _agent("cohort", ["explorer"], step=5),
        "root-cause": _agent("root-cause", ["descriptive"], step=6),
        "cross-verify": _agent(
            "cross-verify", ["root-cause"], ["descriptive", "overtime", "cohort"], step=6.5
        ),
        "validation": _agent("validation", ["cross-verify"], step=7),
        "sizer": _agent("sizer", ["validation"], step=8, critical=False),
    }


# ---------------------------------------------------------------------------
# resolve_plan
# ---------------------------------------------------------------------------

class TestResolvePlan:
    def test_tiers_follow_dependencies(self, registry):
        plan = ["framing", "explorer", "hypothesis", "descriptive", "root-cause", "cross-verify", "validation"]
        tiers = resolve_plan(registry, plan)
        assert tiers == [
            ["framing", "explorer"],
            ["hypothesis", "descriptive"],
            ["root-cause"],
            ["cross-verify"],
            ["validation"],
        ]

    def test_or_gate_members_all_precede_when_present(self, registry):
        plan = ["explorer", "descriptive", "overtime", "root-cause", "cross-verify"]
        tiers = resolve_plan(registry, plan)
        idx = {name: i for i, tier in enumerate(tiers) for name in tier}
        assert idx["cross-verify"] > idx["descriptive"]
        assert idx["cross-verify"] > idx["overtime"]
        assert idx["cross-verify"] > idx["root-cause"]

    def test_dependency_outside_plan_is_dropped(self, registry):
        # cross-verify's deps are all outside the plan -> tier 0
        assert resolve_plan(registry, ["cross-verify", "validation"]) == [["cross-verify"], ["validation"]]
        warnings = plan_warnings(registry, ["cross-verify", "validation"])
        assert any("root-cause" in w for w in warnings)
        assert any("depends_on_any" in w for w in warnings)

    def test_cycle_detected(self, registry):
        registry["framing"]["depends_on"] = ["hypothesis"]
        with pytest.raises(DagError, match="Cycle detected"):
            resolve_plan(registry, ["framing", "hypothesis"])

    def test_unknown_agent(self, registry):
        with pytest.raises(DagError, match="Unknown agent"):
            resolve_plan(registry, ["framing", "nope"])

    def test_unknown_plan_name(self, registry):
        with pytest.raises(DagError, match="Unknown plan"):
            resolve_plan(registry, "no_such_plan", plans={"deep_dive": {"agents": ["framing"]}})

    def test_named_plan(self, registry):
        plans = {"deep_dive": {"agents": ["framing", "hypothesis"]}}
        assert resolve_plan(registry, "deep_dive", plans=plans) == [["framing"], ["hypothesis"]]


# ---------------------------------------------------------------------------
# ready_set / deadlock
# ---------------------------------------------------------------------------

class TestReadySet:
    PLAN = ["explorer", "descriptive", "overtime", "root-cause", "cross-verify", "validation"]

    def _state(self, **statuses):
        return {"agents": {name: {"status": s} for name, s in statuses.items()}}

    def test_initial_ready_is_tier_zero(self, registry):
        assert ready_set(registry, self.PLAN, {"agents": {}}) == ["explorer"]

    def test_and_gate_requires_completion(self, registry):
        state = self._state(explorer="in_progress")
        assert ready_set(registry, self.PLAN, state) == []
        state = self._state(explorer="completed")
        assert ready_set(registry, self.PLAN, state) == ["descriptive", "overtime"]

    def test_or_gate_satisfied_by_one_alternative(self, registry):
        state = self._state(
            explorer="complete", descriptive="complete", overtime="skipped", **{"root-cause": "completed"}
        )
        assert ready_set(registry, self.PLAN, state) == ["cross-verify"]

    def test_skipped_does_not_satisfy_or_gate(self, registry):
        state = self._state(
            explorer="complete", descriptive="skipped", overtime="skipped", **{"root-cause": "completed"}
        )
        assert "cross-verify" not in ready_set(registry, self.PLAN, state)
        assert is_deadlocked(registry, self.PLAN, state)

    def test_degraded_does_not_satisfy_and_gate(self, registry):
        state = self._state(explorer="complete", descriptive="complete", **{"root-cause": "complete", "cross-verify": "degraded"})
        assert "validation" not in ready_set(registry, self.PLAN, state)

    def test_not_deadlocked_while_running(self, registry):
        state = self._state(explorer="in_progress")
        assert not is_deadlocked(registry, self.PLAN, state)

    def test_completed_legacy_counts(self, registry):
        state = self._state(explorer="completed_legacy")
        assert "descriptive" in ready_set(registry, self.PLAN, state)


# ---------------------------------------------------------------------------
# init_run
# ---------------------------------------------------------------------------

class TestInitRun:
    def test_layout_state_and_symlink(self, registry, tmp_path):
        base = tmp_path / "working" / "runs"
        run_dir = init_run(
            "acme", "Why did revenue drop in Q3?", ["framing", "hypothesis"],
            base=base, registry=registry, date="2026-09-02",
        )
        assert run_dir == base / "2026-09-02_acme_why-did-revenue-drop-in-q3"
        assert (run_dir / "working").is_dir() and (run_dir / "outputs").is_dir()
        assert (run_dir / "working" / "query_log_acme_2026-09-02.jsonl").exists()

        state = json.loads((run_dir / "pipeline_state.json").read_text())
        assert state["schema_version"] == 2
        assert state["status"] == "running"
        assert state["run_id"] == run_dir.name
        assert state["agents"]["framing"] == {"status": "pending"}
        assert state["agents"]["hypothesis"] == {"status": "pending"}
        # pipeline agents not in the plan are recorded as skipped
        assert state["agents"]["explorer"] == {"status": "skipped"}
        assert state["tiers"] == [["framing"], ["hypothesis"]]

        latest = tmp_path / "working" / "latest"
        assert latest.is_symlink()
        assert latest.resolve() == run_dir.resolve()

    def test_symlink_is_replaced_on_second_run(self, registry, tmp_path):
        base = tmp_path / "working" / "runs"
        first = init_run("acme", "first question", ["framing"], base=base, registry=registry, date="2026-09-01")
        second = init_run("acme", "second question", ["framing"], base=base, registry=registry, date="2026-09-02")
        latest = tmp_path / "working" / "latest"
        assert latest.resolve() == second.resolve() != first.resolve()

    def test_unknown_plan_agent(self, registry, tmp_path):
        with pytest.raises(DagError):
            init_run("acme", "q", ["nope"], base=tmp_path / "working" / "runs", registry=registry)

    def test_slugify_limits(self):
        assert slugify("Why did activation drop? A very long question with many many words") == \
            "why-did-activation-drop-a-very-long-ques"
        assert slugify("???") == "run"


# ---------------------------------------------------------------------------
# metrics
# ---------------------------------------------------------------------------

class TestMetrics:
    def _state(self):
        return {
            "run_id": "2026-09-02_acme_q",
            "started_at": "2026-09-02T09:00:00Z",
            "completed_at": "2026-09-02T09:10:00Z",
            "tiers": [["framing", "explorer"], ["hypothesis"]],
            "agents": {
                "framing": {"status": "complete", "started_at": "2026-09-02T09:00:00Z", "completed_at": "2026-09-02T09:02:00Z"},
                "explorer": {"status": "complete", "started_at": "2026-09-02T09:00:00Z", "completed_at": "2026-09-02T09:04:00Z"},
                "hypothesis": {"status": "degraded", "started_at": "2026-09-02T09:04:00Z", "completed_at": "2026-09-02T09:07:00Z", "retries": 1},
                "sizer": {"status": "skipped"},
            },
        }

    def test_parallel_efficiency_and_summary(self):
        m = record_metrics(self._state())
        tier0 = m["tiers"]["0"]
        assert tier0["duration_seconds"] == 240.0          # wall clock 09:00 -> 09:04
        assert tier0["sequential_duration_seconds"] == 360.0  # 120 + 240
        assert tier0["parallel_efficiency"] == 1.5
        assert tier0["parallel_agents"] == 2
        assert m["tiers"]["1"]["parallel_efficiency"] == 1.0
        assert m["agents"]["hypothesis"]["retries"] == 1
        assert m["agents"]["sizer"]["duration_seconds"] is None
        assert m["total_duration_seconds"] == 600.0
        assert m["summary"] == {
            "total_agents": 4, "completed": 2, "degraded": 1, "failed": 0,
            "skipped": 1, "total_tiers": 2, "avg_parallel_efficiency": 1.25,
        }

    def test_empty_state(self):
        m = record_metrics({"agents": {}})
        assert m["summary"]["total_agents"] == 0
        assert m["summary"]["avg_parallel_efficiency"] == 0.0

    def test_write_metrics(self, tmp_path):
        path = tmp_path / "pipeline_metrics.json"
        m = write_metrics(self._state(), path)
        assert json.loads(path.read_text()) == m


# ---------------------------------------------------------------------------
# Real registry and plans
# ---------------------------------------------------------------------------

class TestRealRegistry:
    def test_registry_passes_preflight(self):
        registry = load_registry()
        assert validate_registry(registry) == []

    def test_every_plan_resolves(self):
        registry = load_registry()
        plans = load_plans()
        assert {"full_presentation", "deep_dive", "quick_chart", "refresh_deck", "validate_only"} <= set(plans)
        for name in plans:
            tiers = resolve_plan(registry, name, plans=plans)
            assert sum(len(t) for t in tiers) == len(plans[name]["agents"])

    def test_full_presentation_order(self):
        registry = load_registry()
        tiers = resolve_plan(registry, "full_presentation")
        idx = {name: i for i, tier in enumerate(tiers) for name in tier}
        assert idx["question-framing"] == idx["data-explorer"] == 0
        assert idx["cross-verification"] > idx["root-cause-investigator"]
        assert idx["deck-creator"] > idx["storytelling"]
        assert idx["comms-drafter"] > idx["close-the-loop"]
