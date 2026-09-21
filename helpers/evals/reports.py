"""Readable Markdown and HTML reports for evaluation artifacts."""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any


def _pct(value: float | None) -> str:
    return "unknown" if value is None else f"{value * 100:.1f}%"


def render_reliability(report: dict[str, Any], output: str | Path) -> Path:
    lines = [
        "# Reliability report",
        "",
        f"**Verdict:** {report['verdict'].replace('_', ' ')}",
        f"**Successful trials:** {report['successful_trials']} of {report['requested_trials']}",
        f"**Exact agreement:** {_pct(report['exact_agreement']['rate'])}",
        f"**Agreement within the named tolerance:** {_pct(report['tolerance_agreement']['rate'])}",
        "",
        "| Trial | Status | Raw result | Normalized result | What it measured |",
        "|---:|---|---|---:|---|",
    ]
    for row in report["records"]:
        measured = str(row.get("measured") or "").replace("|", "/")
        lines.append(
            f"| {row['trial']} | {row['status']} | {row.get('raw')} | {row.get('normalized')} | {measured} |"
        )
    lines.extend(["", f"> {report['claim']}"])
    if report.get("definition_groups"):
        lines.extend(["", "## Definition groups", ""])
        for key, group in report["definition_groups"].items():
            values = ", ".join(str(value) for value in group.get("values", []))
            lines.append(f"- **{key}:** {group.get('count', 0)} trial(s); values: {values}")
    if not report.get("numerical_comparison_valid", True):
        lines.extend([
            "",
            "> Numerical agreement is not calculated across different analytical definitions.",
        ])
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def render_run_summary(manifest: dict[str, Any], output: str | Path) -> Path:
    title = f"Evaluation run {manifest['run_id']}"
    grade_counts = manifest.get("configuration", {}).get("grade_status_counts", {})
    rows = "".join(
        f"<tr><td>{html.escape(str(key))}</td><td>{value}</td></tr>"
        for key, value in sorted(grade_counts.items())
    )
    document = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>{html.escape(title)}</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 40px; color: #1f2937; }}
.card {{ border: 1px solid #dbe3ea; border-radius: 12px; padding: 24px; max-width: 900px; }}
h1 {{ font-size: 28px; }} table {{ border-collapse: collapse; width: 100%; }}
td, th {{ border-bottom: 1px solid #e5e7eb; padding: 10px; text-align: left; }}
.note {{ background: #eef6ff; border-left: 4px solid #0877b9; padding: 12px; }}
</style></head><body><div class="card">
<h1>{html.escape(title)}</h1>
<p>Suite {html.escape(str(manifest['suite_id']))}, version {html.escape(str(manifest['suite_version']))}, exposure {html.escape(str(manifest['exposure']))}, purpose {html.escape(str(manifest.get('purpose') or 'mixed'))}.</p>
<p>{manifest.get('completed_trials', 0)} of {manifest.get('requested_trials', 0)} trials reached a recorded terminal state.</p>
<h2>Grade outcomes</h2><table><thead><tr><th>Status</th><th>Count</th></tr></thead><tbody>{rows}</tbody></table>
<p class="note">Read the per-case records and traces. An aggregate cannot tell you which failure matters or whether the evaluator itself is sound.</p>
<details><summary>Run manifest</summary><pre>{html.escape(json.dumps(manifest, indent=2))}</pre></details>
</div></body></html>"""
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(document, encoding="utf-8")
    return path
