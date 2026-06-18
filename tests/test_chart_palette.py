"""
Unit tests for helpers/chart_palette.py -- Palette-aware theme utilities.

Covers the 6 public functions (apply_theme_colors, highlight_palette,
categorical_colors, ensure_contrast, palette_for_n, format_hex) and
the internal WCAG helpers (_hex_to_rgb, _rgb_to_hex, _relative_luminance,
_contrast_ratio).
"""

from __future__ import annotations

import re

import matplotlib as mpl
import pytest

from helpers.chart_palette import (
    apply_theme_colors,
    categorical_colors,
    ensure_contrast,
    format_hex,
    highlight_palette,
    palette_for_n,
    _contrast_ratio,
    _hex_to_rgb,
    _relative_luminance,
    _rgb_to_hex,
)


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------

@pytest.fixture()
def theme() -> dict:
    """Minimal theme dict matching _base.yaml structure."""
    return {
        "colors": {
            "primary": "#4878CF",
            "secondary": "#5ABF55",
            "accent": "#D65F5F",
            "neutral": "#B0B0B0",
            "background": "#F7F6F2",
            "text": "#333333",
            "text_light": "#666666",
            "categorical": [
                "#4878CF",
                "#5ABF55",
                "#B47CC7",
                "#D65F5F",
                "#C4AD66",
                "#5FAECC",
                "#D68E5C",
                "#8C8C8C",
            ],
            "sequential": {
                "low": "#E8F4FD",
                "mid": "#4878CF",
                "high": "#1A3A6C",
            },
            "diverging": {
                "negative": "#D65F5F",
                "neutral": "#F7F6F2",
                "positive": "#5ABF55",
            },
            "highlight": {
                "focus": "#4878CF",
                "comparison": "#B0B0B0",
                "alert": "#D65F5F",
            },
        },
    }


_HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")


# ==================================================================
# TestApplyThemeColors
# ==================================================================

class TestApplyThemeColors:
    """apply_theme_colors() should update mpl.rcParams from the theme."""

    @pytest.fixture(autouse=True)
    def _save_restore_rcparams(self):
        """Snapshot rcParams before each test and restore after."""
        original = mpl.rcParams.copy()
        yield
        mpl.rcParams.update(original)

    def test_sets_color_cycle(self, theme: dict) -> None:
        apply_theme_colors(theme)
        cycle_colors = [
            c["color"] for c in mpl.rcParams["axes.prop_cycle"]
        ]
        assert cycle_colors == theme["colors"]["categorical"]

    def test_sets_background(self, theme: dict) -> None:
        apply_theme_colors(theme)
        assert mpl.rcParams["figure.facecolor"] == theme["colors"]["background"]
        assert mpl.rcParams["axes.facecolor"] == theme["colors"]["background"]

    def test_sets_text_colors(self, theme: dict) -> None:
        apply_theme_colors(theme)
        assert mpl.rcParams["text.color"] == theme["colors"]["text"]
        assert mpl.rcParams["axes.labelcolor"] == theme["colors"]["text"]

    def test_sets_tick_colors(self, theme: dict) -> None:
        apply_theme_colors(theme)
        assert mpl.rcParams["xtick.color"] == theme["colors"]["text_light"]
        assert mpl.rcParams["ytick.color"] == theme["colors"]["text_light"]


# ==================================================================
# TestHighlightPalette
# ==================================================================

class TestHighlightPalette:
    """highlight_palette() should return focus/comparison/alert colors."""

    def test_returns_focus(self, theme: dict) -> None:
        result = highlight_palette(theme)
        assert result["focus"] == "#4878CF"

    def test_returns_comparison(self, theme: dict) -> None:
        result = highlight_palette(theme)
        assert result["comparison"] == "#B0B0B0"

    def test_returns_alert(self, theme: dict) -> None:
        result = highlight_palette(theme)
        assert result["alert"] == "#D65F5F"

    def test_returns_only_three_keys(self, theme: dict) -> None:
        result = highlight_palette(theme)
        assert set(result.keys()) == {"focus", "comparison", "alert"}


# ==================================================================
# TestCategoricalColors
# ==================================================================

class TestCategoricalColors:
    """categorical_colors() should return subsets of the palette."""

    def test_full_palette(self, theme: dict) -> None:
        result = categorical_colors(theme)
        assert result == theme["colors"]["categorical"]
        assert len(result) == 8

    def test_subset_n3(self, theme: dict) -> None:
        result = categorical_colors(theme, n=3)
        assert result == theme["colors"]["categorical"][:3]
        assert len(result) == 3

    def test_n_exceeds_palette(self, theme: dict) -> None:
        result = categorical_colors(theme, n=20)
        assert len(result) == 8  # capped at palette length

    def test_n_zero(self, theme: dict) -> None:
        result = categorical_colors(theme, n=0)
        assert result == []

    def test_n_negative(self, theme: dict) -> None:
        result = categorical_colors(theme, n=-5)
        assert result == []

    def test_n_none(self, theme: dict) -> None:
        result = categorical_colors(theme, n=None)
        assert result == theme["colors"]["categorical"]


# ==================================================================
# TestEnsureContrast
# ==================================================================

