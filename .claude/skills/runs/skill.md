---
name: runs
description: Browse, inspect, compare, and clean up past pipeline runs. This skill is your window into analysis history — every `/run-pipeline` execution creates a tracked run with its own working directory, outputs, and state. Use this skill whenever the user wants to see what analyses have been executed, review past work, compare different approaches to the same problem, or clean up old runs. Trigger on phrases like "/runs", "show me my past analyses", "what analyses have I run?", "list my pipeline runs", "show run history", "what did we analyze last week?", "compare these two analyses", "clean up old runs", "show me the latest run", "what was that analysis we did on [dataset]?", "review past work", "show me completed analyses", or any mention of viewing, listing, comparing, or managing previous pipeline executions. Also trigger when users reference a specific analysis by date or dataset name and want to see its details. This skill provides critical context for iterative analytical work — users often need to revisit, compare, or build on previous analyses rather than starting from scratch every time.
---

# Skill: Runs

## Purpose
Browse, inspect, compare, and clean up past pipeline runs. Each run is a
self-contained directory under `working/runs/` with its own working files,
outputs, and pipeline state.

## Architecture: Understanding the Two-Source System

The AI Analyst tracks analysis work in **two independent locations**:

1. **Active Pipeline Runs** (`working/runs/`)
   - Contains in-progress, recently completed, or failed pipeline executions
   - Each run is a directory with `pipeline_state.json` tracking agent progress
   - Used for resuming interrupted work and debugging issues
   - Cleaned up periodically (30-day retention by default)

2. **Archived Analyses** (`.knowledge/analyses/`)
   - Contains completed analyses that have been formally archived
   - Includes validation grades, key findings, and links to outputs
   - Permanent knowledge base for organizational learning
   - Survives even after working/runs/ cleanup

**Why this matters:** A user asking "what analyses have I run?" expects to see BOTH in-progress work (working/runs/) AND completed archived work (.knowledge/analyses/). Missing either source gives an incomplete picture.

## When to Use
- User says `/runs`, `/runs list`, `/runs latest`, `/runs clean`, or `/runs compare`
- When the user wants to see what analyses have been executed

## Invocation
- `/runs` or `/runs list` -- list all past runs
- `/runs latest` -- show details of the most recent run
- `/runs {id}` -- show details of a specific run (partial match supported)
- `/runs clean` -- remove runs older than 30 days (confirmation required)
- `/runs compare {id1} {id2}` -- compare two runs side by side

## Instructions

### Step 1: Determine Command Type

Parse the user's command to understand which operation they want:
- **List:** `/runs` or `/runs list` → requires dual-source scanning
- **Latest:** `/runs latest` → single source (working/latest symlink)
- **Detail:** `/runs {id}` → single source (working/runs/)
- **Compare:** `/runs compare {id1} {id2}` → single source (working/runs/)
- **Clean:** `/runs clean` → single source (working/runs/)

### Step 2: Execute Based on Command Type

#### List Command (`/runs` or `/runs list`)

**This command requires scanning BOTH sources.** Follow this exact sequence:

1. **Scan Source 1: Active Pipeline Runs** (`working/runs/`)
   - Check if directory exists: `ls working/runs/`
   - If missing or empty, note "No active pipeline runs found"
   - If present, list subdirectories
   - For each run directory (format: `{YYYY-MM-DD}_{DATASET}_{SHORT_TITLE}/`):
     - Read `pipeline_state.json` to extract:
       - `pipeline_id`, `dataset`, `question`, `status`
       - `started_at`, `completed_at`
       - `steps` (agent status map to compute completed/total counts)
     - If `pipeline_state.json` is missing/corrupted, infer:
       - Status: `unknown`
       - Date/dataset from directory name

2. **Scan Source 2: Archived Analyses** (`.knowledge/analyses/`)
   - Check if file exists: `ls .knowledge/analyses/index.yaml`
   - If missing, note "No archived analyses found"
   - If present, read `.knowledge/analyses/index.yaml`
   - Extract for each analysis:
     - `id`, `date`, `dataset`, `title`, `status`, `validation_grade`, `key_findings`
   - Note: Archived analyses may not have agent counts (show "N/A" if unavailable)

3. **Merge and Deduplicate**
   - Combine results from both sources
   - If the same analysis appears in both (check by date + dataset + title match), show it once with status from working/runs/ (more current)

4. **Display Merged Table**

Display TWO sections sorted by date descending:

