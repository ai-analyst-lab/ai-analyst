# Contested Wiki Entries — Public Trust Signal

**Status:** Per Decision #14 (public-with-skill-filter), this index lists every wiki entry where the framework has substantive published critics. The runtime `/north-star` skill can filter these out per `filter_mode='trust'` (default = trust = exclude contested) or surface them via `filter_mode='exploratory'`.

**Updated:** 2026-05-26
**Produced by:** debates-assembler (Phase 3, pipeline step 3.6)

## How to read this index

A wiki entry is marked **contested** when at least one of the following holds:

1. A debate page exists in `wiki/debates/` that touches the entry's playbook atoms.
2. The entry's claim has a credible published critic at Tier A (peer-reviewed / first-person primary) or Tier B (named-author practitioner essay on a recognized platform) from `raw/synthesis/counter-research.md`.
3. The entry is identified by `debate-mapper` (`raw/synthesis/debates.md`) as touching a substantive disagreement in the practitioner literature.

"Contested" here means the framework has *substantive published critics with named-author standing*, not internet noise or contrarian commentary. Five of the 14 debates have URL-backed Tier A/B counter-research sources; nine are flagged as contested by `debate-mapper` but remain unsourced within the current counter-research budget (and are honestly labeled as such on their pages).

The runtime skill's `filter_mode` parameter determines how contested entries surface:

- `trust` (default): contested entries are excluded from result sets. The skill serves only verified, consensus material.
- `exploratory`: contested entries are returned with their debate-page paths attached, so the agent can surface "this is contested" honesty signals.
- `research`: all material returned, including rejected entries, for audit purposes.

## Contested concepts

Sorted alphabetically. Each row: concept page → debate page(s) that touch it.

- [`gap-thinking-vs-present-thinking.md`](../concepts/gap-thinking-vs-present-thinking.md) — Debate 14 ([`gap-vs-present-thinking-false-binary.md`](../debates/gap-vs-present-thinking-false-binary.md))
- [`inputs.md`](../concepts/inputs.md) — Debates 5, 7, 11 ([`nsm-one-level-out-of-reach.md`](../debates/nsm-one-level-out-of-reach.md), [`inputs-vs-okrs.md`](../debates/inputs-vs-okrs.md), [`goodhart-and-the-nsm.md`](../debates/goodhart-and-the-nsm.md))
- [`leading-vs-lagging.md`](../concepts/leading-vs-lagging.md) — Debate 3 ([`b2b-revenue-as-nsm.md`](../debates/b2b-revenue-as-nsm.md))
- [`levels-of-bets.md`](../concepts/levels-of-bets.md) — Debate 8 ([`levels-of-bets-vs-ost.md`](../debates/levels-of-bets-vs-ost.md))
- [`make-the-nsm-stick.md`](../concepts/make-the-nsm-stick.md) — Debates 6, 12 ([`nsm-cadence.md`](../debates/nsm-cadence.md), [`nsm-public-to-customers.md`](../debates/nsm-public-to-customers.md))
- [`north-star-framework.md`](../concepts/north-star-framework.md) — Debates 2, 7 ([`one-nsm-vs-loops.md`](../debates/one-nsm-vs-loops.md), [`inputs-vs-okrs.md`](../debates/inputs-vs-okrs.md))
- [`north-star-metric.md`](../concepts/north-star-metric.md) — Debates 1, 2, 3, 4, 9, 10, 11 ([`early-stage-nsm-timing.md`](../debates/early-stage-nsm-timing.md), [`one-nsm-vs-loops.md`](../debates/one-nsm-vs-loops.md), [`b2b-revenue-as-nsm.md`](../debates/b2b-revenue-as-nsm.md), [`nsm-count-vs-rate-vs-ratio.md`](../debates/nsm-count-vs-rate-vs-ratio.md), [`plg-requires-nsm.md`](../debates/plg-requires-nsm.md), [`nsm-vs-vision-statement.md`](../debates/nsm-vs-vision-statement.md), [`goodhart-and-the-nsm.md`](../debates/goodhart-and-the-nsm.md))
- [`north-star-of-the-north-star.md`](../concepts/north-star-of-the-north-star.md) — Debate 10 ([`nsm-vs-vision-statement.md`](../debates/nsm-vs-vision-statement.md))
- [`nsf-vs-okrs-and-roadmaps.md`](../concepts/nsf-vs-okrs-and-roadmaps.md) — Debate 7 ([`inputs-vs-okrs.md`](../debates/inputs-vs-okrs.md))
- [`nsm-checklist.md`](../concepts/nsm-checklist.md) — Debate 4 ([`nsm-count-vs-rate-vs-ratio.md`](../debates/nsm-count-vs-rate-vs-ratio.md))
- [`plg-and-feature-factories.md`](../concepts/plg-and-feature-factories.md) — Debates 1, 9 ([`early-stage-nsm-timing.md`](../debates/early-stage-nsm-timing.md), [`plg-requires-nsm.md`](../debates/plg-requires-nsm.md))
- [`product-vision.md`](../concepts/product-vision.md) — Debates 10, 14 ([`nsm-vs-vision-statement.md`](../debates/nsm-vs-vision-statement.md), [`gap-vs-present-thinking-false-binary.md`](../debates/gap-vs-present-thinking-false-binary.md))
- [`signals-nsf-is-working.md`](../concepts/signals-nsf-is-working.md) — Debate 6 ([`nsm-cadence.md`](../debates/nsm-cadence.md))
- [`squad-organization.md`](../concepts/squad-organization.md) — Debate 13 ([`value-orientation-vs-stable-teams.md`](../debates/value-orientation-vs-stable-teams.md))
- [`three-implementation-traps.md`](../concepts/three-implementation-traps.md) — Debate 11 ([`goodhart-and-the-nsm.md`](../debates/goodhart-and-the-nsm.md))
- [`three-languages-of-teams.md`](../concepts/three-languages-of-teams.md) — Debate 10 ([`nsm-vs-vision-statement.md`](../debates/nsm-vs-vision-statement.md))
- [`vanity-metric.md`](../concepts/vanity-metric.md) — Debates 4, 11 ([`nsm-count-vs-rate-vs-ratio.md`](../debates/nsm-count-vs-rate-vs-ratio.md), [`goodhart-and-the-nsm.md`](../debates/goodhart-and-the-nsm.md))

