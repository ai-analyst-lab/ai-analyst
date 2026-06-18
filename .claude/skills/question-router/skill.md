---
name: question-router
description: |
  Classify incoming analytical questions into complexity levels (L1-L5) and route them to the appropriate response path. This skill ensures that simple questions get quick answers without unnecessary overhead, while complex investigations get the full analytical treatment they deserve. Use this skill at the start of EVERY user interaction that involves data analysis, metrics, business questions, or investigative requests. Trigger on phrases like "analyze", "why did", "what's happening with", "how many", "compare", "show me", "breakdown", "investigate", "root cause", "size the opportunity", "design an experiment", "create a deck", "run the pipeline", or ANY question that asks about data, metrics, trends, segments, funnels, user behavior, revenue, conversion, retention, or any other analytical topic. Also apply when users ask follow-up questions mid-analysis, when they request charts or visualizations, when they mention datasets or tables, when they ask about business performance, when they want to understand why something changed, or when they need to make a data-driven decision. This skill should be your FIRST step before launching any analytical workflow — it prevents wasting time on over-engineered responses to simple questions and ensures complex questions get the depth they deserve. Even if the question seems straightforward, use this skill to confirm the appropriate level of depth. Apply liberally.
---

# Skill: Question Router

## Purpose
Classify incoming user questions into complexity levels (L1-L5) and route
them to the appropriate response path. This replaces the old "skip-step"
logic with a structured classification that adapts the workflow depth to
the question's actual needs.

## When to Use
- At the start of every user interaction that looks like an analytical request
- Before launching the full 18-step pipeline
- When the user asks a follow-up question mid-analysis

## Classification Levels

**Note on /north-star routing:** Questions about North Star Metric design, audit, defense, diagnosis, or evolution route to `/north-star [verb]` — see the dedicated NSM intent section near the bottom of this file.

### L1: Factual Lookup
**Pattern:** User wants a specific number or fact from the data.
**Examples:**
- "How many users signed up in March?"
- "What's the average order value?"
- "How many products are in the electronics category?"
- *NSM L1:* "What's a leading indicator?" / "What's the difference between an NSM and an OKR?" / "What does the playbook say about vanity metrics?" → route to `/north-star explain <concept>`

**Response path:** Query the data directly. Return the answer with source
citation (table, column, filter). No agents needed.

**Time:** ~30 seconds

### L2: Simple Comparison
**Pattern:** User wants to compare two things or see a breakdown.
**Examples:**
- "Compare conversion rates by device"
- "Show me revenue by category"
- "What's the split of users by acquisition channel?"

**Response path:** Query + quick chart. Use `chart_helpers` directly.
Apply Visualization Patterns skill. No full pipeline.

**Time:** ~2 minutes

### L3: Guided Analysis
**Pattern:** User has a specific analytical question requiring multiple steps.
**Examples:**
- "Why did conversion drop last month?"
- "Which user segment has the highest LTV?"
- "Is our new checkout flow performing better?"
- *NSM L3:* "Is X a good north star metric?" / "Audit our NSM candidate" / "Pressure-test 'weekly active reviewing customers'" → route to `/north-star audit "<candidate>"`. Fast-pass triage: "Is this metric worth a full audit?" → route to `/north-star triage "<candidate>"`

**Response path:** Subset of the pipeline — Frame → Explore → Analyze →
Validate → Present findings. Skip storyboard/deck unless requested.
Use 3-5 agents.

**Time:** ~10 minutes

### L4: Deep Investigation
**Pattern:** User needs root cause analysis, opportunity sizing, or
experiment design.
**Examples:**
- "Investigate why mobile revenue dropped 15% in Q3"
- "Size the opportunity if we fix the cart abandonment issue"
- "Design an A/B test for the new pricing page"
- *NSM L4:* "Our north star hasn't moved in 60 days" → at v1.0+ routes to `/north-star diagnose`; at v0.1 the closest available help is `/north-star explain stalled-nsm` or reading `wiki/anti-patterns/lagging-indicator-as-nsm.md` directly. "How do I push back on the CEO's choice of MRR?" → similar pattern; at v0.1 surface what the wiki has on lagging-indicator anti-pattern + offer `/north-star audit "MRR"` which will refuse with the cited reasoning the user can paste into their conversation with the CEO. Do NOT announce "this verb ships at v1.0" to a user in the middle of a real problem — name the closest thing you CAN do and offer it.

