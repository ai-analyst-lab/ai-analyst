# SQL/results evaluations (Session 8)

This mode tests executable SQL and its result table. It does not evaluate a full analytical report, recommendation or chart. The existing complete-analysis cases and mode are unchanged.

## One case

A public case has `evaluation_mode: sql_results` and three required artifacts:

- `calculation.sql`: one read-only query using fully qualified Snowflake sources.
- `results.csv`: the resulting rows and columns, following the public formatting rules.
- `result.json`: case ID, analysis ID, context files used and artifact paths.

The runner starts the analysis record, supplies the installed Python interpreter, runs Claude in an isolated copy, and locks the output. It captures the query log and Snowflake query IDs. No report, chart, HTML trace or LLM judge is required.

The `context_files` field is a model-written account, not proof. Use `tool-events.json`, any `context_loads_<analysis_id>.jsonl` records and the SQL to inspect actual delivery and application.

## Whole suite

Run the current 16-question course suite:

```bash
python -m helpers.evals.full_suite --suite evals/suites/session-8-context-repair.yaml --parallelism 16
```

Use this repository's installed Python environment and the context store and run limits specified in the Session 8 lab. The suite includes questions about guides, semantic models and reviewed queries, plus three already-correct controls. Parallelism is explicit; actual throughput depends on account limits. The lab supplies the complete launch prompt and review steps.

Each case is stored under `working/evals/runs/<run-id>/`. The suite's manifest, system/context snapshots and progress are under `working/evals/suites/<suite-run-id>/`. Tool calls and results, execution evidence, locked files and data fingerprints remain linked to the case run.

Only after candidate runs finish, use the sibling evaluator repository:

```bash
python -m course_evals grade-suite --manifest /absolute/path/to/suite/manifest.json
```

The evaluator executes the candidate SQL and independent reference SQL against the verified data source. It compares result tables using explicit keys, types and tolerances, and checks that the saved CSV agrees with executed SQL. Different SQL text can pass. It does not need to match the reference query's wording.

The report says **SQL/result accuracy**. A final-answer judge is not assessed, rather than incorrectly counted as a pass or failure. Scheduled failures remain visible; a formatting-contract problem or reference mistake must be diagnosed before blaming the analyst.

For matched context experiments, `python -m course_evals compare-suites --before <manifest> --after <manifest>` checks case set/version, model, runtime/case fingerprint, data and grader compatibility. It preserves case-level regressions and improvements. Keep case instructions and grader tolerances fixed between the before and after runs.

## Access and platform limits

SQL workers deny the configured sibling evaluator/course directories and previous working outputs, disable external MCPs, and restrict shell network access to Snowflake. Sandbox failure is an error, not permission to run unprotected. macOS and supported Linux/WSL2 environments need their documented sandbox dependencies. Native Windows requires a supported execution environment before this mode is suitable for students.

This is not an adversarial-security guarantee. References copied into an unlisted location, privileged tools or an incorrectly configured host can defeat a local development setup. Use a separate contained environment for genuinely held-out/adversarial evaluation.

The direct path context source removes cache-reset steps. Isolated runs still take a per-run snapshot so edits during a run cannot silently change that run's inputs. A snapshot is an evidence record, not the mutable sync cache used by the legacy Git resolver.
