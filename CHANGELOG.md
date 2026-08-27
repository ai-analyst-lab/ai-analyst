# Changelog

All notable changes to this project will be documented in this file.

## [3.0.0] - 2026-08-27

Major release. The internal "AI Analyst Plus" line becomes the public AI Analyst: 63 skills,
39 agents, 70 helper modules, an eval harness, and public practice data, with a hardening pass
across the whole tree. v2 is preserved on the `v2` branch and the `v2.0.0` tag.

### Added
- `/analyst` command and the `analyst-core` skill: the method contract (frame the decision,
  profile before trusting, always compare, trace to source, validate, log corrections) as one
  always-relevant skill plus an explicit entry point
- `always-compare`: every number comes with a comparison
- Experimentation: `/experiment` (design, power, SRM, analysis, decision), `/experiment-brief`,
  `/srm-check`, and `/causal` (diff-in-diff, propensity matching, pre/post, Rosenbaum bounds)
  on the `experiment_stats` and `causal_stats` helper libraries
- Trust tooling: `/reliability` (answer stability), `/eval` (gold-suite scoring), `/context-compare`
  (with-and-without a piece of context), `/trace` (provenance viewer), `/codex-review` (a second
  model re-derives the analysis blind)
- Public eval harness: `data/eval/gold.yaml` (10 verified cases over the bundled S&P 500 data)
  with its generator; `eval_driver` runs locally by default and supports an external harness via
  `AIEVALS_REPO`
- Bundled public practice data: S&P 500 daily, sector ETFs, FRED macro series, synthetic A/B
  experiments with answer keys
- Deck tooling: `/deck-critique`, `/slide-transform`, `/deck-rescue`; WCAG-checked brand themes
- `/analysis-design` and `/stress-test` for plan rigor; `/forecast` with seasonality detection
- Google Slides and Notion export alongside Google Docs, PDF, Word, Slack, email
- Provenance: every query through `ConnectionManager` is auto-logged with its result; schema guard;
  archaeology writer convention (validated SQL is curated back into the store)
- `scripts/repo_lint.py`: public-repo hardening lint (frontmatter, case, secrets, private paths,
  public file hosts, residue); runs in CI with the test suite

### Changed
- Every skill is stored as `SKILL.md` with frontmatter (55 were lowercase `skill.md`, invisible to
  case-sensitive checkouts and the skill loader; 5 had no frontmatter)
- Chart hosting for Docs, Slides, and Notion export is Drive-only, uploading local files directly.
  No public file hosts anywhere in the tree
- Statistical fixes: seasonality detection scans through the last computable lag; `seasonal_naive`
  derives its period; exponential smoothing produces future values; Rosenbaum bounds drop tied
  pairs; propensity matching returns scores for common-support checks; date validation parses
  YYYYMMDD integers and fails loudly on unparseable dtypes; one canonical null-severity table
  (<5% ok, 5-20% warning, 20-50% severe warning, >50% blocker); table listing honors manifests
- Consolidated: `feedback-capture` into `log-correction`, `semantic-validation` into
  `triangulation`, `analysis-design-spec` into `question-framing`, `theme-picker` into
  `visualization-patterns`; `presentation-themes` is now a reference inside `deck-rescue`;
  `compare` renamed `context-compare` so plain "compare X and Y" routes to analysis
- Feasibility vocabulary unified to VIABLE / MARGINAL / NOT_VIABLE (matches the power script)
- Warehouse connection docs and skills generalized to the user's own config

### Removed
- `north-star` skill and its agents, engine, tests, and templates (reference corpus not ours to
  redistribute)
- `show-off`, `teach`, `architect`, and other course- or community-specific scaffolding
- Machine-specific paths, hardcoded account identifiers, and personal contact details

## [2.0.0] - 2026-02-23

### Added
- Interactive onboarding: `/setup` interview learns role, data sources, business context
- Knowledge infrastructure: corrections, learnings, query archaeology, organization knowledge
- Self-learning loop: feedback capture, correction logging, proven SQL pattern retrieval
- YAML-based brand theming with WCAG-compliant palettes (`themes/brands/`)
- Pipeline run tracking: `/runs` to list, inspect, compare, and clean up runs
- Comms drafter agent for Slack/email/exec summary output
- Business context system: glossary, metrics, products, teams per organization
- Notion ingest skill for importing business context from Notion workspaces
- Entity resolver for cross-dataset disambiguation
- 8 new slash commands: `/setup`, `/runs`, `/business`, `/log-correction`, `/architect`, `/notion-ingest`, `/setup-dev-context`, `/compare-datasets`
- 9 new skills: archaeology, feedback-capture, log-correction, setup, setup-dev-context, runs, business, notion-ingest, architect
- 606 tests with synthetic fixtures (no external data dependencies)
- Health check system for data connectivity diagnostics
- Schema migration helpers for knowledge file versioning

### Changed
- Fully dataset-agnostic: agents resolve tables/columns from active manifest, not hardcoded names
- Removed bundled NovaMart dataset; bring your own data with `/connect-data`
- Removed legacy setup scripts (`download-data.sh`, `build-duckdb.sh`) and setup docs
- Updated CLAUDE.md with V2 workflow, agent index, and skill table
- Python requirement bumped to 3.10+

### Fixed
- Pipeline resume reliability improved with persistent state management
- Chart palette now validates WCAG contrast ratios

## [1.0.0] - 2026-02-19

### Added
- Initial public release
- 17 specialized analysis agents with DAG-based parallel execution
- 30 auto-applied skills (question framing, data quality, visualization, validation)
- 14 slash commands for interactive use
- Example e-commerce dataset schema (13 tables)
- Tiered data system: Tier 1 in git, Tier 2 via GitHub Releases
- Setup scripts: `setup.sh`, `download-data.sh`, `build-duckdb.sh`
- Multi-warehouse support: DuckDB, MotherDuck, Postgres, BigQuery, Snowflake
- SWD-styled chart generation with collision detection
- Marp slide deck creation with branded HTML components
- 4-layer validation framework with A-F confidence scoring
- Knowledge system for cross-session memory
- Metric dictionary with standardized definitions
- Analysis archive with pattern extraction
