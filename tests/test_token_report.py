"""Tests for scripts/token_report.py — per-skill token attribution from session transcripts."""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import token_report as tr  # noqa: E402


def _assistant(msg_id, usage, content=None, ts="2026-09-02T10:00:00.000Z", session="sess-1"):
    return {
        "type": "assistant",
        "timestamp": ts,
        "sessionId": session,
        "uuid": f"u-{msg_id}",
        "message": {
            "id": msg_id,
            "role": "assistant",
            "model": "claude-fable-5-1",
            "content": content or [{"type": "text", "text": "..."}],
            "usage": usage,
        },
    }


def _skill_call(name):
    return [{"type": "tool_use", "id": "toolu_1", "name": "Skill",
             "input": {"skill": name, "args": ""}}]


def _usage(inp, out, cache_read=0, cache_create=0):
    return {"input_tokens": inp, "output_tokens": out,
            "cache_read_input_tokens": cache_read,
            "cache_creation_input_tokens": cache_create}


def _write(tmp_path, name, records):
    p = tmp_path / name
    p.write_text("\n".join(json.dumps(r) for r in records) + "\n")
    return p


@pytest.fixture
def transcript(tmp_path):
    records = [
        {"type": "user", "timestamp": "2026-09-02T09:59:00.000Z", "sessionId": "sess-1",
         "message": {"role": "user", "content": "hi"}},
        # before any skill
        _assistant("m1", _usage(100, 50, cache_read=1000)),
        # invoke skill A; this message's own usage belongs to A
        _assistant("m2", _usage(10, 20, cache_read=2000), content=_skill_call("data-map")),
        # streamed continuation of m2: same id, same usage, must not double count
        _assistant("m2", _usage(10, 20, cache_read=2000)),
        _assistant("m3", _usage(5, 300, cache_read=3000, cache_create=400)),
        # switch to skill B
        _assistant("m4", _usage(7, 8), content=_skill_call("explore")),
        _assistant("m5", _usage(1, 2)),
        # non-assistant noise records are ignored
        {"type": "attachment", "timestamp": "2026-09-02T10:05:00.000Z", "sessionId": "sess-1"},
        {"type": "system", "timestamp": "2026-09-02T10:05:01.000Z", "sessionId": "sess-1"},
        "this is not json",
    ]
    return _write(tmp_path, "sess-1.jsonl", records)


def test_attribution_and_dedup(transcript):
    result = tr.parse_transcript(transcript)
    skills = result["skills"]
    assert result["session_id"] == "sess-1"
    assert result["messages"] == 5  # m1..m5, the duplicate m2 record counted once

    none = skills[tr.NO_SKILL]
    assert none["input"] == 100 and none["output"] == 50 and none["cache_read"] == 1000
    assert none["invocations"] == 0

    dm = skills["data-map"]
    assert dm["invocations"] == 1
    assert dm["input"] == 15 and dm["output"] == 320
    assert dm["cache_read"] == 5000 and dm["cache_creation"] == 400
    assert dm["messages"] == 2

    ex = skills["explore"]
    assert ex["invocations"] == 1
    assert ex["input"] == 8 and ex["output"] == 10


def test_cost_estimate_uses_rates():
    counts = {"input": 1_000_000, "output": 1_000_000, "cache_read": 1_000_000,
              "cache_creation": 1_000_000}
    assert tr.estimate_cost(counts) == pytest.approx(10 + 10 + 50 + 0.25)
    assert tr.estimate_cost(counts, {"input": 1, "output": 2, "cache_read": 3}) == pytest.approx(1 + 1 + 2 + 3)


def test_build_report_aggregates_across_sessions(tmp_path):
    a = _write(tmp_path, "a.jsonl", [
        _assistant("a1", _usage(10, 10), content=_skill_call("explore"), session="a"),
    ])
    b = _write(tmp_path, "b.jsonl", [
        _assistant("b1", _usage(20, 20), content=_skill_call("explore"), session="b",
                   ts="2026-09-03T10:00:00.000Z"),
    ])
    report = tr.build_report([tr.parse_transcript(a), tr.parse_transcript(b)])
    explore = next(r for r in report["skills"] if r["skill"] == "explore")
    assert explore["invocations"] == 2
    assert explore["sessions"] == 2
    assert explore["input"] == 30 and explore["output"] == 30
    assert report["total"]["sessions"] == 2
    assert report["total"]["output"] == 30


def test_since_filter_skips_old_sessions(tmp_path):
    old = _write(tmp_path, "old.jsonl", [
        _assistant("o1", _usage(10, 10), ts="2026-08-01T00:00:00.000Z", session="old"),
    ])
    since = datetime(2026, 9, 1, tzinfo=timezone.utc)
    result = tr.parse_transcript(old, since=since)
    assert result["skipped"] is True
    assert result["skills"] == {}
    report = tr.build_report([result])
    assert report["total"]["sessions"] == 0


def test_render_text_prints_counts_not_content(transcript):
    report = tr.build_report([tr.parse_transcript(transcript)])
    text = tr.render_text(report)
    assert "data-map" in text and "explore" in text and tr.NO_SKILL in text
    assert "By session (1)" in text
    # Only counts are rendered: no message text, no user prompt text.
    assert "..." not in text and "hi" not in text.split()


def test_cli_json_and_missing_dir(tmp_path, capsys, transcript):
    rc = tr.main(["--project-dir", str(tmp_path), "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert {r["skill"] for r in payload["skills"]} == {tr.NO_SKILL, "data-map", "explore"}

    rc = tr.main(["--project-dir", str(tmp_path / "nowhere")])
    assert rc == 1


def test_default_project_dir_mangles_repo_path(tmp_path):
    repo = tmp_path / "some" / "repo"
    repo.mkdir(parents=True)
    d = tr.default_project_dir(repo)
    assert d.parent.name == "projects"
    assert d.name == str(repo.resolve()).replace("/", "-")
