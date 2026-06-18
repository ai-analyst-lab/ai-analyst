---
name: deck-critique
description: Score any presentation slide-by-slide against the Data Story Checklist (SO-WHAT, STAKES, EVIDENCE, ASK) and return a diagnosis with per-slide scorecards, anti-pattern flags, an overall grade (A-F), and a prioritized prescription for fixes. Use this skill whenever the user asks to review, critique, diagnose, evaluate, or assess a deck or presentation. Trigger on phrases like "review my deck", "what's wrong with these slides", "critique this presentation", "score my slides", "evaluate this deck", "is my presentation any good", "deck feedback", "slide review", "presentation review", "check my slides", "deck diagnosis", or when the user provides a Marp .marp.md file path or Google Slides URL/ID for evaluation. Also auto-fire before running /deck-rescue since the critique is a prerequisite input for the full rescue pipeline. Apply this skill proactively whenever you see deck-related work — if someone mentions slides, presentations, or asks for feedback on their work, this is the right tool to help them improve it.
---

# Skill: Deck Critique

## Purpose
Score any presentation slide-by-slide against the **Data Story Checklist** (SO-WHAT, STAKES, EVIDENCE, ASK). Returns a diagnosis report with per-slide scorecards, anti-pattern flags, an overall grade, and a prioritized prescription for fixes.

## When to Use
Apply this skill when:
1. **The user asks to review, critique, or diagnose a deck** — "review my deck", "what's wrong with these slides", "critique this presentation"
2. **Before running `/deck-rescue`** — the critique is a prerequisite input for the full rescue pipeline
3. **The user provides a Marp `.marp.md` file or a Google Slides URL/ID** for evaluation

This skill can be invoked directly as `/deck-critique` or auto-fires when the presentation-doctor orchestrator agent runs.

## Inputs
- **`{{DECK_SOURCE}}`**: Path to a Marp `.marp.md` file OR a Google Slides presentation ID/URL
- **`{{AUDIENCE}}`** (optional): Who the presentation is for — informs STAKES scoring
- **`{{CONTEXT}}`** (optional): What decision or meeting this deck supports

## Instructions

### The Data Story Checklist Scoring System

Every slide is scored on 4 dimensions, each 0-3 points (max 12 per slide):

#### SO-WHAT (0-3): Does the title state a finding?
| Score | Criteria | Example |
|-------|----------|---------|
| 3 | **Action headline** — states a specific finding with data | "Incomplete onboarding drives 67% of enterprise churn" |
| 2 | **Descriptive headline** — describes what's shown but not what it means | "Churn by onboarding status" |
| 1 | **Label** — generic category name | "Churn Analysis" |
| 0 | **Missing or generic** — no title, or "Q3 Results" | "Q3 Update" |

#### STAKES (0-3): Does the audience know why this matters?
| Score | Criteria | Example |
|-------|----------|---------|
| 3 | **Explicit impact** — quantified business consequence | "$2.3M ARR at risk, growing 15% QoQ" |
| 2 | **Implied impact** — consequence is suggested but not quantified | "This is our fastest-growing churn segment" |
| 1 | **Generic** — vague importance claim | "This is important for the business" |
| 0 | **None** — no reason given for audience to care | (just data, no framing) |

#### EVIDENCE (0-3): Is the evidence focused?
| Score | Criteria | Example |
|-------|----------|---------|
| 3 | **Focused** — 2-3 key data points supporting the claim | Two charts: survival curve + revenue waterfall |
| 2 | **Moderate** — 4-6 data points, slightly broad | Table with 6 rows of relevant data |
| 1 | **Data dump** — 7+ points, multiple charts, unfocused | Wall of 12 bullets, 3 charts crammed together |
| 0 | **No evidence** — claims without supporting data | "We believe churn is a problem" |

#### ASK (0-3): Is there a clear action or decision?
| Score | Criteria | Example |
|-------|----------|---------|
| 3 | **Specific ask** — named action, owner, timeline | "Approve 2 engineers for 6 weeks to rebuild onboarding" |
| 2 | **Vague recommendation** — directional but not actionable | "We should invest in onboarding" |
| 1 | **Implied** — action is suggested indirectly | "Onboarding seems like a priority area" |
| 0 | **None** — no ask, no recommendation, no next step | "Questions?" |

### Diagnosis Process

**CRITICAL:** The 4-dimension scoring framework (SO-WHAT, STAKES, EVIDENCE, ASK) is MANDATORY for every slide. Do NOT substitute with pass/fail checkboxes, emoji ratings, or percentage scores. Users rely on the 0-3 scale to compare decks and track improvements over time.

#### Step 1: Parse the deck

