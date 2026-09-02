---
name: question-router
description: |
  Classify every analytical request (anything about data, metrics, trends, segments, funnels, revenue, retention, experiments, or "why did X change") into complexity levels L1-L5 and route it before any analytical workflow starts, including follow-ups mid-analysis and chart requests. Simple lookups get a direct answer; investigations get the depth they need. Run this first even when the question looks simple.
---

# Skill: Question Router

## Purpose
Classify incoming user questions into complexity levels (L1-L5) and route
them to the appropriate response path.

## When to Use
- At the start of every user interaction that looks like an analytical request
- Before launching the full 18-step pipeline
- When the user asks a follow-up question mid-analysis

## Classification Levels

### L1: Factual Lookup
**Pattern:** User wants a specific number or fact from the data.
**Examples:**
- "How many users signed up in March?"
- "What's the average order value?"
- "How many products are in the electronics category?"

**Response path:** Query the data directly. Return the answer with source
citation (table, column, filter). No agents needed.

### L2: Simple Comparison
**Pattern:** User wants to compare two things or see a breakdown.
**Examples:**
- "Compare conversion rates by device"
- "Show me revenue by category"
- "What's the split of users by acquisition channel?"

**Response path:** Query + quick chart. Use `chart_helpers` directly.
Apply Visualization Patterns skill. No full pipeline.

### L3: Guided Analysis
**Pattern:** User has a specific analytical question requiring multiple steps.
**Examples:**
- "Why did conversion drop last month?"
- "Which user segment has the highest LTV?"
- "Is our new checkout flow performing better?"

**Response path:** Subset of the pipeline — Frame → Explore → Analyze →
Validate → Present findings. Skip storyboard/deck unless requested.
Use 3-5 agents.

### L4: Deep Investigation
**Pattern:** User needs root cause analysis, opportunity sizing, or
experiment design.
**Examples:**
- "Investigate why mobile revenue dropped 15% in Q3"
- "Size the opportunity if we fix the cart abandonment issue"
- "Design an A/B test for the new pricing page"

**Response path:** Full pipeline minus deck. Frame → Hypothesize → Explore →
Analyze → Root Cause → Validate → Size → Present findings.
Use 6-10 agents.

### L5: Full Presentation
**Pattern:** User wants a complete analysis with a polished slide deck.
**Examples:**
- "Run the full pipeline on Q4 performance"
- `/run-pipeline`
- "Build me a board-ready deck on our retention problem"

**Response path:** Complete 18-step pipeline. All agents, full storyboard,
charts, narrative, and Marp deck.

## Classification Algorithm

### Fast-Path Detection (optional shortcut for obvious L1 questions)

Before running the full classification workflow, check if the question matches
an obvious L1 pattern. If YES, skip to L1 execution immediately. If NO or
UNCERTAIN, proceed to Step 0.

**Trigger phrases for fast-path L1:**
- Starts with "how many" or "how much"
- Starts with "what's the total" or "what's the average"
- Starts with "count of" or "number of"
- Contains "count" + single metric/entity + optional time filter
- Examples:
  - "how many orders last month?"
  - "what's the total revenue in Q4?"
  - "count of users who converted"

**Do NOT fast-path if:**
- Question contains "compare", "by", "breakdown", or "split"
- Question contains "why", "investigate", or "analyze"
- Question mentions multiple metrics or dimensions
- Question references a product change or hypothesis
- You're uncertain whether it's genuinely simple

**Why fast-path matters:** L1 questions don't benefit from the full classification
overhead. The user wants a quick answer, not a classification report. Fast-path
saves ~40 seconds and ~7-9k tokens for simple lookups.

**Output format for fast-path L1:**
- Answer the question directly
- Include source citation (table, column, filter)
- Offer 2-3 contextual next actions
- Skip the classification documentation

If you use the fast-path, you're done — don't proceed to Step 0 or beyond.

---

### Step 0: Pre-flight (runs on every query before classification)

