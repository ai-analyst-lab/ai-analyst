---
title: NSM Checklist — The Seven Qualifying Questions
type: concept
schema_version: 1
sources:
  - concepts/concept-p015-l0353-nsm-must-express-customer-value.md
  - concepts/concept-p015-l0359-nsm-should-read-as-strategy.md
  - concepts/concept-p016-l0375-nsm-must-be-leading-indicator.md
  - concepts/concept-p016-l0383-nsm-must-be-actionable.md
  - concepts/concept-p017-l0391-nsm-plain-language-test.md
  - concepts/concept-p017-l0395-nsm-must-be-measurable.md
  - concepts/concept-p018-l0408-nsm-must-not-be-vanity.md
  - principles/principle-p039-l0925-dont-disregard-hard-to-measure.md
related:
  - wiki/concepts/north-star-metric.md
  - wiki/concepts/leading-vs-lagging.md
  - wiki/concepts/vanity-metric.md
  - wiki/concepts/proxy-metric.md
playbook_pages: [15, 16, 17, 18, 39]
tier: 1
confidence: high
confidence_derivation: "7 concept atoms reconciled at 4/4-6/6 (most 5/5+); strong inter-extractor agreement; not flagged in debates → high."
curator_status: approved
verified: true
created: 2026-05-26
updated: 2026-05-26
---

# NSM Checklist — The Seven Qualifying Questions

## TL;DR
A candidate fully qualifies as a North Star Metric only when it passes all seven checklist questions: it (1) expresses customer value, (2) represents the product's vision and strategy, (3) is a leading indicator, (4) is actionable (within the team's sphere of influence), (5) is understandable to non-technical colleagues, (6) is measurable (a proxy is acceptable), and (7) is not a vanity metric. Four of the seven are fatal: failing any of Q1 (customer value), Q3 (leading indicator), Q4 (actionable), or Q7 (not vanity) disqualifies the candidate outright.

## Decision rule
The verdict is one of three tiers, computed in `helpers/north_star/nsm_checklist.py::build_verdict` from the `fatal_if_fail` flags in the yaml-rules block below — this block is the single source of truth, and every other statement of the rule (agent prompts, docstrings, this prose) must agree with it.

- **PASS** — passes all 7 checks.
- **FAIL** — fails one or more *fatal* questions. The fatal set is Q1 (customer value), Q3 (leading indicator), Q4 (actionable), Q7 (not vanity). A fatal failure cannot be offset by passing the others.
- **WEAK** — every fatal question passes and no question is hard-failed, but the Auditor flags a reservation (a WEAK per-question verdict) on one or more non-fatal questions (Q2 vision/strategy, Q5 understandable, Q6 measurable). The candidate is not disqualified.

Mechanics: `build_verdict` assigns FAIL when *any* question carries a FAIL or UNKNOWN verdict, WEAK when the only marks are WEAK, otherwise PASS. The `fatal_if_fail` flags identify which failures are fatal and are surfaced in the `fatal_failures` list for the artifact. The Auditor therefore reserves a hard FAIL verdict for fatal-question violations; non-fatal reservations get a WEAK verdict, not a FAIL.

Note on Q6 (measurable): failing it is non-fatal in the sense that a proxy is acceptable — the Auditor marks Q6 WEAK (not FAIL) whenever a proxy path exists, and a promising NSM concept should not be discarded just because measurement isn't yet figured out [principle-p039-l0925-dont-disregard-hard-to-measure]. Q6 earns a hard FAIL only when there is no path to measurement at all, which does disqualify the candidate.

## Detail
The seven questions, as worked through Chapter 2:

**Q1. Does your NSM express customer value?** "A good North Star Metric represents what customers value about your product. When teams fail to connect their North Star Metric to customer value, they risk leading their business down the wrong path" [concept-p015-l0353-nsm-must-express-customer-value]. DAU and "Registered Users" fail this check.

**Q2. Does your NSM represent your vision and strategy?** "If you've built a strong North Star, someone should be able to read it and understand your company's product strategy and your vision — at least at a high level" [concept-p015-l0359-nsm-should-read-as-strategy]. If the company's mission is not unique, the NSM may not feel uniquely differentiated either — and that is okay.

**Q3. Is your NSM a leading indicator?** "A good North Star Metric is a leading indicator of business success. Metrics like 'Monthly Recurring Revenue' or 'Average Revenue per User (ARPU)' aren't optimal North Star Metrics because they tell you what happened in the past rather than predicting future results" [concept-p016-l0375-nsm-must-be-leading-indicator]. See [Leading vs. Lagging](leading-vs-lagging.md).

**Q4. Is your NSM actionable?** "Your North Star should be something you believe you can influence or change. This means it shouldn't measure a broader market trend or reflect real-world realities that would be true whether your product existed or not" [concept-p016-l0383-nsm-must-be-actionable]. "Customers' Lifelong Employees" for an HR app fails this — the company can influence retention but cannot make customers stay at their jobs forever.

**Q5. Is your NSM understandable?** "The best North Stars are framed in plain language. It shouldn't be so abstract that you can't easily explain it to non-technical people or express it without jargon. A simple test: describe it to someone who knows your business but lacks deep technical knowledge" [concept-p017-l0391-nsm-plain-language-test].

**Q6. Is your NSM measurable?** "If you'll never be able to configure your products and processes to collect the data you need to track and communicate the North Star Metric, it's not a good metric" [concept-p017-l0395-nsm-must-be-measurable]. A proxy metric is acceptable. Do not disregard a promising NSM concept because measurement isn't yet figured out [principle-p039-l0925-dont-disregard-hard-to-measure].

**Q7. Is your NSM not a vanity metric?** "When your North Star changes, you want to be confident that the change is meaningful and valuable... Be wary of choosing these vanity metrics for your North Star Metric" [concept-p018-l0408-nsm-must-not-be-vanity]. DAU, ad impressions, registered users, page views, story points, and time-on-page are explicitly called out as vanity. See [Vanity Metric](vanity-metric.md).

## yaml-rules
```yaml
nsm_checklist:
  questions:
    - id: q1_customer_value
      check: expresses_customer_value
      fatal_if_fail: true
    - id: q2_vision_strategy
      check: represents_vision_and_strategy
      fatal_if_fail: false
    - id: q3_leading_indicator
      check: is_leading_indicator
      fatal_if_fail: true
    - id: q4_actionable
      check: is_actionable
      fatal_if_fail: true
    - id: q5_understandable
      check: understandable_to_non_technical
      fatal_if_fail: false
    - id: q6_measurable
      check: is_measurable_directly_or_via_proxy
      fatal_if_fail: false
      proxy_metric_allowed: true
    - id: q7_not_vanity
      check: not_a_vanity_metric
      fatal_if_fail: true
candidate_qualifies_if:
  passes_all_seven_checklist_criteria: true
```

## Related
- [North Star Metric](north-star-metric.md)
- [Leading vs. Lagging Indicators](leading-vs-lagging.md)
- [Vanity Metric](vanity-metric.md)
- [Proxy Metric](proxy-metric.md)
