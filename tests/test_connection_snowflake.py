"""Snowflake connection branches, exercised against a fake connector (no live warehouse).

Covers the code paths that used to be missing: test_connection, list_tables, read_table, and the
verify_remote guard that proves a session is on Snowflake rather than the local DuckDB fallback.
A live end-to-end Snowflake test needs real credentials and is done separately.
"""
from __future__ import annotations

import sys
import types

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
            self._row = (
                "ACME-PROD",
                "COURSE_STUDENT",
                "READ_ONLY",
                "ANALYST_WH",
                "SALES_DB",
                "PUBLIC",
                "8.1.0",
            )
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


class _NoArrowCursor(_FakeCursor):
    def execute(self, sql, params=None):
        self._p.executed.append(sql)
        self.description = [("N",)]
        self._rows = [(47_199,)]

    def fetch_pandas_all(self):
        raise RuntimeError("Optional dependency: 'pandas' is not installed")


class _NoArrowConn(_FakeConn):
    def cursor(self):
        return _NoArrowCursor(self)


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
    assert res["user"] == "COURSE_STUDENT" and res["role"] == "READ_ONLY"
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


def test_snowflake_query_falls_back_when_connector_pandas_extra_is_missing():
    cm = ConnectionManager(config={"type": "snowflake", "connection": {"schema": "public"}})
    cm._connection = _NoArrowConn()
    cm._conn_type = "snowflake"
    cm._schema_prefix = "public"

    df = cm.query("SELECT COUNT(*) AS n FROM orders", log=False)

    assert df.iloc[0, 0] == 47_199
    assert list(df.columns) == ["N"]


def _fake_snowflake_module(monkeypatch):
    """Install a fake snowflake.connector and return its captured kwargs."""
    captured = {}
    connector = types.ModuleType("snowflake.connector")

    def connect(**kwargs):
        captured.update(kwargs)
        return _FakeConn()

    connector.connect = connect
    snowflake = types.ModuleType("snowflake")
    snowflake.connector = connector
    monkeypatch.setitem(sys.modules, "snowflake", snowflake)
    monkeypatch.setitem(sys.modules, "snowflake.connector", connector)
    return captured


def test_connect_snowflake_uses_explicit_pat(monkeypatch):
    captured = _fake_snowflake_module(monkeypatch)
    cm = ConnectionManager(config={
        "type": "snowflake",
        "connection": {
            "account": "ORG-ACCOUNT",
            "user": "COURSE_AGENT",
            "authenticator": "programmatic_access_token",
            "token": "secret-token",
            "warehouse": "COURSE_WH",
            "database": "COURSE_DB",
            "schema": "COURSE_SCHEMA",
            "role": "COURSE_READER",
        },
    })

    cm.connect()

    assert captured["authenticator"] == "PROGRAMMATIC_ACCESS_TOKEN"
    assert captured["token"] == "secret-token"
    assert "password" not in captured
    assert captured["role"] == "COURSE_READER"


def test_connect_snowflake_keeps_password_compatibility(monkeypatch):
    captured = _fake_snowflake_module(monkeypatch)
    cm = ConnectionManager(config={
        "type": "snowflake",
        "connection": {
            "account": "ORG-ACCOUNT",
            "user": "ANALYST",
            "password": "legacy-secret",
        },
    })

    cm.connect()

    assert captured["password"] == "legacy-secret"
    assert "authenticator" not in captured
    assert "token" not in captured


def test_connect_snowflake_pat_requires_token(monkeypatch):
    _fake_snowflake_module(monkeypatch)
    cm = ConnectionManager(config={
        "type": "snowflake",
        "connection": {
            "authenticator": "pat",
            "token": "",
        },
    })

    with pytest.raises(ConnectionError, match="SNOWFLAKE_TOKEN") as exc:
        cm.connect()

    assert "token=" not in str(exc.value)
