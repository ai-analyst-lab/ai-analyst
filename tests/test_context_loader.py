"""Tests for helpers/knowledge/context_loader.py."""
from __future__ import annotations

import json
import os

import pytest
import yaml

from helpers.knowledge.context_loader import (
    LoadTier,
    estimate_tokens,
    load_multiple_tiered,
    load_tiered,
)


@pytest.fixture
def tmp_yaml(tmp_path):
    """Create a temporary YAML file."""
    data = {
        "glossary": [
            {"term": "Active User", "definition": "User with session in last 30d"},
            {"term": "Churn", "definition": "No activity for 60+ days"},
            {"term": "MRR", "definition": "Monthly recurring revenue"},
        ],
        "version": 1,
        "metadata": {"source": "test", "count": 3},
    }
    path = tmp_path / "test.yaml"
    with open(path, "w") as f:
        yaml.dump(data, f)
    return str(path)


@pytest.fixture
def tmp_json(tmp_path):
    """Create a temporary JSON file."""
    data = {"entries": [{"id": 1}, {"id": 2}], "total": 2}
    path = tmp_path / "test.json"
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    return str(path)


@pytest.fixture
def tmp_markdown(tmp_path):
    """Create a temporary Markdown file."""
    content = """# Glossary

## Terms

### Active User
A user with at least one session in the last 30 days.

### Churn
No activity for 60+ consecutive days.

## Metrics

### MRR
Monthly recurring revenue.
"""
    path = tmp_path / "test.md"
    path.write_text(content)
    return str(path)


@pytest.fixture
def tmp_text(tmp_path):
    """Create a temporary plain text file."""
    content = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5\n"
    path = tmp_path / "test.txt"
    path.write_text(content)
    return str(path)


class TestEstimateTokens:
    def test_empty_string(self):
        assert estimate_tokens("") == 0

    def test_short_string(self):
        result = estimate_tokens("hello")
        assert result >= 1

    def test_longer_string(self):
        text = "a" * 400  # ~100 tokens
        result = estimate_tokens(text)
        assert 90 <= result <= 110

    def test_minimum_one(self):
        assert estimate_tokens("a") == 1


class TestLoadTieredYAML:
    def test_summary_tier(self, tmp_yaml):
        result = load_tiered(tmp_yaml, tier=LoadTier.SUMMARY)
        assert "glossary" in result
        assert "3 items" in result

    def test_full_tier(self, tmp_yaml):
        result = load_tiered(tmp_yaml, tier=LoadTier.FULL)
        assert "Active User" in result

    def test_with_examples_tier(self, tmp_yaml):
        result = load_tiered(tmp_yaml, tier=LoadTier.WITH_EXAMPLES)
        assert "Active User" in result

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            load_tiered("/nonexistent/file.yaml")

    def test_truncation(self, tmp_yaml):
        result = load_tiered(tmp_yaml, tier=LoadTier.FULL, max_tokens=5)
        assert "truncated" in result


class TestLoadTieredJSON:
    def test_summary_tier(self, tmp_json):
        result = load_tiered(tmp_json, tier=LoadTier.SUMMARY)
        assert "entries" in result
        assert "2 items" in result

    def test_full_tier(self, tmp_json):
        result = load_tiered(tmp_json, tier=LoadTier.FULL)
        assert '"entries"' in result


class TestLoadTieredMarkdown:
    def test_summary_tier(self, tmp_markdown):
        result = load_tiered(tmp_markdown, tier=LoadTier.SUMMARY)
        assert "Markdown:" in result
        assert "sections" in result
        assert "# Glossary" in result

    def test_full_tier(self, tmp_markdown):
        result = load_tiered(tmp_markdown, tier=LoadTier.FULL)
        assert "Active User" in result


class TestLoadTieredText:
    def test_summary_tier(self, tmp_text):
        result = load_tiered(tmp_text, tier=LoadTier.SUMMARY)
        assert "5 lines" in result

    def test_full_tier(self, tmp_text):
        result = load_tiered(tmp_text, tier=LoadTier.FULL)
        assert "Line 1" in result


class TestLoadMultipleTiered:
    def test_multiple_files(self, tmp_yaml, tmp_json):
        results = load_multiple_tiered(
            [tmp_yaml, tmp_json],
            tier=LoadTier.SUMMARY,
            total_budget=400,
        )
        assert len(results) == 2
        assert tmp_yaml in results
        assert tmp_json in results

    def test_missing_file_handled(self, tmp_yaml):
        results = load_multiple_tiered(
            [tmp_yaml, "/nonexistent/file.yaml"],
            tier=LoadTier.FULL,
        )
        assert len(results) == 2
        assert "not found" in results["/nonexistent/file.yaml"]

    def test_empty_paths(self):
        results = load_multiple_tiered([], tier=LoadTier.FULL)
        assert results == {}


class TestLoadTierEnum:
    def test_three_tiers(self):
        assert len(LoadTier) == 3

    def test_values(self):
        assert LoadTier.SUMMARY.value == "summary"
        assert LoadTier.FULL.value == "full"
        assert LoadTier.WITH_EXAMPLES.value == "examples"
