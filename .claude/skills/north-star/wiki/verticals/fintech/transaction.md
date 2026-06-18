---
title: Fintech — Transaction Game
type: vertical
schema_version: 1
sources:
  - raw/synthesis/vertical-applications.md
  - raw/atoms/case-study-fragments/case-study-fragment-p030-l0683-financial-institution-primary-bank-nsm.md
  - raw/atoms/case-study-fragments/case-study-fragment-p030-l0676-financial-institution-five-inputs.md
  - raw/atoms/case-study-fragments/case-study-fragment-p028-l0625-financial-institution-brainstorm-process.md
  - raw/atoms/case-study-fragments/case-study-fragment-p049-l1144-dave-context-paycheck-to-paycheck.md
  - raw/atoms/case-study-fragments/case-study-fragment-p049-l1146-dave-retention-driver-recurring-expenses.md
  - raw/atoms/case-study-fragments/case-study-fragment-p049-l1148-dave-outcome-onboarding-rework.md
related:
  - wiki/concepts/games.md
  - wiki/concepts/leading-vs-lagging.md
  - wiki/cases/dave-banking.md
  - wiki/cases/hypothetical-financial-institution.md
  - wiki/anti-patterns/market-trend-as-nsm.md
  - wiki/anti-patterns/lagging-indicator-as-nsm.md
  - wiki/anti-patterns/vanity-metric-as-nsm.md
playbook_pages: [16, 18, 28, 30, 49]
industry: fintech
game: transaction
vertical_id: fintech-transaction
tier: 2
confidence: medium
confidence_derivation: "Synthesis-derived but well-anchored: the playbook's hypothetical financial-institution case (p.28-30) supplies the AND-logic 'primary bank' grammar directly, plus Dave Banking (p.49) provides a real-world fintech case."
curator_status: approved
verified: true
representative_cases: [case-hypothetical-financial-institution, case-dave-banking]
created: 2026-05-26
updated: 2026-05-26
priors:
  vertical_id: fintech-transaction
  industry: fintech
  game: transaction
  typical_nsm_grain: per-customer-per-30d
  typical_nsm_type: count_with_and_logic_high_trust_actions
  common_input_categories: [onboarding_to_money_in, direct_deposit_activation, funded_threshold, recurring_setup, transaction_frequency]
  common_anti_patterns: [lagging-indicator-as-nsm, market-trend-as-nsm, vanity-metric-as-nsm]
  common_traps: [funded_accounts_vanity, aum_lagging, app_opens_vanity, gross_txn_no_trust_gate, single_nsm_consumer_smb]
  example_case_ids: [case-hypothetical-financial-institution, case-dave-banking]
  classification_signals:
    - "Customer's money moves through the product"
    - "Trust is the binding constraint on engagement"
    - "Multiple distinct financial action types matter (deposit / spend / transfer / invest)"
    - "Lifecycle from funding → primary-relationship is observable"
  confidence_envelope:
    tier: 2
    confidence: medium
    curator_status: approved
    verified: false
    notes: "Well-anchored by the playbook's primary-bank case and Dave; AND-logic NSM is directly playbook-derived."
---

# Fintech — Transaction Game

## TL;DR

For consumer fintech (banking apps, money movement, brokerage — Cash-App-style, Robinhood-style, Dave-style): characteristic NSM is a per-customer-per-30d count of high-trust financial actions, typically combining multiple actions with AND-logic ("primary bank" pattern). Common inputs: onboarding to first money-in, direct-deposit activation, account-funded threshold, recurring setup, transaction frequency. Top trap: AUM or funded-accounts as NSM — both lagging and market-trend-corrupted.

## Why this vertical plays the Transaction game

Fintech customer value crystallizes in discrete high-trust financial actions — depositing, paying, sending, investing. Productivity overtones exist for "manage my financial life" workflows (budgeting, automated savings), but the dominant causal game is transaction: more high-trust actions → deeper product reliance → durable retention. The playbook's hypothetical financial-institution case (p.28-30) supplies the canonical fintech grammar with its "primary bank" formulation.

## Characteristic NSM shape

`count of [customers] with [direct deposit AND spending AND transfers] in [past 30d]`

The AND-logic is load-bearing: any single action can be gamed or one-off, but the *combination* of high-trust actions signals real primary-relationship status. Dave Banking (p.49) reinforces this with its paycheck-to-paycheck context — retention is driven by recurring-expense linkage.

## Common inputs

- **Onboarding to first money-in event** — first real funding
- **Direct-deposit activation** — high-commitment trust signal
- **Account-funded threshold** — maintains balance ≥X for ≥N days
- **Recurring-bill / auto-pay setup** — embeds the product in life
- **Transaction frequency** — sends, transfers, spends per period

## Vertical-specific traps

- **"Funded accounts" alone as NSM** — registered-users analog; accounts can be funded once and abandoned
- **AUM as NSM** — see [`lagging-indicator-as-nsm`](../../anti-patterns/lagging-indicator-as-nsm.md) and [`market-trend-as-nsm`](../../anti-patterns/market-trend-as-nsm.md); market moves change AUM independent of product value
- **App opens / balance checks as NSM** — see [`vanity-metric-as-nsm`](../../anti-patterns/vanity-metric-as-nsm.md)
- **Transaction count without trust gate** — the AND-logic exists for a reason
- **Single NSM across consumer + small-business products** — value mechanics differ

## Hypothetical

A Cash-App-style consumer fintech might frame NSM as "monthly count of customers with ≥1 P2P send AND ≥1 card spend AND ≥1 deposit in past 30d" — direct extension of the playbook's primary-bank AND-logic pattern. A Robinhood-style brokerage might use "monthly customers with ≥1 funded trade across ≥2 asset classes," explicitly avoiding AUM.

## See also

- Concepts: [`games`](../../concepts/games.md), [`leading-vs-lagging`](../../concepts/leading-vs-lagging.md)
- Anchor cases: [`dave-banking`](../../cases/dave-banking.md), [`hypothetical-financial-institution`](../../cases/hypothetical-financial-institution.md)
