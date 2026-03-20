# Skill: /setup

Run a 4-phase conversational interview that populates the knowledge system
from the user's real context. Turns a blank `.knowledge/` directory into a
fully configured analytical environment.

## Parameters

- **No arguments**: Start from Phase 1 (or resume from last incomplete phase)
- `/setup status`: Show current setup state
- `/setup reset`: Reset profile and preferences (Tier 1)
- `/setup reset everything`: Full reset including dataset connections (Tier 2)

## Trigger Phrases

- `/setup`
- `set up my environment`
- `configure the analyst`
- `onboard me`

## Design Principles

1. **Conversational, not interrogative.** You are a colleague getting to know
   someone, not a form engine. Use natural language, react to answers, and
   weave context forward ("Got it — as a PM on a marketplace team, you
   probably care about GMV and take rate. Let me ask about your data next.").
2. **2-3 questions at a time, max.** Never dump a wall of questions. Group
   them thematically and wait for a response before continuing.
3. **Validate responses.** If a role sounds unusual or a path does not exist,
   confirm before recording. ("You said your CSV directory is `data/sales/`.
   I do not see that directory — did you mean `data/`?")
4. **Allow skipping.** Mark optional fields clearly. If the user says "skip"
   or "I'll do this later", record `null` and move on. Never block progress
   on optional fields.
5. **Show progress.** After each phase, display a brief summary of what was
   captured and what comes next.

---

## State File

All setup state lives in `.knowledge/setup-state.yaml`. Create it on first
run if it does not exist.

### Schema

```yaml
# .knowledge/setup-state.yaml
setup_version: 1
started_at: "YYYY-MM-DDTHH:MM:SS"
last_updated: "YYYY-MM-DDTHH:MM:SS"
status: "complete" | "partial" | "in-progress"

phases:
  role_and_team:
    status: "complete" | "skipped" | "pending"
    completed_at: "YYYY-MM-DDTHH:MM:SS" | null
  data_connection:
    status: "complete" | "partial" | "skipped" | "pending"
    completed_at: "YYYY-MM-DDTHH:MM:SS" | null
    partial_reason: null | "warehouse_mcp_needed"
  business_context:
    status: "complete" | "skipped" | "pending"
    completed_at: "YYYY-MM-DDTHH:MM:SS" | null
  preferences:
    status: "complete" | "skipped" | "pending"
    completed_at: "YYYY-MM-DDTHH:MM:SS" | null
```

---

## Phase 1: Role & Team

**Goal:** Understand who the user is so we can adapt communication style,
technical depth, and default output formats.

### Questions (ask in 1-2 groups)

**Group 1:**
1. "What's your role? (e.g., Product Manager, Data Scientist, Engineer,
   Marketing Analyst, exec)"
2. "How technical are you with data? Pick the one that fits best:
   - **Beginner** — I look at dashboards but rarely write queries
   - **Intermediate** — I can write SQL and read basic stats
   - **Advanced** — I build models, write complex SQL, and review pipelines"

**Group 2:**
3. "What team or department are you on?" _(optional)_
4. "What domain does your product operate in? (e.g., e-commerce, SaaS,
   fintech, marketplace, healthcare, media)" _(optional)_

### Validation

- If role is empty or unrecognizable, ask once for clarification.
- Map common synonyms: "PM" -> Product Manager, "DS" -> Data Scientist,
  "analyst" -> Analyst, "eng" -> Engineer.
- Technical level must resolve to one of: beginner, intermediate, advanced.

### Outputs

Write to `.knowledge/user/profile.md` (create directory if needed):

```markdown
# User Profile

## Role & Expertise

- **Role:** {role}
- **Technical level:** {technical_level}
- **SQL comfort:** {inferred from technical_level: none|basic|intermediate|advanced}
- **Statistics comfort:** {inferred: none|basic|intermediate|advanced}
- **Domain:** {domain or "not specified"}
- **Team:** {team or "not specified"}

## Communication Preferences

_Set in Phase 4._

## Corrections Log

<!-- Format: YYYY-MM-DD | What was wrong | What was right -->
```

Update `.knowledge/setup-state.yaml`:
- Set `phases.role_and_team.status: complete`
- Set `phases.role_and_team.completed_at` to current timestamp

### Phase 1 Summary

