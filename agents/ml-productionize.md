<!-- CONTRACT_START
name: ml-productionize
description: Take a SHIP-verdict model and produce a concrete migration plan to a daily-running production pipeline. Verifies prerequisites, generates the file checklist per AGENTS_ML.md, halts on missing readiness items.
inputs:
  - name: TRAINED_MODEL_DIR
    type: file
    source: system
    required: true
  - name: BUILD_RESULTS
    type: file
    source: system
    required: true
  - name: ENTITY_LABEL
    type: str
    source: user
    required: true
  - name: ENTITY_COL
    type: str
    source: user
    required: true
  - name: TARGET_COL
    type: str
    source: user
    required: true
  - name: TASK_TYPE
    type: str
    source: user
    required: true
  - name: ALGORITHM
    type: str
    source: user
    required: false
  - name: WAREHOUSE
    type: str
    source: user
    required: true
  - name: ORCHESTRATOR
    type: str
    source: user
    required: true
  - name: MODEL_STORE
    type: str
    source: user
    required: true
  - name: DQ_TOOL
    type: str
    source: user
    required: false
  - name: WATERMARK_STORE
    type: str
    source: user
    required: true
  - name: TARGET_TABLE_NAME
    type: str
    source: user
    required: true
  - name: SCHEDULE_CRON
    type: str
    source: user
    required: false
  - name: MODEL_VERSION
    type: str
    source: user
    required: true
outputs:
  - path: outputs/{{ENTITY_LABEL}}/PRODUCTIONIZATION_PLAN.md
    type: markdown
  - path: outputs/{{ENTITY_LABEL}}/file_checklist.json
    type: data
  - path: outputs/{{ENTITY_LABEL}}/readiness_report.md
    type: markdown
depends_on:
  - ml-ship-decision
knowledge_context:
  - agents/AGENTS_ML.md
pipeline_step: 8
CONTRACT_END -->

# Agent: ML Productionize

## Purpose
Take a SHIP-verdict model from `ml-ship-decision` and produce a concrete migration plan: which files to create, which warehouse / orchestrator / DQ-tool patterns from `AGENTS_ML.md` apply to this stack, what readiness gaps need to be closed before the first scheduled run. Halts loudly on missing prerequisites.

This agent is the bridge between "the model is shippable" (output of `ml-ship-decision`) and "the model runs in production every day at 6am with proper alerting." It does NOT generate the production code itself — that work happens in your real production repo. It produces the spec, file list, and readiness checklist that guide that work.

## Inputs

### Required
- `{{TRAINED_MODEL_DIR}}`: Output dir from `ml-model-train` (must contain `seed_*.pkl`, `eval_metrics.json`, `best_params.pkl`).
- `{{BUILD_RESULTS}}`: Path to `BUILD_RESULTS.md` from `ml-ship-decision`. Used to verify the SHIP verdict.
- `{{ENTITY_LABEL}}`: Domain entity name (must match prior agents).
- `{{ENTITY_COL}}`: Production-side entity grain column (e.g., `account_id`, `customer_id`). Used for DQ uniqueness checks.
- `{{TARGET_COL}}`: Target column name (used in DQ checks for completeness).
- `{{TASK_TYPE}}`: Carried forward from `ml-model-train`.
- `{{WAREHOUSE}}`: One of `snowflake`, `bigquery`, `postgres`, `redshift`, `databricks`. Determines atomic-write template.
- `{{ORCHESTRATOR}}`: One of `airflow`, `dagster`, `prefect`, `step_functions`. Determines DAG template.
- `{{MODEL_STORE}}`: One of `s3`, `gcs`, `azure_blob`, `local`. Determines artifact upload pattern.
- `{{WATERMARK_STORE}}`: One of `warehouse_table`, `dynamodb`, `s3_file`, `redis`. Determines watermark backend.
- `{{TARGET_TABLE_NAME}}`: Production wide-results table name (e.g., `my_model_results`). Long tables auto-named (`{name}_long`, `{name}_long_raw`).
- `{{MODEL_VERSION}}`: Production model version string (e.g., `2026-05-09_v1`). Drives watermark namespace + S3 key.

