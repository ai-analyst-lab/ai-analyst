# Real-data rehearsal findings

September 6, 2026. This supplements deterministic test coverage with observed model
behavior. It does not certify the entire runtime or its built-in plans.

## First run

Run: `20260906T090633_6ed426e6dfe646beaea319f97899e055`.
Request record: `working/verification/rehearsal-1788685593206969000/rehearsal.json`.
Execution started after the account reset, using Opus 4.6 and normal CLI permissions.

The controller launched the analysis worker, accepted its required files, and then
launched a separate reviewer. The analysis computed the requested three monthly
counts and amounts. Those six values agree with the independently computed reference.

### Finding: correct numbers accompanied an unsupported explanation

The chart headline says promotions drove the increase. The request explicitly
asked for descriptive differences without causal claims. The report also proposes
causal explanations and later says that it makes no causal claims. That disclaimer
does not remove the contradictory statements earlier in the report or chart.

The accepted numerical JSON therefore cannot establish acceptance of the complete
analytical deliverable. Mechanical artifact acceptance is not analytical acceptance.

### Finding: scope expanded beyond reproducible saved code

The report adds promotional breakdowns, segment results, prior-quarter comparisons
and possible explanations. The saved script reproduces only the requested monthly
counts and sums. The tool transcript may contain additional queries, but they are
not included in the explicit executable-code handoff.

The worker's general drivers-analysis instructions are too expansive for this
bounded summary. Add an explicit summary mode that respects the supplied question
and requires the saved calculation to support every material numerical claim kept
in the deliverable. Do not add unrelated analysis to satisfy a general template.

### Finding: the rehearsal gave the reviewer an incomplete acceptance task

The reviewer receives code, the report and data, but not the original brief or the
chart. Its assigned scope is numerical verification of six values. Even a correct
review of those values would not establish that the original request was satisfied.

This is a defect in the test contract, not solely a model failure. The next rehearsal
must bind the original request and chart into review and assess the actual final
deliverable. Preserve this first run unchanged for comparison. Do not quietly edit
its outputs or provide the reviewer hints partway through execution.

The run completed in 528.15 seconds. The reviewer returned pass and the numeric
reference comparison passed. Manual acceptance is **rejected**. The reviewer accepted
the causal wording by citing the later disclaimer, and supplied a 95/100 confidence
grade without executing the declared scoring helper. It did catch two smaller
presentation errors. Those successes do not excuse the missed request violation.

The host uses automatic permission mode and many previously allowed tool rules.
No bypass flag was used, but this is not a fresh-student permission rehearsal.
Verify that separately before claiming unattended student compatibility.

## Second run: better handoff, incomplete acceptance

Run: `20260906T155919_cb32331e5989419e93d9677b3048af49`.
Request record: `working/verification/rehearsal-1788710359659119000/rehearsal.json`.

Changes: explicit summary mode, bounded report and chart, original question and
actual chart passed to the reviewer, explicit request/chart verdict fields, and
instructions rejecting unsupported causal wording and invented scoring. Several
things changed together, so this is an integration-repair rehearsal, not an
experiment isolating the effect of any one change.

Both workers completed in 403.95 seconds. The numerical reference matched, and the
reviewer returned pass for the request and chart. Manual review found a 529-word
report despite the explicit whole-file 400-word limit. The reviewer counted only
the narrative to excuse that violation. It also claimed scoring helpers were
unavailable without attempting to locate or import them in its tool trace.

Changes following this run: deterministic whole-file word-count limits, failure
feedback on automatic retries, explicit source-workspace location in the worker
request, snapshot-first Python imports, and a requirement to demonstrate a helper
lookup/import failure before claiming the helper is unavailable.

## Negative regression through the named validation plan

Run: `20260906T162127_19e50689a55949629b585111a59fb678`.
Record: `working/verification/rejection-1788711687410972000/rehearsal.json`.

The actual `validate_only` compiler path received the first run's unchanged report,
code, chart and original brief. The updated reviewer rejected the unsupported
causal claims despite the correct monthly figures. The controller retained the
rejected artifacts, stopped with failed status, and did not retry until it got a
pass. The negative test passed. The analysis itself did not pass.

The validation worker's cross-verification input is optional. Its registry edge
now agrees: if that worker is selected, wait for it; do not require a fabricated
cross-verification report for a standalone validation request.

## Fresh-permission rehearsals

The inherited host configuration has many prior approvals. A separate default-mode
probe with no user/project/local settings denied a file write. A second probe with
an explicit approval for that single file succeeded. No global settings changed.

The controller now has an opt-in local-Python profile. It permits file tools and
Python script execution for the assigned attempt, not arbitrary shell commands.
This authorizes generated code running as the local user. It is not an OS sandbox.

Two subsequent clean-permission runs produced analysis files but remained blocked:

- `20260906T163052_060d4a2fb74e4eaf8fae7a67278c90b7`: denied alternate Python syntax.
- `20260906T164013_54e61886692444cd9a85950d1f1ee47e`: repeated inline Python,
  heredoc and shell-listing denials before producing files through allowed scripts.

Do not accept those files retrospectively or count either run as successful. A
new rehearsal moves the file-based execution instructions into the CLI's additional
system instructions, with an explicit write-then-execute example. Permission rules
remain unchanged. The current record is
`working/verification/rehearsal-1788713774264954000/rehearsal.json`.

That run's analysis completed with zero permission denials. Reviewer launch then
failed because a long text input was probed as a filename and raised ENAMETOOLONG.
The adapter now handles non-path text without that exception, with a regression
test for long and invalid-path strings. Explicit resume preserved analysis and
launched only review. Both real workers completed with zero permission denials.
No permission rules were widened to obtain that result.

Run: `20260906T165614_b92cd273da784e0b92804171656e87c9`.
Analysis session: `8172112c-b646-4fa5-bb7a-5628dbd6c30a`.
Review session: `cea868d3-62d7-4f1b-88fd-caa5232f0a6b`.
Analysis took about 164 seconds; resumed review about 271 seconds, excluding the
intervening code diagnosis and repair. At that point the driver overwrote elapsed
time on resume; the state events preserve the individual execution timestamps.
Later driver code now records individual attempts and cumulative elapsed time.

Manual inspection: all six requested figures match, the chart is readable and
descriptive, and the report satisfies the word limit. Two extra per-order averages
have one-cent rounding errors that review identified. The review nevertheless
labels confidence A while reporting the helper capped it at C, and treats seasonal
plausibility as triangulation. These are unresolved analytical-review defects.
Runtime completion and the permission/resume checks passed. Full analytical
acceptance remains qualified; do not label this capture error-free.

## Boundaries still unverified

- A fresh-permission uninterrupted run from creation through review; the completed
  test above required a code fix and explicit resume. Analytical acceptance remains
  qualified by the issues above.
- Natural-language routing from the actual student prompt.
- All five built-in plans executing to their different deliverables.
- Native Windows execution, a fresh public clone and a published course revision.
- Repeated reliability across questions, datasets and models.

Frozen worker/context snapshots do not freeze the currently installed controller
implementation. Historical inspection verifies saved artifacts without requiring
today's source definitions to match; execution and resume still require matching
worker definitions. Do not claim complete environment reproducibility.

## Implication for Session 3

Use a handoff to teach what the next job must receive and what it is supposed to
establish. Do not teach that a reviewer validates a whole analysis merely because
it returned a report. Formal repeated evaluation remains Session 5; clear job
boundaries and useful outputs belong in the architecture lesson.
