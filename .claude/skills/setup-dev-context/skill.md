---
name: setup-dev-context
description: |
  Configure AI Analyst to understand your development environment and codebase structure. Use this skill whenever developers need to integrate AI Analyst into their workflow, or when questions arise about database configuration, SQL conventions, schema naming patterns, dbt integration, warehouse connections, or team-specific data practices.

  Trigger this skill when users mention: "set up for our team", "configure for our codebase", "integrate with our database", "tell it about our SQL conventions", "set up dbt integration", "configure schema prefix", "set up warehouse connection", "integrate with our data stack", "configure for development", "set up team conventions", or any request about configuring AI Analyst to work with an existing development environment, data warehouse, or analytics infrastructure.

  This is ONLY for development teams integrating AI Analyst into their codebase. Most users (PMs, execs, data scientists doing ad-hoc analysis) should use `/setup` instead. Only invoke this when the user explicitly mentions development integration, codebase configuration, or team-wide setup — not for individual user onboarding.
---

# /setup-dev-context — Developer Context Setup

> Standalone skill for teams integrating AI Analyst into development workflows.
> Most users (PMs, execs, DS) never need this — only teams doing codebase integration.

## Trigger
Invoked as `/setup-dev-context`

## Purpose
Collects codebase-specific context to help AI Analyst understand your development
environment. This enables more accurate SQL generation, schema awareness, and
integration with your existing data infrastructure.

## CRITICAL: Follow This Exact Sequence

This skill has a strict execution flow. Do NOT skip steps or auto-fill values from the user's initial prompt. Each step serves a purpose.

### Step 0: Check Prerequisites (ALWAYS FIRST)

Before doing anything else, verify basic setup is complete:

```bash
# Read setup state file
cat .knowledge/setup-state.yaml
```

Look for `phase_2.status: complete`. If missing or status is not "complete":

```
⚠️  Basic setup not complete. Please run `/setup` first to configure your profile and data connection.

You need to complete the initial setup before configuring development context.
```

STOP here. Do not proceed to interview.

If setup is complete, continue to Step 1.

**Why this matters:** Dev context assumes a dataset already exists. Without Phase 1-2 setup, there's no dataset to configure conventions for. Checking prerequisites prevents configuration errors downstream.

### Step 1: Run the Interview (ALWAYS ASK)

Even if the user provided some details in their initial request, you MUST ask all 5 questions. Here's why: users often provide incomplete information or have assumptions you need to clarify. The interview ensures you capture everything correctly and the user confirms their choices.

Present all 5 questions at once (not one-by-one):

```
I'll ask a few questions about your development environment to provide better support.

1. **Repository type:** What kind of codebase is this?
   - [ ] Analytics/data warehouse (dbt, SQL files, ETL)
   - [ ] Application backend (API, services)
   - [ ] Full-stack application
   - [ ] Data science / ML project
   - [ ] Other: ___

2. **Data layer:** How is your data organized?
   - Database type: (Postgres, BigQuery, Snowflake, DuckDB, other)
   - Schema naming convention: (e.g., `analytics.`, `public.`, `dbt_prod.`)
   - Key tables location: (path to schema definitions, dbt models, etc.)

3. **SQL conventions:** Does your team follow specific patterns?
   - Naming: snake_case / camelCase / other
   - Date handling: timezone-aware? Default timezone?
   - NULL handling: COALESCE patterns? Default values?
   - Any team-specific SQL style guide? (path or URL)

4. **Integration points:** Where does AI Analyst fit in your workflow?
   - [ ] Ad-hoc analysis only (no integration needed)
   - [ ] Reads from dbt models
   - [ ] Connects to production replica
   - [ ] Uses exported CSV/Parquet files
   - [ ] Accesses data warehouse directly
   - Other: ___

5. **File conventions:** (optional)
   - Where do analysis outputs go? (default: `outputs/`)
   - Any naming conventions for SQL files?
   - Git branch strategy for analysis work?
```

**If user already provided some values** in their initial prompt, you can pre-fill your proposed answers in parentheses:

```
2. **Data layer:** How is your data organized?
   - Database type: (you mentioned Snowflake — is that correct?)
   - Schema naming convention: (you mentioned `analytics_prod.` — confirm?)
   - Key tables location: (path to schema definitions, dbt models, etc.)
```

But you MUST still ask for confirmation. Do not just assume and skip ahead.

**Wait for the user's response before proceeding.**

