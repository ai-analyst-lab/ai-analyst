---
title: Connecting Features to Inputs Without Defining the Opportunity
type: anti-pattern
schema_version: 1
sources:
  - raw/atoms/anti-patterns/anti-pattern-p048-l1135-features-to-inputs-without-opportunity.md
related:
  - wiki/concepts/levels-of-bets.md
  - wiki/anti-patterns/no-enabling-constraints.md
  - wiki/anti-patterns/organize-around-tech-stack.md
playbook_pages: [32, 48, 51]
anti_pattern_id: features-without-opportunity
severity: medium
tier: 1
confidence: high
confidence_derivation: "Source atom tier 1, confidence high; explicitly named as implementation trap #1 in Chapter 6."
curator_status: approved
verified: true
created: 2026-05-26
updated: 2026-05-26
---

# Connecting features to inputs without defining the opportunity

## TL;DR
Teams that map intervention-level features directly to inputs — skipping the Level 2 opportunity layer in between — produce arbitrary shipping plans rather than reasoned bets. The team can name the feature but not the opportunity it exploits.

## Spot signals
- Roadmap items map directly to inputs with no opportunity statement in between.
- The team cannot articulate "the opportunity we're betting on" — only "the feature we're building."
- Multiple features are pursued for the same input without comparing the opportunities behind them.
- Squad goals jump straight from input to feature.

## Fix recipe
1. Introduce the Level 2 (opportunities) bet layer between inputs and interventions (p. 51 levels of bets).
2. For each input, list the leverage points/opportunities BEFORE listing the features that exploit them.
3. Use the opportunity statement template (p. 32): "We have an opportunity to improve [AN INPUT] if we could [SOME CHANGE IN BEHAVIOR, OUTCOME]. Potential interventions to exploit that opportunity include [FEATURES, EXPERIMENTS, ETC.]."
4. Force-rank opportunities by likelihood × influence on the input.

## Examples
- One of three implementation traps named together on p. 48: this is trap #1, [no enabling constraints](no-enabling-constraints.md) is #2, [organize around tech stack](organize-around-tech-stack.md) is #3. They commonly co-occur.
