"""
Tests for .knowledge/ directory structure, dataset brain, metric schema,
and analysis archive.

Uses temporary directories (via conftest fixtures) instead of real dataset data.
Validates that the knowledge infrastructure helpers work correctly for
reading, writing, and listing YAML artifacts.
"""

import yaml
import pytest
from pathlib import Path

from helpers.pipeline.file_helpers import (
    atomic_write_yaml,
    safe_read_yaml,
    list_yaml_files,
    ensure_directory,
)


# ---------------------------------------------------------------------------
# 1. Knowledge Directory Structure
# ---------------------------------------------------------------------------

class TestKnowledgeDirectoryStructure:
    """Verify the tmp_knowledge_dir fixture creates the expected layout."""

    EXPECTED_SUBDIRS = [
        "datasets",
        "corrections",
        "learnings",
        "query-archaeology",
        "analyses",
        "global",
    ]

    def test_all_subdirectories_exist(self, tmp_knowledge_dir):
        for subdir in self.EXPECTED_SUBDIRS:
            path = tmp_knowledge_dir / subdir
            assert path.is_dir(), f"Expected subdirectory missing: {subdir}"

    def test_active_yaml_is_readable(self, tmp_knowledge_dir):
        active_path = tmp_knowledge_dir / "active.yaml"
        assert active_path.is_file(), "active.yaml should exist"
        data = yaml.safe_load(active_path.read_text())
        assert data is not None, "active.yaml should parse as valid YAML"

    def test_active_yaml_has_correct_keys(self, tmp_knowledge_dir):
        active_path = tmp_knowledge_dir / "active.yaml"
        data = yaml.safe_load(active_path.read_text())
        assert data["active_dataset"] == "test-dataset"
        assert data["active_organization"] == "test-org"

    def test_datasets_directory_is_initially_empty(self, tmp_knowledge_dir):
        datasets = tmp_knowledge_dir / "datasets"
        contents = list(datasets.iterdir())
        assert contents == [], "datasets/ should be empty before any writes"


# ---------------------------------------------------------------------------
# 2. Dataset Brain (manifest round-trip via file_helpers)
# ---------------------------------------------------------------------------

class TestDatasetBrain:
    """Write and read back a dataset manifest using file_helpers."""

    SAMPLE_MANIFEST = {
        "dataset_id": "test-dataset",
        "display_name": "Test Dataset",
        "connection": {
            "type": "local-csv",
            "path": "data/test/",
        },
        "tables": [
            {"name": "users", "row_count": 1000, "primary_key": "user_id"},
            {"name": "orders", "row_count": 5000, "primary_key": "order_id"},
            {"name": "events", "row_count": 50000, "primary_key": "event_id"},
        ],
        "created_at": "2026-01-15",
        "last_profiled": "2026-02-20",
    }

    def test_write_and_read_manifest(self, tmp_knowledge_dir):
        dataset_dir = ensure_directory(
            tmp_knowledge_dir / "datasets" / "test-dataset"
        )
        manifest_path = dataset_dir / "manifest.yaml"

        atomic_write_yaml(manifest_path, self.SAMPLE_MANIFEST)
        result = safe_read_yaml(manifest_path)

        assert result is not None, "manifest.yaml should be readable"
        assert result["dataset_id"] == "test-dataset"

    def test_manifest_connection_type(self, tmp_knowledge_dir):
        dataset_dir = ensure_directory(
            tmp_knowledge_dir / "datasets" / "test-dataset"
        )
        manifest_path = dataset_dir / "manifest.yaml"

        atomic_write_yaml(manifest_path, self.SAMPLE_MANIFEST)
        result = safe_read_yaml(manifest_path)

        assert result["connection"]["type"] == "local-csv"

    def test_manifest_tables_list(self, tmp_knowledge_dir):
        dataset_dir = ensure_directory(
            tmp_knowledge_dir / "datasets" / "test-dataset"
        )
        manifest_path = dataset_dir / "manifest.yaml"

        atomic_write_yaml(manifest_path, self.SAMPLE_MANIFEST)
        result = safe_read_yaml(manifest_path)

        table_names = [t["name"] for t in result["tables"]]
        assert table_names == ["users", "orders", "events"]
        assert result["tables"][0]["row_count"] == 1000

    def test_safe_read_yaml_returns_none_for_missing_file(self, tmp_knowledge_dir):
        result = safe_read_yaml(tmp_knowledge_dir / "datasets" / "nonexistent.yaml")
        assert result is None


