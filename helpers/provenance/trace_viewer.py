"""/trace viewer (provenance, 0.9).

One self-contained HTML that traces each reported number to the SQL that produced it, with a
confidence badge (cited / value-match / inferred) — the on-demand "expose the query logic" artifact.
Reads the reconcile_provenance output. Self-contained (inline CSS), projection-friendly (large type,
collapsible SQL), and surfaces unmatched findings + orphan queries rather than hiding them.
"""
from __future__ import annotations

import html
import re
from pathlib import Path

_CSS = """
body{font-family:-apple-system,Segoe UI,Roboto,sans-serif;max-width:1000px;margin:24px auto;padding:0 16px;color:#1a1a1a;font-size:16px;line-height:1.5}
h1{font-size:24px} h2{font-size:19px;margin-top:28px;border-bottom:2px solid #eee;padding-bottom:4px}
.meta{color:#555;font-size:14px}
.finding{border:1px solid #e5e5e5;border-radius:8px;padding:14px 16px;margin:14px 0}
.fval{font-size:20px;font-weight:700} .ftext{color:#333} .fid{font-family:monospace;font-size:12px;color:#999}
.badge{display:inline-block;border-radius:12px;padding:1px 9px;font-size:12px;font-weight:600;margin-right:6px}
.cited{background:#dcfce7;color:#166534} .value-match{background:#fef3c7;color:#92400e} .inferred{background:#e5e7eb;color:#374151}
.q{margin:8px 0 0;padding:8px 10px;background:#fafafa;border-radius:6px}
.qid{font-family:monospace;font-size:12px;color:#666} .qmeta{font-size:13px;color:#555}
details summary{cursor:pointer;font-size:13px;color:#2563eb} pre{background:#0f172a;color:#e2e8f0;padding:10px;border-radius:6px;overflow-x:auto;font-size:13px}
.warn{background:#fef2f2;border:1px solid #fecaca;color:#991b1b;border-radius:6px;padding:10px;margin:8px 0}
.ok{background:#f0fdf4;border:1px solid #bbf7d0;color:#166534;border-radius:6px;padding:10px;margin:8px 0}
table{border-collapse:collapse;width:100%;font-size:13px} td,th{border-bottom:1px solid #eee;padding:5px 8px;text-align:left}
.action{border:1px solid #e5e5e5;border-radius:8px;margin:10px 0;background:#fafafa}
.action summary{padding:10px 12px;color:#1a1a1a;font-size:14px}
.action-body{padding:0 12px 12px}.action-meta{color:#666;font-size:12px;margin-bottom:8px}
.action-label{font-weight:600;margin-top:8px}.action-value{white-space:pre-wrap;overflow-wrap:anywhere;background:#fff;border-radius:5px;padding:8px;font-family:monospace;font-size:12px}
.status-success{color:#166534}.status-error{color:#991b1b}
"""


_ACTION_SECRET_PATTERNS = (
    re.compile(r"\b(?:xox[pbarso]-|sk-|ghp_|AKIA)[A-Za-z0-9._-]+"),
    re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+"),
    re.compile(
        r"(?i)(\b(?:password|passwd|api[_-]?key|access[_-]?token|refresh[_-]?token|client[_-]?secret|private[_-]?key|snowflake_token|slack_user_token)\b\s*[:=]\s*)([^\s,;]+)"
    ),
)


def _redact_action_text(value) -> str:
    """Remove common credential shapes before action details enter shareable HTML."""
    text = str(value or "")
    for index, pattern in enumerate(_ACTION_SECRET_PATTERNS):
        if index == 2:
            text = pattern.sub(r"\1[REDACTED]", text)
        else:
            text = pattern.sub("[REDACTED]", text)
    return text


def _q_block(q):
    qid = html.escape(str(q.get("query_id", "")))
    sql = html.escape(str(q.get("sql", "")))
    tables = ", ".join(q.get("tables_accessed") or [])
    meta = (f"tables: {html.escape(tables)} · rows: {q.get('row_count')} · "
            f"result: {html.escape(str(q.get('result_value')))}")
    preview = q.get("result_preview") or []
    preview_html = ""
    if preview:
        preview_html = (
            '<details><summary>Recorded result preview</summary><pre>'
            + html.escape(__import__("json").dumps(preview, indent=2, default=str))
            + "</pre></details>"
        )
    return (f'<div class="q"><span class="qid">{qid}</span> <span class="qmeta">{meta}</span>'
            f'<details><summary>SQL</summary><pre>{sql}</pre></details>{preview_html}</div>')


