"""Archaeology helpers -- capture proven SQL patterns, table cheatsheets, and join patterns.

Write side of query archaeology. Auto-captures artifacts from successful
analyses into .knowledge/query-archaeology/curated/.
"""
from __future__ import annotations

import datetime
import re
from pathlib import Path

from helpers.pipeline.file_helpers import (
    atomic_write_yaml, ensure_directory, list_yaml_files, safe_read_yaml,
)

# -- Internal helpers -------------------------------------------------------

def _next_id(prefix: str, directory: Path) -> str:
    """Return next sequential ID like CK-001 or JP-002."""
    max_num = 0
    pat = re.compile(rf"^{re.escape(prefix)}-(\d+)$")
    for f in list_yaml_files(directory):
        data = safe_read_yaml(f)
        if data and "id" in data:
            m = pat.match(data["id"])
            if m:
                max_num = max(max_num, int(m.group(1)))
    return f"{prefix}-{max_num + 1:03d}"


def _today() -> str:
    return datetime.date.today().isoformat()


def _update_index(arch_dir: str | Path) -> None:
    """Recount all curated entries and update curated/index.yaml."""
    curated = Path(arch_dir) / "curated"
    ensure_directory(curated)
    index_path = curated / "index.yaml"
    index = safe_read_yaml(index_path) or {}
    index.update({
        "schema_version": index.get("schema_version", 1),
        "cookbook_entries": len(list_yaml_files(curated / "cookbook")),
        "table_cheatsheets": len(list_yaml_files(curated / "tables")),
        "join_patterns": len(list_yaml_files(curated / "joins")),
        "last_updated": _today(),
    })
    atomic_write_yaml(index_path, index)

# -- Public API: capture ----------------------------------------------------

def capture_cookbook_entry(
    title: str,
    sql: str,
    dataset: str,
    tables: list[str],
    tags: list[str] | None = None,
    source_analysis: str | None = None,
    arch_dir: str | Path = ".knowledge/query-archaeology",
) -> str:
    """Create a new cookbook entry and return its ID (e.g. CK-001)."""
    cookbook_dir = ensure_directory(Path(arch_dir) / "curated" / "cookbook")
    entry_id = _next_id("CK", cookbook_dir)
    entry = {
        "id": entry_id,
        "title": title,
        "description": f"Reusable pattern: {title}",
        "sql": sql,
        "dataset": dataset,
        "tables": tables or [],
        "tags": tags or [],
        "source_analysis": source_analysis,
        "created_at": _today(),
        "last_used": _today(),
        "use_count": 0,
    }
    atomic_write_yaml(cookbook_dir / f"{entry_id}.yaml", entry)
    _update_index(arch_dir)
    return entry_id


def capture_table_cheatsheet(
    table_name: str,
    dataset: str,
    grain: str,
    primary_key: list[str],
    common_filters: list[str] | None = None,
    gotchas: list[str] | None = None,
    common_joins: list[dict] | None = None,
    arch_dir: str | Path = ".knowledge/query-archaeology",
) -> str:
    """Create or overwrite a table cheatsheet and return the table name."""
    tables_dir = ensure_directory(Path(arch_dir) / "curated" / "tables")
    cheatsheet = {
        "table_name": table_name,
        "dataset": dataset,
        "grain": grain,
        "primary_key": primary_key or [],
        "common_filters": common_filters or [],
        "gotchas": gotchas or [],
        "common_joins": common_joins or [],
        "updated_at": _today(),
    }
    atomic_write_yaml(tables_dir / f"{table_name}.yaml", cheatsheet)
    _update_index(arch_dir)
    return table_name


def capture_join_pattern(
    tables: list[str],
    join_sql: str,
    cardinality: str,
    validated: bool = False,
    dataset: str | None = None,
    notes: str | None = None,
    arch_dir: str | Path = ".knowledge/query-archaeology",
) -> str:
    """Create a new join pattern and return its ID (e.g. JP-001)."""
    joins_dir = ensure_directory(Path(arch_dir) / "curated" / "joins")
    pattern_id = _next_id("JP", joins_dir)
    pattern = {
        "id": pattern_id,
        "tables": tables,
        "join_sql": join_sql,
        "cardinality": cardinality,
        "notes": notes,
        "validated": validated,
        "dataset": dataset,
        "created_at": _today(),
    }
    atomic_write_yaml(joins_dir / f"{pattern_id}.yaml", pattern)
    _update_index(arch_dir)
    return pattern_id

# -- Public API: search / lookup --------------------------------------------

def search_cookbook(
    query: str,
    arch_dir: str | Path = ".knowledge/query-archaeology",
) -> list[dict]:
    """Search cookbook entries by title, tags, or tables (case-insensitive)."""
    cookbook_dir = Path(arch_dir) / "curated" / "cookbook"
    results: list[dict] = []
    q = query.lower()
    for f in list_yaml_files(cookbook_dir):
        entry = safe_read_yaml(f)
        if not entry:
            continue
        searchable = " ".join([
            entry.get("title", ""),
            " ".join(entry.get("tags", [])),
            " ".join(entry.get("tables", [])),
        ]).lower()
        if q in searchable:
            results.append(entry)
    results.sort(key=lambda e: e.get("use_count", 0), reverse=True)
    return results


def search_table_cheatsheet(
    table_name: str,
    arch_dir: str | Path = ".knowledge/query-archaeology",
) -> dict | None:
    """Look up a specific table's cheatsheet. Returns None if not found."""
    path = Path(arch_dir) / "curated" / "tables" / f"{table_name}.yaml"
    return safe_read_yaml(path)


def increment_use_count(
    entry_id: str,
    arch_dir: str | Path = ".knowledge/query-archaeology",
) -> None:
    """Increment use_count and update last_used on a cookbook entry."""
    path = Path(arch_dir) / "curated" / "cookbook" / f"{entry_id}.yaml"
    entry = safe_read_yaml(path)
    if not entry:
        return
    entry["use_count"] = entry.get("use_count", 0) + 1
    entry["last_used"] = _today()
    atomic_write_yaml(path, entry)
