"""Query log — records every data-touching query for provenance and receipts.

Stores queries in JSONL format (one JSON object per line, append-friendly).
Each entry captures the SQL, dialect, tables accessed, result summary, and
timing metadata. The validation agent uses the log for backfill and coverage
reporting. The receipt generator uses it for the full audit trail.

Usage:
    from helpers.query_log import append_entry, read_log, to_markdown

    # Append a query (agents call this after every SQL execution)
    append_entry(
        dataset_name="my_dataset",
        date="2026-04-04",
        agent="descriptive-analytics",
        pipeline_step=5,
        purpose="Revenue by segment",
        sql="SELECT segment, SUM(revenue) FROM orders GROUP BY segment",
        dialect="snowflake",
        connection_type="snowflake",
        tables_accessed=["orders"],
        result_summary="3 rows, revenue by segment",
        row_count=3,
        execution_ms=120,
    )

    # Read the full log
    entries = read_log("my_dataset", "2026-04-04")

    # Render as markdown table
    print(to_markdown(entries))
"""

from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_WORKING_DIR = Path("working")

# If set, overrides _WORKING_DIR for all log operations.
# The pipeline sets this to the run directory's working/ subfolder.
_EXPLICIT_LOG_DIR: Path | None = None


def set_log_dir(path: str | Path) -> None:
    """Override the default log directory.

    Call this at pipeline start to direct logs into the run directory:
        set_log_dir("working/runs/2026-04-04_dataset_question/working")
    """
    global _EXPLICIT_LOG_DIR
    _EXPLICIT_LOG_DIR = Path(path)


def _log_path(dataset_name: str, date: str) -> Path:
    """Return the JSONL log file path for a given analysis run.

    Uses _EXPLICIT_LOG_DIR if set (pipeline mode), otherwise _WORKING_DIR.
    Also writes a copy to the top-level working/ dir for backward compatibility.
    """
    base_dir = _EXPLICIT_LOG_DIR or _WORKING_DIR
    return base_dir / f"query_log_{dataset_name}_{date}.jsonl"


# ---------------------------------------------------------------------------
# Write
# ---------------------------------------------------------------------------

def append_entry(
    dataset_name: str,
    date: str,
    agent: str,
    pipeline_step: float,
    purpose: str,
    sql: str,
    dialect: str = "duckdb",
    connection_type: str = "duckdb",
    tables_accessed: list[str] | None = None,
    columns_accessed: list[str] | None = None,
    result_summary: str = "",
    result_value: str | float | None = None,
    row_count: int | None = None,
    execution_ms: float = 0.0,
    claim_ids: list[str] | None = None,
    approximate_functions_used: list[str] | None = None,
    warehouse_specific_syntax: list[str] | None = None,
    status: str = "success",
    error: str | None = None,
    query_id: str | None = None,
) -> dict:
    """Append a query log entry to the JSONL file.

    Args:
        dataset_name: Active dataset name (for file naming).
        date: Analysis date as YYYY-MM-DD (for file naming).
        agent: Name of the agent that ran the query.
        pipeline_step: Pipeline step number (e.g., 5, 6.5).
        purpose: Human-readable description of why this query ran.
        sql: The SQL query text.
        dialect: SQL dialect used (duckdb, snowflake, bigquery, postgres).
        connection_type: Connection type from manifest.
        tables_accessed: List of table names touched by the query.
        columns_accessed: List of column names referenced.
        result_summary: Brief text description of the result.
        result_value: The key number(s) produced.
        row_count: Number of rows returned.
        execution_ms: Query execution time in milliseconds.
        claim_ids: Finding/claim IDs this query supports (filled later).
        approximate_functions_used: Warehouse-specific approximate functions.
        warehouse_specific_syntax: Non-standard SQL syntax used.
        status: "success" or "error".
        error: Error message if status is "error".
        query_id: Optional explicit ID. Auto-generated if not provided.

    Returns:
        The entry dict that was written.
    """
    log_path = _log_path(dataset_name, date)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # Auto-generate query_id from agent prefix + sequence
    if query_id is None:
        prefix = agent.replace("-", "_")[:8]
        ts = int(time.time() * 1000) % 100000
        query_id = f"{prefix}_{ts:05d}"

    entry = {
        "query_id": query_id,
        "timestamp": datetime.now().isoformat(),
        "agent": agent,
        "pipeline_step": pipeline_step,
        "purpose": purpose,
        "sql": sql,
        "dialect": dialect,
        "connection_type": connection_type,
        "tables_accessed": tables_accessed or [],
        "columns_accessed": columns_accessed or [],
        "result_summary": result_summary,
        "result_value": result_value,
        "row_count": row_count,
        "execution_ms": execution_ms,
        "claim_ids": claim_ids or [],
        "approximate_functions_used": approximate_functions_used or [],
        "warehouse_specific_syntax": warehouse_specific_syntax or [],
        "status": status,
        "error": error,
    }

    with log_path.open("a") as f:
        f.write(json.dumps(entry) + "\n")

    return entry


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------

