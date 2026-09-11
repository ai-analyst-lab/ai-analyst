# Pipeline reliability implementation: verification and remaining work

Status: released as AI Analyst 3.1 on September 10, 2026. The deterministic suite, repository lint,
fresh-clone check, CI, secret scans, and a bounded Session 3 live rehearsal passed. The
environment-specific and analytical boundaries below remain.

Release commit: `c4b91ef835ab99da395d9addf1d4c6dacfa7668c`. The documentation-only release follow-up may move
`main` beyond that commit without changing the pinned course runtime.

Patch release 3.1.1 adds the read-only search permission repair and removes the dead duplicate
Claude adapter from the controller. The live runtime uses the one canonical implementation in
`helpers/engines/claude_cli.py`.

## Latest result after the usage reset

The historical account-limit section below is superseded. Real workers have run.
Latest full regression: **1,138 passed, one skipped**.

The fresh-permission analytical test completed after an explicit resume following
a text/path-probe bug fix. Analysis was not repeated. Both workers recorded zero
permission denials, and the requested figures matched independent SQL. A negative
test through the actual `validate_only` named plan rejected unsupported causal
claims and stopped without retrying to obtain a pass.

See `PIPELINE-REHEARSAL-FINDINGS.md` for captured run IDs, timings, first-attempt
failures and remaining analytical defects. The completed report contains two
one-cent errors in extra averages, caught by review; review's confidence and
triangulation claims still need work. This is not unconditional analytical acceptance.

Natural-language course inspection was also tried in an isolated source copy before release.
It found the relevant components but calculated results before approval and called
an exercise amount revenue. That historical inspection is not proof of the complete student build.
Native Windows and all named-plan model executions remain unverified. The released Session 3
exercise has now been rehearsed from a fresh public checkout. See the September 10 section in
`PIPELINE-REHEARSAL-FINDINGS.md` for the exact outcomes and qualifications.

## Location and preservation

- Release branch: `release/course-runtime-2026-09-10`.
- Public repository: `https://github.com/ai-analyst-lab/ai-analyst`.
- Base commit: `ae114aa5d2606701e76214f0015558a143678227`.
- Release commit: `c4b91ef835ab99da395d9addf1d4c6dacfa7668c`.
- The original dirty `ai-analyst` checkout was not modified while the release was assembled.

## What has been implemented

- Explicit optional dependency semantics in the DAG and affected real worker edges.
- Collision-safe legacy run creation, with an optional symlink and JSON navigation pointer.
- Duplicate registry and plan checks.
- A file-backed version-3 controller with bounded retries, explicit execution mode,
  per-plan deliverables, input binding, approval records, artifact containment and hashes.
- Isolated source workspaces, per-attempt outputs, external file snapshots, per-run locks,
  and explicit resume verification.
- A compiler from existing registry/contract/plan definitions to reviewed run contracts.
- A Claude Code adapter using Opus 4.6, fresh CLI processes, normal permissions, and
  inherited query-log directories. Usage/auth/permission blocks stop without blind retry.
- Shortened run/resume skills delegating mechanics to code, plus migration/limitation docs.

## Deterministic evidence

The original five new regression tests all failed before fixes. They covered optional
contribution ordering, optional failure release, duplicate registry names, repeated-run
collision, and the actual sizing/story conflict.

The isolated environment is `/tmp/ai-analyst-reliability-venv`, installed from the
project's declared development dependencies plus `pygments`. The final full regression
run initially passed **1,040 tests, with one skip and one existing deprecation
warning**. Subsequent hardening and rehearsal checks are recorded below. The JUnit record is
`working/verification/reliability-tests.xml`. All five real named plans also passed
compilation tests using explicitly labeled synthetic input fixtures. This is
structural coverage, not real analytical execution of those plans.

Fault cases cover missing inputs/outputs, failed required workers, degraded optional
workers, changed artifacts/definitions, stale attempt files, concurrent controller locks,
explicit approvals, unsupported isolation, and controller resume. Deterministic test
workers execute real file handoffs; they are not evidence of successful LLM behavior.

## Live model attempt

Sandboxed `claude auth status` misleadingly reported logged out. Outside the sandbox,
the installed Claude CLI was authenticated. No new login is needed.

The exact Opus 4.6 probe outside the sandbox returned:

```text
api_error_status: 429
You've hit your session limit; resets 3am (America/Los_Angeles)
input_tokens: 0
output_tokens: 0
```

The session ID was `aa28be57-d2d4-454b-8445-36c234a4cafa`. No analytical worker
executed. This must not be described as a successful live test. Do not switch
accounts, billing modes, or models to bypass the account limit.

## Remaining verification and engineering work

1. Test at least analysis-only and presentation boundaries through real compiled
   plans. Reconcile legacy optional/wildcard output declarations and any worker
   contract mismatches revealed by those tests. A compiler that fails safely is
   not proof that all existing plans are usable without further configuration.
2. Verify semantic analytical gates. The controller now enforces a declared JSON
   verdict, stopping on rejection without automatic review retries. This still
   does not prove the reviewer performed a correct analytical assessment. The latest
   live review allowed a minor incorrect percentage under PASS.
3. Improve context selection and request-specific exclusions. The latest rehearsal
   supplied revenue metric definitions to a request that explicitly prohibited treating
   `total_amount` as revenue.
4. Test native Windows/PowerShell startup and filesystem behavior. Symlink fallback
   code is not a substitute for an actual Windows rehearsal.
5. Review compatibility: legacy state is preserved but not auto-migrated; worker
   scheduling is initially sequential; broad platform adapters remain deferred.
6. Update this verification record and the course captures after each environment-specific
   rehearsal. Do not turn one successful run into a universal reliability claim.

The broader eval/context integration backlog remains in the approved improvement
plan. It has not been implemented by this orchestration pass.

## Continuation: September 6, before the usage reset

- Added tests for rejected review verdicts and changed helper/context snapshots.
- Declared executable analysis code as an analysis-worker output so review has
  an explicit producer for its required code input.
- Aligned CLAUDE.md and README with the new execution behavior. They no longer
  instruct a silent inline fallback or require a deck for every plan.
- Tested the CLI's logged-out envelope, which can have a null HTTP status. It now
  stops as an account block instead of retrying an analytical job.
- Prepared `scripts/rehearse_pipeline.py`: two existing worker instructions in an
  explicit bounded test contract, using real NovaMart data. The reference SQL is
  executed independently and is not supplied to the workers. This is not a blind
  security boundary, a successful model run, or proof of built-in plan routing.
- Repository lint passes with 29 non-blocking skill-description length warnings.
  Its report covers tracked files; do not imply it inspected every new file.
- Latest full suite after these changes: **1,052 passed, one skipped, one warning**,
  in 8.83 seconds. The JUnit record above contains this run.

Use `prepare` before a new rehearsal so current instructions are snapshotted.
Only `run` invokes Claude. Run assessment checks numerical output against the
reference, but still requires human inspection of the report, chart and tool trace.

The installed CLI help and official programmatic-use documentation were reviewed.
The ordinary print mode can inherit host customizations. The controller's source
snapshot is not a claim of hermetic model context. Bare mode is not being substituted
because it changes authentication requirements. Reference:
https://code.claude.com/docs/en/headless
