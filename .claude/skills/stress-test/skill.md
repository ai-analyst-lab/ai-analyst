---
name: stress-test
description: |
  Pressure-test any analysis plan, investigation design, or analytical approach for hidden methodological flaws before execution. Acts as a "senior data scientist code review" for your analytical thinking, catching issues like wrong baselines, survivorship bias, missing segments, uncontrolled confounds, and absent kill criteria. Use this skill BEFORE committing time to executing an analysis — whether you've designed it via /analysis-design, written it yourself, received it from a stakeholder, or pulled it from a document. Apply this skill whenever someone says "stress test this plan", "review my analysis design", "check my approach", "is this analysis sound?", "can you review my investigation plan?", "does this approach make sense?", "gut-check this analysis", "what am I missing in this design?", "validate my analytical approach", or explicitly invokes `/stress-test`. This skill is critical when you're about to present an analysis design to stakeholders, when committing a week to executing a plan, when reviewing someone else's analytical approach, when an analysis came back with unexpected results and you're wondering if the design was flawed, when you want a methodological sanity check, when designing a high-stakes investigation, when a PM hands you an analysis brief to execute, or anytime you need rigorous validation of analytical thinking before work begins. The skill works standalone — it reviews ANY plan, regardless of how it was created. It produces a 7-point diagnostic with PASS/WARNING/FAIL verdicts, critical issues, warnings, recommended fixes, and an overall grade (A-F). This is your safety net against analytical mistakes that waste time, mislead stakeholders, or produce unreliable conclusions.
---

# Skill: Stress Test

**Type:** Standalone — reviews any analysis plan for methodological flaws

---

## Purpose

Takes an analysis plan, investigation design, or analytical approach and pressure-tests it for hidden flaws — wrong baselines, survivorship bias, missing segments, uncontrolled confounds, and absent kill criteria. Acts as a "senior data scientist code review" for your analytical thinking.

This skill is **standalone** — it works on any analysis plan, whether produced by `/analysis-design`, written by the user, or pulled from an existing document.

---

## When to Use

- Before committing a week to executing an analysis plan
- Before presenting an analysis design to stakeholders
- When you've written an analysis brief and want a gut-check
- When reviewing someone else's analytical approach
- After an analysis came back with unexpected results (was the design flawed?)

---

## Inputs

| Input | Required | Source | Description |
|-------|----------|--------|-------------|
| `{{PLAN}}` | Yes | User or file path | The analysis plan to review. Can be a file path, pasted text, or a description of the approach |
| `{{CONTEXT}}` | No | User | Business context — what decision this analysis will inform |
| `{{AUDIENCE}}` | No | User | Who will consume the results (affects what counts as "fatal" vs. "nice to have") |
| `{{DATA_DESCRIPTION}}` | No | User | Description of available data, if not obvious from the plan |

---

## The 7-Point Stress Test

**CRITICAL FIRST STEP: Check data availability BEFORE methodology review.**

Before reviewing methodology quality, immediately verify that required data exists:
1. Read the active dataset schema (`.knowledge/datasets/{active}/schema.md`)
2. Check if the plan's required fields/tables/dimensions exist in the dataset
3. If ANY required data is missing → HALT, skip checkpoints 1-6, jump straight to checkpoint 7, assign FAIL verdict with BLOCKER status, provide F grade, and stop
4. If all required data exists → proceed with checkpoints 1-7 in order

**Why this matters:** A methodologically perfect plan that requires non-existent data is useless. Data availability is a BLOCKER that makes all other issues irrelevant. Check it FIRST, not last.

**Common data blockers to check for:**
- Plan requires device/platform segmentation → check if device, platform, or user_agent fields exist
- Plan requires funnel analysis → check if event-level tracking exists (page views, clicks, sessions)
- Plan requires traffic source attribution → check if source, medium, campaign, or referrer fields exist
- Plan requires geographic segmentation → check if country, region, city, or geo fields exist
- Plan assumes conversion rate → check if both numerator (orders, signups) AND denominator (sessions, page views) data exist

---

After confirming data availability, review the plan against each checkpoint. For each one, assign a verdict: PASS, WARNING, or FAIL.

