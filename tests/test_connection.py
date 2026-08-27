#!/usr/bin/env python3
"""Tests for the W0.2 connection fix.

Three bugs that stopped a person connecting just by talking to Claude:
  1. query() never opened the connection (fell through to a misleading error).
  2. the saved .env was never loaded, so $SNOWFLAKE_* expanded to blank.
  3. the Snowflake switch was only settable via a terminal env var.

Run: python3 tests/test_connection.py
"""
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import duckdb
from helpers.data.connection_manager import ConnectionManager
import helpers.data.data_helpers as dh

passed = failed = 0
def check(name, cond):
    global passed, failed
    if cond: passed += 1; print(f"  ok   {name}")
    else: failed += 1; print(f"  FAIL {name}")


def test_query_lazy_connects():
    """A fresh ConnectionManager().query() works with no explicit connect()."""
    with tempfile.TemporaryDirectory() as d:
        db = Path(d) / "t.duckdb"
        con = duckdb.connect(str(db)); con.execute("create table t as select 42 as n"); con.close()
        mgr = ConnectionManager(config={"type": "duckdb", "duckdb_path": str(db)})
        # deliberately do NOT call mgr.connect()
        df = mgr.query("select n from t")
        check("query() lazy-connects on duckdb (no explicit connect)", int(df.iloc[0, 0]) == 42)
        mgr.close()


def test_load_env_dotenv_wins():
    """.env wins over a stale shell variable (the bug that broke the live Snowflake auth)."""
    with tempfile.TemporaryDirectory() as d:
        envf = Path(d) / ".env"
        envf.write_text('SNOWFLAKE_USER="alice"\n# comment\nSTALE=fromfile\n')
        os.environ["STALE"] = "leftover_shell_value"   # simulate a stale shell var
        os.environ.pop("SNOWFLAKE_USER", None)
        orig_file, orig_loaded = dh._ENV_FILE, dh._env_loaded
        dh._ENV_FILE = envf; dh._env_loaded = False
        try:
            dh._load_env()
            check("_load_env loads a new var from .env", os.environ.get("SNOWFLAKE_USER") == "alice")
            check("_load_env: .env wins over a stale shell var", os.environ.get("STALE") == "fromfile")
        finally:
            dh._ENV_FILE, dh._env_loaded = orig_file, orig_loaded
            os.environ.pop("SNOWFLAKE_USER", None); os.environ.pop("STALE", None)


def test_remote_enabled_env_switch():
    orig = os.environ.get("AAP_USE_REMOTE")
    try:
        os.environ["AAP_USE_REMOTE"] = "1"
        check("_remote_enabled true when env var set", dh._remote_enabled() is True)
        os.environ.pop("AAP_USE_REMOTE", None)
        # with no env var, it reflects the persisted active.yaml flag (no terminal needed)
        check("_remote_enabled is a bool when env var unset", isinstance(dh._remote_enabled(), bool))
    finally:
        if orig is None: os.environ.pop("AAP_USE_REMOTE", None)
        else: os.environ["AAP_USE_REMOTE"] = orig


def test_default_is_local_duckdb():
    """Default (no remote opt-in) routes to local DuckDB, not Snowflake."""
    orig = os.environ.get("AAP_USE_REMOTE")
    os.environ.pop("AAP_USE_REMOTE", None)
    try:
        src = dh.detect_active_source()
        check("default source type is not a remote warehouse",
              src.get("type") in ("duckdb", "csv", "none", "motherduck"))
    finally:
        if orig is not None: os.environ["AAP_USE_REMOTE"] = orig


if __name__ == "__main__":
    print("test_connection:")
    test_query_lazy_connects()
    test_load_env_dotenv_wins()
    test_remote_enabled_env_switch()
    test_default_is_local_duckdb()
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