**Why this matters:** When you auto-fill, you risk getting details wrong (e.g., user says "Snowflake" but meant "Snowflake schema in Postgres"). The interview is a confirmation step, not a formality.

### Step 2: Create the Configuration File

After collecting responses, create `.knowledge/user/dev-context.yaml`:

```bash
# Create directory if needed
mkdir -p .knowledge/user

# Write configuration
cat > .knowledge/user/dev-context.yaml <<'EOF'
schema_version: 1
created: "2026-04-03"
last_updated: "2026-04-03"

codebase:
  type: analytics           # User's response from Q1
  data_layer:
    database: snowflake     # User's response from Q2
    schema_prefix: analytics_prod.
    models_path: dbt/models/
  sql_conventions:
    naming: snake_case      # User's response from Q3
    timezone_aware: true
    default_timezone: UTC
    null_handling: null
    style_guide: null
  integration:
    mode: dbt               # User's response from Q4
    details: "Reads from dbt prod models"
  file_conventions:
    output_dir: outputs/    # User's response from Q5 (or default)
    sql_naming: null
    git_strategy: null
EOF
```

**Verify the file was created:**

```bash
ls -la .knowledge/user/dev-context.yaml
cat .knowledge/user/dev-context.yaml
```

Show the user what was written. If file creation failed, report the error and stop.

**Why this matters:** Claiming to create a file without verifying leaves the user with incomplete setup. The verification step catches filesystem issues early.

### Step 3: Update Setup State

Mark dev context as complete:

```bash
# Read current state
cat .knowledge/setup-state.yaml

# Update with dev_context status
# (Append if dev_context section doesn't exist, or edit if it does)
```

If `.knowledge/setup-state.yaml` doesn't exist, create it:

```yaml
schema_version: 1
created: "2026-04-03"

phase_1:
  status: complete
phase_2:
  status: complete
dev_context:
  status: complete
  completed_at: "2026-04-03T22:45:00Z"
```

Verify:

```bash
grep -A2 "dev_context:" .knowledge/setup-state.yaml
```

### Step 4: Completion Message

Show the user a confirmation with the specific values they configured:

```
✅ Developer context saved.

AI Analyst will now:
- Use your schema prefix (`analytics_prod.`) in all SQL queries
- Follow snake_case naming conventions
- Handle all timestamps in UTC
- Integrate with your dbt models
- Save analysis outputs to `outputs/`

Configuration saved to: .knowledge/user/dev-context.yaml

You can update these settings anytime by running `/setup-dev-context` again.
```

**Why this matters:** The completion message reassures the user that their specific settings were captured (not just generic defaults).

## What NOT to Do

❌ **Do NOT create dataset configuration files** (`.knowledge/datasets/{name}/manifest.yaml`, `schema.md`, `quirks.md`) — that's a different workflow (use `/connect-data` for that)

❌ **Do NOT create helper scripts** (`helpers/postgres_helpers.py`, `helpers/config_helpers.py`) — this skill only captures team conventions, not infrastructure

❌ **Do NOT write documentation files** (`SETUP_SNOWFLAKE.md`, integration guides) — keep the output minimal

❌ **Do NOT auto-fill values without asking** — always run the interview, even if user provided context

This skill creates exactly ONE file: `.knowledge/user/dev-context.yaml`. That's it.

**Why this matters:** When you over-engineer the output (creating helpers, docs, dataset configs), you've misunderstood the purpose of this skill. Dev-context is a lightweight capture of team conventions, not a full dataset integration. Keep it simple.

## Reset Command

If user runs `/setup-dev-context reset`:

```bash
rm .knowledge/user/dev-context.yaml
# Remove dev_context section from setup-state.yaml
```

Inform user: "Developer context cleared. Run `/setup-dev-context` to reconfigure."

## Edge Cases

**User runs this before `/setup`:**
- Prerequisite check catches this → direct them to `/setup`

**User has already run dev-context setup:**
- Read existing `dev-context.yaml` and pre-fill interview with current values
- Let them edit and overwrite

**User provides conflicting info:**
- E.g., says "Postgres" but also mentions "dbt models in Snowflake"
- Ask clarifying question: "I see you mentioned both Postgres and Snowflake — which database should I configure for SQL generation?"

**User wants multiple database configs:**
- This skill handles ONE primary database configuration
- Suggest: "This tool currently supports one primary database config. Which one should I configure — Postgres or Snowflake?"
