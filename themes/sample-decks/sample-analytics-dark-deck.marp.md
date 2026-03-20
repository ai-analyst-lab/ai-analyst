---
marp: true
theme: analytics-dark
size: 16:9
paginate: true
html: true
footer: "AXS Pte Ltd | Sample Dark Deck"
---

<!-- _class: dark-title -->

<div class="accent-bar"></div>

# Mobile conversion dropped 18% in Q3
Erasing gains from the app redesign

Product Analytics | Q3 2025

<!--
Speaker Notes:
"Today we're looking at a significant drop in mobile conversion that happened over Q3. The data points to a specific, fixable cause. [PAUSE]"
-->

---

## Key Metrics at a Glance

<div class="kpi-row">
  <div class="kpi-card">
    <div class="kpi-value negative">-18%</div>
    <div class="kpi-label">Mobile Conversion</div>
    <div class="kpi-delta down">3.8% to 3.1%</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-value">4.2%</div>
    <div class="kpi-label">Desktop Conversion</div>
    <div class="kpi-delta flat">Stable</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-value negative">$340K</div>
    <div class="kpi-label">Monthly Revenue Impact</div>
    <div class="kpi-delta down">Lost mobile conversions</div>
  </div>
</div>

<div class="data-source">Source: Orders + sessions tables | Jul-Sep 2025</div>

<!--
Speaker Notes:
"Three numbers tell the story. Mobile conversion fell 18%, desktop held steady, and the revenue impact is roughly $340K per month. [HANDS] Raise your hand if that number would get your VP's attention. [ADVANCE]"
-->

---

## Mobile conversion fell sharply after the iOS 18 update

<div class="chart-container">
  <div class="chart-title">Conversion Rate by Device, Weekly (Q2-Q3 2025)</div>
  <div style="height: 280px; display: flex; align-items: center; justify-content: center; color: var(--dk-text-muted); font-style: italic;">[Chart: Line chart showing mobile drop after Aug 12, desktop stable]</div>
  <div class="chart-source">Source: {schema}.sessions + {schema}.orders</div>
</div>

<div class="so-what">The drop correlates precisely with the iOS 18 rollout (Aug 12). Desktop unaffected. This is not a seasonal pattern.</div>

<!--
Speaker Notes:
"Start with the overall trend line. Desktop has been rock-steady at 4.2%. But look at mobile after August 12 — that's when iOS 18 started rolling out. The correlation is strong. [PAUSE — let this sink in] [ADVANCE]"
-->

---

<!-- _class: insight -->

## The checkout flow breaks on iOS 18 Safari

<div class="before-after">
  <div class="panel before">
    <div class="panel-label">Before iOS 18</div>
    <div class="panel-desc">Payment form renders correctly on mobile Safari. Auto-fill works. 3-tap checkout.</div>
    <div class="panel-time">3.8% conversion</div>
  </div>
  <div class="panel after">
    <div class="panel-label">After iOS 18</div>
    <div class="panel-desc">Payment form misaligns. Auto-fill broken. Users abandon at payment step.</div>
    <div class="panel-time">3.1% conversion</div>
  </div>
</div>

<div class="data-source">Source: Session recordings + checkout funnel analysis</div>

<!--
Speaker Notes:
"We traced it to the checkout page specifically. Before iOS 18, the payment form worked fine. After the update, the form elements misalign on Safari and auto-fill stopped working. [ASK] Has anyone seen something like this with a major OS update? [ADVANCE]"
-->

---

## Three findings point to the same root cause

<div class="box-grid">
  <div class="box-card accent">
    <div class="card-title">Drop is mobile-only</div>
    <div class="card-desc">Desktop conversion unchanged at 4.2%. The issue is isolated to mobile Safari browsers.</div>
  </div>
  <div class="box-card accent">
    <div class="card-title">Drop is checkout-specific</div>
    <div class="card-desc">Browse, search, and cart metrics all stable. The funnel breaks at payment.</div>
  </div>
  <div class="box-card accent">
    <div class="card-title">Timing matches iOS 18</div>
    <div class="card-desc">The inflection point is Aug 12, precisely when the iOS 18 public release began.</div>
  </div>
  <div class="box-card accent">
    <div class="card-title">Fix is scoped</div>
    <div class="card-desc">Engineering estimates 2 weeks to patch the Safari CSS and restore auto-fill support.</div>
  </div>
