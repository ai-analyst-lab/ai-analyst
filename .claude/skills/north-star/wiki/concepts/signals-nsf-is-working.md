---
title: Signals the NSF Is Working — Ten Observable Indicators
type: concept
schema_version: 1
sources:
  - concepts/concept-p043-l0011-signals-nsf-is-working.md
related:
  - wiki/concepts/make-the-nsm-stick.md
  - wiki/concepts/north-star-framework.md
  - wiki/concepts/north-star-of-the-north-star.md
playbook_pages: [43]
tier: 1
confidence: high
confidence_derivation: "Single anchor concept atom 2/2; not flagged in debates → high."
curator_status: approved
verified: true
created: 2026-05-26
updated: 2026-05-26
---

# Signals the NSF Is Working — Ten Observable Indicators

## TL;DR
Ten observable signals indicate the NSF is taking root: people connect daily work to the NSM, confidence about impact rises, morale improves, "no"s are easier and evidence-backed, the battle of ideas shifts to impact and experimentation, collaboration becomes more productive, language is shared, more people can describe strategy, non-product teammates use NSF vocabulary, and the NSM is mentioned in large company meetings. These signals are descriptive, not prescriptive — use them to diagnose adoption, not as targets.

## Decision rule
- Treat the 10 signals as a diagnostic rubric for whether the framework is taking root.
- The MOST load-bearing single signal: team members can explain how their day-to-day work connects to the NSM. If this is absent, adoption is not real regardless of other surface indicators.
- These signals are DESCRIPTIVE, not prescriptive — do not run them as a checklist team scorecard; they are leading indicators for the [Make the NSM Stick](make-the-nsm-stick.md) program.

## Detail
The full bundled list, from Chapter 5: "The following are some signals that the North Star Framework is working for your organization and your product:" [concept-p043-l0011-signals-nsf-is-working].

1. **Team members can explain how their day-to-day work connects to the NSM.** The most load-bearing signal. If a designer or engineer cannot trace today's task to an input and from the input to the NSM, the framework is decorative, not operational.

2. **You are more confident about the impact of your work.** The team can articulate expected impact at the bet level, not just describe what's being built.

3. **Improved morale.** Connection between daily work and a meaningful goal is itself motivating; the NSF surfaces that connection.

4. **Easier "no"s, backed by evidence.** When a request doesn't connect to an input, the team can decline with a framework-grounded reason rather than a political one.

5. **The "battle of ideas" shifts from opinions to impact and experimentation.** Debates become "which bet has higher expected value?" rather than "whose feature is more important?"

6. **More productive collaboration.** Cross-team discussions have a shared frame; less time spent re-aligning, more time spent deciding.

7. **Shared language.** Everyone knows what the NSM is, what the inputs are, what an L2 vs. L3 bet means. Vocabulary becomes infrastructure.

8. **More people can describe the strategy.** Not just the founders or the head of product — engineers, designers, marketers can all articulate the product strategy in NSM terms.

9. **Non-product teammates use NSF vocabulary.** Finance, sales, and customer success start referring to the NSM and inputs in their own meetings — diffusion outside the product org.

10. **The NSM is mentioned in large company meetings.** All-hands, board updates, exec offsites — the NSM appears as the organizing artifact, not as one slide among many.

The list is bundled deliberately. No single signal proves adoption; the cluster signals it. Signal 1 is the most diagnostic — without it, the other signals can mask theater. Signal 10 is the most distal — it lags real adoption by several quarters.

This list is also the closest the playbook gets to a "definition of done" for the NSF — except the framework is explicitly never done (see [Implementing the NSF Is Never Done](implementing-nsf-is-never-done.md)).

## yaml-rules
```yaml
signals_nsf_is_working:
  count: 10
  load_bearing_signal: team_can_connect_daily_work_to_nsm
  signals:
    - team_members_explain_work_connection_to_nsm
    - higher_confidence_in_impact_and_decisions
    - improved_morale
    - easier_nos_backed_by_evidence
    - battle_of_ideas_shifts_to_impact_and_experimentation
    - more_productive_collaboration
    - shared_language
    - more_people_can_describe_strategy
    - non_product_teammates_use_nsf_vocab
    - nsm_mentioned_in_large_company_meetings
  use_as: diagnostic_rubric
  do_not_use_as: team_scorecard_or_target
most_diagnostic: signal_1
most_lagging: signal_10
```

## Related
- [Make the NSM Stick](make-the-nsm-stick.md)
- [North Star Framework](north-star-framework.md)
- [North Star of the North Star](north-star-of-the-north-star.md)
