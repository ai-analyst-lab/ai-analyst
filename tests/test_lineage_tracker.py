"""Tests for helpers/provenance/lineage_tracker.py — LineageTracker, get_tracker, track."""

import json
import os
import tempfile

import pytest

from helpers.provenance.lineage_tracker import LineageTracker, get_tracker, track
from helpers.provenance import lineage_tracker as lineage_module


class TestRecordAndChain:
    """Create tracker, record steps, verify lineage chain."""

    def test_three_step_chain(self):
        tracker = LineageTracker(output_dir=tempfile.mkdtemp())

        tracker.record(
            step=1,
            agent="data-explorer",
            inputs=["data/orders.csv", "data/users.csv"],
            outputs=["working/data_inventory.md"],
            metadata={"tables_scanned": 2},
        )
        tracker.record(
            step=2,
            agent="source-tieout",
            inputs=["working/data_inventory.md", "data/orders.csv"],
            outputs=["working/tieout_report.md"],
        )
        tracker.record(
            step=5,
            agent="descriptive-analytics",
            inputs=["working/tieout_report.md", "working/data_inventory.md"],
            outputs=["working/analysis_descriptive.md"],
            metadata={"row_count": 45000, "tables_used": ["orders", "users"]},
        )

        lineage = tracker.get_lineage()
        assert len(lineage) == 3
        assert lineage[0]["id"] == "lin_001"
        assert lineage[1]["id"] == "lin_002"
        assert lineage[2]["id"] == "lin_003"

    def test_first_entry_has_no_parents(self):
        tracker = LineageTracker(output_dir=tempfile.mkdtemp())
        tracker.record(step=1, agent="data-explorer",
                       inputs=["data/orders.csv"], outputs=["working/inventory.md"])
        assert tracker.get_lineage()[0]["parent_ids"] == []

    def test_parent_linking(self):
        tracker = LineageTracker(output_dir=tempfile.mkdtemp())
        tracker.record(step=1, agent="data-explorer",
                       inputs=["data/orders.csv"], outputs=["working/inventory.md"])
        tracker.record(step=2, agent="source-tieout",
                       inputs=["working/inventory.md", "data/orders.csv"],
                       outputs=["working/tieout.md"])
        tracker.record(step=5, agent="descriptive-analytics",
                       inputs=["working/tieout.md", "working/inventory.md"],
                       outputs=["working/analysis.md"])

        lineage = tracker.get_lineage()
        assert "lin_001" in lineage[1]["parent_ids"]
        assert "lin_001" in lineage[2]["parent_ids"]
        assert "lin_002" in lineage[2]["parent_ids"]

    def test_metadata_preserved(self):
        tracker = LineageTracker(output_dir=tempfile.mkdtemp())
        tracker.record(step=1, agent="data-explorer",
                       inputs=["data/orders.csv"], outputs=["working/inventory.md"],
                       metadata={"row_count": 45000})
        assert tracker.get_lineage()[0]["metadata"]["row_count"] == 45000

    def test_agent_name_preserved(self):
        tracker = LineageTracker(output_dir=tempfile.mkdtemp())
        tracker.record(step=1, agent="descriptive-analytics",
                       inputs=["data/orders.csv"], outputs=["working/analysis.md"])
        assert tracker.get_lineage()[0]["agent"] == "descriptive-analytics"

    def test_timestamp_present(self):
        tracker = LineageTracker(output_dir=tempfile.mkdtemp())
        tracker.record(step=1, agent="data-explorer",
                       inputs=["data/orders.csv"], outputs=["working/inventory.md"])
        ts = tracker.get_lineage()[0]["timestamp"]
        assert isinstance(ts, str) and len(ts) > 0


