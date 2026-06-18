#!/usr/bin/env python3
"""Check import layer rules in helpers/ to prevent circular dependencies.

Layer 0: stdlib + yaml only (no project imports)
Layer 1: file_helpers
Layer 2: entity_resolver, business_context, miss_rate_logger,
         archaeology_helpers, context_loader, schema_migration, pipeline_state
Layer 3: chart_helpers, chart_palette, theme_loader, data_helpers,
         sql_helpers, error_helpers, stats_helpers, sql_dialect,
         connection_manager, schema_profiler
Layer 4: confidence_scoring, structural_validator, logical_validator,
         business_rules, simpsons_paradox, business_validation,
         health_check, metric_validator

A module may only import from its own layer or lower layers.
"""

import ast
import sys
from pathlib import Path

HELPERS_DIR = Path(__file__).resolve().parent.parent / "helpers"

# Module name -> layer assignment
LAYER_MAP = {
    # Layer 1
    "file_helpers": 1,
    # Layer 2
    "entity_resolver": 2, "business_context": 2, "miss_rate_logger": 2,
    "archaeology_helpers": 2, "context_loader": 2, "schema_migration": 2,
    "pipeline_state": 2,
    # Layer 3
    "chart_helpers": 3, "chart_palette": 3, "theme_loader": 3,
    "data_helpers": 3, "sql_helpers": 3,
    "error_helpers": 3, "stats_helpers": 3, "sql_dialect": 3,
    "connection_manager": 3, "schema_profiler": 3,
    # Layer 4
    "confidence_scoring": 4, "structural_validator": 4,
    "logical_validator": 4, "business_rules": 4, "simpsons_paradox": 4,
    "business_validation": 4, "health_check": 4, "metric_validator": 4,
}


def get_layer(module_name: str) -> int:
    """Return the layer for a module. Unlisted modules default to layer 0."""
    return LAYER_MAP.get(module_name, 0)


def extract_local_imports(filepath: Path) -> list[str]:
    """Parse a Python file and return names of helpers/ modules it imports."""
    source = filepath.read_text()
    tree = ast.parse(source, filename=str(filepath))
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                parts = alias.name.split(".")
                if parts[0] == "helpers" and len(parts) > 1:
                    imported.append(parts[1])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                parts = node.module.split(".")
                if parts[0] == "helpers" and len(parts) > 1:
                    imported.append(parts[1])
    return imported


def main() -> int:
    py_files = sorted(HELPERS_DIR.glob("*.py"))
    py_files = [f for f in py_files if f.name != "__init__.py"]

    violations = []
    checked = []

    for filepath in py_files:
        mod_name = filepath.stem
        mod_layer = get_layer(mod_name)
        imports = extract_local_imports(filepath)
        checked.append((mod_name, mod_layer))

        for imp in imports:
            imp_layer = get_layer(imp)
            if imp_layer > mod_layer:
                violations.append(
                    (mod_name, mod_layer, imp, imp_layer)
                )

    # --- Summary ---
    print("=" * 60)
    print("  Import Layer Check")
    print("=" * 60)

    # Layer assignments
    for layer in range(5):
        members = [n for n, l in checked if l == layer]
        if members:
            print(f"\n  Layer {layer}: {', '.join(members)}")

    print(f"\n  Modules checked: {len(checked)}")

    if violations:
        print(f"\n  VIOLATIONS FOUND: {len(violations)}")
        print("-" * 60)
        for mod, ml, imp, il in violations:
            print(f"  {mod} (L{ml}) imports {imp} (L{il})")
        print("-" * 60)
        print("  FAIL — fix the imports listed above.")
        return 1
    else:
        print("\n  No violations found.")
        print("  PASS — all imports respect layer boundaries.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
