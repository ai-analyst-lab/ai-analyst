# Connected context

Business meaning lives in the configured context store. Calculation code lives in AI Analyst.
This extension connects reviewed guides to query entries and a small executable semantic layer.
It is not a complete replacement for an existing company semantic platform.

## Analysis workflow

1. Resolve `.knowledge/context-source.yaml` and the active dataset.
2. Discover metadata, load applicable guides, and inspect their typed references and implementation links.
3. Choose a supported metric, a reviewed query, or a separately labeled generated analysis.
4. Code validates parameters and safe join paths, then executes through ConnectionManager.
5. The trace distinguishes loaded resources from actual calculation calls and results.

Prefer an approved supported metric for a maintained calculation, called directly with `metric_id`.
A query-library entry points to reviewed SQL, not a saved metric request.
A reviewed SQL entry can answer patterns outside the semantic engine.
Adapting SQL creates a new unreviewed calculation, not automatically another reviewed query.
The retention example can call its metric directly or use a standalone SQL alternative,
`monthly-acquisition-retention`. Its redundant semantic-query wrapper was removed;
the new library entry contains real parameterized SQL. Both implementations remain draft
pending live verification. The resource YAML and cohort operator are custom
AI Analyst formats, not directly compatible with dbt, Hex or Snowflake semantic definitions.

## Commands for Claude

From AI Analyst, using the active Python environment:

```sh
python -m helpers.connected_context --dataset novamart-snowflake catalog
python -m helpers.connected_context --dataset novamart-snowflake validate
python -m helpers.connected_context --dataset novamart-snowflake migration-preview
```

The catalog separates available, excluded and legacy resources. Drafts cannot execute.
Use `load guide ID --hash HASH --analysis-id an_ID --reason 'Why this applies'` to load a version-2
guide, using its catalog hash. Start an analysis with the existing trace workflow first.

Example structured request file:

```yaml
metric_id: growth-acquisition-retention
dimensions: []
parameters:
  cohort_start: '2024-11-01'
  cohort_end: '2024-12-01'
  return_start: '2024-12-01'
  return_end: '2025-01-01'
```

`plan working/request.yaml` validates without querying. `run working/request.yaml --analysis-id an_ID`
executes on the active connection. Use `query_id` instead of `metric_id` to select a library entry.
No command launches a model or automatically approves context.

The retention SQL alternative takes `query_id: monthly-acquisition-retention` and
`parameters: {reporting_month: '2024-12-01'}`. Its SQL derives the acquisition and return calendar
windows. The guide links to both implementations, but loading it does not execute either.
The SQL route does not inherit the semantic engine's grain/null checks. Its scope requires
separate data-quality checks, and both implementations need review after a definition change.

Executions save `working/context-runs/<analysis_id>/<execution_id>/`: `plan.json`, bound-placeholder
`executed.sql`, `parameters.json`, replayable `calculation.sql`, `results.csv` and `execution.json`
(or `failure.json` when execution fails). Events go to `working/connected_context_<analysis_id>.jsonl`, included
by the existing trace renderer. Query logs preserve bound parameters and query IDs. Requests must
never contain credentials. Each worker needs its own connection and analysis ID.

For output-only selection, aliases, rounding or sorting, save a presentation request:

```yaml
columns:
  - {column: depot, name: segment}
  - {column: inspection_rate, name: value, round: 4}
order_by: [segment]
```

Then use `present EXECUTION_DIR PRESENTATION.yaml --analysis-id an_ID` with the parent
directory returned by `run`. It validates the current resource/plan, parent artifacts and
execution receipt, wraps the exact saved calculation SQL, executes through ConnectionManager,
and compares returned rows against the saved parent after the requested presentation changes.
It preserves duplicate rows and nulls, requires the same analysis ID, and records
`presentation_executed` with the original mode, resource/plan hashes, query ID and artifact
hashes. This is a presentation execution, not a new semantic definition or reviewed query.
Copy its actual SQL/CSV to the required output locations; keep the original context-run files.

Only named input columns, unique safe aliases, optional ROUND with 0–12 digits, and ordering
by selected output names are supported. No formulas, filters, grouping, constants or source
changes. The one syntactic exception to byte-preserved inner SQL is removing a terminal
semicolon, recorded in lineage. Older saved executions lacking artifact integrity receipts
must be rerun first. Changed resources, tampered artifacts or changed returned values fail;
the helper never rewrites the source query or patches result values in Python. Hashes are
integrity receipts, not cryptographic signatures proving the identity of an author.

## Supported semantic calculations

- Physical models with unique grain, typed columns, dimensions and measures.
- Explicit one-to-one and many-to-one joins from the measure's grain. Duplicate keys, unsupported
  paths and disallowed unmatched records stop execution.
- Count/sum/min/max, compatible ratios, reviewed scalar expressions, mandatory predicates and
  typed parameters. Arbitrary optional filters are not exposed; declare parameter predicates.
