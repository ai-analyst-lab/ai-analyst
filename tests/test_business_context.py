"""Tests for helpers/knowledge/business_context.py -- org discovery, context loading, getters, summary."""

from __future__ import annotations

import yaml
import pytest

from helpers.knowledge.business_context import (
    _find_org_id,
    get_business_summary,
    get_glossary,
    get_metrics,
    get_objectives,
    get_products,
    get_teams,
    load_business_context,
)


# ---------------------------------------------------------------------------
# Helpers — build temp org directory trees
# ---------------------------------------------------------------------------


def _write_yaml(path, data):
    """Write a dict as YAML to *path*, creating parents as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))


def _make_org(tmp_path, org_name="mycompany", *, manifest=None, index=None,
              glossary=None, products=None, metrics=None,
              objectives=None, teams=None):
    """Scaffold an organization directory under tmp_path/.knowledge/organizations/."""
    org_dir = tmp_path / "organizations" / org_name
    biz_dir = org_dir / "business"
    biz_dir.mkdir(parents=True)

    _write_yaml(org_dir / "manifest.yaml", manifest or {
        "organization": "My Company",
        "industry": "fintech",
        "description": "Online payment processing platform",
    })

    if index is not None:
        _write_yaml(biz_dir / "index.yaml", index)

    if glossary is not None:
        _write_yaml(biz_dir / "glossary" / "terms.yaml", glossary)
    if products is not None:
        _write_yaml(biz_dir / "products" / "index.yaml", products)
    if metrics is not None:
        _write_yaml(biz_dir / "metrics" / "index.yaml", metrics)
    if objectives is not None:
        _write_yaml(biz_dir / "objectives" / "index.yaml", objectives)
    if teams is not None:
        _write_yaml(biz_dir / "teams" / "index.yaml", teams)

    return str(tmp_path)


# ---------------------------------------------------------------------------
# TestFindOrgId
# ---------------------------------------------------------------------------


class TestFindOrgId:
    def test_no_orgs_directory(self, tmp_path):
        """No organizations/ dir at all -> None."""
        assert _find_org_id(str(tmp_path)) is None

    def test_only_example_dir(self, tmp_path):
        """Underscore-prefixed dirs like _example are skipped."""
        (tmp_path / "organizations" / "_example").mkdir(parents=True)
        assert _find_org_id(str(tmp_path)) is None

    def test_real_org_present(self, tmp_path):
        """A non-prefixed directory is returned as the org id."""
        (tmp_path / "organizations" / "acme").mkdir(parents=True)
        assert _find_org_id(str(tmp_path)) == "acme"


# ---------------------------------------------------------------------------
# TestLoadBusinessContext
# ---------------------------------------------------------------------------


class TestLoadBusinessContext:
    def test_no_org_returns_empty(self, tmp_path):
        ctx = load_business_context(knowledge_dir=str(tmp_path))
        assert ctx == {}

    def test_org_with_manifest(self, tmp_path):
        kdir = _make_org(tmp_path)
        ctx = load_business_context(knowledge_dir=kdir)
        assert ctx["org_id"] == "mycompany"
        assert ctx["company"] == "My Company"
        assert ctx["industry"] == "fintech"
        assert ctx["domain"] == "Online payment processing platform"

    def test_org_with_manifest_and_index(self, tmp_path):
        kdir = _make_org(tmp_path, index={
            "sections": {
                "glossary": "glossary/terms.yaml",
                "products": "products/index.yaml",
            }
        })
        ctx = load_business_context(knowledge_dir=kdir)
        assert sorted(ctx["sections"]) == ["glossary", "products"]

    def test_org_without_index_has_empty_sections(self, tmp_path):
        kdir = _make_org(tmp_path)
        ctx = load_business_context(knowledge_dir=kdir)
        assert ctx["sections"] == []


# ---------------------------------------------------------------------------
# TestGetters
# ---------------------------------------------------------------------------


class TestGetters:
    def test_get_glossary_with_terms(self, tmp_path):
        kdir = _make_org(tmp_path, glossary={
            "terms": [
                {"term": "churn", "definition": "Customer stops paying"},
                {"term": "MRR", "definition": "Monthly recurring revenue"},
            ]
        })
        result = get_glossary(knowledge_dir=kdir)
        assert len(result) == 2
        assert result[0]["term"] == "churn"

    def test_get_products_empty(self, tmp_path):
        kdir = _make_org(tmp_path, products={"products": []})
        assert get_products(knowledge_dir=kdir) == []

    def test_get_metrics_no_file(self, tmp_path):
        kdir = _make_org(tmp_path)  # no metrics file created
        assert get_metrics(knowledge_dir=kdir) == []

    def test_get_teams_with_entries(self, tmp_path):
        kdir = _make_org(tmp_path, teams={
            "teams": [
                {"name": "Growth", "focus": "Acquisition"},
                {"name": "Platform", "focus": "Infrastructure"},
            ]
        })
        result = get_teams(knowledge_dir=kdir)
        assert len(result) == 2
        assert result[1]["name"] == "Platform"

    def test_get_objectives_with_entries(self, tmp_path):
        kdir = _make_org(tmp_path, objectives={
            "objectives": [
                {"objective": "Increase retention", "quarter": "Q1 2026"},
            ]
        })
        result = get_objectives(knowledge_dir=kdir)
        assert len(result) == 1
        assert result[0]["objective"] == "Increase retention"


# ---------------------------------------------------------------------------
# TestGetBusinessSummary
# ---------------------------------------------------------------------------


class TestGetBusinessSummary:
    def test_no_org_returns_setup_prompt(self, tmp_path):
        summary = get_business_summary(knowledge_dir=str(tmp_path))
        assert "No business context" in summary
        assert "/setup" in summary

    def test_org_with_populated_collections(self, tmp_path):
        kdir = _make_org(
            tmp_path,
            products={"products": [{"name": "App"}]},
            metrics={"metrics": [{"name": "dau"}, {"name": "mau"}]},
            objectives={"objectives": [{"objective": "Grow"}]},
            glossary={"terms": [{"term": "LTV"}, {"term": "CAC"}, {"term": "ARPU"}]},
            teams={"teams": [{"name": "Growth"}]},
        )
        summary = get_business_summary(knowledge_dir=kdir)
        assert "My Company" in summary
        assert "fintech" in summary
        assert "1 product" in summary
        assert "2 metrics" in summary
        assert "1 OKR" in summary
        assert "3 glossary terms" in summary
        assert "1 team" in summary

    def test_org_with_empty_collections(self, tmp_path):
        kdir = _make_org(
            tmp_path,
            products={"products": []},
            metrics={"metrics": []},
            objectives={"objectives": []},
            glossary={"terms": []},
            teams={"teams": []},
        )
        summary = get_business_summary(knowledge_dir=kdir)
        assert "My Company" in summary
        assert "fintech" in summary
        # Zero-count collections are excluded from the detail string
        assert "product" not in summary
        assert "metric" not in summary
