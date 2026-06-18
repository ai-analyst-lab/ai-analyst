---
title: One NSM vs. Growth Loops — funnel-tree topology vs. compounding-loop topology
type: debate
schema_version: 1
sources:
  - synthesis/debates.md
  - synthesis/counter-research.md
  - raw/atoms/concepts/concept-p011-l0260-one-nsm-per-product.md
  - raw/atoms/principles/principle-p011-l0262-one-nsm-per-pnl.md
  - raw/atoms/anti-patterns/anti-pattern-p041-l0955-insisting-on-multiple-nsms.md
  - raw/atoms/concepts/concept-p008-l0184-inputs-vary-by-context.md
  - raw/atoms/concepts/concept-p007-l0153-nsf-tree-is-scaffold.md
related:
  - wiki/concepts/north-star-metric.md
  - wiki/concepts/inputs.md
  - wiki/concepts/north-star-framework.md
  - wiki/anti-patterns/insisting-on-multiple-nsms.md
playbook_pages: [11, 7, 8]
tier: 2
confidence: medium
confidence_derivation: "Counter-research Tier-B source (Balfour/Winters/Kwok/Chen, Reforge Growth Loops piece + open Casey Winters First Round interview). Substantive disagreement about scoreboard topology, not just vocabulary."
contested: "Is a single NSM-tree the right organizing scoreboard, or do mature products need a loop-level metric architecture?"
current_consensus: weak
curator_status: approved
verified: true
created: 2026-05-26
updated: 2026-05-26
---

# One NSM vs. Growth Loops

## TL;DR
The playbook says one NSM per product, with inputs as the tree's branches. Reforge's growth-loops school (Balfour, Casey Winters, Kevin Kwok, Andrew Chen) argues mature products run on compounding loops — viral, content, paid, retention — each with its own diagnostic metric, and an NSM-tree is a CFO-friendly rollup that hides loop-level investment decisions. Both sides reject the "every team picks its KPI" pattern. Real disagreement is artifact-level: number-tree or loop diagram?

## Where they agree
- Pirate-metrics / "every team picks its own number" produces in-fighting and incoherent investment.
- Inputs vary by product context [concept-p008-l0184-inputs-vary-by-context]; loop-shaped input architectures are accommodated by the playbook in principle.
- For mature products, *some* shared structure is needed across loops/inputs to coordinate investment.

## Arguments for the playbook stance (one NSM)
- One NSM per product gives a single shared scoreboard that dissolves the apples-and-pants in-fighting Ted Clark's dialogue diagnoses [concept-p011-l0260-one-nsm-per-product].
- The NSM-tree is explicitly a scaffold for conversation, not a contract — inputs can be loop-shaped, retention-shaped, or funnel-shaped depending on the product [concept-p007-l0153-nsf-tree-is-scaffold].
- One-NSM-per-P&L bounds the framework: within a single P&L and customer base, the unifying number is well-defined; across P&Ls, multiple NSMs are appropriate [principle-p011-l0262-one-nsm-per-pnl].
- The anti-pattern of insisting-on-multiple-NSMs captures the failure mode of teams who refuse to converge [anti-pattern-p041-l0955-insisting-on-multiple-nsms].

## Arguments against (loops, not funnels)
- Balfour, Winters, Kwok, and Chen, *Growth Loops are the New Funnels* (Reforge): funnels are one-directional with no concept of reinvestment; mature products run on closed loops where outputs feed back into inputs. ([Reforge, auth-walled but indexed](https://www.reforge.com/blog/growth-loops) — Tier B; counter-research confirms canonical authorship.)
- Casey Winters in the open First Round Review interview: *"Unless there is a core network effect inside of a product, paid acquisition is a race to the bottom over time. … If you can create a content loop across the ways that you acquire and retain users and monetize your product, you're in good shape."* ([First Round Review](https://review.firstround.com/pinterest-and-grubhubs-former-growth-lead-on-building-content-loops/) — Tier B)
- The strong version: an NSM-tree at the top can look flat while one loop is accelerating and another is decaying — a state the loop-level view catches immediately and the rollup hides.
- A team that adopts the playbook literally will not naturally invest in loop-level diagnostics; they will optimize tree-branches without asking which loops are compounding.

## Current consensus
Weak — leans-playbook on artifact, leans-loops on diagnostic discipline. The two schools are not flatly opposed: the playbook's inputs layer can be loop-shaped in principle, and Reforge's loop architecture is compatible with rolling up to a single guiding number for board-level reporting. The substantive disagreement is what the team reviews weekly: a tree of inputs (playbook) or a diagram of loops (Reforge). For mature products with multiple compounding loops, the wiki could strengthen the playbook by explicitly noting that the input layer should be loop-level, not feature-level, and that a flat NSM with one accelerating loop and one decaying loop is the failure mode the tree must catch.

## Why this matters
Affects whether a growth team reviews "the metric tree" or "the loops" in its weekly. It also affects how you read a flat NSM with one loop accelerating and another decaying — the playbook's input view catches this if inputs are loop-shaped; a tree-with-feature-inputs view does not.

## See also
- [North Star Metric concept](../concepts/north-star-metric.md)
- [Inputs concept](../concepts/inputs.md)
- [Insisting on multiple NSMs (anti-pattern)](../anti-patterns/insisting-on-multiple-nsms.md)
