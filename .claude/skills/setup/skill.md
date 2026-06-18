---
name: setup
description: |
  Run a 4-phase conversational interview that populates the knowledge system from the user's real context. Turns a blank `.knowledge/` directory into a fully configured analytical environment. Use this skill whenever the user wants to set up the AI Analyst, configure their environment, get started with the tool, onboard themselves, connect their data for the first time, initialize their profile, or set up the system. Also trigger when users say things like "let's get started", "I'm new here", "configure the analyst", "set up my environment", "onboard me", "connect my data", "initialize", "first time setup", "get this working", "how do I begin", or invoke `/setup`. This skill handles both fresh setup (no existing profile) and resuming partial setup (picking up where they left off). It's especially important to use this skill when you detect the user has no `.knowledge/user/profile.md` or when they explicitly want to reconfigure their settings.
---

# Skill: /setup

Run a 4-phase conversational interview that populates the knowledge system
from the user's real context. Turns a blank `.knowledge/` directory into a
fully configured analytical environment.

This skill is about DOING, not describing. Every "Outputs" section contains tool-use instructions you must execute immediately, not descriptions of what should happen later.

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
   them thematically, ask 2-3, then STOP and wait for a response before continuing.
3. **Validate responses.** If a role sounds unusual or a path does not exist,
   confirm before recording. ("You said your CSV directory is `data/sales/`.
   I do not see that directory — did you mean `data/`?")
4. **Allow skipping.** Mark optional fields clearly. If the user says "skip"
   or "I'll do this later", record `null` and move on. Never block progress
   on optional fields.
5. **Show progress.** After each phase, display the exact summary format specified.

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

### Questions

**IMPORTANT**: Ask Group 1 questions (below). STOP after asking them. Wait for the user's response. Do NOT ask Group 2 questions yet.

**Group 1 (ask these now, then wait):**
1. "What's your role? (e.g., Product Manager, Data Scientist, Engineer,
   Marketing Analyst, exec)"
2. "How technical are you with data? Pick the one that fits best:
   - **Beginner** — I look at dashboards but rarely write queries
   - **Intermediate** — I can write SQL and read basic stats
   - **Advanced** — I build models, write complex SQL, and review pipelines"

**Group 2 (ask AFTER Group 1 response):**
3. "What team or department are you on?" _(optional)_
4. "What domain does your product operate in? (e.g., e-commerce, SaaS,
   fintech, marketplace, healthcare, media)" _(optional)_

### Validation

- If role is empty or unrecognizable, ask once for clarification.
- Map common synonyms: "PM" -> Product Manager, "DS" -> Data Scientist,
  "analyst" -> Analyst, "eng" -> Engineer.
- Technical level must resolve to one of: beginner, intermediate, advanced.

### File Creation (Execute Now)

After collecting all Phase 1 responses:

**Step 1**: Create the user directory if it doesn't exist:
```bash
mkdir -p .knowledge/user
```

**Step 2**: Use the Write tool to create `.knowledge/user/profile.md` with this exact structure:

```markdown
# User Profile

## Role & Expertise

- **Role:** {role}
- **Technical level:** {technical_level}
- **SQL comfort:** {inferred from technical_level: none for beginner, basic for intermediate, intermediate/advanced for advanced}
- **Statistics comfort:** {inferred: none for beginner, basic for intermediate, intermediate/advanced for advanced}
- **Domain:** {domain or "not specified"}
- **Team:** {team or "not specified"}

## Communication Preferences

_Set in Phase 4._

## Corrections Log

<!-- Format: YYYY-MM-DD | What was wrong | What was right -->
```

Replace `{role}`, `{technical_level}`, etc. with actual values from the user's responses.

**Step 3**: Update `.knowledge/setup-state.yaml`:

If the file doesn't exist yet, use Write tool to create it with:
```yaml
setup_version: 1
started_at: "{current timestamp in YYYY-MM-DDTHH:MM:SS format}"
last_updated: "{current timestamp}"
status: "in-progress"

phases:
  role_and_team:
    status: "complete"
    completed_at: "{current timestamp}"
  data_connection:
    status: "pending"
    completed_at: null
  business_context:
    status: "pending"
    completed_at: null
  preferences:
    status: "pending"
    completed_at: null
```

