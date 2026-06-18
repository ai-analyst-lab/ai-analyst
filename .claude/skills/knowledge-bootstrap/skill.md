---
name: knowledge-bootstrap
description: Initialize all knowledge subsystems at session start to load active dataset context, user profile, corrections, learnings, query archaeology, and analysis history into working memory. Use this skill automatically at the start of EVERY new session, immediately after the conversation begins. Also trigger after `/connect-data` or `/switch-dataset` to reload dataset context. Apply when the system detects missing or stale knowledge files, when returning to the tool after a break, during session initialization, at the beginning of any conversation, when Claude Code first starts, when a new Claude conversation opens, or at any session boundary. This skill is critical for contextual awareness — it ensures you understand the user's data environment, preferences, and past work before beginning any analysis. Without running this skill at session start, you lack essential context about what dataset is active, what the user prefers, and what corrections have been logged. Always run this skill first, before responding to any analytical request. Even if the user's first message is a simple question like "what's our conversion rate?", you MUST bootstrap knowledge context before answering so you know which dataset to query and what format the user expects. Make this skill your default session initialization behavior — treat it like loading configuration at startup. If you're ever unsure whether a session just started, err on the side of running bootstrap. The skill gracefully handles missing files, so running it unnecessarily is harmless, but skipping it when needed breaks contextual continuity.
---

# Skill: Knowledge Bootstrap

## Purpose
Initialize all 7 knowledge subsystems for a new session. Loads setup state,
dataset, user profile, integrations, org context, corrections, learnings,
query archaeology, and analysis archive into working memory.

## When to Use
- At the start of any session
- After `/connect-data` or `/switch-dataset`
- When the system detects missing or stale knowledge files

## Instructions

Load each subsystem in order. Every file read MUST gracefully degrade: if the
file does not exist, skip silently and note "not yet populated" in the summary.
Never block the session on a missing subsystem.

### Step 1: Setup State
Read `.knowledge/setup-state.yaml`.
- Parse `setup_complete` and count phases with `status: "complete"`.
- If `setup_complete: false`, note incomplete phases to offer `/setup`.
- **If missing:** Note "Setup: not initialized -- offer /setup".

### Step 2: Active Dataset
Read `.knowledge/active.yaml`.
- If `active_dataset` is null or missing, note "No active dataset" and continue.
- If set, load from `.knowledge/datasets/{active}/`:

| File | Required | If Missing |
|------|----------|------------|
| `manifest.yaml` | Yes | Note "manifest missing -- not usable" |
| `schema.md` | Yes | Generate via `schema_to_markdown()` or profiling |
| `quirks.md` | No | Create empty template |
| `metrics/index.yaml` | No | Count as 0 |

**Schema generation if `schema.md` is missing (REQUIRED):**

The schema is critical for SQL queries and analysis — never proceed without it.
Follow this sequence:

1. Check `data/schemas/{active}.yaml` — if found, import `schema_to_markdown()` from `helpers/schema_helpers.py` and generate schema.md
2. If no YAML schema file exists, use `get_connection_for_profiling()` to query the live database and generate schema.md from introspection
3. For CSV datasets, read the first 1000 rows of each file with pandas, infer dtypes, and write schema.md with table/column/type info
4. Staleness check: if `last_profile.md` exists and is newer than `schema.md`, regenerate

After generation, write schema.md to `.knowledge/datasets/{active}/schema.md` so future sessions can load it directly.

**System variables from manifest:**

Extract these variables for use in SQL queries and agent prompts:
- `{{SCHEMA}}` — Schema prefix for external warehouses (e.g., "analytics", "prod")
- `{{DISPLAY_NAME}}` — User-friendly dataset name for status messages
- `{{DATE_RANGE}}` — Available date range (e.g., "2024-01-01 to 2026-03-31")
- `{{DATABASE}}` — Database name or connection string

Use `{{SCHEMA}}` as a prefix in SQL queries when querying external warehouses (BigQuery, Snowflake, Postgres). For local DuckDB/CSV, it's typically null.

### Step 3: User Profile
Read `.knowledge/user/profile.md`.
- **If exists:** Apply `Detail level`, `Chart preference`, `Narrative style`.
- **If missing:** Create from template (see below), note "Profile: new".

On explicit user corrections during session, update the profile:
append `YYYY-MM-DD | Assumed [X] | User prefers [Y]` to the Corrections Log
section. Never infer from silence.

### Step 4: User Integrations
Read `.knowledge/user/integrations.yaml`.
- Extract `preferred_export_format`, `communication.detail_level`.
- Count configured channels (`configured: true`).
- **If missing:** Note "Integrations: not configured -- defaults apply".

### Step 5: Organization Context
Check for org ID in `setup-state.yaml` (`phases.phase_3_business.data.organization_id`)
or in the active dataset manifest's `organization` field.

