---
name: archaeology
description: >-
  Retrieve proven SQL patterns, table cheatsheets, and join patterns from
  .knowledge/query-archaeology/ so past work gets reused. Fire as a pre-flight step before writing
  ANY SQL. Also trigger on "do we have a known query for X", "how do we usually join these
  tables", "have we computed this metric before". If the store is empty or missing, exit silently.
  Also owns the writer convention: after a validated analysis, curate the final SQL here.
---

# Skill: Query Archaeology

## Purpose
Retrieve proven SQL patterns, table cheatsheets, and join patterns from the
query archaeology store so agents reuse validated work instead of writing SQL
from scratch. The skill also defines the store's local write path: after a
validated analysis, the final SQL is curated back into the store (the Writer
Convention below), which is what makes the retrieval loop close.

## When to Use
- **Automatically** before any analysis agent writes SQL (pre-flight step)
- **Manually** when the user asks about known patterns for a table or join
- **After a validated analysis**, to curate the proven SQL (Writer Convention)

## Instructions

### Step 1: Check the Index

Read `.knowledge/query-archaeology/curated/index.yaml`. Parse counters:
`cookbook_entries`, `table_cheatsheets`, `join_patterns`.

**If all three are zero (or the file is missing), stop here.** Return nothing
and do not mention archaeology to the user.

### Step 2: Identify Search Terms

From the current analysis context, extract:
- **Table names** the agent is about to query (e.g., `orders`, `events`)
- **Query intent tags** (e.g., `funnel`, `retention`, `revenue`, `cohort`)

### Step 3: Search the Three Stores

Search each store that has entries (per index counts). Match using
**case-insensitive substring** -- `order` matches `orders`, `order_items`.

#### 3a. Cookbook (`curated/cookbook/*.yaml`)
For each file, check:
- `tables` array -- any element contains a search table name as substring?
- `tags` array -- any element matches a query intent tag?

Extract on match: `title`, `sql`, `tables`, `tags`, and any `caveats`/`notes`.

#### 3b. Table Cheatsheets (`curated/tables/*.yaml`)
For each file, check:
- `table_name` contains a search table name as substring?

Extract on match: `table_name`, `grain`, `primary_key`, `common_filters`,
`gotchas`, `common_joins`.

#### 3c. Join Patterns (`curated/joins/*.yaml`)
For each file, check:
- `tables` array -- at least two elements match search table names?
- If only one search table, match if `tables` contains it as substring.

Extract on match: `tables`, `join_sql`, `cardinality`, `notes`, `validated`.

### Step 4: Format Results

Return matched entries as a fenced context block. Omit sections with no matches.

```
--- QUERY ARCHAEOLOGY CONTEXT ---

## Cookbook Patterns
### {title}
Tables: {tables}  |  Tags: {tags}
```sql
{sql}
```
Caveats: {caveats or "none"}

## Table Cheatsheets
### {table_name}
- Grain: {grain}
- Primary key: {primary_key}
- Common filters: {common_filters}
- Gotchas: {gotchas}
- Common joins: {common_joins summary}

## Join Patterns
### {tables[0]} <-> {tables[1]}
Cardinality: {cardinality}  |  Validated: {validated}
```sql
{join_sql}
```
Notes: {notes}

--- END ARCHAEOLOGY CONTEXT ---
```

### Step 5: Agent Handoff

Pass the formatted block as additional context to the analysis agent. The
agent should prefer archaeology SQL over writing from scratch, respect any
gotchas listed, and note in working files when an archaeology pattern was used.

## Writer Convention: Curate After a Validated Analysis

Retrieval only pays off if something writes. After an analysis is validated
(the triangulation checks pass and the finding ships), curate the final proven
SQL into the store:

1. Allocate the next entry id `CK-{NNN}`: scan
   `.knowledge/query-archaeology/curated/cookbook/` for the highest existing
   number and increment (start at `CK-001` for an empty store).
2. Write `.knowledge/query-archaeology/curated/cookbook/{entry_id}.yaml` with:
   `id`, `title` (what the query answers), `description`, `sql` (the final
   validated SQL), `dataset`, `tables`, `tags` (query intent tags such as
   `funnel`, `retention`, `revenue`), `source_analysis` (the analysis brief or
   `.knowledge/analyses/` run-record filename), `created_at` and `last_used`
   (today), `use_count: 0`. This is the same cookbook format the curated store
   writes, so imported and locally curated entries live side by side.
3. Create `curated/index.yaml` if it is missing (counters `cookbook_entries`,
   `table_cheatsheets`, `join_patterns`, all starting at 0), then increment
   `cookbook_entries`.

Curate one entry per validated headline query, not every intermediate query.
Skip exploratory SQL and one-off sanity checks.

## Anti-Patterns

1. **Never mention archaeology when the store is empty** -- silent skip
2. **Never require exact matches** -- always substring so `order` finds `orders`
3. **Never load all files eagerly** -- check index counts first, skip zero stores
4. **Retrieval never modifies archaeology files** -- the pre-flight path is
   read-only; only the Writer Convention appends entries, and only after
   validation
5. **Never block analysis if retrieval fails** -- archaeology is additive, not a gate