If it already exists, use Edit tool to set:
- `phases.role_and_team.status: complete`
- `phases.role_and_team.completed_at: "{current timestamp}"`
- `last_updated: "{current timestamp}"`

**Step 4 - CHECKPOINT**: Verify the files were created successfully by using Read tool on `.knowledge/user/profile.md`. If it doesn't exist, something went wrong. Fix it before proceeding.

### Phase 1 Summary (Display Now)

After all files are created, display this exact format:

```
✓ Phase 1 complete — Role & Team

  Role:       {role}
  Tech level: {technical_level}
  Domain:     {domain or "not specified"}
  Team:       {team or "not specified"}

Next up: Phase 2 — Data Connection
```

Then proceed to Phase 2.

---

## Phase 2: Data Connection

**Goal:** Get the user's data connected so analyses can run.

### Questions (2 at a time max)

**Group 1 (ask now, then wait):**
1. "Let's connect your data. What do you have?
   - **CSV files** in a local directory
   - **DuckDB** database file
   - **Cloud warehouse** (MotherDuck, Postgres, BigQuery, Snowflake)
   - **Nothing yet** — I want to use a sample dataset"

STOP. Wait for response before continuing.

### Branch Logic

The user's answer to Group 1 determines what happens next.

**If CSV:**
- Ask: "What's the path to your CSV directory? (relative to this repo root)"
- Use Glob tool to verify the directory exists and list .csv files.
- If directory not found, use Bash tool to check `data/` and `data/examples/` directories, then suggest alternatives.
- If path is confirmed, invoke the Connect Data skill: use the Skill tool with `skill: "connect-data"` and `args: "type=csv path={the_path}"`.
- The Connect Data skill will handle creating dataset brain, profiling schema, updating active.yaml.
- After Connect Data returns, check if `.knowledge/datasets/{dataset_name}/manifest.yaml` exists to confirm success.

**If DuckDB:**
- Ask: "What's the path to your .duckdb file?"
- Use Read or Bash tool to verify the file exists.
- If confirmed, invoke Connect Data: `skill: "connect-data"`, `args: "type=duckdb path={the_path}"`.
- Check for manifest.yaml to confirm success.

**If Cloud warehouse:**
- Explain: "Cloud warehouses connect via MCP (Model Context Protocol). This
  requires configuring `.claude/mcp.json` with your credentials."
- Invoke Connect Data: `skill: "connect-data"`, `args: "type={warehouse_type}"` (warehouse_type = motherduck, postgres, bigquery, or snowflake).
- Connect Data will guide the MCP setup.
- After Connect Data returns, check its status. If it says "MCP configuration needed", mark Phase 2 as `partial`.
- **Do not block Phase 3.** Continue the interview even if warehouse setup is incomplete.

**If Nothing yet / sample dataset:**
- Use Bash tool to list directories in `data/examples/`: `ls -la data/examples/`
- Show brief descriptions if available (check for README files).
- If user picks one, invoke Connect Data with the sample dataset path.
- If user wants to skip: mark phase as `skipped` in next step.

### State Update (Execute Now)

After data connection attempt:

Use Edit tool on `.knowledge/setup-state.yaml` to set:
- `phases.data_connection.status`:
  - `"complete"` if manifest.yaml exists for the connected dataset
  - `"partial"` if warehouse MCP setup is pending
  - `"skipped"` if user chose to skip
- `phases.data_connection.completed_at`: current timestamp (or null if skipped)
- `phases.data_connection.partial_reason`: `"warehouse_mcp_needed"` if partial, otherwise null
- `last_updated`: current timestamp

### Phase 2 Summary (Display Now)

```
✓ Phase 2 complete — Data Connection

  Source:     {type} ({path or "pending MCP setup"})
  Tables:     {N} tables found  (or "N/A — skipped")
  Status:     {connected | partial — warehouse setup needed | skipped}

Next up: Phase 3 — Business Context
```

Then proceed to Phase 3 (even if data connection is partial or skipped).

---

## Phase 3: Business Context

**Goal:** Understand the business so analyses produce relevant insights, not
just numbers.

### Questions (ask in groups of 2, wait between groups)

**Group 1 (ask now, then STOP):**
1. "What does your company/product do? Just a sentence or two is fine."
2. "What are the 2-3 metrics your team cares about most? (e.g., conversion
   rate, MRR, DAU, retention, NPS)"

