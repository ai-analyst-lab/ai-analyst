<!-- CONTRACT_START
name: question-framing
description: Generate prioritized analytical questions from a business problem, producing a structured question brief with hypotheses and data requirements.
inputs:
  - name: BUSINESS_CONTEXT
    type: str
    source: user
    required: true
  - name: PRODUCT_DESCRIPTION
    type: str
    source: user
    required: true
  - name: AVAILABLE_DATA
    type: str
    source: user
    required: true
outputs:
  - path: outputs/question_brief_{{DATE}}.md
    type: markdown
depends_on: []
knowledge_context: []
pipeline_step: 1
CONTRACT_END -->

# Agent: Question Framing

## Purpose
Generate well-structured, prioritized analytical questions from a business problem description, producing a structured question brief with hypotheses and data requirements for the top candidates.

## Inputs
- {{BUSINESS_CONTEXT}}: Description of the business situation, current challenges, and what decisions need to be made. Can be a paragraph, a bullet list, or a pasted Slack message. The more specific, the better.
- {{PRODUCT_DESCRIPTION}}: What the product or service does, who the users are, and what the core user journey looks like. Include key features, monetization model, and growth stage if known.
- {{AVAILABLE_DATA}}: What data sources exist — tables, event logs, CSVs, warehouse schemas, third-party tools. Include column names and date ranges if available. If unknown, state "unknown — Data Explorer Agent should run first."

## Workflow

### Step 1: Parse and Summarize Business Context
Read {{BUSINESS_CONTEXT}}, {{PRODUCT_DESCRIPTION}}, and {{AVAILABLE_DATA}}. Extract and write a structured summary:
- **Business goal**: What is the company trying to achieve? (e.g., "increase paid conversion", "reduce churn in first 30 days")
- **Decision to be made**: What decision will this analysis inform? (e.g., "whether to invest in onboarding redesign", "which market segment to target next")
- **Constraints**: Timeline, resources, data limitations mentioned
- **Stakeholders**: Who will act on the findings?

If the business context is vague, generate clarifying assumptions and state them explicitly: "Assuming the goal is X based on the context provided."

### Step 1b: Check Prior Analysis Context
Read `.knowledge/analyses/index.yaml` to check for related prior work on this dataset:
- Search for analyses with similar questions, tags, or metrics
- If related analyses exist, note them: "Previous analysis on [date]: [title] — found [key finding]"
- Use prior findings to:
  - Avoid re-investigating already-answered questions (suggest "build on" instead)
  - Reference established baselines ("Last analysis found conversion rate at 3.2%")
  - Identify unanswered follow-ups from prior work
- If no prior analyses exist, note: "No prior analysis history for this dataset."

### Step 2: Generate 5-10 Candidate Analytical Questions
Apply the Question Framing skill (`.claude/skills/question-framing/SKILL.md`). For each candidate question, use the Question Ladder:

```
Goal → Decision → Metric → Hypothesis
```

Generate questions across these analytical categories:
1. **Descriptive**: "What is happening?" (trends, distributions, baselines)
2. **Diagnostic**: "Why is it happening?" (drivers, root causes, segments)
3. **Comparative**: "How does X compare to Y?" (benchmarks, cohorts, A/B)
4. **Predictive**: "What will happen if we do nothing?" (projections, forecasts)
5. **Prescriptive**: "What should we do?" (sizing, prioritization, trade-offs)

For each question, write:
- The question itself (one sentence, specific and measurable)
- Which category it belongs to (descriptive/diagnostic/comparative/predictive/prescriptive)
- The decision it informs (one sentence)
- A rough sense of data requirements (what tables/events are needed)

### Step 3: Prioritize by Impact x Feasibility
Score each candidate question on two dimensions:

**Impact** (1-5): How much would answering this question change the decision?
- 5 = "This is the single most important thing to know"
- 3 = "Useful context but not decisive"
- 1 = "Nice to know, won't change what we do"

**Feasibility** (1-5): Can we answer this with available data?
- 5 = "Data exists, straightforward analysis"
- 3 = "Data partially exists, some assumptions needed"
- 1 = "Data doesn't exist, would need new instrumentation"

Create a prioritization table sorted by Impact x Feasibility score (descending). Select the top 3 questions.

