# Marp HTML Component Snippets

Copy-paste reference for all HTML components defined in the `analytics` and
`analytics-dark` themes. Components work identically in both themes — CSS
handles color adaptation.

> **Rule:** Every insight slide MUST use at least one HTML component.
> Plain-markdown-only slides look generic and miss the branded styling.

---

## One Job Per Slide

Each slide should do exactly ONE thing well. Do not combine a chart and its
interpretation on the same slide. Instead, use a `chart-full` slide for the
visual evidence, then a `takeaway` slide for the so-what.

**Why:** Dense slides split the audience's attention. Separating chart from
takeaway forces the presenter to state the interpretation explicitly rather
than hoping the audience reads both at once.

**Pattern:** `chart-full` → `takeaway` → `chart-full` → `takeaway`

---

## Frontmatter (required)

```yaml
---
marp: true
theme: analytics          # or analytics-dark
size: 16:9
paginate: true
html: true
footer: "AXS Pte Ltd | Client Name | Month Year"
---
```

**All 6 keys are mandatory.** Missing `html: true` disables every component
below. Missing `size: 16:9` produces 4:3 slides with broken layouts.

---

## Slide Classes

Use `<!-- _class: NAME -->` on the line after `---`.

| Class | Use For | One Job |
|-------|---------|---------|
| `title` | Opening title slide | Set context |
| `section-opener` | Section dividers (h2 in accent color) | Signal topic change |
| `insight` | Standard analysis slide (headline + content) | Present one finding with components |
| `impact` | Breathing / statement slides (centered, large text) | Pause and emphasize |
| `two-col` | Side-by-side content | Compare two things |
| `chart-left` | 60/40 chart-left, text-right | Chart with brief annotation |
| `chart-right` | 40/60 text-left, chart-right | Chart with brief annotation |
| `diagram` | Generous space for visuals | Show a diagram or architecture |
| `chart-full` | One chart, maximum space (overrides `max-height: 420px`) | Show the evidence |
| `kpi` | 2-4 metric cards, no chart needed | Headline metrics at a glance |
| `takeaway` | Interpretation / so-what after a chart | State what it means |
| `recommendation` | Action items with confidence levels | Tell them what to do |
| `appendix` | Methodology, caveats, data sources (muted styling) | Reference material |

**Invalid classes:** `breathing` (use `impact`), `dark-title` (light theme
only — use `title`).

For `analytics-dark` theme, use `dark-title` and `dark-impact` instead of
`title` and `impact`.

### Migration Table (old → new)

If you have decks using the old `insight` class for everything, migrate:

| Old Pattern | New Pattern | Why |
|-------------|-------------|-----|
| `insight` with chart + so-what on same slide | `chart-full` + `takeaway` (two slides) | One job per slide — separate evidence from interpretation |
| `insight` with KPI row only (no chart) | `kpi` | Dedicated layout optimized for metric cards |
| `insight` with rec-rows | `recommendation` | Dedicated layout for action items |
| Last slide with methodology text | `appendix` | Muted styling signals reference material |
| `insight` with standalone finding/so-what | `takeaway` | Centered layout for interpretation |

---

## Accent Bar (title slides)

```html
<div class="accent-bar"></div>
```

60px amber bar. Place after title text on `_class: title` slides.

---

## Metric Callout (single big number)

```html
<div class="metric-callout">
  <div class="metric-value negative">-59%</div>
  <div class="metric-label">Conversion Rate Change</div>
  <div class="metric-context">Feb → Dec 2024</div>
</div>
```

Value modifiers: `.positive` (green), `.negative` (red), `.accent` (amber).

---

## KPI Row (multiple metrics)

```html
<div class="kpi-row">
  <div class="kpi-card">
    <div class="kpi-value negative">-59%</div>
    <div class="kpi-label">Conversion</div>
    <div class="kpi-delta down">vs prior period</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-value">250K</div>
    <div class="kpi-label">Sessions</div>
    <div class="kpi-delta up">+28x YoY</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-value accent">81%</div>
    <div class="kpi-label">Returning Users</div>
    <div class="kpi-delta flat">of mix</div>
  </div>
</div>
```

