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
    headlines = [
        (row.get("trial"), row.get("headline"))
        for row in report["records"]
        if row.get("headline")
    ]
    if headlines:
        lines.extend(["", "## Trial conclusions", ""])
        for trial, headline in headlines:
            lines.append(f"- **Trial {trial}:** {str(headline).replace(chr(10), ' ')}")
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
    grade_rows = "".join(
        f"<tr><td>{html.escape(str(key))}</td><td>{value}</td></tr>"
        for key, value in sorted(grade_counts.items())
    )
    case_summary = manifest.get("case_summary") or {}
    attempted = len(case_summary)
    passed = sum(
        1 for result in case_summary.values() if result.get("final_status") == "passed"
    )
    accuracy = passed / attempted if attempted else None
    case_rows = "".join(
        "<tr>"
        f"<td>{html.escape(str(case_id))}</td>"
        f"<td>{html.escape(str(result.get('final_status', 'unknown')).replace('_', ' '))}</td>"
        f"<td>{html.escape(', '.join(str(value) for value in result.get('grades', [])) or 'none')}</td>"
        f"<td>{html.escape(str((result.get('slices') or {}).get('domain', 'not tagged')).replace('_', ' '))}</td>"
        f"<td>{html.escape(str((result.get('slices') or {}).get('complexity', 'not tagged')).replace('_', ' '))}</td>"
        f"<td>{html.escape(str((result.get('slices') or {}).get('data_shape', 'not tagged')).replace('_', ' '))}</td>"
        f"<td>{html.escape(str((result.get('slices') or {}).get('risk', 'not tagged')).replace('_', ' '))}</td>"
        "</tr>"
        for case_id, result in sorted(case_summary.items())
    )
    slice_rows = []
    for name, counts in sorted((manifest.get("slice_summary") or {}).items()):
        slice_attempted = sum(int(value) for value in counts.values())
        slice_passed = int(counts.get("pass", 0))
        slice_accuracy = slice_passed / slice_attempted if slice_attempted else None
        dimension, _, value = name.partition(":")
        slice_rows.append(
            "<tr>"
            f"<td>{html.escape(dimension.replace('_', ' '))}</td>"
            f"<td>{html.escape(value.replace('_', ' '))}</td>"
            f"<td>{slice_passed}</td><td>{slice_attempted}</td>"
            f"<td>{_pct(slice_accuracy)}</td>"
            "</tr>"
        )
    case_section = ""
    if case_summary:
        case_section = f"""
<h2>Focused case accuracy</h2>
<div class="metric"><strong>{passed} of {attempted}</strong><span>{_pct(accuracy)}</span></div>
<h2>Every case</h2>
<table><thead><tr><th>Case</th><th>Result</th><th>Grades</th><th>Domain</th><th>Complexity</th><th>Data shape</th><th>Risk</th></tr></thead><tbody>{case_rows}</tbody></table>
"""
    slice_section = ""
    if slice_rows:
        slice_section = f"""
<h2>Slices</h2>
<table><thead><tr><th>Dimension</th><th>Slice</th><th>Passed</th><th>Attempted</th><th>Accuracy</th></tr></thead><tbody>{''.join(slice_rows)}</tbody></table>
<p class="note">Small slices are descriptive. One passing case is not a stable estimate of performance for that domain or risk.</p>
"""
    document = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>{html.escape(title)}</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 40px; color: #1f2937; }}
.card {{ border: 1px solid #dbe3ea; border-radius: 12px; padding: 24px; max-width: 1200px; }}
h1 {{ font-size: 28px; }} table {{ border-collapse: collapse; width: 100%; }}
td, th {{ border-bottom: 1px solid #e5e7eb; padding: 10px; text-align: left; vertical-align: top; }}
.metric {{ display: flex; gap: 20px; align-items: baseline; padding: 16px 20px; background: #f7f9fc; border-left: 4px solid #0877b9; }}
.metric strong {{ font-size: 28px; }} .metric span {{ font-size: 22px; color: #0877b9; font-weight: 700; }}
.note {{ background: #eef6ff; border-left: 4px solid #0877b9; padding: 12px; }}
pre {{ white-space: pre-wrap; overflow-wrap: anywhere; }}
</style></head><body><div class="card">
<h1>{html.escape(title)}</h1>
<p>Suite {html.escape(str(manifest['suite_id']))}, version {html.escape(str(manifest['suite_version']))}, exposure {html.escape(str(manifest['exposure']))}, purpose {html.escape(str(manifest.get('purpose') or 'mixed'))}.</p>
<p>{manifest.get('completed_trials', 0)} of {manifest.get('requested_trials', 0)} trials reached a recorded terminal state.</p>
{case_section}
<h2>Grade outcomes</h2><table><thead><tr><th>Status</th><th>Count</th></tr></thead><tbody>{grade_rows}</tbody></table>
{slice_section}
<p class="note">This score describes focused calculation cases only. It does not establish complete-analysis accuracy. Read every case before trusting the aggregate.</p>
<details><summary>Run manifest</summary><pre>{html.escape(json.dumps(manifest, indent=2))}</pre></details>
</div></body></html>"""
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(document, encoding="utf-8")
    return path
