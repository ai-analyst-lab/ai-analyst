---
title: Jumping to "Can We Measure That?" Too Soon
type: anti-pattern
schema_version: 1
sources:
  - raw/atoms/anti-patterns/anti-pattern-p039-l0923-jumping-to-can-we-measure.md
related:
  - wiki/concepts/nsm-checklist.md
  - wiki/anti-patterns/unmeasurable-or-abstract-nsm.md
playbook_pages: [34, 39, 40]
anti_pattern_id: jumping-to-measurement-too-soon
severity: high
tier: 1
confidence: high
confidence_derivation: "Source atom tier 1, confidence high; listed as trap #1 in the Chapter 4 troubleshooting overview AND given a dedicated section with Ted Clark pull-quote."
curator_status: approved
verified: true
created: 2026-05-26
updated: 2026-05-26
---

# Jumping to "Can we measure that?" too soon

## TL;DR
Disqualifying NSM candidates in the early brainstorm because you don't yet know how to measure them produces narrow, data-shaped metrics instead of strategy-shaped ones. Measurability is a late-stage gate (Checklist Q6), not an early-stage filter. Especially common in companies that have struggled to instrument customer success.

## Spot signals
- Workshop participants ask "how would we measure that?" within the first 5 minutes of brainstorming candidates.
- Strong strategic concepts get rejected because instrumentation doesn't exist today.
- The surviving NSM candidates all look like data the team already collects, rather than the strategy the team actually wants to express.
- The team "jumps straight to the solution" instead of stepping back to see the user's goals (Ted Clark).

## Fix recipe
1. Defer measurability questions: brainstorm strategy-shaped candidates first, then ask "how could we measure this with light instrumentation?"
2. Apply Hubbard's principle (*How to Measure Anything*, cited p. 40): if you know almost nothing, almost any data will reduce uncertainty significantly — you don't need perfect measurement to start.
3. Even imperfect measurement is fine to begin; refine instrumentation as you iterate the NSM.
4. Pair with Checklist Q6 (measurable) as the late-stage gate, not the early-stage filter.

## Examples
- Opposite trap: [Abstract or unmeasurable NSM](unmeasurable-or-abstract-nsm.md) — over-correcting in the other direction and choosing a metric you can never instrument. Both errors live on the same axis: timing of the measurability question.
