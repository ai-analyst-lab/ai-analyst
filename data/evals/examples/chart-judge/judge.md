# Blind chart-judge protocol

Evaluate one chart against every rule in `RUBRIC.md`.

For each rule:

1. Use only evidence visible in the chart.
2. Write one short reason tied to the rule's anchors.
3. Return `pass`, `fail`, or `unknown`.

The overall verdict is `pass` only when every rule passes. It is `unknown` when no rule fails and at
least one rule is unknown. Otherwise it is `fail`.

Do not read the human labels, captured verdicts, or prior scores before judging. Save the chart name,
rubric version, per-rule reasons, per-rule verdicts, and overall verdict before comparing anything
with a human label.
