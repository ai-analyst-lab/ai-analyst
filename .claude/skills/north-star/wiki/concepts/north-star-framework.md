---
title: North Star Framework — A Product Management Model Around One Metric
type: concept
schema_version: 1
sources:
  - definitions/definition-p006-l0123-north-star-framework.md
  - concepts/concept-p005-l0083-three-languages-of-teams.md
  - concepts/concept-p006-l0134-three-purposes-of-nsf.md
  - concepts/concept-p007-l0153-nsf-tree-is-scaffold.md
  - concepts/concept-p019-l0436-what-nsf-is-not.md
related:
  - wiki/concepts/north-star-metric.md
  - wiki/concepts/inputs.md
  - wiki/concepts/the-work.md
  - wiki/concepts/nsf-vs-okrs-and-roadmaps.md
playbook_pages: [5, 6, 7, 19]
tier: 1
confidence: high
confidence_derivation: "Anchor definition atom tier 1, cross_extractor_agreement 2/2; 4 reconciled supporting concept atoms; not flagged by debates.md → high."
curator_status: approved
verified: true
created: 2026-05-26
updated: 2026-05-26
---

# North Star Framework — A Product Management Model Around One Metric

## TL;DR
The North Star Framework (NSF) is a product management model built around a single North Star Metric that best captures the value customers derive from the product. The framework is a tree-shaped scaffold of assumptions, beliefs, and causal relationships that, once assembled and field-tested, acts as a shared formula for the product's fundamental characteristics. Its purpose is to align teams that otherwise speak three different languages — customer, product, business — around one decision-making artifact.

## Decision rule
- Use the NSF when a product team needs to align distinct sub-languages (customer / product / business) around one decision-making artifact.
- Treat the framework as a hypothesis-carrier, not a deliverable; revisit assumptions as you learn.
- Do NOT treat the NSF as: a roadmap, a software development process, a prioritization framework, OKRs, MBOs, or a one-time fix [concept-p019-l0436-what-nsf-is-not].

## Detail
The playbook's canonical one-sentence definition: the NSF is "a product management model based on a single metric — your North Star Metric — that best captures the value customers derive from your product" [definition-p006-l0123-north-star-framework].

The framework exists because product teams typically speak three distinct languages — customer (needs/goals/delight), product (features/workflows/releases), and business (vision/differentiation/revenue/growth) — and need a shared artifact to translate among them [concept-p005-l0083-three-languages-of-teams].

The playbook assigns the NSF three explicit purposes: (1) prioritize and accelerate informed but decentralized decision-making, (2) help teams align and communicate, and (3) enable focus on impact and sustainable, product-led growth [concept-p006-l0134-three-purposes-of-nsf].

The visual representation of the NSF is a tree (NSM at the top, inputs beneath, opportunities and interventions below). This tree is not a static diagram — it is "a scaffold containing assumptions, beliefs, and causal relationships. Once you assemble and field test it, this framework acts as a formula for your company's and product's fundamental characteristics" [concept-p007-l0153-nsf-tree-is-scaffold]. That framing matters: the tree is a hypothesis carrier, and the team's job is to test, refine, and update it.

The playbook is also explicit about what the NSF is NOT: it is not a roadmap, not a software development process, not a prioritization framework, not OKRs, not MBOs, and not a one-time fix [concept-p019-l0436-what-nsf-is-not]. The framework can inform and work alongside several of these — but conflating them produces predictable failure modes (see [Three implementation traps](three-implementation-traps.md)).

## yaml-rules
```yaml
nsf_definition:
  centerpiece_metric: north_star_metric
  represents: customer_value
  is_a: product_management_model
nsf_purposes:
  - prioritize_decentralized_decision_making
  - align_and_communicate
  - enable_sustainable_product_led_growth
nsf_is_not:
  - roadmap
  - software_development_process
  - prioritization_framework
  - okrs
  - mbos
  - one_time_fix
nsf_is_a_scaffold_for:
  - assumptions
  - beliefs
  - causal_relationships
```

## Related
- [North Star Metric](north-star-metric.md)
- [Inputs](inputs.md)
- [The Work](the-work.md)
- [NSF vs. OKRs and Roadmaps](nsf-vs-okrs-and-roadmaps.md)
- [The North Star of the North Star](north-star-of-the-north-star.md)