Enrichment steps — never block routing. If any sub-step fails, skip it silently.
**IMPORTANT:** Only report pre-flight findings if they actually find something.
Silent skip if nothing found.

1. **Feedback check** — If the message is a correction or feedback with no
   analytical question, hand it to the `log-correction` skill and skip routing.

2. **Entity disambiguation** — If the entity index is loaded (from bootstrap):
   - Call `resolve_entity(query_text, entity_index)` from
     `helpers/knowledge/entity_resolver.py`.
   - If matches found, call `format_disambiguation(matches)` and set
     `{{RESOLVED_ENTITIES}}` for downstream agents.
   - Example: "why is cvr dropping?" → Resolved: 'cvr' -> conversion_rate (metric)

3. **Corrections check** — Read `.knowledge/corrections/index.yaml`.
   - If `total_corrections > 0` for the active dataset, set
     `{{CORRECTION_COUNT}}` so analysis agents check the correction log
     before writing SQL (e.g., known join pitfalls, filter requirements).

4. **Dataset detection** — Before classifying, check whether the question
   references a dataset other than the currently active one.
   - Read `.knowledge/datasets/` to get all known dataset IDs and display names.
   - Scan the user's question for exact or fuzzy matches to any dataset name.
   - If a non-active dataset is referenced:
     - Inform the user: "It looks like you're asking about **{display_name}**, but
       the active dataset is **{active_display_name}**."
     - Offer: "Want me to switch? (`/switch-dataset {id}`)"
     - Do NOT proceed with analysis until the user confirms which dataset to use.

5. **Archaeology note** — The Query Archaeology skill provides SQL pattern
   context (prior queries, reusable CTEs) to analysis agents when available.
   No action needed here — just acknowledge it flows downstream automatically.

After pre-flight completes, proceed to Step 1.

---

### Step 1: Parse the question

Extract:
- **Subject:** What entity/metric is being asked about?
- **Action:** Lookup, compare, analyze, investigate, or present?
- **Scope:** Single metric, breakdown, multi-dimensional, or end-to-end?
- **Output expectation:** Number, chart, findings, or deck?

### Step 2: Classify by the strongest signal

Classify by the strongest signal present, in this order: `/run-pipeline` or
"deck / presentation / slides" → L5; "why / investigate / root cause", sizing or
opportunity, experiment or A/B test → L4; "analyze / what's happening with", or a
question with several sub-questions → L3; "compare / by {dimension} / breakdown /
split" → L2; a single number → L1. A "quick" or "just" qualifier drops one
level. When two levels are equally supported, take the lower one (prefer the
faster response).

### Step 3: Adapt from user profile

If `.knowledge/user/profile.md` exists, read the user's preferences:
- **Detail level = "executive-summary":** Bias one level down (L3 → L2)
- **Detail level = "deep-dive":** Bias one level up (L2 → L3)
- **Technical level = "advanced":** Show more SQL, skip explanations
- **Technical level = "beginner":** Add more context, explain terms

### Step 3.5: Pace Mode Selection (L3+ only; skip for L1/L2)

Pace mode is **orthogonal to complexity level**. Level decides *which agents run*;
pace decides *how visible the machinery is*. Any level can run in any mode.

| Mode | Behavior | Best For |
|------|----------|----------|
| **guided** | Announce each phase. Run it. Pause. Wait for `/continue` (or any affirmative reply) before the next phase. | Demos, teaching, first-time users, high-stakes analyses where oversight matters |
| **narrated** | Announce each phase, run it, announce the result, proceed immediately to the next phase. End-to-end but machinery is visible. | Normal use — the user wants to follow the reasoning but not block the flow |
| **autopilot** | Silent end-to-end. No phase banners. Final output only. | Expert users, tight iteration loops, mid-analysis follow-ups |

**Default when no signal is clear: `narrated`.** Never default to guided (blocks the
user) or autopilot (hides the work). Narrated is the failure-safe middle ground.