**For Marp files (.marp.md):**
Read the file directly and manually parse slide structure. Slides are separated by `---` dividers. For each slide, extract:
- **Title**: First heading after `---` (usually `# Title`)
- **Body text**: All content after the title
- **Bullets**: Lines starting with `-` or `*`
- **Bullet count**: Number of bullet points
- **Has chart**: Look for `![...](...)` image syntax or references to chart files
- **Has table**: Look for markdown table syntax (`|---|---|`)
- **Word count**: Approximate content length
- **Slide class**: Check for `::: class-name` or `<!-- class: name -->` syntax

If `helpers/deck_parser.py` exists, you may use `parse_marp(path)` instead, but manual parsing is the fallback.

**For Google Slides:**
If `helpers/deck_parser.py` exists, use `parse_google_slides(presentation_id)` with the Google Workspace MCP to extract slide content. Otherwise, inform the user that Google Slides critique requires the deck parser helper.

**Handling missing images:**
If a deck references chart images that don't exist (e.g., `![chart](charts/funnel.png)` but the file is missing), treat the slide as having `has_chart: true` based on the reference. Note in the critique that the chart file is missing but score based on the intent (a chart was planned for this slide).

#### Step 2: Score each slide

For every slide, assign scores on all 4 dimensions using the 0-3 scale defined above. This is NON-NEGOTIABLE — even if the user's request seems informal, always apply the standardized framework.

**Always write detailed reasoning for each score** — not just the number. The reasoning must explain:
- WHY this score was assigned (which criteria from the rubric it meets/fails)
- WHAT would make it better (specific improvement with an example)
- HOW this connects to the overall deck story

Reasoning should be 2-4 sentences per dimension, not just a phrase. Compare these:

❌ BAD: "SO-WHAT | 1/3 | Label title"
✅ GOOD: "SO-WHAT | 1/3 | 'Background' is a generic section label, not a finding. The slide describes what YOU did ('We analyzed the funnel') instead of what the AUDIENCE should know. Better: 'Q4 conversion fell 2.1 points to 4.2% despite 18% traffic growth'"

Use this format for each slide:

```
### Slide N: "[exact title from deck]"

| Check | Score | Reasoning |
|-------|-------|-----------|
| SO-WHAT | X/3 | [Detailed explanation: Is this an action headline (3), descriptive (2), label (1), or missing (0)? What would make it better?] |
| STAKES | X/3 | [Detailed explanation: Is business impact quantified (3), implied (2), generic (1), or absent (0)? What's missing?] |
| EVIDENCE | X/3 | [Detailed explanation: Is evidence focused (3), moderate (2), data dump (1), or missing (0)? Count bullets/charts.] |
| ASK | X/3 | [Detailed explanation: Is ask specific (3), vague (2), implied (1), or absent (0)? What would be actionable?] |
| **Total** | **X/12** | |

**Anti-patterns:** [List any detected, or "None"]
```

**Important:** Title slides (slide 1) typically score 0-1 on EVIDENCE and ASK — this is expected. Comment on whether they preview the story effectively.

#### Step 3: Flag anti-patterns

Check each slide and the deck overall for these common anti-patterns.

**IMPORTANT:** After scoring all slides, you MUST create an anti-pattern summary table. This is not optional. The table format is:

