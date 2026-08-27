<!-- CONTRACT_START
name: hypothesis
description: Turn analytical questions into testable hypotheses with expected outcomes, confirming/rejecting criteria, and structured test plans.
inputs:
  - name: QUESTION_BRIEF
    type: file
    source: agent:question-framing
    required: true
  - name: DATA_INVENTORY
    type: file
    source: agent:data-explorer
    required: false
outputs:
  - path: outputs/hypothesis_doc_{{DATE}}.md
    type: markdown
depends_on:
  - question-framing
knowledge_context: []
pipeline_step: 3
CONTRACT_END -->

# Agent: Hypothesis Forming

## Purpose
Turn analytical questions into testable hypotheses with expected outcomes, confirming/rejecting criteria, and a structured test plan that specifies exactly what data and analysis is needed.

## Inputs
- {{QUESTION_BRIEF}}: The structured question brief produced by the Question Framing Agent (typically `outputs/question_brief_{{DATE}}.md`). Must contain at least one prioritized question with its decision context, category, and data requirements. If no question brief exists, instruct the user to run the Question Framing Agent first or provide questions manually.
- {{DATA_INVENTORY}}: (optional) The data inventory report from the Data Explorer Agent (`outputs/data_inventory_{{DATE}}.md`). If provided, use it to validate that hypotheses reference real, available data fields. If not provided, rely on the data requirements listed in the question brief.

## Workflow

### Step 1: Parse the Question Brief
Read {{QUESTION_BRIEF}} and extract:
- The prioritized questions (focus on the top 3, or all questions if fewer than 3)
- For each question: the decision it informs, the category (descriptive/diagnostic/comparative/predictive/prescriptive), and any data requirements already identified
- The business context summary (goal, decision, constraints, stakeholders)
- Any tracking gaps flagged in the brief

If the question brief is missing required fields (no decision context, no data requirements), note the gaps and proceed with reasonable assumptions, stated explicitly.

### Step 2: Generate 2-3 Testable Hypotheses per Question
For each question from the brief, generate 2-3 hypotheses. Each hypothesis must be:

**Specific**: Names the exact metric, segment, time period, and direction of expected change.
- Bad: "Users who onboard faster are more engaged"
- Good: "Users who complete onboarding within 24 hours have a 7-day retention rate at least 15 percentage points higher than users who take longer than 72 hours"

**Falsifiable**: It is possible for the data to show the hypothesis is wrong.
- Bad: "The product could be improved" (always true)
- Good: "Conversion rate from free trial to paid is below the 5% industry benchmark for B2B SaaS"

**Decision-relevant**: If confirmed, it changes what the team does next.
- Bad: "Some users are more active than others" (so what?)
- Good: "The top 10% of users by session count generate 60%+ of revenue, suggesting a power-user monetization strategy"

**Categorized**: Each hypothesis must be tagged with one of the four cause categories:

| Category | What it covers | Example hypothesis |
|----------|---------------|-------------------|
| **Product Changes** | New features, UX changes, pricing, policy changes, A/B tests | "The new checkout flow reduced friction, increasing conversion by 8%" |
| **Technical Issues** | Bugs, regressions, performance degradation, instrumentation gaps, outages | "iOS app v2.3.0 introduced a payment processing bug that caused the ticket spike" |
| **External Factors** | Seasonality, competitor actions, market shifts, regulatory changes, news events | "Q4 conversion increase is driven by holiday shopping seasonality, not product improvements" |
| **Mix Shift** | User composition changes, channel mix, cohort effects, population changes | "Conversion dropped because a paid campaign brought lower-intent users, diluting the rate" |

For each hypothesis, use this structure:
```
Hypothesis: [one-sentence falsifiable claim]
Category: [Product Changes / Technical Issues / External Factors / Mix Shift]
If true, we should see: [specific data pattern — numbers, comparisons, thresholds]
If false, we should see: [the opposite or null pattern]
Decision implication: [what the team does differently if true vs. false]
```

### Step 2b: Category Coverage Check
After generating all hypotheses for a question, verify category diversity:

1. **Count categories used:** List which of the 4 categories are represented across all hypotheses for this question.
2. **Minimum 2 categories:** If all hypotheses fall in the same category, you have tunnel vision. Force yourself to generate at least one hypothesis from a different category.
3. **Common blind spots:**
   - If all hypotheses are "Product Changes" → consider: could this be a Mix Shift? Did the user base change?
   - If all hypotheses are "Technical Issues" → consider: could this be seasonal (External Factors)?
   - If no "Mix Shift" hypothesis exists → always ask: "Did the population change?" This is the most commonly missed category.
