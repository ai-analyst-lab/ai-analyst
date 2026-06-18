---
title: The Game — Attention, Transaction, Productivity
type: concept
schema_version: 1
sources:
  - definitions/definition-p010-l0239-the-game-classification.md
  - definitions/definition-p010-l0243-attention-game.md
  - definitions/definition-p010-l0245-transaction-game.md
  - definitions/definition-p010-l0247-productivity-game.md
related:
  - wiki/concepts/north-star-metric.md
  - wiki/concepts/key-value-exchanges.md
playbook_pages: [10]
tier: 1
confidence: high
confidence_derivation: "All 4 anchor definition atoms reconciled with cross_extractor_agreement 2/2 or 3/3; not flagged by debates.md → high."
curator_status: approved
verified: true
created: 2026-05-26
updated: 2026-05-26
---

# The Game — Attention, Transaction, Productivity

## TL;DR
"The game" is a classification of what your business and product fundamentally do; identifying it helps a team converge on a North Star Metric. The playbook enumerates three games: attention (users absorbed in the product; time spent indicates satisfaction), transaction (users completing purchases/transactions), and productivity (users picking the product because they have a job to do). Identify the game before designing the NSM — it shapes which behaviors qualify as customer value.

## Decision rule
- Before the NSM workshop, identify which of the three games the product is playing [definition-p010-l0239-the-game-classification].
- A product can play exactly one primary game; if it appears to play multiple, look for the dominant value loop.
- An NSM should reflect the behavior the game's customers value:
  - Attention game → behaviors signaling absorption / time spent / engagement depth
  - Transaction game → behaviors signaling successful completion of the core transaction
  - Productivity game → behaviors signaling the user accomplished their job

## Detail
The playbook frames this as a PRO TIP in Chapter 1: "In our North Star workshops, before we dig in, we typically ask teams to identify and understand the 'game' their business and product are playing because it helps identify their North Star" [definition-p010-l0239-the-game-classification].

The three games:

**Attention game.** "Your user gets absorbed in your product, and the more time they spend using it shows increased satisfaction" [definition-p010-l0243-attention-game]. Media, social, and entertainment products typically play this game. Spotify's "time spent listening" is an attention-game NSM.

**Transaction game.** "Your user is looking for the right product for their needs, to easily complete transactions, and track production and delivery" [definition-p010-l0245-transaction-game]. E-commerce, marketplaces, QSR (quick service restaurants), grocery delivery, and ticketing products play this game. Burger King's "digital transactions per user" and the playbook's grocery-delivery example are transaction-game NSMs.

**Productivity game.** "Your user chooses your product because they have a job to do" [definition-p010-l0247-productivity-game]. SaaS productivity tools, B2B software, and learning products typically play this game. Amplitude's "Weekly Learning Users" is a productivity-game NSM.

Identifying the game upstream of the NSM workshop saves teams from a common failure mode: picking a metric that is internally coherent but mis-matched to the user's actual reason for being there. An attention-game NSM applied to a transaction product (e.g., measuring "time on site" for an e-commerce checkout) typically drives the wrong roadmap.

## yaml-rules
```yaml
games:
  attention:
    user_pattern: gets_absorbed_in_product
    value_signal: time_spent
    nsm_shape: engagement_or_depth_metric
  transaction:
    user_pattern: completes_transactions
    value_signal: successful_transaction
    nsm_shape: transactions_per_user_or_completion_rate
  productivity:
    user_pattern: has_a_job_to_do
    value_signal: job_completed
    nsm_shape: active_users_completing_core_action
identify_game_when: before_running_nsm_workshop
games_count: 3
exclusive: true
```

## Related
- [North Star Metric](north-star-metric.md)
- [Key Value Exchanges](key-value-exchanges.md)
