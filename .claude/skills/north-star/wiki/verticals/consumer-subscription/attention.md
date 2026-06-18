---
title: Consumer Subscription — Attention Game
type: vertical
schema_version: 1
sources:
  - raw/synthesis/vertical-applications.md
  - raw/atoms/case-study-fragments/case-study-fragment-p008-l0165-netflix-2005-dvd-queue-nsm.md
  - raw/atoms/case-study-fragments/case-study-fragment-p008-l0165-netflix-outcome-retention-subscription.md
  - raw/atoms/case-study-fragments/case-study-fragment-p015-l0362-netflix-strategy-metric-pairing.md
related:
  - wiki/concepts/games.md
  - wiki/concepts/leading-vs-lagging.md
  - wiki/anti-patterns/nsm-disconnected-from-customer-value.md
  - wiki/cases/netflix.md
  - wiki/anti-patterns/lagging-indicator-as-nsm.md
  - wiki/anti-patterns/vanity-metric-as-nsm.md
playbook_pages: [8, 10, 15, 16, 18]
industry: consumer-subscription
game: attention
vertical_id: consumer-subscription-attention
tier: 2
confidence: medium
confidence_derivation: "Synthesis-derived from the Netflix-2005 DVD-queue NSM (p.8) — the canonical attention-game anchor in the playbook — generalized to streaming, news, and content-media subscription products."
curator_status: approved
verified: true
representative_cases: [case-netflix]
created: 2026-05-26
updated: 2026-05-26
priors:
  vertical_id: consumer-subscription-attention
  industry: consumer-subscription
  game: attention
  typical_nsm_grain: per-subscriber-per-week
  typical_nsm_type: count_with_completion_threshold
  common_input_categories: [onboarding_conversion, session_frequency, content_breadth, completion_quality, reengagement]
  common_anti_patterns: [lagging-indicator-as-nsm, vanity-metric-as-nsm, nsm-disconnected-from-customer-value]
  common_traps: [time_on_platform_vanity, dau_default, mrr_lagging, started_not_completed]
  example_case_ids: [case-netflix]
  classification_signals:
    - "Content / media access via paid subscription"
    - "Renewal is the lagging business outcome"
    - "Session-based consumption rhythm"
    - "Completion / satisfaction is the value moment"
  confidence_envelope:
    tier: 2
    confidence: medium
    curator_status: approved
    verified: false
    notes: "Netflix-2005 anchor is solid; modern streaming NSMs are not in the playbook."
---

# Consumer Subscription — Attention Game

## TL;DR

For streaming, news, and content-media subscriptions (Netflix-style, Spotify-style, NYT-style): characteristic NSM is a per-subscriber count or share of *satisfying* consumption events tied to the core content category, gated by a completion threshold. Common inputs: onboarding conversion, session frequency, content breadth, completion quality, re-engagement. Top trap: treating time-on-platform or MRR as the NSM — both fail the leading-indicator and customer-value tests.

## Why this vertical plays the Attention game

The subscriber is paying for ongoing access to content; the value moment is *satisfying consumption*. Transaction underlays (the renewal) are lagging — they tell you what already happened. The NSM should sit upstream of renewal, capturing whether subscribers are *actually* getting value session by session. The playbook's Netflix-2005 NSM ("% of customers placing 3+ DVDs in queue during first session") teaches this exact pattern: behavioral threshold tied to early predictive value.

## Characteristic NSM shape

`count of [subscribers / sessions] with [N or more satisfying consumption events] in [first session / week / month]`

The 2005 Netflix anchor predates streaming but teaches the durable shape: behavior + threshold + window.

## Common inputs

- **Onboarding conversion** — % of new subscribers reaching first satisfying session
- **Session frequency** — sessions per subscriber per week
- **Content breadth** — distinct content units consumed per subscriber per period
- **Completion quality** — % of started sessions completed (the Happy-Deliveries-style quality gate)
- **Re-engagement** — % of dormant subscribers reactivated

## Vertical-specific traps

- **Time-on-platform as NSM** — long time can mean great engagement *or* terrible navigation
- **DAU as NSM** — subscribers may engage in weekly or weekend bursts; daily grain misleads
- **Subscriber count or MRR as NSM** — see [`lagging-indicator-as-nsm`](../../anti-patterns/lagging-indicator-as-nsm.md)
- **"Titles watched" without completion gating** — fails customer-value test; started-but-abandoned content is not value delivered

## Hypothetical

A Netflix-style streaming service today might evolve from the 2005 DVD-queue NSM toward "% of subscribers completing ≥3 satisfying viewing sessions per week" (Netflix's actual current NSM is not in the playbook). The grammar is preserved: count + threshold + window.

## See also

- Concepts: [`games`](../../concepts/games.md), [`leading-vs-lagging`](../../concepts/leading-vs-lagging.md)
- Anchor case: [`netflix`](../../cases/netflix.md)
