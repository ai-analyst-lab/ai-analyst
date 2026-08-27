"""
Palette-aware utilities bridging the theme system and chart creation.

This module sits between theme_loader (which reads YAML themes) and
chart_helpers (which builds charts). It translates theme color definitions
into matplotlib rcParams, provides convenience accessors for highlight and
categorical palettes, generates smart palettes for arbitrary n, and
enforces WCAG contrast requirements.

Usage:
    from helpers.viz.theme_loader import load_theme
    from helpers.viz.chart_palette import (
        apply_theme_colors, highlight_palette, categorical_colors,
        ensure_contrast, palette_for_n, format_hex,
    )

    theme = load_theme("analytics")
    apply_theme_colors(theme)

    colors = highlight_palette(theme)
    # colors["focus"]      -> "#4878CF"
    # colors["comparison"] -> "#B0B0B0"
    # colors["alert"]      -> "#D65F5F"
"""

from __future__ import annotations


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def apply_theme_colors(theme: dict) -> None:
    """Update matplotlib rcParams with colors from the theme.

    Sets the default color cycle, background colors, and text colors so that
    every subsequent chart inherits the theme without manual per-chart
    configuration.  Call once at analysis start.

    Args:
        theme: Parsed theme dict (as returned by ``load_theme()``).
              Expected keys under ``theme["colors"]``: ``categorical``,
              ``background``, ``text``, ``text_light``.
    """
    import matplotlib as mpl
    import matplotlib.pyplot as plt

    colors = theme["colors"]

    # Color cycle from the categorical palette
    mpl.rcParams["axes.prop_cycle"] = plt.cycler(color=colors["categorical"])

    # Backgrounds
    mpl.rcParams["axes.facecolor"] = colors["background"]
    mpl.rcParams["figure.facecolor"] = colors["background"]

    # Text
    mpl.rcParams["text.color"] = colors["text"]
    mpl.rcParams["axes.labelcolor"] = colors["text"]

    # Ticks
    mpl.rcParams["xtick.color"] = colors["text_light"]
    mpl.rcParams["ytick.color"] = colors["text_light"]


def highlight_palette(theme: dict) -> dict:
    """Return a dict of highlight colors for use with highlight_bar / highlight_line.

    Args:
        theme: Parsed theme dict.

    Returns:
        Dict with keys ``focus``, ``comparison``, ``alert`` mapped to hex
        color strings.
    """
    hl = theme["colors"]["highlight"]
    return {
        "focus": hl["focus"],
        "comparison": hl["comparison"],
        "alert": hl["alert"],
    }


def categorical_colors(theme: dict, n: int | None = None) -> list[str]:
    """Return the first *n* colors from the categorical palette.

    Args:
        theme: Parsed theme dict.
        n: Number of colors to return.  ``None`` returns the full palette.
           Capped at the palette length (no IndexError).

    Returns:
        List of hex color strings.
    """
    palette = list(theme["colors"]["categorical"])
    if n is None:
        return palette
    n = max(0, min(n, len(palette)))
    return palette[:n]


def ensure_contrast(
    hex_color: str,
    background: str = "#F7F6F2",
    min_ratio: float = 4.5,
) -> str:
    """Adjust *hex_color* so it meets WCAG contrast against *background*.

    Uses the WCAG 2.1 relative-luminance formula with proper sRGB
    linearization.  If the color already passes, it is returned unchanged.
    Otherwise it is progressively darkened (or lightened when the background
    is dark) until the threshold is met.

    Args:
        hex_color: Foreground color in hex (``"#RRGGBB"`` or ``"#RGB"``).
        background: Background color in hex.
        min_ratio: Minimum WCAG contrast ratio.  Default ``4.5`` (AA normal
                   text).

    Returns:
        Hex color string (uppercase, 6-digit) meeting the contrast requirement.
    """
    fg = _hex_to_rgb(format_hex(hex_color))
    bg = _hex_to_rgb(format_hex(background))

    fg_lum = _relative_luminance(*fg)
    bg_lum = _relative_luminance(*bg)

    if _contrast_ratio(fg_lum, bg_lum) >= min_ratio:
        return format_hex(hex_color)

    # Decide direction: darken foreground if background is light, else lighten
    bg_is_light = bg_lum > 0.5
    step = -0.02 if bg_is_light else 0.02  # shift lightness

    r, g, b = fg
    for _ in range(200):  # safety cap
        # Shift each channel toward 0 (darken) or 255 (lighten)
        if bg_is_light:
            r = max(0, r - 255 * 0.02)
            g = max(0, g - 255 * 0.02)
            b = max(0, b - 255 * 0.02)
        else:
            r = min(255, r + 255 * 0.02)
            g = min(255, g + 255 * 0.02)
            b = min(255, b + 255 * 0.02)

        new_lum = _relative_luminance(r, g, b)
        if _contrast_ratio(new_lum, bg_lum) >= min_ratio:
            break

    return _rgb_to_hex(int(round(r)), int(round(g)), int(round(b)))


