---
title: Make the NSM Stick — The Five-Ingredient Adoption Recipe
type: concept
schema_version: 1
sources:
  - concepts/concept-p044-l0032-make-the-nsm-stick.md
  - concepts/concept-p043-l0011-signals-nsf-is-working.md
  - concepts/concept-p045-l0054-when-to-change-the-nsm.md
related:
  - wiki/concepts/north-star-workshops.md
  - wiki/concepts/signals-nsf-is-working.md
  - wiki/concepts/north-star-metric.md
playbook_pages: [43, 44, 45]
tier: 1
confidence: high
confidence_derivation: "3 concept atoms reconciled at 2/2-4/4; Debate 6 (NSM cadence) and Debate 12 (publish externally?) flag adjacent debates → high with contested flag."
contested: true
curator_status: approved
verified: true
created: 2026-05-26
updated: 2026-05-26
---

# Make the NSM Stick — The Five-Ingredient Adoption Recipe

## TL;DR
Teams who sustain the NSF share five ingredients: (1) a sponsor with influence and authority, (2) leadership buy-in, (3) communication and change-management processes, (4) onboarding that incorporates the framework, and (5) approval processes. This is the multi-month adoption program — distinct from immediate post-workshop socialization. Revisit the NSM when the market changes, the business reaches a new stage, or the metric proves uncontrollable — the directional-revenue test fires when the NSM stops tracking revenue.

## Decision rule
- Ensure all five adoption ingredients are present BEFORE expecting the NSM to durably take root [concept-p044-l0032-make-the-nsm-stick].
- Watch for the 10 signals that the NSF is working (see [Signals NSF Is Working](signals-nsf-is-working.md)) as the leading indicator of successful adoption.
- Revisit the NSM when: the market changes, the business reaches a new stage, or the metric proves uncontrollable [concept-p045-l0054-when-to-change-the-nsm].
- Run the directional-revenue diagnostic: if the NSM is not directionally indicating where revenue is going, revise it.

## Detail
**Five organizational ingredients.** "The teams who've seen the most success implementing — and sticking to — the North Star Framework have: A sponsor with both influence and authority; Leadership buy-in; Communication and change management processes to socialize the concept; An onboarding process that incorporates the framework; Approval processes" [concept-p044-l0032-make-the-nsm-stick].

1. **Sponsor with influence AND authority.** Influence without authority cannot remove blockers; authority without influence cannot generate adoption energy. Both are needed.
2. **Leadership buy-in.** Senior leaders cite the NSM in their own communications, defend resourcing against the inputs, and visibly use the framework in decision-making.
3. **Communication and change management.** Repeated socialization in many forums; not a single all-hands.
4. **Onboarding integration.** New hires learn the NSM and inputs as part of standard onboarding; this is how the framework survives team turnover.
5. **Approval processes.** Major bets require explicit connection to an input; the approval ritual enforces the framework instead of letting it become advisory.

**When to change the NSM.** "At some point, your business may recognize that your North Star is no longer effective. Maybe your market has changed, your business is at a different stage, or you've realized that the metric you defined isn't something you can control" [concept-p045-l0054-when-to-change-the-nsm]. Three trigger conditions:
- Market changes (new segment, new competitive dynamic, new platform)
- Business reaches a new stage (PMF, scale, new business model)
- Metric proves uncontrollable (inputs don't move it, or it moves independently of inputs)

The diagnostic test, attributed to Ted Clark, is directional: if the NSM is flat but revenue is moving, or vice versa, revise the NSM. The NSM should directionally indicate where revenue is going.

> NOTE — CONTESTED: The cadence of NSM revision is contested. The playbook's framing leans toward "rarely, with reluctance" — the multi-year stable artifact that new hires learn. OKR-fluent shops and strategy-refresh practitioners argue NSMs should evolve at the cadence of strategy (annually or even quarterly). See [Debate: How long should an NSM last?](../debates/nsm-cadence.md). Whether to publish the NSM externally to customers is also contested — see [Debate: NSM as public artifact](../debates/nsm-public-to-customers.md).

## yaml-rules
```yaml
make_the_nsm_stick:
  five_ingredients:
    - id: sponsor
      requires_both: [influence, authority]
    - id: leadership_buy_in
      indicators: [cited_in_comms, defends_resourcing, used_in_decisions]
    - id: communication_change_management
      cadence: repeated_in_many_forums
    - id: onboarding_integration
      survives: team_turnover
    - id: approval_processes
      enforces: bet_must_connect_to_input
  distinct_from: immediate_post_workshop_socialization
  timeframe: multi_month
when_to_change_nsm:
  triggers:
    - market_changes
    - business_new_stage
    - metric_proves_uncontrollable
  diagnostic:
    name: directional_revenue_test
    rule: if_nsm_flat_but_revenue_moving_revise_nsm
    attributed_to: ted_clark
```

## Related
- [North Star Workshops](north-star-workshops.md)
- [Signals NSF Is Working](signals-nsf-is-working.md)
- [North Star Metric](north-star-metric.md)
