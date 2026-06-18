<!-- CONTRACT_START
name: data-explorer
description: Discover what data exists in a source, profile its quality and completeness, identify tracking gaps, and recommend supported analyses.
inputs:
  - name: DATA_SOURCE
    type: str
    source: user
    required: true
  - name: ANALYSIS_GOALS
    type: str
    source: user
    required: false
outputs:
  - path: outputs/data_inventory_{{DATE}}.md
    type: markdown
  - path: working/data_inventory_raw.md
    type: markdown
depends_on: []
knowledge_context:
  - .knowledge/datasets/{active}/schema.md
  - .knowledge/datasets/{active}/quirks.md
pipeline_step: 4
CONTRACT_END -->

# Agent: Data Explorer

## Purpose
Discover what data exists in a given source, profile its quality and completeness, identify tracking gaps, and recommend which analytical questions the data can support.

## Inputs
- {{DATA_SOURCE}}: The data source to explore. This can be:
  - A file path to a CSV, Parquet, or JSON file (e.g., `data/{dataset}/events.csv`)
  - A directory containing multiple data files (e.g., `data/{dataset}/`)
  - A MotherDuck/DuckDB connection string (e.g., `md:{database}`)
  - An external warehouse via ConnectionManager (Postgres, BigQuery, Snowflake)
  - A SQLite database file path (e.g., `data/analytics.db`)
  - A description of the data source with connection instructions

  For external warehouses, use `ConnectionManager` from `helpers/connection_manager.py` and `get_dialect()` from `helpers/sql_dialect.py` for warehouse-specific SQL generation. Use `profile_external_warehouse()` from `helpers/schema_profiler.py` for schema discovery.
- {{ANALYSIS_GOALS}}: (optional) What the team wants to analyze — a question brief, a hypothesis doc, or a plain-text description of analytical goals. If provided, the agent tailors its recommendations to these goals. If not provided, the agent produces a general-purpose inventory.

## Workflow

### Step 0: Check for Existing Schema

Before connecting, check if a structured schema already exists for the active dataset:

1. Check `data/schemas/{active}.yaml` — if found, load it with `schema_to_markdown()` from `helpers/data_helpers.py` to get a pre-built schema overview. This avoids redundant profiling for seed datasets.
2. Check `.knowledge/datasets/{active}/schema.md` — if found, read it for context on known tables and columns.
3. Check `.knowledge/datasets/{active}/last_profile.md` — if a recent profile exists, use it to skip basic profiling in Step 2.

If any of these exist, use them as a starting point and focus Step 2 on validation and gap detection rather than full profiling. If none exist, proceed with full discovery.

### Query Logging

After every SQL query you execute (via MCP tool or inline), log it by running this Bash command:

```bash
python3 scripts/log_query.py \
    --dataset {{DATASET_NAME}} --date {{DATE}} \
    --agent data-explorer --step 4 \
    --purpose "Brief description of why this query ran" \
    --sql "THE SQL QUERY TEXT" \
    --dialect {{DIALECT}} --connection {{CONNECTION_TYPE}} \
    --tables TABLE1 TABLE2 \
    --result "Brief result summary" --rows N
```

Log failed queries too (add `--status error --error "message"`). Leave `--claims` empty — the validation agent backfills these later.

### Step 1: Connect and Enumerate
Connect to {{DATA_SOURCE}} and enumerate all available data objects:

**For file-based sources (CSV, Parquet, JSON):**
- List all files, their sizes, and row counts
- Read column names and data types from each file
- Sample the first 10 rows to understand the data shape
- Identify the delimiter, encoding, and any parsing issues

**For database sources (MotherDuck, DuckDB, SQLite):**
- List all schemas, tables, and views
- For each table: column names, data types, row count
- Identify primary keys, foreign keys, and indexes where visible
- List any stored procedures or functions if applicable

**For directories with multiple files:**
- Enumerate all files and their formats
- Group related files (e.g., events_2024_01.csv, events_2024_02.csv are monthly partitions)
- Note any inconsistencies across files (different column counts, naming changes)

Write the results to `working/data_inventory_raw.md` as an intermediate output.

### Step 2: Profile Each Table/File
For each table or file discovered, compute:

**Shape and coverage:**
- Total row count
- Total column count
- Date range (min and max of any timestamp/date columns)
- Distinct count of key identifier columns (user_id, session_id, event_type, etc.)

**Column-level profiling (for each column):**
- Data type (string, integer, float, boolean, timestamp, etc.)
- Null count and null rate (as a percentage)
- Distinct value count
- For numeric columns: min, max, mean, median, standard deviation
- For categorical columns: top 10 most frequent values with counts
- For timestamp columns: min date, max date, any gaps in date coverage

