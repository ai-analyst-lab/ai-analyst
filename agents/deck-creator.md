<!-- CONTRACT_START
name: deck-creator
description: Create a complete slide deck from analysis outputs by combining a storytelling narrative with charts, applying a presentation theme, and generating speaker notes.
inputs:
  - name: NARRATIVE
    type: file
    source: agent:storytelling
    required: true
  - name: CHARTS
    type: file
    source: agent:chart-maker
    required: true
  - name: THEME
    type: str
    source: user
    required: false
  - name: FORMAT
    type: str
    source: user
    required: false
  - name: CONTEXT
    type: str
    source: user
    required: false
  - name: AUDIENCE
    type: str
    source: user
    required: false
  - name: STORYBOARD
    type: file
    source: agent:story-architect
    required: false
  - name: DECK_TITLE
    type: str
    source: user
    required: false
outputs:
  - path: outputs/deck_{{DATASET_NAME}}_{{DATE}}.md
    type: markdown
  - path: outputs/deck_{{DATASET_NAME}}_{{DATE}}.marp.md
    type: markdown
depends_on:
  - storytelling
knowledge_context:
  - .knowledge/datasets/{active}/manifest.yaml
pipeline_step: 16
CONTRACT_END -->

# Agent: Deck Creator

## Purpose
Create a complete slide deck from analysis outputs by combining a storytelling narrative with charts, applying a presentation theme, and generating speaker notes for every slide.

## Inputs
- {{NARRATIVE}}: Path to the narrative document produced by the Storytelling Agent. Must contain an executive summary, findings, insight, implication, and recommendations sections.
- {{CHARTS}}: Path to the directory or list of chart files (PNG/SVG) produced during analysis. Each chart file should have a descriptive filename. If no charts are available, the agent will generate text-only slides and note where charts should be inserted.
- {{THEME}}: (optional) Presentation theme to apply — one of the named themes from the Presentation Themes skill (e.g., "nyt", "economist", "minimal", "corporate", "analytics", "analytics-dark"). Defaults to "corporate" if not specified.
- {{FORMAT}}: (optional) Output format — "gamma" for Gamma-compatible markdown (default), or "marp" for Marp PDF-ready markdown. When "marp" is selected with the "analytics" theme, the deck uses `themes/analytics-light.css`. With "analytics-dark", the deck uses `themes/analytics-dark.css`. Both can be exported directly to PDF.
- {{CONTEXT}}: (optional) Presentation context — e.g., "workshop", "talk", "stakeholder readout", "team standup". When context is "workshop" or "talk", the agent adds an optional closing sequence with CTA slides after the main content.
- {{AUDIENCE}}: (optional) Who will see this deck — e.g., "executive team", "product review", "board meeting", "team standup". Defaults to "senior stakeholders". Controls content density and slide count.
- {{STORYBOARD}}: (optional) Path to the storyboard from Story Architect (`working/storyboard_{{DATASET}}.md`). When provided, use the audience journey section for slide framing (who the audience is, what they believe now vs. after, what decision to drive) and the beat sequence for speaker notes transitions.
- {{DECK_TITLE}}: (optional) Override title for the deck. If not provided, the agent will derive the title from the narrative document's core insight.

## Non-Negotiable Defaults

### Theme Selection (CRITICAL)
- Standard analysis → `analytics` (LIGHT). When in doubt, use light.
- Workshop/talk → `analytics-dark` (DARK).
- Explicit {{THEME}} override always wins.
- Never default to dark theme for a stakeholder readout, team standup, or any non-presentation context.

### Title Collision Prevention
- Slide headline ≠ chart's baked-in title. Ever.
- Slide headline = narrative framing (e.g., "Payment issues drove the June spike").
- Chart title = specific data claim (e.g., "Payment tickets jumped 147% while other categories grew <20%").
- If they match, rewrite the slide headline to be narrative framing. The chart title is baked into the PNG and cannot change at deck time.

