---
title: B2B SaaS — Transaction Game
type: vertical
schema_version: 1
sources:
  - raw/synthesis/vertical-applications.md
  - raw/atoms/case-study-fragments/case-study-fragment-p012-l0270-burger-king-nsm-statement.md
  - raw/atoms/case-study-fragments/case-study-fragment-p018-l0429-happy-deliveries-nsm-research-insight.md
  - raw/atoms/case-study-fragments/case-study-fragment-p018-l0427-happy-deliveries-rejected-candidates.md
related:
  - wiki/concepts/games.md
  - wiki/concepts/leading-vs-lagging.md
  - wiki/cases/burger-king.md
  - wiki/cases/happy-deliveries.md
  - wiki/anti-patterns/vanity-metric-as-nsm.md
  - wiki/anti-patterns/lagging-indicator-as-nsm.md
playbook_pages: [10, 12, 16, 18]
industry: b2b-saas
game: transaction
vertical_id: b2b-saas-transaction
tier: 2
confidence: medium
confidence_derivation: "Synthesis-derived. The playbook's transaction-game grammar is anchored in Burger King (B2C) and Happy Deliveries (delivery app); generalization to usage-based B2B infrastructure is inferential."
curator_status: approved
verified: true
representative_cases: [case-burger-king, case-happy-deliveries]
created: 2026-05-26
updated: 2026-05-26
priors:
  vertical_id: b2b-saas-transaction
  industry: b2b-saas
  game: transaction
  typical_nsm_grain: per-account-per-week
  typical_nsm_type: count_quality_gated
  common_input_categories: [activation_ttft, volume_depth, use_case_breadth, reliability, account_expansion]
  common_anti_patterns: [vanity-metric-as-nsm, lagging-indicator-as-nsm]
  common_traps: [api_call_vanity, gross_volume_ignores_quality, failed_transaction_pollution, pricing_change_coupling]
  example_case_ids: [case-burger-king, case-happy-deliveries]
  classification_signals:
    - "Usage-based or consumption-based billing"
    - "Discrete value-bearing transactions as the unit of work"
    - "Reliability / success-rate is core to customer value"
    - "Account-level (not seat-level) economic unit"
  confidence_envelope:
    tier: 2
    confidence: medium
    curator_status: approved
    verified: false
    notes: "B2C anchors (Burger King) carry the grammar; B2B usage-infra generalization is inferential."
---

# B2B SaaS — Transaction Game

## TL;DR

For usage-based B2B infrastructure (payments, dev infra, APIs): characteristic NSM is a per-active-account-per-period count of successful, quality-gated transactions processed through the product. Common inputs: TTFT activation, volume depth, use-case breadth, reliability, account expansion. Top trap: counting gross transaction volume (or raw API calls) without a reliability / quality gate — classic Happy-Deliveries failure.

## Why this vertical plays the Transaction game

When billing scales with consumed transactions (charges, API calls, deploys, messages), the customer-value moment *is* the successful transaction. The product is the rails. Productivity overtones appear when the product is dev infra consumed inside engineering workflows, but the dominant causal game is still transaction: more successful transactions → more value delivered → more usage-based revenue.

## Characteristic NSM shape

`count of [successful customer transactions / units processed] per [active account] per [billing period or short window]`

Burger King's "digital transactions per user" (p.12) supplies the grammar; Happy Deliveries (p.18) supplies the quality gate that protects against the vanity-volume trap.

## Common inputs

- **TTFT activation** — new-account time to first successful transaction
- **Volume depth** — transactions per account per period
- **Use-case breadth** — distinct integrations or endpoints touched per account
- **Reliability** — successful-transaction rate (the Happy Deliveries lesson)
- **Account expansion** — additional environments, sub-accounts, or business units onboarded

## Vertical-specific traps

- **API call count as NSM** — page-view-style vanity; see [`vanity-metric-as-nsm`](../../anti-patterns/vanity-metric-as-nsm.md)
- **Gross transaction volume ignoring quality** — direct parallel to [Happy Deliveries](../../cases/happy-deliveries.md)
- **Counting failed / retried transactions in the input chain** — corrupts the leading-indicator property
- **Coupling NSM to pricing changes** — pricing model shifts produce NSM movement that isn't customer value

## Hypothetical

A Stripe-style payment processor might frame NSM as "weekly active merchants processing ≥10 successful charges per week" — adapting the Burger King transaction grammar with a quality threshold à la Happy Deliveries. A messaging-infra platform might use "weekly accounts with ≥1K delivered messages and <1% bounce rate."

## See also

- Concepts: [`games`](../../concepts/games.md), [`leading-vs-lagging`](../../concepts/leading-vs-lagging.md)
- Anchor cases: [`burger-king`](../../cases/burger-king.md), [`happy-deliveries`](../../cases/happy-deliveries.md)
