---
title: Bets — Framing Work as Hypotheses
type: concept
schema_version: 1
sources:
  - definitions/definition-p049-l0159-bet.md
  - definitions/definition-p050-l0179-portfolio-of-bets.md
  - definitions/definition-p051-l0187-levels-of-bets.md
  - definitions/definition-p051-l0195-level-0-bet.md
  - definitions/definition-p051-l0196-level-1-bet.md
  - definitions/definition-p051-l0197-level-2-bet.md
  - definitions/definition-p051-l0198-level-3-bet.md
  - concepts/concept-p051-l0202-shift-language-from-done-to-review.md
  - principles/principle-p052-l0206-review-every-bet.md
  - principles/principle-p055-l0286-prioritize-by-expected-value.md
  - principles/principle-p055-l0287-prefer-small-bets-to-big-bet.md
related:
  - wiki/concepts/levels-of-bets.md
  - wiki/concepts/north-star-metric.md
  - wiki/concepts/inputs.md
playbook_pages: [49, 50, 51, 52, 55]
tier: 1
confidence: high
confidence_derivation: "Multiple anchor atoms reconciled at 2/2-4/4; Debate 8 (Levels-of-bets vs. Opportunity Solution Trees) flags an alternative framework but not contradicting → high with contested flag."
contested: true
curator_status: approved
verified: true
created: 2026-05-26
updated: 2026-05-26
---

# Bets — Framing Work as Hypotheses

## TL;DR
A bet is an initiative associated with a potential outcome — a hypothesis the team is trying to prove. If true, the team wins; if false, it loses. Framing work as bets makes it safe for uncertainty. A roadmap can be thought of as a portfolio of bets. The Levels of Bets model categorizes them by time horizon. Review every bet; prefer small bets to one big bet; prioritize by expected value.

## Decision rule
- Frame work as bets (hypotheses with potential outcomes), not as committed deliverables [definition-p049-l0159-bet].
- Review every bet you accomplish — large or small [principle-p052-l0206-review-every-bet].
- A series of small bets is preferable to one big bet [principle-p055-l0287-prefer-small-bets-to-big-bet].
- Prioritize based on expected value or influence on the NSM, not on amount of work completed [principle-p055-l0286-prioritize-by-expected-value].
- Shift project language from "to do, doing, done" to "focus on next, focusing, review" (or "to try, trying, review") to make the learning step explicit [concept-p051-l0202-shift-language-from-done-to-review].

## Detail
**Bet (definition).** "A bet is an initiative of any size that's associated with a potential outcome. Think of a bet akin to a hypothesis that you're trying to prove. If the hypothesis is true, you win the bet, and if it's false you lose. You're 'betting' that the work will produce a result. By calling it a bet, you're making it safe for uncertainty" [definition-p049-l0159-bet]. Bets terminology comes from John Cutler; the playbook contrasts bets with "experiments" in an adjacent PRO TIP on p. 50 — a bet is broader (any initiative with a potential outcome); an experiment is narrower (a structured test of a single variable).

**Portfolio of bets.** "For larger initiatives or projects, you might have a portfolio of bets, where the larger project is a bet consisting of smaller bets that might be related to and dependent on each other... You can think of your roadmap as a portfolio of bets" [definition-p050-l0179-portfolio-of-bets]. Roadmap-as-portfolio is the bridge between bets-talk and standard product-management vocabulary.

**Three core practices** the playbook attaches to bets:

1. **Review every bet.** "Each bet you accomplish along the way should be reviewed" [principle-p052-l0206-review-every-bet]. No exceptions for small bets. The review is where the learning lives.

2. **Prefer small bets.** "A series of small bets or experiments is preferable to one big bet or experiment" [principle-p055-l0287-prefer-small-bets-to-big-bet]. Small bets compound learning faster; one big bet compounds risk.

3. **Prioritize by expected value, not work completed.** "Prioritize based on expected value or influence, not to maximize the amount of work completed" [principle-p055-l0286-prioritize-by-expected-value]. This is the playbook's push-back against velocity-maximization.

**Language shift to encourage learning.** "Many companies get in the habit of labeling a project as 'done' and calling it a day instead of learning from it... shift to 'focus on next, focusing, and review' and 'to try, trying, review'" [concept-p051-l0202-shift-language-from-done-to-review]. The vocabulary change is tied to the levels-of-bets review board (fig-52-1) — every bet ends in a review column, not a done column.

> NOTE — CONTESTED: Teresa Torres' Opportunity Solution Tree (Continuous Discovery Habits) covers similar ground with different organizing primitives — outcome → opportunities → solutions → assumption tests. The Levels-of-Bets model organizes by time horizon; OST organizes by customer opportunity. Different artifacts, different review meetings. See [Debate: Levels of bets vs. opportunity solution trees](../debates/levels-of-bets-vs-ost.md).

## yaml-rules
```yaml
bet:
  definition: initiative_associated_with_potential_outcome
  framing: hypothesis_to_prove
  purpose: makes_work_safe_for_uncertainty
  size_range: any
portfolio_of_bets:
  is: larger_initiative_of_smaller_bets
  roadmap_is_a: portfolio_of_bets
core_practices:
  - review_every_bet
  - prefer_series_of_small_bets_over_one_big_bet
  - prioritize_by_expected_value_or_influence_not_work_completed
language_shift:
  from: ["to do", "doing", "done"]
  to: ["focus on next", "focusing", "review"]
  alternative_to: ["to try", "trying", "review"]
  purpose: incorporate_learning_step
```

## Related
- [Levels of Bets](levels-of-bets.md)
- [North Star Metric](north-star-metric.md)
- [Inputs](inputs.md)