```
## Active Pipeline Runs (working/runs/)

| # | Date       | Dataset   | Title                    | Status    | Agents |
|---|------------|-----------|--------------------------|-----------|--------|
| 1 | 2026-02-23 | acme-analytics | why-revenue-dropped-q3   | completed | 14/14  |
| 2 | 2026-02-21 | acme-analytics | activation-funnel-deep   | failed    | 8/14   |

## Archived Analyses (.knowledge/analyses/)

| # | Date       | Dataset   | Title                    | Grade | Status    |
|---|------------|-----------|--------------------------|-------|-----------|
| 1 | 2026-02-19 | hero      | churn-by-segment         | A     | completed |
| 2 | 2026-02-15 | hero      | feature-impact-nov       | B+    | completed |

Total: {N} runs found. Use `/runs {#}` or `/runs {title}` for details.
```

The `Agents` column shows `{completed}/{total}` from the pipeline_state steps map.

**Error handling:**
- If `working/runs/` doesn't exist: Show only archived analyses with note "No active runs found. Use /run-pipeline to create one."
- If `.knowledge/analyses/index.yaml` doesn't exist: Show only active runs with note "No archived analyses yet."
- If both are missing: "No analyses found. Use /run-pipeline to start your first analysis."

#### Latest Command (`/runs latest`)

Read the `working/latest` symlink to determine which run is latest:

```bash
# Read the symlink target
ls -l working/latest
# Or use readlink if available
readlink working/latest
```

The symlink points to a run directory (e.g., `working/runs/2026-04-03_<dataset>_checkout-feature-impact/`). Extract the run directory name from the symlink target and display the detail view for that run (same format as `/runs {id}` below).

**Error handling:**
- If `working/latest` doesn't exist: "No active pipeline runs found. Use /run-pipeline to start one."
- If symlink is broken: "Latest run symlink is broken. Use /runs list to see available runs."

#### Detail Command (`/runs {id}`)

Match `{id}` against run directory names (supports partial match -- e.g.,
`/runs acme-analytics` matches the most recent acme-analytics run). Display:

```
Run: {directory_name}
Status: {status}
Dataset: {dataset}
Question: {question}
Started: {started_at}
Completed: {completed_at} ({duration})

Agent Status:
  completed: {list}
  failed: {list with errors}
  skipped: {list}
  pending: {list}

Output Files:
  - {RUN_DIR}/outputs/{file1}
  - {RUN_DIR}/outputs/{file2}
  ...

Confidence: {grade from validation if available}
```

If the run has a validation report in `outputs/` or `working/`, extract and show the confidence grade.

**Error handling:**
- If no match found: "No run matching '{id}' found. Use /runs list to see available runs."
- If multiple matches: List all matches and ask user to be more specific

#### Clean Command (`/runs clean`)

1. Scan `working/runs/` for runs older than 30 days (based on directory date prefix)
2. List them and ask for confirmation:
   ```
   Found {N} runs older than 30 days:
     - {dir1} (completed, {date})
     - {dir2} (failed, {date})

   Delete these runs? This cannot be undone. [y/N]
   ```
3. On confirmation, remove the directories using `rm -rf`
4. If `working/latest` pointed to a deleted run, remove the symlink

**Error handling:**
- If no old runs found: "No runs older than 30 days found. Nothing to clean."

#### Compare Command (`/runs compare {id1} {id2}`)

1. Match `{id1}` and `{id2}` against run directory names (partial match supported)
2. Load `pipeline_state.json` from both runs
3. Optionally load key output files (analysis reports, validation reports) if available

Display comparison table:

```
Comparing Runs:
  A: {dir1}
  B: {dir2}

| Dimension          | Run A              | Run B              |
|--------------------|--------------------|--------------------|
| Date               | {date_a}           | {date_b}           |
| Dataset            | {dataset_a}        | {dataset_b}        |
| Status             | {status_a}         | {status_b}         |
| Agents completed   | {count_a}          | {count_b}          |
| Confidence grade   | {grade_a}          | {grade_b}          |
| Charts generated   | {chart_count_a}    | {chart_count_b}    |
| Key findings       | {finding_count_a}  | {finding_count_b}  |
| Duration           | {duration_a}       | {duration_b}       |
```

If both runs analyzed the same dataset, also compare:
- Top 3 findings from each (extracted from analysis reports in `outputs/`)
- Any metrics that differ significantly

**Error handling:**
- If either ID doesn't match: "Cannot find run '{id}'. Use /runs list to see available runs."
- If partial match is ambiguous: List matches and ask user to be more specific

## Edge Cases
- **No runs directory:** Report "No pipeline runs found. Use `/run-pipeline` to start one."
- **Empty runs directory:** Same message as above
- **Corrupted pipeline_state.json:** Show run with `status: unknown`, note the error: "Warning: pipeline_state.json is corrupted or unreadable"
- **Partial match ambiguity:** If multiple runs match, list them and ask user to be more specific: "Multiple runs match '{id}': [list]. Please specify."
- **Legacy runs (no run directory):** Note: "Found legacy `working/pipeline_state.json` -- not in per-run format. Use `/run-pipeline` to create a tracked run."
