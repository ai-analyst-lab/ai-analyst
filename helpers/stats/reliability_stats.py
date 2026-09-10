#!/usr/bin/env python3
"""Compatibility CLI for the shared evaluation reliability engine.

Usage:
    python3 helpers/stats/reliability_stats.py <run_dir>

New workflows should use ``helpers.evals.reliability`` directly. This wrapper
keeps earlier skills and saved exercises working while producing the stronger
Week 3 record.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from helpers.evals.normalization import normalize_number
from helpers.evals.reliability import measure_reliability
from helpers.evals.reports import render_reliability


def parse_number(headline):
    return normalize_number(headline).value


def compute(runs, *, unit_hint=None, absolute_tolerance=None, relative_tolerance=None):
    report = measure_reliability(
        runs,
        unit_hint=unit_hint,
        absolute_tolerance=absolute_tolerance,
        relative_tolerance=relative_tolerance,
    )
    distribution = report.get("distribution") or {}
    exact = report["exact_agreement"]
    old_verdict = {
        "exactly_stable": "STABLE",
        "stable_within_tolerance": "STABLE",
        "variable": "DRIFT",
        "unknown": "UNKNOWN",
    }[report["verdict"]]
    return {
        **report,
        "n": report["requested_trials"],
        "n_numeric": report["successful_trials"],
        "headlines": [row.get("headline") for row in runs],
        "mean": distribution.get("mean"),
        "stdev": distribution.get("stdev"),
        "cv": distribution.get("cv"),
        "min": distribution.get("minimum"),
        "max": distribution.get("maximum"),
        "range": distribution.get("range"),
        "distinct_values": distribution.get("distinct", []),
        "n_distinct": len(distribution.get("distinct", [])),
        "agreements": exact["count"],
        "differences": report["successful_trials"] - exact["count"],
        "agreement_rate": exact["rate"],
        "used_dictionary": sum(
            "dictionary" in str(row.get("definition_source") or "").casefold() for row in runs
        ),
        "verdict": old_verdict,
    }


def write_report(run_dir, question, runs, stats):
    report = dict(stats)
    report["question"] = question
    return render_reliability(report, Path(run_dir) / "report.md")


def main():
    run_dir = Path(sys.argv[1])
    payload = json.loads((run_dir / "runs.json").read_text(encoding="utf-8"))
    question = payload.get("question", "(unknown)")
    tolerance = payload.get("decision_tolerance", {})
    stats = compute(
        payload.get("runs", []),
        unit_hint=tolerance.get("unit"),
        absolute_tolerance=tolerance.get("absolute"),
        relative_tolerance=tolerance.get("relative"),
    )
    stats["question"] = question
    stats["computed_at"] = datetime.now(timezone.utc).isoformat()
    (run_dir / "stats.json").write_text(json.dumps(stats, indent=2) + "\n", encoding="utf-8")
    write_report(run_dir, question, payload.get("runs", []), stats)

    log_dir = Path(".knowledge/reliability")
    log_dir.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": stats["computed_at"],
        "question": question,
        "requested": stats["requested_trials"],
        "successful": stats["successful_trials"],
        "verdict": stats["verdict"],
        "exact_agreement_rate": stats["exact_agreement"]["rate"],
        "tolerance_agreement_rate": stats["tolerance_agreement"]["rate"],
        "dir": str(run_dir),
    }
    with (log_dir / "log.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry) + "\n")
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