**Execute this profiling using Python (pandas) or SQL depending on the data source type.** Write the actual code, run it, and capture the results. Do not estimate or guess — compute the real values.

### Step 2.5: Sanity Gate (Silent, Always-On)

After profiling, run lightweight boundary checks to catch obvious data problems before analysis begins. This gate is Tier 1 — zero additional queries, uses only the profile data already computed.

```python
from helpers.data_quality_extras import check_null_concentration

for table_name, df in profiled_tables.items():
    null_results = check_null_concentration(df)
    for r in null_results:
        if r["status"] == "FAIL":
            # Column is >95% null — flag as BLOCKER
            log_sanity_issue(table_name, r["column"], "BLOCKER", r["detail"])
        elif r["status"] == "WARN":
            log_sanity_issue(table_name, r["column"], "WARNING", r["detail"])
```

Additionally check for impossible values in the profile data:
- **Negative row counts or distinct counts** (data loading corruption)
- **Date ranges extending into the future** (clock skew or bad data)
- **Numeric columns where min > max** (impossible — profiling error)

If any BLOCKER-level issue is found, include it prominently in the data inventory report header. These issues carry forward as context for downstream agents.

This gate is **silent** — it does not produce a separate report or halt the pipeline. Its findings are folded into Step 3 (Data Quality) and Step 6 (Final Report).

### Step 3: Assess Data Quality
Apply the Data Quality Check skill (`.claude/skills/data-quality-check/skill.md`). For each table/file, check:

**Completeness:**
- Flag columns with >5% null rate as WARNING, >20% as BLOCKER
- Flag date ranges with missing days/weeks as WARNING
- Flag tables with unexpectedly low row counts as WARNING

**Consistency:**
- Check for duplicate rows (exact duplicates and near-duplicates on key columns)
- Verify referential integrity across tables (e.g., all user_ids in events exist in users)
- Check for data type mismatches (strings in numeric columns, dates formatted inconsistently)
- Check for impossible values (negative counts, future dates, percentages >100%)

**Distribution sanity:**
- Flag any column where >50% of values are a single value (low cardinality warning)
- Flag numeric columns with extreme outliers (>3 standard deviations from mean)
- Flag any sudden changes in data volume over time (potential tracking breakage)

Rate each finding with a severity:
- **BLOCKER**: Analysis will be wrong if this is not addressed (e.g., 80% nulls in a key column)
- **WARNING**: Results should be interpreted with caution (e.g., 10% nulls in a segmentation column)
- **INFO**: Worth noting but does not affect analysis (e.g., 0.1% duplicates)

### Step 4: Identify Tracking Gaps
Apply the Tracking Gap Identification skill (`.claude/skills/tracking-gaps/skill.md`):

**If {{ANALYSIS_GOALS}} is provided:**
- Extract the data requirements from the analysis goals (questions, hypotheses, or plain text)
- For each required data point, check if it exists in the inventory
- Classify each as: AVAILABLE (exists and is quality), PARTIAL (exists but quality issues), MISSING (not in the data), DERIVABLE (not directly present but can be computed from existing fields)
- For MISSING fields: suggest workarounds or alternative approaches
- For DERIVABLE fields: describe how to compute them (e.g., "session duration can be derived from timestamp of first and last event in a session")

**If {{ANALYSIS_GOALS}} is not provided:**
- Identify what common analytical questions this data CAN support based on the fields present
- Note obvious gaps: "This dataset has user events but no user attributes — segmentation by user properties won't be possible"
- Suggest what additional data would make the dataset more analytically useful

### Step 5: Generate Recommended Analyses
Based on the data inventory and quality assessment, recommend specific analyses:

**For each recommendation, specify:**
- **Analysis description**: One sentence describing what to investigate
- **Why this data supports it**: Which tables/columns make this feasible
- **Suggested approach**: Funnel analysis, segmentation, trend analysis, etc.
- **Agent to use**: Which agent would execute this (Descriptive Analytics Agent, Overtime/Trend Agent, etc.)
- **Caveats**: Any data quality issues that would affect this analysis

Generate 3-5 recommendations, ordered by the strength of data support (most feasible first).

**If {{ANALYSIS_GOALS}} is provided**, additionally map each goal to the available data and indicate whether it is fully supported, partially supported, or not supported.

### Step 5b: Record Lineage
Log this agent's data flow for traceability:

```python
from helpers.lineage_tracker import track

track(
    step=4,  # pipeline_step from CONTRACT
    agent="data-explorer",
    inputs=[str(DATA_SOURCE)],  # source files/tables explored
    outputs=["outputs/data_inventory_{{DATE}}.md"],
    metadata={"tables_profiled": len(tables), "total_rows": total_rows}
)
```

### Step 6: Compile the Data Inventory Report
Assemble all outputs into a single structured document following the Output Format below. Remove the intermediate file from `working/`.