| Anti-Pattern | Detection | Severity |
|-------------|-----------|----------|
| **Wall of bullets** | bullet_count > 6 on a single slide | High |
| **Chart-as-title** | Title is a chart type name ("Pie Chart", "Bar Graph") | High |
| **Orphan data** | Data presented with no interpretation or context | Medium |
| **No narrative arc** | Slides are unconnected; could be reordered without impact | High |
| **Missing transitions** | No logical flow from one slide to the next | Medium |
| **Data dump** | 3+ charts or tables on a single slide | High |
| **Label titles** | All slide titles are category labels, not findings | High |
| **Pie charts** | Any pie chart present (banned per SWD principles) | Medium |
| **No ask** | Final slide has no recommendation or decision request | High |
| **"Questions?" closer** | Deck ends with a "Questions?" slide instead of a clear ask | High |
| **Appendix bloat** | More than 3 appendix slides (suggests content wasn't curated) | Low |
| **Placeholder content** | Uses "Feature X", "Segment Y", or other generic placeholders | Medium |

**After identifying anti-patterns, create the summary table in this exact format:**

```markdown
## Anti-Pattern Summary

| Anti-Pattern | Slides Affected | Severity |
|-------------|----------------|----------|
| [pattern name] | [slide numbers] | [High/Medium/Low] |
```

This table is MANDATORY — it provides a scannable view of structural problems and helps prioritize fixes.

#### Step 4: Calculate overall grade

**Deck Score** = average of all slide scores (out of 12)

Calculate the average carefully: sum all slide totals, divide by number of slides, round to 1 decimal place.

| Grade | Avg Score | Diagnosis |
|-------|-----------|-----------|
| A | 10-12 | Excellent — clear story, focused evidence, specific ask |
| B | 8-9.9 | Good — minor improvements needed (tighten headlines or evidence) |
| C | 6-7.9 | Mediocre — story exists but is buried; needs restructuring |
| D | 4-5.9 | Poor — data dump with no clear story or ask |
| F | 0-3.9 | Failing — no story, no stakes, no ask; needs complete rewrite |

**Be brutally honest with grading.** Grade inflation undermines trust. Apply these rules:

- **All label titles ("Background", "Methodology") = D or F** — Not C, not B. Label titles mean there's no story.
- **Ends with "Questions?" instead of a specific ask = automatic F** — This is the worst anti-pattern.
- **No quantified stakes anywhere = max grade is C** — Data without impact is trivia.
- **8+ slides scoring below 6/12 = F** — Even if a few slides are good.

The purpose of an honest grade is to route the user to the right fix:
- F → /deck-rescue (complete rewrite)
- D → /deck-rescue (major restructuring)
- C → /slide-transform (fix worst slides)
- B → manual fixes (tactical polish)
- A → ready to present

If you give a D to a deck that deserves an F, the user won't get the full rewrite they need.

#### Step 5: Generate the prescription

Produce a prioritized list of fixes, ordered by impact. **The prescription MUST be organized into three tiers:**

### Critical
Fixes that would change the overall grade (e.g., F→C, D→B). These address fundamental story structure failures.

Examples:
- "Rewrite all titles as action headlines" (if all slides use label titles)
- "Add quantified stakes to every slide" (if deck has no business impact anywhere)
- "Replace 'Questions?' with specific ask" (if deck ends with worst anti-pattern)

### High-Impact
Fixes that improve audience comprehension without changing the grade. These address evidence clarity, comparison context, or narrative flow.

Examples:
- "Add comparison benchmarks to all metrics"
- "Build a narrative arc connecting slides"
- "Annotate charts to highlight key takeaways"

### Polish
Fixes that improve professionalism and visual design. These are nice-to-haves.

Examples:
- "Replace pie charts with horizontal bars"
- "Reduce bullet counts to max 4 per slide"
- "Remove appendix bloat"

**For each fix in each tier, provide:**
- **What to change** (specific, actionable)
- **Why it matters** (connect to scoring framework)
- **Example** (show a rewrite or provide a concrete suggestion)

**Make prescriptions actionable.** Instead of "Improve titles", say "Rewrite slide 2 title from 'Background' to 'Q4 conversion fell 3.2 points YoY despite traffic growth'".

### Output Format

Save the critique to `working/deck_critique_YYYYMMDD.md` (use current date). The file should follow this exact structure:

```markdown
# Deck Critique: [Deck Title or Filename]

**Date:** YYYY-MM-DD
**Source:** [file path or Slides ID]
**Audience:** [if provided, else "Not specified"]
**Context:** [if provided, else "Not specified"]

## Overall Grade: [A-F]

**Diagnosis:** [1-sentence summary — e.g., "This deck has data but no story. 6 of 8 slides fail the SO-WHAT check."]

**Deck Score:** [X.X/12 average]

## Per-Slide Scorecard

### Slide 1: "[title]"
| Check | Score | Reasoning |
|-------|-------|-----------|
| SO-WHAT | X/3 | [why] |
| STAKES | X/3 | [why] |
| EVIDENCE | X/3 | [why] |
| ASK | X/3 | [why] |
| **Total** | **X/12** | |

**Anti-patterns:** [list or "None"]

[Repeat for each slide]

## Anti-Pattern Summary

| Anti-Pattern | Slides Affected | Severity |
|-------------|----------------|----------|
| [pattern] | [slide numbers] | [High/Medium/Low] |

## Prescription (Prioritized Fixes)

### Critical
1. [fix description — what to change and why]

### High-Impact
1. [fix description]

### Polish
1. [fix description]

## Recommendation
- **Grade B-C:** Run `/slide-transform` on the [N] worst-scoring slides
- **Grade D-F:** Run `/deck-rescue` for a complete rewrite
```

## Handoff

After generating the critique:
- **Grade B-C:** Suggest `/slide-transform` on the lowest-scoring slides
- **Grade D-F:** Suggest `/deck-rescue` for a full rewrite
- The presentation-doctor orchestrator agent handles this routing automatically

## Anti-Patterns (for this skill)

1. **Never score without reasoning** — every score needs a "why"
2. **Never inflate grades** — a deck with label titles and no ask is not a B
3. **Never critique visual design here** — this skill evaluates story structure, not fonts or colors. The Visual Design Critic agent handles aesthetics.
4. **Never skip the prescription** — the critique is only useful if it comes with actionable fixes

## Skills Used
- `helpers/deck_parser.py` — for parsing deck formats into slide objects
- `.claude/skills/stakeholder-communication/skill.md` — for evaluating audience-appropriateness of stakes and asks
