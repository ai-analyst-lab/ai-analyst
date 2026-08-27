"""ConnectionManager over a folder of CSV files: DuckDB views + SQL + auto-logging.

CSV folders are the most common way people start. They must behave like any other backend:
`query()` runs real SQL against views named after the file stems, returns a DataFrame, and goes
through the same provenance auto-log path as DuckDB/Snowflake.
"""
from datetime import date

import pandas as pd
import pytest

from helpers.data.connection_manager import ConnectionManager
from helpers.provenance import query_log


def _mk_csvs(tmp_path):
    folder = tmp_path / "data"
    folder.mkdir()
    pd.DataFrame({"order_id": [1, 2, 3], "total": [10.0, 20.0, 12.5]}).to_csv(
        folder / "orders.csv", index=False
    )
    pd.DataFrame({"user_id": [1, 2], "country": ["US", "UK"]}).to_csv(
        folder / "users.csv", index=False
    )
    return folder


def test_views_registered_from_folder(tmp_path):
    folder = _mk_csvs(tmp_path)
    with ConnectionManager(config={"type": "csv", "csv_path": str(folder)}) as cm:
        assert cm.connection_type == "csv"
        assert cm.list_tables() == ["orders", "users"]
        assert cm.test_connection()["ok"] is True
        # dtype inference via read_csv_auto: total is numeric, not text
        schema = {c["name"]: c["type"] for c in cm.get_table_schema("orders")}
        assert set(schema) == {"order_id", "total"}
        assert "DOUBLE" in schema["total"].upper()


def test_query_returns_rows(tmp_path):
    folder = _mk_csvs(tmp_path)
    cm = ConnectionManager(config={"type": "csv", "csv_path": str(folder)})
    # No explicit connect(): query() lazy-connects like the other backends.
    df = cm.query("SELECT order_id, total FROM orders WHERE total > 11 ORDER BY order_id", log=False)
    assert isinstance(df, pd.DataFrame)
    assert df["order_id"].tolist() == [2, 3]
    joined = cm.query(
        "SELECT count(*) AS n FROM orders o JOIN users u ON o.order_id = u.user_id", log=False
    )
    assert int(joined.iloc[0, 0]) == 2
    # read_table still works and matches the view
    assert len(cm.read_table("orders")) == 3
    cm.close()


def test_connect_is_idempotent(tmp_path):
    folder = _mk_csvs(tmp_path)
    cm = ConnectionManager(config={"type": "csv", "csv_path": str(folder)})
    cm.connect()
    cm.connect()  # CREATE OR REPLACE VIEW: no "already exists" error
    assert cm.list_tables() == ["orders", "users"]
    assert int(cm.query("SELECT count(*) FROM orders", log=False).iloc[0, 0]) == 3
    cm.close()


def test_table_names_from_manifest_files_list(tmp_path):
    folder = _mk_csvs(tmp_path)
    # A stray CSV in the same folder must NOT become a table when files: is declared.
    pd.DataFrame({"x": [1]}).to_csv(folder / "scratch.csv", index=False)
    cm = ConnectionManager(
        config={"type": "csv", "csv_path": str(folder), "files": ["orders.csv", str(folder / "users.csv")]}
    )
    cm.connect()
    assert cm.list_tables() == ["orders", "users"]
    with pytest.raises(Exception):
        cm.query("SELECT * FROM scratch", log=False)
    cm.close()


def test_missing_file_error_lists_found_files(tmp_path):
    folder = _mk_csvs(tmp_path)
    cm = ConnectionManager(
        config={"type": "csv", "csv_path": str(folder), "files": ["orders.csv", "payments.csv"]}
    )
    with pytest.raises(ConnectionError) as exc:
        cm.connect()
    msg = str(exc.value)
    assert "payments.csv" in msg
    assert "orders.csv" in msg and "users.csv" in msg  # what it did find
    assert cm.test_connection()["ok"] is False


def test_query_autologs_through_existing_hook(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "working").mkdir(exist_ok=True)
    monkeypatch.setattr(query_log, "_EXPLICIT_LOG_DIR", tmp_path)
    monkeypatch.setattr(query_log, "_AUTOLOG_ENABLED", True)

    folder = _mk_csvs(tmp_path)
    cm = ConnectionManager(config={"type": "csv", "csv_path": str(folder), "dataset_id": "csvds"})
    df = cm.query("select sum(total) as s from orders")
    assert float(df.iloc[0, 0]) == 42.5

    entries = query_log.read_log("csvds", date.today().isoformat())
    assert len(entries) == 1
    e = entries[0]
    assert "sum(total)" in e["sql"].lower()        # the exact SQL that ran
    assert float(e["result_value"]) == 42.5        # scalar 1x1 result captured
    assert e.get("analysis_id")
    assert "orders" in (e.get("tables_accessed") or [])
    assert e["connection_type"] == "csv"
    assert e["dialect"] == "duckdb"

    cm.query("select sum(total) as s from orders", log=False)
    assert len(query_log.read_log("csvds", date.today().isoformat())) == 1
