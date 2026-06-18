---
name: explore
description: |
  Quick, interactive data exploration without the full pipeline. Use this skill whenever a user wants to explore data, understand what's in a dataset, browse tables or columns, check data distributions, spot patterns, or get familiar with data before analysis. Trigger on phrases like "/explore", "let me explore the data", "what's in this dataset?", "show me what data we have", "browse the data", "what tables are available?", "what columns does X have?", "show me a sample of the data", "what does the distribution look like?", "explore this table", or any request to understand data structure, contents, or patterns before diving into formal analysis. This is especially important after connecting a new dataset or when the user wants to poke around without committing to a specific analytical question yet. DISAMBIGUATION: this is interactive poke-around within an already-known dataset. For a first-contact dataset-wide overview ("tell me about this data"), use `data-map`; for a plain schema/structure listing, use `/data` (data-inspect).
---

# Skill: Explore Data

## Purpose
Quick, interactive data exploration without the full pipeline. Lets users
poke around the active dataset — preview tables, check distributions, spot
patterns, and form hypotheses before committing to a formal analysis.

## When to Use
- User says `/explore` or "let me explore the data" or "what's in this dataset?"
- After connecting a new dataset, before any formal analysis
- When the user wants to understand data shape without a specific question

## Invocation
`/explore` — explore the active dataset
`/explore {table}` — focus on a specific table
`/explore {table} {column}` — deep-dive into a specific column

## Instructions

### Step 1: Load Context (with Fallback)

**Try to load formal context first:**
1. Check if `.knowledge/active.yaml` exists
2. If yes, read it to identify the active dataset name
3. Read `.knowledge/datasets/{active}/schema.md` for table/column reference
4. Read `.knowledge/datasets/{active}/quirks.md` for known gotchas

**If .knowledge/ files don't exist (common for new users), fall back:**
1. Look for data in these locations (in order):
   - `data/examples/*.csv` (shared example datasets)
   - `data/practice/*.csv` (if a local practice dataset is present)
   - `tests/fixtures/*.csv` (test data)
2. Use the first location where data is found
3. Infer schema by reading a sample of the data
4. Proceed with exploration using discovered data

**If no data found anywhere:**
- Prompt: "No dataset found. Use `/connect-data` to add one, or point me to your data files."
- Do NOT proceed with hypothetical exploration

### Step 2: Choose Exploration Mode

**Mode A: Dataset overview** (no table specified) — **READ-AND-STEER**

Goal: Give the user just enough orientation to steer, then **stop and ask** what they want to explore. Do NOT autopilot into observations, findings, or starting questions. The tool's job is to read the situation and hand the steering wheel back to the user.

Deliver (keep it tight — this is a one-screen opener, not an analysis):
1. **Dataset identity:** name, source/connection, coverage window.
2. **Table list:** names with row counts. One-line format per table, no embellishment.
3. **Entity map:** a short diagram of how the tables relate (e.g., `users → orders → order_items → products`).
4. **Stop and ask.** End with an open question, e.g. _"What would you like to explore in {dataset}?"_

**DO NOT** at this stage:
- Run summary queries (status distributions, conversion rates, AOV, etc.).
- Surface "what jumped out" observations, paradoxes, or quality flags.
- Suggest 3 starting questions or propose investigations.
- Save `working/explore_notes_*.md` — there is nothing to note yet.

All of that comes **after** the user gives a real analytical question. Once they steer (e.g., "look at cancellations by device"), proceed with queries, charts, and notes — but narrate the invisible layers first (see Mode A → Follow-up below).

**Mode A → Follow-up: User Steers With an Analytical Question** — **NARRATE THE MACHINERY**

When the user answers the Mode A opener with a specific analytical question (e.g., "top 5 product categories by support ticket volume", "how does conversion vary by device"), DO NOT jump straight to SQL. The user is inside `/explore` to *see* the AI Analyst stack at work. Surface the invisible layers as four labeled, visible blocks — in this order, before presenting any numbers:

