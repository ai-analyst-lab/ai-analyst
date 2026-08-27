"""Tests for helpers/data/schema_guard.py.

Uses an in-memory DuckDB fixture so the guard is exercised end-to-end with no Snowflake.
"""
from __future__ import annotations

import duckdb
import yaml
import pytest

from helpers.data.schema_guard import (
    STATUS_QUARANTINED,
    check_schema,
    guard_context,
    load_snapshots,
    schema_checksum,
    snapshot_schema,
)


@pytest.fixture
def conn():
    c = duckdb.connect(":memory:")
    c.execute("CREATE TABLE orders (order_id INTEGER, status VARCHAR, total_amount DOUBLE)")
    c.execute("CREATE TABLE memberships (membership_id INTEGER, is_current BOOLEAN)")
    yield c
    c.close()


@pytest.fixture
def context_dir(tmp_path):
    """A minimal context dir with entities pointing at the fixture tables."""
    (tmp_path / "semantic").mkdir(parents=True, exist_ok=True)
    (tmp_path / "semantic" / "entities.yaml").write_text(
        yaml.safe_dump(
            {
                "entities": [
                    {"entity": "order", "base_table": "orders", "primary_key": "order_id"},
                    {"entity": "membership", "base_table": "memberships", "primary_key": "membership_id"},
                ]
            }
        )
    )
    return tmp_path


# ── schema_checksum ──────────────────────────────────────────────────────

class TestSchemaChecksum:
    def test_deterministic(self, conn):
        assert schema_checksum(conn, ["orders"]) == schema_checksum(conn, ["orders"])

    def test_changes_when_column_added(self, conn):
        before = schema_checksum(conn, ["orders"])
        conn.execute("ALTER TABLE orders ADD COLUMN region VARCHAR")
        after = schema_checksum(conn, ["orders"])
        assert before != after

    def test_missing_table_does_not_crash(self, conn):
        # An absent table is recorded as part of the shape, not an exception.
        cs = schema_checksum(conn, ["no_such_table"])
        assert isinstance(cs, str) and cs


# ── check_schema ─────────────────────────────────────────────────────────

class TestCheckSchema:
    def test_matching_checksum_passes(self, conn):
        stored = schema_checksum(conn, ["orders"])
        ok, current = check_schema(conn, "orders", stored)
        assert ok is True
        assert current == stored

    def test_added_column_mismatches(self, conn):
        stored = schema_checksum(conn, ["orders"])
        conn.execute("ALTER TABLE orders ADD COLUMN region VARCHAR")
        ok, current = check_schema(conn, "orders", stored)
        assert ok is False
        assert current != stored

    def test_renamed_column_mismatches(self, conn):
        stored = schema_checksum(conn, ["orders"])
        conn.execute("ALTER TABLE orders RENAME COLUMN status TO order_status")
        ok, current = check_schema(conn, "orders", stored)
        assert ok is False


# ── snapshot_schema + guard_context ──────────────────────────────────────

class TestGuardContext:
    def test_clean_context_quarantines_nothing(self, conn, context_dir):
        snapshot_schema(conn, context_dir)
        quarantined = guard_context(conn, context_dir)
        assert quarantined == []

    def test_snapshot_is_written_keyed_by_table(self, conn, context_dir):
        snapshot_schema(conn, context_dir)
        snaps = load_snapshots(context_dir)
        assert set(snaps.keys()) == {"orders", "memberships"}

    def test_renamed_column_quarantines_that_definition(self, conn, context_dir):
        snapshot_schema(conn, context_dir)
        # Simulate a warehouse rename: status -> order_status on orders.
        conn.execute("ALTER TABLE orders RENAME COLUMN status TO order_status")
        quarantined = guard_context(conn, context_dir)
        assert len(quarantined) == 1
        q = quarantined[0]
        assert q["name"] == "order"
        assert q["table"] == "orders"
        assert q["status"] == STATUS_QUARANTINED
        assert q["current_checksum"] != q["stored_checksum"]

    def test_added_column_quarantines(self, conn, context_dir):
        snapshot_schema(conn, context_dir)
        conn.execute("ALTER TABLE memberships ADD COLUMN tier VARCHAR")
        quarantined = guard_context(conn, context_dir)
        assert [q["name"] for q in quarantined] == ["membership"]

    def test_quarantine_marks_does_not_delete(self, conn, context_dir):
        snapshot_schema(conn, context_dir)
        before = (context_dir / "semantic" / "entities.yaml").read_text()
        conn.execute("ALTER TABLE orders RENAME COLUMN status TO order_status")
        guard_context(conn, context_dir)
        after = (context_dir / "semantic" / "entities.yaml").read_text()
        # The definitions file is untouched; quarantine is an in-memory stamp only.
        assert before == after
        # The entity is still present on disk, not deleted.
        data = yaml.safe_load(after)
        names = {e["entity"] for e in data["entities"]}
        assert "order" in names

    def test_revert_clears_quarantine(self, conn, context_dir):
        snapshot_schema(conn, context_dir)
        conn.execute("ALTER TABLE orders RENAME COLUMN status TO order_status")
        assert len(guard_context(conn, context_dir)) == 1
        # Revert the rename: checksum matches again, nothing quarantined.
        conn.execute("ALTER TABLE orders RENAME COLUMN order_status TO status")
        assert guard_context(conn, context_dir) == []

    def test_no_snapshot_means_no_quarantine(self, conn, context_dir):
        # Without a known-good snapshot there is nothing to compare against; skip, do not quarantine.
        quarantined = guard_context(conn, context_dir)
        assert quarantined == []
