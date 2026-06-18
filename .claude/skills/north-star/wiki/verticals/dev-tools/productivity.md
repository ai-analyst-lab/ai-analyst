---
title: Dev Tools — Productivity Game
type: vertical
schema_version: 1
sources:
  - raw/synthesis/vertical-applications.md
  - raw/atoms/case-study-fragments/case-study-fragment-p026-l0591-amplitude-wlu-nsm.md
  - raw/atoms/concepts/concept-p015-l0353-nsm-must-express-customer-value.md
  - raw/atoms/concepts/concept-p016-l0383-nsm-must-be-actionable.md
related:
  - wiki/concepts/games.md
  - wiki/concepts/north-star-metric.md
  - wiki/cases/amplitude.md
  - wiki/anti-patterns/vanity-metric-as-nsm.md
  - wiki/anti-patterns/lagging-indicator-as-nsm.md
playbook_pages: [10, 15, 16, 26]
industry: dev-tools
game: productivity
vertical_id: dev-tools-productivity
tier: 2
confidence: medium
confidence_derivation: "Synthesis-derived. No direct dev-tools anchor in the playbook; pattern extrapolated from Amplitude WLU grammar (p.26) — developer-as-active-user, shipped-work-as-collaboration-threshold."
curator_status: approved
verified: true
representative_cases: [case-amplitude]
created: 2026-05-26
updated: 2026-05-26
priors:
  vertical_id: dev-tools-productivity
  industry: dev-tools
  game: productivity
  typical_nsm_grain: per-developer-per-week
  typical_nsm_type: count_of_shipped_work_units
  common_input_categories: [ttfs_activation, ship_frequency, repo_breadth, rollback_rate_inverse, team_adoption]
  common_anti_patterns: [vanity-metric-as-nsm, lagging-indicator-as-nsm]
  common_traps: [commits_vanity, stars_vanity, failed_builds_counted, dau_without_shipping_gate]
  example_case_ids: [case-amplitude]
  classification_signals:
    - "Customers are developers / engineering teams"
    - "Value moment is shipped / merged / deployed work"
    - "Success/failure of work is observable in-product"
    - "Often consumption-billed (build-minutes, deploys, seats)"
  confidence_envelope:
    tier: 2
    confidence: medium
    curator_status: approved
    verified: false
    notes: "No direct dev-tools case in playbook; Amplitude grammar transferred."
---

# Dev Tools — Productivity Game

## TL;DR

For IDEs, hosting/deploy platforms, repo collaboration tools (GitHub-style, Vercel-style, Linear-style): characteristic NSM is a per-active-developer-per-week count of "shipped work" units, gated by a non-rollback success threshold. Common inputs: TTFS activation, ship frequency, repo breadth, rollback rate (inverse), team adoption. Top trap: counting commits or lines of code as NSM — vanity that doesn't express customer value.

## Why this vertical plays the Productivity game

Developers hire dev tools to *ship work successfully* — code merged, deploys promoted, environments provisioned. Transaction overtones appear when billing is consumption-based (build-minutes, deploy units), but the dominant causal game is productivity: more successful shipped work → more developer trust → more team/account expansion. The Amplitude WLU pattern (p.26) is the nearest grammar match — developer-as-active-user, shipped-work as the collaboration-threshold analog.

## Characteristic NSM shape

`count of [active developers / teams] who [shipped a unit of work successfully] in [past week]`

The success gate (no rollback, build passing, deploy promoted) is what separates a productivity NSM from vanity activity.

## Common inputs

- **TTFS** — time-to-first-shipped-unit for new developers
- **Ship frequency** — per-developer shipped units per period
- **Repo / project breadth** — distinct projects each developer ships into
- **Rollback / failed-deploy rate** — inverse input; health indicator
- **Team adoption** — % of an account's developers actively shipping

## Vertical-specific traps

- **"Commits" or "lines of code" as NSM** — see [`vanity-metric-as-nsm`](../../anti-patterns/vanity-metric-as-nsm.md); fails customer-value test
- **GitHub stars / social signals as NSM** — vanity
- **Counting failed builds in deploy counts** — pollutes leading-indicator property
- **"Active developers" without a "shipped something useful" gate** — defaults to DAU vanity

## Hypothetical

A Vercel-style hosting platform might frame NSM as "weekly active teams with ≥1 successful production deploy that wasn't rolled back within 24h." The rollback gate is the dev-tools analog of Happy Deliveries' "no-issues" gate. A GitHub-style repo platform might use "weekly developers merging ≥1 PR into an active repo with ≥1 other collaborator."

## See also

- Concepts: [`games`](../../concepts/games.md), [`north-star-metric`](../../concepts/north-star-metric.md)
- Grammar parallel: [`amplitude`](../../cases/amplitude.md)
