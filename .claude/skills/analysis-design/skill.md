---
name: analysis-design
description: |
  Takes a vague analytical hunch, stakeholder request, or business question and produces a rigorous, stakeholder-ready analysis plan through a multi-stage pipeline. Use this skill whenever someone says "I think X caused Y", "help me investigate...", "design an analysis for...", "can you look into why...", "we need to figure out what's driving...", or presents any analytical question that needs methodological rigor before execution. This skill is essential when a PM has a hunch but no plan, when an analysis needs redesign after stakeholder feedback, or before starting any major investigation to prevent wasted work. The skill orchestrates hypothesis sharpening → confound scanning → investigation planning → V1 execution → feedback synthesis → V2 redesign. Apply this whenever the user is moving from vague intuition to structured investigation, when they're about to dive into data without a clear plan, when they need to validate an analytical approach before running queries, or when they're iterating on findings after stakeholder review. Key phrases that should trigger this: "analyze why", "investigate", "figure out what caused", "design an experiment", "help me understand", "look into", "what's driving", "V2 after feedback", "stakeholder comments", "redesign the analysis". DISAMBIGUATION vs `analysis-design-spec`: that skill is the lightweight 7-field framing gate that runs before EVERY analysis; reach for THIS heavier on-demand multi-agent pipeline only when there's a real hunch to sharpen, confounds to scan, or a V1→V2 redesign — not for routine upfront framing of a straightforward question.
---

# Skill: Analysis Design

**Trigger:** `/analysis-design`, "design an analysis for...", "I think X caused Y", "help me investigate..."
**Type:** Orchestrator — runs a multi-agent pipeline

---

## Purpose

Takes a vague analytical hunch, stakeholder request, or business question and produces a rigorous, stakeholder-ready analysis plan through a multi-stage pipeline. Chains three specialized agents: Hypothesis Sharpener → Confound Scanner → (optional) Feedback Synthesizer.

This skill orchestrates the full lifecycle: **hunch → testable hypothesis → threat assessment → investigation plan → V1 execution → feedback synthesis → V2 redesign.**

---

## When to Use

- A PM has a hunch but no plan: "I think removing the widget caused repeat purchases to drop"
- A vague request lands: "Can you look into why conversion dropped?"
- An analysis needs redesign after stakeholder feedback: "Here's V1 and the comments — help me build V2"
- Before starting any major investigation (prevents wasted work)

---

## Inputs

| Input | Required | Source | Description |
|-------|----------|--------|-------------|
| `{{HUNCH}}` | Yes | User | The vague hypothesis, business question, or analytical request |
| `{{DATA_PATH}}` | No | User or auto-detect | Path to relevant dataset(s). If not provided, uses active dataset from `.knowledge/active.yaml` |
| `{{AUDIENCE}}` | No | User | Who will consume the analysis (e.g., "VP of Product", "exec team", "cross-functional leads") |
| `{{V1_FINDINGS}}` | No | User or working/ | Path to V1 analysis output — triggers V2 redesign flow |
| `{{FEEDBACK}}` | No | User | Stakeholder feedback (comments, meeting transcript, Slack thread) — triggers Feedback Synthesizer |
| `{{URGENCY}}` | No | User | Timeline constraint (e.g., "need by EOD", "board meeting Friday"). Affects investigation depth. |

---

## CRITICAL: First Action - Show Architecture Preview

**BEFORE doing ANYTHING else, output the architecture preview.** This is the very first thing you do when this skill is invoked. Do not read agent files, do not start Stage 1, do not process inputs — show the preview first.

### Preview Format

**If {{V1_FINDINGS}} or {{FEEDBACK}} is provided (V2 redesign scenario):**

```
ANALYSIS DESIGN PIPELINE — V2 REDESIGN
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
V1 analysis + feedback detected.

Skipping Stages 1-3 (Hypothesis Sharpener, Confound Scanner, Investigation Plan).
Jumping directly to Stage 4: Feedback Synthesizer.

This stage will:
- Extract and categorize each piece of feedback
- Assess what V1 got right, wrong, and missed
- Design V2 investigation plan addressing all stakeholder concerns
- Map each feedback item to specific V2 analysis steps

Starting Stage 4...
```

**Otherwise (fresh analysis scenario):**

```
ANALYSIS DESIGN PIPELINE
━━━━━━━━━━━━━━━━━━━━━━━━
I'll investigate this in 3 stages:
  1. Hypothesis Sharpener — turn your hunch into a testable claim
  2. Confound Scanner — find everything that could make this wrong
  3. Investigation Plan — prioritize what to check first

Starting Stage 1...
```

