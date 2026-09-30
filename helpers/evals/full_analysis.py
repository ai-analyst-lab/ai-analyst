"""Lifecycle for versioned full-analysis development evaluation cases."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import struct
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from .controller import new_run_id
from .fingerprints import file_digest, payload_digest, system_fingerprint
from .records import write_json
from helpers.knowledge.analysis_context import current_analysis


SCHEMA_VERSION = "1"
REQUIRED_OUTPUTS = (
    "result.json",
    "monthly-results.csv",
    "brief.md",
    "chart.png",
    "chart-data.csv",
    "calculation.sql",
)
PRIVATE_FIELD_NAMES = frozenset(
    {
        "expected",
        "accepted",
        "reference",
        "reference_query",
        "answer",
        "answer_key",
        "ground_truth",
        "judge_prompt",
    }
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _read_yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a YAML mapping")
    return value


def _private_keys(value: Any, path: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else str(key)
            if str(key).lower() in PRIVATE_FIELD_NAMES:
                found.append(child_path)
            found.extend(_private_keys(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(_private_keys(child, f"{path}[{index}]"))
    return found


def load_public_case(case_dir: str | Path) -> tuple[Path, dict[str, Any], dict[str, Any]]:
    root = Path(case_dir).resolve()
    case_path = root / "case.yaml"
    schema_path = root / "result.schema.json"
    if not case_path.is_file() or not schema_path.is_file():
        raise ValueError(f"public case must contain case.yaml and result.schema.json: {root}")
    case = _read_yaml(case_path)
    result_schema = _read_json(schema_path)
    leaks = _private_keys(case)
    if leaks:
        raise ValueError(f"public case contains private fields: {leaks}")
    for field in ("case_id", "case_version", "task", "data_scope", "required_outputs"):
        if not case.get(field):
            raise ValueError(f"public case is missing {field}")
    required_outputs = tuple(case["required_outputs"])
    mode = case.get("evaluation_mode", "full_analysis")
    if mode not in {"full_analysis", "sql_results"}:
        raise ValueError(f"unknown evaluation_mode: {mode}")
    core_outputs = ({"result.json", "calculation.sql"} if mode == "sql_results" else
                    {"result.json", "brief.md", "chart.png", "chart-data.csv", "calculation.sql"})
    if any(Path(name).name != name or name.startswith(".") for name in required_outputs):
        raise ValueError("required_outputs must be plain file names")
    if not core_outputs <= set(required_outputs):
        raise ValueError(f"required_outputs must include {sorted(core_outputs)}")
    result_tables = [name for name in required_outputs if name.endswith(".csv") and name != "chart-data.csv"]
    if len(required_outputs) != len(core_outputs) + 1 or len(result_tables) != 1:
        raise ValueError("required_outputs must contain the mode's core artifacts and one result-table CSV")
    if case.get("result_schema") != "result.schema.json":
        raise ValueError("result_schema must point to result.schema.json")
    return root, case, result_schema


def _compact_system_fingerprint(project_root: Path) -> dict[str, Any]:
    value = system_fingerprint(project_root)
    return {
        "system_digest": value["system_digest"],
        "file_count": value["tree"]["file_count"],
        "git": value["git"],
    }


def _verify_snowflake_snapshot(project_root: Path, data_scope: dict[str, Any]) -> dict[str, Any]:
    expected = (data_scope.get("snapshot_fingerprint") or {}).get("sha256")
    if not expected:
        raise ValueError("Snowflake case is missing an expected snapshot fingerprint")
    try:
        from dotenv import load_dotenv
        import snowflake.connector
    except ImportError as exc:
        raise ValueError("Snowflake snapshot verification dependencies are unavailable") from exc

    load_dotenv(project_root / ".env")
    required = (
        "SNOWFLAKE_ACCOUNT",
        "SNOWFLAKE_USER",
        "SNOWFLAKE_WAREHOUSE",
        "SNOWFLAKE_DATABASE",
        "SNOWFLAKE_ROLE",
    )
    missing = [name for name in required if not os.environ.get(name)]
    if missing:
        raise ValueError(f"Snowflake snapshot verification is missing environment variables: {missing}")
    kwargs = {
        "account": os.environ["SNOWFLAKE_ACCOUNT"],
        "user": os.environ["SNOWFLAKE_USER"],
        "warehouse": os.environ["SNOWFLAKE_WAREHOUSE"],
        "database": os.environ["SNOWFLAKE_DATABASE"],
        "role": os.environ["SNOWFLAKE_ROLE"],
        "schema": data_scope["schema"],
    }
    auth = os.environ.get("SNOWFLAKE_AUTHENTICATOR", "password").lower().replace("-", "_")
    if auth in {"programmatic_access_token", "pat"}:
        kwargs["authenticator"] = "PROGRAMMATIC_ACCESS_TOKEN"
        kwargs["token"] = os.environ.get("SNOWFLAKE_TOKEN")
    else:
        kwargs["password"] = os.environ.get("SNOWFLAKE_PASSWORD")
    if not kwargs.get("token") and not kwargs.get("password"):
        raise ValueError("Snowflake snapshot verification is missing its authentication credential")

    fingerprint = data_scope["snapshot_fingerprint"]
    query = fingerprint.get("query")
    if not query:
        qualified = ".".join(
            str(data_scope[name]) for name in ("database", "schema", "table")
        )
        query = f"""
            SELECT COUNT(*), MIN(order_date), MAX(order_date),
                   COUNT(DISTINCT order_id), ROUND(SUM(total_amount), 2)
            FROM {qualified}
        """
    with snowflake.connector.connect(**kwargs) as connection:
        with connection.cursor() as cursor:
            cursor.execute(query)
            values = cursor.fetchone()
    canonical = "|".join(str(value) for value in values)
    observed = hashlib.sha256(canonical.encode()).hexdigest()
    if observed != expected:
        raise ValueError(
            "Snowflake snapshot fingerprint does not match the case. "
            "Do not compare this run with the reviewed reference until the data is reconciled."
        )
    return {
        "status": "verified",
        "snapshot_id": data_scope.get("snapshot_id"),
        "method": data_scope["snapshot_fingerprint"]["method"],
        "sha256": observed,
        "verified_at": utc_now(),
    }


def _append_event(run_root: Path, event: str, **details: Any) -> None:
    payload = {"at": utc_now(), "event": event, **details}
    with (run_root / "events.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True, default=str) + "\n")


def _resolve_run(runs_root: str | Path, run_id: str) -> Path:
    root = Path(runs_root).resolve() / run_id
    if not (root / "manifest.json").is_file():
        raise ValueError(f"evaluation run does not exist: {run_id}")
    return root


def _only_trial(run_root: Path, trial_id: str | None = None) -> Path:
    trials_root = run_root / "trials"
    if trial_id:
        trial = trials_root / trial_id
        if not (trial / "trial.json").is_file():
            raise ValueError(f"trial does not exist in run: {trial_id}")
        return trial
    trials = sorted(path for path in trials_root.iterdir() if (path / "trial.json").is_file())
    if len(trials) != 1:
        raise ValueError("specify --trial-id when a run does not contain exactly one trial")
    return trials[0]


def _sql_discovery_snapshot(project_root: Path, run_root: Path, dataset: str | None) -> dict[str, Any] | None:
    """Save the same local catalogs a SQL worker otherwise discovers with two calls.

    This neither selects resources nor loads guide bodies or executes SQL. Errors
    remain explicit: an unavailable catalog must never look like an empty one.
    """
    if not dataset:
        return None
    from helpers.knowledge.context_guides import guide_catalog
    from helpers.connected_context.store import Store
    payload: dict[str, Any] = {"schema_version": "1", "dataset": dataset, "status": "ready"}
    try:
        payload["business_guides"] = guide_catalog(project_root, dataset=dataset)
        payload["calculations"] = Store.from_project(project_root, dataset).catalog()
    except Exception as exc:
        payload = {"schema_version": "1", "dataset": dataset, "status": "error", "error_type": type(exc).__name__, "error": str(exc)}
    path = run_root / "context-discovery.json"
    write_json(path, payload)
    return {"path": str(path), "sha256": file_digest(path), "status": payload["status"]}


def start_run(
    *,
    project_root: str | Path,
    case_dir: str | Path,
    runs_root: str | Path = "working/evals/runs",
    baseline_run_id: str | None = None,
    intended_change: str | None = None,
    model: str = "claude-opus-4-6",
) -> dict[str, Any]:
    project_root = Path(project_root).resolve()
    runs_root = (
        Path(runs_root).resolve()
        if Path(runs_root).is_absolute()
        else (project_root / runs_root).resolve()
    )
    case_root, case, result_schema = load_public_case(case_dir)
    exposure = "development" if baseline_run_id else "blind"
    baseline_manifest = None
    if baseline_run_id:
        baseline_root = _resolve_run(runs_root, baseline_run_id)
        baseline_manifest = _read_json(baseline_root / "manifest.json")
        for field, observed in (
            ("case_id", case["case_id"]),
            ("case_version", str(case["case_version"])),
            ("data_snapshot", case["data_scope"].get("snapshot_id")),
        ):
            if str(baseline_manifest.get(field)) != str(observed):
                raise ValueError(
                    f"baseline is incompatible on {field}: "
                    f"{baseline_manifest.get(field)!r} != {observed!r}"
                )

    run_id = new_run_id("analysis-eval")
    trial_id = f"{case['case_id']}-t1-{uuid.uuid4().hex[:6]}"
    run_root = runs_root / run_id
    trial_root = run_root / "trials" / trial_id
    draft = trial_root / "draft"
    public_copy = trial_root / "public-case"
    draft.mkdir(parents=True)
    public_copy.mkdir(parents=True)
    for name in ("case.yaml", "result.schema.json", "README.md"):
        source = case_root / name
        if source.is_file():
            shutil.copy2(source, public_copy / name)

    public_files = [
        {
            "path": path.name,
            "sha256": file_digest(path),
            "bytes": path.stat().st_size,
        }
        for path in sorted(public_copy.iterdir())
        if path.is_file()
    ]
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "suite_id": "sql-results-development" if case.get("evaluation_mode") == "sql_results" else "full-analysis-development",
        "evaluation_mode": case.get("evaluation_mode", "full_analysis"),
        "status": "awaiting_submission",
        "exposure": exposure,
        "case_id": case["case_id"],
        "case_version": str(case["case_version"]),
        "data_snapshot": case["data_scope"].get("snapshot_id"),
        "data_scope": case["data_scope"],
        "baseline_run_id": baseline_run_id,
        "intended_change": intended_change,
        "model": model,
        "project_root": str(project_root),
        "runs_root": str(runs_root),
        "public_task_digest": payload_digest(case),
        "public_case_files": public_files,
        "system_fingerprint": _compact_system_fingerprint(project_root),
        "created_at": utc_now(),
        "trial_ids": [trial_id],
    }
    trial = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "trial_id": trial_id,
        "case_id": case["case_id"],
        "case_version": str(case["case_version"]),
        "status": "draft",
        "draft_path": str(draft),
        "analysis_id": None,
        "artifact_bundle_digest": None,
        "created_at": utc_now(),
    }
    if case.get("evaluation_mode") == "sql_results":
        from helpers.knowledge.analysis_context import start_analysis
        active_path = project_root / ".knowledge" / "active.yaml"
        active_dataset = _read_yaml(active_path).get("active_dataset") if active_path.is_file() else None
        trial["analysis_id"] = start_analysis(
            working_dir=project_root / "working", question=case["task"],
            dataset=active_dataset or "unknown", output_dir=draft,
        )
        discovery = _sql_discovery_snapshot(project_root, run_root, active_dataset)
        if discovery is not None:
            manifest["context_discovery"] = discovery
    write_json(run_root / "manifest.json", manifest)
    write_json(trial_root / "trial.json", trial)
    _append_event(run_root, "run_started", trial_id=trial_id, exposure=exposure)

    trace_instruction = (
        "This is a SQL/results test, not a complete-analysis test. Start one analysis record with the trace helper, "
        "use its analysis ID for the connection helper's query log, and save your SQL and result table. "
        "Record any context files you read in result.json. Do not create a report, chart, findings or HTML trace. "
        "The lock captures the analysis record and query log automatically."
        if case.get("evaluation_mode") == "sql_results" else
        "Use that same analysis ID for every query, finding, receipt, and trace artifact in this trial. "
        "Do not start a second analysis trace."
    )
    instructions = f"""# Run {run_id}

