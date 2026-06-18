---
title: Inputs at the Wrong Granularity
type: anti-pattern
schema_version: 1
sources:
  - raw/atoms/anti-patterns/anti-pattern-p032-l0706-inputs-wrong-granularity.md
related:
  - wiki/concepts/inputs.md
  - wiki/concepts/input-tests-greenfield-and-roadmap.md
  - wiki/concepts/input-tests-greenfield-and-roadmap.md
  - wiki/anti-patterns/focusing-only-on-nsm-not-inputs.md
playbook_pages: [27, 32]
anti_pattern_id: inputs-wrong-granularity
severity: medium
tier: 1
confidence: high
confidence_derivation: "Source atom tier 1, confidence high; direct treatment with two worked examples and two named diagnostic tests."
curator_status: approved
verified: true
created: 2026-05-26
updated: 2026-05-26
---

# Inputs at the wrong granularity

## TL;DR
Inputs that are too broad don't focus team effort; inputs that are too narrow over-constrain the solution space. Both fail to give teams an actionable lever. The playbook's example: "satisfied customers" is too broad, "positive reviews on social media" is too narrow.

## Spot signals
- **Too broad:** the team brainstorms dozens of opportunities for the input, all over the map (Greenfield test signal: "swimming in ideas — many overly broad").
- **Too narrow:** the team can only think of one or two ways to influence the input; the input prescribes the solution.
- The input also doubles as something close to the NSM (too lagging).
- Teams can't make the input actionable in a single squad's quarter.

## Fix recipe
1. Run **Input Test 1 — the Greenfield test** (p. 32): "How many opportunities can you come up with in two minutes to influence this input?" Too few → too narrow. Too many overly-broad → too broad. Use the opportunity-statement template.
2. Run **Input Test 2 — the roadmap check** (p. 32): map current initiatives to the input. Clear links = good. No links = missing a factor of your NSM (or working on something not valuable).
3. Re-run mind-mapping (p. 27-31) to find the right level between high-level themes and prescriptive features.

## Examples
- **Too broad:** "Satisfied customers" — no team can act on this directly without sub-decomposition.
- **Too narrow:** "Positive reviews on social media" — prescribes the channel and the tactic; eliminates the solution space.
- Related: [Focusing only on the NSM, not the inputs](focusing-only-on-nsm-not-inputs.md) — when inputs are wrong-grained, teams often retreat to NSM-only thinking.
