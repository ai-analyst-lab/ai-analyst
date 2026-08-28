---
name: setup-snowflake
description: >-
  First-time Snowflake setup wizard for the NATIVE ConnectionManager path (the connection the
  analyst actually queries through, with auto-logged provenance). Prompts for every connection
  field, writes credentials to .env, registers the dataset, and VERIFIES the session is live on
  the warehouse before declaring success. Use when the user says "set up snowflake", "connect to
  snowflake", "configure the warehouse", or is routed here from /connect-data. For day-to-day
  remote querying after setup, use connect-snowflake. An optional Snowflake MCP server (for
  interactive ad-hoc queries) is covered in the appendix.
---

# Skill: Setup Snowflake

## Purpose
Guided first-time Snowflake setup for the **native `ConnectionManager` path** — the connection the
AI Analyst uses for every query, so every result is traced and logged. This wizard collects the
connection details, writes credentials safely, registers the dataset, and then **proves the session
is actually on the warehouse** (not the local practice copy) before it will report success.

This is deliberately native-first. The old MCP server (`snowflake-labs-mcp` via `uvx`) is a separate,
optional tool for interactive ad-hoc queries and is kept in the Appendix. The analyst does not query
through the MCP, so setting up only the MCP leaves the analyst unconnected. Set up the native path
first.

## When to Use
- `/setup-snowflake`, "set up snowflake", "connect to snowflake", "I have a snowflake account"
- Routed here from `/connect-data` when the user selects Snowflake

## Prerequisite: the driver
The native path needs `snowflake-connector-python`. Check it and install if missing:
```bash
python3 -c "import snowflake.connector; print('driver OK')" || pip install snowflake-connector-python
```
(It also ships in the `warehouses` extra: `pip install -e ".[warehouses]"`.)

## Step 1: Collect the connection details
The repo ships blank, so ask for **every** field, one question at a time. In a class the instructor
will read these out; leave each empty until the user gives it. Collect:

1. **Account identifier** — e.g. `ORGNAME-ACCOUNTNAME` (Snowsight: your name, bottom-left, then
   Account, then View account details).
2. **Username**
3. **Password** — "Paste it and I will write it straight to `.env`, never to the terminal."
4. **Warehouse** — the compute warehouse to run on (e.g. `ANALYST_WH`).
5. **Database**
6. **Schema** — default `PUBLIC` if they do not say.
7. **Role** — optional; skip if they do not use one.
8. **A short dataset name** for this connection (used as the dataset id, lowercase-hyphen).

**Credential security (non-negotiable):**
- Never echo, print, or log the password; never pass it as a CLI arg (visible in `ps`).
- Write secrets only with the **Write/Edit** tool, never `bash echo`/`cat`.

## Step 2: Write credentials to `.env`
Read any existing `.env` first and preserve other variables. Then set (Write/Edit tool only):
```
SNOWFLAKE_PASSWORD=<password>
```
The password is the one secret that must live in `.env`. Account, user, warehouse, database, schema,
and role are not secrets and go in the dataset manifest below (which is gitignored). Confirm:
"Password saved to `.env` (gitignored, never committed)."

## Step 3: Register the dataset
Create `.knowledge/datasets/{id}/` and write `manifest.yaml` from
`connection_templates/snowflake.yaml.example`, filling the connection block and referencing the
password by env var:
```yaml
connection:
  type: snowflake
  account: "<account>"
  warehouse: "<warehouse>"
  database: "<database>"
  schema: "<schema>"
  user: "<username>"
  password: "$SNOWFLAKE_PASSWORD"   # expanded from .env at connect time
  # role: "<role>"                  # include only if given
```
Also create an empty `quirks.md` and `metrics/index.yaml`, and point `.knowledge/active.yaml` at this
dataset with the remote opt-in on:
```yaml
active_dataset: "{id}"
use_remote: true
```

## Step 4: Verify you are LIVE on Snowflake (hard gate)
This is the step the old flow was missing. Connect through `ConnectionManager` and confirm the session
is really on the warehouse, not the local DuckDB fallback. Run:
```bash
AAP_USE_REMOTE=1 python3 - <<'PY'
from helpers.data.connection_manager import ConnectionManager
cm = ConnectionManager(dataset_id="{id}")
cm.connect()
print(cm.test_connection()["message"])          # -> "Live on account ..., warehouse ..."
v = cm.verify_remote()                            # proves snowflake, not the local fallback
assert v["remote"], f"NOT LIVE: {v['reason']}"
print("Tables:", cm.list_tables()[:25])
PY
```
- **`v["remote"]` is True** → show the account, warehouse, database.schema, and the table list as
  proof, then go to Step 5.
- **`v["remote"]` is False** → do NOT declare success. The `reason` tells you what to fix:
  - "resolved to 'duckdb'/'csv', not snowflake" → the remote opt-in did not take. Make sure
    `AAP_USE_REMOTE=1` is in the **same** shell command as `python3`, and `use_remote: true` is in
    `active.yaml`.
  - "not installed" → install `snowflake-connector-python` (Prerequisite above).
  - an auth/account error → re-collect the offending field (Step 1). Common: wrong account
    identifier format, password typo, warehouse suspended, account not activated.

Never report "connected" on the strength of the manifest file existing. Success means
`verify_remote()` returned True.

## Step 5: Explore and hand off
With the connection verified, show what is there and suggest a first question:
```bash
AAP_USE_REMOTE=1 python3 -c "from helpers.data.connection_manager import ConnectionManager as C; c=C(dataset_id='{id}'); c.connect(); print(c.list_tables())"
```
Tell the user: the analyst now queries this warehouse for every request, and each query is logged for
provenance. For day-to-day "am I on live or local?" checks, use `/connect-snowflake`. Remind them that
remote is opt-in: `use_remote: true` is set for this dataset, and `AAP_USE_REMOTE=1` in the shell is the
belt-and-suspenders guard.

---

## Appendix (optional): the Snowflake MCP server
Only if the user specifically wants the interactive `snowflake-labs-mcp` query tool in addition to the
native path. The analyst does not query through it, so this is not required for setup.

1. Install `uv`: `curl -LsSf https://astral.sh/uv/install.sh | sh`, then `~/.local/bin/uvx --version`.
2. Create `snowflake-mcp-config.yaml` with read-only SQL permissions:
   ```yaml
   other_services: {object_manager: true, query_manager: true, semantic_manager: true}
   sql_statement_permissions:
     - Select: true
     - Create: false
     - Drop: false
     - Update: false
     - Delete: false
     - Insert: false
   ```
3. Add a `snowflake` server to `.mcp.json` (preserve other servers). The `command` is the absolute
   path to `uvx`; credentials go in `args` as explicit flags (`--account`, `--user`, `--warehouse`,
   `--password`) because the server ignores the env block. Do NOT use `--connection-name`.
4. Restart Claude Code so the MCP config loads, then query with the MCP `run_snowflake_query` tool:
   `SELECT CURRENT_ACCOUNT(), CURRENT_WAREHOUSE(), CURRENT_VERSION()`.
