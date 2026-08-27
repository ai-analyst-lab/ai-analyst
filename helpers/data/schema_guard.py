"""Schema-diff guard: stop the analyst from running SQL against a table that changed shape.

Context goes stale two ways. Freshness catches the slow way (a definition nobody re-checked).
This catches the fast way: someone renames or drops a column in the warehouse, and every definition
that points at the old name is wrong instantly and silently.

The guard records a fingerprint of each table's column shape (a checksum of column name + type) at
verify time, stored in a sidecar schema_snapshots.yaml in the context repo. Before the analyst trusts
the context, it re-reads the live schema and compares. If a column got renamed or dropped, the
fingerprint will not match, and the affected definition is quarantined: marked in memory so the agent
will not use it, never deleted, until a human re-verifies it. It fails loud instead of handing back a
confident wrong number.

schema_checksum uses the same DESCRIBE TABLE hash convention as the external eval harness (optional),
the gold cases bind to, so the checksum convention is consistent across the eval harness and the
context guard. The connection is always supplied by the caller and works against either a DuckDB
connection (conn.execute) or a standard DBAPI connection such as Snowflake (conn.cursor().execute).
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

SNAPSHOT_FILENAME = "schema_snapshots.yaml"

# Quarantine is a mark, never a delete. A quarantined definition stays on disk and stays
# in the file; the guard only stamps it so the agent will not use it until re-verified.
STATUS_QUARANTINED = "quarantined"


def _exec(conn: Any, sql: str):
    """Run SQL portably across a DuckDB connection (conn.execute) and a standard DBAPI
    connection such as Snowflake (conn.cursor().execute). Returns a cursor-like object."""
    execute = getattr(conn, "execute", None)
    if callable(execute):
        return execute(sql)               # DuckDB-style direct execute
    cur = conn.cursor()                    # standard DBAPI (Snowflake, Postgres, ...)
    cur.execute(sql)
    return cur


def schema_checksum(conn: Any, tables) -> str:
    """A stable checksum of the named tables' column shape (name + type), so a schema change
    invalidates a bound definition instead of silently changing the answer. Order-independent
    per table; deterministic across runs.

    Same convention as the external eval harness (optional) so the checksum the context guard
    compares against is the same fingerprint the gold cases use.
    """
    parts = []
    for t in sorted(tables):
        try:
            rows = _exec(conn, f"DESCRIBE TABLE {t}").fetchall()
        except Exception:
            # An absent table is itself part of the shape: record it as missing, do not crash.
            parts.append(f"{t}:MISSING")
            continue
        cols = sorted(f"{r[0]}:{r[1]}" for r in rows)   # (column_name, column_type)
        parts.append(f"{t}(" + ",".join(cols) + ")")
    blob = "|".join(parts).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()[:16]


def check_schema(conn: Any, table: str, stored_checksum: str) -> Tuple[bool, str]:
    """Recompute the live checksum for one table and compare to the stored known-good.

    Args:
        conn: a DuckDB or DBAPI connection.
        table: the table to fingerprint.
        stored_checksum: the known-good checksum snapshotted at verify time.

    Returns:
        (ok, current_checksum). ok is True when the live shape still matches the stored one.
    """
    current = schema_checksum(conn, [table])
    return current == stored_checksum, current


# ---------------------------------------------------------------------------
# Loading the table-backed definitions and the snapshot sidecar
# ---------------------------------------------------------------------------

def load_table_definitions(context_dir: Union[str, Path]) -> List[Dict[str, str]]:
    """Return the table-backed definitions: [{name, table}] from semantic/entities.yaml.

    Each entity names the warehouse table it is the source of truth for (base_table, or
    logical_table when base_table is absent). Those are the tables whose shape the guard checks.
    """
    import yaml

    context_dir = Path(context_dir)
    defs: List[Dict[str, str]] = []
    entities_path = context_dir / "semantic" / "entities.yaml"
    if entities_path.exists():
        data = yaml.safe_load(entities_path.read_text()) or {}
        for e in data.get("entities", []):
            table = e.get("base_table") or e.get("logical_table")
            if table:
                defs.append({"name": e.get("entity"), "table": table})
    return defs


def _snapshot_path(context_dir: Union[str, Path]) -> Path:
    return Path(context_dir) / SNAPSHOT_FILENAME


def load_snapshots(context_dir: Union[str, Path]) -> Dict[str, str]:
    """Load the per-table known-good checksums from the sidecar (table -> checksum)."""
    import yaml

    path = _snapshot_path(context_dir)
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text()) or {}
    return data.get("tables", {}) or {}


def write_snapshots(context_dir: Union[str, Path], snapshots: Dict[str, str]) -> Path:
    """Write the per-table checksums to the sidecar. Machine-written, not human-edited."""
    import yaml

    path = _snapshot_path(context_dir)
    path.write_text(
        "# Schema snapshots: known-good column-shape checksums per table.\n"
        "# Machine-written at verify time (schema_guard.snapshot_schema), keyed by table.\n"
        "# The schema-diff guard compares the live schema to these and quarantines on drift.\n"
        + yaml.safe_dump({"tables": dict(sorted(snapshots.items()))}, sort_keys=False)
    )
    return path


def snapshot_schema(conn: Any, context_dir: Union[str, Path]) -> Dict[str, str]:
    """Record the current schema checksum for each table-backed definition (the known-good).

    Run this at verify time to bind the snapshot the guard later compares against. Returns the
    full table -> checksum map and writes it to the sidecar.
    """
    snapshots = load_snapshots(context_dir)
    for d in load_table_definitions(context_dir):
        snapshots[d["table"]] = schema_checksum(conn, [d["table"]])
    write_snapshots(context_dir, snapshots)
    return snapshots


def guard_context(conn: Any, context_dir: Union[str, Path]) -> List[Dict[str, Any]]:
    """Check every table-backed definition's live schema against its known-good snapshot.

    For each definition with a stored checksum, recompute the live checksum and compare. On a
    mismatch, the definition is quarantined: returned with a status="quarantined" stamp (in memory,
    not deleted, the file is untouched) so the agent will not use it until a human re-verifies.

    A definition with no stored snapshot is skipped (there is nothing known-good to compare against),
    not quarantined.

    Args:
        conn: a DuckDB or DBAPI connection to the live warehouse.
        context_dir: the dataset context dir (holds semantic/entities.yaml and the snapshot sidecar).

    Returns:
        list of quarantined definition dicts: {name, table, stored_checksum, current_checksum, status}.
    """
    snapshots = load_snapshots(context_dir)
    quarantined: List[Dict[str, Any]] = []
    for d in load_table_definitions(context_dir):
        stored = snapshots.get(d["table"])
        if stored is None:
            continue
        ok, current = check_schema(conn, d["table"], stored)
        if not ok:
            quarantined.append(
                {
                    "name": d["name"],
                    "table": d["table"],
                    "stored_checksum": stored,
                    "current_checksum": current,
                    "status": STATUS_QUARANTINED,
                }
            )
    return quarantined
