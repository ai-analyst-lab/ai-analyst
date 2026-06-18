---
name: distribution-profiler
description: |
  Profile the statistical distribution of any data column and produce a complete
  analytical playbook — distribution identification, valid summary statistics,
  recommended tests, A/B testing guidance, and common traps to avoid.

  Use this skill whenever the user wants to understand a metric's distribution,
  check statistical assumptions, profile data before analysis, or figure out the
  right test for a metric. Trigger on phrases like "profile this column",
  "what distribution is this", "check the distribution", "is this normal",
  "what test should I use", "understand this metric", "distribution check",
  "data profiling", "statistical assumptions", "check assumptions before A/B test",
  "how is this data distributed", "profile the data", or any request to understand
  the shape/distribution of a numeric column before or during analysis.

  Also trigger proactively at the start of any analysis involving numeric metrics —
  profiling the distribution first prevents the #1 mistake in product analytics:
  using the wrong test because you assumed normality. When in doubt, profile first.
---

# Skill: Distribution Profiler

## Purpose

Take any numeric data column and produce a complete analytical playbook: identify
the distribution, compute the right summary statistics, recommend the correct
statistical tests, flag common traps, and give specific A/B testing guidance.

This skill exists because the #1 mistake in product analytics is assuming data is
normal when it's not — leading to wrong tests, false positives, and misleading
dashboards. The profiler catches this automatically.

## When to Use

- Before any analysis involving a numeric metric
- When the user asks "what distribution is this?" or "what test should I use?"
- When checking assumptions for an A/B test
- When a user says "profile" or "understand" a metric
- Proactively when you notice an analysis is about to use a t-test or OLS on
  data that hasn't been checked

## Invocation

`/distribution-profiler` — profile a data column's distribution

## Instructions

### Step 0: Identify the Target

Figure out what column/metric the user wants profiled. This could be:
- A specific column name (e.g., "total_amount from orders")
- A derived metric (e.g., "revenue per user", "sessions per user per month")
- A SQL query result

If unclear, ask. If the user hasn't specified, look at what they're analyzing
and suggest the most relevant metric to profile.

### Step 1: Extract the Data

Write and execute a Python script to extract the target column from the active
dataset. Use `helpers/data_helpers.py` to resolve the data source:

```python
from helpers.data_helpers import detect_active_source, check_connection
source = detect_active_source()
```

For MCP-connected warehouses (MotherDuck, Snowflake, Postgres), query via MCP.
For local DuckDB or CSV sources, connect directly in Python. Follow the Data
Source Fallback rules in CLAUDE.md.

For per-user metrics (revenue per user, sessions per user), aggregate first —
the unit of analysis matters. Profile the metric at the level it will be used
in the analysis (per-user, per-session, per-day, etc.).

### Step 2: Run the Diagnostic Pipeline

Write and execute a single Python script that computes all diagnostics.
The script should print results as structured output that you'll use to
build the report.

**Core diagnostics to compute:**

```python
import numpy as np
from scipy import stats

# --- Data basics ---
n = len(x)
n_zeros = (x == 0).sum()
pct_zeros = n_zeros / n
n_unique = len(np.unique(x))
is_integer = np.all(x == np.floor(x))
x_min, x_max = x.min(), x.max()

# --- Central tendency ---
mean = np.mean(x)
median = np.median(x)
mean_median_ratio = mean / median if median != 0 else float('inf')

# --- Spread ---
sd = np.std(x, ddof=1)
cv = sd / mean if mean != 0 else float('inf')
iqr = stats.iqr(x)
mad = stats.median_abs_deviation(x)

# --- Shape ---
skewness = stats.skew(x)
excess_kurtosis = stats.kurtosis(x, fisher=True)

# --- Distribution-specific diagnostics ---
vmr = np.var(x, ddof=1) / mean if mean != 0 else float('inf')  # for counts

# --- Formal tests ---
# Normality (on raw data)
if n <= 5000:
    shapiro_stat, shapiro_p = stats.shapiro(x)
anderson_result = stats.anderson(x, dist='norm')

# Normality of log-transformed data (if all positive)
if x_min > 0:
    log_x = np.log(x)
    shapiro_log_stat, shapiro_log_p = stats.shapiro(log_x)

# Bimodality
bimodality_coeff = (skewness**2 + 1) / (excess_kurtosis + 3)
```

**Key decision points the diagnostics must answer:**

1. **Is the data discrete (counts) or continuous?** → determines count vs continuous branch
2. **Is there zero-inflation?** → compare observed zero % to expected under fitted distribution
3. **Is it bounded (0,1)?** → beta distribution
4. **For counts: VMR near 1, >> 1, or < 1?** → Poisson vs NB vs Binomial
5. **For continuous positive: is log(x) normal?** → log-normal check
6. **Is it symmetric?** → normal check
7. **Is it bimodal?** → dip test + bimodality coefficient
8. **Is the tail extremely heavy?** → power law check (mean/median ratio, top 1% share)

