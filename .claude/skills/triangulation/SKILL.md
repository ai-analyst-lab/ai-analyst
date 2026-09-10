---
name: triangulation
description: Analyze one decision through independent methods or sources, compare the paths, rerun them, and reconcile disagreement. Use when a novel analysis needs corroboration and no single answer key is available.
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

## Compare and rerun

Use `helpers.evals.triangulation.build_grid` to assemble the first grid. Run the same paths a second time under the same configuration. Use `compare_rounds` to separate run noise from persistent disagreement.

When paths disagree, locate the difference in their populations, assumptions, sources, or counterfactuals. Reconcile the difference only when the evidence supports it. Otherwise preserve the disagreement and escalate it.

When paths agree, state what their independence adds and what it still cannot establish. Convergence is not proof of correctness.