Read `trials/{trial_id}/public-case/README.md` and `case.yaml`.

Before querying data, use the repository's trace skill to start one analysis trace whose output directory is exactly:

`{draft}`

{trace_instruction}

Complete the analysis with AI Analyst and save exactly these required files in:

`{draft}`

{chr(10).join(f'- `{name}`' for name in case['required_outputs'])}

After the analysis and trace are complete, lock the run:

```bash
python3 -m helpers.evals.full_analysis lock --run-id {run_id}
```

Do not place reference answers or grader files in this run directory.
Do not use the incomplete-trace or snapshot-verification bypass flags. If the lock reports
missing trace evidence, repair the trace and run the normal lock command again.
"""
    (run_root / "RUN-INSTRUCTIONS.md").write_text(instructions, encoding="utf-8")
    if case.get("evaluation_mode") == "sql_results":
        instructions = f"""# SQL/results run {run_id}

This run and analysis record already exist. Do not start another run or analysis.
Use analysis ID `{trial['analysis_id']}`. The active analysis record points to this draft.
The exact task from the public case is:

{case['task']}

The remaining public-case fields are reproduced without removing any constraints:
```yaml
{yaml.safe_dump({key: value for key, value in case.items() if key != 'task'}, sort_keys=False)}
```

The exact result.json schema is:
```json
{json.dumps(result_schema, indent=2)}
```

