# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in this project, please report it responsibly.

**Do NOT open a public GitHub issue for security vulnerabilities.**

Instead, email: **shane@aianalystlab.ai**

Include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if you have one)

You should receive a response within 48 hours. We will work with you to understand and address the issue before any public disclosure.

## Scope

This policy covers:
- The AI Analyst repository code
- Configuration files and templates
- Setup scripts
- Data handling and connection logic

This policy does NOT cover:
- Claude Code itself (report to [Anthropic](https://www.anthropic.com/security))
- MotherDuck (report to [MotherDuck](https://motherduck.com))
- Third-party dependencies (report to their maintainers)

## Best Practices for Users

- Never commit `.claude/mcp.json` with real tokens (use `.claude/mcp.json.example`)
- Never commit connection templates with credentials (use `.yaml.example` files)
- Never share your MotherDuck token publicly
- Review `.gitignore` before pushing to ensure no sensitive data is tracked

## What runs on your machine, and what leaves it

**Hooks.** `.claude/settings.json` configures two Claude Code `PostToolUse` hooks that run after
tool calls in this project:

- `.claude/hooks/log-action.sh` appends one JSON line per tool action to
  `working/action_log_<date>.jsonl`. This is the provenance trail the `trace` skill reads, so
  "where did this number come from" points at logged actions, not a reconstructed story.
- `.claude/hooks/log-snowflake-query.sh` records queries made through the Snowflake MCP tool
  into the query log (requires `jq`; exits silently without it).

Both write local files only and never block Claude. To turn them off, delete the `hooks` block
in `.claude/settings.json`.

**Data handling.** Your data is read and processed locally (pandas, DuckDB, or your warehouse
connection). What leaves the machine:

- Your prompts and the context Claude reads (which can include query results) go to the Claude
  API as part of using Claude Code.
- Exports you explicitly invoke: Google Docs / Slides / Drive, Notion, Slack, email.

Nothing else. In particular, chart images for Docs and Slides are uploaded to *your own* Google
Drive through the chart-to-drive skill; no public file hosts are used anywhere in this repo, and
`scripts/repo_lint.py` fails CI if one is introduced.

**Credentials.** Warehouse credentials live in `.env` (gitignored) or your OS keychain, never in
tracked files; `connection_templates/*.yaml.example` and `.env.example` show the shape. The
analyst never prints credentials to the terminal, files, or logs.
