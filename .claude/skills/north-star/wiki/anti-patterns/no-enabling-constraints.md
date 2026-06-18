---
title: Failing to Use Enabling Constraints
type: anti-pattern
schema_version: 1
sources:
  - raw/atoms/anti-patterns/anti-pattern-p048-l1136-no-enabling-constraints.md
related:
  - wiki/concepts/levels-of-bets.md
  - wiki/anti-patterns/features-to-inputs-without-opportunity.md
playbook_pages: [48, 51, 52, 55]
anti_pattern_id: no-enabling-constraints
severity: medium
tier: 1
confidence: high
confidence_derivation: "Source atom tier 1, confidence high; explicitly named as implementation trap #2 in Chapter 6's 'Things to watch out for'."
curator_status: approved
verified: true
created: 2026-05-26
updated: 2026-05-26
---

# Failing to use enabling constraints

## TL;DR
Without WIP limits, timeboxes, force-ranked backlogs, and structured reviews, teams "move around" without producing the sense-and-respond loops the framework relies on. Constraints aren't bureaucracy — they're the mechanism that turns activity into learning.

## Spot signals
- Backlogs are unranked or ranked by recency rather than expected NSM impact.
- Multiple bets are in-flight simultaneously per team with no WIP cap.
- Sprint reviews don't tie completed work back to input movement.
- Teams report shipping a lot but cannot point to input deltas.

## Fix recipe
1. Adopt WIP limits per squad — usually one Level 1 bet with a handful of supporting Level 2/3 bets (p. 51-52).
2. Force-rank the backlog by expected NSM impact (input influence × opportunity likelihood — p. 55).
3. Shift kanban language from "to do, doing, done" to "focus on next, focusing, review" and "to try, trying, review" (p. 51).
4. Build structured review checkpoints into every bet completion — including learning, not just delivery.

## Examples
- One of three implementation traps named together on p. 48. Commonly co-occurs with [features-to-inputs without opportunity](features-to-inputs-without-opportunity.md) and [organize around tech stack](organize-around-tech-stack.md).
