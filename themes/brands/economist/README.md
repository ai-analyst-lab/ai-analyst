# Brand Theme: The Economist

A brand theme evoking *The Economist*'s house style: the signature pale blue-gray
canvas, Economist blue for primary data, and the Economist red highlight for the
one thing that matters.

## Palette

- **Background:** `#D5E4EB` — the pale blue-gray canvas
- **Primary:** `#006BA2` — Economist blue (key data, first series)
- **Highlight/focus:** `#E3120B` — Economist red (the one highlighted bar/line)
- **Categorical:** blue → teal → sea green → gold → red → gray → rose → brown

Some hues (teal, gold, captions) are darkened slightly from the source brand so the
palette clears WCAG contrast against the light canvas. Verify with
`python scripts/check_theme.py economist`.

## How It Works

Brand themes inherit from `themes/_base.yaml` via deep merge. The `theme.yaml` here
contains only overrides — any field not listed falls back to the base default.

## Creating Your Own Brand Theme

1. Copy a worked example: `cp -r themes/brands/economist themes/brands/your-org`
2. Edit `theme.yaml` — colors, fonts, and metadata to match your brand.
3. Keep only the fields you want to override; delete the rest.
4. Run the autograder until all gates pass: `python scripts/check_theme.py your-org`
5. Your theme then appears in the theme picker automatically.

## Colorblind Safety

The categorical palette must stay colorblind-safe:
- Never place red and green adjacent in the ordering.
- Distinguish categories by hue **and** lightness, not hue alone.
- Test with a simulator like [Coblis](https://www.color-blindness.com/coblis-color-blindness-simulator/) before shipping.
