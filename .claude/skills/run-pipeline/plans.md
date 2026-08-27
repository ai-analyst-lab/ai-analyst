# Execution Plans

Execution plans define which agents to include in a pipeline run. Each plan is an allow-list: agents not in the plan are skipped. Dependencies are still respected — if a skipped agent's output is needed, the pipeline will warn.

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
```

## Plan: quick_chart

**Use when:** User just wants a chart from existing analysis. Skips framing and analysis.

```yaml
agents:
  - chart-maker
  - visual-design-critic
checkpoints: [3]
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
requires_context:
  - working/investigation_*.md OR outputs/analysis_report_*.md
```

## Plan Selection Logic

1. If user passes `plan=X`, use that plan
2. If user says "just make a chart" or similar, auto-select `quick_chart`
3. If user says "refresh the deck" or "rebuild slides", auto-select `refresh_deck`
4. If user says "validate" or "re-check", auto-select `validate_only`
5. If Question Router classifies as L3/L4, auto-select `deep_dive`
6. Default: `full_presentation`

## Custom Plans

Users can specify an inline agent list:
```
/run-pipeline agents=question-framing,hypothesis,data-explorer,cross-verification
```

This creates an ad-hoc plan with only the listed agents. Dependency warnings still apply.
