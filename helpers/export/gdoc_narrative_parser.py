"""Parse pipeline artifacts into structured data for gdoc_builder.build_readout().

Reads:
  - outputs/narrative_*.md         → title, context, findings, recommendations
  - working/pipeline_summary.md    → dataset name, date, metadata
  - outputs/validation_*.md        → confidence grade/score
  - outputs/close_the_loop_*.md    → success tracking, action items
  - working/cross_verification_*.yaml → provenance data stamps
  - working/query_log_*.jsonl      → SQL per finding

All files are optional. Missing files produce None values, not errors.
"""

from __future__ import annotations

import glob
import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Optional

from helpers.export.gdoc_builder import (
    AnalysisData, Finding, SubFinding, Recommendation, SqlQuery,
    SuccessTracking,
)

_log = logging.getLogger("gdoc_narrative_parser")


def _find_latest(pattern: str, base_dir: str) -> Optional[str]:
    """Find the most recently modified file matching a glob pattern."""
    matches = glob.glob(os.path.join(base_dir, pattern))
    if not matches:
        return None
    return max(matches, key=os.path.getmtime)


def _read_file(path: Optional[str]) -> Optional[str]:
    """Read file contents, return None if path is None or file missing."""
    if not path or not os.path.isfile(path):
        return None
    with open(path, "r") as f:
        return f.read()


def _extract_between(text: str, start_heading: str,
                     end_headings: list[str],
                     heading_level: int = 2) -> Optional[str]:
    """Extract text between two headings of the same level.

    Args:
        text: Full markdown text.
        start_heading: The heading text to start from (without ## prefix).
        end_headings: List of heading texts that mark the end.
        heading_level: Number of # characters (2 for ##, 3 for ###).

    Returns:
        Text between the headings, or None if start not found.
    """
    prefix = "#" * heading_level
    # Match the start heading (case-insensitive, allow leading/trailing space)
    pattern = rf"^{prefix}\s+{re.escape(start_heading)}\s*$"
    match = re.search(pattern, text, re.MULTILINE | re.IGNORECASE)
    if not match:
        return None

    start_pos = match.end()

    # Find the next heading at the same or higher level
    next_heading_pattern = rf"^#{{{1},{heading_level}}}\s+"
    remaining = text[start_pos:]
    next_match = re.search(next_heading_pattern, remaining, re.MULTILINE)

    if next_match:
        return remaining[:next_match.start()].strip()
    return remaining.strip()


# ---------------------------------------------------------------------------
# Narrative parsing
# ---------------------------------------------------------------------------

def _parse_narrative_title(text: str) -> str:
    """Extract the H1 title from narrative markdown."""
    match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    return match.group(1).strip() if match else "Untitled Analysis"


def _parse_context(text: str) -> Optional[str]:
    """Extract the Context section."""
    raw = _extract_between(text, "Context", [
        "Key Findings", "Findings", "Executive Summary",
    ])
    return _strip_markdown(raw) if raw else None


def _parse_executive_summary(text: str) -> Optional[str]:
    """Extract the Executive Summary section."""
    raw = _extract_between(text, "Executive Summary", [
        "Context", "Key Findings", "Findings",
    ])
    return _strip_markdown(raw) if raw else None


def _strip_markdown(text: str) -> str:
    """Strip markdown formatting artifacts from text.

    Removes:
    - --- horizontal rules (standalone lines)
    - Markdown table rows (lines starting with |)
    - Leading/trailing whitespace
    """
    lines = []
    for line in text.split("\n"):
        stripped = line.strip()
        # Skip horizontal rules
        if re.match(r'^-{3,}\s*$', stripped):
            continue
        # Skip markdown table rows
        if stripped.startswith("|") and "|" in stripped[1:]:
            continue
        lines.append(line)
    return "\n".join(lines).strip()