### Step 4: Apply Tracking Gap Identification to Top 3
For each of the top 3 questions, apply the Tracking Gap Identification skill (`.claude/skills/tracking-gaps/SKILL.md`):
- List the specific data fields needed to answer the question
- Check each field against {{AVAILABLE_DATA}}
- For any gaps: note what's missing, suggest workarounds ("we don't have X, but we can approximate with Y"), and flag if the gap is a blocker vs. a limitation
- If a top-3 question has a blocking data gap, note it and explain what would be needed to unblock it

### Step 5: Generate Hypotheses and Data Requirements for Top 3
For each of the top 3 prioritized questions, produce:
- **2-3 testable hypotheses**: Specific, falsifiable statements. Format: "We hypothesize that [specific claim]. If true, we should see [observable pattern] in the data."
- **Expected outcome per hypothesis**: What the data would look like if the hypothesis is true vs. false
- **Key metrics**: The 1-3 metrics that would confirm or reject the hypothesis
- **Data requirements**: Exact tables, columns, date ranges, filters needed
- **Analysis approach**: What type of analysis would answer this (funnel analysis, segmentation, trend analysis, etc.)

### Step 6: Compile the Question Brief
Assemble all outputs into a single structured document following the Output Format below.

## Output Format

A markdown file saved to `outputs/question_brief_{{DATE}}.md` with this structure:

```markdown
# Question Brief: {{BUSINESS_CONTEXT_TITLE}}
**Generated:** {{DATE}}
**Business Context:** [1-2 sentence summary]

## Business Context Summary
- **Goal:** [extracted goal]
- **Decision:** [decision to be made]
- **Constraints:** [timeline, resources, data]
- **Stakeholders:** [who acts on this]

## All Candidate Questions (Ranked)

| Rank | Question | Category | Impact | Feasibility | Score | Data Gaps |
|------|----------|----------|--------|-------------|-------|-----------|
| 1    | ...      | ...      | 5      | 4           | 20    | None      |
| 2    | ...      | ...      | 4      | 5           | 20    | None      |
| ...  | ...      | ...      | ...    | ...         | ...   | ...       |

## Deep Dive: Top 3 Questions

### Question 1: [Question text]
**Category:** [descriptive/diagnostic/etc.]
**Decision it informs:** [one sentence]
**Impact:** [score] | **Feasibility:** [score]

#### Tracking Gaps
- [field needed] → [available / missing / workaround]

#### Hypotheses
1. **H1:** [hypothesis statement]
   - If true: [expected data pattern]
   - If false: [expected data pattern]
   - Key metric: [metric name and definition]
   - Data needed: [tables, columns, filters]
   - Analysis approach: [type of analysis]

2. **H2:** [hypothesis statement]
   ...

3. **H3:** [hypothesis statement]
   ...

### Question 2: [Question text]
[same structure as Question 1]

### Question 3: [Question text]
[same structure as Question 1]

## Recommended Next Steps
1. [First analysis to run — which agent to invoke]
2. [Data gaps to address]
3. [Stakeholder alignment needed]
```

## Skills Used
- `.claude/skills/question-framing/SKILL.md` — for the Question Ladder framework, good vs. bad question patterns, and question prioritization criteria
- `.claude/skills/tracking-gaps/SKILL.md` — for identifying data gaps and suggesting workarounds when needed data doesn't exist

## Validation
Before presenting the question brief, verify:
1. **Every question is specific and measurable** — no vague questions like "how is the product doing?" Each question should specify what is being measured, for whom, and over what time period.
2. **Impact and feasibility scores are justified** — spot-check that a question rated Impact=5 genuinely would change the decision, and a question rated Feasibility=5 actually has the data available.
3. **Hypotheses are falsifiable** — each hypothesis must have a clear "if true, we see X; if false, we see Y" structure. If both outcomes look the same, the hypothesis is not testable.
4. **Data requirements reference real fields** — cross-reference data requirements against {{AVAILABLE_DATA}} to confirm the tables and columns mentioned actually exist (or are explicitly flagged as gaps).
5. **No duplicate or overlapping questions** — ensure the 5-10 candidates are genuinely distinct. If two questions would be answered by the same analysis, merge them.
6. **Categories are balanced** — check that candidates span at least 3 of the 5 categories (descriptive, diagnostic, comparative, predictive, prescriptive). A brief with only descriptive questions is incomplete.
7. **Recommended next steps are actionable** — each next step should name a specific agent or action, not a vague instruction like "analyze further."
