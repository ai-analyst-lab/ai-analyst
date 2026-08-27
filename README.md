<div align="center"><pre>
 █████╗ ██╗     █████╗ ███╗   ██╗ █████╗ ██╗  ██╗   ██╗███████╗████████╗
██╔══██╗██║    ██╔══██╗████╗  ██║██╔══██╗██║  ╚██╗ ██╔╝██╔════╝╚══██╔══╝
███████║██║    ███████║██╔██╗ ██║███████║██║   ╚████╔╝ ███████╗   ██║   
██╔══██║██║    ██╔══██║██║╚██╗██║██╔══██║██║    ╚██╔╝  ╚════██║   ██║   
██║  ██║██║    ██║  ██║██║ ╚████║██║  ██║███████╗██║   ███████║   ██║   
╚═╝  ╚═╝╚═╝    ╚═╝  ╚═╝╚═╝  ╚═══╝╚═╝  ╚═╝╚══════╝╚═╝   ╚══════╝   ╚═╝   
</pre>

<strong>An open-source AI data analyst that runs inside Claude Code.</strong>

<img src="https://img.shields.io/badge/skills-63-D97706"> <img src="https://img.shields.io/badge/agents-39-D97706"> <img src="https://img.shields.io/badge/helpers-70%20modules-D97706"> <img src="https://img.shields.io/badge/python-3.10%2B-3776AB"> <img src="https://img.shields.io/badge/license-MIT-3da639"> <a href="https://github.com/ai-analyst-lab/ai-analyst/actions/workflows/ci.yml"><img src="https://github.com/ai-analyst-lab/ai-analyst/actions/workflows/ci.yml/badge.svg"></a>

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

Under the hood: 63 skills (the standards it follows), 39 agents (the multi-step workflows behind the big jobs), 70 Python helper modules (the deterministic statistics: experiments, causal inference, forecasting, profiling, validation), an 18-step analysis pipeline you can run, resume, and inspect, and an eval harness so you can measure the analyst instead of trusting it.

Works on CSV files, DuckDB, Postgres, BigQuery, and Snowflake.

## Ten-minute start

Nothing to sign up for. The repo includes public practice data (S&P 500 daily prices, sector ETFs, FRED macro series, and synthetic A/B experiments with answer keys).

```bash
git clone https://github.com/ai-analyst-lab/ai-analyst.git
cd ai-analyst
pip install -e ".[dev]"
claude
```

Then, inside Claude Code:

```
/analyst Using data/sp500/sp500_daily.csv, I need to decide whether to keep our equity allocation. How did the S&P 500 do in 2023 versus 2022, and what was the worst drawdown along the way? Save me a one-page brief with one chart.
```

It frames the decision, profiles the file, runs the comparison, flags anything odd, and writes the brief and chart into `outputs/`. When you are ready for your own data, run `/connect-data` (CSV folder, DuckDB, Postgres, BigQuery, or Snowflake) and it builds the `.knowledge/` context for that dataset automatically.

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

**Agents** are the multi-step workflows behind the bigger jobs. A full analysis moves through a pipeline: frame the question, explore and validate the data, investigate the root cause, build the story, design the charts, assemble the deck, checking its own work at each step. `/run-pipeline` runs it; `/resume-pipeline` and `/runs` pick up and inspect runs.

**Helpers** are the deterministic Python underneath: `experiment_stats` (power, SRM, sequential tests, variance reduction), `causal` (difference-in-differences, propensity matching, Rosenbaum bounds), forecasting with seasonality detection, structural validation, provenance logging. The model reasons; the arithmetic runs in code.

The result is an analyst that tells you what it found and why it matters, not a query that returns rows.

## Commands

You can always just ask in plain English. Slash commands are shortcuts.

**Analysis**
`/analyst` start any analysis the full-method way · `/run-pipeline` full analysis to slide deck · `/resume-pipeline` pick up an interrupted run · `/explore` browse a dataset · `/analysis-design` turn a hunch into a plan · `/stress-test` review a plan for flaws · `/forecast` time-series projection

**Experiments and causal**
`/experiment` A/B design, power, analysis, decision · `/experiment-brief` structured test brief · `/srm-check` sample-ratio gate · `/causal` diff-in-diff, matching, before/after

