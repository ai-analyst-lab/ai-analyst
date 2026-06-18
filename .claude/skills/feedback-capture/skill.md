---
name: feedback-capture
description: Automatically capture user corrections, methodology learnings, and positive feedback to the knowledge system. This skill runs silently BEFORE Question Router on every user message to detect feedback signals. Use this skill whenever the user corrects your work ("that's wrong", "actually it's...", "you should have..."), teaches a methodology ("next time...", "always use...", "never do..."), or confirms correctness ("that's right", "perfect", "good analysis"). Also trigger when users mention mistakes, errors, incorrect numbers, wrong columns, missing filters, double-counting, or any variant of "you forgot to..." or "it should be...". This skill learns from every correction to prevent repeating the same analytical mistakes. Captures to `.knowledge/corrections/` and `.knowledge/learnings/` automatically without blocking the pipeline.
---

# Skill: Feedback Capture

## Purpose
Pre-router interceptor that runs BEFORE Question Router on every user message.
Detects correction signals, methodology learnings, and positive feedback, captures
them to `.knowledge/`, then passes through to normal routing.

This is production code that runs on every message. It should be completely invisible
to the user — no output, no announcements, no execution reports.

## When to Use
- On every incoming user message, before Question Router classification
- Runs silently — the user should never notice this skill executing
- This is NOT a testing/demonstration context — it's real production behavior

## Instructions

### Step 0: Understand what "silent operation" means

This skill runs in production on every user message. The user should experience:
- Brief acknowledgment ("Got it, logged as CORR-X" or "Noted for future analyses")
- Immediate answer to their actual question
- NO execution reports, NO summaries of what the skill did

**What you will produce:**
```
Got it, logged as CORR-008. Here's the corrected Q4 conversion rate using order_total:
[analysis results here]
```

**What you will NOT produce:**
```
# Feedback Capture Skill Output
## Execution Summary
Task: User provided a correction...
Actions Taken: 1. Detected correction signal...
```

If you create sections like "Execution Summary", "Skill Behavior Verification",
"Correction Logged", or any meta-commentary about the skill's operation, you have
failed. The skill's job is to capture silently and let the analyst do their work.

**Critical**: Wrap all logic in try/except. If anything fails, pass through silently
to Question Router. Never block the pipeline.

### Step 1: Detect feedback type

Scan the user's message for these signal patterns:

**Correction signals** (user says something was wrong):
- "that's wrong", "that's incorrect", "actually it's...", "it should be..."
- "the column is X not Y", "that number should be...", "you used the wrong..."
- "off by...", "overcounted", "undercounted", "double-counted"
- "that join is wrong", "missing a filter", "forgot to exclude..."

**Learning signals** (user teaches a reusable methodology):
- "next time...", "always use...", "never use...", "prefer X over Y"
- "the convention here is...", "our team uses...", "don't forget to..."
- "a better approach would be...", "going forward...", "remember that..."

**Positive signals** (user confirms correctness):
- "that's right", "exactly", "perfect", "good analysis", "looks good"

**No signal**: If no pattern matched, pass through silently. If multiple match,
prioritize: Correction > Learning > Positive.

### Step 2: Act on detection

#### If Correction detected:

1. Read `.knowledge/corrections/index.yaml` to get `last_correction_id`.
2. Compute next ID: increment the numeric suffix (e.g., `CORR-001` -> `CORR-002`).
   If `last_correction_id` is null, start at `CORR-001`.
3. Estimate severity from context:
   - **critical**: Wrong conclusion presented to stakeholders
   - **high**: Wrong numbers in output, incorrect joins affecting results
   - **medium**: Wrong column, filter, or metric definition used
   - **low**: Minor label, formatting, or naming issue
4. Classify category: `join_error` | `filter_missing` | `metric_definition` |
   `date_range` | `aggregation` | `schema` | `logic` | `other`
5. Read `.knowledge/corrections/log.yaml`.
6. Append a new entry to the `corrections` list:
   ```yaml
   - id: "CORR-{N}"
     date: "{TODAY}"
     severity: "{estimated}"
     category: "{classified}"
     dataset: "{active dataset or null}"
     tables: []
     description: "{what the user said was wrong}"
     fix: "{what the user said is correct}"
     sql_before: null
     sql_after: null
     prevented_by: null
   ```
   Fill `tables`, `sql_before`, `sql_after`, and `prevented_by` only if the
   user's message contains enough detail. Leave null otherwise.
7. Write updated `log.yaml`.
8. Update `.knowledge/corrections/index.yaml`: increment `total_corrections`,
   increment the matching `by_severity` and `by_category` counts, set
   `last_correction_id` and `last_updated`.
9. Acknowledge briefly in your response: "Got it, logged as {ID}."
10. **Then immediately process the user's underlying request** — if they asked
    "that's wrong, the column is X not Y, now show me the correct analysis",
    you logged the correction AND you run the corrected analysis. Don't stop
    after logging.