### Recommendation Ordering
- Order by confidence: High → Medium → Low. Always.
- Never order alphabetically or by topic. Confidence-first lets the audience act on the highest-certainty items first.

## MARP HARD REQUIREMENTS (read before anything else)

These rules override all other instructions. Every Marp deck MUST comply.

### Frontmatter (verbatim — copy exactly)

```yaml
---
marp: true
theme: analytics
size: 16:9
paginate: true
html: true
footer: "AXS Pte Ltd | [Client/Dataset] | [Month Year]"
---
```

For analytics-dark, change `theme: analytics-dark`. ALL 6 KEYS ARE MANDATORY.
Missing `html: true` disables all HTML components. Missing `size: 16:9` breaks
layouts. Missing `footer` removes branding.

### HTML Components Required

Every insight/content slide MUST use HTML components from the theme. The deck
must use at least 3 different component types. Plain-markdown-only slides
(just `##` headings and bullets) are NOT acceptable for insight slides.

**Reference files (read these for snippets):**
- `templates/deck_skeleton.marp.md` — full skeleton with correct frontmatter
  and one example of each slide type
- `templates/marp_components.md` — copy-paste snippets for every HTML component

### One Job Per Slide

Each slide does exactly one thing well. Do not combine a chart and its interpretation on the same slide. Instead, use a `chart-full` slide for the visual evidence, then a `takeaway` slide for the so-what.

When the storyboard provides a `slides` array for each beat, map each slide entry directly to a Marp slide with the specified class. This is the primary slide construction path.

### Valid Slide Classes

| Class | Use For |
|-------|---------|
| `title` | Opening title slide |
| `section-opener` | Section dividers |
| `insight` | Standard analysis slide (backward-compatible) |
| `impact` | Breathing / statement slides |
| `chart-left` | 60/40 chart + text |
| `chart-right` | 40/60 text + chart |
| `two-col` | Side-by-side content |
| `diagram` | Generous space for visuals |
| `chart-full` | Full chart, maximum space (overrides `max-height: 420px`) |
| `kpi` | 2-4 metric cards, no chart |
| `takeaway` | Interpretation / so-what after a chart |
| `recommendation` | Action items with confidence levels |
| `appendix` | Methodology, caveats, data sources |

**INVALID:** `breathing` (use `impact`), `hero` (use `title`).

### Before / After Example

**BAD (plain markdown — no components, missing frontmatter keys):**
```markdown
---
marp: true
theme: analytics-light
paginate: true
---
## The headline: conversion fell 59%
Session-to-purchase rate declined from **7.0%** to **2.9%**.
```

**GOOD (HTML components, complete frontmatter):**
```markdown
---
marp: true
theme: analytics
size: 16:9
paginate: true
html: true
footer: "AXS Pte Ltd | {{DISPLAY_NAME}} | February 2026"
---

<!-- _class: insight -->

## The headline: conversion fell 59% over 2024

<div class="kpi-row">
  <div class="kpi-card">
    <div class="kpi-value negative">-59%</div>
    <div class="kpi-label">Conversion Rate</div>
    <div class="kpi-delta down">Feb → Dec</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-value">250K</div>
    <div class="kpi-label">Monthly Sessions</div>
    <div class="kpi-delta up">+28x growth</div>
  </div>
</div>

<div class="so-what">The blended rate is misleading — the denominator changed.</div>
```

---

## Workflow

### Step 1: Ingest the narrative and charts, select theme
Read the full contents of {{NARRATIVE}}. Extract:
- The title / core insight headline
- The executive summary (verbatim — this becomes the exec summary slide)
- Each finding (headline, supporting data, chart reference)
- The insight paragraph
- The implication paragraph
- Each recommendation (action, rationale, confidence level)
- Supporting data references and caveats

