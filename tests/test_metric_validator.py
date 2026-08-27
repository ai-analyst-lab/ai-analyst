"""Tests for helpers/validation/metric_validator.py."""

import pytest
from pathlib import Path

from helpers.validation.metric_validator import (
    validate_metric_definition,
    validate_metric_file,
    validate_all_metrics,
    check_metric_value,
)


class TestValidateMetricDefinition:
    def test_valid_metric(self):
        metric = {
            "name": "conversion_rate",
            "display_name": "Conversion Rate",
            "definition": "Purchasers / Visitors",
            "sql_template": "COUNT(DISTINCT buyers) / COUNT(DISTINCT visitors)",
            "grain": "daily",
            "owner": "Growth",
        }
        result = validate_metric_definition(metric)
        assert result["ok"] is True
        assert len(result["errors"]) == 0

    def test_missing_required_fields(self):
        result = validate_metric_definition({"name": "test"})
        assert result["ok"] is False
        assert len(result["errors"]) >= 2

    def test_invalid_status(self):
        metric = {
            "name": "test",
            "display_name": "Test",
            "definition": "A test",
            "status": "invalid_status",
        }
        result = validate_metric_definition(metric)
        assert result["ok"] is False

    def test_min_gt_max_fails(self):
        metric = {
            "name": "test",
            "display_name": "Test",
            "definition": "A test",
            "min_value": 10,
            "max_value": 5,
        }
        result = validate_metric_definition(metric)
        assert result["ok"] is False

    def test_not_a_dict(self):
        result = validate_metric_definition("not a dict")
        assert result["ok"] is False


class TestValidateMetricFile:
    def test_file_not_found(self):
        result = validate_metric_file("/nonexistent/path.yaml")
        assert result["ok"] is False

    def test_valid_file(self, tmp_path):
        f = tmp_path / "metric.yaml"
        f.write_text(
            "name: test_metric\n"
            "display_name: Test Metric\n"
            "definition: A test metric\n"
        )
        result = validate_metric_file(f)
        assert result["ok"] is True
        assert result["metric_name"] == "test_metric"


class TestCheckMetricValue:
    def test_value_in_range(self):
        metric = {"min_value": 0, "max_value": 1}
        result = check_metric_value(0.5, metric)
        assert result["ok"] is True

    def test_value_out_of_range(self):
        metric = {"min_value": 0, "max_value": 1}
        result = check_metric_value(1.5, metric)
        assert len(result["warnings"]) > 0

    def test_none_value(self):
        result = check_metric_value(None, {})
        assert result["ok"] is True

    def test_non_numeric(self):
        result = check_metric_value("abc", {})
        assert result["ok"] is False


class TestValidateAllMetrics:
    def test_empty_dataset(self, tmp_path):
        result = validate_all_metrics("nonexistent", knowledge_dir=tmp_path)
        assert result["ok"] is True
        assert result["total"] == 0