#### If Learning detected:

1. Read `.knowledge/learnings/index.md`.
2. Classify into one of the six categories:
   - Data Patterns | Query Techniques | Business Context |
     Stakeholder Preferences | Visualization Insights | Methodology Notes
3. Append a bullet point under the matching `### {N}. {Category}` heading.
   Format: `- {concise learning} (source: user feedback, {TODAY})`
4. Write updated `index.md`.
5. Acknowledge briefly in your response: "Noted for future analyses."
6. **Then immediately process the user's underlying request** — if they said
   "next time exclude test users" as part of asking for a retention analysis,
   you log the learning AND you run the retention analysis with test users
   excluded.

#### If Positive feedback detected:

Acknowledge briefly in your response ("Thanks!" or similar) and continue processing
the rest of the message normally. No file writes needed.

**If the message contains a follow-up request after positive feedback** (e.g.,
"that looks perfect, now can you..."), proceed directly to fulfilling that request.

#### If No signal detected:

Pass through silently. Do NOT say "I didn't detect feedback." Proceed directly
to the Question Router for normal request processing.

### Step 3: Respond to the user (production output)

Your response to the user should feel natural and helpful. Examples:

**Correction with follow-up:**
```
Got it, logged as CORR-008. Here's the corrected Q4 2024 conversion rate using order_total:
- October: 89.02% conversion, $5,586.21 revenue
- November: 84.62% conversion, $3,110.90 revenue
- December: 86.81% conversion, $9,522.20 revenue
- Q4 Total: 86.85% conversion, $18,219.32 revenue

[SQL query here if relevant]
```

**Learning without follow-up:**
```
Noted for future analyses. I've updated the methodology to exclude test users
(email contains '@test.com' or user_id < 1000) in all retention calculations.
```

**Positive feedback with follow-up:**
```
Thanks! Here's the breakdown by device type:
[analysis results here]
```

**What NOT to include:**
- Section headers like "## Execution Summary" or "## Skill Behavior Verification"
- Descriptions of what the skill detected or how it classified the feedback
- File paths showing where data was saved
- Lists of "Actions Taken" or "File Changes"
- Meta-commentary about skill operation

The user cares about their ANALYSIS, not about your bookkeeping. The only mention
of feedback capture should be the brief acknowledgment line.

### Error handling

All detection and capture logic MUST be wrapped in try/except. If file reads or
writes fail, skip capture entirely and proceed to routing. The analyst's primary
job is answering questions, not bookkeeping.

If a file write fails, do NOT retry or announce the failure. Log nothing and
continue to the user's request as if feedback capture never ran.

## Anti-Patterns (Common Mistakes)

1. **Creating execution reports** -- Do NOT write sections like "## Execution Summary",
   "## Skill Behavior Verification", "## File Changes", "## What the user would see".
   These are meta-commentary. The user wants their ANALYSIS, not a report about your
   internal bookkeeping.

2. **Stopping after logging** -- Do NOT log the feedback and then stop. If the user
   asked "that's wrong, use column X, now show me the corrected analysis", you must
   do BOTH: log the correction AND run the corrected analysis in the same response.

3. **Announcing detection** -- Do NOT say "I detected a correction signal" or
   "feedback type classified as learning". Just acknowledge briefly and continue.

4. **Asking for confirmation** -- Do NOT ask "should I log this as a correction?"
   Classify silently and log.

5. **Blocking the pipeline** -- If file writes fail, skip silently and continue to
   the user's request. Never halt on logging errors.

6. **Fabricating details** -- Use `null` for correction fields you cannot infer from
   the user's message. Don't guess.

7. **Announcing non-detection** -- If no feedback was detected, pass through silently.
   Do NOT say "I didn't detect any feedback."

8. **Heavy processing** -- This runs on EVERY message. Keep it fast: pattern match,
   write files, acknowledge, continue. No complex analysis of the feedback itself.

## Examples of correct behavior

**Example 1: Correction with follow-up**
User: "Actually that conversion rate is wrong, you're using total_revenue when you should be using order_total. Show me the correct numbers."

Your response: "Got it, logged as CORR-004. Here's the corrected conversion rate using order_total: [runs analysis with correct column]"

**Example 2: Learning without follow-up**
User: "Next time when you're calculating retention always exclude test users where email contains '@test.com' or user_id < 1000."

Your response: "Noted for future analyses. I've updated the learnings system to exclude test users (email '@test.com' or user_id < 1000) in all retention calculations."

**Example 3: Positive feedback with follow-up**
User: "That analysis looks perfect! Can you now break it down by device type?"

Your response: "Thanks! Here's the breakdown by device type: [runs device segmentation analysis]"

**Example 4: No feedback signal**
User: "Show me revenue by category for Q4"

Your response: [proceeds directly to analysis, no mention of feedback capture]
