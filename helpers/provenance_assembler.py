"""Provenance assembler — builds structured provenance blocks for 3 audience levels.

Audience levels:
  - Glance:     Data stamp one-liner (always visible, all tiers, all exports)
  - Curious:    Citation appendix / toggle blocks (Tier 2+)
  - Reproduce:  Full receipt with SQL, connection details, query log (Tier 3)

Consumers: storytelling agent (embeds data stamps), export agents (render at
audience-appropriate level), receipt generator (full audit trail).

Usage:
    from helpers.provenance_assembler import (
        build_provenance_blocks,
        build_data_stamp,
        format_row_count,
    )

    blocks = build_provenance_blocks(
        findings=findings_list,
        cross_verification=cv_data,
        confidence_result=confidence_result,
        query_log_entries=log_entries,
    )
    for block in blocks:
        print(block["data_stamp"]["one_liner"])
"""

from __future__ import annotations

import re
import textwrap
from typing import Any, Dict, List, Optional, TypedDict


# ---------------------------------------------------------------------------
# TypedDicts — structured schemas for provenance data
# ---------------------------------------------------------------------------

class DataStamp(TypedDict):
    """Compact data provenance for a single finding."""
    one_liner: str          # [145K rows | Jan-Mar 2026 | ORDERS | Confidence: B (82/100)]
    abbreviated: str        # 145K | Jan-Mar 2026 | ORDERS | B (82)
    no_validation: str      # [145K rows | Jan-Mar 2026 | ORDERS]
    row_count: int
    row_count_formatted: str
    date_range: str
    primary_table: str
    confidence_grade: Optional[str]
    confidence_score: Optional[int]


class SQLBlock(TypedDict):
    """SQL provenance for Curious and Reproduce audiences."""
    query_full: str         # Normalized full SQL
    query_truncated: str    # 15-line cap for appendix display


class Methodology(TypedDict):
    """How the analysis was conducted."""
    approach: str           # e.g., "segmented comparison"
    aggregation: str        # e.g., "SUM by segment"
    filters: List[str]      # e.g., ["date >= '2026-01-01'", "status = 'completed'"]
    date_handling: str      # e.g., "monthly granularity, UTC"


class CrossVerificationSummary(TypedDict):
    """Cross-verification result for a single finding."""
    method: str             # e.g., "Type B: Parts-to-whole"
    result: str             # "PASS", "WARN", "FAIL"
    verified: bool
    detail: str             # e.g., "Within 0.3% tolerance"


class ValidationSummary(TypedDict):
    """Validation result summary for a finding."""
    status: str             # "PASS", "WARNING", "BLOCKER"
    checks_applied: List[str]
    warnings: List[str]


class ReproducibilityInfo(TypedDict):
    """Connection and source information for reproducibility."""
    connection_type: str    # "snowflake", "bigquery", "duckdb", "csv"
    database: str
    tables: List[str]
    deterministic: bool


class ProvenanceBlock(TypedDict):
    """Complete provenance record for one finding."""
    finding_id: str                                     # "F1"
    finding_title: str                                  # "Mobile converts at half the rate"
    data_stamp: DataStamp
    sql: Optional[SQLBlock]
    methodology: Optional[Methodology]
    cross_verification: Optional[CrossVerificationSummary]
    validation: Optional[ValidationSummary]
    reproducibility: Optional[ReproducibilityInfo]
    query_ids: List[str]                                # Backing query log IDs


# ---------------------------------------------------------------------------
# Row count formatting
# ---------------------------------------------------------------------------

def format_row_count(n: int) -> str:
    """Format a row count for display in data stamps.

    Rules:
        - Under 1K: exact (e.g., "842")
        - 1K-9,999: one decimal K (e.g., "3.2K")
        - 10K-999K: whole K (e.g., "145K")
        - 1M+: one decimal M (e.g., "2.4M")

    Args:
        n: Row count integer.

    Returns:
        Formatted string.
    """
    if n < 0:
        return str(n)
    if n < 1_000:
        return str(n)
    if n < 10_000:
        return f"{n / 1_000:.1f}K"
    if n < 1_000_000:
        return f"{n // 1_000}K"
    return f"{n / 1_000_000:.1f}M"


