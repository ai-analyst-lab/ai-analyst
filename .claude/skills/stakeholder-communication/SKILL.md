---
name: stakeholder-communication
description: Adapt analytical findings to the audience — same insight, different framing, detail level, and format depending on who will read it. Use this skill whenever producing a narrative, creating a deck, writing an executive summary, drafting a report, generating stakeholder communications, or whenever the user mentions an audience (executive, PM, engineer, data scientist, leadership team, stakeholders, decision-makers). Apply when users say things like "prepare this for leadership", "write this for the product team", "explain this to engineering", "create a deck for the VP", "draft a summary for stakeholders", "make this executive-friendly", "adapt this for data scientists", "what should I tell the CEO", "how do I present this", "tailor this for the audience", or any request involving communication, presentation, reporting, or sharing findings with others. Always apply when the Storytelling agent runs, when the Deck Creator agent runs, when drafting communications, when exporting results, or when the output will be read by someone other than the user. Default to Product Team format if no audience is specified.
---

# Skill: Stakeholder Communication Matrix

## Purpose
Adapt analytical findings to the audience — same insight, different framing, detail level, and format depending on who will read it. Ensures that executives get the bottom line, PMs get the implications, engineers get the specifics, and data teams get the methodology.

## When to Use
Apply this skill when producing a narrative (Storytelling agent), creating a deck (Deck Creator agent), or whenever the user specifies an audience. If no audience is specified, default to **Product Team** format.

## Instructions

### Pre-flight: Load Learnings
Before executing, check `.knowledge/learnings/index.md` for relevant communication preferences:
1. **Try to read the file**: Use the Read tool on `.knowledge/learnings/index.md`
2. **If it exists**, scan for entries under these headings:
   - **"Communication"** - stakeholder preferences, formatting conventions
   - **"General"** - cross-cutting preferences that apply to all work
   - **"Stakeholder Preferences"** - audience-specific guidance
3. **If it doesn't exist or is empty**, skip silently and proceed with standard stakeholder matrix
4. **If entries exist**, incorporate them as constraints (e.g., "VP prefers 1-page summaries", "always include confidence grades for data team")
5. **Never block execution** if learnings are unavailable - this is an enhancement, not a blocker

Example learnings that would apply:
- "Executive team prefers dashboards over text reports"
- "Product team wants effort estimates in days, not story points"
- "Data team requires p-values for all statistical claims"

### The Stakeholder Matrix

Different audiences care about different things. For the same finding, adapt:

| Dimension | Executive | Product Team | Engineering | Data Team |
|-----------|----------|-------------|-------------|-----------|
| **Lead with** | Business impact ($, users, risk) | What to do about it (action) | What's broken and where (specifics) | How we found it (methodology) |
| **Detail level** | Bottom line + 1 supporting fact | Findings + implications + next steps | Root cause + technical details + fix scope | Methodology + data quality + caveats |
| **Format** | 3 slides max / 1-paragraph summary | Analysis report with charts | Investigation log with queries/code | Full report with validation section |
| **Metrics language** | Revenue, users, growth rate | Conversion, retention, engagement | Error rate, latency, success rate | Statistical significance, confidence intervals |
| **Time horizon** | This quarter / this year | This sprint / this month | This release / this deploy | This analysis / this dataset |
| **Charts** | 1-2 high-level (big number, trend) | 3-5 focused (funnel, segmentation) | Technical plots (timelines, error logs) | Distribution, correlation, validation |
| **Caveats** | Only if they change the recommendation | Noted alongside findings | Noted with technical implications | Full methodology section |
| **Recommendation style** | "We should X" (decisive) | "I recommend X because Y" (reasoned) | "The fix is X, effort is Y" (scoped) | "The data supports X with caveats Y" (qualified) |

### How to Adapt

#### Step 1: Identify the Audience

Detect the audience from both **explicit mentions** and **context clues**. Never guess blindly - if unclear after checking these signals, ask the user to clarify.

**Explicit signals** (direct audience mentions):
- "Prepare this for the leadership team" / "my VP wants to see this" / "present to the CEO" → Executive
- "present to the product team" / "sprint planning" / "PM review" → Product Team
- "Can you dig into the root cause?" / "engineering needs this" → Engineering
- "data science team wants to understand" / "review before we present" / "peer review" → Data Team

