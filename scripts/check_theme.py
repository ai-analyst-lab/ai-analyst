"""Single-command theme checker — the autograder for the build-your-own-theme module.

Runs all three theme gates against one theme (or all themes) and explains
exactly what failed and how to fix it:

    1. Color-conflict lint (scripts/lint_chart_colors.py)
    2. WCAG contrast (scripts/lint_wcag.py)
    3. Base-key sync (scripts/check_theme_sync.py)

Usage:
    python scripts/check_theme.py <theme-name>
    python scripts/check_theme.py --all
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow imports from repo root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from helpers.theme_loader import ThemeNotFoundError, list_themes, load_theme  # noqa: E402

from check_theme_sync import check_brand  # noqa: E402
from lint_chart_colors import lint_theme as lint_colors  # noqa: E402
from lint_wcag import lint_theme as lint_wcag  # noqa: E402

FIX_HINTS = {
    "categorical >= 6 colors": "Add colors to colors.categorical until there are at least 6.",
    "no duplicate categorical colors": "Two entries in colors.categorical are identical — make each unique.",
    "highlight colors all distinct": "highlight.focus, highlight.comparison, and highlight.alert must be three different colors.",
    "primary in categorical palette": "colors.primary must also appear in colors.categorical (it's used for series).",
}


def check_one(name: str, themes_dir: str, level: str) -> bool:
    """Run all three gates on one theme. Returns True if everything passed."""
    print(f"\n=== Theme: {name} ===")
    try:
        load_theme(name, themes_dir=themes_dir)
    except ThemeNotFoundError as exc:
        print(f"  [FAIL] {exc}")
        return False

    passed = True

    print("\n  Gate 1 — color conflicts:")
    for check, ok in lint_colors(name, themes_dir):
        print(f"    [{'PASS' if ok else 'FAIL'}] {check}")
        if not ok:
            passed = False
            hint = FIX_HINTS.get(check)
            if hint:
                print(f"           fix: {hint}")

    print("\n  Gate 2 — WCAG contrast:")
    for check, ok, ratio in lint_wcag(name, themes_dir, level):
        print(f"    [{'PASS' if ok else 'FAIL'}] {check}  (ratio: {ratio:.2f})")
        if not ok:
            passed = False
            print("           fix: darken the color (or lighten the background) until the ratio clears the threshold.")

    if name != "analytics":
        print("\n  Gate 3 — base-key sync:")
        ok, extras = check_brand(name, themes_dir)
        print(f"    [{'PASS' if ok else 'FAIL'}] all override keys exist in _base.yaml")
        if not ok:
            passed = False
            for e in extras:
                print(f"           unknown key: {e} — check spelling against themes/_base.yaml")

    print(f"\n  {'ALL GATES GREEN — theme is ready to use.' if passed else 'NOT READY — fix the failures above and re-run.'}")
    return passed


def main() -> None:
    parser = argparse.ArgumentParser(description="Run all theme gates on one theme (or all).")
    parser.add_argument("theme", nargs="?", help="Theme name (e.g. fivethirtyeight)")
    parser.add_argument("--all", action="store_true", help="Check every available theme")
    parser.add_argument("--themes-dir", default="themes", help="Themes directory (default: themes)")
    parser.add_argument("--level", default="AA", choices=["AA", "AAA"], help="WCAG level (default: AA)")
    args = parser.parse_args()

    if not args.theme and not args.all:
        names = list_themes(args.themes_dir)
        parser.error(f"name a theme or pass --all. Available: {', '.join(names)}")

    targets = list_themes(args.themes_dir) if args.all else [args.theme]
    results = [check_one(name, args.themes_dir, args.level) for name in targets]
    print()
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
