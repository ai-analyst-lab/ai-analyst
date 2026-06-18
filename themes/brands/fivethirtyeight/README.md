# FiveThirtyEight Theme — the Worked Example

This is the reference brand theme for the build-your-own-theme module. It
recreates the FiveThirtyEight look: bold primaries on the signature
light-gray canvas, thick lines, no chart box.

It exists so you can see what a finished, *passing* theme looks like before
you build your own. Every color in it clears the autograder:

```bash
python scripts/check_theme.py fivethirtyeight
```

## Build your own

1. Copy this directory (or `themes/brands/example/` for a blanker slate):
   `cp -r themes/brands/fivethirtyeight themes/brands/your-theme`
2. Edit `theme.yaml` — change `theme.name`, the colors, and the fonts.
   Only include fields you want to override; everything else inherits from
   `themes/_base.yaml`.
3. Check your work: `python scripts/check_theme.py your-theme`
   It runs three gates — color-conflict lint, WCAG contrast, and
   base-key sync — and tells you exactly which color fails and why.
4. Once green, your theme automatically appears in the theme picker and can
   be passed to any chart: `swd_style(theme=load_theme_colors("your-theme"))`.

## Design notes worth stealing

- **One loud color, everything else recedes.** `highlight.focus` is the only
  saturated color most charts need; `comparison` gray does the de-emphasis.
- **Contrast is a budget.** A light canvas (here `#F0F0F0`) costs you
  contrast on every color. The brighter your background, the easier the
  WCAG checks get.
- **Red and green never sit adjacent** in the categorical ordering —
  colorblind viewers lose that distinction first.
