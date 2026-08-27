"""Tests for helpers/pipeline/pipeline_state.py -- V1-to-V2 migration and version detection."""

from __future__ import annotations

import pytest
from datetime import datetime, timezone

from helpers.pipeline.pipeline_state import (
    detect_schema_version,
    is_v1_state,
    migrate_v1_to_v2,
)


# ---------------------------------------------------------------------------
# detect_schema_version
# ---------------------------------------------------------------------------

class TestDetectSchemaVersion:
    def test_v2_explicit(self):
        assert detect_schema_version({"schema_version": 2}) == 2

    def test_v2_higher(self):
        assert detect_schema_version({"schema_version": 3}) == 2

    def test_v1_missing_field(self):
        assert detect_schema_version({"pipeline_id": "abc"}) == 1

    def test_v1_version_one(self):
        assert detect_schema_version({"schema_version": 1}) == 1

    def test_v1_version_zero(self):
        assert detect_schema_version({"schema_version": 0}) == 1

    def test_v1_non_integer(self):
        assert detect_schema_version({"schema_version": "2"}) == 1

    def test_empty_dict(self):
        assert detect_schema_version({}) == 1


# ---------------------------------------------------------------------------
# is_v1_state
# ---------------------------------------------------------------------------

class TestIsV1State:
    def test_true_for_v1(self):
        assert is_v1_state({"pipeline_id": "2026-02-23T09:30:00Z"}) is True

    def test_false_for_v2(self):
        assert is_v1_state({"schema_version": 2, "agents": {}}) is False

    def test_true_for_empty(self):
        assert is_v1_state({}) is True


# ---------------------------------------------------------------------------
# migrate_v1_to_v2
# ---------------------------------------------------------------------------

class TestMigrateV1ToV2:
    """Core migration tests."""

    @pytest.fixture()
    def v1_state(self):
        """A realistic V1 pipeline state."""
        return {
            "pipeline_id": "2026-02-23T09:30:00Z",
            "current_step": 5,
            "question": "Why did activation drop?",
            "steps": {
                "1": {
                    "agent": "question-framing",
                    "status": "complete",
                    "output_files": ["outputs/question_brief_2026-02-23.md"],
                },
                "2": {
                    "agent": "hypothesis",
                    "status": "complete",
                    "output_files": [
                        "outputs/hypothesis_doc_2026-02-23.md",
                        "working/hypothesis_scratch.md",
                    ],
                },
                "3": {
                    "agent": "data-explorer",
                    "status": "running",
                    "output_files": [],
                },
                "4": {
                    "agent": "source-tieout",
                    "status": "pending",
                },
            },
        }

    def test_adds_schema_version(self, v1_state):
        result = migrate_v1_to_v2(v1_state, dataset="my_dataset")
        assert result["schema_version"] == 2

    def test_generates_run_id(self, v1_state):
        result = migrate_v1_to_v2(v1_state, dataset="my_dataset")
        assert result["run_id"] == "2026-02-23_my_dataset_why-did-activation-drop"

    def test_preserves_started_at(self, v1_state):
        result = migrate_v1_to_v2(v1_state, dataset="my_dataset")
        assert result["started_at"] == "2026-02-23T09:30:00Z"

    def test_sets_updated_at(self, v1_state):
        result = migrate_v1_to_v2(v1_state, dataset="my_dataset")
        assert "updated_at" in result
        # Should be a valid ISO datetime
        datetime.fromisoformat(result["updated_at"].replace("Z", "+00:00"))

    def test_sets_dataset(self, v1_state):
        result = migrate_v1_to_v2(v1_state, dataset="acme_data")
        assert result["dataset"] == "acme_data"

    def test_preserves_question(self, v1_state):
        result = migrate_v1_to_v2(v1_state, dataset="my_dataset")
        assert result["question"] == "Why did activation drop?"

    def test_converts_step_keys_to_agent_keys(self, v1_state):
        result = migrate_v1_to_v2(v1_state, dataset="my_dataset")
        agents = result["agents"]
        assert "question-framing" in agents
        assert "hypothesis" in agents
        assert "data-explorer" in agents
        assert "source-tieout" in agents
        # Numeric keys should not be present
        assert "1" not in agents
        assert "2" not in agents

    def test_preserves_status_values(self, v1_state):
        result = migrate_v1_to_v2(v1_state, dataset="my_dataset")
        agents = result["agents"]
        assert agents["question-framing"]["status"] == "complete"
        assert agents["hypothesis"]["status"] == "complete"
        assert agents["data-explorer"]["status"] == "running"
        assert agents["source-tieout"]["status"] == "pending"

    def test_takes_first_output_file(self, v1_state):
        result = migrate_v1_to_v2(v1_state, dataset="my_dataset")
        agents = result["agents"]
        assert agents["question-framing"]["output_file"] == "outputs/question_brief_2026-02-23.md"
        # hypothesis had two files — should take first
        assert agents["hypothesis"]["output_file"] == "outputs/hypothesis_doc_2026-02-23.md"

    def test_no_output_file_for_empty_list(self, v1_state):
        result = migrate_v1_to_v2(v1_state, dataset="my_dataset")
        assert "output_file" not in result["agents"]["data-explorer"]

    def test_no_output_file_for_pending(self, v1_state):
        result = migrate_v1_to_v2(v1_state, dataset="my_dataset")
        assert "output_file" not in result["agents"]["source-tieout"]

    def test_pipeline_status_paused_when_running_step(self, v1_state):
        """A V1 state with a running step means it was interrupted -> paused."""
        result = migrate_v1_to_v2(v1_state, dataset="my_dataset")
        assert result["status"] == "paused"