def _parse_findings(text: str, charts_dir: str) -> list[Finding]:
    """Parse ## Key Findings → ### Finding N sections.

    Handles structured narrative format with **Headline:**, **Detail:**,
    **Impact:**, **Metrics:**, **Chart:**, **Source:** fields per finding.
    """
    findings_text = _extract_between(text, "Key Findings", [
        "Insight", "Implication", "Recommendations", "Supporting Data",
    ])
    if not findings_text:
        return []

    findings = []
    # Split on ### Finding N: headings
    parts = re.split(r"^###\s+(?:Finding\s+\d+:\s*)?(.+)$",
                     findings_text, flags=re.MULTILINE)

    # parts[0] is text before first finding (usually empty)
    # parts[1] is first heading text, parts[2] is first body, etc.
    for i in range(1, len(parts), 2):
        headline = parts[i].strip()
        raw_body = parts[i + 1].strip() if i + 1 < len(parts) else ""

        # Parse structured fields from the body
        parsed = _parse_finding_fields(raw_body)

        # Resolve chart path
        chart_path = _find_chart_for_finding(
            parsed.get("chart_ref", ""), raw_body, charts_dir
        )

        # Build clean body from Detail + Impact (no Headline duplicate, no Chart/Source lines)
        body_parts = []
        if parsed.get("detail"):
            body_parts.append(parsed["detail"])
        if parsed.get("impact"):
            body_parts.append(parsed["impact"])
        if parsed.get("metrics"):
            body_parts.append(parsed["metrics"])

        clean_body = "\n\n".join(body_parts) if body_parts else parsed.get("fallback_body", "")

        # Build summary from the Headline field or first sentence of detail
        summary_source = parsed.get("headline_text") or parsed.get("detail") or clean_body
        summary = _first_sentence(summary_source)

        # Sub-finding title: use "Detail" to avoid duplicating the H3 headline
        sub_title = "Detail" if parsed.get("detail") else headline

        # Build sub-finding
        sub = SubFinding(
            title=sub_title,
            body=clean_body,
            chart_path=chart_path,
            chart_caption=headline,
        )

        # Build data_stamp from Source field if available
        data_stamp = None
        if parsed.get("source"):
            data_stamp = f"[{parsed['source']}]"

        findings.append(Finding(
            headline=headline,
            summary=summary,
            sub_findings=[sub],
            data_stamp=data_stamp,
        ))

    return findings


def _parse_finding_fields(body: str) -> dict:
    """Parse structured fields from a finding body.

    Recognizes: **Headline:**, **Detail:**, **Impact:**, **Metrics:**,
    **Chart:**, **Source:**.

    Returns dict with keys: headline_text, detail, impact, metrics,
    chart_ref, source, fallback_body.
    """
    result = {}

    # Extract known **Label:** fields
    field_patterns = {
        "headline_text": r'\*\*Headline:\*\*\s*(.+?)(?=\n\*\*\w|\n---|\Z)',
        "detail": r'\*\*Detail:\*\*\s*(.+?)(?=\n\*\*\w|\n---|\Z)',
        "impact": r'\*\*Impact:\*\*\s*(.+?)(?=\n\*\*\w|\n---|\Z)',
        "chart_ref": r'\*\*Chart:\*\*\s*(\S+\.png)',
        "source": r'\*\*Source:\*\*\s*(.+?)(?=\n\*\*\w|\n---|\Z)',
    }

    for key, pattern in field_patterns.items():
        match = re.search(pattern, body, re.DOTALL)
        if match:
            result[key] = match.group(1).strip()

    # Extract **Metrics:** block (bullet list)
    metrics_match = re.search(
        r'\*\*Metrics:\*\*\s*\n((?:- .+\n?)+)', body
    )
    if metrics_match:
        raw_metrics = metrics_match.group(1).strip()
        # Format as clean bullet points (strip pipe-delimited format)
        metric_lines = []
        for line in raw_metrics.split("\n"):
            line = line.strip().lstrip("- ").strip()
            if "|" in line:
                parts = [p.strip() for p in line.split("|")]
                # Format: "value — label (context)"
                if len(parts) >= 2:
                    metric_lines.append(f"{parts[0]} — {parts[1]}" +
                                         (f" ({parts[2]})" if len(parts) >= 3 else ""))
                else:
                    metric_lines.append(line)
            else:
                metric_lines.append(line)
        result["metrics"] = "\n".join(metric_lines)

    # If no structured fields found, use cleaned body as fallback
    if not any(k in result for k in ("detail", "impact", "headline_text")):
        result["fallback_body"] = _strip_markdown(body)

    return result


