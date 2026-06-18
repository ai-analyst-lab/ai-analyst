# AI Analyst

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![Claude Code Required](https://img.shields.io/badge/requires-Claude%20Code-blueviolet.svg)](https://claude.ai/code)
[![Version 3](https://img.shields.io/badge/version-3.0-success.svg)](#-whats-new-in-v3)

An AI-powered product analyst that lives inside Claude Code. Ask business questions in plain English, get validated analyses, branded charts, and stakeholder-ready slide decks, in minutes, not days.

**43** agents | **65** skills | **44** helper modules | DAG-based parallel execution | PDF + HTML + Google Docs / Slides / Notion export

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

## What This Is

AI Analyst turns Claude Code into a product analytics system. It combines:

- **Skills** (`.claude/skills/`), standards Claude follows automatically (chart styling, data validation, question framing, stakeholder communication)
- **Agents** (`agents/`), multi-step analytical workflows orchestrated by a DAG engine (question framing → data exploration → analysis → storytelling → deck creation)
- **Helpers** (`helpers/`), Python modules for charting, SQL validation, data connectivity, statistical tests, and more
- **Knowledge** (`.knowledge/`), persistent memory for dataset context, corrections, proven SQL patterns, and business glossary

You interact by talking to Claude. Ask a question, invoke a slash command, or let Claude figure out which skills and agents to apply.

---

## Quick Start

**1. Clone and install**

```bash
git clone https://github.com/ai-analyst-lab/ai-analyst.git
cd ai-analyst
pip install -e ".[dev]"
```

**2. Connect your data** (optional)

In Claude Code, run `/connect-data` to wire up a warehouse (DuckDB, Postgres,
BigQuery, Snowflake) or a CSV directory. Curated public datasets with guides live
in `data/examples/`.

**3. Start Claude Code**

```bash
claude
```

**4. Ask a question**

```
What's our conversion rate by device?
```

Or run the full pipeline:

```
/run-pipeline question="Why is conversion dropping on mobile?"
```

---

## Don't Know What to Do? Just Ask.

Claude knows the entire system, every agent, skill, command, and dataset. If you're stuck:

```
What can I do with this data?
What should I run to refresh the deck?
How do I connect my own CSV files?
Which agents handle root cause analysis?
Re-run just the chart maker and deck creator.
```

You don't need to memorize anything in this README. Think of it as a reference, Claude is the guide.

---

## Five Things You Can Do

### 1. Ask a quick question

```
What's our conversion rate by device?
```

Claude queries the data and returns an answer with a chart. Simple questions get answered in under 2 minutes without running the full pipeline.

### 2. Run a full analysis

```
/run-pipeline question="What's driving the decline in conversion?"
```

The pipeline runs 18 agents across 4 phases: Frame the question, Analyze the data, Build the story, Create the deck. You get a validated analysis, branded charts, a narrative, and a slide deck with speaker notes. Exports to PDF, HTML, and Google Docs.

### 3. Explore a dataset

```
/explore
```

Interactive data browsing without committing to a full analysis. Preview tables, check distributions, spot patterns, form hypotheses.

### 4. Connect your own data

```
/connect-data
```

Guided wizard for CSV files, local DuckDB, Postgres, BigQuery, or Snowflake. Auto-profiles your data, creates schema docs, and remembers context across sessions.

### 5. Make a single chart

```
Make a funnel chart of the checkout flow, highlighting the biggest drop-off step.
```

Charts follow Storytelling with Data methodology: warm off-white background, decluttered axes, action title, direct labels instead of legends.

---

## How It Works: The Pipeline

When you run `/run-pipeline`, Claude orchestrates 18 agents across 4 phases:

```
1. FRAME              2. ANALYZE                          3. STORY                 4. DECK
+-----------------+   +-----------------------------+   +--------------------+   +------------------+
| Question        |   | Data Explorer               |   | Story Architect    |   | Storytelling     |
|   Framing       |   |   > Source Tie-Out           |   |   > Coherence      |   |   > Deck Creator |
|   > Hypothesis  |   |   > Descriptive Analytics    |   |     Reviewer       |   |   > Slide Review |
|     Generation  |   |   > Root Cause Investigator  |   |   > Chart Maker    |   |   > Close the    |
|                 |-->|   > Validation               |-->|   > Design Critic  |-->|     Loop         |
+-----------------+   |   > Opportunity Sizer        |   +--------------------+   +------------------+
                      +-----------------------------+
```

**Phase 1, Frame:** Structures your business question into analytical questions with testable hypotheses.

**Phase 2, Analyze:** Explores the data, verifies loading integrity, runs segmentation/funnel/drivers analysis, drills to root cause, validates findings, and sizes the opportunity.

**Phase 3, Story:** Designs a storyboard (Context-Tension-Resolution arc), generates charts with collision detection, and reviews visual quality.

**Phase 4, Deck:** Writes a stakeholder narrative, builds a branded Marp slide deck, reviews design, and ensures every recommendation has a follow-up plan. Exports to PDF, HTML, and Google Docs.

Five execution plans let you run just the part you need:

| Plan | Use When | What Runs |
|------|----------|-----------|
| `full_presentation` | Complete analysis to slide deck | All 18 agents |
| `deep_dive` | Analysis without presentation | Phases 1-2 only |
| `quick_chart` | Just need one chart | Chart Maker + Design Critic |
| `refresh_deck` | Re-do the presentation layer | Phases 3-4 (reuses analysis) |
| `validate_only` | Check existing work | Validation + Source Tie-Out |

```
/run-pipeline question="..." plan=deep_dive
```

If the pipeline gets interrupted, resume where you left off:

```
/resume-pipeline
```

---

## All Commands

| Command | What It Does |
|---------|-------------|
| `/run-pipeline` | Full analysis to slide deck |
| `/resume-pipeline` | Resume interrupted pipeline |
| `/explore` | Interactive data exploration |
| `/data` | Show active dataset schema |
| `/datasets` | List all connected datasets |
| `/switch-dataset` | Change the active dataset |
| `/connect-data` | Add a new data source |
| `/setup` | Interactive onboarding interview |
| `/metrics` | Browse the metric dictionary |
| `/history` | View past analyses |
| `/patterns` | View recurring patterns |
| `/export` | Export as slides, email, Slack, Google Doc, or Word |
| `/forecast` | Generate a time-series forecast |
| `/runs` | List, inspect, compare pipeline runs |
| `/business` | Browse organization knowledge |
| `/log-correction` | Log a data or methodology correction |
| `/architect` | Multi-persona planning methodology |
| `/notion-ingest` | Import business context from Notion |
| `/compare-datasets` | Compare metrics across datasets |
| `/deck-critique` | Score a deck slide-by-slide against SWD checklist |
| `/deck-rescue` | Full deck rewrite pipeline |
| `/slide-transform` | Redesign a single bad slide |
| `/analysis-design` | Full lifecycle from hunch to validated investigation plan |
| `/stress-test` | 7-point review of any analysis plan |
| `/experiment-brief` | Generate a structured A/B test brief |
| `/kickoff` | Introduce yourself to the community on Slack |
| `/show-off` | Share what you built with the community |

Or just ask in plain English. "Show me conversion by device" works as well as any command.

---

## Your Data

This repo ships clean, no bundled datasets. Connect your own data and the system builds context around it.

### Connect your own

Run `/connect-data` for a guided wizard, or `/setup` for full onboarding. Supported sources:

- **CSV files**, drop them in a directory, point Claude at it
- **DuckDB**, local or MotherDuck
- **Postgres**, any Postgres-compatible database
- **BigQuery**, Google BigQuery with service account
- **Snowflake**, Snowflake with user/password or key pair

The system auto-profiles your data, creates schema documentation, and remembers context across sessions in `.knowledge/datasets/`.

### Sample data

Bring your own data via `/connect-data` (DuckDB, Postgres, BigQuery, Snowflake, or
a CSV directory). Curated public datasets with README guides are available in `data/examples/`.

---

## Architecture

```
ai-analyst/
├── CLAUDE.md                    # AI persona, skills table, rules, workflow
├── agents/                      # 18 agent prompt templates (markdown)
│   ├── registry.yaml            # DAG dependencies and execution order
│   └── CONTRACT_TEMPLATE.md     # Template for writing new agents
├── .claude/skills/              # 55 skill definitions
├── helpers/                     # 40 Python modules
│   ├── chart_helpers.py         # SWD charting (swd_style, highlight_bar, etc.)
│   ├── data_helpers.py          # Data source abstraction
│   ├── sql_helpers.py           # SQL sanity checks
│   └── ...
├── .knowledge/                  # Persistent memory (dataset context, corrections, patterns)
│   ├── active.yaml              # Currently active dataset
│   └── datasets/                # Per-dataset manifest, schema, quirks
├── themes/                      # Marp CSS themes (light + dark)
├── templates/                   # Marp deck templates, HTML components
├── outputs/                     # Final deliverables (analyses, charts, decks)
└── working/                     # Intermediate files (gitignored)
```

### Skills vs Agents

**Skills** are standards Claude follows automatically. When you make a chart, the Visualization Patterns skill activates. When you start an analysis, Data Quality Check runs. You never invoke them, they apply when their trigger condition matches. Multiple skills can fire at once.

**Agents** are multi-step workflows for specific tasks. They're markdown prompt templates with `{{VARIABLES}}` that get substituted at runtime. The pipeline orchestrates them in dependency order using a DAG engine.

### Knowledge System

`.knowledge/` persists across sessions:
- **Dataset context**, schema, quirks, connection details per dataset
- **Corrections**, logged mistakes so the same SQL error never happens twice
- **Query archaeology**, proven SQL patterns retrieved before writing new queries
- **Business glossary**, organization-specific terms, metrics, products, teams (importable from Notion)

---

## Customization

| Want to... | Do this |
|-----------|---------|
| Change how Claude thinks | Edit `CLAUDE.md` (persona, rules, workflow) |
| Add a new skill | Create `.claude/skills/my-skill/skill.md` |
| Add a new agent | Create `agents/my-agent.md` using `agents/CONTRACT_TEMPLATE.md` |
| Change the slide theme | Create a YAML theme in `themes/brands/` |
| Modify the pipeline | Edit `.claude/skills/run-pipeline/skill.md` |
| Add to the agent DAG | Edit `agents/registry.yaml` |

---

## Requirements

- **Python 3.10+**
- **Claude Code** with a [Claude Pro or Max subscription](https://claude.ai/pro)
- **Node.js 18+** (for Marp PDF/HTML export)
- **Internet connection** (for Claude API and optional cloud data sources)

---

## Getting Help

- **Setup guide:** [docs/setup-guide.md](docs/setup-guide.md)
- **Theming:** [docs/theming.md](docs/theming.md)
- **Questions or bugs:** Ask in the `#help` channel on Slack
