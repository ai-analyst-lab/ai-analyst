"""Tier routing for a resolved metric question (v3.1).

The natural-language work (deciding WHICH metric a question is about) stays in the analyst-core
skill, where the model lives. This helper answers the narrow, deterministic question that follows:
given a dataset and a resolved metric id (or none), which tier handles it, and why.

  Tier A  the metric exists and has a valid compile block          -> deterministic compiler
  Tier B  the metric exists and declares an external binding        -> the team's semantic layer
  Tier C  no metric resolved, or it has no compile/external block   -> generate SQL + validate

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
MODE_CONTRACT = "contract"        # Tier A
MODE_EXTERNAL = "external"        # Tier B (suffix with the source, e.g. "external:dbt")
MODE_GENERATED = "generated"      # Tier C, validated
MODE_GENERATED_UNVERIFIED = "generated-unverified"  # Tier C, validation failed or skipped


def list_metrics(dataset: str, project_root: str | Path = ".") -> list[dict[str, Any]]:
    """The metric index entries for a dataset, or [] if none are defined."""
    idx = Path(project_root) / ".knowledge" / "datasets" / dataset / "metrics" / "index.yaml"
    if not idx.exists():
        return []
    return yaml.safe_load(idx.read_text()) or []


def route(dataset: str, metric_id: str | None, project_root: str | Path = ".") -> dict[str, Any]:
    """Return ``{tier, mode, metric_id, external, reason}`` for a resolved metric id.

    ``metric_id`` is what the skill resolved the question to, or None if it could not resolve a
    single defined metric. This function does no NL matching; it only inspects the metric file.
    """
    if not metric_id:
        return _tier_c("no defined metric resolved for this question")

    try:
        metric = load_metric(dataset, metric_id, project_root)
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
            "mode": MODE_CONTRACT,
            "metric_id": metric_id,
            "external": None,
            "reason": "metric has a valid compile block",
        }

    return _tier_c(f"metric {metric_id!r} has no compile or external block")


def _tier_c(reason: str) -> dict[str, Any]:
    return {"tier": "C", "mode": MODE_GENERATED, "metric_id": None, "external": None, "reason": reason}
