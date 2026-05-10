# Skill: Target Engineering

## Purpose

Procedure for constructing a regression or classification target from raw
data. Covers forward-shifting (avoiding leakage), external/market adjustment,
clipping vs winsorization, skew diagnostics, and class balance profiling.
Target design decisions have outsized impact on model utility — this skill
ensures they are made deliberately, not ad hoc.

## When to Use

- Defining a new target variable from raw data
- Modifying an existing target (changing horizon, adding adjustment)
- Debugging unexpected model behavior (target shape may be the cause)
- Reviewing a model's target design during evaluation

## Instructions

### Step 1: Define the Prediction Task

Before touching any data, answer these questions explicitly:

```
## Target Definition
| Question | Answer |
|----------|--------|
| What are we predicting? | e.g., "6-month forward project growth rate" |
| What entity? | e.g., "account (entity_id)" |
| What time grain? | e.g., "monthly snapshots" |
| What horizon? | e.g., "6 months forward from snapshot" |
| What is the operational use? | e.g., "flag accounts predicted to decline" |
| Regression or classification? | e.g., "regression with binary binning" |
| What does 0 mean? | e.g., "no growth (flat)" |
```

**Severity:**
- BLOCKER: If "what decision does this inform?" has no clear answer, stop.
  A target without a use case produces a model without a purpose.

### Step 2: Construct the Raw Target

Build the target variable from raw data. This is the unprocessed version
before any adjustment or clipping.

#### 2a: Forward-Shift Targets (Time-Series / Panel Data)

For prediction tasks, the target is a future outcome measured relative to the
snapshot date. The shift must match the prediction horizon.

**Procedure:**
1. For each entity-snapshot row, look forward N periods to compute the outcome
2. Use the entity's own future data, not aggregate data
3. Rows without sufficient forward data get NaN target (drop for training)

```python
# Example: 6-month forward growth rate
# trailing_6m is known at snapshot time
# forward_6m requires looking 6 months ahead
df['forward_6m_metric'] = (
    df.groupby('entity_id')['metric_value']
    .transform(lambda s: s.shift(-6).rolling(6).sum())
)
denominator = df['prior_6m_metric'].clip(lower=1)
df['growth_rate_6m'] = (df['forward_6m_metric'] - df['prior_6m_metric']) / denominator
```

**Severity:**
- BLOCKER: If the forward shift uses data from the snapshot month itself
  (off-by-one). The model must not see the period it's predicting.
- BLOCKER: If the denominator can be zero without clipping (division by zero).
- WARNING: If > 30% of rows get NaN target (insufficient forward data). Check
  whether the horizon is too long for the available history.
- INFO: Log how many rows were dropped due to NaN target.

#### 2b: Cross-Sectional Targets

For non-temporal tasks, the target is observed directly (e.g., price, label).
No shift needed — but verify the target is not derived from features in the
same row (circular definition).

**Severity:**
- BLOCKER: Target is computed from features available at prediction time
  (leakage by construction).

### Step 3: Profile the Raw Target

Before any adjustment or clipping, measure the raw target distribution.

**Required checks:**

| Check | How | Severity |
|-------|-----|----------|
| Skew | `df[target].skew()` | WARNING if abs > 2.0, BLOCKER if abs > 4.0 |
| Kurtosis | `df[target].kurtosis()` | WARNING if > 10 (extreme tails) |
| Outlier range | 1st and 99th percentile vs domain bounds | WARNING if 99th > 5× median |
| NaN rate | `df[target].isna().mean()` | WARNING if > 20% |
| Infinite values | `np.isinf(df[target]).sum()` | BLOCKER if any |
| Zero inflation | `(df[target] == 0).mean()` | INFO if > 30% (may need special handling) |
| Class balance | Count per bin (declining/flat/growing) | WARNING if minority < 15% |

```
## Raw Target Profile
| Metric | Value | Severity |
|--------|-------|----------|
| Mean | | |
| Median | | |
| Std | | |
| Skew | | |
| Kurtosis | | |
| Min / Max | | |
| P01 / P99 | | |
| NaN rate | | |
| Declining % | | |
| Flat % | | |
| Growing % | | |
```