## Output Format

A markdown file saved to `outputs/data_inventory_{{DATE}}.md` with this structure:

```markdown
# Data Inventory Report: {{DATA_SOURCE_NAME}}
**Generated:** {{DATE}}
**Source:** {{DATA_SOURCE}}
**Total tables/files:** [count]
**Date range:** [earliest date] to [latest date]
**Total rows across all tables:** [count]

## Executive Summary
[3-5 sentences: what data exists, its overall quality, and what it can support.
 Highlight any blockers. State the single most important finding about this data.]

## Table/File Inventory

### [Table/File 1 Name]
- **Rows:** [count]
- **Columns:** [count]
- **Date range:** [min] to [max]
- **Description:** [inferred description of what this table contains]

| Column | Type | Nulls | Null % | Distinct | Notes |
|--------|------|-------|--------|----------|-------|
| user_id | string | 0 | 0% | 45,231 | Primary identifier |
| event_type | string | 0 | 0% | 23 | Top: page_view (40%), click (25%) |
| timestamp | datetime | 12 | 0.01% | — | Range: 2024-01-01 to 2024-12-31 |
| revenue | float | 1,205 | 8.5% | — | Min: 0, Max: 9,999, Mean: 42.50 |
| ... | ... | ... | ... | ... | ... |

### [Table/File 2 Name]
[same structure]

## Data Quality Assessment

### Blockers
| Issue | Table | Column | Detail | Impact |
|-------|-------|--------|--------|--------|
| High null rate | events | user_segment | 35% nulls | Cannot segment 35% of users |

### Warnings
| Issue | Table | Column | Detail | Impact |
|-------|-------|--------|--------|--------|
| [issue] | [table] | [column] | [detail] | [impact] |

### Info
| Issue | Table | Column | Detail |
|-------|-------|--------|--------|
| [issue] | [table] | [column] | [detail] |

## Tracking Gap Analysis
[Only present if {{ANALYSIS_GOALS}} was provided]

| Required Data Point | Status | Source | Notes |
|--------------------|--------|--------|-------|
| [data point from goals] | AVAILABLE | events.column_name | Clean, ready to use |
| [data point from goals] | PARTIAL | users.segment | 35% nulls — use with caution |
| [data point from goals] | DERIVABLE | Compute from events.timestamp | session_duration = max(ts) - min(ts) per session |
| [data point from goals] | MISSING | — | Would need user survey data; workaround: use behavioral proxy |

## Recommended Analyses

### 1. [Analysis title]
- **Description:** [one sentence]
- **Data support:** [which tables/columns]
- **Approach:** [analysis type]
- **Agent:** [which agent to invoke]
- **Caveats:** [quality issues to watch]

### 2. [Analysis title]
[same structure]

### 3. [Analysis title]
[same structure]

## Entity Relationship Map
[If multiple tables exist, describe how they connect:]
- `users.user_id` → `events.user_id` (one-to-many)
- `events.product_id` → `products.product_id` (many-to-one)
- [Note any orphaned records: "1,203 events reference user_ids not in the users table"]

## Next Steps
1. [Address blockers — specific action items]
2. [Recommended first analysis to run]
3. [Data enrichment opportunities]
```

## Skills Used
- `.claude/skills/data-quality-check/skill.md` — for the completeness, consistency, and distribution checks in Step 3, including severity rating criteria (BLOCKER/WARNING/INFO)
- `.claude/skills/tracking-gaps/skill.md` — for the gap analysis in Step 4, including the AVAILABLE/PARTIAL/MISSING/DERIVABLE classification and workaround suggestions

## Validation
Before presenting the data inventory report, verify:
1. **Row counts are real, not estimated** — re-run a `COUNT(*)` or `len(df)` on each table/file and confirm the number in the report matches. Do not estimate row counts from file size.
2. **Null percentages are arithmetic-correct** — verify that null_count / total_rows = reported null percentage for at least 3 columns. Rounding errors are acceptable; order-of-magnitude errors are not.
3. **Date ranges are plausible** — check that the reported min and max dates are reasonable (not in the future, not before the product existed). Flag any date column where min/max seems wrong.
4. **All tables/files are accounted for** — count the tables/files discovered in Step 1 and confirm the same count appears in the report. Missing a table is a critical error.
5. **Quality severity ratings are consistent** — re-read each BLOCKER and confirm it meets the criteria (>20% nulls or analysis would be wrong). Ensure no WARNING should actually be a BLOCKER.
6. **Entity relationships are validated** — if the report claims table A joins to table B on a key, verify by checking that the join key exists in both tables and report the orphan rate.
7. **Recommendations reference real data** — each recommended analysis must cite specific tables and columns from the inventory. A recommendation that references non-existent data is invalid.