def _find_chart_for_finding(chart_ref: str, body: str,
                             charts_dir: str) -> Optional[str]:
    """Look for chart file references in finding body text.

    Checks (in order):
    1. Explicit chart_ref from **Chart:** field parsing
    2. Markdown image syntax: ![...](path.png)
    3. Backtick-wrapped paths: `outputs/charts/file.png`
    4. Bare paths: charts/file.png or outputs/charts/file.png
    """
    # Collect all candidate filenames
    candidates = []

    # From **Chart:** field (highest priority)
    if chart_ref:
        candidates.append(chart_ref)

    # Markdown image syntax
    for match in re.finditer(r"!\[.*?\]\(([^)]*\.png)\)", body):
        candidates.append(match.group(1))

    # Backtick paths
    for match in re.finditer(r"`((?:outputs/)?charts/[^`]+\.png)`", body):
        candidates.append(match.group(1))

    # Bare paths
    for match in re.finditer(r"((?:outputs/)?charts/\S+\.png)", body):
        candidates.append(match.group(1))

    # Try to resolve each candidate
    for ref in candidates:
        basename = os.path.basename(ref)
        for path in [
            ref,
            os.path.join(charts_dir, basename),
            os.path.join("outputs", "charts", basename),
        ]:
            if os.path.isfile(path):
                return os.path.abspath(path)

    return None


def _first_sentence(text: str) -> str:
    """Extract the first sentence from a paragraph."""
    text = text.strip()
    # Remove markdown image references
    text = re.sub(r"!\[.*?\]\([^)]*\)", "", text).strip()
    # Strip markdown bold markers
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    match = re.match(r"(.+?\.)\s", text)
    return match.group(1) if match else text[:200]


def _parse_recommendations(text: str) -> list[Recommendation]:
    """Parse the ## Recommendations section."""
    rec_text = _extract_between(text, "Recommendations", [
        "Supporting Data", "Skills Used", "Validation",
    ])
    if not rec_text:
        return []

    # Strip trailing close-the-loop content (**Track:**, **Next step:**, **Decision owner:**, ---)
    rec_text = re.split(
        r'\n\*\*(?:Track|Next step|Decision owner|Review date):',
        rec_text, maxsplit=1,
    )[0]
    rec_text = re.split(r'\n---', rec_text, maxsplit=1)[0]

    recs = []
    # Match numbered items: 1. **Action**: Description. Confidence level.
    items = re.findall(
        r"\d+\.\s+\*\*(.+?)\*\*:?\s*(.+?)(?=\n\d+\.|\Z)",
        rec_text, re.DOTALL,
    )
    for action, detail in items:
        detail = detail.strip()
        # Extract confidence if mentioned (handle **Confidence: HIGH** format too)
        conf_match = re.search(
            r"\*{0,2}[Cc]onfidence(?:\s+level)?:?\s*(HIGH|High|MEDIUM|Medium|LOW|Low)\*{0,2}",
            detail,
        )
        confidence = conf_match.group(1).capitalize() if conf_match else "Medium"
        # Clean confidence mention and surrounding **markers from rationale
        rationale = re.sub(
            r"\s*\*{0,2}[Cc]onfidence(?:\s+level)?:?\s*(?:HIGH|High|MEDIUM|Medium|LOW|Low)\*{0,2}"
            r"[^.]*\.?",
            "", detail,
        ).strip()
        # Strip remaining markdown artifacts from rationale
        rationale = _strip_markdown(rationale)
        recs.append(Recommendation(
            action=action.strip(),
            rationale=rationale,
            confidence=confidence,
        ))

    return recs


def _parse_insight(text: str) -> Optional[str]:
    """Parse the ## Insight section (maps to Synthesis)."""
    raw = _extract_between(text, "Insight", [
        "Implication", "Recommendations",
    ])
    return _strip_markdown(raw) if raw else None


def _parse_implication(text: str) -> Optional[str]:
    """Parse the ## Implication section."""
    raw = _extract_between(text, "Implication", [
        "Recommendations", "Supporting Data",
    ])
    return _strip_markdown(raw) if raw else None


# ---------------------------------------------------------------------------
# Pipeline summary parsing
# ---------------------------------------------------------------------------

