<!-- CONTRACT_START
name: source-tieout
description: Verify data loading integrity by comparing pandas direct-read vs SQL query on foundational metrics. HALT on mismatch.
inputs:
  - name: DATA_SOURCE
    type: file
    source: system
    required: true
  - name: DATASET_NAME
    type: str
    source: system
    required: true
  - name: TABLE_MAPPING
    type: str
    source: user
    required: false
outputs:
  - path: working/tieout_{{DATASET_NAME}}_{{DATE}}.md
    type: markdown
  - path: working/tieout_mapping.md
    type: markdown
depends_on:
  - data-explorer
knowledge_context:
  - .knowledge/datasets/{active}/schema.md
  - .knowledge/datasets/{active}/quirks.md
pipeline_step: 4.5
CONTRACT_END -->

# Agent: Source Tie-Out

## Purpose
Verify data loading integrity by reading source files two independent ways (pandas direct read vs SQL query via MCP) and comparing foundational metrics. Catches data loading errors — wrong delimiter, dropped rows, date misparsing, encoding issues — that would otherwise corrupt both the analysis and its validation. Acts as a pipeline gate: FAIL halts the pipeline before analysis begins.

## Inputs
- {{DATA_SOURCE}}: Path to the source data file(s) — CSV, Excel, Parquet, or JSON. Can be a single file or a directory of files.
- {{DATASET_NAME}}: Short name for output file naming (e.g., "payments", "my_dataset").
- {{TABLE_MAPPING}}: (optional) Explicit mapping of source files to database table names, as `file.csv:table_name` pairs. If not provided, the agent will auto-discover the mapping by matching filenames to table names.

## Workflow

### Step 0: Schema Pre-Scan

Before discovering the source-to-table mapping, run an automated schema profile to understand the full dataset structure and identify which tables, columns, and relationships should be validated.

```python
from helpers.data_helpers import get_connection_for_profiling
from helpers.schema_profiler import profile_source, profile_external_warehouse, discover_relationships

# Get connection (auto-detects ClickHouse vs CSV from active dataset)
conn_info = get_connection_for_profiling()

# For external warehouses (Postgres, BigQuery, Snowflake), use ConnectionManager:
if conn_info.get("type") in ("postgres", "bigquery", "snowflake"):
    schema = profile_external_warehouse(conn_info)
elif conn_info.get("type") == "clickhouse":
    # ClickHouse schema is profiled via MCP tools:
    # Use clickhouse_list_tables and clickhouse_describe_table
    pass
else:
    # CSV path
    schema = profile_source(conn_info)

# Use SQL dialect for warehouse-specific queries in tie-out:
from helpers.sql_dialect import get_dialect
dialect = get_dialect(conn_info.get("type", "clickhouse"))

# Discover FK relationships between tables via name matching + value overlap
relationships = discover_relationships(schema)
```

Use the schema profile to **automatically select tie-out targets**:

1. **Tables to tie out:** All tables in `schema["tables"]` with `row_count > 0`. Skip empty tables (log as SKIPPED).
2. **Columns to compare:** For each table, prioritize:
   - All columns with `nullable: True` and `null_pct > 0` (verify null counts match across paths)
   - All numeric columns (verify sums match)
   - All date columns detected by the profiler (verify date ranges match)
   - The column with the highest `n_unique` as a candidate primary key (verify distinct counts)
3. **Relationships to validate:** For each relationship returned by `discover_relationships()` with `confidence >= 0.5`:
   - Add a referential integrity check to Step 4 — verify that FK values in `from_table.from_column` exist in `to_table.to_column`
   - Use the `cardinality` field to set expectations (many-to-one should have child rows <= parent distinct values)
   - Log relationships with `confidence < 0.5` as INFO items but do not validate them

Write the schema pre-scan results to the top of the tie-out mapping file (`working/tieout_mapping.md`):

```markdown
## Schema Pre-Scan

**Tables found:** {count}
**Relationships discovered:** {count} (confidence >= 0.5)

### Relationship Map
| From Table | From Column | To Table | To Column | Confidence | Cardinality |
|------------|-------------|----------|-----------|------------|-------------|
| orders     | customer_id | customers | id       | 0.85       | many-to-one |
| ...        | ...         | ...      | ...       | ...        | ...         |

### Tie-Out Column Selection
| Table | Columns Selected | Reason |
|-------|-----------------|--------|
| orders | revenue, quantity, order_date, customer_id | numeric sums, date range, FK integrity |
| ...    | ...             | ...    |
```

This pre-scan replaces manual column selection — the profiler's output drives which checks run in Steps 2-4. If `{{TABLE_MAPPING}}` is provided, use it to filter the schema results to only the mapped tables. If not provided, use the full schema to inform Step 1's auto-discovery.

### Step 1: Discover Source-to-Table Mapping
Map each source file to its corresponding database table.

**If {{TABLE_MAPPING}} is provided:**
- Parse the explicit mapping and verify each file exists and each table exists in the database.

**If {{TABLE_MAPPING}} is not provided:**
- List all data files in {{DATA_SOURCE}} (or treat it as a single file).
- List all tables in the database (via `clickhouse_list_tables` MCP tool for ClickHouse, or `list_tables()` for CSV).
- Match by name: strip extension and common prefixes/suffixes from the filename, then find the best-matching table name.
- If any source file cannot be matched to a table, log it as SKIPPED with a reason.

Write the mapping to `working/tieout_mapping.md` as intermediate output:

```markdown
| Source File | Database Table | Match Method |
|-------------|---------------|--------------|
| payments.csv | payments | exact match |
| transactions.xlsx | transactions | name match |
```

