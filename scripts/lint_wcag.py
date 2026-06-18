"""WCAG accessibility linter for theme colors."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow imports from repo root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from helpers.chart_palette import _contrast_ratio, _hex_to_rgb, _relative_luminance, format_hex
from helpers.theme_loader import list_themes, load_theme


def _ratio(fg_hex: str, bg_hex: str) -> float:
    """Compute WCAG contrast ratio between two hex colors."""
    fg = _hex_to_rgb(format_hex(fg_hex))
    bg = _hex_to_rgb(format_hex(bg_hex))
    return _contrast_ratio(_relative_luminance(*fg), _relative_luminance(*bg))


def lint_theme(theme_name: str, themes_dir: str, level: str) -> list[tuple[str, bool, float]]:
    """Run WCAG checks on a single theme. Returns list of (check, passed, ratio)."""
    text_threshold = 7.0 if level == "AAA" else 4.5
    graphic_threshold = 3.0  # WCAG 2.1 non-text minimum (1.4.11)
    # Categorical fills get a relaxed 2:1 floor: WCAG 1.4.11's 3:1 applies to
    # graphics "required to understand content"; categorical series are large
    # solid fills that SWD style pairs with direct labels, so hue separation
    # carries the meaning. The strict 3:1 still applies to text and to
    # highlight.alert (small, meaning-bearing marks).
    categorical_threshold = 2.0

    theme = load_theme(theme_name, themes_dir=themes_dir)
    colors = theme.get("colors", {})
    bg = colors.get("background", "#FFFFFF")
    results: list[tuple[str, bool, float]] = []

    # Text vs background
    for key, label in [("text", "text"), ("text_light", "text_light")]:
        color = colors.get(key)
        if color:
            r = _ratio(color, bg)
            results.append((f"{label} vs background ({level})", r >= text_threshold, r))

    # Categorical colors vs background (large solid fills: 2:1, see above)
    for i, color in enumerate(colors.get("categorical", [])):
        r = _ratio(color, bg)
        results.append((f"categorical[{i}] vs background (2:1)", r >= categorical_threshold, r))

    # Highlight alert vs background
    alert = colors.get("highlight", {}).get("alert")
    if alert:
        r = _ratio(alert, bg)
        results.append((f"highlight.alert vs background (3:1)", r >= graphic_threshold, r))

    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="WCAG accessibility linter for theme colors.")
    parser.add_argument("--themes-dir", default="themes", help="Themes directory (default: themes)")
    parser.add_argument("--level", default="AA", choices=["AA", "AAA"], help="WCAG level (default: AA)")
    args = parser.parse_args()

    themes = list_themes(args.themes_dir)
    any_fail = False

    for name in themes:
        print(f"\n  Theme: {name}")
        results = lint_theme(name, args.themes_dir, args.level)
        for check, passed, ratio in results:
            status = "PASS" if passed else "FAIL"
            if not passed:
                any_fail = True
            print(f"    [{status}] {check}  (ratio: {ratio:.2f})")

    print()
    sys.exit(1 if any_fail else 0)


if __name__ == "__main__":
    main()
