# Outputs: one convention

Every analysis writes its deliverables into **one place, one shape**, so a folder full of past
work stays legible instead of turning into a junk drawer. This supersedes the older split between
a flat `outputs/` dump and a `reports/` tree.

## The convention: one folder per analysis

```
outputs/{YYYY-MM-DD}_{dataset}_{slug}/
  brief.md            # the written analysis: recommendation first, then the story
  charts/             # PNG charts (one story per chart)
  data/               # CSV extracts the analysis produced
  deck.pdf            # optional slide deck (deck.marp.md + deck.pdf/.html)
  query_log.jsonl     # provenance: every SQL query the analysis ran
```

- `{YYYY-MM-DD}` — the date the analysis was run.
- `{dataset}` — the active dataset id (e.g. `acme-warehouse`).
- `{slug}` — a short kebab-case name for *this* analysis, taken from the decision it serves
  (e.g. `q3-churn-drivers`, `west-region-revenue`). Named up front by the analyst, confirmed with
  the user (see the naming interview below).

Example: `outputs/2026-08-28_acme-warehouse_q3-churn-drivers/`.

## Rules

- **One analysis, one folder.** Never dump loose files into the root of `outputs/`. If you did not
  set up a run folder, make one before saving anything.
- **Name for a stranger.** A file's name plus its folder should tell someone what it is without
  opening it. `brief.md`, `charts/retention_by_cohort.png`, not `chart1.png`.
- **The chart is a deliverable, not scratch.** Charts that make the argument live in the run
  folder's `charts/`. Throwaway exploration stays in `working/`.
- **`working/` is for intermediates**, and it is gitignored. `outputs/` is for deliverables, and it
  is gitignored too — the user chooses what to commit. Nothing here ships in the repo.

## The naming interview

At the start of any analysis that will produce deliverables (a brief, charts, a deck), after the
question is framed and before writing files, the analyst:

1. Proposes a run-folder name derived from the framed decision:
   `outputs/2026-08-28_acme-warehouse_q3-churn-drivers/`.
2. Asks the user to confirm it or rename the `{slug}`.
3. States where everything will land, so the user knows where to look.

For a quick factual lookup that produces no files, skip the interview and just answer.
