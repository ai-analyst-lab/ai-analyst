"""Generate a theme cheat sheet / reference for a given theme."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow imports from repo root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from helpers.viz.theme_loader import load_theme


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a theme reference summary.")
    parser.add_argument("--theme", default="analytics", help="Theme name (default: analytics)")
    parser.add_argument("--themes-dir", default="themes", help="Themes directory (default: themes)")
    args = parser.parse_args()

    theme = load_theme(args.theme, themes_dir=args.themes_dir)

    meta = theme.get("theme", {})
    colors = theme.get("colors", {})
    typo = theme.get("typography", {})
    charts = theme.get("charts", {})

    # Header
    print(f"{'=' * 60}")
    print(f"  Theme: {meta.get('display_name', meta.get('name', 'unknown'))}")
    print(f"  {meta.get('description', '')}")
    print(f"{'=' * 60}")

    # Color palette
    print("\n--- Color Palette ---")
    for key in ("primary", "secondary", "accent", "neutral", "background", "text", "text_light"):
        if key in colors:
            print(f"  {key:<14} {colors[key]}")

    print("\n  Categorical:")
    for i, c in enumerate(colors.get("categorical", [])):
        print(f"    [{i}] {c}")

    seq = colors.get("sequential", {})
    if seq:
        print(f"\n  Sequential:  {seq.get('low')} -> {seq.get('mid')} -> {seq.get('high')}")

    div = colors.get("diverging", {})
    if div:
        print(f"  Diverging:   {div.get('negative')} -> {div.get('neutral')} -> {div.get('positive')}")

    hl = colors.get("highlight", {})
    if hl:
        print(f"\n  Highlight:")
        for k, v in hl.items():
            print(f"    {k:<14} {v}")

    # Typography
    print("\n--- Typography ---")
    print(f"  Font family:   {typo.get('font_family', 'N/A')}")
    print(f"  Heading font:  {typo.get('heading_font', 'N/A')}")
    print(f"  Monospace:     {typo.get('monospace_font', 'N/A')}")
    sizes = typo.get("sizes", {})
    if sizes:
        print("  Sizes (pt):")
        for k, v in sizes.items():
            print(f"    {k:<14} {v}")

    # Chart defaults
    print("\n--- Chart Defaults ---")
    fig = charts.get("figure", {})
    if fig:
        print(f"  figsize:       {fig.get('figsize')}")
        print(f"  dpi:           {fig.get('dpi')}")
        print(f"  facecolor:     {fig.get('facecolor')}")
    bar = charts.get("bar", {})
    if bar:
        print(f"  bar default:   {bar.get('default_color')}")
        print(f"  bar highlight: {bar.get('highlight_color')}")
    line = charts.get("line", {})
    if line:
        print(f"  line default:  {line.get('default_color')}")
        print(f"  line highlight:{line.get('highlight_color')}")
        print(f"  line width:    {line.get('width')}")

    print()


if __name__ == "__main__":
    main()
