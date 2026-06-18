---
title: Vanity Metric — Feel-Good Signal That Doesn't Track Long-Term Value
type: concept
schema_version: 1
sources:
  - definitions/definition-p018-l0409-vanity-metric.md
  - concepts/concept-p018-l0408-nsm-must-not-be-vanity.md
related:
  - wiki/concepts/north-star-metric.md
  - wiki/concepts/nsm-checklist.md
  - wiki/concepts/leading-vs-lagging.md
playbook_pages: [18]
tier: 1
confidence: high
confidence_derivation: "Anchor definition atom 5/5; supporting concept atom 5/5; not flagged in debates → high."
curator_status: approved
verified: true
created: 2026-05-26
updated: 2026-05-26
---

# Vanity Metric — Feel-Good Signal That Doesn't Track Long-Term Value

## TL;DR
A vanity metric makes a team feel good about short-term performance but does not reliably indicate the product's long-term success. Vanity metrics are not appropriate North Star Metrics. When the NSM changes, the team should be confident the change is meaningful and valuable — vanity metrics fail this test. The playbook enumerates seven recurring vanity-metric anti-patterns: DAU, ad impressions, registered users, page views, story points, time on page, and similar feel-good counts.

## Decision rule
- A candidate fails NSM Question 7 (and is disqualified) if it is a vanity metric [concept-p018-l0408-nsm-must-not-be-vanity].
- A metric is a vanity metric if its movement does not reliably indicate meaningful, valuable change in the product or customer outcome.
- Specific disqualified examples (anti-pattern instances): Daily Active Users, ad impressions, registered users, page views, story points, time on page.

## Detail
Canonical definition: "Though some metrics might make you feel good about your performance in the short term, they don't always tell you about your product's long-term success. Be wary of choosing these vanity metrics for your North Star Metric" [definition-p018-l0409-vanity-metric].

The body claim that anchors checklist Question 7: "When your North Star changes, you want to be confident that the change is meaningful and valuable. Though some metrics might make you feel good about your performance in the short term, they don't always tell you about your product's long-term success" [concept-p018-l0408-nsm-must-not-be-vanity].

The distinction between vanity and non-vanity is not about whether a metric is measurable or readable — it is about whether movement in the metric reliably implies movement in customer value and durable business results. DAU can rise because of paid acquisition spend while engaged-user health declines; ad impressions can rise while transaction completion falls; registered users can rise while activation rates collapse. In each case the metric goes up while the product gets worse.

The seven vanity-metric examples the playbook enumerates (each cataloged as an anti-pattern instance):

1. Daily Active Users (DAU)
2. Ad impressions
3. Registered users
4. Page views
5. Story points
6. Time on page
7. Other short-term feel-good counts

A vanity metric typically violates at least one other checklist criterion as well — most often the customer-value check (Q1) or the leading-indicator check (Q3). The playbook treats vanity as a distinct failure mode worth its own diagnostic because teams attached to a vanity metric often defend it on the other criteria (it IS measurable, it IS understandable) without noticing the deeper miss.

## yaml-rules
```yaml
vanity_metric_definition:
  short_term: feels_good
  long_term: does_not_indicate_product_success
  use_as_nsm: never
vanity_metric_examples:
  - daily_active_users
  - ad_impressions
  - registered_users
  - page_views
  - story_points
  - time_on_page
vanity_metric_test:
  fails_if: movement_does_not_imply_meaningful_customer_value_change
typical_co_violations:
  - q1_customer_value
  - q3_leading_indicator
```

## Related
- [North Star Metric](north-star-metric.md)
- [NSM Checklist](nsm-checklist.md)
- [Leading vs. Lagging](leading-vs-lagging.md)