Wait for response.

**Group 2 (ask after Group 1 response, optional):**
3. "What business question or problem are you trying to answer right now?
   This helps me prioritize what to explore first." _(optional — user can skip)_
4. "Are there any current OKRs or goals I should know about?"
   _(optional)_

Wait for response.

**Group 3 (ask only if domain warrants it, optional):**
5. "Any key segments I should know about? (e.g., free vs paid users,
   regions, platforms)" _(optional)_
6. "Is there seasonality or known patterns in your data? (e.g., holiday
   spikes, end-of-quarter effects)" _(optional)_

### Validation

- Metrics: normalize common names ("CVR" -> "conversion rate", "rev" ->
  "revenue"). If a metric is ambiguous, ask for a brief definition.
- Business question: if provided, note it for future use. Do NOT run Question Router here — just capture the text.

### File Creation (Execute Now)

**Step 1**: Use Write tool to create `.knowledge/user/business-context.md`:

```markdown
# Business Context

## Company & Product

{company_description from Group 1 Q1}

## Key Metrics

| Metric | Definition | Notes |
|--------|-----------|-------|
| {metric_1 from Group 1 Q2} | {definition if user provided one, otherwise "TBD"} | |
| {metric_2 from Group 1 Q2} | {definition if provided, otherwise "TBD"} | |
| {metric_3 if provided} | {definition if provided, otherwise "TBD"} | |

## Current Focus

- **Primary question:** {business_question from Group 2 Q3, or "Not specified"}
- **OKRs/Goals:** {okrs from Group 2 Q4, or "Not specified"}

## Segments & Patterns

- **Key segments:** {segments from Group 3 Q5, or "Not specified"}
- **Seasonality:** {seasonality from Group 3 Q6, or "Not specified"}
```

**Step 2** (Optional - only if dataset is connected AND user provided metrics):

If Phase 2 status is "complete" (not skipped or partial), AND the user provided metrics in Group 1 Q2:
- Read `.knowledge/active.yaml` to get the active dataset name
- Check if `.knowledge/datasets/{active}/metrics/index.yaml` exists
- If it doesn't exist, create it with stub entries for each metric:

```yaml
metrics:
  - name: "{metric_1}"
    definition: ""
    sql: ""

  - name: "{metric_2}"
    definition: ""
    sql: ""
```

