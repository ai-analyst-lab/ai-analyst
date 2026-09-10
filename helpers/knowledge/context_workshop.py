"""Scaffold and validate a small context package for the Week 4 build labs.

The scaffold intentionally contains structure but almost no business meaning. Students
use Claude to profile the practice data, propose the missing artifacts, and then review
those artifacts before they become trusted. The validator checks whether the package is
internally usable. It cannot decide whether a company's definition is true.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml


_METRIC_FIELDS = {
    "id", "name", "aliases", "means", "grain", "numerator", "denominator",
    "window", "filters", "rejected", "status", "owner", "source", "last_reviewed",
}
_ENTITY_FIELDS = {"entity", "table", "primary_key", "grain", "status", "owner", "last_reviewed"}
_RELATIONSHIP_FIELDS = {"id", "left", "right", "on", "cardinality", "status", "owner", "last_reviewed"}
_DIMENSION_FIELDS = {"id", "entity", "expression", "aliases", "sample_values", "status", "owner", "last_reviewed"}
_ALLOWED_CARDINALITIES = {"one_to_one", "one_to_many", "many_to_one", "many_to_many"}
_ALLOWED_STATUSES = {"proposed", "reviewed", "trusted", "stale", "quarantined", "untrusted"}


def _write_yaml(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")


def scaffold_context_store(destination: str | Path, *, dataset: str = "novamart") -> dict[str, Any]:
    """Create an idempotent, deliberately sparse context package."""
    root = Path(destination)
    root.mkdir(parents=True, exist_ok=True)
    existing = [path for path in root.rglob("*") if path.is_file()]
    if existing:
        return {
            "status": "existing",
            "context_dir": str(root),
            "created": [],
            "message": "The destination already contains files. Nothing was overwritten.",
        }

    files: dict[str, Any] = {
        "manifest.yaml": {
            "dataset_id": dataset,
            "display_name": "NovaMart practice data",
            "description": "Disposable context package built during Session 7",
            "connection_type": "duckdb",
            "database": "data/practice/novamart_practice.duckdb",
            "organization": "novamart",
            "context_policy": "context-policy.yaml",
        },
        "context-policy.yaml": {
            "schema_version": 1,
            "dataset": dataset,
            "principles": [
                "Select the smallest sufficient context for the question and worker.",
                "Stop when reviewed definitions conflict.",
                "Do not promote proposed context without human review and evaluation evidence.",
            ],
            "delivery": {
                "resident": ["custom_instructions"],
                "selected": ["metrics", "entities", "relationships", "dimensions", "filters", "verified_queries", "corrections"],
                "compiled": ["metrics_with_compile_blocks"],
            },
            "authority": {"trusted": 30, "reviewed": 20, "proposed": 10, "untrusted": 0},
            "freshness": {"default_review_days": 90, "metric_review_days": 90},
            "budgets": {"default_tokens": 1800, "resident_tokens": 300},
            "conflicts": {
                "behavior": "stop",
                "compare_fields": ["means", "numerator", "denominator", "grain", "window", "filters"],
            },
        },
        "metrics/index.yaml": [],
        "semantic/entities.yaml": {"schema_version": 1, "dataset": dataset, "entities": []},
        "semantic/relationships.yaml": {"schema_version": 1, "dataset": dataset, "relationships": []},
        "semantic/dimensions.yaml": {"schema_version": 1, "dataset": dataset, "dimensions": []},
        "semantic/filters.yaml": {"schema_version": 1, "dataset": dataset, "filters": []},
        "verified_queries.yaml": {"schema_version": 1, "dataset": dataset, "verified_queries": []},
        "corrections.yaml": {"schema_version": 1, "dataset": dataset, "corrections": []},
    }
    created = []
    for relative, value in files.items():
        path = root / relative
        _write_yaml(path, value)
        created.append(str(path))
    instructions = root / "custom_instructions.md"
    instructions.write_text(
        "# NovaMart standing instructions\n\n"
        "This file is intentionally sparse. Add only rules that should apply to most NovaMart analyses.\n",
        encoding="utf-8",
    )
    created.append(str(instructions))
    return {
        "status": "created",
        "context_dir": str(root),
        "created": created,
        "message": "The package contains structure, not reviewed business meaning.",
    }


def _load_yaml(path: Path, errors: list[str]) -> Any:
    if not path.exists():
        errors.append(f"missing required file: {path}")
        return None
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:
        errors.append(f"invalid YAML: {path}: {exc}")
        return None


def _missing(row: dict[str, Any], fields: set[str]) -> list[str]:
    return sorted(field for field in fields if field not in row or row[field] in (None, ""))


def _validate_status(row: dict[str, Any], label: str, errors: list[str]) -> None:
    if row.get("status") not in _ALLOWED_STATUSES:
        errors.append(f"{label} has unsupported status {row.get('status')!r}")


def validate_context_store(context_dir: str | Path) -> dict[str, Any]:
    """Check structure and references without claiming that business meaning is correct."""
    root = Path(context_dir)
    errors: list[str] = []
    warnings: list[str] = []

    manifest = _load_yaml(root / "manifest.yaml", errors) or {}
    policy = _load_yaml(root / "context-policy.yaml", errors) or {}
    index_raw = _load_yaml(root / "metrics" / "index.yaml", errors)
    index_rows = index_raw if isinstance(index_raw, list) else (index_raw or {}).get("metrics", [])
    if not isinstance(index_rows, list):
        errors.append("metrics/index.yaml must be a list or contain a metrics list")
        index_rows = []

    if not manifest.get("dataset_id"):
        errors.append("manifest.yaml is missing dataset_id")
    if not isinstance(policy.get("delivery"), dict):
        errors.append("context-policy.yaml is missing delivery configuration")

    metric_count = 0
    for entry in index_rows:
        if not isinstance(entry, dict):
            errors.append("metrics/index.yaml contains a non-mapping entry")
            continue
        metric_id = str(entry.get("id") or entry.get("metric") or "")
        if not metric_id:
            errors.append("a metric index entry is missing id")
            continue
        metric_file = root / "metrics" / str(entry.get("path") or f"{metric_id}.yaml")
        metric = _load_yaml(metric_file, errors)
        if not isinstance(metric, dict):
            continue
        metric_count += 1
        missing = _missing(metric, _METRIC_FIELDS)
        if missing:
            errors.append(f"metric {metric_id} is missing: {', '.join(missing)}")
        if str(metric.get("id")) != metric_id:
            errors.append(f"metric index id {metric_id} does not match file id {metric.get('id')!r}")
        if not isinstance(metric.get("rejected"), list) or not metric.get("rejected"):
            errors.append(f"metric {metric_id} needs at least one rejected interpretation")
        _validate_status(metric, f"metric {metric_id}", errors)

    entities_raw = _load_yaml(root / "semantic" / "entities.yaml", errors) or {}
    relationships_raw = _load_yaml(root / "semantic" / "relationships.yaml", errors) or {}
    dimensions_raw = _load_yaml(root / "semantic" / "dimensions.yaml", errors) or {}
    filters_raw = _load_yaml(root / "semantic" / "filters.yaml", errors) or {}
    _load_yaml(root / "verified_queries.yaml", errors)
    _load_yaml(root / "corrections.yaml", errors)

    entities = entities_raw.get("entities", []) if isinstance(entities_raw, dict) else []
    relationships = relationships_raw.get("relationships", []) if isinstance(relationships_raw, dict) else []
    dimensions = dimensions_raw.get("dimensions", []) if isinstance(dimensions_raw, dict) else []
    filters = filters_raw.get("filters", []) if isinstance(filters_raw, dict) else []
    entity_ids: set[str] = set()

    for row in entities:
        label = f"entity {row.get('entity')!r}"
        missing = _missing(row, _ENTITY_FIELDS)
        if missing:
            errors.append(f"{label} is missing: {', '.join(missing)}")
        if row.get("entity"):
            entity_ids.add(str(row["entity"]))
        _validate_status(row, label, errors)

    for row in relationships:
        label = f"relationship {row.get('id')!r}"
        missing = _missing(row, _RELATIONSHIP_FIELDS)
        if missing:
            errors.append(f"{label} is missing: {', '.join(missing)}")
        if row.get("cardinality") not in _ALLOWED_CARDINALITIES:
            errors.append(f"{label} has unsupported cardinality {row.get('cardinality')!r}")
        _validate_status(row, label, errors)

    for row in dimensions:
        label = f"dimension {row.get('id')!r}"
        missing = _missing(row, _DIMENSION_FIELDS)
        if missing:
            errors.append(f"{label} is missing: {', '.join(missing)}")
        if row.get("entity") and str(row["entity"]) not in entity_ids:
            errors.append(f"{label} references unknown entity {row['entity']!r}")
        if not isinstance(row.get("sample_values"), list) or not row.get("sample_values"):
            warnings.append(f"{label} has no reviewed sample values")
        _validate_status(row, label, errors)

    if not metric_count:
        warnings.append("the store contains no registered metric contracts")
    if not entities:
        warnings.append("the store contains no structured entities")
    if not relationships:
        warnings.append("the store contains no reviewed relationships")
    if not dimensions:
        warnings.append("the store contains no reviewed dimensions")
    if not filters:
        warnings.append("the store contains no reviewed filters")

    return {
        "schema_version": "1.0",
        "context_dir": str(root),
        "valid": not errors,
        "counts": {
            "metrics": metric_count,
            "entities": len(entities),
            "relationships": len(relationships),
            "dimensions": len(dimensions),
            "filters": len(filters),
        },
        "errors": errors,
        "warnings": warnings,
        "claim": "This validation checks structure and references. A qualified human must still review business meaning and source authority.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Scaffold or validate a context package")
    subparsers = parser.add_subparsers(dest="command", required=True)
    scaffold = subparsers.add_parser("scaffold")
    scaffold.add_argument("--output", required=True)
    scaffold.add_argument("--dataset", default="novamart")
    validate = subparsers.add_parser("validate")
    validate.add_argument("--context-dir", required=True)
    args = parser.parse_args(argv)

    if args.command == "scaffold":
        result = scaffold_context_store(args.output, dataset=args.dataset)
        print(json.dumps(result, indent=2) + "\n", end="")
        return 0

    result = validate_context_store(args.context_dir)
    print(json.dumps(result, indent=2) + "\n", end="")
    return 0 if result["valid"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