Display:
```
Phase 1 complete — Role & Team

  Role:       {role}
  Tech level: {technical_level}
  Domain:     {domain}
  Team:       {team}

Next up: Phase 2 — Data Connection
```

---

## Phase 2: Data Connection

**Goal:** Get the user's data connected so analyses can run.

### Questions

**Group 1:**
1. "Let's connect your data. What do you have?
   - **CSV files** in a local directory
   - **ClickHouse** database (connects via MCP)
   - **Cloud warehouse** (Postgres, BigQuery, Snowflake)
   - **Nothing yet** — I want to use a sample dataset"

### Branch Logic

**If CSV:**
- Ask: "What's the path to your CSV directory? (relative to this repo root)"
- Verify the directory exists and list .csv files found.
- If directory not found, suggest alternatives (check `data/`, `data/examples/`).
- If confirmed, invoke the Connect Data skill internally (`/connect-data type=csv`)
  to create the dataset brain and profile schema.

**If ClickHouse:**
- Ask: "Database name and schema (if any)?"
- Explain: "ClickHouse connects via MCP tools. Make sure your ClickHouse MCP
  server is configured in `.claude/mcp.json`."
- Invoke `/connect-data type=clickhouse` to set up the connection.
- If MCP tools are not available, mark as `partial` with
  `partial_reason: clickhouse_mcp_needed`.

**If Cloud warehouse:**
- Explain: "Cloud warehouses connect via MCP (Model Context Protocol). This
  requires configuring `.claude/mcp.json` with your credentials."
- Route to `/connect-data` for full setup.
- Mark this phase as `partial` with `partial_reason: warehouse_mcp_needed`.
- **Do not block Phase 3.** Continue the interview — data connection can be
  completed separately.

**If Nothing yet / sample dataset:**
- Check `data/examples/` for available sample datasets.
- List them with brief descriptions.
- If user picks one, copy/link it and invoke `/connect-data type=csv`.
- If user wants to skip: mark phase as `skipped`, note that `/connect-data`
  is available later.

### Fork Decision

After Phase 2:
- If `data_connection.status == "complete"`: data is available. Continue to
  Phase 3.
- If `data_connection.status == "partial"` (warehouse MCP needed): continue
  to Phase 3 anyway. The user can finish data connection separately.
- If `data_connection.status == "skipped"`: continue to Phase 3.

### Outputs

Dataset artifacts are created by the `/connect-data` skill (manifest.yaml,
schema.md, active.yaml). Phase 2 only tracks the interview state.

Update `.knowledge/setup-state.yaml`:
- Set `phases.data_connection.status` appropriately
- Set `phases.data_connection.completed_at` or leave null if partial/skipped
- Set `phases.data_connection.partial_reason` if applicable

### Phase 2 Summary

Display:
```
Phase 2 complete — Data Connection

  Source:     {type} ({path or "pending MCP setup"})
  Tables:     {N} tables found  (or "N/A — skipped")
  Status:     {connected | partial — warehouse setup needed | skipped}

Next up: Phase 3 — Business Context
```

---

## Phase 3: Business Context

**Goal:** Understand the business so analyses produce relevant insights, not
just numbers.

### Questions (ask in 2-3 groups)

**Group 1:**
1. "What does your company/product do? Just a sentence or two is fine."
2. "What are the 2-3 metrics your team cares about most? (e.g., conversion
   rate, MRR, DAU, retention, NPS)"

**Group 2:**
3. "What business question or problem are you trying to answer right now?
   This helps me prioritize what to explore first." _(optional)_
4. "Are there any current OKRs or goals I should know about?"
   _(optional)_

**Group 3 (if domain warrants it):**
5. "Any key segments I should know about? (e.g., free vs paid users,
   regions, platforms)" _(optional)_
6. "Is there seasonality or known patterns in your data? (e.g., holiday
   spikes, end-of-quarter effects)" _(optional)_

### Validation

- Metrics: normalize common names ("CVR" -> "conversion rate", "rev" ->
  "revenue"). If a metric is ambiguous, ask for a brief definition.
- Business question: if provided, classify it using the Question Router
  skill (L1-L5) and note the level. This seeds the first analysis.

### Outputs

Write to `.knowledge/user/business-context.md`:

