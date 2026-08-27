"""
Cross-module integration tests for AI Analyst subsystem interactions.

Tests verify that modules compose correctly when used together,
not individual function behavior (that belongs in unit tests).
"""

import json
import pytest
import yaml

from helpers.knowledge.entity_resolver import load_entity_index, resolve_entity
from helpers.knowledge.business_context import load_business_context, get_glossary
from helpers.knowledge.archaeology_helpers import capture_cookbook_entry, search_cookbook
from helpers.pipeline.pipeline_state import migrate_v1_to_v2, detect_schema_version
from helpers.knowledge.context_loader import load_tiered, LoadTier
from helpers.pipeline.schema_migration import (
    CURRENT_VERSIONS,
    migrate_if_needed,
    register_migration,
    clear_registry,
)

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# 1. Entity Resolution + Business Context
# ---------------------------------------------------------------------------

class TestEntityResolutionWithBusinessContext:
    """Entity resolver should return results consistent with business context."""

    def test_resolved_entities_match_glossary(self, tmp_org_dir):
        """Entities resolved from a query should reference terms that exist
        in the business glossary loaded from the same org directory."""
        knowledge_dir = str(tmp_org_dir.parent.parent)

        # Place entity-index.yaml at org root so load_entity_index finds it
        import shutil
        src = tmp_org_dir / "entities" / "entity-index.yaml"
        shutil.copy(str(src), str(tmp_org_dir / "entity-index.yaml"))

        # Load through both subsystems from the same org
        entity_index = load_entity_index(
            org_id="test-org", knowledge_dir=knowledge_dir
        )
        glossary = get_glossary(
            org_id="test-org", knowledge_dir=knowledge_dir
        )
        context = load_business_context(
            org_id="test-org", knowledge_dir=knowledge_dir
        )

        # Resolve a query that mentions a glossary term
        matches = resolve_entity("What is our GMV trend?", entity_index)

        # The entity resolver must find GMV
        assert len(matches) >= 1
        gmv_match = next(m for m in matches if m["entity"] == "gmv")
        assert gmv_match["type"] == "metric"

        # The glossary must also know about GMV
        glossary_terms = {t["term"] for t in glossary}
        assert "GMV" in glossary_terms

        # Business context should report a valid org
        assert context["org_id"] == "test-org"


# ---------------------------------------------------------------------------
# 2. Archaeology Capture + Search round-trip
# ---------------------------------------------------------------------------

class TestArchaeologyRoundTrip:
    """Capturing a cookbook entry then searching for it must succeed."""

    def test_capture_then_search(self, tmp_path):
        """Capture a SQL cookbook entry, then search by title keyword and
        by tag -- both must return the captured entry."""
        arch_dir = str(tmp_path / "archaeology")

        entry_id = capture_cookbook_entry(
            title="Monthly active users by country",
            sql="SELECT country, COUNT(DISTINCT user_id) FROM events GROUP BY 1",
            dataset="analytics",
            tables=["events"],
            tags=["mau", "geo"],
            arch_dir=arch_dir,
        )

        assert entry_id == "CK-001"

        # Search by title keyword
        by_title = search_cookbook("active users", arch_dir=arch_dir)
        assert len(by_title) == 1
        assert by_title[0]["id"] == entry_id
        assert by_title[0]["sql"].startswith("SELECT country")

        # Search by tag
        by_tag = search_cookbook("geo", arch_dir=arch_dir)
        assert len(by_tag) == 1
        assert by_tag[0]["id"] == entry_id

        # Search miss returns empty
        assert search_cookbook("nonexistent", arch_dir=arch_dir) == []


# ---------------------------------------------------------------------------
# 3. Pipeline State Migration (V1 -> V2)
# ---------------------------------------------------------------------------

class TestPipelineStateMigration:
    """V1 pipeline state must migrate cleanly to V2 structure."""

    def test_v1_to_v2_preserves_agent_data(self):
        """Migrate a realistic V1 state and verify V2 structure,
        including run_id generation, status derivation, and agent entries."""
        v1_state = {
            "pipeline_id": "2025-06-15T10:30:00Z",
            "question": "Why did activation drop in Q3?",
            "steps": {
                "1": {
                    "agent": "question-framing",
                    "status": "complete",
                    "started_at": "2025-06-15T10:30:00Z",
                    "completed_at": "2025-06-15T10:31:00Z",
                    "output_files": ["working/question-brief.md"],
                },
                "2": {
                    "agent": "data-explorer",
                    "status": "complete",
                    "started_at": "2025-06-15T10:31:00Z",
                    "completed_at": "2025-06-15T10:35:00Z",
                    "output_files": ["working/data-inventory.md"],
                },
                "3": {
                    "agent": "descriptive-analytics",
                    "status": "running",
                    "started_at": "2025-06-15T10:35:00Z",
                },
            },
        }

        assert detect_schema_version(v1_state) == 1

        v2 = migrate_v1_to_v2(v1_state, dataset="product-db")

        assert detect_schema_version(v2) == 2
        assert v2["schema_version"] == 2
        assert v2["dataset"] == "product-db"
        assert "activation-drop" in v2["run_id"]

        # Agent entries preserved
        assert "question-framing" in v2["agents"]
        assert v2["agents"]["question-framing"]["status"] == "complete"
        assert v2["agents"]["question-framing"]["output_file"] == "working/question-brief.md"

        # Running step -> overall status paused (interrupted)
        assert v2["status"] == "paused"

        # Idempotent: migrating V2 returns it unchanged
        v2_again = migrate_v1_to_v2(v2, dataset="product-db")
        assert v2_again is v2


