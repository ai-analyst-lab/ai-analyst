from __future__ import annotations

import json
import struct
import zlib
from pathlib import Path

import pytest

from helpers.evals.full_analysis import (
    REQUIRED_OUTPUTS,
    compare_runs,
    load_public_case,
    lock_run,
    start_run,
    verify_locked_submission,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CASE_DIR = (
    PROJECT_ROOT
    / "evals"
    / "cases"
    / "public"
    / "novamart-monthly-operating-review-001"
    / "v1"
)
PROMOTION_CASE_DIR = (
    PROJECT_ROOT
    / "evals"
    / "cases"
    / "public"
    / "novamart-promotion-profitability-002"
    / "v1"
)


def png(width: int = 800, height: int = 450) -> bytes:
    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))

    raw = b"".join(b"\x00" + b"\xff\xff\xff" * width for _ in range(height))
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )


def populate(draft: Path, *, count: int = 10) -> None:
    result = {
        "case_id": "novamart-monthly-operating-review-001",
        "period": {"start": "2024-10-01", "end_exclusive": "2025-01-01"},
        "monthly_results": [
            {
                "month": month,
                "completed_order_count": count + index,
                "completed_order_value": 100.0 + index,
                "average_completed_order_value": 10.0,
            }
            for index, month in enumerate(("2024-10", "2024-11", "2024-12"))
        ],
        "october_to_december": {
            "completed_order_count_absolute_change": 2,
            "completed_order_count_percent_change": 20.0,
            "completed_order_value_absolute_change": 2.0,
            "completed_order_value_percent_change": 2.0,
            "average_completed_order_value_absolute_change": 0.0,
            "average_completed_order_value_percent_change": 0.0,
        },
        "final_answer": {
            "conclusion": "The value increased.",
            "recommended_next_step": "Investigate the increase.",
            "supporting_facts": ["Counts increased."],
            "important_limitation": "This is descriptive.",
        },
        "methodology": {
            "analysis_type": "descriptive",
            "population": "Completed orders.",
            "date_field": "order_date",
            "filters": ["status = completed"],
            "calculation_summary": "Monthly count, sum, and average.",
            "validation_checks": [],
            "assumptions": [],
        },
        "artifacts": {
            "monthly_results": "monthly-results.csv",
            "brief": "brief.md",
            "chart": "chart.png",
            "chart_data": "chart-data.csv",
            "calculation": "calculation.sql",
        },
    }
    (draft / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    csv_text = (
        "month,completed_order_count,completed_order_value,average_completed_order_value\n"
        f"2024-10,{count},100.0,10.0\n"
        f"2024-11,{count + 1},101.0,10.0\n"
        f"2024-12,{count + 2},102.0,10.0\n"
    )
    (draft / "monthly-results.csv").write_text(csv_text)
    (draft / "chart-data.csv").write_text(csv_text)
    (draft / "brief.md").write_text("# Review\n\n" + "A complete descriptive operating review. " * 5)
    (draft / "calculation.sql").write_text("SELECT month, COUNT(*) FROM orders GROUP BY month;\n")
    (draft / "chart.png").write_bytes(png())


def attach_analysis(project_root: Path, started: dict, analysis_id: str = "an_test_1234") -> str:
    working = project_root / "working"
    working.mkdir(exist_ok=True)
    record = {
        "analysis_id": analysis_id,
        "dataset": "novamart",
        "output_dir": started["draft_path"],
    }
    (working / "current-analysis.json").write_text(json.dumps(record))
    (working / f"analysis_{analysis_id}.json").write_text(json.dumps(record))
    return analysis_id


def test_public_case_contains_no_private_fields():
    _, case, _ = load_public_case(CASE_DIR)
    assert case["case_id"] == "novamart-monthly-operating-review-001"
    assert tuple(case["required_outputs"]) == REQUIRED_OUTPUTS
    public_text = "\n".join(
        path.read_text(errors="ignore") for path in CASE_DIR.iterdir() if path.is_file()
    )
    for private_value in ("4672", "6048", "6215", "381765.78", "441001.93", "453073.37"):
        assert private_value not in public_text
    for secret_marker in ("SNOWFLAKE_TOKEN=", "SNOWFLAKE_PASSWORD=", "PRIVATE KEY"):
        assert secret_marker not in public_text


def test_start_lock_verify_and_detect_mutation(tmp_path):
    runs_root = tmp_path / "runs"
    started = start_run(project_root=tmp_path, case_dir=CASE_DIR, runs_root=runs_root)
    assert started["analysis_id"] is None
    populate(Path(started["draft_path"]))
    analysis_id = attach_analysis(tmp_path, started)
    locked = lock_run(
        project_root=tmp_path,
        runs_root=runs_root,
        run_id=started["run_id"],
        verify_data_snapshot=False,
        allow_incomplete_trace=True,
    )
    assert locked["trace_complete"] is False
    verified = verify_locked_submission(locked["run_root"] if "run_root" in locked else runs_root / started["run_id"])
    assert verified["bundle_digest"] == locked["bundle_digest"]

    result = Path(verified["submission_path"]) / "result.json"
    result.chmod(0o644)
    result.write_text(result.read_text() + " ")
    with pytest.raises(ValueError, match="locked artifact changed"):
        verify_locked_submission(runs_root / started["run_id"])


def test_verify_detects_locked_trace_mutation(tmp_path):
    runs_root = tmp_path / "runs"
    started = start_run(project_root=tmp_path, case_dir=CASE_DIR, runs_root=runs_root)
    populate(Path(started["draft_path"]))
    analysis_id = "an_trace_mutation"
    working = tmp_path / "working"
    working.mkdir(exist_ok=True)
    attach_analysis(tmp_path, started, analysis_id)
    (working / f"trace_receipt_{analysis_id}.json").write_text(json.dumps({"analysis_id": analysis_id}))
    (working / f"provenance_{analysis_id}.json").write_text(json.dumps({"analysis_id": analysis_id}))
    (Path(started["draft_path"]) / f"trace_{analysis_id}.html").write_text("<html>trace</html>")
    (working / "query_log_test.jsonl").write_text(json.dumps({"analysis_id": analysis_id, "sql": "select 1"}) + "\n")
    (working / "action_log_test.jsonl").write_text(json.dumps({"analysis_id": analysis_id, "action": "query"}) + "\n")
    lock_run(project_root=tmp_path, runs_root=runs_root, run_id=started["run_id"], verify_data_snapshot=False)
    trial_root = next((runs_root / started["run_id"] / "trials").iterdir())
    copied_log = next((trial_root / "trace").glob("action_log_*.jsonl"))
    copied_log.chmod(0o644)
    copied_log.write_text('{"changed":true}\n')
    with pytest.raises(ValueError, match="locked trace artifact changed"):
        verify_locked_submission(runs_root / started["run_id"])


def test_second_case_uses_its_own_output_contract(tmp_path):
    runs_root = tmp_path / "runs"
    started = start_run(project_root=tmp_path, case_dir=PROMOTION_CASE_DIR, runs_root=runs_root)
    draft = Path(started["draft_path"])
    result = {
        "case_id": "novamart-promotion-profitability-002",
        "promotion_results": [
            {
                "promo_name": name,
                "start_date": start,
                "end_date": end,
                "promo_days": days,
                "completed_order_count": count,
                "discounted_merchandise_value": value,
                "merchandise_cost": cost,
                "merchandise_gross_profit": profit,
                "gross_profit_per_day": per_day,
            }
            for name, start, end, days, count, value, cost, profit, per_day in (
                ("Black Friday", "2024-11-25", "2024-12-01", 7, 2387, 117239.0, 86793.53, 30445.47, 4349.35),
                ("Holiday Sale", "2024-12-15", "2024-12-31", 17, 3520, 220071.05, 152784.6, 67286.45, 3958.03),
            )
        ],
        "final_answer": {
            "conclusion": "Holiday Sale led in total profit while Black Friday led per day.",
            "recommended_next_step": "Investigate incremental demand before repeating either promotion.",
            "supporting_facts": ["The rankings differ."],
            "important_limitation": "This descriptive comparison does not prove causation.",
        },
        "methodology": {
            "analysis_type": "descriptive",
            "population": "Completed orders attached to the two promotions.",
            "grain": "One row per promotion.",
            "joins": ["orders to order_items to products and promotions"],
            "calculation_summary": "Merchandise value less product cost, divided by inclusive days.",
            "validation_checks": ["protected order grain"],
            "assumptions": [],
        },
        "artifacts": {
            "promotion_results": "promotion-results.csv",
            "brief": "brief.md",
            "chart": "chart.png",
            "chart_data": "chart-data.csv",
            "calculation": "calculation.sql",
        },
    }
    (draft / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    (draft / "promotion-results.csv").write_text(
        "promo_name,start_date,end_date,promo_days,completed_order_count,discounted_merchandise_value,merchandise_cost,merchandise_gross_profit,gross_profit_per_day\n"
        "Black Friday,2024-11-25,2024-12-01,7,2387,117239.00,86793.53,30445.47,4349.35\n"
        "Holiday Sale,2024-12-15,2024-12-31,17,3520,220071.05,152784.60,67286.45,3958.03\n"
    )
    (draft / "chart-data.csv").write_text(
        "promo_name,merchandise_gross_profit,gross_profit_per_day\n"
        "Black Friday,30445.47,4349.35\nHoliday Sale,67286.45,3958.03\n"
    )
    (draft / "brief.md").write_text("# Promotion review\n\n" + "A complete descriptive comparison. " * 5)
    (draft / "calculation.sql").write_text("SELECT promo_name FROM promotions;\n")
    (draft / "chart.png").write_bytes(png())
    analysis_id = attach_analysis(tmp_path, started, "an_promotion")
    locked = lock_run(
        project_root=tmp_path,
        runs_root=runs_root,
        run_id=started["run_id"],
        analysis_id=analysis_id,
        verify_data_snapshot=False,
        allow_incomplete_trace=True,
    )
    assert locked["bundle_digest"]
    assert "promotion-results.csv" in (Path(started["instructions_path"])).read_text()
    assert "monthly-results.csv" not in (Path(started["instructions_path"])).read_text()


def test_lock_refuses_incomplete_bundle(tmp_path):
    runs_root = tmp_path / "runs"
    started = start_run(project_root=tmp_path, case_dir=CASE_DIR, runs_root=runs_root)
    populate(Path(started["draft_path"]))
    analysis_id = attach_analysis(tmp_path, started)
    (Path(started["draft_path"]) / "chart.png").unlink()
    with pytest.raises(ValueError, match="missing=.*chart.png"):
        lock_run(
            project_root=tmp_path,
            runs_root=runs_root,
            run_id=started["run_id"],
            analysis_id=analysis_id,
            verify_data_snapshot=False,
            allow_incomplete_trace=True,
        )


def test_lock_refuses_incomplete_trace_by_default(tmp_path):
    runs_root = tmp_path / "runs"
    started = start_run(project_root=tmp_path, case_dir=CASE_DIR, runs_root=runs_root)
    populate(Path(started["draft_path"]))
    attach_analysis(tmp_path, started)
    with pytest.raises(ValueError, match="trace is incomplete"):
        lock_run(
            project_root=tmp_path,
            runs_root=runs_root,
            run_id=started["run_id"],
            verify_data_snapshot=False,
        )


def test_lock_captures_trace_evidence_by_analysis_id(tmp_path):
    runs_root = tmp_path / "runs"
    started = start_run(project_root=tmp_path, case_dir=CASE_DIR, runs_root=runs_root)
    populate(Path(started["draft_path"]))
    analysis_id = "an_test_1234"
    working = tmp_path / "working"
    output_dir = Path(started["draft_path"])
    attach_analysis(tmp_path, started, analysis_id)
    (working / f"trace_receipt_{analysis_id}.json").write_text(json.dumps({"analysis_id": analysis_id}))
    (working / f"provenance_{analysis_id}.json").write_text(json.dumps({"analysis_id": analysis_id}))
    (output_dir / f"trace_{analysis_id}.html").write_text("<html>trace</html>")
    (working / "query_log_novamart_2026-09-21.jsonl").write_text(
        json.dumps({"analysis_id": analysis_id, "sql": "select 1"}) + "\n"
    )
    (working / "action_log_2026-09-21.jsonl").write_text(
        json.dumps({"analysis_id": analysis_id, "action": "query"}) + "\n"
    )
    locked = lock_run(
        project_root=tmp_path,
        runs_root=runs_root,
        run_id=started["run_id"],
        verify_data_snapshot=False,
    )
    assert locked["trace_complete"] is True
    trial = next((runs_root / started["run_id"] / "trials").iterdir())
    trace_manifest = json.loads((trial / "trace" / "manifest.json").read_text())
    assert {row["path"] for row in trace_manifest["files"]} >= {
        f"analysis_{analysis_id}.json",
        f"query_log_{analysis_id}.jsonl",
        f"action_log_{analysis_id}.jsonl",
        f"trace_receipt_{analysis_id}.json",
        f"provenance_{analysis_id}.json",
        f"trace_{analysis_id}.html",
    }


def test_development_run_links_to_baseline_and_compares(tmp_path):
    runs_root = tmp_path / "runs"
    before = start_run(project_root=tmp_path, case_dir=CASE_DIR, runs_root=runs_root)
    populate(Path(before["draft_path"]))
    before_analysis_id = attach_analysis(tmp_path, before, "an_test_before")
    lock_run(
        project_root=tmp_path,
        runs_root=runs_root,
        run_id=before["run_id"],
        analysis_id=before_analysis_id,
        verify_data_snapshot=False,
        allow_incomplete_trace=True,
    )
    before_trial = next((runs_root / before["run_id"] / "trials").iterdir())
    (before_trial / "grades").mkdir()
    (before_trial / "grades" / "summary.json").write_text(
        json.dumps({"output_contract": 1, "deterministic_accuracy": 0, "final_answer_judge": 0, "case_pass": 0})
    )

    after = start_run(
        project_root=tmp_path,
        case_dir=CASE_DIR,
        runs_root=runs_root,
        baseline_run_id=before["run_id"],
        intended_change="Clarify the calculation method.",
    )
    populate(Path(after["draft_path"]))
    after_analysis_id = attach_analysis(tmp_path, after, "an_test_after")
    lock_run(
        project_root=tmp_path,
        runs_root=runs_root,
        run_id=after["run_id"],
        analysis_id=after_analysis_id,
        verify_data_snapshot=False,
        allow_incomplete_trace=True,
    )
    after_trial = next((runs_root / after["run_id"] / "trials").iterdir())
    (after_trial / "grades").mkdir()
    (after_trial / "grades" / "summary.json").write_text(
        json.dumps({"output_contract": 1, "deterministic_accuracy": 1, "final_answer_judge": 1, "case_pass": 1})
    )
    comparison = compare_runs(
        runs_root=runs_root,
        before_run_id=before["run_id"],
        after_run_id=after["run_id"],
    )
    assert comparison["gates"]["case_pass"] == {"before": 0, "after": 1}
    assert comparison["intended_change"] == "Clarify the calculation method."