# ---------------------------------------------------------------------------
# 3. Entity Index (via tmp_org_dir)
# ---------------------------------------------------------------------------

class TestEntityIndex:
    """Verify the entity-index.yaml fixture and alias resolution."""

    def test_entity_index_loads(self, tmp_org_dir):
        index_path = tmp_org_dir / "entities" / "entity-index.yaml"
        data = safe_read_yaml(index_path)
        assert data is not None, "entity-index.yaml should be loadable"
        assert "aliases" in data
        assert "entities" in data
        assert "relationships" in data

    def test_alias_count(self, tmp_org_dir):
        data = safe_read_yaml(tmp_org_dir / "entities" / "entity-index.yaml")
        assert len(data["aliases"]) == 10, "Expected 10 aliases"

    def test_alias_resolves_cvr(self, tmp_org_dir):
        data = safe_read_yaml(tmp_org_dir / "entities" / "entity-index.yaml")
        alias_entry = data["aliases"]["cvr"]
        assert alias_entry["entity"] == "conversion_rate"
        assert alias_entry["type"] == "metric"

    def test_alias_resolves_full_name(self, tmp_org_dir):
        data = safe_read_yaml(tmp_org_dir / "entities" / "entity-index.yaml")
        alias_entry = data["aliases"]["gross merchandise value"]
        assert alias_entry["entity"] == "gmv"

    def test_entity_count(self, tmp_org_dir):
        data = safe_read_yaml(tmp_org_dir / "entities" / "entity-index.yaml")
        assert len(data["entities"]) == 5, "Expected 5 entities"

    def test_entity_types(self, tmp_org_dir):
        data = safe_read_yaml(tmp_org_dir / "entities" / "entity-index.yaml")
        types = {e["type"] for e in data["entities"].values()}
        assert types == {"metric", "product"}

    def test_relationship_marketplace_metrics(self, tmp_org_dir):
        data = safe_read_yaml(tmp_org_dir / "entities" / "entity-index.yaml")
        mp_rel = data["relationships"]["marketplace"]
        assert "conversion_rate" in mp_rel["metrics"]
        assert "gmv" in mp_rel["metrics"]
        assert mp_rel["team"] == "commerce"

    def test_relationship_metric_to_product(self, tmp_org_dir):
        data = safe_read_yaml(tmp_org_dir / "entities" / "entity-index.yaml")
        cvr_rel = data["relationships"]["conversion_rate"]
        assert cvr_rel["product"] == "marketplace"


# ---------------------------------------------------------------------------
# 4. Analysis Archive
# ---------------------------------------------------------------------------

class TestAnalysisArchive:
    """Write, read, and list analysis records in the analyses directory."""

    SAMPLE_ANALYSIS = {
        "analysis_id": "analysis-2026-02-23-checkout-drop",
        "date": "2026-02-23",
        "question": "Why did checkout conversion drop 12% in February?",
        "dataset": "test-dataset",
        "findings_summary": "Mobile checkout latency increased 3x after Feb 10 deploy.",
        "confidence_grade": "B",
        "recommendations": [
            "Revert mobile checkout to pre-Feb-10 build",
            "Add latency monitoring to checkout flow",
        ],
        "artifacts": [
            "outputs/checkout-drop-analysis.html",
            "outputs/checkout-drop-deck.html",
        ],
    }

    def test_write_and_read_analysis(self, tmp_knowledge_dir):
        analyses_dir = tmp_knowledge_dir / "analyses"
        analysis_path = analyses_dir / "analysis-2026-02-23-checkout-drop.yaml"

        atomic_write_yaml(analysis_path, self.SAMPLE_ANALYSIS)
        result = safe_read_yaml(analysis_path)

        assert result is not None
        assert result["analysis_id"] == "analysis-2026-02-23-checkout-drop"
        assert result["date"] == "2026-02-23"
        assert result["confidence_grade"] == "B"

    def test_analysis_findings_summary(self, tmp_knowledge_dir):
        analyses_dir = tmp_knowledge_dir / "analyses"
        analysis_path = analyses_dir / "analysis-2026-02-23-checkout-drop.yaml"

        atomic_write_yaml(analysis_path, self.SAMPLE_ANALYSIS)
        result = safe_read_yaml(analysis_path)

        assert "mobile checkout latency" in result["findings_summary"].lower()

    def test_analysis_recommendations_structure(self, tmp_knowledge_dir):
        analyses_dir = tmp_knowledge_dir / "analyses"
        analysis_path = analyses_dir / "analysis-2026-02-23-checkout-drop.yaml"

        atomic_write_yaml(analysis_path, self.SAMPLE_ANALYSIS)
        result = safe_read_yaml(analysis_path)

        assert isinstance(result["recommendations"], list)
        assert len(result["recommendations"]) == 2

    def test_list_yaml_files_in_analyses(self, tmp_knowledge_dir):
        analyses_dir = tmp_knowledge_dir / "analyses"

        # Write two analysis files
        atomic_write_yaml(
            analyses_dir / "analysis-2026-02-20-activation.yaml",
            {"analysis_id": "activation", "date": "2026-02-20"},
        )
        atomic_write_yaml(
            analyses_dir / "analysis-2026-02-23-checkout.yaml",
            {"analysis_id": "checkout", "date": "2026-02-23"},
        )

        files = list_yaml_files(analyses_dir)
        assert len(files) == 2
        # list_yaml_files returns sorted by name
        assert files[0].name == "analysis-2026-02-20-activation.yaml"
        assert files[1].name == "analysis-2026-02-23-checkout.yaml"

    def test_list_yaml_files_empty_directory(self, tmp_knowledge_dir):
        files = list_yaml_files(tmp_knowledge_dir / "analyses")
        assert files == []

    def test_list_yaml_files_nonexistent_directory(self, tmp_knowledge_dir):
        files = list_yaml_files(tmp_knowledge_dir / "does-not-exist")
        assert files == []


