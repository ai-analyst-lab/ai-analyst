---
name: data-map
description: |
  Produce a comprehensive cross-table data health map for the active dataset — the full payoff answer to open-ended "tell me about this data" questions. Run all tables, not just one: table inventory with row counts, PK uniqueness, date range per table, date alignment across tables, column completeness, foreign-key join-rate matrix, relationship diagram, and a thread-to-pull opening hypothesis. Use this skill whenever the user asks a **dataset-wide open question** — "tell me about this data", "tell me about the data", "tell me about this dataset", "what's in here", "what's in this data", "give me an overview", "give me the map", "map out the data", "what do I have", "what does this data look like", "show me what we've got", or any broad first-contact question about the active dataset as a whole (not scoped to one table). This skill is the curriculum payoff moment — students who just connected data get cross-table health, relationship mapping, and date alignment on the first broad question, not a schema dump and not a read-and-steer nudge. Does NOT trigger for table-scoped questions (use `data-quality-check` instead) or `/explore` follow-up questions within an already-mapped dataset (use `explore`). For just the schema/structure listing, use `/data` (data-inspect); for a deep statistical profile (distributions, correlations, anomalies), use `data-profiling`.
---

# Skill: Data Map

## Purpose
Answer the broadest possible question — "tell me about this data" — with the broadest substantive answer: cross-table health, relationships, date alignment, and an opening analytical thread. This is first-contact dataset exploration, not a schema dump and not a steering question.

## When to Fire

**Fires on dataset-wide open questions:**
- "tell me about this data / the data / this dataset / the dataset"
- "what's in here / what's in this data / what's in the data"
- "give me an overview / give me the map / map out the data"
- "what do I have / what do we have here"
- "what does this data look like / show me what we've got"
- Any open question that references the dataset as a whole

**Does NOT fire when:**
- The question names a specific table → use `data-quality-check` (Rule 18)
- User invoked `/explore` or is mid-exploration within an already-mapped dataset → use `explore`
- User invoked `/data` or `/data {table}` → use `data-inspect` (schema-only)
- User invoked `/run-pipeline` or a specific analysis → run the pipeline