The full public case and schema remain available at `{public_copy / 'case.yaml'}`
and `{public_copy / 'result.schema.json'}`. Follow the output contract and data scope
above as well as the task and JSON schema. You do not need to reread those files
merely to rediscover the same fields reproduced above.

Use the existing Python interpreter supplied by the runner. Do not create a virtual
environment or install dependencies. Use ConnectionManager for logged Snowflake queries.
For physical column names and types, use the supported metadata method
`conn.get_table_schema('TABLE')` inside the same ConnectionManager context; it returns
a list of dictionaries with `name`, `type` and `nullable`. Use an actual table name
in the configured dataset scope. Do not send DESCRIBE or INFORMATION_SCHEMA discovery
through conn.query: that method is for scoped analytical SELECTs. Metadata is not a
business definition or proof of which column implements a business rule.
Save only result.json, results.csv and calculation.sql under `{draft}`.
Record the paths of context files actually read in result.json; do not invent a list.
Before calculating, inspect BOTH the business-guide catalog and the connected
calculation catalog for the active dataset from .knowledge/active.yaml:
If `context-discovery.json` exists beside this instruction file with status `ready`,
read it: it contains the same two local catalogs prepared for this isolated run,
including workspace guidance, descriptions, eligibility and resource hashes. This
satisfies catalog discovery; do not repeat the catalog calls just to obtain the
same information. It does not select a resource or load a guide's full content.
If its status is `error`, that is a discovery problem, not an empty catalog. Inspect
the error and use the normal commands below to diagnose it or report the blocker.
When no snapshot is present, obtain both catalogs with:
`helpers.knowledge.context_guides.guide_catalog('.', dataset=<active_dataset from .knowledge/active.yaml>)`.
`-m helpers.connected_context --dataset DATASET catalog`
Read workspace guidance and descriptions. Load relevant guides with `load_guide` using
their catalog hashes and this analysis ID. Do not preload every guide or invent missing policy.
The exact Python call is:
`helpers.knowledge.context_guides.load_guide('.', dataset=DATASET, guide_id=ID, question=QUESTION, reason=REASON, analysis_id='{trial['analysis_id']}', expected_sha256=HASH)`.
Use the catalog's `file_sha256` for HASH. DATASET, ID, QUESTION and REASON are your
discovered dataset, selected guide, current question and selection explanation.
Inspect eligible metric/query resources, including any guide `implementations` links;
the connected catalog also exposes resources that have no guide link. A loaded guide
or a model YAML file is not an executed calculation.

Choose the calculation path by meaning, population, period, grouping and supported
parameters. When an eligible maintained metric or reviewed query exactly supports
the question, load it with its catalog hash and selection reason, then execute it
through the installed connected-context service. Do not rewrite its SQL manually.
Use the supplied interpreter with these commands (DATASET, KIND, ID, HASH and REQUEST
are values discovered from the catalog, not literal placeholders):
`-m helpers.connected_context --dataset DATASET load KIND ID --hash HASH --analysis-id {trial['analysis_id']} --reason 'why this scope matches'`
Save a structured YAML/JSON request under working/ with `metric_id`, declared
`parameters`, and supported `dimensions`, or with `query_id` and declared `parameters`.
`-m helpers.connected_context --dataset DATASET plan REQUEST`
`-m helpers.connected_context --dataset DATASET run REQUEST --analysis-id {trial['analysis_id']}`
Inspect its checks and returned artifacts. A successful run records an `executed`
event with mode `semantic_compiled` or `reviewed_query`, query ID and resource hash.
Keep those original artifacts under working/context-runs/ for trace capture.

