"""Tests for helpers.provenance.codex_validation — preflight detection + audit logging."""

import json
import pytest
from pathlib import Path

import helpers.provenance.codex_validation as cv


# =====================================================================
# Fixtures
# =====================================================================

@pytest.fixture
def tmp_plugin_cache(tmp_path, monkeypatch):
    """Point the plugin-cache lookup at an empty temp dir by default."""
    cache = tmp_path / "cache"
    cache.mkdir()
    monkeypatch.setattr(cv, "_PLUGIN_CACHE_DIR", cache)
    return cache


@pytest.fixture
def tmp_log_dir(tmp_path, monkeypatch):
    """Redirect the audit log to a temp dir."""
    log_dir = tmp_path / "codex-review"
    monkeypatch.setattr(cv, "_LOG_DIR", log_dir)
    return log_dir


@pytest.fixture
def no_auth_probe(monkeypatch):
    """Default auth to undetermined so --check tests are deterministic."""
    monkeypatch.setattr(cv, "_check_auth", lambda: None)


# =====================================================================
# check()
# =====================================================================

def test_check_all_present(tmp_plugin_cache, monkeypatch, no_auth_probe):
    (tmp_plugin_cache / cv._PLUGIN_NAME).mkdir()
    monkeypatch.setattr(cv.shutil, "which", lambda name: "/usr/bin/codex")

    result = cv.check()

    assert result["codex_cli"] is True
    assert result["plugin"] is True
    assert result["missing"] == []
    assert result["ready"] is True
    assert "proceed" in result["directive"].lower()


def test_check_codex_cli_absent(tmp_plugin_cache, monkeypatch, no_auth_probe):
    (tmp_plugin_cache / cv._PLUGIN_NAME).mkdir()
    monkeypatch.setattr(cv.shutil, "which", lambda name: None)

    result = cv.check()

    assert result["codex_cli"] is False
    assert "codex_cli" in result["missing"]


def test_check_plugin_absent(tmp_plugin_cache, monkeypatch, no_auth_probe):
    # cache dir exists but the openai-codex entry does not
    monkeypatch.setattr(cv.shutil, "which", lambda name: "/usr/bin/codex")

    result = cv.check()

    assert result["plugin"] is False
    assert "plugin" in result["missing"]


def test_check_not_ready_directive_says_stop(tmp_plugin_cache, monkeypatch, no_auth_probe):
    """When Codex is missing, the directive must forbid a Claude fallback."""
    monkeypatch.setattr(cv.shutil, "which", lambda name: None)  # no CLI

    result = cv.check()

    assert result["ready"] is False
    directive = result["directive"].lower()
    assert "stop" in directive
    assert "do not" in directive
    assert "claude" in directive  # explicitly names the forbidden fallback


def test_check_auth_false_adds_missing(tmp_plugin_cache, monkeypatch):
    (tmp_plugin_cache / cv._PLUGIN_NAME).mkdir()
    monkeypatch.setattr(cv.shutil, "which", lambda name: "/usr/bin/codex")
    monkeypatch.setattr(cv, "_check_auth", lambda: False)

    result = cv.check()

    assert result["auth"] is False
    assert "auth" in result["missing"]


def test_check_auth_none_not_missing(tmp_plugin_cache, monkeypatch):
    (tmp_plugin_cache / cv._PLUGIN_NAME).mkdir()
    monkeypatch.setattr(cv.shutil, "which", lambda name: "/usr/bin/codex")
    monkeypatch.setattr(cv, "_check_auth", lambda: None)

    result = cv.check()

    assert result["auth"] is None
    assert "auth" not in result["missing"]


def test_check_auth_probe_never_raises(monkeypatch):
    """_check_auth swallows subprocess failures and returns None."""
    monkeypatch.setattr(cv.shutil, "which", lambda name: "/usr/bin/codex")

    def boom(*a, **k):
        raise OSError("no such binary")

    monkeypatch.setattr(cv.subprocess, "run", boom)
    assert cv._check_auth() is None


def test_check_auth_clean_exit_is_true(monkeypatch):
    monkeypatch.setattr(cv.shutil, "which", lambda name: "/usr/bin/codex")

    class Proc:
        returncode = 0

    monkeypatch.setattr(cv.subprocess, "run", lambda *a, **k: Proc())
    assert cv._check_auth() is True


# =====================================================================
# log_run()
# =====================================================================

def _write_verdict(run_dir, findings, question="What's retention?"):
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "verdict.json").write_text(json.dumps({
        "question": question, "model": "codex", "findings": findings,
    }))


def test_log_run_appends_one_line(tmp_path, tmp_log_dir):
    run_dir = tmp_path / "run1"
    _write_verdict(run_dir, [
        {"name": "retention", "verdict": "AGREE"},
        {"name": "activation", "verdict": "DISAGREE"},
        {"name": "growth", "verdict": "PARTIAL"},
    ])

    entry = cv.log_run(run_dir)

    log_lines = (tmp_log_dir / "log.jsonl").read_text().splitlines()
    assert len(log_lines) == 1
    logged = json.loads(log_lines[0])
    assert logged == entry
    assert entry["n_findings"] == 3
    assert entry["agree"] == 1
    assert entry["disagree"] == 1
    assert entry["partial"] == 1


def test_log_run_creates_log_dir_if_absent(tmp_path, tmp_log_dir):
    assert not tmp_log_dir.exists()
    run_dir = tmp_path / "run1"
    _write_verdict(run_dir, [{"name": "x", "verdict": "AGREE"}])

    cv.log_run(run_dir)

    assert (tmp_log_dir / "log.jsonl").exists()


def test_log_run_appends_across_runs(tmp_path, tmp_log_dir):
    for i in range(3):
        run_dir = tmp_path / f"run{i}"
        _write_verdict(run_dir, [{"name": "x", "verdict": "AGREE"}])
        cv.log_run(run_dir)

    assert len((tmp_log_dir / "log.jsonl").read_text().splitlines()) == 3


def test_log_run_unknown_verdict_bucketed(tmp_path, tmp_log_dir):
    run_dir = tmp_path / "run1"
    _write_verdict(run_dir, [{"name": "x", "verdict": "MAYBE"}])

    entry = cv.log_run(run_dir)

    assert entry["unknown"] == 1
    assert entry["agree"] == 0


def test_log_run_missing_verdict_file_raises(tmp_path, tmp_log_dir):
    with pytest.raises(FileNotFoundError):
        cv.log_run(tmp_path / "nonexistent")


def test_log_run_malformed_json_raises_valueerror(tmp_path, tmp_log_dir):
    run_dir = tmp_path / "run1"
    run_dir.mkdir()
    (run_dir / "verdict.json").write_text("{not json")

    with pytest.raises(ValueError):
        cv.log_run(run_dir)


# =====================================================================
# CLI (main)
# =====================================================================

def test_main_check_returns_zero(capsys, tmp_plugin_cache, monkeypatch, no_auth_probe):
    monkeypatch.setattr(cv.shutil, "which", lambda name: "/usr/bin/codex")
    rc = cv.main(["--check"])
    assert rc == 0
    assert "codex_cli" in capsys.readouterr().out


def test_main_log_missing_dir_returns_one(capsys, tmp_path, tmp_log_dir):
    rc = cv.main(["--log", str(tmp_path / "nope")])
    assert rc == 1
    assert "error" in capsys.readouterr().err


def test_main_log_requires_argument(capsys):
    assert cv.main(["--log"]) == 2


def test_main_unknown_mode(capsys):
    assert cv.main(["--frobnicate"]) == 2


def test_main_no_args(capsys):
    assert cv.main([]) == 2