**Fires regardless of:**
- Whether the dataset was recently profiled (data-profiling populates `.knowledge/`, this skill produces a live report)
- Whether the user explicitly asked for DQ (it's implicit in "tell me about")

## Instructions

### Step 0 — Resolve active dataset

1. Read `.knowledge/active.yaml` to get `active_dataset`. If missing, halt and tell the user to run `/connect-data` or `/setup`.
2. Read `.knowledge/datasets/{active}/manifest.yaml` for connection type and local paths.
3. Read `.knowledge/datasets/{active}/schema.md` for table list and column types.
4. Read `.knowledge/datasets/{active}/quirks.md` to surface known gotchas inline.
5. Verify connectivity per CLAUDE.md rule 9 (MotherDuck → local DuckDB → CSV fallback). Announce which source is active in one line.

### Step 1 — Table inventory and PK health

For every table in schema.md, run:

```sql
SELECT
  COUNT(*)                                       AS row_count,
  COUNT(DISTINCT {pk_col})                       AS distinct_pk,
  COUNT(*) - COUNT(DISTINCT {pk_col})            AS pk_dupes,
  SUM(CASE WHEN {pk_col} IS NULL THEN 1 ELSE 0 END) AS pk_nulls
FROM {schema}.{table};
```

PK inference order: (1) `{table_singular}_id` (e.g., `order_id` for `orders`), (2) column literally named `id`, (3) if neither, note "no single PK detected — composite candidate" and check the most plausible composite. For `order_items` specifically, use `order_item_id` if present, else `(order_id, product_id)`.

### Step 2 — Date range + primary timestamp

For each table, identify the primary timestamp column (prefer `*_timestamp`, then `*_date`, then `created_at`/`started_at`/`session_start`/`event_timestamp`). Run:

```sql
SELECT MIN({ts}) AS min_ts, MAX({ts}) AS max_ts, COUNT(DISTINCT DATE({ts})) AS distinct_days
FROM {schema}.{table};
```

Tables with no timestamp (e.g., `products`, `calendar`, `promotions` if static): note as "static/reference."

### Step 3 — Column completeness (null rates)

For every column in every non-reference table, compute null %. Use a single query per table:

```sql
SELECT
  SUM(CASE WHEN {col_1} IS NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*) AS {col_1}_null_pct,
  SUM(CASE WHEN {col_2} IS NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*) AS {col_2}_null_pct,
  ...
FROM {schema}.{table};
```

Flag any column with null% > 5%. For DOUBLE foreign-key columns (e.g., `orders.promo_id`), high nulls may be expected (not every order used a promo) — note but don't alarm.

### Step 4 — Foreign key inference and join-rate matrix

Infer FKs from naming: a column named `{entity}_id` in table T likely references the `{entity}s` (or `{entity}`) table's PK. For each inferred FK, run:

```sql
SELECT
  COUNT(*)                                          AS child_rows,
  COUNT(DISTINCT c.{fk_col})                        AS distinct_fks,
  SUM(CASE WHEN p.{pk_col} IS NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*) AS orphan_pct
FROM {schema}.{child_table} c
LEFT JOIN {schema}.{parent_table} p
  ON c.{fk_col} = p.{pk_col};
```

Expected FKs in a typical e-commerce schema (illustrative example):
- `orders.user_id` → `users.user_id`
- `order_items.order_id` → `orders.order_id`
- `order_items.product_id` → `products.product_id`
- `events.user_id` → `users.user_id`
- `events.session_id` → `sessions.session_id`
- `events.product_id` → `products.product_id` (nullable — only product-related events)
- `sessions.user_id` → `users.user_id`
- `memberships.user_id` → `users.user_id`
- `nps_responses.user_id` → `users.user_id`
- `support_tickets.user_id` → `users.user_id`
- `support_tickets.order_id` → `orders.order_id` (nullable)
- `experiment_assignments.user_id` → `users.user_id`
- `experiment_assignments.experiment_id` → `experiments.experiment_id`
- `orders.promo_id` → `promotions.promo_id` (nullable)

Generalize by scanning column names for `*_id` patterns — the FK list above is one example shape, not a required schema.

### Step 5 — Cross-table date alignment

Build a table: each row is a table, columns are (min_ts, max_ts, distinct_days). Identify:
- **Pivot range:** the intersection of all core fact tables' date ranges (the window where all data coexists).
- **Misalignments:** tables that start late or end early vs. the pivot. Flag if a fact table's range is <80% of the pivot.
- **Calendar overlap:** if a `calendar` table exists, confirm its range covers the fact tables.

### Step 6 — Relationship diagram

Render an ASCII DAG. Use this layout pattern:

```
              users ──┬── sessions ── events
                      ├── orders ── order_items ── products
                      ├── memberships
                      ├── nps_responses
                      ├── support_tickets ──(nullable)── orders
                      └── experiment_assignments ── experiments
                                     
              promotions ──(nullable)── orders
              calendar  (reference / date spine)
```

Only include tables that actually exist in the active schema.

### Step 7 — Surface quirks

From `quirks.md`, inline any noted gotchas in the relevant section of the output. If quirks.md is empty or placeholder-only, note: "No quirks documented yet — run `/data-profiling` for deep column-level analysis."

### Step 8 — Opening thread to pull

Close with one concrete analytical thread. Prefer a thread that:
1. Matches the dataset's apparent business theme (e.g. e-commerce → funnel, membership, support, experiments; SaaS → activation, usage, churn)
2. Uses the data you just confirmed is present and joinable
3. Points at a specific decision or question (not "segment by X")

Pick a thread grounded in the data's strongest signal — a visible spike, a clear cohort split, or a conspicuous gap. For example: if a `support_tickets` table shows a sharp weekly-volume spike, a strong opener is *"ticket volume jumped in week N — want to pull the thread on what drove it?"*

### Step 9 — Log every query

After running, log each SQL query via `python3 scripts/log_query.py --dataset {active} --agent data-map --purpose "{purpose}" --sql "{sql}" --result "{n_rows}"`.

## Output Format

```markdown
# Data Map: {display_name}

**Source:** {connection_type} @ {path}  •  **Active:** {min_date} → {max_date}  •  **Tables:** {n}

## Cross-Table Health

| Table | Rows | PK Unique | Primary Timestamp | Date Range | Days | Completeness |
|-------|-----:|:---------:|:------------------|:-----------|-----:|:-------------|
| users | 50,000 | ✅ | signup_timestamp | 2024-01-01 → 2024-12-31 | 366 | A |
| orders | 47,199 | ✅ | order_timestamp | 2024-01-02 → 2024-12-31 | 364 | A |
| ... | | | | | | |

**Legend:** ✅ PK unique, no nulls  •  ⚠ PK dupes or nulls  •  Completeness A (<1% null) / B (1-5%) / C (5-20%) / D (>20%)

## Relationship Map

[ASCII DAG]

## Join-Rate Matrix

| Child → Parent | Child Rows | Distinct FKs | Orphans |
|----------------|-----------:|-------------:|--------:|
| orders.user_id → users | 47,199 | 28,403 | 0.0% |
| ... | | | |

**Orphans > 1%** are flagged. Nullable FKs (e.g., `orders.promo_id`) are noted but not flagged.

## Date Alignment

- **Pivot range:** YYYY-MM-DD → YYYY-MM-DD ({N} days, all core facts present)
- **Misalignments:** [list any table with range <80% of pivot, or note "All core tables aligned."]
- **Calendar coverage:** [confirm calendar spans the pivot, or flag]

## Completeness Flags

[Any column with >5% nulls, excluding expected-nullable FKs. If none, write "No columns exceed 5% null threshold (excluding nullable FKs)."]

## Quirks

[From quirks.md, or "No quirks documented — run `/data-profiling` for deep profiling."]

## Thread to Pull

[One concrete analytical opener, 1-2 sentences, grounded in the data.]

---

_Generated by `data-map` skill. For a deeper statistical profile, run `/data-profiling`. For one-table DQ, ask about the table directly. For guided exploration, use `/explore`._
```

## Budget and Safeguards

- **Query budget:** ~2-4 queries per table + one per inferred FK. For a 13-table dataset this is typically 40-70 queries. All logged.
- **Large tables (>100M rows):** Before running null-rate or PK-dupe checks, ask the user: "Table X has {N} rows — run full probe or sample at {sample_pct}%?" Default to sampling at 1% for >100M-row tables, full scan otherwise.
- **Connection failures:** Fall back per Rule 9 and note which source is active.
- **Schema drift:** If a column referenced in schema.md doesn't exist in the live data, catch the error, note it in the Completeness Flags section, and continue.
- **Reference tables (no timestamp):** `calendar`, `products`, `promotions`, `experiments` are static. Skip date range and note as "reference."

## Anti-Patterns

1. **Never answer with schema-only.** Schema.md is an input, not the output. The deliverable includes live probes.
2. **Never ask a steering question instead of running the map.** The whole point is that the broadest question gets the broadest substantive answer. Asking "what do you want to explore?" violates this skill.
3. **Never skip date alignment.** The "data starts 3 months apart" trap is the most common way analyses break — always check.
4. **Never skip the FK matrix.** Orphan rates determine whether joins will silently drop data.
5. **Never fabricate PKs or FKs.** If inference is ambiguous, say so and check the most plausible candidate.
6. **Never produce the thread-to-pull as a vague suggestion.** It should cite a concrete signal visible in the data you just probed.
7. **Never skip the quirks section.** Even "none documented yet" is a useful signal — it tells the student this dataset hasn't been explored in depth.

## Interaction With Other Skills

- **Runs alongside `data-quality-check`**: this skill is DQ at the dataset level; table-scoped DQ still fires on table-specific questions per Rule 18.
- **Supersedes `data-inspect`**: if the user's question is open-ended ("tell me about") rather than `/data`-commanded, run `data-map`, not `data-inspect`.
- **Does not replace `data-profiling`**: that skill is a deep, per-column statistical profile meant to run once after connection. `data-map` is the conversational first-contact answer.
- **Does not replace `/explore`**: `/explore` is for iterative, user-steered exploration within an already-mapped dataset.