#### Auto-detection signals

Read these from the user's message and session context. Pick **guided** on
teaching or pacing language ("walk me through", "teach me", "step by step",
"slow down", "one step at a time") or a `technical_level: beginner` profile.
Pick **autopilot** on "just run it / silent / don't narrate", a terse task-like
prompt ("conversion by device last week"), a mid-analysis follow-up ("now break
by country"), or an advanced profile in a session that has already run several
analyses. Otherwise, including a bare `/run-pipeline`, pick **narrated**. A
`/pace` choice persisted this session overrides all of these (see below).

#### Persisted mode (survives across phases and sessions)

On every router run, read `working/session_state.yaml`. If `pace_mode` is set,
use it as the starting mode **regardless of auto-detected signals** — an
explicit user choice beats heuristics.

The `/pace` skill writes this key. On session resume (`/resume-pipeline`), the
persisted mode is honored.

#### Override commands (honored at any time, including mid-phase)

- `/pace guided` | `/pace narrated` | `/pace autopilot` — switch modes
- `/continue` — in guided mode, proceed past the current pause point
- `/skip {phase}` — skip the named upcoming phase (e.g., `/skip validation`)
- `/explain` — during a guided pause, expand on the output of the phase that
  just completed before continuing
- `/abort` — stop the current analysis, discard in-progress work (preserve
  `working/` artifacts for inspection)

### Step 4: Respond based on classification level

**For L1-L2:** Execute immediately. No confirmation needed. Streamlined output:
- Answer the question (or produce chart)
- Include source citation (table, column, filter)
- Offer 2-3 contextual next actions
- **Do NOT include:** Full classification rationale, pre-flight details (unless
  something was found), complexity scoring table, skill adherence checklist.
  Save that documentation for your own internal tracking — the user just wants
  the answer.

**For L3-L5:** Brief the user on the plan AND the pace BEFORE executing:
```
I'd classify this as a **[Level] — [Label]**.

**Pace: {mode}** ({one-line rationale — e.g., "detected teaching signals",
"default for L3+", "persisted from earlier `/pace` command"})
- guided → I'll pause after each phase and wait for `/continue`.
- narrated → I'll announce each phase and run end-to-end.
- autopilot → I'll run silently and show you the final deliverable.

**Plan:**
1. [Phase name] — [one-line purpose]
2. [Phase name] — [one-line purpose]
...

Reply to proceed, or:
- `/pace {other_mode}` to change how I surface the work
- Adjust the scope in your own words ("skip validation", "go deeper on X")
```

Include any relevant pre-flight findings (dataset mismatch, corrections available,
resolved entities) in this confirmation message.

The user can:
- **Confirm:** Proceed with the plan at the proposed pace
- **Adjust up:** "Go deeper" → bump to next level
- **Adjust down:** "Just give me the quick answer" → drop to lower level
- **Change pace:** `/pace guided|narrated|autopilot` → re-brief with new pace

---

## Integration with Pipeline

When routed to L3+, the Question Router hands off to the appropriate agents
by setting the entry point in the Default Workflow:

| Level | Entry Point | Exit Point | Validation Tier |
|-------|-------------|------------|-----------------|
| L1 | Direct query | Answer inline | Tier 1 only (always-on) |
| L2 | Direct query + chart | Answer inline | Tier 1 only (always-on) |
| L3 | Step 1 (Frame) | Step 7 (Validate) — present findings inline | Tier 1 always + Tier 2 offered (CP 2.1) |
| L4 | Step 1 (Frame) | Step 8 (Size) — present findings inline | Tier 2 default (CP 2.1 menu) |
| L5 | Step 1 (Frame) | Step 18 (Close the Loop) — full deck | Tier 2 default, Tier 3 available (CP 2.1 menu) |

---

## Contextual Suggestions

After delivering results at any level, offer 2-3 relevant next actions based
on what was just completed. Match suggestions to the level and findings.

**After L1/L2 results:**
- "Want to break this down by [dimension from schema]?"
- "Want to see how this trended over time?"
- "Want to compare this across [available segment]?"

**After L3 findings:**
- "Want me to investigate the root cause of [top finding]?"
- "Want to size the opportunity if we fix [issue]?"
- "Want a deck of these findings for [audience]?"

**After L4 investigation:**
- "Want me to design an experiment to test [hypothesis]?"
- "Want a presentation-ready deck?"
- "Want to check this against [related metric from dictionary]?"

**After L5 deck delivery:**
- "Want to archive this analysis? (`/archive`)"
- "Want to explore a related question?"
- "Want to export in a different format? (`/export`)"

Always tailor suggestions to the actual findings — reference specific metrics,
segments, or anomalies discovered. Generic suggestions ("want to know more?")
are not helpful.

---

## Edge Cases

- **Ambiguous questions:** Default to L2, ask a clarifying question. "Do you
  want a quick breakdown, or should I investigate the drivers?"
- **Follow-up after analysis:** Re-classify. "Now make a deck" bumps a
  completed L3 to L5 (but reuses existing analysis, skips to Step 9).
- **Multiple questions in one message:** Classify each separately. Execute
  the highest-level one, note the others as follow-ups.
- **Non-analytical requests:** "Help me write a SQL query" or "Explain this
  chart" — handle directly without classification.
- **Guided-mode silence:** If the user doesn't reply after a guided pause
  point, do NOT block indefinitely. Treat any next message (even a new
  unrelated question) as implicit intent to move on. If the next message is a
  new analytical question, re-route it — treat the paused one as abandoned
  and preserve its `working/` artifacts untouched.
- **Mode switch mid-phase:** `/pace X` takes effect at the **next phase
  boundary**, never mid-phase. Tell the user which phase it applies from.
- **Unknown `/pace` argument:** Echo the valid modes and ask which they want;
  do not silently fall back.
- **`working/session_state.yaml` write fails:** Honor the requested mode for
  the current session in memory. Warn the user: "Pace set to X for this
  session but I couldn't persist it — `/pace X` again after resume." Never
  let a persistence failure block the analysis.

---

## Phase Banner Format

Every time a skill or agent begins executing inside an L3+ analysis, emit a
**phase banner** so the user can see the machinery. This is the entire point
of narrated and guided modes.

**Opening banner:**
```
▶ Phase {n}/{N}: {Skill or Agent Name}
  Why: {one-line reason this phase is firing now}
  Input: {brief summary — not a dump — of what's being fed in}
```

**Closing banner:**
```
✓ {Phase name} complete — {one-line result summary}
```

**In guided mode, append to the closing banner:**
```
  Reply to proceed, or: /explain (expand on this phase), /skip (skip next),
  /pace {mode} (change pace), /abort (stop).
```

**On failure:**
```
✗ {Phase name} failed — {reason}.
  Options: retry (reply "retry"), skip (reply "skip"), abort (/abort).
```

**Mode-specific rules:**

| Mode | Opening banner | Work | Closing banner | Pause? |
|------|:--------------:|:----:|:--------------:|:------:|
| guided | ✓ | ✓ | ✓ + prompt | **yes** |
| narrated | ✓ | ✓ | ✓ | no |
| autopilot | — | ✓ | — | no |

---

## Anti-Patterns

1. **Never run the full 18-step pipeline for an L1 question.** "How many
   users do we have?" should not trigger hypothesis generation.
2. **Never skip validation for L3+ questions.** Even guided analyses need
   a sanity check before presenting results.
3. **Never assume the user wants a deck.** Only create slides if explicitly
   requested or classified as L5.
4. **Never re-classify mid-execution without user input.** If you realize
   the question is more complex than initially classified, pause and ask.
5. **Never include classification overhead in L1/L2 output.** The user asked
   "how many orders?" — give them the number, not a 3-page classification report.