Use the returned results and replayable calculation.sql for the submission. If the
case requires only presentation changes (column aliases, column selection, ordering
or rounding), wrap the returned SQL as a subquery, execute that wrapper through
ConnectionManager using the same analysis ID, and save its SQL and actual returned
CSV. Preserve the maintained calculation inside it; do not replace it with handwritten
source-table SQL or hard-coded results.
For simple selection/rounding/aliases/order, prefer `-m helpers.connected_context --dataset DATASET present EXECUTION_DIR PRESENTATION_YAML --analysis-id {trial['analysis_id']}` with `columns: [{{column: INPUT, name: OUTPUT, round: DIGITS}}]` (round optional) and optional `order_by: [OUTPUT]`; it executes and verifies a wrapper around the preserved SQL and records parent lineage.

If no eligible executable supports the requested scope, generated SQL is allowed
when the business meaning and source mapping are sufficient. A nearby reviewed
query may be loaded as an exemplar and adapted for a different grouping or scope;
label that calculation generated/adapted, log its actual SQL, and keep the reviewed
resource unchanged. Never label adapted SQL as reviewed-query or semantic execution.
Missing business meaning, ambiguous matching definitions, failed quality checks or
failed safety/review checks must be reported; do not bypass those failures by
silently generating an equivalent query.

For generated/adapted SQL or a presentation wrapper, the supported logged query API
is the following Python pattern. `sql` must contain your actual read-only SQL and
DATASET must be the active dataset you discovered; neither is an answer supplied
by the runner. Use required column aliases and rounding in SQL, not a separate
unlogged alteration of the returned values.

```python
from pathlib import Path
from helpers.data.connection_manager import ConnectionManager
draft = Path({str(draft)!r})
with ConnectionManager(dataset_id=DATASET) as conn:
    frame = conn.query(sql, analysis_id={trial['analysis_id']!r})
frame.to_csv(draft / 'results.csv', index=False)
(draft / 'calculation.sql').write_text(sql)
```

The query method returns a pandas DataFrame, not a dictionary or a cursor. For
Snowflake output, double-quote aliases to match the case's required column names
exactly (for example, AS "segment" and AS "value"); unquoted aliases become uppercase.
Check the actual DataFrame columns before exporting. Do not rename only the CSV
while leaving different column names in the saved SQL result. For
result.json, follow the supplied schema: case_id is {case['case_id']!r}, analysis_id
is {trial['analysis_id']!r}; standard artifact paths are calculation.sql and results.csv.
List only context files actually read. Do not add narrative or status keys forbidden
by that schema. A parameterized library query must remain unchanged in the library;
the submitted calculation.sql must be replayable for this case without missing
parameter values. Inspect the service's returned calculation.sql before copying it.

Record the selected path and any adaptation or presentation wrapper in the existing
context event stream, not extra result.json fields. Use
`helpers.connected_context.store.event('.', ANALYSIS_ID, 'calculation_selected', path=PATH, reason=REASON)`
with this run's analysis ID and the chosen path (`semantic_compiled`, `reviewed_query`,
or `generated_sql`). For adaptation, include `source_query_id`, `source_hash` and
`adaptation` keyword details; for presentation changes include `presentation` details.
This selection note explains intent; only the service's later `executed` event proves
maintained execution. Keep result.json within its supplied schema; do not invent fields.

No report, chart, findings or HTML trace is needed. The lock copies the SQL execution
log, connected execution events and any maintained-calculation artifacts.

Use the supplied interpreter to run:
`-m helpers.evals.full_analysis lock --run-id {run_id}`

After the normal lock succeeds, the task is complete. Return the run ID and final
lock status immediately; do not begin another inspection or calculation after locking.

