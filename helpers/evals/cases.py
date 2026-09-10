"""Load, validate, and publish evaluation cases."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .schema import EvaluationCase

PRIVATE_CASE_FIELDS = frozenset(
    {"expected", "accepted", "reference_query", "reproduction"}
)


def _load_yaml(path: str | Path) -> dict[str, Any]:
    payload = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a YAML mapping")
    return payload


def load_suite(path: str | Path, *, allow_private: bool = False) -> tuple[dict[str, Any], list[EvaluationCase]]:
    payload = _load_yaml(path)
    cases_raw = payload.get("cases") or []
    if not isinstance(cases_raw, list):
        raise ValueError("cases must be a list")
    if not allow_private:
        leaks = {
            case.get("case_id", f"case-{index}"): sorted(PRIVATE_CASE_FIELDS.intersection(case))
            for index, case in enumerate(cases_raw, start=1)
            if isinstance(case, dict) and PRIVATE_CASE_FIELDS.intersection(case)
        }
        if leaks:
            raise ValueError(f"public suite contains private reference fields: {leaks}")
    cases = [EvaluationCase.from_dict(case) for case in cases_raw]
    ids = [case.case_id for case in cases]
    if len(ids) != len(set(ids)):
        raise ValueError("case_id values must be unique within a suite")
    metadata = {key: value for key, value in payload.items() if key != "cases"}
    return metadata, cases


def publish_manifest(private_path: str | Path, public_path: str | Path) -> Path:
    """Write a question-only manifest from a private suite."""
    metadata, cases = load_suite(private_path, allow_private=True)
    public = {
        **metadata,
        "visibility": "public-task-manifest",
        "cases": [case.to_dict(public=True) for case in cases if case.status != "retired"],
    }
    target = Path(public_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(yaml.safe_dump(public, sort_keys=False), encoding="utf-8")
    return target


def join_public_and_private(
    public_cases: list[EvaluationCase], private_cases: list[EvaluationCase]
) -> list[tuple[EvaluationCase, EvaluationCase]]:
    private_by_id = {case.case_id: case for case in private_cases}
    pairs = []
    for public in public_cases:
        private = private_by_id.get(public.case_id)
        if private is None:
            raise ValueError(f"private reference missing for public case {public.case_id}")
        if public.case_version != private.case_version or public.task != private.task:
            raise ValueError(f"public and private case drift for {public.case_id}")
        pairs.append((public, private))
    return pairs
