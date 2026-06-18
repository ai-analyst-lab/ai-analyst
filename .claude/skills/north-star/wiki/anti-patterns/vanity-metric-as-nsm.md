---
title: Vanity Metric as North Star
type: anti-pattern
schema_version: 1
sources:
  - raw/atoms/anti-patterns/anti-pattern-p018-l0407-vanity-metric-as-nsm.md
  - raw/atoms/anti-patterns/anti-pattern-p018-l0412-instance-daily-active-users.md
  - raw/atoms/anti-patterns/anti-pattern-p018-l0413-instance-ad-impressions.md
  - raw/atoms/anti-patterns/anti-pattern-p018-l0414-instance-number-of-downloads.md
  - raw/atoms/anti-patterns/anti-pattern-p018-l0415-instance-page-views.md
  - raw/atoms/anti-patterns/anti-pattern-p018-l0416-instance-registered-users.md
  - raw/atoms/anti-patterns/anti-pattern-p018-l0417-instance-story-points-delivered.md
  - raw/atoms/anti-patterns/anti-pattern-p018-l0418-instance-time-on-page.md
  - raw/atoms/case-study-fragments/case-study-fragment-p018-l0427-happy-deliveries-rejected-candidates.md
  - raw/atoms/case-study-fragments/case-study-fragment-p018-l0429-happy-deliveries-nsm-research-insight.md
related:
  - wiki/concepts/nsm-checklist.md
  - wiki/anti-patterns/nsm-disconnected-from-customer-value.md
  - wiki/cases/happy-deliveries.md
playbook_pages: [15, 18]
anti_pattern_id: vanity-metric-as-nsm
severity: high
tier: 1
confidence: high
confidence_derivation: "Source atom and 7 instance atoms all tier 1, confidence high; explicit Checklist Q7 treatment plus NORTH STAR IN ACTION callout (Happy Deliveries)."
curator_status: approved
verified: true
created: 2026-05-26
updated: 2026-05-26
---

# Vanity metric as North Star

## TL;DR
A vanity metric gives the team warm fuzzies but isn't actually evidence of product success. It usually only goes up, counts activity rather than value, and decouples team excitement from any change in customer outcomes. Replace with a behavior-grounded metric using the vanity-metric test.

## Spot signals
- The metric only ever goes up — there's no plausible scenario in which it moves down.
- The metric is a raw count of activity (impressions, views, downloads, registrations) rather than a behavior that indicates value received.
- Team excitement about the number is decoupled from any change in customer outcomes, retention, or revenue.
- The metric mostly tracks marketing or release activity rather than what users actually did with the product.
- You cannot explain in one sentence how a change in this metric reflects customer value.

## Fix recipe
1. Run the vanity-metric test: ask whether movement in this metric reliably indicates customers got more value, not just that more activity happened.
2. Replace with a behavior-grounded metric. The Happy Deliveries team moved from "People Opening the App / Scheduled Deliveries / Early Deliveries" to deliveries with no issues — which correlated with retention and CLTV.
3. Pressure-test against Checklist Q1 (customer value) and Q7 (not vanity).
4. Confirm the metric can move both up and down based on real product changes.

## Examples — vanity metrics the playbook names explicitly (p. 18)

- **Daily Active Users (DAU)** — counts logins, not value received. Climbs with notifications, required logins, or addictive patterns without improving customer outcomes. (See also p. 15.) `[instance-dau-as-nsm]`
- **Ad impressions** — counts ad serves, not engagement or conversion. Rises from inventory expansion alone, independent of audience quality. `[instance-ad-impressions-as-nsm]`
- **Number of downloads** — counts installs without usage thresholds. Spikes with paid acquisition regardless of product quality; gives no view of activation. `[instance-downloads-as-nsm]`
- **Page views** — counts traffic, not what visitors accomplished. Climbs with SEO/ad spend; high page views often coexist with poor conversion or retention. `[instance-page-views-as-nsm]`
- **Registered users** — cumulative-only count of accounts that exists. Can only go up; doesn't distinguish active from dormant. (Also cited p. 15.) `[instance-registered-users-as-nsm]`
- **Story points delivered** — measures engineering throughput, not whether shipped work created customer value. Feature-factory signature. `[instance-story-points-as-nsm]`
- **Time on page** — directionally ambiguous: high time can mean engagement OR confusion/inability to complete a task. `[instance-time-on-page-as-nsm]`

**Case in action:** [Happy Deliveries](../cases/happy-deliveries.md) — rejected the activity-flavored candidates above and chose "deliveries with no issues," which research showed correlated with CLTV.