def read_log(dataset_name: str, date: str) -> list[dict]:
    """Read all entries from a query log file.

    Returns an empty list if the file does not exist.
    """
    log_path = _log_path(dataset_name, date)
    if not log_path.exists():
        return []

    entries = []
    with log_path.open() as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return entries


# ---------------------------------------------------------------------------
# Match claims
# ---------------------------------------------------------------------------

def match_claims(entries: list[dict], claims: list[dict]) -> dict:
    """Match query log entries to analytical claims.

    Attempts to match each claim to log entries by:
    1. Explicit claim_ids already set on the entry.
    2. Fuzzy match on result_value against claim values.

    Args:
        entries: List of query log entry dicts.
        claims: List of claim dicts with at least 'claim_id' and 'value' keys.

    Returns:
        dict mapping claim_id -> list of matching query_ids.
    """
    matches: dict[str, list[str]] = {c["claim_id"]: [] for c in claims}

    # Pass 1: explicit claim_ids
    for entry in entries:
        for cid in entry.get("claim_ids", []):
            if cid in matches and entry["query_id"] not in matches[cid]:
                matches[cid].append(entry["query_id"])

    # Pass 2: fuzzy value match for unmatched claims
    for claim in claims:
        cid = claim["claim_id"]
        if matches[cid]:
            continue  # already matched

        claim_val = claim.get("value")
        if claim_val is None:
            continue

        for entry in entries:
            entry_val = entry.get("result_value")
            if entry_val is None:
                continue

            # Try numeric comparison within 0.1%
            try:
                cv = float(claim_val)
                ev = float(entry_val)
                if cv != 0 and abs(cv - ev) / abs(cv) < 0.001:
                    matches[cid].append(entry["query_id"])
            except (ValueError, TypeError):
                # String equality fallback
                if str(claim_val) == str(entry_val):
                    matches[cid].append(entry["query_id"])

    return matches


# ---------------------------------------------------------------------------
# Backfill
# ---------------------------------------------------------------------------

def backfill_entry(
    dataset_name: str,
    date: str,
    agent: str,
    pipeline_step: float,
    purpose: str,
    sql: str,
    claim_ids: list[str],
    **kwargs,
) -> dict:
    """Append a backfilled entry for a query that was not logged at runtime.

    Identical to append_entry but marks the entry as backfilled.
    Used by the validation agent to fill gaps in the query log.
    """
    query_id = kwargs.pop("query_id", None)
    if query_id is None:
        query_id = f"backfill_{int(time.time() * 1000) % 100000:05d}"

    return append_entry(
        dataset_name=dataset_name,
        date=date,
        agent=agent,
        pipeline_step=pipeline_step,
        purpose=f"[BACKFILLED] {purpose}",
        sql=sql,
        claim_ids=claim_ids,
        query_id=query_id,
        **kwargs,
    )


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def to_markdown(entries: list[dict]) -> str:
    """Render query log entries as a markdown table.

    Args:
        entries: List of entry dicts from read_log().

    Returns:
        Markdown table string.
    """
    if not entries:
        return "_No queries logged._"

    lines = [
        "| # | Agent | Step | Purpose | Tables | Rows | Time (ms) | Status |",
        "|---|-------|------|---------|--------|------|-----------|--------|",
    ]

    for i, e in enumerate(entries, 1):
        tables = ", ".join(e.get("tables_accessed", []))[:30]
        purpose = e.get("purpose", "")[:40]
        rows = e.get("row_count", "—")
        ms = e.get("execution_ms", 0)
        status = e.get("status", "success")
        step = e.get("pipeline_step", "—")
        agent = e.get("agent", "—")

        lines.append(
            f"| {i} | {agent} | {step} | {purpose} "
            f"| {tables} | {rows} | {ms:.0f} | {status} |"
        )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Coverage report
# ---------------------------------------------------------------------------

def coverage_report(
    entries: list[dict],
    claims: list[dict],
) -> dict:
    """Compute query log coverage statistics.

    Args:
        entries: Query log entries.
        claims: List of claims with 'claim_id' keys.

    Returns:
        dict with keys:
            total_claims: int
            matched_claims: int
            coverage_pct: float (0-1)
            backfilled_count: int
            unmatched_claim_ids: list[str]
            status: "PASS" (>=80%) | "WARN" (<80%)
    """
    matches = match_claims(entries, claims)

    matched = sum(1 for v in matches.values() if v)
    total = len(claims)
    coverage = matched / total if total > 0 else 1.0

    backfilled = sum(
        1 for e in entries
        if e.get("query_id", "").startswith("backfill_")
    )

    unmatched = [cid for cid, qids in matches.items() if not qids]

    return {
        "total_claims": total,
        "matched_claims": matched,
        "coverage_pct": round(coverage, 4),
        "backfilled_count": backfilled,
        "unmatched_claim_ids": unmatched,
        "status": "PASS" if coverage >= 0.8 else "WARN",
    }
