# Skills map

57 skills under `.claude/skills/`, each a `SKILL.md` with a `name` and a trigger `description`. The description is what makes a skill fire; open a skill file to see the full method it enforces. Grouped here for people; the loader needs them flat.

## Method (always on)

| Skill | One line |
|---|---|
| `analyst-core` | Operating rules for every data analysis. |
| `always-compare` | Never present a metric or number in isolation; anchor every number to a comparison (prior period, benchmark, or another segment) or state that none is available. |
| `question-framing` | Structure analytical questions with the Question Ladder (Goal, Decision, Metric, Hypothesis), then fill the 7-field Analysis Design Spec, before touching data. |
| `question-router` | Classify incoming analytical questions into complexity levels (L1-L5) and route them to the appropriate response path. |
| `close-the-loop` | Ensure every analysis that includes a recommendation ends with a clear, actionable follow-up plan. |
| `guardrails` | Ensure every success metric is paired with guardrail metrics and check for trade-offs before presenting improvements as wins. |
| `stakeholder-communication` | Adapt analytical findings to the audience — same insight, different framing, detail level, and format depending on who will read it. |

## Data

| Skill | One line |
|---|---|
| `connect-data` | Guided wizard to connect a new dataset to the AI Analyst system. |
| `data-inspect` | Show the active dataset's schema — tables, columns, row counts, and relationships. |
| `data-map` | Produce a comprehensive cross-table data health map for the active dataset — the full payoff answer to open-ended "tell me about this data" questions. |
| `data-profiling` | Deep-profile the active dataset: distributions, temporal patterns, correlations, completeness gaps, anomalies. |
| `data-quality-check` | Validate data completeness, consistency, and coverage before any analysis, flagging issues with severity ratings. |
| `distribution-profiler` | Single-column distribution deep-dive. |
| `datasets` | List all connected datasets with their status, table counts, and last analysis date. |
| `compare-datasets` | Compare metrics, findings, and patterns across two or more connected datasets. |
| `connect-snowflake` | Query the live/remote Snowflake warehouse instead of the local practice copy. |
| `setup-snowflake` | First-time Snowflake setup wizard: install the Snowflake MCP tooling, write connection config from the template, and verify a live query round-trip. |
| `explore` | Quick, interactive data exploration without the full pipeline. |

## Analysis

| Skill | One line |
|---|---|
| `analysis-design` | Takes a vague analytical hunch, stakeholder request, or business question and produces a rigorous, stakeholder-ready analysis plan through a multi-stage pipeline. |
| `stress-test` | Pressure-test any analysis plan, investigation design, or analytical approach for hidden methodological flaws before execution. |
| `forecast` | Generate time-series forecasts and projections for metrics over future time periods. |
| `run-pipeline` | Execute the complete end-to-end analysis pipeline — from raw data and business question to validated slide deck with charts. |
| `resume-pipeline` | Resume an interrupted or paused analysis pipeline and pick up where you left off. |
| `runs` | Browse, inspect, compare, and clean up past pipeline runs. |
| `history` | Browse and search past analyses from the knowledge system's analysis archive. |
| `archive-analysis` | Save completed analyses to the knowledge system's analysis archive for future reference. |

## Experiments and causal

| Skill | One line |
|---|---|
| `experiment` | The analysis and lifecycle owner for experiments. |
| `experiment-brief` | Auto-generate a structured experiment brief when a user expresses intent to test something. |
| `srm-check` | Automatically detect Sample Ratio Mismatch (SRM) in experiment or A/B test data before any analysis proceeds. |
| `causal` | Causal inference toolkit for when experiments are not possible: estimate treatment effects from observational data with assumption checks and mandatory caveats. |

## Trust

| Skill | One line |
|---|---|
| `triangulation` | Cross-reference and validate findings before presenting them: mandatory segment-first Simpson's Paradox check, denominator changes, survivorship bias, plausibility vs benchmarks. |
| `trace` | Show the provenance trace — every reported number linked to the SQL that produced it, with a confidence badge. |
| `reliability` | Check whether an AI analysis answer is STABLE by running the same question several independent times and measuring what holds versus what drifts. |
| `eval` | Run the held-out gold suite live against the analyst and score it. |
| `context-compare` | Advanced: runs the same question under two configurations and diffs the results. |
| `codex-review` | Independently validate the current analysis with a second model (OpenAI Codex). |
| `tracking-gaps` | Assess whether the data needed for an analysis actually exists, identify what's missing, and produce prioritized instrumentation requests for engineering when gaps are found. |

## Visuals and deliverables

| Skill | One line |
|---|---|
| `visualization-patterns` | Apply this skill whenever you generate ANY chart, graph, or data visualization in this AI Product Analyst tool. |
| `export` | Export analysis results in different formats for different audiences — email summaries, Slack updates, decision briefs, Google Docs with embedded charts, Word documents, slide decks, or raw data CSVs. |
| `google-doc-export` | Create properly formatted Google Docs via the MCP API. |
| `google-slides-export` | Create properly formatted Google Slides presentations via the MCP API. |
| `notion-export` | Export analysis results to a Notion page with proper structure, embedded charts, data stamps, and provenance toggle blocks. |
| `chart-to-drive` | Upload chart PNGs to the user's own Google Drive for Docs and Slides insertion; no public file hosts. |
| `setup-notion` | Guided Notion connection setup wizard. |

## Knowledge and memory

| Skill | One line |
|---|---|
| `knowledge-bootstrap` | Initialize all knowledge subsystems at session start to load active dataset context, user profile, corrections, learnings, query archaeology, and analysis history into working memory. |
| `log-correction` | Record analyst mistakes, fixes, and reusable learnings so future analyses never repeat an error. |
| `archaeology` | Retrieve proven SQL patterns, table cheatsheets, and join patterns from .knowledge/query-archaeology/ so past work gets reused. |
| `business` | Browse, search, and explore your organization's business context system — glossary terms, product catalog, metric definitions, OKRs/objectives, and team structure. |
| `metrics` | Browse, search, and display metric definitions from the active dataset's metric dictionary. |
| `metric-spec` | Define any metric completely with a standardized template: calculation, denominator, time window, filters, interpretation. |
| `patterns` | Browse, search, and leverage recurring analytical patterns discovered across past analyses. |

## Session machinery

| Skill | One line |
|---|---|
| `setup` | Run a 4-phase conversational interview that populates the knowledge system from the user's real context. |
| `setup-dev-context` | Configure AI Analyst to understand your development environment and codebase structure. |
| `auth-preflight` | Verify Google Workspace MCP authentication at the start of any session that needs Google APIs (Docs, Slides, Drive). |
| `pace` | Change how visibly Claude surfaces analytical work during L3+ analyses. |
| `session-handoff` | Preserve critical state when a session approaches context limits so the next session can pick up seamlessly. |
| `switch-dataset` | Change the active dataset to switch between different data sources for analysis. |

