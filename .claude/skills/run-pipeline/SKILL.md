---
name: run-pipeline
description: Plan and run coordinated analysis using explicit input bindings, isolated workers, run-local artifacts, and the Python workflow controller.
---

# Run an analytical workflow

Choose the amount of work that serves the request. A chart, investigation,
validation report, and presentation have different completion conditions.
Do not add presentation work to an analysis-only or validation-only request.

## Inspect and propose

Read `plans.md`, `agents/registry.yaml`, and the selected worker contracts.
The registry declares coordination; contracts declare input requirements.
Do not infer required inputs from whatever happens to exist in global outputs.

Prepare a request JSON under `working/requests/` with:

- `plan`: an existing named plan.
- `variables`: concrete filename placeholder values.
- `bindings`: each worker's input values or explicit producer references.
- `output_paths`: exact paths replacing wildcard/dynamic output declarations.
- `external_dependencies`: input names replacing omitted producers.
- `approval_gates`: required approvals with `id`, `after`, and `before`.
- `context`: the exact analytical `question`, plus optional `worker_questions` when a worker needs
  a narrower framing.

For produced inputs use `{"from": "worker.result"}`. The first registered output
is `result`; later outputs are `artifact_2`, etc. Inspect the registry before
selecting one. For existing files supply an exact `path`, computed `sha256`,
and a `purpose` explaining why the file suits this question. Evaluate dataset,
scope and age as well: a hash establishes identity, not analytical suitability.

Never invent missing data, credentials, meaning, or approval. Ask only for inputs
that cannot be safely supplied from the request and verified context.

When `context.question` is present, the controller builds a deterministic manifest and bounded
bundle for each worker from the frozen run snapshot. It attaches both as explicit inputs and blocks
on trusted-definition conflicts. The bundle records supply. Workers must cite relevant context item
IDs, and downstream validation still checks whether the work applied them.

## Compile before executing

Use the active project Python environment:

```python
import json
from pathlib import Path
from helpers.pipeline.compile_plan import compile_named_plan
from helpers.pipeline.controller import Controller

root = Path.cwd()
request = json.loads(Path("working/requests/request.json").read_text())
definition, inputs = compile_named_plan(root, request)
print(json.dumps(definition, indent=2))
```

Replace the request path with the actual file. Review jobs, input bindings,
handoffs, deliverables and stopping conditions before execution.
`dry-run=true` ends here without creating a run or launching workers. Compilation
is not model execution or proof of analytical correctness.

For custom workflows use the explicit definition format in
`docs/PIPELINE-CONTROLLER.md`. A list of worker names alone is not a complete
workflow contract.

## Execute through the controller

After the proposed scope is authorized:

```python
run = Controller.create(root, definition, inputs)
print(run.directory)
```

Then invoke `python -m helpers.pipeline.controller run EXACT_RUN_DIRECTORY`.
The controller uses Claude Code with `claude-opus-4-6`, a fresh process per job,
normal permissions, and explicit output paths. Never bypass permissions or
silently execute a blocked isolated job inline. Workers must not recursively
invoke this skill or edit controller state.

Code owns readiness, bounded retries, artifact checks, status and completion.
Query logging inherits a worker-specific directory. Only validated run-local
artifacts enter the handoff ledger. This is logical isolation, not an OS sandbox.

Numeric historical checkpoints in plans are not executable approvals. New gates
are explicit. Record an approval only after the named person approves the actual
evidence; local actor strings do not authenticate identities.

## Inspect and report

Read final status and actual artifacts. An optional failure produces a degraded
run, even when a deliverable exists. Missing required evidence is not success.
Structural checks do not establish analytical correctness. Apply the relevant
analytical methods and preserve limitations.

Presentation workers retain their own chart, storytelling and export standards.
This entry point does not impose those deliverables on unrelated plans.

Resume only the explicitly identified run using `/resume-pipeline`. Do not copy
global artifacts into a run to make it look complete. See
`docs/PIPELINE-CONTROLLER.md` for migration and current limitations.
