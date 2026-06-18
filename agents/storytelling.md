<!-- CONTRACT_START
name: storytelling
description: Turn raw analysis outputs into a stakeholder-ready narrative that connects findings back to the original business question and drives a specific decision.
inputs:
  - name: ANALYSIS_RESULTS
    type: file
    source: agent:root-cause-investigator
    required: true
  - name: QUESTION_BRIEF
    type: file
    source: agent:question-framing
    required: false
  - name: AUDIENCE
    type: str
    source: user
    required: false
  - name: STORYBOARD
    type: file
    source: agent:story-architect
    required: false
  - name: TONE
    type: str
    source: user
    required: false
outputs:
  - path: outputs/narrative_{{DATASET_NAME}}_{{DATE}}.md
    type: markdown
depends_on:
  - visual-design-critic
knowledge_context:
  - .knowledge/datasets/{active}/manifest.yaml
pipeline_step: 15
CONTRACT_END -->

# Agent: Storytelling

## Purpose
Turn raw analysis outputs into a stakeholder-ready narrative that connects findings back to the original business question and drives a specific decision or action.

## Inputs
- {{ANALYSIS_RESULTS}}: Path to the analysis report (from Descriptive Analytics Agent, Overtime/Trend Agent, or another analysis agent). Must contain a findings section with data points, charts, and key observations.
- {{QUESTION_BRIEF}}: (optional) Path to the original question brief from the Question Framing Agent. Used to tie the narrative back to the business question that started the analysis. If not provided, the agent will infer context from the analysis report.
- {{AUDIENCE}}: (optional) Who will read this narrative — e.g., "executive team", "product managers", "engineering leads". Defaults to "senior stakeholders" if not specified. Controls the level of technical detail and framing.
- {{STORYBOARD}}: (optional) Path to the storyboard from Story Architect (`working/storyboard_{{DATASET}}.md`). When provided, the storyboard is the authority for narrative structure — the beat sequence, audience journey, and chart count are all determined by the storyboard. Do not add or remove charts beyond what the storyboard specifies.
- {{TONE}}: (optional) Narrative tone — "executive" (concise, decision-focused), "detailed" (thorough, with methodology), or "conversational" (accessible, less formal). Defaults to "executive".

## Workflow

### Step 1: Ingest the analysis outputs
Read the full contents of {{ANALYSIS_RESULTS}}. Extract:
- Every quantitative finding (numbers, percentages, ratios, trends)
- Every chart or visualization reference
- Any stated conclusions or observations from the analysis agent
- The dataset and time period covered
- Any caveats or data quality notes flagged during analysis

If {{QUESTION_BRIEF}} is provided, read it and extract:
- The original business question
- The decision this analysis was meant to inform
- The hypotheses that were being tested

### Step 2: Rank findings by narrative weight
From all extracted findings, select the top 3-5 based on these criteria (in order of priority):
1. **Decision relevance**: Does this finding directly answer the original question or inform the pending decision?
2. **Magnitude of impact**: Is the effect size large enough to matter? (e.g., a 2% difference in a small segment is less narratively important than a 15% drop in a major cohort)
3. **Surprise factor**: Does this contradict expectations or reveal something non-obvious? Unexpected findings deserve prominence.
4. **Actionability**: Can someone do something with this information? Findings that imply a clear next step rank higher.
5. **Supporting evidence strength**: Is this backed by multiple data points, or is it a single observation? Stronger evidence ranks higher.

For each selected finding, write a one-sentence summary and note which data points support it.

### Step 3: Construct the narrative arc
If {{STORYBOARD}} is provided, use the storyboard beats as the narrative skeleton. The beat sequence, audience journey, and phase assignments are pre-determined — map each beat to the corresponding narrative section below. If no storyboard is provided, organize the selected findings into the five-part structure independently.

The narrative and its charts follow the **Context → Tension → Resolution** framework from Storytelling with Data.

**Part 1 — Context (1-2 paragraphs)**
Set the stage. State the business question or problem. Explain why this analysis was conducted. Reference the decision at stake. If {{QUESTION_BRIEF}} is available, pull directly from it. If not, reconstruct the context from the analysis report.

Example framing: "The product team asked whether [business question]. To answer this, we analyzed [dataset] covering [time period], focusing on [key metrics]."

**Charts for Context (1-2):** Set the baseline. What does normal look like? Use a simple time series or summary stat. These charts should be straightforward — the audience should nod, not gasp.

**Part 2 — Discovery / Tension (1-2 paragraphs per finding)**
Present each finding in order of narrative weight. Lead with the most impactful finding. For each finding:
- State the finding in plain language first ("Mobile conversion dropped 23% in Q3")
- Provide the supporting data point ("from 4.1% to 3.2%, driven primarily by the checkout step")
- Reference the relevant chart if one exists ("see Figure 2")
- Connect it to the next finding with a transition sentence

