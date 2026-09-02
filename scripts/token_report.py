#!/usr/bin/env python3
"""Per-skill and per-session token report from Claude Code session transcripts.

Claude Code writes one JSONL transcript per session under
``~/.claude/projects/<project-dir>/``. Each assistant record carries
``message.usage`` (input, output, cache-read and cache-creation tokens) and
Skill invocations appear as ``tool_use`` blocks named ``Skill`` whose
``input.skill`` names the skill. This script attributes every assistant
message's usage to the most recently invoked skill in that session (or
``(no skill)`` before the first invocation) and prints totals and an
estimated cost.

Only counts are read and printed. No prompt or response text is ever
echoed.

Usage:
    python3 scripts/token_report.py                      # this project, all sessions
    python3 scripts/token_report.py --since 2026-09-01   # sessions on/after a date
    python3 scripts/token_report.py --json               # machine-readable
    python3 scripts/token_report.py --project-dir ~/.claude/projects/-path-to-repo
    python3 scripts/token_report.py --rates 5,25,0.5     # $/M input, output, cache read
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

NO_SKILL = "(no skill)"

# $ per million tokens: input, output, cache read. Claude Fable 5.1 list rates.
DEFAULT_RATES = {"input": 10.0, "output": 50.0, "cache_read": 0.25}


# ---------------------------------------------------------------------------
# Locating transcripts
# ---------------------------------------------------------------------------

def default_project_dir(repo_root: Path | None = None) -> Path:
    """Claude Code's transcript directory for a repo: ~/.claude/projects/<mangled path>."""
    root = (repo_root or Path(__file__).resolve().parent.parent).resolve()
    mangled = str(root).replace("/", "-")
    return Path.home() / ".claude" / "projects" / mangled


