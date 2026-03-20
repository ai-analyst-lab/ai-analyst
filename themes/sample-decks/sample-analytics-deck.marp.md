---
marp: true
theme: analytics-light
size: 16:9
paginate: true
html: true
footer: "AXS Pte Ltd | Sample Deck"
---

<!-- _class: title -->

<div class="accent-bar"></div>

# Mobile conversion dropped 18% in Q3
Erasing gains from the app redesign

Product Analytics | Q3 2025

<!--
Speaker Notes:
"Today we're looking at a significant drop in mobile conversion that happened over Q3. The data points to a specific, fixable cause."
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
"Three numbers tell the story. Mobile conversion fell 18%, desktop held steady, and the revenue impact is roughly $340K per month."
-->

---

## Mobile conversion fell sharply after the iOS 18 update

<div class="chart-container">
  <div class="chart-title">Conversion Rate by Device, Weekly (Q2-Q3 2025)</div>
  <div style="height: 280px; display: flex; align-items: center; justify-content: center; color: var(--text-muted); font-style: italic;">[Chart: Line chart showing mobile drop after Aug 12, desktop stable]</div>
  <div class="chart-source">Source: {schema}.sessions + {schema}.orders</div>
</div>

<div class="so-what">The drop correlates precisely with the iOS 18 rollout (Aug 12). Desktop unaffected. This is not a seasonal pattern.</div>

<!--
Speaker Notes:
"Start with the overall trend line. Desktop has been rock-steady at 4.2%. But look at mobile after August 12 — that's when iOS 18 started rolling out. The correlation is strong."
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
"We traced it to the checkout page specifically. Before iOS 18, the payment form worked fine. After the update, the form elements misalign on Safari and auto-fill stopped working. Users get frustrated at the last step."
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
"Four data points all converge. It's mobile-only, checkout-specific, correlated with iOS 18, and engineering says it's a 2-week fix. This is a solvable problem."
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
"Three actions, in priority order. The first one is clear — fix the checkout. The second prevents this from happening again. The third is proactive monitoring for the next OS cycle."
-->

---

<!-- _class: impact -->

## Fix the checkout. Recover $340K/month. Ship by end of October.

Next step: Eng lead to scope the Safari CSS fix by EOD Friday.

<!--
Speaker Notes:
"One slide summary. We know what's broken, we know the impact, and we know the fix. The ask is clear: prioritize this sprint."
-->
