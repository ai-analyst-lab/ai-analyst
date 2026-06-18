---
title: Two Categories of Trouble — Shared Understanding vs. Common Traps
type: concept
schema_version: 1
sources:
  - concepts/concept-p034-l0770-two-categories-of-trouble.md
  - concepts/concept-p040-l0949-focus-on-inputs-not-nsm.md
  - concepts/concept-p041-l0965-look-for-real-product-boundaries.md
  - principles/principle-p039-l0925-dont-disregard-hard-to-measure.md
related:
  - wiki/concepts/beliefs.md
  - wiki/concepts/product-vision.md
  - wiki/concepts/key-value-exchanges.md
  - wiki/concepts/north-star-metric.md
playbook_pages: [34, 39, 40, 41]
tier: 1
confidence: high
confidence_derivation: "Anchor concept 3/3; supporting atoms 3/3 and 4/4 → high."
curator_status: approved
verified: true
created: 2026-05-26
updated: 2026-05-26
---

# Two Categories of Trouble — Shared Understanding vs. Common Traps

## TL;DR
When teams struggle with the NSF, their difficulties fall into two categories. Category 1: they lack shared understanding — fix by surfacing beliefs, connecting to product vision, and identifying key value exchanges. Category 2: they fall into common traps — jumping immediately to "can we measure that?" before scoping, fixating on the NSM rather than the inputs, insisting they need multiple NSMs, and letting dysfunction overwhelm them. The diagnosis routes the team to the right intervention.

## Decision rule
- Diagnose which category the team is in BEFORE applying interventions:
  - If team members give different answers to "what does the customer value?" → Category 1 (shared understanding)
  - If team can answer the customer-value question consistently but keeps getting stuck → Category 2 (common traps)
- For Category 1: run the three shared-understanding tools (beliefs, product vision, key value exchanges).
- For Category 2: identify which specific trap and apply the matching counter-rule below.

## Detail
Chapter 4 framing: "The difficulties teams experience often fall into one of the two categories below" [concept-p034-l0770-two-categories-of-trouble]. The two columns (fig-34-1) split troubleshooting into:

**Category 1 — Need shared understanding.** Fixed by:
- Surfacing [Beliefs](beliefs.md) — make tacit assumptions explicit before debating metrics
- Connecting to [Product Vision](product-vision.md) — use the existing vision as a catalyst
- Identifying [Key Value Exchanges](key-value-exchanges.md) — anchor in 3-6 essential value-deriving actions

**Category 2 — Common traps.** Four named traps and their counter-rules:

1. **Measurement-first thinking — "Can we measure that?" asked too early.** Counter-rule: "Though 'measurable' is a characteristic of a good North Star, avoid getting too concerned too soon with how you'll calculate the metric or its inputs" [principle-p039-l0925-dont-disregard-hard-to-measure]. Don't disregard a promising NSM concept because you aren't yet sure how to measure it; consider proxies (see [Proxy Metric](proxy-metric.md)).

2. **Fixating on the NSM instead of the inputs.** "It can be difficult to shift focus from driving the metric to driving the inputs. By design, the North Star Metric is not immediately actionable — the inputs are" [concept-p040-l0949-focus-on-inputs-not-nsm]. If a team fixates on moving the NSM, revisit the inputs; try the depth / breadth / frequency / efficiency heuristic to translate the formula into product terms.

3. **Insisting on multiple NSMs.** "Challenge the need for multiple North Star Metrics. Look for real boundaries in terms of users, their needs, and the strategy to meet those needs" [concept-p041-l0965-look-for-real-product-boundaries]. A large bank's consumer banking products may all share one NSM if customers experience the bank as a single product. Org-chart boundaries are not customer boundaries.

4. **Letting dysfunction overwhelm the team.** When organizational dysfunction blocks the framework, the answer is not to abandon the NSF — it is to use the NSF to surface the dysfunction (e.g., the team's inability to converge on inputs reveals an underlying disagreement about strategy).

The Category 1 vs. Category 2 split is diagnostic: applying shared-understanding tools to a team that has shared understanding but is stuck in a trap wastes time, and vice versa. Diagnose first, intervene second.

## yaml-rules
```yaml
two_categories_of_trouble:
  category_1_shared_understanding:
    diagnostic: team_gives_different_answers_to_what_does_customer_value
    tools:
      - surface_beliefs
      - connect_to_product_vision
      - identify_key_value_exchanges
  category_2_common_traps:
    diagnostic: team_aligned_on_customer_value_but_stuck
    traps:
      - id: measurement_first_thinking
        counter_rule: do_not_reject_nsm_at_q6_before_considering_proxy
      - id: fixating_on_nsm_not_inputs
        counter_rule: revisit_inputs_use_depth_breadth_frequency_efficiency
      - id: insisting_on_multiple_nsms
        counter_rule: look_for_real_product_boundaries_not_org_chart
      - id: letting_dysfunction_overwhelm
        counter_rule: use_nsf_to_surface_dysfunction
diagnose_before_intervening: true
```

## Related
- [Beliefs](beliefs.md)
- [Product Vision](product-vision.md)
- [Key Value Exchanges](key-value-exchanges.md)
- [North Star Metric](north-star-metric.md)