If it already exists, skip this step (don't overwrite existing metrics).

**Step 3**: Use Edit tool on `.knowledge/setup-state.yaml` to set:
- `phases.business_context.status: complete`
- `phases.business_context.completed_at: "{current timestamp}"`
- `last_updated: "{current timestamp}"`

**Step 4 - CHECKPOINT**: Use Read tool to verify `.knowledge/user/business-context.md` exists and contains the user's responses.

### Phase 3 Summary (Display Now)

```
✓ Phase 3 complete — Business Context

  Product:    {one-line summary from company_description}
  Key metrics: {metric_1}, {metric_2}, {metric_3 if provided}
  Focus:      {business_question or "General exploration"}

Next up: Phase 4 — Preferences
```

Then proceed to Phase 4.

---

## Phase 4: Preferences

**Goal:** Configure output style and communication preferences so results
match what the user actually wants.

### Questions (ask in groups of 2, wait between groups)

**Group 1 (ask now, then STOP):**
1. "How much detail do you usually want in results?
   - **Executive summary** — just the key findings and recommendations
   - **Standard** — findings with supporting evidence and charts
   - **Deep dive** — full methodology, validation details, and data tables"
2. "Do you prefer lots of charts, or mostly text with a few visuals?
   - **Minimal** — text-first, charts only when essential
   - **Standard** — a chart for each key finding
   - **Chart-heavy** — visualize everything possible"

Wait for response.

**Group 2 (ask after Group 1 response, optional):**
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

- Detail level must resolve to: executive-summary, standard, or deep-dive.
- Chart preference must resolve to: minimal, standard, or chart-heavy.
- Export channels: record as-is (free-form).

### File Updates (Execute Now)

**Step 1**: Use Edit tool on `.knowledge/user/profile.md` to fill in the Communication Preferences section (currently says "_Set in Phase 4._").

Replace that line with:

```markdown
## Communication Preferences

- **Detail level:** {detail_level from Group 1 Q1}
- **Chart preference:** {chart_preference from Group 1 Q2}
- **Narrative style:** {infer: bullet-points for executive-summary, prose for deep-dive, mixed for standard}
- **Preferred exports:** {export_channels from Group 2 Q3, or "Not specified"}
- **Custom notes:** {anything_else from Group 2 Q4, or "None"}
```

**Step 2**: Use Edit tool on `.knowledge/setup-state.yaml` to set:
- `phases.preferences.status: complete`
- `phases.preferences.completed_at: "{current timestamp}"`
- `status: "complete"` (or `"partial"` if data_connection status was partial)
- `last_updated: "{current timestamp}"`

**Step 3 - CHECKPOINT**: Use Read tool to verify `.knowledge/user/profile.md` now contains the Communication Preferences section with actual values (not "_Set in Phase 4._").

### Setup Complete Summary (Display Now)

After Phase 4 completes, display this comprehensive summary:

```
=== SETUP COMPLETE ===

  Role:         {role} ({technical_level})
  Domain:       {domain}
  Data:         {dataset_name} — {N} tables ({source_type})
              ({or "None connected" if data was skipped})
  Key metrics:  {metric_1}, {metric_2}, {metric_3}
  Detail level: {detail_level}
  Charts:       {chart_preference}

  Status: {"✓ Ready for analysis" | "⚠ Partial — data connection pending"}

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

### Execution Steps

**Step 1**: Check if `.knowledge/setup-state.yaml` exists using Read tool.

**Step 2**: If file doesn't exist, display:
```
Setup has not been started yet. Run /setup to begin.
```

**Step 3**: If file exists, read it and display:

```
Setup Status
============

  Phase 1 — Role & Team:       {status}  {completed_at or ""}
  Phase 2 — Data Connection:   {status}  {completed_at or ""}
              {partial_reason if status is partial}
  Phase 3 — Business Context:  {status}  {completed_at or ""}
  Phase 4 — Preferences:       {status}  {completed_at or ""}

  Overall: {status}
  Started: {started_at}
  Updated: {last_updated}
```

---

## Subcommand: /setup reset

Two-tier reset system to prevent accidental data loss.

### Tier 1: `/setup reset`

Clears profile and preferences (Phase 1 + Phase 4 data). Does NOT touch
data connections or business context.

### CONFIRMATION REQUIRED

Before proceeding, ask the user:

```
This will reset your role profile and output preferences. Your data connections and business context are safe.

Continue? (yes/no)
```

STOP. Wait for explicit "yes" before continuing. If user says anything other than "yes" (including "no", "cancel", "wait", etc.), respond:

```
Reset cancelled. Your setup is unchanged.
```

And DO NOT proceed with deletion.

### Execution (only after "yes" confirmation)

**Step 1**: Use Bash tool to delete profile:
```bash
rm -f .knowledge/user/profile.md
```

**Step 2**: Use Edit tool on `.knowledge/setup-state.yaml` to set:
- `phases.role_and_team.status: pending`
- `phases.role_and_team.completed_at: null`
- `phases.preferences.status: pending`
- `phases.preferences.completed_at: null`
- `status: partial`
- `last_updated: "{current timestamp}"`

**Step 3**: Display:
```
✓ Profile and preferences reset. Your data and business context are preserved.

Run /setup to reconfigure your profile.
```

### Tier 2: `/setup reset everything`

Clears the entire setup — profile, preferences, business context, AND
dataset connections. This is destructive.

### CONFIRMATION REQUIRED (Stricter)

Display this prompt:

```
This will erase your entire setup:
  - User profile and preferences
  - Business context
  - All dataset connections and schema documentation

This cannot be undone.

To confirm, type exactly: reset everything
```

STOP. Wait for user input.

**If user types anything OTHER than the exact phrase "reset everything"** (case-sensitive), respond:
```
Reset cancelled. Your setup is unchanged.
```

And DO NOT proceed.

**Only if user types "reset everything" exactly**, proceed with deletion.

### Execution (only after exact phrase confirmation)

**Step 1**: Use Bash tool to delete all setup files:
```bash
rm -f .knowledge/user/profile.md
rm -f .knowledge/user/business-context.md
rm -rf .knowledge/datasets/
rm -f .knowledge/active.yaml
```

**Step 2**: Use Write tool to reset `.knowledge/setup-state.yaml` to initial state:
```yaml
setup_version: 1
started_at: "{current timestamp}"
last_updated: "{current timestamp}"
status: "pending"

phases:
  role_and_team:
    status: "pending"
    completed_at: null
  data_connection:
    status: "pending"
    completed_at: null
  business_context:
    status: "pending"
    completed_at: null
  preferences:
    status: "pending"
    completed_at: null
```

**Step 3**: Display:
```
✓ Complete reset finished. All setup data has been cleared.

Run /setup to start fresh.
```

---

## Resume Logic

When `/setup` is invoked and `.knowledge/setup-state.yaml` already exists:

**Step 1**: Use Read tool to read `.knowledge/setup-state.yaml`.

**Step 2**: Check the `status` field and phase statuses. Determine state:
- If all phases have status "complete": setup is complete
- If any phase has status "pending": setup is incomplete, needs resuming
- If any phase has status "partial": setup has pending work

**Step 3**: Route based on state:

**If all phases are complete:**
Display:
```
Setup is already complete. Use /setup status to review, or /setup reset to start over.
```
STOP. Do not proceed to Phase 1.

**If some phases are complete:**
Find the first phase with status "pending". Display:
```
Welcome back. Phase{s} {completed_phase_numbers} are done. Picking up at Phase {next_phase_number} — {phase_name}.
```

Then jump directly to that phase (skip completed phases).

**If a phase is "partial":**
Check which phase is partial. If it's Phase 2 (data_connection):
```
Phase 2 (Data Connection) is partially complete — your warehouse needs MCP configuration.

Want to finish that now (enter 'finish'), or continue to Phase 3 (enter 'continue')?
```

Wait for user response. If "finish", invoke Connect Data skill. If "continue", proceed to Phase 3.

---

## Anti-Patterns

1. **Never dump all questions at once.** Ask 2-3, then STOP and await response.
2. **Never block on optional fields.** If the user says "skip" or "later",
   record `null` and move on.
3. **Never overwrite existing files silently.** If profile.md exists when
   starting Phase 1, warn: "You already have a profile. Running setup will
   overwrite it. Continue? (yes/no)" Wait for confirmation.
4. **Never store credentials in setup-state.yaml.** Credentials go through
   `/connect-data` and are stored in manifest.yaml or environment variables only.
5. **Never skip file writes.** Every "File Creation" section is mandatory. Use
   Write/Edit tools immediately after collecting the required information.
6. **Never skip checkpoints.** After creating files, verify them with Read tool
   before proceeding to the next phase.
7. **Never run Phase 3+ without Phase 1 first** (unless resuming from partial state).
8. **Never combine reset tiers.** `/setup reset` is always Tier 1. Tier 2
   requires the exact phrase "reset everything".

---

## Edge Cases

| Scenario | Handling |
|----------|----------|
| User runs `/setup` but profile.md already exists | Warn and ask to confirm overwrite before proceeding. Use Read tool to check for existing profile before Phase 1. |
| CSV path does not exist | Use Bash `ls` to check path. Suggest `data/` and `data/examples/` alternatives. |
| User provides warehouse type but no MCP | Mark Phase 2 as `partial` with reason "warehouse_mcp_needed". Continue to Phase 3. |
| User skips all optional fields | Fine. Record nulls ("not specified") and proceed. |
| User wants to jump to specific phase | If they say "/setup phase 3", read setup-state.yaml, verify Phases 1-2 are complete, then jump to Phase 3. |
| Session ends mid-interview | State is saved after each phase. Next `/setup` reads setup-state.yaml and resumes from first pending phase. |
| `/setup` called during active pipeline | Warn: "Setup changes may affect the running pipeline. Finish the pipeline first, or continue at your own risk." |
| User gives contradictory answers | Ask once for clarification: "Earlier you said X, now you're saying Y. Which should I record?" Use their final answer. |
| Setup-state.yaml exists but profile.md doesn't | This indicates inconsistent state (likely Phase 1 was marked complete but file wasn't written). Warn user: "Setup state says Phase 1 is complete, but profile.md is missing. I'll recreate it." Then run Phase 1 questions and create the file. |
