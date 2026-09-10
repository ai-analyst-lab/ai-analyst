"""Build an inspectable context manifest for one analytical question.

This module does not attempt semantic search. It provides a small, deterministic
reference implementation for the context decisions the course teaches:

* content: what information exists;
* representation: metric, relationship, example, correction, or instruction;
* delivery: resident, selected, or compiled;
* governance: source, owner, status, review date, conflicts, and freshness.

Production systems can replace the selection function with a catalog or retrieval
service while preserving the manifest contract and the evidence it creates.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable

import yaml

from helpers.data.metric_compiler import is_compilable
from helpers.data.metric_router import list_metrics
from helpers.knowledge.context_loader import estimate_tokens
from helpers.knowledge.context_sync import resolve_context_dir, resolved_commit


_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "did", "do", "does",
    "for", "from", "how", "i", "in", "is", "it", "of", "on", "or", "our",
    "the", "this", "to", "was", "we", "what", "when", "where", "which", "who",
    "why", "with", "you", "your",
}


def _load_yaml(path: Path) -> Any:
    if not path.exists():
        return None
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _tokens(value: Any) -> set[str]:
    text = value if isinstance(value, str) else yaml.safe_dump(value, sort_keys=True)
    return {
        token
        for token in re.findall(r"[a-z0-9_]+", text.casefold())
        if len(token) > 1 and token not in _STOPWORDS
    }


def _review_age(value: Any, today: str | date | None) -> int | None:
    if not value:
        return None
    current = date.today() if today is None else (
        today if isinstance(today, date) else datetime.strptime(str(today), "%Y-%m-%d").date()
    )
    reviewed = value if isinstance(value, date) else datetime.strptime(str(value), "%Y-%m-%d").date()
    return (current - reviewed).days


def _content_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    return yaml.safe_dump(content, sort_keys=False)


def _search_content(content: Any) -> Any:
    """Remove governance boilerplate that should not make two items relevant."""
    if not isinstance(content, dict):
        return content
    meaning_fields = {
        "id", "name", "aliases", "means", "formula", "grain", "numerator",
        "denominator", "window", "filters", "rejected", "entity", "table", "left",
        "right", "on", "cardinality", "warning", "expression", "description",
        "sample_values", "question", "intent", "domains", "teaches", "issue",
        "instruction", "compile",
    }
    return {key: value for key, value in content.items() if key in meaning_fields}


def _structural_references(items: Iterable[dict[str, Any]]) -> set[str]:
    """Return explicit entity, table, dimension, and filter references.

    Relevance tokens are useful for choosing the first metric or example, but they are
    too loose for dependency expansion. A word such as ``status`` or ``period`` can
    otherwise drag most of a semantic layer into a small question. This resolver only
    expands through identifiers and table names present in the selected content.
    """
    references: set[str] = set()
    for item in items:
        content = item.get("content")
        if not isinstance(content, dict):
            continue
        for key in ("entity", "table", "left", "right"):
            value = content.get(key)
            if value:
                references.add(str(value).casefold())
        compile_block = content.get("compile")
        if isinstance(compile_block, dict):
            if compile_block.get("table"):
                references.add(str(compile_block["table"]).casefold())
            for key in ("dimensions", "filters"):
                values = compile_block.get(key)
                if isinstance(values, dict):
                    references.update(str(value).casefold() for value in values)
        for value in content.get("context_refs", []) or []:
            references.add(str(value).casefold())
    return references


def _supports_references(item: dict[str, Any], references: set[str]) -> bool:
    content = item.get("content")
    if not isinstance(content, dict):
        return False
    candidates = {str(item["item_id"]).casefold()}
    for key in ("id", "entity", "table", "left", "right"):
        value = content.get(key)
        if value:
            candidates.add(str(value).casefold())
            candidates.add(f"{item['kind']}:{str(value).casefold()}")
    return bool(candidates.intersection(references))


def _intent_condition(item: dict[str, Any], question_tokens: set[str]) -> tuple[bool, list[str]]:
    """Return whether a context item is eligible for the question's stated intent.

    ``applies_when`` is intentionally a small, inspectable delivery rule. It is useful
    for definitions that remain valid only for a named historical report or another
    explicit intent. The selector does not infer that intent from general relevance.
    At least one declared term must appear in the question.
    """
    content = item.get("content")
    if not isinstance(content, dict):
        return True, []
    raw_terms = content.get("applies_when") or []
    if isinstance(raw_terms, str):
        raw_terms = [raw_terms]
    terms = sorted({token for term in raw_terms for token in _tokens(str(term))})
    if not terms:
        return True, []
    return bool(question_tokens.intersection(terms)), terms


def _quarantine_match(
    item: dict[str, Any],
    quarantined_entities: set[str],
    quarantined_tables: set[str],
) -> bool:
    """Return whether an item depends directly on quarantined structure."""
    content = item.get("content")
    if not isinstance(content, dict):
        return False
    entity_values = {
        str(content.get(key)).casefold()
        for key in ("entity", "left", "right")
        if content.get(key)
    }
    table_values = {
        str(content.get(key)).casefold()
        for key in ("table", "base_table", "logical_table")
        if content.get(key)
    }
    compile_block = content.get("compile")
    if isinstance(compile_block, dict) and compile_block.get("table"):
        table_values.add(str(compile_block["table"]).casefold())
    usage_checks = content.get("usage_checks")
    if isinstance(usage_checks, dict):
        for value in usage_checks.get("sql_requires_all", []) or []:
            normalized = str(value).casefold()
            if normalized in quarantined_tables:
                table_values.add(normalized)
    for reference in content.get("context_refs", []) or []:
        value = str(reference).casefold()
        if value.startswith("entity:"):
            entity_values.add(value.split(":", 1)[1])
    return bool(entity_values.intersection(quarantined_entities)) or bool(
        table_values.intersection(quarantined_tables)
    )


def _item(
    *,
    item_id: str,
    subject_key: str,
    kind: str,
    path: Path,
    content: Any,
    delivery: str,
    today: str | date | None,
    policy: dict[str, Any],
    eligible: bool = True,
) -> dict[str, Any]:
    raw = content if isinstance(content, dict) else {}
    status = str(raw.get("status") or ("trusted" if eligible else "untrusted"))
    reviewed = raw.get("last_reviewed") or raw.get("last_verified") or raw.get("verified_at")
    age = _review_age(reviewed, today)
    review_days = int(
        (policy.get("freshness") or {}).get(
            f"{kind.rstrip('s')}_review_days",
            (policy.get("freshness") or {}).get("default_review_days", 90),
        )
    )
    if kind in {"policy", "instruction", "schema"}:
        freshness = "not-applicable"
    else:
        freshness = "missing" if age is None else ("stale" if age > review_days else "current")
    text = _content_text(content)
    return {
        "item_id": item_id,
        "subject_key": subject_key,
        "kind": kind,
        "path": str(path),
        "delivery": delivery,
        "status": status,
        "eligible": bool(eligible and status in {"trusted", "reviewed"}),
        "owner": raw.get("owner"),
        "source": raw.get("source"),
        "last_reviewed": str(reviewed) if reviewed else None,
        "age_days": age,
        "freshness": freshness,
        "review_days": review_days,
        "estimated_tokens": estimate_tokens(text),
        "content_digest": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "search_tokens": sorted(_tokens(_search_content(content))),
        "content": content,
        "usage_checks": raw.get("usage_checks") or {},
    }


def _list_entries(path: Path, key: str) -> list[dict[str, Any]]:
    raw = _load_yaml(path) or {}
    rows = raw if isinstance(raw, list) else raw.get(key, [])
    return [row for row in rows if isinstance(row, dict)]


def inventory_context(context_dir: str | Path, today: str | date | None = None) -> list[dict[str, Any]]:
    """Return every supported context item, including non-promoted proposals."""
    context_dir = Path(context_dir)
    policy = _load_yaml(context_dir / "context-policy.yaml") or {}
    items: list[dict[str, Any]] = []

    for filename, kind, item_id in (
        ("context-policy.yaml", "policy", "context-policy"),
        ("custom_instructions.md", "instruction", "custom-instructions"),
        ("schema.md", "schema", "schema-summary"),
        ("quirks.md", "correction", "dataset-quirks"),
    ):
        path = context_dir / filename
        if not path.exists():
            continue
        content = path.read_text(encoding="utf-8") if path.suffix == ".md" else _load_yaml(path)
        delivery = "resident" if kind in {"policy", "instruction"} else "selected"
        items.append(
            _item(
                item_id=f"{kind}:{item_id}",
                subject_key=f"{kind}:{item_id}",
                kind=kind,
                path=path,
                content=content,
                delivery=delivery,
                today=today,
                policy=policy,
            )
        )

    dataset = str((_load_yaml(context_dir / "manifest.yaml") or {}).get("dataset_id") or context_dir.name)
    for row in list_metrics(dataset, context_dir=context_dir):
        metric_id = str(row.get("id") or row.get("metric") or row.get("name"))
        path = context_dir / "metrics" / str(row.get("path") or f"{metric_id}.yaml")
        content = _load_yaml(path) or dict(row)
        delivery = "compiled" if is_compilable(content) else "selected"
        items.append(
            _item(
                item_id=f"metric:{metric_id}",
                subject_key=f"metric:{metric_id}",
                kind="metric",
                path=path,
                content=content,
                delivery=delivery,
                today=today,
                policy=policy,
            )
        )

    structured = (
        ("semantic/entities.yaml", "entities", "entity"),
        ("semantic/relationships.yaml", "relationships", "relationship"),
        ("semantic/dimensions.yaml", "dimensions", "dimension"),
        ("semantic/filters.yaml", "filters", "filter"),
        ("verified_queries.yaml", "verified_queries", "verified_query"),
        ("corrections.yaml", "corrections", "correction"),
    )
    for filename, key, kind in structured:
        path = context_dir / filename
        for position, content in enumerate(_list_entries(path, key), start=1):
            name = (
                content.get("id") or content.get(kind) or content.get("name")
                or f"{kind}-{position}"
            )
            items.append(
                _item(
                    item_id=f"{kind}:{name}",
                    subject_key=f"{kind}:{name}",
                    kind=kind,
                    path=path,
                    content=content,
                    delivery="selected",
                    today=today,
                    policy=policy,
                )
            )

    proposals_dir = context_dir / "proposals"
    if proposals_dir.exists():
        for path in sorted(proposals_dir.glob("*.yaml")):
            content = _load_yaml(path) or {}
            proposal_id = str(content.get("id") or path.stem)
            items.append(
                _item(
                    item_id=f"proposal:{proposal_id}",
                    subject_key=f"metric:{proposal_id}",
                    kind="metric",
                    path=path,
                    content=content,
                    delivery="not-promoted",
                    today=today,
                    policy=policy,
                    eligible=False,
                )
            )
    return items


def _conflict_fields(a: dict[str, Any], b: dict[str, Any], fields: Iterable[str]) -> list[str]:
    left = a.get("content") if isinstance(a.get("content"), dict) else {}
    right = b.get("content") if isinstance(b.get("content"), dict) else {}
    return [field for field in fields if left.get(field) != right.get(field) and (left.get(field) or right.get(field))]


def detect_conflicts(items: list[dict[str, Any]], policy: dict[str, Any]) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        groups.setdefault(item["subject_key"], []).append(item)
    fields = (policy.get("conflicts") or {}).get("compare_fields", ["means", "formula", "grain"])
    conflicts = []
    for subject, rows in groups.items():
        if len(rows) < 2:
            continue
        for index, left in enumerate(rows):
            for right in rows[index + 1:]:
                changed = _conflict_fields(left, right, fields)
                if not changed:
                    continue
                blocking = bool(left["eligible"] and right["eligible"])
                conflicts.append(
                    {
                        "subject_key": subject,
                        "items": [left["item_id"], right["item_id"]],
                        "different_fields": changed,
                        "blocking": blocking,
                        "resolution": (
                            "stop and obtain an approved definition"
                            if blocking else "keep the proposal outside trusted context until reviewed"
                        ),
                    }
                )
    return conflicts


def build_context_manifest(
    context_dir: str | Path,
    question: str,
    *,
    max_tokens: int | None = None,
    today: str | date | None = None,
    source: str = "local",
    source_commit: str | None = None,
    quarantined: Iterable[dict[str, Any]] = (),
) -> dict[str, Any]:
    """Select a deterministic, inspectable context bundle for ``question``."""
    context_dir = Path(context_dir)
    policy = _load_yaml(context_dir / "context-policy.yaml") or {}
    if max_tokens is None:
        max_tokens = int((policy.get("budgets") or {}).get("default_tokens", 2400))
    items = inventory_context(context_dir, today=today)
    question_tokens = _tokens(question)
    conflicts = detect_conflicts(items, policy)
    quarantine_rows = list(quarantined)
    quarantined_entities = {
        str(row.get("name")).casefold() for row in quarantine_rows if row.get("name")
    }
    quarantined_tables = {
        str(row.get("table")).casefold() for row in quarantine_rows if row.get("table")
    }

    scored: list[tuple[int, dict[str, Any]]] = []
    for item in items:
        condition_met, condition_terms = _intent_condition(item, question_tokens)
        item["intent_condition"] = condition_terms
        item["intent_condition_met"] = condition_met
        item["quarantined"] = _quarantine_match(
            item, quarantined_entities, quarantined_tables
        )
        overlap = question_tokens.intersection(item["search_tokens"])
        score = len(overlap) * 10
        if item["delivery"] == "resident":
            score = 10_000
        if item["kind"] == "schema":
            score += 1
        if not item["eligible"] or not condition_met or item["quarantined"]:
            score = -1
        scored.append((score, item))

    best_relevance = max(
        (score for score, item in scored if score > 0 and item["delivery"] != "resident" and item["kind"] != "schema"),
        default=0,
    )
    relevance_floor = max(10, (best_relevance + 1) // 2) if best_relevance else 0

    selected: list[dict[str, Any]] = []
    omitted: list[dict[str, Any]] = []
    used_tokens = 0

    for score, item in sorted(scored, key=lambda pair: (-pair[0], pair[1]["item_id"])):
        if score < 0:
            reason = (
                "quarantined after schema drift"
                if item["quarantined"]
                else (
                    "requires explicit intent: " + ", ".join(item["intent_condition"])
                    if item["eligible"] and not item["intent_condition_met"]
                    else "not promoted to trusted context"
                )
            )
            omitted.append({"item_id": item["item_id"], "reason": reason})
            continue
        if score == 0 and item["delivery"] != "resident":
            continue
        if (
            item["delivery"] != "resident"
            and item["kind"] != "schema"
            and score < relevance_floor
        ):
            continue
        cost = item["estimated_tokens"]
        if used_tokens + cost > max_tokens:
            omitted.append({"item_id": item["item_id"], "reason": "context budget"})
            continue
        row = {key: value for key, value in item.items() if key not in {"search_tokens", "content"}}
        row["selection_reason"] = (
            "resident policy" if item["delivery"] == "resident"
            else "matched question or selected context"
        )
        selected.append(row)
        used_tokens += cost

    selected_ids = {row["item_id"] for row in selected}
    selected_inventory = [item for _, item in scored if item["item_id"] in selected_ids]
    references = _structural_references(selected_inventory)
    # Add only structural context explicitly referenced by a selected metric or example.
    # This lets a membership metric bring the membership entity and its named filter without
    # allowing generic words such as "status" to pull in unrelated context.
    for score, item in sorted(scored, key=lambda pair: (-pair[0], pair[1]["item_id"])):
        if (
            item["item_id"] in selected_ids
            or not item["eligible"]
            or item["quarantined"]
            or item["delivery"] == "resident"
        ):
            continue
        if item["kind"] not in {"entity", "relationship", "dimension", "filter", "correction"}:
            continue
        if not _supports_references(item, references):
            continue
        cost = item["estimated_tokens"]
        if used_tokens + cost > max_tokens:
            omitted.append({"item_id": item["item_id"], "reason": "context budget"})
            continue
        row = {key: value for key, value in item.items() if key not in {"search_tokens", "content"}}
        row["selection_reason"] = "supports another selected item"
        selected.append(row)
        selected_ids.add(item["item_id"])
        used_tokens += cost

    for _, item in scored:
        if item["item_id"] not in selected_ids and not any(o["item_id"] == item["item_id"] for o in omitted):
            omitted.append({"item_id": item["item_id"], "reason": "not relevant to this question"})

    blocking_conflicts = [c for c in conflicts if c["blocking"]]
    relevant_quarantine = [
        item["item_id"]
        for _, item in scored
        if item["quarantined"] and question_tokens.intersection(item["search_tokens"])
    ]
    warnings = []
    for row in quarantine_rows:
        warnings.append(
            {
                "item_id": f"entity:{row.get('name') or row.get('table') or 'unknown'}",
                "type": "schema-quarantine",
                "message": (
                    f"table {row.get('table') or 'unknown'} no longer matches its reviewed schema; "
                    "dependent context is excluded"
                ),
            }
        )
    for item in selected:
        if item["freshness"] not in {"current", "not-applicable"}:
            warnings.append(
                {
                    "item_id": item["item_id"],
                    "type": "freshness",
                    "message": f"review status is {item['freshness']}",
                }
            )
    for conflict in conflicts:
        warnings.append(
            {
                "item_id": conflict["subject_key"],
                "type": "conflict",
                "message": conflict["resolution"],
            }
        )

    fingerprint_payload = {
        "question": question,
        "selected": [
            {
                "item_id": row["item_id"],
                "path": row["path"],
                "content_digest": row["content_digest"],
            }
            for row in selected
        ],
        "source": source,
        "source_commit": source_commit,
    }
    fingerprint = hashlib.sha256(
        json.dumps(fingerprint_payload, sort_keys=True).encode("utf-8")
    ).hexdigest()
    return {
        "schema_version": "1.0",
        "question": question,
        "context_dir": str(context_dir),
        "source": source,
        "source_commit": source_commit,
        "budget_tokens": max_tokens,
        "estimated_tokens": used_tokens,
        "selected": selected,
        "omitted": sorted(omitted, key=lambda row: row["item_id"]),
        "conflicts": conflicts,
        "blocking": bool(blocking_conflicts or relevant_quarantine),
        "quarantine": quarantine_rows,
        "quarantined_relevant_items": sorted(relevant_quarantine),
        "warnings": warnings,
        "context_fingerprint": fingerprint,
        "claim": "This manifest proves what the deterministic selector supplied. It does not prove the worker used it or that the information is correct.",
    }


def reconcile_context_use(
    manifest: dict[str, Any],
    *,
    cited_item_ids: Iterable[str] = (),
    claimed_used_item_ids: Iterable[str] = (),
    sql: str = "",
) -> dict[str, Any]:
    """Compare supplied context with worker citations and simple SQL evidence."""
    cited = set(cited_item_ids)
    claimed = set(claimed_used_item_ids)
    normalized_sql = re.sub(r"\s+", " ", sql.casefold())
    rows = []
    for item in manifest.get("selected", []):
        item_id = item["item_id"]
        checks = item.get("usage_checks") or {}
        required = [str(term).casefold() for term in checks.get("sql_requires_all", [])]
        forbidden = [str(term).casefold() for term in checks.get("sql_forbids", [])]
        applied = None
        evidence = []
        if required or forbidden:
            missing = [term for term in required if term not in normalized_sql]
            present_forbidden = [term for term in forbidden if term in normalized_sql]
            applied = not missing and not present_forbidden
            if missing:
                evidence.append(f"missing SQL evidence: {', '.join(missing)}")
            if present_forbidden:
                evidence.append(f"forbidden SQL evidence: {', '.join(present_forbidden)}")
            if applied:
                evidence.append("SQL contains the required context evidence")
        rows.append(
            {
                "item_id": item_id,
                "supplied": True,
                "cited": item_id in cited,
                "claimed_used": item_id in claimed,
                "applied": applied,
                "evidence": evidence,
            }
        )
    return {
        "schema_version": "1.0",
        "context_fingerprint": manifest.get("context_fingerprint"),
        "items": rows,
        "supplied_not_cited": [row["item_id"] for row in rows if not row["cited"]],
        "cited_not_applied": [
            row["item_id"] for row in rows if row["cited"] and row["applied"] is False
        ],
        "claim": "Citations and SQL checks provide use evidence. They do not prove the analytical interpretation or business definition is correct.",
    }


def render_context_manifest(manifest: dict[str, Any]) -> str:
    """Render the manifest as a compact student-readable report."""
    lines = [
        "# Context trace",
        "",
        f"**Question:** {manifest['question']}",
        "",
        f"**Source:** {manifest['source']}",
        "",
        f"**Context fingerprint:** `{manifest['context_fingerprint']}`",
        "",
        f"**Budget:** {manifest['estimated_tokens']} of {manifest['budget_tokens']} estimated tokens",
        "",
        f"**Blocking conflict:** {'yes' if manifest['blocking'] else 'no'}",
        "",
        "## Supplied to the worker",
        "",
    ]
    for item in manifest.get("selected", []):
        state = item["freshness"]
        lines.append(
            f"- `{item['item_id']}`: {item['delivery']}; {item['status']}; "
            f"review {state}; {item['selection_reason']}"
        )
    if not manifest.get("selected"):
        lines.append("- None")
    lines.extend(["", "## Warnings", ""])
    for warning in manifest.get("warnings", []):
        lines.append(f"- `{warning['item_id']}`: {warning['message']}")
    if not manifest.get("warnings"):
        lines.append("- None")
    lines.extend(["", "## Not supplied", ""])
    for item in manifest.get("omitted", []):
        lines.append(f"- `{item['item_id']}`: {item['reason']}")
    if not manifest.get("omitted"):
        lines.append("- None")
    lines.extend(["", "## What this proves", "", manifest["claim"], ""])
    return "\n".join(lines)


def _active_dataset(project_root: Path) -> str:
    active = _load_yaml(project_root / ".knowledge" / "active.yaml") or {}
    dataset = active.get("active_dataset")
    if not dataset:
        raise ValueError("No active dataset. Configure one before building a context manifest.")
    return str(dataset)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a question-specific context manifest")
    parser.add_argument("--question", required=True)
    parser.add_argument("--project-root", default=".")
    parser.add_argument(
        "--context-dir",
        help="Optional explicit dataset context directory. Useful for a disposable build workspace.",
    )
    parser.add_argument("--output")
    parser.add_argument("--max-tokens", type=int)
    parser.add_argument("--today")
    parser.add_argument("--duckdb", help="Optional DuckDB path for schema-drift enforcement")
    args = parser.parse_args(argv)

    root = Path(args.project_root).resolve()
    if args.context_dir:
        context_dir = Path(args.context_dir)
        if not context_dir.is_absolute():
            context_dir = root / context_dir
        context_dir = context_dir.resolve()
        source = "explicit"
        commit = None
    else:
        dataset = _active_dataset(root)
        context_dir, source = resolve_context_dir(dataset, root)
        commit = resolved_commit(context_dir.parents[1]) if source == "git" else None
    quarantine = []
    if args.duckdb:
        import duckdb
        from helpers.data.schema_guard import guard_context

        connection = duckdb.connect(str(Path(args.duckdb).resolve()), read_only=True)
        try:
            quarantine = guard_context(connection, context_dir)
        finally:
            connection.close()
    manifest = build_context_manifest(
        context_dir,
        args.question,
        max_tokens=args.max_tokens,
        today=args.today,
        source=source,
        source_commit=commit,
        quarantined=quarantine,
    )
    payload = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(payload, encoding="utf-8")
        output.with_suffix(".md").write_text(render_context_manifest(manifest), encoding="utf-8")
    print(payload, end="")
    return 2 if manifest["blocking"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
