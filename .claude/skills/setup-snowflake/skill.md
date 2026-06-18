# Skill: Setup Snowflake

## Purpose
Guided first-time Snowflake setup wizard. Installs dependencies, configures
the MCP server, collects credentials, writes `.env`, tests the connection,
explores available data, and gets the user querying.

## When to Use
- User says `/setup-snowflake`, "connect to snowflake", "set up snowflake",
  "I have a snowflake account"
- Routed here from `/connect-data` when the user selects Snowflake

## Invocation
`/setup-snowflake` — start the setup wizard

## Instructions

### Step 1: Check Existing Configuration

**1a. Check `.env` for credentials:**
Read `.env` (if it exists) and check for these variables:
- `SNOWFLAKE_ACCOUNT`
- `SNOWFLAKE_USER`
- `SNOWFLAKE_PASSWORD`

**1b. Check MCP server is configured:**
Read `.mcp.json` (if it exists) and check for a `snowflake` server entry.

**1c. Check `uvx` is installed:**
Run `which uvx` or check `~/.local/bin/uvx`.

**Decision matrix:**
- All credentials + MCP configured → skip to Step 5 (test connection)
- Credentials exist but no MCP config → skip to Step 3 (configure MCP)
- Missing credentials → continue to Step 2
- `uvx` not installed → install it in Step 3

### Step 2: Collect Credentials
Ask one question at a time:

1. **Account Identifier**
   - "What's your Snowflake account identifier?"
   - Help text: "Find it in Snowsight: click your name in the bottom-left →
     click your account name under **Account** → click **View account details** →
     copy the **Account identifier** from the modal. It looks like
     `ORGNAME-ACCOUNTNAME` (e.g., `MYORG-MYACCOUNT`)."

2. **Username**
   - "What username did you create during Snowflake signup?"

3. **Password**
   - "Paste your Snowflake password. I'll write it directly to `.env` and
     never display it in the terminal."

**CRITICAL SECURITY RULES:**
- **Never** echo, print, or log the password in any command
- **Never** pass the password as a CLI argument (visible in `ps`)
- **Never** include the password in any output shown to the user
- **Never** use `Bash` with `echo` or `cat` to write credentials — use the
  `Write` or `Edit` tool only

### Step 3: Install Dependencies & Configure MCP Server

**3a. Install `uv` (if `uvx` not found):**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```
Then verify: `~/.local/bin/uvx --version`

**3b. Write `.env`:**
1. If `.env` already exists, read it first to preserve existing variables
   (e.g., `SLACK_TOKEN`, `MOTHERDUCK_TOKEN`)
2. Add or update these variables:
   ```
   SNOWFLAKE_ACCOUNT=<account_identifier>
   SNOWFLAKE_USER=<username>
   SNOWFLAKE_PASSWORD=<password>
   SNOWFLAKE_WAREHOUSE=COMPUTE_WH
   ```
3. Use the **Write** or **Edit** tool — NOT bash echo/cat
4. Confirm: "Credentials saved to `.env`. This file is gitignored and never
   committed."

**3c. Create `snowflake-mcp-config.yaml`** (if it doesn't exist):
```yaml
# Snowflake MCP Server Configuration
# Controls which Snowflake services are available via MCP tools.
# Auth is handled via .env (SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER, SNOWFLAKE_PASSWORD).

agent_services: []
search_services: []
analyst_services: []

other_services:
  object_manager: true
  query_manager: true
  semantic_manager: true

sql_statement_permissions:
  - Select: true
  - Create: false
  - Drop: false
  - Update: false
  - Delete: false
  - Insert: false