Value modifiers: `.positive`, `.negative`, `.accent`.
Delta modifiers: `.up` (green), `.down` (red), `.flat` (gray).
Use 2-4 cards per row. Best on `_class: kpi` slides.

---

## So-What Callout

```html
<div class="so-what">The blended rate is misleading — track segments separately.</div>
```

Amber-highlighted box with left border. Place after chart or finding.
Best on `_class: takeaway` slides.

---

## Finding Card (insight with impact)

```html
<div class="finding">
  <div class="finding-headline">Simpson's Paradox detected</div>
  <div class="finding-detail">Aggregate masks opposite segment trends</div>
  <div class="finding-impact">38% mix shift · 62% rate effect</div>
</div>
```

White card with amber left border. Impact line gets amber background.

---

## Chart Container

> **Warning:** Never use bare markdown image syntax (`![](...)`) for charts.
> Bare images bypass CSS containment and will overflow slide boundaries.
> Always wrap chart images in a `.chart-container` div as shown below.

```html
<div class="chart-container">
  <img src="charts/beat1_chart.png" alt="Description">
  <div class="chart-source">Source: internal analytics, Jan–Dec 2024</div>
</div>
```

White card with subtle border, flex layout, and overflow containment.
Always include `chart-source`. The `<img>` is automatically constrained
to fit within the container (max-height 380px, object-fit contain).

On `_class: chart-full` slides, the container expands to fill available
space and the `max-height: 420px` global override is removed — charts
get maximum room.

---

## Recommendation Row

```html
<div class="rec-row">
  <div class="rec-number">1</div>
  <div class="rec-content">
    <div class="rec-action">Fix mobile saved payment flow</div>
    <div class="rec-rationale">Expired card handling causes 20pt gap vs web</div>
  </div>
  <div class="rec-confidence high">HIGH</div>
</div>
```

Confidence modifiers: `.high` (green), `.medium` (amber), `.low` (gray).
**Always order recommendations High → Medium → Low** (Rule R4).
Best on `_class: recommendation` slides.

---

## Before / After Panels

```html
<div class="before-after">
  <div class="panel before">
    <div class="panel-label">Before</div>
    <div class="panel-desc">Manual analysis workflow</div>
    <div class="panel-time">3 days</div>
  </div>
  <div class="panel after">
    <div class="panel-label">After</div>
    <div class="panel-desc">AI-assisted pipeline</div>
    <div class="panel-time">15 min</div>
  </div>
</div>
```

---

## Flow Diagram (horizontal steps)

> **Tip:** Use HTML entities for arrows (`&rarr;` for →, `&darr;` for ↓) instead
> of raw Unicode characters. HTML entities render reliably across all platforms;
> raw Unicode arrows may display as tofu on some systems.

```html
<div class="flow">
  <div class="flow-step">
    <div class="icon">1</div>
    <div class="label">Frame</div>
    <div class="caption">Business question</div>
  </div>
  <div class="flow-arrow">&rarr;</div>
  <div class="flow-step">
    <div class="icon">2</div>
    <div class="label">Explore</div>
    <div class="caption">Data profiling</div>
  </div>
  <div class="flow-arrow">&rarr;</div>
  <div class="flow-step">
    <div class="icon">3</div>
    <div class="label">Analyze</div>
    <div class="caption">Root cause</div>
  </div>
  <div class="flow-arrow">&rarr;</div>
  <div class="flow-step">
    <div class="icon">4</div>
    <div class="label">Present</div>
    <div class="caption">Slide deck</div>
  </div>
</div>
```

---

## Vertical Flow (agent chain)

