"""Schema migration framework for knowledge system files.

Provides a registration-based migration system for upgrading file schemas
across versions. In V2, this framework is inert — no migrations are
registered. It is ready for V2.1 when schema changes require migration.

Supported file types:
    setup_state, entity_index, manifest, org_manifest,
    corrections_log, corrections_index, notion_page, pipeline_state

Usage:
    from helpers.pipeline.schema_migration import migrate_if_needed

    # Returns data unchanged in V2 (no migrations registered)
    data = migrate_if_needed(data, "setup_state")

    # Register a migration for V2.1:
    # register_migration("setup_state", 1, 2, migrate_setup_v1_to_v2)
"""
from __future__ import annotations

import copy
import json
import os
from typing import Any, Callable, Dict, List, Optional, Tuple


# Type alias for migration functions
MigrationFn = Callable[[Dict[str, Any]], Dict[str, Any]]

# Schema types that support migration
SUPPORTED_TYPES = frozenset([
    "setup_state",
    "entity_index",
    "manifest",
    "org_manifest",
    "corrections_log",
    "corrections_index",
    "notion_page",
    "pipeline_state",
])

# Current schema versions (all at V1 for initial release)
CURRENT_VERSIONS: Dict[str, int] = {
    "setup_state": 1,
    "entity_index": 1,
    "manifest": 1,
    "org_manifest": 1,
    "corrections_log": 1,
    "corrections_index": 1,
    "notion_page": 1,
    "pipeline_state": 2,  # V2 pipeline state (post-migration)
}

# Migration registry: (schema_type, from_version, to_version) -> function
_registry: Dict[Tuple[str, int, int], MigrationFn] = {}


def register_migration(
    schema_type: str,
    from_version: int,
    to_version: int,
    fn: MigrationFn,
) -> None:
    """Register a migration function for a schema type.

    Args:
        schema_type: One of SUPPORTED_TYPES.
        from_version: Source schema version.
        to_version: Target schema version (must be from_version + 1).
        fn: Migration function that takes a dict and returns a migrated dict.

    Raises:
        ValueError: If schema_type is not supported or versions are invalid.
    """
    if schema_type not in SUPPORTED_TYPES:
        raise ValueError(
            f"Unknown schema type '{schema_type}'. "
            f"Supported: {sorted(SUPPORTED_TYPES)}"
        )
    if to_version != from_version + 1:
        raise ValueError(
            f"Migrations must be sequential: {from_version} -> {from_version + 1}, "
            f"got {from_version} -> {to_version}"
        )
    _registry[(schema_type, from_version, to_version)] = fn


def get_schema_version(data: Dict[str, Any]) -> int:
    """Extract schema version from a data dict.

    Looks for 'schema_version' key. Defaults to 1 if not present.

    Args:
        data: Data dictionary to check.

    Returns:
        Schema version integer.
    """
    return data.get("schema_version", 1)


def needs_migration(data: Dict[str, Any], schema_type: str) -> bool:
    """Check if data needs migration to reach current version.

    Args:
        data: Data dictionary to check.
        schema_type: Schema type to check against.

    Returns:
        True if data version is below current version for this type.
    """
    if schema_type not in SUPPORTED_TYPES:
        return False
    current = CURRENT_VERSIONS.get(schema_type, 1)
    data_version = get_schema_version(data)
    return data_version < current


def migrate_if_needed(
    data: Dict[str, Any],
    schema_type: str,
    backup_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Migrate data to the current schema version if needed.

    If no migration is needed (data is already at current version),
    returns the data unchanged. If migrations are registered for
    the version gap, applies them sequentially.

    Args:
        data: Data dictionary to migrate.
        schema_type: Schema type (must be in SUPPORTED_TYPES).
        backup_path: Optional path to save a backup before migration.

    Returns:
        Migrated data dictionary (or original if no migration needed).

    Raises:
        ValueError: If schema_type is not supported.
        RuntimeError: If a required migration is not registered.
    """
    if schema_type not in SUPPORTED_TYPES:
        raise ValueError(
            f"Unknown schema type '{schema_type}'. "
            f"Supported: {sorted(SUPPORTED_TYPES)}"
        )

    current_target = CURRENT_VERSIONS.get(schema_type, 1)
    data_version = get_schema_version(data)

    # Already at current version
    if data_version >= current_target:
        return data

    # Create backup if path provided
    if backup_path:
        _create_backup(data, backup_path)

    # Apply migrations sequentially
    result = copy.deepcopy(data)
    version = data_version

    while version < current_target:
        next_version = version + 1
        key = (schema_type, version, next_version)

        if key not in _registry:
            # No migration registered — this is expected in V2
            # Just bump the version and return
            result["schema_version"] = current_target
            return result

        migration_fn = _registry[key]
        result = migration_fn(result)
        result["schema_version"] = next_version
        version = next_version

    return result


def list_migrations(schema_type: Optional[str] = None) -> List[Tuple[str, int, int]]:
    """List all registered migrations.

    Args:
        schema_type: Optional filter by schema type.

    Returns:
        List of (schema_type, from_version, to_version) tuples.
    """
    if schema_type:
        return [k for k in _registry.keys() if k[0] == schema_type]
    return list(_registry.keys())


def clear_registry() -> None:
    """Clear all registered migrations. Used for testing."""
    _registry.clear()


def _create_backup(data: Dict[str, Any], path: str) -> None:
    """Save a JSON backup of data before migration."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)
