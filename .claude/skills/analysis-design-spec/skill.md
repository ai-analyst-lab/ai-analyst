---
name: analysis-design-spec
description: |
  Produce an Analysis Design Spec before running any data query or analysis. Use this skill at the start of EVERY analytical request — whether it's "analyze why conversion dropped", "investigate this metric", "compare segments", "what was X last week", or any question involving data. This skill prevents wasted work by defining the question, decision, data needs, dimensions, time range, output format, and success criteria upfront. Apply even when users say "quick question" or "just pull this number" — the spec ensures you understand the decision context before querying. Skip ONLY if the user's request already explicitly states all seven fields (Question, Decision, Data Needed, Dimensions, Time Range, Output Format, Success Criteria) — which virtually never happens. The spec takes 2-5 minutes but prevents hours of rework from scope creep, misaligned analysis, or discovering data gaps mid-stream. When in doubt, use this skill. Trigger on phrases like: analyze, investigate, look into, what happened with, compare, segment, breakdown, explore, root cause, deep dive, trend, pattern, why did, what caused, show me, pull, calculate, measure. DISAMBIGUATION: this is the quick 7-field framing GATE that runs before every analysis — NOT the full design pipeline. When the user wants a multi-stage investigation design (hypothesis sharpening, confound scan, V1→V2 redesign after feedback), use `analysis-design` instead.
---

# Skill: Analysis Design Spec

## Purpose
Ensure every analysis starts with a clear plan — what question it answers, what decision it informs, what data it needs, and what "done" looks like — before any queries are written or data is explored.

## When to Use
Apply this skill at the start of every new analysis, before running the Data Explorer or any analysis agent. If a user asks you to analyze something, produce an Analysis Design Spec first. Skip only if the user provides a request that already covers all seven fields (rare).

## Instructions

### Step 1: Produce the Spec

Before touching data, fill in this template. Every field is required. If you can't fill a field, ask the user.

```markdown
## Analysis Design Spec

### 1. Question
What are we trying to answer?
[A specific, testable question — apply the Question Framing skill]

### 2. Decision
What will this analysis inform?
[A concrete action the team will take based on the answer]
[If the answer is "nothing specific" — this may be reporting, not analysis. Confirm with the user.]

### 3. Data Needed
| Data | Source | Available? | Notes |
|------|--------|-----------|-------|
| [metric/field] | [table/system] | Yes/No/Partial | [gaps, quality concerns] |

### 4. Dimensions
What should we segment or decompose by?
- [Dimension 1]: [why — what would different values tell us?]
- [Dimension 2]: [why]
- [Dimension 3]: [why]

### 5. Time Range & Granularity
- **Period:** [start date — end date]
- **Granularity:** [daily / weekly / monthly]
- **Comparison:** [vs. prior period / vs. same period last year / vs. benchmark]

### 6. Output Format
What deliverable does the user need?
- [ ] Quick answer (1-2 sentences + supporting number)
- [ ] Analysis report (structured findings with charts)
- [ ] Presentation deck (slides for stakeholders)
- [ ] Data table (for further analysis by the user)

### 7. Success Criteria
How will we know the analysis answered the question?
[Specific conditions — e.g., "Identify which segment drove >50% of the decline"
or "Determine whether the change is statistically meaningful at the segment level"]
```

### Step 2: STOP and Present the Spec

**After filling in all 7 fields, STOP before running any queries.**

Present the spec to the user and say:

> "I've drafted an Analysis Design Spec to ensure we're aligned before I start querying data. Please review the 7 sections above. Does this capture what you need? Any adjustments before I proceed?"

**Why this matters:** The spec might reveal data gaps, scope mismatches, or missing context. Catching these upfront saves hours of rework. The user might say "actually, I only need X" or "I forgot to mention Y" — that's gold.

### Step 3: Adjust if Needed

If the user requests changes, update the spec. Once aligned, proceed with the analysis.

### How to Use the Spec

**Before analysis:**
1. Fill in all 7 fields
2. **STOP and confirm with the user** — don't assume the spec is correct
3. Flag any data gaps in field 3 (apply the Tracking Gaps skill if needed)
4. Use field 4 to inform which agents to invoke and what segmentation to run

**During analysis:**
- Check the spec before each major step — are you still answering the stated question?
- If the analysis reveals a more interesting question, note it but finish the original question first
- Use field 7 to know when to stop — avoid analysis rabbit holes

**After analysis:**
- Verify the deliverable matches field 6
- Verify the success criteria in field 7 are met
- If criteria aren't met, note what's missing and why

