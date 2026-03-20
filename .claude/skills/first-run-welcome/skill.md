# Skill: First-Run Welcome

## Purpose
Provide an adaptive welcome experience based on setup state. Routes new users
through `/setup` for guided onboarding. Welcomes returning users with context
about their active dataset and quick actions.

## When to Use
- Session start (triggered by Knowledge Bootstrap)
- Before any analysis work begins

## Instructions

### Step 1: Detect setup state

Read `.knowledge/setup-state.yaml`. Classify into one of three states:

1. **Cold start** — file does not exist OR `setup_complete: false` with no
   `phases_completed` (empty or missing).
2. **Partial setup** — file exists, `setup_complete: false`, and at least one
   entry in `phases_completed`.
3. **Warm start** — file exists and `setup_complete: true`.

### Step 2: Route based on state

---

#### Cold Start (no setup-state.yaml or setup_complete: false, no phases done)

Present this welcome and route to `/setup`:

```
Welcome to AXS Analyst — your analytical partner for AXS product teams.

I help you turn business questions into validated insights, charts, and
presentations. Think funnel analysis, segmentation, root cause investigation,
trend detection — from question to slide deck.

Let's get you set up. I'll walk you through a quick interview to learn about
your data, your role, and what you want to analyze.

Starting setup now...
```

Then invoke `/setup` to begin the guided interview. Do NOT show dataset info,
tutorial content, or example queries. The setup flow handles all onboarding.

---

#### Partial Setup (some phases complete, setup not finished)

Read `phases_completed` and `phases_remaining` from `.knowledge/setup-state.yaml`.

```
Welcome back! Your setup is partially complete.

Done: [list phases_completed]
Remaining: [list phases_remaining]

Want to pick up where you left off? Type `/setup` to resume, or ask me
a question if you'd rather dive in.
```

---

#### Warm Start (setup_complete: true)

Read context from:
- `.knowledge/active.yaml` → `active_dataset` name
- `.knowledge/datasets/{active}/manifest.yaml` → table count
- `.knowledge/analyses/index.yaml` → `last_updated` for last analysis date

```
Welcome back! Here's where things stand:

Dataset: [DATASET_NAME] ([N] tables)
Last analysis: [DATE or "none yet"]

Quick actions:
- Ask a question — "What's our conversion rate by channel?"
- /explore — interactive data exploration
- /run-pipeline — full analysis from question to deck

What would you like to work on?
```

If `active_dataset` is null (setup complete but no data connected), show:

```
Welcome back! Setup is complete but no dataset is active yet.

- /connect-data — add a dataset
- /datasets — see available datasets

What would you like to do?
```

### Step 3: Proceed

After presenting the welcome:
- **Cold start:** Hand off to `/setup`. Do not proceed with analysis.
- **Partial setup:** If user types `/setup`, hand off. If user asks a question,
  route through Question Router and note that setup can be finished later.
- **Warm start:** If user asks a question, route through Question Router.
  If user picks a quick action, invoke that skill/agent.

## Anti-Patterns

1. **Never show welcome to warm-start users who typed a question.** If their
   first message is a question, answer it — weave a one-line "welcome back"
   naturally.
2. **Never show dataset details or tutorial content on cold start.** The
   `/setup` flow handles all onboarding.
3. **Never overwhelm with feature lists.** Keep each welcome variant concise.
4. **Never reference NovaMart, bootcamp, or workshop content.** This is a
   general-purpose tool, not a course.
5. **Never block on welcome.** If the user already asked a question, serve
   it — adapt the welcome around their intent.
