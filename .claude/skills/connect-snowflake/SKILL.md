---
name: connect-snowflake
description: >-
  Query the live/remote Snowflake warehouse instead of the local practice copy. Use when the
  user says "connect to snowflake", "use the live data", "go remote", "query the warehouse",
  or asks "is this hitting snowflake or duckdb?". Assumes credentials already exist (first-time
  setup is /setup-snowflake); opts into remote via ConnectionManager and verifies the
  connection type before any query runs.
---

# Skill: Connect to Live Snowflake

## Purpose
Run queries against the **live Snowflake** warehouse — not the local
DuckDB practice copy. This is the runbook for "actually go remote." Credentials
and config already exist; this skill is about *opting into remote and verifying
you landed there*.

This is distinct from `/setup-snowflake` (the first-time wizard that collects the
connection fields, stores the approved credential in `.env`, and verifies the native
ConnectionManager session). Use **this** skill when the
warehouse is already configured and you just want to query the live data through
`ConnectionManager`.

## When to Use
Trigger on any request to use the live/remote Snowflake data, e.g.:
- "connect to snowflake", "query snowflake", "use the live data / live warehouse"
- "run this against snowflake / the real data / production", "go remote"
- "is this hitting snowflake or duckdb?", "query the live tables"
- Any analysis where the user explicitly wants live warehouse numbers rather than
  the local DuckDB practice snapshot

## How the repo decides local vs. remote
`detect_active_source()` (in `helpers/data/data_helpers.py`) defaults to the **local
DuckDB** copy even though the active dataset declares
`connection_type: snowflake`. It only goes remote when you **opt in**, via either:
- **Env flag (per-shell):** `AAP_USE_REMOTE=1` (also accepts `true` / `yes`), OR
- **Persisted flag:** `use_remote: true` in `.knowledge/active.yaml`

Set `use_remote: true` in `.knowledge/active.yaml` for a persistent opt-in, and set
`AAP_USE_REMOTE=1` in the same shell command as `python3` as a belt-and-suspenders guard.
To confirm you actually landed on the warehouse (not the local fallback), call
`ConnectionManager.verify_remote()`: it returns `{"remote": bool, "identity": {account, warehouse,
database, schema, version}, "reason": ...}` from Snowflake's own session context functions. Treat
`remote: False` as "you are NOT on Snowflake" and fix the reason before querying.

## Instructions

### Step 1 — Run through ConnectionManager with remote opted in
`ConnectionManager` auto-loads `.env`, expands the `$SNOWFLAKE_*` placeholders
from the manifest, and lazy-connects. **The `export` must be in the same Bash
call as the `python3`** — shell env does not persist between separate tool calls.

```bash
export AAP_USE_REMOTE=1 && python3 -W ignore -c "
import warnings; warnings.filterwarnings('ignore')
from helpers.data.connection_manager import ConnectionManager
mgr = ConnectionManager()
print('backend:', mgr.connection_type)   # MUST print 'snowflake'
df = mgr.query('SELECT event_type, COUNT(*) n FROM events GROUP BY event_type ORDER BY n DESC')
print(df.to_string(index=False))
mgr.close()
"
```

Tables are **unqualified** in your configured schema (e.g. `events`, `orders`,
`sessions`, `users`, `promotions`, `products`). Use Snowflake dialect:
`DATE_TRUNC('month', col)`, etc. — or `get_dialect("snowflake")` from
`helpers/data/sql_dialect.py`.

### Step 2 — Verify you're actually on Snowflake (not the DuckDB fallback)
Before trusting any number, confirm:
- `mgr.connection_type` returns **`snowflake`** (if it prints `duckdb`, the
  opt-in didn't take — re-check that `export AAP_USE_REMOTE=1` ran in the *same*
  command).
- A `SELECT CURRENT_ACCOUNT(), CURRENT_WAREHOUSE(), CURRENT_DATABASE(), CURRENT_SCHEMA()`
  returns the account, warehouse, database, and schema from **your own connection
  config** (`.env` / `connection_templates/`) — compare against what you expect,
  never assume.

Always tell the user which source is live.

### Step 3 — Log every query
`ConnectionManager.query()` **auto-logs** at execution by default — that covers
the requirement. If you query some other way (raw connector, MCP), log manually:
```bash
python3 scripts/log_query.py --dataset {active} --agent ad-hoc \
  --purpose "..." --sql "..." --result "..."
```

## Gotchas
- `export AAP_USE_REMOTE=1` and the `python3` call **must share one Bash
  command** (`&&`), or the flag is lost and you silently get DuckDB.
- Read `.knowledge/datasets/{active}/quirks.md` before trusting edge columns.
- Ignore the LibreSSL / urllib3 / NotOpenSSL warnings — harmless. Suppress with
  `-W ignore` + `warnings.filterwarnings('ignore')` as shown.
- Requires `snowflake-connector-python` (`pip install -e ".[warehouses]"`; see the
  /setup-snowflake prerequisite).
- A PAT lives in `.env` as `SNOWFLAKE_TOKEN`; a legacy password uses
  `SNOWFLAKE_PASSWORD`. Account, user, warehouse, database, schema, and role live in the dataset
  manifest. Never echo or cat `.env`.

## To go back to local DuckDB
Unset the opt-in: `unset AAP_USE_REMOTE` for the shell, and/or set
`use_remote: false` in `.knowledge/active.yaml`. `connection_type` will then
report `duckdb`.
