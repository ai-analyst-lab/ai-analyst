"""BigQuery and Databricks connection branches, exercised against fake clients (no live warehouse).

Covers the code paths added when finishing BigQuery and adding Databricks: query, test_connection,
list_tables, read_table, and verify_remote. Live end-to-end runs need real credentials.
"""
from __future__ import annotations

import pandas as pd

from helpers.data.connection_manager import ConnectionManager


# ----------------------------- BigQuery fakes -----------------------------
class _BQJob:
    def __init__(self, rows):
        self._rows = rows

    def result(self):
        return list(self._rows)


class _BQTable:
    def __init__(self, tid):
        self.table_id = tid


class _FakeBQ:
    project = "my-proj"

    def query(self, sql):
        if "SELECT 1" in sql:
            return _BQJob([{"x": 1}])
        return _BQJob([{"region": "West", "rev": 812}, {"region": "East", "rev": 640}])

    def list_tables(self, ref):
        assert ref == "my-proj.analytics"
        return [_BQTable("orders"), _BQTable("customers")]


def _bq_cm():
    cm = ConnectionManager(config={"type": "bigquery", "connection": {"dataset": "analytics"}})
    cm._connection = _FakeBQ()
    cm._conn_type = "bigquery"
    cm._schema_prefix = "analytics"
    return cm


def test_bigquery_test_connection_reports_project():
    res = _bq_cm().test_connection()
    assert res["ok"] and res["project"] == "my-proj" and res["dataset"] == "analytics"


def test_bigquery_query_and_list_and_read():
    cm = _bq_cm()
    df = cm.query("SELECT region, rev FROM t")
    assert list(df.columns) == ["region", "rev"] and len(df) == 2
    assert cm.list_tables() == ["customers", "orders"]
    assert len(cm.read_table("orders")) == 2


def test_bigquery_verify_remote():
    v = _bq_cm().verify_remote()
    assert v["remote"] is True and v["identity"]["project"] == "my-proj"


# ----------------------------- Databricks fakes -----------------------------
class _DBXCursor:
    def __init__(self):
        self.description = None

    def execute(self, sql, params=None):
        u = sql.upper()
        if "CURRENT_CATALOG" in u:
            self._row = ("main", "default")
            self.description = [("c",), ("s",)]
        elif u.startswith("SHOW TABLES"):
            self._rows = [("default", "orders", False), ("default", "customers", False)]
            self.description = [("database",), ("tableName",), ("isTemporary",)]
        else:
            self._rows = [(1,), (2,), (3,)]
            self.description = [("n",)]

    def fetchone(self):
        return getattr(self, "_row", None)

    def fetchall(self):
        return getattr(self, "_rows", [])

    def close(self):
        pass


class _FakeDBX:
    def cursor(self):
        return _DBXCursor()


def _dbx_cm():
    cm = ConnectionManager(config={"type": "databricks", "connection": {"schema": "default"}})
    cm._connection = _FakeDBX()
    cm._conn_type = "databricks"
    cm._schema_prefix = "default"
    return cm


def test_databricks_test_connection_reports_identity():
    res = _dbx_cm().test_connection()
    assert res["ok"] and res["catalog"] == "main" and res["schema"] == "default"


def test_databricks_query_list_read():
    cm = _dbx_cm()
    df = cm.query("SELECT n FROM t")
    assert list(df.columns) == ["n"] and len(df) == 3
    assert cm.list_tables() == ["customers", "orders"]
    assert len(cm.read_table("orders")) == 3


def test_databricks_verify_remote():
    v = _dbx_cm().verify_remote()
    assert v["remote"] is True and v["identity"]["catalog"] == "main"