**Trust**
`/reliability` is an answer stable across runs · `/eval` score the analyst against gold cases · `/context-compare` does a piece of context change the answer · `/trace` where a number came from · `/codex-review` a second model re-derives the analysis blind

**Decks and sharing**
`/export` to Docs, Slides, Notion, PDF, Word, Slack, or email. Fixing an existing deck lives in [deck-doctor](https://github.com/ai-analyst-lab/deck-doctor)

**Your data**
`/connect-data` add a source · `/data` show the schema · `/datasets` list and switch datasets · `/compare-datasets` compare across two · `/connect-snowflake` and `/setup-snowflake` for a live warehouse

**Knowledge and setup**
`/setup` guided onboarding · `/business` browse org knowledge · `/metrics` the metric dictionary · `/metric-spec` define a metric properly · `/log-correction` teach it something · `/history` past analyses

The full list with triggers is in `CLAUDE.md`, and every skill's own `SKILL.md` documents when it fires.

## Your data

The repo includes public practice data so it works before you connect anything. For your own data, run `/connect-data` (or `/setup` for full onboarding). Supported sources:

- **CSV files**, dropped in a directory
- **DuckDB**, local or MotherDuck
- **Postgres**, any Postgres-compatible database
- **BigQuery**, with a Google service account
- **Snowflake**, with user/password or key pair (see `SETUP_SNOWFLAKE.md`)

It profiles the data, writes schema documentation, and remembers context across sessions in `.knowledge/`: corrections, proven query patterns, metric definitions, your business glossary. Nothing in `.knowledge/`, `data/`, or `outputs/` that you generate is committed unless you choose to.

## Test your analyst

Most AI-analysis tools ask you to trust them. This one includes an eval harness.

`data/eval/gold.yaml` holds 10 verified questions over the bundled S&P 500 data, each with a computed answer, a tolerance, and the method used to derive it (`data/eval/make_gold.py` regenerates the whole file, so the key is auditable). Run `/eval train` and the analyst is driven on each question blind, then graded; the run record carries the git sha, the model, and which metrics were defined at the time, so you can watch accuracy move as you change skills or add context. Add your own gold cases in the same shape.

Two companion checks: `/reliability` asks the same question N times and reports whether the answer is stable, and `/context-compare` runs a question with and without a piece of context to measure whether that context is worth keeping.

## What runs on your machine

Two Claude Code hooks are configured in `.claude/settings.json`: one appends a line per tool
action to `working/action_log_<date>.jsonl` (the provenance trail the `trace` skill reads), one
records Snowflake MCP queries into the query log. Both write local files only; delete the `hooks`
block to turn them off. Your data is processed locally; what leaves the machine is your prompts
to the Claude API and exports you explicitly invoke. Details in
[SECURITY.md](.github/SECURITY.md).

## Make it yours

| Want to... | Do this |
|-----------|---------|
| Change how it thinks | Edit `CLAUDE.md` (persona, rules, workflow) |
| Add a skill | Create `.claude/skills/my-skill/SKILL.md` with a `name` and trigger `description` |
| Add an agent | Copy `agents/CONTRACT_TEMPLATE.md` |
| Change the chart or deck theme | Add a YAML theme in `themes/brands/` (FiveThirtyEight and Economist are included as examples) |
| Adjust the pipeline | Edit `.claude/skills/run-pipeline/SKILL.md` |
| Keep it honest | Run `python scripts/repo_lint.py` and `pytest` before you commit; CI runs both |

See [docs/setup-guide.md](docs/setup-guide.md) for setup and [docs/theming.md](docs/theming.md) for branding.

## Coming from v2

v3 replaces the v2 tree. The v2 release is preserved as the `v2` branch and the `v2.0.0` tag, so existing links and clones keep working. What changed:

- **Architecture.** v2 had 23 agents and no skills; v3 is skills-first (63) with the agents (39) behind the pipeline. Your v2 `CLAUDE.md` customizations need to be re-applied on the v3 file.
- **Knowledge store.** `.knowledge/` layout is the same idea with a richer tree (corrections, archaeology, organizations, reliability). Run `/connect-data` again on your datasets to rebuild the brain.
- **Removed.** The north-star skill (its reference corpus is not ours to redistribute), community skills tied to a course, and duplicate skills merged into their stronger sibling (see CHANGELOG).
- **Data.** v2 bundled one demo dataset. v3 bundles several public ones plus the eval gold set.

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
