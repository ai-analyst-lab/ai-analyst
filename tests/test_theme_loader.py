"""Comprehensive tests for helpers/viz/theme_loader.py.

Covers: _deep_merge, load_theme, get_color, get_categorical_palette,
get_sequential_colormap, get_diverging_colormap, clear_cache, list_themes.
"""

from __future__ import annotations

import copy
from pathlib import Path

import pytest
import yaml

from helpers.viz.theme_loader import (
    ThemeNotFoundError,
    _deep_merge,
    clear_cache,
    get_categorical_palette,
    get_color,
    get_diverging_colormap,
    get_sequential_colormap,
    list_themes,
    load_theme,
)

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture()
def base_yaml() -> dict:
    """Load the minimal base theme fixture as a dict."""
    with open(FIXTURES_DIR / "theme_base.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


@pytest.fixture()
def brand_yaml() -> dict:
    """Load the minimal brand override fixture as a dict."""
    with open(FIXTURES_DIR / "theme_brand.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


@pytest.fixture()
def themes_dir(tmp_path: Path, base_yaml: dict, brand_yaml: dict) -> Path:
    """Create a temporary themes directory with base + brand for load_theme tests.

    Structure:
        tmp_path/themes/
            _base.yaml
            brands/
                testbrand/
                    theme.yaml
    """
    themes = tmp_path / "themes"
    themes.mkdir()

    # Write base theme
    with open(themes / "_base.yaml", "w", encoding="utf-8") as f:
        yaml.dump(base_yaml, f, default_flow_style=False)

    # Write brand theme
    brand_dir = themes / "brands" / "testbrand"
    brand_dir.mkdir(parents=True)
    with open(brand_dir / "theme.yaml", "w", encoding="utf-8") as f:
        yaml.dump(brand_yaml, f, default_flow_style=False)

    return themes


@pytest.fixture(autouse=True)
def _clear_theme_cache():
    """Clear the module-level theme cache before and after every test."""
    clear_cache()
    yield
    clear_cache()


# ===========================================================================
# TestDeepMerge
# ===========================================================================


class TestDeepMerge:
    """Tests for the _deep_merge internal helper."""

    def test_merge_scalar_override(self, base_yaml: dict, brand_yaml: dict):
        """Brand scalar value replaces base scalar value."""
        merged = _deep_merge(base_yaml, brand_yaml)
        assert merged["colors"]["primary"] == "#0D9488"  # brand value

    def test_merge_dict_recursive(self, base_yaml: dict, brand_yaml: dict):
        """Nested dicts are merged recursively."""
        merged = _deep_merge(base_yaml, brand_yaml)
        # Brand overrides highlight.focus but base has highlight.comparison
        assert merged["colors"]["highlight"]["focus"] == "#0D9488"
        assert merged["colors"]["highlight"]["comparison"] == "#B0B0B0"

    def test_merge_list_replaces(self, base_yaml: dict, brand_yaml: dict):
        """Brand list replaces base list entirely (no element-level merge)."""
        merged = _deep_merge(base_yaml, brand_yaml)
        assert merged["colors"]["categorical"] == ["#0D9488", "#F97316", "#6366F1"]

    def test_merge_does_not_mutate_base(self, base_yaml: dict, brand_yaml: dict):
        """_deep_merge must not mutate the original base dict."""
        original_primary = base_yaml["colors"]["primary"]
        _deep_merge(base_yaml, brand_yaml)
        assert base_yaml["colors"]["primary"] == original_primary

    def test_merge_adds_new_keys(self, base_yaml: dict):
        """Brand can introduce keys not present in base."""
        override = {"brand_meta": {"contact": "test@example.com"}}
        merged = _deep_merge(base_yaml, override)
        assert merged["brand_meta"]["contact"] == "test@example.com"
        # Original keys still present
        assert "theme" in merged

    def test_merge_empty_override(self, base_yaml: dict):
        """Empty override returns an identical copy of base."""
        merged = _deep_merge(base_yaml, {})
        assert merged == base_yaml
        # But it should be a different object (deep copy)
        assert merged is not base_yaml


# ===========================================================================
# TestLoadTheme
# ===========================================================================


class TestLoadTheme:
    """Tests for load_theme (file loading, merging, caching)."""

    def test_load_base_theme(self, themes_dir: Path, base_yaml: dict):
        """load_theme(None) returns the base theme."""
        theme = load_theme(None, themes_dir=str(themes_dir))
        assert theme["theme"]["name"] == "analytics"

    def test_load_base_theme_by_name(self, themes_dir: Path):
        """load_theme('analytics') returns the base theme."""
        theme = load_theme("analytics", themes_dir=str(themes_dir))
        assert theme["theme"]["name"] == "analytics"

    def test_load_brand_theme(self, themes_dir: Path):
        """load_theme('testbrand') returns a merged result."""
        theme = load_theme("testbrand", themes_dir=str(themes_dir))
        # Brand name is overridden
        assert theme["theme"]["name"] == "test-brand"
        # Still has base keys that brand didn't override
        assert "typography" in theme

    def test_brand_overrides_base(self, themes_dir: Path):
        """Brand values take precedence over base values."""
        theme = load_theme("testbrand", themes_dir=str(themes_dir))
        assert theme["colors"]["primary"] == "#0D9488"  # brand value, not base

    def test_brand_inherits_base(self, themes_dir: Path):
        """Unoverridden base values are preserved in brand theme."""
        theme = load_theme("testbrand", themes_dir=str(themes_dir))
        # Brand fixture does not override 'text' or 'neutral'
        assert theme["colors"]["text"] == "#333333"
        assert theme["colors"]["neutral"] == "#B0B0B0"

    def test_theme_not_found(self, themes_dir: Path):
        """load_theme('nonexistent') raises ThemeNotFoundError."""
        with pytest.raises(ThemeNotFoundError, match="nonexistent"):
            load_theme("nonexistent", themes_dir=str(themes_dir))

    def test_base_not_found(self, tmp_path: Path):
        """ThemeNotFoundError when _base.yaml is missing."""
        empty_dir = tmp_path / "empty_themes"
        empty_dir.mkdir()
        with pytest.raises(ThemeNotFoundError, match="Base theme not found"):
            load_theme(None, themes_dir=str(empty_dir))

    def test_cache_hit(self, themes_dir: Path):
        """Second call returns data without re-reading from disk."""
        theme1 = load_theme("analytics", themes_dir=str(themes_dir))
        # Delete the file to prove the second call uses cache
        (themes_dir / "_base.yaml").unlink()
        theme2 = load_theme("analytics", themes_dir=str(themes_dir))
        assert theme1 == theme2

    def test_clear_cache_works(self, themes_dir: Path):
        """After clear_cache(), next load re-reads from disk."""
        theme1 = load_theme("analytics", themes_dir=str(themes_dir))
        clear_cache()
        # Now it must read from disk again — file still exists, so it works
        theme2 = load_theme("analytics", themes_dir=str(themes_dir))
        assert theme1 == theme2

    def test_load_returns_deepcopy(self, themes_dir: Path):
        """Modifying the returned dict does not affect the cache."""
        theme1 = load_theme("analytics", themes_dir=str(themes_dir))
        theme1["colors"]["primary"] = "#MUTATED"
        theme2 = load_theme("analytics", themes_dir=str(themes_dir))
        assert theme2["colors"]["primary"] != "#MUTATED"


# ===========================================================================
# TestGetColor
# ===========================================================================


class TestGetColor:
    """Tests for get_color (dot-notation color lookup)."""

    def test_get_simple_color(self, base_yaml: dict):
        """get_color(theme, 'primary') returns a top-level color."""
        assert get_color(base_yaml, "primary") == "#4878CF"

    def test_get_nested_color(self, base_yaml: dict):
        """get_color(theme, 'highlight.focus') resolves nested path."""
        assert get_color(base_yaml, "highlight.focus") == "#4878CF"

    def test_key_not_found(self, base_yaml: dict):
        """Raises KeyError with helpful message for missing key."""
        with pytest.raises(KeyError, match="not found"):
            get_color(base_yaml, "nonexistent_color")

    def test_nested_key_not_found(self, base_yaml: dict):
        """Raises KeyError for invalid nested path."""
        with pytest.raises(KeyError, match="not found"):
            get_color(base_yaml, "highlight.nonexistent")

    def test_non_string_value(self, base_yaml: dict):
        """Raises KeyError when path resolves to a dict, not a string."""
        # 'highlight' alone resolves to a dict
        with pytest.raises(KeyError, match="non-string"):
            get_color(base_yaml, "highlight")


# ===========================================================================
# TestGetCategoricalPalette
# ===========================================================================


class TestGetCategoricalPalette:
    """Tests for get_categorical_palette."""

    def test_full_palette(self, base_yaml: dict):
        """Returns all colors when n is not specified."""
        palette = get_categorical_palette(base_yaml)
        assert len(palette) == 4  # base fixture has 4 categorical colors
        assert palette[0] == "#4878CF"

    def test_subset_palette(self, base_yaml: dict):
        """n=3 returns only the first 3 colors."""
        palette = get_categorical_palette(base_yaml, n=3)
        assert len(palette) == 3

    def test_n_exceeds_length(self, base_yaml: dict):
        """n exceeding palette length caps at palette length."""
        palette = get_categorical_palette(base_yaml, n=100)
        assert len(palette) == 4  # capped at actual palette size

    def test_n_zero(self, base_yaml: dict):
        """n=0 returns an empty list."""
        palette = get_categorical_palette(base_yaml, n=0)
        assert palette == []

    def test_n_none(self, base_yaml: dict):
        """n=None returns the full palette (same as no argument)."""
        palette = get_categorical_palette(base_yaml, n=None)
        assert len(palette) == 4


# ===========================================================================
# TestColormaps
# ===========================================================================


class TestColormaps:
    """Tests for get_sequential_colormap and get_diverging_colormap."""

    def test_sequential_colormap_type(self, base_yaml: dict):
        """Returns a LinearSegmentedColormap."""
        from matplotlib.colors import LinearSegmentedColormap

        cmap = get_sequential_colormap(base_yaml)
        assert isinstance(cmap, LinearSegmentedColormap)

    def test_sequential_colormap_name(self, base_yaml: dict):
        """Colormap name incorporates the theme name."""
        cmap = get_sequential_colormap(base_yaml)
        assert "analytics" in cmap.name

    def test_diverging_colormap_type(self, base_yaml: dict):
        """Returns a LinearSegmentedColormap."""
        from matplotlib.colors import LinearSegmentedColormap

        cmap = get_diverging_colormap(base_yaml)
        assert isinstance(cmap, LinearSegmentedColormap)

    def test_diverging_colormap_name(self, base_yaml: dict):
        """Colormap name incorporates the theme name."""
        cmap = get_diverging_colormap(base_yaml)
        assert "analytics" in cmap.name


# ===========================================================================
# TestListThemes
# ===========================================================================


class TestListThemes:
    """Tests for list_themes (theme discovery)."""

    def test_lists_base_theme(self, themes_dir: Path):
        """'analytics' is always present in the list."""
        themes = list_themes(themes_dir=str(themes_dir))
        assert "analytics" in themes

    def test_lists_brand_themes(self, themes_dir: Path):
        """Discovers brand directories that contain theme.yaml."""
        themes = list_themes(themes_dir=str(themes_dir))
        assert "testbrand" in themes

    def test_no_brands_dir(self, tmp_path: Path):
        """Returns only ['analytics'] when brands/ directory is missing."""
        # Create a themes dir with only _base.yaml, no brands/
        themes = tmp_path / "themes_no_brands"
        themes.mkdir()
        (themes / "_base.yaml").write_text("theme:\n  name: analytics\n")
        result = list_themes(themes_dir=str(themes))
        assert result == ["analytics"]
