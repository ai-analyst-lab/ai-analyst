"""Verify brand themes only override keys that exist in the base theme."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow imports from repo root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from helpers.pipeline.file_helpers import safe_read_yaml
from helpers.viz.theme_loader import list_themes

# Top-level sections allowed to differ freely between brand and base
EXEMPT_SECTIONS = {"theme"}


def _collect_key_paths(d: dict, prefix: str = "") -> set[str]:
    """Recursively collect all leaf and branch key paths from a dict."""
    paths: set[str] = set()
    for key, value in d.items():
        full = f"{prefix}.{key}" if prefix else key
        paths.add(full)
        if isinstance(value, dict):
            paths.update(_collect_key_paths(value, full))
    return paths


def check_brand(brand_name: str, themes_dir: str) -> tuple[bool, list[str]]:
    """Check a single brand theme against the base. Returns (passed, extra_keys)."""
    brand_path = Path(themes_dir).resolve() / "brands" / brand_name / "theme.yaml"
    base_path = Path(themes_dir).resolve() / "_base.yaml"

    brand_data = safe_read_yaml(brand_path)
    base_data = safe_read_yaml(base_path)

    if brand_data is None or base_data is None:
        return False, ["could not load theme files"]

    # Filter out exempt sections before collecting paths
    brand_filtered = {k: v for k, v in brand_data.items() if k not in EXEMPT_SECTIONS}
    base_filtered = {k: v for k, v in base_data.items() if k not in EXEMPT_SECTIONS}

    brand_paths = _collect_key_paths(brand_filtered)
    base_paths = _collect_key_paths(base_filtered)

    extra = sorted(brand_paths - base_paths)
    return len(extra) == 0, extra


def main() -> None:
    parser = argparse.ArgumentParser(description="Check brand themes reference valid base keys.")
    parser.add_argument("--themes-dir", default="themes", help="Themes directory (default: themes)")
    args = parser.parse_args()

    themes = list_themes(args.themes_dir)
    brand_themes = [t for t in themes if t != "analytics"]
    any_fail = False

    if not brand_themes:
        print("  No brand themes found. Nothing to check.")
        sys.exit(0)

    for name in brand_themes:
        passed, extras = check_brand(name, args.themes_dir)
        status = "PASS" if passed else "FAIL"
        if not passed:
            any_fail = True
        print(f"\n  [{status}] Brand: {name}")
        if extras:
            for e in extras:
                print(f"    Extra key not in base: {e}")

    print()
    sys.exit(1 if any_fail else 0)


if __name__ == "__main__":
    main()