# ---------------------------------------------------------------------------
# SQL normalization
# ---------------------------------------------------------------------------

def _normalize_sql_for_display(sql: str) -> str:
    """Normalize SQL for clean display in provenance blocks.

    - Strips leading/trailing whitespace
    - Collapses excessive blank lines to single blank line
    - Normalizes indentation (dedent)
    - Strips trailing semicolons

    Args:
        sql: Raw SQL string.

    Returns:
        Cleaned SQL string.
    """
    if not sql:
        return ""

    # Dedent and strip
    cleaned = textwrap.dedent(sql).strip()

    # Collapse multiple blank lines to one
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

    # Strip trailing semicolons
    cleaned = cleaned.rstrip(";").rstrip()

    return cleaned


def _truncate_sql(sql: str, max_lines: int = 15) -> str:
    """Truncate SQL to a maximum number of lines for appendix display.

    Args:
        sql: Normalized SQL string.
        max_lines: Maximum lines to keep. Default 15.

    Returns:
        Truncated SQL, with "-- ... (truncated)" if cut.
    """
    if not sql:
        return ""

    lines = sql.split("\n")
    if len(lines) <= max_lines:
        return sql

    truncated = "\n".join(lines[:max_lines])
    return truncated + f"\n-- ... ({len(lines) - max_lines} more lines)"


# ---------------------------------------------------------------------------
# Data stamp builder
# ---------------------------------------------------------------------------

def build_data_stamp(
    row_count: int,
    date_range: str,
    primary_table: str,
    confidence_grade: str | None = None,
    confidence_score: int | None = None,
) -> DataStamp:
    """Build a DataStamp dict for a finding.

    Args:
        row_count: Number of rows in the result set.
        date_range: Human-readable date range (e.g., "Jan-Mar 2026").
        primary_table: Primary table name (e.g., "ORDERS").
        confidence_grade: Letter grade from confidence scoring (A-F).
        confidence_score: Numeric score (0-100).

    Returns:
        DataStamp TypedDict.
    """
    rc_fmt = format_row_count(row_count)

    # No-validation format (always available)
    no_val = f"[{rc_fmt} rows | {date_range} | {primary_table}]"

    # Full format (with confidence if available)
    if confidence_grade and confidence_score is not None:
        one_liner = (
            f"[{rc_fmt} rows | {date_range} | {primary_table} | "
            f"Confidence: {confidence_grade} ({confidence_score}/100)]"
        )
        abbreviated = (
            f"{rc_fmt} | {date_range} | {primary_table} | "
            f"{confidence_grade} ({confidence_score})"
        )
    else:
        one_liner = no_val
        abbreviated = f"{rc_fmt} | {date_range} | {primary_table}"

    return DataStamp(
        one_liner=one_liner,
        abbreviated=abbreviated,
        no_validation=no_val,
        row_count=row_count,
        row_count_formatted=rc_fmt,
        date_range=date_range,
        primary_table=primary_table,
        confidence_grade=confidence_grade,
        confidence_score=confidence_score,
    )


# ---------------------------------------------------------------------------
# Provenance block builder
# ---------------------------------------------------------------------------