def render_trace(provenance, out_path, title="Provenance trace"):
    """Render the reconcile_provenance dict to a self-contained HTML. Returns out_path."""
    findings = provenance.get("findings", [])
    qindex = {q.get("query_id"): q for q in provenance.get("query_entries", [])}
    links_by_f = {}
    for l in provenance.get("links", []):
        links_by_f.setdefault(l["finding_id"], []).append(l)
    aid = html.escape(str(provenance.get("analysis_id", "")))
    analysis = provenance.get("analysis") or {}
    question = html.escape(str(analysis.get("question") or "Not recorded"))
    decision = html.escape(str(analysis.get("intended_decision") or "Not recorded"))

    conf_counts = {}
    for l in provenance.get("links", []):
        conf_counts[l["confidence"]] = conf_counts.get(l["confidence"], 0) + 1
    conf_str = ", ".join(f"{c} {n}" for c, n in conf_counts.items()) or "none"
    meta = (f"analysis {aid} · {len(findings)} findings · {len(qindex)} queries · "
            f"{len(provenance.get('actions') or [])} actions · links: {conf_str}")

    blocks = []
    for f in findings:
        fid = f.get("finding_id")
        fl = links_by_f.get(fid, [])
        qhtml = ""
        for l in fl:
            q = qindex.get(l["query_id"], {"query_id": l["query_id"]})
            qhtml += f'<span class="badge {l["confidence"]}">{l["confidence"]}</span>' + _q_block(q)
        if not fl:
            qhtml = '<div class="warn">No query linked — this number is unverified.</div>'
        blocks.append(
            f'<div class="finding"><div class="fval">{html.escape(str(f.get("value")))}</div>'
            f'<div class="ftext">{html.escape(str(f.get("text", "")))}</div>'
            f'<div class="fid">{html.escape(str(fid))}</div>'
            + (f'<div class="qmeta">calculation: {html.escape(str(f.get("calculation")))}</div>'
               if f.get("calculation") else "")
            + f'{qhtml}</div>')
    findings_html = "".join(blocks) or "<p>No findings recorded.</p>"

    qs = sorted(provenance.get("query_entries", []), key=lambda q: q.get("timestamp") or "")
    trows = "".join(
        f'<tr><td class="qid">{html.escape(str(q.get("query_id", "")))}</td>'
        f'<td>{html.escape(str(q.get("timestamp", "")))}</td>'
        f'<td>{html.escape(str(q.get("result_value")))}</td>'
        f'<td>{html.escape((q.get("sql") or "")[:80])}</td></tr>' for q in qs)
    timeline = ('<table><thead><tr><th>query</th><th>when</th><th>result</th><th>sql</th></tr>'
                f'</thead><tbody>{trows}</tbody></table>')

    actions = sorted(provenance.get("actions") or [], key=lambda a: a.get("timestamp") or "")
    action_blocks = []
    for index, action in enumerate(actions, start=1):
        timestamp = html.escape(str(action.get("timestamp") or "Time not recorded"))
        tool = html.escape(str(action.get("tool") or "Tool not recorded"))
        method = html.escape(str(action.get("method") or "action"))
        summary = html.escape(str(action.get("summary") or tool))
        status_raw = str(action.get("status") or "unknown")
        status = html.escape(status_raw)
        status_class = "status-success" if status_raw == "success" else "status-error" if status_raw == "error" else ""
        inputs = html.escape(_redact_action_text(action.get("inputs") or "Not recorded"))
        output = html.escape(_redact_action_text(action.get("output_summary") or "Not recorded"))
        action_blocks.append(
            f'<details class="action"><summary><strong>{index}. {summary}</strong> '
            f'<span class="{status_class}">[{status}]</span></summary>'
            f'<div class="action-body"><div class="action-meta">{timestamp} · {tool} · {method}</div>'
            f'<div class="action-label">Input</div><div class="action-value">{inputs}</div>'
            f'<div class="action-label">Recorded output</div><div class="action-value">{output}</div>'
            f'</div></details>'
        )
    actions_html = "".join(action_blocks) or "<p>No matching actions were recorded for this analysis.</p>"

    warns = ""
    if provenance.get("unmatched_findings"):
        warns += ('<div class="warn">Unmatched findings (no query linked): '
                  f'{html.escape(", ".join(provenance["unmatched_findings"]))}</div>')
    if provenance.get("orphan_queries"):
        warns += ('<div class="warn">Orphan queries (linked to no finding): '
                  f'{len(provenance["orphan_queries"])}</div>')

    doc = (f'<!doctype html><html><head><meta charset="utf-8"><title>{html.escape(title)}</title>'
           f'<style>{_CSS}</style></head><body>'
           f'<h1>{html.escape(title)}</h1><p class="meta">{meta}</p>'
           f'<h2>Analysis</h2><p><strong>Question:</strong> {question}</p>'
           f'<p><strong>Decision:</strong> {decision}</p>{warns}'
           f'<h2>Findings → the query that produced each</h2>{findings_html}'
           f'<h2>Query timeline</h2>{timeline}'
           f'<h2>Action timeline</h2><p class="meta">Actions recorded under this analysis ID. Expand an action to inspect its input and recorded output.</p>'
           f'{actions_html}</body></html>')
    Path(out_path).write_text(doc)
    return str(out_path)


def build_trace(analysis_id, dataset, date, working_dir=None, out_path=None):
    """Reconcile the analysis, render the trace HTML, return its path."""
    from helpers.provenance.reconcile_provenance import reconcile_analysis

    prov = reconcile_analysis(analysis_id, dataset, date, working_dir=working_dir)
    if out_path is None:
        base = Path(working_dir) if working_dir else Path("working")
        out_path = base / f"trace_{analysis_id}.html"
    return render_trace(prov, out_path)