def _parse_pipeline_summary(text: str) -> dict:
    """Extract metadata from pipeline_summary.md."""
    meta = {}

    # Title
    match = re.search(r"^#\s+Pipeline Summary:\s*(.+)$", text, re.MULTILINE)
    if match:
        meta["business_context"] = match.group(1).strip()

    # Dataset
    match = re.search(r"\*\*Dataset:\*\*\s*(.+)$", text, re.MULTILINE)
    if match:
        meta["dataset"] = match.group(1).strip()

    # Date
    match = re.search(r"\*\*Date:\*\*\s*(.+)$", text, re.MULTILINE)
    if match:
        meta["date"] = match.group(1).strip()

    return meta


# ---------------------------------------------------------------------------
# Validation parsing
# ---------------------------------------------------------------------------

def _parse_validation(text: str) -> dict:
    """Extract confidence grade and score from validation report."""
    result = {}

    # Overall Confidence: HIGH | MEDIUM | LOW
    match = re.search(r"Overall Confidence:\s*(HIGH|MEDIUM|LOW)",
                      text, re.IGNORECASE)
    if match:
        level = match.group(1).upper()
        grade_map = {"HIGH": "A", "MEDIUM": "B", "LOW": "C"}
        result["grade"] = grade_map.get(level, "B")

    # Confidence Score: A (92/100) or similar
    match = re.search(r"Confidence Score:.*?([A-F][+-]?)\s*\((\d+)/100\)", text)
    if match:
        result["grade"] = match.group(1)
        result["score"] = int(match.group(2))

    # Look for caveats in Data Quality Notes or warnings
    match = re.search(r"Data Quality Notes\s*\n(.+?)(?=\n##|\Z)",
                      text, re.DOTALL)
    if match:
        caveat = _strip_markdown(match.group(1).strip())
        if caveat and caveat.lower() != "none":
            result["caveat"] = caveat[:200]  # truncate long caveats

    return result


# ---------------------------------------------------------------------------
# SQL collection
# ---------------------------------------------------------------------------

def _collect_sql(base_dir: str) -> list[SqlQuery]:
    """Collect SQL files from working/sql_queries/."""
    sql_dir = os.path.join(base_dir, "working", "sql_queries")
    if not os.path.isdir(sql_dir):
        return []

    queries = []
    for path in sorted(glob.glob(os.path.join(sql_dir, "*.sql"))):
        name = Path(path).stem
        # Convert filename to title: "01_revenue_by_segment" → "Revenue By Segment"
        title = re.sub(r"^\d+_", "", name).replace("_", " ").title()
        sql = _read_file(path) or ""
        queries.append(SqlQuery(title=title, sql=sql))

    return queries


# ---------------------------------------------------------------------------
# Provenance enrichment
# ---------------------------------------------------------------------------

def _load_yaml_safe(path: str) -> Any:
    """Load a YAML file, return None on any error."""
    try:
        import yaml
        with open(path, "r") as f:
            return yaml.safe_load(f)
    except Exception:
        return None


def _load_jsonl(path: str) -> list[dict]:
    """Load a JSONL file into a list of dicts."""
    entries = []
    try:
        with open(path, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))
    except Exception:
        pass
    return entries


