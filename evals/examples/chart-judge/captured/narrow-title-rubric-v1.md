# Narrow chart-title judge, version 1

Question: Does the chart title state a takeaway that is supported by the values visible in the chart?

Return `pass`, `fail`, or `unknown`.

- Pass when the title states a directional takeaway and the plotted trend moves in that direction.
- Fail when the title only names the subject or contradicts the visible direction.
- Unknown when the title or plotted evidence is not visible enough to judge.

For every verdict, return the chart name, rubric version, title claim, visible values or trend used, verdict, and a short reason. Do not infer hidden data, intent, causality, or business correctness.

This first rule is intentionally incomplete. It checks the direction of a claim but does not require the judge to verify a numerical magnitude in the title.
