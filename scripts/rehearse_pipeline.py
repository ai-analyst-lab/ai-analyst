"""Prepare and assess a bounded, real-data controller rehearsal.

This uses the existing descriptive and validation worker instructions, with an
explicit two-worker test contract. It is not proof of all built-in plans or of
natural-language routing. Preparation executes SQL, not a model. Execution is a
separate, explicit command using the normal Claude Code account and permissions.
"""
from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import sys
import time

import duckdb

from helpers.pipeline.controller import ClaudeCLI, Controller, PipelineError, digest
from helpers.pipeline.compile_plan import compile_named_plan


SQL = """
SELECT strftime(order_date, '%Y-%m') AS month,
       count(*) AS completed_orders,
       round(sum(total_amount), 2) AS total_amount_sum
FROM orders
WHERE status = 'completed'
  AND order_date >= DATE '2024-10-01'
  AND order_date < DATE '2025-01-01'
GROUP BY 1 ORDER BY 1
"""

BRIEF = """# Monthly completed-order review

Summarize October, November and December 2024 in the supplied NovaMart practice
database. Use orders with status exactly 'completed' and order_date from
2024-10-01 inclusive to 2025-01-01 exclusive. Report completed order count and
the sum of total_amount, rounded to two decimal places, for each month. Treat
these as specified exercise measures, not an approved company revenue definition.

Produce one readable completed-order count bar chart, a report under 400 words
(count all whitespace-delimited words in the entire report file, including tables),
a data-readiness note, reproducible
Python containing the SQL, and numeric_results JSON. The JSON is an object with
a 'months' list. Each row has month (YYYY-MM), completed_orders (integer), and
total_amount_sum (number). Explain the observed differences without causal claims.
Do not run experiments, causal models, or an unrelated full investigation. Do not
add promotional breakdowns, other segments or earlier comparison periods. Show
amounts in the report rather than adding a second vertical axis to the chart.

Use the assigned input database read-only. Review the relevant schema before
querying. Save your actual calculations as the analysis-code output. The script
must accept the database path as its first argument and print the calculated
monthly result. Keep temporary files inside the assigned attempt directory.
"""


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def file_input(path, purpose):
    return {"path": str(path.resolve()), "sha256": digest(path), "purpose": purpose}


def prepare(root, database):
    database = database.resolve()
    with duckdb.connect(str(database), read_only=True) as connection:
        columns = [col[0] for col in connection.execute(SQL).description]
        expected = [dict(zip(columns, row)) for row in connection.fetchall()]
    if len(expected) != 3:
        raise PipelineError("Expected three populated months; inspect the dataset")
    evidence = root / "working/verification" / ("rehearsal-" + str(time.time_ns()))
    evidence.mkdir(parents=True)
    brief = evidence / "request.md"
    brief.write_text(BRIEF)
    definition = {
        "name": "bounded-monthly-review-rehearsal",
        "execution_mode": "isolated", "max_attempts": 1,
        "deliverables": ["analysis.result", "review.result", "review.verdict"],
        "workers": {
            "analysis": {
                "file": "agents/pipeline/descriptive-analytics.md",
                "inputs": {"DATASET": {"type": "file"}, "QUESTION_BRIEF": {"type": "file"},
                           "FOCUS_AREA": {}},
                "outputs": {"result": "report.md", "chart": "monthly-orders.png",
                            "readiness": "readiness.md", "artifact_4": "analysis.py",
                            "numeric_results": "monthly-results.json"},
                "output_checks": {"result": {"max_words": 400}},
            },
            "review": {
                "file": "agents/pipeline/validation.md",
                "inputs": {"ANALYSIS_CODE": {"from": "analysis.artifact_4"},
                           "ANALYSIS_RESULTS": {"from": "analysis.result"},
                           "DATA_SOURCE": {"type": "file"},
                           "QUESTION_BRIEF": {"type": "file"},
                           "CHART": {"from": "analysis.chart"},
                           "VALIDATION_SCOPE": {}},
                "outputs": {"result": "review.md", "verdict": "verdict.json"},
                "output_checks": {"verdict": {"equals": {
                    "verdict": "pass", "request_adherence": "pass", "chart_review": "pass"}}},
            },
        },
    }
    inputs = {
        "analysis": {"DATASET": file_input(database, "Specified exercise database, read-only"),
                     "FOCUS_AREA": "summary",
                     "QUESTION_BRIEF": file_input(brief, "Fixed three-month descriptive question")},
        "review": {"DATA_SOURCE": file_input(database, "Re-derive the reported monthly measures"),
                   "QUESTION_BRIEF": file_input(brief, "Acceptance requirements for the complete deliverable"),
                   "VALIDATION_SCOPE": "Verify the complete deliverable against the original brief, including "
                       "the actual chart image, scope boundaries and absence of unsupported causal claims. "
                       "Verify the three monthly counts and sums against the database. "
                       "Inspect the calculation and independently re-derive the numbers. "
                       "Do not treat a matching chart as verification. Do not edit upstream artifacts."},
    }
    c = Controller.create(root, definition, inputs)
    record = {"run_dir": str(c.directory), "status": "prepared_not_executed",
              "database_sha256": digest(database), "question": BRIEF,
              "expected": expected, "reference_sql": SQL,
              "scope": "Two canonical worker instructions in a bounded test contract, not a built-in plan"}
    # The reference answer is not supplied to either worker. Local filesystem
    # access is not a blind-evaluation security boundary.
    write_json(evidence / "rehearsal.json", record)
    print(evidence / "rehearsal.json")


