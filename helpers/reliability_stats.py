#!/usr/bin/env python3
"""Deterministic reliability statistics from N independent runs.

Usage:
    python3 helpers/reliability_stats.py <run_dir>

Expects <run_dir>/runs.json shaped like:
    {"question": "...", "runs": [
        {"run": 1, "headline": "25.3%", "measured": "...", "definition_source": "..."},
        ...
    ]}

Writes <run_dir>/stats.json and <run_dir>/report.md, and appends one line to
.knowledge/reliability/log.jsonl so every reliability check is tracked and auditable.
The numbers are computed here (deterministically), never estimated by the model.
"""
import json
import re
import sys
import statistics
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


def parse_number(headline):
    """Pull the leading numeric value out of a headline like '25.3%', '$3.15M', '1,409'."""
    if headline is None:
        return None
    text = str(headline).replace(",", "")
    m = re.search(r"-?\d+(?:\.\d+)?", text)
    if not m:
        return None
    value = float(m.group())
    suffix = text[m.end():m.end() + 1].lower()
    if suffix == "k":
        value *= 1e3
    elif suffix == "m":
        value *= 1e6
    elif suffix == "b":
        value *= 1e9
    return value


def compute(runs):
    n = len(runs)
    headlines = [r.get("headline") for r in runs]
    nums = [v for v in (parse_number(h) for h in headlines) if v is not None]
    stats = {"n": n, "n_numeric": len(nums), "headlines": headlines}

    if nums:
        mean = statistics.fmean(nums)
        sd = statistics.pstdev(nums) if len(nums) > 1 else 0.0
        rounded = [round(v, 4) for v in nums]
        counts = Counter(rounded)
        modal_value, modal_count = counts.most_common(1)[0]
        rel_range = (max(nums) - min(nums)) / abs(mean) if mean else (0.0 if len(set(rounded)) == 1 else 1.0)
        converged = len(set(rounded)) == 1 or rel_range <= 0.02
        stats.update({
            "mean": round(mean, 4),
            "stdev": round(sd, 4),
            "cv": round(sd / mean, 4) if mean else None,   # coefficient of variation
            "min": min(nums),
            "max": max(nums),
            "range": round(max(nums) - min(nums), 4),
            "rel_range": round(rel_range, 4),
            "distinct_values": sorted(set(rounded)),
            "n_distinct": len(set(rounded)),
            "agreements": modal_count,            # runs sharing the most common value
            "differences": n - modal_count,
            "agreement_rate": round(modal_count / n, 3),
            "verdict": "STABLE" if converged else "DRIFT",
        })
    else:
        stats["verdict"] = "UNKNOWN"   # no parseable numbers

    sources = [str(r.get("definition_source") or "").strip().lower() for r in runs]
    stats["used_dictionary"] = sum(1 for s in sources if "dictionary" in s)
    return stats


def write_report(run_dir, question, runs, stats):
    lines = [f"# Reliability report", "", f"**Question:** {question}",
             f"**Runs:** {stats['n']}  ·  **Verdict:** {stats['verdict']}", ""]
    if stats.get("verdict") in ("STABLE", "DRIFT"):
        lines += [
            f"- distinct values: {stats['n_distinct']}  ({', '.join(str(v) for v in stats['distinct_values'])})",
            f"- agreements: {stats['agreements']} / {stats['n']}  (agreement rate {stats['agreement_rate']})",
            f"- differences: {stats['differences']}",
            f"- mean {stats['mean']}  ·  stdev {stats['stdev']}  ·  CV {stats['cv']}  ·  range {stats['range']} (rel {stats['rel_range']})",
            f"- used metric dictionary: {stats['used_dictionary']} / {stats['n']} runs",
            "",
        ]
    lines += ["| Run | Headline | What it measured | Source |", "|---|---|---|---|"]
    for r in runs:
        lines.append(f"| {r.get('run')} | {r.get('headline','')} | {str(r.get('measured','')).replace('|','/')} | {r.get('definition_source','')} |")
    lines += ["", "_Stability is necessary, not sufficient: a wrong query is perfectly stable. "
              "N is illustrative; this check needs no answer key and is nearly free when the runs are genuinely independent._"]
    (run_dir / "report.md").write_text("\n".join(lines))


def main():
    run_dir = Path(sys.argv[1])
    payload = json.loads((run_dir / "runs.json").read_text())
    question = payload.get("question", "(unknown)")
    runs = payload.get("runs", [])
    stats = compute(runs)
    stats["question"] = question
    stats["computed_at"] = datetime.now(timezone.utc).isoformat()
    (run_dir / "stats.json").write_text(json.dumps(stats, indent=2))
    write_report(run_dir, question, runs, stats)

    # Append to the audit log (tracked over time).
    log_dir = Path(".knowledge/reliability")
    log_dir.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": stats["computed_at"], "question": question, "n": stats["n"],
        "verdict": stats["verdict"], "cv": stats.get("cv"), "n_distinct": stats.get("n_distinct"),
        "agreement_rate": stats.get("agreement_rate"), "dir": str(run_dir),
    }
    with (log_dir / "log.jsonl").open("a") as f:
        f.write(json.dumps(entry) + "\n")

    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
