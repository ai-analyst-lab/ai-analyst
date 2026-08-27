---
name: question-framing
description: >-
  Structure analytical questions with the Question Ladder (Goal, Decision, Metric, Hypothesis),
  then fill the 7-field Analysis Design Spec, before touching data. Trigger on "analyze",
  "investigate", "look into", "why did", "what's happening with", "what happened with", "figure
  out", "explore", "deep dive", "what caused", "compare", "breakdown", "root cause", "show me",
  "pull", "calculate". Framing first, analysis second.
---

# Skill: Question Framing

## Purpose
Structure analytical questions using the Question Ladder framework so every analysis starts with a clear decision context, measurable success criteria, and testable hypotheses.

## When to Use
Apply this skill when starting any new analysis, when a user asks a vague question ("How are we doing?"), or when an analysis request lacks decision context. Always frame before analyzing.

## Instructions

### Pre-flight: Load Learnings
Before executing, check `.knowledge/learnings/index.md` for relevant entries:
- Read the file. If it doesn't exist or is empty, skip silently.
- Scan for entries under **"Question Framing"** and **"General"** headings (or related categories like "Business Context", "Methodology Notes").
- If entries exist, incorporate them as constraints or context for this execution.
- Never block execution if learnings are unavailable.

### The Question Ladder

Every analytical question climbs four rungs:

```
GOAL        → What business outcome are we trying to achieve?
DECISION    → What specific decision will this analysis inform?
METRIC      → What will we measure to inform that decision?
HYPOTHESIS  → What do we expect to find, and why?
```

**The rule:** Never start analyzing data until you can state all four rungs. If the requester only gives you a goal ("improve retention"), your first job is to climb the ladder before touching data.

### Framing Process


**Step 1: Extract the decision**
Ask: "What will you DO differently based on the answer?"
- If the answer is "nothing" or "I'm just curious" → this is reporting, not analysis. Offer two paths:
  - **Path A**: Quick stat/dashboard (if truly no decision)
  - **Path B**: Clarify decision context first, then frame properly
- If the answer is a specific action → you have a decision. Proceed to Step 2.

**Step 2: Define success criteria**
Ask: "How will you know the analysis answered your question?"
- The answer should be specific: "If conversion rate dropped >10% in segment X, we'll prioritize a fix"
- Not vague: "We'll understand our users better"
- Success criteria should include specific thresholds, conditions, or decision rules

**Step 3: Form testable hypotheses**
Ask: "What do you think is happening, and why?"
- Good: "I think mobile conversion dropped because the checkout redesign broke on small screens"
- Bad: "I think things are bad"
- Extract hypotheses from vague statements - e.g., "cart abandonment is high" → "abandonment >20% due to checkout friction at payment stage"

