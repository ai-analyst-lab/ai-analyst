from __future__ import annotations

import pytest

from helpers.knowledge.archaeology_helpers import (
    capture_cookbook_entry,
    capture_join_pattern,
    capture_table_cheatsheet,
    increment_use_count,
    search_cookbook,
    search_table_cheatsheet,
)
from helpers.pipeline.file_helpers import atomic_write_yaml, safe_read_yaml


@pytest.fixture()
def arch_dir(tmp_path):
    """Create the query-archaeology directory tree and empty index."""
    base = tmp_path / "query-archaeology"
    (base / "curated" / "cookbook").mkdir(parents=True)
    (base / "curated" / "tables").mkdir(parents=True)
    (base / "curated" / "joins").mkdir(parents=True)
    atomic_write_yaml(base / "curated" / "index.yaml", {"schema_version": 1})
    return base


# -- TestCaptureCookbookEntry -------------------------------------------------

class TestCaptureCookbookEntry:

    def test_creates_yaml_file_with_correct_fields(self, arch_dir):
        entry_id = capture_cookbook_entry(
            title="Daily active users",
            sql="SELECT COUNT(DISTINCT user_id) FROM events",
            dataset="hero",
            tables=["events"],
            tags=["engagement"],
            arch_dir=arch_dir,
        )
        assert entry_id == "CK-001"
        data = safe_read_yaml(arch_dir / "curated" / "cookbook" / "CK-001.yaml")
        assert data["title"] == "Daily active users"
        assert data["sql"] == "SELECT COUNT(DISTINCT user_id) FROM events"
        assert data["dataset"] == "hero"
        assert data["tables"] == ["events"]
        assert data["tags"] == ["engagement"]
        assert data["use_count"] == 0

    def test_sequential_ids(self, arch_dir):
        first = capture_cookbook_entry(
            title="First", sql="SELECT 1", dataset="d", tables=[], arch_dir=arch_dir,
        )
        second = capture_cookbook_entry(
            title="Second", sql="SELECT 2", dataset="d", tables=[], arch_dir=arch_dir,
        )
        assert first == "CK-001"
        assert second == "CK-002"

    def test_index_updated_with_count(self, arch_dir):
        capture_cookbook_entry(
            title="Entry", sql="SELECT 1", dataset="d", tables=[], arch_dir=arch_dir,
        )
        capture_cookbook_entry(
            title="Entry 2", sql="SELECT 2", dataset="d", tables=[], arch_dir=arch_dir,
        )
        index = safe_read_yaml(arch_dir / "curated" / "index.yaml")
        assert index["cookbook_entries"] == 2

    def test_defaults_for_optional_fields(self, arch_dir):
        capture_cookbook_entry(
            title="Bare", sql="SELECT 1", dataset="d", tables=[], arch_dir=arch_dir,
        )
        data = safe_read_yaml(arch_dir / "curated" / "cookbook" / "CK-001.yaml")
        assert data["tags"] == []
        assert data["source_analysis"] is None


# -- TestCaptureTableCheatsheet -----------------------------------------------

class TestCaptureTableCheatsheet:

    def test_creates_file_named_after_table(self, arch_dir):
        result = capture_table_cheatsheet(
            table_name="orders",
            dataset="hero",
            grain="one row per order",
            primary_key=["order_id"],
            arch_dir=arch_dir,
        )
        assert result == "orders"
        path = arch_dir / "curated" / "tables" / "orders.yaml"
        assert path.exists()

    def test_all_fields_present(self, arch_dir):
        capture_table_cheatsheet(
            table_name="orders",
            dataset="hero",
            grain="one row per order",
            primary_key=["order_id"],
            gotchas=["nulls in status"],
            common_joins=[{"table": "users", "on": "user_id"}],
            arch_dir=arch_dir,
        )
        data = safe_read_yaml(arch_dir / "curated" / "tables" / "orders.yaml")
        assert data["grain"] == "one row per order"
        assert data["primary_key"] == ["order_id"]
        assert data["gotchas"] == ["nulls in status"]
        assert data["common_joins"] == [{"table": "users", "on": "user_id"}]

    def test_overwrite_same_table(self, arch_dir):
        capture_table_cheatsheet(
            table_name="orders", dataset="hero", grain="old grain",
            primary_key=["order_id"], arch_dir=arch_dir,
        )
        capture_table_cheatsheet(
            table_name="orders", dataset="hero", grain="new grain",
            primary_key=["order_id"], arch_dir=arch_dir,
        )
        data = safe_read_yaml(arch_dir / "curated" / "tables" / "orders.yaml")
        assert data["grain"] == "new grain"
        # Index should still show 1 cheatsheet, not 2
        index = safe_read_yaml(arch_dir / "curated" / "index.yaml")
        assert index["table_cheatsheets"] == 1


