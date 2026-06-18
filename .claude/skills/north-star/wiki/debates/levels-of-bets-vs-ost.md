---
title: Levels of bets vs. opportunity solution trees
type: debate
schema_version: 1
sources:
  - synthesis/debates.md
  - raw/atoms/definitions/definition-p051-l0187-levels-of-bets.md
  - raw/atoms/principles/principle-p048-l0136-define-opportunity-before-feature.md
  - raw/atoms/concepts/concept-p048-l0133-three-implementation-traps.md
  - raw/atoms/definitions/definition-p049-l0159-bet.md
  - raw/atoms/principles/principle-p055-l0287-prefer-small-bets-to-big-bet.md
related:
  - wiki/concepts/levels-of-bets.md
  - wiki/concepts/bets.md
  - wiki/concepts/three-implementation-traps.md
  - wiki/anti-patterns/features-to-inputs-without-opportunity.md
playbook_pages: [51, 48, 49, 55]
tier: 2
confidence: low
confidence_derivation: "debate-mapper Debate 8. Counter-research located no Tier-A/B direct critique of levels-of-bets framing within budget; Torres' published OST work is canonical but a head-to-head comparison was not found."
contested: "Should the organizing primitive of product planning be time-horizon (Levels 0-3 bets) or customer-opportunity (OST: outcome → opportunity → solution → test)?"
current_consensus: weak
curator_status: approved
verified: false
created: 2026-05-26
updated: 2026-05-26
---

# Levels of bets vs. opportunity solution trees

## TL;DR
The playbook organizes bets into Levels 0-3 by time horizon — larger bets ladder up to the NSM, smaller bets are quarterly interventions. Teresa Torres' Opportunity Solution Tree (Continuous Discovery Habits) covers similar ground with different vocabulary: outcome → opportunities → solutions → assumption tests. Both reject jumping from features to outcomes without an opportunity layer. They disagree on the organizing primitive: time horizon (playbook) vs. customer opportunity (Torres). Different artifacts, different review meetings.

## Where they agree
- Jumping from features to outcomes without an opportunity layer is a failure mode [principle-p048-l0136-define-opportunity-before-feature].
- Three implementation traps (feature factory, premature solutions, no discovery) plague teams that skip the opportunity layer [concept-p048-l0133-three-implementation-traps].
- Small bets generally outperform big bets when learning is the goal [principle-p055-l0287-prefer-small-bets-to-big-bet].
- Discovery work is real product work, not pre-work.

## Arguments for the playbook stance (Levels 0-3)
- Levels 0-3 give a portfolio-management frame: leadership can see how time and headcount are allocated across multi-year, annual, quarterly, and monthly horizons [definition-p051-l0187-levels-of-bets].
- A bet has a defined unit [definition-p049-l0159-bet]; classifying by horizon makes planning, staffing, and risk-management decisions tractable at the org level.
- The model maps cleanly to the NSM tree: L0/L1 bets ladder to NSM and inputs; L2/L3 bets are interventions inside a quarter.
- Quarterly portfolio reviews work because the time-horizon classification is legible to executives who need to know "what are we betting on this year" without reading the customer-research artifacts.

## Arguments against (Opportunity Solution Tree)
- Teresa Torres' OST organizes around *customer opportunities* — clustered customer needs — rather than time horizons. The argument: a time-horizon frame hides the customer-need clustering OST makes visible.
- Bets-talk encourages portfolio thinking at the expense of the customer-discovery loop OST insists on (continuous interviewing, assumption tests, solution exploration).
- An OST shop reviews "which opportunities have we validated and which are still hypothetical" — a question the levels-of-bets frame does not naturally surface.
- The OST's assumption-test layer (what would have to be true for this solution to work?) is a discipline the bets framework does not require.
- **No Tier-A/B head-to-head critique was located within counter-research's budget.** Torres' *Continuous Discovery Habits* is canonical but does not specifically critique the playbook's levels-of-bets framing; the contrast is more inferential.

## Current consensus
Weak — leans playbook for portfolio-management contexts (org > 50 PMs, multi-team coordination), leans OST for product-team-level discovery work. The two frameworks are not flatly opposed: an L1 bet in the playbook's vocabulary can sit on top of an OST opportunity in Torres' vocabulary; they are operating at different altitudes. The substantive question is what artifact the product org defends to leadership: a portfolio of bets by horizon (playbook) or a tree of opportunities by customer need (Torres). The wiki could improve by noting OST as a complementary discovery practice at the L2/L3 layer rather than positioning the two as alternatives.

## Why this matters
A levels-of-bets shop runs quarterly portfolio reviews; an OST shop runs continuous discovery interviews. Different muscle, different staffing (research vs. portfolio management), different artifacts on the wall.

## See also
- [Levels of bets concept](../concepts/levels-of-bets.md)
- [Bets concept](../concepts/bets.md)
- [Three implementation traps](../concepts/three-implementation-traps.md)
- [Features-to-inputs without opportunity (anti-pattern)](../anti-patterns/features-to-inputs-without-opportunity.md)
