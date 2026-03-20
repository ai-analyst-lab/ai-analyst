---
marp: true
theme: analytics
size: 16:9
paginate: true
html: true
footer: "AXS Pte Ltd | {{CLIENT}} | {{MONTH_YEAR}}"
---

<!-- _class: title -->

# {{DECK_TITLE}}

**{{SUBTITLE}}**
{{MONTH_YEAR}}

<div class="accent-bar"></div>

<!--
Speaker Notes:
"Opening context. What question are we answering today? [PAUSE] [ADVANCE]"
-->

---

<!-- _class: section-opener -->

## Context

The setup — what happened and why we looked into it

<!--
Speaker Notes:
"Before diving into findings, let me set the stage. [ADVANCE]"
-->

---

<!-- _class: kpi -->

## The headline finding with specific numbers

<div class="kpi-row">
  <div class="kpi-card">
    <div class="kpi-value negative">-59%</div>
    <div class="kpi-label">Conversion Rate</div>
    <div class="kpi-delta down">Feb → Dec 2024</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-value">250K</div>
    <div class="kpi-label">Monthly Sessions</div>
    <div class="kpi-delta up">+28x growth</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-value accent">81%</div>
    <div class="kpi-label">Returning Users</div>
    <div class="kpi-delta flat">of session mix</div>
  </div>
</div>

<!--
Speaker Notes:
"Three numbers that tell the story. [PAUSE] Each card is one metric — no chart needed. [ADVANCE]"
-->

---

<!-- _class: chart-full -->

## Conversion declined steadily across all segments

<div class="chart-container">
  <img src="charts/beat1_example.png" alt="Line chart showing conversion decline by segment">
  <div class="chart-source">Source: internal analytics, Jan–Dec 2024</div>
</div>

<!--
Speaker Notes:
"One chart, maximum space. Walk through the trend line. [PAUSE] [ADVANCE]"
-->

---

<!-- _class: takeaway -->

## The blended conversion rate is misleading

<div class="so-what">The denominator changed as much as the numerator — the mix shifted toward low-converting segments, masking real rate improvements in high-value cohorts.</div>

<div class="finding">
  <div class="finding-headline">Simpson's Paradox detected</div>
  <div class="finding-detail">Every segment improved individually, but the aggregate declined due to a 38% mix shift toward TikTok-sourced users with 2.2% baseline conversion.</div>
</div>

<!--
Speaker Notes:
"This is the so-what from the previous chart. Separate slides force you to state the interpretation explicitly. [ADVANCE]"
-->

---

<!-- _class: chart-right -->

## Narrative on the left, chart on the right

Key finding description with supporting detail.

- **Segment A:** 9.2% → 6.1% (real decline)
- **Segment B:** ~2.2% (stable)

<div class="finding">
  <div class="finding-headline">Simpson's Paradox detected</div>
  <div class="finding-detail">The aggregate masks opposite segment trends</div>
  <div class="finding-impact">38% mix shift · 62% real rate effect</div>
</div>

<div class="chart-container">
  <img src="charts/beat3_example.png" alt="Chart showing segment comparison">
</div>

<!--
Speaker Notes:
"Left side: narrative context. Right side: visual evidence. [ADVANCE]"
-->

---

<!-- _class: impact -->

## The pivotal question or transition statement

What should we do about this?

<!--
Speaker Notes:
"[PAUSE for effect] This is the pivot from diagnosis to action. [ADVANCE]"
-->

---

<!-- _class: recommendation -->

## Recommendations

<div class="rec-row">
  <div class="rec-number">1</div>
  <div class="rec-content">
    <div class="rec-action">Highest-confidence action item</div>
    <div class="rec-rationale">Why this matters and expected impact</div>
  </div>
  <div class="rec-confidence high">HIGH</div>
</div>

<div class="rec-row">
  <div class="rec-number">2</div>
  <div class="rec-content">
    <div class="rec-action">Second priority action</div>
    <div class="rec-rationale">Supporting rationale</div>
  </div>
  <div class="rec-confidence medium">MEDIUM</div>
</div>

<div class="rec-row">
  <div class="rec-number">3</div>
  <div class="rec-content">
    <div class="rec-action">Lower confidence exploration</div>
    <div class="rec-rationale">Requires additional data</div>
  </div>
  <div class="rec-confidence low">LOW</div>
</div>

<!--
Speaker Notes:
"Three recommendations, ordered by confidence. [Walk through each] [ADVANCE]"
-->

---

<!-- _class: insight -->

## Before / After comparison

<div class="before-after">
  <div class="panel before">
    <div class="panel-label">Before</div>
    <div class="panel-desc">Current state description</div>
    <div class="panel-time">3 days</div>
  </div>
  <div class="panel after">
    <div class="panel-label">After</div>
    <div class="panel-desc">Improved state description</div>
    <div class="panel-time">15 min</div>
  </div>
</div>

<!--
Speaker Notes:
"The contrast makes the value proposition concrete. [ADVANCE]"
-->

---

<!-- _class: appendix -->

## Appendix: Methodology & Caveats

- **Data source:** {{DISPLAY_NAME}} analytics warehouse, {{DATE_RANGE}}
- **Cohort definition:** Users with at least one session in the analysis period
- **Exclusions:** Bot traffic filtered via User-Agent rules (< 0.3% of sessions)
- **Statistical tests:** Two-proportion z-test for segment comparisons (p < 0.01)
- **Known limitation:** Attribution model is last-touch; may undercount multi-channel journeys

<!--
Speaker Notes:
"Reference slide — not presented live unless asked. [END]"
-->