# ---------------------------------------------------------------------------
# 4. Context Loader Multi-Format
# ---------------------------------------------------------------------------

class TestContextLoaderMultiFormat:
    """load_tiered must handle YAML, JSON, and Markdown files with
    tier-appropriate detail levels."""

    def test_tiered_loading_across_formats(self, tmp_path):
        """Write YAML, JSON, and MD files, then load each at SUMMARY
        and FULL tiers, verifying content adapts to the tier."""
        # YAML file
        yaml_path = tmp_path / "glossary.yaml"
        yaml_path.write_text(yaml.dump({
            "terms": [
                {"term": "GMV", "definition": "Gross Merchandise Value"},
                {"term": "AOV", "definition": "Average Order Value"},
            ]
        }))

        # JSON file
        json_path = tmp_path / "config.json"
        json_path.write_text(json.dumps({
            "version": 2,
            "features": ["analytics", "forecasting", "exports"],
        }))

        # Markdown file
        md_path = tmp_path / "notes.md"
        md_path.write_text("# Analysis Notes\n## Overview\nSome details.\n## Methods\nMore info.\n")

        # SUMMARY tier -- structural overview, much shorter than raw
        yaml_summary = load_tiered(str(yaml_path), tier=LoadTier.SUMMARY)
        json_summary = load_tiered(str(json_path), tier=LoadTier.SUMMARY)
        md_summary = load_tiered(str(md_path), tier=LoadTier.SUMMARY)

        assert "terms" in yaml_summary
        assert "2 items" in yaml_summary
        assert "version" in json_summary
        assert "Markdown:" in md_summary
        assert "sections" in md_summary

        # FULL tier -- contains actual content
        yaml_full = load_tiered(str(yaml_path), tier=LoadTier.FULL)
        assert "GMV" in yaml_full
        assert "Average Order Value" in yaml_full

        json_full = load_tiered(str(json_path), tier=LoadTier.FULL)
        assert "forecasting" in json_full

        md_full = load_tiered(str(md_path), tier=LoadTier.FULL)
        assert "# Analysis Notes" in md_full


# ---------------------------------------------------------------------------
# 5. Schema Migration + Data Integrity
# ---------------------------------------------------------------------------

class TestSchemaMigrationDataIntegrity:
    """register_migration + migrate_if_needed must transform data correctly."""

    def test_registered_migration_transforms_data(self):
        """Register a v1->v2 migration for setup_state, apply it,
        and verify the transform ran and schema_version was bumped."""
        clear_registry()
        # Temporarily set target version to 2 so migration triggers
        original_version = CURRENT_VERSIONS["setup_state"]
        CURRENT_VERSIONS["setup_state"] = 2

        try:
            def migrate_setup_v1_to_v2(data):
                """Add a 'migrated' flag and normalize the phase keys."""
                result = dict(data)
                result["migrated_from_v1"] = True
                phases = result.get("phases", {})
                result["phases"] = {
                    k.lower().replace(" ", "_"): v for k, v in phases.items()
                }
                return result

            register_migration("setup_state", 1, 2, migrate_setup_v1_to_v2)

            original = {
                "schema_version": 1,
                "phases": {
                    "Data Connect": {"status": "complete"},
                    "Org Setup": {"status": "pending"},
                },
            }

            migrated = migrate_if_needed(original, "setup_state")

            assert migrated["schema_version"] == 2
            assert migrated["migrated_from_v1"] is True
            assert "data_connect" in migrated["phases"]
            assert "org_setup" in migrated["phases"]
            assert migrated["phases"]["data_connect"]["status"] == "complete"

            # Original is untouched (deepcopy inside migrate_if_needed)
            assert original["schema_version"] == 1
            assert "migrated_from_v1" not in original
        finally:
            CURRENT_VERSIONS["setup_state"] = original_version
            clear_registry()