def palette_for_n(theme: dict, n: int) -> list[str]:
    """Return exactly *n* colors, choosing the best strategy for the count.

    - ``n <= 8``: first *n* categorical colors (distinct, colorblind-safe).
    - ``n > 8``:  *n* evenly-spaced samples from the sequential colormap.

    Args:
        theme: Parsed theme dict.
        n: Number of colors needed.

    Returns:
        List of *n* hex color strings.
    """
    if n <= 0:
        return []

    cat = theme["colors"]["categorical"]
    if n <= len(cat):
        return list(cat[:n])

    # Fall back to sequential colormap sampling
    import matplotlib.colors as mcolors
    import numpy as np

    seq = theme["colors"]["sequential"]
    cmap = mcolors.LinearSegmentedColormap.from_list(
        "theme_seq",
        [seq["low"], seq["mid"], seq["high"]],
        N=256,
    )
    positions = np.linspace(0.0, 1.0, n)
    return [
        _rgb_to_hex(
            int(round(cmap(p)[0] * 255)),
            int(round(cmap(p)[1] * 255)),
            int(round(cmap(p)[2] * 255)),
        )
        for p in positions
    ]


def format_hex(color: str) -> str:
    """Normalize a hex color to uppercase 6-digit format (e.g. ``"#4878CF"``).

    Handles 3-digit shorthand (``"#ABC"`` -> ``"#AABBCC"``) and strips
    surrounding whitespace.

    Args:
        color: Hex color string with leading ``#``.

    Returns:
        Uppercase 6-digit hex string.
    """
    color = color.strip()
    if not color.startswith("#"):
        color = "#" + color
    raw = color[1:]
    if len(raw) == 3:
        raw = raw[0] * 2 + raw[1] * 2 + raw[2] * 2
    return "#" + raw.upper()[:6]


# ---------------------------------------------------------------------------
# Internal helpers — WCAG contrast
# ---------------------------------------------------------------------------


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Parse a 6-digit hex string to (R, G, B) integers 0-255."""
    h = hex_color.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _rgb_to_hex(r: int, g: int, b: int) -> str:
    """Convert (R, G, B) integers 0-255 to an uppercase hex string."""
    r = max(0, min(255, r))
    g = max(0, min(255, g))
    b = max(0, min(255, b))
    return f"#{r:02X}{g:02X}{b:02X}"


def _linearize(channel_8bit: float) -> float:
    """Convert an sRGB channel value (0-255) to linear RGB (0-1).

    Implements the sRGB transfer function inverse per IEC 61966-2-1.
    """
    s = channel_8bit / 255.0
    if s <= 0.04045:
        return s / 12.92
    return ((s + 0.055) / 1.055) ** 2.4


def _relative_luminance(r: float, g: float, b: float) -> float:
    """WCAG 2.1 relative luminance from (R, G, B) in 0-255 range."""
    return (
        0.2126 * _linearize(r)
        + 0.7152 * _linearize(g)
        + 0.0722 * _linearize(b)
    )


def _contrast_ratio(lum1: float, lum2: float) -> float:
    """WCAG contrast ratio between two relative luminance values."""
    lighter = max(lum1, lum2)
    darker = min(lum1, lum2)
    return (lighter + 0.05) / (darker + 0.05)
