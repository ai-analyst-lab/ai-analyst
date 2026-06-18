---
name: switch-dataset
description: |
  Change the active dataset to switch between different data sources for analysis. Use this skill whenever the user wants to analyze a different dataset, switch to another database, change data sources, work with different tables, or explicitly invokes /switch-dataset. This skill handles the full switch workflow: validating the target dataset exists, checking for in-progress work that might be lost, updating the active pointer, and confirming the switch with a summary of the new dataset. Apply when users say things like "switch to sales data", "use the other dataset", "change to production database", "work with the marketing tables instead", "let's look at last month's data instead", "/switch-dataset analytics", or any request to change which dataset is currently being analyzed. Also trigger when starting a new analysis if the user mentions a dataset name that differs from the currently active one.
---

# Skill: Switch Dataset

## Purpose
Change the active dataset. Updates the active pointer, validates the target dataset exists, and confirms with a summary of what's now active.

## When to Use
Invoke as `/switch-dataset {name}` when the user wants to analyze a different dataset than the currently active one.

## Instructions

### Step 1: Validate the target dataset

1. List available datasets by checking `.knowledge/datasets/` directory for subdirectories with `manifest.yaml` files
2. Normalize the target name to lowercase for comparison (handles SALES-DATA → sales-data)
3. If `{name}` matches exactly (case-insensitive), proceed to Step 2
4. If not found, try fuzzy matching:
   - Check if `{name}` is a substring of any dataset name (e.g., "marketing" would match "marketing-prod")
   - Case-insensitive partial match
   - If exactly one match found, use that dataset and inform user: "Matched '{name}' to '{actual_dataset_name}'"
   - If multiple matches found, list all matches and ask user to choose
5. If still not found, list all available datasets with brief descriptions (from manifests) and ask user to choose or suggest running `/connect-data` to add a new dataset

### Step 2: Check if already active

1. Read `.knowledge/active.yaml` to get the current `active_dataset`
2. If `{name}` matches the current active dataset (case-insensitive):
   - Inform the user: "The {name} dataset is already active."
   - Display the current dataset summary (same format as Step 6)
   - List other available datasets they could switch to instead
   - STOP here (do not proceed to Step 3)

### Step 3: Validate the data brain exists

1. Check that `.knowledge/datasets/{name}/manifest.yaml` exists
2. If it doesn't exist, suggest: "Dataset '{name}' directory exists but has no manifest. Run `/connect-data` to set it up."
3. If manifest is missing, STOP (do not proceed)

### Step 4: Check for in-progress work (CRITICAL SAFETY CHECK)

This step prevents accidental loss of analytical work. When you switch datasets, files in `working/` become contextually orphaned — they contain SQL queries, charts, and data tied to the OLD dataset's schema and tables, which won't match the NEW dataset's structure. This doesn't delete the files, but it makes resuming that work much harder because the context has changed.

**Why explicit confirmation is required:** Users often have hours of work in the working/ directory. A dataset switch mid-analysis can make that work difficult or impossible to resume without manually reconnecting the artifacts to the original dataset.

1. List all files in `working/` directory (exclude `.gitkeep` and hidden files like `.DS_Store`)
2. If 3 or more files exist:
   - Warn: "⚠️  You have {count} files in progress for {old_dataset}, including: [list first 3-5 files]. Switching datasets now may make that work harder to resume. Continue anyway?"
   - Provide two explicit options:
     - "Type 'yes' to proceed with the switch"
     - "Type 'no' to cancel and stay on {old_dataset}"
   - HALT and wait for user response
   - If user says "no" or "cancel" or "wait": STOP immediately and inform them the switch was cancelled
   - If user says "yes" or "continue" or "proceed": Continue to Step 5
3. If fewer than 3 files exist, proceed directly to Step 5 (no confirmation needed — minimal risk of context loss)

### Step 5: Update the active pointer

1. Read `.knowledge/active.yaml`
2. Update `active_dataset` to `{name}` (use the exact case from the manifest)
3. Write updated `.knowledge/active.yaml`

### Step 6: Confirm the switch

Read the target dataset's `manifest.yaml` and display a confirmation summary using this format:

```
✓ Switched to: {name}
Tables: {count of tables in manifest}
Date range: {date_range.start} to {date_range.end} (or "not specified" if missing)
Connection: {connection_type}
Last analysis: {last_used or "never"}
Row counts: {summary of top 3 tables by row count with table names, or list all if ≤3 tables}
```

**Example:**
```
✓ Switched to: analytics_prod
Tables: 6
Date range: 2024-01-01 to 2026-03-31
Connection: snowflake
Last analysis: 2026-04-01
Row counts: fct_orders (245K), fct_sessions (1.2M), dim_users (89K)
```

If the user had in-progress work and proceeded anyway, add a reminder for how to switch back:
```
→ To return to {old_dataset}, run: /switch-dataset {old_dataset}
```

## Anti-Patterns

1. **Never silently switch** — always confirm with a summary
2. **Never skip the in-progress work check** — if working/ has 3+ artifacts, HALT and require explicit user confirmation before proceeding
3. **Never infer the dataset** — only switch when explicitly requested via this skill
4. **Never fail on case mismatch** — normalize to lowercase for comparison (SALES-DATA should match sales-data)
5. **Never assume data_sources.yaml exists or is populated** — it may be empty, use `.knowledge/datasets/` directory listing as source of truth
6. **Never re-switch to an already-active dataset** — detect this in Step 2 and inform user instead of performing redundant operations
