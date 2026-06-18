---
title: Levels of Bets — Time-Horizon Categorization (L0-L3)
type: concept
schema_version: 1
sources:
  - definitions/definition-p051-l0187-levels-of-bets.md
  - definitions/definition-p051-l0195-level-0-bet.md
  - definitions/definition-p051-l0196-level-1-bet.md
  - definitions/definition-p051-l0197-level-2-bet.md
  - definitions/definition-p051-l0198-level-3-bet.md
  - principles/principle-p048-l0136-define-opportunity-before-feature.md
  - concepts/concept-p048-l0133-three-implementation-traps.md
related:
  - wiki/concepts/bets.md
  - wiki/concepts/statement-exercise.md
  - wiki/concepts/three-implementation-traps.md
  - wiki/concepts/north-star-metric.md
  - wiki/concepts/inputs.md
playbook_pages: [48, 51]
tier: 1
confidence: high
confidence_derivation: "5 anchor atoms reconciled at 2/2-4/4; Debate 8 (Levels-of-Bets vs. Opportunity Solution Trees) flags alternative framework → high with contested flag."
contested: true
curator_status: approved
verified: true
created: 2026-05-26
updated: 2026-05-26
---

# Levels of Bets — Time-Horizon Categorization (L0-L3)

## TL;DR
The Levels of Bets model categorizes bets into four levels (0-3) by time horizon. Level 0 (Years, RISKY/UNCERTAIN) connects the NSM to company/product success. Level 1 (1-3 quarters) connects inputs to the NSM — the input-assumption layer. Level 2 (1-3 months) represents opportunities to influence an input. Level 3 (1-3 weeks, SAFE/CERTAIN) represents interventions — work executable in a sprint. Smaller bets ladder up to larger bets; larger bets (L0/L1) are closely associated with the NSM and inputs.

## Decision rule
- Place every bet at one of four levels (L0, L1, L2, L3) by time horizon [definition-p051-l0187-levels-of-bets].
- L0 and L1 bets MUST connect explicitly to the NSM and inputs respectively; if they don't, the bet is mis-categorized or the framework is not yet operational.
- L2 bets (opportunities) and L3 bets (interventions) must connect through a level above them; never jump from an L3 intervention directly to an input or NSM [principle-p048-l0136-define-opportunity-before-feature].
- Define the opportunity (L2) BEFORE connecting features (L3) to inputs.

## Detail
**Umbrella definition.** "Teams can categorize bets into levels, and associate a specific time frame for feedback, execution, or review. Each level is related — you knock out the smaller bets to get to the larger bets. And those larger level bets — Level 0 and 1 — are closely associated with your North Star Metric and inputs" [definition-p051-l0187-levels-of-bets].

**Level 0 — Years (RISKY/UNCERTAIN).** Connects the NSM to the success of the company and product. Example: "If we increase digital transactions, our total annual sales will increase" [definition-p051-l0195-level-0-bet]. This is the highest-uncertainty bet — that the NSM itself is the right thing to grow.

**Level 1 — 1 to 3 quarters (Input Assumptions).** Connects inputs to the NSM. Example: "If we improve the rate at which new users register for our digital applications, we will increase total digital transactions" [definition-p051-l0196-level-1-bet]. This is the bet that a chosen input causally moves the NSM.

**Level 2 — 1 to 3 months (Opportunities).** Opportunities to influence an input. Example: "If we make it really appealing for new users to sign up for our mobile product, we'll increase digital registrations" [definition-p051-l0197-level-2-bet]. L2 bets map directly to the "opportunities" tier of the [Statement Exercise](statement-exercise.md).

**Level 3 — 1 to 3 weeks (SAFE/CERTAIN, Interventions).** Interventions to influence opportunities — work executable in a sprint. Example: "If we add a feature where the app includes special mobile-only discounts, it will be more appealing for users to register" [definition-p051-l0198-level-3-bet]. L3 bets map to the "interventions" tier of the Statement Exercise.

**The ladder rule.** Smaller bets must ladder up. An L3 intervention exists to deliver an L2 opportunity; an L2 opportunity exists to move an L1 input; the L1 input bet exists to move the L0 NSM. Skipping a level is the first of the three implementation traps: "They connect the features they're building to the inputs without first defining the opportunity" [principle-p048-l0136-define-opportunity-before-feature, concept-p048-l0133-three-implementation-traps]. See [Three Implementation Traps](three-implementation-traps.md).

> NOTE — CONTESTED: The Continuous Discovery / Opportunity Solution Tree tradition (Teresa Torres) organizes the same conceptual territory by customer opportunity rather than by time horizon. Each framework has different review cadences and artifacts. See [Debate: Levels of bets vs. OST](../debates/levels-of-bets-vs-ost.md).

## yaml-rules
```yaml
levels_of_bets:
  level_0:
    horizon: years
    uncertainty: risky_uncertain
    connects: nsm_to_company_and_product_success
    example: "If we increase digital transactions, our total annual sales will increase"
  level_1:
    horizon: 1_to_3_quarters
    uncertainty: high
    connects: inputs_to_nsm
    statement_tier_alias: input_assumption
    example: "If we improve registration rate, we will increase total digital transactions"
  level_2:
    horizon: 1_to_3_months
    uncertainty: medium
    connects: opportunities_to_inputs
    statement_tier_alias: opportunity
    example: "If we make signup more appealing, we'll increase digital registrations"
  level_3:
    horizon: 1_to_3_weeks
    uncertainty: safe_certain
    connects: interventions_to_opportunities
    statement_tier_alias: intervention
    example: "If we add mobile-only discounts, signup will be more appealing"
ladder_rule:
  must_ladder_up: true
  forbidden: jumping_from_l3_to_input_or_nsm
  define_opportunity_before_feature: true
```

## Related
- [Bets](bets.md)
- [Statement Exercise](statement-exercise.md)
- [Three Implementation Traps](three-implementation-traps.md)
- [North Star Metric](north-star-metric.md)
- [Inputs](inputs.md)
