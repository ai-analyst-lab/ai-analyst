"""Tests for helpers/knowledge/entity_resolver.py -- entity resolution and disambiguation."""
from __future__ import annotations

import yaml
import pytest
from pathlib import Path

from helpers.knowledge.entity_resolver import (
    load_entity_index,
    resolve_entity,
    build_entity_index,
    format_disambiguation,
)


# ---------------------------------------------------------------------------
# Helpers -- tiny YAML writers for temp org structures
# ---------------------------------------------------------------------------

def _write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        yaml.dump(data, f, default_flow_style=False)


def _make_entity_index_yaml() -> dict:
    """Minimal entity-index.yaml content for tests."""
    return {
        "entities": {
            "conversion_rate": {"type": "metric", "display_name": "Conversion Rate"},
            "checkout": {"type": "product", "display_name": "Checkout"},
        },
        "aliases": {
            "cvr": {"entity": "conversion_rate", "type": "metric"},
            "conversion rate": {"entity": "conversion_rate", "type": "metric"},
            "checkout": {"entity": "checkout", "type": "product"},
        },
    }


# ===================================================================
# TestLoadEntityIndex
# ===================================================================

class TestLoadEntityIndex:
    """load_entity_index: org discovery, YAML loading, and fallback build."""

    def test_no_org_directory_returns_empty(self, tmp_path):
        """No organizations/ dir at all -> empty dict."""
        result = load_entity_index(knowledge_dir=str(tmp_path))
        assert result == {}

    def test_loads_entity_index_yaml(self, tmp_path):
        """Org with entity-index.yaml -> returns entities and aliases."""
        org = tmp_path / "organizations" / "acme"
        org.mkdir(parents=True)
        _write_yaml(org / "entity-index.yaml", _make_entity_index_yaml())

        result = load_entity_index(org_id="acme", knowledge_dir=str(tmp_path))

        assert "entities" in result
        assert "aliases" in result
        assert "conversion_rate" in result["entities"]
        # aliases are lowercased
        assert "cvr" in result["aliases"]

    def test_falls_back_to_build_when_no_index_yaml(self, tmp_path):
        """Org dir exists but no entity-index.yaml -- builds from business files."""
        org = tmp_path / "organizations" / "acme"
        _write_yaml(org / "business" / "glossary" / "terms.yaml", {
            "terms": [{"term": "GMV", "definition": "Gross Merchandise Value"}],
        })

        result = load_entity_index(org_id="acme", knowledge_dir=str(tmp_path))

        assert "entities" in result
        assert "gmv" in result["entities"]

    def test_auto_detect_skips_example(self, tmp_path):
        """Auto-detect org_id skips _example and picks the real org."""
        orgs = tmp_path / "organizations"
        (orgs / "_example").mkdir(parents=True)
        real_org = orgs / "beta"
        real_org.mkdir(parents=True)
        _write_yaml(real_org / "entity-index.yaml", _make_entity_index_yaml())

        result = load_entity_index(org_id=None, knowledge_dir=str(tmp_path))

        assert "entities" in result
        assert "conversion_rate" in result["entities"]


# ===================================================================
# TestResolveEntity
# ===================================================================