- One first-purchase/return operator: identify the cohort using available qualifying history,
  then count customers returning, not orders. An empty cohort has undefined retention.
- A `related_record_flag` operator: preserve each physical source row and add an integer flag
  for the existence of a qualifying related record. Distinct related keys prevent repeated
  events or tickets from multiplying source rows or monetary measures.
- A `paired_interval_flag` operator: preserve each physical source fact and flag whether its
  timestamp falls inside one validated lifecycle interval paired from two physical record roles.

No arbitrary many-to-many joins, reverse fan-out, cross-fact metrics or unmodeled allocations.
No unsupported cohort grouping. Data-history completeness and business interpretation still need review.

### Related-record existence contract

This derived model declares `operator: related_record_flag`, references both physical input models,
and supplies the following `arguments` (fictional parcel-inspection example):

```yaml
source_model: parcels
related_model: inspections
keys: [[PARCEL_ID, PARCEL_ID]]
flag_column: inspected_flag
related_filter: {column: INSPECTION_RESULT, value: accepted}
required_non_null: [RECEIVED_DATE, DEPOT]
```

The derived `columns` must exactly copy source names and types plus the integer flag; `grain`
must exactly copy the source grain. Key pairs must cover the entire source grain once, with
matching declared types. Composite keys are supported. Both input models must be physical,
with unique, non-null record grains; repeated related *link* keys are allowed. Declare dimensions
and measures against the resulting source columns and flag. Existing metric date predicates,
typed parameters and grouping work normally. A count of `CASE WHEN inspected_flag = 1 THEN
PARCEL_ID END` gives zero on an empty population; dividing by `NULLIF` of the parcel count
gives an undefined rate. An empty grouped request returns no invented dimension rows.

`related_filter` is a single equality comparison with a bound typed literal, or YAML `null`
to include all related records. String, integer, decimal, date, naive timestamp and boolean values are supported;
compound conditions, user-supplied SQL, derived inputs and joins from the
derived model are unsupported. The operator has no event-time filter: metric date predicates
apply to source columns. Business rules needing additional windows require a separate design.

Required source columns reject nulls even if the request does not group by them. These checks
and both grain checks cover the entire physical models, not just the requested date interval.
Null related link keys cannot match; their qualifying count is recorded as an allowed diagnostic.
Orphan related links also cannot contribute source rows. Neither establishes event-ingestion
completeness. Execution evidence contains compiled SQL, bound values, quality checks and results;
loading this model YAML alone does not demonstrate calculation execution.

### Paired lifecycle interval contract

This derived model declares `operator: paired_interval_flag` and explicit `refs` to three
physical models. Two role models can reference the same physical table. The following fictional
machine-permit example illustrates its `arguments`; it is not an approved dataset mapping:

```yaml
source_model: machine_readings
start_model: permit_issuance_records
end_model: permit_terminal_records
keys: [[MACHINE_ID, MACHINE_ID, MACHINE_ID]]
source_time: READING_AT
start_time: EFFECTIVE_AT
end_time: EXPIRES_AT
end_anchor_time: LAST_RENEWED_AT  # optional integrity check, not the interval start
start_filters:
  - {column: RECORD_ROLE, op: '=', value: issued}
end_filters:
  - {column: RECORD_ROLE, op: '=', value: terminal}
  - {column: STATE, op: in, values: [current, closed]}
flag_column: permitted_flag
required_non_null: [SITE]
timestamp_semantics: naive_common_clock
bounds: '[)'
null_end: open
```

Each key triple is `[source_column, start_column, end_column]`, with matching declared types.
Composite entity keys are supported; many source facts can share an entity. Each physical model
must have a unique, non-null record grain. The derived columns must exactly copy the source
columns/types plus one integer flag, and preserve its grain. Role filters are ANDed lists of
typed equality or nonempty `in` comparisons, with bound values; arbitrary SQL is not accepted.
An empty filter list selects every record and remains subject to the same uniqueness checks.

The supported contract is **one qualifying start and one qualifying terminal record per entity**,
not arbitrary overlapping intervals or multiple lifecycle histories. Duplicate qualifying roles
fail rather than using MIN/MAX to invent history. Qualifying starts and ends must pair in both
directions, including entities with no source facts. Source entities with neither role are
legitimately retained with flag zero. Required source columns, entity links and source timestamps
cannot be null. Qualifying role entity links and start timestamps cannot be null; null terminal
ends mean ongoing access. A finite end must be strictly after its start. When declared,
`end_anchor_time` must be non-null, at or after inception and no later than a finite end.
These checks cover full physical inputs/qualifying roles, not only the metric's reporting window.

Facts match at `source_time >= start_time` and `source_time < end_time`, with no upper bound for
an open end. Source rows without a match remain in denominators. The operator never uses a
stored source status flag or terminal renewal timestamp as a substitute for inception.
Metric predicates supply the reporting period and population; dimensions and empty-population
count/ratio behavior are the same as other models. Joins from derived models remain unsupported.