</div>

<!--
Speaker Notes:
"Four data points all converge. It's mobile-only, checkout-specific, correlated with iOS 18, and engineering says it's a 2-week fix. This is a solvable problem. [ADVANCE]"
-->

---

## Recommended Actions

<div class="rec-row">
  <div class="rec-number">1</div>
  <div class="rec-content">
    <div class="rec-action">Prioritize the iOS 18 checkout fix over planned Q4 features</div>
    <div class="rec-rationale">Recovering $340K/month in lost mobile revenue has higher ROI than any planned Q4 feature.</div>
  </div>
  <div class="rec-confidence high">High</div>
</div>
<div class="rec-row">
  <div class="rec-number">2</div>
  <div class="rec-content">
    <div class="rec-action">Add mobile Safari to the pre-release testing matrix</div>
    <div class="rec-rationale">This was caught by users, not by QA. Prevent recurrence on future OS updates.</div>
  </div>
  <div class="rec-confidence high">High</div>
</div>
<div class="rec-row">
  <div class="rec-number">3</div>
  <div class="rec-content">
    <div class="rec-action">Monitor Android 15 rollout for similar issues</div>
    <div class="rec-rationale">Android 15 launches in October. Run the same funnel check proactively.</div>
  </div>
  <div class="rec-confidence medium">Medium</div>
</div>

<!--
Speaker Notes:
"Three actions, in priority order. The first one is clear — fix the checkout. The second prevents this from happening again. The third is proactive monitoring for the next OS cycle. [POLL] Drop in chat: 1, 2, or 3 — which of these would your team push back on? [ADVANCE]"
-->

---

## Metric Callout Example

<div class="metric-callout">
  <div class="metric-value accent">$4.1M</div>
  <div class="metric-label">Annual Revenue at Risk</div>
  <div class="metric-context">$340K/month x 12 months if unfixed</div>
</div>

<!--
Speaker Notes:
"This slide demonstrates the metric-callout component in dark mode. Large numbers with accent coloring stand out clearly against the dark background."
-->

---

## Finding Card Example

<div class="finding">
  <div class="finding-headline">Mobile Safari users abandon checkout at 3x the desktop rate</div>
  <div class="finding-detail">Since the iOS 18 update, the checkout abandonment rate on mobile Safari increased from 12% to 36%, while desktop Chrome remained stable at 11%.</div>
  <div class="finding-impact">Impact: ~8,500 abandoned checkouts per month, representing $340K in lost revenue</div>
</div>

<div class="callout">
  <div class="callout-title">Key Takeaway</div>
  <div class="callout-text">The finding and callout components render with dark surfaces and amber accents automatically in the analytics-dark theme.</div>
</div>

<!--
Speaker Notes:
"This demonstrates the finding card and callout components. Both use the dark surface color with amber accent borders."
-->

---

## Component Reference: Tables

| Metric | Q2 Average | Q3 Average | Delta |
|--------|-----------|-----------|-------|
| **Mobile Conversion** | 3.8% | 3.1% | -18% |
| **Desktop Conversion** | 4.2% | 4.2% | 0% |
| **Cart Add Rate** | 12.1% | 11.8% | -2% |
| **Checkout Start** | 8.4% | 7.9% | -6% |
| **Payment Complete** | 3.8% | 3.1% | -18% |

<div class="data-source">Source: Funnel analysis | Q2-Q3 2025</div>

<!--
Speaker Notes:
"Tables render with dark headers (elevated surface + amber bottom border) and subtle zebra striping. Bold text in cells uses the amber-light color for emphasis."
-->

---

<!-- _class: dark-impact -->

## Fix the checkout. Recover $340K/month. Ship by end of October.

Next step: Eng lead to scope the Safari CSS fix by EOD Friday.

<!--
Speaker Notes:
"One slide summary. We know what's broken, we know the impact, and we know the fix. The ask is clear: prioritize this sprint. [PAUSE — let this sink in]"
-->
