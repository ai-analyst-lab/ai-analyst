---
title: Beliefs — Surfacing Assumptions in the NSF Context
type: concept
schema_version: 1
sources:
  - definitions/definition-p035-l0788-beliefs.md
related:
  - wiki/concepts/two-categories-of-trouble.md
  - wiki/concepts/north-star-framework.md
  - wiki/concepts/product-vision.md
  - wiki/concepts/key-value-exchanges.md
playbook_pages: [35]
tier: 1
confidence: high
confidence_derivation: "Single anchor definition atom 3/3; not flagged in debates → high (single anchor but reconciled multi-extractor)."
curator_status: approved
verified: true
created: 2026-05-26
updated: 2026-05-26
---

# Beliefs — Surfacing Assumptions in the NSF Context

## TL;DR
In the North Star Framework, "beliefs" are the assumptions and biases each teammate brings to a problem — about customer value, causation, market direction, technology trends, competitors' strategy, and the value the team provides. Surfacing beliefs is part of creating shared understanding before converging on a North Star. The NSF tree itself is a scaffold of beliefs and assumptions; making those beliefs explicit is the first move when a team is stuck.

## Decision rule
- When a team disagrees about the NSM, surface beliefs explicitly before debating metrics.
- Treat the NSF tree as a hypothesis-carrier — each node is a belief that can be tested and revised.
- Use belief surfacing as one of three "shared understanding" tools alongside [Product Vision](product-vision.md) and [Key Value Exchanges](key-value-exchanges.md). See [Two Categories of Trouble](two-categories-of-trouble.md).

## Detail
Canonical definition: "Every person approaches a business problem or product opportunity with beliefs and biases. These often describe: Assumptions about what your customers value; Assumptions about causation or results of actions; Theories about where the market is going; Predictions about technology trends..." [definition-p035-l0788-beliefs].

The playbook enumerates six common belief categories:

1. **Assumptions about what your customers value** — what the team thinks the user is really there for
2. **Assumptions about causation or results of actions** — what the team thinks moves what
3. **Theories about where the market is going** — where the team thinks the industry is heading
4. **Predictions about technology trends** — what platform/capability shifts the team is betting on
5. **Beliefs about competitors' strategy** — what the team thinks competitors will and won't do
6. **Beliefs about the value the team provides** — what the team thinks it is uniquely good at

The reason for surfacing beliefs is operational: unstated beliefs become hidden assumptions in the NSF tree, and a tree built on hidden assumptions cannot be tested or refined. The NSF visual is explicitly framed as "a scaffold containing assumptions, beliefs, and causal relationships" (see [North Star Framework](north-star-framework.md)) — beliefs surfaced are beliefs that can be challenged, validated, or revised. Beliefs left tacit get smuggled in and protected.

Belief surfacing is one of the three "shared understanding" troubleshooting tools the playbook prescribes when teams struggle to converge — alongside connecting to product vision and identifying key value exchanges. See [Two Categories of Trouble](two-categories-of-trouble.md) for the full troubleshooting taxonomy.

## yaml-rules
```yaml
beliefs:
  definition: assumptions_and_biases_each_teammate_brings
  categories:
    - assumptions_about_customer_value
    - assumptions_about_causation
    - theories_about_market_direction
    - predictions_about_technology_trends
    - beliefs_about_competitors_strategy
    - beliefs_about_team_value_provided
  surface_when: team_disagrees_about_nsm
  surface_before: debating_metrics
shared_understanding_tools:
  - surfacing_beliefs
  - connecting_to_product_vision
  - identifying_key_value_exchanges
nsf_tree_is_a: scaffold_of_beliefs
tacit_belief_failure_mode: protected_assumption_in_the_tree
```

## Related
- [Two Categories of Trouble](two-categories-of-trouble.md)
- [North Star Framework](north-star-framework.md)
- [Product Vision](product-vision.md)
- [Key Value Exchanges](key-value-exchanges.md)