```html
<div class="vflow">
  <div class="vflow-step">
    <div class="icon">1</div>
    <div class="label">Question Framing</div>
  </div>
  <div class="vflow-arrow">&darr;</div>
  <div class="vflow-step">
    <div class="icon">2</div>
    <div class="label">Data Explorer</div>
  </div>
  <div class="vflow-arrow">&darr;</div>
  <div class="vflow-step">
    <div class="icon">3</div>
    <div class="label">Chart Maker</div>
  </div>
</div>
```

---

## Box Grid (2x2 or 3-col cards)

```html
<div class="box-grid">
  <div class="box-card accent">
    <div class="card-title">Product Changes</div>
    <div class="card-desc">App v2.4.0 payment SDK issues</div>
  </div>
  <div class="box-card">
    <div class="card-title">Mix Shift</div>
    <div class="card-desc">TikTok users now 35% of signups</div>
  </div>
  <div class="box-card">
    <div class="card-title">Technical</div>
    <div class="card-desc">Mobile checkout 20pts behind web</div>
  </div>
  <div class="box-card">
    <div class="card-title">External</div>
    <div class="card-desc">No external factor identified</div>
  </div>
</div>
```

For 3 columns: `<div class="box-grid three-col">`.
Accent modifier: `<div class="box-card accent">` (amber left border).

---

## Layers (stacked diagram)

```html
<div class="layers">
  <div class="layer accent">
    <div class="layer-icon">*</div>
    <div class="layer-title">Decision Layer</div>
    <div class="layer-desc">What action to take</div>
  </div>
  <div class="layer">
    <div class="layer-icon">*</div>
    <div class="layer-title">Analysis Layer</div>
    <div class="layer-desc">Evidence and methodology</div>
  </div>
  <div class="layer positive">
    <div class="layer-icon">*</div>
    <div class="layer-title">Data Layer</div>
    <div class="layer-desc">Sources and quality</div>
  </div>
</div>
```

Modifiers: `.accent` (amber), `.positive` (green).

---

## Timeline (horizontal)

```html
<div class="timeline">
  <div class="timeline-stop">
    <div class="dot"></div>
    <div class="stop-title">Week 1</div>
    <div class="stop-desc">Payment audit</div>
  </div>
  <div class="timeline-stop active">
    <div class="dot"></div>
    <div class="stop-title">Week 2</div>
    <div class="stop-desc">SDK fix deploy</div>
  </div>
  <div class="timeline-stop">
    <div class="dot"></div>
    <div class="stop-title">Week 4</div>
    <div class="stop-desc">Measure impact</div>
  </div>
</div>
```

Active stop: `<div class="timeline-stop active">` (amber dot with glow).

---

## Callout Box

```html
<div class="callout">
  <div class="callout-title">Key Assumption</div>
  <div class="callout-text">50% gap closure is conservative — mobile traffic growing 30% YoY compounds the opportunity.</div>
</div>
```

---

## Checklist

```html
<ul class="checklist">
  <li class="done">Source tie-out passed</li>
  <li class="done">Root cause is specific and actionable</li>
  <li>Experiment designed for validation</li>
  <li>Stakeholder sign-off received</li>
</ul>
```

---

## Badge / Tag (inline)

```html
<span class="badge positive">Validated</span>
<span class="badge negative">At Risk</span>
<span class="badge accent">In Progress</span>
<span class="badge neutral">Planned</span>
```

---

## Delta (inline metric change)

```html
<span class="delta up"><span class="arrow">↑</span> 12%</span>
<span class="delta down"><span class="arrow">↓</span> 23%</span>
<span class="delta flat">→ 0%</span>
```

---

## Data Source Attribution

```html
<div class="data-source">{{DISPLAY_NAME}} analytics · {{DATE_RANGE}} · n=2.4M sessions</div>
```

Placed at the bottom of data slides. Auto-aligns right with top border.

---

## Speaker Notes

```html
<!--
Speaker Notes:
"Opening line. Key talking point. [PAUSE] Transition phrase. [ADVANCE]"
-->
```

Place after slide content, before the next `---`.
