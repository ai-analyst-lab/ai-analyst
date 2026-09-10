"""Tier routing for a resolved metric question (v3.1).

The natural-language work (deciding WHICH metric a question is about) stays in the analyst-core
skill, where the model lives. This helper answers the narrow, deterministic question that follows:
given a dataset and a resolved metric id (or none), which tier handles it, and why.

  Tier A  the metric exists and has a valid compile block          -> deterministic compiler
  Tier B  the metric exists and declares an external binding       -> the team's semantic layer
  Tier C  no metric resolved, or it has no executable binding      -> generate SQL + validate

Tier C is the fall-forward: an unresolved or uncompilable metric is never refused, it is answered
by the generate-and-validate path and labelled as generated. The provenance label each tier carries
is the value returned here so the skill can stamp every number consistently.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from helpers.data.metric_compiler import is_compilable, load_metric

# provenance_mode values, shared with analyst-core and the trace skill.
MODE_COMPILED = "compiled"        # Tier A, deterministic local compiler
MODE_CONTRACT = MODE_COMPILED      # Backward-compatible constant name
MODE_EXTERNAL = "external"        # Tier B (suffix with the source, e.g. "external:dbt")
MODE_CONTRACT_GUIDED = "contract-guided"  # Tier C, definition informed generated SQL
MODE_GENERATED = "generated"      # Tier C, validated
MODE_GENERATED_UNVERIFIED = "generated-unverified"  # Tier C, validation failed or skipped
# The router cannot know whether a Tier C answer passed validation, so it always returns
# MODE_GENERATED; the analyst-core skill downgrades it to MODE_GENERATED_UNVERIFIED after the
# validation step when a check fails. The constant lives here so the vocabulary has one home.


def _metric_entries(raw: Any) -> list[dict[str, Any]]:
    """Normalize both supported metric-index shapes.

    Current stores use a list of lightweight entries. Older context stores used a mapping
    with a ``metrics`` list. Reading both keeps old stores inspectable while giving new
    stores one file per metric as their canonical form.
    """
    if isinstance(raw, list):
        return [row for row in raw if isinstance(row, dict)]
    if isinstance(raw, dict) and isinstance(raw.get("metrics"), list):
        return [row for row in raw["metrics"] if isinstance(row, dict)]
    return []


def list_metrics(
    dataset: str,
    project_root: str | Path = ".",
    context_dir: str | Path | None = None,
) -> list[dict[str, Any]]:
    """The metric index entries for a dataset, or [] if none are defined."""
    base = Path(context_dir) if context_dir is not None else (
        Path(project_root) / ".knowledge" / "datasets" / dataset
    )
    idx = base / "metrics" / "index.yaml"
    if not idx.exists():
        return []
    return _metric_entries(yaml.safe_load(idx.read_text()))


def route(
    dataset: str,
    metric_id: str | None,
    project_root: str | Path = ".",
    context_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Return ``{tier, mode, metric_id, external, reason}`` for a resolved metric id.

    ``metric_id`` is what the skill resolved the question to, or None if it could not resolve a
    single defined metric. This function does no NL matching; it only inspects the metric file.
    """
    if not metric_id:
        return _tier_c("no defined metric resolved for this question")

    try:
        metric = load_metric(dataset, metric_id, project_root, context_dir=context_dir)
    except Exception:
        return _tier_c(f"metric id {metric_id!r} not found in {dataset}")

    external = ((metric.get("compile") or {}).get("external")) if isinstance(metric.get("compile"), dict) else None
    if isinstance(external, dict) and external.get("source"):
        return {
            "tier": "B",
            "mode": f"{MODE_EXTERNAL}:{external['source']}",
            "metric_id": metric_id,
            "external": external,
            "reason": f"metric binds to the {external['source']} semantic layer",
        }

    if is_compilable(metric):
        return {
            "tier": "A",
            "mode": MODE_COMPILED,
            "metric_id": metric_id,
            "external": None,
            "reason": "metric has a valid compile block",
        }

    return {
        "tier": "C",
        "mode": MODE_CONTRACT_GUIDED,
        "metric_id": metric_id,
        "external": None,
        "reason": f"metric {metric_id!r} guides generated SQL but has no executable binding",
    }


def _tier_c(reason: str) -> dict[str, Any]:
    return {"tier": "C", "mode": MODE_GENERATED, "metric_id": None, "external": None, "reason": reason}
