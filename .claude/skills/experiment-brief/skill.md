---
name: experiment-brief
description: Auto-generate a structured experiment brief when a user expresses intent to test something. Use this skill whenever users mention testing, experiments, A/B tests, or want to validate a product change with data. Trigger on phrases like "I want to test...", "Let's experiment with...", "Should we A/B test...", "Can we test whether...", "I think X will improve Y", "We should validate...", "Let's try...", or any request involving running an experiment or measuring the impact of a change. This skill is your "think before you design" safety net — it forces clarity on hypothesis, metrics, guardrails, success criteria, and feasibility BEFORE any statistical design work begins. Apply this skill automatically when experiment intent is detected, even if the user hasn't explicitly asked for a brief. The skill ensures every experiment starts with a clear hypothesis (what change, what metric, what mechanism), exactly ONE north star metric (force a choice if multiple metrics are mentioned), guardrail metrics (what must not break), pre-registered success criteria (ship/kill/iterate thresholds decided before seeing results), and a feasibility estimate (traffic, baseline, MDE, duration). This brief becomes the input to the Experiment Designer agent. Never skip the brief and jump straight to power analysis — a well-designed experiment that tests the wrong thing is worse than no experiment at all.
---

# Skill: Experiment Brief

## Purpose
Auto-generate a structured experiment brief when a user expresses intent to test something. This is the "think before you design" safety net — ensuring every experiment starts with a clear hypothesis, north star metric, guardrail metrics, success criteria, and duration estimate before the Experiment Designer agent runs.

## When to Use
Apply this skill when:
1. **The user says "I want to test..."** or "Let's experiment with..." or "Should we A/B test..." or any variant expressing intent to run an experiment
2. **Before invoking the Experiment Designer agent** — the brief is a prerequisite input
3. **When an experiment request is vague** — the user wants to test something but hasn't specified metrics, duration, or success criteria

This skill auto-fires on experiment intent detection. Do NOT wait to be asked.

## Critical Requirements

**The brief must be COMPLETE and ACTIONABLE:**
- No "TBD" placeholders — all decisions are made in the brief
- No "Would you like me to..." deferral — do the work now
- No missing thresholds — every guardrail has a number
- No ambiguous success criteria — ship/kill/iterate conditions are specific
- Always includes a VIABLE/LONG/IMPRACTICAL feasibility flag

**If the user provides baseline values, VALIDATE them by querying the data first.** Correct misstatements with actual numbers before using them in the brief.

## Instructions

### What Is an Experiment Brief?

An **experiment brief** is a one-page document that captures the essential decisions BEFORE any statistical design work begins. It answers: What are we testing? Why? How will we know if it worked? What must we not break?

```
EXPERIMENT BRIEF
━━━━━━━━━━━━━━━━
WHAT:       What change are we testing?
WHY:        What business outcome do we expect?
HYPOTHESIS: We believe [change] will [impact metric] because [reason]
NORTH STAR: The ONE metric we're trying to move
GUARDRAILS: Metrics that must NOT degrade
SUCCESS:    What result would make us ship?
DURATION:   Rough estimate of how long we'd need to run
```

**The rule:** Never jump to power analysis or test design without a brief. A well-designed experiment that tests the wrong thing is worse than no experiment at all.

### Briefing Process

#### Step 0: Validate user-provided baselines (if any)

If the user provides ANY numeric claim about current performance — baseline metric values ("our conversion rate is 3%"), traffic volume ("we get 500 checkouts per day"), current rates ("abandonment is at 65%") — **query the data to validate it before proceeding**. Do not trust user claims without verification — they are often wrong or outdated.

- If the user's claim is correct, note it and continue
- If the user's claim is wrong, correct it in the brief and note the discrepancy: "Note: User mentioned 65% abandonment, but actual data shows 96% (4% conversion)"
- Use the validated baseline for all calculations

#### Step 0.5: Verify data availability for proposed metrics

Before designing the experiment, **verify the active dataset can actually measure the proposed metrics**. Check:
- Does the dataset contain the events/tables needed to calculate the north star metric?
- Are the guardrail metrics measurable with available data?
- If metrics are NOT measurable, HALT and explain: "The active dataset ([dataset name]) cannot measure [metric]. You would need [description of required data] to run this experiment."

**Example:** If the user wants to test a music app feature but the active dataset is e-commerce data, stop and explain the mismatch rather than proceeding with an invalid brief.

#### Step 1: Extract the hypothesis

If the user provides a vague intent ("I want to test regional playlists"), structure it into a proper hypothesis:

> "We believe that **[specific change]** will **[increase/decrease] [specific metric]** because **[mechanism/reason]**."

**Rules for a good hypothesis:**
- Must be falsifiable — the experiment must be able to disprove it
- Must specify a direction — "improve" is not enough; state whether you expect an increase or decrease
- Must include a mechanism — the "because" clause explains HOW the change affects user behavior, not just restates the metric
  - ❌ Bad: "because it will increase engagement"
  - ✅ Good: "because region-specific content is more relevant, triggering more clicks and return visits"
- Must be specific enough to measure — "improve user experience" is not measurable; "increase 7-day retention by reducing onboarding steps" is

If the user's intent is too vague to form a hypothesis, ask:
- "What specific behavior do you expect to change?"
- "Why do you think this change will have that effect?"
- "How would you know if it worked?"

#### Step 2: Define the north star metric

Select exactly ONE primary metric using the Metric Spec skill (`.claude/skills/metric-spec/skill.md`):

