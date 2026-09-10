<div align="center"><pre>
 █████╗ ██╗     █████╗ ███╗   ██╗ █████╗ ██╗  ██╗   ██╗███████╗████████╗
██╔══██╗██║    ██╔══██╗████╗  ██║██╔══██╗██║  ╚██╗ ██╔╝██╔════╝╚══██╔══╝
███████║██║    ███████║██╔██╗ ██║███████║██║   ╚████╔╝ ███████╗   ██║   
██╔══██║██║    ██╔══██║██║╚██╗██║██╔══██║██║    ╚██╔╝  ╚════██║   ██║   
██║  ██║██║    ██║  ██║██║ ╚████║██║  ██║███████╗██║   ███████║   ██║   
╚═╝  ╚═╝╚═╝    ╚═╝  ╚═╝╚═╝  ╚═══╝╚═╝  ╚═╝╚══════╝╚═╝   ╚══════╝   ╚═╝   
</pre>

<strong>An open-source AI data analyst that runs inside Claude Code.</strong>

<img src="https://img.shields.io/badge/skills-63-D97706"> <img src="https://img.shields.io/badge/agents-40-D97706"> <img src="https://img.shields.io/badge/helpers-147%20modules-D97706"> <img src="https://img.shields.io/badge/python-3.10%2B-3776AB"> <img src="https://img.shields.io/badge/license-MIT-3da639"> <a href="https://github.com/ai-analyst-lab/ai-analyst/actions/workflows/ci.yml"><img src="https://github.com/ai-analyst-lab/ai-analyst/actions/workflows/ci.yml/badge.svg"></a>

frames the decision · profiles before trusting · every number gets a comparison · traces findings to rows · validates before presenting · remembers your corrections

<a href="#what-it-does">What it does</a> ·
<a href="#ten-minute-start">Ten-minute start</a> ·
<a href="#how-it-works">How it works</a> ·
<a href="#commands">Commands</a> ·
<a href="#test-your-analyst">Test your analyst</a> ·
<a href="#coming-from-v2">Coming from v2</a> ·
<a href="https://github.com/ai-analyst-lab/ai-analyst-plugin">Cowork plugin</a> ·
<a href="https://join.slack.com/t/aianalystlab/shared_invite/zt-3yhcg5cit-WnENO3sWfnvro6kvDqQNgA">Slack</a>
</div>

---

## What it does

You talk to it the way you would talk to an analyst on your team. Connect your data, ask what you want to know, and it does the work like a careful analyst would: it asks what decision the answer serves, profiles the data before trusting it, pairs every number with a comparison, traces each finding back to the rows behind it, validates before presenting, and saves real deliverables (briefs, charts, decks) into your project. A `.knowledge/` folder is its memory: schema notes, data quirks, your metric definitions, and a log of every correction you make, so a mistake corrected once is never repeated.

Under the hood: reusable skills for the standards it follows, 40 registered pipeline agents for the multi-step workflows behind the big jobs, deterministic Python helpers for experiments, causal inference, forecasting, profiling, and validation, an analysis pipeline you can run, resume, and inspect, and an eval harness so you can measure the analyst instead of trusting it.

Works on CSV files, DuckDB, Postgres, BigQuery, Snowflake, Databricks, Redshift, SQL Server, and MySQL.

## Ten-minute start

The repository ships with small public examples, synthetic NovaMart context, and public evaluation tasks. It does not contain the NovaMart database, private held-out answers, company data, or credentials. The checked-in active context is NovaMart so course exercises work after the student adds the database. Everyone else should run `/setup` before analysis to connect a source and replace that active context.

```bash
git clone https://github.com/ai-analyst-lab/ai-analyst.git
cd ai-analyst
pip install -e ".[dev]"
claude
```

Then, inside Claude Code, get set up:

```
/setup
```

`/setup` runs a short conversational interview (who you are, what you work on, what data to connect) and wires up your source, CSV folder, DuckDB, MotherDuck, Postgres, BigQuery, or Snowflake, building the `.knowledge/` context for it automatically. Then ask a real question:

```
/analyst Using the orders table, how did revenue trend last quarter versus the one before, and where did we lose the most? Save me a one-page brief with one chart.
```

It frames the decision, profiles the data, runs the comparison, flags anything odd, and writes the brief and chart into `outputs/`. Course students place `novamart_practice.duckdb` at `data/practice/novamart_practice.duckdb`. Other public practice datasets and synthetic evaluation examples are included in `data/`.

**Explicit beats implicit.** Starting a request with `/analyst` runs the full method by name every time. Plain questions work too, and the analyst-core skill steers them, but the command is the reliable path when you want the whole method.

## What you can do

Each line is something you would actually type.

**Get a quick answer.** A number with context and a chart.
> Which channel has the best 30-day retention?

**Run a full analysis.** An end-to-end investigation that hands back a validated analysis and a deck.
> Why is checkout conversion dropping on mobile?

