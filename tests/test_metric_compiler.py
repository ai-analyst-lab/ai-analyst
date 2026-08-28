"""Tests for the Tier A metric compiler (helpers/data/metric_compiler.py).

Covers: compile correctness, the whitelist guards (reject unknown dim/filter), parameter binding
(values are bound, never interpolated), the ratio bound guard, and end-to-end execution against a tiny SYNTHETIC dataset built at
runtime in a temp dir (the repo ships no data), with exact expected numbers derived from it.
"""
from __future__ import annotations

import math
from pathlib import Path

import pytest

from helpers.data import metric_compiler as mc

ROOT = Path(__file__).resolve().parents[1]

# Fixture metrics for the tests. The repo ships NO baked-in metrics (a user defines their own),
# so the compiler is tested against these fixtures pointed at a synthetic dataset built in a temp dir.
_FIXTURES = {
    "avg-daily-volume": {"compile": {
        "measure": "AVG(Volume)", "table": "sp500_daily", "grain_key": ["Date"],
        "dimensions": {"year": "extract(year from Date)"},
        "filters": {"year": "extract(year from Date) = :year"}}},
    "total-volume": {"compile": {
        "measure": "SUM(Volume)", "table": "sp500_daily", "grain_key": ["Date"],
        "dimensions": {"year": "extract(year from Date)"},
        "filters": {"year": "extract(year from Date) = :year"}}},
    "avg-close": {"compile": {
        "measure": "AVG(Close)", "table": "sp500_daily", "grain_key": ["Date"],
        "dimensions": {"year": "extract(year from Date)"},
        "filters": {"year": "extract(year from Date) = :year"}}},
    "sector-share-of-volume": {"compile": {
        "measure": "SUM(Volume)", "denominator": "SUM(SUM(Volume)) OVER ()",
        "table": "sector_etfs_daily", "grain_key": ["Date", "Sector"],
        "dimensions": {"sector": "Sector"},
        "filters": {"year": "extract(year from Date) = :year"}}},
}


def _load(metric_id):
    import copy
    return copy.deepcopy(_FIXTURES[metric_id])


# ---- compile-level (no database) ----

def test_compile_simple_measure_with_filter():
    metric = _load("avg-daily-volume")
    sql, params = mc.compile_metric(metric, group_by=[], filters={"year": 2024})
    assert "AVG(Volume)" in sql and "AS value" in sql
    assert "FROM sp500_daily" in sql
    assert "?" in sql and "extract(year from Date)" in sql
    assert params == [2024]
    assert "GROUP BY" not in sql  # no dimension requested


def test_compile_group_by_dimension():
    metric = _load("total-volume")
    sql, params = mc.compile_metric(metric, group_by=["year"], filters={})
    assert "GROUP BY" in sql and "ORDER BY" in sql
    assert "AS year" in sql


def test_ratio_metric_uses_safe_divide():
    metric = _load("sector-share-of-volume")
    sql, params = mc.compile_metric(metric, group_by=["sector"], filters={"year": 2024})
    assert "OVER ()" in sql  # the denominator window
    assert params == [2024]


def test_unknown_dimension_rejected():
    metric = _load("avg-daily-volume")
    with pytest.raises(mc.MetricCompileError):
        mc.compile_metric(metric, group_by=["not_a_dim"], filters={})


def test_unknown_filter_rejected():
    metric = _load("avg-daily-volume")
    with pytest.raises(mc.MetricCompileError):
        mc.compile_metric(metric, group_by=[], filters={"ticker": "AAPL"})


def test_values_are_bound_not_interpolated():
    metric = _load("avg-daily-volume")
    # An injection attempt as a filter value must land in params, never in the SQL string.
    sql, params = mc.compile_metric(metric, filters={"year": "2024; DROP TABLE sp500_daily"})
    assert "DROP TABLE" not in sql
    assert params == ["2024; DROP TABLE sp500_daily"]


def test_is_compilable():
    assert mc.is_compilable(_load("avg-daily-volume")) is True
    assert mc.is_compilable({"name": "x"}) is False
    assert mc.is_compilable({"compile": {"table": "t"}}) is False  # missing measure


# ---- execution against the bundled sp500 data ----