def prepare_rejection(root, previous_record):
    previous = json.loads(previous_record.read_text())
    old = Controller.open(previous["run_dir"])
    old.verify(check_current_definitions=False)
    evidence = root / "working/verification" / ("rejection-" + str(time.time_ns()))
    evidence.mkdir(parents=True)
    request = {"plan": "validate_only", "variables": {"DATASET_NAME": "novamart", "DATE": "2026-09-06"},
        "bindings": {"validation": {
            "ANALYSIS_CODE": file_input(Path(old.artifact("analysis.artifact_4")["path"]), "Original executable calculation"),
            "ANALYSIS_RESULTS": file_input(Path(old.artifact("analysis.result")["path"]), "Original captured report to review"),
            "CHART": file_input(Path(old.artifact("analysis.chart")["path"]), "Original captured chart to review"),
            "DATA_SOURCE": file_input(Path(old.state["inputs"]["analysis"]["DATASET"]), "Original analytical data"),
            "QUESTION_BRIEF": file_input(Path(old.state["inputs"]["analysis"]["QUESTION_BRIEF"]), "Original acceptance requirements"),
            "VALIDATION_SCOPE": "Compare the deliverable with the original brief first. "
                "If you establish a material failure, explain it with precise references and stop; "
                "do not perform an unnecessary exhaustive numeric review or invent a confidence grade. "
                "Otherwise review the actual chart and independently verify the numerical claims. "
                "Never edit the supplied report, chart, or code."}}}
    definition, inputs = compile_named_plan(root, request)
    c = Controller.create(root, definition, inputs)
    write_json(evidence / "request.json", request)
    write_json(evidence / "rehearsal.json", {"run_dir": str(c.directory),
        "status": "prepared_not_executed", "expected_rejection": True,
        "scope": "Real validate_only plan must reject a captured out-of-scope causal claim"})
    print(evidence / "rehearsal.json")


def assess(record):
    c = Controller.open(record["run_dir"])
    c.verify(check_current_definitions=False)
    if record.get("expected_rejection"):
        entry = c.state["agents"]["validation"]
        rejected = entry.get("rejected_artifacts", {}).get("artifact_2")
        verdict = json.loads(Path(rejected["path"]).read_text()) if rejected else {}
        return {"passed": c.state["status"] == "failed" and verdict.get("verdict") == "fail",
                "scope": record["scope"], "expected_rejection": True,
                "status": c.state["status"], "verdict": verdict,
                "remaining_review": "Confirm the rejection identifies the actual defect, not an unrelated failure."}
    artifact = c.artifact("analysis.numeric_results")
    if not artifact:
        return {"passed": False, "reason": "No accepted numerical analysis artifact", "status": c.state["status"]}
    actual = json.loads(Path(artifact["path"]).read_text()).get("months", [])
    expected = record["expected"]
    matches = len(actual) == len(expected)
    for got, want in zip(actual, expected):
        matches = matches and got.get("month") == want["month"]
        matches = matches and type(got.get("completed_orders")) is int and got["completed_orders"] == want["completed_orders"]
        total = got.get("total_amount_sum")
        matches = matches and isinstance(total, (int, float)) and math.isclose(total, want["total_amount_sum"], abs_tol=0.005, rel_tol=0)
    return {"passed": bool(matches and c.state["status"] == "completed"),
            "status": c.state["status"], "numeric_reference_match": bool(matches),
            "actual": actual, "expected": expected,
            "remaining_review": "Inspect report claims, chart legibility, code and actual tool trace. "
                                "This does not establish repeated reliability or routing correctness."}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    commands = p.add_subparsers(dest="command", required=True)
    prep = commands.add_parser("prepare")
    prep.add_argument("database", type=Path)
    prep.add_argument("--root", type=Path, default=Path.cwd())
    rejection = commands.add_parser("prepare-rejection")
    rejection.add_argument("previous_record", type=Path)
    rejection.add_argument("--root", type=Path, default=Path.cwd())
    for name in ("run", "assess"):
        command = commands.add_parser(name)
        command.add_argument("record", type=Path)
        if name == "run":
            command.add_argument("--retry-failed", action="store_true",
                                 help="Explicitly resume failed/blocked jobs while preserving completed artifacts")
            command.add_argument("--allow-local-python", action="store_true")
            command.add_argument("--fresh-permissions", action="store_true",
                                 help="Test with no user/project/local settings; managed policy still applies")
    args = p.parse_args()
    if args.command == "prepare":
        prepare(args.root.resolve(), args.database)
        return
    if args.command == "prepare-rejection":
        prepare_rejection(args.root.resolve(), args.previous_record)
        return
    record = json.loads(args.record.read_text())
    if args.command == "run":
        start = time.monotonic()
        # Workers use the same installed dependencies as the rehearsal driver.
        os.environ["PATH"] = str(Path(sys.executable).parent) + os.pathsep + os.environ.get("PATH", "")
        state = Controller.open(record["run_dir"]).execute(ClaudeCLI(
            allow_local_python=args.allow_local_python,
            setting_sources="" if args.fresh_permissions else None), retry_failed=args.retry_failed)
        elapsed = round(time.monotonic() - start, 2)
        attempts = record.setdefault("execution_attempts", [])
        if not attempts and record.get("elapsed_seconds") is not None:
            attempts.append({"status": record.get("status"),
                             "elapsed_seconds": record["elapsed_seconds"],
                             "note": "Prior execution, preserved when resuming"})
        attempts.append({"status": state["status"], "elapsed_seconds": elapsed,
                         "retry_failed": args.retry_failed,
                         "fresh_permissions": args.fresh_permissions,
                         "allow_local_python": args.allow_local_python})
        record.update(status=state["status"], elapsed_seconds=sum(a["elapsed_seconds"] for a in attempts))
        write_json(args.record, record)
    result = assess(record)
    write_json(args.record.parent / "assessment.json", result)
    print(json.dumps(result, indent=2))
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
