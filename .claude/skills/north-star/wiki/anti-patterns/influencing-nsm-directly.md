---
title: Influencing the NSM Directly
type: anti-pattern
schema_version: 1
sources:
  - raw/atoms/anti-patterns/anti-pattern-p009-l0194-influencing-nsm-directly.md
related:
  - wiki/concepts/north-star-metric.md
  - wiki/concepts/inputs.md
  - wiki/debates/nsm-one-level-out-of-reach.md
playbook_pages: [9, 32, 40]
anti_pattern_id: nsm-directly-influenced
severity: high
tier: 1
confidence: high
confidence_derivation: "Source atom tier 1, confidence high; stated as explicit rule and reinforced by attributed John Cutler quote on p. 9."
curator_status: approved
verified: true
contested: true
created: 2026-05-26
updated: 2026-05-26
---

# Influencing the NSM directly

## TL;DR
The NSM is designed to be one level out of reach — an outcome influenced through inputs, not a lever a single project can move on its own. If a feature ship or a campaign can move it next sprint, it's the wrong NSM. John Cutler's rule: "If you can move your North Star directly, it's probably not a good North Star."

## Spot signals
- A single feature ship or campaign can move the metric next sprint.
- The metric has only one input feeding it — there's nothing composite about it.
- Teams plan work directly against the NSM number rather than against inputs.
- There's no time-lag between team action and NSM movement.

## Fix recipe
1. Decompose the NSM into 3-5 inputs the team can influence (mind mapping, p. 27).
2. Move team execution against the inputs; let the NSM be the dependent variable that confirms the formula works.
3. If the metric still moves directly after decomposition, it's an input — promote a level up to find the real NSM.
4. Pressure-test with the Greenfield test (p. 32): can the team generate many opportunities to influence it indirectly?

## Examples
- This is a structural failure mode — sister anti-pattern to [ignoring inputs](focusing-only-on-nsm-not-inputs.md): one designs the NSM wrong, the other ignores the design.
- Contested: a minority position (CFO/RevOps in B2B) argues revenue or ARR *is* the NSM. See debate page on revenue-as-NSM.
