#!/usr/bin/env python3
"""Render the JSONL action log into a human-readable view.

Reads   working/action_log_<date>.jsonl
Writes  working/action_log_<date>.md   (clean chronological list)
        working/action_log_<date>.html (optional, with --html)

So a person can read exactly what the agent did, step by step — and the
answer to "what did you do?" points at this rendered log, not a guess.

Usage:
    python3 scripts/render_action_log.py                 # today, md only
    python3 scripts/render_action_log.py --date 2026-06-26
    python3 scripts/render_action_log.py --date 2026-06-26 --html
    python3 scripts/render_action_log.py --log-path working/action_log_X.jsonl
"""

from __future__ import annotations

import argparse
import html as _html
from datetime import datetime
from pathlib import Path

# Reuse path + read helpers from the logger so both stay in sync.
try:
    from scripts.log_action import action_log_path, read_log
except ImportError:  # when run as a script, scripts/ may not be a package
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from scripts.log_action import action_log_path, read_log


def _time_only(ts: str) -> str:
    """Show just HH:MM:SS from an ISO timestamp; fall back to the raw value."""
    try:
        return datetime.fromisoformat(ts).strftime("%H:%M:%S")
    except (ValueError, TypeError):
        return str(ts or "")


# ---------------------------------------------------------------------------
# Markdown
# ---------------------------------------------------------------------------

def to_markdown(entries: list[dict], date: str = "") -> str:
    """Render entries as a clean chronological markdown list."""
    title = f"# Action log — {date}" if date else "# Action log"
    if not entries:
        return f"{title}\n\n_No actions logged._\n"

    lines = [title, "", f"_{len(entries)} actions recorded._", ""]
    for i, e in enumerate(entries, 1):
        t = _time_only(e.get("timestamp", ""))
        tool = e.get("tool", "?")
        method = e.get("method", "")
        summary = e.get("summary", "")
        status = e.get("status", "success")
        flag = "" if status == "success" else f" **[{status}]**"

        lines.append(f"### {i}. `{t}` — {tool} ({method}){flag}")
        lines.append("")
        lines.append(summary)
        inputs = e.get("inputs", "")
        if inputs:
            lines.append("")
            lines.append("```")
            lines.append(inputs)
            lines.append("```")
        out = e.get("output_summary", "")
        if out:
            lines.append("")
            lines.append(f"**Output:** {out}")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# HTML
# ---------------------------------------------------------------------------

def to_html(entries: list[dict], date: str = "") -> str:
    """Render entries as a simple standalone HTML page."""
    title = f"Action log — {date}" if date else "Action log"
    rows = []
    for i, e in enumerate(entries, 1):
        t = _html.escape(_time_only(e.get("timestamp", "")))
        tool = _html.escape(str(e.get("tool", "?")))
        method = _html.escape(str(e.get("method", "")))
        summary = _html.escape(str(e.get("summary", "")))
        inputs = _html.escape(str(e.get("inputs", "")))
        out = _html.escape(str(e.get("output_summary", "")))
        status = _html.escape(str(e.get("status", "success")))
        status_cls = "ok" if status == "success" else "err"
        rows.append(
            f'<tr class="{status_cls}">'
            f"<td>{i}</td><td class=t>{t}</td>"
            f"<td><span class=tool>{tool}</span><br><span class=method>{method}</span></td>"
            f"<td>{summary}"
            + (f"<pre>{inputs}</pre>" if inputs else "")
            + (f'<div class=out>{out}</div>' if out else "")
            + f"</td><td>{status}</td></tr>"
        )
    body = "\n".join(rows) if rows else '<tr><td colspan=5>No actions logged.</td></tr>'
    count = len(entries)
    return f"""<!DOCTYPE html>
<html lang=en><head><meta charset=utf-8>
<title>{_html.escape(title)}</title>
<style>
 body{{font:14px/1.5 -apple-system,Segoe UI,Roboto,sans-serif;margin:2rem;color:#1a1a1a;background:#fafafa}}
 h1{{font-size:1.4rem}}
 .meta{{color:#666;margin-bottom:1rem}}
 table{{border-collapse:collapse;width:100%;background:#fff}}
 th,td{{border:1px solid #e0e0e0;padding:.5rem .6rem;text-align:left;vertical-align:top}}
 th{{background:#f0f0f0}}
 .t{{white-space:nowrap;color:#555;font-variant-numeric:tabular-nums}}
 .tool{{font-weight:600}}
 .method{{color:#888;font-size:.85em}}
 pre{{margin:.4rem 0 0;padding:.4rem;background:#f6f8fa;border-radius:4px;white-space:pre-wrap;word-break:break-word;font-size:.85em}}
 .out{{margin-top:.4rem;color:#444;font-size:.9em}}
 tr.err{{background:#fff5f5}}
</style></head><body>
<h1>{_html.escape(title)}</h1>
<div class=meta>{count} actions recorded.</div>
<table>
<thead><tr><th>#</th><th>Time</th><th>Tool</th><th>What it did</th><th>Status</th></tr></thead>
<tbody>
{body}
</tbody></table>
</body></html>
"""


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Render the JSONL action log to markdown/HTML.")
    parser.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"), help="Log date YYYY-MM-DD (default today)")
    parser.add_argument("--working-dir", default=None, help="Working dir holding the logs (default <project>/working)")
    parser.add_argument("--log-path", default=None, help="Explicit JSONL path (overrides --date/--working-dir)")
    parser.add_argument("--html", action="store_true", help="Also write the HTML view")
    args = parser.parse_args()

    if args.log_path:
        jsonl = Path(args.log_path)
    else:
        jsonl = action_log_path(args.date, args.working_dir)

    entries = read_log(jsonl)

    md_path = jsonl.with_suffix(".md")
    md_path.write_text(to_markdown(entries, args.date))
    print(f"Wrote {md_path} ({len(entries)} actions)")

    if args.html:
        html_path = jsonl.with_suffix(".html")
        html_path.write_text(to_html(entries, args.date))
        print(f"Wrote {html_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