# ---------------------------------------------------------------------------
# 5. Corrections Directory
# ---------------------------------------------------------------------------

class TestCorrections:
    """Write and read correction entries."""

    def test_write_and_read_correction(self, tmp_knowledge_dir):
        correction = {
            "correction_id": "corr-001",
            "date": "2026-02-23",
            "original_query": "SELECT COUNT(*) FROM orders",
            "issue": "Missing WHERE clause excluded cancelled orders",
            "corrected_query": "SELECT COUNT(*) FROM orders WHERE status != 'cancelled'",
            "impact": "Count was 15% higher than reality",
        }

        correction_path = tmp_knowledge_dir / "corrections" / "corr-001.yaml"
        atomic_write_yaml(correction_path, correction)
        result = safe_read_yaml(correction_path)

        assert result is not None
        assert result["correction_id"] == "corr-001"
        assert result["issue"] == "Missing WHERE clause excluded cancelled orders"
        assert "cancelled" in result["corrected_query"]

    def test_multiple_corrections_listed(self, tmp_knowledge_dir):
        corrections_dir = tmp_knowledge_dir / "corrections"

        for i in range(3):
            atomic_write_yaml(
                corrections_dir / f"corr-{i:03d}.yaml",
                {"correction_id": f"corr-{i:03d}", "date": "2026-02-23"},
            )

        files = list_yaml_files(corrections_dir)
        assert len(files) == 3


# ---------------------------------------------------------------------------
# 6. Glossary
# ---------------------------------------------------------------------------

class TestGlossary:
    """Load and verify the glossary from the org directory."""

    def test_glossary_loads(self, tmp_org_dir):
        glossary_path = tmp_org_dir / "business" / "glossary" / "terms.yaml"
        data = safe_read_yaml(glossary_path)
        assert data is not None
        assert "terms" in data

    def test_glossary_term_count(self, tmp_org_dir):
        data = safe_read_yaml(
            tmp_org_dir / "business" / "glossary" / "terms.yaml"
        )
        assert len(data["terms"]) == 2

    def test_glossary_term_definitions(self, tmp_org_dir):
        data = safe_read_yaml(
            tmp_org_dir / "business" / "glossary" / "terms.yaml"
        )
        terms_by_name = {t["term"]: t for t in data["terms"]}

        assert "GMV" in terms_by_name
        assert terms_by_name["GMV"]["definition"] == "Gross Merchandise Value"

        assert "Take Rate" in terms_by_name
        assert terms_by_name["Take Rate"]["definition"] == "Revenue / GMV"

    def test_glossary_aliases(self, tmp_org_dir):
        data = safe_read_yaml(
            tmp_org_dir / "business" / "glossary" / "terms.yaml"
        )
        terms_by_name = {t["term"]: t for t in data["terms"]}

        assert "gross merchandise value" in terms_by_name["GMV"]["aliases"]
        assert "commission rate" in terms_by_name["Take Rate"]["aliases"]
