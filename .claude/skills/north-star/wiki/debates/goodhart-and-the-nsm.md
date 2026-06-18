---
title: Goodhart's Law and the NSM — does the playbook address inevitable metric corruption?
type: debate
schema_version: 1
sources:
  - synthesis/debates.md
  - synthesis/counter-research.md
  - raw/atoms/concepts/concept-p018-l0408-nsm-must-not-be-vanity.md
  - raw/atoms/principles/principle-p009-l0194-never-influence-nsm-directly.md
  - raw/atoms/concepts/concept-p045-l0054-when-to-change-the-nsm.md
  - raw/atoms/concepts/concept-p048-l0133-three-implementation-traps.md
related:
  - wiki/concepts/north-star-metric.md
  - wiki/concepts/vanity-metric.md
  - wiki/anti-patterns/vanity-metric-as-nsm.md
  - wiki/anti-patterns/influencing-nsm-directly.md
playbook_pages: [18, 9, 45, 48]
tier: 2
confidence: high
confidence_derivation: "Counter-research Tier-A source (Strathern 1997, peer-reviewed European Review). Highest-leverage latent critique in the corpus per debate-mapper notes."
contested: "Does the playbook's defense against metric gaming (vanity anti-pattern + Cutler rule + directional-revenue check) sufficiently address Goodhart's Law, or does it need an explicit NSM re-validation cadence?"
current_consensus: evolving
curator_status: approved
verified: true
created: 2026-05-26
updated: 2026-05-26
---

# Goodhart's Law and the NSM

## TL;DR
The playbook addresses metric gaming implicitly: the vanity-metric anti-pattern, the "never move the NSM directly" rule, and the wall-proclamation anti-pattern all partially defend against Goodhart-style decay. But the playbook never names Goodhart's Law and never prescribes a periodic NSM re-validation ritual. Marilyn Strathern's canonical 1997 restatement — *"When a measure becomes a target, it ceases to be a good measure"* — implies the playbook's defenses are necessary but not sufficient. This is the highest-leverage latent critique in the corpus.

## Where they agree
- Gaming is a real risk; the playbook explicitly fights it via the vanity-metric criterion [concept-p018-l0408-nsm-must-not-be-vanity].
- A metric optimized by the team that owns it tends to corrupt — both sides treat this as observed fact.
- Customer-value alignment is the right anchor for a metric's design.

## Arguments for (the playbook's existing defenses are sufficient)
- The "one level out of reach" Cutler rule means no single team can directly hit the NSM — it can only be moved through inputs, which dilutes any single team's ability to game it [principle-p009-l0194-never-influence-nsm-directly].
- The vanity-metric criterion structurally excludes the most gamable metric forms (DAU-as-NSM, registered-users-as-NSM, etc.) at design time [concept-p018-l0408-nsm-must-not-be-vanity].
- The directional-revenue test (NSM flat but revenue moving, or vice versa) provides a built-in late-stage early-warning when the NSM has stopped measuring what it was chosen to measure [concept-p045-l0054-when-to-change-the-nsm].
- The three-implementation-traps atom names the failure modes (feature factory, premature solutions, no discovery) that produce Goodhart-style decay in practice [concept-p048-l0133-three-implementation-traps].
- The playbook's culture work (sponsor, leadership buy-in, onboarding) creates organizational defenses against the "redefine the metric to hit the number" failure mode.

## Arguments against (defenses are partial; Goodhart needs explicit treatment)
- Marilyn Strathern (1997), *"Improving ratings": audit in the British University system*, European Review 5(3): 305-321: *"When a measure becomes a target, it ceases to be a good measure."* ([Wikipedia canonical restatement](https://en.wikipedia.org/wiki/Goodhart%27s_law); [PMC peer-reviewed context](https://pmc.ncbi.nlm.nih.gov/articles/PMC7901608/) — Tier A) Strathern generalized Goodhart's original 1975 monetary-aggregates observation to social systems and audit cultures.
- The implication for the NSF: a metric chosen at year zero to be a leading indicator of customer value will, by year three, be a leading indicator of "things teams do to move this number" — even when the metric is one level out of reach.
- The playbook never names Goodhart, never prescribes a periodic NSM-validation ritual, and never asks teams to write down a falsification test for their NSM.
- The directional-revenue check fires too late: by the time the NSM has decoupled from revenue, the team has spent two years optimizing the wrong thing.
- The "one level out of reach" rule slows decay but does not prevent it. Once teams have run for two years on Spotify-style "time spent listening," the entire incentive system bends toward time-on-platform even at the expense of user wellbeing.

## Current consensus
Evolving — the playbook's defenses are real and partial; Strathern's critique is widely cited across the metric-design literature and is the strongest single addition the wiki could surface. The most defensible curator move: pair the NSM checklist with an explicit "Goodhart hygiene" practice — "what evidence would convince us this NSM no longer measures customer value?" — run annually, with documented falsification tests. This addresses the critique without abandoning the framework. The convergence flag from counter-research: if `real-world-validator` surfaces any documented case of an NSM (Spotify time-listened, Facebook MAU) showing Goodhart-style decay, the pairing makes this the strongest single addition to the wiki.

## Why this matters
Determines whether teams build a "what would falsify this NSM?" review into their annual planning or assume the framework's hygiene is enough. The difference is the failure mode: caught-early Goodhart decay (with re-validation ritual) vs. caught-late Goodhart decay (with directional-revenue check). The latter has cost organizations product-strategy years.

## See also
- [North Star Metric concept](../concepts/north-star-metric.md)
- [Vanity metric concept](../concepts/vanity-metric.md)
- [Vanity metric as NSM (anti-pattern)](../anti-patterns/vanity-metric-as-nsm.md)
- [Influencing NSM directly (anti-pattern)](../anti-patterns/influencing-nsm-directly.md)
- Related debates: [NSM one level out of reach](nsm-one-level-out-of-reach.md), [How long should an NSM last?](nsm-cadence.md)
