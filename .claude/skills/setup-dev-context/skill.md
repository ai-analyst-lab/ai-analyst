# /setup-dev-context — Developer Context Setup

> Standalone skill for teams integrating AI Analyst into development workflows.
> Most users (PMs, execs, DS) never need this — only teams doing codebase integration.

## Trigger
Invoked as `/setup-dev-context`

## Purpose
Collects codebase-specific context to help AI Analyst understand your development
environment. This enables more accurate SQL generation, schema awareness, and
integration with your existing data infrastructure.

## Prerequisites
- `/setup` interview (Phases 1-2) must be completed first
- Read `.knowledge/setup-state.yaml` to verify `phase_2.status: complete`
- If setup incomplete, inform user: "Run `/setup` first to configure your profile and data connection."

## Interview Flow

### Step 1: Codebase Structure
Ask the user:
```
I'll ask a few questions about your development environment to provide better support.

1. **Repository type:** What kind of codebase is this?
   - [ ] Analytics/data warehouse (dbt, SQL files, ETL)
   - [ ] Application backend (API, services)
   - [ ] Full-stack application
   - [ ] Data science / ML project
   - [ ] Other: ___
```

Record response in `.knowledge/user/dev-context.yaml` under `codebase.type`.

### Step 2: Data Layer
Ask the user:
```
2. **Data layer:** How is your data organized?
   - Database type: (Postgres, BigQuery, Snowflake, ClickHouse, other)
   - Schema naming convention: (e.g., `analytics.`, `public.`, `dbt_prod.`)
   - Key tables location: (path to schema definitions, dbt models, etc.)
```

Record under `codebase.data_layer`.

### Step 3: SQL Conventions
Ask the user:
```
3. **SQL conventions:** Does your team follow specific patterns?
   - Naming: snake_case / camelCase / other
   - Date handling: timezone-aware? Default timezone?
   - NULL handling: COALESCE patterns? Default values?
   - Any team-specific SQL style guide? (path or URL)
```

Record under `codebase.sql_conventions`.

### Step 4: Integration Points
Ask the user:
```
4. **Integration points:** Where does AI Analyst fit in your workflow?
   - [ ] Ad-hoc analysis only (no integration needed)
   - [ ] Reads from dbt models
   - [ ] Connects to production replica
   - [ ] Uses exported CSV/Parquet files
   - [ ] Accesses data warehouse directly
   - Other: ___
```

Record under `codebase.integration`.

### Step 5: File Conventions
Ask the user:
```
5. **File conventions:** (optional)
   - Where do analysis outputs go? (default: `outputs/`)
   - Any naming conventions for SQL files?
   - Git branch strategy for analysis work?
```

Record under `codebase.file_conventions`.

## Output

Save collected context to `.knowledge/user/dev-context.yaml`:

```yaml
schema_version: 1
created: "{{DATE}}"
last_updated: "{{DATE}}"

codebase:
  type: null           # analytics | backend | fullstack | data-science | other
  data_layer:
    database: null     # postgres | bigquery | snowflake | clickhouse | other
    schema_prefix: null
    models_path: null  # path to dbt models or schema definitions
  sql_conventions:
    naming: snake_case
    timezone_aware: false
    default_timezone: UTC
    null_handling: null
    style_guide: null
  integration:
    mode: null         # adhoc | dbt | replica | exported | direct
    details: null
  file_conventions:
    output_dir: outputs/
    sql_naming: null
    git_strategy: null
```

Update `.knowledge/setup-state.yaml`:
```yaml
dev_context:
  status: complete
  completed_at: "{{DATE}}"
```

## Completion Message
```
Developer context saved. AI Analyst will now:
- Use your schema prefix ({{schema_prefix}}) in SQL queries
- Follow your team's SQL conventions
- Output files to {{output_dir}}

You can update this anytime with `/setup-dev-context`.
```

## Reset
`/setup-dev-context reset` — Clears dev-context.yaml and resets to defaults.