**Step 4: Identify data requirements**
Ask: "What data do we need, and do we have it?"
- Map each hypothesis to specific metrics, segments, and time ranges
- Check if the data exists by reviewing schema documentation (don't query the database - just check availability)
- Flag gaps early: "We need funnel step events, but only have order status"
- Document what CAN and CANNOT be answered with available data

**Step 5: Produce the Question Brief**
Write the brief using the template below. Save it to `question_brief.md` in the working folder, or present it inline.
- DO NOT proceed to analysis after writing the brief
- DO NOT run SQL queries or call analysis agents
- Hand off to the next phase (exploration/analysis) after the brief is approved

### Good vs. Bad Questions

| Bad Question | Problem | Good Question |
|---|---|---|
| "How are our users doing?" | No decision context, unmeasurable | "Did the onboarding redesign improve Day-7 retention for new users?" |
| "Analyze our funnel" | No hypothesis, no scope | "Where in the signup-to-purchase funnel are we losing the most users, and does it differ by acquisition channel?" |
| "What's our conversion rate?" | Reporting, not analysis | "Why did conversion rate drop 15% in March, and is it affecting all segments equally?" |
| "Tell me about churn" | Too broad, no decision | "Which user segments have the highest 90-day churn rate, and what behaviors predict churn in the first 30 days?" |
| "Is our product doing well?" | Unmeasurable, no comparison | "How does our monthly active user growth compare to Q3, and which features are driving engagement?" |

### Impact × Feasibility Prioritization

When multiple questions emerge, prioritize:

```
                    HIGH IMPACT
                        │
          ┌─────────────┼─────────────┐
          │   DO FIRST   │   PLAN FOR  │
          │  (Quick win)  │  (Strategic) │
HIGH      │               │              │
FEASIBILITY ──────────────┼──────────────── LOW
          │               │              │ FEASIBILITY
          │   DO IF TIME  │    SKIP     │
          │  (Nice to have)│  (Not worth) │
          └─────────────┼─────────────┘
                        │
                    LOW IMPACT
```

**Impact criteria:**
- Revenue/cost implication >$100K → High
- Affects >10% of users → High
- Informs a decision being made this quarter → High
- Curiosity-driven, no pending decision → Low

**Feasibility criteria:**
- Data exists and is clean → High
- Can be answered in <4 hours → High
- Requires new instrumentation → Low
- Requires data from another team → Low

### Output Format: Question Brief (Ladder + Analysis Design Spec)

The Question Brief is the concrete artifact the Ladder produces. Climb the
Ladder first, then fill the seven spec fields. Every field is required; if you
cannot fill one, ask the user. Save it to `question_brief.md` in the working
folder (or present it inline for quick asks).

```markdown
# Question Brief: [Title]
## Date: [YYYY-MM-DD]

### Business Context
[2-3 sentences: what's happening, why this matters now]

### The Question Ladder
| Rung | Statement |
|------|-----------|
| **Goal** | [Business outcome] |
| **Decision** | [Specific action this informs] |
| **Metric** | [What we'll measure] |
| **Hypothesis** | [What we expect to find and why] |

### 1. Question
What are we trying to answer?
[A specific, testable question, sharpened from the Ladder]

### 2. Decision
What will this analysis inform?
[A concrete action the team will take based on the answer]
[If the answer is "nothing specific", this may be reporting, not analysis. Confirm with the user.]

### 3. Data Needed
| Data | Source | Available? | Notes |
|------|--------|-----------|-------|
| [metric/field] | [table/system] | Yes/No/Partial | [gaps, quality concerns] |

### 4. Dimensions
What should we segment or decompose by?
- [Dimension 1]: [why: what would different values tell us?]
- [Dimension 2]: [why]
- [Dimension 3]: [why]

### 5. Time Range & Granularity
- **Period:** [start date to end date]
- **Granularity:** [daily / weekly / monthly]
- **Comparison:** [vs. prior period / vs. same period last year / vs. benchmark]

### 6. Output Format
What deliverable does the user need?
- [ ] Quick answer (1-2 sentences + supporting number)
- [ ] Analysis report (structured findings with charts)
- [ ] Presentation deck (slides for stakeholders)
- [ ] Data table (for further analysis by the user)

### 7. Success Criteria
How will we know the analysis answered the question?
[Specific, falsifiable conditions, e.g. "Identify which segment drove >50% of the decline"]

### Priority
- **Impact:** [High/Medium/Low, with justification]
- **Feasibility:** [High/Medium/Low, with justification]
- **Recommendation:** [Do First / Plan For / Do If Time / Skip]
```

### Using the Spec

**Scope calibration.** Match spec depth to the request. A number pull gets 1-2
sentences per field and fits on one screen; a monitoring ask gets a medium spec;
an exploration or deep dive gets full sections with sub-bullets. Never let the
spec become a blocker for quick pulls.

**Before analysis:** present the brief, STOP, and confirm with the user before
running any queries. The spec often reveals data gaps, scope mismatches, or
missing context; catching them upfront saves hours of rework.

**During analysis:** check the spec before each major step: are you still
answering the stated question? If something more interesting appears, note it as
a follow-up but finish the original question first.

**After analysis:** verify the deliverable matches field 6 and the success
criteria in field 7 are met; if not, note what is missing and why.

**Writing rules for the spec fields:**
- Dimensions must be justified; do not segment by everything. Each dimension
  needs a reason ("different devices have different UX, so conversion may differ").
- Success criteria must be falsifiable. "Good analysis" is not a criterion;
  "identify the segment responsible for >50% of the change" is.
- Output format must match the audience: an executive gets a deck, a data
  scientist gets a table, a PM gets an analysis report.

## Examples

### Example 1: Vague → Well-framed
**Incoming request:** "Can you look at our signup numbers?"

**Reframed:**
| Rung | Statement |
|------|-----------|
| **Goal** | Increase new user signups by 20% in Q1 |
| **Decision** | Should we invest in fixing the mobile signup flow or increasing top-of-funnel traffic? |
| **Metric** | Signup completion rate by device type + traffic source conversion rate |
| **Hypothesis** | Mobile signup completion rate is <50% of desktop because the form doesn't render properly on small screens. Fixing mobile is higher ROI than more traffic. |

### Example 2: Curiosity → Decision-driven
**Incoming request:** "I'm curious about our power users"

**Reframed:**
| Rung | Statement |
|------|-----------|
| **Goal** | Increase the percentage of users who become power users (>10 sessions/month) |
| **Decision** | Which onboarding interventions should we prioritize to convert casual → power users? |
| **Metric** | Behaviors in first 7 days that predict power user status at Day 30 |
| **Hypothesis** | Users who complete the tutorial AND create a project in their first session are 3x more likely to become power users. The tutorial completion rate is only 23%. |

### Example 3: Broad → Scoped
**Incoming request:** "Analyze our churn"

**Reframed:**
| Rung | Statement |
|------|-----------|
| **Goal** | Reduce 90-day churn from 35% to 25% |
| **Decision** | Which segment's churn should we tackle first — low-engagement users or users who hit a specific friction point? |
| **Metric** | 90-day churn rate by: (a) engagement tier in first 30 days, (b) last feature used before churning |
| **Hypothesis** | Users who never use Feature X churn at 2x the rate of users who do. Feature X has a discoverability problem, not a value problem. |

## Anti-Patterns

1. **Never start analyzing before framing** — "just pulling some numbers" without a question leads to interesting-but-useless findings. Produce the Question Brief FIRST, then hand off to analysis.
2. **Never accept "just curious" as the decision** — Push for "what would you do differently?" If the answer is truly nothing, offer Path A (quick stat) or Path B (clarify decision context first).
3. **Never frame questions with implied answers** — "Can you prove that Feature X works?" is not a question, it's confirmation bias. Reframe as "What is the impact of Feature X on [metric]?"
4. **Never frame questions too broadly** — "How are we doing?" needs scoping. What metric? What time range? Compared to what?
5. **Never skip the hypothesis** — Hypotheses prevent fishing expeditions and give you something specific to test.
6. **Never proceed without clarifying vague requests** — If you don't understand the decision context, ask clarifying questions iteratively until you do. Don't guess or assume.
