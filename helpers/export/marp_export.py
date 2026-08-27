"""Marp CLI export wrapper — generates PDF and HTML from Marp decks.

Functions:
  export_pdf(deck_path, theme)  — export to PDF
  export_html(deck_path, theme) — export to HTML
  export_both(deck_path, theme) — export both, return dict of paths

All functions resolve theme name to the correct CSS file path and check
for npx @marp-team/marp-cli availability before running.
"""

import subprocess
import shutil
from pathlib import Path


# Theme name → CSS file mapping
THEME_CSS = {
    "analytics": "analytics-light.css",
    "analytics-light": "analytics-light.css",
    "analytics-dark": "analytics-dark.css",
}


def _find_themes_dir(deck_path):
    """Locate the themes/ directory relative to the deck file.

    Searches upward from the deck file's directory for a themes/ folder
    containing the expected CSS files.
    """
    deck_dir = Path(deck_path).resolve().parent
    # Search up to 3 levels up
    for parent in [deck_dir] + list(deck_dir.parents)[:3]:
        themes_dir = parent / "themes"
        if themes_dir.is_dir():
            return themes_dir
    return None


def _resolve_theme_css(theme, deck_path):
    """Resolve a theme name to the full CSS file path.

    Args:
        theme: Theme name (e.g., "analytics", "analytics-dark")
        deck_path: Path to the deck file (for relative resolution)

    Returns:
        Path to the CSS file.

    Raises:
        FileNotFoundError: If theme CSS cannot be found.
    """
    css_filename = THEME_CSS.get(theme)
    if not css_filename:
        raise ValueError(
            f"Unknown theme '{theme}'. Valid themes: {list(THEME_CSS.keys())}"
        )

    themes_dir = _find_themes_dir(deck_path)
    if themes_dir is None:
        raise FileNotFoundError(
            f"Cannot find themes/ directory relative to {deck_path}"
        )

    css_path = themes_dir / css_filename
    if not css_path.exists():
        raise FileNotFoundError(f"Theme CSS not found: {css_path}")

    return css_path


def _check_marp_cli():
    """Check if Marp CLI is available via npx.

    Returns:
        True if available, False otherwise.
    """
    try:
        result = subprocess.run(
            ["npx", "@marp-team/marp-cli", "--version"],
            capture_output=True, text=True, timeout=30,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def _run_marp(deck_path, theme, output_format):
    """Run Marp CLI to export a deck.

    Args:
        deck_path: Path to the .marp.md file.
        theme: Theme name.
        output_format: "pdf" or "html".

    Returns:
        Path to the generated output file.

    Raises:
        RuntimeError: If Marp CLI fails.
        FileNotFoundError: If theme CSS cannot be found.
    """
    deck_path = Path(deck_path).resolve()
    css_path = _resolve_theme_css(theme, deck_path)

    # Determine output path
    stem = deck_path.stem
    if stem.endswith(".marp"):
        stem = stem[:-5]  # Remove .marp from stem
    output_path = deck_path.parent / f"{stem}.{output_format}"

    cmd = [
        "npx", "@marp-team/marp-cli",
        "--no-stdin",
        f"--{output_format}",
        "--html",
        "--allow-local-files",
        "--theme", str(css_path),
        "--output", str(output_path),
        str(deck_path),
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(deck_path.parent),
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(
            f"Marp CLI timed out after 120s exporting {output_format}"
        )
    except FileNotFoundError:
        raise RuntimeError(
            "npx not found. Install Node.js and run: npm install -g @marp-team/marp-cli"
        )

    if result.returncode != 0:
        raise RuntimeError(
            f"Marp CLI failed (exit {result.returncode}):\n"
            f"stdout: {result.stdout}\n"
            f"stderr: {result.stderr}"
        )

    if not output_path.exists():
        raise RuntimeError(
            f"Marp CLI completed but output not found at {output_path}"
        )

    return output_path


def export_pdf(deck_path, theme="analytics"):
    """Export a Marp deck to PDF.

    Args:
        deck_path: Path to the .marp.md file.
        theme: Theme name (default: "analytics").

    Returns:
        Path to the generated PDF file.
    """
    return _run_marp(deck_path, theme, "pdf")


def export_html(deck_path, theme="analytics"):
    """Export a Marp deck to self-contained HTML.

    Args:
        deck_path: Path to the .marp.md file.
        theme: Theme name (default: "analytics").

    Returns:
        Path to the generated HTML file.
    """
    return _run_marp(deck_path, theme, "html")


def export_both(deck_path, theme="analytics"):
    """Export a Marp deck to both PDF and HTML.

    Args:
        deck_path: Path to the .marp.md file.
        theme: Theme name (default: "analytics").

    Returns:
        dict with keys "pdf" and "html", each mapping to the output Path.
    """
    pdf_path = export_pdf(deck_path, theme)
    html_path = export_html(deck_path, theme)
    return {"pdf": pdf_path, "html": html_path}


def check_ready():
    """Check if the export system is ready.

    Returns:
        dict with:
          - marp_cli: bool (is npx marp-cli available?)
          - node: bool (is node available?)
          - themes_available: list of available theme names
    """
    node_ok = shutil.which("node") is not None
    marp_ok = _check_marp_cli() if node_ok else False

    # Check for themes in common locations
    themes_available = []
    for theme_name, css_file in THEME_CSS.items():
        # Check common relative paths
        for base in [Path("."), Path(".."), Path("../..") ]:
            css_path = base / "themes" / css_file
            if css_path.exists():
                if theme_name not in themes_available:
                    themes_available.append(theme_name)
                break

    return {
        "marp_cli": marp_ok,
        "node": node_ok,
        "themes_available": themes_available,
    }


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        # Print readiness check
        status = check_ready()
        print(f"Node.js:    {'OK' if status['node'] else 'NOT FOUND'}")
        print(f"Marp CLI:   {'OK' if status['marp_cli'] else 'NOT FOUND'}")
        print(f"Themes:     {', '.join(status['themes_available']) or 'none found'}")
        if not status["marp_cli"]:
            print("\nInstall: npm install -g @marp-team/marp-cli")
        sys.exit(0)

    deck_path = sys.argv[1]
    theme = sys.argv[2] if len(sys.argv) > 2 else "analytics"
    fmt = sys.argv[3] if len(sys.argv) > 3 else "both"

    if fmt == "pdf":
        out = export_pdf(deck_path, theme)
        print(f"PDF: {out}")
    elif fmt == "html":
        out = export_html(deck_path, theme)
        print(f"HTML: {out}")
    else:
        out = export_both(deck_path, theme)
        print(f"PDF:  {out['pdf']}")
        print(f"HTML: {out['html']}")