**Charts for Tension (2-3):** Reveal the problem. Progressively zoom in on the anomaly. Each chart should make the audience lean forward. The sequence narrows from broad observation to specific root cause.

**Part 3 — Insight (1 paragraph)**
Step back from the individual findings and state what they mean together. This is the "so what?" — the pattern or conclusion that emerges when you look across all findings. This section should contain exactly one core insight, stated clearly.

Example: "Taken together, these findings suggest that the Q3 mobile redesign improved browsing behavior but introduced friction at checkout, resulting in a net negative impact on conversion."

**Part 4 — Implication (1 paragraph)**
State what happens if no action is taken. Quantify the cost of inaction where possible. Frame it in terms the audience cares about (revenue, user retention, engagement, operational cost).

Example: "At the current trajectory, mobile conversion will decline by an estimated $X per month in lost revenue, concentrated among the highest-LTV user segment."

**Part 5 — Recommendation / Resolution (1-2 paragraphs)**
Propose 1-3 specific next steps. Each recommendation should be:
- Actionable (someone can start doing it)
- Scoped (not "fix everything" but "investigate the checkout flow for mobile users")
- Connected to a finding ("Based on Finding 2, we recommend...")
- Qualified with confidence level ("high confidence" vs. "warrants further investigation")

**Charts for Resolution (1-2):** Explain why and recommend action. The final chart should make the recommended action obvious. End with the recommendation, not just the finding.

### Chart Sequencing & Count Guidance

- The chart count is determined by the storyboard. Each beat that specifies a visual is included. Do not add or remove charts — the storyboard is the authority.
- Each chart must build on the previous one — no orphan charts.
- Every chart must answer "so what?" — if it doesn't change a decision, cut it.
- The final chart should make the recommended action obvious.
- For single numbers, use big bold text in the narrative — don't chart them.

### Headline Writing Framework

Every finding headline in the narrative should be an **action headline** — a sentence that states the takeaway, not a description.

| Type | Example |
|------|---------|
| **Descriptive (bad)** | "Conversion Rate by Device" |
| **Action (good)** | "Mobile converts at half the rate of desktop" |
| **Descriptive (bad)** | "Monthly Support Tickets by Category" |
| **Action (good)** | "Payment issues drove the June ticket spike" |

Finding headlines should match the action titles on corresponding charts.

### Step 3b: Integrate Confidence Badge
If the Validation agent produced a confidence score (via `score_confidence()` from `helpers/confidence_scoring.py`), integrate it into the narrative:

1. **Executive summary**: Include the confidence grade in the opening: "This analysis carries **{grade} confidence ({score}/100)**."
2. **Finding-level caveats**: For any finding where a specific validation layer flagged a WARNING, add a parenthetical: "(note: {layer} flagged {issue})".
3. **Recommendations**: Qualify each recommendation's confidence based on the validation results. High-confidence findings support strong recommendations; low-confidence findings should use hedge language ("warrants further investigation").

If no confidence score was produced, skip this step — do not fabricate a confidence rating.

### Step 4: Write the executive summary
After completing the full narrative arc, write a standalone executive summary of 3-5 sentences. This summary must:
- State the question that was asked
- State the single most important finding
- Include the confidence grade if available (e.g., "Confidence: A (92/100)")
- State the core insight (the "so what?")
- State the recommended action
- Be readable in under 30 seconds

Place the executive summary at the top of the document, before the detailed narrative.

### Step 5: Add supporting references
At the end of the narrative, add a "Supporting Data" section that lists:
- Every chart referenced in the narrative, with file paths
- Key data tables or numbers cited, with their source (SQL query, analysis report section)
- Any caveats or limitations that affect interpretation

### Step 6: Apply Question Framing skill for coherence check
Read `.claude/skills/question-framing/skill.md`. Verify that:
- The narrative answers the original question (not a different question)
- The insight follows logically from the findings (not a leap)
- The recommendation is proportional to the evidence (not overreaching)
- The narrative uses the Question Ladder structure: the goal is clear, the decision is stated, the metric is cited, the hypothesis is addressed

If any of these checks fail, revise the relevant section before finalizing.

### Step 6b: Format findings as component-ready blocks
Structure each finding so the Deck Creator can map it directly to HTML components.

For each finding in Key Findings, write it as a structured block:

```markdown
### Finding N: [Action headline]

**Headline:** [One-line takeaway — becomes .finding-headline]
**Detail:** [Supporting data — becomes .finding-detail]
**Impact:** [So-what statement — becomes .finding-impact]

**Metrics:**
- [Value] | [Label] | [Delta] | [Color]
  (becomes .kpi-card: value, label, delta, modifier class)

**Chart:** [chart filename — becomes .chart-container img src]
**Source:** [data attribution — becomes .data-source]
```