def build_provenance_blocks(
    findings: List[Dict[str, Any]],
    cross_verification: Optional[List[Dict[str, Any]]] = None,
    confidence_result: Optional[Dict[str, Any]] = None,
    query_log_entries: Optional[List[Dict[str, Any]]] = None,
    connection_type: str = "duckdb",
    database: str = "",
) -> List[ProvenanceBlock]:
    """Build provenance blocks for all findings in an analysis.

    Each finding dict should have:
        finding_id: str (e.g., "F1")
        finding_title: str (action headline)
        row_count: int (result set rows)
        date_range: str (e.g., "Jan-Mar 2026")
        primary_table: str (e.g., "ORDERS")
        sql: str (optional, the query that produced the finding)
        methodology: dict (optional, approach/aggregation/filters/date_handling)
        tables_accessed: list[str] (optional)

    Args:
        findings: List of finding dicts from the analysis.
        cross_verification: List of per-claim verification records
            (from working/cross_verification_*.yaml).
        confidence_result: Output from score_confidence() — used for
            the confidence grade/score in data stamps.
        query_log_entries: Entries from the query log JSONL.
        connection_type: Active connection type for reproducibility info.
        database: Database name for reproducibility info.

    Returns:
        List of ProvenanceBlock dicts, one per finding.
    """
    # Extract confidence info
    grade = None
    score = None
    if confidence_result:
        grade = confidence_result.get("grade")
        score = confidence_result.get("score")

    # Index cross-verification by claim_id for fast lookup
    cv_index: Dict[str, Dict[str, Any]] = {}
    if cross_verification:
        for cv in cross_verification:
            cid = cv.get("claim_id") or cv.get("finding_id")
            if cid:
                cv_index[cid] = cv

    # Index query log entries for finding-to-query linkage
    ql_by_claim: Dict[str, List[str]] = {}    # claim_id -> [query_ids]
    ql_by_table: Dict[str, List[str]] = {}    # TABLE_NAME -> [query_ids]
    if query_log_entries:
        for qe in query_log_entries:
            qid = qe.get("query_id", "")
            # Index by explicit claim_ids
            for cid in qe.get("claim_ids", []):
                ql_by_claim.setdefault(cid, []).append(qid)
            # Index by tables_accessed (uppercased for case-insensitive match)
            for tbl in qe.get("tables_accessed", []):
                ql_by_table.setdefault(tbl.upper(), []).append(qid)

    blocks: List[ProvenanceBlock] = []

    for finding in findings:
        fid = finding.get("finding_id", "?")
        title = finding.get("finding_title", "")
        row_count = finding.get("row_count", 0)
        date_range = finding.get("date_range", "")
        primary_table = finding.get("primary_table", "")
        raw_sql = finding.get("sql", "")
        methodology_data = finding.get("methodology")
        tables = finding.get("tables_accessed", [])

        # Build data stamp
        stamp = build_data_stamp(
            row_count=row_count,
            date_range=date_range,
            primary_table=primary_table,
            confidence_grade=grade,
            confidence_score=score,
        )

        # Build SQL block
        sql_block = None
        if raw_sql:
            normalized = _normalize_sql_for_display(raw_sql)
            sql_block = SQLBlock(
                query_full=normalized,
                query_truncated=_truncate_sql(normalized),
            )

        # Build methodology
        methodology = None
        if methodology_data:
            methodology = Methodology(
                approach=methodology_data.get("approach", ""),
                aggregation=methodology_data.get("aggregation", ""),
                filters=methodology_data.get("filters", []),
                date_handling=methodology_data.get("date_handling", ""),
            )

        # Build cross-verification summary
        cv_summary = None
        cv_record = cv_index.get(fid)
        if cv_record:
            verification = cv_record.get("verification", {})
            # Determine primary method and result
            method, result, detail = _extract_cv_summary(verification)
            cv_summary = CrossVerificationSummary(
                method=method,
                result=result,
                verified=result in ("PASS", "WARN"),
                detail=detail,
            )

        # Build reproducibility info
        repro = ReproducibilityInfo(
            connection_type=connection_type,
            database=database,
            tables=tables if tables else [primary_table] if primary_table else [],
            deterministic=connection_type in ("duckdb", "csv"),
        )

        # Match finding to backing query log entries
        matched_qids: List[str] = []
        # Priority 1: explicit claim_ids referencing this finding
        if fid in ql_by_claim:
            matched_qids.extend(ql_by_claim[fid])
        # Priority 2: table name match (if no explicit claim link)
        if not matched_qids and primary_table:
            matched_qids.extend(ql_by_table.get(primary_table.upper(), []))
        # Deduplicate while preserving order
        seen: set[str] = set()
        unique_qids: List[str] = []
        for qid in matched_qids:
            if qid not in seen:
                seen.add(qid)
                unique_qids.append(qid)

        block = ProvenanceBlock(
            finding_id=fid,
            finding_title=title,
            data_stamp=stamp,
            sql=sql_block,
            methodology=methodology,
            cross_verification=cv_summary,
            validation=None,  # Filled by validation agent downstream
            reproducibility=repro,
            query_ids=unique_qids,
        )
        blocks.append(block)

    return blocks


