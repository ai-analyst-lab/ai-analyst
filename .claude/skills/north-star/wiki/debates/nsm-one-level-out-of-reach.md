---
title: Should the NSM be one level out of reach? (the Cutler rule)
type: debate
schema_version: 1
sources:
  - synthesis/debates.md
  - raw/atoms/principles/principle-p009-l0194-never-influence-nsm-directly.md
  - raw/atoms/concepts/concept-p027-l0603-inputs-are-leverage-points.md
  - raw/atoms/concepts/concept-p040-l0949-focus-on-inputs-not-nsm.md
  - raw/atoms/concepts/concept-p009-l0190-inputs-independent-nsm-dependent.md
  - raw/atoms/concepts/concept-p007-l0153-nsf-tree-is-scaffold.md
related:
  - wiki/concepts/inputs.md
  - wiki/concepts/north-star-metric.md
  - wiki/anti-patterns/influencing-nsm-directly.md
  - wiki/anti-patterns/focusing-only-on-nsm-not-inputs.md
playbook_pages: [9, 27, 40]
tier: 2
confidence: low
confidence_derivation: "debate-mapper Debate 5. Counter-research located no Tier-A/B critique of the Cutler rule within budget. Epistemic critique is sound but lacks single citable essay."
contested: "Does the 'never move the NSM directly' rule prevent gaming, or does it convert the input-NSM causal claim into a faith document that nobody is allowed to test?"
current_consensus: weak
curator_status: approved
verified: false
created: 2026-05-26
updated: 2026-05-26
---

# Should the NSM be one level out of reach? (the Cutler rule)

## TL;DR
The playbook says never influence the NSM directly — move the inputs. If the NSM can be moved directly, it is probably not a good NSM. Critics argue this rule, taken literally, produces a hidden feature factory at the input layer: teams ship interventions whose only defense is "it moves an input," and the input→NSM link becomes a faith document. Both sides agree direct optimization of one number produces gaming. They disagree on whether the playbook polices the causal model.

## Where they agree
- Direct optimization of an NSM by a single team usually produces gaming or vanity feature work.
- The NSM should reflect customer value, not be a hackable single number.
- Inputs need to be defined and measured, not just named [principle-p027-l0611-name-and-define-inputs-too is referenced in the playbook].

## Arguments for the playbook stance
- The "Cutler rule" — never influence the NSM directly — dissolves territorial battles between teams about who "owns" the metric [principle-p009-l0194-never-influence-nsm-directly].
- Inputs are the leverage points where work happens; the NSM is the outcome that integrates them [concept-p027-l0603-inputs-are-leverage-points].
- Focus on inputs, not the NSM, because the NSM is dependent and inputs are independent [concept-p009-l0190-inputs-independent-nsm-dependent], [concept-p040-l0949-focus-on-inputs-not-nsm].
- The tree is a scaffold for conversation, not a contract [concept-p007-l0153-nsf-tree-is-scaffold] — the playbook does not claim the input→NSM relationship is unfalsifiable, just that the team should not try to short-circuit it.
- Organizationally, the rule prevents the "we hit the NSM by changing how we count" failure mode that plagues companies who let a single team own a top-line number.

## Arguments against (epistemic critique)
- If teams are told "never touch the NSM," they ship features whose only defense is "it moves an input" — and the input may have weak causal coupling to the NSM that nobody is allowed to question.
- The rule is sound *organizationally* (it dissolves turf battles) but epistemically dangerous: it discourages periodically re-testing whether the chosen inputs actually predict NSM movement.
- Andrew Chen's goal-fixation writing and outcome-oriented PM voices (Marty Cagan) argue that the right discipline is *outcome accountability*, which sometimes requires touching the top-line metric to test the model.
- Reforge's loop-diagnostic culture asks teams to test loop strength quarterly — a practice the Cutler rule discourages by default.
- The tree converts to a faith document over time: nobody remembers why these particular three inputs were chosen, but everyone defends moving them.
- **No Tier-A/B source explicitly critiquing the Cutler rule was located within counter-research's budget.** The position is implicit in outcome-orientation literature but not crystallized as a single essay.

## Current consensus
Weak — leans playbook on org dynamics, leans critic on epistemic hygiene. The Cutler rule is genuinely useful at the organizational level (it shuts down "I'll move the NSM by changing the definition" politics), and the playbook's defenders are right that direct optimization tends to corrupt the metric. The critic is right that the rule, applied for years without re-validation, lets the input→NSM causal model ossify. A wiki-level improvement: pair the Cutler rule with an explicit annual "input-NSM coupling audit" — does last year's input movement actually predict last year's NSM movement? If not, the tree needs revision.

## Why this matters
Determines whether teams are required to periodically re-test the tree's causal claims (loop-diagnostic culture) or are allowed to treat the tree as durable assumption (playbook default). Affects the failure mode: gaming-via-direct-optimization (which the rule prevents) vs. faith-document-decay (which the rule enables).

## See also
- [Inputs concept](../concepts/inputs.md)
- [Influencing NSM directly (anti-pattern)](../anti-patterns/influencing-nsm-directly.md)
- [Focusing only on NSM not inputs (anti-pattern)](../anti-patterns/focusing-only-on-nsm-not-inputs.md)
- Related debate: [Goodhart's Law and the NSM](goodhart-and-the-nsm.md)
