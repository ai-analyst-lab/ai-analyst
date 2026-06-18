---
title: Social / Content — Attention Game
type: vertical
schema_version: 1
sources:
  - raw/synthesis/vertical-applications.md
  - raw/atoms/concepts/concept-p015-l0353-nsm-must-express-customer-value.md
related:
  - wiki/concepts/games.md
  - wiki/concepts/leading-vs-lagging.md
  - wiki/anti-patterns/nsm-disconnected-from-customer-value.md
  - wiki/anti-patterns/vanity-metric-as-nsm.md
  - wiki/anti-patterns/lagging-indicator-as-nsm.md
playbook_pages: [10, 15, 16, 18, 25]
industry: social-content
game: attention
vertical_id: social-content-attention
tier: 2
confidence: medium
confidence_derivation: "Synthesis-derived. No direct full case-fragment anchor for social/content platforms; the Frequent Content Sharers glossary term (p.25) is the closest in-corpus anchor. Pattern extrapolated from attention-game framing and the playbook's strong stance on time-on-page / DAU / impressions anti-patterns (p.18)."
curator_status: approved
verified: true
representative_cases: []
created: 2026-05-26
updated: 2026-05-26
priors:
  vertical_id: social-content-attention
  industry: social-content
  game: attention
  typical_nsm_grain: per-user-per-week
  typical_nsm_type: count_with_interaction_quality_gate
  common_input_categories: [activation_first_meaningful, interaction_depth, creator_participation, reciprocity, reengagement]
  common_anti_patterns: [vanity-metric-as-nsm, lagging-indicator-as-nsm, nsm-disconnected-from-customer-value]
  common_traps: [time_on_platform_vanity, dau_default, impressions_vanity, posts_without_consumption_gate, engagement_bait_optimization]
  example_case_ids: []
  classification_signals:
    - "Free-to-use, ad or sub-funded"
    - "Content (user-generated or curated) is the unit of consumption"
    - "Network effects on both consumption and creation sides"
    - "Engagement-bait / rage-bait is a known failure mode"
  confidence_envelope:
    tier: 2
    confidence: medium
    curator_status: approved
    verified: false
    notes: "No full case anchor in playbook; FCS glossary term is the closest reference. Pattern is well-supported by anti-pattern list."
---

# Social / Content — Attention Game

## TL;DR

For short-video, forums, community chat, live-streaming platforms (TikTok-style, Reddit-style, Twitch-style, Discord-style): characteristic NSM is a per-active-user-per-period count of *meaningful* engagement events, where the quality gate is the hardest part to get right. Common inputs: activation to first meaningful interaction, interaction depth, creator-side participation, reciprocity, re-engagement. Top trap: time-on-platform, DAU, or impressions as NSM — every classic attention-game vanity metric lives here.

## Why this vertical plays the Attention game

These products win or lose on whether users keep returning to consume and interact with content. Transaction underlays (ad revenue, subscription) are lagging — they're downstream of attention quality. Network effects add structural complexity (covered in [edge-cases/multi-game-hybrid](../edge-cases/multi-game-hybrid.md) for LinkedIn-style platforms), but pure-attention platforms have a clean primary game. The trap is that passive scrolling *looks* like engagement, so the NSM needs an interaction quality gate.

## Characteristic NSM shape

`count of [active users] with [N or more meaningful interactions — completed view, comment, share, follow-back] in [short window — daily or weekly]`

The Frequent Content Sharers (FCS) glossary term (p.25) is the closest in-corpus exemplar — though without a full case fragment, the pattern is extrapolated rather than directly anchored.

## Common inputs

- **Activation to first meaningful interaction** — not just first session
- **Interaction depth** — distinct interaction types per user per period
- **Creator participation** — % of users producing content vs consuming only
- **Reciprocity** — % of consumed content that triggers a return interaction
- **Re-engagement** — dormant user reactivation

## Vertical-specific traps

- **Time-on-platform / minutes-watched as NSM** — the canonical place this trap shows up; see [`vanity-metric-as-nsm`](../../anti-patterns/vanity-metric-as-nsm.md)
- **DAU as NSM** — high DAU can coexist with declining real engagement
- **Impressions / ad-views as NSM** — vanity volume
- **"Posts published" without consumption-side gating** — a post with zero viewers is not value delivered
- **Optimizing an NSM that rewards rage-bait / engagement-bait** — playbook is silent here; open question

## Hypothetical

A TikTok-style short-video platform might frame NSM as "weekly active users with ≥3 completed video views (≥N% watched) AND ≥1 interaction (like / comment / share) per week." The double-AND construction protects against pure-passive consumption being read as value, mirroring the playbook's general quality-gate insistence.

## See also

- Concepts: [`games`](../../concepts/games.md), [`leading-vs-lagging`](../../concepts/leading-vs-lagging.md)
- Edge case: [`multi-game-hybrid`](../edge-cases/multi-game-hybrid.md) (for LinkedIn-style platforms)
