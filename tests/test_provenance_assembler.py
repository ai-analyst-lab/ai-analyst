"""Tests for helpers/provenance/provenance_assembler.py."""

from __future__ import annotations

import pytest

from helpers.provenance.provenance_assembler import (
    DataStamp,
    ProvenanceBlock,
    NOT_AVAILABLE,
    NOT_YET_WIRED_FIELDS,
    LIFECYCLE_FIELDS,
    SOURCE_TIER_HIERARCHY,
    TIER_GOVERNED,
    TIER_CURATED,
    TIER_RAW,
    build_data_stamp,
    build_full_footer,
    build_provenance_blocks,
    derive_source_tier,
    load_tier_metadata,
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


# ── build_full_footer ────────────────────────────────────────────────────

class TestBuildFullFooter:
    def _block(self):
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
        return build_provenance_blocks(findings, confidence_result={"grade": "B", "score": 82})[0]

    def test_includes_built_fields(self):
        md = build_full_footer(self._block())
        # Built fields stay live in the footer.
        assert "### F1: Mobile converts at half the rate" in md
        assert "```sql" in md
        assert "**Methodology:** segmented comparison" in md
        assert "Confidence: B (82/100)" in md

    def test_source_tier_reads_raw_for_novamart(self):
        # No governance metadata -> the honest tier is raw, never "not available".
        md = build_full_footer(self._block())
        assert "**Source tier:** raw - direct query" in md
        assert f"**Source tier:** {NOT_AVAILABLE}" not in md

    def test_owner_and_signals_stay_not_available(self):
        md = build_full_footer(self._block())
        assert f"**Owner:** {NOT_AVAILABLE}" in md
        assert f"**Signals:** {NOT_AVAILABLE}" in md
        # Freshness without dates also stays not available.
        assert f"**Freshness:** {NOT_AVAILABLE}" in md

    def test_placeholder_value_is_not_available(self):
        assert NOT_AVAILABLE == "not available"
        # Placeholders are never faked as zeros or empty values.
        assert NOT_AVAILABLE != "0"
        assert NOT_AVAILABLE != ""

    def test_all_four_fields_present(self):
        md = build_full_footer(self._block())
        # All four lifecycle fields render, in order, exactly once.
        labels = [label for label, _ in LIFECYCLE_FIELDS]
        assert labels == ["Source tier", "Owner", "Freshness", "Signals"]
        for label in labels:
            assert md.count(f"**{label}:**") == 1
        # The two genuinely-not-wired fields still show the placeholder.
        not_wired = [label for label, _ in NOT_YET_WIRED_FIELDS]
        assert not_wired == ["Owner", "Signals"]
        for label in not_wired:
            assert f"**{label}:** {NOT_AVAILABLE}" in md

    def test_source_tier_upgrades_with_governance_metadata(self):
        # When the touched table carries governance metadata, the tier upgrades.
        tier_metadata = {"EVENTS": TIER_GOVERNED}
        md = build_full_footer(self._block(), tier_metadata=tier_metadata)
        assert "**Source tier:** governed - certified source" in md

    def test_placeholders_follow_built_fields(self):
        md = build_full_footer(self._block())
        # The not-available block comes after the built appendix content.
        assert md.index("**Source tier:**") > md.index("### F1:")
        assert md.index("**Source tier:**") > md.index("```sql")

    def test_freshness_reads_real_color_when_last_verified_supplied(self):
        # With a last_verified date and today, Freshness reads the real color, not the placeholder.
        md = build_full_footer(self._block(), last_verified="2026-06-25", today="2026-06-26")
        assert f"**Freshness:** {NOT_AVAILABLE}" not in md
        assert "**Freshness:** green (verified 2026-06-25, 1d ago)" in md
        # Source tier reads a real (raw) tier; Owner and Signals stay not available.
        assert "**Source tier:** raw - direct query" in md
        assert f"**Owner:** {NOT_AVAILABLE}" in md
        assert f"**Signals:** {NOT_AVAILABLE}" in md

    def test_freshness_red_color_when_stale(self):
        md = build_full_footer(self._block(), last_verified="2026-01-01", today="2026-06-26")
        assert "**Freshness:** red (verified 2026-01-01," in md

    def test_freshness_falls_back_without_dates(self):
        # No last_verified -> Freshness stays not available (the existing behavior).
        md = build_full_footer(self._block())
        assert f"**Freshness:** {NOT_AVAILABLE}" in md

    def test_minimal_block_still_shows_placeholders(self):
        findings = [{
            "finding_id": "F1",
            "finding_title": "Simple finding",
            "row_count": 100,
            "date_range": "Q1",
            "primary_table": "T",
        }]
        block = build_provenance_blocks(findings)[0]
        md = build_full_footer(block)
        # Even with no SQL/methodology, all four lifecycle fields still render.
        assert "**Source tier:** raw - direct query" in md
        assert f"**Owner:** {NOT_AVAILABLE}" in md
        assert f"**Freshness:** {NOT_AVAILABLE}" in md
        assert f"**Signals:** {NOT_AVAILABLE}" in md


# ── derive_source_tier ───────────────────────────────────────────────────

class TestDeriveSourceTier:
    def test_raw_when_no_metadata(self):
        # The NovaMart case: tables touched, but no governance metadata at all.
        assert derive_source_tier(["ORDERS"]) == "raw - direct query"
        assert derive_source_tier(["ORDERS", "ORDER_ITEMS"], {}) == "raw - direct query"

    def test_raw_never_returns_not_available(self):
        assert derive_source_tier(["ORDERS"]) != NOT_AVAILABLE

    def test_no_tables_is_raw(self):
        assert derive_source_tier([]) == "raw - direct query"
        assert derive_source_tier(None) == "raw - direct query"

    def test_curated_tier(self):
        meta = {"ORDERS": TIER_CURATED}
        assert derive_source_tier(["ORDERS"], meta) == "curated - semantic-layer source"

    def test_governed_tier(self):
        meta = {"ORDERS": TIER_GOVERNED}
        assert derive_source_tier(["ORDERS"], meta) == "governed - certified source"

    def test_case_insensitive_table_match(self):
        meta = {"ORDERS": TIER_GOVERNED}
        assert derive_source_tier(["orders"], meta) == "governed - certified source"

    def test_floor_wins_mixed_tiers(self):
        # governed + curated -> curated is the floor (least governed).
        meta = {"ORDERS": TIER_GOVERNED, "EVENTS": TIER_CURATED}
        assert derive_source_tier(["ORDERS", "EVENTS"], meta) == "curated - semantic-layer source"

    def test_unlabeled_table_drags_to_raw(self):
        # One governed table, one with no metadata -> raw (only as governed as the weakest input).
        meta = {"ORDERS": TIER_GOVERNED}
        assert derive_source_tier(["ORDERS", "EVENTS"], meta) == "raw - direct query"

    def test_all_governed_stays_governed(self):
        meta = {"ORDERS": TIER_GOVERNED, "ORDER_ITEMS": TIER_GOVERNED}
        assert derive_source_tier(["ORDERS", "ORDER_ITEMS"], meta) == "governed - certified source"

    def test_hierarchy_constant_shape(self):
        # The hierarchy a lesson/slide mirrors: governed > curated > raw, most governed first.
        keys = [k for k, _label, _meaning in SOURCE_TIER_HIERARCHY]
        assert keys == ["governed", "curated", "raw"]
        labels = {k: label for k, label, _meaning in SOURCE_TIER_HIERARCHY}
        assert labels["raw"] == "raw - direct query"


# ── load_tier_metadata ───────────────────────────────────────────────────

class TestLoadTierMetadata:
    def test_empty_when_no_source_tier_field(self):
        # NovaMart's real shape: entities pin meaning/structure, no source_tier.
        entities = {"entities": [
            {"entity": "order", "logical_table": "orders",
             "base_table": "ANALYTICS_DB.SALES.ORDERS", "primary_key": "order_id"},
        ]}
        assert load_tier_metadata(entities) == {}

    def test_reads_governed_entity(self):
        entities = {"entities": [
            {"entity": "order", "logical_table": "orders",
             "base_table": "ANALYTICS_DB.SALES.ORDERS", "source_tier": "governed"},
        ]}
        meta = load_tier_metadata(entities)
        # All three names a query might log resolve to the tier (upper-cased).
        assert meta["ANALYTICS_DB.SALES.ORDERS"] == TIER_GOVERNED
        assert meta["ORDERS"] == TIER_GOVERNED
        assert meta["ORDER"] == TIER_GOVERNED

    def test_accepts_bare_list(self):
        entities = [{"entity": "order", "logical_table": "orders", "source_tier": "curated"}]
        meta = load_tier_metadata(entities)
        assert meta["ORDERS"] == TIER_CURATED

    def test_ignores_invalid_tier(self):
        entities = [{"entity": "order", "logical_table": "orders", "source_tier": "bogus"}]
        assert load_tier_metadata(entities) == {}

    def test_end_to_end_governed_footer(self):
        # Loader output feeds derive_source_tier and upgrades the footer.
        entities = [{"entity": "event", "logical_table": "events",
                     "base_table": "ANALYTICS_DB.SALES.EVENTS", "source_tier": "governed"}]
        meta = load_tier_metadata(entities)
        assert derive_source_tier(["EVENTS"], meta) == "governed - certified source"