**Context clues** (implicit signals):
- **Urgency + Business outcome** → likely Executive
  - "tomorrow morning" / "board meeting Friday" / "urgent update needed"
  - Combined with business language ($, revenue, users, risk)
- **Planning context** → likely Product Team
  - "sprint planning" / "roadmap discussion" / "prioritization meeting"
  - Questions like "what should we do?" / "how do we prioritize?"
- **Technical investigation** → likely Engineering
  - "root cause" / "debug" / "fix" / "error logs" / "latency issue"
  - Focus on specific systems, code, or infrastructure
- **Methodology questions** → likely Data Team
  - "how confident are we?" / "validate this" / "peer review"
  - Requests for methodology, statistical rigor, caveats

If no audience is specified and no clear context clues, default to **Product Team** format (most versatile).

#### Step 2: Select the Lead

Every communication starts with the most important thing for that audience:

```
EXECUTIVE:    "This is costing us $X per month."
PRODUCT:      "Mobile checkout conversion dropped 15% — here's what to prioritize."
ENGINEERING:  "iOS app v2.3.0 has a payment processing regression in the checkout flow."
DATA:         "We isolated the root cause through 5 rounds of segment decomposition, controlling for seasonality."
```

Same finding. Different first sentence.

#### Step 3: Calibrate Detail

Use the pyramid principle — start with the conclusion, add detail as the audience requires:

```
Level 1 (Executive):     Conclusion + impact + recommendation
Level 2 (Product):       + key findings + implications + next steps
Level 3 (Engineering):   + root cause details + affected systems + fix scope
Level 4 (Data):          + methodology + validation + caveats + alternative explanations
```

Each level includes everything above it plus more depth.

#### Step 4: Adapt the Recommendation

| Audience | Recommendation Style | Example |
|----------|---------------------|---------|
| Executive | Decisive, resource-oriented | "Recommend allocating 2 engineers for 1 sprint to fix the iOS payment bug. Expected recovery: $64K/year." |
| Product | Reasoned, prioritized | "Recommend prioritizing the iOS payment fix over the checkout redesign. The bug affects 12% of transactions and has a clear fix, while the redesign has uncertain ROI." |
| Engineering | Specific, scoped | "The regression is in `PaymentProcessor.swift` introduced in v2.3.0 commit `abc123`. Hotfix path: revert the payment tokenization change and deploy v2.3.1." |
| Data | Qualified, methodical | "The data strongly supports a causal link between v2.3.0 and the ticket spike (r²=0.94, controlled for seasonality and mix shift). Recommend confirming with server logs before concluding." |

### Multi-Audience Documents

**Use multi-audience format when:**
- The document will be shared widely (emailed to a distribution list with mixed roles, posted to wiki)
- It's a formal analysis report that serves as a reference document
- The user explicitly says "this needs to work for everyone" or mentions multiple audience types
- You're creating an artifact that will be archived/referenced later by different stakeholders
- **Unclear who the audience is** (when in doubt, default to multi-audience with labeled sections)

**Use single-audience format when:**
- The user specifies a single audience ("prepare this for my VP", "write this for engineering")
- It's a live presentation (deck, meeting brief) — pick the primary audience in the room
- Time is constrained ("tomorrow morning") — optimize for one audience, don't try to serve everyone
- The context is meeting-specific ("sprint planning", "board meeting") — tailor to that meeting's attendees

**Default rule:** When unclear about the audience, ASK the user "Who will read this?" before proceeding. A quick clarification question saves rework.

**Multi-audience structure** (when needed):
1. **Executive Summary** (Level 1) — 3-5 sentences, bottom line first
2. **Key Findings for Product** (Level 2) — what happened, why, what to do
3. **Technical Details for Engineering** (Level 3) — root cause, affected systems, fix scope
4. **Methodology for Data** (Level 4) — how the analysis was done, validation, caveats

Label sections clearly so readers can jump to their level. This creates a "pyramid" structure where each level contains everything above it plus more depth.

### Output Format