**Design and read experiments.** Plan an A/B test, size it, check sample ratios, interpret the result. Or handle the cases where you cannot randomize.
> Help me design a test for the new onboarding flow.
> Is this experiment a clear win, or should we keep it running?

**Check whether an answer is trustworthy.** Run the same question several times and see if it holds.
> Run that retention number again a few times and tell me if it's stable.

**Make a single chart.** Storytelling-with-data styling, gray-first color, an action title.
> Make a funnel chart of the checkout flow and highlight the biggest drop-off.

**Share it anywhere.** Google Docs, Google Slides, Notion, PDF, Word, Slack, or email.
> Export this as a Google Doc for the leadership review.

## How it works

Three layers, and Claude handles the routing.

**Skills** are standards it follows automatically. When it makes a chart, it styles it properly. When it starts an analysis, it checks data quality first. When it reports a number, it gives you a comparison so the number means something. You rarely call these by name; they apply whenever they are relevant, and several apply at once. Every skill is a `SKILL.md` under `.claude/skills/` with a trigger description, so you can read what it enforces.

**Pipeline agents** are the multi-step workflow definitions behind the bigger jobs. They live in top-level `agents/` because `/run-pipeline`, not Claude Code's native project-agent loader, reads their contracts and registry. The controller validates explicit input bindings and launches each worker through a configured engine adapter, sequentially. Claude Code remains the default engine; the OpenAI-compatible adapter is disabled until it is configured and approved. The controller records outputs directly inside the selected run and does not silently fall back to the main conversation. The controller has deterministic and subprocess integration coverage. Live-provider behavior and native Windows remain separate verification boundaries documented in [verification status](docs/PIPELINE-VERIFICATION.md). See [Agent architecture](docs/AGENT_ARCHITECTURE.md) for the distinction from native subagents.

**Helpers** are the deterministic Python underneath: `experiment_stats` (power, SRM, sequential tests, variance reduction), `causal` (difference-in-differences, propensity matching, Rosenbaum bounds), forecasting with seasonality detection, structural validation, provenance logging. The model reasons; the arithmetic runs in code.

The result is an analyst that tells you what it found and why it matters, not a query that returns rows.

## Commands

You can always just ask in plain English. Slash commands are shortcuts.

**Analysis**
`/analyst` start any analysis the full-method way · `/run-pipeline` full analysis to slide deck · `/resume-pipeline` pick up an interrupted run · `/explore` browse a dataset · `/analysis-design` turn a hunch into a plan · `/stress-test` review a plan for flaws · `/forecast` time-series projection

**Experiments and causal**
`/experiment` A/B design, power, analysis, decision · `/experiment-brief` structured test brief · `/srm-check` sample-ratio gate · `/causal` diff-in-diff, matching, before/after

**Trust**
`/reliability` does behavior repeat · `/trace-analysis` inspect the evidence behind a claim · `/triangulation` compare independent analytical paths · `/score-analysis` decide whether to use one analysis · `/eval` run a frozen system suite · `/evaluate-grader` compare a model grader with human labels · `/monitor-evals` inspect regressions and drift · `/context-compare` test one context change · `/codex-review` ask a second model to re-derive an analysis

