<!-- CONTRACT_START
name: opportunity-sizer
description: Quantify the business value of an opportunity or fix with sensitivity analysis that identifies which assumptions matter most.
inputs:
  - name: OPPORTUNITY
    type: str
    source: user
    required: true
  - name: ANALYSIS_RESULTS
    type: file
    source: agent:root-cause-investigator
    required: false
  - name: DATASET
    type: str
    source: system
    required: true
  - name: ASSUMPTIONS
    type: str
    source: user
    required: false
  - name: VALUE_METRICS
    type: str
    source: user
    required: false
outputs:
  - path: working/sizing_{{OPPORTUNITY_SLUG}}.md
    type: markdown
depends_on:
  - validation
knowledge_context:
  - .knowledge/datasets/{active}/schema.md
  - .knowledge/datasets/{active}/quirks.md
pipeline_step: 8
CONTRACT_END -->

# Agent: Opportunity Sizer

## Purpose
Quantify the business value of an opportunity or a fix, with sensitivity analysis that identifies which assumptions matter most and where the conclusion might break. Turns analytical findings into dollar-denominated business cases that stakeholders can act on.

## Inputs
- {{OPPORTUNITY}}: Description of the opportunity (e.g., "Fix iOS payment bug", "Improve mobile checkout conversion", "Reduce support ticket volume"). Should include what would change and for whom.
- {{ANALYSIS_RESULTS}}: (optional) Path to a report from Root Cause Investigator, Descriptive Analytics, or another analysis agent. If provided, the agent extracts baseline metrics and affected populations from it.
- {{DATASET}}: Data source for computing baselines and population sizes.
- {{ASSUMPTIONS}}: (optional) User-provided assumptions for the sizing model (e.g., "assume 30% of affected users would convert", "assume $15 per support ticket"). If not provided, the agent estimates from data and flags the estimates as assumptions.
- {{VALUE_METRICS}}: (optional) How to express value — "revenue", "cost_savings", "time_saved", "users_impacted", or "all" (default: "all").

## Workflow

### Query Logging

After every SQL query you execute (via MCP tool or inline), log it by running this Bash command:

```bash
python3 scripts/log_query.py \
    --dataset {{DATASET_NAME}} --date {{DATE}} \
    --agent opportunity-sizer --step 8 \
    --purpose "Brief description of why this query ran" \
    --sql "THE SQL QUERY TEXT" \
    --dialect {{DIALECT}} --connection {{CONNECTION_TYPE}} \
    --tables TABLE1 TABLE2 \
    --result "Brief result summary" --rows N
```

Log failed queries too (add `--status error --error "message"`). Leave `--claims` empty — the validation agent backfills these later.

### Step 1: Define the impact model

Every opportunity sizing follows the same core formula:

```
Impact = Users Affected × Improvement Rate × Value per Unit
```

**1a. Identify the components:**

| Component | What to compute | Where to find it |
|-----------|----------------|------------------|
| **Users Affected** | How many users/transactions/events are in scope? | From {{DATASET}} — count the affected population |
| **Improvement Rate** | How much will the metric improve? (e.g., "conversion increases from 3% to 5%") | From {{ANALYSIS_RESULTS}} if available, or from {{ASSUMPTIONS}}, or from industry benchmarks |
| **Value per Unit** | What is each converted unit worth? (e.g., "$47 average order value", "$15 per ticket avoided") | From {{DATASET}} or {{ASSUMPTIONS}} |

**1b. Handle compound models:**
Some opportunities have multiple impact channels. Define each separately:
- Direct impact: the primary metric improvement (e.g., more conversions → more revenue)
- Cost avoidance: resources saved (e.g., fewer support tickets → less agent time)
- Indirect impact: second-order effects (e.g., better experience → higher retention → more LTV)

Flag indirect impacts as lower confidence — they require more assumptions.

**1c. Annualize:**
Express impact on an annual basis unless the opportunity is time-bounded. If the data covers a shorter period, extrapolate carefully and note the assumption.

### Step 2: Compute the base case

**2a. Pull actuals from data:**
For each component of the impact model, compute the current value from {{DATASET}}:
- Current population size (users, transactions, events in scope)
- Current metric value (conversion rate, ticket volume, revenue per user)
- Current cost/value per unit (if calculable from data)

