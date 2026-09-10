# AI Analyst Setup Guide

## Prerequisites

- **Python 3.10+** with pip
- **Claude Code** CLI installed ([docs](https://docs.anthropic.com/en/docs/claude-code))
- Your data in CSV, DuckDB, or a supported warehouse

## Quick Start

### 1. Clone and install

```bash
git clone <repo-url> ai-analyst
cd ai-analyst
pip install -e ".[dev]"
```

### 2. Launch Claude Code

```bash
claude
```

### 3. Connect your data

On first launch, Claude will detect a fresh install and start the interactive
setup interview. It walks you through:

1. **Your role and team:** so Claude adapts its communication style
2. **Your data source:** CSV directory, DuckDB file, or warehouse connection
3. **Your business context:** what your company does, key metrics, team structure
4. **Your preferences:** output formats, chart style, export channels

You can also run the setup manually at any time:

```
/setup
```

### 4. Start analyzing

Once setup is complete, just ask a question:

```
What's our conversion rate by device type?
```

Or run the full analysis pipeline:

```
/run-pipeline
```

## Connecting Data Sources

### CSV files

Place your CSV files in a directory (e.g., `data/my_dataset/`) and tell Claude
during setup. Each `.csv` file becomes a queryable table.

### Local DuckDB

Point Claude to a `.duckdb` file during setup. DuckDB provides fast SQL
queries over local data.

### External Warehouses

Run `/connect-data` and follow the prompts for Postgres, BigQuery, Snowflake, Databricks,
Redshift, SQL Server, or MySQL. The analyst will select a native Python connector, CLI, API, or
MCP integration based on the source and available authentication. MCP is one interface option,
not a requirement for every warehouse.

## Resetting

To start fresh:

```
/setup reset
```

- **Tier 1 reset:** clears your profile and preferences
- **Tier 2 reset:** clears everything including dataset connections

## Running Tests

```bash
python -m pytest tests/ -v
```

## Project Structure

```
ai-analyst/
  .claude/skills/     # Claude skill definitions and triggers
  .knowledge/         # Context, definitions, corrections, and dataset manifests
  agents/             # Pipeline-agent workflow definitions
  helpers/            # Deterministic Python modules
  tests/              # Pytest test suite
  data/               # Public examples plus your gitignored datasets
  docs/               # Documentation
  outputs/            # Gitignored analysis outputs
  working/            # Gitignored intermediate files and run records
```
