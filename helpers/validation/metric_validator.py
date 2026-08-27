from __future__ import annotations

"""
Metric Validator — validates metric definitions and calculated values.

Ensures metric YAML files are well-formed and that computed metric values
match their definitions. Used by the /metrics skill and validation pipeline.
"""

from pathlib import Path
from typing import Any

try:
    import yaml
    _YAML_AVAILABLE = True
except ImportError:
    _YAML_AVAILABLE = False


# Required fields for a metric definition
_REQUIRED_FIELDS = ["name", "display_name", "definition"]
_OPTIONAL_FIELDS = [
    "sql_template", "grain", "owner", "target", "guardrails",
    "segments", "caveats", "added_at", "last_validated", "status",
    "min_value", "max_value",
]
_VALID_STATUSES = ["active", "deprecated", "draft"]


def validate_metric_definition(metric: dict) -> dict:
    """Validate a metric definition dict against the schema.

    Args:
        metric: Dict loaded from a metric YAML file.

    Returns:
        dict with ok, errors (list[str]), warnings (list[str])
    """
    errors = []
    warnings = []

    if not isinstance(metric, dict):
        return {"ok": False, "errors": ["Metric must be a dict"], "warnings": []}

    # Check required fields
    for field in _REQUIRED_FIELDS:
        if field not in metric:
            errors.append(f"Missing required field: {field}")
        elif not metric[field]:
            errors.append(f"Empty required field: {field}")

    # Validate name format (snake_case)
    name = metric.get("name", "")
    if name and not all(c.isalnum() or c == "_" for c in name):
        warnings.append(f"Metric name '{name}' should be snake_case")

    # Validate status
    status = metric.get("status")
    if status and status not in _VALID_STATUSES:
        errors.append(f"Invalid status '{status}'. Must be one of: {_VALID_STATUSES}")

    # Validate guardrails is a list
    guardrails = metric.get("guardrails")
    if guardrails is not None and not isinstance(guardrails, list):
        errors.append("guardrails must be a list")

    # Validate min/max
    min_val = metric.get("min_value")
    max_val = metric.get("max_value")
    if min_val is not None and max_val is not None:
        if min_val > max_val:
            errors.append(f"min_value ({min_val}) > max_value ({max_val})")

    # Warnings for recommended fields
    if "sql_template" not in metric:
        warnings.append("No sql_template — metric may be hard to compute automatically")
    if "grain" not in metric:
        warnings.append("No grain specified — may cause aggregation confusion")
    if "owner" not in metric:
        warnings.append("No owner — accountability unclear")

    return {
        "ok": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
    }


def validate_metric_file(file_path: str | Path) -> dict:
    """Validate a metric YAML file on disk.

    Args:
        file_path: Path to the YAML file.

    Returns:
        dict with ok, errors, warnings, metric_name
    """
    path = Path(file_path)
    if not path.exists():
        return {"ok": False, "errors": [f"File not found: {path}"], "warnings": [], "metric_name": None}

    if not _YAML_AVAILABLE:
        return {"ok": False, "errors": ["PyYAML not installed"], "warnings": [], "metric_name": None}

    try:
        with open(path) as f:
            data = yaml.safe_load(f)
    except Exception as e:
        return {"ok": False, "errors": [f"YAML parse error: {e}"], "warnings": [], "metric_name": None}

    result = validate_metric_definition(data)
    result["metric_name"] = data.get("name") if isinstance(data, dict) else None
    return result


def validate_all_metrics(dataset_id: str, knowledge_dir: str | Path | None = None) -> dict:
    """Validate all metric files for a dataset.

    Args:
        dataset_id: Dataset identifier.
        knowledge_dir: Override knowledge directory path.

    Returns:
        dict with ok, total, valid, invalid, results (list per file)
    """
    base = Path(knowledge_dir) if knowledge_dir else Path(".knowledge")
    metrics_dir = base / "datasets" / dataset_id / "metrics"

    if not metrics_dir.is_dir():
        return {"ok": True, "total": 0, "valid": 0, "invalid": 0, "results": []}

    results = []
    for f in sorted(metrics_dir.glob("*.yaml")):
        if f.name.startswith("_") or f.name == "index.yaml":
            continue
        result = validate_metric_file(f)
        result["file"] = str(f)
        results.append(result)

    valid = sum(1 for r in results if r["ok"])
    invalid = sum(1 for r in results if not r["ok"])

    return {
        "ok": invalid == 0,
        "total": len(results),
        "valid": valid,
        "invalid": invalid,
        "results": results,
    }


def check_metric_value(value: Any, metric: dict) -> dict:
    """Check if a computed metric value is plausible given its definition.

    Args:
        value: The computed value to check.
        metric: The metric definition dict.

    Returns:
        dict with ok, warnings
    """
    warnings = []

    if value is None:
        return {"ok": True, "warnings": ["Metric value is None"]}

    try:
        num_value = float(value)
    except (TypeError, ValueError):
        return {"ok": False, "warnings": [f"Non-numeric value: {value}"]}

    min_val = metric.get("min_value")
    max_val = metric.get("max_value")

    if min_val is not None and num_value < min_val:
        warnings.append(f"Value {num_value} below min {min_val}")
    if max_val is not None and num_value > max_val:
        warnings.append(f"Value {num_value} above max {max_val}")

    target = metric.get("target")
    if target is not None:
        try:
            pct_diff = abs(num_value - float(target)) / float(target) * 100
            if pct_diff > 50:
                warnings.append(f"Value {num_value} is {pct_diff:.0f}% away from target {target}")
        except (ZeroDivisionError, TypeError, ValueError):
            pass

    return {
        "ok": len(warnings) == 0 or all("away from target" in w for w in warnings),
        "warnings": warnings,
    }
