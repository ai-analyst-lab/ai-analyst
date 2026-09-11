# File-backed workflow controller

AI Analyst 3.1 includes a version-3 controller. It has deterministic regression coverage and a
bounded live-model rehearsal. Consult `docs/PIPELINE-VERIFICATION.md` for the verified boundaries
before treating one environment or plan as evidence for every workflow.

## Responsibilities

The model proposes an analysis and explicit bindings. Python validates the plan,
launches workers, verifies artifacts, applies failure policy, and records completion.
Existing registry entries remain the coordination source; worker CONTRACT inputs
remain the input-requirement source. The compiler combines them and fails on missing
bindings. It does not infer semantic suitability from a filename.

An execution definition may also declare `context.question` and optional
`context.worker_questions`. Before each worker launches, the controller builds a deterministic
manifest from the frozen run snapshot, writes the selected source content into a bounded bundle,
and supplies both files as explicit worker inputs. A blocking trusted-definition conflict stops the
worker. The manifest records supply. It does not prove the worker applied the context correctly.

Execution mode and concurrency are separate. The initial Claude adapter runs jobs
sequentially in fresh CLI processes, including a lone ready worker. It does not
depend on native `.claude/agents/` discovery, require an Agent SDK service account,
or bypass normal tool permissions. Parallel worker scheduling is not implemented
in this initial controller. Separate runs have independent directories and locks.

## Direct definition format

Use JSON for the frozen execution request. Existing named plans remain in Markdown
for compatibility; converting their storage format is not necessary for these fixes.

```json
{
  "name": "question-then-hypothesis",
  "execution_mode": "isolated",
  "max_attempts": 2,
  "context": {"question": "Why did membership retention change?"},
  "workers": {
    "framing": {
      "file": "agents/pipeline/question-framing.md",
      "inputs": {"BUSINESS_CONTEXT": {"required": true}},
      "outputs": {"result": "question-brief.md"},
      "depends_on": []
    },
    "hypothesis": {
      "file": "agents/pipeline/hypothesis.md",
      "inputs": {"QUESTION_BRIEF": {"from": "framing.result"}},
      "outputs": {"result": "hypotheses.md"},
      "depends_on": ["framing"]
    }
  },
  "deliverables": ["hypothesis.result"]
}
```

This abbreviated example explains the format, not a complete invocation of those
workers: the framing contract also needs product description and available data.
Use `compile_named_plan` for existing plans so their required fields are checked.
Custom definitions must declare their complete input requirements themselves.

External file inputs require type `file`, exact path, SHA-256 and a purpose. They
are copied into the run's inputs directory before execution. The system checks
identity; a person or analytical method must still establish scope, meaning, and
freshness. Dataset/context values supplied as ordinary text are not automatically
snapshotted files. Declare file dependencies explicitly when identity matters.

## Required and optional contributions

`depends_on` means completion is required. `optional_dependencies` means wait for
the selected worker to finish, but permit failure when all required inputs remain
available. An input with a `from` reference adds the appropriate dependency.
An optional worker's failure never becomes a successful input or a fabricated stub.
Final status remains degraded if any selected optional worker degraded.

The legacy DAG helper still permits out-of-plan dependencies for structural graph
inspection. The execution compiler requires a named external file binding for such
omissions. Structural resolution and execution readiness are different checks.

## Artifacts and recovery

Every run has a unique directory. Every attempt has unique output paths, preventing
a previous attempt's leftover file from satisfying a new attempt. Output paths
cannot escape the assigned directory; accepted artifacts are recorded with hashes.
Query logging inherits `AI_ANALYST_QUERY_LOG_DIR` in worker subprocesses.

The Claude process starts in a per-run source workspace containing analytical code,
worker definitions, skills, templates and knowledge. Relative legacy `working/`
and `outputs/` writes stay in that workspace. Source credential files, local
permission settings, Git state, environments and dataset directories are not
implicitly copied. Supply approved data explicitly and authorize tools normally.
Knowledge can contain private business context: do not publish a run wholesale.

The controller verifies completed artifacts and worker-definition hashes before
resuming and before/after a job. A changed artifact or definition blocks reuse.
It does not automatically invalidate and recompute a graph after arbitrary edits.
Start a new run with reviewed inputs for such changes.