### 1. Hypothesis Clarity

**Check:** Is there a specific, testable hypothesis? Or is this a fishing expedition?

| Verdict | Criteria |
|---------|----------|
| PASS | Hypothesis is falsifiable with a clear claim about cause and effect |
| WARNING | Hypothesis exists but is vague ("engagement is down") or has multiple interpretations |
| FAIL | No hypothesis — plan is "explore the data and see what we find" |

**Fix if FAIL:** "State what you expect to find AND what would prove you wrong."

### 2. Baseline Validity

**Check:** Is the comparison group / baseline appropriate?

| Verdict | Criteria |
|---------|----------|
| PASS | Baseline accounts for seasonality, concurrent changes, and selection effects |
| WARNING | Baseline is reasonable but has known gaps (e.g., no YoY comparison available) |
| FAIL | Baseline is naive (e.g., "compare to last week" without checking for holidays, campaigns, or deployments) |

Common traps to check:
- Comparing to a period with a holiday, major campaign, or outage
- Before/after with no control group
- Comparing cohorts of different sizes or compositions
- Using "last month" when the metric is seasonal

**Fix if FAIL:** "Identify 2-3 alternative baselines and explain why each is valid or invalid."

### 3. Survivorship Bias

**Check:** Does the analysis only look at entities that "survived" to be measured?

| Verdict | Criteria |
|---------|----------|
| PASS | Analysis includes churned/dropped users, failed transactions, abandoned sessions |
| WARNING | Survivorship risk is acknowledged but not controlled for |
| FAIL | Analysis only includes "active" or "completed" entities without acknowledging what's excluded |

Common traps:
- "Average revenue per user" that only counts users who made a purchase
- "Onboarding completion rate" that only counts users who started onboarding
- "Feature satisfaction" survey that only reaches users who didn't churn
- Retention analysis that excludes users who churned before the measurement window

**Fix if FAIL:** "Explicitly define the denominator. Who is EXCLUDED from this analysis and why?"

### 4. Segment Coverage

**Check:** Will the analysis check for segment-level differences that could reverse the overall finding?

| Verdict | Criteria |
|---------|----------|
| PASS | Plan includes segment breakdowns on 3+ dimensions with explicit Simpson's paradox check |
| WARNING | Plan checks 1-2 segments but doesn't systematically test all categorical dimensions |
| FAIL | Plan only reports overall/aggregate numbers |

Key segments to always check:
- Device (mobile/desktop/tablet)
- Platform (iOS/Android/web)
- User tenure (new/returning/power user)
- Geography (if multi-market)
- Traffic source / acquisition channel
- Product category / feature area
- Customer tier / plan type

**Fix if FAIL:** "Add segment breakdowns for every categorical dimension with >2 values. Flag any reversal."

### 5. Confound Identification

**Check:** Does the plan identify and control for concurrent changes?

| Verdict | Criteria |
|---------|----------|
| PASS | Plan lists all known concurrent changes and has a control strategy for each |
| WARNING | Plan acknowledges confounds exist but doesn't have a strategy to isolate them |
| FAIL | Plan doesn't mention confounds or assumes the hypothesized cause is the only thing that changed |

Questions to surface confounds:
- What else shipped/launched/changed in the same time period?
- Were there any data pipeline or tracking changes?
- Did marketing spend or campaign strategy shift?
- Were there external events (holidays, competitor moves, news)?
- Did the user population change (growth spike, new channel, geography expansion)?

**Fix if FAIL:** "List every change that happened in the same time window. For each, explain how you'll separate its effect."

### 6. Kill Criteria

**Check:** Does the plan define what would make you REJECT the hypothesis?

| Verdict | Criteria |
|---------|----------|
| PASS | Explicit thresholds for acceptance AND rejection, plus practical significance criteria |
| WARNING | Has acceptance criteria but no rejection criteria (can only "confirm," never "disprove") |
| FAIL | No criteria — "we'll see what the data shows" |

What good criteria look like:
- "If the effect is less than 2pp, it's not practically significant regardless of p-value"
- "If the drop is uniform across all segments, the widget hypothesis is rejected"
- "If the confound analysis shows the loyalty program explains >60% of the variance, the widget is not the primary cause"

