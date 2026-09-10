# Execution Plans

Execution plans select the workers and requested deliverables. The execution
compiler requires explicit input bindings. If an omitted producer supplies a
required input, bind an appropriate existing artifact with its identity and purpose
or include the producer. A structural graph warning is not permission to execute
without the input.

## Plan: full_presentation (default)

**Use when:** End-to-end analysis from business question to validated slide deck.

```yaml
agents:
  - question-framing
  - hypothesis
  - data-explorer
  - cross-verification
  - descriptive-analytics   # or overtime-trend or cohort-analysis
  - root-cause-investigator
  - validation
  - opportunity-sizer
  - story-architect
  - narrative-coherence-reviewer
  - chart-maker
  - visual-design-critic
  - storytelling
  - deck-creator
  - visual-design-critic-slides
  - close-the-loop
  - comms-drafter        # non-critical — pipeline continues if this fails
checkpoints: [1, 2, 2.5, 3, 4]
deliverables: [deck-creator.result, close-the-loop.result]
```

## Plan: deep_dive

**Use when:** Thorough analysis without deck creation. Stops after opportunity sizing.

```yaml
agents:
  - question-framing
  - hypothesis
  - data-explorer
  - cross-verification
  - descriptive-analytics
  - root-cause-investigator
  - validation
  - opportunity-sizer
checkpoints: [1, 2]
deliverables: [cross-verification.result, validation.result]
```

## Plan: quick_chart

**Use when:** User just wants a chart from existing analysis. Skips framing and analysis.

```yaml
agents:
  - chart-maker
  - visual-design-critic
checkpoints: [3]
deliverables: [chart-maker.result]
skip_validation: true
requires_context:
  - working/storyboard_*.md OR explicit chart spec from user
```

## Plan: refresh_deck

**Use when:** Re-generate the deck from existing storyboard and charts. Skips analysis.

```yaml
agents:
  - storytelling
  - deck-creator
  - visual-design-critic
checkpoints: [4]
deliverables: [deck-creator.result]
requires_context:
  - working/storyboard_*.md
  - outputs/charts/*.png
```

## Plan: validate_only

**Use when:** Re-run validation on existing analysis. Does not produce new analysis.

```yaml
agents:
  - validation
checkpoints: []
deliverables: [validation.result]
requires_context:
  - working/investigation_*.md OR outputs/analysis_report_*.md
```

## Plan Selection Logic

Numeric `checkpoints` above are legacy presentation references, not executable
approval gates. The controller validates every declared artifact. Add explicit
`approval_gates` with `id`, `after`, and `before` to a reviewed request when human
approval is needed. These are local approval records, not authenticated identities.
Never describe artifact validation alone as validation of analytical correctness.

`deliverables` is the machine-readable completion boundary. `result` means the
worker's first registered output; subsequent outputs are `artifact_2`, etc.
All declared worker outputs are required by the new controller. Wildcards and
unresolved variables must be bound to explicit paths before a run is created.
An optional worker can fail without blocking consumers whose required inputs
remain available; the final run is then degraded, not fully successful.

1. If user passes `plan=X`, use that plan
2. If user says "just make a chart" or similar, auto-select `quick_chart`
3. If user says "refresh the deck" or "rebuild slides", auto-select `refresh_deck`
4. If user says "validate" or "re-check", auto-select `validate_only`
5. If Question Router classifies as L3/L4, auto-select `deep_dive`
6. Default: `full_presentation`

## Custom Plans

An inline agent list can express the user's proposed scope:
```
/run-pipeline agents=question-framing,hypothesis,data-explorer,cross-verification
```

It is not an executable workflow by itself. Translate that proposal into the
explicit definition and input format in `docs/PIPELINE-CONTROLLER.md`, including
required inputs, producer bindings, output paths, dependencies and deliverables.
Review and validate the definition before creating a run. Never substitute global
files or skip required inputs just to make the proposed list execute.
