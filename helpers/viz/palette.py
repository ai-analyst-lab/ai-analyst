"""Canonical Storytelling With Data palette: the single source of truth for chart color.

Every color the chart system uses derives from the constants here, so the mplstyle,
``chart_helpers.COLORS``, and the default YAML theme cannot drift apart (they did: the focus
color was amber in one layer and two different blues in the others). See
knowledge-base/raw/research/storytelling-with-data-2026-08/SWD-ALIGNMENT.md.

The design is deliberately narrow. Most of a chart is gray context. Exactly one saturated accent
(FOCUS, blue) marks the thing the takeaway argues; a second accent (SECONDARY, orange) is held in
reserve for a two-focal or good-vs-bad case and for diverging ramps. FOCUS and SECONDARY are both
canonical Okabe-Ito colors, so the accent pair is colorblind-safe by construction (blue vs orange,
never red vs green). Amber stays the BRAND color elsewhere (thumbnails, decks); it is retired only
from the chart focus role.
"""
from __future__ import annotations

# --- The two accents (both Okabe-Ito, so the pair is colorblind-safe) ---
FOCUS = "#0072B2"       # Okabe-Ito blue: the ONE series/point the takeaway argues
SECONDARY = "#D55E00"   # Okabe-Ito vermilion: second focal / negative / diverging low

# --- Gray context ramp (single hue, colorblind-safe by construction) ---
CONTEXT_LIGHTEST = "#F0F0F0"
CONTEXT_LIGHT = "#E0E0E0"
CONTEXT = "#BDBDBD"      # default for all non-focal data
CONTEXT_DARK = "#757575"
CONTEXT_DARKEST = "#404040"
GRAY_RAMP = [CONTEXT_LIGHTEST, CONTEXT_LIGHT, CONTEXT, CONTEXT_DARK, CONTEXT_DARKEST]

# --- Text ---
TEXT = "#1F2937"            # near-black; the ONLY near-black text (titles, key labels)
TEXT_SECONDARY = "#4B5563"  # one recessive gray for every structural label (axes, ticks, notes)

# --- Ground (SWD figure/ground: a warm off-white reads calmer than pure white) ---
BACKGROUND = "#F7F6F2"

# --- Categorical: use ONLY when a chart genuinely has independent categories.
# Okabe-Ito, non-adjacent, capped at 5. Never the old 8-hue rainbow. ---
CATEGORICAL = [FOCUS, SECONDARY, "#009E73", "#CC79A7", CONTEXT_DARKEST]
CATEGORICAL_CAP = 5

# --- Sequential (retention, intensity): single-hue blue, light to saturated ---
SEQUENTIAL_LOW = "#F2F7FB"
SEQUENTIAL_MID = "#9CC7E4"
SEQUENTIAL_HIGH = FOCUS

# --- Diverging (sensitivity, deviation): orange <-> neutral <-> blue. NOT red-green. ---
DIVERGING_LOW = SECONDARY      # "bad" / negative
DIVERGING_MID = "#F0F0F0"
DIVERGING_HIGH = FOCUS         # "good" / positive


def sequential_cmap(name: str = "swd_sequential"):
    """A single-hue blue sequential colormap (light -> FOCUS). For heatmaps and intensity."""
    from matplotlib.colors import LinearSegmentedColormap

    return LinearSegmentedColormap.from_list(
        name, [SEQUENTIAL_LOW, SEQUENTIAL_MID, SEQUENTIAL_HIGH]
    )


def diverging_cmap(name: str = "swd_diverging"):
    """A colorblind-safe diverging colormap (orange <-> neutral <-> blue). Replaces red-green."""
    from matplotlib.colors import LinearSegmentedColormap

    return LinearSegmentedColormap.from_list(
        name, [DIVERGING_LOW, DIVERGING_MID, DIVERGING_HIGH]
    )


def categorical(n: int) -> list[str]:
    """First *n* categorical colors, capped at CATEGORICAL_CAP. More than 5 categories is a
    signal to rethink the chart, not to add hues, so this never rainbows past the cap."""
    n = max(0, min(n, CATEGORICAL_CAP))
    return CATEGORICAL[:n]
