"""Redshift / SQL Server / MySQL connection branches (the Postgres-family DBAPI path).

These share the same query / test_connection / list_tables / read_table / verify_remote code as
Postgres, so one parametrized fake DBAPI connection covers all three. Live runs need real creds.
"""
from __future__ import annotations

import pandas as pd
import pytest

from helpers.data.connection_manager import ConnectionManager


class _FamCursor:
    def __init__(self):
        self.description = None

    def execute(self, sql, params=None):
        self._rows = []
        if "information_schema.tables" in sql.lower():
            self._rows = [("customers",), ("orders",)]
        elif "select 1" in sql.lower():
            self._rows = [(1,)]

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def fetchall(self):
        return self._rows

    def close(self):
        pass


class _FamConn:
    def cursor(self):
        return _FamCursor()


def _cm(ctype):
    cm = ConnectionManager(config={"type": ctype, "connection": {"schema": "public"}})
    cm._connection = _FamConn()
    cm._conn_type = ctype
    cm._schema_prefix = "public"
    return cm


@pytest.mark.parametrize("ctype", ["redshift", "mssql", "mysql"])
def test_test_connection_ok(ctype):
    res = _cm(ctype).test_connection()
    assert res["ok"] is True and res["type"] == ctype


@pytest.mark.parametrize("ctype", ["redshift", "mssql", "mysql"])
def test_list_tables(ctype):
    assert _cm(ctype).list_tables() == ["customers", "orders"]


@pytest.mark.parametrize("ctype", ["redshift", "mssql", "mysql"])
def test_verify_remote_true(ctype):
    v = _cm(ctype).verify_remote()
    assert v["remote"] is True and v["connection_type"] == ctype


@pytest.mark.parametrize("ctype", ["redshift", "mssql", "mysql"])
def test_query_and_read_table(ctype, monkeypatch):
    # query/read_table use pd.read_sql; stub it so the branch is exercised without a live driver.
    monkeypatch.setattr(pd, "read_sql", lambda sql, conn: pd.DataFrame({"n": [1, 2]}))
    cm = _cm(ctype)
    assert len(cm.query("SELECT * FROM orders")) == 2
    assert len(cm.read_table("orders")) == 2


def test_dialects_registered():
    from helpers.data.sql_dialect import get_dialect
    assert get_dialect("redshift").name == "redshift"
    assert get_dialect("mysql").safe_divide("a", "b") == "a / NULLIF(b, 0)"
    assert get_dialect("mssql").string_agg("x", ",") == "STRING_AGG(x, ',')"