### Step 3: Identify the Distribution

Use the diagnostic results and the decision flowchart from the reference guide
at `.knowledge/references/statistical-distributions-guide.md` (Section 15:
Distribution Identification Flowchart) to identify the most likely distribution.

Read the relevant section of the reference guide for the identified distribution
to get the full details on summary stats, tests, transformations, and A/B
implications.

**Report your confidence level:**
- **High confidence**: Formal tests agree, visual shape matches, domain makes sense
- **Moderate confidence**: Some tests agree, shape is consistent but not perfect
- **Low confidence**: Tests disagree or data doesn't fit cleanly into one family.
  In this case, report the top 2-3 candidates and what would distinguish them.

### Step 4: Generate the Report

Produce a clear, actionable report with these sections. Be specific and concrete —
use the actual numbers from the diagnostics, not generic advice.

#### Report Template

```
## Distribution Profile: [metric name]

### 1. Distribution: [Name] (confidence: high/moderate/low)

[One sentence: what distribution this is and why it makes sense for this metric.]
[If moderate/low confidence, list alternatives.]

### 2. Key Diagnostics

| Diagnostic | Value | What It Tells Us |
|-----------|-------|------------------|
| n | ... | Sample size |
| Mean | ... | ... |
| Median | ... | ... |
| Mean/Median ratio | ... | [>1.3 = right-skewed; near 1 = symmetric] |
| SD | ... | ... |
| MAD | ... | [Robust alternative to SD] |
| CV (SD/Mean) | ... | [~1 = exponential; >1.5 = heavy tail] |
| Skewness | ... | ... |
| Excess kurtosis | ... | ... |
| % zeros | ... | [if relevant] |
| VMR (Var/Mean) | ... | [for counts: ~1 Poisson, >>1 NB] |

**Shapiro-Wilk (normality):** p = ... → [reject/fail to reject]
**Shapiro-Wilk (log-normality):** p = ... → [reject/fail to reject] (if applicable)

### 3. Valid Summary Statistics

Use these to describe this metric:
- **Central tendency:** [median / geometric mean / mean — with reasoning]
- **Spread:** [IQR / MAD / CV — with reasoning]
- **Avoid:** [what NOT to report and why]

### 4. Recommended Statistical Tests

| Purpose | Recommended Test | Why |
|---------|-----------------|-----|
| Compare two groups | ... | ... |
| Regression | ... | ... |
| Confidence intervals | ... | ... |

### 5. A/B Testing Playbook

- **Recommended approach:** [specific method]
- **Sample size impact:** [how this distribution affects required n]
- **Effect size measure:** [what to use instead of / in addition to Cohen's d]
- **Common traps:** [specific warnings for this distribution]
- **Practical tip:** [one concrete thing to do]

### 6. If You Need to Transform

[Recommended transformation and when to use it vs. GLM vs. non-parametric]
```

### Step 5: Generate a Diagnostic Chart

Create a matplotlib visualization with 4 panels:

1. **Histogram with KDE** — shows the shape of the distribution
2. **Q-Q plot** (against normal) — shows departure from normality
3. **Box plot** — shows median, IQR, and outliers
4. **Log-scale histogram** (if data is positive and skewed) — shows whether
   log-transform normalizes the data

Save as a PNG file. Use `plt.savefig()` and `plt.close()` to avoid display issues.

### Step 6: Offer Next Steps

After presenting the report, suggest what the user might want to do next:
- "Want me to run the recommended A/B test on this metric?"
- "Should I profile another column for comparison?"
- "Want to see how this distribution changes across user segments?"

## Reference

The comprehensive distribution reference guide is at:
`.knowledge/references/statistical-distributions-guide.md`

This 1,700+ line guide covers 12 distributions plus zero-inflated models,
with detection heuristics, valid summary statistics, recommended tests,
transformations, A/B testing implications, and Python code for each.

**When to read it:** After identifying the distribution in Step 3, read the
specific section for that distribution to get detailed guidance. Don't load
the entire guide — read only the relevant section (each is ~100 lines).

Key sections:
- Sections 1-12: Individual distribution cards (A through G for each)
- Section 13: Zero-inflated distributions
- Section 14: Practical guidance (t-test rules, family tree, effect sizes, censoring)
- Section 15: Quick-reference lookup tables
- Appendix: Quick diagnostic ratios

## Rules

1. Always show your work — print the diagnostic numbers, don't just state conclusions
2. Always generate the 4-panel chart — visual evidence is as important as the numbers
3. Never assume normality without testing — that's the whole point of this skill
4. If the distribution is unclear, say so — report multiple candidates with reasoning
5. Use the reference guide for detailed recommendations, not your own memory
6. Profile at the right level of aggregation — per-user, per-session, etc.
7. Warn loudly if the user is about to use a test that's wrong for the distribution