**If {{URGENCY}} is detected, add:**

```
⏰ URGENCY DETECTED: {{URGENCY}}
Applying timeline compression:
- Prioritizing core investigation steps
- Flagging optional deep-dives that may be skipped
- Setting explicit scope boundaries
```

---

## Pipeline Flow

```
/analysis-design "{{HUNCH}}"
       │
       ├─ FIRST: Output Architecture Preview (see above)
       │
       ├─ Does the user have V1 + feedback?
       │   YES → Skip to Stage 4 (Feedback Synthesizer)
       │   NO  → Start from Stage 1
       │
       ▼
  ┌─────────────────────────────────────┐
  │  STAGE 1: Hypothesis Sharpener      │
  │  Agent: agents/hypothesis-sharpener │
  │                                     │
  │  Input:  {{HUNCH}}                  │
  │  Output: Testable hypothesis,       │
  │          Analysis Design Brief,     │
  │          natural experiments found, │
  │          key segments identified    │
  └──────────────┬──────────────────────┘
                 │
                 ├─ ⏸ CHECKPOINT: Present Stage 1 summary.
                 │   Output: "⏸ STAGE 1 COMPLETE
                 │   Review the hypothesis above.
                 │   Reply 'continue' to proceed to Stage 2,
                 │   or provide corrections."
                 │   STOP HERE. WAIT for user response.
                 │   Do NOT proceed to Stage 2 automatically.
                 │
                 ▼
  ┌─────────────────────────────────────┐
  │  STAGE 2: Confound Scanner          │
  │  Agent: agents/confound-scanner     │
  │                                     │
  │  Input:  Sharpened hypothesis +     │
  │          data context               │
  │  Output: Threats to validity,       │
  │          concurrent changes,        │
  │          data quality flags,        │
  │          selection biases           │
  └──────────────┬──────────────────────┘
                 │
                 ├─ ⏸ CHECKPOINT: Present Stage 2 summary.
                 │   Output: "⏸ STAGE 2 COMPLETE
                 │   Review the confounds above.
                 │   Reply 'continue' to proceed to Stage 3,
                 │   or provide corrections."
                 │   STOP HERE. WAIT for user response.
                 │   Do NOT proceed to Stage 3 automatically.
                 │
                 ▼
  ┌─────────────────────────────────────┐
  │  STAGE 3: Investigation Plan        │
  │  (Skill generates directly)         │
  │                                     │
  │  Combines Stage 1 + Stage 2 into   │
  │  a prioritized investigation plan   │
  │  with criteria (no time estimates)  │
  └──────────────┬──────────────────────┘
                 │
                 ├─ USER CHECKPOINT: "Review the plan?"
                 │   APPROVE → Execute V1
                 │   MODIFY → Re-run with adjustments
                 │
                 ▼
  ┌─────────────────────────────────────┐
  │  STAGE 3b: V1 Execution             │
  │  (Skill runs analysis using         │
  │   Descriptive Analytics agent or    │
  │   direct Python/SQL as appropriate) │
  │                                     │
  │  Output: V1 findings summary        │
  │          saved to working/          │
  └──────────────┬──────────────────────┘
                 │
                 ├─ Present V1 to user
                 │   "Share with stakeholders and
                 │    come back with feedback"
                 │
                 │  ... stakeholder feedback arrives ...
                 │
                 ▼
  ┌─────────────────────────────────────┐
  │  STAGE 4: Feedback Synthesizer      │
  │  Agent: agents/feedback-synthesizer │
  │                                     │
  │  Input:  V1 findings + {{FEEDBACK}} │
  │  Output: Categorized feedback,      │
  │          V1 right/wrong assessment, │
  │          V2 investigation plan,     │
  │          stakeholder answer map     │
  └──────────────┬──────────────────────┘
                 │
                 ▼
          V2 Analysis Plan
          (stakeholder-ready)
```

---

## Stage 3: Investigation Plan Generation

After the Hypothesis Sharpener and Confound Scanner run, the skill synthesizes their outputs into a prioritized investigation plan. The plan MUST include:

### Required Elements

1. **Analysis Design Brief** (populated from Stage 1 + Stage 2):
   ```
   QUESTION:    [from Hypothesis Sharpener Step 1 — the specific investigation question]
   DECISION:    [from user context — what action depends on the answer]
   HYPOTHESIS:  [from Hypothesis Sharpener]
   COMPARISON:  [from Hypothesis Sharpener — natural experiments, baselines]
   SEGMENTS:    [from Hypothesis Sharpener — key cuts identified]
   CONFOUNDS:   [from Confound Scanner — all threats listed]
   CRITERIA:    [from Hypothesis Sharpener — accept/reject thresholds]
   ```