# -- TestCaptureJoinPattern ---------------------------------------------------

class TestCaptureJoinPattern:

    def test_creates_yaml_with_jp_id(self, arch_dir):
        jp_id = capture_join_pattern(
            tables=["orders", "users"],
            join_sql="orders.user_id = users.id",
            cardinality="many-to-one",
            arch_dir=arch_dir,
        )
        assert jp_id == "JP-001"
        path = arch_dir / "curated" / "joins" / "JP-001.yaml"
        assert path.exists()

    def test_cardinality_and_tables_fields(self, arch_dir):
        capture_join_pattern(
            tables=["events", "sessions"],
            join_sql="events.session_id = sessions.id",
            cardinality="many-to-one",
            validated=True,
            arch_dir=arch_dir,
        )
        data = safe_read_yaml(arch_dir / "curated" / "joins" / "JP-001.yaml")
        assert data["cardinality"] == "many-to-one"
        assert data["tables"] == ["events", "sessions"]
        assert data["validated"] is True


# -- TestSearchFunctions ------------------------------------------------------

class TestSearchFunctions:

    def test_search_cookbook_empty_returns_empty(self, arch_dir):
        results = search_cookbook("anything", arch_dir=arch_dir)
        assert results == []

    def test_search_by_table_name(self, arch_dir):
        capture_cookbook_entry(
            title="User counts", sql="SELECT COUNT(*) FROM users",
            dataset="hero", tables=["users"], arch_dir=arch_dir,
        )
        capture_cookbook_entry(
            title="Order totals", sql="SELECT SUM(total) FROM orders",
            dataset="hero", tables=["orders"], arch_dir=arch_dir,
        )
        results = search_cookbook("users", arch_dir=arch_dir)
        assert len(results) == 1
        assert results[0]["id"] == "CK-001"

    def test_search_sorted_by_use_count(self, arch_dir):
        capture_cookbook_entry(
            title="Low usage query", sql="SELECT 1", dataset="d",
            tables=["t"], arch_dir=arch_dir,
        )
        capture_cookbook_entry(
            title="High usage query", sql="SELECT 2", dataset="d",
            tables=["t"], arch_dir=arch_dir,
        )
        # Bump the second entry's use count
        increment_use_count("CK-002", arch_dir=arch_dir)
        increment_use_count("CK-002", arch_dir=arch_dir)
        results = search_cookbook("query", arch_dir=arch_dir)
        assert len(results) == 2
        assert results[0]["id"] == "CK-002"
        assert results[0]["use_count"] == 2

    def test_search_table_cheatsheet_missing(self, arch_dir):
        result = search_table_cheatsheet("nonexistent", arch_dir=arch_dir)
        assert result is None


# -- TestIncrementUseCount ----------------------------------------------------

class TestIncrementUseCount:

    def test_increments_from_zero_to_one(self, arch_dir):
        capture_cookbook_entry(
            title="Entry", sql="SELECT 1", dataset="d", tables=[],
            arch_dir=arch_dir,
        )
        increment_use_count("CK-001", arch_dir=arch_dir)
        data = safe_read_yaml(arch_dir / "curated" / "cookbook" / "CK-001.yaml")
        assert data["use_count"] == 1

    def test_nonexistent_entry_no_error(self, arch_dir):
        # Should silently return without raising
        increment_use_count("CK-999", arch_dir=arch_dir)
