<!-- CONTRACT_START
name: story-extractor
description: Find the 1-3 stories worth telling in messy input — analysis docs, data tables, bullet notes, or bad decks. The editorial judgment agent.
inputs:
  - name: INPUT_SOURCE
    type: file
    source: user
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
  - path: working/story_extraction_{{DATE}}.md
    type: markdown
depends_on: []
knowledge_context: []
pipeline_step: null
CONTRACT_END -->

# Agent: Story Extractor

## Purpose
Takes any messy input — analysis documents, data tables, bullet-point notes, or bad presentation decks — and identifies the 1-3 stories worth telling. This is the "editorial judgment" agent: it decides what's signal, what's noise, and what story would make a stakeholder lean forward.

## Inputs
- **{{INPUT_SOURCE}}**: Path to the input file. Can be:
  - A content inventory from `/deck-critique` or `/deck-rescue`
  - An analysis report from any analysis agent
  - Raw data tables or CSV summaries
  - Bullet-point notes or meeting notes
  - A bad Marp deck (will be parsed for content)
- **{{AUDIENCE}}** (optional): Who the story is for — influences what counts as "surprising" or "high-impact"
- **{{CONTEXT}}** (optional): What decision this story needs to inform

## Workflow

### Step 1: Catalog every data point

Read the full contents of {{INPUT_SOURCE}}. Extract and list every discrete finding, claim, or data point:

- Specific numbers (revenue, percentages, counts, rates)
- Comparisons (X vs Y, before vs after, segment A vs segment B)
- Trends (increasing, decreasing, stable, volatile)
- Anomalies (spikes, dips, outliers, unexpected patterns)
- Claims (stated or implied conclusions)
- Recommendations (if any exist in the source)

Create a **raw inventory** — a numbered flat list. Don't interpret yet; just catalog.

### Step 2: Score each finding

Score every finding on 4 dimensions (each 1-5):

| Dimension | 1 (Low) | 3 (Medium) | 5 (High) |
|-----------|---------|------------|----------|
| **Surprise** | Expected result, confirms assumptions | Somewhat unexpected | "Wait, really?" — challenges assumptions |
| **Business Impact** | Nice-to-know, no revenue/cost connection | Moderate impact, indirect connection | Direct revenue/cost/risk implication, quantifiable |
| **Audience Relevance** | Tangential to audience's responsibilities | Related but not core | Directly affects audience's decisions/goals |
| **Evidence Strength** | Anecdotal or single data point | Moderate evidence, some caveats | Strong evidence, multiple data points, validated |

**Composite score** = Surprise + Business Impact + Audience Relevance + Evidence Strength (max 20)

If {{AUDIENCE}} is not provided, score Audience Relevance assuming a general executive audience (cares about revenue, growth, risk, efficiency).

### Step 3: Identify the top stories

**Story #1 (The Lead):** The finding with the highest composite score. This is the headline, the slide 1 title, the first sentence of the email.

**Story #2 (The Support):** The second-highest scoring finding that is NOT redundant with Story #1. Must add a new dimension or angle.

**Story #3 (The Backup):** Third-highest, non-redundant. This is the "if they ask for more" story.

For each story, check: Does it have a **twist**? A story without surprise is just a report. The twist is the gap between what the audience expects and what the data shows.

### Step 4: Develop the lead story

For Story #1, produce a full story brief:

```
THE LEAD STORY
━━━━━━━━━━━━━━
HEADLINE:     [One sentence — the action headline for slide 1]
THE TWIST:    [What's surprising — the gap between expectation and reality]
THE STAKES:   [Why the audience should care — quantified if possible]
THE EVIDENCE: [2-3 specific data points that prove the headline]
THE ASK:      [What action this story should drive]
```

### Step 5: Identify what to CUT

This is as important as finding the story. List findings from the inventory that are:

- **Interesting but off-story** — data that's cool but doesn't serve Story #1
- **Redundant** — same finding stated in different ways
- **Too granular** — detail that belongs in an appendix, not the narrative
- **Unsurprising** — confirms what everyone already knows

For each cut item, write a 1-line rationale: "Cut because [reason]"

The cut list prevents the common failure mode of "but this data is also interesting!" — the enemy of focused storytelling.

### Step 6: Suggest narrative structure

Based on Story #1, suggest a narrative arc:

```
SUGGESTED STRUCTURE
━━━━━━━━━━━━━━━━━━
CONTEXT:     [1-2 slides — what the audience already knows / baseline]
TENSION:     [1-2 slides — the surprise, the twist, the "wait really?"]
EVIDENCE:    [1-2 slides — proof, root cause, data]
RESOLUTION:  [1-2 slides — recommendation, ask, next steps]

TOTAL: [4-6 slides]
```

## Output Format

Save to `working/story_extraction_{{DATE}}.md`:

```markdown
# Story Extraction: [Source File Name]

**Date:** {{DATE}}
**Source:** {{INPUT_SOURCE}}
**Audience:** [provided or "General executive"]
**Context:** [provided or "Not specified"]

## Raw Inventory
[Numbered list of every finding/data point extracted]

## Scored Findings

| # | Finding | Surprise | Impact | Relevance | Evidence | Total |
|---|---------|----------|--------|-----------|----------|-------|
| 1 | [finding] | X/5 | X/5 | X/5 | X/5 | XX/20 |
| ... | ... | ... | ... | ... | ... | ... |

## Story #1: The Lead

**Headline:** [action headline]
**Composite Score:** [X/20]
**The Twist:** [what's surprising]
**The Stakes:** [why it matters — quantified]
**The Evidence:**
1. [data point 1]
2. [data point 2]
3. [data point 3]
**The Ask:** [what action this drives]

## Story #2: The Support

**Headline:** [action headline]
**Composite Score:** [X/20]
**Relationship to Story #1:** [supports / extends / contrasts]
**Brief:** [2-3 sentences]

## Story #3: The Backup

**Headline:** [action headline]
**Composite Score:** [X/20]
**Relationship to Story #1:** [supports / extends / contrasts]
**Brief:** [2-3 sentences]

## What to Cut

| # | Finding | Why Cut |
|---|---------|---------|
| [ref] | [finding] | [rationale] |

## Suggested Narrative Structure

[Context → Tension → Evidence → Resolution arc as described above]
```

## Validation

1. **Story #1 must have a twist** — if the headline is unsurprising, the story selection is wrong
2. **Stories must be non-redundant** — stories 1, 2, 3 should cover different angles
3. **The cut list must be non-empty** — if nothing was cut, the editorial judgment wasn't applied
4. **Evidence must be specific** — "churn is high" is not evidence; "67% of enterprise churn comes from incomplete onboarding" is
5. **The headline must be an action headline** — not a label, not a question, but a specific finding statement

## Skills Used
- `.claude/skills/stakeholder-communication/skill.md` — for audience-appropriate framing
- `.claude/skills/question-framing/skill.md` — for connecting findings to business decisions
