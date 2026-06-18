"""Tests for helpers/provenance_assembler.py."""

from __future__ import annotations

import pytest

from helpers.provenance_assembler import (
    DataStamp,
    ProvenanceBlock,
    build_data_stamp,
    build_provenance_blocks,
    format_row_count,
    render_data_stamp,
    render_provenance_appendix,
    _normalize_sql_for_display,
    _truncate_sql,
    _extract_cv_summary,
)


# ── format_row_count ─────────────────────────────────────────────────────

class TestFormatRowCount:
    def test_zero(self):
        assert format_row_count(0) == "0"

    def test_small(self):
        assert format_row_count(842) == "842"

    def test_under_1k(self):
        assert format_row_count(999) == "999"

    def test_1k_boundary(self):
        assert format_row_count(1000) == "1.0K"

    def test_low_k(self):
        assert format_row_count(3200) == "3.2K"

    def test_9999(self):
        assert format_row_count(9999) == "10.0K"

    def test_10k_boundary(self):
        assert format_row_count(10000) == "10K"

    def test_mid_k(self):
        assert format_row_count(145000) == "145K"

    def test_999k(self):
        assert format_row_count(999000) == "999K"

    def test_1m_boundary(self):
        assert format_row_count(1000000) == "1.0M"

    def test_large_m(self):
        assert format_row_count(2400000) == "2.4M"

    def test_negative(self):
        assert format_row_count(-5) == "-5"


# ── _normalize_sql_for_display ───────────────────────────────────────────

class TestNormalizeSql:
    def test_empty(self):
        assert _normalize_sql_for_display("") == ""

    def test_strips_whitespace(self):
        assert _normalize_sql_for_display("  SELECT 1  ") == "SELECT 1"

    def test_strips_semicolon(self):
        assert _normalize_sql_for_display("SELECT 1;") == "SELECT 1"

    def test_collapses_blank_lines(self):
        sql = "SELECT 1\n\n\n\nFROM t"
        result = _normalize_sql_for_display(sql)
        assert result == "SELECT 1\n\nFROM t"

    def test_dedents(self):
        sql = "    SELECT col\n    FROM table"
        result = _normalize_sql_for_display(sql)
        assert result == "SELECT col\nFROM table"

    def test_preserves_internal_indent(self):
        sql = "SELECT\n  col1,\n  col2\nFROM t"
        result = _normalize_sql_for_display(sql)
        assert "  col1" in result


# ── _truncate_sql ────────────────────────────────────────────────────────

class TestTruncateSql:
    def test_empty(self):
        assert _truncate_sql("") == ""

    def test_short_sql_unchanged(self):
        sql = "SELECT 1\nFROM t"
        assert _truncate_sql(sql, max_lines=15) == sql

    def test_truncates_long_sql(self):
        lines = [f"LINE {i}" for i in range(30)]
        sql = "\n".join(lines)
        result = _truncate_sql(sql, max_lines=5)
        assert result.endswith("-- ... (25 more lines)")
        assert result.count("\n") == 5  # 5 lines + truncation note

    def test_exact_limit(self):
        lines = [f"LINE {i}" for i in range(15)]
        sql = "\n".join(lines)
        assert _truncate_sql(sql, max_lines=15) == sql


# ── build_data_stamp ─────────────────────────────────────────────────────

class TestBuildDataStamp:
    def test_with_confidence(self):
        stamp = build_data_stamp(
            row_count=145000,
            date_range="Jan-Mar 2026",
            primary_table="ORDERS",
            confidence_grade="B",
            confidence_score=82,
        )
        assert stamp["one_liner"] == "[145K rows | Jan-Mar 2026 | ORDERS | Confidence: B (82/100)]"
        assert stamp["abbreviated"] == "145K | Jan-Mar 2026 | ORDERS | B (82)"
        assert stamp["no_validation"] == "[145K rows | Jan-Mar 2026 | ORDERS]"
        assert stamp["row_count"] == 145000
        assert stamp["row_count_formatted"] == "145K"
        assert stamp["confidence_grade"] == "B"
        assert stamp["confidence_score"] == 82

    def test_without_confidence(self):
        stamp = build_data_stamp(
            row_count=500,
            date_range="Q4 2025",
            primary_table="EVENTS",
        )
        assert stamp["one_liner"] == "[500 rows | Q4 2025 | EVENTS]"
        assert stamp["abbreviated"] == "500 | Q4 2025 | EVENTS"
        assert stamp["no_validation"] == "[500 rows | Q4 2025 | EVENTS]"
        assert stamp["confidence_grade"] is None
        assert stamp["confidence_score"] is None

    def test_large_row_count(self):
        stamp = build_data_stamp(
            row_count=2400000,
            date_range="2025",
            primary_table="TRANSACTIONS",
            confidence_grade="A",
            confidence_score=95,
        )
        assert "2.4M rows" in stamp["one_liner"]


