---
name: history
description: Browse and search past analyses from the knowledge system's analysis archive. Use this skill whenever the user invokes `/history` or variants like `/history search=X`, `/history {id}`, `/history --all`, `/history dataset=X`, or asks questions about their analytical work history such as "what have I analyzed before?", "what analyses have I run?", "show me past work", "show my history", "what have we looked at?", "what questions have I answered?", "can I see my analysis history?", "list my analyses", "what did I work on last week?", "have I analyzed X before?", "find analyses about Y", or mentions reviewing prior analyses, checking if similar work was already done, needing context on previous findings, or wants to build on past work. This skill also applies automatically at session start when you need context on the user's analytical history to inform current work. When displaying history, ALWAYS filter to the active dataset unless the user explicitly requests --all or dataset={id}.
---

# Skill: History

## Purpose
Browse and search past analyses from the analysis archive. Helps users
recall what they've analyzed before, find prior findings, and build on
previous work.

## When to Use
- User says `/history` or "what have I analyzed before?"
- At session start, to provide context on prior work
- When framing a new question, to check if similar analysis exists

## Invocation
`/history` — list recent analyses (last 10)
`/history {id}` — show full details for a specific analysis
`/history search={term}` — search by title, question, or tags
`/history --all` — list all analyses across all datasets
`/history dataset={id}` — filter to a specific dataset

## Instructions

### Step 1: Load Archive
1. Read `.knowledge/analyses/index.yaml`
2. If empty: "No analyses archived yet. Complete an analysis and it will appear here."

### Step 2: Determine Active Dataset (Critical)
**IMPORTANT:** Before filtering results, determine the active dataset:

1. Read `.knowledge/active.yaml` to get the active dataset ID
2. If `--all` flag is present: skip filtering, show all datasets
3. If `dataset={id}` is specified: filter to that dataset
4. Otherwise: **filter to active dataset only**

This ensures users see relevant analyses for their current working context by default.

### Step 3: Execute Command

**List recent (`/history`):**
- **Filter to active dataset** (unless `--all` flag present)
- Sort by date descending
- Show last 10 as a table: date, title, level, key finding count, dataset
- Show total count: "Showing 10 of {total} analyses for {dataset_name}." (or "across all datasets" if --all)

**Show specific (`/history {id}`):**
- Find entry by ID in index
- Display: title, date, question, level, all key findings, metrics used,
  agents used, output files, tags, confidence, recommendations
- **If output files exist**, offer: "Want to review the full analysis? The deck is at {path}"

**Search (`/history search={term}`):**
- **Filter to active dataset first** (unless `--all` or `dataset={id}` specified)
- Search across: title, question, key_findings, tags (case-insensitive)
- Display matching entries as a table
- If no matches: "No analyses match '{term}' in {dataset_name}. Try broader terms or use `--all` to search across all datasets."

**All datasets (`/history --all`):**
- Include dataset_id column in output
- Sort by date descending across all datasets

### Step 4: Contextual Suggestions
After displaying history:
- "Want to re-run this analysis with fresh data?"
- "Want to build on finding #{n}?"
- If recent analysis was partial: "This analysis was incomplete. Resume with `/resume-pipeline`."

## Edge Cases
- **No active dataset:** Show all analyses or prompt to connect
- **Archive file missing:** Create empty index
- **Analysis output files deleted:** Note "output files no longer available"
- **Very long history (>100):** Paginate, show 20 at a time

## Why This Matters

**Dataset filtering** ensures users see relevant analyses for their current working context. A user analyzing one dataset shouldn't see unrelated-dataset analyses by default — it creates noise and makes it harder to find relevant prior work. The `--all` flag is available when cross-dataset comparison is needed.

**Contextual offers** ("Want to review the full analysis?") help users take action on the information. Simply listing file paths isn't enough — explicitly offering next steps makes the history actionable.

**Consistent table format** allows quick scanning. Users browse history to find patterns, check if work was done before, or locate specific analyses. Tables are faster to scan than prose paragraphs.