**HALT** on any BLOCKER. Fix before proceeding.

### Step 4: Apply External Adjustment (Optional)

**Trigger:** When the target is influenced by external factors (market trends,
seasonality, macro conditions) that the model should not credit or penalize
accounts for.

**Purpose:** Isolate the entity-specific signal from the market signal. Without
adjustment, the model learns "everyone declined in Q2 2020" instead of "this
account declined relative to its peers."

#### 4a: Choose the Adjustment Factor

The adjustment should be:
- **Measurable independently** of the entities being modeled (e.g., industry
  volume index, not the average of your own accounts)
- **At the same time grain** as the target (monthly, quarterly)
- **Directionally correct** — when the market is up, the adjustment is positive

Common adjustment types:

| Type | When to use | Example |
|------|------------|---------|
| Market index (YoY) | Cyclical business with clear market proxy | Buy-side NDA volume YoY |
| Seasonal decomposition | Strong seasonal pattern | Retail sales seasonal component |
| Peer group median | No external index available | Median growth of same-tier accounts |
| None | Target is already relative or market-neutral | Churn flag, satisfaction score |

#### 4b: Apply the Adjustment

```python
# Subtract the market trend — residual is entity-specific
df['adjusted_target'] = df['raw_target'] - df['market_index']
```

**Severity:**
- WARNING: If the market index has missing values for some periods. Decide:
  fill forward, interpolate, or exclude those rows.
- WARNING: If the market index has extreme values (e.g., COVID months with
  50%+ swings). Consider excluding distorted periods with a threshold:

```python
# Exclude months where market distortion exceeds threshold
covid_threshold = 0.50  # domain-specific
distorted = df['market_index'].abs() > covid_threshold
df = df[~distorted]
```

- INFO: Log the adjustment factor's summary stats. If its variance is larger
  than the raw target's variance, the adjustment dominates — verify this is
  intended.

#### 4c: Validate the Adjustment

After adjusting, re-run the profile from Step 3 on the adjusted target.
Compare:

```
## Adjustment Impact
| Metric | Before | After | Delta |
|--------|--------|-------|-------|
| Mean | | | |
| Std | | | |
| Skew | | | |
| Declining % | | | |
```

The adjusted target should have:
- Lower variance from macro effects
- Similar or reduced skew
- More stable class balance across time periods

**Severity:**
- WARNING: If adjustment increased skew (sign that the index is misaligned)
- WARNING: If class balance changed dramatically (> 10pp shift in minority %)

### Step 5: Apply Target Clipping or Winsorization

**Trigger:** When Step 3 or Step 4c shows skew WARNING or extreme outliers.

**Two strategies — choose one:**

#### Strategy A: Hard Clipping (Recommended for Most Cases)

Set explicit bounds based on domain knowledge. Values outside bounds are
clamped.

```python
clip_lower = config['training']['target_clip']['lower']  # e.g., -0.75
clip_upper = config['training']['target_clip']['upper']  # e.g., +0.75
df[target] = df[target].clip(clip_lower, clip_upper)
```

**When to use:** When you have domain knowledge about reasonable bounds.
A growth rate > 75% or < -75% in 6 months is likely noise, not signal.

**Important:** Clip the TRAINING target only. For evaluation, decide whether
to also clip the test target (consistent evaluation) or not (realistic
evaluation). Document the choice.

#### Strategy B: Percentile Winsorization

Set bounds at data-driven percentiles. Useful when you lack domain knowledge.

```python
p01 = df[target].quantile(0.01)
p99 = df[target].quantile(0.99)
df[target] = df[target].clip(p01, p99)
```

**When to use:** Exploratory phase when you don't yet know the domain bounds.
Replace with hard clipping once you understand the data.

**Severity:**
- WARNING: If clip range > 2× the interquartile range (clipping is too loose
  to help with outliers)
- WARNING: If > 5% of rows are clipped (either bounds are too tight or data
  has real extreme values worth investigating)
- INFO: Log clip bounds and % of rows affected

#### Post-Clipping Profile

Re-run the target profile after clipping:

```
## Clipping Impact
| Metric | Before | After | Delta |
|--------|--------|-------|-------|
| Skew | | | |
| P01 / P99 | | | |
| Rows clipped (%) | — | | |
```

### Step 6: Profile Class Balance

**Trigger:** Always — even for regression targets, if the model's operational
use involves binning (e.g., "flag if predicted < 0"), class balance matters.

**Procedure:**
1. Define the bin boundary from config (e.g., `declining_threshold: 0.00`)
2. Compute minority class % overall
3. Compute minority class % per time period (per CV fold if defined)
4. Check for temporal concentration

```python
threshold = config['training']['bin_thresholds']['declining']
df['is_minority'] = df[target] < threshold

overall_minority_pct = df['is_minority'].mean()

# Per-period balance
period_balance = df.groupby('snapshot_month')['is_minority'].mean()
```

```
## Class Balance Profile
| Metric | Value | Severity |
|--------|-------|----------|
| Overall minority % | | INFO/WARNING |
| Min period minority % | | |
| Max period minority % | | |
| Std across periods | | WARNING if > 0.10 |
| Minority concentrated? | | WARNING if >50% from <20% of periods |
```

**Severity:**
- WARNING: Minority < 15% overall — sample weights will be critical
- WARNING: Standard deviation of minority % across periods > 0.10 — model
  may learn period-specific patterns, not entity patterns
- INFO: Document balance for downstream use by optimization skills

### Step 7: Produce Target Engineering Report

Fill this summary after all steps complete:

```
## Target Engineering Report

### Definition
| Field | Value |
|-------|-------|
| Raw target | [column name, formula] |
| Final target | [column name] |
| Prediction horizon | [N periods forward] |
| Entity grain | [entity column] |
| Time grain | [snapshot column] |

### Adjustments Applied
| Step | Applied? | Details |
|------|----------|---------|
| Forward shift | Yes/No | [horizon, denominator clipping] |
| External adjustment | Yes/No | [index name, exclusions] |
| Clipping | Yes/No | [bounds, strategy, % rows affected] |

### Final Target Profile
| Metric | Value |
|--------|-------|
| Rows (valid) | |
| Mean | |
| Median | |
| Std | |
| Skew | |
| P01 / P99 | |
| Minority class % | |
| Class balance stability | [std across periods] |

### Config
```yaml
training:
  target_variable: "..."
  target_clip:
    lower: ...
    upper: ...
  bin_thresholds:
    declining: ...
```

### BLOCKERs: [count]
### WARNINGs: [count]
```

## Connections to Other Skills

- **Feature Hygiene** — runs after target engineering. The target column(s)
  and any intermediate columns (raw growth, market index) must be in the
  Feature Hygiene exclude list.
- **Recall Optimization / F1 Optimization** — class balance from Step 6
  feeds directly into Lever 3 (sample weight sweep). Skew from Step 3/5
  feeds Lever 1 (target clipping re-evaluation).
- **Forward-Chaining CV** — the prediction horizon from Step 1 determines
  the test window length in CV fold design.

## Anti-Patterns

- **Using the raw target without profiling.** Extreme skew, outliers, or
  class imbalance will silently degrade model performance. Always run Step 3.
- **Adjusting with a correlated-but-wrong index.** The adjustment factor must
  causally explain variance in the target, not just correlate. A misaligned
  index adds noise instead of removing it. Validate with Step 4c.
- **Clipping test targets differently from train.** Inconsistent clipping
  between train and test makes metrics incomparable. Document your choice
  (clip both or clip neither) and stick with it across the pipeline.
- **Forward-shifting without dropping NaN rows.** Rows at the end of the
  time series have no valid forward target. If these enter training, the model
  learns from NaN-filled or zero-filled targets — garbage signal.
- **Using entity averages as the adjustment factor.** If your market index
  is the mean of the same entities you're modeling, you're adjusting each
  entity relative to itself. Use an external, independently measured index.
- **Ignoring temporal class balance shifts.** A target that's 30% minority
  overall but 50% minority in H2 2025 creates misleading CV fold metrics.
  The model appears to work well on some folds and poorly on others — it's
  the data, not the model.
