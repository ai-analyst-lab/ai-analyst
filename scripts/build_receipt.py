#!/usr/bin/env python3
"""Assemble Sections 1-7 of the analysis receipt from pipeline artifacts.

The receipt is the Reproduce-level audit trail: environment, per-finding
provenance with full SQL, validation summary, the complete query log,
cross-verification detail, pipeline execution, and reproduction steps. All of
that is fully determined by the artifacts on disk, so this script writes it.
Section 8 (Caveats and Limitations) is a judgment call; the receipt-generator
agent writes it after reading the skeleton this script produces.

Usage:
    python3 scripts/build_receipt.py --dataset NAME --date YYYY-MM-DD \
        [--run-dir working/runs/<run>] [--out outputs/analysis_receipt_NAME_DATE.md]

Explicit artifact paths (--query-log, --validation, --cv-yaml, --cv-md,
--state, --manifest) override discovery. Discovery looks in the run directory
first (when given), then in working/ and outputs/, and picks the newest file
by date suffix when several match.

Every section names the artifact it was built from and that file's
modification time. A missing optional artifact yields a clearly marked
"not available" section; a missing query log is the one hard error, because a
receipt without queries is not a receipt.

Exit codes:
    0 - receipt written
    1 - query log not found (or bad arguments)
    2 - write error
"""

from __future__ import annotations

import argparse
import json
import platform
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from helpers.provenance.query_log import to_markdown  # noqa: E402

try:  # yaml is a project dependency, but the receipt must not die without it
    import yaml
except ImportError:  # pragma: no cover
    yaml = None


class ReceiptError(Exception):
    """Raised when the receipt cannot be built at all (no query log)."""


NOT_AVAILABLE = "_Not available._"
SECTION_8_PLACEHOLDER = (
    "<!-- receipt-generator: replace this comment with the caveats and limitations. "
    "Every caveat must trace to an artifact listed in the seeds below. -->"
)
LARGE_LOG_THRESHOLD = 100
LARGE_LOG_KEEP = 50

# Per-connection reproduction tolerance notes. Deterministic sources reproduce
# exactly; live warehouses may vary on approximate functions or fresh rows.
_TOLERANCE_NOTES = {
    "duckdb": (0.0, "DuckDB on static files should reproduce exactly."),
    "csv": (0.0, "CSV sources should reproduce exactly."),
    "sqlite": (0.0, "SQLite on a static file should reproduce exactly."),
    "snowflake": (1.0, "Snowflake may show minor variance on approximate functions (HyperLogLog) and on tables receiving new rows."),
    "bigquery": (1.0, "BigQuery may show variance from the streaming buffer and approximate functions."),
    "postgres": (0.5, "Postgres may show variance from concurrent transactions (MVCC snapshots)."),
    "redshift": (1.0, "Redshift may show variance on approximate functions and recently loaded rows."),
    "databricks": (1.0, "Databricks may show variance on approximate functions and streaming tables."),
}


# ---------------------------------------------------------------------------
# Artifact discovery and loading
# ---------------------------------------------------------------------------

def _newest(paths: list[Path]) -> Path | None:
    """Pick the newest file by name (date suffix sorts lexically) then mtime."""
    existing = [p for p in paths if p.is_file()]
    if not existing:
        return None
    return sorted(existing, key=lambda p: (p.name, p.stat().st_mtime))[-1]


def _find(
    candidates_dirs: list[Path], exact: str, pattern: str, explicit: str | None
) -> Path | None:
    """Resolve an artifact: explicit path, else exact name, else newest glob match."""
    if explicit:
        p = Path(explicit)
        return p if p.is_file() else None
    for d in candidates_dirs:
        p = d / exact
        if p.is_file():
            return p
    for d in candidates_dirs:
        found = _newest(list(d.glob(pattern)))
        if found:
            return found
    return None


