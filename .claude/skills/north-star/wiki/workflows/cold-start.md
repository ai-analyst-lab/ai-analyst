---
title: "Cold Start — Designing an NSM from Scratch"
type: workflow
schema_version: 1
workflow_id: cold-start
estimated_lookups: 8
steps_file: _steps/cold-start.yaml
sources:
  - raw/atoms/workflow-steps/workflow-step-p010-l0238-cold-start-step-1-classify-the-game.md
  - raw/atoms/workflow-steps/workflow-step-p035-l0786-cold-start-step-2-surface-beliefs.md
  - raw/atoms/workflow-steps/workflow-step-p037-l0838-cold-start-step-3-connect-to-vision.md
  - raw/atoms/workflow-steps/workflow-step-p038-l0890-cold-start-step-4-key-value.md
  - raw/atoms/workflow-steps/workflow-step-p019-l0447-cold-start-step-5-draft-statement.md
  - raw/atoms/workflow-steps/workflow-step-p024-l0537-cold-start-step-6-name-and-define.md
  - raw/atoms/workflow-steps/workflow-step-p027-l0621-cold-start-step-7-mind-map-inputs.md
  - raw/atoms/workflow-steps/workflow-step-p032-l0712-cold-start-step-8-test-inputs.md
related:
  - wiki/concepts/games.md
  - wiki/concepts/beliefs.md
  - wiki/concepts/product-vision.md
  - wiki/concepts/key-value-exchanges.md
  - wiki/concepts/statement-exercise.md
  - wiki/concepts/north-star-metric.md
  - wiki/concepts/inputs.md
  - wiki/concepts/input-tests-greenfield-and-roadmap.md
  - wiki/anti-patterns/rushing-statement-exercise.md
  - wiki/anti-patterns/inputs-wrong-granularity.md
  - wiki/workflows/audit.md
playbook_pages: [10, 19, 20, 24, 27, 32, 35, 37, 38]
tier: 1
confidence: high
confidence_derivation: "All 8 step atoms are Tier 1, high-confidence, reconciliation_status reconciled, cross-extractor agreement ≥3/3, and trace directly to Chapters 2-4 of the playbook."
curator_status: pending
verified: false
created: 2026-05-26
updated: 2026-05-26
---

# Cold Start — Designing an NSM from Scratch

## TL;DR
Walk a team from "no NSM" to a passing-7/7 North Star Metric, 3-6 inputs, and a stress-tested metric tree. Eight steps, ~90 minutes for the workshop core. Run this when you have a product but no documented NSM, or when the team is misaligned on what "winning" means. Output: a named, defined NSM plus an inputs map ready for socialization.

## When to use
- You have a product but no documented North Star Metric
- The team is building product but mis-aligned on what "winning" means
- You're starting a quarterly planning cycle and need a multi-quarter anchor
- A new product line, vertical, or business unit needs its own NSM

## When NOT to use
- You already have an NSM that's working — use [audit](audit.md) instead
- Pre-product-market-fit (NSM may be premature; debate is open)
- One-person team (overhead exceeds value)
- You only need to triage candidate metrics — use [vanity-triage](vanity-triage.md)

## Steps

1. **Classify the game** — Decide whether your product plays the [attention, transaction, or productivity game](../concepts/games.md). This is the playbook's explicit "before we dig in" gate. One classification frames every later candidate. Source: `workflow-step-p010-l0238-cold-start-step-1-classify-the-game`. ~5 min.

2. **Surface beliefs and biases** — Each teammate independently fills the five [belief templates](../concepts/beliefs.md) (competition, technology change, why-we-win, market behavior, customer-need tradeoffs) so latent assumptions are visible before drafting anything. Source: `workflow-step-p035-l0786-cold-start-step-2-surface-beliefs`. ~15 min.

3. **Connect to product vision** — Review your existing [product vision statement](../concepts/product-vision.md) (or draft one via the Geoffrey Moore template) and extract distinctness/foundational claims the NSM must remain consistent with. Source: `workflow-step-p037-l0838-cold-start-step-3-connect-to-vision`. ~10 min.

4. **Identify key value exchanges** — Map customer journeys and isolate 3-6 essential moments where customers derive value. These are the candidate behaviors the NSM should reflect. Include exchanges that happen outside the product. Source: `workflow-step-p038-l0890-cold-start-step-4-key-value`. ~15 min.

5. **Run the statement exercise** — Fill the [four-tier worksheet](../concepts/statement-exercise.md) top-down (statement → inputs → opportunities → interventions) qualitatively, before any numbers. Anchors thinking on ideas, not metrics. If you skip this, see [rushing-statement-exercise](../anti-patterns/rushing-statement-exercise.md). Source: `workflow-step-p019-l0447-cold-start-step-5-draft-statement`. ~20 min.

6. **Name and define the NSM** — Convert the qualitative statement into a pithy named metric plus a precise measurement definition. Use the template "Our North Star Metric is called X, which we define as Y." Apply the same name+definition treatment to each input. Source: `workflow-step-p024-l0537-cold-start-step-6-name-and-define`. ~15 min.

7. **Mind-map the inputs** — Brainstorm-then-refine [input metrics](../concepts/inputs.md) in three passes: (a) messy sticky-note dump, (b) cluster into 5-6 high-level inputs, (c) attach a precise measurement to each. Template: "I believe that [NSM] is a function of [X, Y, AND Z]." Watch for [inputs-wrong-granularity](../anti-patterns/inputs-wrong-granularity.md). Source: `workflow-step-p027-l0621-cold-start-step-7-mind-map-inputs`. ~20 min.

8. **Stress-test the inputs** — Run [Greenfield + roadmap check](../concepts/input-tests-greenfield-and-roadmap.md). Greenfield: brainstorm opportunities for two minutes per input — run-out-of-ideas means too narrow, swimming-in-broad-ideas means too high-level. Roadmap check: trace every current initiative to an input; missing links signal a missing input or wasted work. Source: `workflow-step-p032-l0712-cold-start-step-8-test-inputs`. ~15 min.

## Outputs

What the user walks away with:
- A named North Star Metric (subject + verb + object) with a precise measurement definition
- 3-6 input metrics with names, definitions, and an independence check
- Notes from belief-surfacing and vision-connection (working assumptions the NSM rests on)
- A list of 3-6 key value exchanges grounding the metric in customer behavior
- A Greenfield + roadmap stress-test verdict per input

## See also

- [Audit existing NSM](audit.md) — once drafted, run the 7-checklist
- [Vanity Metric Triage](vanity-triage.md) — for sorting candidate metrics
- [Statement exercise concept](../concepts/statement-exercise.md)
- [Inputs concept](../concepts/inputs.md)
- Machine contract: [`_steps/cold-start.yaml`](_steps/cold-start.yaml)
