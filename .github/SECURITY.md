# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in this project, please report it responsibly.

**Do NOT open a public GitHub issue for security vulnerabilities.**

Instead, email the security team at AXS Pte Ltd.

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
- ClickHouse (report to [ClickHouse](https://clickhouse.com))
- Third-party dependencies (report to their maintainers)

## Best Practices for Users

- Never commit `.claude/mcp.json` with real tokens (use `.claude/mcp.json.example`)
- Never commit connection templates with credentials (use `.yaml.example` files)
- Never share your ClickHouse credentials publicly
- Review `.gitignore` before pushing to ensure no sensitive data is tracked
