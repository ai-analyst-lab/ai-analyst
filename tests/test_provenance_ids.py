"""Tests for the provenance ID infra (0.8a): analysis_id context, collision-free query_id,
analysis_id + result_value recorded on the query log entry."""
from __future__ import annotations

from helpers.knowledge import analysis_context as ac
from helpers.provenance.query_log import append_entry, read_log, set_log_dir


def test_analysis_context_create_stable_clear(tmp_path):
    assert ac.current_analysis_id(create=False, working_dir=tmp_path) is None
    aid = ac.current_analysis_id(create=True, working_dir=tmp_path)
    assert aid and aid.startswith("an_")
    # stable across calls (persisted)
    assert ac.current_analysis_id(create=False, working_dir=tmp_path) == aid
    ac.clear_analysis(working_dir=tmp_path)
    assert ac.current_analysis_id(create=False, working_dir=tmp_path) is None


def test_query_id_is_collision_free(tmp_path):
    set_log_dir(tmp_path)
    ids = {append_entry("ds", "2026-06-27", "auto-hook", 0, "p", f"select {i}")["query_id"]
           for i in range(300)}
    assert len(ids) == 300  # the old ms%100000 scheme collided under rapid/concurrent calls


def test_analysis_id_and_result_value_recorded(tmp_path):
    set_log_dir(tmp_path)
    e = append_entry("ds", "2026-06-27", "auto-hook", 0, "p", "select 1",
                     analysis_id="an_test", result_value=42.0)
    assert e["analysis_id"] == "an_test" and e["result_value"] == 42.0
    entries = read_log("ds", "2026-06-27")
    assert entries[-1]["analysis_id"] == "an_test"  # round-trips to disk
