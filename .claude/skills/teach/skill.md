---
name: teach
description: |
  Generate teaching visuals for analytics and statistics concepts on demand.
  Each topic produces a small, opinionated set of charts that illustrate one
  intuition clearly — not a generic explainer, but the specific picture that
  makes the idea click.

  Use this skill whenever the user invokes `/teach <topic>`, says "teach me X",
  "show me the intuition for X", "make the chart that explains X", or asks for
  visuals to walk someone else through a concept. Trigger on phrases like
  "/teach", "teach signal vs noise", "explain variance with a chart", "show
  the intuition", "make a teaching chart", "I want to walk through X with a
  picture".

  Topics are extensible — each lives under `topics/` as a single Python script
  that renders to `outputs/charts/teach/<topic>/`.
---

# Skill: Teach

## Purpose

Render the canonical chart(s) for a teaching concept, so anyone with this repo
can run `/teach <topic>` and get a consistent, slide-ready visual without
re-deriving the layout, the parameters, or the takeaway.

## How to invoke

The user will type one of:
- `/teach <topic>` — run the named topic
- `/teach` — list available topics

## Available topics

| Topic | Script | What it produces |
|-------|--------|------------------|
| `signal-vs-noise` | `topics/signal_vs_noise.py` | Two bell-curve charts (tight vs. wide SD, same means) + a side-by-side combined image. Illustrates that a 1.6-pt mean gap is a clear signal when SD is small and disappears in noise when SD is large. |

## Execution

1. Resolve the topic name to its script under `.claude/skills/teach/topics/`.
   - Accept hyphenated, underscored, or spaced forms (`signal-vs-noise`,
     `signal_vs_noise`, `signal vs noise`).
2. Run the script with `python3`. Each script is self-contained and writes to
   `outputs/charts/teach/<topic>/`.
3. Read each generated PNG back so the user can see it in the conversation.
4. Briefly summarize what each chart shows and the takeaway in 1–2 sentences.
5. If the topic is not in the registry, list available topics and stop —
   do not invent a new topic on the fly. Adding a topic is a deliberate
   step (see "Adding a topic" below).

## Adding a topic

To add a new topic:
1. Create `topics/<topic_name>.py` with a `main()` that renders to
   `outputs/charts/teach/<topic_name>/`.
2. Use `swd_style()` and `action_title()` from `helpers/chart_helpers.py` so
   visuals match the rest of the repo.
3. Add a row to the topics table in this file with the script path and a
   one-line description of what it produces.

## Output convention

All teaching charts go to:
```
outputs/charts/teach/<topic>/<chart>.png
```

`outputs/` is gitignored — the script is the source of truth, not the PNGs.
Re-running the skill regenerates them.
