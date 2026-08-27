"""ConnectionManager.query() auto-logs every query to the query log at the moment it executes.

This is the provenance capture: the log records what actually ran on the connection, not what the
analyst later claims it ran. Covered on DuckDB so no warehouse is needed; the path is identical for
Snowflake (only the execute branch differs).
"""
from datetime import date

import duckdb

from helpers.data.connection_manager import ConnectionManager
from helpers.provenance import query_log


def _mk_db(tmp_path):
    db = tmp_path / "t.duckdb"
    con = duckdb.connect(str(db))
    con.execute("create table orders as select 42 as total")
    con.close()
    return db


def _cm(db):
    return ConnectionManager(config={"type": "duckdb", "duckdb_path": str(db), "dataset_id": "testds"})


def _today_entries(tmp_path):
    return query_log.read_log("testds", date.today().isoformat())


def test_query_autologs_at_execution(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "working").mkdir(exist_ok=True)
    monkeypatch.setattr(query_log, "_EXPLICIT_LOG_DIR", tmp_path)
    monkeypatch.setattr(query_log, "_AUTOLOG_ENABLED", True)

    cm = _cm(_mk_db(tmp_path))
    df = cm.query("select sum(total) as s from orders")
    assert int(df.iloc[0, 0]) == 42

    entries = _today_entries(tmp_path)
    assert len(entries) == 1
    e = entries[0]
    assert "sum(total)" in e["sql"].lower()          # the exact SQL that ran
    assert float(e["result_value"]) == 42.0          # scalar result captured (1x1 cell)
    assert e.get("analysis_id")                       # grouped under an analysis_id
    assert "orders" in (e.get("tables_accessed") or [])
    assert e["connection_type"] == "duckdb"


def test_query_log_false_suppresses(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "working").mkdir(exist_ok=True)
    monkeypatch.setattr(query_log, "_EXPLICIT_LOG_DIR", tmp_path)
    monkeypatch.setattr(query_log, "_AUTOLOG_ENABLED", True)

    cm = _cm(_mk_db(tmp_path))
    cm.query("select sum(total) as s from orders", log=False)
    assert _today_entries(tmp_path) == []


def test_set_autolog_false_suppresses(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "working").mkdir(exist_ok=True)
    monkeypatch.setattr(query_log, "_EXPLICIT_LOG_DIR", tmp_path)
    monkeypatch.setattr(query_log, "_AUTOLOG_ENABLED", False)   # a pipeline logs by hand

    cm = _cm(_mk_db(tmp_path))
    cm.query("select sum(total) as s from orders")
    assert _today_entries(tmp_path) == []
