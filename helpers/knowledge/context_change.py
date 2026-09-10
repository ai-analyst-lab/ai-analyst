"""Create an evidence-backed receipt for a context change."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from helpers.evals.comparison import compare_manifests


def _case_outcome(case: dict[str, Any]) -> bool | None:
    value = case.get("blocking_pass")
    return value if isinstance(value, bool) else None


def build_context_change_receipt(
    baseline: dict[str, Any],
    candidate: dict[str, Any],
    *,
    changed_paths: list[str],
    change_summary: str,
    context_before: str | None = None,
    context_after: str | None = None,
    target_case_ids: list[str] | None = None,
    context_use_evidence: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    comparison = compare_manifests(baseline, candidate)
    baseline_cases = baseline.get("case_summary", {})
    candidate_cases = candidate.get("case_summary", {})
    all_cases = sorted(set(baseline_cases) | set(candidate_cases))
    improved: list[str] = []
    regressed: list[str] = []
    unchanged_pass: list[str] = []
    unchanged_fail: list[str] = []
    ungradeable: list[str] = []

    for case_id in all_cases:
        before = _case_outcome(baseline_cases.get(case_id, {}))
        after = _case_outcome(candidate_cases.get(case_id, {}))
        if before is False and after is True:
            improved.append(case_id)
        elif before is True and after is False:
            regressed.append(case_id)
        elif before is True and after is True:
            unchanged_pass.append(case_id)
        elif before is False and after is False:
            unchanged_fail.append(case_id)
        else:
            ungradeable.append(case_id)

    targets = sorted(set(target_case_ids or []))
    improved_set = set(improved)
    missing_targets = [case_id for case_id in targets if case_id not in all_cases]
    targets_improved = bool(targets) and not missing_targets and all(
        case_id in improved_set for case_id in targets
    )

    if not comparison["comparable"]:
        decision = "revise"
        reason = "The runs are not comparable, so the score movement cannot be attributed to this context change."
    elif regressed:
        decision = "revert"
        reason = "At least one previously passing case regressed and needs explanation before promotion."
    elif targets and not targets_improved:
        decision = "revise"
        reason = "One or more named target cases did not move from failing to passing."
    elif improved and targets:
        decision = "accept"
        reason = "Target cases improved, no passing case regressed, and the comparison remained controlled."
    elif improved:
        decision = "accept"
        reason = "At least one failing case improved, no passing case regressed, and the comparison remained controlled."
    else:
        decision = "revise"
        reason = "The controlled change did not improve a failing case."

    context_diff = {
        "before": context_before,
        "after": context_after,
        "changed": context_before != context_after if context_before or context_after else None,
    }
    digest = hashlib.sha256(
        json.dumps(
            {
                "baseline": baseline.get("run_id"),
                "candidate": candidate.get("run_id"),
                "changed_paths": sorted(changed_paths),
                "summary": change_summary,
            },
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()
    return {
        "schema_version": "1.0",
        "receipt_id": f"context-change-{digest[:12]}",
        "baseline_run_id": baseline.get("run_id"),
        "candidate_run_id": candidate.get("run_id"),
        "change_summary": change_summary,
        "changed_paths": sorted(changed_paths),
        "context_fingerprint": context_diff,
        "comparison": comparison,
        "improved_cases": improved,
        "regressed_cases": regressed,
        "unchanged_passing_cases": unchanged_pass,
        "unchanged_failing_cases": unchanged_fail,
        "ungradeable_cases": ungradeable,
        "target_cases": targets,
        "missing_target_cases": missing_targets,
        "all_target_cases_improved": targets_improved if targets else None,
        "context_use_evidence": context_use_evidence or [],
        "decision": decision,
        "decision_reason": reason,
        "limitations": [
            "An evaluation result supports a promotion decision only for the reviewed cases and configuration tested.",
            "Domain review is still required for claims about business meaning.",
        ],
    }


def render_context_change_receipt(receipt: dict[str, Any]) -> str:
    def bullets(values: list[str]) -> str:
        return "\n".join(f"- `{value}`" for value in values) if values else "- None"

    compatible = "yes" if receipt["comparison"]["comparable"] else "no"
    return f"""# Context change receipt

## Decision

**{receipt['decision'].upper()}**

{receipt['decision_reason']}

## Change

{receipt['change_summary']}

Changed files:

{bullets(receipt['changed_paths'])}

## Comparison

- Baseline run: `{receipt['baseline_run_id']}`
- Candidate run: `{receipt['candidate_run_id']}`
- Comparable: {compatible}
- Context fingerprint before: `{receipt['context_fingerprint']['before']}`
- Context fingerprint after: `{receipt['context_fingerprint']['after']}`
- Actual system files changed: {', '.join(receipt['comparison']['changed_system_paths']) or 'None'}
- Unapproved system files changed: {', '.join(receipt['comparison']['unapproved_system_changes']) or 'None'}

## Named target cases

{bullets(receipt['target_cases'])}

## Improved cases

{bullets(receipt['improved_cases'])}

## Regressed cases

{bullets(receipt['regressed_cases'])}

## Unchanged passing cases

{bullets(receipt['unchanged_passing_cases'])}

## Still failing

{bullets(receipt['unchanged_failing_cases'])}

## Ungradeable cases

{bullets(receipt['ungradeable_cases'])}

## Context-use evidence

{bullets([str(value) for value in receipt['context_use_evidence']])}

## Limitations

{bullets(receipt['limitations'])}
"""


def write_context_change_receipt(receipt: dict[str, Any], output: str | Path) -> tuple[Path, Path]:
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    json_path = output.with_suffix(".json")
    md_path = output.with_suffix(".md")
    json_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(render_context_change_receipt(receipt), encoding="utf-8")
    return json_path, md_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build an evidence-backed context change receipt")
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--changed-path", action="append", default=[])
    parser.add_argument("--summary", required=True)
    parser.add_argument("--context-before")
    parser.add_argument("--context-after")
    parser.add_argument("--target-case", action="append", default=[])
    parser.add_argument("--context-use", action="append", default=[])
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    baseline = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
    candidate = json.loads(Path(args.candidate).read_text(encoding="utf-8"))
    context_use = [json.loads(Path(path).read_text(encoding="utf-8")) for path in args.context_use]
    receipt = build_context_change_receipt(
        baseline,
        candidate,
        changed_paths=args.changed_path,
        change_summary=args.summary,
        context_before=args.context_before,
        context_after=args.context_after,
        target_case_ids=args.target_case,
        context_use_evidence=context_use,
    )
    json_path, md_path = write_context_change_receipt(receipt, args.output)
    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")
    return 0 if receipt["decision"] == "accept" else 2


if __name__ == "__main__":
    raise SystemExit(main())