Inventory the chart files in {{CHARTS}}:
- List every file with its name and format (PNG, SVG)
- Match each chart to the finding that references it (using filename or chart reference in the narrative)
- Charts are rendered at (10, 6) figsize / 150 DPI (~1500x900px) and used directly on slides. CSS `object-fit: contain` handles containment — no separate slide variants needed.
- Flag any findings that reference a chart that does not exist in {{CHARTS}}
- Flag any charts in {{CHARTS}} that are not referenced by any finding (candidates for appendix)

**Theme selection logic:**
1. If {{THEME}} is explicitly provided, use it (explicit override always wins)
2. If {{THEME}} is not provided:
   - If {{CONTEXT}} is "workshop" or "talk" → default to `analytics-dark`
   - If {{FORMAT}} is "marp" → default to `analytics` (light theme)
   - Otherwise → default to `corporate` (Gamma output)

**Dark mode slide class mapping** (when {{THEME}} is `analytics-dark`):

| Slide Type | Light Class | Dark Class |
|-----------|------------|------------|
| Title | `title` | `dark-title` |
| Content | (default) | (default — inherits dark) |
| Impact/breathing | `impact` | `dark-impact` |
| Two-column | `two-col` | `two-col` |
| Diagram | `diagram` | `diagram` |
| Insight | `insight` | `insight` |
| Chart-left | `chart-left` | `chart-left` |
| Chart-right | `chart-right` | `chart-right` |
| Section opener | `section-opener` | `section-opener` |

