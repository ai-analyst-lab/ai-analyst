---
title: Marketplace — Transaction Game
type: vertical
schema_version: 1
sources:
  - raw/synthesis/vertical-applications.md
  - raw/atoms/case-study-fragments/case-study-fragment-p018-l0429-happy-deliveries-nsm-research-insight.md
  - raw/atoms/case-study-fragments/case-study-fragment-p018-l0427-happy-deliveries-rejected-candidates.md
  - raw/atoms/case-study-fragments/case-study-fragment-p008-l0177-grocery-delivery-nsm-monthly-items.md
  - raw/atoms/case-study-fragments/case-study-fragment-p008-l0179-grocery-input-1-place-orders.md
  - raw/atoms/case-study-fragments/case-study-fragment-p008-l0180-grocery-input-2-orders-with-items.md
  - raw/atoms/case-study-fragments/case-study-fragment-p008-l0181-grocery-input-3-fulfilling-orders.md
  - raw/atoms/case-study-fragments/case-study-fragment-p008-l0182-grocery-input-4-delivering-on-time.md
related:
  - wiki/concepts/games.md
  - wiki/concepts/leading-vs-lagging.md
  - wiki/cases/happy-deliveries.md
  - wiki/cases/hypothetical-grocery-delivery.md
  - wiki/anti-patterns/vanity-metric-as-nsm.md
  - wiki/anti-patterns/lagging-indicator-as-nsm.md
playbook_pages: [8, 10, 11, 16, 18]
industry: marketplace
game: transaction
vertical_id: marketplace-transaction
tier: 2
confidence: medium
confidence_derivation: "Synthesis-derived. The playbook doesn't carve out marketplaces specifically; the Happy Deliveries quality-gate principle (p.18) and the grocery-delivery hypothetical (p.8) supply the closest direct grammar. Two-sidedness is inferential extension."
curator_status: approved
verified: true
representative_cases: [case-happy-deliveries, case-hypothetical-grocery-delivery]
created: 2026-05-26
updated: 2026-05-26
priors:
  vertical_id: marketplace-transaction
  industry: marketplace
  game: transaction
  typical_nsm_grain: per-week-per-market
  typical_nsm_type: count_two_sided_quality_gated
  common_input_categories: [demand_activation, supply_onboarding, liquidity, transaction_quality, repeat_both_sides]
  common_anti_patterns: [vanity-metric-as-nsm, lagging-indicator-as-nsm, insisting-on-multiple-nsms]
  common_traps: [gmv_lagging, demand_only_blindspot, requests_vanity, no_quality_gate, single_nsm_across_geos]
  example_case_ids: [case-happy-deliveries, case-hypothetical-grocery-delivery]
  classification_signals:
    - "Two-sided platform brokering value exchange"
    - "Transactions can fail at multiple steps (request → match → completion)"
    - "Geographic / market segmentation matters for liquidity"
    - "Both sides have ratings / feedback mechanisms"
  confidence_envelope:
    tier: 2
    confidence: medium
    curator_status: approved
    verified: false
    notes: "Two-sided framing is inferential; playbook's anchors are delivery-app + grocery hypothetical, not full marketplaces."
---

# Marketplace — Transaction Game

## TL;DR

For two-sided marketplaces (Uber-style, DoorDash-style, Airbnb-style, eBay-style): characteristic NSM is a per-period count of completed transactions where *both* sides were satisfied. Common inputs: demand activation, supply onboarding, liquidity, transaction quality, repeat on both sides. Top trap: GMV as NSM (lagging) or demand-only metrics (ignores supply-side collapse risk).

## Why this vertical plays the Transaction game

The marketplace exists to broker discrete value-exchange events. The NSM must capture the *completed* transaction — not the request, not the listing, not the click. The two-sidedness adds a structural wrinkle the playbook doesn't address directly: a healthy NSM must protect against demand-side blindness (lots of requests, no fulfillment) and supply-side blindness (lots of supply, no demand). The Happy Deliveries lesson (p.18) — quality-gate every transaction count — generalizes especially well here.

## Characteristic NSM shape

`count of [completed transactions] where [demand-side satisfaction AND supply-side satisfaction conditions met] per [period]`

The grocery-delivery hypothetical (p.8) extends this to a 4-input chain (placing orders → orders with items → orders fulfilled → delivered on time) — a useful template for any marketplace where transactions can fail at multiple steps.

## Common inputs

- **Demand activation** — new buyers reaching first completed transaction
- **Supply onboarding** — new providers/drivers/hosts reaching first earned transaction
- **Liquidity** — % of demand requests fulfilled within target SLA
- **Transaction quality** — % of transactions with no complaints from either side (Happy Deliveries analog)
- **Repeat frequency** — on both sides

## Vertical-specific traps

- **GMV as NSM** — classic lagging indicator; see [`lagging-indicator-as-nsm`](../../anti-patterns/lagging-indicator-as-nsm.md)
- **Treating only demand-side activity as NSM** — ignores supply-side collapse risk
- **"Requests received" or "driver app opens" as inputs** — vanity volume; see [`vanity-metric-as-nsm`](../../anti-patterns/vanity-metric-as-nsm.md)
- **Counting cancelled / refunded transactions** — fails the quality gate
- **Single NSM across geographies** when supply density varies dramatically can mask city-level dysfunction

## Hypothetical

An Uber-style rideshare might frame NSM as "weekly count of completed trips with rider rating ≥4 AND no driver-side cancellation." The grammar mirrors Happy Deliveries (quality gate) plus the grocery-delivery hypothetical (on-time / satisfying-completion gate).

## See also

- Concepts: [`games`](../../concepts/games.md), [`leading-vs-lagging`](../../concepts/leading-vs-lagging.md)
- Anchor cases: [`happy-deliveries`](../../cases/happy-deliveries.md), [`hypothetical-grocery-delivery`](../../cases/hypothetical-grocery-delivery.md)