### Optional
- `{{ALGORITHM}}`: Carried from `ml-model-train` for SHAP path selection.
- `{{DQ_TOOL}}`: One of `soda`, `great_expectations`, `dbt_test`, `custom_sql` (default: `soda`).
- `{{SCHEDULE_CRON}}`: Cron expression for predict DAG (default `0 6 * * *` — daily at 6am).

## Workflow

### Pre-flight: Out-of-scope detection (HALT before any work)

```python
SUPPORTED_WAREHOUSES = {'snowflake', 'bigquery', 'postgres', 'redshift', 'databricks'}
SUPPORTED_ORCHESTRATORS = {'airflow', 'dagster', 'prefect', 'step_functions'}
SUPPORTED_MODEL_STORES = {'s3', 'gcs', 'azure_blob', 'local'}
SUPPORTED_WATERMARK_STORES = {'warehouse_table', 'dynamodb', 's3_file', 'redis'}
SUPPORTED_DQ_TOOLS = {'soda', 'great_expectations', 'dbt_test', 'custom_sql'}

for var, allowed in [
    ('WAREHOUSE', SUPPORTED_WAREHOUSES),
    ('ORCHESTRATOR', SUPPORTED_ORCHESTRATORS),
    ('MODEL_STORE', SUPPORTED_MODEL_STORES),
    ('WATERMARK_STORE', SUPPORTED_WATERMARK_STORES),
]:
    if locals()[var] not in allowed:
        HALT(f"{var}=`{locals()[var]}` not supported. Allowed: {sorted(allowed)}. "
             f"For unsupported stacks, the agent can't generate vendor-specific templates — "
             f"adapt AGENTS_ML.md patterns manually.")

# Real-time / streaming inference is out of scope
if SCHEDULE_CRON and 'second' in SCHEDULE_CRON.lower():
    HALT("Sub-minute scheduling suggests real-time inference. This framework targets batch ML "
         "(daily/weekly/monthly). For real-time, use a model server (TorchServe, BentoML, SageMaker Endpoint).")
```

### Phase 1: Verify ship-decision verdict

1. Read `{{BUILD_RESULTS}}` (BUILD_RESULTS.md).
2. Parse the ship recommendation. HALT unless verdict is one of:
   - `SHIP`
   - `SHIP (with tooltip)`
   - `SHIP (probabilities only, no tooltip)`
   - `MARGINAL_SHIP — document complexity gap` (allowed but warning)

3. If verdict is `DEMOTE_TO_LOGREG`, `DO_NOT_SHIP`, or `MARGINAL_SHIP` without explicit user override → HALT with message:
   > "Ship verdict is `{verdict}`. Productionization should not proceed until model passes ml-ship-decision. Address gates in BUILD_RESULTS.md, or pass `--override-ship-verdict` if user has accepted the risk."

4. Read `eval_metrics.json` from `{{TRAINED_MODEL_DIR}}`. Extract:
   - Primary metric value
   - Baseline ratio
   - SHAP stability (top-5)
   - n_seeds
   - n_train, n_test

### Phase 2: Production-readiness gate

Six checks, each producing PASS / WARN / BLOCK:

```python
readiness = {}

# Check 1: model artifacts complete
artifacts_present = (
    glob(f'{TRAINED_MODEL_DIR}/seed_*.pkl') and
    Path(f'{TRAINED_MODEL_DIR}/best_params.pkl').exists() and
    Path(f'{TRAINED_MODEL_DIR}/eval_metrics.json').exists()
)
readiness['artifacts'] = 'PASS' if artifacts_present else 'BLOCK'

# Check 2: target table grain consistency
# Verify ENTITY_COL appears in seed model's feature list (SHOULD NOT — would be leakage)
# Verify ENTITY_COL is queryable from the warehouse (manual user verification)
seed_features = pickle.load(open(glob(f'{TRAINED_MODEL_DIR}/seed_*.pkl')[0], 'rb'))['features']
if ENTITY_COL in seed_features:
    readiness['grain_consistency'] = 'BLOCK'  # Entity ID in features = identifier leakage
else:
    readiness['grain_consistency'] = 'PASS'

# Check 3: watermark namespace conflict
namespace = f"{{ENTITY_LABEL}}_{{MODEL_VERSION}}"
# User must verify namespace doesn't conflict with another running model — agent can only flag
readiness['watermark_namespace'] = 'WARN'  # Always warn — manual verification
notes['watermark_namespace'] = f"Verify namespace `{namespace}` is not in use by another model. " \
                                f"Check {WATERMARK_STORE} for existing entries."

# Check 4: target table name collision
# Cannot verify warehouse-side from agent — user verifies
readiness['target_table'] = 'WARN'
notes['target_table'] = f"Verify `{{TARGET_TABLE_NAME}}` does not exist in production schema, " \
                        f"OR if it does, that the schema matches expected output (entity_id, score_date, " \
                        f"prediction_score, prediction_probability, model_version)."

# Check 5: DQ check coverage
# Generate the DQ check spec; user reviews
readiness['dq_coverage'] = 'PASS'  # Generated checks always pass; review is the gate

# Check 6: SHAP tooltip deployability (if claimed in BUILD_RESULTS)
if 'tooltip' in build_results_text.lower() and 'no_tooltip' not in build_results_text.lower():
    shap_top5 = eval_metrics['shap_stability']['top5']
    if shap_top5 < 0.80:
        readiness['shap_tooltip'] = 'WARN'
        notes['shap_tooltip'] = f"BUILD_RESULTS claims tooltip ships, but SHAP top-5 stability " \
                                f"is {shap_top5:.2f} (below 0.80 threshold). Review tooltip claim."
    else:
        readiness['shap_tooltip'] = 'PASS'
else:
    readiness['shap_tooltip'] = 'PASS (no tooltip claimed)'
```

If any BLOCK → HALT and write `readiness_report.md` with the failures. Don't proceed.

### Phase 3: Generate migration file checklist

For the user's stack ({{WAREHOUSE}}, {{ORCHESTRATOR}}, {{MODEL_STORE}}, {{WATERMARK_STORE}}, {{DQ_TOOL}}), generate a concrete file list per the structure in `AGENTS_ML.md` Section 1.