All interval time columns must be declared `timestamp` and share a verified timezone-free clock.
The optional `source_time_policy: date_start_of_day` instead requires a physical `date` source
column and explicitly casts it to midnight in that common clock; start/end bounds remain
timestamps. This is a reviewed reporting policy, never an inferred missing event time.
Omitting this argument retains the original timestamp-only source contract.
Timestamp parameters/role literals accept timezone-free ISO instants with seconds and at most
six fractional digits (or naive Python datetimes); zoned timestamps and extra precision fail.
Date and timestamp `allowed`, `min`, and `max` parameter rules use typed comparisons. Physical
types, timezone conventions, source timestamp precision, lifecycle continuity and source-history
completeness still need independent verification; the compiler does not infer them from YAML.
The calculation trace preserves validation checks, bound parameters, compiled SQL and results.

## Authoring and compatibility

Guide prose owns business meaning, scope, exclusions and limitations, not physical column
mappings or join recipes. A plain-language numerator/denominator belongs in a guide.
Dataset documentation describes physical schema; semantic models and relationships encode
data structure, while metrics and reviewed SQL implement calculations. Optional guide
`implementations` links point to actual metric/query resources. A guide can stand alone with
existing schema documentation; do not require a semantic model solely to fill a link.
This separation is an authoring contract, not something YAML parsing can prove. Check the
content explicitly before recording review. Editing guide prose changes its fingerprint and
invalidates dependent reviews; preserve earlier run snapshots and re-test before claiming
unchanged analytical behavior.

Use `/maintain-context`. It reads templates and scaffolds drafts before review. Canonical paths:

```text
guides/<id>.yaml
datasets/<dataset>/semantic/models/<id>.yaml
datasets/<dataset>/semantic/relationships/<id>.yaml
datasets/<dataset>/semantic/metrics/<id>.yaml
datasets/<dataset>/queries/<id>.yaml
```

Files have schema version 2, kind, ID, dataset, description, owner, status, scope and typed refs.
Semantic templates are under `templates/semantic/{model,metric,relationship}.yaml`. Models contain
dimensions and measures; metrics use those measures; relationships connect models. These are parts
of one semantic layer, stored separately for reuse and review. Guides and reviewed SQL use
`templates/guide.yaml` and `templates/query.yaml`. SQL bodies live under `datasets/<dataset>/queries/sql/`.
Review hashes cover substantive content and dependencies. Formula/source edits invalidate dependent
reviews. Review metadata is an audit record, not a cryptographic signature or access control.

Guide `refs` declare required local dependencies; they can be empty for a self-contained,
owner-reviewed business definition. Retention uses this approach, without a duplicate source file.
Its cohort model and metric reference the guide in their `refs`. Changes to the guide invalidate
dependent calculation reviews, even after the guide itself is reapproved.

Optional guide `source_references` cite existing company documents: each has `title`, HTTP(S) `url`,
`owner`, `reviewed_on` (ISO date), and optional `version`. Metadata travels with guide loads and is
covered by review hashes. This does not fetch, verify access to, or detect changes in remote documents.
Keep reviewed meaning in the guide, cite only real inspected sources, and use an explicit connector or
human review process for freshness. Existing local `{kind: source, path: ...}` refs still hash file bytes.

Optional `implementations` links identify
metric/query implementations without declaring them approved: guide loading returns their current
availability. Approving business meaning is separate from approving a calculation. Implementation
edits do not invalidate a guide's business-source review, but still invalidate the affected executable
dependency chain; plan/run always check it. Changing a guide's links or source invalidates its review.

The retention cohort model declares `window_policy: adjacent_calendar_months`. Dates are parameters,
not fixed November/December values. Code rejects partial months, gaps and multi-month windows. The
original operator's ordered-nonoverlapping behavior remains for existing resources that omit this
policy. Data freshness/history completeness still require separate evidence.

Legacy guides remain readable through the existing loader; legacy metrics retain their API. The new
catalog inventories legacy files but does not silently convert or approve them. Migration preview is
read-only: inspect historical formats/callers before conversion. Avoid two active implementations of
one definition after migration.

Version-2 metrics now belong in `semantic/metrics/`. The loader reports an explicit migration error
for version-2 files at the former `metrics/` path rather than silently ignoring them. Move only those
files; legacy metric formats retain their existing path/API. IDs and definition content need not change.
Saved `semantic_request` query wrappers are no longer supported: replace their call sites with direct
`metric_id` requests before removing them. Do not alter archived run evidence to match new paths.

## Delivery status

The single generalized Growth guide replaces the older fixed-period guide. Its semantic models and
metric remain drafts. Live schema, independent Snowflake results and model-selection checks must pass
before calling the connected calculation student-ready. Offline fixtures do not establish that.
