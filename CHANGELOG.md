# Changelog

All notable changes to this project will be documented in this file.

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
- Removed bundled NovaMart dataset — bring your own data with `/connect-data`
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
- Multi-warehouse support: ClickHouse, Postgres, BigQuery, Snowflake
- SWD-styled chart generation with collision detection
- Marp slide deck creation with branded HTML components
- 4-layer validation framework with A-F confidence scoring
- Knowledge system for cross-session memory
- Metric dictionary with standardized definitions
- Analysis archive with pattern extraction
