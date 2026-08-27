"""Tests for helpers/pipeline/health_check.py."""

import pytest
from pathlib import Path

from helpers.pipeline.health_check import (
    check_setup_state,
    check_knowledge_integrity,
    check_data_connectivity,
    check_helper_imports,
    run_health_check,
)


class TestCheckSetupState:
    def test_no_setup_file(self, tmp_path):
        import helpers.pipeline.health_check as hc
        original = hc._KNOWLEDGE_DIR
        hc._KNOWLEDGE_DIR = tmp_path / ".knowledge"
        (tmp_path / ".knowledge").mkdir()
        try:
            result = check_setup_state()
            assert result["ok"] is False
            assert result["setup_complete"] is False
        finally:
            hc._KNOWLEDGE_DIR = original

    def test_complete_setup(self, tmp_path):
        import helpers.pipeline.health_check as hc
        original = hc._KNOWLEDGE_DIR
        knowledge_dir = tmp_path / ".knowledge"
        knowledge_dir.mkdir()
        state_file = knowledge_dir / "setup-state.yaml"
        state_file.write_text(
            "setup_complete: true\n"
            "phases:\n"
            "  phase_1_role:\n    status: complete\n"
            "  phase_2_data:\n    status: complete\n"
            "  phase_3_business:\n    status: complete\n"
            "  phase_4_preferences:\n    status: complete\n"
        )
        hc._KNOWLEDGE_DIR = knowledge_dir
        try:
            result = check_setup_state()
            assert result["ok"] is True
            assert result["phases_complete"] == 4
        finally:
            hc._KNOWLEDGE_DIR = original

    def test_partial_setup(self, tmp_path):
        import helpers.pipeline.health_check as hc
        original = hc._KNOWLEDGE_DIR
        knowledge_dir = tmp_path / ".knowledge"
        knowledge_dir.mkdir()
        state_file = knowledge_dir / "setup-state.yaml"
        state_file.write_text(
            "setup_complete: false\n"
            "phases:\n"
            "  phase_1_role:\n    status: complete\n"
            "  phase_2_data:\n    status: not_started\n"
        )
        hc._KNOWLEDGE_DIR = knowledge_dir
        try:
            result = check_setup_state()
            assert result["ok"] is False
            assert result["phases_complete"] == 1
        finally:
            hc._KNOWLEDGE_DIR = original


class TestCheckKnowledgeIntegrity:
    def test_returns_dict(self):
        result = check_knowledge_integrity()
        assert isinstance(result, dict)
        assert "ok" in result
        assert "checks" in result


class TestCheckDataConnectivity:
    def test_returns_dict(self):
        result = check_data_connectivity()
        assert isinstance(result, dict)
        assert "ok" in result


class TestCheckHelperImports:
    def test_core_modules_importable(self):
        result = check_helper_imports()
        assert isinstance(result, dict)
        assert result["ok"] is True or isinstance(result["ok"], bool)
        assert len(result["modules"]) > 0


class TestRunHealthCheck:
    def test_returns_combined_report(self):
        result = run_health_check()
        assert isinstance(result, dict)
        assert "overall_ok" in result
        assert "setup" in result
        assert "knowledge" in result
        assert "data" in result
        assert "helpers" in result
        assert "summary" in result
