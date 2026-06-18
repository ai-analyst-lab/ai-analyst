---
title: Refusing to Change an NSM That Has Stopped Working
type: anti-pattern
schema_version: 1
sources:
  - raw/atoms/anti-patterns/anti-pattern-p045-l1058-attachment-to-nsm.md
  - raw/atoms/case-study-fragments/case-study-fragment-p045-l1063-amplitude-nsm-evolution.md
related:
  - wiki/anti-patterns/cycle-of-doubt-paralysis.md
  - wiki/cases/amplitude.md
playbook_pages: [45]
anti_pattern_id: attachment-to-stale-nsm
severity: medium
tier: 1
confidence: high
confidence_derivation: "Source atom tier 1, confidence high; direct treatment with Ted Clark's diagnostic rule and John Cutler's attribution; reinforced by Amplitude's own NSM revision case."
curator_status: approved
verified: true
created: 2026-05-26
updated: 2026-05-26
---

# Refusing to change an NSM that has stopped working

## TL;DR
When the NSM no longer directionally predicts revenue — because market, strategy, or stage has shifted — teams often refuse to revise it out of attachment. The framework loses its predictive power and becomes a relic. John Cutler: changing the NSM "is often one of the hardest things for companies."

## Spot signals
- NSM is flat while revenue is moving (or vice versa) for multiple quarters.
- Strategy shifts have happened (new market, new customer segment, productization change) but the NSM hasn't been revisited.
- The team defends the NSM on identity grounds ("this has always been our metric") rather than on predictive grounds.
- Bets and squads still ladder up to the old NSM even though strategy moved.

## Fix recipe
1. Adopt Ted Clark's check explicitly: at every quarterly review, ask "is the NSM still directionally indicating where revenue is going?" If not, revise.
2. Embrace that NSMs SHOULD change at strategic inflection points — see Amplitude's own NSM revision when they moved upmarket (p. 45).
3. Treat NSM revision as a planned, transparent event with insight, humility, and communication — not a failure.
4. When strategy shifts, also shift the bets teams prioritize and the metrics they measure success by.

## Examples
- **Amplitude (p. 45):** Revised their NSM when they moved upmarket — strategic inflection point triggered a planned, transparent revision.
- Opposite trap: [Cycle of doubt paralysis](cycle-of-doubt-paralysis.md) — the pre-launch version of NSM commitment problems.