```

Note: SQL permissions are read-only by default for safety. Users can enable
write permissions later if needed.

**3d. Add Snowflake to `.mcp.json`:**
1. Read `.mcp.json` if it exists (preserve other servers)
2. Add the `snowflake` server entry:
   ```json
   {
     "mcpServers": {
       "snowflake": {
         "command": "<absolute_path_to_uvx>",
         "args": [
           "snowflake-labs-mcp",
           "--service-config-file",
           "snowflake-mcp-config.yaml",
           "--account",
           "<account_identifier>",
           "--user",
           "<username>",
           "--warehouse",
           "COMPUTE_WH",
           "--password",
           "<password>"
         ]
       }
     }
   }
   ```
3. The `command` must be the **absolute path** to `uvx` (e.g.,
   `/Users/<name>/.local/bin/uvx`). Find it with `which uvx` or
   check `~/.local/bin/uvx`.
4. All credentials go in `args` with explicit flags (`--account`,
   `--user`, `--warehouse`, `--password`). The env var approach does
   not work — the server ignores `SNOWFLAKE_PASSWORD` from the `env`
   block and requires `--password` as a CLI arg.
5. **Do NOT use `--connection-name`** — it requires a Snowflake
   `connections.toml` config file that most users won't have.

### Step 4: Restart Required
The MCP server won't be available until Claude Code restarts and loads the
new `.mcp.json` config.

Tell the user:
- "Everything is configured. The Snowflake MCP server needs Claude Code to
  restart to pick up the new config."
- "Exit with `/exit`, then run `claude` again."
- "When you're back, run `/setup-snowflake` — I'll detect your saved config
  and jump straight to testing the connection."

Stop here — do not proceed to Step 5 in this session.

### Step 5: Test Connection
Use the Snowflake MCP `run_snowflake_query` tool to run:
```sql
SELECT CURRENT_ACCOUNT(), CURRENT_USER(), CURRENT_WAREHOUSE(), CURRENT_VERSION()
```

**If connection succeeds:**
- Show: account name, username, warehouse, Snowflake version
- Continue to Step 6.

**If connection fails:**
- Show the error message
- Offer to re-enter credentials (go back to Step 2)
- Common issues to suggest: wrong account identifier format, password typo,
  account not yet activated, warehouse suspended

### Step 6: Explore Available Data
Run these queries via the Snowflake MCP:

1. `SHOW DATABASES` — list available databases
2. `SHOW SCHEMAS IN SNOWFLAKE_SAMPLE_DATA` — list schemas in the sample data
3. `SHOW TABLES IN SNOWFLAKE_SAMPLE_DATA.TPCH_SF1` — list TPC-H tables

Present a summary to the user:
- "You have access to **N** databases."
- "The sample data includes **TPC-H** with 8 tables: CUSTOMER, ORDERS,
  LINEITEM, PART, PARTSUPP, SUPPLIER, NATION, REGION."
- Brief description of what TPC-H models (retail order processing).

Suggest a first query: "Try asking me something like: *What are the top 10
customers by total order value?*"

### Step 7: Optional — Create Dataset Knowledge
Offer: "Want me to set up TPC-H as a named dataset so I always know what
tables and columns are available?"

**If yes:**
1. Create `.knowledge/datasets/snowflake-tpch/manifest.yaml`:
   ```yaml
   dataset_id: snowflake-tpch
   display_name: Snowflake TPC-H (SF1)
   connection_type: snowflake_mcp
   database: SNOWFLAKE_SAMPLE_DATA
   schema: TPCH_SF1
   warehouse: COMPUTE_WH
   notes: >
     TPC-H benchmark dataset at scale factor 1. 8 tables modeling a
     retail order-processing scenario. Read-only sample data provided
     by Snowflake.
   ```
2. Generate `schema.md` by querying `INFORMATION_SCHEMA.COLUMNS` for
   each table and formatting with `schema_to_markdown()` or manually
3. Create empty `quirks.md` with section headers
4. Update `.knowledge/active.yaml` to point to `snowflake-tpch`
5. Confirm: "TPC-H is now your active dataset. Ask any question to get started."

**If no:** Skip — the user can run `/connect-data` later.

## Rules
1. Never display passwords or secrets in terminal output or chat
2. Always use Write/Edit tool for `.env` — never Bash echo/cat
3. Always test the connection before declaring success
4. After writing `.mcp.json` or `.env` for the first time, tell the user to
   restart — the MCP server won't load until next session
5. Preserve existing `.env` variables when adding Snowflake credentials
6. Preserve existing `.mcp.json` servers when adding the Snowflake entry
7. Use absolute path for `uvx` in `.mcp.json` `command` field
8. Default SQL permissions to read-only (Select only) for safety