# ── render_data_stamp ────────────────────────────────────────────────────

class TestRenderDataStamp:
    def test_full_level(self):
        stamp = build_data_stamp(145000, "Jan-Mar 2026", "ORDERS", "B", 82)
        assert render_data_stamp(stamp, "full") == stamp["one_liner"]

    def test_abbreviated_level(self):
        stamp = build_data_stamp(145000, "Jan-Mar 2026", "ORDERS", "B", 82)
        assert render_data_stamp(stamp, "abbreviated") == stamp["abbreviated"]

    def test_no_validation_level(self):
        stamp = build_data_stamp(145000, "Jan-Mar 2026", "ORDERS", "B", 82)
        assert render_data_stamp(stamp, "no_validation") == stamp["no_validation"]

    def test_default_is_full(self):
        stamp = build_data_stamp(145000, "Jan-Mar 2026", "ORDERS")
        assert render_data_stamp(stamp) == stamp["one_liner"]


# ── _extract_cv_summary ─────────────────────────────────────────────────

class TestExtractCvSummary:
    def test_type_d_preferred(self):
        verification = {
            "boundary": {"status": "PASS", "checks": ["non_negative"]},
            "parts_to_whole": {"status": "PASS", "diff_pct": 0.003},
            "algebraic_identity": {"status": "PASS", "diff_pct": 0.0001},
        }
        method, result, detail = _extract_cv_summary(verification)
        assert method == "Type D: Algebraic identity"
        assert result == "PASS"

    def test_type_b_when_no_cd(self):
        verification = {
            "boundary": {"status": "PASS", "checks": ["non_negative"]},
            "parts_to_whole": {"status": "WARN", "diff_pct": 0.08},
            "ratio_recompute": {"status": "N/A"},
            "algebraic_identity": {"status": "N/A"},
        }
        method, result, detail = _extract_cv_summary(verification)
        assert method == "Type B: Parts-to-whole"
        assert result == "WARN"

    def test_boundary_only(self):
        verification = {
            "boundary": {"status": "FAIL", "checks": ["non_negative", "percentage_bounds"]},
        }
        method, result, detail = _extract_cv_summary(verification)
        assert method == "Type A: Boundary check"
        assert result == "FAIL"
        assert "Boundary violation" in detail

    def test_no_checks(self):
        verification = {}
        method, result, detail = _extract_cv_summary(verification)
        assert method == "None"
        assert result == "N/A"


# ── build_provenance_blocks ──────────────────────────────────────────────