- The metric the hypothesis predicts will change
- Must be fully specified: numerator, denominator, time window
- Must be measurable with available data
- **Only one.** If the user mentions multiple metrics they want to improve (e.g., "conversion AND session length AND bounce rate AND AOV"), **refuse to proceed until they prioritize**. Respond with: "Which of these metrics is the primary decision criterion for shipping this feature? The others can be guardrails or secondary metrics, but we need exactly ONE north star for the ship/no-ship decision."

**Anti-pattern to avoid:** Listing "Primary Metric: X" plus "Secondary Metrics: Y, Z, W" without forcing prioritization. This creates metric proliferation and invites post-hoc rationalization. If AOV doesn't lift but items-per-order does, was it a win? Force the choice upfront. When the user lists multiple desired outcomes, push back immediately and make them choose.

#### Step 3: Define guardrail metrics

Apply the Guardrails Awareness skill (`.claude/skills/guardrails/skill.md`):

- At least one guardrail per experiment
- The guardrail must measure a different dimension of value than the north star
- Common pairs: engagement ↔ churn, conversion ↔ quality, speed ↔ accuracy
- **Define an acceptable threshold with a specific number:** "Churn must not increase by more than 0.5 percentage points"

**Anti-pattern to avoid:** Vague guardrails like "We need to ensure checkout doesn't slow down" or "Should not degrade customer satisfaction." These are aspirations, not testable conditions. Every guardrail needs a threshold.

**Good guardrail examples:**
- "Checkout Conversion Rate: must not decrease by >0.3 percentage points (baseline 4.0%, acceptable floor 3.7%)"
- "Page Load Time (p95): must not increase by >200ms (baseline 1.2s, acceptable ceiling 1.4s)"
- "Email Capture Rate: must achieve ≥70% opt-in (new metric, no baseline)"

#### Step 4: Define success criteria

Pre-register what "success" looks like BEFORE seeing results:

```
SUCCESS CRITERIA
━━━━━━━━━━━━━━━━
Ship if:     [north star improves by ≥X% AND guardrails are clean]
Kill if:     [north star shows no effect OR guardrails degrade significantly]
Iterate if:  [mixed results — e.g., works for some segments but not others]
```

This prevents post-hoc rationalization. The team decides what they'll do with each outcome before the data arrives.

**Anti-pattern to avoid:** Success criteria with "TBD" placeholders like "Minimum Detectable Effect: +5% increase in AOV (TBD based on current baseline)". If it's TBD, it's not pre-registered. Calculate it now.

#### Step 5: Estimate duration and feasibility

Provide a rough estimate (not a formal power analysis — that's the Experiment Designer's job):

- **Traffic:** How many users/day enter the affected flow?
- **Baseline:** What's the current value of the north star metric?
- **MDE:** What's the smallest change worth detecting? (Default: 5% relative for conversion, 10% for revenue)
- **Rough duration:** Based on traffic and MDE, is this a 1-week, 4-week, or 3-month experiment?
- **Feasibility flag (MANDATORY):** VIABLE (< 4 weeks), LONG (4-8 weeks), IMPRACTICAL (> 8 weeks — consider alternatives)

**Anti-pattern to avoid:** Estimating "2-4 weeks" without classifying as VIABLE/LONG/IMPRACTICAL. The flag tells stakeholders whether the test is worth running.

If feasibility is LONG or IMPRACTICAL, suggest alternatives:
- Increase MDE to shorten duration
- Segment test to high-traffic subset
- Multi-armed bandit instead of fixed-horizon A/B
- Fix obvious issues first (if diagnostic data suggests technical problems)

### Output Format

```markdown
# Experiment Brief: [Descriptive Name]

## Hypothesis
We believe that **[change]** will **[increase/decrease] [metric]** because **[reason]**.

## North Star Metric
| Metric | Definition | Current Baseline | Target Lift |
|--------|-----------|-----------------|-------------|
| [name] | [numerator / denominator, time window] | [current value] | [≥X% relative] |

## Guardrail Metrics
| Metric | Definition | Current Value | Acceptable Threshold |
|--------|-----------|---------------|---------------------|
| [name] | [definition] | [current] | [must not degrade by >X%] |

## Success Criteria
- **Ship if:** [conditions]
- **Kill if:** [conditions]
- **Iterate if:** [conditions]

## Feasibility Estimate
| Parameter | Estimate |
|-----------|---------|
| Daily traffic | [N users/day] |
| Baseline metric value | [X%] |
| Minimum detectable effect | [Y% relative] |
| Rough duration | [Z weeks] |
| Feasibility | [VIABLE / LONG / IMPRACTICAL] |

## Next Step
→ Pass this brief to the **Experiment Designer agent** for formal power analysis and test design.
```

## Handoff

After generating the brief, the next step is ALWAYS the Experiment Designer agent (`agents/experiment-designer.md`). Pass the hypothesis, metric definitions, and feasibility estimate as inputs.

## Anti-Patterns (What NOT to Do)

1. **Never skip the hypothesis** — "Let's just test it and see what happens" is not an experiment; it's hoping
2. **Never allow multiple north star metrics** — one primary metric. Everything else is secondary or a guardrail
3. **Never omit guardrails** — every optimization creates a trade-off. Name it upfront
4. **Never skip success criteria** — deciding what to do with results AFTER seeing them invites bias
5. **Never let "we'll figure it out" be a success criterion** — pre-register specific thresholds
6. **Never defer to "TBD" or "would you like me to..."** — the brief must be complete and actionable
7. **Never trust user-provided baselines without validation** — query the data first
8. **Never omit the feasibility flag** — VIABLE/LONG/IMPRACTICAL is mandatory

## Skills Used
- `.claude/skills/metric-spec/skill.md` — for fully specifying the north star metric
- `.claude/skills/guardrails/skill.md` — for selecting and defining guardrail metrics
