# Agent architecture

This repository defines analytical workers and coordinates them through workflow plans.
Worker execution and workflow coordination are separate architectural decisions.

## The distinction

An agent is the general concept: an AI worker that owns a defined job inside a larger system.
There are several ways to implement that concept.

Claude Code native project subagents live in `.claude/agents/`. Claude Code discovers those files
directly and runs each worker in its own context.

The agents in this repository live in top-level `agents/`. They are pipeline workflow definitions
with contracts and variable placeholders. `/run-pipeline` reads `agents/registry.yaml`, uses
`helpers/pipeline/dag.py` to validate the graph and compute ready tiers, assembles runtime context,
then executes each selected definition.

## Execution modes

The version-3 controller launches each worker in a fresh Claude Code CLI process,
including when only one worker is ready. It runs workers sequentially initially.
There is no silent inline fallback. Native project subagents could be an alternative
execution adapter beneath the same coordination policy; the concepts do not conflict.

See `PIPELINE-CONTROLLER.md` for actual guarantees, permissions, legacy migration,
and limits. Separate context does not mean an operating-system sandbox or a fully
independent analytical review.

## Why the files stay in `agents/`

The registry points to these paths. The compiler resolves output filename variables;
the worker receives its original instructions alongside explicit named input values
and exact output paths. It interprets those bindings rather than receiving a fully
text-substituted prompt template. The contract format contains pipeline-specific
dependencies and output ownership. Moving these files into
`.claude/agents/` would not automatically convert them into native subagents and would break the
pipeline references.

Do not maintain duplicate agent definitions in both locations. If native adapters are added later,
keep the pipeline definition as the source of truth and generate or validate the adapters.

## What is deterministic

`helpers/pipeline/dag.py` deterministically handles registry loading, validation, dependency
resolution, tier computation, ready-set calculation, deadlock detection, legacy state
initialization, and execution metrics. `compile_plan.py` validates explicit request
bindings. `controller.py` owns version-3 transitions, isolated worker launch, bounded
retries, run-local artifact checks, approvals, and per-plan completion. The model
still performs analytical reasoning. Artifact validation does not prove that an
analysis is correct.

## Adding a pipeline agent

1. Create the workflow definition under the appropriate `agents/` subdirectory.
2. Add its contract using `agents/CONTRACT_TEMPLATE.md`.
3. Register it in `agents/registry.yaml`.
4. Add it to `agents/INDEX.md`.
5. Run the pipeline DAG tests and repository lint.
