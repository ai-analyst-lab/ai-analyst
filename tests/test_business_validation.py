"""Tests for helpers/validation/business_validation.py."""

import pytest
import pandas as pd
from pathlib import Path

from helpers.validation.business_validation import (
    load_metric_rules,
    load_guardrail_pairs,
    validate_against_knowledge,
)


class TestLoadMetricRules:
    def test_no_dataset_returns_empty(self):
        rules = load_metric_rules("nonexistent_dataset_xyz")
        assert rules == []

    def test_returns_list(self):
        result = load_metric_rules()
        assert isinstance(result, list)

    def test_with_yaml_files(self, tmp_path):
        """Create temporary metric YAML and verify loading."""
        metrics_dir = tmp_path / ".knowledge" / "datasets" / "test" / "metrics"
        metrics_dir.mkdir(parents=True)

        # Write a metric file
        metric_yaml = metrics_dir / "conversion_rate.yaml"
        metric_yaml.write_text(
            "name: conversion_rate\n"
            "display_name: Conversion Rate\n"
            "min_value: 0\n"
            "max_value: 1\n"
            "guardrails: [aov]\n"
        )

        # Monkey-patch the knowledge dir
        import helpers.validation.business_validation as bv
        original = bv._KNOWLEDGE_DIR
        bv._KNOWLEDGE_DIR = tmp_path / ".knowledge"
        try:
            rules = load_metric_rules("test")
            assert len(rules) == 1
            assert rules[0]["column"] == "conversion_rate"
            assert rules[0]["min"] == 0
            assert rules[0]["max"] == 1
        finally:
            bv._KNOWLEDGE_DIR = original


class TestLoadGuardrailPairs:
    def test_no_dataset_returns_empty(self):
        pairs = load_guardrail_pairs("nonexistent_dataset_xyz")
        assert pairs == []

    def test_returns_list(self):
        result = load_guardrail_pairs()
        assert isinstance(result, list)


class TestValidateAgainstKnowledge:
    def test_no_rules_returns_ok(self):
        df = pd.DataFrame({"a": [1, 2, 3]})
        result = validate_against_knowledge(df, dataset_id="nonexistent_xyz")
        assert result["ok"] is True
        assert result["rules_checked"] == 0

    def test_violations_detected(self, tmp_path):
        """Create rules and verify violation detection."""
        metrics_dir = tmp_path / ".knowledge" / "datasets" / "test" / "metrics"
        metrics_dir.mkdir(parents=True)
        (metrics_dir / "rate.yaml").write_text(
            "name: rate\nmin_value: 0\nmax_value: 1\n"
        )

        import helpers.validation.business_validation as bv
        original = bv._KNOWLEDGE_DIR
        bv._KNOWLEDGE_DIR = tmp_path / ".knowledge"
        try:
            df = pd.DataFrame({"rate": [0.5, 1.5, 0.3]})  # 1.5 is out of range
            result = validate_against_knowledge(df, dataset_id="test")
            assert result["ok"] is False
            assert len(result["violations"]) == 1
        finally:
            bv._KNOWLEDGE_DIR = original

    def test_valid_data_passes(self, tmp_path):
        metrics_dir = tmp_path / ".knowledge" / "datasets" / "test" / "metrics"
        metrics_dir.mkdir(parents=True)
        (metrics_dir / "rate.yaml").write_text(
            "name: rate\nmin_value: 0\nmax_value: 1\n"
        )

        import helpers.validation.business_validation as bv
        original = bv._KNOWLEDGE_DIR
        bv._KNOWLEDGE_DIR = tmp_path / ".knowledge"
        try:
            df = pd.DataFrame({"rate": [0.5, 0.8, 0.3]})
            result = validate_against_knowledge(df, dataset_id="test")
            assert result["ok"] is True
        finally:
            bv._KNOWLEDGE_DIR = original
