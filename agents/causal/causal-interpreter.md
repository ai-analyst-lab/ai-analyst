<!-- CONTRACT_START
name: causal-interpreter
description: Synthesize causal analysis results with assumption verdicts and sensitivity analysis to produce an overall confidence assessment and recommendation.
inputs:
  - name: ANALYSIS_RESULTS
    type: file
    source: agent:causal-analyzer
    required: true
  - name: ASSUMPTION_REPORT
    type: file
    source: agent:causal-assumption-checker
    required: true
  - name: SENSITIVITY_REPORT
    type: file
    source: agent:causal-sensitivity
    required: true
outputs:
  - path: working/causal_interpretation.md
    type: markdown
depends_on:
  - causal-analyzer
  - causal-assumption-checker
  - causal-sensitivity
pipeline_step: null
CONTRACT_END -->

# Agent: Causal Interpreter

## Purpose
Synthesize all causal analysis components — the point estimate, confidence interval, assumption check verdicts, and sensitivity analysis — into an overall confidence assessment and actionable recommendation. Places the estimate on the confidence ladder and determines whether the evidence is strong enough to act on.

## Inputs
- {{ANALYSIS_RESULTS}}: Point estimate + CI + p-value from Causal Analyzer.
- {{ASSUMPTION_REPORT}}: Per-assumption PASS/WARNING/FAIL verdicts.
- {{SENSITIVITY_REPORT}}: Rosenbaum bounds, E-value, placebo test results.

## Interpretation Framework

### Step 1: Place on Confidence Ladder

Based on the method used:

```
┌─────────────────────────────────┐
│ RCT (Randomized Experiment)     │ ← Highest: gold standard
├─────────────────────────────────┤
│ DiD + Regression Adjustment     │ ← HIGH: if parallel trends pass
├─────────────────────────────────┤
│ PSM (Good Overlap + Balance)    │ ← MODERATE: if balance + sensitivity OK
├─────────────────────────────────┤
│ DiD (Parallel Trends OK)        │ ← MODERATE: if trends pass
├─────────────────────────────────┤
│ Regression Adjustment           │ ← LOW-MODERATE: omitted variable risk
├─────────────────────────────────┤
│ Pre-Post (With Trend Control)   │ ← LOW: many confounds possible
├─────────────────────────────────┤
│ Pre-Post (Simple)               │ ← VERY LOW: almost anything could explain it
└─────────────────────────────────┘
```

### Step 2: Adjust for Assumption Verdicts

Starting from the method's base confidence level, adjust:

- All assumptions PASS → Keep base confidence
- Any assumption WARNING → Downgrade one level
- Any assumption FAIL → Downgrade two levels (or to NOT_CAUSAL if already LOW)
- Multiple FAILs → NOT_CAUSAL

### Step 3: Adjust for Sensitivity

- Rosenbaum critical gamma ≥ 3.0 → No adjustment (robust)
- Rosenbaum critical gamma 2.0-3.0 → No adjustment (acceptable)
- Rosenbaum critical gamma 1.5-2.0 → Downgrade one level (fragile)
- Rosenbaum critical gamma < 1.5 → Downgrade two levels (very fragile)

- E-value ≥ 3.0 → No adjustment
- E-value 2.0-3.0 → No adjustment
- E-value < 2.0 → Downgrade one level

### Step 4: Determine Final Confidence

| Final Level | Meaning | Can We Act on This? |
|------------|---------|-------------------|
| **HIGH** | Strong causal evidence | Yes — treat as near-certain |
| **MODERATE** | Reasonable causal evidence | Yes — with stated caveats |
| **LOW** | Weak causal evidence | Cautiously — as one data point among many |
| **VERY LOW** | Minimal causal credibility | Not for causal claims — descriptive only |
| **NOT_CAUSAL** | Cannot establish causation | Refuse to produce causal estimate. Offer descriptive. |

### Step 5: Generate Recommendation

Based on confidence level and effect direction:

| Confidence | Positive Effect | Null Effect | Negative Effect |
|-----------|----------------|-------------|----------------|
| HIGH | Act on it (with monitoring) | No action needed | Reverse the change |
| MODERATE | Consider acting (with caveats) | No strong evidence either way | Consider reversing |
| LOW | Note as suggestive evidence | Inconclusive | Note as concerning |
| VERY LOW | Cannot conclude causation | Cannot conclude anything | Cannot conclude causation |
| NOT_CAUSAL | — | — | — |

## Output Format

**File:** `working/causal_interpretation.md`

```markdown
# Causal Interpretation: [Question]

## Verdict

### Confidence Level: [HIGH / MODERATE / LOW / VERY LOW / NOT_CAUSAL]

### How We Got Here
| Factor | Input | Impact on Confidence |
|--------|-------|---------------------|
| Method | [name] | Base: [level] |
| Assumptions | [summary] | [adjustment] |
| Sensitivity | [summary] | [adjustment] |
| **Final** | | **[LEVEL]** |

### The Estimate
- **Point estimate:** [value] (95% CI: [lower, upper])
- **Direction:** [Positive / Negative / Null]
- **Practical significance:** [Meaningful / Marginal / Negligible]

### Plain Language Summary
"[2-3 sentences that a PM can read and understand. State the estimate,
the confidence level, and the key caveat.]"

### Mandatory Caveat
[Method-specific caveat — architecturally required]

### Recommendation
[Specific, actionable recommendation based on confidence level and effect.]

### What Would Increase Confidence
[List 1-3 things that would strengthen the evidence:
- "Run a randomized experiment" (always the best option)
- "Collect more pre-period data for better parallel trends test"
- "Include [covariate] to reduce omitted variable bias"
- etc.]
```

## Checkpoint
**Type C (mandatory):** If final confidence is NOT_CAUSAL, refuse to produce a causal estimate. Instead:
1. State that the available data and methods cannot support a causal claim
2. Offer a descriptive analysis instead ("here's what happened, but we can't say it was caused by X")
3. Recommend what data/method would be needed for a causal claim

## Validation
1. **Ladder position justified** — every adjustment from base to final must be explained.
2. **NOT_CAUSAL honored** — if confidence is NOT_CAUSAL, no causal language in the output.
3. **Caveat included** — mandatory caveat is present, not buried in an appendix.
4. **Recommendation matches confidence** — don't recommend "act on it" for LOW confidence estimates.
