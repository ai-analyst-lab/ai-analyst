---
name: datasets
description: List all connected datasets with their status, table counts, and last analysis date. Use this skill whenever the user invokes `/datasets`, or asks questions like "what datasets do I have?", "show me my data sources", "list datasets", "which datasets are connected?", "what data is available?", "show all datasets", "what datasets can I analyze?", "view my datasets", "what data sources are set up?", or any request to see what datasets exist in the system. Also trigger when users mention "switch dataset", "change dataset", "use a different dataset", or "what's my active dataset?" since seeing the list helps them choose. This is a foundational command that should be offered proactively whenever users seem unsure about what data they're working with or when they need to understand what datasets are available before starting analysis.
---

# Skill: Datasets

## Purpose
List all connected datasets with their status, table counts, and last analysis date.

## When to Use
Invoke as `/datasets` when the user wants to see what datasets are available.

## Instructions

### Step 1: Discover available datasets

The system supports two discovery paths:

**Path A: Registry-first** (preferred)
- Read `data_sources.yaml` to get the official list of registered sources
- If the file exists and has entries, use this as your source of truth

**Path B: Brain-first** (fallback when registry is empty)
- If `data_sources.yaml` is empty or missing, scan `.knowledge/datasets/` directory
- Each subdirectory represents a dataset (directory name = dataset ID)
- Read each dataset's `manifest.yaml` to get connection details and metadata

Use whichever path yields results. Many installations have datasets in `.knowledge/datasets/` but an empty `data_sources.yaml` registry — this is normal during initial setup or when datasets are added manually.

### Step 2: Read the active pointer

Read `.knowledge/active.yaml` to determine which dataset is currently active.

### Step 3: Enrich with manifest data

For each discovered dataset (whether from registry or directory scan), read `.knowledge/datasets/{name}/manifest.yaml` to get:
- `display_name` — human-readable name
- `connection.type` — connection type (csv, local_duckdb, snowflake, postgres, bigquery, motherduck)
- `connection.database` or other connection-specific fields
- `summary.table_count` — number of tables
- `summary.date_range` — temporal coverage (if available)
- `summary.row_counts` — per-table row counts (if profiled)
- `summary.last_updated` — when manifest was last written

If a manifest is missing or incomplete, show what you can determine from the directory structure and note that the dataset needs profiling.

### Step 4: Display the list

```
Connected Datasets:

  * your_dataset (active)
    Your Dataset Name — {table_count} tables, {date_range}
    Connection: {type} ({database})
    Analyses: 0

  - {other_dataset}
    {display_name} — {table_count} tables, {date_range}
    Connection: {type} ({details})
    Analyses: {count}

Commands:
  /switch-dataset {name}  — switch active dataset
  /connect-data           — connect a new dataset
  /data                   — inspect active dataset schema
```

Mark the active dataset with `*`. Mark others with `-`.

## Important Notes

1. **Security**: Never display connection credentials (tokens, passwords, API keys) — show only connection type and database/schema names
2. **Discovery**: If `data_sources.yaml` is empty but `.knowledge/datasets/` has content, scan the directory and show what's available — this is a normal state during development or manual dataset setup
3. **Incomplete manifests**: If a dataset directory exists but has no manifest or an incomplete manifest, include it in the list with status "Not yet profiled" and show whatever metadata is available
4. **Duplicate detection**: If you notice two datasets pointing to the same underlying data (same path or same database), mention this in a Notes section to help users clean up
