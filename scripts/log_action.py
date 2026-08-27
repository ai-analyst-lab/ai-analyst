#!/usr/bin/env python3
"""Action logger — records every tool action the analyst agent takes.

This is the companion to scripts/log_query.py. Where log_query.py captures
SQL queries for provenance, this captures *every* tool action (Bash, Read,
Edit, Write, MCP calls, ...) so that the question "what did you do?" can be
answered from a concrete log instead of from the chat transcript (which the
agent could hallucinate).

It is driven by Claude Code's PostToolUse hook. The hook feeds the tool-call
JSON on stdin; this script parses it, builds one compact entry, and appends
it as a single line to a per-day JSONL action log:

    working/action_log_<YYYY-MM-DD>.jsonl

Each entry captures:
    timestamp        ISO-8601 time the action was logged
    tool             tool name (Bash, Read, Edit, Write, mcp__snowflake__...)
    method           coarse action kind (shell, read, edit, write, sql, mcp, tool)
    summary          one-line human-readable description of the action
    inputs           the command / file / sql, truncated sensibly
    output_summary   brief summary of the key output, when available
    status           success | error
    session_id       hook session id, when provided

Usage (hook mode — reads hook JSON from stdin):
    cat hook_input.json | python3 scripts/log_action.py

Usage (importable for the renderer and tests):
    from scripts.log_action import build_entry, append_entry, action_log_path

Never raises on bad input by design: the goal is to never block the agent.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

# How much of a command / file path / sql to keep in the log.
_INPUT_TRUNCATE = 600
_OUTPUT_TRUNCATE = 400


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

def project_root() -> Path:
    """Best-effort project root (parent of scripts/)."""
    return Path(__file__).resolve().parent.parent


def action_log_path(date: str, working_dir: str | Path | None = None) -> Path:
    """Return the JSONL action-log path for a given date.

    working_dir defaults to <project_root>/working.
    """
    base = Path(working_dir) if working_dir is not None else project_root() / "working"
    return base / f"action_log_{date}.jsonl"


def _truncate(text: str, limit: int) -> str:
    text = text.replace("\r\n", "\n").strip()
    if len(text) <= limit:
        return text
    return text[:limit] + f"... [+{len(text) - limit} chars]"


# ---------------------------------------------------------------------------
# Output summarisation
# ---------------------------------------------------------------------------

def _summarize_output(tool_response) -> str:
    """Produce a brief, human-readable summary of a tool's output.

    Handles the common shapes a PostToolUse hook delivers: a plain string,
    a dict (Bash: stdout/stderr/interrupted; MCP: structured), or a list
    (MCP query rows). Returns "" when nothing useful is available.
    """
    if tool_response is None:
        return ""

    # Plain string output (e.g. Read content, some MCP tools)
    if isinstance(tool_response, str):
        return _truncate(tool_response, _OUTPUT_TRUNCATE)

    # List output (e.g. Snowflake MCP returns a list of row dicts)
    if isinstance(tool_response, list):
        return f"{len(tool_response)} rows/items returned"

    # Dict output
    if isinstance(tool_response, dict):
        # Bash-style response
        if "stdout" in tool_response or "stderr" in tool_response:
            out = (tool_response.get("stdout") or "").strip()
            err = (tool_response.get("stderr") or "").strip()
            if out:
                return _truncate(out, _OUTPUT_TRUNCATE)
            if err:
                return "stderr: " + _truncate(err, _OUTPUT_TRUNCATE)
            return "(no output)"
        # File-edit style response
        for key in ("filePath", "file_path"):
            if key in tool_response:
                parts = [f"file={tool_response[key]}"]
                if "structuredPatch" in tool_response:
                    patch = tool_response["structuredPatch"]
                    if isinstance(patch, list):
                        parts.append(f"{len(patch)} hunk(s)")
                return ", ".join(parts)
        # Generic dict — show keys
        return _truncate("keys: " + ", ".join(map(str, tool_response.keys())), _OUTPUT_TRUNCATE)

    return _truncate(str(tool_response), _OUTPUT_TRUNCATE)


# ---------------------------------------------------------------------------
# Entry construction
# ---------------------------------------------------------------------------

def _classify(tool: str, tool_input: dict) -> tuple[str, str, str]:
    """Return (method, summary, inputs) for a tool call.

    method  — coarse action kind
    summary — one-line human-readable description
    inputs  — the load-bearing input (command/file/sql), truncated
    """
    ti = tool_input if isinstance(tool_input, dict) else {}

    if tool == "Bash":
        cmd = str(ti.get("command", ""))
        desc = str(ti.get("description", "")).strip()
        first_line = cmd.strip().splitlines()[0] if cmd.strip() else ""
        summary = desc or (f"Ran: {first_line}" if first_line else "Ran a shell command")
        return "shell", summary, _truncate(cmd, _INPUT_TRUNCATE)

    if tool == "Read":
        fp = str(ti.get("file_path", ""))
        return "read", f"Read {Path(fp).name or fp}", _truncate(fp, _INPUT_TRUNCATE)

    if tool == "Edit":
        fp = str(ti.get("file_path", ""))
        return "edit", f"Edited {Path(fp).name or fp}", _truncate(fp, _INPUT_TRUNCATE)

    if tool == "Write":
        fp = str(ti.get("file_path", ""))
        return "write", f"Wrote {Path(fp).name or fp}", _truncate(fp, _INPUT_TRUNCATE)

    if tool == "NotebookEdit":
        fp = str(ti.get("notebook_path", ""))
        return "edit", f"Edited notebook {Path(fp).name or fp}", _truncate(fp, _INPUT_TRUNCATE)

    # Snowflake MCP (and any *run*query* MCP tool) — capture the SQL
    if "snowflake" in tool.lower() or "statement" in ti or "query" in ti:
        sql = str(ti.get("statement") or ti.get("query") or "")
        if sql:
            first = " ".join(sql.split())[:80]
            return "sql", f"SQL: {first}", _truncate(sql, _INPUT_TRUNCATE)

    if tool.startswith("mcp__"):
        # Compact dump of the input args for any other MCP tool.
        try:
            args = _truncate(json.dumps(ti, default=str), _INPUT_TRUNCATE)
        except Exception:
            args = _truncate(str(ti), _INPUT_TRUNCATE)
        return "mcp", f"MCP call: {tool}", args

    # Fallback for any other tool (Glob, Grep, WebFetch, ...)
    try:
        args = _truncate(json.dumps(ti, default=str), _INPUT_TRUNCATE)
    except Exception:
        args = _truncate(str(ti), _INPUT_TRUNCATE)
    return "tool", f"{tool}", args


def build_entry(hook_data: dict) -> dict:
    """Build a single action-log entry dict from PostToolUse hook JSON.

    Accepts the raw hook payload. Tolerant of missing fields.
    """
    hd = hook_data if isinstance(hook_data, dict) else {}
    tool = str(hd.get("tool_name") or hd.get("tool") or "unknown")
    tool_input = hd.get("tool_input") or {}
    tool_response = hd.get("tool_response")

    method, summary, inputs = _classify(tool, tool_input)
    output_summary = _summarize_output(tool_response)

    # Best-effort status detection.
    status = "success"
    if isinstance(tool_response, dict):
        if tool_response.get("interrupted") or tool_response.get("is_error") or tool_response.get("error"):
            status = "error"

    return {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "tool": tool,
        "method": method,
        "summary": summary,
        "inputs": inputs,
        "output_summary": output_summary,
        "status": status,
        "session_id": hd.get("session_id"),
    }


def append_entry(entry: dict, log_path: str | Path) -> dict:
    """Append one entry as a JSON line to log_path (creating parents)."""
    p = Path(log_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a") as f:
        f.write(json.dumps(entry) + "\n")
    return entry


# ---------------------------------------------------------------------------
# Read (used by the renderer and tests)
# ---------------------------------------------------------------------------

def read_log(log_path: str | Path) -> list[dict]:
    """Read all entries from a JSONL action log. Empty list if missing."""
    p = Path(log_path)
    if not p.exists():
        return []
    entries = []
    with p.open() as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return entries


# ---------------------------------------------------------------------------
# CLI / hook entry point
# ---------------------------------------------------------------------------

def main() -> int:
    """Read PostToolUse hook JSON from stdin and append one log entry.

    Always exits 0 — logging must never block the agent.
    """
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            return 0
        hook_data = json.loads(raw)
        entry = build_entry(hook_data)

        date = datetime.now().strftime("%Y-%m-%d")
        # Honour the hook's cwd if provided, else project root.
        cwd = hook_data.get("cwd")
        working_dir = (Path(cwd) / "working") if cwd else None
        path = action_log_path(date, working_dir)
        append_entry(entry, path)
    except Exception:
        # Never block the agent on a log failure.
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