2. **Prioritized Steps** — ordered by information value (what eliminates the most uncertainty fastest). Use a **3-column table** (no time estimates):
   | # | Step | Why First |
   |---|------|-----------|
   | 1 | [what to check — concise] | [what it eliminates] |

3. **Confound Control Strategy** — how each confound from Stage 2 will be addressed:
   | Confound | Control Method | Data Needed |
   |----------|---------------|-------------|
   | ... | ... | ... |

4. **Kill Criteria** — what would make you STOP the investigation early:
   - "If [condition], the hypothesis is rejected — stop here"
   - "If [condition], data quality is insufficient — escalate to Data Eng"

### Urgency Handling

If `{{URGENCY}}` is set:
- **EOD:** Compress to top-3 steps only. Skip confound controls that require new data pulls. Flag what's being skipped.
- **This week:** Full plan, but prioritize ruthlessly. Parallelize where possible.
- **No rush:** Full plan with optional deep-dives.

---

## Output Files

### Intermediate Files (working/)

| Stage | Output Path | Content |
|-------|------------|---------|
| Stage 1 | `working/hypothesis_{{DATE}}.md` | Sharpened hypothesis + Analysis Design Brief |
| Stage 2 | `working/confound_scan_{{DATE}}.md` | Threats to validity |
| Stage 3 | `working/investigation_plan_{{DATE}}.md` | Prioritized plan |
| Stage 3b | `working/v1_findings_{{DATE}}.md` | V1 analysis results |
| Stage 4 | `working/v2_plan_{{DATE}}.md` | V2 redesign with stakeholder answer map |

### Final Deliverable: Analysis Plan Document

The final output of each pipeline run is a **stakeholder-friendly analysis plan document** — a structured Google Doc (or markdown) that you'd share with your pod (PM, tech lead, data scientist). The document should be written in natural prose, not framework skeleton format.

**Document structure:**

1. **Context** — what happened, why we're investigating, what decision depends on the answer
2. **Questions** — primary question + supporting questions, each specific and answerable with rationale
3. **Approach** — population, metric definition, key comparisons, segments to check
4. **Known risks and concurrent changes** — confounds called out before analysis runs
5. **Investigation priority** — ordered steps, with reasoning for the order
6. **What would change our conclusion** — explicit accept/reject criteria in plain language
7. **Deliverables** — what the output of the analysis will be

For V2 plans, also include:
- **What V1 established / could not resolve**
- **Stakeholder feedback incorporated** — table mapping each concern to how V2 addresses it
- **Revised questions** — what's new or changed from V1

Generate the document via the Google Doc Creator agent (see `agents/google-doc-creator.md`) with Google Doc Export skill formatting (navy blue headings, bold callout labels, proper table spacing). If Google Workspace MCP is not available, output as clean markdown.

---

## Checkpoints

| Checkpoint | Type | When | Skippable? |
|------------|------|------|------------|
| Plan Review | B (draft review) | After Stage 3 generates plan | Yes — "just do it" skips |
| V1 Presentation | C (branch decision) | After Stage 3b | No — user must decide to gather feedback or proceed |

---

## Integration with Other Skills

- **Analysis Design Spec skill** — this skill supersedes it for complex investigations. For simple L1/L2 questions, Analysis Design Spec is sufficient.
- **`/stress-test`** — can be invoked independently on ANY analysis plan (not just ones produced by this skill)
- **Descriptive Analytics agent** — called during Stage 3b for V1 execution
- **Question Framing skill** — fires automatically at Stage 1 if the hunch is too vague to sharpen

---

## Examples

### Simple: Hunch to Plan
```
/analysis-design "I think our repeat purchase rate dropped because we removed the post-purchase recommendations widget last month"
```
→ Runs Stages 1-3, outputs investigation plan

### With Data
```
/analysis-design "Why did conversion drop last week?" data=data/cartloop_transactions.csv audience="VP Product"
```
→ Runs Stages 1-3b, executes V1 analysis on the data

### V2 Redesign (skip to Stage 4)
```
/analysis-design v1=working/v1_findings_2026-03-28.md feedback="VP says loyalty program is a confound. Marketing says the promo inflated baselines. Data Eng says mobile tracking pixel changed mid-month."
```
→ Runs Stage 4 only, outputs V2 plan

### Full Lifecycle
```
/analysis-design "I think the new onboarding flow is causing enterprise churn" data=data/enterprise_accounts.csv audience="VP Customer Success" urgency="board meeting Friday"
```
→ Runs all stages with urgency compression
