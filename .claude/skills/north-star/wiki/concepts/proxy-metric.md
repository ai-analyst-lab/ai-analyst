---
title: Proxy Metric — Measurable Stand-In for a Hard-to-Track Behavior
type: concept
schema_version: 1
sources:
  - definitions/definition-p017-l0399-proxy-metric.md
  - principles/principle-p039-l0925-dont-disregard-hard-to-measure.md
related:
  - wiki/concepts/nsm-checklist.md
  - wiki/concepts/north-star-metric.md
playbook_pages: [17, 39]
tier: 1
confidence: high
confidence_derivation: "Anchor definition atom 6/6; principle 3/3; not flagged in debates → high."
curator_status: approved
verified: true
created: 2026-05-26
updated: 2026-05-26
---

# Proxy Metric — Measurable Stand-In for a Hard-to-Track Behavior

## TL;DR
A proxy metric is a measurable metric used to stand in for a target customer behavior that is hard to instrument directly. Proxy metrics let an NSM survive Question 6 of the checklist (measurability) without abandoning the customer-value-aligned behavior the team really cares about. Do not disregard a promising NSM concept just because it isn't yet measurable — find or build a proxy.

## Decision rule
- If the target behavior is the right customer-value signal but cannot be instrumented, use a proxy metric that correlates with it.
- Do not reject a promising NSM candidate at Question 6 (measurability) before considering proxies [principle-p039-l0925-dont-disregard-hard-to-measure].
- The proxy must itself pass the rest of the NSM checklist (especially Q1 customer value and Q3 leading indicator).

## Detail
Canonical definition: "In this example, the number of customers sharing their insights — a measurable metric — is a proxy metric for the number of customers pondering the films, which is tougher to collect" [definition-p017-l0399-proxy-metric].

The playbook's worked example: a film-aficionado streaming service wants to measure "customers pondering the films they watch" — a high-value behavior, but not directly observable in product instrumentation. The team picks "number of customers sharing their insights about a film" as the proxy. The behavior the team cares about (pondering) is the customer-value target; the measurable behavior (sharing insights) is a downstream signal that correlates with it.

The companion principle: "Though 'measurable' is a characteristic of a good North Star, avoid getting too concerned too soon with how you'll calculate the metric or its inputs" [principle-p039-l0925-dont-disregard-hard-to-measure]. Teams that jump immediately to "can we measure that?" tend to short-circuit the NSM design, settling for a measurable-but-low-value metric over a high-value-but-currently-hard-to-measure one.

A proxy is not a license to cheat. The proxy itself must pass the rest of the NSM checklist — it must express customer value, be a leading indicator, be actionable, be understandable, and not be a vanity metric. The proxy's relationship to the target behavior is also subject to revisit: if instrumentation improves or correlation breaks down, the team should revisit the proxy choice.

Amplitude's own NSM (Weekly Learning Users — "users who have shared a learning with at least two other people in the last seven days") is itself proxy-shaped: the team cannot directly measure whether someone "learned" something, but they can measure whether someone shared a learning with two other people, which they treat as a reliable proxy.

## yaml-rules
```yaml
proxy_metric_definition:
  is: measurable_metric
  stands_in_for: target_behavior_hard_to_instrument
when_to_use_proxy:
  - target_behavior_is_correct_customer_value_signal
  - target_behavior_cannot_be_instrumented_directly
  - measurable_proxy_correlates_with_target_behavior
do_not:
  - disregard_promising_nsm_for_lack_of_direct_measurement
proxy_must_still_pass:
  - q1_customer_value
  - q3_leading_indicator
  - q4_actionable
  - q5_understandable
  - q7_not_vanity
proxy_revisit_triggers:
  - instrumentation_improved_target_now_measurable
  - correlation_target_proxy_broke_down
```

## Related
- [NSM Checklist](nsm-checklist.md)
- [North Star Metric](north-star-metric.md)
