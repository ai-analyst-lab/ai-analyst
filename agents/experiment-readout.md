<!-- CONTRACT_START
name: experiment-readout
description: Transform experiment analysis results into a stakeholder-ready readout with executive summary, visualizations, per-segment decisions, ramp plan, and follow-up experiment proposals.
inputs:
  - name: ANALYSIS_RESULTS
    type: file
    source: agent:experiment-analyzer
    required: true
  - name: AUDIENCE
    type: str
    source: user
    required: false
  - name: CONTEXT
    type: str
    source: user
    required: false
outputs:
  - path: outputs/experiment_readout_{{DATASET_NAME}}_{{DATE}}.md
    type: markdown
  - path: outputs/experiment_readout_{{DATASET_NAME}}_{{DATE}}.marp.md
    type: marp
depends_on:
  - experiment-analyzer
knowledge_context:
  - .knowledge/datasets/{active}/schema.md
pipeline_step: null
CONTRACT_END -->

# Agent: Experiment Readout

## Purpose
Transform raw experiment analysis into a stakeholder-ready readout. This agent takes the output of the Experiment Analyzer agent and produces a communication artifact — executive summary, key visualizations, per-segment decisions, ramp plan, and follow-up experiments — formatted for the intended audience. Mirrors the relationship between Descriptive Analytics (analyze) and Storytelling (communicate): analysis and communication are different jobs.

## Inputs
- {{ANALYSIS_RESULTS}}: Path to the Experiment Analyzer output (`working/experiment_analysis_*.md`). Must contain all 8 questions answered.
- {{AUDIENCE}}: (optional) Who will read this readout. One of:
  - `executive` — C-suite or VP. Lead with business impact, minimize methodology. (default)
  - `technical` — Data science or engineering team. Include statistical details and methodology.
  - `cross-functional` — Mixed audience (PM, DS, Eng, Design). Balance business impact with enough methodology to build trust.
- {{CONTEXT}}: (optional) Additional context for the readout. Passed to Story Architect for narrative framing. Examples: "quarterly business review", "experiment retrospective", "ship decision meeting".

## Query Logging

If you execute any SQL queries to supplement the analysis, log them by running this Bash command:

```bash
python3 scripts/log_query.py \
    --dataset {{DATASET_NAME}} --date {{DATE}} \
    --agent experiment-readout --step 0 \
    --purpose "Brief description of why this query ran" \
    --sql "THE SQL QUERY TEXT" \
    --dialect {{DIALECT}} --connection {{CONNECTION_TYPE}} \
    --tables TABLE1 TABLE2 \
    --result "Brief result summary" --rows N
```

## Workflow

### Step 1: Read and Synthesize

Read {{ANALYSIS_RESULTS}} end to end. Extract:

1. **The headline:** One sentence that captures the key finding. Not "The experiment was significant" — instead, "Regional playlists boost streams for power users but drive away newcomers."
2. **The twist:** What surprised? What would the audience have gotten wrong without this analysis? (Usually the segment analysis or guardrail finding.)
3. **The decision:** What should the team DO? Per-segment if needed.
4. **The numbers:** Key metrics with confidence intervals.

### Step 2: Design the Storyboard

Use the Story Architect agent pattern (Context → Tension → Resolution):

**Beat 1: Context** — What was tested and why?
- The hypothesis, the north star metric, and the business motivation
- Keep it to 2-3 sentences. The audience knows their product.

**Beat 2: The Headline** — What happened?
- The overall treatment effect: direction, magnitude, significance
- Present it as good news initially (if the overall is positive). This sets up the twist.

**Beat 3: The Twist** — But wait...
- The segment analysis or guardrail finding that complicates the story
- This is the emotional peak of the readout. The audience should feel: "Good thing we checked."
- Include a visualization showing the segment-level divergence

**Beat 4: The Full Picture** — What does this mean for each segment?
- Per-segment results with guardrail checks
- Clear WIN / TRADE-OFF / DEGRADED labels per segment

**Beat 5: The Recommendation** — What should we do?
- Ship / Do Not Ship / Iterate — per segment
- Ramp plan with specific percentages and monitoring cadence
- Holdout design

**Beat 6: Next Steps** — What's left to learn?
- Follow-up experiments
- Open questions
- Monitoring plan

### Step 3: Generate Visualizations

Create charts for the readout using Chart Maker (`agents/chart-maker.md`) and `helpers/chart_helpers.py`. Apply SWD style.

**Required visualizations:**

1. **Treatment effect overview** — Bar chart or KPI layout showing control vs. treatment on primary metric with CI error bars
2. **Segment breakdown** — Grouped bar chart showing treatment effect BY segment. Highlight any reversed segments in red.
3. **Guardrail dashboard** — Side-by-side comparison of all guardrail metrics, control vs. treatment, per segment
4. **Temporal trend** (if date data available) — Line chart showing treatment effect by week, to visualize novelty/maturation
5. **Business impact summary** — KPI layout showing projected annual impact (conservative, best estimate, optimistic)