When applying this skill, note the audience adaptation at the top of the deliverable:

```markdown
**Audience:** [Executive / Product / Engineering / Data / Multi-audience]
**Adapted for:** [Name or role, if known]
**Detail level:** [Level 1-4]
```

#### Template Mode vs Analysis Presentation

Distinguish between drafting a structure and presenting actual findings:

**If you're drafting a template or structure** (user hasn't done analysis yet):
- Use clearly marked placeholders: `[Insert actual value from analysis]` or `[$X in lost revenue - from analysis]`
- Never fabricate numbers or statistics to illustrate the template
- Focus on structure, format, and what goes where
- Example: "Revenue at risk: `[$X/month from mobile checkout funnel analysis]`"

**If you're presenting actual analysis results**:
- Use concrete numbers from your analysis or the user's findings
- Cite the data source (table, query, date range) inline
- Show your work (include supporting queries/charts as appendices for technical audiences)
- Example: "Revenue at risk: $47K/month (from orders.checkout_completed, Oct 2024)"

This prevents hallucination while preserving the skill's value for both planning and presenting.

#### Source Attribution by Audience

For every quantitative claim, cite the source appropriate to the audience:

| Audience | Attribution Style | Example |
|----------|------------------|---------|
| **Executive** | Brief inline citation | "based on mobile checkout data, Oct 2024" |
| **Product** | Table/column reference | "from orders.checkout_completed events" |
| **Engineering** | Full query in appendix with explanation | "See Appendix A: checkout_drop_query.sql lines 15-23" |
| **Data** | Complete query + validation + data quality notes | "Query validates with row count match (n=15,234), no nulls in key fields, 2% outlier rate within expected bounds" |

This builds trust and allows stakeholders to verify claims independently.

## Examples

### Example: Same Finding, Four Audiences

**Finding:** Support ticket volume spiked 55% in June due to an iOS payment bug in app v2.3.0, causing 356 excess tickets and ~$5,340 in support costs.

**Executive version:**
> Support costs increased $5,340/month due to an iOS app bug. Engineering has identified the fix. Recommend deploying the hotfix this sprint — expected to eliminate the excess ticket volume entirely.

**Product version:**
> iOS payment failures spiked in June after the v2.3.0 release, driving a 55% increase in support tickets. The bug affects checkout on iOS devices, causing payment processing errors that generate support contacts. Recommend prioritizing the hotfix (v2.3.1) over planned feature work this sprint. After the fix, monitor ticket volume for 2 weeks to confirm recovery.

**Engineering version:**
> The payment tokenization change in v2.3.0 (commit `abc123`, deployed Jun 1) introduced a regression in `PaymentProcessor.swift` that causes intermittent failures on iOS 16+ when using Apple Pay. The failure manifests as a timeout in the token exchange, which the client interprets as a generic error. 356 excess support tickets were generated between Jun 1-14. The fix is to revert the tokenization change and use the v2.2.x payment path until the token exchange timeout is resolved. Estimated effort: 2 story points.

**Data version:**
> We isolated the root cause through 5 rounds of iterative decomposition: total tickets → monthly anomaly (June) → category isolation (payment issues, 72% of excess) → device isolation (iOS, 89% of payment excess) → version isolation (v2.3.0, 95% of iOS excess). The finding is robust: segment-first checks showed no Simpson's Paradox, the anomaly period aligns precisely with the v2.3.0 release window (Jun 1-14), and the v2.4.0 hotfix on Jun 15 shows immediate recovery. Confidence: HIGH. Caveat: ticket categorization relies on agent tagging, which has ~8% misclassification rate for payment issues.

## Anti-Patterns

1. **Never give an executive a methodology-first report** — they need the bottom line, not how you got there
2. **Never give an engineer a business-impact-only summary** — they need the specifics to act on it
3. **Never skip the recommendation** — every audience needs to know what to do next, even if the framing differs
4. **Never assume one format fits all** — if you're presenting to a mixed group, use the multi-audience structure with labeled sections
5. **Never hide caveats from the data team** — they will find them and lose trust in the analysis
6. **Never overload executives with caveats** — mention only caveats that would change the recommendation
