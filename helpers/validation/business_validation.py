from __future__ import annotations

"""
Business Validation — loads rules from knowledge system and validates results.

Bridges .knowledge/ business context with the validation framework.
Reads metric definitions, known ranges, and domain rules to validate
analysis outputs against business expectations.
"""

from pathlib import Path
from typing import Any

import pandas as pd

try:
    import yaml
    _YAML_AVAILABLE = True
except ImportError:
    _YAML_AVAILABLE = False


_KNOWLEDGE_DIR = Path(".knowledge")


def load_metric_rules(dataset_id: str | None = None) -> list[dict]:
    """Load metric validation rules from .knowledge/datasets/{id}/metrics/.

    Reads all metric YAML files and extracts validation rules (ranges,
    guardrails, expected segments).

    Returns list of rule dicts suitable for business_rules.validate_ranges().
    """
    if not _YAML_AVAILABLE:
        return []

    if dataset_id is None:
        # Try to read active dataset
        active_path = _KNOWLEDGE_DIR / "active.yaml"
        if active_path.exists():
            try:
                with open(active_path) as f:
                    data = yaml.safe_load(f)
                dataset_id = data.get("active_dataset") if isinstance(data, dict) else None
            except Exception:
                pass

    if dataset_id is None:
        return []

    metrics_dir = _KNOWLEDGE_DIR / "datasets" / dataset_id / "metrics"
    if not metrics_dir.is_dir():
        return []

    rules = []
    for metric_file in metrics_dir.glob("*.yaml"):
        if metric_file.name.startswith("_") or metric_file.name == "index.yaml":
            continue
        try:
            with open(metric_file) as f:
                metric = yaml.safe_load(f)
            if not isinstance(metric, dict):
                continue
            # Extract range rules if defined
            name = metric.get("name", metric_file.stem)
            rule = {"column": name, "label": metric.get("display_name", name)}
            if "min_value" in metric:
                rule["min"] = metric["min_value"]
            if "max_value" in metric:
                rule["max"] = metric["max_value"]
            # Default ranges for common metric types
            if "rate" in name or "ratio" in name or "pct" in name:
                rule.setdefault("min", 0)
                rule.setdefault("max", 1)
            if rule.get("min") is not None or rule.get("max") is not None:
                rules.append(rule)
        except Exception:
            continue

    return rules


def load_guardrail_pairs(dataset_id: str | None = None) -> list[dict]:
    """Load guardrail metric pairs from metric definitions.

    Returns list of dicts: [{"primary": "conversion_rate", "guardrails": ["aov", "cart_abandonment"]}]
    """
    if not _YAML_AVAILABLE:
        return []

    if dataset_id is None:
        active_path = _KNOWLEDGE_DIR / "active.yaml"
        if active_path.exists():
            try:
                with open(active_path) as f:
                    data = yaml.safe_load(f)
                dataset_id = data.get("active_dataset") if isinstance(data, dict) else None
            except Exception:
                pass

    if dataset_id is None:
        return []

    metrics_dir = _KNOWLEDGE_DIR / "datasets" / dataset_id / "metrics"
    if not metrics_dir.is_dir():
        return []

    pairs = []
    for metric_file in metrics_dir.glob("*.yaml"):
        if metric_file.name.startswith("_") or metric_file.name == "index.yaml":
            continue
        try:
            with open(metric_file) as f:
                metric = yaml.safe_load(f)
            if isinstance(metric, dict) and metric.get("guardrails"):
                pairs.append({
                    "primary": metric.get("name", metric_file.stem),
                    "guardrails": metric["guardrails"],
                })
        except Exception:
            continue

    return pairs


def validate_against_knowledge(
    df: pd.DataFrame,
    dataset_id: str | None = None,
    columns: list[str] | None = None,
) -> dict:
    """Validate DataFrame columns against known business rules from knowledge system.

    Loads metric rules for the dataset and checks applicable columns.

    Returns:
        dict with ok, rules_checked, violations, warnings
    """
    rules = load_metric_rules(dataset_id)
    if not rules:
        return {
            "ok": True,
            "rules_checked": 0,
            "violations": [],
            "warnings": ["No business rules loaded — dataset may not have metric definitions"],
        }

    # Filter to columns present in the DataFrame
    applicable_rules = []
    for rule in rules:
        col = rule["column"]
        if col in df.columns:
            if columns is None or col in columns:
                applicable_rules.append(rule)

    if not applicable_rules:
        return {
            "ok": True,
            "rules_checked": 0,
            "violations": [],
            "warnings": ["No applicable rules for the columns in this DataFrame"],
        }

    violations = []
    for rule in applicable_rules:
        col = rule["column"]
        series = df[col].dropna()
        if len(series) == 0:
            continue
        min_val = rule.get("min")
        max_val = rule.get("max")
        if min_val is not None and series.min() < min_val:
            violations.append({
                "column": col,
                "rule": f"min >= {min_val}",
                "actual": float(series.min()),
                "label": rule.get("label", col),
            })
        if max_val is not None and series.max() > max_val:
            violations.append({
                "column": col,
                "rule": f"max <= {max_val}",
                "actual": float(series.max()),
                "label": rule.get("label", col),
            })

    return {
        "ok": len(violations) == 0,
        "rules_checked": len(applicable_rules),
        "violations": violations,
        "warnings": [],
    }
