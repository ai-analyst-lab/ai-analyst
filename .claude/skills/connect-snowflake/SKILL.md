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

This is distinct from `/setup-snowflake` (the first-time MCP wizard that installs
`uvx` + `snowflake-labs-mcp` and writes credentials). Use **this** skill when the
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

`.knowledge/active.yaml` currently has `use_remote: true`, so the persistent
opt-in is already set. Still set `AAP_USE_REMOTE=1` in the same shell command as
a belt-and-suspenders guard — and to make remote intent explicit/visible.

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

Always tell the user which source is live (Rule 9).

### Step 3 — Log every query (Rule 17)
`ConnectionManager.query()` **auto-logs** at execution by default — that covers
the requirement. If you query some other way (raw connector, MCP), log manually:
```bash
python3 scripts/log_query.py --dataset {active} --agent ad-hoc \
  --purpose "..." --sql "..." --result "..."
```

## Gotchas
- `export AAP_USE_REMOTE=1` and the `python3` call **must share one Bash
  command** (`&&`), or the flag is lost and you silently get DuckDB.
- **Do not trust `sessions.had_purchase` for Nov–Dec 2024** — derive purchases
  from `events.event_type = 'purchase_complete'` or by joining `orders` on
  `session_id`. See `.knowledge/datasets/{active}/quirks.md`.
- Ignore the LibreSSL / urllib3 / NotOpenSSL warnings — harmless. Suppress with
  `-W ignore` + `warnings.filterwarnings('ignore')` as shown.
- Requires `snowflake-connector-python` (installed on this machine).
- Credentials live in `.env` (6 keys: `SNOWFLAKE_ACCOUNT`, `SNOWFLAKE_USER`,
  `SNOWFLAKE_PASSWORD`, `SNOWFLAKE_WAREHOUSE`, `SNOWFLAKE_DATABASE`,
  `SNOWFLAKE_ROLE`). Gitignored. Never echo/cat them (Rule 16).

## To go back to local DuckDB
Unset the opt-in: `unset AAP_USE_REMOTE` for the shell, and/or set
`use_remote: false` in `.knowledge/active.yaml`. `connection_type` will then
report `duckdb`.