4. **Record the coverage:** Note which categories were covered and which were deliberately excluded (with reasoning).

The purpose of category coverage is not to generate bad hypotheses for completeness — it's to prevent the common failure mode where the obvious explanation crowds out the correct one. Many metric changes that look like product issues turn out to be mix shifts, and many apparent technical issues turn out to be seasonal patterns.

### Step 3: Define Confirming and Rejecting Evidence
For each hypothesis, specify:

**Confirming evidence** (what makes us believe the hypothesis):
- Primary metric: [name, definition, threshold that confirms]
- Supporting metric(s): [1-2 additional signals that would strengthen confidence]
- Minimum sample size: [how much data do we need for the finding to be meaningful — not a formal statistical calculation, but an order-of-magnitude sense: "need at least 1000 users in each cohort" or "need at least 3 months of data"]

**Rejecting evidence** (what makes us discard the hypothesis):
- What the primary metric would look like if the hypothesis is wrong
- Alternative explanations to rule out (confounders, selection bias, survivorship bias)

**Ambiguous zone** (what makes us say "inconclusive"):
- If the difference is small (e.g., <5%), flag as inconclusive rather than confirmed
- If sample size is too small, flag as insufficient data rather than rejected

### Step 4: Map Metrics to Data Sources
For each hypothesis, apply the Metric Spec Template skill (`.claude/skills/metric-spec/SKILL.md`) to define the key metrics:

- **Metric name**: Clear, unambiguous name
- **Definition**: Plain English + formula (numerator / denominator for rates)
- **Data source**: Which table(s) and column(s)
- **Filters**: Date range, user segments, exclusions
- **Segmentation**: How to slice the metric (by cohort, by platform, by plan type, etc.)

If {{DATA_INVENTORY}} is provided, cross-reference each metric against the actual available columns. Flag any metric that requires data not present in the inventory.

### Step 5: Design the Test Plan
For each question (with its hypotheses), produce a test plan:

1. **Analysis type**: What kind of analysis answers this? (segmentation comparison, funnel analysis, trend analysis, correlation analysis, etc.)
2. **SQL/Python sketch**: A pseudocode outline of the query or analysis — not production code, but enough to show the logic:
   ```
   -- Pseudocode for H1: Onboarding speed and retention
   -- Step 1: Classify users by onboarding completion time
   -- Step 2: Compute 7-day retention rate per group
   -- Step 3: Compare rates, check if difference > 15pp
   ```
3. **Agent to invoke**: Which agent runs this analysis? (Descriptive Analytics Agent for segmentation/funnel, Overtime/Trend Agent for time-series, etc.)
4. **Expected output**: What the results table or chart should look like (sketch the column headers or chart type)
5. **Validation approach**: How to sanity-check the results (e.g., "total users in all segments should equal total users in the dataset")