```markdown
# Business Context

## Company & Product

{company_description}

## Key Metrics

| Metric | Definition | Notes |
|--------|-----------|-------|
| {metric_1} | {definition or "TBD"} | {any notes} |
| {metric_2} | {definition or "TBD"} | |

## Current Focus

- **Primary question:** {business_question or "Not specified"}
- **OKRs/Goals:** {okrs or "Not specified"}

## Segments & Patterns

- **Key segments:** {segments or "Not specified"}
- **Seasonality:** {seasonality or "Not specified"}
```

If the user provided metrics and a dataset is connected, seed
`.knowledge/datasets/{active}/metrics/index.yaml` with stub entries for each
metric (name + empty definition). These can be fleshed out later with
`/metrics`.

Update `.knowledge/setup-state.yaml`:
- Set `phases.business_context.status: complete`
- Set `phases.business_context.completed_at`

### Phase 3 Summary

Display:
```
Phase 3 complete — Business Context

  Product:    {one-line summary}
  Key metrics: {metric_1}, {metric_2}, {metric_3}
  Focus:      {business_question or "General exploration"}

Next up: Phase 4 — Preferences
```

---

## Phase 4: Preferences

**Goal:** Configure output style and communication preferences so results
match what the user actually wants.

### Questions (ask in 1-2 groups)

**Group 1:**
1. "How much detail do you usually want in results?
   - **Executive summary** — just the key findings and recommendations
   - **Standard** — findings with supporting evidence and charts
   - **Deep dive** — full methodology, validation details, and data tables"
2. "Do you prefer lots of charts, or mostly text with a few visuals?
   - **Minimal** — text-first, charts only when essential
   - **Standard** — a chart for each key finding
   - **Chart-heavy** — visualize everything possible"

**Group 2:**
3. "How do you usually share results? (helps me format exports)
   - Slide deck
   - Email summary
   - Slack message
   - Written brief
   - Jupyter notebook
   - Multiple of the above" _(optional)_
4. "Anything else I should know about how you like to work? (e.g., 'always
   show me the SQL', 'I hate pie charts', 'keep it under 5 slides')"
   _(optional)_

### Validation

- Detail level must resolve to: executive-summary, standard, deep-dive.
- Chart preference must resolve to: minimal, standard, chart-heavy.
- Export channels are free-form but normalize to the `/export` format list.

### Outputs

Update `.knowledge/user/profile.md` — fill in the Communication Preferences
section:

```markdown
## Communication Preferences

- **Detail level:** {detail_level}
- **Chart preference:** {chart_preference}
- **Narrative style:** {inferred: bullet-points for exec-summary, prose for deep-dive, mixed for standard}
- **Preferred exports:** {export_channels}
- **Custom notes:** {anything_else or "None"}
```

Update `.knowledge/setup-state.yaml`:
- Set `phases.preferences.status: complete`
- Set `phases.preferences.completed_at`
- Set `status: complete` (or `partial` if data_connection was partial)
- Set `last_updated`

---

## Setup Complete Summary

After Phase 4, display the final summary:

```
=== SETUP COMPLETE ===

  Role:         {role} ({technical_level})
  Domain:       {domain}
  Data:         {dataset_name} — {N} tables ({source_type})
  Key metrics:  {metric_1}, {metric_2}, {metric_3}
  Detail level: {detail_level}
  Charts:       {chart_preference}

  Status: {"Ready for analysis" | "Partial — data connection pending"}

Get started:
  - Ask a question: "What's our {metric_1} trend?"
  - Explore data:   /data
  - Full pipeline:  /run-pipeline
  - Dev context:    /setup-dev-context (optional — for development workflow preferences)
```

If setup status is `partial`, also display:
```
  To finish data setup: /connect-data
```

---

## Subcommand: /setup status

Show the current setup state by reading `.knowledge/setup-state.yaml`.

### Output Format

```
Setup Status
============

  Phase 1 — Role & Team:       {status}  {completed_at or ""}
  Phase 2 — Data Connection:   {status}  {completed_at or ""}
  Phase 3 — Business Context:  {status}  {completed_at or ""}
  Phase 4 — Preferences:       {status}  {completed_at or ""}

  Overall: {status}
  Started: {started_at}
  Updated: {last_updated}
```

If no setup-state.yaml exists:
```
Setup has not been started yet. Run /setup to begin.
```

---

## Subcommand: /setup reset

Two-tier reset system to prevent accidental data loss.

