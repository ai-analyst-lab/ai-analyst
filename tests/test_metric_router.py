"""Tests for the Tier router (helpers/data/metric_router.py)."""
from __future__ import annotations

from pathlib import Path

from helpers.data import metric_router as mr

ROOT = Path(__file__).resolve().parents[1]


def test_defined_compilable_metric_is_tier_a():
    r = mr.route("sp500", "avg-daily-volume", project_root=ROOT)
    assert r["tier"] == "A" and r["mode"] == mr.MODE_CONTRACT
    assert r["metric_id"] == "avg-daily-volume"


def test_unresolved_metric_falls_forward_to_tier_c():
    r = mr.route("sp500", None, project_root=ROOT)
    assert r["tier"] == "C" and r["mode"] == mr.MODE_GENERATED
    assert r["metric_id"] is None


def test_unknown_metric_id_falls_to_tier_c():
    r = mr.route("sp500", "does-not-exist", project_root=ROOT)
    assert r["tier"] == "C"


def test_external_binding_is_tier_b(tmp_path):
    # A metric that binds to an external layer routes to Tier B with the source in the mode.
    d = tmp_path / ".knowledge" / "datasets" / "acme" / "metrics"
    d.mkdir(parents=True)
    (d / "revenue.yaml").write_text(
        "name: Revenue\ncompile:\n  external:\n    source: dbt\n    ref: revenue\n"
    )
    r = mr.route("acme", "revenue", project_root=tmp_path)
    assert r["tier"] == "B" and r["mode"] == "external:dbt"


def test_list_metrics():
    ids = [m["id"] for m in mr.list_metrics("sp500", project_root=ROOT)]
    assert "avg-daily-volume" in ids and "sector-share-of-volume" in ids
