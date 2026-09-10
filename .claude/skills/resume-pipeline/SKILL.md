---
name: resume-pipeline
description: Resume a specifically identified analysis using its verified run-local artifacts and controller state.
---

# Resume the requested analysis

1. Identify the exact run. Inspect question, inputs, plan and status. If several
   match, ask which one. A latest link does not select the user's intended work.
2. Version 3 state uses `helpers.pipeline.controller.Controller`. Never overwrite
   or reinterpret legacy state as version 3. Offer a new run with explicitly
   selected, verified legacy artifacts while retaining the originals.
3. For blocked approval gates, show evidence and request approval. Record it only
   after receiving it, with checkpoint, actor and reason. Local records are not
   authenticated identities.
4. For failures, inspect the cause before retrying. Confirm an interrupted worker
   is no longer running. Never remove a lock while another controller is active.
5. Run `python -m helpers.pipeline.controller run EXACT_RUN_DIRECTORY`, with
   `--retry-failed` only for an intentional retry. Code validates definition and
   artifact hashes and skips valid completed work. Changed definitions/artifacts
   require a new reviewed run; do not silently reuse stale work.
6. Report the actual final status and outputs. Never manually change statuses or
   create a deck for a plan that did not request one.

Authentication, tool permissions and workflow approvals are separate requirements.
See `docs/PIPELINE-CONTROLLER.md` for recovery and migration details.
