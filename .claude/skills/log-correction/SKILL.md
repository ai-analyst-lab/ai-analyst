---
name: log-correction
description: >-
  Record analyst mistakes, fixes, and reusable learnings so future analyses never repeat an error.
  Fires automatically when the user corrects work ("actually it's Y", "that's wrong") or teaches
  a rule ("always use X", "never include test users", "remember that our fiscal year starts in
  February"), and manually on "log a correction", "save this mistake", "record this lesson".
  Writes the .knowledge store per docs/KNOWLEDGE.md.
---

# Skill: Log Correction

## Purpose
Record analyst mistakes, their fixes, and reusable learnings so future analyses
learn from past errors. Runs in two modes against the same store (defined in
`docs/KNOWLEDGE.md`): **auto mode** detects corrections and learnings in the
user's messages without being asked, and **manual mode** handles explicit
"log a correction" requests with full detail.

## When to Use
- **Auto:** the user corrects your work ("that's wrong", "actually it's...",
  "you used the wrong column") or teaches a reusable rule ("always use X",
  "never do Y", "remember that our fiscal year starts in February") without
  asking you to log anything
- **Manual:** user says "log a correction", "save this mistake", "record this
  lesson", or similar
- After discovering and fixing an error mid-analysis worth preserving

## Auto Mode

Watch every user message for these signals. When one fires, capture it
immediately; the user never has to ask.

**Correction signals** (something you produced was wrong):
- "that's wrong", "that's incorrect", "actually it's...", "it should be..."
- "the column is X not Y", "you used the wrong...", "off by...",
  "double-counted", "that join is wrong", "missing a filter", "forgot to exclude..."

**Learning signals** (a reusable methodology or fact):
- "always use...", "never use...", "next time...", "prefer X over Y"
- "remember that...", "the convention here is...", "our team uses...",
  "going forward...", "don't forget to..."

If both match, treat it as a correction. If neither matches, do nothing and
say nothing about it.

**On a correction signal:** run Steps 1-5 below, but never interrogate the
user. Infer severity, category, dataset, and tables from context; leave fields
you cannot infer as null. Acknowledge in one line ("Got it, logged as CORR-008.")
and then immediately continue with the user's underlying request; logging is
never the whole response.

**On a learning signal:** append a bullet to `.knowledge/learnings/index.md`
under the closest category heading (Data Patterns, Query Techniques, Business
Context, Stakeholder Preferences, Visualization Insights, Methodology Notes),
formatted `- {concise learning} (source: user feedback, {YYYY-MM-DD})`.
Acknowledge in one line ("Noted for future analyses.") and continue with the
user's request.

**Auto-mode rules:**
1. Silent operation: no execution reports, no "I detected a correction signal",
   no file-path listings. One brief acknowledgment line, then the analysis.
2. Never ask "should I log this?" Classify and log.
3. Never block: if a read or write fails, skip capture and answer the user's
   question as if nothing happened. Do not retry or announce the failure.
4. Never fabricate detail; use null for anything not stated by the user.

## Manual Mode Instructions

### Step 1: Gather Details

Extract from conversation context or ask the user:

1. **What was wrong?** — One-sentence description of the error
2. **What is the correct answer?** — The fix or corrected approach
3. **Which dataset/tables?** — Dataset name and affected table(s)
4. **How severe?** — `critical` (wrong numbers shared) | `high` (changes conclusions) | `medium` (directionally correct) | `low` (no impact)
5. **SQL before/after?** — If the error involved a query, capture both versions

If any required field is unclear, ask the user. Do not guess severity.

### Step 2: Categorize

**IMPORTANT:** Assign exactly ONE category from the following list. These are the only valid categories — do not create custom categories.

| Category | Description | Examples |
|----------|-------------|----------|
| `sql` | Wrong query — bad join, missing filter, incorrect aggregation, wrong GROUP BY, missing WHERE clause | INNER JOIN instead of LEFT JOIN; forgot WHERE clause to filter test users; COUNT(*) instead of COUNT(DISTINCT); aggregation before filtering |
| `metric` | Wrong metric definition — numerator/denominator error, wrong time window, wrong column | Used revenue_usd instead of order_total_usd for GMV; calculated DAU as total events instead of distinct users; wrong date range for YoY comparison |
| `schema` | Wrong column or table reference — stale schema, misnamed field, wrong table | Referenced old_column_name after schema migration; queried staging.users instead of prod.users; assumed column existed but it doesn't |
| `logic` | Flawed reasoning — Simpson's paradox missed, survivorship bias, wrong comparison | Compared current users to all-time users (survivorship bias); aggregated across segments hiding a reversal; compared apples to oranges |
| `other` | Anything that does not fit the above | Data interpretation error, visualization mistake, wrong stakeholder audience |

**If the user mentions a category not in this list** (e.g., "filter_missing", "metric_definition"), map it to the closest match from the allowed categories above and confirm with the user.

### Step 3: Write the Correction

1. Read `.knowledge/corrections/index.yaml` (treat a missing or corrupt file per Rule 3: recreate from scratch)
2. Derive next ID: if `last_correction_id` is null, use `CORR-001`; otherwise
   parse the numeric suffix, increment, and zero-pad to 3 digits
3. Build the entry in exactly this format:

```yaml
- id: "CORR-{N}"
  date: "{YYYY-MM-DD}"
  severity: "{severity}"
  category: "{category}"
  dataset: "{dataset_name}"
  tables: ["{table1}", "{table2}"]
  description: "{what was wrong}"
  fix: "{what the correct approach is}"
  sql_before: "{original query, if applicable, else null}"
  sql_after: "{corrected query, if applicable, else null}"
  prevented_by: "{which validation layer should have caught this}"
```

**The `prevented_by` field** should reference one of these validation layers:

- `structural` — schema checks, PK validation, null checks, row count validation
- `logical` — aggregation consistency, trend direction, progression rates < 100%
- `business-rules` — metric plausibility, known data quality rules, domain constraints
- `Simpson's check` — segment-first analysis to detect reversals
- `source tie-out` — pandas vs DuckDB comparison on foundational metrics

**Examples of prevented_by:**
- For wrong aggregation: `"logical (progression rates should never exceed 100%)"`
- For missing filter: `"business-rules (check for test account filtering in conversion metrics)"`
- For wrong column: `"structural (column validation against schema)"`

4. Read `.knowledge/corrections/log.yaml` (missing or corrupt: recreate per Rule 3)
5. Append the new entry to the `corrections` list
6. Write the YAML back (write the full file in one go so a failed write cannot leave a half-written log)

### Step 4: Update Index

1. Read `.knowledge/corrections/index.yaml` (already loaded in Step 3)
2. Increment `total_corrections`
3. Increment the matching `by_severity.{severity}` counter
4. Increment `by_category.{category}` (create the key if it does not exist)
5. Set `last_correction_id` to the new ID
6. Set `last_updated` to today's date
7. Write the YAML back (full file in one go)

### Step 5: Confirm

Report to the user:

```
Correction logged: {id}
  Severity: {severity} | Category: {category}
  Description: {description}
  Fix: {fix}

Future analyses will check for this pattern during validation.
```

## Rules
1. Never overwrite existing corrections -- always append
2. Always read current state before writing (no blind overwrites)
3. If `log.yaml` or `index.yaml` is missing or corrupt, create from scratch
   with schema_version 1
4. SQL snippets in `sql_before`/`sql_after` should be trimmed to the relevant
   clause, not the entire multi-hundred-line query
5. `prevented_by` should reference a specific validation layer from the list
   in Step 3. Be specific about what check should have caught this.
6. **ONLY use the 5 allowed categories** (sql, metric, schema, logic, other).
   If the user suggests a different category, map it to the closest match.

## Edge Cases
- **No SQL involved:** Set `sql_before` and `sql_after` to null
- **Dataset unknown:** Set `dataset` to "unknown" and note in description
- **Duplicate correction:** Still log it -- repeated errors signal a systemic gap
- **Correction to a correction:** Log as a new entry referencing the prior ID in description
- **User suggests custom category:** Map to closest allowed category and confirm. Example: "filter_missing" → `sql` category with description noting the missing filter.