class TestGetLineageForOutput:
    def test_traces_full_ancestry(self):
        tracker = LineageTracker(output_dir=tempfile.mkdtemp())
        tracker.record(step=1, agent="data-explorer",
                       inputs=["data/orders.csv"], outputs=["working/inventory.md"])
        tracker.record(step=2, agent="source-tieout",
                       inputs=["working/inventory.md"], outputs=["working/tieout.md"])
        tracker.record(step=5, agent="descriptive-analytics",
                       inputs=["working/tieout.md"], outputs=["working/analysis.md"])

        chain = tracker.get_lineage_for_output("working/analysis.md")
        chain_ids = [e["id"] for e in chain]
        assert len(chain) == 3
        assert chain_ids[0] == "lin_003"
        assert "lin_002" in chain_ids
        assert "lin_001" in chain_ids

    def test_nonexistent_output_returns_empty(self):
        tracker = LineageTracker(output_dir=tempfile.mkdtemp())
        tracker.record(step=1, agent="data-explorer",
                       inputs=["data/orders.csv"], outputs=["working/inventory.md"])
        assert tracker.get_lineage_for_output("working/nonexistent.md") == []


class TestSaveLoadRoundtrip:
    def test_round_trip(self):
        tmp_dir = tempfile.mkdtemp()
        tracker = LineageTracker(output_dir=tmp_dir)
        tracker.record(step=1, agent="data-explorer",
                       inputs=["data/orders.csv"], outputs=["working/inventory.md"],
                       metadata={"tables": 5})
        tracker.record(step=2, agent="source-tieout",
                       inputs=["working/inventory.md"], outputs=["working/tieout.md"])
        tracker.save()

        tracker2 = LineageTracker(output_dir=tmp_dir)
        tracker2.load()
        lineage1 = tracker.get_lineage()
        lineage2 = tracker2.get_lineage()

        assert len(lineage2) == len(lineage1)
        assert [e["id"] for e in lineage2] == [e["id"] for e in lineage1]
        assert lineage2[0]["metadata"]["tables"] == 5
        assert lineage2[1]["parent_ids"] == lineage1[1]["parent_ids"]

    def test_json_file_on_disk(self):
        tmp_dir = tempfile.mkdtemp()
        tracker = LineageTracker(output_dir=tmp_dir)
        tracker.record(step=1, agent="data-explorer",
                       inputs=["data/orders.csv"], outputs=["working/inventory.md"])
        tracker.save()

        log_path = os.path.join(tmp_dir, "lineage.json")
        assert os.path.exists(log_path)
        with open(log_path) as f:
            raw = json.load(f)
        assert isinstance(raw, list)
        assert len(raw) == 1


class TestClear:
    def test_clear_resets(self):
        tracker = LineageTracker(output_dir=tempfile.mkdtemp())
        tracker.record(step=1, agent="data-explorer",
                       inputs=["data/orders.csv"], outputs=["working/inventory.md"])
        tracker.record(step=2, agent="source-tieout",
                       inputs=["working/inventory.md"], outputs=["working/tieout.md"])
        assert len(tracker.get_lineage()) == 2
        tracker.clear()
        assert len(tracker.get_lineage()) == 0

    def test_ids_restart_after_clear(self):
        tracker = LineageTracker(output_dir=tempfile.mkdtemp())
        tracker.record(step=1, agent="data-explorer",
                       inputs=["data/orders.csv"], outputs=["working/inventory.md"])
        tracker.clear()
        tracker.record(step=1, agent="fresh-start",
                       inputs=["data/new.csv"], outputs=["working/fresh.md"])
        assert tracker.get_lineage()[0]["id"] == "lin_001"


class TestSingletonTrack:
    def test_convenience_function(self):
        lineage_module._singleton_tracker = None
        tracker = get_tracker()
        assert isinstance(tracker, LineageTracker)
        assert len(tracker.get_lineage()) == 0

        track(step=1, agent="data-explorer",
              inputs=["data/orders.csv"], outputs=["working/inventory.md"])
        track(step=2, agent="source-tieout",
              inputs=["working/inventory.md"], outputs=["working/tieout.md"])

        singleton = get_tracker()
        assert singleton is tracker
        assert len(singleton.get_lineage()) == 2
        assert "lin_001" in singleton.get_lineage()[1]["parent_ids"]

        lineage_module._singleton_tracker = None
