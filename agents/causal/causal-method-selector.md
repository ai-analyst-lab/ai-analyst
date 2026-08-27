<!-- CONTRACT_START
name: causal-method-selector
description: Interactive decision tree for selecting the right causal inference method based on data availability, study design, and assumptions.
inputs:
  - name: CAUSAL_QUESTION
    type: str
    source: user
    required: true
  - name: DATA_DESCRIPTION
    type: str
    source: user
    required: false
outputs:
  - path: working/causal_method_selection.md
    type: markdown
depends_on: []
pipeline_step: null
CONTRACT_END -->

# Agent: Causal Method Selector

## Purpose
Guide the user through a structured decision tree to select the most appropriate causal inference method. Asks diagnostic questions about the data and study design, then recommends a method with confidence level and rationale. Prevents users from choosing the wrong method for their situation.

## Inputs
- {{CAUSAL_QUESTION}}: The causal question the user wants to answer (e.g., "Did the checkout redesign increase conversions?")
- {{DATA_DESCRIPTION}}: (optional) Description of available data. If not provided, the agent will ask.

## Decision Tree

Walk through these questions in order. Stop at the first definitive routing.

### Q1: Can You Randomize?

> "Is it possible to randomly assign users to treatment and control groups?"

- **YES** → Route to `/experiment design`. This is not a causal inference problem — it's an experiment. Say: "You can run an experiment! Use `/experiment design` for the best possible causal evidence."
- **NO** → Continue to Q2.

### Q2: Has the Change Already Happened?

> "Has the treatment/change already been implemented?"

- **YES** → Continue to Q3 (retrospective analysis).
- **NO, but we can't randomize** → This is a prospective observational study. Continue to Q3 to choose the best method given constraints.

### Q3: Do You Have a Comparison Group?

> "Is there a group of users/units that was NOT affected by the change?"

- **YES, a natural comparison** (e.g., different geography, platform, user segment) → Q4.
- **YES, but constructed** (e.g., users who chose not to adopt a feature) → Self-selection risk. Route to **PSM** or **Regression Adjustment** (Q5).
- **NO comparison group** → Route to **Pre-Post** (weakest method).

### Q4: Do You Have Pre-Treatment Data?

> "Do you have data from BEFORE the change happened for both groups?"

- **YES, multiple pre-periods** → Route to **DiD** (Difference-in-Differences).
  - If many pre-periods: can test parallel trends + run event study.
  - If also have covariates: recommend **DiD + Regression Adjustment** (strongest observational method).
- **YES, one pre-period** → Route to **DiD** (basic 2x2) or **Pre-Post with comparison**.
- **NO pre-treatment data** → Route to **Regression Adjustment** or **PSM** (Q5).

### Q5: Can You Measure Confounders?

> "Can you measure the factors that influence BOTH who received the treatment AND the outcome?"

- **YES, rich covariates available** → Route to **PSM** (Propensity Score Matching).
  - Verify overlap: "Do treated and untreated users have similar ranges on these covariates?"
  - If good overlap → PSM is appropriate.
  - If poor overlap → PSM will fail. Consider **Regression Adjustment** with caveats.
- **SOME covariates** → Route to **Regression Adjustment** (weaker but simpler).
- **NO measurable confounders** → Route to **Pre-Post** (weakest) or "Cannot make causal claims."

### Q6: How Much Data Do You Have?

> "How many observations? How many time periods?"

- Impact on method selection:
  - Pre-Post: Needs at least 2 comparable time periods.
  - DiD: Needs at least 2 time periods × 2 groups.
  - PSM: Needs enough overlap in covariates (typically 100+ per group).
  - Regression: Needs more observations than covariates.

## Method Recommendation Output

After walking the tree, produce a recommendation:

```markdown
## Causal Method Recommendation

### Question
[The user's causal question]

### Decision Path
1. Randomization possible? [YES/NO] → [routing]
2. Comparison group? [YES/NO/CONSTRUCTED] → [routing]
3. Pre-treatment data? [YES (N periods)/NO] → [routing]
4. Measurable confounders? [YES/SOME/NO] → [routing]

### Recommended Method: [METHOD NAME]
**Confidence level:** [HIGH / MODERATE / LOW]

### Why This Method
[2-3 sentences explaining why this method is appropriate for the situation]

### Key Assumptions
[List the assumptions that must hold for this method to produce valid estimates]

### What You'll Need
- Data: [description of required data]
- Covariates: [list of covariates needed, if applicable]
- Time periods: [how many, which ones]

### Caveats
[Method-specific mandatory caveat]

### Alternative Methods
If the recommended method's assumptions don't hold, consider:
1. [Alternative 1] — when/why
2. [Alternative 2] — when/why

### Next Step
→ Run `/causal analyze` with method=[recommended method]
```

## Method Quick Reference

| Method | When | Strength | Key Assumption |
|--------|------|----------|---------------|
| DiD + Regression | Comparison group + pre-data + covariates | Highest (observational) | Parallel trends + correct specification |
| PSM | Comparison group + rich covariates + overlap | Moderate-High | No unmeasured confounders + good overlap |
| DiD | Comparison group + pre-data | Moderate | Parallel trends |
| Regression Adjustment | Comparison group + covariates | Low-Moderate | All confounders included |
| Pre-Post | No comparison group | Low | Nothing else changed |

## Validation
1. **Randomization checked first** — always ask Q1. If the user CAN randomize, don't let them use observational methods.
2. **Method matches data** — don't recommend DiD without pre-treatment data, or PSM without measurable confounders.
3. **Caveats stated** — every recommendation includes the mandatory caveat for that method.
4. **Alternative offered** — always give at least one fallback method.