### Tier 1: `/setup reset`

Clears profile and preferences (Phase 1 + Phase 4 data). Does NOT touch
data connections or business context.

**What it does:**
1. Delete `.knowledge/user/profile.md`
2. Reset `phases.role_and_team` and `phases.preferences` to `pending` in
   setup-state.yaml
3. Set `status: partial`
4. Set `last_updated`

**Confirmation required:** Ask once: "This will reset your role profile and
output preferences. Your data connections and business context are safe.
Continue? (yes/no)"

### Tier 2: `/setup reset everything`

Clears the entire setup — profile, preferences, business context, AND
dataset connections. This is a destructive operation.

**What it does:**
1. Delete `.knowledge/user/profile.md`
2. Delete `.knowledge/user/business-context.md`
3. Delete all `.knowledge/datasets/*/` directories
4. Reset `.knowledge/active.yaml` to `active_dataset: null`
5. Reset `.knowledge/setup-state.yaml` to all-pending state
6. Clear `data_sources.yaml` entries added by setup

**Confirmation required:** The user must type the exact phrase
`reset everything` to confirm.

Prompt:
```
This will erase your entire setup:
  - User profile and preferences
  - Business context
  - All dataset connections and schema documentation

This cannot be undone.

To confirm, type: reset everything
```

If the user types anything other than `reset everything`, cancel the
operation: "Reset cancelled. Your setup is unchanged."

---

## Phase 5 Note: Development Context

Phase 5 (development context) is opt-in and independent of the core setup
flow. It covers development workflow preferences such as IDE, language,
framework conventions, and code style preferences.

At the end of Phase 4, mention its existence:
```
Optional: Run /setup-dev-context to configure development workflow
preferences (IDE, languages, code style). This is independent of
your analytics setup.
```

This skill does NOT implement Phase 5. The `/setup-dev-context` skill
handles it separately.

---

## Resume Logic

When `/setup` is invoked and `.knowledge/setup-state.yaml` already exists:

1. Read the state file.
2. Find the first phase with status `pending`.
3. If all phases are `complete`, display:
   ```
   Setup is already complete. Use /setup status to review,
   or /setup reset to start over.
   ```
4. If some phases are complete, greet briefly and resume:
   ```
   Welcome back. Phases 1-2 are done. Picking up at Phase 3 —
   Business Context.
   ```
5. If a phase is `partial`, offer to complete it or skip:
   ```
   Phase 2 (Data Connection) is partially complete — your warehouse
   needs MCP configuration. Want to finish that now, or continue
   to Phase 3?
   ```

---

## Anti-Patterns

1. **Never dump all questions at once.** Always group 2-3 and wait for a
   response.
2. **Never block on optional fields.** If the user says "skip" or "later",
   accept it and move on.
3. **Never overwrite existing profile data silently.** If profile.md
   already exists when starting Phase 1, warn: "You already have a profile.
   Running setup will overwrite it. Continue?"
4. **Never store credentials in setup-state.yaml.** Data connection
   credentials go through `/connect-data` and are stored in manifest.yaml
   or environment variables only.
5. **Never skip the state file update.** Every phase completion must be
   written to setup-state.yaml before proceeding to the next phase.
6. **Never run Phase 3+ without asking Phase 1 first** (unless resuming).
   The role context from Phase 1 shapes how questions are asked in later
   phases.
7. **Never combine reset tiers.** `/setup reset` is always Tier 1.
   Tier 2 requires the explicit `reset everything` phrase.

---

## Edge Cases

| Scenario | Handling |
|----------|----------|
| User runs `/setup` but profile.md already exists | Warn and ask to confirm overwrite before proceeding |
| CSV path does not exist | Suggest alternatives, check `data/` and `data/examples/` |
| User provides warehouse type but no MCP | Mark Phase 2 as partial, continue interview |
| User skips all optional fields | That is fine. Record nulls and proceed. |
| User wants to jump to a specific phase | Allow it: "/setup phase 3" resumes from Phase 3 |
| Session ends mid-interview | State is saved per-phase. Next `/setup` resumes. |
| `/setup` called inside a pipeline | Warn: "Setup changes may affect the running pipeline. Finish the pipeline first, or continue at your own risk." |
| User gives contradictory answers | Ask once for clarification. Record what they confirm. |
