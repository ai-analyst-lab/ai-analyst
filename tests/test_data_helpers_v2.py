"""Tests for helpers/data/data_helpers.py — V2 (no NovaMart dependencies)."""

import tempfile
from pathlib import Path

import pandas as pd
import pytest

from helpers.data.data_helpers import (
    list_tables,
    read_table,
    get_data_source_info,
    schema_to_markdown,
)


class TestListTables:
    def test_lists_csv_files(self, tmp_path):
        (tmp_path / "orders.csv").write_text("id\n1")
        (tmp_path / "users.csv").write_text("id\n1")
        (tmp_path / "readme.txt").write_text("not a table")
        result = list_tables(str(tmp_path))
        assert result == ["orders", "users"]

    def test_empty_directory(self, tmp_path):
        assert list_tables(str(tmp_path)) == []

    def test_nonexistent_directory(self):
        assert list_tables("/nonexistent/path") == []

    def test_sorted_alphabetically(self, tmp_path):
        (tmp_path / "zeta.csv").write_text("id\n1")
        (tmp_path / "alpha.csv").write_text("id\n1")
        assert list_tables(str(tmp_path)) == ["alpha", "zeta"]


class TestReadTable:
    def test_reads_csv(self, tmp_path):
        (tmp_path / "orders.csv").write_text("id,amount\n1,10.5\n2,20.0")
        df = read_table("orders", data_dir=str(tmp_path))
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert list(df.columns) == ["id", "amount"]

    def test_file_not_found_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="not found"):
            read_table("nonexistent", data_dir=str(tmp_path))

    def test_error_lists_available(self, tmp_path):
        (tmp_path / "orders.csv").write_text("id\n1")
        with pytest.raises(FileNotFoundError, match="orders"):
            read_table("users", data_dir=str(tmp_path))


class TestGetDataSourceInfo:
    def test_csv_available(self, tmp_path):
        (tmp_path / "orders.csv").write_text("id\n1")
        info = get_data_source_info(data_dir=str(tmp_path))
        assert info["csv_available"] is True
        assert "orders" in info["tables"]

    def test_no_csv(self, tmp_path):
        info = get_data_source_info(data_dir=str(tmp_path))
        assert info["csv_available"] is False
        assert info["tables"] == []

    def test_no_duckdb(self, tmp_path):
        info = get_data_source_info(duckdb_path=str(tmp_path / "missing.duckdb"))
        assert info["duckdb_available"] is False


class TestSchemaToMarkdown:
    def test_basic_schema(self):
        schema = {
            "dataset": "test_data",
            "tables": [
                {
                    "name": "orders",
                    "description": "Customer orders",
                    "row_count": 1000,
                    "columns": [
                        {"name": "order_id", "type": "INTEGER", "nullable": False,
                         "description": "Primary key"},
                        {"name": "amount", "type": "FLOAT", "nullable": True,
                         "description": "Order total"},
                    ],
                }
            ],
        }
        md = schema_to_markdown(schema)
        assert "# Schema: test_data" in md
        assert "## orders" in md
        assert "`order_id`" in md
        assert "1,000" in md

    def test_empty_schema(self):
        md = schema_to_markdown({"dataset": "empty", "tables": []})
        assert "# Schema: empty" in md

    def test_no_novamart_references(self):
        schema = {"dataset": "test", "tables": []}
        md = schema_to_markdown(schema)
        assert "novamart" not in md.lower()
