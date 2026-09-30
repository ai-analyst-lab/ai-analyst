"""Scoped metadata API: no warehouse credentials or network needed."""
from unittest.mock import Mock

import pytest

from helpers.data.connection_manager import ConnectionManager


def manager(config=None):
    cm = ConnectionManager(config=config or {
        "type": "snowflake", "connection": {"database": "APP_DB", "schema": "PUBLIC"},
    })
    cursor = Mock(sfqid="metadata-query-id")
    cursor.fetchall.return_value = [
        ("ID", "NUMBER", "NO", 38, 0),
        ("AMOUNT", "NUMBER", "YES", 12, 2),
        ("NAME", "TEXT", "YES", None, None),
        ("OCCURRED_AT", "TIMESTAMP_NTZ", "NO", None, None),
    ]
    cm._connection = Mock()
    cm._connection.cursor.return_value = cursor
    cm._autolog_query = Mock()
    return cm, cursor


@pytest.mark.parametrize("reference", ["orders", "public.orders", "APP_DB.PUBLIC.ORDERS"])
def test_metadata_is_authoritative_scoped_ordered_and_bound(reference):
    cm, cursor = manager()
    assert cm.get_table_schema(reference) == [
        {"name": "ID", "type": "NUMBER(38,0)", "nullable": False},
        {"name": "AMOUNT", "type": "NUMBER(12,2)", "nullable": True},
        {"name": "NAME", "type": "TEXT", "nullable": True},
        {"name": "OCCURRED_AT", "type": "TIMESTAMP_NTZ", "nullable": False},
    ]
    sql, parameters = cursor.execute.call_args.args
    assert "APP_DB.INFORMATION_SCHEMA.COLUMNS" in sql
    assert "ORDER BY ORDINAL_POSITION" in sql
    assert sql.count("%s") == 3
    assert parameters == ("APP_DB", "PUBLIC", "ORDERS")
    assert "ORDERS" not in sql
    cursor.close.assert_called_once()
    assert cm.last_schema_query_id == "metadata-query-id"
    assert cm._autolog_query.call_args.kwargs["parameters"] == list(parameters)


@pytest.mark.parametrize("reference", [
    "ORDERS; DROP TABLE X", "SELECT * FROM ORDERS", "ORDERS -- hi", "", "A.B.C.D",
])
def test_sql_text_rejected_before_connect(reference):
    cm, cursor = manager()
    cm._connection = None
    cm.connect = Mock()
    with pytest.raises(ValueError):
        cm.get_table_schema(reference)
    cm.connect.assert_not_called()
    cursor.execute.assert_not_called()


@pytest.mark.parametrize("reference", ["OTHER.PUBLIC.ORDERS", "APP_DB.SECRET.ORDERS"])
def test_other_namespaces_rejected(reference):
    cm, cursor = manager()
    with pytest.raises(ValueError, match="disallowed_source"):
        cm.get_table_schema(reference)
    cursor.execute.assert_not_called()


def test_exact_source_allowlist_overrides_namespace():
    cm, cursor = manager({"type": "snowflake", "connection": {"database": "APP_DB", "schema": "PUBLIC"},
                          "allowed_sources": ["APP_DB.PUBLIC.ORDERS"]})
    cm.get_table_schema("ORDERS")
    cursor.execute.reset_mock()
    with pytest.raises(ValueError, match="disallowed_source"):
        cm.get_table_schema("CUSTOMERS")
    cursor.execute.assert_not_called()
    cm._config["allowed_sources"] = []
    with pytest.raises(ValueError, match="disallowed_source"):
        cm.get_table_schema("ORDERS")


def test_quoted_identifier_case_and_punctuation_preserved():
    cm, cursor = manager({"type": "snowflake", "connection": {"database": '"App.Db"', "schema": '"Sales"'}})
    cm.get_table_schema('"Buyer\'s.orders"')
    sql, parameters = cursor.execute.call_args.args
    assert 'FROM "App.Db".INFORMATION_SCHEMA.COLUMNS' in sql
    assert parameters == ("App.Db", "Sales", "Buyer's.orders")
    assert "Buyer's" not in sql


def test_lazy_connect_and_session_namespace():
    cm, cursor = manager({"type": "snowflake"})
    connection = cm._connection
    cm._connection = None
    def connect():
        cm._connection = connection
        cm._connection_identity = {"database": "App.Db", "schema": "Sales"}
    cm.connect = Mock(side_effect=connect)
    cm.get_table_schema('"Orders"')
    cm.connect.assert_called_once()
    assert cursor.execute.call_args.args[1] == ("App.Db", "Sales", "Orders")


def test_missing_namespace_cannot_authorize_fully_qualified_table():
    cm, cursor = manager({"type": "snowflake"})
    with pytest.raises(ValueError, match="disallowed_source"):
        cm.get_table_schema("APP_DB.PUBLIC.ORDERS")
    cursor.execute.assert_not_called()


def test_absent_table_returns_empty_schema():
    cm, cursor = manager()
    cursor.fetchall.return_value = []
    assert cm.get_table_schema("ABSENT") == []
    cursor.close.assert_called_once()


@pytest.mark.parametrize("failure", ["execute", "fetchall"])
def test_metadata_errors_propagate_and_close_cursor(failure):
    cm, cursor = manager()
    getattr(cursor, failure).side_effect = RuntimeError("warehouse unavailable")
    with pytest.raises(RuntimeError, match="warehouse unavailable"):
        cm.get_table_schema("ORDERS")
    cursor.close.assert_called_once()
    cm._autolog_query.assert_not_called()


def test_metadata_api_does_not_relax_analytical_sql_policy():
    cm, cursor = manager()
    with pytest.raises(ValueError, match="disallowed_source"):
        cm.query("SELECT * FROM APP_DB.INFORMATION_SCHEMA.COLUMNS")
    cursor.execute.assert_not_called()
