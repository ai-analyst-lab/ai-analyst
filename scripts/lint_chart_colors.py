"""Lint chart colors for conflicts and issues across all themes."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow imports from repo root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from helpers.viz.theme_loader import list_themes, load_theme


def lint_theme(theme_name: str, themes_dir: str) -> list[tuple[str, bool]]:
    """Run color lint checks on a single theme. Returns list of (check_name, passed)."""
    theme = load_theme(theme_name, themes_dir=themes_dir)
    colors = theme.get("colors", {})
    results: list[tuple[str, bool]] = []

    # 1. Categorical palette has at least 6 colors
    cat = colors.get("categorical", [])
    results.append(("categorical >= 6 colors", len(cat) >= 6))

    # 2. No duplicate colors in categorical palette
    upper = [c.strip().upper() for c in cat]
    results.append(("no duplicate categorical colors", len(upper) == len(set(upper))))

    # 3. Highlight colors are distinct from each other
    hl = colors.get("highlight", {})
    focus = hl.get("focus", "").strip().upper()
    comparison = hl.get("comparison", "").strip().upper()
    alert = hl.get("alert", "").strip().upper()
    all_distinct = len({focus, comparison, alert}) == 3
    results.append(("highlight colors all distinct", all_distinct))

    # 4. Primary color appears in categorical palette
    primary = colors.get("primary", "").strip().upper()
    results.append(("primary in categorical palette", primary in upper))

    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Lint chart colors for all themes.")
    parser.add_argument("--themes-dir", default="themes", help="Themes directory (default: themes)")
    args = parser.parse_args()

    themes = list_themes(args.themes_dir)
    any_fail = False

    for name in themes:
        print(f"\n  Theme: {name}")
        results = lint_theme(name, args.themes_dir)
        for check, passed in results:
            status = "PASS" if passed else "FAIL"
            if not passed:
                any_fail = True
            print(f"    [{status}] {check}")

    print()
    sys.exit(1 if any_fail else 0)


if __name__ == "__main__":
    main()
