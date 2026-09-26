"""Regression tests for two connection bugs found in testing on 2026-09-25.

1. ConnectionManager._load_config ignored its dataset_id argument, so a run that asked
   for a local dataset could land on the active remote one.
2. The repo .env's AAP_USE_REMOTE overrode the shell, so `AAP_USE_REMOTE=0` on the
   command line could not switch remote off. Behavior switches (AAP_*) now follow standard
   dotenv precedence (shell wins); credentials keep .env-wins (see test_connection.py).
"""
import duckdb
import pytest
import yaml

import helpers.data.data_helpers as dh
from helpers.data.connection_manager import ConnectionManager


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    """A throwaway repo root with two datasets: an active remote one and a local DuckDB one."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(dh, "_REPO_ROOT", tmp_path)
    monkeypatch.setattr(dh, "_ENV_FILE", tmp_path / ".env")
    monkeypatch.setattr(dh, "_env_loaded", False)
    monkeypatch.setattr(dh, "_dotenv_keys", set(), raising=False)
    monkeypatch.delenv("AAP_USE_REMOTE", raising=False)

    kdir = tmp_path / ".knowledge"
    db = tmp_path / "local.duckdb"
    con = duckdb.connect(str(db))
    con.execute("create table orders as select 7 as n")
    con.close()

    (kdir / "datasets" / "remote_ds").mkdir(parents=True)
    (kdir / "datasets" / "remote_ds" / "manifest.yaml").write_text(yaml.safe_dump({
        "display_name": "Remote",
        "connection_type": "snowflake",
        "connection": {"type": "snowflake", "schema": "PUBLIC"},
        "local_data": {"duckdb": str(db)},
    }))
    (kdir / "datasets" / "local_ds").mkdir(parents=True)
    (kdir / "datasets" / "local_ds" / "manifest.yaml").write_text(yaml.safe_dump({
        "display_name": "Local",
        "connection": {"type": "duckdb"},
        "local_data": {"duckdb": str(db)},
    }))
    (kdir / "active.yaml").write_text(
        yaml.safe_dump({"active_dataset": "remote_ds", "use_remote": True}))
    return tmp_path


# --- Bug 1: dataset_id is honoured -------------------------------------------------------

def test_load_config_honours_dataset_id_over_active_remote(workspace, monkeypatch):
    monkeypatch.setenv("AAP_USE_REMOTE", "1")
    cfg = ConnectionManager._load_config("local_ds")
    assert cfg["dataset_id"] == "local_ds"
    assert cfg["type"] == "duckdb"


def test_connection_manager_with_dataset_id_queries_local(workspace, monkeypatch):
    monkeypatch.setenv("AAP_USE_REMOTE", "1")
    mgr = ConnectionManager(dataset_id="local_ds")
    try:
        assert mgr.dataset_id == "local_ds"
        assert int(mgr.query("select n from orders").iloc[0, 0]) == 7
    finally:
        mgr.close()


def test_load_config_without_dataset_id_uses_active(workspace, monkeypatch):
    monkeypatch.setenv("AAP_USE_REMOTE", "1")
    cfg = ConnectionManager._load_config()
    assert cfg["dataset_id"] == "remote_ds"
    assert cfg["type"] == "snowflake"


def test_load_config_unknown_dataset_id_raises(workspace):
    with pytest.raises(RuntimeError, match="not_there"):
        ConnectionManager._load_config("not_there")


# --- Bug 2: shell AAP_USE_REMOTE beats .env ----------------------------------------------

def test_shell_off_switch_beats_dotenv_and_active_yaml(workspace, monkeypatch):
    (workspace / ".env").write_text("AAP_USE_REMOTE=1\n")
    monkeypatch.setenv("AAP_USE_REMOTE", "0")
    src = dh.detect_active_source()
    assert dh.os.environ["AAP_USE_REMOTE"] == "0"
    assert dh._remote_enabled() is False
    assert src["source"] == "remote_ds"
    assert src["type"] == "duckdb"


def test_dotenv_switch_applies_when_shell_unset(workspace):
    (workspace / ".env").write_text("AAP_USE_REMOTE=1\n")
    (workspace / ".knowledge" / "active.yaml").write_text(
        yaml.safe_dump({"active_dataset": "remote_ds", "use_remote": False}))
    try:
        dh._load_env()
        assert dh.os.environ["AAP_USE_REMOTE"] == "1"
        assert dh._remote_enabled() is True
    finally:
        dh.os.environ.pop("AAP_USE_REMOTE", None)


def test_dotenv_zero_does_not_cancel_persisted_opt_in(workspace):
    """A .env default of 0 must not undo the connect flow's use_remote: true."""
    (workspace / ".env").write_text("AAP_USE_REMOTE=0\n")
    try:
        dh._load_env()
        assert dh._remote_enabled() is True
    finally:
        dh.os.environ.pop("AAP_USE_REMOTE", None)


def test_credentials_still_dotenv_wins(workspace, monkeypatch):
    (workspace / ".env").write_text("SNOWFLAKE_USER=fromfile\n")
    monkeypatch.setenv("SNOWFLAKE_USER", "stale_shell_value")
    dh._load_env()
    assert dh.os.environ["SNOWFLAKE_USER"] == "fromfile"
