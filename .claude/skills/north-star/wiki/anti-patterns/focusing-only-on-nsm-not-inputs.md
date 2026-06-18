---
title: Focusing Only on the NSM, Not the Inputs
type: anti-pattern
schema_version: 1
sources:
  - raw/atoms/anti-patterns/anti-pattern-p040-l0947-focusing-only-on-nsm-not-inputs.md
  - raw/atoms/case-study-fragments/case-study-fragment-p012-l0271-burger-king-three-inputs.md
  - raw/atoms/case-study-fragments/case-study-fragment-p012-l0286-burger-king-squads-trace-inputs.md
related:
  - wiki/concepts/inputs.md
  - wiki/anti-patterns/influencing-nsm-directly.md
  - wiki/anti-patterns/inputs-wrong-granularity.md
  - wiki/cases/burger-king.md
playbook_pages: [27, 34, 40]
anti_pattern_id: ignoring-inputs
severity: high
tier: 1
confidence: high
confidence_derivation: "Source atom tier 1, confidence high; listed as trap #2 in Chapter 4 with dedicated section and explicit fix."
curator_status: approved
verified: true
created: 2026-05-26
updated: 2026-05-26
---

# Focusing only on the NSM, not the inputs

## TL;DR
The NSM is intentionally one level out of reach. Teams that fixate on the NSM number and ignore inputs have no actionable lever and stall — they ask "the NSM is flat, what do we do?" without naming which input is flat. The inputs are where the work happens.

## Spot signals
- Standups and reviews only mention the NSM number, never inputs.
- Roadmap items map to the NSM with no input layer in between.
- Teams report "the NSM is flat, what do we do?" without naming which input is flat.
- Squad goals are written against the NSM instead of against a single input.

## Fix recipe
1. Revisit inputs: run mind-mapping (p. 27) to surface the formula of inputs that produce the metric.
2. Use the depth/breadth/frequency/efficiency heuristic (p. 40) to translate the NSM into input categories.
3. Reorganize execution around inputs: each squad/team owns an input, not the NSM (Burger King pattern).
4. Define inputs at the right granularity (Greenfield + roadmap-check tests, p. 32).

## Examples
- **Burger King squads (p. 12):** Each squad owns one input (acquisition, frequency, retention via mobile coupons). The NSM is never the unit of squad-level execution.
- Sibling failure: [Influencing the NSM directly](influencing-nsm-directly.md) is the design-time version of this anti-pattern; this is the execution-time version.
