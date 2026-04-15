# AI Analyst — Pearson ELL

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Claude Code Required](https://img.shields.io/badge/requires-Claude%20Code-blueviolet.svg)](https://claude.ai/code)

An AI product analyst built on Claude Code, configured for **Pearson English Language Learning (ELL)**. You ask a business question about PEP and its connected products — Claude queries Mixpanel via MCP, finds the answer, and hands you a validated insight, chart, or Mixpanel dashboard.

**18** specialized agents | **39** auto-applied skills | **20** slash commands | Mixpanel MCP data source | BigQuery-ready for future use

---

## What This Is

This is the AI Analyst framework, customized for Pearson ELL analytics. It is pre-configured with:

- **Pearson ELL organization context** — glossary of PEP products and terms (PEP, MEL, PEC, SLG, ST, TH), data interpretation rules (entitlement ≠ engagement, TestHub provisioning, user role context)
- **User profile** — Christian Dalmau, Product Analyst, Pearson ELL
- **Mixpanel MCP dataset** — `mixpanel_pep` connected as the active dataset
- **Two primary use cases** — answer business questions from Mixpanel data; build and update Mixpanel dashboards directly via MCP

Future use cases (infrastructure already in place): BigQuery as an additional data source; PowerBI as a dashboard output.

---

## Before You Start

This is a tool for analysts, not a replacement for them. It handles about 80% of what a human analyst does — the 80% that takes all the time. But it only works if you're the expert.

**You are the eval.** Run this on questions you already know the answer to. When Claude picks the wrong event name or misinterprets a metric, you'll catch it immediately. You correct it, it saves the correction, and it doesn't make that mistake again. That's the whole loop: look, know, correct, move on.

Don't run it on data you've never seen. The analyses it produces need your judgment before they go anywhere near a stakeholder. If you skip validation, you'll get confident-sounding numbers that might be wrong.

**The byproduct of building this is the work itself.** You're not taking time off from your job to set up an AI tool. You're doing your actual work through it. The first analysis takes a bit longer while you're correcting event names and teaching it your context. By the third one, you're faster than doing it by hand.

**This doesn't work out of the box.** The Pearson ELL context is pre-loaded, but Mixpanel event names and metric definitions are always queried live from Mixpanel via MCP. Claude does not assume what events exist — it asks. Correct it when it's wrong, and it learns.

---

## Don't Know What to Do? Just Ask.

Claude knows the entire system — every agent, skill, command, and the Pearson ELL business context. If you're stuck, ask it:

```
What can I do with Mixpanel data?
How do I build a retention dashboard in Mixpanel?
Which events should I use for the activation funnel?
How do I check if SLG adoption is growing week over week?
```

Claude will frame the question, query Mixpanel, and either answer directly or run the relevant agents. You don't need to memorize anything in this README.

---

## Quick Start

**1. Install Claude Code** (requires a [Claude Pro subscription](https://claude.ai/pro))

```bash
npm install -g @anthropic-ai/claude-code
```

**2. Clone and install**

```bash
git clone <your-fork-url>
cd ai-analyst
pip install -e .
```

**3. Configure Mixpanel MCP**

Add the Mixpanel MCP server to your Claude Code settings so Claude can make MCP tool calls to Mixpanel. Once configured, the `mixpanel_pep` dataset activates automatically.

**4. Start Claude Code and go**

```bash
claude
```

The knowledge system auto-loads at session start: Pearson ELL org context, your user profile, and the Mixpanel dataset. No `/setup` needed.

---

## Six Things You Can Do

### 1. Ask a quick question

```
How many teachers used SLG last week?
```

Claude queries Mixpanel via MCP and returns the answer with a chart. Simple questions get answered in under 2 minutes without running the full pipeline.

### 2. Run a full analysis

```
/run-pipeline question="Why did PEP activation drop in March?"
```

The pipeline runs agents across 4 phases: Frame the question, Analyze the data, Build the story, Create the deck. You get a validated analysis, branded charts, a narrative, and a slide deck with speaker notes.

### 3. Explore Mixpanel data

```
/explore
```

Interactive data browsing without committing to a full analysis. Discover available events, check property distributions, spot patterns, form hypotheses.

### 4. Build or update a Mixpanel dashboard

```
Build a retention dashboard in Mixpanel for PEP teachers — show SLG sessions per week and DAU/MAU.
```

Claude queries the data via MCP, designs the metric logic, and creates or updates the dashboard directly in Mixpanel.

### 5. Make a single chart

```
Make a funnel chart of the PEP activation flow, highlighting the biggest drop-off step.
```

Claude generates a chart following Storytelling with Data methodology: warm off-white background, decluttered axes, action title, direct labels.

### 6. Define and document a metric

```
/metrics activation_rate
```

Browse or define metrics. Claude frames the definition, flags guardrail metrics, and documents caveats (e.g. "entitlement ≠ usage; exclude TestHub").

---

## How It Works: The Pipeline

When you run `/run-pipeline`, Claude orchestrates agents across 4 phases:

```
1. FRAME              2. ANALYZE                          3. STORY                 4. DECK
+-----------------+   +-----------------------------+   +--------------------+   +------------------+
| Question        |   | Data Explorer               |   | Story Architect    |   | Storytelling     |
|   Framing       |   |   > Descriptive Analytics   |   |   > Coherence      |   |   > Deck Creator |
|   > Hypothesis  |   |   > Root Cause Investigator |   |     Reviewer       |   |   > Slide Review |
|     Generation  |-->|   > Validation              |-->|   > Chart Maker    |-->|   > Close the    |
|                 |   |   > Opportunity Sizer       |   |   > Design Critic  |   |     Loop         |
+-----------------+   +-----------------------------+   +--------------------+   +------------------+
```

Note: Source Tie-Out (the pandas vs DuckDB cross-validation step from the generic framework) is skipped — it does not apply to Mixpanel MCP data.

**Phase 1 — Frame:** Structures your business question into analytical questions with testable hypotheses.

**Phase 2 — Analyze:** Explores Mixpanel data via MCP, runs segmentation/funnel/drivers analysis, drills down to root cause, validates findings, and sizes the opportunity.

**Phase 3 — Story:** Designs a storyboard (Context-Tension-Resolution arc), generates charts, and reviews visual quality against a 16-point checklist.

**Phase 4 — Deck:** Writes a stakeholder narrative, builds a branded Marp slide deck, reviews slide design, and ensures every recommendation has a follow-up plan.

Five execution plans let you run just the part you need:

| Plan | Use When | What Runs |
|------|----------|-----------|
| `full_presentation` | Complete analysis to slide deck | All agents |
| `deep_dive` | Analysis without presentation | Phases 1-2 only |
| `quick_chart` | Just need one chart | Chart Maker + Design Critic |
| `refresh_deck` | Re-do the presentation layer | Phases 3-4 (reuses analysis) |
| `validate_only` | Check existing work | Validation agent |

```
/run-pipeline question="What's driving SLG adoption?" plan=deep_dive
```

Resume an interrupted pipeline:

```
/resume-pipeline
```

---

## How It Works: The DAG Engine

The pipeline resolves agent dependencies automatically and runs independent agents in parallel:

```
Tier 0 (parallel)    Question Framing --------> Hypothesis
                     Data Explorer (via MCP)
                           |
Tier 2 (parallel)    Descriptive Analytics  /  Overtime Trend  /  Cohort Analysis
                                |
Tier 3 (sequential)  Root Cause --> Validation --> Opportunity Sizer
                                                         |
Tier 4 (sequential)  Story Architect --> Coherence Review
                                               |
Tier 5 (parallel)    Chart Maker (per beat) --> Design Critic
                                                      |
Tier 6 (sequential)  Storytelling --> Deck Creator --> Slide Review --> Close the Loop
```

- **Parallel execution:** Agents in the same tier run concurrently (up to 3 at once).
- **Automatic dependency resolution:** The engine reads `agents/registry.yaml` and computes execution tiers via topological sort.
- **Circuit breaker:** If 3 agents fail in the same tier, the pipeline halts with a diagnostic report.
- **Checkpoints:** Quality gates between phases. Two automated (analysis verification, deck lint). Two user-facing (frame review, storyboard review). Say "just do it" to skip user-facing gates.

---

## All Commands

| Command | What It Does | Example |
|---------|-------------|---------|
| `/run-pipeline` | Full analysis to slide deck | `/run-pipeline question="Why is SLG adoption low?"` |
| `/resume-pipeline` | Resume interrupted pipeline | `/resume-pipeline` |
| `/explore` | Interactive data exploration | `/explore` |
| `/data` | Show active dataset schema | `/data` |
| `/datasets` | List all connected datasets | `/datasets` |
| `/switch-dataset` | Change the active dataset | `/switch-dataset bigquery_pep` |
| `/connect-data` | Add a new data source | `/connect-data` |
| `/setup` | Interactive onboarding interview | `/setup` |
| `/metrics` | Browse the metric dictionary | `/metrics activation_rate` |
| `/history` | View past analyses | `/history` |
| `/patterns` | View recurring patterns | `/patterns` |
| `/export` | Export results in various formats | `/export slides` or `/export email` |
| `/forecast` | Generate a time-series forecast | `/forecast` |
| `/runs` | List, inspect, compare pipeline runs | `/runs` |
| `/business` | Browse Pearson ELL organization knowledge | `/business glossary` |
| `/log-correction` | Log a data or methodology correction | `/log-correction` |
| `/architect` | Multi-persona planning methodology | `/architect` |
| `/notion-ingest` | Import business context from Notion | `/notion-ingest` |
| `/compare-datasets` | Compare metrics across datasets | `/compare-datasets` |

Or just ask in plain English. "Show me SLG sessions by institution" works as well as any command.

---

## Charts and Visualization

Every chart follows the Storytelling with Data methodology:

```
Mixpanel MCP data --> chart_helpers.py --> Base Chart (150 DPI)
                                               |
                                       Collision Check
                                       (3 fix strategies)
                                               |
                                       Marp Deck (HTML components)
                                               |
                                       marp_linter.py (8 check categories)
                                               |
                                       marp_export.py --> PDF + HTML
```

**What happens automatically:**

- `swd_style()` applies warm off-white background (#F7F6F2), removes clutter, sets consistent typography
- Every chart gets an action title (takeaway statement) and a subtitle (data source, time range)
- Direct labels replace legends wherever possible
- Collision detection with 3 auto-fix strategies
- Branded HTML components: KPI cards, finding cards, recommendation rows, so-what callouts
- YAML-based theming with brand color overrides and WCAG-compliant palettes

---

## Your Data

### Current: Mixpanel via MCP

The active dataset is `mixpanel_pep` — Mixpanel event data for PEP and all connected ELL products (MEL, PEC, SLG, Speaking Tutor, TestHub).

**How it works:** Claude calls Mixpanel MCP tools directly to query events, properties, and metrics. No local files, no SQL. Mixpanel is the source of truth — schema, event names, and metric definitions are always queried live.

**Connectivity:** Before any analysis, Claude runs a lightweight MCP probe query to confirm the server is available. If MCP is unavailable, the analysis stops — there is no fallback.

**Business context:** Pre-loaded in `.knowledge/`. Interpretation rules (entitlement ≠ engagement, TestHub provisioning, role segmentation, Speaking Tutor event volume) are documented in `.knowledge/datasets/mixpanel_pep/quirks.md`.

### Future: BigQuery

BigQuery support is already scaffolded:
- `connection_templates/bigquery.yaml.example` — connection config template
- `helpers/dialects/bigquery.py` — BigQuery SQL dialect adapter
- `helpers/connection_manager.py` — warehouse connection management
- `helpers/schema_profiler.py` — schema discovery

When ready, run `/connect-data` and select BigQuery.

---

## What Just Happened? (Output Guide)

After running a pipeline, here's what you'll find:

```
outputs/
  question_brief_YYYY-MM-DD.md          # Your question, structured
  hypothesis_doc_YYYY-MM-DD.md          # Testable hypotheses
  data_inventory_YYYY-MM-DD.md          # What data exists
  analysis_report_YYYY-MM-DD.md         # Full analysis with findings
  validation_<dataset>_YYYY-MM-DD.md    # Independent validation
  narrative_<dataset>_YYYY-MM-DD.md     # Stakeholder-ready story
  deck_<dataset>_YYYY-MM-DD.marp.md    # Slide deck (Marp source)
  deck_<dataset>_YYYY-MM-DD.pdf        # PDF export
  deck_<dataset>_YYYY-MM-DD.html       # HTML export (self-contained)
  close_the_loop_YYYY-MM-DD.md         # Follow-up plan for recommendations
  charts/                               # All generated charts

working/                                # Intermediate files (safe to delete)
  storyboard_<dataset>.md              # Story beats + visual mapping
  design_review_<dataset>.md           # Chart quality review (16-point checklist)
  investigation_<dataset>.md           # Root cause drill-down log
  sizing_*.md                           # Opportunity sizing with sensitivity analysis
```

`outputs/` contains your deliverables. `working/` contains intermediate artifacts that support resumability and debugging.

---

## Customization

| Want to... | Do this |
|-----------|---------|
| Change how Claude thinks | Edit `CLAUDE.md` (persona, rules, workflow) |
| Update Pearson ELL business context | Edit `.knowledge/organizations/pearson/business/glossary/terms.yaml` |
| Update data interpretation rules | Edit `.knowledge/datasets/mixpanel_pep/quirks.md` |
| Add a new skill | Create `.claude/skills/my-skill/skill.md`, reference it in `CLAUDE.md` |
| Add a new agent | Create `agents/my-agent.md` using `agents/CONTRACT_TEMPLATE.md` |
| Change the slide theme | Create a YAML theme in `themes/brands/` |
| Add deck components | Edit `templates/marp_components.md` |
| Modify the pipeline | Edit `.claude/skills/run-pipeline/skill.md` |
| Add OKRs / team context | Edit `.knowledge/organizations/pearson/business/objectives/index.yaml` and `teams/index.yaml` |

---

<details>
<summary><strong>All Agents</strong> (click to expand)</summary>

Agents are markdown prompt templates in `agents/`. Each defines a multi-step workflow with `{{VARIABLES}}` filled in at runtime. Invoke via `/run-pipeline` or ask Claude to run a specific one.

### Framing

| Agent | What It Does | Pipeline Step |
|-------|-------------|---------------|
| question-framing | Turns a business problem into structured analytical questions with hypotheses and data requirements | 1 |
| hypothesis | Generates testable hypotheses across cause categories: product changes, technical issues, external factors, mix shift | 3 |

### Data Discovery

| Agent | What It Does | Pipeline Step |
|-------|-------------|---------------|
| data-explorer | Profiles the active dataset: schema, distributions, quality, gaps, supported analyses. For Mixpanel MCP, queries Mixpanel directly for event and property discovery. | 4 |

### Analysis

| Agent | What It Does | Pipeline Step |
|-------|-------------|---------------|
| descriptive-analytics | Segmentation, funnel analysis, and drivers analysis | 5 |
| overtime-trend | Time-series analysis: trends, anomalies, seasonality | 5 |
| cohort-analysis | Retention curves, cohort comparison, vintage analysis | 5 |
| root-cause-investigator | Iteratively drills down through dimensions to find the specific, actionable root cause | 6 |
| validation | 4-layer verification: structural, logical, business rules, and Simpson's Paradox checks | 7 |
| opportunity-sizer | Quantifies business impact with sensitivity analysis | 8 |

### Storytelling

| Agent | What It Does | Pipeline Step |
|-------|-------------|---------------|
| story-architect | Designs a storyboard with Context-Tension-Resolution arc | 9 |
| narrative-coherence-reviewer | Reviews the storyboard for story gaps before any charting | 10 |
| chart-maker | Generates SWD-styled charts with collision detection and action titles | 12 |
| visual-design-critic | Reviews charts against a 16-point SWD checklist; also reviews slide-level deck design | 13/17 |

### Presentation

| Agent | What It Does | Pipeline Step |
|-------|-------------|---------------|
| storytelling | Converts findings into a stakeholder-ready narrative | 15 |
| deck-creator | Builds a branded Marp slide deck with HTML components and speaker notes | 16 |
| comms-drafter | Generates stakeholder communications: Slack summary, email brief, exec summary | 19 |

### Standalone

| Agent | What It Does |
|-------|-------------|
| experiment-designer | Designs A/B tests with power estimation, guardrail selection, and decision rules |

</details>

---

<details>
<summary><strong>All Skills</strong> (click to expand)</summary>

Skills are instruction files in `.claude/skills/` that Claude follows automatically when a trigger condition matches.

### Always Active

| Skill | What It Does |
|-------|-------------|
| analysis-design-spec | Ensures every analysis starts with a plan: question, decision, data needed, success criteria |
| close-the-loop | Every recommendation gets a decision owner, success metric, follow-up date, and fallback plan |
| data-quality-check | Validates data completeness and consistency before analysis begins |
| feedback-capture | Captures user corrections and methodology guidance to the learnings system |
| guardrails | Pairs every success metric with a guardrail metric; checks positive findings for trade-offs |
| knowledge-bootstrap | Loads Pearson ELL org context, user profile, and Mixpanel dataset at session start |
| metric-spec | Standardized template for defining metrics with no ambiguity |
| question-framing | Structures vague business questions into analytical specs |
| question-router | Classifies questions L1-L5 and routes to the right response path |
| stakeholder-communication | Adapts findings to the audience: same insight, different framing |
| tracking-gaps | Identifies when required data doesn't exist and produces instrumentation requests |
| triangulation | Cross-references findings against multiple sources before presenting |
| visualization-patterns | Ensures every chart follows SWD design standards |
| archaeology | Retrieves proven query patterns before writing new ones |

### On-Demand (Slash Commands)

| Skill | Command | What It Does |
|-------|---------|-------------|
| run-pipeline | `/run-pipeline` | End-to-end analysis with DAG execution, checkpoints, and export |
| resume-pipeline | `/resume-pipeline` | Resume interrupted work from last completed agent |
| explore | `/explore` | Quick interactive data exploration |
| export | `/export` | Export as slides, email, Slack message, or data |
| connect-data | `/connect-data` | Guided wizard to add a new dataset (e.g. BigQuery) |
| switch-dataset | `/switch-dataset` | Change the active dataset |
| datasets | `/datasets` | List all connected datasets with status |
| data-inspect | `/data` | Show active schema, optionally drill into an event/table |
| metrics | `/metrics` | Browse and manage metric dictionary entries |
| history | `/history` | View past analyses from the archive |
| forecast | `/forecast` | Generate time-series forecasts |
| business | `/business` | Browse Pearson ELL organization knowledge (glossary, products) |
| log-correction | `/log-correction` | Deliberate correction logging for event names or methodology |
| architect | `/architect` | Multi-persona planning methodology for new projects |
| runs | `/runs` | List, inspect, compare, and clean up pipeline runs |

</details>

---

<details>
<summary><strong>Helper Modules</strong> (click to expand)</summary>

Python modules in `helpers/` called by agents during execution.

### Charts and Visualization

| Module | What It Does |
|--------|-------------|
| `chart_helpers.py` | Core SWD charting: `swd_style()`, `highlight_bar()`, `highlight_line()`, `action_title()`, `annotate_point()`, `save_chart()`, `retention_heatmap()`, `funnel_waterfall()` |
| `chart_palette.py` | WCAG-compliant color palettes with brand override support |
| `chart_style_guide.md` | Full SWD reference: color palette, declutter checklist, chart decision tree, anti-patterns |
| `analytics_chart_style.mplstyle` | Matplotlib style: off-white background, no top/right spines, 150 DPI |
| `marp_linter.py` | Validates Marp decks: frontmatter, HTML components, slide classes, pacing |
| `marp_export.py` | Exports Marp decks to PDF and HTML via Marp CLI |
| `theme_loader.py` | YAML-based theme system with brand color loading and inheritance |

### Data and SQL (BigQuery-ready)

| Module | What It Does |
|--------|-------------|
| `data_helpers.py` | Data source abstraction: `detect_active_source()`, `check_connection()`, MCP routing |
| `sql_helpers.py` | SQL sanity checks: join cardinality, percentage sums, date bounds (for BigQuery) |
| `sql_dialect.py` | SQL dialect router — BigQuery dialect active |
| `connection_manager.py` | Unified interface for warehouse connections (BigQuery) |
| `schema_profiler.py` | Automated schema discovery and documentation (for BigQuery) |
| `dialects/bigquery.py` | BigQuery-specific SQL generation |

### Analytics and Statistics

| Module | What It Does |
|--------|-------------|
| `analytics_helpers.py` | Segmentation, decomposition, driver analysis, RFM, concentration, insight synthesis |
| `stats_helpers.py` | Statistical tests: proportion, mean, Mann-Whitney, chi-squared, bootstrap CI, effect size |
| `forecast_helpers.py` | Time-series forecasting with trend and seasonality detection |
| `deep_profiler.py` | Advanced data quality: distributions, correlations, completeness, anomalies |
| `simpsons_paradox.py` | Simpson's Paradox scanner |

### Validation

| Module | What It Does |
|--------|-------------|
| `structural_validator.py` | Layer 1: schema, primary keys, completeness checks |
| `logical_validator.py` | Layer 2: aggregation consistency, trend logic |
| `business_rules.py` | Layer 3: plausibility checks against domain rules |
| `business_validation.py` | Business rule validation against Pearson ELL knowledge |
| `confidence_scoring.py` | Synthesizes all 4 layers into an A-F confidence grade |

### Knowledge & Context

| Module | What It Does |
|--------|-------------|
| `context_loader.py` | Loads active dataset context, schema, quirks at session start |
| `archaeology_helpers.py` | Query archaeology: capture and retrieve proven query patterns |
| `business_context.py` | Pearson ELL organization knowledge: glossary, products |
| `entity_resolver.py` | Disambiguates entity references across datasets |
| `metric_validator.py` | Validates metric definitions against schema |

### System

| Module | What It Does |
|--------|-------------|
| `error_helpers.py` | Friendly error messages with suggestions |
| `file_helpers.py` | Atomic file writes, content hashing, safe YAML I/O |
| `health_check.py` | System health diagnostics for data connectivity and dependencies |
| `lineage_tracker.py` | Tracks data lineage from source through transformations to findings |

</details>

---

## Requirements

- **Python 3.10+**
- **Node.js 18+** (for Claude Code)
- **Claude Code** with a [Claude Pro subscription](https://claude.ai/pro)
- **Mixpanel MCP server** configured in Claude Code settings
- **Internet connection** (for Claude API and Mixpanel MCP)

---

## License

[MIT](LICENSE) — use it however you want.
