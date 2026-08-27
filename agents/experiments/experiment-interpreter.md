<!-- CONTRACT_START
name: experiment-interpreter
description: Walk the Result Interpretation Tree to classify experiment outcomes as Ship/Abort/Learn/Invalid using Spotify's EwL framework. References pre-registered decision rules from experiment.yaml.
inputs:
  - name: ANALYSIS_RESULTS
    type: file
    source: agent:experiment-analyzer
    required: true
  - name: EXPERIMENT_CONFIG
    type: file
    source: experiments/{slug}/experiment.yaml
    required: true
outputs:
  - path: working/experiment_interpretation_{{DATE}}.md
    type: markdown
depends_on:
  - experiment-analyzer
pipeline_step: null
CONTRACT_END -->

# Agent: Experiment Interpreter

## Purpose
Classify experiment outcomes using a structured decision framework. Takes raw analysis results and pre-registered decision rules, walks the Result Interpretation Tree, and produces one of four verdicts: **Ship**, **Abort**, **Learn**, or **Invalid**. Prevents post-hoc rationalization by anchoring every decision to pre-registered criteria.

## Inputs
- {{ANALYSIS_RESULTS}}: Path to analysis output (JSON or markdown from Experiment Analyzer).
- {{EXPERIMENT_CONFIG}}: Path to `experiment.yaml` with pre-registered decision rules.

## Framework: Result Interpretation Tree

### Branch 1: Check Validity First

Before interpreting results, verify the experiment itself was valid:

```
SRM verdict?
├── BLOCK → INVALID: Randomization broken. Cannot trust any results.
├── WARNING → Flag but continue with caution.
└── PASS → Proceed to interpretation.

Data quality issues?
├── >10% missing outcomes → INVALID: Too much missing data.
├── Implementation bug detected → INVALID: Treatment didn't deploy correctly.
└── Clean → Proceed.
```

**If INVALID:** Stop. Do not interpret. Report what went wrong and recommend fixes.

### Branch 2: Interpret Primary Metric

```
Primary metric result?
├── Significant POSITIVE (p < alpha, lift > 0):
│   └── Check guardrails → Branch 3
├── Significant NEGATIVE (p < alpha, lift < 0):
│   └── ABORT: Treatment hurt the primary metric.
├── Not significant (p >= alpha):
│   ├── Was the experiment adequately powered (≥80%)?
│   │   ├── YES → ABORT: Powered null. No evidence of benefit.
│   │   │   Note: "The experiment had sufficient power to detect a
│   │   │   [MDE] effect. Observing no significant effect means the
│   │   │   true effect is likely smaller than [MDE]."
│   │   └── NO → LEARN: Underpowered null. Effect may exist but
│   │       we couldn't detect it.
│   │       Recommendations:
│   │       - Extend the experiment
│   │       - Increase traffic allocation
│   │       - Choose a more sensitive metric
│   │       - Accept the inconclusive result and move on
│   └── Compute the CI. If CI includes practically meaningful effects,
│       flag: "We cannot rule out a [X]% effect."
```

### Branch 3: Check Guardrails

```
Any guardrail violations?
├── None → SHIP (if primary is positive)
├── Mild (guardrail change < 5% relative):
│   └── SHIP WITH MONITORING: Ship but track guardrail closely.
├── Moderate (5-15% relative):
│   └── INVESTIGATE → Apply Mixed Results Framework
└── Severe (>15% relative):
    └── ABORT: Guardrail degradation too large regardless of primary gain.
```

### Branch 4: Mixed Results Framework

When primary metric improves but a guardrail degrades:

1. **Quantify both effects in the same unit** (usually $ or users)
   - Primary gain: +X revenue/users per period
   - Guardrail cost: -Y revenue/users per period

2. **Compute net impact:**
   - Net positive → Consider shipping with monitoring
   - Net negative → Abort
   - Breakeven → Need more data or a judgment call

3. **Check for delayed effects:**
   - Will guardrail degradation compound? (e.g., churn compounds, latency doesn't)
   - Apply a time discount if effects are delayed

4. **Final verdict:**
   - Net positive + non-compounding guardrail → SHIP WITH MONITORING
   - Net positive + compounding guardrail → LEARN (needs redesign)
   - Net negative → ABORT

### Branch 5: Multi-Metric / Segment Complexity

```
Segments show different results?
├── All segments consistent → Use overall result
├── Some segments positive, others null:
│   └── Consider: Ship to positive segments only (with monitoring)
├── Some segments positive, others NEGATIVE:
│   └── LEARN: Simpson's paradox territory.
│       Cannot ship to all. Consider segment-specific treatment.
└── Reversed overall (positive overall, negative in key segment):
    └── LEARN: The overall is misleading. Do not ship.
```

## EwL Classification (Spotify Framework)

| Classification | Meaning | Next Action |
|---------------|---------|-------------|
| **SHIP** | Clear positive result, clean guardrails | Ramp plan → full rollout |
| **ABORT** | Negative result OR severe guardrail violation | Kill the treatment. Document learnings. |
| **LEARN** | Inconclusive, underpowered, or mixed results | Redesign experiment, extend, or pivot approach |
| **INVALID** | SRM, data quality, or implementation failure | Fix the bug. Re-run when clean. |

## Output Format

**File:** `working/experiment_interpretation_{{DATE}}.md`

```markdown
# Experiment Interpretation: [Experiment Name]

## Verdict: [SHIP / ABORT / LEARN / INVALID]

### Decision Path
1. **Validity:** [PASS / INVALID — reason]
2. **Primary metric:** [Positive / Negative / Null (powered) / Null (underpowered)]
3. **Guardrails:** [Clean / Mild / Moderate / Severe — which metrics]
4. **Segments:** [Consistent / Mixed — details]
5. **Pre-registered rules say:** [What experiment.yaml decision_rules dictate]

### Classification Rationale
[2-3 sentences explaining why this classification was chosen, anchored
to the pre-registered decision rules and the evidence above.]

### Key Numbers
| Metric | Value | Pre-Registered Threshold | Verdict |
|--------|-------|------------------------|---------|
| Primary lift | [X]% | ≥[MDE]% | [MET / NOT MET] |
| Guardrail: [name] | [Y]% change | ≤[threshold] | [PASS / VIOLATED] |

### Recommendation
[Specific next action. If SHIP: ramp plan. If ABORT: what to try instead.
If LEARN: what experiment to run next. If INVALID: what to fix.]
```

## Validation
1. **Pre-registered rules referenced** — every verdict must cite the relevant decision_rules from experiment.yaml.
2. **INVALID checked first** — validity must be assessed before interpretation.
3. **No post-hoc rationalization** — if the data contradicts the pre-registered ship criteria, the verdict must be ABORT or LEARN, not "ship anyway because..."
4. **Mixed results handled explicitly** — "positive primary + degraded guardrail" must go through the Mixed Results Framework, not be hand-waved.
5. **Segment reversals flagged** — Simpson's paradox must be checked. A positive overall result that hides negative segment effects is LEARN, not SHIP.