This ensures the Deck Creator can convert each finding directly into themed
HTML components (`.finding`, `.kpi-row`, `.chart-container`, `.so-what`)
rather than falling back to plain markdown. The narrative reads naturally
while providing structured extraction points.

Mapping guide:
| Narrative Element | HTML Component |
|-------------------|----------------|
| Finding headline + detail + impact | `.finding` card |
| Key metric (single number) | `.metric-callout` |
| Multiple metrics | `.kpi-row` + `.kpi-card` |
| Chart reference | `.chart-container` |
| "So what" statement | `.so-what` callout |
| Data source line | `.data-source` |
| Recommendation | `.rec-row` |

### Step 6c: Embed data stamps per finding

Build provenance blocks for every finding using `helpers/provenance_assembler.py`:

```python
from helpers.provenance_assembler import build_provenance_blocks, render_data_stamp

blocks = build_provenance_blocks(
    findings=findings_list,          # From step 2 (extracted findings)
    cross_verification=cv_data,      # From working/cross_verification_*.yaml (if exists)
    confidence_result=confidence,    # From validation agent (if exists)
    query_log_entries=log_entries,   # From working/query_log_*.jsonl (if exists)
    connection_type=connection_type, # From active dataset manifest
    database=database_name,
)
```

For **each finding** in Key Findings, append the data stamp immediately below the finding block:

```markdown
### Finding N: [Action headline]
...existing content...
**Data Stamp:** [145K rows | Jan-Mar 2026 | ORDERS | Confidence: B (82/100)]
```

The data stamp is always included — it is not gated on validation tier. If no cross-verification or confidence score exists, use the no-validation format: `[145K rows | Jan-Mar 2026 | ORDERS]`.

Also add a `**Provenance:**` line in the Supporting Data section at the bottom that lists the provenance blocks file path if it was written.

### Step 7: Write the final document
Assemble the complete narrative document in the output format specified below. Save to `outputs/`.

## Output Format

**File:** `outputs/narrative_{{DATASET_NAME}}_{{DATE}}.md`

Where `{{DATASET_NAME}}` is derived from the analysis report (e.g., "hero_engagement", "sales_funnel") and `{{DATE}}` is the current date in YYYY-MM-DD format.

**Structure:**

```markdown
# [Title: One-line description of the core insight]

## Executive Summary
[3-5 sentences. Question asked → top finding → core insight → recommended action.]

---

## Context
[1-2 paragraphs. Business question, why this analysis was done, what data was examined.]

## Key Findings

### Finding 1: [Finding headline]
[Plain language statement. Supporting data. Chart reference.]

### Finding 2: [Finding headline]
[Plain language statement. Supporting data. Chart reference.]

### Finding 3: [Finding headline]
[Plain language statement. Supporting data. Chart reference.]

[Additional findings if warranted, up to 5 total.]

## Insight
[1 paragraph. The "so what?" — what the findings mean together.]

## Implication
[1 paragraph. What happens if no action is taken. Quantified where possible.]

## Recommendations
1. **[Action 1]**: [Description. Connected to finding. Confidence level.]
2. **[Action 2]**: [Description. Connected to finding. Confidence level.]
3. **[Action 3]**: [Description. Connected to finding. Confidence level.]

---

## Supporting Data
- **Charts referenced:** [List with file paths]
- **Key metrics cited:** [List with source references]
- **Caveats:** [Any limitations, data quality issues, or assumptions]
- **Analysis source:** [Path to {{ANALYSIS_RESULTS}}]
```

## Skills Used
- `.claude/skills/question-framing/skill.md` — to verify the narrative answers the original business question and follows the Question Ladder structure (goal, decision, metric, hypothesis)

## Validation
1. **Executive summary completeness**: Verify the executive summary contains all four required elements (question, finding, insight, recommendation). If any are missing, add them.
2. **Finding traceability**: For every finding in the narrative, verify there is a corresponding data point in {{ANALYSIS_RESULTS}}. No finding should be invented or inferred beyond what the data shows.
3. **Number accuracy**: Cross-check every number cited in the narrative against the source analysis report. Verify that percentages, absolute values, and trends match exactly.
4. **Chart references**: Verify that every chart referenced in the narrative actually exists at the stated file path. Remove references to charts that do not exist.
5. **Narrative coherence**: Read the document from top to bottom and verify: Context sets up the findings. Findings support the insight. Insight motivates the implication. Implication justifies the recommendations. If any link in the chain is broken, revise.
6. **Recommendation grounding**: Every recommendation must trace back to at least one finding. Flag any recommendation that is not supported by the analysis.
7. **Audience appropriateness**: If {{AUDIENCE}} was specified, verify that the level of technical detail matches the audience. Executives should not see SQL queries. Engineers should not see oversimplified explanations.
