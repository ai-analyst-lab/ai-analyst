"""Tests for the action logger — JSONL action logging + human-readable render.

Covers scripts/log_action.py (entry construction, append, read) and
scripts/render_action_log.py (markdown + HTML rendering).
"""

import json
from pathlib import Path

import pytest

from scripts.log_action import (
    build_entry,
    append_entry,
    read_log,
    action_log_path,
)
from scripts.render_action_log import to_markdown, to_html


# =====================================================================
# Fixtures — a couple of fake hook payloads / entries
# =====================================================================

FAKE_HOOKS = [
    {
        "session_id": "sess-1",
        "tool_name": "Bash",
        "tool_input": {"command": "echo hello world", "description": "Print a greeting"},
        "tool_response": {"stdout": "hello world\n", "stderr": "", "interrupted": False},
    },
    {
        "session_id": "sess-1",
        "tool_name": "Read",
        "tool_input": {"file_path": "/tmp/x/repo/helpers/provenance/query_log.py"},
        "tool_response": "line1\nline2\nline3\n",
    },
    {
        "session_id": "sess-1",
        "tool_name": "mcp__snowflake__run_snowflake_query",
        "tool_input": {"statement": "SELECT COUNT(*) FROM novamart.orders"},
        "tool_response": [{"COUNT": 3150000}],
    },
]


@pytest.fixture
def log_file(tmp_path):
    """Write the fake hook payloads as entries to a temp JSONL log."""
    path = tmp_path / "working" / "action_log_2026-06-26.jsonl"
    for hook in FAKE_HOOKS:
        append_entry(build_entry(hook), path)
    return path


# =====================================================================
# Path
# =====================================================================

def test_action_log_path_format(tmp_path):
    p = action_log_path("2026-06-26", tmp_path / "working")
    assert p.name == "action_log_2026-06-26.jsonl"
    assert p.parent.name == "working"


# =====================================================================
# Entry construction
# =====================================================================

def test_build_entry_bash():
    e = build_entry(FAKE_HOOKS[0])
    assert e["tool"] == "Bash"
    assert e["method"] == "shell"
    assert e["summary"] == "Print a greeting"
    assert e["inputs"] == "echo hello world"
    assert "hello world" in e["output_summary"]
    assert e["status"] == "success"
    assert "timestamp" in e


def test_build_entry_read():
    e = build_entry(FAKE_HOOKS[1])
    assert e["tool"] == "Read"
    assert e["method"] == "read"
    assert "query_log.py" in e["summary"]
    assert e["inputs"].endswith("query_log.py")


def test_build_entry_sql():
    e = build_entry(FAKE_HOOKS[2])
    assert e["method"] == "sql"
    assert "SELECT" in e["inputs"]
    assert "rows/items" in e["output_summary"]


def test_build_entry_tolerates_garbage():
    # Missing fields must not raise.
    e = build_entry({})
    assert e["tool"] == "unknown"
    assert "timestamp" in e


def test_long_input_is_truncated():
    big = "x" * 5000
    e = build_entry({"tool_name": "Bash", "tool_input": {"command": big}})
    assert len(e["inputs"]) < len(big)
    assert "chars]" in e["inputs"]


# =====================================================================
# Round-trip: JSONL parses
# =====================================================================

def test_jsonl_parses(log_file):
    # Every line must be valid JSON.
    raw_lines = [l for l in log_file.read_text().splitlines() if l.strip()]
    assert len(raw_lines) == 3
    for line in raw_lines:
        obj = json.loads(line)  # raises if malformed
        assert "tool" in obj and "timestamp" in obj


def test_read_log_round_trip(log_file):
    entries = read_log(log_file)
    assert len(entries) == 3
    assert [e["tool"] for e in entries] == [
        "Bash",
        "Read",
        "mcp__snowflake__run_snowflake_query",
    ]


def test_read_log_missing_file(tmp_path):
    assert read_log(tmp_path / "nope.jsonl") == []


# =====================================================================
# Rendering — markdown
# =====================================================================

def test_markdown_contains_entries(log_file):
    md = to_markdown(read_log(log_file), "2026-06-26")
    assert "Action log" in md
    assert "Print a greeting" in md      # Bash summary
    assert "echo hello world" in md      # Bash inputs
    assert "query_log.py" in md          # Read summary
    assert "SELECT COUNT(*) FROM novamart.orders" in md  # SQL inputs
    assert "3 actions recorded" in md


def test_markdown_empty():
    md = to_markdown([], "2026-06-26")
    assert "No actions logged" in md


# =====================================================================
# Rendering — HTML
# =====================================================================

def test_html_contains_entries(log_file):
    html = to_html(read_log(log_file), "2026-06-26")
    assert "<html" in html
    assert "Print a greeting" in html
    assert "echo hello world" in html
    assert "query_log.py" in html
    assert "3 actions recorded" in html


def test_html_escapes_markup():
    hook = {"tool_name": "Bash", "tool_input": {"command": "echo '<script>'"}}
    html = to_html([build_entry(hook)])
    assert "<script>" not in html        # raw tag must be escaped
    assert "&lt;script&gt;" in html
