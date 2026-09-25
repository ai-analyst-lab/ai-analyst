# Chart-judge alignment exercise

This is the fourteen-chart reviewed set used in Session 6. It comes from the chart-judge exercise
delivered in an advanced Agentic Analytics course. The charts and labels are preserved so the
class can reproduce the measured alignment change instead of relying on a verbal example.

## What is here

- `RUBRIC.md` is the starter rubric students revise.
- `judge.md` is the blind scoring protocol.
- `reviewed-set/` contains fourteen charts and the frozen human labels.
- `captured/initial-verdicts.csv` contains the recorded five-rule judge verdicts.
- `captured/revised-verdicts.csv` contains the recorded verdicts after adding two missing rules.
- `score_alignment.py` compares grader labels with human labels and reports the confusion counts,
  accuracy, precision, and recall.

## The classroom loop

1. Write a narrow binary rubric before reading the reviewed labels.
2. Have the model score every chart blind and save one overall verdict per chart.
3. Compare those verdicts with the frozen human labels.
4. Inspect every disagreement.
5. Add only the standards revealed by the false passes.
6. Rerun the complete set and compare the measurements.
7. Repeat selected boundary examples to test the judge's own stability.

The original five-rule run produced four true passes and two false passes. Precision was `4 / 6 =
0.667`, recall was `4 / 4 = 1.000`, and accuracy was `12 / 14 = 0.857`. The two false passes were an
exaggerated title and inappropriate numerical precision. Adding a title-accuracy rule and a
clean-numbers rule brought all fourteen verdicts into agreement with the reviewed labels on this
working set.

That result is an alignment check on a small working set. It is not proof that the judge is correct
or stable on future charts.

## Reproduce the captured measurements

Prompt Claude to run:

```text
python3 evals/examples/chart-judge/score_alignment.py \
  --human evals/examples/chart-judge/reviewed-set/human-labels.csv \
  --grader evals/examples/chart-judge/captured/initial-verdicts.csv
```

Then replace `initial-verdicts.csv` with `revised-verdicts.csv` and run the same comparison.

## Provenance

Built and delivered on July 1, 2026, then adapted into this public exercise. The captured verdicts
and reviewed human labels needed to reproduce the reported measurements are preserved here.
