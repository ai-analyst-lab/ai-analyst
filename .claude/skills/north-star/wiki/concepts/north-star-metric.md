---
title: North Star Metric — Leading Indicator of Customer Value
type: concept
schema_version: 1
sources:
  - definitions/definition-p008-l0160-north-star-metric.md
  - concepts/concept-p006-l0126-nsm-three-core-qualities.md
  - concepts/concept-p008-l0165-nsm-leading-indicator-relationship.md
  - concepts/concept-p011-l0260-one-nsm-per-product.md
  - principles/principle-p011-l0262-one-nsm-per-pnl.md
  - concepts/concept-p041-l0965-look-for-real-product-boundaries.md
related:
  - wiki/concepts/nsm-checklist.md
  - wiki/concepts/inputs.md
  - wiki/concepts/leading-vs-lagging.md
  - wiki/concepts/vanity-metric.md
  - wiki/concepts/games.md
playbook_pages: [6, 8, 9, 11, 41]
tier: 1
confidence: high
confidence_derivation: "Anchor definition atom 2/2; 5 reconciled supporting atoms with 2/2 or higher; contestation present (Debate 1: should early-stage have an NSM; Debate 2: one NSM vs. loops) but not contradicting the definition → high with contested flag."
contested: true
curator_status: approved
verified: true
created: 2026-05-26
updated: 2026-05-26
---

# North Star Metric — Leading Indicator of Customer Value

## TL;DR
The North Star Metric (NSM) is a single critical rate, count, or ratio that represents the product strategy. It is the heart of the NSF and a leading indicator of business results. A good NSM has three core qualities: (1) it represents user value, (2) it sits within product and marketing's sphere of influence, and (3) it leads revenue. One NSM per product, per P&L and customer base.

## Decision rule
- A candidate qualifies as an NSM iff it passes all seven checklist criteria (see [NSM Checklist](nsm-checklist.md)).
- If the candidate can be moved directly by a single team's work, it is disqualified — the NSM is by design one level out of reach (see [Inputs](inputs.md)).
- One NSM per product when the team contributes to a single P&L, has a single product development department, and serves a single customer base [principle-p011-l0262-one-nsm-per-pnl].
- When teams insist they need multiple NSMs, look for real product boundaries (users, needs, strategy), not org-chart boundaries [concept-p041-l0965-look-for-real-product-boundaries].

## Detail
The canonical playbook definition: "the heart of the North Star Framework is the North Star Metric, a single critical rate, count, or ratio that represents your product strategy" [definition-p008-l0160-north-star-metric].

The NSM is defined by three core qualities, introduced in Chapter 1: (1) it represents the value users get from the product, (2) it lies within product and marketing's sphere of influence, and (3) it is a leading indicator of revenue [concept-p006-l0126-nsm-three-core-qualities]. These three qualities are the first-pass framing; the seven-item diagnostic checklist in Chapter 2 elaborates them.

Functionally, the NSM "defines the relationship between the customer problems your product team is trying to solve and sustainable, long-term business results" — as the NSM changes, business results should change accordingly [concept-p008-l0165-nsm-leading-indicator-relationship].

A team should have one NSM per product when it operates within a single P&L, a single product development department, and a single customer base [concept-p011-l0260-one-nsm-per-product, principle-p011-l0262-one-nsm-per-pnl]. Larger enterprises with diverse divisions or distinct customer bases may have different NSMs per division. When teams push back and insist they need multiple NSMs, the resolution test is: look for real product boundaries in terms of users, needs, and strategy — not balance-sheet or org-chart boundaries. A large bank's consumer banking products may share one NSM if customers experience the bank as one product [concept-p041-l0965-look-for-real-product-boundaries].

> NOTE — CONTESTED: Several practitioners disagree with the "one NSM" framing. The Reforge growth-loops tradition argues mature products run on multiple compounding loops, each with its own diagnostic metric; B2B operators argue revenue (ARR/NRR) IS the NSM in contract-driven businesses. The playbook's position is defensible but not universally held — see [Debate: One NSM vs. loops](../debates/one-nsm-vs-loops.md) and [Debate: B2B revenue as NSM](../debates/b2b-revenue-as-nsm.md).

## yaml-rules
```yaml
nsm_definition:
  form: rate_or_count_or_ratio
  count: 1
  represents: product_strategy
  is_a: leading_indicator
nsm_three_core_qualities:
  - represents_customer_value
  - within_product_and_marketing_sphere_of_influence
  - leading_indicator_of_revenue
one_nsm_per_product_when:
  - single_pnl: true
  - single_product_development_department: true
  - single_customer_base: true
multiple_nsms_warranted_when:
  - distinct_divisions: true
  - distinct_customer_bases: true
disqualifying_signals:
  - directly_movable_by_single_input
  - lagging_only
  - vanity_metric
```

## Related
- [NSM Checklist (the seven qualifying questions)](nsm-checklist.md)
- [Inputs](inputs.md)
- [Leading vs. Lagging Indicators](leading-vs-lagging.md)
- [Vanity Metric](vanity-metric.md)
- [The Game (attention / transaction / productivity)](games.md)
