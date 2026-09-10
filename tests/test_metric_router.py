"""Tests for the Tier router (helpers/data/metric_router.py).

Self-contained: metrics are written into a tmp .knowledge tree, so the tests do not depend on any
metric files shipping in the repo (the repo ships none; a user defines their own).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from helpers.data import metric_router as mr


@pytest.fixture()
def ds(tmp_path):
    """A tmp dataset dir with a couple of metrics; returns (project_root, dataset)."""
    d = tmp_path / ".knowledge" / "datasets" / "acme" / "metrics"
    d.mkdir(parents=True)
    (d / "revenue.yaml").write_text(
        "name: Revenue\ncompile:\n  measure: SUM(amount)\n  table: orders\n"
    )
    (d / "note.yaml").write_text(  # defined but not compilable (no compile block)
        "name: A Note\ndefinition:\n  plain_english: prose only\n"
    )
    (d / "ext.yaml").write_text(
        "name: Ext\ncompile:\n  external:\n    source: dbt\n    ref: revenue\n"
    )
    (d / "index.yaml").write_text(
        "- id: revenue\n  name: Revenue\n- id: note\n  name: A Note\n- id: ext\n  name: Ext\n"
    )
    return tmp_path, "acme"


def test_defined_compilable_metric_is_tier_a(ds):
    root, dataset = ds
    r = mr.route(dataset, "revenue", project_root=root)
    assert r["tier"] == "A" and r["mode"] == mr.MODE_CONTRACT and r["metric_id"] == "revenue"


def test_defined_but_uncompilable_falls_to_tier_c(ds):
    root, dataset = ds
    r = mr.route(dataset, "note", project_root=root)
    assert r["tier"] == "C" and r["mode"] == mr.MODE_CONTRACT_GUIDED
    assert r["metric_id"] == "note"


def test_external_binding_is_tier_b(ds):
    root, dataset = ds
    r = mr.route(dataset, "ext", project_root=root)
    assert r["tier"] == "B" and r["mode"] == "external:dbt"


def test_unresolved_metric_falls_forward_to_tier_c(ds):
    root, dataset = ds
    r = mr.route(dataset, None, project_root=root)
    assert r["tier"] == "C" and r["metric_id"] is None


def test_unknown_metric_id_falls_to_tier_c(ds):
    root, dataset = ds
    assert mr.route(dataset, "does-not-exist", project_root=root)["tier"] == "C"


def test_list_metrics(ds):
    root, dataset = ds
    ids = [m["id"] for m in mr.list_metrics(dataset, project_root=root)]
    assert ids == ["revenue", "note", "ext"]


def test_list_metrics_empty_when_none_defined(tmp_path):
    assert mr.list_metrics("nothing", project_root=tmp_path) == []


def test_router_reads_the_resolved_context_directory(tmp_path):
    local = tmp_path / ".knowledge" / "datasets" / "acme" / "metrics"
    local.mkdir(parents=True)
    resolved = tmp_path / "shared" / "datasets" / "acme"
    (resolved / "metrics").mkdir(parents=True)
    (resolved / "metrics" / "revenue.yaml").write_text(
        "name: Revenue\ncompile:\n  measure: SUM(amount)\n  table: orders\n"
    )
    (resolved / "metrics" / "index.yaml").write_text(
        "- id: revenue\n  name: Revenue\n"
    )
    result = mr.route("acme", "revenue", project_root=tmp_path, context_dir=resolved)
    assert result["tier"] == "A"
    assert [row["id"] for row in mr.list_metrics("acme", context_dir=resolved)] == ["revenue"]