class TestResolveEntity:
    """resolve_entity: alias matching, ordering, case, longest-match."""

    @pytest.fixture()
    def index(self) -> dict:
        return {
            "entities": {
                "conversion_rate": {"type": "metric", "display_name": "Conversion Rate"},
                "cart_abandonment_rate": {"type": "metric", "display_name": "Cart Abandonment Rate"},
                "checkout": {"type": "product", "display_name": "Checkout"},
                "cart": {"type": "product", "display_name": "Cart"},
            },
            "aliases": {
                "cvr": {"entity": "conversion_rate", "type": "metric"},
                "conversion rate": {"entity": "conversion_rate", "type": "metric"},
                "cart abandonment rate": {"entity": "cart_abandonment_rate", "type": "metric"},
                "cart": {"entity": "cart", "type": "product"},
                "checkout": {"entity": "checkout", "type": "product"},
            },
        }

    def test_known_alias_returns_match(self, index):
        matches = resolve_entity("What is our cvr?", index)
        assert len(matches) == 1
        hit = matches[0]
        assert hit["entity"] == "conversion_rate"
        assert hit["type"] == "metric"
        assert hit["confidence"] > 0

    def test_no_matches_returns_empty(self, index):
        assert resolve_entity("How is the weather today?", index) == []

    def test_multiple_matches_sorted_by_position(self, index):
        matches = resolve_entity("Compare cvr and checkout performance", index)
        assert len(matches) == 2
        assert matches[0]["entity"] == "conversion_rate"  # cvr appears first
        assert matches[1]["entity"] == "checkout"

    def test_case_insensitive(self, index):
        matches = resolve_entity("Our CVR is dropping", index)
        assert len(matches) == 1
        assert matches[0]["entity"] == "conversion_rate"

    def test_longest_match_wins(self, index):
        """'cart abandonment rate' should match before 'cart'."""
        matches = resolve_entity("What is the cart abandonment rate?", index)
        entities = [m["entity"] for m in matches]
        assert "cart_abandonment_rate" in entities
        # 'cart' should NOT appear as a separate match since it's consumed by the longer alias
        assert "cart" not in entities


# ===================================================================
# TestBuildEntityIndex
# ===================================================================

class TestBuildEntityIndex:
    """build_entity_index: constructs index from business source files."""

    def test_build_from_glossary(self, tmp_path):
        _write_yaml(tmp_path / "business" / "glossary" / "terms.yaml", {
            "terms": [
                {"term": "GMV", "definition": "Gross Merchandise Value",
                 "aliases": ["gross merchandise value"]},
                {"term": "Take Rate", "definition": "Revenue / GMV"},
            ],
        })

        result = build_entity_index(tmp_path)

        assert "gmv" in result["entities"]
        assert result["entities"]["gmv"]["type"] == "term"
        assert "gmv" in result["aliases"]
        assert "gross merchandise value" in result["aliases"]
        assert "take_rate" in result["entities"]

    def test_build_from_products(self, tmp_path):
        _write_yaml(tmp_path / "business" / "products" / "index.yaml", {
            "products": [
                {"name": "Marketplace", "description": "Main marketplace"},
                {"name": "Search", "description": "Search product"},
            ],
        })

        result = build_entity_index(tmp_path)

        assert "marketplace" in result["entities"]
        assert result["entities"]["marketplace"]["type"] == "product"
        assert "search" in result["aliases"]

    def test_build_from_metrics(self, tmp_path):
        _write_yaml(tmp_path / "business" / "metrics" / "index.yaml", {
            "metrics": [
                {"name": "conversion_rate", "display_name": "Conversion Rate",
                 "definition": "Orders / Sessions"},
            ],
        })

        result = build_entity_index(tmp_path)

        assert "conversion_rate" in result["entities"]
        assert result["entities"]["conversion_rate"]["type"] == "metric"
        # both the key and display name should be aliases
        assert "conversion_rate" in result["aliases"]
        assert "conversion rate" in result["aliases"]

    def test_empty_org_dir_returns_valid_structure(self, tmp_path):
        """No business files at all -> valid dict with empty entities/aliases."""
        result = build_entity_index(tmp_path)

        assert result == {"entities": {}, "aliases": {}}


# ===================================================================
# TestFormatDisambiguation
# ===================================================================

class TestFormatDisambiguation:
    """format_disambiguation: human-readable match formatting."""

    def test_empty_matches_returns_empty_string(self):
        assert format_disambiguation([]) == ""

    def test_single_match_formatted(self):
        matches = [{"matched_text": "cvr", "entity": "conversion_rate",
                     "type": "metric", "confidence": 0.8}]
        result = format_disambiguation(matches)
        assert result == "Resolved: 'cvr' -> conversion_rate (metric)"

    def test_multiple_matches_formatted(self):
        matches = [
            {"matched_text": "cvr", "entity": "conversion_rate",
             "type": "metric", "confidence": 0.8},
            {"matched_text": "checkout", "entity": "checkout",
             "type": "product", "confidence": 1.0},
        ]
        result = format_disambiguation(matches)
        assert result.startswith("Resolved: ")
        assert "'cvr' -> conversion_rate (metric)" in result
        assert "'checkout' -> checkout (product)" in result
        assert ", " in result