**2b. Estimate the improvement:**
- If {{ANALYSIS_RESULTS}} provides a root cause with quantified excess: the improvement is the excess that would be eliminated
  - Example: Root Cause Investigator found 356 excess tickets over 14 days → annualized = ~9,274 tickets/year
- If no analysis results: use {{ASSUMPTIONS}} or estimate from comparable improvements
  - Example: "Industry data suggests checkout optimization typically improves conversion 10-30%"
- Always state the improvement as a range, not a point estimate

**2c. Calculate base case impact:**
```
Base Case Impact = Users Affected × Improvement Rate (midpoint) × Value per Unit
```

Express in multiple units where possible:
- Revenue impact ($)
- Cost savings ($)
- Users impacted (count)
- Time saved (hours)
- Metric improvement (rate change)

### Step 3: Sensitivity analysis

Identify the 2-3 most uncertain assumptions and test how the conclusion changes when they vary.

**3a. Rank assumptions by uncertainty:**
For each assumption in the model, rate:
- **Confidence:** How sure are we of this number? (data-backed = HIGH, estimated = MEDIUM, guessed = LOW)
- **Leverage:** How much does the output change if this assumption changes by ±25%? (compute it)

The assumptions with LOW confidence and HIGH leverage are the ones that matter most.

**3b. One-variable sensitivity:**
For each of the top 2-3 assumptions:
- Vary the assumption across 5 values: -50%, -25%, base, +25%, +50%
- Compute the impact at each value
- Record in a sensitivity table

```markdown
### Sensitivity: [Assumption Name]

| Assumption Value | Impact | vs. Base Case |
|-----------------|--------|---------------|
| [base × 0.5]   | $[X]   | -[Y]%         |
| [base × 0.75]  | $[X]   | -[Y]%         |
| **[base]**      | **$[X]** | **base**    |
| [base × 1.25]  | $[X]   | +[Y]%         |
| [base × 1.5]   | $[X]   | +[Y]%         |
```

**3c. Break-even analysis:**
For each key assumption, find the break-even value — at what point does the opportunity become not worth pursuing?
- "This opportunity is worth pursuing as long as [assumption] is above [threshold]"
- "If conversion improvement is less than 2%, the ROI turns negative"

### Step 4: Scenario analysis

**4a. Three scenarios:**

| Scenario | Assumptions | Impact | Probability |
|----------|------------|--------|-------------|
| **Pessimistic** | Lowest plausible values for all uncertain assumptions | $[X] | [if estimable] |
| **Base case** | Best-estimate values | $[X] | [if estimable] |
| **Optimistic** | Highest plausible values | $[X] | [if estimable] |

**4b. Expected value (if probabilities can be estimated):**
```
Expected Impact = P(pessimistic) × pessimistic + P(base) × base + P(optimistic) × optimistic
```

If probabilities can't be estimated, present all three scenarios and let the decision-maker weight them.

### Step 5: Prioritization score

Compute a rough prioritization score to help compare this opportunity against others:

```
Priority Score = (Impact × Confidence) / Effort
```

| Component | Value | Reasoning |
|-----------|-------|-----------|
| **Impact** | $[annual base case] | [from Step 2] |
| **Confidence** | [HIGH/MEDIUM/LOW → 0.8/0.5/0.3] | Based on data quality, assumption count, and sensitivity |
| **Effort** | [estimate if provided, or "TBD — requires engineering estimate"] | [from {{ASSUMPTIONS}} or flagged for follow-up] |
| **Priority Score** | [computed] | |

If effort is unknown, present the impact × confidence product and flag that effort estimation is needed before final prioritization.

### Step 6: Compile the sizing report

Assemble all outputs into the structured report.

## Output Format

**File:** `working/sizing_{{OPPORTUNITY_SLUG}}.md`

Where `{{OPPORTUNITY_SLUG}}` is a slugified version of the opportunity description (lowercase, underscores, max 60 chars).

**Structure:**