def _extract_cv_summary(verification: Dict[str, Any]) -> tuple[str, str, str]:
    """Extract the primary cross-verification result from a verification record.

    Picks the most specific verification type that ran (D > C > B > boundary).

    Args:
        verification: The 'verification' dict from a cross-verification claim.

    Returns:
        Tuple of (method, result, detail).
    """
    # Check in order of specificity: D, C, B, boundary
    for check_type, label in [
        ("algebraic_identity", "Type D: Algebraic identity"),
        ("ratio_recompute", "Type C: Ratio recompute"),
        ("parts_to_whole", "Type B: Parts-to-whole"),
        ("boundary", "Type A: Boundary check"),
    ]:
        check = verification.get(check_type)
        if check and check.get("status") not in (None, "N/A"):
            status = check["status"]
            if check_type == "parts_to_whole":
                diff = check.get("diff_pct", 0)
                detail = f"Within {diff:.2%} tolerance" if status == "PASS" else f"{diff:.2%} deviation"
            elif check_type == "boundary":
                checks_list = check.get("checks", [])
                detail = f"{len(checks_list)} checks passed" if status == "PASS" else "Boundary violation"
            else:
                diff = check.get("diff_pct", 0)
                detail = f"{diff:.4%} deviation" if diff else status
            return label, status, detail

    return "None", "N/A", "No verification checks ran"


# ---------------------------------------------------------------------------
# Rendering helpers for export agents
# ---------------------------------------------------------------------------

def render_data_stamp(stamp: DataStamp, level: str = "full") -> str:
    """Render a data stamp at the requested audience level.

    Args:
        stamp: DataStamp dict.
        level: "full" (default), "abbreviated", or "no_validation".

    Returns:
        Formatted stamp string.
    """
    if level == "abbreviated":
        return stamp["abbreviated"]
    if level == "no_validation":
        return stamp["no_validation"]
    return stamp["one_liner"]


def render_provenance_appendix(block: ProvenanceBlock) -> str:
    """Render a full provenance appendix entry for Curious audience.

    Produces a markdown section with SQL (truncated), methodology,
    cross-verification result, and validation status.

    Args:
        block: ProvenanceBlock dict.

    Returns:
        Markdown string.
    """
    parts = [f"### {block['finding_id']}: {block['finding_title']}"]
    parts.append("")
    parts.append(f"**Data:** {block['data_stamp']['one_liner']}")

    if block.get("sql"):
        parts.append("")
        parts.append("**SQL:**")
        parts.append(f"```sql\n{block['sql']['query_truncated']}\n```")

    if block.get("methodology"):
        m = block["methodology"]
        parts.append("")
        parts.append(f"**Methodology:** {m['approach']}")
        if m.get("aggregation"):
            parts.append(f"- Aggregation: {m['aggregation']}")
        if m.get("filters"):
            parts.append(f"- Filters: {', '.join(m['filters'])}")
        if m.get("date_handling"):
            parts.append(f"- Date handling: {m['date_handling']}")

    if block.get("cross_verification"):
        cv = block["cross_verification"]
        verified_label = "Verified" if cv["verified"] else "Not verified"
        parts.append("")
        parts.append(f"**Cross-verification:** {cv['method']} — {cv['result']} ({verified_label})")
        if cv.get("detail"):
            parts.append(f"- {cv['detail']}")

    if block.get("validation"):
        v = block["validation"]
        parts.append("")
        parts.append(f"**Validation:** {v['status']}")
        if v.get("warnings"):
            for w in v["warnings"]:
                parts.append(f"- {w}")

    if block.get("query_ids"):
        parts.append("")
        parts.append(f"**Backing queries:** {', '.join(block['query_ids'])}")

    return "\n".join(parts)