1. **🧭 Question Router** — State the classification and routing decision out loud. Use the L1-L5 ladder (L1 factual lookup, L2 simple comparison/aggregation, L3 diagnostic, L4 root-cause, L5 strategic) and name the route (`data-retrieval`, `definition`, `troubleshooting`, `framing`, etc.). One or two sentences. Example: _"Classified as **L2 data retrieval** — a ranked aggregation over a known grain. Routing to query-and-return."_

2. **🎯 Framed Query** — Translate the plain-English ask into a precise, executable spec before running it. 3-6 bullets covering: the grain (what's being counted), the joins required, the aggregation, how ambiguity is resolved (ties, duplicates, null keys, one-to-many fan-out), the ordering and limit. This is the "sharpening" step — the user can correct it before execution. Example: _"Grain: one row per support ticket. Join: `support_tickets → orders → order_items → products`. Count: distinct `ticket_id` per `products.category`. Ambiguity: an order can span multiple categories; a ticket is counted once per distinct category it touches (so percentages can sum >100%). Order by ticket count desc, limit 5."_

3. **✅ Data Quality Check** — Run the checks the framed query depends on *before* the main aggregation, and report PASS / WARN / FAIL per check with actual numbers. Cover at minimum: (a) join-key coverage (what % of the left-side rows have a matching key?), (b) null rates on the columns used in GROUP BY / WHERE, (c) cardinality sanity (does any category look suspiciously large or small?). If a WARN would materially skew results (e.g., "60% of tickets have no `order_id`, so we're answering the question for the 40% that do"), surface it here — not in a footnote after the table.

4. **📊 Answer** — Only after the three blocks above, run the query and present the result table with a one-line source citation. Include any methodology caveats that the Data Quality Check surfaced.

**Keep each block tight** — 2-5 lines. The goal is visible machinery, not a wall of text. The student should be able to point at each block and say "that's the Router," "that's the framing layer," "that's the quality check."

**Rationale:** Bare `/explore` is often used as a teaching surface for the AI Analyst architecture. Running queries silently hides the parts of the system that are most valuable to see. Narrating these three layers on every follow-up question inside `/explore` makes the copilot model legible.

**Mode B: Table exploration** (table specified)

Goal: Help the user understand one table's structure, quality, and analytical potential.

Deliver:
1. **Column list** with data types and null rates
2. **5 random sample rows** to show actual data
3. **Summary statistics by column type:**
   - Numeric: min, max, mean, median
   - Categorical: top 5 values with counts
   - Date: earliest, latest, coverage (% of days with data)
4. **Quality flags** - Report ANY of these issues:
   - Columns with >5% nulls (specify which columns and %)
   - Low cardinality categoricals (only 1-2 unique values)
   - Suspicious values (negatives where impossible, future dates, outlier extremes)
   - Data type mismatches (dates stored as strings)
5. **Analytical potential** - What analyses would this table support?

**Mode C: Column deep-dive** (table + column specified)

Goal: Understand the distribution, quality, and business meaning of one column.

Deliver:
1. **Full distribution visualization:**
   - Numeric: histogram with SWD styling (use `swd_style()`)
   - Categorical: horizontal bar chart (top 10-20 values, SWD styled)
   - Date: coverage heatmap by week
2. **Null analysis:**
   - Null count and percentage
   - Pattern: random (scattered) vs systematic (clustered in time/segments)
3. **Outlier detection (numeric only):**
   - Use IQR method (values > Q3 + 1.5*IQR or < Q1 - 1.5*IQR)
   - Report count, range, and business plausibility
   - Flag if outliers represent >10% of data (unusual)
4. **Business context:**
   - What does this column measure?
   - What's a "normal" value vs an extreme?
   - Revenue impact if this metric improves/degrades
5. **Related columns for cross-analysis** - Suggest 2-3 other columns to slice/segment by

### Step 3: Interactive Follow-Up

After presenting results, ALWAYS offer 2-3 **specific, actionable** next steps.

Good examples (use actual names from the data):
- "Want to see how {column} varies by {dimension}?" (segmentation)
- "Orders show a 9.5% cancellation rate. Want to investigate root causes?"
- "You have high-value outliers (>$500 orders). Want to profile that customer segment?"
- "This funnel data looks ready for conversion analysis. Run `/run-pipeline`?"

Avoid generic suggestions like "Want to analyze more?" — make them specific to findings.

### Step 4: Save Exploration Notes (CRITICAL)

**Only after the user has steered with a real question and you've run actual exploration queries**, write a summary file to `working/explore_notes_{YYYYMMDD}.md`. Do NOT write this file on the initial read-and-steer prompt (Mode A opener) — there is nothing to note when the user hasn't asked anything yet.

Include:
- **Tables examined:** List with timestamps
- **Key observations:** 3-5 bullet points of most important findings
- **Quality flags:** List any blockers or warnings discovered
- **Suggested next steps:** Copy the interactive suggestions from Step 3

**Why this matters:** Subsequent agents (Question Framing, Hypothesis Generation, Data Explorer) can read these notes to avoid redundant work and build on your findings.

**Format:**
```markdown
## Tables Examined
- {table_name} (explored {date})

## Key Observations
- {observation 1}
- {observation 2}

## Quality Flags
- ⚠️ {issue description}
- ✅ {positive finding}

## Suggested Next Steps
1. {suggestion 1}
2. {suggestion 2}
```

## Rules

1. **Read-and-steer on open-ended `/explore`** — Bare `/explore` is an *invitation*, not an instruction. Orient the user (dataset name, source, coverage, table list, entity map) and then STOP and ask what they want to explore. Never autopilot into observations, summary queries, quality flags, or proposed investigations on the opener. Only run analytical queries after the user provides a specific question. `/explore {table}` and `/explore {table} {column}` already carry intent — go ahead with Mode B / Mode C there.

2. **Narrate the stack on every follow-up inside `/explore`** — When the user steers with an analytical question after the Mode A opener, you MUST output the four labeled blocks (🧭 Question Router → 🎯 Framed Query → ✅ Data Quality Check → 📊 Answer) before presenting results. Do not run the aggregation and then retrofit the narration. These layers normally run silently across the system; inside `/explore` they are surfaced on purpose, because `/explore` is the teaching surface for the AI Analyst architecture. Skipping them defeats the point of using the command.

3. **Keep it fast** — No more than 3-4 queries per exploration step. Users want speed, not exhaustive profiling.

2. **Always apply `swd_style()`** if generating any chart. Call it BEFORE creating the chart.

3. **Never modify data** during exploration. Read-only operations only.

4. **Always cite table and column names** in output. Users need to know what you're referencing.

5. **Mention data source explicitly** - Tell the user where data came from:
   - "Using data from {path} (local CSV files)"
   - "Connected to MotherDuck database"
   - "Reading from {specific file path}"

6. **Use actual data** - Never provide hypothetical/generic exploration. If data doesn't exist, say so clearly and stop.

## Edge Cases

- **Empty table (0 rows):** Report row count = 0, suggest checking data load process, do NOT attempt distribution analysis

- **Table not found:** Use fuzzy matching to suggest closest match:
  - User typed "order" → suggest "orders" or "order_items"
  - Show available table names to help user correct

- **Column has 100% nulls:** Flag as BLOCKER, suggest checking data pipeline, do NOT attempt distribution analysis

- **Very wide table (>50 columns):** Group columns by semantic category (IDs, metrics, dimensions, dates), show summary counts per category instead of listing all 50+

- **Date column stored as VARCHAR/text:** Flag in quality section, remind user to cast as `::DATE` or `CAST(... AS DATE)` in SQL queries

- **Mixed data sources:** If some tables are in DuckDB and others are CSVs, mention this explicitly so user understands why queries might behave differently