## Contested anti-patterns

- [`attachment-to-nsm.md`](../anti-patterns/attachment-to-nsm.md) — Debate 6 ([`nsm-cadence.md`](../debates/nsm-cadence.md))
- [`features-to-inputs-without-opportunity.md`](../anti-patterns/features-to-inputs-without-opportunity.md) — Debate 8 ([`levels-of-bets-vs-ost.md`](../debates/levels-of-bets-vs-ost.md))
- [`focusing-only-on-nsm-not-inputs.md`](../anti-patterns/focusing-only-on-nsm-not-inputs.md) — Debate 5 ([`nsm-one-level-out-of-reach.md`](../debates/nsm-one-level-out-of-reach.md))
- [`gap-thinking.md`](../anti-patterns/gap-thinking.md) — Debate 14 ([`gap-vs-present-thinking-false-binary.md`](../debates/gap-vs-present-thinking-false-binary.md))
- [`influencing-nsm-directly.md`](../anti-patterns/influencing-nsm-directly.md) — Debates 5, 11 ([`nsm-one-level-out-of-reach.md`](../debates/nsm-one-level-out-of-reach.md), [`goodhart-and-the-nsm.md`](../debates/goodhart-and-the-nsm.md))
- [`insisting-on-multiple-nsms.md`](../anti-patterns/insisting-on-multiple-nsms.md) — Debate 2 ([`one-nsm-vs-loops.md`](../debates/one-nsm-vs-loops.md))
- [`lagging-indicator-as-nsm.md`](../anti-patterns/lagging-indicator-as-nsm.md) — Debate 3 ([`b2b-revenue-as-nsm.md`](../debates/b2b-revenue-as-nsm.md))
- [`nsm-as-wall-proclamation.md`](../anti-patterns/nsm-as-wall-proclamation.md) — Debates 1, 9, 12 ([`early-stage-nsm-timing.md`](../debates/early-stage-nsm-timing.md), [`plg-requires-nsm.md`](../debates/plg-requires-nsm.md), [`nsm-public-to-customers.md`](../debates/nsm-public-to-customers.md))
- [`organize-around-tech-stack.md`](../anti-patterns/organize-around-tech-stack.md) — Debate 13 ([`value-orientation-vs-stable-teams.md`](../debates/value-orientation-vs-stable-teams.md))
- [`rushing-statement-exercise.md`](../anti-patterns/rushing-statement-exercise.md) — Debate 1 ([`early-stage-nsm-timing.md`](../debates/early-stage-nsm-timing.md))
- [`vanity-metric-as-nsm.md`](../anti-patterns/vanity-metric-as-nsm.md) — Debate 11 ([`goodhart-and-the-nsm.md`](../debates/goodhart-and-the-nsm.md))