**Response path:** Full pipeline minus deck. Frame → Hypothesize → Explore →
Analyze → Root Cause → Validate → Size → Present findings.
Use 6-10 agents.

**Time:** ~20 minutes

### L5: Full Presentation
**Pattern:** User wants a complete analysis with a polished slide deck.
**Examples:**
- "Run the full pipeline on Q4 performance"
- `/run-pipeline`
- "Build me a board-ready deck on our retention problem"
- *NSM L5:* "We need to pick a north star metric" / "Help us design an NSM from scratch" / "Walk us through the 8-step statement exercise" → route to `/north-star draft` (constrained-template mode in v0.1)

**Response path:** Complete 18-step pipeline. All agents, full storyboard,
charts, narrative, and Marp deck.

**Time:** ~30-45 minutes

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

1. **Feedback check** — The Feedback Capture skill runs BEFORE this router.
   By the time a message reaches here, corrections/learnings are already
   captured. If the message was purely feedback (no analytical question),
   it was handled upstream — skip routing.

2. **Entity disambiguation** — If the entity index is loaded (from bootstrap):
   - Call `resolve_entity(query_text, entity_index)` from
     `helpers/entity_resolver.py`.
   - If matches found, call `format_disambiguation(matches)` and set
     `{{RESOLVED_ENTITIES}}` for downstream agents.
   - Example: "why is cvr dropping?" → Resolved: 'cvr' -> conversion_rate (metric)
   - **ONLY REPORT IF MATCHES FOUND.** If no matches, silent skip.

3. **Corrections check** — Read `.knowledge/corrections/index.yaml`.
   - If `total_corrections > 0` for the active dataset, set
     `{{CORRECTION_COUNT}}` so analysis agents check the correction log
     before writing SQL (e.g., known join pitfalls, filter requirements).
   - **ONLY REPORT IF CORRECTIONS EXIST.** If index missing or count is 0, silent skip.

4. **Dataset detection** — Before classifying, check whether the question
   references a dataset other than the currently active one.
   - Read `.knowledge/datasets/` to get all known dataset IDs and display names.
   - Scan the user's question for exact or fuzzy matches to any dataset name.
   - **ONLY REPORT IF MISMATCH FOUND.** If no dataset reference or matches active, silent skip.
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

### Step 2: Score complexity signals

| Signal | L1 | L2 | L3 | L4 | L5 |
|--------|----|----|----|----|-----|
| Asks for a single number | +3 | | | | |
| Uses "compare" or "by {dimension}" | | +3 | | | |
| Uses "why", "investigate", "root cause" | | | | +3 | |
| Uses "analyze", "what's happening with" | | | +3 | | |
| Mentions "deck", "presentation", "slides" | | | | | +3 |
| Uses `/run-pipeline` | | | | | +5 |
| Mentions sizing, opportunity, impact | | | | +2 | |
| Mentions experiment, A/B test | | | | +2 | |
| Question has multiple sub-questions | | | +2 | +1 | |
| "Quick" or "just" qualifier | +2 | +1 | | | |

Assign the level with the highest score. Ties break toward the lower level
(prefer faster response).

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

Score these from the user's message and session context. Highest score wins.
Ties break to `narrated`.

| Signal | guided | narrated | autopilot |
|--------|:------:|:--------:|:---------:|
| "walk me through", "teach me", "step by step", "explain as you go" | +3 | | |
| "show me how you", "I want to learn" | +3 | | |
| Long-form prompt with framing/context (>80 words, multi-paragraph) | +1 | +1 | |
| Terse task-like prompt ("conversion by device last week") | | | +2 |
| User has already run ≥3 analyses in this session | | | +1 |
| Profile `technical_level: beginner` | +1 | | |
| Profile `technical_level: advanced` | | | +1 |
| User previously invoked `/pace X` this session | (persisted — see below) | | |
| `/run-pipeline` invocation without other signals | | +2 | |
| Mid-analysis follow-up ("now break by country") | | | +2 |
| "just run it", "silent", "don't narrate" | | | +3 |
| "slow down", "one step at a time", "pause between" | +3 | | |

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

Estimated time: ~[X] minutes.

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

**Never in autopilot:** don't emit banners. Final deliverable only.

**Never in guided or narrated:** don't skip banners. Silent execution in these
modes is the specific failure that pace mode exists to prevent.

---

## NSM Intent Routing (/north-star)

When the user's question is about a North Star Metric (design, audit, defense, diagnosis, evolution), route to `/north-star` instead of the L1-L5 analysis pipeline.