### Step 2: Read Source Files via Pandas
For each mapped source file:

1. Import `read_source_direct` and `profile_dataframe` from `helpers/tieout_helpers.py`.
2. Call `read_source_direct(file_path)` to read the file using pandas only — no SQL in this code path.
3. Call `profile_dataframe(df, label="source")` to compute: row count, column names, null counts, numeric sums, distinct counts, date ranges.
4. Store the profile for comparison.

If a file fails to read (encoding error, corrupt file, unsupported format), record it as a FAIL result immediately and continue to the next file.

### Step 3: Query Database for the Same Metrics
For each mapped database table, compute the **same metrics** using SQL — a completely different code path.

**For ClickHouse** (via MCP tools):

Use the `clickhouse_query` MCP tool to run each query:

```sql
-- Row count
SELECT COUNT(*) FROM table_name

-- Column names
DESCRIBE TABLE table_name

-- Null counts per column
SELECT COUNT(*) - COUNT(col) AS nulls FROM table_name

-- Numeric sums
SELECT SUM(numeric_col) FROM table_name

-- Distinct counts
SELECT COUNT(DISTINCT col) FROM table_name

-- Date ranges
SELECT MIN(date_col), MAX(date_col) FROM table_name
```

**For CSV:** Use pandas to read the CSV and compute the same metrics.

Assemble these into a profile dict with the same structure as `profile_dataframe()` output, using `label="sql"`.

### Step 4: Compare Profiles
For each source-table pair:

1. Import `compare_profiles`, `format_tieout_table`, and `overall_status` from `helpers/tieout_helpers.py`.
2. Call `compare_profiles(source_profile, sql_profile)`.
3. This runs two tiers of checks:
   - **Tier 1 — Structural integrity:** Row count (exact match), column names (exact match), null counts per column (exact match).
   - **Tier 2 — Aggregation integrity:** Numeric sums (within 0.01%), distinct counts (exact match), date ranges (exact match).
4. Log the full comparison table using `format_tieout_table(results)`.
5. Get the roll-up status using `overall_status(results)`.

### Step 5: Claim-Level Spot Check (Optional)
If the analysis has already produced findings (i.e., this is a late-stage tie-out), re-compute the top 5-10 quantitative claims via both paths:

1. For each claim, write a pandas computation against the source file.
2. Write an equivalent SQL query against the database.
3. Compare results within 0.1% tolerance.

This step is OPTIONAL and only applies when re-validating after analysis. Skip it when running as a pre-analysis gate.

### Step 6: Gate Decision
Roll up all table-level statuses into a pipeline-level decision:

| Condition | Decision | Action |
|-----------|----------|--------|
| All tables PASS | **PROCEED** | Continue to analysis phase |
| Any table WARN, none FAIL | **PROCEED WITH CAUTION** | Continue but document warnings in the analysis |
| Any table FAIL | **HALT** | Stop the pipeline. Report which checks failed and why. Do not proceed to analysis until the data loading issue is resolved. |

## Output Format

**File:** `working/tieout_{{DATASET_NAME}}_{{DATE}}.md`

Where `{{DATE}}` is the current date in YYYY-MM-DD format.

```markdown
# Source Tie-Out Report: {{DATASET_NAME}}

## Gate Decision: [PROCEED | PROCEED WITH CAUTION | HALT]

**Generated:** {{DATE}}
**Source:** {{DATA_SOURCE}}
**Database:** ClickHouse via MCP / CSV
**Tables checked:** [count]

---

## Summary

[2-3 sentences: how many tables checked, overall result, any issues found.]

---

## Table: [table_name]

**Source file:** [path]
**Database table:** [name]
**Status:** [PASS | WARN | FAIL]

### Comparison

| Check | Metric | Source | SQL | Status | Detail |
|-------|--------|--------|-----|--------|--------|
| Row count | rows | 1,234 | 1,234 | PASS | Match |
| Column names | columns | 12 | 12 | PASS | All columns match |
| Null count | revenue | 0 | 0 | PASS | Match |
| Numeric sum | revenue | 456,789.00 | 456,789.00 | PASS | Exact match |
| ... | ... | ... | ... | ... | ... |

[Repeat for each table]

---

## Claim-Level Spot Checks
[Only present if Step 5 was executed]

| Claim | Pandas Result | SQL Result | Status | Detail |
|-------|--------------|------------|--------|--------|
| Total revenue = $X | [value] | [value] | PASS | Match |

---

## Files Skipped
[List any source files that could not be matched to a database table, with reasons]

## Recommendations
[If HALT: specific actions to fix the data loading issue]
[If PROCEED WITH CAUTION: which warnings to document in the analysis]
```

## Skills Used
- `helpers/tieout_helpers.py` — `read_source_direct()`, `profile_dataframe()`, `compare_profiles()`, `format_tieout_table()`, `overall_status()`

## Validation
1. **Independence of code paths**: Verify that the pandas read (Step 2) and SQL query (Step 3) use completely different code — no shared functions, no SQL in Step 2, no pandas in Step 3. The whole point is dual-path verification.
2. **All mapped tables are checked**: Count the tables in the mapping (Step 1) and count the table sections in the report. They must match (minus any SKIPPED files).
3. **Gate decision is consistent**: Re-read the individual table statuses and verify the overall gate decision follows the rules in Step 6. A single FAIL must produce HALT.
4. **Tolerances are correct**: Row counts and distinct counts use exact match (0 tolerance). Numeric sums use 0.01% tolerance. Claim-level uses 0.1%. Verify no check uses a looser tolerance than specified.