def discover_artifacts(
    dataset: str,
    date: str,
    run_dir: Path | None = None,
    root: Path = Path("."),
    overrides: dict[str, str | None] | None = None,
) -> dict[str, Path | None]:
    """Locate every artifact the receipt reads. Missing ones map to None."""
    overrides = overrides or {}
    working_dirs = [root / "working"]
    output_dirs = [root / "outputs"]
    state_dirs = [root / "working"]
    if run_dir:
        working_dirs = [run_dir / "working", run_dir, *working_dirs]
        output_dirs = [run_dir / "outputs", run_dir, *output_dirs]
        state_dirs = [run_dir, run_dir / "working", *state_dirs]

    tag = f"{dataset}_{date}"
    manifest = root / ".knowledge" / "datasets" / dataset / "manifest.yaml"
    if overrides.get("manifest"):
        manifest = Path(overrides["manifest"])

    return {
        "query_log": _find(working_dirs, f"query_log_{tag}.jsonl", f"query_log_{dataset}_*.jsonl", overrides.get("query_log")),
        "validation": _find(output_dirs, f"validation_{tag}.md", f"validation_{dataset}_*.md", overrides.get("validation")),
        "cv_yaml": _find(working_dirs, f"provenance_{tag}.yaml", f"provenance_{dataset}_*.yaml", overrides.get("cv_yaml")),
        "cv_md": _find(working_dirs, f"cross_verification_{tag}.md", f"cross_verification_{dataset}_*.md", overrides.get("cv_md")),
        "state": _find(state_dirs, "pipeline_state.json", "pipeline_state.json", overrides.get("state")),
        "manifest": manifest if manifest.is_file() else None,
    }


def _read_jsonl(path: Path) -> list[dict]:
    entries = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries


def _read_yaml(path: Path | None) -> Any:
    if path is None or yaml is None:
        return None
    try:
        with path.open() as f:
            return yaml.safe_load(f)
    except Exception:
        return None


def _read_json(path: Path | None) -> dict | None:
    if path is None:
        return None
    try:
        with path.open() as f:
            data = json.load(f)
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def _stamp(path: Path | None) -> str:
    """'Source: <path> (modified <iso time>)' or a not-available marker."""
    if path is None:
        return "_Source: not available._"
    mtime = datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
    return f"_Source: `{path}` (modified {mtime})_"


# ---------------------------------------------------------------------------
# Derived facts
# ---------------------------------------------------------------------------

def _claims_from_provenance(prov: Any) -> list[dict]:
    """Normalize the provenance YAML into a list of claim dicts.

    The cross-verification agent writes either a top-level list of claims or a
    mapping with a `claims` list; both are accepted.
    """
    if isinstance(prov, dict):
        claims = prov.get("claims") or []
    elif isinstance(prov, list):
        claims = prov
    else:
        claims = []
    return [c for c in claims if isinstance(c, dict) and (c.get("claim_id") or c.get("finding_id"))]


def _claim_id(claim: dict) -> str:
    return str(claim.get("claim_id") or claim.get("finding_id"))


def _connection_facts(manifest: Any, entries: list[dict]) -> tuple[str, str]:
    """(connection_type, database) from the manifest, else the query log, else unknown."""
    conn_type = ""
    database = ""
    if isinstance(manifest, dict):
        conn_type = str(manifest.get("connection_type") or "")
        conn = manifest.get("connection")
        if isinstance(conn, dict):
            conn_type = conn_type or str(conn.get("type") or "")
            database = str(conn.get("database") or conn.get("path") or conn.get("db_path") or "")
        database = database or str(manifest.get("database") or manifest.get("db_path") or "")
    if not conn_type:
        types = [e.get("connection_type") for e in entries if e.get("connection_type") not in (None, "", "unknown")]
        conn_type = types[0] if types else "unknown"
    return conn_type.lower(), database or "not recorded"


def _tables_accessed(entries: list[dict]) -> list[str]:
    seen: dict[str, None] = {}
    for e in entries:
        for t in e.get("tables_accessed") or []:
            seen.setdefault(str(t), None)
    return list(seen)


def _lib_version(name: str) -> str:
    try:
        from importlib.metadata import version
        return version(name)
    except Exception:
        return "not installed"


def _status_of(check: Any) -> str:
    if isinstance(check, dict):
        return str(check.get("status") or "N/A")
    return "N/A"


def _overall_claim_status(verification: dict) -> str:
    statuses = [
        _status_of(verification.get(k))
        for k in ("boundary", "parts_to_whole", "ratio_recompute", "algebraic_identity", "reproducibility")
    ]
    if "FAIL" in statuses:
        return "Failed"
    if "WARN" in statuses:
        return "Partial"
    if "PASS" in statuses:
        return "Verified"
    return "Unverified"