Do not use bypass flags or read reference answers. If execution or locking fails,
report the error for this run instead of starting another run or changing the case.
If essential business meaning is unavailable after inspecting the relevant catalogs
and accessible sources, stop with that specific missing-information explanation.
Do not repeatedly search unavailable sources or fabricate numeric rows to satisfy
the output contract. Such a run is incomplete, not a successful numeric submission.
"""
        (run_root / "RUN-INSTRUCTIONS.md").write_text(instructions, encoding="utf-8")
    return {
        "run_id": run_id,
        "trial_id": trial_id,
        "run_root": str(run_root),
        "draft_path": str(draft),
        "task_path": str(public_copy / "case.yaml"),
        "instructions_path": str(run_root / "RUN-INSTRUCTIONS.md"),
        "exposure": exposure,
        "analysis_id": trial["analysis_id"],
    }


def _analysis_id_for_lock(
    *, project_root: Path, trial_root: Path, requested_analysis_id: str | None
) -> str | None:
    """Resolve the analysis that actually produced this trial's draft.

    Evaluation setup creates the immutable run boundary, while the analytical
    workflow creates the analysis boundary when work begins. The link is valid
    only when the analysis output directory is this exact trial draft.
    """
    draft = (trial_root / "draft").resolve()
    if requested_analysis_id:
        record_path = project_root / "working" / f"analysis_{requested_analysis_id}.json"
        if not record_path.is_file():
            raise ValueError(f"analysis record does not exist: {record_path}")
        record = _read_json(record_path)
    else:
        record = current_analysis(working_dir=project_root / "working")
        if not record:
            raise ValueError(
                "no active analysis trace exists; start one with the trial draft as its output directory"
            )
        requested_analysis_id = record.get("analysis_id")
    if not requested_analysis_id:
        raise ValueError("analysis record is missing analysis_id")
    output_dir = record.get("output_dir")
    if not output_dir:
        raise ValueError("analysis record is missing output_dir")
    observed = Path(output_dir).expanduser()
    if not observed.is_absolute():
        observed = project_root / observed
    if observed.resolve() != draft:
        raise ValueError(
            "active analysis belongs to a different output directory: "
            f"{observed.resolve()} != {draft}"
        )
    return str(requested_analysis_id)


def _schema_errors(value: Any, schema: dict[str, Any], path: str = "result") -> list[str]:
    errors: list[str] = []
    kind = schema.get("type")
    matches_type = {
        "object": isinstance(value, dict),
        "array": isinstance(value, list),
        "string": isinstance(value, str),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "number": isinstance(value, (int, float)) and not isinstance(value, bool),
        "boolean": isinstance(value, bool),
    }
    if kind and not matches_type.get(kind, True):
        return [f"{path} must be {kind}"]
    if "const" in schema and value != schema["const"]:
        errors.append(f"{path} must equal {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path} must be one of {schema['enum']!r}")
    if isinstance(value, dict):
        required = set(schema.get("required") or [])
        missing = sorted(required - set(value))
        if missing:
            errors.append(f"{path} is missing {missing}")
        properties = schema.get("properties") or {}
        if schema.get("additionalProperties") is False:
            extra = sorted(set(value) - set(properties))
            if extra:
                errors.append(f"{path} has unexpected fields {extra}")
        for name, child_schema in properties.items():
            if name in value:
                errors.extend(_schema_errors(value[name], child_schema, f"{path}.{name}"))
    if isinstance(value, list):
        if len(value) < int(schema.get("minItems", 0)):
            errors.append(f"{path} has fewer than {schema['minItems']} items")
        if schema.get("maxItems") is not None and len(value) > int(schema["maxItems"]):
            errors.append(f"{path} has more than {schema['maxItems']} items")
        item_schema = schema.get("items") or {}
        for index, item in enumerate(value):
            errors.extend(_schema_errors(item, item_schema, f"{path}[{index}]"))
    if isinstance(value, str) and len(value) < int(schema.get("minLength", 0)):
        errors.append(f"{path} is shorter than {schema['minLength']} characters")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if schema.get("minimum") is not None and value < schema["minimum"]:
            errors.append(f"{path} is below {schema['minimum']}")
    return errors


def _validate_result_contract(
    draft: Path,
    case: dict[str, Any],
    result_schema: dict[str, Any],
) -> dict[str, Any]:
    case_id = case["case_id"]
    required_outputs = tuple(case["required_outputs"])
    files = {path.name for path in draft.iterdir() if path.is_file() and not path.name.startswith(".")}
    missing = sorted(set(required_outputs) - files)
    system_evidence = {name for name in files if re.fullmatch(r"trace_an_[^.]+\.html", name)}
    extra = sorted(files - set(required_outputs) - system_evidence)
    if missing or extra:
        raise ValueError(f"draft output mismatch: missing={missing}, extra={extra}")

    result = _read_json(draft / "result.json")
    errors = _schema_errors(result, result_schema)
    if errors:
        raise ValueError("result.json does not match result.schema.json: " + "; ".join(errors[:20]))

    contract = case.get("output_contract") or {}
    for spec in contract.get("csv") or []:
        name = spec["path"]
        with (draft / name).open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            csv_rows = list(reader)
            if reader.fieldnames != spec["columns"]:
                raise ValueError(f"{name} columns must be {spec['columns']}")
            if len(csv_rows) < int(spec.get("min_rows", 0)):
                raise ValueError(f"{name} has too few rows")
            if spec.get("max_rows") is not None and len(csv_rows) > int(spec["max_rows"]):
                raise ValueError(f"{name} has too many rows")

    full_analysis = case.get("evaluation_mode", "full_analysis") == "full_analysis"
    text_spec = contract.get("text") or ({"path": "brief.md", "min_characters": 100} if full_analysis else None)
    if text_spec:
        brief = (draft / text_spec["path"]).read_text(encoding="utf-8").strip()
        if len(brief) < int(text_spec.get("min_characters", 1)):
            raise ValueError(f"{text_spec['path']} is too short")
    sql_spec = contract.get("sql") or {"path": "calculation.sql"}
    sql = (draft / sql_spec["path"]).read_text(encoding="utf-8").strip()
    if not sql:
        raise ValueError(f"{sql_spec['path']} is empty")
    image_spec = contract.get("image") or ({"path": "chart.png", "min_width": 400, "min_height": 250} if full_analysis else None)
    if image_spec:
        png = (draft / image_spec["path"]).read_bytes()
        if len(png) < 24 or png[:8] != b"\x89PNG\r\n\x1a\n":
            raise ValueError(f"{image_spec['path']} is not a readable PNG")
        width, height = struct.unpack(">II", png[16:24])
        if width < int(image_spec.get("min_width", 1)) or height < int(image_spec.get("min_height", 1)):
            raise ValueError(f"{image_spec['path']} is too small: {width}x{height}")
    return result


def _copy_calculation_evidence(working: Path, destination: Path, analysis_id: str | None) -> list[Path]:
    """Preserve maintained calculation artifacts before a temporary worker disappears."""
    if not analysis_id:
        return []
    if not re.fullmatch(r"an_[A-Za-z0-9_]+", analysis_id):
        raise ValueError("Invalid calculation evidence analysis ID")
    root = working / "context-runs" / analysis_id
    if not root.exists():
        return []
    if root.is_symlink() or root.parent.is_symlink():
        raise ValueError("Calculation evidence rejects symlinks")
    copied = []
    names = {"plan.json", "executed.sql", "parameters.json", "calculation.sql", "results.csv", "execution.json", "failure.json"}
    for run in sorted(root.iterdir()):
        if run.is_symlink():
            raise ValueError("Calculation evidence rejects symlinks")
        if not run.is_dir():
            continue
        for name in sorted(names):
            source = run / name
            if source.is_symlink():
                raise ValueError("Calculation evidence rejects symlinks")
            if source.is_file():
                target = destination / "connected-calculations" / run.name / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
                copied.append(target)
    return copied


def _copy_trace_evidence(
    *, project_root: Path, trial_root: Path, analysis_id: str | None,
    evaluation_mode: str = "full_analysis",
) -> dict[str, Any]:
    trace_root = trial_root / "trace"
    trace_root.mkdir(parents=True, exist_ok=True)
    working = project_root / "working"
    copied: list[Path] = []
    missing: list[str] = []
    if not analysis_id:
        missing = ["analysis_record", "query_log", "action_log", "trace_receipt", "provenance", "trace_html"]
    else:
        direct = {
            "analysis_record": working / f"analysis_{analysis_id}.json",
            "trace_receipt": working / f"trace_receipt_{analysis_id}.json",
            "provenance": working / f"provenance_{analysis_id}.json",
            "findings": working / f"findings_{analysis_id}.jsonl",
        }
        analysis_record = None
        for label, source in direct.items():
            if source.is_file():
                target = trace_root / source.name
                shutil.copy2(source, target)
                copied.append(target)
                if label == "analysis_record":
                    analysis_record = _read_json(source)
            elif label != "findings":
                missing.append(label)

        for label, pattern in (("query_log", "query_log_*.jsonl"), ("action_log", "action_log_*.jsonl"), ("context_loads", "context_loads_*.jsonl"), ("connected_context", "connected_context_*.jsonl")):
            matches: list[str] = []
            for source in sorted(working.glob(pattern)):
                for line in source.read_text(encoding="utf-8").splitlines():
                    try:
                        row = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if row.get("analysis_id") == analysis_id:
                        matches.append(json.dumps(row, sort_keys=True, default=str))
            if matches:
                target = trace_root / f"{label}_{analysis_id}.jsonl"
                target.write_text("\n".join(matches) + "\n", encoding="utf-8")
                copied.append(target)
            elif label not in {"context_loads", "connected_context"}:
                missing.append(label)

        trace_candidates = [working / f"trace_{analysis_id}.html"]
        if analysis_record and analysis_record.get("output_dir"):
            trace_candidates.append(
                Path(analysis_record["output_dir"]).expanduser() / f"trace_{analysis_id}.html"
            )
        trace_source = next((path for path in trace_candidates if path.is_file()), None)
        if trace_source:
            target = trace_root / f"trace_{analysis_id}.html"
            shutil.copy2(trace_source, target)
            copied.append(target)
        else:
            missing.append("trace_html")

    if evaluation_mode == "sql_results":
        # SQL mode captures execution evidence, not a fabricated full analytical trace.
        missing = [label for label in missing if label in {"analysis_record", "query_log"}]
    copied.extend(_copy_calculation_evidence(working, trace_root, analysis_id))
    files = [
        {"path": path.relative_to(trace_root).as_posix(), "sha256": file_digest(path), "bytes": path.stat().st_size}
        for path in sorted(copied)
    ]
    bundle_digest = payload_digest(files)
    manifest = {
        "evaluation_mode": evaluation_mode,
        "analysis_id": analysis_id,
        "files": files,
        "bundle_digest": bundle_digest,
        "missing": sorted(set(missing)),
        "complete": not missing,
        "captured_at": utc_now(),
    }
    manifest_path = write_json(trace_root / "manifest.json", manifest)
    for path in [*copied, manifest_path]:
        try:
            path.chmod(0o444)
        except OSError:
            pass
    return manifest


def lock_run(
    *,
    project_root: str | Path,
    runs_root: str | Path,
    run_id: str,
    trial_id: str | None = None,
    analysis_id: str | None = None,
    verify_data_snapshot: bool = True,
    allow_incomplete_trace: bool = False,
) -> dict[str, Any]:
    project_root = Path(project_root).resolve()
    runs_root = (
        Path(runs_root).resolve()
        if Path(runs_root).is_absolute()
        else (project_root / runs_root).resolve()
    )
    run_root = _resolve_run(runs_root, run_id)
    manifest = _read_json(run_root / "manifest.json")
    trial_root = _only_trial(run_root, trial_id)
    trial_path = trial_root / "trial.json"
    trial = _read_json(trial_path)
    if trial.get("status") != "draft":
        raise ValueError(f"trial cannot be locked from status {trial.get('status')}")
    analysis_id = _analysis_id_for_lock(
        project_root=project_root,
        trial_root=trial_root,
        requested_analysis_id=analysis_id or trial.get("analysis_id"),
    )
    draft = trial_root / "draft"
    public_case_root = trial_root / "public-case"
    for entry in manifest.get('public_case_files', []):
        file = public_case_root / entry['path']
        if not file.is_file() or file_digest(file) != entry['sha256'] or file.stat().st_size != entry['bytes']:
            raise ValueError('Public case changed after the run started; do not alter the test to make it pass')
    public_case = _read_yaml(public_case_root / "case.yaml")
    if payload_digest(public_case) != manifest.get('public_task_digest'):
        raise ValueError('Public task changed after the run started')
    result_schema = _read_json(public_case_root / "result.schema.json")
    _validate_result_contract(draft, public_case, result_schema)
    if public_case.get("data_scope", {}).get("platform", "").lower() == "snowflake":
        from helpers.data.sql_policy import inspect_sql, qualify_table
        scope = public_case["data_scope"]
        sources = [qualify_table(table, database=scope["database"], schema=scope["schema"])
                   for table in scope.get("tables", [scope["table"]] if scope.get("table") else [])]
        sql_path = (public_case.get("output_contract", {}).get("sql") or {}).get("path", "calculation.sql")
        safety = inspect_sql((draft / sql_path).read_text(encoding="utf-8"), allowed_sources=sources)
        write_json(trial_root / "prelock-sql-policy.json", safety.as_dict())
        if not safety.passed:
            raise ValueError("final SQL failed pre-lock policy; correct and rerun it before locking: "
                             + "; ".join(safety.violations))
    if verify_data_snapshot:
        data_fingerprint = _verify_snowflake_snapshot(project_root, manifest["data_scope"])
    else:
        data_fingerprint = {
            "status": "skipped",
            "snapshot_id": manifest.get("data_snapshot"),
            "reason": "explicit test-only or recovery bypass",
        }

    trace_manifest = _copy_trace_evidence(
        project_root=project_root,
        trial_root=trial_root,
        analysis_id=analysis_id,
        evaluation_mode=public_case.get("evaluation_mode", "full_analysis"),
    )
    if not trace_manifest["complete"] and not allow_incomplete_trace:
        raise ValueError(
            "trace is incomplete; create the missing evidence before locking: "
            + ", ".join(trace_manifest["missing"])
        )

    submission = trial_root / "submission"
    if submission.exists():
        raise ValueError("submission directory already exists; refusing to overwrite it")
    submission.mkdir()
    required_outputs = tuple(public_case["required_outputs"])
    for name in required_outputs:
        shutil.copy2(draft / name, submission / name)

    files = [
        {"path": name, "sha256": file_digest(submission / name), "bytes": (submission / name).stat().st_size}
        for name in required_outputs
    ]
    bundle_digest = payload_digest(files)
    artifact_manifest = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "trial_id": trial["trial_id"],
        "case_id": trial["case_id"],
        "case_version": trial["case_version"],
        "locked_at": utc_now(),
        "files": files,
        "bundle_digest": bundle_digest,
    }
    artifact_manifest_path = trial_root / "artifact-manifest.json"
    write_json(artifact_manifest_path, artifact_manifest)
    for path in [*(submission / name for name in required_outputs), artifact_manifest_path]:
        try:
            path.chmod(0o444)
        except OSError:
            pass

    trial.update(
        {
            "status": "locked",
            "analysis_id": analysis_id,
            "artifact_bundle_digest": bundle_digest,
            "artifact_manifest": str(artifact_manifest_path),
            "trace_manifest": str(trial_root / "trace" / "manifest.json"),
            "trace_bundle_digest": trace_manifest["bundle_digest"],
            "locked_at": artifact_manifest["locked_at"],
        }
    )
    manifest["status"] = "locked"
    manifest["locked_at"] = artifact_manifest["locked_at"]
    manifest["data_fingerprint"] = data_fingerprint
    write_json(trial_path, trial)
    write_json(run_root / "manifest.json", manifest)
    _append_event(
        run_root,
        "submission_locked",
        trial_id=trial["trial_id"],
        bundle_digest=bundle_digest,
        trace_complete=trace_manifest["complete"],
        data_fingerprint_status=data_fingerprint["status"],
    )
    return {
        "run_id": run_id,
        "trial_id": trial["trial_id"],
        "bundle_digest": bundle_digest,
        "submission_path": str(submission),
        "trace_complete": trace_manifest["complete"],
        "missing_trace_evidence": trace_manifest["missing"],
        "data_fingerprint": data_fingerprint,
    }


def verify_locked_submission(run_root: str | Path, trial_id: str | None = None) -> dict[str, Any]:
    run_root = Path(run_root).resolve()
    trial_root = _only_trial(run_root, trial_id)
    trial = _read_json(trial_root / "trial.json")
    if trial.get("status") not in {"locked", "graded"}:
        raise ValueError(f"trial is not locked: {trial.get('status')}")
    artifact_manifest = _read_json(trial_root / "artifact-manifest.json")
    submission = trial_root / "submission"
    observed_names = sorted(path.name for path in submission.iterdir() if path.is_file())
    expected_names = sorted(record["path"] for record in artifact_manifest["files"])
    if observed_names != expected_names:
        raise ValueError(f"locked submission file set changed: {observed_names}")
    observed = []
    for record in artifact_manifest["files"]:
        path = submission / record["path"]
        if not path.is_file():
            raise ValueError(f"locked artifact is missing: {record['path']}")
        actual = file_digest(path)
        if actual != record["sha256"] or path.stat().st_size != record["bytes"]:
            raise ValueError(f"locked artifact changed: {record['path']}")
        observed.append({"path": record["path"], "sha256": actual, "bytes": path.stat().st_size})
    digest = payload_digest(observed)
    if digest != artifact_manifest["bundle_digest"] or digest != trial["artifact_bundle_digest"]:
        raise ValueError("locked artifact bundle digest does not match the trial record")
    trace_root = trial_root / "trace"
    trace_manifest = _read_json(trace_root / "manifest.json")
    trace_observed = []
    for record in trace_manifest.get("files") or []:
        path = trace_root / record["path"]
        if not path.is_file():
            raise ValueError(f"locked trace artifact is missing: {record['path']}")
        actual = {"path": record["path"], "sha256": file_digest(path), "bytes": path.stat().st_size}
        if actual != record:
            raise ValueError(f"locked trace artifact changed: {record['path']}")
        trace_observed.append(actual)
    trace_digest = payload_digest(trace_observed)
    if trace_digest != trace_manifest.get("bundle_digest") or trace_digest != trial.get("trace_bundle_digest"):
        raise ValueError("locked trace bundle digest does not match the trial record")
    return {
        "run_id": trial["run_id"],
        "trial_id": trial["trial_id"],
        "bundle_digest": digest,
        "trace_bundle_digest": trace_digest,
        "submission_path": str(submission),
        "trial_root": str(trial_root),
    }


def compare_runs(
    *, runs_root: str | Path, before_run_id: str, after_run_id: str
) -> dict[str, Any]:
    runs_root = Path(runs_root).resolve()
    before_root = _resolve_run(runs_root, before_run_id)
    after_root = _resolve_run(runs_root, after_run_id)
    before_manifest = _read_json(before_root / "manifest.json")
    after_manifest = _read_json(after_root / "manifest.json")
    incompatibilities = []
    for field in ("case_id", "case_version", "data_snapshot"):
        if before_manifest.get(field) != after_manifest.get(field):
            incompatibilities.append(
                {"field": field, "before": before_manifest.get(field), "after": after_manifest.get(field)}
            )
    if incompatibilities:
        raise ValueError(f"runs are incompatible: {incompatibilities}")
    before_trial = _only_trial(before_root)
    after_trial = _only_trial(after_root)
    before_grade = _read_json(before_trial / "grades" / "summary.json")
    after_grade = _read_json(after_trial / "grades" / "summary.json")
    gates = {}
    for gate in ("output_contract", "deterministic_accuracy", "final_answer_judge", "case_pass"):
        gates[gate] = {"before": before_grade.get(gate), "after": after_grade.get(gate)}
    comparison = {
        "schema_version": SCHEMA_VERSION,
        "before_run_id": before_run_id,
        "after_run_id": after_run_id,
        "case_id": before_manifest["case_id"],
        "case_version": before_manifest["case_version"],
        "data_snapshot": before_manifest["data_snapshot"],
        "intended_change": after_manifest.get("intended_change"),
        "system_digest_changed": before_manifest["system_fingerprint"]["system_digest"]
        != after_manifest["system_fingerprint"]["system_digest"],
        "gates": gates,
        "created_at": utc_now(),
    }
    comparison_root = after_root / "comparisons"
    write_json(comparison_root / f"from-{before_run_id}.json", comparison)
    lines = [
        f"# Run comparison: {before_run_id} to {after_run_id}",
        "",
        f"**Case:** {comparison['case_id']} v{comparison['case_version']}",
        f"**Data snapshot:** {comparison['data_snapshot']}",
        f"**Intended change:** {comparison.get('intended_change') or 'Not recorded'}",
        f"**System fingerprint changed:** {'Yes' if comparison['system_digest_changed'] else 'No'}",
        "",
        "| Gate | Before | After |",
        "|---|---:|---:|",
    ]
    for gate, values in gates.items():
        lines.append(f"| {gate.replace('_', ' ')} | {values['before']} | {values['after']} |")
    (comparison_root / f"from-{before_run_id}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    _append_event(after_root, "runs_compared", before_run_id=before_run_id)
    return comparison


def _print(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True, default=str))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Full-analysis development evaluation lifecycle")
    sub = parser.add_subparsers(dest="command", required=True)

    start = sub.add_parser("start")
    start.add_argument("--case", required=True)
    start.add_argument("--project-root", default=".")
    start.add_argument("--runs-root", default="working/evals/runs")
    start.add_argument("--baseline-run-id")
    start.add_argument("--intended-change")
    start.add_argument("--model", default="claude-opus-4-6")

    lock = sub.add_parser("lock")
    lock.add_argument("--run-id", required=True)
    lock.add_argument("--trial-id")
    lock.add_argument("--analysis-id")
    lock.add_argument("--project-root", default=".")
    lock.add_argument("--runs-root", default="working/evals/runs")
    lock.add_argument(
        "--skip-data-snapshot-verification",
        action="store_true",
        help="Test and recovery use only. A skipped fingerprint is not eligible for trusted grading.",
    )
    lock.add_argument(
        "--allow-incomplete-trace",
        action="store_true",
        help="Recovery use only. Trusted course runs require a complete trace.",
    )

    verify = sub.add_parser("verify")
    verify.add_argument("--run-id", required=True)
    verify.add_argument("--trial-id")
    verify.add_argument("--project-root", default=".")
    verify.add_argument("--runs-root", default="working/evals/runs")

    compare = sub.add_parser("compare")
    compare.add_argument("--before-run-id", required=True)
    compare.add_argument("--after-run-id", required=True)
    compare.add_argument("--project-root", default=".")
    compare.add_argument("--runs-root", default="working/evals/runs")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    project_root = Path(args.project_root).resolve()
    runs_root = (
        Path(args.runs_root).resolve()
        if Path(args.runs_root).is_absolute()
        else (project_root / args.runs_root).resolve()
    )
    if args.command == "start":
        _print(
            start_run(
                project_root=project_root,
                case_dir=args.case,
                runs_root=runs_root,
                baseline_run_id=args.baseline_run_id,
                intended_change=args.intended_change,
                model=args.model,
            )
        )
    elif args.command == "lock":
        _print(
            lock_run(
                project_root=project_root,
                runs_root=runs_root,
                run_id=args.run_id,
                trial_id=args.trial_id,
                analysis_id=args.analysis_id,
                verify_data_snapshot=not args.skip_data_snapshot_verification,
                allow_incomplete_trace=args.allow_incomplete_trace,
            )
        )
    elif args.command == "verify":
        _print(verify_locked_submission(_resolve_run(runs_root, args.run_id), args.trial_id))
    elif args.command == "compare":
        _print(
            compare_runs(
                runs_root=runs_root,
                before_run_id=args.before_run_id,
                after_run_id=args.after_run_id,
            )
        )


if __name__ == "__main__":
    main()