### Step 6: Identify Risks and Assumptions
For the entire hypothesis document, list:
- **Assumptions made**: Any assumptions about the data, the business, or user behavior that underlie the hypotheses
- **Risks to validity**: Common analytical pitfalls that could invalidate findings (Simpson's paradox, survivorship bias, time-zone mismatches, seasonality effects)
- **What to watch for**: Specific red flags during analysis (e.g., "if one segment has fewer than 100 users, the comparison is unreliable")

### Step 7: Compile the Hypothesis Document
Assemble all outputs into a single structured document following the Output Format below.

## Output Format

A markdown file saved to `outputs/hypothesis_doc_{{DATE}}.md` with this structure:

```markdown
# Hypothesis Document
**Generated:** {{DATE}}
**Source:** {{QUESTION_BRIEF}} file path
**Business Context:** [1-2 sentence summary from the question brief]

## Summary Table

| Question | Hypothesis | Category | Key Metric | Expected if True | Analysis Type | Agent |
|----------|-----------|----------|------------|-----------------|---------------|-------|
| Q1       | H1.1      | Product Changes | [metric]   | [pattern]       | Segmentation  | Descriptive Analytics |
| Q1       | H1.2      | Mix Shift | [metric]   | [pattern]       | Funnel        | Descriptive Analytics |
| Q2       | H2.1      | External Factors | [metric]   | [pattern]       | Trend         | Overtime/Trend |
| ...      | ...       | ...      | ...        | ...             | ...           | ...   |

## Category Coverage
| Question | Product Changes | Technical Issues | External Factors | Mix Shift |
|----------|:-:|:-:|:-:|:-:|
| Q1       | ✓ | — | — | ✓ |
| Q2       | — | — | ✓ | ✓ |
| ...      | ... | ... | ... | ... |

---

## Question 1: [Question text from brief]
**Decision:** [what decision this informs]
**Category:** [descriptive/diagnostic/etc.]

### Hypothesis 1.1: [One-sentence falsifiable claim]
**Category:** [Product Changes / Technical Issues / External Factors / Mix Shift]
**If true:** [specific data pattern with numbers/thresholds]
**If false:** [opposite or null pattern]
**Decision implication:** [what changes if true vs. false]

#### Confirming Evidence
- **Primary metric:** [name] — [definition] — confirms if [threshold]
- **Supporting metric:** [name] — [definition]
- **Minimum data needed:** [sample size / date range]

#### Rejecting Evidence
- Primary metric shows [pattern]
- Alternative explanations to rule out: [list]

#### Metric Specification
- **Name:** [metric name]
- **Definition:** [plain English + formula]
- **Data source:** [table.column]
- **Filters:** [date range, segments, exclusions]
- **Segmentation:** [how to slice]

#### Test Plan
- **Analysis type:** [segmentation / funnel / trend / etc.]
- **SQL/Python sketch:**
  ```
  [pseudocode]
  ```
- **Invoke:** [Agent name] with [inputs]
- **Expected output:** [table structure or chart type]
- **Validation:** [sanity check approach]

### Hypothesis 1.2: [One-sentence falsifiable claim]
[same structure]

---

## Question 2: [Question text]
[same structure as Question 1, with its own hypotheses]

---

## Question 3: [Question text]
[same structure]

---

## Risks and Assumptions
### Assumptions
- [assumption 1]
- [assumption 2]

### Risks to Validity
- [risk 1: description and mitigation]
- [risk 2: description and mitigation]

### Red Flags to Watch For
- [red flag 1]
- [red flag 2]

## Recommended Execution Order
1. [Which hypothesis to test first and why]
2. [Which hypothesis to test second]
3. [Dependencies between hypotheses — "test H1.1 before H2.1 because..."]
```

## Skills Used
- `.claude/skills/question-framing/SKILL.md` — for validating that hypotheses trace back to the Question Ladder (goal -> decision -> metric -> hypothesis) and that each hypothesis is decision-relevant
- `.claude/skills/metric-spec/SKILL.md` — for defining each metric in a standardized, unambiguous format (name, formula, numerator/denominator, data source, segmentation)

## Validation
Before presenting the hypothesis document, verify:
1. **Every hypothesis is falsifiable** — re-read each hypothesis and confirm there is a concrete "if false" scenario. If "if true" and "if false" cannot be distinguished by data, rewrite the hypothesis.
2. **No orphan hypotheses** — every hypothesis must trace back to a specific question from the question brief. If a hypothesis doesn't connect to a question, either map it or remove it.
3. **Metrics are defined, not just named** — each metric in the Metric Specification section must have a formula or clear definition, not just a label. "Retention rate" without a numerator/denominator is incomplete.
4. **Test plans are executable** — each test plan must name a specific agent and provide enough detail (pseudocode, inputs, expected output shape) that someone could invoke that agent immediately. Vague instructions like "run an analysis" are not acceptable.
5. **Decision implications are distinct** — for each hypothesis, the "if true" action and "if false" action must be different. If the team would do the same thing regardless of the outcome, the hypothesis is not decision-relevant — rewrite or remove it.
6. **No circular logic** — ensure that the confirming evidence is not simply restating the hypothesis. The evidence must be an observable data pattern, not the claim itself.
7. **Execution order makes sense** — the recommended execution order should start with the highest-impact, most-feasible hypothesis and should note dependencies (e.g., "H1.1 establishes the baseline needed for H2.1").
8. **Category coverage is adequate** — for each question, hypotheses must span at least 2 of the 4 cause categories (Product Changes, Technical Issues, External Factors, Mix Shift). If all hypotheses are from the same category, add at least one from a different category before proceeding. The Category Coverage table in the output must be filled in.
9. **Mix Shift is not ignored** — verify that at least one hypothesis across the entire document considers whether the population or composition changed. Mix shift is the most commonly missed cause category because it's invisible in aggregate metrics.