@pytest.fixture(scope="module")
def conn(tmp_path_factory):
    # Build a tiny, deterministic dataset in a temp dir so the tests carry their own data.
    # sp500_daily: 1 row/day. 2023: Volume 100,200 (avg 150) Close 4000,4200 (avg 4100).
    #              2024: Volume 300,500 (avg 400, sum 800) Close 5000,5800.
    # sector_etfs_daily (2024): Tech 300+400=700, Energy 100+200=300, total 1000 -> shares .7/.3.
    from helpers.data.connection_manager import ConnectionManager
    d = tmp_path_factory.mktemp("synth_sp500")
    (d / "sp500_daily.csv").write_text(
        "Date,Volume,Close\n"
        "2023-06-01,100,4000\n2023-06-02,200,4200\n"
        "2024-06-01,300,5000\n2024-06-02,500,5800\n")
    (d / "sector_etfs_daily.csv").write_text(
        "Date,Sector,Volume\n"
        "2024-06-01,Tech,300\n2024-06-01,Energy,100\n"
        "2024-06-02,Tech,400\n2024-06-02,Energy,200\n")
    cm = ConnectionManager(config={"type": "csv", "csv_path": str(d)})
    cm.connect()
    return cm


def test_avg_daily_volume_2024_exact(conn):
    df = mc.run_metric(conn, _load("avg-daily-volume"), filters={"year": 2024})
    assert math.isclose(float(df["value"].iloc[0]), 400.0, rel_tol=1e-9)  # (300+500)/2


def test_avg_close_2023_exact(conn):
    df = mc.run_metric(conn, _load("avg-close"), filters={"year": 2023})
    assert math.isclose(float(df["value"].iloc[0]), 4100.0, rel_tol=1e-9)  # (4000+4200)/2


def test_sector_share_sums_to_one_and_bounded(conn):
    df = mc.run_metric(conn, _load("sector-share-of-volume"), group_by=["sector"], filters={"year": 2024})
    assert math.isclose(float(df["value"].sum()), 1.0, abs_tol=1e-6)
    assert df["value"].max() <= 1.0 and df["value"].min() >= 0.0


def test_ratio_guard_halts_on_impossible_share(conn, monkeypatch):
    # Force a denominator that under-counts so the share exceeds 1, and confirm the guard halts
    # rather than returning an impossible number.
    bad = _load("sector-share-of-volume")
    bad["compile"]["denominator"] = "SUM(Volume) / 10.0"  # ten times too small -> shares ~10x
    with pytest.raises(mc.MetricCompileError):
        mc.run_metric(conn, bad, group_by=["sector"], filters={"year": 2024})


def test_filter_param_count_mismatch_raises():
    metric = _load("avg-daily-volume")
    # A list value with the wrong number of markers must raise a clear error, not StopIteration.
    metric["compile"]["filters"]["between"] = "Date between :a and :b"
    with pytest.raises(mc.MetricCompileError):
        mc.compile_metric(metric, filters={"between": [1, 2, 3]})


def test_list_value_filter_binds_in_order():
    metric = _load("avg-daily-volume")
    metric["compile"]["filters"]["between"] = "Date between :a and :b"
    sql, params = mc.compile_metric(metric, filters={"between": ["2024-01-01", "2024-12-31"]})
    assert params == ["2024-01-01", "2024-12-31"]
    assert sql.count("?") == 2


def test_fanout_guard_halts_on_wrong_grain(conn):
    # avg-daily-volume declares grain_key [Date] and its table is 1 row/day, so it passes.
    mc.run_metric(conn, _load("avg-daily-volume"), filters={"year": 2024})
    # Point the same metric at the long-format sector table (many rows per Date) with grain_key
    # [Date]: rows != distinct Date, so the fan-out guard must halt.
    bad = _load("avg-daily-volume")
    bad["compile"]["table"] = "sector_etfs_daily"
    bad["compile"]["grain_key"] = ["Date"]
    with pytest.raises(mc.MetricCompileError):
        mc.run_metric(conn, bad, filters={"year": 2024})


def test_ratio_bounds_from_metric(conn):
    # A legitimate ratio that exceeds 1 (this year vs a smaller base) must NOT halt when the metric
    # declares wider bounds.
    metric = {
        "compile": {
            "measure": "SUM(Volume)",
            "denominator": "SUM(Volume) / 2.0",   # ratio ~= 2.0 everywhere
            "table": "sp500_daily",
            "dimensions": {},
            "filters": {"year": "extract(year from Date) = :year"},
            "value_bounds": [0, 10],
        }
    }
    df = mc.run_metric(conn, metric, filters={"year": 2024})
    assert float(df["value"].iloc[0]) > 1.0  # allowed by the wider bound
