"""Theme loader for AI Analyst.

Loads, merges, and caches themes. The base theme lives at themes/_base.yaml.
Brand themes live at themes/brands/{brand}/theme.yaml and inherit from the
base theme via deep merge (brand values override base values).

Public API:
    load_theme()              - Load and cache a theme by name
    get_color()               - Look up a color by key (supports dot notation)
    get_categorical_palette() - Get the categorical color list
    get_sequential_colormap() - Build a matplotlib sequential colormap
    get_diverging_colormap()  - Build a matplotlib diverging colormap
    clear_cache()             - Clear the theme cache
    list_themes()             - List all available theme names
"""

from __future__ import annotations

import copy
from pathlib import Path

from helpers.pipeline.file_helpers import safe_read_yaml


# ---------------------------------------------------------------------------
# Custom exception
# ---------------------------------------------------------------------------

class ThemeNotFoundError(FileNotFoundError):
    """Raised when a requested theme file does not exist."""


# ---------------------------------------------------------------------------
# Module-level cache
# ---------------------------------------------------------------------------

_cache: dict[str, dict] = {}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge *override* into a deep copy of *base*.

    - Dict values are merged recursively.
    - List values in *override* replace the base list entirely.
    - Scalar values in *override* replace the base value.
    """
    merged = copy.deepcopy(base)
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def _resolve_base_path(themes_dir: str) -> Path:
    """Return the absolute path to _base.yaml."""
    return Path(themes_dir).resolve() / "_base.yaml"


def _resolve_brand_path(theme_name: str, themes_dir: str) -> Path:
    """Return the absolute path to a brand theme.yaml."""
    return Path(themes_dir).resolve() / "brands" / theme_name / "theme.yaml"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_theme(theme_name: str | None = None, themes_dir: str = "themes") -> dict:
    """Load a theme by name, with caching.

    Parameters
    ----------
    theme_name : str or None
        Theme to load. ``None`` or ``"analytics"`` loads the base theme.
        Any other string loads the brand theme and deep-merges it onto
        the base.
    themes_dir : str
        Root directory containing ``_base.yaml`` and ``brands/``.

    Returns
    -------
    dict
        The fully-resolved theme dictionary.

    Raises
    ------
    ThemeNotFoundError
        If the requested theme file does not exist on disk.
    """
    # Normalise to the base theme name when None
    if theme_name is None:
        theme_name = "analytics"

    # Return from cache if available
    cache_key = f"{themes_dir}::{theme_name}"
    if cache_key in _cache:
        return copy.deepcopy(_cache[cache_key])

    # Load base theme (always needed)
    base_path = _resolve_base_path(themes_dir)
    base_data = safe_read_yaml(base_path)
    if base_data is None:
        raise ThemeNotFoundError(
            f"Base theme not found at {base_path}. "
            "Ensure themes/_base.yaml exists."
        )

    if theme_name == "analytics":
        # Pure base theme
        _cache[cache_key] = copy.deepcopy(base_data)
        return copy.deepcopy(base_data)

    # Brand theme — load and merge onto base
    brand_path = _resolve_brand_path(theme_name, themes_dir)
    brand_data = safe_read_yaml(brand_path)
    if brand_data is None:
        raise ThemeNotFoundError(
            f"Brand theme '{theme_name}' not found at {brand_path}. "
            f"Expected themes/brands/{theme_name}/theme.yaml."
        )

    merged = _deep_merge(base_data, brand_data)
    _cache[cache_key] = copy.deepcopy(merged)
    return copy.deepcopy(merged)


def get_color(theme: dict, key: str) -> str:
    """Look up a color by key, supporting dot notation for nested access.

    Examples
    --------
    >>> get_color(theme, "primary")          # theme["colors"]["primary"]
    >>> get_color(theme, "highlight.focus")  # theme["colors"]["highlight"]["focus"]

    Parameters
    ----------
    theme : dict
        A theme dictionary as returned by :func:`load_theme`.
    key : str
        Dot-separated path into ``theme["colors"]``.

    Returns
    -------
    str
        The hex color string.

    Raises
    ------
    KeyError
        If the key path does not exist in the colors section.
    """
    node = theme.get("colors", {})
    parts = key.split(".")
    for i, part in enumerate(parts):
        if not isinstance(node, dict) or part not in node:
            traversed = ".".join(parts[: i + 1])
            available = list(node.keys()) if isinstance(node, dict) else []
            raise KeyError(
                f"Color key '{traversed}' not found. "
                f"Available keys at this level: {available}"
            )
        node = node[part]
    if not isinstance(node, str):
        raise KeyError(
            f"Color key '{key}' resolved to a non-string value ({type(node).__name__}). "
            "Use a more specific key to reach a color string."
        )
    return node


def get_categorical_palette(theme: dict, n: int | None = None) -> list[str]:
    """Return the categorical color palette.

    Parameters
    ----------
    theme : dict
        A theme dictionary as returned by :func:`load_theme`.
    n : int or None
        If provided, return only the first *n* colors (capped at the
        palette length).

    Returns
    -------
    list[str]
        List of hex color strings.
    """
    palette = list(theme.get("colors", {}).get("categorical", []))
    if n is not None:
        return palette[: min(n, len(palette))]
    return palette


def get_sequential_colormap(theme: dict) -> object:
    """Build a matplotlib ``LinearSegmentedColormap`` from the sequential palette.

    Uses ``colors.sequential`` (low -> mid -> high).

    Parameters
    ----------
    theme : dict
        A theme dictionary as returned by :func:`load_theme`.

    Returns
    -------
    matplotlib.colors.LinearSegmentedColormap
    """
    from matplotlib.colors import LinearSegmentedColormap

    seq = theme.get("colors", {}).get("sequential", {})
    colors = [seq.get("low", "#FFFFFF"), seq.get("mid", "#888888"), seq.get("high", "#000000")]
    name = theme.get("theme", {}).get("name", "custom") + "_sequential"
    return LinearSegmentedColormap.from_list(name, colors, N=256)


def get_diverging_colormap(theme: dict) -> object:
    """Build a matplotlib ``LinearSegmentedColormap`` from the diverging palette.

    Uses ``colors.diverging`` (negative -> neutral -> positive).

    Parameters
    ----------
    theme : dict
        A theme dictionary as returned by :func:`load_theme`.

    Returns
    -------
    matplotlib.colors.LinearSegmentedColormap
    """
    from matplotlib.colors import LinearSegmentedColormap

    div = theme.get("colors", {}).get("diverging", {})
    colors = [div.get("negative", "#FF0000"), div.get("neutral", "#FFFFFF"), div.get("positive", "#00FF00")]
    name = theme.get("theme", {}).get("name", "custom") + "_diverging"
    return LinearSegmentedColormap.from_list(name, colors, N=256)


def clear_cache() -> None:
    """Clear the theme cache."""
    _cache.clear()


def list_themes(themes_dir: str = "themes") -> list[str]:
    """List all available theme names.

    Always includes ``"analytics"`` (the base theme). Additionally lists
    any brand directory under ``themes/brands/`` that contains a
    ``theme.yaml`` file.

    Parameters
    ----------
    themes_dir : str
        Root directory containing ``_base.yaml`` and ``brands/``.

    Returns
    -------
    list[str]
        Sorted list of theme names.
    """
    themes = ["analytics"]
    brands_dir = Path(themes_dir).resolve() / "brands"
    if brands_dir.is_dir():
        for entry in sorted(brands_dir.iterdir()):
            if entry.is_dir() and (entry / "theme.yaml").is_file():
                themes.append(entry.name)
    return themes
