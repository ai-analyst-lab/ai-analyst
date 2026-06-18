---
title: Product Vision — Catalyst for the NSM
type: concept
schema_version: 1
sources:
  - concepts/concept-p037-l0840-vision-statement-informs-nsm.md
  - concepts/concept-p025-l0560-tension-current-vs-future.md
related:
  - wiki/concepts/north-star-metric.md
  - wiki/concepts/statement-exercise.md
  - wiki/concepts/two-categories-of-trouble.md
  - wiki/concepts/north-star-of-the-north-star.md
playbook_pages: [25, 37]
tier: 1
confidence: high
confidence_derivation: "2 concept atoms reconciled at 3/3 and 1/1; Debate 10 (metric-centric vs. narrative-centric) flags an active disagreement → high with contested flag."
contested: true
curator_status: approved
verified: true
created: 2026-05-26
updated: 2026-05-26
---

# Product Vision — Catalyst for the NSM

## TL;DR
An existing product vision is a useful catalyst for teasing out a good NSM. When designing a North Star, ask: "What does this vision say that is distinct?" and "What can we learn about our product's value from it?" The best NSM definitions span both the product's current state and its future ambition — the tension between what the product IS and what it WANTS to be is a feature, not a bug.

## Decision rule
- If the company has a product vision statement, use it as the catalyst for NSM design — do not start from scratch [concept-p037-l0840-vision-statement-informs-nsm].
- When writing the NSM definition, span both current state AND future ambition; healthy tension between the two is intentional [concept-p025-l0560-tension-current-vs-future].
- Use product-vision connection as one of three "shared understanding" tools (with [Beliefs](beliefs.md) and [Key Value Exchanges](key-value-exchanges.md)) when a team is stuck converging on the NSM.

## Detail
The catalyst principle: "Your business may have already done the important work of crafting a product vision statement. These existing statements can be great catalysts for teasing out a good North Star" [concept-p037-l0840-vision-statement-informs-nsm]. The two questions to ask about an existing vision statement:

1. **What does this say that is distinct or foundational?** — extract what makes this product different
2. **What can we learn about our product's value from this statement?** — extract the customer-value signal that the NSM should track

The playbook gives two worked vision-statement examples on p. 37 (film-aficionado and label-design products) showing how a vision sentence translates into NSM-candidate language.

**Current state vs. future tension is a feature.** "The best metric definitions cover your product's current market, functionality, performance, and its potential future. There will always be healthy tension between what you are — the current state of your product — and what you want to be — some new reality you want to enable with your product" [concept-p025-l0560-tension-current-vs-future]. A definition that only describes the current product becomes a status report. A definition that only describes the future becomes aspirational marketing. Spanning both makes the NSM a strategy artifact — it tells you what the product is AND what it is trying to become.

Product vision is one of the three "shared understanding" troubleshooting tools the playbook prescribes for teams stuck disagreeing about the NSM — alongside [Beliefs](beliefs.md) and [Key Value Exchanges](key-value-exchanges.md). See [Two Categories of Trouble](two-categories-of-trouble.md).

> NOTE — CONTESTED: The Geoffrey Moore strategic-discipline lineage and Marty Cagan's product-vision tradition argue that the NARRATIVE (a 3-5 year story of the future product) — not the metric — should be the unifying artifact. The playbook itself partially concedes this in its "North Star of the North Star" framing about conversation quality. See [Debate: Metric-centric vs. narrative-centric](../debates/nsm-vs-vision-statement.md).

## yaml-rules
```yaml
product_vision_as_catalyst:
  use_when: company_has_existing_vision_statement
  questions_to_ask:
    - what_does_vision_say_that_is_distinct_or_foundational
    - what_can_we_learn_about_product_value_from_vision
nsm_definition_should_span:
  - current_state
  - future_ambition
tension_between_current_and_future:
  is_a_feature: true
  is_a_bug: false
shared_understanding_tools:
  - beliefs
  - product_vision
  - key_value_exchanges
```

## Related
- [North Star Metric](north-star-metric.md)
- [Statement Exercise](statement-exercise.md)
- [Two Categories of Trouble](two-categories-of-trouble.md)
- [North Star of the North Star](north-star-of-the-north-star.md)
