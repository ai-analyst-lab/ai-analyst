#!/usr/bin/env python3
"""Small CLI for the lifecycle of an interactive analysis trace."""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from helpers.knowledge.analysis_context import current_analysis, start_analysis
from helpers.knowledge.findings import record_finding
from helpers.provenance.trace_viewer import build_trace


def _start(args) -> int:
    aid = start_analysis(
        question=args.question,
        intended_decision=args.decision,
        dataset=args.dataset,
        output_dir=args.output_dir,
    )
    print(json.dumps(current_analysis(), indent=2))
    return 0


def _record(args) -> int:
    finding = record_finding(
        args.value,
        args.text,
        query_ids=args.query_id,
        analysis_id=args.analysis_id,
        kind=args.kind,
        calculation=args.calculation,
        source_finding_ids=args.source_finding_id,
    )
    print(json.dumps(finding, indent=2))
    return 0


def _build(args) -> int:
    record = current_analysis() or {}
    aid = args.analysis_id or record.get("analysis_id")
    dataset = args.dataset or record.get("dataset")
    if not aid or not dataset:
        raise SystemExit("analysis_id and dataset are required")
    output_dir = Path(args.output_dir or record.get("output_dir") or "working")
    output_dir.mkdir(parents=True, exist_ok=True)
    out = output_dir / f"trace_{aid}.html"
    html_path = build_trace(aid, dataset, args.date, out_path=out)
    result = {
        "analysis_id": aid,
        "html": html_path,
        "provenance": f"working/provenance_{aid}.json",
        "receipt": f"working/trace_receipt_{aid}.json",
    }
    print(json.dumps(result, indent=2))
    return 0


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)

    start = sub.add_parser("start", help="start a fresh analysis boundary")
    start.add_argument("--question", required=True)
    start.add_argument("--decision", required=True)
    start.add_argument("--dataset", required=True)
    start.add_argument("--output-dir", required=True)
    start.set_defaults(func=_start)

    finding = sub.add_parser("record-finding", help="link one reported value to evidence")
    finding.add_argument("--analysis-id", required=True)
    finding.add_argument("--value", required=True)
    finding.add_argument("--text", required=True)
    finding.add_argument("--query-id", action="append", default=[])
    finding.add_argument("--kind", default="reported", choices=("reported", "derived"))
    finding.add_argument("--calculation")
    finding.add_argument("--source-finding-id", action="append", default=[])
    finding.set_defaults(func=_record)

    build = sub.add_parser("build", help="build and share the trace HTML")
    build.add_argument("--analysis-id")
    build.add_argument("--dataset")
    build.add_argument("--date", default=date.today().isoformat())
    build.add_argument("--output-dir")
    build.set_defaults(func=_build)
    return p


def main() -> int:
    args = parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
