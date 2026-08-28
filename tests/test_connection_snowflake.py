"""Snowflake connection branches, exercised against a fake connector (no live warehouse).

Covers the code paths that used to be missing: test_connection, list_tables, read_table, and the
verify_remote guard that proves a session is on Snowflake rather than the local DuckDB fallback.
A live end-to-end Snowflake test needs real credentials and is done separately.
"""
from __future__ import annotations

import pandas as pd
import pytest

from helpers.data.connection_manager import ConnectionManager


class _FakeCursor:
    def __init__(self, parent):
        self._p = parent
        self.description = None

    def execute(self, sql, params=None):
        self._p.executed.append(sql)
        u = sql.upper()
        if "CURRENT_ACCOUNT" in u:
            self._row = ("ACME-PROD", "ANALYST_WH", "SALES_DB", "PUBLIC", "8.1.0")
            self.description = [("a",)]
        elif "INFORMATION_SCHEMA.TABLES" in u:
            self._rows = [("customers",), ("orders",), ("products",)]
        else:
            self.description = [("x",)]

    def fetchone(self):
        return getattr(self, "_row", None)

    def fetchall(self):
        return getattr(self, "_rows", [])

    def fetch_pandas_all(self):
        return pd.DataFrame({"n": [1, 2, 3]})

    def close(self):
        pass


class _FakeConn:
    def __init__(self):
        self.executed = []

    def cursor(self):
        return _FakeCursor(self)


def _snowflake_cm():
    cm = ConnectionManager(config={"type": "snowflake", "connection": {"schema": "public"}})
    cm._connection = _FakeConn()
    cm._conn_type = "snowflake"
    cm._schema_prefix = "public"
    return cm


def test_test_connection_reports_live_identity():
    cm = _snowflake_cm()
    res = cm.test_connection()
    assert res["ok"] is True and res["type"] == "snowflake"
    assert res["account"] == "ACME-PROD" and res["warehouse"] == "ANALYST_WH"
    assert "ACME-PROD" in res["message"]


def test_verify_remote_true_on_snowflake():
    cm = _snowflake_cm()
    v = cm.verify_remote()
    assert v["remote"] is True and v["identity"]["account"] == "ACME-PROD"


def test_verify_remote_account_mismatch_fails():
    cm = _snowflake_cm()
    v = cm.verify_remote(expect_account="OTHER-ORG")
    assert v["remote"] is False and "expected OTHER-ORG" in v["reason"]


def test_verify_remote_flags_local_fallback():
    # A dataset that declares snowflake but resolved to the local DuckDB copy must be caught.
    cm = ConnectionManager(config={"type": "csv"})
    cm._conn_type = "duckdb"
    v = cm.verify_remote()
    assert v["remote"] is False and "AAP_USE_REMOTE" in v["reason"]


def test_list_tables_snowflake():
    cm = _snowflake_cm()
    assert cm.list_tables() == ["customers", "orders", "products"]


def test_read_table_snowflake_uses_query():
    cm = _snowflake_cm()
    df = cm.read_table("orders")
    assert list(df.columns) == ["n"] and len(df) == 3
    assert any("SELECT * FROM public.orders" in q for q in cm._connection.executed)
