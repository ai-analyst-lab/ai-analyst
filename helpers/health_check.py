from __future__ import annotations

"""
Health Check — validates system state, knowledge integrity, and data connectivity.

Used by /setup status, knowledge-bootstrap, and diagnostic commands.
Checks: setup state, knowledge file integrity, data source connectivity,
helper module imports, and configuration consistency.
"""

from pathlib import Path
from typing import Any

try:
    import yaml
    _YAML_AVAILABLE = True
except ImportError:
    _YAML_AVAILABLE = False


_KNOWLEDGE_DIR = Path(".knowledge")


def check_setup_state() -> dict:
    """Check if setup has been completed.

    Returns:
        dict with ok, setup_complete, phases_complete, phases_total, message
    """
    state_path = _KNOWLEDGE_DIR / "setup-state.yaml"
    if not state_path.exists():
        return {
            "ok": False,
            "setup_complete": False,
            "phases_complete": 0,
            "phases_total": 4,
            "message": "No setup-state.yaml found. Run /setup to begin.",
        }

    if not _YAML_AVAILABLE:
        return {
            "ok": False,
            "setup_complete": False,
            "phases_complete": 0,
            "phases_total": 4,
            "message": "PyYAML not installed. pip install pyyaml",
        }

    try:
        with open(state_path) as f:
            state = yaml.safe_load(f)
    except Exception as e:
        return {
            "ok": False,
            "setup_complete": False,
            "phases_complete": 0,
            "phases_total": 4,
            "message": f"Error reading setup-state.yaml: {e}",
        }

    if not isinstance(state, dict):
        return {
            "ok": False,
            "setup_complete": False,
            "phases_complete": 0,
            "phases_total": 4,
            "message": "setup-state.yaml is malformed",
        }

    phases = state.get("phases", {})
    complete_count = sum(
        1 for p in phases.values()
        if isinstance(p, dict) and p.get("status") == "complete"
    )

    return {
        "ok": state.get("setup_complete", False),
        "setup_complete": state.get("setup_complete", False),
        "phases_complete": complete_count,
        "phases_total": 4,
        "message": f"Setup {'complete' if state.get('setup_complete') else 'incomplete'}: {complete_count}/4 phases done",
    }


def check_knowledge_integrity() -> dict:
    """Verify that expected knowledge directories and files exist and parse.

    Returns:
        dict with ok, checks (list of {path, exists, parseable, message})
    """
    checks = []

    expected_dirs = [
        "datasets",
        "corrections",
        "learnings",
        "query-archaeology",
        "analyses",
        "global",
    ]

    for dir_name in expected_dirs:
        dir_path = _KNOWLEDGE_DIR / dir_name
        checks.append({
            "path": str(dir_path),
            "exists": dir_path.exists(),
            "parseable": None,
            "message": "OK" if dir_path.exists() else f"Missing directory: {dir_name}",
        })

    # Check key YAML files
    yaml_files = [
        "active.yaml",
        "setup-state.yaml",
        "corrections/log.yaml",
        "corrections/index.yaml",
        "analyses/index.yaml",
    ]

    for rel_path in yaml_files:
        file_path = _KNOWLEDGE_DIR / rel_path
        check = {
            "path": str(file_path),
            "exists": file_path.exists(),
            "parseable": None,
            "message": "",
        }

        if file_path.exists() and _YAML_AVAILABLE:
            try:
                with open(file_path) as f:
                    yaml.safe_load(f)
                check["parseable"] = True
                check["message"] = "OK"
            except Exception as e:
                check["parseable"] = False
                check["message"] = f"Parse error: {e}"
        elif file_path.exists():
            check["message"] = "File exists but YAML not available to validate"
        else:
            check["message"] = f"Not found (created by setup or first use)"

        checks.append(check)

    all_ok = all(
        c["exists"] for c in checks
        if c["path"].endswith(("datasets", "corrections", "learnings"))
    )

    return {
        "ok": all_ok,
        "checks": checks,
    }


def check_data_connectivity() -> dict:
    """Check if a data source is connected and accessible.

    Returns:
        dict with ok, source, type, message
    """
    try:
        from helpers.data_helpers import detect_active_source, check_connection
        source = detect_active_source()
        if source.get("type") == "none":
            return {
                "ok": False,
                "source": source.get("source", "unknown"),
                "type": "none",
                "message": "No data source connected. Run /connect-data.",
            }
        result = check_connection(source)
        return result
    except Exception as e:
        return {
            "ok": False,
            "source": "unknown",
            "type": "error",
            "message": f"Error checking connectivity: {e}",
        }


def check_helper_imports() -> dict:
    """Verify all helper modules can be imported.

    Returns:
        dict with ok, modules (list of {name, importable, message})
    """
    modules_to_check = [
        "helpers.data_helpers",
        "helpers.chart_helpers",
        "helpers.sql_helpers",
        "helpers.stats_helpers",
        "helpers.error_helpers",
        "helpers.file_helpers",
        "helpers.schema_profiler",
        "helpers.connection_manager",
        "helpers.sql_dialect",
        "helpers.lineage_tracker",
        "helpers.analytics_helpers",
    ]

    results = []
    for mod_name in modules_to_check:
        try:
            __import__(mod_name)
            results.append({"name": mod_name, "importable": True, "message": "OK"})
        except Exception as e:
            results.append({"name": mod_name, "importable": False, "message": str(e)})

    return {
        "ok": all(r["importable"] for r in results),
        "modules": results,
    }


def run_health_check() -> dict:
    """Run all health checks and return a combined report.

    Returns:
        dict with overall_ok, setup, knowledge, data, helpers, summary
    """
    setup = check_setup_state()
    knowledge = check_knowledge_integrity()
    data = check_data_connectivity()
    helpers = check_helper_imports()

    overall = setup["ok"] and knowledge["ok"] and helpers["ok"]
    # Data connectivity is soft — system works without it (just can't analyze)

    checks_passed = sum([
        setup["ok"],
        knowledge["ok"],
        data["ok"],
        helpers["ok"],
    ])

    return {
        "overall_ok": overall,
        "setup": setup,
        "knowledge": knowledge,
        "data": data,
        "helpers": helpers,
        "summary": f"{checks_passed}/4 checks passed",
    }
