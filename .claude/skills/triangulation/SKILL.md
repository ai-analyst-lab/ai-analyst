---
name: triangulation
description: Analyze one decision through independent methods or sources, compare the paths, and reconcile disagreement. Use when a novel analysis needs corroboration and no single answer key is available.
---

# Triangulate an analysis

## Select paths deliberately

First determine what the available data can support. Choose paths that differ in method, source, population, assumptions, or counterfactual. Opening more sessions that repeat the same method is not meaningful triangulation.

Each path must work without seeing the other paths' conclusions. Record:

- path ID;
- method;
- source;
- population;
- assumptions;
- direction as `yes`, `no`, or `unclear`; and
- the evidence supporting that direction.

For a live analysis, use three paths unless the user requests another number. Inspect the available data first, then propose three methods that answer different parts of the decision and rely on meaningfully different assumptions. Aim for a 400-word proposal and never exceed 500 words. Keep each path narrow enough to complete with no more than two read-only queries and a narrative of no more than 250 words unless the user asks for a deeper analysis. Compact SQL and result tables do not count toward the narrative limit.

After the user approves the methods, run the three paths in fresh subagents in parallel. Give each subagent the complete original task and terminology constraints, its assigned method, the approved data source, the two-query and 250-word narrative limits, and the required output fields. Do not paraphrase or omit user constraints when delegating. Do not show one path another path's work.

Save each path separately under `working/triangulation/<slug>/`, then save a comparison that shows the method, question answered, assumptions, important evidence, direction, and limitations for every path.

## Compare the paths

Use `helpers.evals.triangulation.build_grid` to assemble the comparison. Run each genuinely different path once. A second full round is not required. If one path is surprising or disputed, rerun only that path in a fresh context to determine whether the difference is run variation or a persistent methodological disagreement.

When paths disagree, locate the difference in their populations, assumptions, sources, or counterfactuals. Reconcile the difference only when the evidence supports it. Otherwise preserve the disagreement and escalate it.

When paths agree, state what their independence adds and what it still cannot establish. Convergence is not proof of correctness.