class TestEnsureContrast:
    """ensure_contrast() should adjust colors to meet WCAG contrast."""

    def test_passing_color_unchanged(self) -> None:
        # Dark blue on light background — already high contrast
        dark = "#1A1A1A"
        result = ensure_contrast(dark, background="#F7F6F2")
        assert result == format_hex(dark)

    def test_failing_color_darkened(self) -> None:
        # Very light color on light background — must be darkened
        light_fg = "#E0E0E0"
        result = ensure_contrast(light_fg, background="#F7F6F2")
        # The result should be darker (lower luminance) than the original
        orig_lum = _relative_luminance(*_hex_to_rgb(format_hex(light_fg)))
        result_lum = _relative_luminance(*_hex_to_rgb(result))
        assert result_lum < orig_lum

    def test_result_meets_threshold(self) -> None:
        light_fg = "#E0E0E0"
        bg = "#F7F6F2"
        result = ensure_contrast(light_fg, background=bg, min_ratio=4.5)
        fg_lum = _relative_luminance(*_hex_to_rgb(result))
        bg_lum = _relative_luminance(*_hex_to_rgb(format_hex(bg)))
        ratio = _contrast_ratio(fg_lum, bg_lum)
        assert ratio >= 4.5

    def test_dark_bg_lightens(self) -> None:
        # Dark foreground on dark background — should lighten fg
        dark_fg = "#1A1A1A"
        dark_bg = "#0A0A0A"
        result = ensure_contrast(dark_fg, background=dark_bg)
        orig_lum = _relative_luminance(*_hex_to_rgb(format_hex(dark_fg)))
        result_lum = _relative_luminance(*_hex_to_rgb(result))
        assert result_lum > orig_lum

    def test_custom_min_ratio(self) -> None:
        light_fg = "#CCCCCC"
        bg = "#F7F6F2"
        result = ensure_contrast(light_fg, background=bg, min_ratio=3.0)
        fg_lum = _relative_luminance(*_hex_to_rgb(result))
        bg_lum = _relative_luminance(*_hex_to_rgb(format_hex(bg)))
        ratio = _contrast_ratio(fg_lum, bg_lum)
        assert ratio >= 3.0

    def test_already_at_threshold(self) -> None:
        # Black on white — well above any threshold
        result = ensure_contrast("#000000", background="#FFFFFF", min_ratio=4.5)
        assert result == "#000000"


# ==================================================================
# TestPaletteForN
# ==================================================================

class TestPaletteForN:
    """palette_for_n() picks the best strategy for the requested count."""

    def test_n_within_categorical(self, theme: dict) -> None:
        result = palette_for_n(theme, 5)
        assert result == theme["colors"]["categorical"][:5]

    def test_n_equals_categorical(self, theme: dict) -> None:
        result = palette_for_n(theme, 8)
        assert result == theme["colors"]["categorical"]

    def test_n_exceeds_categorical(self, theme: dict) -> None:
        result = palette_for_n(theme, 12)
        assert len(result) == 12
        # Should NOT simply be the categorical list (it's sampled from sequential)
        assert result != theme["colors"]["categorical"][:12]

    def test_returns_exact_count(self, theme: dict) -> None:
        for n in (1, 3, 8, 10, 15):
            assert len(palette_for_n(theme, n)) == n

    def test_n_zero(self, theme: dict) -> None:
        assert palette_for_n(theme, 0) == []

    def test_all_hex_format(self, theme: dict) -> None:
        for n in (3, 8, 12):
            colors = palette_for_n(theme, n)
            for c in colors:
                assert _HEX_RE.match(c), f"{c} is not valid #RRGGBB"


# ==================================================================
# TestFormatHex
# ==================================================================

class TestFormatHex:
    """format_hex() normalizes hex strings to uppercase 6-digit format."""

    def test_uppercase(self) -> None:
        assert format_hex("#4878cf") == "#4878CF"

    def test_shorthand_expanded(self) -> None:
        assert format_hex("#abc") == "#AABBCC"

    def test_strips_whitespace(self) -> None:
        assert format_hex("  #4878CF  ") == "#4878CF"

    def test_no_hash_prefix(self) -> None:
        assert format_hex("4878CF") == "#4878CF"

    def test_already_formatted(self) -> None:
        assert format_hex("#4878CF") == "#4878CF"

    def test_mixed_case(self) -> None:
        assert format_hex("#4a7BcF") == "#4A7BCF"


# ==================================================================
# TestWcagHelpers (internal but critical)
# ==================================================================

class TestWcagHelpers:
    """WCAG contrast helper functions (_hex_to_rgb, _rgb_to_hex, etc.)."""

    def test_hex_to_rgb_white(self) -> None:
        assert _hex_to_rgb("#FFFFFF") == (255, 255, 255)

    def test_hex_to_rgb_black(self) -> None:
        assert _hex_to_rgb("#000000") == (0, 0, 0)

    def test_rgb_to_hex(self) -> None:
        assert _rgb_to_hex(72, 120, 207) == "#4878CF"

    def test_relative_luminance_white(self) -> None:
        lum = _relative_luminance(255, 255, 255)
        assert lum == pytest.approx(1.0, abs=0.001)

    def test_relative_luminance_black(self) -> None:
        lum = _relative_luminance(0, 0, 0)
        assert lum == pytest.approx(0.0, abs=0.001)

    def test_contrast_ratio_bw(self) -> None:
        white_lum = _relative_luminance(255, 255, 255)
        black_lum = _relative_luminance(0, 0, 0)
        ratio = _contrast_ratio(white_lum, black_lum)
        assert ratio == pytest.approx(21.0, abs=0.05)

    def test_contrast_ratio_same(self) -> None:
        lum = _relative_luminance(128, 128, 128)
        ratio = _contrast_ratio(lum, lum)
        assert ratio == pytest.approx(1.0, abs=0.001)
