# Example Brand Theme: Acme Corp

This is a reference brand theme that demonstrates how to customize the AI Analyst visual identity for an organization. It uses a teal/coral palette and Inter font.

## How It Works

Brand themes inherit from `themes/_base.yaml` via deep merge. The `theme.yaml` file here only contains overrides -- any field not listed falls back to the base default. This keeps brand files small and maintainable.

## Creating Your Own Brand Theme

1. Copy this directory: `cp -r themes/brands/example themes/brands/your-org`
   (or copy `themes/brands/fivethirtyeight/` to start from the worked example).
2. Edit `theme.yaml` -- change the colors, fonts, and metadata to match your brand.
3. Only include fields you want to override. Delete everything else.
4. Run the autograder until all gates pass: `python scripts/check_theme.py your-org`
5. Your theme now appears in the theme picker automatically. Set it as the
   session default, name it per-chart, or set it in your dataset manifest.

## Colorblind Safety

The categorical palette must remain colorblind-safe. Key rules:
- Never place red and green adjacent in the palette ordering.
- Use hue + lightness variation (not just hue) to distinguish categories.
- Test with a simulator like [Coblis](https://www.color-blindness.com/coblis-color-blindness-simulator/) before shipping.
- The example palette (teal, orange, indigo, rose, amber, sky, emerald, slate) avoids red-green adjacency.
