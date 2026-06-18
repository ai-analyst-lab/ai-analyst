---
name: log-correction
description: Record analyst mistakes and their fixes so future analyses learn from past errors. Manual counterpart to automatic feedback capture. Use this skill whenever the user wants to deliberately log a correction to the knowledge system — when they say "log a correction", "save this mistake", "record this error", "that was wrong because...", "I want to capture this fix", "add this to corrections", "log this for next time", "record this lesson", "save this to learnings", or similar correction-logging phrases. Also trigger when the feedback-capture skill routes here for detailed correction entry, or after discovering and fixing an error mid-analysis that should be preserved for future sessions. This skill ensures mistakes are documented with full context (severity, category, dataset, SQL before/after, prevention layer) so the validation system can catch the same error next time. Apply whenever someone wants to make sure a specific error gets logged and learned from, when you've just fixed a bug and want to prevent recurrence, when wrapping up an analysis where you found an issue, when a user corrects your work and says to remember it, or when documenting why a previous approach was wrong so future runs avoid it.
---

# Skill: Log Correction

## Purpose
Record analyst mistakes and their fixes so future analyses learn from past
errors. Manual counterpart to automatic feedback capture.

## When to Use
- User says "log a correction", "that was wrong because...", or similar
- Feedback-capture skill routes here for detailed correction entry
- After discovering and fixing an error mid-analysis

## Instructions

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

1. Read `.knowledge/corrections/index.yaml` using `safe_read_yaml()`
2. Derive next ID: if `last_correction_id` is null, use `CORR-001`; otherwise
   parse the numeric suffix, increment, and zero-pad to 3 digits
3. Build the entry following `.knowledge/corrections/log.template.yaml`:

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

4. Read `.knowledge/corrections/log.yaml` using `safe_read_yaml()`
5. Append the new entry to the `corrections` list
6. Write back using `atomic_write_yaml()`

### Step 4: Update Index

1. Read `.knowledge/corrections/index.yaml` (already loaded in Step 3)
2. Increment `total_corrections`
3. Increment the matching `by_severity.{severity}` counter
4. Increment `by_category.{category}` (create the key if it does not exist)
5. Set `last_correction_id` to the new ID
6. Set `last_updated` to today's date
7. Write back using `atomic_write_yaml()`

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