**Fix if FAIL:** "Define the minimum effect size that matters AND what finding would disprove your hypothesis."

### 7. Output Alignment

**Check:** Will the analysis output actually answer the stakeholder's question? **AND can the analysis be executed with available data?**

| Verdict | Criteria |
|---------|----------|
| PASS | Output format matches stakeholder need AND all required data exists |
| WARNING | Output will be useful but may need translation for the audience, OR data exists but may have quality/completeness issues |
| FAIL | Output is descriptive ("here's what happened") when stakeholder needs prescriptive ("here's what to do"), OR **BLOCKER: required data does not exist** (e.g., plan requires "product category" but dataset has no category field) |

Common misalignment:
- Stakeholder wants a recommendation, plan produces a description
- Stakeholder wants dollar impact, plan produces percentages
- Stakeholder wants a yes/no, plan produces "it depends"
- Stakeholder wants a 1-page brief, plan will produce a 20-page report
- **BLOCKER: Plan requires data fields that don't exist in the dataset**

**Fix if FAIL (data blocker):** "HALT — this analysis cannot be executed. The dataset does not contain [required field]. Either locate the field in another table, request a data extension, or pivot to a different dimension that exists (e.g., analyze by customer segment instead of product category)."

**Fix if FAIL (alignment):** "Restate the stakeholder's actual question and work backwards to what the output must contain."

---

## Output Format

**Start with a 1-sentence executive summary at the top** (before the separator line) stating the grade and any blockers.

```
STRESS TEST RESULTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[1-sentence summary: e.g., "GRADE D (2 FAILs, 2 WARNINGs) — significant redesign needed before execution" or "GRADE F — BLOCKER: required data does not exist"]

OVERALL GRADE: [A/B/C/D/F]

| # | Check | Verdict | Issue |
|---|-------|---------|-------|
| 1 | Hypothesis Clarity | PASS/WARNING/FAIL | ... |
| 2 | Baseline Validity | PASS/WARNING/FAIL | ... |
| 3 | Survivorship Bias | PASS/WARNING/FAIL | ... |
| 4 | Segment Coverage | PASS/WARNING/FAIL | ... |
| 5 | Confound Identification | PASS/WARNING/FAIL | ... |
| 6 | Kill Criteria | PASS/WARNING/FAIL | ... |
| 7 | Output Alignment | PASS/WARNING/FAIL | ... |

CRITICAL ISSUES (must fix before executing):
  - ... [If data blocker: "BLOCKER: Cannot execute — required data does not exist. [Field name] not found in dataset."]

WARNINGS (address if time allows):
  - ...

RECOMMENDED FIXES:
  1. ... [Include estimated time impact for top 3 fixes: "~30 min", "~2 hours", etc.]
  2. ...
  3. ...
```

### Grading Scale

| Grade | Criteria |
|-------|---------|
| A | 0 FAILs, 0-1 WARNINGs — execute with confidence |
| B | 0 FAILs, 2-3 WARNINGs — execute but address warnings |
| C | 1 FAIL, any WARNINGs — fix the failure before executing |
| D | 2 FAILs — significant redesign needed |
| F | 3+ FAILs — start over with the Analysis Design Brief |

---

## Output File

Saves to: `working/stress_test_{{DATE}}.md`

---

## Examples

### Review a plan you wrote
```
/stress-test "I'm going to compare this month's conversion rate to last month's, broken by device, to see if the new checkout flow helped."
```

### Review a file
```
/stress-test working/investigation_plan_2026-03-28.md
```

### With context
```
/stress-test working/analysis_brief.md context="Board meeting Friday, need to decide whether to invest $500K in onboarding redesign" audience="CEO and CFO"
```

---

## Integration

- Works independently of `/analysis-design` — use it on ANY plan
- Can be chained: `/analysis-design` → `/stress-test` → fix → re-test
- Complements the **Analysis Design Spec skill** (which helps you write the plan) by reviewing it after it's written
- Pairs with **Confound Scanner agent** — the scanner finds threats proactively during planning; `/stress-test` reviews an existing plan retroactively
