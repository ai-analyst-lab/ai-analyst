# Causal Analysis Prompt Templates

Three annotated prompt templates for the most common causal inference scenarios. Each prompt is designed to run with the AI Analyst's causal inference toolkit (`helpers/experiment_stats/causal/`).

---

## Prompt 1: Pre-Post Analysis

**When to use:** A change shipped with no control group. You have before/after data.

```
I need to analyze the impact of [CHANGE DESCRIPTION] that launched on [DATE].

Data: [DATASET PATH]
- Pre-period: [START DATE] to [DAY BEFORE LAUNCH]
- Post-period: [LAUNCH DATE] to [END DATE]
- Primary metric: [METRIC NAME] (e.g., daily conversion rate)
- Time granularity: [daily / weekly]

Please run a pre-post analysis:
1. Plot the metric over time with the intervention date marked
2. Compare pre-period average vs post-period average
3. Control for day-of-week seasonality if daily data
4. Estimate the treatment effect with confidence interval
5. Flag any concurrent events that could confound the result
6. State the mandatory caveat: this assumes nothing else changed

Use: from helpers.experiment_stats.causal import pre_post_analysis
```

### What the AI Analyst does:
- Calls `pre_post_analysis(pre_data, post_data, covariates=['day_of_week'])`
- Produces OLS regression controlling for trend and seasonality
- Returns: estimated effect, CI, p-value, R-squared
- Generates time series chart with intervention line

### Key caveat (non-negotiable):
> "This pre-post analysis assumes nothing else changed during this period. Any concurrent event — a marketing campaign, a competitor launch, a seasonal shift — could explain part or all of this result."

---

## Prompt 2: Difference-in-Differences (DiD)

**When to use:** A change affected one group but not another (e.g., iOS users got a feature, Android didn't).

```
I need to analyze the causal impact of [FEATURE/CHANGE] using DiD.

Data: [DATASET PATH]
- Treatment group: [WHO WAS AFFECTED] (e.g., iOS users)
- Control group: [WHO WAS NOT AFFECTED] (e.g., Android users)
- Pre-period: weeks [X] to [Y]
- Post-period: weeks [Y+1] to [Z]
- Outcome metric: [METRIC] (e.g., weekly orders)

Please run a DiD analysis:
1. First, test the parallel trends assumption on pre-period data
2. If parallel trends hold, estimate the DiD treatment effect
3. Plot pre/post trends for both groups
4. Run an event study if enough time periods exist
5. Report the effect with confidence interval and significance
6. State the mandatory caveat about the parallel trends assumption

Use: from helpers.experiment_stats.causal import did_basic, parallel_trends_test
```

### What the AI Analyst does:
- Calls `parallel_trends_test(df, treat_col, time_col, outcome_col)` — MUST PASS before proceeding
- Calls `did_basic(df, treat_col='treated', post_col='post', outcome_col='orders')`
- Wraps `pyfixest` for fixed-effects DiD estimation
- Returns: DiD estimate, CI, p-value, parallel trends test result
- Generates event study plot if >= 4 pre-periods

### Key caveat (non-negotiable):
> "This DiD estimate assumes the control group (Android) would have followed the same trend as the treatment group (iOS) in the absence of the feature. This is plausible based on pre-period trends but unprovable."

---

## Prompt 3: Propensity Score Matching (PSM)

**When to use:** Users self-selected into a treatment (e.g., adopted a feature). No randomization, no natural experiment.

```
I need to estimate the causal effect of [FEATURE ADOPTION / BEHAVIOR] on [OUTCOME].

Data: [DATASET PATH]
- Treatment indicator: [COLUMN] (e.g., heavy_usage, adopted_feature)
- Outcome: [COLUMN] (e.g., retained_30d, orders_30d)
- Potential confounders: [COLUMNS] (e.g., job_role, tenure_months, plan_type)

Please run a PSM analysis:
1. Fit a propensity score model (logistic regression) using the confounders
2. Check common support — are there comparable users in both groups?
3. Match treated users to untreated users with similar propensity scores
4. Check balance — are matched groups similar on all confounders? (SMD < 0.1)
5. Estimate the ATT (Average Treatment Effect on the Treated) with CI
6. Run sensitivity analysis — how strong would an unmeasured confounder need to be?
7. State the mandatory caveat about unobserved confounders

Use: from helpers.experiment_stats.causal import propensity_match, balance_table, love_plot
     from helpers.experiment_stats.causal import rosenbaum_bounds, e_value
```

### What the AI Analyst does:
- Calls `propensity_match(df, treat_col, covariates, method='nearest')` — sklearn logistic + matching
- Calls `balance_table(matched_df, covariates, treat_col)` — checks SMD < 0.1 for all covariates
- Calls `love_plot(balance_result)` — visual balance diagnostic
- Estimates ATT from matched sample
- Calls `rosenbaum_bounds(matched_outcome, gammas=[1.0, 1.5, 2.0, 3.0])` — sensitivity
- Calls `e_value(risk_ratio)` — minimum confounder strength to nullify result

### Key caveat (non-negotiable):
> "PSM controls for observed confounders only (job_role, tenure, plan_type). Unmeasured factors — motivation, team culture, onboarding quality — could still bias this estimate. The sensitivity analysis suggests an unmeasured confounder would need to be [X]x stronger than our strongest measured confounder to nullify this result."

---

## Choosing the Right Method

```
Can you randomize?
├── YES → A/B test (/experiment)
└── NO
    ├── Is there a comparison group that wasn't affected?
    │   ├── YES → DiD (Prompt 2)
    │   └── NO
    │       ├── Can you match treated/untreated users on observables?
    │       │   ├── YES → PSM (Prompt 3)
    │       │   └── NO → Pre-Post (Prompt 1) — weakest causal evidence
    │       └── Do you have pre/post time series data?
    │           ├── YES → Pre-Post (Prompt 1)
    │           └── NO → Descriptive only (no causal claim possible)
```

**Use `/causal select` to walk through this decision tree interactively.**
