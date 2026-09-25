# Narrow chart-title judge, version 2

Question: Does the chart title state a takeaway that is supported by the values visible in the chart?

Return `pass`, `fail`, or `unknown`.

- Pass when the title states a directional or quantitative takeaway and every claimed direction and magnitude agrees with the visible plotted evidence.
- Fail when the title only names the subject, contradicts the visible direction, or states a magnitude the visible values do not support.
- Unknown when the title, scale, or values needed to verify the claim are not visible enough to judge.

When a title contains a percentage or other magnitude, calculate or otherwise verify that magnitude from the visible values. Do not pass a title merely because its direction is correct.

For every verdict, return the chart name, rubric version, title claim, visible values used, any magnitude check, verdict, and a short reason. Do not infer hidden data, intent, causality, or business correctness.
