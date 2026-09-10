---
name: connect-data
description: |
  Guided wizard to connect a new dataset to the AI Analyst system. Use this skill whenever the user wants to add a new data source, connect a database, set up data access, or configure a new dataset for analysis. This skill handles the full connection workflow: choosing connection type (CSV, DuckDB, PostgreSQL, Snowflake, BigQuery, Databricks, Redshift, SQL Server, MySQL), collecting credentials, validating connectivity, profiling schema, and setting up the knowledge brain. Trigger this skill when users say things like "/connect-data", "connect my database", "add a new dataset", "set up my data", "I have a database I want to analyze", "can you connect to my Postgres/BigQuery/Snowflake", "I need to add CSV files", "how do I get my data into this system", or "connect to my warehouse". Also trigger after first-run welcome when users need to set up their first dataset, or after /switch-dataset when the target dataset doesn't exist yet. This is the primary entry point for all new data connections — always offer this when users mention having data they want to analyze but haven't connected yet.
---
> Once a CSV folder is registered, it is SQL-queryable through `ConnectionManager().query(sql)`:
> each file becomes a table named after its file stem (`orders.csv` -> `orders`), and the
> manifest's `files:` list is the table inventory. Every query is auto-logged for provenance.


# Skill: Connect Data

## Purpose
**This is an interactive setup wizard, not a documentation generator.** Guide the user through the actual connection process by executing each step, creating files, testing connectivity, and setting up the knowledge system. Do not just explain what would happen — make it happen.

## When to Use
- User says `/connect-data` or "connect my database" or "add a new dataset"
- First-run welcome suggests connecting data
- After `/switch-dataset` when the target dataset doesn't exist yet

## Invocation
`/connect-data` — start the connection wizard
`/connect-data type=postgres` — skip type selection and go directly to Step 2

**Parameter Handling:** If the user provides `type={connection_type}` (e.g., `type=bigquery`, `type=postgres`), SKIP Step 1 entirely and proceed directly to Step 2 with that connection type already selected.

## Instructions

### Step 1: Choose Connection Type
**Skip this step if `type` parameter was provided in the invocation.**

Present options:
1. **CSV files** — "I have CSV files in a local directory"
2. **DuckDB** — "I have a local DuckDB database file"
3. **PostgreSQL** — "I have a PostgreSQL database"
4. **Snowflake** — "I have a Snowflake warehouse"
5. **BigQuery** — "I have a Google BigQuery dataset"
6. **Databricks** — "I have a Databricks SQL warehouse"
7. **Redshift** — "I have an Amazon Redshift cluster"
8. **SQL Server** — "I have a Microsoft SQL Server / Azure SQL database"
9. **MySQL** — "I have a MySQL or MariaDB database"

### Step 2: Collect Connection Details

**For CSV:**
- Ask: "What's the path to your CSV directory? (relative to this repo)"
- Verify the directory exists and contains .csv files
- List found files and ask to confirm

**For DuckDB:**
- Ask: "Path to your .duckdb file?"
- Verify file exists
- Test connection with `SELECT 1`

