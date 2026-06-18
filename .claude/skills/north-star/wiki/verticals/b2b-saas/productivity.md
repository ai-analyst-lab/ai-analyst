---
title: B2B SaaS — Productivity Game
type: vertical
schema_version: 1
sources:
  - raw/synthesis/vertical-applications.md
  - raw/atoms/case-study-fragments/case-study-fragment-p026-l0591-amplitude-wlu-nsm.md
  - raw/atoms/case-study-fragments/case-study-fragment-p026-l0594-amplitude-threshold-rationale.md
  - raw/atoms/case-study-fragments/case-study-fragment-p044-l1043-amplitude-culture-integration.md
  - raw/atoms/case-study-fragments/case-study-fragment-p045-l1063-amplitude-nsm-evolution.md
related:
  - wiki/concepts/games.md
  - wiki/concepts/north-star-metric.md
  - wiki/concepts/plg-and-feature-factories.md
  - wiki/cases/amplitude.md
  - wiki/anti-patterns/lagging-indicator-as-nsm.md
  - wiki/anti-patterns/vanity-metric-as-nsm.md
playbook_pages: [10, 13, 26, 44, 45]
industry: b2b-saas
game: productivity
vertical_id: b2b-saas-productivity
tier: 2
confidence: medium
confidence_derivation: "Synthesis-derived from the playbook's Amplitude WLU worked example (canonical productivity-game NSM grammar) plus the three-games framing (p.10). Pattern generalization is inferential — flagged medium not high."
curator_status: approved
verified: true
representative_cases: [case-amplitude]
created: 2026-05-26
updated: 2026-05-26
priors:
  vertical_id: b2b-saas-productivity
  industry: b2b-saas
  game: productivity
  typical_nsm_grain: per-user-per-week
  typical_nsm_type: count_with_collaboration_threshold
  common_input_categories: [activation, depth, collaboration, account_expansion, retention_friction]
  common_anti_patterns: [lagging-indicator-as-nsm, vanity-metric-as-nsm, insisting-on-multiple-nsms]
  common_traps: [arr_as_nsm, dau_default, one_nsm_all_tiers, registered_users_vanity, sales_motion_coupling]
  example_case_ids: [case-amplitude]
  classification_signals:
    - "Collaboration / workflow / knowledge tool"
    - "Seat-based or usage-tiered billing"
    - "Async work cadence, weekly or longer"
    - "Value compounds when teammates are pulled in"
  confidence_envelope:
    tier: 2
    confidence: medium
    curator_status: approved
    verified: false
    notes: "Synthesis-derived. Amplitude is the only fully-instrumented anchor case."
---

# B2B SaaS — Productivity Game

## TL;DR

For collaboration, workflow, and knowledge tools (Notion-style, Asana-style, Linear-style, Amplitude itself): characteristic NSM is a per-active-user-per-week count of value-delivering work artifacts, typically gated by a collaboration or completion threshold. Common input categories: activation, depth, collaboration, account expansion, retention friction. Top trap: defaulting to ARR/MRR or DAU instead of a leading work-output measure.

## Why this vertical plays the Productivity game

The customer is hiring the product to *get work done* and to coordinate that work across teammates. The lagging business outcome (seat expansion, renewal, ARR) is downstream of whether individual users complete meaningful work and pull collaborators into the product. Transaction overtones appear in seat-based or usage-tiered billing, but the *causal* game is productivity: more useful work shipped → more seats added → more revenue. The playbook's Amplitude WLU case (p.26) is the canonical worked example of this pattern.

## Characteristic NSM shape

`count of [active users] who [produced / completed a work artifact] [shared with / consumed by ≥N others] in the past [7-30 days]`

The 7-day window is preferred when work cadence is weekly; 30-day for slower-cadence enterprise tools. The collaboration / threshold gate is what separates a productivity NSM from vanity active-user counts.

## Common inputs

- **Activation** — new-user time-to-first-value-moment
- **Depth** — variety of work-types or features touched per user
- **Collaboration** — work artifacts shared, edited, or consumed by teammates
- **Account expansion** — new seats added, new teams onboarded per workspace
- **Retention friction** — week-over-week active workspace count

## Vertical-specific traps

- **ARR/MRR as NSM** — lagging; see [`lagging-indicator-as-nsm`](../../anti-patterns/lagging-indicator-as-nsm.md)
- **DAU defaulting** — work is asynchronous; weekly cadence is the true rhythm
- **One NSM stretched across SMB + Enterprise tiers** — value mechanics differ (individual productivity vs team coordination); these may functionally be two products
- **Registered-users / signups vanity** — see [`vanity-metric-as-nsm`](../../anti-patterns/vanity-metric-as-nsm.md)
- **Sales-led closed-won deals as NSM input** — couples NSM to sales motion, not customer value

## Hypothetical

A workflow SaaS with Asana/Linear-style positioning might land on "weekly active team members who completed ≥1 task within an active project in the past 7 days" — mirroring Amplitude's WLU grammar (active user + verb + collaboration threshold + 7-day window).

## See also

- Concepts: [`games`](../../concepts/games.md), [`north-star-metric`](../../concepts/north-star-metric.md), [`plg-and-feature-factories`](../../concepts/plg-and-feature-factories.md)
- Anchor case: [`amplitude`](../../cases/amplitude.md)
