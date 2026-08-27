"""Tests for helpers/pipeline/schema_migration.py."""
from __future__ import annotations

import json
import os

import pytest

from helpers.pipeline.schema_migration import (
    CURRENT_VERSIONS,
    SUPPORTED_TYPES,
    clear_registry,
    get_schema_version,
    list_migrations,
    migrate_if_needed,
    needs_migration,
    register_migration,
)


@pytest.fixture(autouse=True)
def clean_registry():
    """Clear migration registry before and after each test."""
    clear_registry()
    yield
    clear_registry()


class TestSupportedTypes:
    def test_has_expected_types(self):
        expected = {
            "setup_state", "entity_index", "manifest", "org_manifest",
            "corrections_log", "corrections_index", "notion_page",
            "pipeline_state",
        }
        assert expected == SUPPORTED_TYPES

    def test_frozen(self):
        assert isinstance(SUPPORTED_TYPES, frozenset)


class TestGetSchemaVersion:
    def test_explicit_version(self):
        assert get_schema_version({"schema_version": 3}) == 3

    def test_missing_defaults_to_one(self):
        assert get_schema_version({}) == 1

    def test_version_one(self):
        assert get_schema_version({"schema_version": 1}) == 1


class TestNeedsMigration:
    def test_no_migration_needed(self):
        data = {"schema_version": 1}
        assert needs_migration(data, "setup_state") is False

    def test_migration_needed(self):
        data = {"schema_version": 1}
        assert needs_migration(data, "pipeline_state") is True

    def test_unknown_type(self):
        assert needs_migration({}, "nonexistent") is False


class TestMigrateIfNeeded:
    def test_noop_when_current(self):
        data = {"schema_version": 1, "key": "value"}
        result = migrate_if_needed(data, "setup_state")
        assert result["key"] == "value"

    def test_bumps_version_when_no_migration_registered(self):
        """In V2, no migrations are registered. Version should be bumped."""
        data = {"schema_version": 1, "key": "value"}
        result = migrate_if_needed(data, "pipeline_state")
        assert result["schema_version"] == 2
        assert result["key"] == "value"

    def test_invalid_schema_type(self):
        with pytest.raises(ValueError, match="Unknown schema type"):
            migrate_if_needed({}, "invalid_type")

    def test_runs_registered_migration(self):
        def migrate_v1_to_v2(data):
            data["migrated"] = True
            return data

        register_migration("setup_state", 1, 2, migrate_v1_to_v2)
        # Temporarily set current version to 2
        old = CURRENT_VERSIONS["setup_state"]
        CURRENT_VERSIONS["setup_state"] = 2
        try:
            data = {"schema_version": 1}
            result = migrate_if_needed(data, "setup_state")
            assert result["migrated"] is True
            assert result["schema_version"] == 2
        finally:
            CURRENT_VERSIONS["setup_state"] = old

    def test_does_not_mutate_original(self):
        data = {"schema_version": 1, "items": [1, 2, 3]}
        result = migrate_if_needed(data, "pipeline_state")
        assert data["schema_version"] == 1  # Original unchanged

    def test_creates_backup(self, tmp_path):
        backup = str(tmp_path / "backup.json")
        data = {"schema_version": 1, "key": "value"}
        migrate_if_needed(data, "pipeline_state", backup_path=backup)
        assert os.path.exists(backup)
        with open(backup) as f:
            saved = json.load(f)
        assert saved["schema_version"] == 1


class TestRegisterMigration:
    def test_register_valid(self):
        register_migration("setup_state", 1, 2, lambda d: d)
        assert len(list_migrations()) == 1

    def test_invalid_type(self):
        with pytest.raises(ValueError, match="Unknown schema type"):
            register_migration("bogus", 1, 2, lambda d: d)

    def test_non_sequential(self):
        with pytest.raises(ValueError, match="sequential"):
            register_migration("setup_state", 1, 3, lambda d: d)


class TestListMigrations:
    def test_empty(self):
        assert list_migrations() == []

    def test_filtered(self):
        register_migration("setup_state", 1, 2, lambda d: d)
        register_migration("manifest", 1, 2, lambda d: d)
        result = list_migrations("setup_state")
        assert len(result) == 1
        assert result[0][0] == "setup_state"