If an org ID exists and is not `_example`:
- Read `.knowledge/organizations/{org_id}/manifest.yaml` for name, industry.
- Read `.knowledge/organizations/{org_id}/business/index.yaml` for section counts
  (glossary terms, products, metrics, objectives, teams).
- **If org dir missing:** Note "Org: linked but not found".

If no org linked: Note "Org: not configured".

### Step 6: Corrections
Read `.knowledge/corrections/index.yaml`.
- Extract `total_corrections` and `by_severity` counts.
- If `total_corrections > 0`, highlight critical/high counts so agents check
  the full log before writing SQL.
- **If missing:** Note "Corrections: not yet populated".

### Step 7: Learnings
Read `.knowledge/learnings/index.md`.
- Scan for category headings (`### N. Category Name`).
- Note which categories have content entries vs are empty.
- Do NOT load full content -- just category presence.
- **If missing:** Note "Learnings: not yet populated".

### Step 8: Query Archaeology
Read `.knowledge/query-archaeology/curated/index.yaml`.
- Extract `cookbook_entries`, `table_cheatsheets`, `join_patterns` counts.
- **If missing:** Note "Archaeology: not yet populated".

### Step 9: Analysis Archive
Read `.knowledge/analyses/index.yaml`:
- Extract `total_analyses` and last 5 entries (title, date, findings count, level).
- **If most recent analysis was <24h ago:** Add to user-facing status as "Recent work: [title] from [date]" and suggest "Want to build on your recent analysis?" This helps users pick up where they left off.

Read `.knowledge/analyses/_patterns.yaml`:
- Count `patterns[]` entries and note pattern names if any.
- **If missing:** Note "Patterns: not yet populated".

### Step 10: Mark Bootstrap Complete

Write a completion signal so agents can check if bootstrap already ran this session:

```python
import yaml
from datetime import datetime

timestamp = datetime.now().isoformat()
with open('.knowledge/.bootstrap_timestamp', 'w') as f:
    yaml.dump({'last_bootstrap': timestamp, 'status': 'complete'}, f)
```

This prevents redundant re-runs mid-session. To check if bootstrap is needed, read this file and compare timestamps — if <5 minutes old, skip re-running.

### Step 11: Report Readiness

Compile an **internal context summary** (held in working memory, not shown raw):

```
Setup: {complete (N/M phases) | incomplete (list missing) | not initialized}
Dataset: {display_name} ({source_type}, {N} tables, ~{rows} rows, {date_range}) | not configured
Profile: {role}, {detail_level} | new
Integrations: {preferred_format}, {N} channels | not configured
Org: {company} ({industry}), {N} glossary, {N} products, {N} metrics | not configured
Corrections: {N} logged ({N} critical, {N} high) | none
Learnings: {N}/{6} categories populated | not yet populated
Archaeology: {N} cookbook, {N} cheatsheets, {N} join patterns | not yet populated
Archive: {N} analyses, {N} recurring patterns | none
```

Then output the **user-facing status**:

```
Dataset: {display_name} ({source_type})
Tables: {N} tables, ~{row_count} rows
Date range: {date_range}
Metrics: {M} defined
Profile: {loaded | new}
Status: Ready for analysis
```

If a critical subsystem is missing (no dataset, no manifest), adjust the status
and suggest `/connect-data` or `/setup`.

---

## User Profile Template

```markdown
# User Profile

Auto-created by knowledge bootstrap. Updated as the system learns preferences.

## Role & Expertise
- **Role:** _[auto-detected or user-specified]_
- **Technical level:** _[beginner | intermediate | advanced]_
- **SQL comfort:** _[none | basic | intermediate | advanced]_
- **Statistics comfort:** _[none | basic | intermediate | advanced]_
- **Domain:** _[e-commerce | fintech | saas | marketplace | other]_

## Communication Preferences
- **Detail level:** _[executive-summary | standard | deep-dive]_
- **Chart preference:** _[minimal | standard | chart-heavy]_
- **Narrative style:** _[bullet-points | prose | mixed]_

## Corrections Log
_Records of times the user corrected the system's assumptions._
<!-- Format: YYYY-MM-DD | What was wrong | What was right -->
```

## Edge Cases
- **No `.knowledge/` dir:** Create full tree and prompt `/connect-data`.
- **Empty schema.md:** Regenerate via profiling.
- **No data files:** Suggest checking connection or falling back to CSV.
- **Multiple datasets:** Report active, remind about `/switch-dataset`.
- **Setup incomplete:** Note phases, do not block. Suggest `/setup`.

## Anti-Patterns
1. **Never skip bootstrap.** Always read manifest -- details may have changed.
2. **Never hardcode dataset names.** Resolve from `active.yaml`.
3. **Never modify manifest during bootstrap.** Bootstrap is read-only.
4. **Never dump raw YAML to the user.** Show the brief status, not the load.
5. **Never block on a missing subsystem.** Graceful degradation always.
