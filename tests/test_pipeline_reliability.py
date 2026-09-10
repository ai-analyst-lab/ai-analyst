"""Regression cases recovered from the September course/runtime audit."""

import json
from pathlib import Path

import pytest

from helpers.pipeline.dag import DagError, init_run, load_registry, ready_set, resolve_plan


def worker(name, required=(), optional=()):
    return {"name": name, "depends_on": list(required), "depends_on_any": [],
            "optional_dependencies": list(optional), "critical": True}


def test_optional_failure_releases_consumer_but_waits_until_terminal():
    registry = {"validation": worker("validation"), "sizer": worker("sizer", ["validation"]),
                "story": worker("story", ["validation"], ["sizer"])}
    states = {"validation": {"status": "completed"}, "sizer": {"status": "running"},
              "story": {"status": "pending"}}
    assert ready_set(registry, list(registry), {"agents": states}) == []
    states["sizer"]["status"] = "degraded"
    assert ready_set(registry, list(registry), {"agents": states}) == ["story"]
    states["validation"]["status"] = "failed"
    assert ready_set(registry, list(registry), {"agents": states}) == []


def test_optional_jobs_are_ordered_before_consumer_when_selected():
    r = {"a": worker("a"), "b": worker("b", optional=["a"])}
    assert resolve_plan(r, ["a", "b"]) == [["a"], ["b"]]
    assert resolve_plan(r, ["b"]) == [["b"]]


def test_duplicate_registry_names_fail(tmp_path):
    p = tmp_path / "registry.yaml"
    p.write_text("agents:\n- name: x\n- name: x\n")
    with pytest.raises(DagError, match="Duplicate"):
        load_registry(p)


def test_identical_requests_create_distinct_runs(tmp_path):
    r = {"a": worker("a")}
    first = init_run("sample", "same question", ["a"], registry=r,
                     base=tmp_path / "working/runs", root=tmp_path)
    marker = first / "outputs/keep.txt"
    marker.write_text("existing work")
    second = init_run("sample", "same question", ["a"], registry=r,
                      base=tmp_path / "working/runs", root=tmp_path)
    assert first != second
    assert marker.read_text() == "existing work"
    assert json.loads((first / "pipeline_state.json").read_text())["run_id"] != json.loads(
        (second / "pipeline_state.json").read_text())["run_id"]


def test_real_story_can_continue_without_optional_sizing():
    r = load_registry()
    plan = ["root-cause-investigator", "cross-verification", "validation", "opportunity-sizer", "story-architect"]
    state = {"agents": {name: {"status": "completed"} for name in plan}}
    state["agents"]["opportunity-sizer"]["status"] = "degraded"
    state["agents"]["story-architect"]["status"] = "pending"
    assert ready_set(r, plan, state) == ["story-architect"]