def find_transcripts(project_dir: Path) -> list[Path]:
    if not project_dir.is_dir():
        return []
    return sorted(p for p in project_dir.glob("*.jsonl") if p.is_file())


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def _parse_ts(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _usage_counts(usage: dict) -> dict:
    return {
        "input": int(usage.get("input_tokens") or 0),
        "output": int(usage.get("output_tokens") or 0),
        "cache_read": int(usage.get("cache_read_input_tokens") or 0),
        "cache_creation": int(usage.get("cache_creation_input_tokens") or 0),
    }


def parse_transcript(path: Path, since: datetime | None = None) -> dict:
    """Return per-skill usage for one session transcript.

    Result shape::

        {
          "session_id": str, "path": str, "started": iso-or-None,
          "messages": int, "skipped": bool,
          "skills": {name: {"invocations": n, "input": .., "output": ..,
                            "cache_read": .., "cache_creation": .., "messages": n}},
        }

    A streamed assistant message is written as several records that share
    one ``message.id`` and repeat the same usage; each id is counted once.
    """
    per_skill = defaultdict(lambda: {"invocations": 0, "input": 0, "output": 0,
                                     "cache_read": 0, "cache_creation": 0, "messages": 0})
    current = NO_SKILL
    seen_message_ids: set[str] = set()
    session_id = path.stem
    started = None
    n_messages = 0

    with path.open("r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(rec, dict):
                continue

            ts = _parse_ts(rec.get("timestamp"))
            if ts and started is None:
                started = ts
            if rec.get("sessionId"):
                session_id = rec["sessionId"]

            if rec.get("type") != "assistant":
                continue
            message = rec.get("message") or {}
            if not isinstance(message, dict):
                continue

            # Skill invocations switch attribution for subsequent messages.
            for block in message.get("content") or []:
                if (isinstance(block, dict) and block.get("type") == "tool_use"
                        and block.get("name") == "Skill"):
                    skill = (block.get("input") or {}).get("skill")
                    if skill:
                        current = str(skill)
                        per_skill[current]["invocations"] += 1

            usage = message.get("usage")
            if not isinstance(usage, dict):
                continue
            msg_id = message.get("id") or rec.get("uuid")
            if msg_id in seen_message_ids:
                continue
            seen_message_ids.add(msg_id)

            counts = _usage_counts(usage)
            bucket = per_skill[current]
            for k, v in counts.items():
                bucket[k] += v
            bucket["messages"] += 1
            n_messages += 1

    skipped = bool(since and started and started < since)
    return {
        "session_id": session_id,
        "path": str(path),
        "started": started.isoformat() if started else None,
        "messages": n_messages,
        "skipped": skipped,
        "skills": dict(per_skill) if not skipped else {},
    }


# ---------------------------------------------------------------------------
# Aggregation and cost
# ---------------------------------------------------------------------------

def estimate_cost(counts: dict, rates: dict = DEFAULT_RATES) -> float:
    """Dollar estimate. Cache-creation tokens are billed at the input rate."""
    return (
        (counts.get("input", 0) + counts.get("cache_creation", 0)) * rates["input"]
        + counts.get("output", 0) * rates["output"]
        + counts.get("cache_read", 0) * rates["cache_read"]
    ) / 1_000_000


def build_report(sessions: list[dict], rates: dict = DEFAULT_RATES) -> dict:
    by_skill = defaultdict(lambda: {"invocations": 0, "input": 0, "output": 0,
                                    "cache_read": 0, "cache_creation": 0, "messages": 0,
                                    "sessions": 0})
    session_rows = []
    for s in sessions:
        if s["skipped"]:
            continue
        totals = {"input": 0, "output": 0, "cache_read": 0, "cache_creation": 0}
        for name, c in s["skills"].items():
            b = by_skill[name]
            for k in ("invocations", "input", "output", "cache_read", "cache_creation", "messages"):
                b[k] += c[k]
            b["sessions"] += 1
            for k in totals:
                totals[k] += c[k]
        session_rows.append({
            "session_id": s["session_id"],
            "started": s["started"],
            "messages": s["messages"],
            "skills": sorted(n for n in s["skills"] if n != NO_SKILL),
            **totals,
            "cost_usd": round(estimate_cost(totals, rates), 4),
        })

    skill_rows = []
    for name, c in by_skill.items():
        skill_rows.append({"skill": name, **c, "cost_usd": round(estimate_cost(c, rates), 4)})
    skill_rows.sort(key=lambda r: r["cost_usd"], reverse=True)

    grand = {"input": 0, "output": 0, "cache_read": 0, "cache_creation": 0}
    for r in skill_rows:
        for k in grand:
            grand[k] += r[k]
    return {
        "rates_per_million": rates,
        "sessions": session_rows,
        "skills": skill_rows,
        "total": {**grand, "cost_usd": round(estimate_cost(grand, rates), 4),
                  "sessions": len(session_rows)},
    }


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def _fmt(n: int) -> str:
    return f"{n:,}"


def render_text(report: dict) -> str:
    out = []
    r = report["rates_per_million"]
    out.append(f"Token report  (rates $/M: input {r['input']}, output {r['output']}, "
               f"cache read {r['cache_read']}; cache writes billed at the input rate)")
    out.append("")
    out.append("By skill")
    hdr = f"{'skill':<28}{'inv':>5}{'msgs':>6}{'input':>12}{'output':>11}{'cache read':>13}{'cost $':>10}"
    out.append(hdr)
    out.append("-" * len(hdr))
    for s in report["skills"]:
        out.append(f"{s['skill'][:27]:<28}{s['invocations']:>5}{s['messages']:>6}"
                   f"{_fmt(s['input'] + s['cache_creation']):>12}{_fmt(s['output']):>11}"
                   f"{_fmt(s['cache_read']):>13}{s['cost_usd']:>10.2f}")
    t = report["total"]
    out.append("-" * len(hdr))
    out.append(f"{'total':<28}{'':>5}{'':>6}{_fmt(t['input'] + t['cache_creation']):>12}"
               f"{_fmt(t['output']):>11}{_fmt(t['cache_read']):>13}{t['cost_usd']:>10.2f}")
    out.append("")
    out.append(f"By session ({t['sessions']})")
    hdr2 = f"{'started':<20}{'session':<10}{'msgs':>6}{'input':>12}{'output':>11}{'cost $':>10}  skills"
    out.append(hdr2)
    out.append("-" * len(hdr2))
    for s in sorted(report["sessions"], key=lambda x: x["started"] or ""):
        started = (s["started"] or "")[:19].replace("T", " ")
        skills = ", ".join(s["skills"]) if s["skills"] else "-"
        out.append(f"{started:<20}{s['session_id'][:8]:<10}{s['messages']:>6}"
                   f"{_fmt(s['input'] + s['cache_creation']):>12}{_fmt(s['output']):>11}"
                   f"{s['cost_usd']:>10.2f}  {skills}")
    return "\n".join(out)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_rates(text: str) -> dict:
    parts = [float(x) for x in text.split(",")]
    if len(parts) != 3:
        raise argparse.ArgumentTypeError("--rates expects three numbers: input,output,cache_read")
    return {"input": parts[0], "output": parts[1], "cache_read": parts[2]}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--project-dir", type=Path, default=None,
                    help="Claude Code transcript directory (default: this repo's)")
    ap.add_argument("--since", type=str, default=None,
                    help="Only sessions started on or after YYYY-MM-DD (UTC)")
    ap.add_argument("--json", action="store_true", help="Print JSON instead of a table")
    ap.add_argument("--rates", type=_parse_rates, default=DEFAULT_RATES,
                    help="$/M tokens as input,output,cache_read (default 10,50,0.25)")
    args = ap.parse_args(argv)

    project_dir = args.project_dir or default_project_dir()
    since = None
    if args.since:
        since = datetime.strptime(args.since, "%Y-%m-%d").replace(tzinfo=timezone.utc)

    paths = find_transcripts(project_dir)
    if not paths:
        print(f"No transcripts found under {project_dir}", file=sys.stderr)
        return 1

    sessions = [parse_transcript(p, since=since) for p in paths]
    report = build_report(sessions, rates=args.rates)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(render_text(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
