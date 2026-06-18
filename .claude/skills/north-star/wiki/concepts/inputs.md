---
title: Inputs — Independent Variables That Move the NSM
type: concept
schema_version: 1
sources:
  - definitions/definition-p008-l0174-input-metric.md
  - concepts/concept-p008-l0184-inputs-vary-by-context.md
  - concepts/concept-p009-l0190-inputs-independent-nsm-dependent.md
  - principles/principle-p009-l0194-never-influence-nsm-directly.md
  - concepts/concept-p027-l0603-inputs-are-leverage-points.md
  - concepts/concept-p032-l0705-inputs-too-broad-too-narrow.md
  - principles/principle-p027-l0611-name-and-define-inputs-too.md
  - concepts/concept-p040-l0949-focus-on-inputs-not-nsm.md
related:
  - wiki/concepts/north-star-metric.md
  - wiki/concepts/input-tests-greenfield-and-roadmap.md
  - wiki/concepts/system-health-indicator.md
  - wiki/concepts/statement-exercise.md
playbook_pages: [8, 9, 27, 32, 40]
tier: 1
confidence: high
confidence_derivation: "Anchor definition atom 2/2; principle and 6 concept atoms reconciled with 2/2-5/5 agreement; Debate 5 (one-level-out-of-reach) flags an epistemic critique but does not contradict the operational rule → high with contested flag."
contested: true
curator_status: approved
verified: true
created: 2026-05-26
updated: 2026-05-26
---

# Inputs — Independent Variables That Move the NSM

## TL;DR
Inputs are a small set of influential, complementary factors that most directly affect the North Star Metric. Inputs are independent variables — the tools product and marketing teams deploy in daily work to influence the NSM. The NSM is the dependent variable: its value depends on changes in the inputs. Teams move inputs, not the NSM directly. Inputs vary greatly by industry, business model, and product; the NSM is a function of its inputs.

## Decision rule
- Never try to influence the North Star Metric directly [principle-p009-l0194-never-influence-nsm-directly]. Move inputs.
- Each input must have BOTH a pithy name AND a precise definition, just like the NSM [principle-p027-l0611-name-and-define-inputs-too].
- An input is too broad if it is hard to focus effort and measure impact (e.g., "satisfied customers"); too narrow if it constrains solutions (e.g., "positive reviews on social media") [concept-p032-l0705-inputs-too-broad-too-narrow]. Test with the Greenfield test and the roadmap check.
- If a team fixates on moving the NSM directly, revisit the inputs and try the depth / breadth / frequency / efficiency heuristic [concept-p040-l0949-focus-on-inputs-not-nsm].

## Detail
Canonical definition: "North Star inputs are a small set of influential, complementary factors that you believe most directly affect your North Star Metric" [definition-p008-l0174-input-metric].

Inputs are independent variables; the NSM is the dependent variable. "Inputs are the tools product and marketing teams deploy in their day to day work to influence the North Star. Inputs are independent variables. The North Star Metric is an outcome, a dependent variable, meaning its value depends on changes in your inputs" [concept-p009-l0190-inputs-independent-nsm-dependent].

This is why the NSM is "one level out of reach" — a good NSM correlates with top-level business outcomes but is hard for any one team to move directly given the multitude of inputs and time lag. Teams are better served moving a single component (an input) that ladders up to the larger metric and is more of a leading indicator of impact [concept-p027-l0603-inputs-are-leverage-points]. By design, the NSM is not immediately actionable — the inputs are [concept-p040-l0949-focus-on-inputs-not-nsm].

Inputs are not portable across companies. They "vary greatly by industry, business model, and a product's unique characteristics. The trick is to identify the key factors that contribute to the North Star Metric for your business. We view the North Star Metric as a function of key inputs that are both descriptive and actionable" [concept-p008-l0184-inputs-vary-by-context].

Two failure modes during input design (the Goldilocks framing): inputs that are too broad or lagging make it hard to focus effort and measure impact; inputs that are too specific make it hard to find innovative solutions. The playbook offers two diagnostic tests — the [Greenfield test and the roadmap check](input-tests-greenfield-and-roadmap.md) — to pressure-test input scope [concept-p032-l0705-inputs-too-broad-too-narrow].

Inputs deserve the same care as the NSM in naming and definition: each input must have both a pithy name AND a precise definition explaining exactly how it will be measured [principle-p027-l0611-name-and-define-inputs-too].

> NOTE — CONTESTED: Some practitioners (Andrew Chen lineage, outcome-oriented PM voices) argue the "never influence NSM directly" rule, taken literally, can produce a hidden feature factory at the input layer — teams ship features whose only defense is "it moves an input," without testing whether the input-NSM causal coupling holds. See [Debate: One level out of reach](../debates/nsm-one-level-out-of-reach.md).

## yaml-rules
```yaml
inputs_definition:
  count: 3_to_5_typical
  property: independent_variables
  vary_by: [industry, business_model, product]
nsm_relationship:
  nsm_is: dependent_variable
  nsm_function_of: inputs
move_what:
  move: inputs
  never_move_directly: north_star_metric
input_naming:
  requires_name: true
  requires_definition: true
input_scope_failures:
  too_broad_signal: hard_to_focus_effort
  too_narrow_signal: constrains_solutions
input_tests:
  - greenfield_test
  - roadmap_check
```

## Related
- [North Star Metric](north-star-metric.md)
- [Input Tests: Greenfield and Roadmap Check](input-tests-greenfield-and-roadmap.md)
- [System Health Indicator (specialized input)](system-health-indicator.md)
- [Statement Exercise (NSM → Inputs → Opportunities → Interventions)](statement-exercise.md)
