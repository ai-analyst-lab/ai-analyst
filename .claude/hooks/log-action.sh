#!/bin/bash
# PostToolUse hook: logs EVERY meaningful tool action to a per-day action log.
# Receives tool-call JSON on stdin from Claude Code and forwards it to
# scripts/log_action.py, which appends one JSON line to
#   working/action_log_<date>.jsonl
#
# This is the "what did you do?" log — a concrete record of actions taken,
# so answers point at logged data, not a hallucinated transcript.
#
# Companion to log-snowflake-query.sh (which logs SQL provenance). Both run.
# Never blocks the agent: any failure is swallowed (|| true) and exit is 0.

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"

# Forward the hook payload (stdin) to the Python logger. The logger reads
# stdin itself and never raises, but we guard with || true regardless.
python3 "$PROJECT_DIR/scripts/log_action.py" 2>/dev/null || true

exit 0
