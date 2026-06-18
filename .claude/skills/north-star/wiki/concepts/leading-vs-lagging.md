---
title: Leading vs. Lagging Indicators
type: concept
schema_version: 1
sources:
  - definitions/definition-p016-l0373-leading-indicator.md
  - definitions/definition-p016-l0373-lagging-indicator.md
  - concepts/concept-p016-l0375-nsm-must-be-leading-indicator.md
related:
  - wiki/concepts/north-star-metric.md
  - wiki/concepts/nsm-checklist.md
  - wiki/concepts/vanity-metric.md
playbook_pages: [16]
tier: 1
confidence: high
confidence_derivation: "Anchor definitions reconciled at 5/5 each; supporting concept atom 6/6; not flagged in debates → high."
curator_status: approved
verified: true
created: 2026-05-26
updated: 2026-05-26
---

# Leading vs. Lagging Indicators

## TL;DR
A leading indicator predicts what will happen to the business; a lagging indicator tells you what has already happened. A good NSM is a leading indicator of business success. Lagging metrics like MRR or ARPU are not optimal NSMs because they report the past rather than predict the future. Subscription businesses should identify behaviors that correlate with renewal and build an NSM around those.

## Decision rule
- An NSM must be a leading indicator of business success [concept-p016-l0375-nsm-must-be-leading-indicator].
- Lagging metrics (MRR, ARPU, revenue, gross sales) are explicitly disqualified as NSM candidates.
- For subscription businesses: identify the behavior that correlates with renewal, then build the NSM around that behavior — not around the renewal itself.

## Detail
Both definitions come from the same playbook passage: "Some metrics tell you what has already happened to your business; these are lagging indicators. Other metrics predict what will happen to your business; these are leading indicators" [definition-p016-l0373-leading-indicator, definition-p016-l0373-lagging-indicator].

The concept body claim, which is checklist Q3 in the NSM diagnostic: "A good North Star Metric is a leading indicator of business success. Metrics like 'Monthly Recurring Revenue' or 'Average Revenue per User (ARPU)' aren't optimal North Star Metrics because they tell you what happened in the past rather than predicting future results" [concept-p016-l0375-nsm-must-be-leading-indicator].

This rule is one of the most-cited and least-controversial parts of the playbook. The reason for the rule is operational: if the NSM reports the past, the team's interventions arrive too late to course-correct. A leading indicator gives the team a chance to see a problem (or opportunity) early enough to act.

The practical handle for subscription businesses: revenue/renewal is the lagging signal you ultimately care about. The leading NSM is whatever behavior predicts renewal. For Dave (the banking app), the leading behavior was adding recurring expenses during onboarding — users who did so were 5.7x more likely to still be using Dave three months later. The NSM lives upstream of the lagging signal.

> NOTE — CONTESTED for B2B: Many B2B operators argue revenue (ARR/NRR) IS the NSM in contract-driven businesses where the buyer-user gap and value-event tracking noise make behavioral NSMs unreliable. See [Debate: B2B non-revenue NSM](../debates/b2b-revenue-as-nsm.md).

## yaml-rules
```yaml
leading_indicator:
  predicts: future_business_results
  use_as: north_star_metric
lagging_indicator:
  reports: past_business_results
  do_not_use_as: north_star_metric
  examples: [monthly_recurring_revenue, arpu, gross_sales]
nsm_constraint:
  must_be: leading_indicator
  must_not_be: lagging_indicator
subscription_business_pattern:
  build_nsm_around: behavior_correlated_with_renewal
  not_around: renewal_itself
```

## Related
- [North Star Metric](north-star-metric.md)
- [NSM Checklist](nsm-checklist.md)
- [Vanity Metric](vanity-metric.md)
