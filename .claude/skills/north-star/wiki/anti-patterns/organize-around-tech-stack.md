---
title: Organizing Around Tech Stack Instead of Inputs
type: anti-pattern
schema_version: 1
sources:
  - raw/atoms/anti-patterns/anti-pattern-p048-l1137-organize-around-tech-stack.md
related:
  - wiki/anti-patterns/focusing-only-on-nsm-not-inputs.md
playbook_pages: [48, 57, 58]
anti_pattern_id: organize-around-tech-stack
severity: medium
tier: 1
confidence: high
confidence_derivation: "Source atom tier 1, confidence high; explicitly named as implementation trap #3 and reinforced by org-design tips on p. 58."
curator_status: approved
verified: true
contested: true
created: 2026-05-26
updated: 2026-05-26
---

# Organizing around tech stack instead of inputs

## TL;DR
Keeping team structure aligned to the tech stack or product areas — and optimizing for predictably shipping features — defeats the framework's intent to organize around input movement. The org chart, not the customer, ends up driving prioritization.

## Spot signals
- Teams are named after components or product areas, not inputs.
- Squad goals are framed as features shipped, not input movement.
- Reorganizations are driven by tech-stack changes rather than NSM strategy shifts.
- "Keeping people busy" or "predictable feature shipping" is the executive scorecard.

## Fix recipe
1. Consider letting a team (or group of teams) own a single input for an extended period — Amplitude calls this a pod (p. 58).
2. Organize to minimize handoffs and start together when possible (p. 58).
3. Resist letting current org structure force decisions about value and priority — organize around what is valuable, not workflows or technologies.
4. Reframe technical debt and non-feature work as drag on value-creation flow (p. 57), not as separate streams.

## Examples
- **Amplitude pods (p. 58):** Each pod owns a single NSM input for an extended period — the opposite of tech-stack-aligned squads.
- One of three implementation traps named together on p. 48. Commonly co-occurs with [features-to-inputs without opportunity](features-to-inputs-without-opportunity.md) and [no enabling constraints](no-enabling-constraints.md).
- **Contested:** Conway's-Law-aware practitioners argue tech-stack alignment is sometimes necessary for delivery velocity. See debate page.