class TestBuildProvenanceBlocks:
    def test_basic_finding(self):
        findings = [{
            "finding_id": "F1",
            "finding_title": "Mobile converts at half the rate",
            "row_count": 50000,
            "date_range": "Jan-Mar 2026",
            "primary_table": "EVENTS",
            "sql": "SELECT device, COUNT(*) FROM events GROUP BY device;",
        }]
        blocks = build_provenance_blocks(findings)
        assert len(blocks) == 1
        b = blocks[0]
        assert b["finding_id"] == "F1"
        assert b["data_stamp"]["row_count"] == 50000
        assert b["data_stamp"]["confidence_grade"] is None
        assert b["sql"]["query_full"] == "SELECT device, COUNT(*) FROM events GROUP BY device"
        assert b["reproducibility"]["connection_type"] == "duckdb"

    def test_with_confidence(self):
        findings = [{
            "finding_id": "F1",
            "finding_title": "Test",
            "row_count": 1000,
            "date_range": "Q1",
            "primary_table": "T",
        }]
        confidence = {"grade": "A", "score": 92}
        blocks = build_provenance_blocks(findings, confidence_result=confidence)
        assert blocks[0]["data_stamp"]["confidence_grade"] == "A"
        assert blocks[0]["data_stamp"]["confidence_score"] == 92

    def test_with_cross_verification(self):
        findings = [{
            "finding_id": "C1",
            "finding_title": "Revenue is $2.4M",
            "row_count": 10000,
            "date_range": "2025",
            "primary_table": "ORDERS",
        }]
        cv_data = [{
            "claim_id": "C1",
            "verification": {
                "boundary": {"status": "PASS", "checks": ["non_negative"]},
                "parts_to_whole": {"status": "PASS", "diff_pct": 0.002},
            },
        }]
        blocks = build_provenance_blocks(findings, cross_verification=cv_data)
        assert blocks[0]["cross_verification"] is not None
        assert blocks[0]["cross_verification"]["verified"] is True
        assert blocks[0]["cross_verification"]["method"] == "Type B: Parts-to-whole"

    def test_multiple_findings(self):
        findings = [
            {"finding_id": f"F{i}", "finding_title": f"Finding {i}",
             "row_count": i * 1000, "date_range": "Q1", "primary_table": "T"}
            for i in range(1, 4)
        ]
        blocks = build_provenance_blocks(findings)
        assert len(blocks) == 3
        assert [b["finding_id"] for b in blocks] == ["F1", "F2", "F3"]

    def test_snowflake_connection(self):
        findings = [{
            "finding_id": "F1",
            "finding_title": "Test",
            "row_count": 100,
            "date_range": "Q1",
            "primary_table": "T",
        }]
        blocks = build_provenance_blocks(
            findings, connection_type="snowflake", database="ANALYTICS"
        )
        assert blocks[0]["reproducibility"]["connection_type"] == "snowflake"
        assert blocks[0]["reproducibility"]["database"] == "ANALYTICS"
        assert blocks[0]["reproducibility"]["deterministic"] is False

    def test_with_methodology(self):
        findings = [{
            "finding_id": "F1",
            "finding_title": "Test",
            "row_count": 100,
            "date_range": "Q1",
            "primary_table": "T",
            "methodology": {
                "approach": "segmented comparison",
                "aggregation": "SUM by segment",
                "filters": ["date >= '2026-01-01'"],
                "date_handling": "monthly, UTC",
            },
        }]
        blocks = build_provenance_blocks(findings)
        assert blocks[0]["methodology"] is not None
        assert blocks[0]["methodology"]["approach"] == "segmented comparison"

    def test_no_sql(self):
        findings = [{
            "finding_id": "F1",
            "finding_title": "Test",
            "row_count": 100,
            "date_range": "Q1",
            "primary_table": "T",
        }]
        blocks = build_provenance_blocks(findings)
        assert blocks[0]["sql"] is None

    def test_empty_findings(self):
        blocks = build_provenance_blocks([])
        assert blocks == []


# ── render_provenance_appendix ───────────────────────────────────────────

class TestRenderProvenanceAppendix:
    def test_basic_rendering(self):
        findings = [{
            "finding_id": "F1",
            "finding_title": "Mobile converts at half the rate",
            "row_count": 50000,
            "date_range": "Jan-Mar 2026",
            "primary_table": "EVENTS",
            "sql": "SELECT device, COUNT(*) FROM events GROUP BY device",
            "methodology": {
                "approach": "segmented comparison",
                "aggregation": "COUNT by device",
                "filters": [],
                "date_handling": "monthly",
            },
        }]
        blocks = build_provenance_blocks(findings)
        md = render_provenance_appendix(blocks[0])
        assert "### F1: Mobile converts at half the rate" in md
        assert "```sql" in md
        assert "**Methodology:** segmented comparison" in md

    def test_with_cv(self):
        findings = [{
            "finding_id": "F1",
            "finding_title": "Revenue total",
            "row_count": 1000,
            "date_range": "Q1",
            "primary_table": "ORDERS",
        }]
        cv = [{
            "claim_id": "F1",
            "verification": {
                "parts_to_whole": {"status": "PASS", "diff_pct": 0.001},
            },
        }]
        blocks = build_provenance_blocks(findings, cross_verification=cv)
        md = render_provenance_appendix(blocks[0])
        assert "Cross-verification" in md
        assert "Verified" in md

    def test_no_optional_fields(self):
        findings = [{
            "finding_id": "F1",
            "finding_title": "Simple finding",
            "row_count": 100,
            "date_range": "Q1",
            "primary_table": "T",
        }]
        blocks = build_provenance_blocks(findings)
        md = render_provenance_appendix(blocks[0])
        assert "### F1: Simple finding" in md
        assert "**Data:**" in md
        # Should not have SQL or methodology sections
        assert "```sql" not in md
        assert "**Methodology:**" not in md