### Trigger phrases

**Explicit NSM mentions:**
- "north star metric" / "NSM" / "anchor metric"
- "is X a good north star" / "audit our NSM" / "pressure-test our north star"
- Colloquial framings: "the one number we care about" / "what we're optimizing for" / "the metric our CEO actually looks at" / "our strategic anchor"

Bare phrases like "primary success metric", "guiding metric", or "our team's main metric" are NOT enough to route to /north-star — they're L3 metric-analysis triggers and only route here when paired with explicit NSM lifecycle context (audit / design / defend / diagnose / evolve).

**Lifecycle-specific phrasing:**
- Design: "we need an NSM" / "help us pick" / "walk us through statement exercise"
- Audit: "is X right" / "audit this" / "pressure-test this candidate"
- Defense: "how do I push back on" / "CEO wants us to use X but..."
- Diagnosis: "NSM hasn't moved" / "stopped predicting" / "what's wrong with our metric"
- Evolution: "should we change our NSM" / "outgrown our north star"

### Verb dispatch table

| User phrasing | Verb | v0.1? |
|---|---|---|
| "explain X" / "what is X" (NSM concept) | `/north-star explain <slug>` | yes |
| "is X a good NSM" / "audit X" | `/north-star audit "<candidate>"` | yes |
| "worth a full audit?" / "quick check on X" | `/north-star triage "<candidate>"` | yes |
| "we need an NSM" / "help us design" | `/north-star draft` | yes (constrained-template) |
| "what input metrics" / "metric tree" | `/north-star inputs` | yes (greenfield-only) |
| "diagnose our NSM" / "stopped moving" | `/north-star diagnose` | v1.0 — escalate to `/north-star explain` |
| "defend X to CEO" / "push back" | `/north-star defend` | v1.0 — same escalation |
| "should we change" / "evolve our NSM" | `/north-star evolve` | v1.5 — same escalation |

### Disambiguation rules

1. **NSM-shaped phrasing wins over generic metric phrasing.** "our team's main metric" alone is L3 metric analysis; "our team's main metric — is it a good NSM?" routes to `/north-star audit`.
2. **`/metric-spec` for the spec, `/north-star` for the strategy.** "Define this metric" → `/metric-spec`. "Is this our north star?" → `/north-star audit`.
3. **Composition: when in doubt, defer to `/north-star`** if the user's intent involves the strategic anchor role of the metric, not its specific calculation.
4. **For deferred-version verbs** (defend, diagnose, evolve, etc. at v0.1), route to the closest available v0.1 verb + offer the relevant wiki page. **Do not name internal version numbers to the user** — P4 boundary speech says name what we CAN do, not what we can't. Bad: "diagnose ships at v1.0." Good: "The closest thing I can do today is run audit on your current NSM — if it's failing checklist criteria, that's often the root of 'stopped moving'. Want to try?"

---

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
6. **Never skip phase banners in guided or narrated mode.** Silent execution
   in these modes is the specific failure pace mode exists to prevent. If you
   catch yourself running a skill without announcing it first, stop and emit
   the banner retroactively before proceeding.
7. **Never block indefinitely in guided mode.** Pause points wait for one
   user turn. If the next message is a new analytical question, re-route —
   don't hold the old one open forever.
8. **Never let pace persistence failure block analysis.** If
   `working/session_state.yaml` can't be written, warn and continue in memory.
   The analysis always proceeds; persistence is best-effort.
9. **Never pick guided or autopilot as the default.** When auto-detection
   signals are mixed or absent, always default to `narrated`. Guided blocks;
   autopilot hides. Narrated is the only safe default.

---

## Why These Changes Matter

**Fast-path for L1:** Testing showed the full classification workflow adds
~40 seconds and ~9k tokens for simple lookups. The user who asks "how many
orders last month?" doesn't need to see pre-flight checks, scoring tables,
and skill adherence checklists — they need the answer. Fast-path detection
identifies obvious L1 questions and shortcuts to execution.

**Silent pre-flight:** Pre-flight enrichment (entity disambiguation, corrections
check) adds value ONLY when it finds something. Reporting "no entity matches,
no corrections, no dataset conflict" adds noise without insight. The improved
version only surfaces findings when they exist.

**Streamlined L1/L2 output:** The classification rationale matters for L3+
where you're asking the user to commit 10-20 minutes. For L1/L2, the decision
is already made — just execute and deliver. Save the process documentation for
internal tracking.
