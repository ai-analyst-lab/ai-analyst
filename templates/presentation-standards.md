# Presentation Standards (reference)

Reference file; not separately triggerable. Loaded by the deck-creator agent
(and by deck-doctor's rescue skill in its own repo) for theme specs, layout rules,
palettes, fonts, and density guidelines.

# Skill: Presentation Themes

## Purpose
Generate slide decks that look professional, tell a coherent analytical story, and follow consistent theme standards matching the visualization patterns.

## When to Use
Apply this skill whenever creating a presentation, slide deck, or structured output intended for stakeholders. Always apply the active theme. Default theme: `corporate`.

## Instructions

### Slide Structure Templates

Every presentation follows this arc:

```
Title → Executive Summary → Context → Insight Slides → Synthesis → Recommendations → Appendix
```

#### Slide Types

**1. Title Slide**
```markdown
# [Takeaway headline — not "Q3 Analysis"]
## [Subtitle: scope, date range, audience]
### [Author / Team] | [Date]
```

**2. Executive Summary Slide**
```markdown
# [Key takeaway in one sentence]

- **Finding 1:** [One sentence with key number]
- **Finding 2:** [One sentence with key number]
- **Finding 3:** [One sentence with key number]

**Recommendation:** [One clear action]
```

**3. Context / Setup Slide**
```markdown
# [Why we looked at this]

- **Question:** [The business question that triggered this analysis]
- **Data:** [What data we used, time range, scope]
- **Method:** [How we analyzed it — one sentence]
```

**4. Insight Slide (one per finding)**
```markdown
# [Finding as a headline — "Mobile conversion dropped 18% in Q3"]

[ONE chart that proves this finding]

- [Supporting detail 1]
- [Supporting detail 2]

**So what:** [Why this matters for the business]
```

**5. Synthesis Slide**
```markdown
# [So what? — The combined story]

[How the findings connect to each other and what they mean together]

- **Pattern:** [What the findings reveal as a whole]
- **Root cause:** [If identified]
- **Magnitude:** [How big is this? Revenue impact, user impact]
```

**6. Recommendation Slide**
```markdown
# [Action to take — imperative verb]

| Action | Owner | Timeline | Expected Impact |
|--------|-------|----------|-----------------|
| [Action 1] | [Team] | [When] | [Quantified if possible] |
| [Action 2] | [Team] | [When] | [Quantified if possible] |

**Next step:** [The one thing to do Monday morning]
```

**7. Appendix Slide**
```markdown
# Appendix: [Topic]

[Supporting data, methodology details, caveats, additional charts]
[This is where you put things that support the story but would slow down the main narrative]
```

### Narrative Arc

Every deck follows: **Situation → Analysis → Finding → Implication → Recommendation**

| Arc Element | Slide Types | Purpose |
|---|---|---|
| **Situation** | Context slide | Why are we here? What question are we answering? |
| **Analysis** | (Implied — the work happened) | Don't show methodology unless asked |
| **Finding** | Insight slides (1 per finding) | What did we discover? One chart, one headline per finding. |
| **Implication** | Synthesis slide | So what? Why does this matter? |
| **Recommendation** | Recommendation slide | Now what? What should we do? |

### Content Density Rules

1. **Maximum 3 bullet points per slide** — if you need more, split into two slides
2. **One chart per slide** — never stack charts; each deserves its own headline
3. **Headlines are takeaways, not labels** — "Mobile conversion dropped 18%" not "Conversion by Device"
4. **No full sentences in bullets** — fragments with key numbers
5. **Slide count guidance**: 5-8 slides for a 10-minute readout, 10-15 for a 30-minute presentation
6. **The "headline test"**: read only the headlines in sequence — they should tell the complete story

### Theme Specifications

#### Theme: `corporate`
- Title font: Arial Bold, 28pt, #1B2A4A
- Body font: Arial, 16pt, #333333
- Accent color: #0066CC
- Background: white
- Chart style: `corporate` from Visualization Patterns skill
- Header bar: thin #0066CC line below headline

#### Theme: `minimal`
- Title font: Helvetica Bold, 24pt, #333333
- Body font: Helvetica, 14pt, #555555
- Accent color: #2563EB
- Background: white
- Chart style: `minimal` from Visualization Patterns skill
- No decorative elements

#### Theme: `nyt`
- Title font: Georgia Bold, 26pt, #000000
- Body font: Arial, 14pt, #333333
- Accent color: #D03A2B
- Background: white
- Chart style: `nyt` from Visualization Patterns skill
- Source attribution at bottom of each chart slide

#### Theme: `economist`
- Title font: Helvetica Bold, 24pt, #1F2E3C
- Body font: Helvetica, 14pt, #333333
- Accent color: #E3120B
- Background: #D7E4E8
- Chart style: `economist` from Visualization Patterns skill
- Red bar at top of each slide

#### Theme: `analytics`
- Title font: Inter/system sans-serif Bold, 36pt, #1F2937
- Body font: Inter/system sans-serif, 16pt, #4B5563
- Accent color: #D97706 (amber)
- Background: #F7F6F2 (warm off-white)
- Surface: #FFFFFF (white cards — charts integrate naturally)
- Chart style: charts on white backgrounds with clean borders
- Brand signature: 3px amber left border on every slide
- Positive metrics: #059669 (emerald), Negative metrics: #DC2626 (red)
- Marp CSS theme: `themes/analytics-light.css`
- Best for: Analytics presentations with charts, data tables, and KPI metrics. Designed for screen share and print.

**Analytics theme components:**
- `.metric-callout` — Single big number with label and context
- `.kpi-row` > `.kpi-card` — Multiple metrics side by side (value, label, delta)
- `.finding` — Insight card with headline, detail, and impact callout
- `.chart-container` — White card with border for chart images
- `.rec-row` — Recommendation with number, action, rationale, confidence badge
- `.callout` — Amber callout box for key takeaways
- `.so-what` — Amber highlight box for "so what" on insight slides
- `.delta` — Inline change indicator (`.up` green, `.down` red, `.flat` gray)
- `.badge` — Tags (`.positive`, `.negative`, `.accent`, `.neutral`)
- `.data-source` — Attribution line at bottom of slide

**Analytics layout variants:**

| Variant | Class Directive | Purpose |
|---------|----------------|---------|
| Insight (full-width) | `<!-- _class: insight -->` | Full-width chart under headline — default for first insight slide |
| Chart-left (60/40) | `<!-- _class: chart-left -->` | Chart on left, text/callout on right — good for chart + so-what pairs |
| Chart-right (40/60) | `<!-- _class: chart-right -->` | Text/callout on left, chart on right — alternates with chart-left |
| Impact | `<!-- _class: impact -->` | Centered statement slide — breathing/pacing between insight runs |

#### Theme: `analytics-dark`
- Background: #1A1A17 (warm dark)
- Surface: #222220
- Elevated: #2A2A27
- Text: #F5F5F0 (off-white)
- Text secondary: #A8A090 (muted amber)
- Text muted: #8A8580
- Accent: #D97706 (amber-orange)
- Accent light: #F0A060
- Brand signature: 3px amber left border on every slide
- Positive: #22C55E, Negative: #EF4444
- Marp CSS theme: `themes/analytics-dark.css`
- Best for: Workshop presentations, talks, screen-share heavy contexts, dark environments

**Analytics-dark slide variants:**

| Variant | Class Directive | Purpose |
|---------|----------------|---------|
| Default dark | (no class needed) | Standard content slides — warm dark bg, amber accents |
| Dark title | `<!-- _class: dark-title -->` | Opening/hero slides — larger type, centered layout |
| Dark impact | `<!-- _class: dark-impact -->` | Breathing/statement slides — centered, big numbers or single takeaway |
| Two-column | `<!-- _class: two-col -->` | Side-by-side layout (inherits dark styling automatically) |
| Diagram | `<!-- _class: diagram -->` | Extra padding for visual components |
| Insight | `<!-- _class: insight -->` | Compact padding for chart + so-what callout |
| Chart-left | `<!-- _class: chart-left -->` | 60/40 split — chart on left, text/callout on right |
| Chart-right | `<!-- _class: chart-right -->` | 40/60 split — text/callout on left, chart on right |

All components (`.kpi-card`, `.finding`, `.rec-row`, `.box-card`, `.before-after`, etc.) render correctly on every slide variant without additional class overrides — the CSS handles dark styling at the theme level.

**CSS scoping warning:** When extending `analytics-dark.css` with new component styles, ensure overrides cover all three dark-specific variants if they have unique backgrounds:
```css
section.dark-title .component,
section.dark-impact .component { ... }
```
This prevents light-mode colors from leaking through on title and impact slides (which have distinct background gradients). The base `section` selector covers standard dark slides.

### Automatic Theme Selection

When no `{{THEME}}` is explicitly passed, Deck Creator auto-selects the theme based on context:

| Condition | Default Theme | Rationale |
|-----------|--------------|-----------|
| `{{THEME}}` explicitly provided | Use as-is | Explicit override always wins |
| `{{CONTEXT}}` is "workshop" or "talk" | `analytics-dark` | Dark themes project better in live settings |
| `{{FORMAT}}` is "marp" (no context) | `analytics` (light) | Analyst deliverables default to light for readability |
| Otherwise | `corporate` | Gamma output default |

Pass `{{THEME}}` to override auto-selection for any context.

### Font Size Minimums for Presentations

These minimums ensure readability during screen-share and projection:

| Element | Minimum Size | Recommended |
|---------|-------------|-------------|
| h1 (title slides) | 48px | 52px |
| h1 (content slides) | 44px | 44px |
| h2 | 36px | 36px |
| h3 | 28px | 28px |
| Body / paragraphs | 24px | 24px |
| List items | 22px | 22px |
| Minimum readable | 16px | — |
| Footer / page numbers | 12-14px | 14px |

Nothing except footers and page numbers should be below 16px. If text must be smaller, it belongs in the appendix or speaker notes.

### QR Code Integration Pattern

When embedding QR codes on dark slides, wrap in a white container to ensure scannability:

```html
<div style="background:#fff; border-radius:10px; padding:6px; display:inline-block;">
  <img src="qr-code.png" style="width:140px; height:140px; display:block;">
</div>
<div style="font-size:14px; color:#8A8580; margin-top:6px;">Scan for [description]</div>
```

Sizing: 120-160px for supporting QR codes, 180-220px for primary CTA QR codes.

### Workshop Closing Sequence Template

Optional slide sequence for workshop/talk decks. Add after the recommendation or appendix slides:

1. **Course overview slide** — Brief description of full course offering with QR code link
2. **Free resource slide** — Email course, community, newsletter with QR code
3. **Free workshops slide** — Upcoming dates and topics
4. **CTA / discount slide** — Discount code, enrollment link, contact info

This sequence follows an **escalating commitment pattern**: free resources first (low barrier), then paid offering (higher commitment). Never lead with the paid CTA.

### Speaker Notes Engagement Tactics

Enhance speaker notes beyond standard talking points with these engagement markers:

- **Audience polls**: `[POLL] "Drop in chat: 1, 2, or 3 — which scenario is closest to your team?"`
- **Show of hands**: `[HANDS] "Raise your hand if you've ever waited 2+ weeks for an analysis"`
- **Reflective pause**: `[PAUSE — let this sink in]`
- **Story sharing**: `[ASK] "Has anyone seen something like this at their company?"`
- **Transition cues**: `[ADVANCE]` or `[NEXT SLIDE]`
- **Chat engagement**: `[CHAT] "Type your biggest analytics pain point in the chat"`

Place engagement markers at natural breaks — after revealing a key number, before transitioning to recommendations, or when introducing a framework.

### Export Formats

**Marp PDF (recommended for `analytics` theme):**

Marp converts markdown directly to PDF via Chromium. Use when you need a self-contained PDF deck.

```markdown
---
marp: true
theme: analytics
size: 16:9
paginate: true
html: true
footer: "[Organization] | [Author] | [Date]"
---

## Slide Headline

Content here

<!--
Speaker Notes:
"Notes go in HTML comments."
-->

---

## Next Slide Headline

Content here
```

Generate PDF with:
```bash
# Light theme (analytics)
npx @marp-team/marp-cli --no-stdin --pdf --html --allow-local-files \
  --theme themes/analytics-light.css \
  outputs/deck_name.marp.md \
  -o outputs/deck_name.pdf

# Dark theme (analytics-dark)
npx @marp-team/marp-cli --no-stdin --pdf --html --allow-local-files \
  --theme themes/analytics-dark.css \
  outputs/deck_name.marp.md \
  -o outputs/deck_name.pdf
```

**Gamma-compatible Markdown:**
```markdown
---
theme: [theme_name]
---

# Slide Title

Content here

---

# Next Slide Title

Content here
```

**Structured JSON (for programmatic use):**
```json
{
  "title": "Deck Title",
  "theme": "corporate",
  "slides": [
    {
      "type": "title",
      "headline": "...",
      "subtitle": "...",
      "speaker_notes": "..."
    }
  ]
}
```

**Speaker Notes Format:**
Every slide includes speaker notes with:
- Opening line (what to say when this slide appears)
- 2-3 talking points
- Transition to next slide
- Anticipated questions

## Examples

### Example 1: Correct insight slide
```markdown
# Mobile conversion dropped 18% in Q3, erasing gains from the app redesign

[Bar chart: Conversion rate by device, Q2 vs Q3, mobile highlighted in red]

- Desktop conversion stable at 4.2% (±0.1%)
- Mobile fell from 3.8% to 3.1% between July and September
- Drop correlates with iOS 18 update rollout (Aug 12)

**So what:** The app redesign ROI is negative until we fix the iOS 18 compatibility issue. ~$340K/month in lost mobile conversions.
```

### Example 2: Correct executive summary
```markdown
# Q3 conversion dropped 12% — mobile is the culprit, and it's fixable

- **Mobile conversion fell 18%** after the iOS 18 update broke checkout flow on iPhones
- **Desktop held steady** at 4.2%, confirming the issue is mobile-specific
- **Fix is scoped** — engineering estimates 2 weeks to patch, recovering ~$340K/month

**Recommendation:** Prioritize the iOS 18 checkout fix over the planned Q4 feature work.
```

## Anti-Patterns

1. **Never put more than one chart on a slide** — each finding deserves its own space
2. **Never use label headlines** ("Revenue by Quarter") — use takeaway headlines ("Revenue grew 23%")
3. **Never exceed 3 bullet points** — if you need more, you need another slide
4. **Never show methodology in the main deck** — put it in the appendix
5. **Never skip the "so what"** — every insight slide must answer "why does this matter?"
6. **Never create a deck without a recommendation slide** — analysis without action is wasted
7. **Never use full sentences as bullets** — use fragments with key numbers
8. **Never present findings in the order you discovered them** — present in the order that tells the best story
