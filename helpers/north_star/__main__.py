"""CLI wrappers for /north-star helpers — invoked from SKILL.md dispatcher.

Usage:
    python -m helpers.north_star refusal "<candidate>"           # check refusal
    python -m helpers.north_star refusal --stdin                  # read candidate from stdin
    python -m helpers.north_star classify-vertical "<desc>" "<industry>" "<biz_model>"
    python -m helpers.north_star calibration <vertical_id> <verb>
    python -m helpers.north_star case-lookup <vertical_id> [--limit N]
    python -m helpers.north_star checklist                         # dump rubric as JSON

Output is JSON on stdout for easy parsing by the dispatcher. Errors go to stderr
with non-zero exit code.

Why a CLI: SKILL.md is markdown that Claude executes via Bash tool. Single-quoted
`python -c "..."` invocations break on candidates with quotes/backslashes/newlines.
A subcommand CLI with --stdin support handles arbitrary input safely.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from enum import Enum
from types import MappingProxyType
from typing import Any


def _serialize(obj: Any) -> Any:
    """JSON-serialize dataclasses, enums, MappingProxyType, etc.

    Walks the tree manually instead of using dataclasses.asdict() because asdict
    does a deepcopy that fails on MappingProxyType (used by ConfidenceEnvelope
    to make `source` tamper-resistant).
    """
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {f.name: _serialize(getattr(obj, f.name)) for f in dataclasses.fields(obj)}
    if isinstance(obj, MappingProxyType):
        return {k: _serialize(v) for k, v in obj.items()}
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [_serialize(v) for v in obj]
    if isinstance(obj, Enum):
        return obj.value
    return obj


def _cmd_refusal(args: argparse.Namespace) -> int:
    from helpers.north_star.refusal import check
    candidate = sys.stdin.read() if args.stdin else (args.candidate or "")
    result = check(candidate)
    print(json.dumps(_serialize(result), default=str))
    return 0 if not result.refused else 0  # exit 0 either way; refusal is data, not failure


def _cmd_classify_vertical(args: argparse.Namespace) -> int:
    from helpers.north_star.vertical_classifier import classify
    profile = classify(
        product_description=args.description,
        stated_industry=args.industry,
        business_model=args.business_model,
    )
    print(json.dumps(_serialize(profile), default=str))
    return 0


def _cmd_calibration(args: argparse.Namespace) -> int:
    from helpers.north_star.vertical_classifier import calibration_for
    cov = calibration_for(args.vertical_id, args.verb)
    print(json.dumps(_serialize(cov), default=str))
    return 0


def _cmd_case_lookup(args: argparse.Namespace) -> int:
    from helpers.north_star.case_lookup import lookup
    cases = lookup(
        game=args.game,
        industry=args.industry,
        stage=args.stage,
        vertical_id=args.vertical_id,
        limit=args.limit,
    )
    print(json.dumps([_serialize(c) for c in cases], default=str))
    return 0


def _cmd_checklist(args: argparse.Namespace) -> int:
    from helpers.north_star.nsm_checklist import load_questions
    qs = load_questions()
    print(json.dumps([_serialize(q) for q in qs], default=str))
    return 0


def _cmd_check_input_tree(args: argparse.Namespace) -> int:
    """Validate an NSM input tree read from stdin JSON.

    Stdin: {"nsm": [...], "inputs": {"Breadth": [...], ...}, "how": "product"}
    The /north-star inputs verb pipes the per-period series it computed from the
    active dataset; this enforces the restatement + reconciliation guardrail.
    """
    from helpers.north_star.input_tree import check_input_tree
    payload = json.loads(sys.stdin.read())
    verdict = check_input_tree(
        payload["nsm"], payload["inputs"], how=payload.get("how", "product")
    )
    print(json.dumps(_serialize(verdict), default=str))
    return 0


def _cmd_drivers(args: argparse.Namespace) -> int:
    """Deterministic driver decomposition + report for /north-star drivers.

    Writes <out>.md and <out>.html (Economist report with the diverging chart)
    and prints the stats. Same window in => same numbers out, every run.
    """
    from helpers.north_star import drivers as drv
    data = args.data or str(drv.DEFAULT_DATA)
    name = args.name
    if not name:
        # Default to the active dataset's display name — never hardcode.
        try:
            from helpers.data_helpers import detect_active_source
            name = (detect_active_source() or {}).get("display_name")
        except Exception:
            name = None
    stats = drv.compute(data, start=args.start, end=args.end, nsm=args.nsm, name=name)
    out = __import__("pathlib").Path(args.out)
    if args.format in ("md", "both"):
        out.with_suffix(".md").write_text(drv.render_md(stats), encoding="utf-8")
        print(f"Wrote {out.with_suffix('.md')}")
    if args.format in ("html", "both"):
        out.with_suffix(".html").write_text(drv.render_html(stats), encoding="utf-8")
        print(f"Wrote {out.with_suffix('.html')}")
    printable = {k: v for k, v in stats.items() if not k.startswith("_")}
    print(json.dumps(printable, default=str))
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="python -m helpers.north_star")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("refusal")
    p.add_argument("candidate", nargs="?", help="NSM candidate string")
    p.add_argument("--stdin", action="store_true", help="read candidate from stdin (recommended for arbitrary input)")
    p.set_defaults(func=_cmd_refusal)

    p = sub.add_parser("classify-vertical")
    p.add_argument("description", help="product description")
    p.add_argument("--industry", default=None, help="stated industry")
    p.add_argument("--business-model", default=None, help="business model")
    p.set_defaults(func=_cmd_classify_vertical)

    p = sub.add_parser("calibration")
    p.add_argument("vertical_id")
    p.add_argument("verb")
    p.set_defaults(func=_cmd_calibration)

    p = sub.add_parser("case-lookup")
    p.add_argument("--vertical-id", default=None)
    p.add_argument("--game", default=None)
    p.add_argument("--industry", default=None)
    p.add_argument("--stage", default=None)
    p.add_argument("--limit", type=int, default=5)
    p.set_defaults(func=_cmd_case_lookup)

    p = sub.add_parser("checklist")
    p.set_defaults(func=_cmd_checklist)

    p = sub.add_parser("check-input-tree", help="validate an NSM input tree (stdin JSON)")
    p.set_defaults(func=_cmd_check_input_tree)

    p = sub.add_parser("drivers", help="deterministic driver decomposition + report")
    p.add_argument("--data", default=None, help="data dir (default: repo data/practice)")
    p.add_argument("--start", default=None, help="window start YYYY-MM (default: first full month)")
    p.add_argument("--end", default=None, help="window end YYYY-MM (default: last full month)")
    p.add_argument("--nsm", default="weekly completed orders")
    p.add_argument("--name", default=None, help="report label (default: active dataset display name)")
    p.add_argument("--out", default="outputs/north-star/drivers_report.md")
    p.add_argument("--format", choices=["md", "html", "both"], default="both")
    p.set_defaults(func=_cmd_drivers)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
