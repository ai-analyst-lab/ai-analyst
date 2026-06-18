---
title: Consumer Subscription — Productivity Game
type: vertical
schema_version: 1
sources:
  - raw/synthesis/vertical-applications.md
  - raw/atoms/concepts/concept-p008-l0184-inputs-vary-by-context.md
  - raw/atoms/concepts/concept-p015-l0353-nsm-must-express-customer-value.md
related:
  - wiki/concepts/games.md
  - wiki/concepts/north-star-metric.md
  - wiki/cases/amplitude.md
  - wiki/anti-patterns/vanity-metric-as-nsm.md
  - wiki/anti-patterns/lagging-indicator-as-nsm.md
playbook_pages: [8, 10, 15, 16, 18]
industry: consumer-subscription
game: productivity
vertical_id: consumer-subscription-productivity
tier: 2
confidence: medium
confidence_derivation: "Synthesis-derived. No direct playbook anchor for habit/learning/wellness apps; pattern extrapolated from the productivity-game framing (p.10-11) and Amplitude's WLU grammar (p.26)."
curator_status: approved
verified: true
representative_cases: []
created: 2026-05-26
updated: 2026-05-26
priors:
  vertical_id: consumer-subscription-productivity
  industry: consumer-subscription
  game: productivity
  typical_nsm_grain: per-subscriber-per-week
  typical_nsm_type: count_of_completed_habit_action
  common_input_categories: [onboarding_to_first_completion, streak_adherence, session_depth, habit_breadth, program_completion]
  common_anti_patterns: [vanity-metric-as-nsm, lagging-indicator-as-nsm]
  common_traps: [app_opens_vanity, streak_gameable, enrollments_without_completion, renewal_lagging]
  example_case_ids: []
  classification_signals:
    - "Subscriber pays for behavior change / skill acquisition / wellness outcome"
    - "Value moment is a completed practice / lesson / workout"
    - "Habit cadence is daily or every-few-days"
    - "Streaks / programs / plans appear in product UX"
  confidence_envelope:
    tier: 2
    confidence: medium
    curator_status: approved
    verified: false
    notes: "No direct playbook case anchor. Pattern extrapolated from productivity-game framing and habit-app practitioner knowledge."
---

# Consumer Subscription — Productivity Game

## TL;DR

For habit, learning, and wellness consumer subscriptions (Duolingo-style, Calm-style, Strava-style): characteristic NSM is a per-subscriber count of *completed* self-improvement actions, gated by a meaningful-completion threshold within a cadence matching the habit being formed. Common inputs: onboarding-to-first-completion, streak adherence, session depth, habit breadth, program completion. Top trap: app opens or session starts as NSM — vanity volume that decouples from real value.

## Why this vertical plays the Productivity game

The subscriber is hiring the product to *accomplish something* — meditate, learn a language, exercise — not consume content for its own sake. The lagging outcome (renewal) is downstream of whether the user actually built the habit. Attention mechanics matter for sub-second UX, but the *causal* game is productivity: real progress → real retention. This is the productivity-game generalization from playbook p.10-11, adapted to a B2C subscription wrapper.

## Characteristic NSM shape

`count of [subscribers] who [completed N units of the target habit] in [habit-appropriate window — daily / weekly]`

Cadence matters: daily for meditation/journaling, weekly for fitness, every-few-days for language learning. The "completed" gate distinguishes real practice from passive opens.

## Common inputs

- **Onboarding to first completed practice** — first real session, not first signup
- **Streak adherence** — consecutive-day engagement, with caveat below
- **Session depth** — minutes practiced, lessons completed, exercises finished
- **Habit breadth** — distinct practice types touched per user
- **Program completion rate** — % of started plans / courses / programs finished

## Vertical-specific traps

- **App opens or sessions started as NSM** — page-view-style vanity; see [`vanity-metric-as-nsm`](../../anti-patterns/vanity-metric-as-nsm.md)
- **Streak length alone as NSM** — gameable; streak-saving features can decouple streak from real value
- **Course enrollments without completion** — registered-users analog
- **Subscription renewal as NSM** — see [`lagging-indicator-as-nsm`](../../anti-patterns/lagging-indicator-as-nsm.md); renewal should be downstream of the productivity NSM, not the NSM itself

## Hypothetical

A Duolingo-style language app might land on "weekly active learners who completed ≥1 lesson within their active path on ≥3 days in the past 7." The inner threshold (lesson completed within path, not just any tap) protects against the streak-saving vanity trap. A Calm-style meditation app might use "weekly subscribers completing ≥3 sessions of ≥5 minutes."

## See also

- Concepts: [`games`](../../concepts/games.md), [`north-star-metric`](../../concepts/north-star-metric.md)
- Grammar parallel: [`amplitude`](../../cases/amplitude.md) (B2B productivity-game anchor)
