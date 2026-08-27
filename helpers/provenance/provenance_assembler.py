"""Provenance assembler — builds structured provenance blocks for 3 audience levels.

Audience levels:
  - Glance:     Data stamp one-liner (always visible, all tiers, all exports)
  - Curious:    Citation appendix / toggle blocks (Tier 2+)
  - Reproduce:  Full receipt with SQL, connection details, query log (Tier 3)

Consumers: storytelling agent (embeds data stamps), export agents (render at
audience-appropriate level), receipt generator (full audit trail).

Usage:
    from helpers.provenance.provenance_assembler import (
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

from helpers.data.freshness import COLOR_MISSING, freshness


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


# ---------------------------------------------------------------------------
# Source tier — where a number came from, on a governance hierarchy
# ---------------------------------------------------------------------------

# The source-tier hierarchy, most governed first. A number is only as trustworthy
# as the least-governed table it was read from, so the footer reports the FLOOR of
# a query's inputs. The lesson and the slide mirror this list verbatim.
#
#   governed  a certified / blessed source, signed off by a data owner
#   curated   a semantic-layer / verified-query source (modeled, not yet certified)
#   raw       a direct table query, ungoverned (the honest default)
#
# Each row is (tier_key, rendered_label, one_line_meaning).
SOURCE_TIER_HIERARCHY: List[tuple[str, str, str]] = [
    ("governed", "governed - certified source",
     "a certified / blessed source, signed off by a data owner"),
    ("curated", "curated - semantic-layer source",
     "a semantic-layer / verified-query source, modeled but not certified"),
    ("raw", "raw - direct query",
     "a direct table query, ungoverned"),
]

# Tier keys, named so callers and tests don't pass bare strings.
TIER_GOVERNED = "governed"
TIER_CURATED = "curated"
TIER_RAW = "raw"

# Derived lookups: rank (higher = more governed) and the rendered label per key.
_TIER_RANK: Dict[str, int] = {
    key: len(SOURCE_TIER_HIERARCHY) - i - 1
    for i, (key, _label, _meaning) in enumerate(SOURCE_TIER_HIERARCHY)
}
_TIER_LABEL: Dict[str, str] = {
    key: label for key, label, _meaning in SOURCE_TIER_HIERARCHY
}


def load_tier_metadata(entities: Any) -> Dict[str, str]:
    """Build a table-name -> tier map from parsed semantic-layer entities.

    Reads the OPTIONAL ``source_tier`` field on each entity in entities.yaml.
    ``entities`` may be the parsed top-level dict (with an ``entities`` list) or
    the list itself. An entity whose ``source_tier`` is "governed" or "curated"
    contributes its base_table, logical_table, and entity name to the map (keys
    upper-cased for case-insensitive match); an entity without the field
    contributes nothing, so it falls through to raw.

    Today NovaMart's entities.yaml carries no ``source_tier`` on any entity, so
    this returns an empty map and every NovaMart query reads as raw — the honest
    tier. Adding ``source_tier: governed`` to one entity is the one-line change
    that upgrades that table's footer, and this loader is what reads it.

    Args:
        entities: parsed entities.yaml (dict with "entities", or a list of dicts).

    Returns:
        dict mapping each table/entity name (upper-cased) -> tier key.
    """
    if isinstance(entities, dict):
        entity_list = entities.get("entities", [])
    else:
        entity_list = entities or []

    out: Dict[str, str] = {}
    valid = {TIER_GOVERNED, TIER_CURATED}
    for ent in entity_list:
        if not isinstance(ent, dict):
            continue
        tier = ent.get("source_tier")
        if tier not in valid:
            continue
        for key in (ent.get("base_table"), ent.get("logical_table"), ent.get("entity")):
            if key:
                out[str(key).upper()] = tier
    return out


def derive_source_tier(
    tables_accessed: Optional[List[str]],
    tier_metadata: Optional[Dict[str, str]] = None,
) -> str:
    """Return the rendered source-tier label for a query, given the tables it touched.

    The tier sits on the governance hierarchy governed > curated > raw
    (see SOURCE_TIER_HIERARCHY). ``tier_metadata`` maps a table name -> its tier
    key ("governed" or "curated"), typically produced by load_tier_metadata from
    the semantic layer. Matching is case-insensitive on the table name.

    A result is only as governed as its least-governed input, so the tier is the
    FLOOR across the touched tables: any table without governance metadata counts
    as raw and drags the whole query to raw. When NO touched table carries
    governance metadata — the NovaMart case, where entities.yaml pins meaning and
    structure but assigns no tier — the honest answer is "raw - direct query".
    This never returns "not available".

    Args:
        tables_accessed: the tables the backing query read.
        tier_metadata: optional table-name -> tier key map ("governed"/"curated").

    Returns:
        A rendered label from SOURCE_TIER_HIERARCHY (e.g. "raw - direct query").
    """
    tables = [t for t in (tables_accessed or []) if t]
    if not tables:
        return _TIER_LABEL[TIER_RAW]

    norm = {str(k).upper(): v for k, v in (tier_metadata or {}).items()}

    floor_key = TIER_GOVERNED
    for tbl in tables:
        tier = norm.get(str(tbl).upper(), TIER_RAW)  # unlabeled table = raw
        if _TIER_RANK.get(tier, 0) < _TIER_RANK[floor_key]:
            floor_key = tier
    return _TIER_LABEL.get(floor_key, _TIER_LABEL[TIER_RAW])


# ---------------------------------------------------------------------------
# Full footer — built fields plus honest placeholders for what is not yet wired
# ---------------------------------------------------------------------------

# Placeholder value for footer fields whose backing data is not yet produced.
# Shown verbatim so the reader can see what the system cannot yet stand behind,
# rather than a faked value or a silently dropped line.
NOT_AVAILABLE = "not available"

# The four lifecycle fields, in footer order, with their wiring status:
#   wired      reads a real derived value (Source tier, Freshness)
#   not_wired  renders the explicit NOT_AVAILABLE placeholder (Owner, Signals)
LIFECYCLE_FIELDS: List[tuple[str, str]] = [
    ("Source tier", "wired"),
    ("Owner", "not_wired"),
    ("Freshness", "wired"),
    ("Signals", "not_wired"),
]

# Footer fields the assembler does not yet produce. Each is rendered as the
# explicit NOT_AVAILABLE placeholder until the data behind it is wired. Source
# tier and Freshness have since been wired and dropped off this list.
NOT_YET_WIRED_FIELDS: List[tuple[str, str]] = [
    ("Owner", "from the metric definition, with a Missing fallback"),
    ("Signals", "the five-signal traffic light"),
]


def build_full_footer(
    block: ProvenanceBlock,
    last_verified: Optional[str] = None,
    today: Optional[str] = None,
    tier_metadata: Optional[Dict[str, str]] = None,
) -> str:
    """Render the complete provenance footer for a finding.

    This is the full teaching shape of the footer. It starts with the built
    fields (data stamp, SQL, methodology, cross-verification, reproducibility,
    backing query-id links, and the confidence grade/score embedded in the data
    stamp), then shows the four lifecycle fields.

    Source tier is wired: it is derived from the tables the backing query touched
    (block reproducibility tables, falling back to the data-stamp primary table)
    against any governance metadata in ``tier_metadata`` (see derive_source_tier
    and load_tier_metadata). With no governance metadata — the NovaMart case — it
    reads "raw - direct query", never "not available".

    Freshness is wired: when the caller supplies the definition's last_verified
    date (and today), the Freshness field reads the real green/yellow/red color
    and age, drawn from helpers.data.freshness. With no last_verified available it
    falls back to the explicit "not available" placeholder.

    The remaining placeholders are deliberate. The footer shows every field, and
    a field reads "not available" when the data behind it is not yet produced.
    That is itself a provenance signal: the reader can see what the system
    cannot yet stand behind, instead of a faked value or a quietly omitted line.

    Lifecycle fields:
      - Source tier   (governed / curated / raw classification) - wired here
      - Owner         (from the metric definition, with a Missing fallback) - not yet wired
      - Freshness     (last-verified date + green/yellow/red color) - wired here
      - Signals       (the five-signal traffic light) - not yet wired

    Args:
        block: ProvenanceBlock dict.
        last_verified: the backing definition's last-verified date (YYYY-MM-DD),
            or None when no freshness metadata is available.
        today: the date to measure freshness against (YYYY-MM-DD). Passed in so
            the footer is deterministic; required for a real Freshness read.
        tier_metadata: optional table-name -> tier key map for source-tier
            derivation. None (the default) means no governance metadata, so the
            tier reads raw.

    Returns:
        Markdown string: the appendix entry followed by the four lifecycle lines.
    """
    parts = [render_provenance_appendix(block), ""]

    # Source tier — derived from the tables the backing query touched.
    repro = block.get("reproducibility") or {}
    tables = list(repro.get("tables") or [])
    if not tables:
        primary = (block.get("data_stamp") or {}).get("primary_table")
        if primary:
            tables = [primary]
    source_tier_value = derive_source_tier(tables, tier_metadata)

    # Freshness — real color/age when last_verified is supplied, else placeholder.
    freshness_value = NOT_AVAILABLE
    if last_verified and today:
        age_days, color = freshness(last_verified, today)
        if color != COLOR_MISSING:
            freshness_value = f"{color} (verified {last_verified}, {age_days}d ago)"

    wired_values = {
        "Source tier": source_tier_value,
        "Freshness": freshness_value,
    }
    for label, status in LIFECYCLE_FIELDS:
        if status == "wired":
            parts.append(f"**{label}:** {wired_values[label]}")
        else:
            parts.append(f"**{label}:** {NOT_AVAILABLE}")
    return "\n".join(parts)