**Decks and sharing**
`/export` to Docs, Slides, Notion, PDF, Word, Slack, or email. Fixing an existing deck lives in [deck-doctor](https://github.com/ai-analyst-lab/deck-doctor)

**Your data**
`/connect-data` add a source · `/data` show the schema · `/datasets` list and switch datasets · `/compare-datasets` compare across two · `/connect-snowflake` and `/setup-snowflake` for a live warehouse

**Knowledge and setup**
`/setup` guided onboarding · `/business` browse org knowledge · `/metrics` the metric dictionary · `/metric-spec` define a metric properly · `/log-correction` teach it something · `/history` past analyses

The full list with triggers is in `CLAUDE.md`, and every skill's own `SKILL.md` documents when it fires.

## Your data

The repo includes small public practice datasets, synthetic NovaMart context, and public evaluation fixtures. The larger NovaMart DuckDB file is distributed separately for the course. For your own data, run `/connect-data` or `/setup` for full onboarding. Supported sources:

- **CSV files**, dropped in a directory
- **DuckDB**, local or MotherDuck
- **Postgres**, any Postgres-compatible database
- **BigQuery**, with a Google service account
- **Snowflake**, with user/password or key pair (see `docs/SETUP_SNOWFLAKE.md`)
- **Databricks**, through a configured SQL warehouse
- **Redshift**, through its PostgreSQL-compatible interface
- **SQL Server or Azure SQL**, through ODBC
- **MySQL or MariaDB**, through a configured connection

It profiles the data, writes schema documentation, and remembers context across sessions in `.knowledge/`: corrections, proven query patterns, metric definitions, your business glossary. Nothing in `.knowledge/`, `data/`, or `outputs/` that you generate is committed unless you choose to.

## Test your analyst

Most AI analysis tools ask you to trust a polished result. This repository includes an evaluation control plane so you can inspect one analysis and measure the system across frozen tasks.

Public task manifests live under `data/evals/public/`. The controller records the complete system and data configuration, creates a fresh trial, locks its output, and only then permits grading. Local working cases support iteration. Course heldout references remain outside the student clone and are graded through a separate course boundary. A visible answer file on the same machine is useful development material, but it is not described as a secret heldout test.

The checks answer different questions. `/reliability` measures repeated behavior without claiming correctness. `/trace-analysis` follows a claim to its source and query. `/triangulation` compares methodologically distinct paths. `/eval` measures a named system configuration across working, heldout, capability, or regression cases. `/evaluate-grader` tests the evaluator against frozen human labels. None of these signals is allowed to cancel a blocking failure in another dimension. `data/evals/public/week5-engine.yaml` is the compact controlled suite for comparing two configured engines while the surrounding system remains fixed.

## Engines and operating handoff

Engine adapters live under `helpers/engines/`. Secret-free definitions live in `config/engines.yaml`; credentials are referenced by environment-variable name and never belong in that file. Capability preflight distinguishes unavailable credentials or unsupported behavior from analytical failure. Evaluation receipts record the engine fingerprint, usage where supplied, latency, known cost, and raw-envelope paths. Missing cost remains unknown.

`examples/analyst-v1/` is a bounded operating-handoff example. It includes a system manifest, autonomy policy, one approved workflow, release and recovery records, a value scorecard, and an operator guide. The local operator is inspectable course infrastructure, not a hosted service or an operating-system security boundary.

## What runs on your machine

Two Claude Code hooks are configured in `.claude/settings.json`: one appends a line per tool
action to `working/action_log_<date>.jsonl` (the provenance trail the `trace` skill reads), one
records Snowflake MCP queries into the query log. Both write local files only; delete the `hooks`
block to turn them off. Local tools process your data on your machine, but model prompts and
supplied context travel to the configured model provider unless you selected and verified a
genuinely local endpoint. Exports can also leave the machine when you explicitly invoke them. Details in
[SECURITY.md](.github/SECURITY.md).

## Make it yours

| Want to... | Do this |
|-----------|---------|
| Change how it thinks | Edit `CLAUDE.md` (persona, rules, workflow) |
| Add a skill | Create `.claude/skills/my-skill/SKILL.md` with a `name` and trigger `description` |
| Add an agent | Copy `agents/CONTRACT_TEMPLATE.md` |
| Change the chart or deck theme | Add a YAML theme in `themes/brands/` (FiveThirtyEight and Economist are included as examples) |
| Adjust the pipeline | Review plans, registry and explicit bindings; see `docs/PIPELINE-CONTROLLER.md` |
| Keep it honest | Run `python scripts/repo_lint.py` and `pytest` before you commit; CI runs both |

See [docs/setup-guide.md](docs/setup-guide.md) for setup and [docs/theming.md](docs/theming.md) for branding.

## Coming from v2

v3 replaces the v2 tree. The v2 release is preserved as the `v2` branch and the `v2.0.0` tag, so existing links and clones keep working. What changed:

- **Architecture.** v2 had 23 agents and no skills; v3 is skills-first with 40 registered agents behind the pipeline. Your v2 `CLAUDE.md` customizations need to be re-applied on the v3 file.
- **Knowledge store.** `.knowledge/` layout is the same idea with a richer tree (corrections, archaeology, organizations, reliability). Run `/connect-data` again on your datasets to rebuild the brain.
- **Removed.** The north-star skill (its reference corpus is not ours to redistribute), community skills tied to a course, and duplicate skills merged into their stronger sibling (see CHANGELOG).
- **Data.** v2 bundled a larger demo dataset. v3 includes only small public examples, synthetic NovaMart context, and public evaluation fixtures. The NovaMart database and all private held-out references remain outside the repository.

## Cowork plugin

If you want the analyst without the repo, [ai-analyst-plugin](https://github.com/ai-analyst-lab/ai-analyst-plugin) is the same method packaged as a Claude Cowork and Claude Code plugin: skills only, no pipeline orchestration, no eval harness. This repo is the full system; the plugin is the lightweight distribution of it.

## Requirements

- Python 3.10+
- Claude Code with a Claude subscription
- Node.js 18+ for PDF and HTML slide export
- An internet connection for the Claude API and any cloud data sources

## Help and license

Questions or bugs: open an [issue](https://github.com/ai-analyst-lab/ai-analyst/issues), or ask in [Slack](https://join.slack.com/t/aianalystlab/shared_invite/zt-3yhcg5cit-WnENO3sWfnvro6kvDqQNgA). Licensed under [MIT](LICENSE).

Built by [Shane Butler](https://aianalystlab.ai) at AI Analyst Lab.