def _primary_check(verification: dict) -> tuple[str, str, str]:
    """Most specific check that ran (D > C > B > A): (method, status, detail)."""
    for key, label in (
        ("algebraic_identity", "Type D: Algebraic identity"),
        ("ratio_recompute", "Type C: Ratio recompute"),
        ("parts_to_whole", "Type B: Parts-to-whole"),
        ("boundary", "Type A: Boundary check"),
    ):
        check = verification.get(key)
        status = _status_of(check)
        if status == "N/A":
            continue
        if key == "boundary":
            n = len(check.get("checks") or [])
            detail = f"{n} checks passed" if status == "PASS" else "Boundary violation"
        else:
            diff = check.get("diff_pct")
            tol = check.get("effective_tolerance")
            detail = ""
            if isinstance(diff, (int, float)):
                detail = f"diff {diff:.4%}"
                if isinstance(tol, (int, float)):
                    detail += f", tolerance {tol:.2%}"
            detail = detail or status
        return label, status, detail
    return "None", "N/A", "No verification checks ran"


def _duration(start: str | None, end: str | None) -> str:
    try:
        s = datetime.fromisoformat(str(start).replace("Z", "+00:00"))
        e = datetime.fromisoformat(str(end).replace("Z", "+00:00"))
    except Exception:
        return "—"
    secs = int((e - s).total_seconds())
    if secs < 0:
        return "—"
    if secs < 60:
        return f"{secs}s"
    return f"{secs // 60}m {secs % 60:02d}s"


# ---------------------------------------------------------------------------
# Section renderers
# ---------------------------------------------------------------------------

def _section_environment(conn_type: str, database: str, tables: list[str], manifest_path: Path | None) -> str:
    libs = ", ".join(f"{n} {_lib_version(n)}" for n in ("pandas", "duckdb", "matplotlib"))
    rows = [
        ("Connection type", conn_type),
        ("Database", database),
        ("Tables accessed", ", ".join(tables) if tables else "none recorded"),
        ("Python version", platform.python_version()),
        ("Key libraries", libs),
    ]
    table = "| Property | Value |\n|----------|-------|\n" + "\n".join(f"| {k} | {v} |" for k, v in rows)
    return f"## 1. Environment\n\n{_stamp(manifest_path)}\n\n{table}"


def _section_findings(claims: list[dict], entries: list[dict], conn_type: str, database: str, cv_path: Path | None) -> str:
    head = f"## 2. Findings Provenance\n\n{_stamp(cv_path)}"
    if not claims:
        return f"{head}\n\n{NOT_AVAILABLE} No provenance record was produced for this analysis, so findings cannot be listed with their backing queries."
    by_id = {e.get("query_id"): e for e in entries}
    by_claim: dict[str, list[dict]] = {}
    for e in entries:
        for cid in e.get("claim_ids") or []:
            by_claim.setdefault(str(cid), []).append(e)

    blocks = [head]
    for i, claim in enumerate(claims, 1):
        cid = _claim_id(claim)
        title = str(claim.get("claim_text") or claim.get("finding_title") or "")
        verification = claim.get("verification") or {}
        refs = [str(r) for r in (claim.get("query_log_refs") or [])]
        backing = [by_id[r] for r in refs if r in by_id] + [e for e in by_claim.get(cid, []) if e.get("query_id") not in refs]

        part = [f"### F{i}: {cid} — {title}".rstrip(" —")]
        if backing:
            for e in backing:
                part.append("")
                part.append(f"**Query `{e.get('query_id')}`** ({e.get('agent', '—')}, step {e.get('pipeline_step', '—')}): {e.get('purpose', '')}")
                part.append(f"- Tables: {', '.join(e.get('tables_accessed') or []) or '—'}")
                part.append(f"- Result: {e.get('result_summary') or '—'} (rows: {e.get('row_count', '—')}, {float(e.get('execution_ms') or 0):.0f} ms, {e.get('status', 'success')})")
                part.append("")
                part.append("```sql")
                part.append(str(e.get("sql") or "").rstrip())
                part.append("```")
        else:
            part.append("")
            part.append("**SQL:** no query in the log is linked to this claim.")

        method, status, detail = _primary_check(verification)
        part.append("")
        part.append("**Cross-verification:**")
        part.append(f"- Method: {method}")
        part.append(f"- Result: {status}")
        part.append(f"- Detail: {detail}")

        repro = verification.get("reproducibility")
        part.append("")
        part.append("**Reproducibility:**")
        if isinstance(repro, dict):
            part.append(f"- Runs: {repro.get('n_runs', 0)}")
            part.append(f"- Variance: {repro.get('variance', 0)}")
            part.append(f"- Deterministic: {str(bool(repro.get('deterministic', conn_type in ('duckdb', 'csv')))).lower()}")
        else:
            part.append(f"- Not run (source: {conn_type}, database: {database})")
        blocks.append("\n".join(part))
    return "\n\n".join(blocks)