Normal completion updates state atomically. A per-run exclusive lock prevents two
controllers from advancing the same run. A process crash can leave a lock file.
Confirm both controller and worker processes have stopped before removing only that
run's stale lock. Then explicitly retry failed/interrupted jobs. Never clear all
run locks or infer safety merely from their age.

Version-1/2 runs are preserved and are not automatically migrated. Inspect their
outputs, select appropriate external inputs, and create a new version-3 run.
The original `init_run` helper also now avoids same-request collisions and provides
`working/latest.json` where Windows symlinks are unavailable.

## Approval and quality limits

Explicit approval gates declare completed `after` jobs and gated `before` jobs.
The actor/reason record is a local attestation. It is not identity authentication
and does not prevent a malicious local process from editing state.

The controller checks existence, containment, nonempty outputs, hashes, and JSON
syntax. Workers can declare `output_checks` against named JSON fields, or a
positive integer `max_words` for the entire whitespace-delimited text file. A word
limit failure can trigger a bounded new attempt with the failure message supplied
to the worker. The current
validation worker must supply a status JSON with `verdict: pass`; a failed or
blocked verdict prevents downstream work and is retained for inspection. The
controller does not retry a rejected review until it produces a passing answer.

Enforcing a declared verdict does not establish that the review itself is correct,
statistically valid, or complete. A model can still miss an error. Do not describe
this controller as a complete analytical quality gate or confuse it with the
later course evaluation methodology.

Output confinement is a ledger rule, not an operating-system sandbox. An engine
with broad local tool permissions may write elsewhere; those files are not accepted
as handoffs. Existing helpers may maintain indexes or caches inside the execution
workspace. These are not automatically accepted as handoffs or merged back into the
source repository. Absolute paths and broad permissions can still access outside
resources, so this is not a security boundary.

## Current migration constraints

- Exact output paths replace glob declarations for each execution. The compiler
  intentionally refuses unresolved filenames instead of guessing a successful file.
- All registered output declarations currently become required in compiled plans.
  Some legacy workers describe optional outputs in prose. Reconcile that metadata
  before claiming all historical plans run without additional configuration.
- A request must name its context question. The controller can assemble a bounded bundle from the
  frozen project snapshot, but a live warehouse schema quarantine must be passed into context
  selection before the run when structural drift is possible.
- The initial CLI adapter retains ordinary Claude Code permissions. A noninteractive
  worker can fail on a permission request; never silently grant broader permissions.
- Formal typed semantic outputs, broad metadata generation, parallel scheduling,
  and cross-repository eval/context changes remain separate work. Claude CLI and
  OpenAI-compatible engine adapters now share one request and result contract.
  A configured adapter does not imply that tool behavior, structured output,
  provider policy, or analytical quality are equivalent. No new framework is
  required for this controller.

## Explicit local-code permission option

`run EXACT_RUN_DIRECTORY --allow-local-python` is an explicit opt-in to executing
generated Python as the current user. Do not add it silently in a skill. Explain
the capability and obtain the user's approval first. It does not install packages,
change global settings, or disable permission checks. File-tool rules target the
run workspace, bound input files and attempt outputs. Bash rules target Python
script execution, not arbitrary shell commands. Python itself can access files and
network resources under the user's account, so these rules are not confinement.

Workers receive the approved execution pattern in additional system instructions:
save a script with file tools, then execute it with the specified interpreter.
Engine launch arguments and responses are preserved per attempt. Unresolved
denials stop the controller. Narrowly recognized denied alternate Python syntax
can be retained as a warning only after a non-error response; normal artifact and
downstream review requirements still apply. Read the rehearsal findings before
claiming this profile works for fresh student accounts.

The profile explicitly preapproves the read-only `Glob` and `Grep` tools. Path-bounded `Read`,
attempt-bounded `Edit`, and exact Python-script Bash rules remain separate. The controller imports
this adapter from `helpers/engines/claude_cli.py`; there is no second controller-local
implementation to keep synchronized.

The test driver's `--fresh-permissions` option omits user/project/local settings
for compatibility testing. It does not eliminate managed policy and is not the
normal student launch command.

CLI flags were checked against the installed CLI and the official
[Claude Code CLI reference](https://code.claude.com/docs/en/cli-reference).