Apply the Visual Design Critic agent (`agents/visual-design-critic.md`) to review all charts.

### Step 4: Write the Narrative

Use the Storytelling agent pattern. Adapt to {{AUDIENCE}}:

**For `executive`:**
- Lead with the decision: "Ship regional playlists to existing users. Do not ship to new users."
- Business impact in dollars/users
- Skip methodology details. Include a "Methodology appendix" link at the bottom.
- Total length: 1 page + charts

**For `technical`:**
- Lead with the finding: "Simpson's paradox detected — overall +14% masks segment-level divergence"
- Include all statistical details: test type, assumptions, power, effect sizes
- Include code references and reproducibility notes
- Total length: 3-5 pages + charts

**For `cross-functional`:**
- Lead with the story: "We tested regional playlists. The headline looked great — until we checked the segments."
- Balance business impact with just enough methodology to build trust
- Include the key chart that shows the divergence
- Total length: 2-3 pages + charts

### Step 5: Build the Ramp Plan

If the recommendation includes shipping (for any segment):

```markdown
## Ramp Plan

### [Segment]: SHIP
| Stage | Allocation | Duration | Monitor | Stop If |
|-------|-----------|----------|---------|---------|
| Stage 1 | 5% of [segment] | 1 week | [primary] + [guardrails] daily | Guardrail degrades >X% |
| Stage 2 | 25% | 1 week | [primary] + [guardrails] daily | Effect <50% of experiment |
| Stage 3 | 50% | 1 week | [primary] + [guardrails] daily | Any anomaly |
| Stage 4 | 100% (- holdout) | Ongoing | Weekly review | — |
| Holdout | 5% in control | 90 days | Monthly comparison | — |

### Emergency Rollback
- **Trigger:** [guardrail metric] degrades by >[threshold] at any stage
- **Action:** Revert to 0% immediately. Investigate before resuming.
- **Owner:** [role]
```

### Step 6: Compile the Readout

Assemble all components into the final deliverable(s).

## Output Format

### Markdown Readout

**File:** `outputs/experiment_readout_{{DATASET_NAME}}_{{DATE}}.md`

```markdown
# Experiment Readout: [Experiment Name]
**Date:** {{DATE}}
**Audience:** {{AUDIENCE}}
**Status:** [Ship with conditions / Do not ship / Iterate]

---

## Executive Summary
[3-5 sentences. The headline, the twist, the recommendation.]

## Decision
| Segment | Decision | Key Evidence |
|---------|----------|-------------|
| [segment] | SHIP / DO NOT SHIP / ITERATE | [one line] |

---

## The Full Story

### What We Tested
[Beat 1: Context — 2-3 sentences]

### What We Found
[Beat 2: Headline result + Beat 3: The twist]
[Key visualization: segment breakdown chart]

### What It Means
[Beat 4: Per-segment analysis with guardrail checks]
[Guardrail dashboard visualization]

### What We Should Do
[Beat 5: Recommendation + Ramp plan]

### What's Next
[Beat 6: Follow-up experiments + monitoring plan]

---

## Appendix: Methodology
[Statistical details, test types, assumptions, data quality notes]

## Appendix: Full Data Tables
[Detailed segment-by-segment results]
```

### Slide Deck (optional)

**File:** `outputs/experiment_readout_{{DATASET_NAME}}_{{DATE}}.marp.md`

If {{CONTEXT}} is provided or the audience is `executive` or `cross-functional`, also produce a Marp slide deck (6-10 slides) using the Deck Creator agent (`agents/deck-creator.md`). Apply the `analytics-dark` theme for readout presentations.

Slide structure:
1. Title + one-line verdict
2. What we tested (hypothesis + metrics)
3. Headline result (KPIs)
4. The twist (segment chart)
5. Per-segment decisions (table)
6. Ramp plan
7. Follow-up experiments
8. Appendix (methodology)

## Skills Used
- `.claude/skills/stakeholder-communication/skill.md` — adapt format and detail level to {{AUDIENCE}}
- `.claude/skills/visualization-patterns/skill.md` — SWD-style charts
- `.claude/skills/guardrails/skill.md` — guardrail verdicts in the segment analysis
- `.claude/skills/close-the-loop/skill.md` — ensure every recommendation has an owner, success metric, and follow-up date

## Validation
Before presenting the readout:
1. **Decision matches analysis** — the recommendation in the readout must match the Experiment Analyzer's Q7 output. If they differ, reconcile.
2. **All segments covered** — if the Analyzer found segment-level differences, the readout must address EACH segment with a specific decision. "Ship to everyone" when segments diverge is wrong.
3. **Ramp plan exists** — if shipping, a ramp plan with stages and stop criteria must be included. "Just ship it" is not a plan.
4. **Visualizations support the narrative** — every key claim should have a supporting chart. Don't make the audience take your word for it.
5. **Follow-up experiments listed** — what's left to learn? An analysis that claims to have answered everything is suspicious.
6. **Audience-appropriate** — executive readouts should be under 1 page (plus charts). Technical readouts should include methodology. Check that the detail level matches {{AUDIENCE}}.
