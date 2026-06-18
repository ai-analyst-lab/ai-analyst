---
name: archive-analysis
description: Save completed analyses to the knowledge system's analysis archive for future reference. Use this skill after completing any L3+ analysis, when `/run-pipeline` completes, when the user explicitly says "save this analysis" or "archive this", or automatically at the end of Step 18 (Close the Loop) in the analysis workflow. This skill captures key findings, metrics used, agents invoked, and output file paths so past work can be referenced in future sessions. Trigger whenever you finish validation on a multi-step analysis, complete an analytical deck, wrap up a root cause investigation, finish an opportunity sizing exercise, or close any analysis that produced deliverables worth preserving. Also apply when the user mentions saving work, archiving results, preserving findings, or wants to ensure an analysis can be recalled later. This is your analytical memory system — use it proactively to build institutional knowledge.
---

# Skill: Archive Analysis

## Purpose
Save a completed analysis to the knowledge system's analysis archive for
future recall. Captures key findings, metrics used, agents invoked, and
output file paths so that past work can be referenced in future sessions.

## When to Use
- After completing an L3+ analysis (post-validation)
- After `/run-pipeline` completes successfully
- User says "save this analysis" or "archive this"
- Automatically triggered at the end of Step 18 (Close the Loop)
- **VERIFICATION MODE:** User says "verify the archive" or "show me what was captured" — read existing entry, don't create new

## Instructions

### Step 0: Determine Mode

Check if this is an **archive request** (create new entry) or a **verification request** (read existing entry).

**Verification signals:**
- User says "verify", "check", "show me what was captured", "did it save", "was it archived"
- User mentions pipeline "auto-saved" or "already completed"
- No new findings mentioned — just wants to see what's already there

**If verification:** Skip to Verification Mode (below). Otherwise, proceed to Step 1.

### Step 1: Gather Analysis Metadata from Session Context

**IMPORTANT: Capture only what the user explicitly mentioned or what exists in actual files. DO NOT invent:**
- Findings not stated by the user
- Metrics not mentioned in the analysis
- Files not actually present in outputs/ or working/
- Validation grades if validation wasn't run
- Business impact estimates unless explicitly provided
- Detailed analysis steps or methodology not mentioned

**DO NOT fabricate or invent session details.** Extract metadata from actual files and session history.

**Where to look:**

1. **Pipeline state** — Read `working/session_state.yaml` if it exists (contains pipeline progress, agents run, resume instructions)
2. **Active dataset** — Read `.knowledge/active.yaml` for dataset ID
3. **Output files** — Scan `outputs/` and `working/` directories for artifacts created in this session (use `ls -lt` to find recent files)
4. **Validation report** — Look for `working/validation_report.md` or `working/validation_summary.json` for confidence grade
5. **User's stated findings** — If user provides key findings in their request, use those verbatim

**What to extract:**

1. **Title:** Derive from the original question or business context (check session history for the initial analytical question)
2. **Question:** The original user question (look back in conversation for the first analytical request)
3. **Question level:** From the Question Router classification (L1-L5) — check if router was invoked
4. **Dataset ID:** From `.knowledge/active.yaml`
5. **Key findings:**
   - If validation report exists, extract from there
   - Otherwise, check `working/analysis_summary.md` or `outputs/narrative.md`
   - If nothing exists, use findings the user mentioned in their archive request
   - Format as single-sentence bullets with numbers
6. **Metrics used:**
   - Check validation report or analysis summary for metric references
   - Scan SQL queries in `working/*.sql` for column names
   - Match against `.knowledge/metrics/index.yaml` if available
7. **Agents used:**
   - Read `working/session_state.yaml` if pipeline was used
   - Check conversation history for agent invocations (look for "Task" tool uses)
   - List in execution order
8. **Output files:**
   - Run `ls -lt outputs/ working/ | head -20` to find recent files
   - Filter for files created during this session (check timestamps)
   - Include both deliverables (outputs/) and working files (working/)
   - **ONLY list files that actually exist** — check the directory before listing
   - If no files exist or user didn't mention any outputs, set `output_files: []`
   - DO NOT invent file names or list files from unrelated analyses
9. **Tags:** Auto-generate from:
   - Keywords in the original question (mobile, checkout, seasonal, etc.)
   - Metric names used
   - Dataset name
   - Analysis type (funnel, root-cause, segmentation, etc.)
10. **Confidence:**
    - Read from `working/validation_report.md` or `working/validation_summary.json`
    - If validation was not run, set to `null` and note it

**If actual files don't exist:** Create the archive with whatever metadata is available. Mark it as `partial: true` if deliverables are missing.

### Step 2: Create Archive Entry

1. **Read the schema:** `.knowledge/analyses/_schema.yaml` to understand required/optional fields
2. Generate a unique ID: `analysis_{YYYYMMDD}_{HHMMSS}` (use current timestamp)
3. Build the entry dict following the schema structure

Example entry format:

```yaml
- id: analysis_20260403_232623
  title: "Mobile checkout conversion drop investigation"
  date: "2026-04-03"
  dataset: {active_dataset}
  question: "What caused the conversion rate drop and how does it relate to the mobile checkout flow?"
  question_level: L4
  findings:
    - "Mobile checkout flow has significant usability issues causing conversion drop"
    - "Checkout funnel shows critical drop-off points in mobile experience"
    - "Conversion rate varies significantly by device type"
    - "Mobile optimization is required to recover lost conversions"
  metrics:
    - conversion_rate
    - checkout_completion
    - funnel_drop_off
    - device_segmentation
  agents:
    - question-framing
    - data-explorer
    - descriptive-analytics
    - root-cause-investigator
    - validation
    - chart-maker
  output_files:
    - outputs/checkout_conversion_analysis.png
    - outputs/conversion_funnel_chart.png
    - working/checkout_funnel_analysis.png
  tags:
    - conversion
    - mobile
    - checkout
    - funnel-analysis
    - root-cause
  confidence: B
  partial: false
```

### Step 3: Append to Index
1. Read `.knowledge/analyses/index.yaml`
2. If file doesn't exist, create it from template:
   ```yaml
   analyses: []
   total_analyses: 0
   last_updated: null
   ```
3. Append the new entry to the `analyses` list
4. Increment `total_analyses`
5. Update `last_updated` to current date (YYYY-MM-DD)
6. Write back to `index.yaml`

### Step 4: Update Dataset Stats
1. Read `.knowledge/datasets/{active}/manifest.yaml`
2. Increment `analysis_count`
3. Update `last_used` to current date
4. Write back

### Step 5: Confirm
Report to user:
```
Analysis archived: {title}
ID: {id}
Findings: {count} key findings captured
Use `/history` to browse past analyses.
```

### Step 6: Capture to Query Archaeology (Optional)

**When to apply:** Only for completed analyses (not partial) with confidence grade B or better.

After archiving, check if the analysis produced reusable patterns worth saving
to `.knowledge/query-archaeology/curated/` via `helpers/archaeology_helpers.py`.

1. **SQL patterns** — If validated SQL queries exist in `working/*.sql`:
   - Ask: "Would you like to save any SQL patterns from this analysis?"
   - Offer to capture via `capture_cookbook_entry(title, sql, dataset, tables, tags)`
   - Only capture queries that passed tie-out or validation checks

2. **Table knowledge** — If the analysis revealed useful table metadata:
   - Offer to capture/update via `capture_table_cheatsheet(table_name, dataset, grain, primary_key, common_filters, gotchas, common_joins)`
   - Include grain, primary key, common filters, gotchas, and common joins

3. **Join patterns** — If the analysis used non-obvious joins:
   - Offer to capture via `capture_join_pattern(tables, join_sql, cardinality, validated, dataset)`
   - Record cardinality and whether the join was validated

**Rules for this step:**
- Ask the user: "Would you like to save any SQL patterns from this analysis?"
- If the user declines or there are no reusable patterns, skip silently
- Only offer for analyses with confidence grade B or better
- Never auto-capture without user confirmation

## Verification Mode

**When user wants to verify an existing archive (not create a new one):**

1. Read `.knowledge/analyses/index.yaml`
2. Find the most recent entry (highest index, latest date)
3. Display what was captured:
   - Analysis ID and title
   - Date archived
   - Key findings (list them)
   - Metrics used
   - Agents invoked
   - Output files preserved
   - Tags
   - Confidence grade
4. Confirm dataset manifest was updated
5. Report archive stats (total analyses, last updated)

**Do NOT create a new archive entry in verification mode.**

Report format:
```
Archive verified: {title}
ID: {id}
Status: Successfully archived on {date}

Captured:
- {count} key findings
- {count} metrics tracked
- {count} agents used
- {count} output files preserved

Use `/history` to browse all past analyses.
```

## Rules
1. **Never overwrite an existing archive entry** — always append
2. **Never fabricate session context** — read from actual files or use what the user provided
3. Key findings should be one sentence each, factual, with numbers where possible
4. Tags should be lowercase, no spaces (use hyphens)
5. If validation was not run, set confidence to null and note it
6. Archive even partial analyses — mark as `partial: true`
7. **Verification requests don't create new entries** — read and report existing archives
8. **DO NOT create standalone analysis markdown files or archive directories** — the archive system stores metadata in `index.yaml` only. Output files remain in their original locations (`outputs/`, `working/`) and are referenced by path in the `output_files` array. DO NOT copy or duplicate artifacts.

## Edge Cases
- **No outputs exist:** Set `output_files: []`, do not invent file names. Archive with metadata only.
- **Pipeline was interrupted:** Archive what's available, mark as `partial: true`, document reason in a `reason_incomplete` field
- **Duplicate question:** Still archive — different runs may find different things
- **Analysis index doesn't exist:** Create it from template
- **User says 'verify' but no archive exists:** Report "No archive found. Would you like to create one?" and proceed to archive mode if confirmed
- **Session state files don't exist:** Use conversation history and user-provided metadata to build the archive entry
- **User mentioned files but they don't exist:** Only list files that actually exist in outputs/ or working/. If the user mentioned output files but they're not present, note in confirmation: "Files mentioned but not found: {list}"
