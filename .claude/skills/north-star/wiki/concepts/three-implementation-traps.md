---
title: Three Implementation Traps — Post-Definition Failure Modes
type: concept
schema_version: 1
sources:
  - concepts/concept-p048-l0133-three-implementation-traps.md
  - principles/principle-p048-l0136-define-opportunity-before-feature.md
  - concepts/concept-p054-l0263-make-the-nsm-tactical-and-visual.md
  - principles/principle-p058-l0373-organize-around-value-not-features.md
related:
  - wiki/concepts/levels-of-bets.md
  - wiki/concepts/squad-organization.md
  - wiki/concepts/bets.md
playbook_pages: [48, 54, 58]
tier: 1
confidence: high
confidence_derivation: "Anchor atom 3/3; supporting principle 3/3; concept atom 1/1 (singleton); principle 2/2; Debate 11 (Goodhart) and Debate 13 (org design) flag adjacent debates → high with contested flag."
contested: true
curator_status: approved
verified: true
created: 2026-05-26
updated: 2026-05-26
---

# Three Implementation Traps — Post-Definition Failure Modes

## TL;DR
Once a team has defined its NSM and inputs, three traps derail implementation: (1) connecting features to inputs without first defining the opportunity, (2) failing to use enabling constraints (WIP limits, timeboxes, force-ranked backlogs, structured reviews), and (3) organizing work around tech stack, product areas, or "keeping people busy" instead of around what drives the inputs. These are distinct from the "Two Categories of Trouble" — those block convergence ON the NSM; these block effective USE.

## Decision rule
- Always define the opportunity (L2 bet) BEFORE connecting a feature/intervention (L3) to an input [principle-p048-l0136-define-opportunity-before-feature].
- Use enabling constraints — WIP limits, timeboxes, force-ranked backlogs, structured reviews — to make the framework operational.
- Organize teams around what is valuable (inputs/NSM-aligned), not around features, workflows, touchpoints, technologies, or actors that don't align [principle-p058-l0373-organize-around-value-not-features].

## Detail
Chapter 6 framing: "Three ways that teams struggle to implement the North Star Framework and connect it to their work include: 1. They connect the features they're building to the inputs without first defining the opportunity..." [concept-p048-l0133-three-implementation-traps].

**Trap 1: Skipping the opportunity tier.** Teams connect L3 interventions (features) directly to inputs, skipping the L2 opportunity layer. The counter-rule: "They connect the features they're building to the inputs without first defining the opportunity" [principle-p048-l0136-define-opportunity-before-feature]. Without the opportunity layer, the team cannot tell whether the chosen feature is the best of several possible solutions or just the one someone proposed first. The opportunity is the leverage point; the intervention is one option for working that leverage point. Always define the opportunity first.

**Trap 2: Failing to use enabling constraints.** Without WIP limits, timeboxes, force-ranked backlogs, and structured reviews, the framework becomes a wall artifact rather than an operating system. The fix: make the NSM tactical and visual. "Making it tactical and visual can be extremely powerful... It helps your teams translate the North Star into something you do instead of something you did at a workshop" [concept-p054-l0263-make-the-nsm-tactical-and-visual]. Replace traditional requirements documents with succinct one-pagers that make each bet explicit and transparent (physical board or online whiteboard).

**Trap 3: Organizing work around the wrong primitive.** Teams organize around tech stack, product areas, touchpoints, or "keeping people busy" instead of around what drives the inputs. The counter-rule: "Organize your teams around what is valuable. Resist letting your current organizational structure force decisions about value and priorities. Be cautious about organizing around features, workflows, touchpoints, technologies, actors, etc. that do not align with your North Star and inputs" [principle-p058-l0373-organize-around-value-not-features]. See [Squad Organization](squad-organization.md) for the playbook's pod pattern.

These three traps are POST-definition failure modes. They sit downstream of the [Two Categories of Trouble](two-categories-of-trouble.md), which block teams from converging on a NSM in the first place.

> NOTE — CONTESTED: Trap 3 (organizing around value) is contested by the Team Topologies tradition (Skelton/Pais) and stable-team research, which argues stable stream-aligned teams outperform constantly-rewired value-chasing pods. See [Debate: Organize around value vs. stable teams](../debates/value-orientation-vs-stable-teams.md). Trap 2 is also adjacent to Debate 11 (Goodhart) — the playbook's enabling-constraints discipline partially defends against metric corruption but the defense is incomplete.

## yaml-rules
```yaml
three_implementation_traps:
  trap_1:
    name: skip_opportunity_tier
    pattern: connect_feature_to_input_without_defining_opportunity
    counter_rule: define_opportunity_before_feature
    enforces: four_tier_statement_exercise_during_execution
  trap_2:
    name: no_enabling_constraints
    pattern: framework_becomes_wall_artifact
    counter_rule: make_nsm_tactical_and_visual
    artifacts:
      - one_pagers_per_bet
      - physical_or_online_board
      - wip_limits
      - timeboxes
      - force_ranked_backlogs
      - structured_reviews
  trap_3:
    name: wrong_organizing_primitive
    pattern: organize_around_tech_stack_or_features_or_busy_work
    counter_rule: organize_around_value
    organize_around: [nsm, inputs]
    do_not_organize_around: [features, workflows, touchpoints, technologies, actors]
distinct_from: two_categories_of_trouble
trap_phase: post_definition
```

## Related
- [Levels of Bets](levels-of-bets.md)
- [Squad Organization](squad-organization.md)
- [Bets](bets.md)