class TestMigrateV1ToV2EdgeCases:
    """Edge cases and error handling."""

    def test_noop_for_v2_state(self):
        """If state is already V2, return it unchanged."""
        v2 = {
            "schema_version": 2,
            "run_id": "2026-02-23_data_test",
            "agents": {"question-framing": {"status": "complete"}},
        }
        result = migrate_v1_to_v2(v2, dataset="data")
        assert result is v2  # Same object, not a copy

    def test_empty_steps(self):
        state = {"pipeline_id": "2026-02-23T09:30:00Z", "steps": {}}
        result = migrate_v1_to_v2(state, dataset="test")
        assert result["agents"] == {}
        assert result["schema_version"] == 2

    def test_missing_steps_key(self):
        state = {"pipeline_id": "2026-02-23T09:30:00Z"}
        result = migrate_v1_to_v2(state, dataset="test")
        assert result["agents"] == {}

    def test_default_dataset(self):
        state = {"pipeline_id": "2026-02-23T09:30:00Z", "steps": {}}
        result = migrate_v1_to_v2(state)
        assert result["dataset"] == "unknown"
        assert "unknown" in result["run_id"]

    def test_missing_pipeline_id(self):
        state = {"steps": {"1": {"agent": "question-framing", "status": "complete"}}}
        result = migrate_v1_to_v2(state, dataset="test")
        assert result["schema_version"] == 2
        assert "started_at" in result
        # run_id should still be generated (uses today's date)
        assert "test" in result["run_id"]

    def test_step_without_agent_key_is_skipped(self):
        state = {
            "pipeline_id": "2026-02-23T09:30:00Z",
            "steps": {
                "1": {"status": "complete"},  # Missing 'agent' key
                "2": {"agent": "hypothesis", "status": "complete"},
            },
        }
        result = migrate_v1_to_v2(state, dataset="test")
        assert "hypothesis" in result["agents"]
        assert len(result["agents"]) == 1

    def test_preserves_error_field(self):
        state = {
            "pipeline_id": "2026-02-23T09:30:00Z",
            "steps": {
                "1": {
                    "agent": "data-explorer",
                    "status": "failed",
                    "error": "Connection timeout",
                },
            },
        }
        result = migrate_v1_to_v2(state, dataset="test")
        assert result["agents"]["data-explorer"]["error"] == "Connection timeout"

    def test_preserves_timestamps_on_steps(self):
        state = {
            "pipeline_id": "2026-02-23T09:30:00Z",
            "steps": {
                "1": {
                    "agent": "question-framing",
                    "status": "complete",
                    "started_at": "2026-02-23T09:30:00Z",
                    "completed_at": "2026-02-23T09:32:00Z",
                    "output_files": ["outputs/qb.md"],
                },
            },
        }
        result = migrate_v1_to_v2(state, dataset="test")
        agent = result["agents"]["question-framing"]
        assert agent["started_at"] == "2026-02-23T09:30:00Z"
        assert agent["completed_at"] == "2026-02-23T09:32:00Z"

    def test_all_complete_gives_completed_status(self):
        state = {
            "pipeline_id": "2026-02-23T09:30:00Z",
            "steps": {
                "1": {"agent": "question-framing", "status": "complete"},
                "2": {"agent": "hypothesis", "status": "complete"},
            },
        }
        result = migrate_v1_to_v2(state, dataset="test")
        assert result["status"] == "completed"

    def test_failed_step_gives_failed_status(self):
        state = {
            "pipeline_id": "2026-02-23T09:30:00Z",
            "steps": {
                "1": {"agent": "question-framing", "status": "complete"},
                "2": {"agent": "hypothesis", "status": "failed"},
            },
        }
        result = migrate_v1_to_v2(state, dataset="test")
        assert result["status"] == "failed"

    def test_pending_steps_gives_running_status(self):
        state = {
            "pipeline_id": "2026-02-23T09:30:00Z",
            "steps": {
                "1": {"agent": "question-framing", "status": "complete"},
                "2": {"agent": "hypothesis", "status": "pending"},
            },
        }
        result = migrate_v1_to_v2(state, dataset="test")
        assert result["status"] == "running"

    def test_output_files_as_string(self):
        """Some V1 states might have output_files as a string instead of list."""
        state = {
            "pipeline_id": "2026-02-23T09:30:00Z",
            "steps": {
                "1": {
                    "agent": "question-framing",
                    "status": "complete",
                    "output_files": "outputs/question_brief.md",
                },
            },
        }
        result = migrate_v1_to_v2(state, dataset="test")
        assert result["agents"]["question-framing"]["output_file"] == "outputs/question_brief.md"

    def test_question_slug_truncated(self):
        """Long questions should produce a reasonably sized slug."""
        state = {
            "pipeline_id": "2026-02-23T09:30:00Z",
            "question": "What is the root cause of the extremely long and detailed issue "
                        "that spans multiple lines and categories of analysis?",
            "steps": {},
        }
        result = migrate_v1_to_v2(state, dataset="test")
        # Slug should be capped at 60 chars
        slug_part = result["run_id"].split("test_", 1)[1]
        assert len(slug_part) <= 60

    def test_mixed_complete_and_skipped(self):
        state = {
            "pipeline_id": "2026-02-23T09:30:00Z",
            "steps": {
                "1": {"agent": "question-framing", "status": "complete"},
                "2": {"agent": "hypothesis", "status": "skipped"},
            },
        }
        result = migrate_v1_to_v2(state, dataset="test")
        assert result["status"] == "completed"

    def test_degraded_step_preserves_status(self):
        state = {
            "pipeline_id": "2026-02-23T09:30:00Z",
            "steps": {
                "1": {
                    "agent": "opportunity-sizer",
                    "status": "degraded",
                    "error": "Insufficient data",
                },
            },
        }
        result = migrate_v1_to_v2(state, dataset="test")
        agent = result["agents"]["opportunity-sizer"]
        assert agent["status"] == "degraded"
        assert agent["error"] == "Insufficient data"