def _enrich_findings_with_provenance(
    findings: list[Finding],
    base_dir: str,
    confidence_grade: str | None = None,
    confidence_score: int | None = None,
) -> list | None:
    """Enrich findings with provenance data (data stamps, methodology, SQL, cross-verification).

    Loads cross-verification YAML and query log JSONL from working/,
    builds provenance blocks via provenance_assembler, then populates
    Finding.data_stamp, .methodology, .sql, and .cross_verification.

    Returns provenance_blocks list for AnalysisData.provenance_blocks,
    or None if enrichment could not run.
    """
    try:
        from helpers.provenance.provenance_assembler import (
            build_provenance_blocks,
            render_data_stamp,
        )
    except ImportError:
        _log.debug("provenance_assembler not available, skipping enrichment")
        return None

    working_dir = os.path.join(base_dir, "working")

    # Load cross-verification data
    cv_path = _find_latest("cross_verification_*.yaml", working_dir)
    cv_data = None
    if cv_path:
        raw = _load_yaml_safe(cv_path)
        if isinstance(raw, dict):
            cv_data = raw.get("claims", [])
        elif isinstance(raw, list):
            cv_data = raw

    # Load query log entries
    ql_path = _find_latest("query_log_*.jsonl", working_dir)
    ql_entries = _load_jsonl(ql_path) if ql_path else []

    # Build finding dicts for provenance_assembler
    finding_dicts = []
    for i, f in enumerate(findings, 1):
        # Try to extract table name and date range from the finding text
        primary_table = ""
        date_range = ""
        row_count = 0

        # Check if there's a matching query log entry for this finding
        for entry in ql_entries:
            purpose = entry.get("purpose", "")
            # Match by finding index or headline keywords
            headline_lower = f.headline.lower()
            if (f"finding {i}" in purpose.lower()
                    or any(word in purpose.lower()
                           for word in headline_lower.split()[:3] if len(word) > 3)):
                row_count = entry.get("rows", 0) or 0
                sql_text = entry.get("sql", "")
                # Extract table from SQL (simple FROM clause extraction)
                table_match = re.search(r'\bFROM\s+(\S+)', sql_text, re.IGNORECASE)
                if table_match:
                    primary_table = table_match.group(1).strip('";`').upper()
                # Extract date range from SQL
                date_matches = re.findall(r"'(\d{4}-\d{2}-\d{2})'", sql_text)
                if len(date_matches) >= 2:
                    date_range = f"{date_matches[0]} to {date_matches[-1]}"
                elif len(date_matches) == 1:
                    date_range = f"from {date_matches[0]}"
                break

        finding_dicts.append({
            "finding_id": f"F{i}",
            "finding_title": f.headline,
            "row_count": row_count,
            "date_range": date_range,
            "primary_table": primary_table,
            "sql": "",  # will be populated from query log below
        })

    # Try to match each finding to its SQL from query log
    for i, fd in enumerate(finding_dicts):
        for entry in ql_entries:
            purpose = entry.get("purpose", "")
            headline_lower = findings[i].headline.lower()
            if (f"finding {i+1}" in purpose.lower()
                    or any(word in purpose.lower()
                           for word in headline_lower.split()[:3] if len(word) > 3)):
                fd["sql"] = entry.get("sql", "")
                break

    # Build confidence result dict
    confidence_result = None
    if confidence_grade:
        confidence_result = {
            "grade": confidence_grade,
            "score": confidence_score,
        }

    # Build provenance blocks
    blocks = build_provenance_blocks(
        findings=finding_dicts,
        cross_verification=cv_data,
        confidence_result=confidence_result,
        query_log_entries=ql_entries,
    )

    # Populate Finding fields from provenance blocks
    for i, block in enumerate(blocks):
        if i >= len(findings):
            break

        finding = findings[i]

        # Data stamp one-liner
        stamp = block.get("data_stamp", {})
        one_liner = stamp.get("one_liner", "")
        if one_liner and stamp.get("row_count", 0) > 0:
            finding.data_stamp = one_liner

        # Methodology
        meth = block.get("methodology")
        if meth and meth.get("approach"):
            parts = [f"Approach: {meth['approach']}"]
            if meth.get("aggregation"):
                parts.append(f"Aggregation: {meth['aggregation']}")
            if meth.get("filters"):
                parts.append(f"Filters: {', '.join(meth['filters'])}")
            if meth.get("date_handling"):
                parts.append(f"Date handling: {meth['date_handling']}")
            finding.methodology = ". ".join(parts)

        # SQL
        sql_block = block.get("sql")
        if sql_block and sql_block.get("query_full"):
            finding.sql = sql_block["query_full"]

        # Cross-verification
        cv = block.get("cross_verification")
        if cv and cv.get("method") != "None":
            finding.cross_verification = (
                f"{cv['method']} — {cv['result']}"
                + (f" ({cv['detail']})" if cv.get("detail") else "")
            )

    return blocks


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_pipeline_outputs(base_dir: str = ".") -> AnalysisData:
    """Parse all pipeline artifacts and return structured AnalysisData.

    Args:
        base_dir: Root directory of the ai-analyst project.

    Returns:
        AnalysisData ready for gdoc_builder.build_readout().
    """
    outputs_dir = os.path.join(base_dir, "outputs")
    working_dir = os.path.join(base_dir, "working")
    charts_dir = os.path.join(outputs_dir, "charts")

    # Find source files
    narrative_path = _find_latest("narrative_*.md", outputs_dir)
    summary_path = os.path.join(working_dir, "pipeline_summary.md")
    validation_path = _find_latest("validation_*.md", outputs_dir)
    close_loop_path = _find_latest("close_the_loop_*.md", outputs_dir)

    # Read files
    narrative_text = _read_file(narrative_path)
    summary_text = _read_file(summary_path)
    validation_text = _read_file(validation_path)
    close_loop_text = _read_file(close_loop_path)

    # Parse narrative (primary source)
    title = "Untitled Analysis"
    context = None
    findings = []
    recommendations = []
    synthesis = None
    implications = None

    if narrative_text:
        title = _parse_narrative_title(narrative_text)
        context = _parse_context(narrative_text)
        findings = _parse_findings(narrative_text, charts_dir)
        recommendations = _parse_recommendations(narrative_text)
        synthesis = _parse_insight(narrative_text)
        implications = _parse_implication(narrative_text)

        # If no context from narrative, try executive summary
        if not context:
            context = _parse_executive_summary(narrative_text)

    # Parse pipeline summary (metadata)
    meta = _parse_pipeline_summary(summary_text) if summary_text else {}
    dataset = meta.get("dataset", "")
    date = meta.get("date", "")
    subtitle = f"{dataset} | {date}" if dataset else None

    # Parse validation (confidence)
    validation = _parse_validation(validation_text) if validation_text else {}
    confidence_grade = validation.get("grade")
    confidence_score = validation.get("score")
    confidence_caveat = validation.get("caveat")

    # Enrich findings with provenance (data stamps, methodology, SQL, cross-verification)
    provenance_blocks = None
    if findings:
        try:
            provenance_blocks = _enrich_findings_with_provenance(
                findings, base_dir, confidence_grade, confidence_score,
            )
        except Exception as e:
            _log.warning("Provenance enrichment failed (non-fatal): %s", e)

    # Collect SQL queries
    sql_queries = _collect_sql(base_dir)

    # Parse close-the-loop (success tracking)
    success_tracking = None
    open_questions = None
    next_steps_actions = None

    if close_loop_text:
        # Try to extract action items
        actions_section = _extract_between(close_loop_text, "Action Items", [
            "Success", "Open Questions", "Follow-up",
        ])
        if actions_section:
            next_steps_actions = actions_section

        # Try to extract success metric
        success_section = _extract_between(close_loop_text, "Success Metric", [
            "Open Questions", "Action Items", "Follow-up",
        ])
        if success_section:
            metric_match = re.search(r"Metric:\s*(.+)", success_section)
            baseline_match = re.search(r"Baseline:\s*(.+)", success_section)
            target_match = re.search(r"Target:\s*(.+)", success_section)
            checkin_match = re.search(r"Check.in:\s*(.+)", success_section)
            if metric_match:
                success_tracking = SuccessTracking(
                    metric=metric_match.group(1).strip(),
                    baseline=baseline_match.group(1).strip() if baseline_match else "TBD",
                    target=target_match.group(1).strip() if target_match else "TBD",
                    check_in_date=checkin_match.group(1).strip() if checkin_match else None,
                )

        # Open questions
        oq_section = _extract_between(close_loop_text, "Open Questions", [
            "Action Items", "Success", "Follow-up",
        ])
        if oq_section:
            open_questions = oq_section

    return AnalysisData(
        title=title,
        subtitle=subtitle,
        author="AI Analyst",
        date=date,
        confidence_grade=confidence_grade,
        confidence_score=confidence_score,
        confidence_caveat=confidence_caveat,
        context=context,
        findings=findings,
        synthesis=synthesis,
        implications=implications,
        recommendations=recommendations,
        next_steps_actions=next_steps_actions,
        success_tracking=success_tracking,
        open_questions=open_questions,
        sql_queries=sql_queries,
        data_sources=f"Dataset: {dataset}" if dataset else None,
        provenance_blocks=provenance_blocks,
    )