## All debate pages

Sorted alphabetically by slug.

| Debate page | Tier-A/B sourced? | Current consensus | Highest-leverage critique? |
|---|---|---|---|
| [`b2b-revenue-as-nsm.md`](../debates/b2b-revenue-as-nsm.md) | Yes (Roberge, Stage 2 Capital — Tier B) | strong (converges with playbook) | Critique converges with playbook |
| [`early-stage-nsm-timing.md`](../debates/early-stage-nsm-timing.md) | No (unsourced within budget) | none | — |
| [`gap-vs-present-thinking-false-binary.md`](../debates/gap-vs-present-thinking-false-binary.md) | No (unsourced within budget) | weak | — |
| [`goodhart-and-the-nsm.md`](../debates/goodhart-and-the-nsm.md) | Yes (Strathern 1997 — Tier A peer-reviewed) | evolving | **Highest-leverage latent critique in the corpus** |
| [`inputs-vs-okrs.md`](../debates/inputs-vs-okrs.md) | Yes (Wodtke — Tier A first-person; Garr — Tier B cross-reference) | weak | High operational leverage |
| [`levels-of-bets-vs-ost.md`](../debates/levels-of-bets-vs-ost.md) | No (unsourced within budget) | weak | — |
| [`nsm-cadence.md`](../debates/nsm-cadence.md) | No (unsourced within budget) | weak | — |
| [`nsm-count-vs-rate-vs-ratio.md`](../debates/nsm-count-vs-rate-vs-ratio.md) | No (unsourced within budget) | weak | — |
| [`nsm-one-level-out-of-reach.md`](../debates/nsm-one-level-out-of-reach.md) | No (unsourced within budget) | weak | — |
| [`nsm-public-to-customers.md`](../debates/nsm-public-to-customers.md) | No (unsourced within budget) | weak | — |
| [`nsm-vs-vision-statement.md`](../debates/nsm-vs-vision-statement.md) | No (unsourced within budget) | weak | — |
| [`one-nsm-vs-loops.md`](../debates/one-nsm-vs-loops.md) | Yes (Balfour/Winters/Kwok/Chen Reforge — Tier B; First Round Winters interview — Tier B) | weak | Deepest competing framework |
| [`plg-requires-nsm.md`](../debates/plg-requires-nsm.md) | No (unsourced within budget) | weak | — |
| [`value-orientation-vs-stable-teams.md`](../debates/value-orientation-vs-stable-teams.md) | No (unsourced within budget) | weak | — |

## Coverage notes

- **5 of 14 debates** have URL-backed Tier A/B counter-research sources: Goodhart, loops-not-funnels, inputs-vs-OKRs, B2B-revenue-as-NSM, and HEART/balanced-scorecard (the last folded into related entries rather than its own debate page).
- **9 of 14 debates** are flagged as contested by `debate-mapper` but remain unsourced within the current counter-research budget. Their debate pages honestly disclose this on the page itself rather than fabricating citations.
- **Highest-leverage critique:** Goodhart's Law applied to product metrics ([`goodhart-and-the-nsm.md`](../debates/goodhart-and-the-nsm.md)). The most defensible single curator addition to the wiki: pair the NSM checklist with an explicit annual "Goodhart hygiene" practice — "what evidence would convince us this NSM no longer measures customer value?"
- **Convergent critique:** Roberge ([`b2b-revenue-as-nsm.md`](../debates/b2b-revenue-as-nsm.md)) is the strongest "the playbook is right but for partial reasons" finding. The B2B-operator counter-position the debate-mapper anticipated is *not* supported by the strongest published B2B SaaS metric-design voice.
- A future counter-research pass with a fresh budget should target the nine unsourced debates: early-stage NSM timing, count-vs-rate, Cutler rule critique, NSM cadence, OST critique, founder-taste PLG, narrative-centric vision, public NSM, and Team Topologies.

## See also

- `raw/synthesis/debates.md` — `debate-mapper`'s structured catalog of 14 contested claims.
- `raw/synthesis/counter-research.md` — `counter-research-agent`'s URL-backed external sources for 5 of the 14 debates.
- `WIKI_SCHEMA.md` §Debate page template — schema authority for the debate type.
- `wiki/SCHEMAS/DebateArticle.yaml` — concrete schema for debate pages.