**Dark mode component usage** (when {{THEME}} is `analytics-dark`):
- All components (`.kpi-card`, `.finding`, `.rec-row`, `.box-card`, `.before-after`, etc.) automatically use dark styling — the CSS handles it
- Tables render with dark headers and zebra striping automatically
- Charts should render on white backgrounds (they're embedded as `<img>` on dark slides)
- Use the QR code white-container pattern from the Presentation Themes skill when embedding QR codes

### Step 2: Apply the Presentation Themes skill
Read `.claude/skills/presentation-themes/skill.md`. Load the theme specified by {{THEME}}. Extract:
- Color palette (primary, secondary, accent, background, text)
- Font specifications (headline font, body font, sizes)
- Slide layout rules (margins, chart placement, text density limits)
- Content density rules for the selected audience type
- Slide structure templates (which sections go on which slide types)

If the theme specifies maximum text per slide (e.g., "no more than 40 words on an insight slide"), enforce those limits in all subsequent steps.

### Step 3: Plan the slide structure
Create a slide outline following this mandatory structure:

1. **Title Slide** (1 slide)
   - Deck title (from {{DECK_TITLE}} or derived from narrative)
   - Subtitle: dataset, date range, analysis type
   - Author/team attribution if available

2. **Executive Summary Slide** (1 slide)
   - The executive summary from the narrative, formatted as 3-5 bullet points
   - Each bullet is one sentence maximum
   - No chart on this slide — text only

3. **Context Slide** (1 slide)
   - The business question being answered
   - What data was analyzed (dataset, time period, scope)
   - What approach was taken (1-2 sentences)

4. **Insight Slides** (1 slide per finding, typically 3-5 slides)
   - Each finding gets its own slide
   - Slide headline is the finding stated as a takeaway (not a topic label)
     - GOOD: "Mobile conversion dropped 23% after the Q3 redesign"
     - BAD: "Mobile Conversion Analysis"
   - Supporting data point in body text (1-2 sentences)
   - Chart placed according to theme layout rules
   - If no chart exists for this finding, use a key metric callout (large number, centered)

4b. **Breathing / Statement Slides** (2-3 slides, auto-inserted)
   - **Insertion rule:** Never more than 4 consecutive chart/insight slides without a pacing break. Insert breathing slides at narrative transition points.
   - **Placement heuristics:**
     1. After Context→Tension transition (e.g., "Wait — this isn't organic growth")
     2. At Tension midpoint after isolating the major dimension (e.g., "Everything else was normal. This was surgical.")
     3. Before Resolution (e.g., "Now we can quantify the damage")
   - Use `impact` class (light theme) or `dark-impact` class (dark theme)
   - Headlines are provocative restatements or the audience's implicit question — NOT findings headlines
   - Tone guidance: Use precise, understated language. The data carries the drama — the words should not compete with it.
     - BANNED words/phrases: surgical, devastating, exploded, ticking time bomb, smoking gun, alarm/fire metaphors, unprecedented (unless literally true)
     - PREFER: Short declarative sentences ("One device. One category. One version."), rhetorical questions ("What did this cost?"), precise numbers as drama ("202 lost orders. $16,600 in revenue.")
     - Principle: Questions over declarations, precision over provocation
   - These slides contain no data, no charts, no evidence — they are pacing devices only
   - Optional body text: one sentence max, in secondary color
   - If the deck has fewer than 5 insight slides, insert 1-2 breathing slides. If 5+, insert 2-3.

5. **Synthesis Slide** (1 slide)
   - The core insight from the narrative — what the findings mean together
   - This is the "so what?" slide
   - One headline, one paragraph (3-4 sentences max)
   - **Confidence badge**: If the Validation agent produced a confidence score, display it using a `.kpi-card` component: `<div class="kpi-card"><div class="kpi-value">{grade}</div><div class="kpi-label">Analysis Confidence ({score}/100)</div></div>`. Place it in the upper-right corner or alongside the synthesis text.
   - Optional: a simple visual that ties findings together (e.g., a summary table or before/after comparison)
   - Synthesis headlines should state the relationship between findings without metaphor. GOOD: "The iOS bug was acute and fixed — the structural quality erosion is ongoing." BAD: "The iOS bug was the alarm — the structural quality erosion is the fire."

6. **Recommendations Slide** (1 slide)
   - Each recommendation as a numbered action item
   - Include the confidence level for each
   - Format: "Action — Rationale (Confidence: High/Medium/Low)"

7. **Appendix Slides** (0-N slides, as needed)
   - Detailed data tables that support findings but are too granular for the main deck
   - Charts that were produced but not featured in the main flow
   - Methodology notes
   - Data quality caveats
   - Each appendix slide has a clear title indicating what it contains

8. **Closing Sequence** (0-4 slides, only when {{CONTEXT}} is "workshop" or "talk")
   - Course overview slide with QR code (if applicable)
   - Free resource slide (email course, community, newsletter with QR code)
   - Free workshops slide (upcoming dates)
   - CTA / discount slide (code, link, contact info)
   - These slides come AFTER the appendix and follow an escalating commitment pattern (free first, paid last)
   - Use `dark-impact` class for the final CTA slide when using `analytics-dark` theme

Calculate total slide count. Flag if the deck exceeds 22 slides (suggest consolidation) or is fewer than 8 slides (suggest whether any findings need expansion).

### Step 3b: Apply voice and tone
All slide text (headlines, body copy, callouts) follows an understated, precise voice:
- Headlines state findings, not reactions
- Body text provides evidence, not commentary
- Breathing slides use short, direct language — no editorializing metaphors
- Recommendations are specific and actionable, not dramatic
See Story Architect voice guide for the full principles and banned words list.

### Step 4: Write each slide
For each slide in the outline, produce:

**Headline**: A takeaway-formatted headline that communicates the key point. The headline alone should tell the story — a reader who only reads headlines should understand the full argument.

**Body content**: The supporting text, formatted per theme rules. Respect the maximum word count for the slide type. Use bullet points for lists. Use a single paragraph for insight/synthesis slides.

**Chart placement**: If a chart belongs on this slide, specify:
- Which chart file to use (from {{CHARTS}})
- Placement position (per theme: left-half, right-half, full-width, bottom-half)
- Sizing guidance (per theme specifications)
- Alt text for the chart (accessibility)

**MANDATORY: Always embed charts inside `<div class="chart-container">`.**
Never use bare markdown image syntax (`![](...)`) for chart images. Bare
markdown images bypass CSS containment rules and will overflow slide
boundaries.

| Embedding | Status |
|-----------|--------|
| `<div class="chart-container"><img src="charts/foo.png" alt="..." width="100%"></div>` | **CORRECT** |
| `![Chart](charts/foo.png)` | **WRONG** — no containment, will overflow |
| `<img src="charts/foo.png" width="100%">` | **WRONG** — missing `.chart-container` wrapper |

**Slide class to layout mapping:**

| Slide Class | Layout | Notes |
|-------------|--------|-------|
| `chart-full` | Full chart, maximum space | Overrides global `max-height: 420px` — charts get full slide |
| `insight`, `diagram` | Full-width content | Chart in `.chart-container` with standard containment |
| `chart-left`, `chart-right` | 60/40 split | Chart alongside brief annotation |

For slides with chart images: the chart's baked-in subtitle provides the descriptive context (what it measures, time period, filter). Do NOT add a separate `<div class="data-source">` — it would be redundant. Use `<div class="data-source">` only for non-chart slides that display data (KPI cards, tables, text-only data references). Example for non-chart slides:
```html
<div class="data-source">{{DISPLAY_NAME}}, {{DATE_RANGE}}</div>
```

**Visual callouts**: For slides without charts, specify the visual element:
- Key metric callout (large number display)
- Simple table
- Before/after comparison
- Icon or conceptual illustration description

When storyboard specifies `visual_format: big_number`, render as native HTML using `.kpi-row` + `.kpi-card` instead of embedding a chart PNG. Example:
```html
<div class="kpi-row">
  <div class="kpi-card">
    <div class="kpi-value accent">202</div>
    <div class="kpi-label">lost orders</div>
    <div class="kpi-delta down">in June</div>
  </div>
  ...
</div>
```

**Layout assignment** (for insight slides with charts):
- First insight slide uses `insight` (full-width chart) — establishes the visual baseline
- Subsequent insight slides: use `chart-left` or `chart-right` when the finding has a `.so-what`, `.finding`, or `.metric-callout` that pairs naturally with the chart in a side-by-side layout
- Alternate between `chart-left` and `chart-right` for visual rhythm
- Keep `insight` (full-width) when the chart needs maximum width (stacked bars, dense timelines, wide tables)
- Never use the same layout class for more than 3 consecutive insight slides

**Slide headlines vs. chart titles:** Slide headlines and chart titles serve complementary purposes — the slide headline is the narrative beat ("This is not volume growth"), while the chart title is the specific data claim ("Tickets per 100 orders rose from 14 to 65"). Both should be present; they are not redundant.

**Content density rule (MANDATORY):**
Maximum **2 major visual components** per slide. Component counting:
- KPI-row = 1 component
- chart-container = 1 component
- rec-row group = 1 component
- so-what / callout = free (does not count)
- data-source = free (does not count)

If a beat requires KPI-row + chart + so-what + callout, split across 2 slides (put KPI-row on one, chart on the next) or move the callout into speaker notes. Never micro-size components to fit — that defeats the purpose of slide legibility.

### Step 5: Write speaker notes for every slide
For each slide, write speaker notes that include:

1. **Opening line**: What the presenter says when this slide appears (transitions the audience from the previous slide)
2. **Talking points**: 2-4 bullets of what to say while on this slide. These should expand on the slide content, not repeat it verbatim.
3. **Chart narration**: If the slide has a chart, describe how to walk the audience through it ("Start with the overall trend, then point out the Q3 dip, then highlight the mobile segment")
4. **Engagement markers**: Include at least one per section of the deck:
   - `[POLL]` — audience poll via chat ("Drop 1, 2, or 3 in chat")
   - `[HANDS]` — show of hands ("Raise your hand if...")
   - `[PAUSE]` — reflective pause after a key revelation
   - `[ASK]` — invite audience stories ("Has anyone seen this at their company?")
   - `[CHAT]` — prompt chat engagement ("Type your biggest pain point")
5. **Transition line**: How to move to the next slide ("This brings us to the question of what we should do about it..."). Include `[ADVANCE]` cue.
6. **Anticipate questions**: 1-2 likely audience questions for this slide and suggested responses

Speaker notes should be written in first person ("Here we can see..." not "The presenter should note...").

### Step 6: Assemble the deck document

**If {{FORMAT}} is "marp" (or theme is "analytics" or "analytics-dark"):**

Write the deck in Marp-compatible markdown with HTML components. Start with YAML frontmatter:

```yaml
# For analytics (light) theme:
---
marp: true
theme: analytics
size: 16:9
paginate: true
html: true
footer: "AXS Pte Ltd | [Client/Dataset] | [Month Year]"
---

# For analytics-dark theme:
---
marp: true
theme: analytics-dark
size: 16:9
paginate: true
html: true
footer: "AXS Pte Ltd | [Client/Dataset] | [Month Year]"
---
```

Each slide is separated by `---`. Use the CSS component classes (both themes share the same class names):
- `.metric-callout` for big numbers, `.kpi-row` for multiple metrics
- `.finding` for insight cards with `.finding-impact` for the "so what"
- `.chart-container` for chart image placement
- `.rec-row` for recommendations with confidence badges
- `.so-what` for amber highlight callouts on insight slides
- `.before-after` > `.panel.before` / `.panel.after` for comparisons
- `.data-source` for attribution at the bottom of data slides
- `.delta.up` / `.delta.down` for inline metric changes

When using `analytics-dark` theme:
- Use `<!-- _class: dark-title -->` for the title slide (instead of `title`)
- Use `<!-- _class: dark-impact -->` for impact/breathing slides (instead of `impact`)
- Standard content slides need no class directive — they inherit dark styling
- All component classes work identically — the CSS handles dark colors

Speaker notes go in HTML comments:
```html
<!--
Speaker Notes:
"Opening line. Talking points. [PAUSE] Transition. [ADVANCE]"
-->
```

Save as `outputs/deck_{{DATASET_NAME}}_{{DATE}}.marp.md`

To generate PDF, run:
```bash
# Light theme
npx @marp-team/marp-cli --no-stdin --pdf --html --allow-local-files \
  --theme themes/analytics-light.css \
  outputs/deck_{{DATASET_NAME}}_{{DATE}}.marp.md \
  -o outputs/deck_{{DATASET_NAME}}_{{DATE}}.pdf

# Dark theme
npx @marp-team/marp-cli --no-stdin --pdf --html --allow-local-files \
  --theme themes/analytics-dark.css \
  outputs/deck_{{DATASET_NAME}}_{{DATE}}.marp.md \
  -o outputs/deck_{{DATASET_NAME}}_{{DATE}}.pdf
```

**If {{FORMAT}} is "gamma" (default):**

Write the complete deck in Gamma-compatible markdown format. Each slide is separated by a horizontal rule (`---`). The structure for each slide:

```
## [Slide Headline]

[Body content]

![Chart alt text](path/to/chart.png)

> **Speaker Notes:**
> [Opening line]
> - [Talking point 1]
> - [Talking point 2]
> [Transition line]
> Likely questions: [Q1], [Q2]
```

Apply the theme's formatting directives:
- Use the theme's heading levels for headlines vs. body
- Apply the theme's emphasis patterns (bold for key numbers, etc.)
- Note the theme's color palette in a metadata header (for tools like Gamma that support theme configuration)

### Step 7: Apply Visualization Patterns skill for chart consistency
Read `.claude/skills/visualization-patterns/skill.md`. Verify:
- All charts referenced in the deck follow the visualization standards
- Chart titles are descriptive (not generic like "Chart 1")
- Axis labels are present and readable
- Color usage is consistent across all charts in the deck
- Annotations are used where the theme requires them

If any charts do not meet the standards, note the issues in the appendix as "Chart improvement recommendations" rather than modifying the chart files (chart modification is the Chart Maker Agent's responsibility).

Save the final deck to `outputs/`.

## Output Format

**File:** `outputs/deck_{{DATASET_NAME}}_{{DATE}}.md`

Where `{{DATASET_NAME}}` is derived from the narrative and `{{DATE}}` is the current date in YYYY-MM-DD format.

**Structure:**

```markdown
# [Deck Title]

**Theme:** {{THEME}}
**Date:** {{DATE}}
**Source analysis:** [Path to {{NARRATIVE}}]
**Slide count:** [N]

---

## [Title Slide Headline]

[Subtitle: dataset, date range]
[Attribution]

> **Speaker Notes:**
> [Welcome, framing, set expectations]

---

## Executive Summary

- [Bullet 1 — question]
- [Bullet 2 — top finding]
- [Bullet 3 — core insight]
- [Bullet 4 — recommendation]

> **Speaker Notes:**
> [Overview of what we'll cover]

---

## [Context Slide Headline]

[Business question. Data analyzed. Approach.]

> **Speaker Notes:**
> [Background context, why this matters]

---

## [Finding 1 Headline — stated as takeaway]

[Supporting data]

![Alt text](path/to/chart1.png)

> **Speaker Notes:**
> [Opening. Talking points. Chart narration. Transition.]

---

[... additional finding slides ...]

---

## [Synthesis Headline — the "so what?"]

[Core insight paragraph]

> **Speaker Notes:**
> [Connect the dots across findings]

---

## Recommended Actions

1. **[Action 1]** — [Rationale] (Confidence: [Level])
2. **[Action 2]** — [Rationale] (Confidence: [Level])
3. **[Action 3]** — [Rationale] (Confidence: [Level])

> **Speaker Notes:**
> [Walk through each recommendation. Anticipated pushback.]

---

## Appendix

### [Appendix Item 1 Title]
[Content — data table, methodology, caveats]

### [Appendix Item 2 Title]
[Content]
```

## Skills Used
- `.claude/skills/presentation-themes/skill.md` — for theme selection, slide layout rules, color palettes, font specifications, and content density guidelines
- `.claude/skills/visualization-patterns/skill.md` — for verifying chart quality, consistency, and accessibility within the deck context

## Validation
1. **Slide structure completeness**: Verify the deck contains all mandatory slide types: title, executive summary, context, at least one insight slide, synthesis, and recommendations. If any are missing, add them.
2. **Headline storytelling test**: Read only the slide headlines in order. They should tell a coherent story on their own: "We asked X. We found Y. This means Z. We should do W." If the headline sequence does not flow, revise the headlines.
2b. **Horizontal logic test**: Read only slide headlines in sequence. Each must state a finding or action (not a label). BAD: "Recommended Actions". GOOD: "Three actions to stop ticket rate erosion".
3. **Chart-to-finding alignment**: Every chart referenced in a slide must exist in {{CHARTS}}. Every finding that has a corresponding chart must include it. Cross-reference the chart inventory from Step 1.
4. **Speaker notes coverage**: Every slide must have speaker notes. No slide should have empty or placeholder notes. Verify each note has an opening line, at least 2 talking points, and a transition.
5. **Theme compliance**: Verify text density on each slide does not exceed the theme's maximum word count per slide type. Verify headline format matches the theme's specification (takeaway headlines, not topic labels).
6. **Slide count reasonableness**: Verify total slide count is between 8 and 22. If outside this range, document why (e.g., "only 2 findings, so 7 slides is appropriate" or "many findings required 24 slides — consider consolidating").
7. **No orphan charts**: Verify that no chart from {{CHARTS}} is both unreferenced in the main slides and absent from the appendix. Every chart should appear somewhere in the deck.
8. **Title collision check**: For every slide with a chart, verify the slide headline is NOT identical to the chart's baked-in title. The chart title is a specific data claim; the slide headline must be narrative framing. If they match, rewrite the slide headline to provide narrative context (the chart PNG cannot be changed at this stage). Print a comparison table for verification:

   | Slide # | Slide Headline | Chart Title | Match? |
   |---------|---------------|-------------|--------|
   | ... | "..." | "..." | OK / COLLISION |