**For Databricks:**
- Copy `connection_templates/databricks.yaml.example`
- Ask for: server_hostname, http_path (both from the SQL warehouse "Connection
  details" panel), catalog, schema
- Store the personal access token in `.env` as `$DATABRICKS_TOKEN` (never inline)

**For BigQuery:**
- Copy `connection_templates/bigquery.yaml.example`
- Ask for the GCP project id and BigQuery dataset name
- Use Application Default Credentials for local development. Ask the user to complete
  `gcloud auth application-default login` themselves if ADC is not already available.
- Never ask for a service-account JSON key in chat and never copy one into the repository.
- After writing the manifest, verify with
  `ConnectionManager(dataset_id=...).verify_remote()` before declaring success.

**For PostgreSQL / Redshift / SQL Server / MySQL:**
- Copy the matching template from `connection_templates/` (`postgres`, `redshift`,
  `mssql`, `mysql`)
- Ask the user to fill in host, port, database, schema, and username. MySQL keys
  `information_schema` by database and SQL Server defaults to the `dbo` schema.
- **IMPORTANT:** Never ask for or store passwords directly. Put the password in `.env`
  as an env var (e.g., `$REDSHIFT_PASSWORD`, `$MSSQL_PASSWORD`, `$MYSQL_PASSWORD`) and
  reference it from the manifest.
- After writing the manifest, verify with `ConnectionManager(dataset_id=...).verify_remote()`
  before declaring success (remote opt-in: `AAP_USE_REMOTE=1` / `use_remote: true`).

**For Snowflake:**
- Route to the dedicated setup wizard: "Run `/setup-snowflake` for guided
  Snowflake setup — it collects every field, writes the password to `.env`,
  and verifies you are live on the warehouse before finishing."

### Step 3: Create Dataset Brain
1. **Generate a dataset_id from the display name** using lowercase letters with hyphens (NOT underscores).
   - Example: "Production Analytics" → `production-analytics`
   - Example: "GA4 Event Data" → `ga4-event-data`
   - Example: "Sales Database" → `sales-database`
2. Create `.knowledge/datasets/{id}/` directory
3. Write `manifest.yaml` from the connection template + user inputs
4. Create empty `quirks.md` with section headers
5. Create empty `metrics/index.yaml`

### Step 4: Test Connection
**You MUST use ConnectionManager — do not write custom connection scripts.**

Use `ConnectionManager` from `helpers/data/connection_manager.py`:
1. Instantiate with the new config:
   ```python
   from helpers.data.connection_manager import ConnectionManager
   config = {"type": connection_type, "dataset_id": dataset_id, ...}
   mgr = ConnectionManager(config=config)
   ```
2. Call `test_connection()`:
   ```python
   result = mgr.test_connection()
   ```
3. If fails: show error, offer to retry or edit config
4. If it passes, call `verify_remote()` and show the remote identity before proceeding.
5. If the selected source resolves to DuckDB, CSV, or another fallback, stop. Do not
   describe the remote connection as successful.

**Why ConnectionManager?** It handles connection pooling, error handling, and provides a consistent interface across every supported source type. Do not bypass it with psycopg2, pandas, or warehouse-specific clients.

### Step 5: Profile Schema
**Use ConnectionManager methods — do not write raw SQL for schema introspection.**

1. Call `mgr.list_tables()` to enumerate tables
2. For each table: get column names and types via `mgr.get_table_schema(table_name)`
3. Generate `schema.md` using `schema_to_markdown()` from `helpers/data/data_helpers.py`
4. Write to `.knowledge/datasets/{id}/schema.md`
5. Offer to run full data profiling: "Want me to deep-profile this dataset?"

**Why?** ConnectionManager abstracts away warehouse-specific schema queries (INFORMATION_SCHEMA for Postgres/BigQuery, PRAGMA for DuckDB, pandas for CSV).

### Step 6: Set Active
1. Update `.knowledge/active.yaml` to point to the new dataset
2. Confirm: "Connected! **{display_name}** is now your active dataset."
3. Show: table count, estimated row count, date range (if detected)
4. Suggest next steps: `/explore` to browse, `/metrics` to define metrics,
   or just ask a question

## Rules
1. Never store credentials in plain text in manifest files
2. Always test the connection before declaring success
3. Always generate a schema.md — it's required for analysis
4. Create the full .knowledge/datasets/{id}/ tree even if profiling fails
5. If the user already has this dataset, ask before overwriting

## Edge Cases
- **Directory doesn't exist:** Offer to create it
- **No CSV files found:** Check for other formats (.parquet, .json)
- **Connection fails repeatedly:** Suggest checking credentials, firewall, VPN
- **Schema too large (>100 tables):** Profile only, skip per-table details
- **Dataset name collision:** Append a number (e.g., "mydata-2")
