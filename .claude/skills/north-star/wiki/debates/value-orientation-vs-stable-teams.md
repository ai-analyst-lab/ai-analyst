---
title: Organize around value vs. organize around stable teams
type: debate
schema_version: 1
sources:
  - synthesis/debates.md
  - raw/atoms/principles/principle-p058-l0373-organize-around-value-not-features.md
  - raw/atoms/concepts/concept-p058-l0367-no-optimal-org-design.md
  - raw/atoms/anti-patterns/anti-pattern-p048-l1137-organize-around-tech-stack.md
  - raw/atoms/principles/principle-p057-l0360-reframe-tech-debt-as-drag.md
related:
  - wiki/concepts/squad-organization.md
  - wiki/anti-patterns/organize-around-tech-stack.md
playbook_pages: [58, 48, 57]
tier: 2
confidence: low
confidence_derivation: "debate-mapper Debate 13. Counter-research located no Tier-A/B Team Topologies critique within budget. Skelton/Pais's book is canonical but not specifically a critique of NSF organizing logic."
contested: "Should teams be organized around the NSM's current value chain (and reorganized when inputs shift), or around long-lived stream-aligned teams whose stability is itself a value driver?"
current_consensus: weak
curator_status: approved
verified: false
created: 2026-05-26
updated: 2026-05-26
---

# Organize around value vs. organize around stable teams

## TL;DR
The playbook says organize teams around value; resist letting org structure force priorities; avoid organizing around features, workflows, technologies, or actors that don't align with NSM and inputs. The Team Topologies tradition (Skelton, Pais) and stable-team agile literature argue team stability is itself a value driver — velocity, code ownership, on-call quality, and trust all degrade when teams re-form around shifting value areas. Both reject organizing purely around tech stack or org-chart accident.

## Where they agree
- Organizing around features, tech stack, or actors that don't align with value is a failure mode [anti-pattern-p048-l1137-organize-around-tech-stack].
- There is no single optimal org design [concept-p058-l0367-no-optimal-org-design].
- Tech debt is a drag on velocity and should be reframed, not hidden [principle-p057-l0360-reframe-tech-debt-as-drag].
- Teams that produce no measurable value are misaligned regardless of how stable they are.

## Arguments for the playbook stance (value-orientation)
- Organize around what is valuable, not around features or tech stacks [principle-p058-l0373-organize-around-value-not-features].
- The NSM's input layer reveals where value actually accrues; team boundaries should follow that revelation.
- Stable teams aligned to a stale value chain produce the legacy-team failure mode: well-coordinated, well-trusting, building the wrong thing.
- The "no optimal org design" atom is honest about tradeoffs and explicitly allows that organizing logic should follow the value chain, not vice versa.
- The framework's worked examples show org redesigns following NSM-tree clarification, not preceding it.

## Arguments against (Team Topologies, stable-team agile)
- Matthew Skelton and Manuel Pais (*Team Topologies*) argue stream-aligned teams with long-lived ownership outperform value-chasing pods that re-form quarterly.
- Allen Holub and much of the agile literature: shipping velocity, code ownership, on-call quality, and team trust all degrade when teams re-form around shifting value areas.
- The strong version: reorganizing around the NSM every time inputs shift produces a constantly-rewired org with low cohesion, and the rewiring cost exceeds the alignment benefit.
- Cognitive-load-based team design (Team Topologies' core argument) requires team stability — the team must learn the system it owns, which takes months, not the duration of an input-shift cycle.
- The playbook's position can read as license for frequent reorganization, which is itself a known anti-pattern in the agile literature.
- **No Tier-A/B essay specifically critiquing the NSF's organizing logic from a Team Topologies perspective was located within counter-research's budget.** Skelton and Pais's book is canonical in the team-design literature but does not target the NSF framing.

## Current consensus
Weak — leans Team Topologies on stability discipline, leans playbook on value-discovery cadence. The two positions are reconcilable: the playbook does not require reorganizing every quarter, and Team Topologies does not require teams to never change boundaries. The substantive question is the default cadence — how often the org should reshape itself to track the NSM tree. The playbook implies "whenever the tree clarifies"; Team Topologies implies "as rarely as possible, and only after careful cognitive-load analysis." A wiki-level improvement: explicitly recommend that NSF-driven reorganizations be rare events (annual at most), and that the NSM-tree be designed to fit the existing stream-aligned team structure where possible rather than forcing teams to chase moving input boundaries.

## Why this matters
Determines whether reorgs are a frequent NSF-driven activity or a rare and reluctant event. Affects shipping velocity, team trust, on-call quality, and the time-to-productivity of new hires.

## See also
- [Squad organization](../concepts/squad-organization.md)
- [Organize around tech stack (anti-pattern)](../anti-patterns/organize-around-tech-stack.md)