_CONF_RE = re.compile(r"([A-F])\s*\((\d{1,3})/100\)|(\d{1,3})/100\s*\(([A-F])\)")


def _section_validation(path: Path | None) -> tuple[str, dict]:
    """Render Section 3 and return facts (grade, score, blockers) for later use."""
    facts: dict[str, Any] = {"grade": None, "score": None, "overall": None, "recommendations": []}
    head = f"## 3. Validation Summary\n\n{_stamp(path)}"
    if path is None:
        return f"{head}\n\n{NOT_AVAILABLE} Validation not performed.", facts
    text = path.read_text()

    m = re.search(r"^## Overall Confidence:\s*(.+)$", text, re.M)
    if m:
        facts["overall"] = m.group(1).strip()
    m = _CONF_RE.search(text)
    if m:
        facts["grade"] = m.group(1) or m.group(4)
        facts["score"] = int(m.group(2) or m.group(3))
    m = re.search(r"^\*\*Summary:\*\*\s*(.+)$", text, re.M)
    summary = m.group(1).strip() if m else ""

    def section(name: str) -> str:
        sm = re.search(rf"^## {re.escape(name)}\s*\n(.*?)(?=^## |\Z)", text, re.M | re.S)
        return sm.group(1).strip() if sm else ""

    layers = section("Validation Layers")
    recs = section("Recommendations")
    facts["recommendations"] = [ln.strip() for ln in recs.splitlines() if re.match(r"^\s*\d+\.", ln)]

    lines = [head, ""]
    lines.append(f"**Overall confidence:** {facts['overall'] or 'not stated'}")
    if facts["score"] is not None:
        lines.append(f"**Score:** {facts['score']}/100 ({facts['grade']})")
    else:
        lines.append("**Score:** not stated in the validation report")
    if summary:
        lines.append(f"**Summary:** {summary}")
    lines.append("")
    lines.append("### Validation layers")
    lines.append("")
    lines.append(layers or "_The validation report has no Validation Layers table._")
    lines.append("")
    lines.append("### Recommendations")
    lines.append("")
    lines.append(recs or "_None listed._")
    return "\n".join(lines), facts


def _section_query_log(entries: list[dict], claims: list[dict], path: Path) -> tuple[str, dict]:
    total_ms = sum(float(e.get("execution_ms") or 0) for e in entries)
    errors = sum(1 for e in entries if e.get("status") == "error")
    backfilled = sum(1 for e in entries if str(e.get("query_id", "")).startswith("backfill_"))

    shown = entries
    note = ""
    if len(entries) > LARGE_LOG_THRESHOLD:
        shown = sorted(entries, key=lambda e: float(e.get("execution_ms") or 0), reverse=True)[:LARGE_LOG_KEEP]
        note = f"\n\n_Showing the {LARGE_LOG_KEEP} slowest of {len(entries)} queries; the full log is in the source file._"

    linked = {str(c) for e in entries for c in (e.get("claim_ids") or [])}
    matched = 0
    for c in claims:
        cid = _claim_id(c)
        if cid in linked or c.get("query_log_refs"):
            matched += 1
    total_claims = len(claims)
    pct = (matched / total_claims * 100) if total_claims else None

    facts = {"total": len(entries), "errors": errors, "backfilled": backfilled, "coverage_pct": pct, "matched": matched, "total_claims": total_claims}
    coverage_line = (
        f"**Coverage:** {pct:.0f}% of claims have backing queries ({matched}/{total_claims})"
        if pct is not None else "**Coverage:** no claims to match (no provenance record)"
    )
    body = (
        f"## 4. Full Query Log\n\n{_stamp(path)}\n\n{to_markdown(shown)}{note}\n\n"
        f"{coverage_line}\n"
        f"**Total queries:** {len(entries)} ({errors} errored, {backfilled} backfilled)\n"
        f"**Total execution time:** {total_ms:.0f}ms"
    )
    return body, facts


