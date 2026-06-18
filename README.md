# AI Analyst

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![Claude Code Required](https://img.shields.io/badge/requires-Claude%20Code-blueviolet.svg)](https://claude.ai/code)
[![Version 3](https://img.shields.io/badge/version-3.0-success.svg)](#whats-new-in-v3)

An AI product analyst that lives inside Claude Code. Ask questions about your data in plain English and get back validated analyses, branded charts, and stakeholder-ready slide decks, in minutes, not days.

You talk to it the way you'd talk to an analyst on your team. No SQL to write, no dashboards to build. Connect your data, ask what you want to know, and it does the rest.

**65 skills · 43 agents · 44 helper modules · works on DuckDB, Postgres, BigQuery, and Snowflake**

---

## What's New in v3

v3 roughly doubles what AI Analyst can do, growing from 40 to 65 skills and 22 to 43 agents. The highlights:

- **Run experiments.** `/experiment` takes an A/B test from design through power, sample-ratio checks, analysis, and a clear ship or abort call. `/causal` covers the cases you can't randomize, like diff-in-diff and before/after comparisons.
- **Set a North Star.** `/north-star` helps you choose, audit, and diagnose your team's guiding metric.
- **Trust your numbers.** `/reliability` runs a question several times and tells you whether the answer holds steady enough to act on.
- **Fix your decks.** `/deck-critique`, `/slide-transform`, and `/deck-rescue` turn weak slides into a clear story.
- **Stay on brand.** `/theme-picker` and ready-made themes (FiveThirtyEight, Economist, or your own) keep every chart styled and easy to read.
- **Plan before you query.** `/analysis-design` turns a hunch into a testable plan, and `/stress-test` catches flaws before you waste time on the wrong analysis.
- **Share anywhere.** Export to Google Docs, Google Slides, Notion, PDF, Word, Slack, or email.
- **Teach and extend.** `/teach` builds visuals that explain a concept, and `/skill-creator` lets you add your own skills.

There's no bundled dataset, so it works on your own data from day one. Run `/connect-data` to hook up DuckDB, Postgres, BigQuery, or Snowflake, and AI Analyst learns your schema automatically.

---

## Getting Started

Three steps and you're running.

**1. Install**

```bash
git clone https://github.com/ai-analyst-lab/ai-analyst.git
cd ai-analyst
pip install -e ".[dev]"
```

**2. Open it**

Start Claude Code in the project folder. Run `/setup` for a short guided onboarding, or `/connect-data` to point it straight at your data.

**3. Ask**

Type a question the way you'd ask a colleague:

> What's our conversion rate by device?

That's all. It figures out which data to query, runs the analysis, and answers with a chart and a short read on what it means.

---

## What You Can Do

You drive everything in plain English. Here are the things people reach for most. Each example is something you'd actually type.

**Get a quick answer.** Ask a question, get a number with context and a chart.

> Which channel has the best 30-day retention?

**Run a full analysis.** For the bigger questions, it runs an end-to-end investigation and hands back a validated analysis and a slide deck.

> Why is checkout conversion dropping on mobile?

**Design and read experiments.** Plan an A/B test, size it, and interpret the result. Or handle the situations where you can't randomize.

> Help me design a test for the new onboarding flow.
>
> Is this experiment ready to ship, or should we keep it running?

**Set and defend a North Star.** Get help choosing your team's guiding metric, pressure-testing it, and figuring out why it stalled.

> Is "weekly active teams" a good north star for us?

**Check whether an answer is trustworthy.** Run the same question a few times and see if it holds steady enough to act on.

> Run that retention number again a few times and tell me if it's stable.

**Make a single chart.** Describe what you want and get a clean, on-brand chart.

> Make a funnel chart of the checkout flow and highlight the biggest drop-off.

**Fix a weak deck.** Score a presentation slide by slide and rebuild the ones that aren't landing.

> Critique this deck and rescue the worst slides.

**Share it anywhere.** Send results out in whatever format the audience needs.

> Export this as a Google Doc for the leadership review.

And when you're not sure what to do next, just ask:

> What can I do with this data?

---

## How It Works

Two ideas, and Claude handles the rest.

**Skills** are standards it follows automatically. When it makes a chart, it styles it properly. When it starts an analysis, it checks data quality first. When it reports a number, it gives you a comparison so the number means something. You never call these. They apply whenever they're relevant, and several can apply at once.

**Agents** are the multi-step workflows behind the bigger jobs. When you run a full analysis, Claude moves through a pipeline: it frames your question, explores and validates the data, investigates the root cause, builds a story, designs the charts, and assembles the deck, checking its own work at each step.

The result is an analyst that tells you what it found and why it matters, not just a query that returns rows.

---

## Commands

You can always just ask in plain English. Slash commands are shortcuts for common jobs.

**Analysis**
`/run-pipeline` full analysis to slide deck · `/resume-pipeline` pick up an interrupted run · `/explore` browse a dataset · `/analysis-design` turn a hunch into a plan · `/stress-test` review a plan for flaws · `/forecast` time-series projection

**Experiments and causal**
`/experiment` A/B design, power, analysis, decision · `/experiment-brief` structured test brief · `/causal` diff-in-diff, matching, before/after

**Metrics and trust**
`/north-star` design and audit your guiding metric · `/metrics` browse the metric dictionary · `/reliability` check if an answer is stable

**Decks and sharing**
`/deck-critique` score a deck · `/slide-transform` redesign one slide · `/deck-rescue` rebuild a whole deck · `/export` to Docs, Slides, Notion, PDF, Word, Slack, or email

**Your data**
`/connect-data` add a source · `/data` show the schema · `/datasets` list connected datasets · `/switch-dataset` change the active one · `/compare-datasets` compare across two

**Setup and knowledge**
`/setup` guided onboarding · `/business` browse org knowledge · `/history` past analyses · `/runs` inspect pipeline runs · `/teach` concept visuals · `/skill-creator` build your own skills

---

## Your Data

The repo ships clean, with no bundled dataset. You connect your own, and the system builds context around it.

Run `/connect-data` for a guided wizard (or `/setup` for full onboarding). Supported sources:

- **CSV files**, dropped in a directory
- **DuckDB**, local or MotherDuck
- **Postgres**, any Postgres-compatible database
- **BigQuery**, with a Google service account
- **Snowflake**, with user/password or key pair

It auto-profiles your data, writes schema documentation, and remembers context across sessions in `.knowledge/`. That memory also captures corrections (so the same mistake doesn't happen twice), proven query patterns, and your business glossary. A few public practice datasets live in `data/examples/`.

---

## Make It Yours

| Want to... | Do this |
|-----------|---------|
| Change how Claude thinks | Edit `CLAUDE.md` (persona, rules, workflow) |
| Add a new skill | Create `.claude/skills/my-skill/skill.md` |
| Add a new agent | Copy `agents/CONTRACT_TEMPLATE.md` |
| Change the slide theme | Add a YAML theme in `themes/brands/` |
| Adjust the pipeline | Edit `.claude/skills/run-pipeline/skill.md` |

See [docs/setup-guide.md](docs/setup-guide.md) for setup and [docs/theming.md](docs/theming.md) for branding.

---

## Requirements

- **Python 3.10+**
- **Claude Code** with a [Claude subscription](https://claude.ai/code)
- **Node.js 18+** for PDF and HTML slide export
- An internet connection for the Claude API and any cloud data sources

---

## Help and License

Questions or bugs: open an [issue](https://github.com/ai-analyst-lab/ai-analyst/issues). Licensed under [MIT](LICENSE).