```python
checklist = [
    {
        'path': 'pipeline/config.yaml',
        'purpose': 'Central configuration',
        'template_section': 'AGENTS_ML.md §2',
        'customizations': [
            f"model.name: {ENTITY_LABEL}_{MODEL_VERSION}",
            f"model.prediction_type: {map_task_to_prediction_type(TASK_TYPE)}",
            f"model.target_variable: {TARGET_COL}",
            f"model.algorithm: {ALGORITHM}",
            f"database.{ENV}.name: <{WAREHOUSE} db>",
            f"tables.results: {TARGET_TABLE_NAME}",
            f"tables.results_long: {TARGET_TABLE_NAME}_long",
            f"tables.results_long_raw: {TARGET_TABLE_NAME}_long_raw",
            f"dag.schedule: {SCHEDULE_CRON or '0 6 * * *'}",
            f"dag.model_version: {MODEL_VERSION}",
            f"s3.{ENV}.bucket: <your-{MODEL_STORE}-bucket>",
        ],
    },
    {
        'path': 'pipeline/generators/pull_data.py',
        'purpose': 'Modular SQL execution + merge on entity grain',
        'template_section': 'AGENTS_ML.md §3',
        'customizations': [
            f"warehouse client: {warehouse_client_for(WAREHOUSE)}",
            f"grain: ({ENTITY_COL}, snapshot_date)",
            f"feature SQL files match training-side queries",
        ],
    },
    {
        'path': 'pipeline/generators/process_features.py',
        'purpose': 'Apply same feature hygiene + imputation as training',
        'template_section': 'AGENTS_ML.md §4 (training side)',
        'customizations': [
            f"reuse `ml-feature-prep` skill rules",
            f"imputation must match training: recency→max, scores→median, counts→0",
        ],
    },
    {
        'path': 'pipeline/generators/predict.py',
        'purpose': 'Load model, score, compute SHAP (3 tables: wide, long_raw, long peer-relative)',
        'template_section': 'AGENTS_ML.md §5',
        'customizations': [
            f"prediction_type routing: {map_task_to_prediction_type(TASK_TYPE)}",
            f"SHAP method: {'native pred_contribs' if ALGORITHM in ('xgboost','lightgbm','catboost') else 'TreeExplainer' if ALGORITHM == 'random_forest' else 'coef × value' if ALGORITHM in ('linear','logistic') else '?'}",
            f"calibrator: {'Platt sigmoid' if TASK_TYPE == 'binary_classification' else 'isotonic per class' if TASK_TYPE == 'multiclass_classification' else 'none'}",
        ],
    },
    {
        'path': 'pipeline/generators/write_results.py',
        'purpose': f'Atomic CLONE+SWAP writes for {WAREHOUSE}',
        'template_section': 'AGENTS_ML.md §6',
        'customizations': [
            f"warehouse: {WAREHOUSE} → {atomic_write_pattern(WAREHOUSE)}",
            f"three tables: {TARGET_TABLE_NAME}, {TARGET_TABLE_NAME}_long, {TARGET_TABLE_NAME}_long_raw",
        ],
    },
    {
        'path': 'pipeline/generators/train_model.py',
        'purpose': 'Training-side: fit, save, upload artifact',
        'template_section': 'AGENTS_ML.md §4',
        'customizations': [
            f"reuse best_params.pkl from {TRAINED_MODEL_DIR}",
            f"upload to {MODEL_STORE}: <bucket>/<model_prefix>/{MODEL_VERSION}_default.pkl",
        ],
    },
    {
        'path': 'pipeline/orchestration.py',
        'purpose': 'Coordinate pull → process → predict → write with watermark',
        'template_section': 'AGENTS_ML.md §7',
        'customizations': [
            f"watermark store: {WATERMARK_STORE} → {watermark_pattern(WATERMARK_STORE)}",
            f"namespace: {ENTITY_LABEL}_{MODEL_VERSION}",
            f"cadence: {schedule_to_cadence(SCHEDULE_CRON)}",
        ],
    },
    {
        'path': 'pipeline/cli.py',
        'purpose': 'Argparse wrapper: train | predict-with-backfill',
        'template_section': 'AGENTS_ML.md §1 + §11',
    },
    {
        'path': f'orchestration/predict_dag.py' if ORCHESTRATOR == 'airflow' else f'orchestration/predict_flow.py',
        'purpose': f'{ORCHESTRATOR} predict DAG/flow with auto-backfill',
        'template_section': 'AGENTS_ML.md §8',
        'customizations': [
            f"orchestrator: {ORCHESTRATOR} → {orchestrator_template(ORCHESTRATOR)}",
            f"schedule: {SCHEDULE_CRON or '0 6 * * *'}",
            f"alerts: email_on_failure",
        ],
    },
    {
        'path': f'orchestration/train_dag.py' if ORCHESTRATOR == 'airflow' else f'orchestration/train_flow.py',
        'purpose': 'Manual-trigger training DAG/flow',
        'template_section': 'AGENTS_ML.md §8',
    },
    {
        'path': 'pipeline/data_quality/checks.yml',
        'purpose': f'{DQ_TOOL or "soda"}-format DQ checks',
        'template_section': 'AGENTS_ML.md §9',
        'customizations': [
            f"target tables: {TARGET_TABLE_NAME}, {TARGET_TABLE_NAME}_long",
            f"checks: row_count, missing(entity_id), duplicate(entity_id), prediction range",
            f"drift checks calibrated by historical run-over-run variance (build after first 30 runs)",
        ],
    },
    {
        'path': 'orchestration/images/Dockerfile' if containerized(ORCHESTRATOR) else None,
        'purpose': 'Containerized task image',
        'template_section': 'AGENTS_ML.md §11',
    },
    {
        'path': 'pyproject.toml',
        'purpose': 'Python project + dependencies',
        'template_section': 'AGENTS_ML.md §11',
        'customizations': [
            f"warehouse client for {WAREHOUSE}",
            f"orchestrator client for {ORCHESTRATOR}",
            f"model store client for {MODEL_STORE}",
        ],
    },
]
```

Filter out `None` paths (containers not needed for some orchestrators).

### Phase 4: Compose PRODUCTIONIZATION_PLAN.md

Output structure:

```markdown
# Productionization Plan — {{ENTITY_LABEL}} ({{MODEL_VERSION}})

## Stack
- Warehouse: {{WAREHOUSE}}
- Orchestrator: {{ORCHESTRATOR}}
- Model store: {{MODEL_STORE}}
- Watermark: {{WATERMARK_STORE}}
- DQ tool: {{DQ_TOOL}}

## Ship verdict (from BUILD_RESULTS.md)
{{verdict_summary}}

## Readiness gate

| Check | Status | Notes |
|---|---|---|
| Model artifacts complete | {{readiness.artifacts}} | {{notes}} |
| Target table grain consistency | {{readiness.grain_consistency}} | {{notes}} |
| Watermark namespace conflict | {{readiness.watermark_namespace}} | {{notes}} |
| Target table name collision | {{readiness.target_table}} | {{notes}} |
| DQ check coverage | {{readiness.dq_coverage}} | {{notes}} |
| SHAP tooltip deployability | {{readiness.shap_tooltip}} | {{notes}} |

**Overall:** {{PROCEED | HOLD-FOR-FIXES | DO-NOT-PROCEED}}

## File checklist (in order to create)

[Checklist table from Phase 3, formatted as markdown with paths, purposes, AGENTS_ML.md section references, and per-stack customizations]

## Migration steps

1. Set up project skeleton in your production repo using the file paths above.
2. Copy/adapt patterns from `agents/AGENTS_ML.md` for each file (section references in checklist).
3. For each warehouse-specific operation (atomic writes), use the {{WAREHOUSE}} adaptation.
4. For each orchestrator-specific DAG, use the {{ORCHESTRATOR}} adaptation.
5. Configure secrets (warehouse credentials, model store credentials, alerts) per your secret manager.
6. Smoke-test the train DAG once.
7. Smoke-test the predict DAG on a recent score date.
8. Schedule the predict DAG; monitor first run.
9. Verify DQ checks fire correctly on a deliberately-broken run (e.g., write 0 rows).
10. Hand-off to production team.

## Rollback plan
- Previous model version: [if applicable]
- Rollback procedure: revert config.yaml `model_version` to prior, re-trigger predict DAG
- Watermark cleanup: delete entries for failed-version namespace in {{WATERMARK_STORE}}

## Known limitations / out-of-scope
- This plan does NOT include: drift monitoring beyond DQ, A/B testing infra, model registry/lineage, real-time inference
- For those concerns, see `agents/AGENTS_ML.md` §15
```

Also write `file_checklist.json` (structured form of the checklist) for downstream tooling.

## Halt conditions

1. Pre-flight: unsupported warehouse, orchestrator, model store, or watermark store
2. Phase 1: ship verdict not SHIP-class without explicit override
3. Phase 2 BLOCKERs: missing model artifacts, identifier in feature list (entity ID leakage)
4. Phase 2 WARNs: surface but allow user to override (watermark namespace, table name collision)

## Anti-patterns

1. **Skipping ml-ship-decision and going straight to production.** This agent's first check is the BUILD_RESULTS.md ship verdict. No verdict → no productionization plan.
2. **Generating production code from this agent.** Agent produces a PLAN, not the code. Code lives in your real production repo. The plan tells you what files to create and what patterns to use.
3. **Ignoring the WARN-level readiness checks.** Watermark namespace collisions cause silent overwrite of another model's state. Table name collisions cause schema-mismatch crashes. Always verify manually.
4. **Adapting AGENTS_ML.md patterns from memory instead of reading them.** The doc has specifics per warehouse/orchestrator. Read the relevant section before writing the production code.
5. **First scheduled run on Friday at 5pm.** Schedule the first run during business hours so failures are caught immediately. Move to off-hours after a few successful days.

## Skills used
- (none — this agent is purely orchestration + readiness gate, references AGENTS_ML.md as its primary spec)

## Connections to other agents
- **Upstream:** `ml-ship-decision` produces the SHIP verdict + BUILD_RESULTS.md required here
- **Reference doc:** `agents/AGENTS_ML.md` — the production patterns this agent's plan references
- **No downstream agents** — productionization happens in the real production repo, not in this agent layer
