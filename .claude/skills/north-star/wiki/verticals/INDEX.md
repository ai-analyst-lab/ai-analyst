---
title: Verticals Index
type: index
schema_version: 1
sources:
  - raw/synthesis/vertical-applications.md
related:
  - wiki/concepts/games.md
  - wiki/concepts/north-star-metric.md
tier: 2
confidence: medium
curator_status: approved
created: 2026-05-26
updated: 2026-05-26
---

# Verticals Index

Per-(industry × game) wiki pages capturing the playbook's vertical-specific guidance. Each page projects into a runtime `VerticalProfile` via its `priors` YAML block. All pages are Tier 2 (synthesis-derived) unless otherwise noted.

## Verticals (8)

| Industry × Game | NSM grain | Anchor case(s) | Confidence |
|---|---|---|---|
| [B2B SaaS — Productivity](b2b-saas/productivity.md) | per-user-per-week | [Amplitude](../cases/amplitude.md) | medium |
| [B2B SaaS — Transaction](b2b-saas/transaction.md) | per-account-per-week | [Burger King](../cases/burger-king.md), [Happy Deliveries](../cases/happy-deliveries.md) | medium |
| [Consumer Subscription — Attention](consumer-subscription/attention.md) | per-subscriber-per-week | [Netflix](../cases/netflix.md) | medium |
| [Consumer Subscription — Productivity](consumer-subscription/productivity.md) | per-subscriber-per-week | — | medium |
| [Marketplace — Transaction](marketplace/transaction.md) | per-week-per-market | [Happy Deliveries](../cases/happy-deliveries.md), [Hypothetical Grocery](../cases/hypothetical-grocery-delivery.md) | medium |
| [Dev Tools — Productivity](dev-tools/productivity.md) | per-developer-per-week | [Amplitude](../cases/amplitude.md) (grammar parallel) | medium |
| [Fintech — Transaction](fintech/transaction.md) | per-customer-per-30d | [Dave Banking](../cases/dave-banking.md), [Hypothetical Financial Institution](../cases/hypothetical-financial-institution.md) | medium |
| [Social / Content — Attention](social-content/attention.md) | per-user-per-week | — | medium |

## Edge cases (3)

Places where the playbook's framework needs adaptation or explicit framework-extension.

| Edge case | What bends | Confidence |
|---|---|---|
| [Multi-game hybrid (LinkedIn-style)](edge-cases/multi-game-hybrid.md) | The "one NSM per product" rule when a product genuinely runs multiple games | low |
| [Sales-led enterprise B2B](edge-cases/sales-led-b2b.md) | The PLG-centric NSM-drives-growth framing | low |
| [Open-source / community products](edge-cases/open-source-community.md) | The revenue-as-lagging-outcome scaffolding | low |

## How to use

- **Runtime classifier** (`classify_vertical()`) reads the `priors` YAML block from these pages to seed defaults.
- **Concept pages** ([`games`](../concepts/games.md), [`north-star-metric`](../concepts/north-star-metric.md)) carry the underlying framework; vertical pages apply it.
- **Case pages** ([`cases/`](../cases/)) carry the worked examples; vertical pages reference them.
- **Anti-pattern pages** ([`anti-patterns/`](../anti-patterns/)) carry the failure modes; vertical pages link to the most relevant per-vertical traps.