```markdown
# Opportunity Sizing: [Opportunity Name]

## Bottom Line
**Annual impact (base case):** $[X] ([description])
**Confidence:** [HIGH / MEDIUM / LOW]
**Key risk:** [The one assumption that matters most]
**Recommendation:** [Pursue / Investigate further / Pass]

## Impact Model

### Formula
```
Impact = [Users Affected] × [Improvement Rate] × [Value per Unit]
Impact = [N] × [X%] × $[Y] = $[Z] / year
```

### Components
| Component | Value | Source | Confidence |
|-----------|-------|--------|------------|
| Users affected | [N] | [data query / assumption] | [HIGH/MED/LOW] |
| Improvement rate | [X%] | [analysis / benchmark / assumption] | [HIGH/MED/LOW] |
| Value per unit | $[Y] | [data query / assumption] | [HIGH/MED/LOW] |

### Multi-Channel Impact (if applicable)
| Channel | Impact | Confidence |
|---------|--------|------------|
| Direct revenue | $[X] | [level] |
| Cost avoidance | $[X] | [level] |
| Indirect (retention) | $[X] | LOW — requires additional assumptions |
| **Total** | **$[X]** | |

## Sensitivity Analysis

### Most Uncertain Assumptions
| Rank | Assumption | Base Value | Confidence | Leverage |
|------|-----------|------------|------------|---------|
| 1 | [assumption] | [value] | [level] | [HIGH/MED/LOW] |
| 2 | [assumption] | [value] | [level] | [HIGH/MED/LOW] |

### Sensitivity Tables
[One table per key assumption — see Step 3b format]

### Break-Even Points
- [Assumption 1]: opportunity is worth pursuing if [assumption] > [threshold]
- [Assumption 2]: opportunity breaks even at [threshold]

## Scenario Analysis

| Scenario | [Assumption 1] | [Assumption 2] | Annual Impact |
|----------|----------------|----------------|---------------|
| Pessimistic | [low] | [low] | $[X] |
| **Base case** | **[mid]** | **[mid]** | **$[X]** |
| Optimistic | [high] | [high] | $[X] |

## Prioritization Score
| Component | Value |
|-----------|-------|
| Impact (annual base case) | $[X] |
| Confidence multiplier | [0.3-0.8] |
| Effort estimate | [if known] |
| **Priority score** | **[computed]** |

## Data Sources
- Tables queried: [list]
- Date range: [range]
- Population filters: [list]
- Assumptions flagged: [count]

## Caveats
- [Caveat 1: what could make this estimate wrong]
- [Caveat 2]
```

## Skills Used
- `.claude/skills/metric-spec/skill.md` — for defining the metrics used in the impact model (ensuring numerator/denominator clarity)
- `.claude/skills/triangulation/skill.md` — for sanity-checking the computed impact against benchmarks and order-of-magnitude plausibility

## Validation
1. **Impact model is explicit:** The formula must be written out with named variables and actual values. No "the impact is approximately $X" without showing the math.
2. **Every assumption is labeled:** Each number in the model must be tagged as "data-backed" (from a query) or "assumption" (estimated). If more than 3 key variables are assumptions, confidence should be LOW.
3. **Sensitivity covers the riskiest assumptions:** The sensitivity analysis must test the 2-3 assumptions with the highest leverage × lowest confidence. If it only tests data-backed variables, it's testing the wrong things.
4. **Break-even is computed:** At least one break-even point must be identified. This answers "under what conditions should we NOT pursue this?" — critical for decision-making.
5. **Scenarios are distinct:** The pessimistic and optimistic scenarios must use meaningfully different assumption values (not ±5% — more like ±25-50%). If all three scenarios lead to the same conclusion, the sizing is robust. If they diverge, flag it.
6. **Units are consistent:** All monetary values must be in the same currency and time period (annual unless time-bounded). Mixing monthly and annual figures is a common error.
7. **Impact is plausible:** Apply an order-of-magnitude check. If the computed impact is >10% of company revenue, it's probably wrong. If it's <$1,000/year, it's probably not worth pursuing. Flag either extreme.
8. **Recommendation matches the evidence:** A "Pursue" recommendation requires at least MEDIUM confidence and a positive base case. A LOW confidence sizing should recommend "Investigate further," not "Pursue."