def _section_cross_verification(claims: list[dict], prov: Any, path: Path | None) -> str | None:
    """Section 5, or None when cross-verification did not run (the section is omitted)."""
    if not claims:
        return None
    lines = [f"## 5. Cross-Verification Detail", "", _stamp(path), ""]
    if isinstance(prov, dict):
        meta = []
        if prov.get("gate_decision"):
            meta.append(f"**Gate decision:** {prov['gate_decision']}")
        if prov.get("confidence_score") is not None:
            meta.append(f"**Confidence contribution:** {prov['confidence_score']}/15")
        if meta:
            lines.extend(meta)
            lines.append("")
    lines.append("| Claim | Type A | Type B | Type C | Type D | Repro | Overall |")
    lines.append("|-------|--------|--------|--------|--------|-------|---------|")
    for c in claims:
        v = c.get("verification") or {}
        text = str(c.get("claim_text") or "")
        label = f"{_claim_id(c)}: {text[:50]}" if text else _claim_id(c)
        lines.append(
            f"| {label} | {_status_of(v.get('boundary'))} | {_status_of(v.get('parts_to_whole'))} | "
            f"{_status_of(v.get('ratio_recompute'))} | {_status_of(v.get('algebraic_identity'))} | "
            f"{_status_of(v.get('reproducibility')) if v.get('reproducibility') else 'N/A'} | {_overall_claim_status(v)} |"
        )
    return "\n".join(lines)


def _section_pipeline(state: dict | None, path: Path | None) -> str | None:
    """Section 6, or None when there is no pipeline state (the section is omitted)."""
    if not state:
        return None
    agents = state.get("agents") or {}
    lines = [f"## 6. Pipeline Execution", "", _stamp(path), ""]
    lines.append(f"**Run ID:** {state.get('run_id', 'not recorded')}")
    lines.append(f"**Pipeline status:** {state.get('status', 'not recorded')}")
    lines.append("")
    lines.append("| Agent | Status | Started | Duration | Output |")
    lines.append("|-------|--------|---------|----------|--------|")
    complete = 0
    for name, a in agents.items():
        a = a or {}
        status = a.get("status", "pending")
        if status in ("complete", "completed_legacy"):
            complete += 1
        lines.append(
            f"| {name} | {status} | {a.get('started_at', '—')} | "
            f"{_duration(a.get('started_at'), a.get('completed_at'))} | {a.get('output_file', '—')} |"
        )
    lines.append("")
    lines.append(f"**Total pipeline time:** {_duration(state.get('started_at'), state.get('updated_at'))}")
    lines.append(f"**Agents completed:** {complete} / {len(agents)}")
    degraded = [n for n, a in agents.items() if (a or {}).get('status') == 'degraded']
    failed = [n for n, a in agents.items() if (a or {}).get('status') == 'failed']
    if degraded:
        lines.append(f"**Degraded:** {', '.join(degraded)}")
    if failed:
        lines.append(f"**Failed:** {', '.join(failed)}")
    return "\n".join(lines)


def _section_reproduce(conn_type: str, database: str, tables: list[str], n_findings: int) -> str:
    tol, note = _TOLERANCE_NOTES.get(conn_type, (None, "Variance characteristics for this source are not documented; compare within a small relative tolerance."))
    tol_line = f"expect up to {tol:g}% variance on approximate functions" if tol else "reproduction should be exact"
    where = "Section 2" if n_findings else "Section 4"
    return "\n".join([
        "## 7. Reproducibility Instructions",
        "",
        "To reproduce this analysis:",
        "",
        f"1. **Data source:** Connect to the `{conn_type}` source, database `{database}`",
        f"2. **Tables required:** {', '.join(tables) if tables else 'see the query log'}",
        f"3. **Run queries:** Execute each SQL query in {where} in order",
        f"4. **Expected results:** Compare your output to the result recorded with each query",
        f"5. **Tolerance:** For {conn_type}, {tol_line}",
        "",
        f"Note: {note}",
    ])


