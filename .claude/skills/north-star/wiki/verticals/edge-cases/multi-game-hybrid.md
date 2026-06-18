---
title: Edge Case — Multi-Game Hybrid Products (LinkedIn-style)
type: vertical
schema_version: 1
sources:
  - raw/synthesis/vertical-applications.md
  - raw/atoms/concepts/concept-p011-l0260-one-nsm-per-product.md
  - raw/atoms/anti-patterns/anti-pattern-p041-l0955-insisting-on-multiple-nsms.md
  - raw/atoms/case-study-fragments/case-study-fragment-p030-l0683-financial-institution-primary-bank-nsm.md
related:
  - wiki/concepts/games.md
  - wiki/concepts/north-star-metric.md
  - wiki/anti-patterns/insisting-on-multiple-nsms.md
  - wiki/cases/hypothetical-financial-institution.md
playbook_pages: [11, 30, 41]
industry: multi-game-hybrid
game: productivity
vertical_id: edge-multi-game-hybrid
tier: 2
confidence: low
confidence_derivation: "Edge case. The playbook is explicit about 'one NSM per product' (p.11) and 'don't insist on multiple NSMs' (p.41), but does not directly address LinkedIn-style hybrids. This page documents the extension, not a playbook-direct prescription. Low confidence because the resolution paths are inferential."
curator_status: approved
verified: false
representative_cases: [case-hypothetical-financial-institution]
created: 2026-05-26
updated: 2026-05-26
priors:
  vertical_id: edge-multi-game-hybrid
  industry: multi-game-hybrid
  game: productivity  # nominal — actual game varies by product
  typical_nsm_grain: varies
  typical_nsm_type: composite_and_logic_or_split_products
  common_input_categories: [dominant_game_inputs, plus_cross_game_health_indicators]
  common_anti_patterns: [insisting-on-multiple-nsms]
  common_traps: [forcing_one_nsm_when_two_products, picking_wrong_dominant_game, composite_nsm_uninterpretable]
  example_case_ids: [case-hypothetical-financial-institution]
  classification_signals:
    - "Product clearly serves >1 of {attention, transaction, productivity}"
    - "Different sub-products plausibly have different NSMs"
    - "Network effects span multiple game types"
    - "'Which game are we?' generates internal disagreement"
  resolution_paths: [dominant_causal_game, split_sub_products, composite_and_logic_nsm]
  confidence_envelope:
    tier: 2
    confidence: low
    curator_status: approved
    verified: false
    notes: "Edge case. Resolution paths are inferential extensions of the playbook, not playbook-direct prescriptions."
---

# Edge Case — Multi-Game Hybrid Products

## TL;DR

Some products (LinkedIn-style) run Attention, Transaction, and Productivity games simultaneously. The playbook's hard line "one NSM per product" (p.11) bumps against this reality. Three resolution paths: pick the dominant causal game, split into sub-products, or compose an AND-logic NSM (primary-bank pattern, p.30). The playbook doesn't directly address this — flag as framework extension, not framework application.

## Why this is an edge case

The playbook's three-games framework (p.10) assumes each product is dominantly one game. LinkedIn, for instance, has:

- **Attention mechanics** — feed scrolling, content consumption
- **Transaction mechanics** — job-application completion, InMail credits, subscription tiers
- **Productivity mechanics** — profile maintained as a professional artifact, network connections established

The "one NSM per product" rule (p.11, reinforced by `insisting-on-multiple-nsms` at p.41) creates real tension here.

## Three resolution paths

### 1. Pick the dominant causal game

Choose the game whose NSM most directly drives the long-term business outcome. For LinkedIn, that's likely Productivity — the durable value is the professional network artifact; Attention and Transaction mechanics are downstream of that artifact's quality. Pros: keeps one-NSM discipline. Cons: requires confident causal claim.

### 2. Treat sub-products as separate products

The playbook permits this. A "Jobs" sub-product is a different product than the "Feed"; each can have its own NSM. Pros: each NSM stays clean. Cons: cross-product strategy gets harder; "company NSM" question reopens at the org level.

### 3. Composite AND-logic NSM

The playbook's hypothetical primary-bank NSM (p.30) shows AND-logic across multiple action types in a single NSM. The same construction can let a hybrid product capture "user did meaningful work across multiple game types in the period." Pros: one NSM, captures hybridity. Cons: composite metrics are notoriously hard to interpret when they move; you can't tell *which* game drove the change.

## Open question

The playbook does not explicitly endorse any of these paths for LinkedIn-style products — the closest it gets is the multi-input AND construction in the financial-institution case. A curator should treat this page as framework extension, not framework application. Real-world validation against LinkedIn's actual NSM (which is not in the playbook) would strengthen confidence.

## See also

- Concepts: [`games`](../../concepts/games.md), [`north-star-metric`](../../concepts/north-star-metric.md)
- Anti-pattern: [`insisting-on-multiple-nsms`](../../anti-patterns/insisting-on-multiple-nsms.md)
- Related case: [`hypothetical-financial-institution`](../../cases/hypothetical-financial-institution.md) (AND-logic NSM pattern)