### Scope Calibration

Not every request needs the same depth. Match the spec verbosity to the request type:

| Request Type | Spec Depth | Example | Typical Fields |
|-------------|-----------|---------|----------------|
| **Number pull** | Lightweight (1-2 sentences per field) | "What was revenue last month?" | Brief question, simple decision threshold, single metric, no dimensions |
| **Monitoring** | Medium (2-3 sentences per field) | "How is retention trending?" | Specific metric definition, comparison period, success thresholds |
| **Exploration** | Full (3-5 sentences per field) | "What's happening with signups?" | Multiple dimensions, hypotheses, data gaps documented |
| **Deep dive** | Comprehensive (full sections with sub-bullets) | "Why did conversion drop?" | Detailed data audit, 4+ dimensions with rationale, multiple success criteria |

**Rule of thumb:** A number pull spec should fit on one screen. A deep dive spec may span 2-3 screens with data limitation sections and pre-flight checklists.

### Writing Rules

1. **The question must be specific** — "How are users doing?" is not a question. "Did 7-day retention change for users who signed up after the redesign?" is.
2. **The decision must be actionable** — "We'll understand users better" is not a decision. "We'll decide whether to roll back the redesign" is.
3. **Dimensions must be justified** — don't segment by everything. Each dimension should have a reason: "Different devices have different UX, so conversion may differ."
4. **Success criteria must be falsifiable** — "Good analysis" is not a criterion. "Identify the segment responsible for >50% of the change" is.
5. **Output format must match the audience** — an executive gets a deck, a data scientist gets a table, a PM gets an analysis report.

## Examples

### Example 1: Root Cause Investigation

```markdown
## Analysis Design Spec

### 1. Question
Why did support ticket volume increase 55% in June compared to the prior 6-month average?

### 2. Decision
If the root cause is a product bug, we'll prioritize a hotfix. If it's seasonal or external, we'll adjust staffing.

### 3. Data Needed
| Data | Source | Available? | Notes |
|------|--------|-----------|-------|
| Support tickets (volume, category, severity) | {schema}.support_tickets | Yes | |
| User device and app version | {schema}.events | Yes | Need to join on user_id |
| Product release dates | Engineering team | Partial | May need to ask |

### 4. Dimensions
- Category: which types of tickets spiked?
- Device/platform: is it isolated to one platform?
- App version: did a specific release cause it?
- Severity: are these critical or minor?

### 5. Time Range & Granularity
- **Period:** Jan 1 – Jul 31 (7 months for baseline + anomaly)
- **Granularity:** Daily for the anomaly month, monthly for baseline
- **Comparison:** June vs. Jan-May average

### 6. Output Format
- [x] Analysis report (structured findings with charts)
- [ ] Presentation deck

### 7. Success Criteria
Identify the specific root cause (what changed, when, affecting whom) and quantify the excess ticket volume attributable to it.
```

### Example 2: Quick Number Pull

```markdown
## Analysis Design Spec

### 1. Question
What was the checkout conversion rate for mobile users last week?

### 2. Decision
Monitoring check — if it dropped below 2.5%, we'll investigate further.

### 3. Data Needed
| Data | Source | Available? | Notes |
|------|--------|-----------|-------|
| Checkout events by device | {schema}.events | Yes | |
| Purchase events | {schema}.orders | Yes | |

### 4. Dimensions
- None needed for the initial pull (just mobile, last week)

### 5. Time Range & Granularity
- **Period:** Last 7 days
- **Granularity:** Single number (weekly total)
- **Comparison:** vs. prior 4-week average

### 6. Output Format
- [x] Quick answer (1-2 sentences + supporting number)

### 7. Success Criteria
A single conversion rate number with context (vs. recent average). If below threshold, flag for investigation.
```

## Anti-Patterns

1. **Never start an analysis without knowing the decision it informs** — if you can't fill in field 2, you're doing a fishing expedition
2. **Never let the spec become a blocker** — for quick number pulls, fill it in one sentence per field and move on. The spec scales with the analysis complexity.
3. **Never ignore the spec mid-analysis** — if you discover something more interesting, note it as a follow-up question but finish what was asked first
4. **Never over-scope** — if the user asked a monitoring question, don't design a deep dive. Match the depth to the request.
5. **Never skip dimensions** — "Let me segment by everything" is not a plan. Choose 2-4 dimensions with reasons.
6. **Never proceed without user confirmation** — after producing the spec, STOP and ask if it looks right before running queries.