def _section_caveats(seeds: list[str]) -> str:
    lines = ["## 8. Caveats and Limitations", "", SECTION_8_PLACEHOLDER, ""]
    lines.append("**Seeds from the artifacts** (facts the caveats must account for; delete this list once the caveats are written):")
    lines.append("")
    for s in seeds or ["- No warnings, gaps, or variance were found in the artifacts."]:
        lines.append(s)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------

def build_receipt(
    dataset: str,
    date: str,
    run_dir: Path | None = None,
    root: Path = Path("."),
    overrides: dict[str, str | None] | None = None,
) -> tuple[str, dict]:
    """Assemble the receipt markdown. Returns (markdown, facts).

    Raises ReceiptError when no query log can be found.
    """
    art = discover_artifacts(dataset, date, run_dir, root, overrides)
    if art["query_log"] is None:
        raise ReceiptError("Query log not found. Receipt requires a query log.")

    entries = _read_jsonl(art["query_log"])
    prov = _read_yaml(art["cv_yaml"])
    claims = _claims_from_provenance(prov)
    manifest = _read_yaml(art["manifest"])
    state = _read_json(art["state"])
    conn_type, database = _connection_facts(manifest, entries)
    tables = _tables_accessed(entries)

    sec1 = _section_environment(conn_type, database, tables, art["manifest"])
    sec2 = _section_findings(claims, entries, conn_type, database, art["cv_yaml"])
    sec3, vfacts = _section_validation(art["validation"])
    sec4, qfacts = _section_query_log(entries, claims, art["query_log"])
    sec5 = _section_cross_verification(claims, prov, art["cv_yaml"])
    sec6 = _section_pipeline(state, art["state"])
    sec7 = _section_reproduce(conn_type, database, tables, len(claims))

    seeds: list[str] = []
    if art["validation"] is None:
        seeds.append("- Validation report not available: no confidence score backs these findings.")
    elif vfacts.get("grade") in ("C", "D", "F"):
        seeds.append(f"- Validation grade {vfacts['grade']} ({vfacts['score']}/100): the report's recommendations apply before presenting.")
    for r in vfacts.get("recommendations") or []:
        seeds.append(f"- Validation recommendation: {r}")
    if sec5 is None:
        seeds.append("- Cross-verification not performed for this analysis.")
    else:
        for c in claims:
            v = c.get("verification") or {}
            na = [k for k in ("parts_to_whole", "ratio_recompute", "algebraic_identity") if _status_of(v.get(k)) == "N/A"]
            bad = [k for k in ("boundary", "parts_to_whole", "ratio_recompute", "algebraic_identity") if _status_of(v.get(k)) in ("WARN", "FAIL")]
            if bad:
                seeds.append(f"- {_claim_id(c)}: {', '.join(bad)} returned {', '.join(_status_of(v.get(k)) for k in bad)}.")
            if len(na) == 3:
                seeds.append(f"- {_claim_id(c)}: only boundary checks ran (Types B, C, D were N/A).")
            repro = v.get("reproducibility")
            if isinstance(repro, dict) and repro.get("status") in ("WARN", "FAIL"):
                seeds.append(f"- {_claim_id(c)}: reproducibility {repro.get('status')} (variance {repro.get('variance')}).")
    if sec6 is None:
        seeds.append("- Pipeline state not available: execution timing and agent status are not recorded.")
    else:
        for n, a in (state.get("agents") or {}).items():
            if (a or {}).get("status") in ("degraded", "failed"):
                seeds.append(f"- Agent {n} {a['status']}: {a.get('error', 'no error recorded')}.")
    if qfacts["coverage_pct"] is not None and qfacts["coverage_pct"] < 100:
        seeds.append(f"- Query log coverage {qfacts['coverage_pct']:.0f}%: {qfacts['total_claims'] - qfacts['matched']} claim(s) have no backing query.")
    if qfacts["errors"]:
        seeds.append(f"- {qfacts['errors']} logged query(ies) errored; see Section 4.")
    if qfacts["backfilled"]:
        seeds.append(f"- {qfacts['backfilled']} query(ies) were backfilled after the fact rather than logged at execution.")
    if qfacts["total"] > LARGE_LOG_THRESHOLD:
        seeds.append(f"- Section 4 shows {LARGE_LOG_KEEP} of {qfacts['total']} queries.")
    sec8 = _section_caveats(seeds)

    tier = None
    if state and isinstance(state.get("validation_tier"), dict):
        tier = state["validation_tier"].get("selected")
    tier_label = {"tier_1_only": "1 (Quick)", "tier_2": "2 (Standard)", "tier_3": "3 (Deep)"}.get(tier, tier or "not recorded")

    header = "\n".join([
        "# Analysis Receipt",
        "",
        f"**Run ID:** {state.get('run_id') if state and state.get('run_id') else 'not recorded'}",
        f"**Dataset:** {dataset}",
        f"**Question:** {state.get('question') if state and state.get('question') else 'not recorded'}",
        f"**Date:** {date}",
        f"**Validation Tier:** {tier_label}",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} by scripts/build_receipt.py",
    ])

    sections = [header, sec1, sec2, sec3, sec4]
    if sec5:
        sections.append(sec5)
    if sec6:
        sections.append(sec6)
    sections.extend([sec7, sec8])
    markdown = "\n\n---\n\n".join(sections) + "\n"

    facts = {
        "artifacts": {k: (str(v) if v else None) for k, v in art.items()},
        "findings": len(claims),
        "queries": qfacts["total"],
        "cv_claims": len(claims) if sec5 else 0,
        "sections": 8,
        "seeds": len(seeds),
        "grade": vfacts.get("grade"),
        "score": vfacts.get("score"),
    }
    return markdown, facts


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Assemble Sections 1-7 of the analysis receipt from pipeline artifacts.")
    parser.add_argument("--dataset", required=True, help="Dataset name, as used in artifact file names")
    parser.add_argument("--date", required=True, help="Analysis date YYYY-MM-DD, as used in artifact file names")
    parser.add_argument("--run-dir", default=None, help="Pipeline run directory (working/runs/<run>); searched before working/ and outputs/")
    parser.add_argument("--out", default=None, help="Output path (default: outputs/analysis_receipt_<dataset>_<date>.md)")
    parser.add_argument("--query-log", default=None, help="Explicit query log JSONL path")
    parser.add_argument("--validation", default=None, help="Explicit validation report path")
    parser.add_argument("--cv-yaml", default=None, help="Explicit provenance YAML path (cross-verification)")
    parser.add_argument("--cv-md", default=None, help="Explicit cross-verification markdown path")
    parser.add_argument("--state", default=None, help="Explicit pipeline_state.json path")
    parser.add_argument("--manifest", default=None, help="Explicit dataset manifest path")
    args = parser.parse_args(argv)

    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", args.date):
        print("ERROR: --date must be YYYY-MM-DD", file=sys.stderr)
        return 1

    overrides = {
        "query_log": args.query_log, "validation": args.validation, "cv_yaml": args.cv_yaml,
        "cv_md": args.cv_md, "state": args.state, "manifest": args.manifest,
    }
    run_dir = Path(args.run_dir) if args.run_dir else None
    try:
        markdown, facts = build_receipt(args.dataset, args.date, run_dir=run_dir, overrides=overrides)
    except ReceiptError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    out = Path(args.out) if args.out else Path("outputs") / f"analysis_receipt_{args.dataset}_{args.date}.md"
    try:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(markdown)
    except OSError as e:
        print(f"ERROR: could not write {out}: {e}", file=sys.stderr)
        return 2

    missing = [k for k, v in facts["artifacts"].items() if v is None]
    print(f"Receipt skeleton written: {out}")
    print(f"Sections: 1-7 assembled; Section 8 awaits caveats ({facts['seeds']} seed facts listed)")
    print(f"Findings documented: {facts['findings']}")
    print(f"Queries logged: {facts['queries']}")
    print(f"Cross-verification claims: {facts['cv_claims']}")
    if missing:
        print(f"Artifacts not available: {', '.join(missing)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
