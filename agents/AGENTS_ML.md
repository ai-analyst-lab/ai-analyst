# AGENTS_ML.md — Production ML Pipeline Reference

This document is the **production-side spec** that complements the ML build agents (`ml-feature-prep`, `ml-model-train`, `ml-ship-decision`). Those agents produce a trained, validated model. This doc covers what happens next: turning that model into a daily-running production pipeline.

It's **vendor-neutral** — patterns work on any combination of {Snowflake, BigQuery, Postgres} × {Airflow, Dagster, Prefect} × {S3, GCS, Azure Blob} × {Great Expectations, Soda, dbt-test}. Concrete implementation depends on your stack. Where vendor specifics matter, the doc notes adaptation points.

**Scope:** batch-trained tabular supervised ML, daily/weekly/monthly scoring cadence. Not for real-time inference (separate concerns), online learning (different architecture), or streaming.

---

## 1. Repo Architecture

A production ML pipeline has 5 logical layers. Map them to a single repo or split across repos as your team prefers.

```
my_ml_pipeline/
├── pipeline/                      # Main package
│   ├── config.yaml                # Central configuration (model name, table targets, S3 paths, schedule)
│   ├── orchestration.py           # Coordinates pull → process → train|predict → write
│   ├── cli.py                     # argparse wrapper for orchestration
│   ├── generators/
│   │   ├── pull_data.py           # Data extraction (warehouse → DataFrame)
│   │   ├── process_features.py    # Feature engineering, derived columns
│   │   ├── train_model.py         # Model training, S3 upload
│   │   ├── predict.py             # Load model from S3, score, compute SHAP
│   │   ├── write_results.py       # Atomic warehouse writes
│   │   └── utils.py               # Shared helpers (warehouse client wrappers, etc.)
│   ├── sql/feature_queries/       # Modular SQL — one file per feature group
│   │   ├── base_data.sql
│   │   ├── usage_features.sql
│   │   ├── firmographic_features.sql
│   │   └── engagement_features.sql
│   └── data_quality/              # Per-table DQ check definitions
│       └── checks.yml
└── orchestration/                 # Workflow definitions
    ├── train_dag.py               # Manual-trigger DAG
    ├── predict_dag.py             # Scheduled DAG, auto-backfill
    └── images/my_ml_pipeline/     # If using containerized tasks
        ├── Dockerfile
        └── pyproject.toml
```

**Mapping to the build agents:**
- `ml-feature-prep` operates on the output of `pull_data.py` + `process_features.py`
- `ml-model-train` is the training-time logic that lives in `train_model.py`
- `ml-ship-decision` runs once before the first deployment to decide whether the model is ship-worthy
- `predict.py` + `write_results.py` are the production-only runtime layer

---

## 2. Configuration (config.yaml)

Central config keeps everything driven from one file. Every other module reads from here.

```yaml
# Required sections
model:
  name: my_model_v1
  prediction_type: classification        # classification | regression | ranking
  target_variable: target_180d
  algorithm: xgboost                     # xgboost | lightgbm | catboost | random_forest | linear
  prediction_horizon_days: 180
  primary_metric: pr_auc                 # pr_auc | roc_auc | f1 | r2 | rmse | ndcg

database:
  dev:
    name: <dev-warehouse>
    schema: <dev-schema>
  prod:
    name: <prod-warehouse>
    schema: <prod-schema>

tables:
  results: my_model_results              # Wide format (one row per entity per score date)
  results_long: my_model_results_long    # Long format (peer-relative SHAP)
  results_long_raw: my_model_results_long_raw  # Long format (raw signed SHAP)

sql_files:
  base_table: base_data.sql
  feature_queries:
    - usage_features.sql
    - firmographic_features.sql
    - engagement_features.sql

dag:
  schedule: "0 6 * * *"                  # Cron expression for predict DAG
  test_mode: false                       # true → dev tables, false → prod tables
  model_version: "2026-05-09"            # Drives watermark namespace + S3 key
  email_alerts: ["data-team@..."]

s3:
  dev:
    bucket: <dev-model-bucket>
    model_prefix: my_model
  prod:
    bucket: <prod-model-bucket>
    model_prefix: my_model

predict:
  model_location: s3                     # s3 | gcs | local
  model_version: "2026-05-09"            # Pins the prediction-time model
  model_files:
    default: "2026-05-09_model.pkl"

train:
  output_dir: model/models               # Local pre-S3-upload location
```

**Critical conventions:**
- Use `dev`/`prod` env switching at runtime, never hardcode environments
- `model_version` is the single coupling between trained-model artifacts and watermark/scoring runs — bump it to force reprocessing
- `prediction_type` switches algorithm + metric routing throughout the pipeline (see Section 4)

---

## 3. Modular SQL Pattern

**Goal:** one query file per feature group, all on the same grain (`entity_id`, `date`). The orchestrator merges them.

```sql
-- sql/base_data.sql
select
  entity_id,
  date,
  -- core attributes only
  ...
from {schema}.entities
where date between '{start_date}' and '{end_date}';

-- sql/usage_features.sql
select
  entity_id,
  date,
  count(distinct event_id) as usage_events_30d,
  ...
from {schema}.events
where event_date <= date  -- POINT-IN-TIME — never use future data
  and event_date > date - interval '30 days'
group by 1, 2;

-- ... one file per feature group
```

```python
# generators/pull_data.py
def pull_data(config, target_date=None):
    base = execute_sql(config['sql_files']['base_table'], target_date)
    for sql_file in config['sql_files']['feature_queries']:
        feat = execute_sql(sql_file, target_date)
        base = pd.merge(base, feat, on=['entity_id', 'date'], how='left')
    return base
```

**Critical conventions:**
- **Same grain across all files.** If `base_data.sql` is `(entity_id, date)`, every feature query must be `(entity_id, date)` too. Mismatched grain → silent row explosion or NULL-fill on join.
- **Strict point-in-time cutoffs in SQL** (`event_date <= score_date`, not `< score_date + 1 day`). The `oot-window-selection` skill discusses why.
- **One feature group per file.** "All firmographic features" or "all usage features" — not "all 180 columns in one query." Smaller files are auditable; one giant query hides leakage.
- **Parameterize schema, dates, and entity filters** via `{placeholder}` substitution at execute time. Never hardcode `prod.schema.table` literals in the query.

**Adaptation points by warehouse:**
- Snowflake: `CREATE TABLE ... CLONE` for atomic swap, time-travel for backfill
- BigQuery: `CREATE OR REPLACE TABLE ... AS SELECT` for swap; no native time travel for >7 days
- Postgres: `BEGIN; ALTER TABLE x RENAME TO x_old; ALTER TABLE x_new RENAME TO x; COMMIT;` for atomic swap

---

## 4. Train Model (generators/train_model.py)

Reads cleaned data, fits the model, saves locally, uploads to S3. **Algorithm and metric selection routed by `config['model']['prediction_type']`**.

```python
def train_model(df, config, model_name, model_version):
    X, y, features = prepare_features_and_target(df, config)
    prediction_type = config['model']['prediction_type']
    algorithm = config['model']['algorithm']

    # 1. Algorithm selection routed by prediction_type
    if prediction_type == 'classification':
        if algorithm == 'xgboost':
            model = XGBClassifier(**get_hyperparams(config))
        elif algorithm == 'lightgbm':
            model = LGBMClassifier(**get_hyperparams(config))
        # ... etc
        model.fit(X, y)

        # Calibration if binary (see ensemble-calibration skill)
        if config['model'].get('calibrate', True):
            calibrator = CalibratedClassifierCV(model, method='sigmoid', cv='prefit')
            calibrator.fit(X_cal, y_cal)
        else:
            calibrator = None

        # Metrics
        y_pred_proba = model.predict_proba(X)[:, 1]
        metrics = {
            'pr_auc': average_precision_score(y, y_pred_proba),
            'roc_auc': roc_auc_score(y, y_pred_proba),
        }
        model_data = {
            'model': model,
            'calibrator': calibrator,
            'features': features,
            'threshold': config['model'].get('threshold', 0.5),
        }

    elif prediction_type == 'regression':
        if algorithm == 'xgboost':
            model = XGBRegressor(**get_hyperparams(config))
        # ... etc
        model.fit(X, y)
        y_pred = model.predict(X)
        metrics = {
            'rmse': np.sqrt(mean_squared_error(y, y_pred)),
            'mae': mean_absolute_error(y, y_pred),
            'r2': r2_score(y, y_pred),
        }
        model_data = {'model': model, 'features': features}

    elif prediction_type == 'ranking':
        # LightGBM-rank or XGBoost-rank
        model = LGBMRanker(**get_hyperparams(config))
        groups = X.groupby('query_id').size().values
        model.fit(X.drop('query_id', axis=1), y, group=groups)
        # Metrics: NDCG@k, MAP, MRR
        ...

    # 2. Save locally
    local_path = f"{config['train']['output_dir']}/{model_version}_{model_name}.pkl"
    pickle.dump(model_data, open(local_path, 'wb'))

    # 3. Upload to model store
    upload_artifact(local_path, config, model_name, model_version)

    return local_path, metrics
```

**Conventions:**
- ✅ Exclude `target_variable`, entity_id, date, `*_date` columns from features
- ✅ Filter to numeric dtypes (int/float/bool); see `ml-feature-prep` for deeper hygiene
- ✅ Pickle the whole model_data dict (model + calibrator + features + threshold), not just the model
- ✅ Save locally first, then upload — easier to debug
- ✅ Algorithm selection routed by config, not hardcoded — reuse this template for any tabular ML

---

## 5. Predict (generators/predict.py)

Load model from S3, score the latest data, compute SHAP, return wide + long results.

```python
def predict(df, config, score_date):
    # 1. Load model
    model_data = load_artifact(config, 'default')
    prediction_type = config['model']['prediction_type']

    # 2. Filter to score_date
    df = df[df['date'] == pd.to_datetime(score_date)].copy()

    # 3. Score (routed by prediction_type)
    X = df[model_data['features']].fillna(0)

    if prediction_type == 'classification':
        y_pred_proba = model_data['model'].predict_proba(X)[:, 1]
        if model_data.get('calibrator') is not None:
            y_pred_proba = model_data['calibrator'].predict_proba(
                y_pred_proba.reshape(-1, 1)
            )[:, 1]
        y_pred_binary = (y_pred_proba >= model_data.get('threshold', 0.5)).astype(int)
        results_df = pd.DataFrame({
            'entity_id': df['entity_id'],
            'score_date': score_date,
            'prediction_probability': y_pred_proba,
            'prediction_score': y_pred_proba * 100,
            'prediction_binary': y_pred_binary,
            'model_version': config['predict']['model_version'],
        })

    elif prediction_type == 'regression':
        y_pred = model_data['model'].predict(X)
        # Apply constraints if appropriate (e.g., predicted counts must be ≥ 0)
        y_pred = np.maximum(y_pred, 0)  # only if domain demands non-negativity
        results_df = pd.DataFrame({
            'entity_id': df['entity_id'],
            'score_date': score_date,
            'prediction_score': y_pred,
            'model_version': config['predict']['model_version'],
        })

    elif prediction_type == 'ranking':
        scores = model_data['model'].predict(X)
        results_df = pd.DataFrame({
            'entity_id': df['entity_id'],
            'query_id': df['query_id'],
            'score_date': score_date,
            'prediction_score': scores,
            'rank_in_query': df.groupby('query_id')['prediction_score'].rank(ascending=False),
            'model_version': config['predict']['model_version'],
        })

    # 4. Compute SHAP (routed by algorithm)
    shap_long_df = compute_shap_long(model_data, X, df, score_date, config)

    return results_df, shap_long_df


def compute_shap_long(model_data, X, df, score_date, config):
    """Returns long-format SHAP per entity per feature.

    Routed by algorithm:
    - tree-based (xgboost/lightgbm/catboost): native pred_contribs
    - random forest: shap.TreeExplainer
    - linear: coefficient × feature_value (linear approximation)
    """
    algorithm = config['model']['algorithm']
    model = model_data['model']

    if algorithm in ('xgboost', 'lightgbm', 'catboost'):
        # Native pred_contribs path (avoids shap library version issues)
        if algorithm == 'xgboost':
            booster = model.get_booster()
            contribs = booster.predict(xgb.DMatrix(X.values, feature_names=list(X.columns)),
                                        pred_contribs=True)
            shap_values = contribs[:, :-1]  # last column is bias
        # ... lightgbm / catboost variants

    elif algorithm == 'random_forest':
        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(X)
        if isinstance(shap_values, list):
            shap_values = shap_values[1]  # binary classification positive class

    elif algorithm in ('linear', 'logistic'):
        # Linear approximation: coef * feature_value
        coefs = model.coef_[0] if model.coef_.ndim > 1 else model.coef_
        shap_values = X.values * coefs  # broadcast multiply

    # Convert to long format
    return pd.DataFrame([
        {'entity_id': eid, 'score_date': score_date,
         'feature_name': feat, 'shap_value': float(shap_values[i, j])}
        for i, eid in enumerate(df['entity_id'])
        for j, feat in enumerate(model_data['features'])
    ])
```

**Conventions:**
- ✅ Wide results table for scanning (one row per entity per score_date)
- ✅ Long SHAP table for joining (one row per entity per feature per score_date)
- ✅ SHAP method routed by algorithm — see the `shapley-values` and `shap-rep-explanations` skills for the rationale
- ✅ Apply imputation IDENTICALLY to training (same recency-max, score-median, count-zero rules per `smart-imputation` skill). `fillna(0)` is a footgun for recency columns.

---

## 6. Atomic Warehouse Writes (generators/write_results.py)

**Goal:** zero-downtime updates. The production query never reads a partially-written table.

The pattern: CLONE → DELETE old date → INSERT new → SWAP → DROP temp.

```python
def write_results(results_df, shap_long_df, config):
    atomic_write(results_df, config['tables']['results'], config, date_col='score_date')
    atomic_write(shap_long_df, config['tables']['results_long'], config, date_col='score_date')


def atomic_write(df, table_name, config, date_col):
    """
    1. Clone existing table to temp (if exists)
    2. Delete rows for the date range we're about to write
    3. Insert new rows into temp
    4. Swap temp ↔ live
    5. Drop the now-old table
    """
    schema = config['database'][env_from_config(config)]['schema']
    db = config['database'][env_from_config(config)]['name']
    temp_table = f"{table_name}_temp"
    date_value = df[date_col].iloc[0]  # Single date per write

    with warehouse_connection(db, schema) as conn:
        # 1. Check if live table exists
        exists = table_exists(conn, db, schema, table_name)

        if exists:
            # 2. Clone live → temp
            conn.execute(f"CREATE OR REPLACE TABLE {temp_table} CLONE {table_name}")
            # 3. Delete old date in temp
            conn.execute(f"DELETE FROM {temp_table} WHERE {date_col} = '{date_value}'")
            # 4. Insert new rows into temp
            write_dataframe(conn, df, temp_table, schema, db)
            # 5. Atomic swap
            conn.execute(f"ALTER TABLE {table_name} SWAP WITH {temp_table}")
            # 6. Drop the old (post-swap) temp
            conn.execute(f"DROP TABLE {temp_table}")
        else:
            # First-ever write
            write_dataframe(conn, df, table_name, schema, db, create_if_missing=True)
```

**Adaptation points by warehouse:**
- **Snowflake**: native `CREATE OR REPLACE TABLE ... CLONE` (zero-copy, instant). `ALTER TABLE ... SWAP WITH ...` is atomic.
- **BigQuery**: no zero-copy clone; use `CREATE OR REPLACE TABLE temp AS SELECT * FROM live`. Swap via `DROP live; ALTER TABLE temp RENAME TO live;` (small window of unavailability — for stricter atomicity use BQ snapshots).
- **Postgres**: clone via `CREATE TABLE temp (LIKE live INCLUDING ALL); INSERT INTO temp SELECT * FROM live;`. Swap via `BEGIN; ALTER TABLE live RENAME TO live_old; ALTER TABLE temp RENAME TO live; COMMIT; DROP TABLE live_old;` (transactional, atomic).
- **DuckDB / SQLite**: rename-based swap; less production-relevant.

**Conventions:**
- ✅ Always clone+swap, never `INSERT OVERWRITE` directly into the live table
- ✅ Cleanup the temp table on success AND on error (use try/finally or context managers)
- ✅ Use uppercase column names if your warehouse defaults to upper-case (Snowflake) — saves casting headaches downstream

---

## 7. Watermark + Auto-Backfill

**Goal:** the predict DAG runs daily. If yesterday's run failed, today's run picks up both yesterday's and today's score dates without manual intervention.

The pattern: a watermark store (any KV store) tracks "last successfully completed score_date for this model_version." On each run, walk forward from the watermark to today.

```python
def run_predict_with_backfill(config, model_version, backfill_start_date):
    """
    1. Generate all target dates from backfill_start to today
    2. For each, check watermark: completed?
       - If yes, skip
       - If no, process and mark complete
    3. Fail loudly on any single-date failure (DAG re-runs handle it)
    """
    namespace = f"{config['model']['name']}_{model_version}"
    target_dates = generate_dates(backfill_start_date, today(), cadence=config['model'].get('cadence', 'daily'))

    for target_date in target_dates:
        completed = watermark_get(namespace, 'last_processed', target_date)
        if completed is not None:
            log.info(f"Skip {target_date} — already complete")
            continue

        try:
            df = pull_data(config, target_date=target_date)
            df_processed = process_features(df, config, training_mode=False)
            results_df, shap_df = predict(df_processed, config, target_date)
            write_results(results_df, shap_df, config)
            watermark_put(namespace, 'last_processed', target_date, datetime.now())
            log.info(f"✅ Completed {target_date}")
        except Exception as e:
            log.error(f"❌ Failed {target_date}: {e}")
            raise  # Fail the DAG → operator gets alerted, retries
```

**Adaptation points by watermark store:**
- **Postgres / Snowflake table**: `watermarks(namespace, key, value, completed_at)` with a unique index on `(namespace, key)`. Simple, transactional.
- **DynamoDB**: `(partition_key=namespace, sort_key=key, value, completed_at)`. Single GetItem / PutItem.
- **S3 file**: `s3://watermarks/{namespace}/{key}.txt` with completed_at as content. Cheap, eventually-consistent.
- **Redis**: `HSET watermarks:{namespace} {key} {completed_at}`. Fast, non-durable unless persistence is on.

**Conventions:**
- ✅ Include `model_version` in the watermark namespace — bumping versions forces reprocess
- ✅ Store the actual completion timestamp (not just a boolean) — useful for debugging "was this run actually fresh?"
- ✅ Fail the DAG on any single-date error. Don't silently skip — the alert is the feature.

---

## 8. Train DAG vs Predict DAG

Two DAGs, different cadences and triggers.

### Predict DAG — scheduled, auto-backfill

```python
# orchestration/predict_dag.py — Airflow example
from datetime import datetime
from airflow import DAG
from airflow.operators.python import PythonOperator

with DAG(
    'my_model_predict',
    schedule='0 6 * * *',           # Daily at 6am
    start_date=datetime(2026, 5, 1),
    catchup=False,                   # Don't auto-backfill past dates on first run
    default_args={'retries': 2, 'email_on_failure': True},
) as dag:
    predict_task = PythonOperator(
        task_id='predict_with_backfill',
        python_callable=run_predict_with_backfill,
        op_kwargs={
            'config': load_config(),
            'model_version': '{{ params.model_version }}',
            'backfill_start_date': '{{ params.backfill_start_date }}',
        },
    )
    quality_check_task = PythonOperator(
        task_id='dq_checks',
        python_callable=run_dq_checks,
        op_kwargs={'config': load_config()},
    )
    predict_task >> quality_check_task  # DQ runs only if predict succeeded
```

### Train DAG — manual trigger

```python
# orchestration/train_dag.py
with DAG(
    'my_model_train',
    schedule=None,                   # Manual trigger only
    start_date=datetime(2026, 5, 1),
    catchup=False,
) as dag:
    train_task = PythonOperator(
        task_id='train',
        python_callable=run_training,
        op_kwargs={
            'config': load_config(),
            'model_version': '{{ params.model_version }}',
        },
    )
```

**Adaptation points by orchestrator:**
- **Airflow**: as shown. Use `DAG` + `PythonOperator` or containerized tasks via `KubernetesPodOperator`.
- **Dagster**: `@asset` and `@op` decorators. Auto-materialize policies replace cron schedules.
- **Prefect**: `@flow` and `@task` decorators with `IntervalSchedule` or `CronSchedule`.
- **Step Functions**: state machine JSON; predict and train are separate state machines.

**Conventions:**
- ✅ Predict DAG is scheduled; train DAG is manual
- ✅ Predict DAG always does auto-backfill (the loop in Section 7)
- ✅ DQ checks run AFTER predict succeeds, BEFORE downstream consumers can read
- ✅ `model_version` is a DAG parameter, not hardcoded — pass it via runtime config
- ✅ Email/Slack/PagerDuty alerts on failure — watermark + raise pattern surfaces issues

---

## 9. Data Quality Checks

After every successful predict run, validate the output. Catch silent regressions before stakeholders see bad data.

Vendor-neutral schema (translates to Soda, Great Expectations, or dbt-test):

```yaml
# data_quality/checks.yml — abstract, translates to your DQ tool

# Filter: always check the latest score_date only
filter my_model_results [latest]:
  where: score_date = (SELECT MAX(score_date) FROM my_model_results)

checks for my_model_results [latest]:
  # Volume — catches pipeline failures that produce empty / partial outputs
  - name: row_count_above_threshold
    metric: row_count
    operator: ">"
    value: 100
    severity: blocker

  # Completeness — every entity has a non-null score
  - name: no_missing_entity_ids
    metric: missing_count
    column: entity_id
    operator: "="
    value: 0
    severity: blocker

  - name: no_missing_scores
    metric: missing_count
    column: prediction_score
    operator: "="
    value: 0
    severity: blocker

  # Uniqueness — entity should appear exactly once per score_date
  - name: no_duplicate_entities
    metric: duplicate_count
    column: entity_id
    operator: "="
    value: 0
    severity: blocker

  # Distribution — sanity bounds on the score
  - name: score_range_valid
    metric: invalid_count
    column: prediction_probability
    valid_min: 0.0
    valid_max: 1.0
    operator: "="
    value: 0
    severity: blocker

  # Drift — score distribution shouldn't shift dramatically run-over-run
  - name: score_mean_drift
    metric: avg
    column: prediction_score
    compare_to: previous_run
    max_change_pct: 25
    severity: warning
```

**Adaptation points by DQ tool:**
- **Soda**: native YAML format with `filter` and `checks for` blocks
- **Great Expectations**: `ExpectationSuite` JSON with `expect_column_values_to_not_be_null`, `expect_column_values_to_be_between`, etc.
- **dbt-test**: `tests:` block in `schema.yml` with `unique`, `not_null`, `relationships`, plus custom SQL tests
- **Custom SQL**: `select count(*) from my_model_results where prediction_score is null` style asserts in a test runner

**Conventions:**
- ✅ Always filter to `[latest]` — running checks against full history is slow and noisy
- ✅ Severity tiers: BLOCKER (fail the DAG, alert), WARNING (log, don't fail), INFO (record only)
- ✅ Cover four categories: volume, completeness, uniqueness, distribution. Drift checks are the highest-value warning type.
- ✅ Drift thresholds calibrated by historical run-over-run variance, not arbitrary

---

## 10. Three-Output Table Convention

Production ML pipelines should write three tables, not one.

| Table | Format | Purpose | Consumed by |
|---|---|---|---|
| `<model>_results` | Wide (1 row per entity per score_date) | Stakeholder UI / dashboard / CRM field | Sales reps, dashboards, downstream apps |
| `<model>_results_long_raw` | Long (1 row per entity per feature per score_date) | Raw signed SHAP — peer-mean source for backfill consistency | Internal tooling, debugging, build-vs-build comparison |
| `<model>_results_long` | Long, peer-relative | Stakeholder-readable explanation: negative SHAP = worse than peers | Tooltip rendering, "why this account" UI |

**Why three?**
- **Wide** is for scanning ("show me my top 50 accounts").
- **Long raw** is for joining ("for account X on date Y, what was the SHAP for feature Z?").
- **Long peer-relative** is for explanation ("this account scored low because its [feature] is below the cohort average").

The peer-relative transformation requires the raw values cached somewhere — that's the `_long_raw` table. Without it, account-specific backfills can't reproduce peer means consistently.

**Generation pattern (in predict.py):**
```python
def predict(df, config, score_date):
    # ... score and SHAP as Section 5 ...
    results_wide = build_wide(df, predictions, config)
    shap_long_raw = build_shap_long_raw(df, shap_values, config)

    # Compute peer means for THIS score_date's cohort
    peer_means = shap_long_raw.groupby('feature_name')['shap_value'].mean()

    # Peer-relative = signed SHAP minus peer mean, then flipped sign
    # so negative = worse than peers (UI-friendly convention)
    shap_long = shap_long_raw.copy()
    shap_long['shap_value'] = -1 * (shap_long['shap_value'] -
                                      shap_long['feature_name'].map(peer_means))

    return results_wide, shap_long, shap_long_raw
```

See the `shapley-values` skill for the rationale behind the sign-flip + peer-relative convention.

---

## 11. Docker / Python Project Conventions

If using containerized tasks (Kubernetes, ECS):

```toml
# pyproject.toml — Python 3.11+ recommended
[project]
name = "my-ml-pipeline"
version = "0.1.0"
requires-python = ">=3.11,<3.12"
dependencies = [
  "scikit-learn>=1.4",
  "xgboost>=2.0,<3.0",
  "pandas>=2.0,<3.0",
  "numpy>=1.26,<2.0",
  "shap>=0.45,<1.0",
  "boto3>=1.26",
  "pyyaml>=6.0",
  # warehouse client (your choice):
  # "snowflake-connector-python[pandas]>=3.0",
  # "google-cloud-bigquery>=3.0",
  # "psycopg2-binary>=2.9",
]
```

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY pyproject.toml .
RUN pip install --no-cache-dir .

COPY pipeline/ pipeline/
COPY orchestration/ orchestration/

ENTRYPOINT ["python", "-m", "pipeline.cli"]
```

**Conventions:**
- ✅ Pin major versions (`xgboost>=2.0,<3.0`); patch updates are safe
- ✅ Don't pin to exact patches in pyproject.toml; use a lockfile (poetry.lock / requirements.lock) for reproducibility
- ✅ Slim base image, multi-stage build if needed for size
- ✅ ENTRYPOINT to the CLI; the orchestrator passes args (`train --model-version 2026-05-09` or `predict-with-backfill --backfill-start-date 2026-04-01`)

---

## 12. Watermark + Backfill Recipes

Common scenarios and how the pattern handles them:

| Scenario | What happens |
|---|---|
| Daily DAG runs successfully | Watermark advances by 1 day. Next run does 1 day. |
| Daily DAG fails on day N | Watermark NOT advanced. Day N+1 run picks up day N + day N+1. |
| Manual backfill of 30 days | Reset watermark, set `backfill_start_date = today - 30d`, run. Pipeline does all 30 dates sequentially. |
| Bumped `model_version` | New namespace. ALL dates from `backfill_start_date` re-process under new version. Use sparingly — costs scale linearly. |
| Account-specific backfill (e.g., fixing a single entity's score) | Different pattern — load cached peer means from `_long_raw`, score the entity, write directly. See the `shapley-values` skill backfill section. |

---

## 13. Operationalization Checklist

Before shipping a model to production, verify:

- [ ] `ml-ship-decision` returned a SHIP verdict (not MARGINAL_SHIP without explicit override, not DEMOTE_TO_LOGREG)
- [ ] `model_version` is set in config and matches the trained artifact
- [ ] All three output tables (`results`, `results_long_raw`, `results_long`) are defined and the schema matches `predict.py` output
- [ ] DQ checks cover volume, completeness, uniqueness, and distribution at minimum
- [ ] Watermark namespace includes `model_version` (no cross-version reuse)
- [ ] Train DAG can run end-to-end on a recent date (smoke test before scheduling Predict DAG)
- [ ] Predict DAG runs successfully on the latest score_date in dev
- [ ] Alerts (email / Slack / PagerDuty) are wired to DAG failure
- [ ] Stakeholder consumers (BI tool, CRM, internal app) can read from the live results table
- [ ] Rollback plan exists: can revert to the previous `model_version` by config change + Predict DAG re-run

---

## 14. Related Skills and Agents

This document is the production reference. The build-side counterparts:

**Skills (the standards)**
- `feature-hygiene` — drop IDs, dates, leakage, high-NaN, zero-variance
- `smart-imputation` — recency → max, scores → median, counts → 0
- `target-engineering` — forward shift, market adjustment, clipping, class balance
- `oot-window-selection` — pick OOT respecting target censoring
- `hybrid-cv` / `forward-chaining-cv` — temporal cut + GroupKFold patterns
- `bayesian-tuning` — Optuna TPE, search space, scale_pos_weight handling
- `ensemble-calibration` — multi-seed bagging + Platt / isotonic calibration
- `library-compat-smoke-test` — 30-second pre-flight before training
- `ml-baseline-gate` — LogReg-K and heuristic comparison
- `shapley-values` — SHAP computation, three-table output, peer-relative
- `shap-rep-explanations` — anchor stress test, deployable threshold
- `rolling-backtest` — per-snapshot historical scoring vs actuals

**Agents (the orchestrators)**
- `ml-feature-prep` — build-time feature hygiene
- `ml-model-train` — end-to-end training, routes by task / structure / algorithm
- `ml-model-evaluation` — post-train CV evaluation
- `ml-ship-decision` — ship/no-ship verdict with templated BUILD_RESULTS.md
- `ml-productionize` — production-readiness gate; references this doc

---

## 15. Out of Scope

This doc does NOT cover:
- Real-time / online inference (use a model server: TorchServe, BentoML, SageMaker Endpoint)
- Online learning / streaming ML (use River, Vowpal Wabbit, or Spark ML Streaming)
- Model registry / lineage tracking (use MLflow, Weights & Biases, Neptune)
- A/B testing infrastructure (use a feature flag + experimentation system)
- Drift monitoring beyond DQ checks (use Evidently, WhyLabs, Arize, Fiddler)
- Deep learning training loops (use PyTorch Lightning, HuggingFace Trainer)
- LLM fine-tuning or inference (use the `claude-api` skill or the relevant SDK)

These are separate concerns with their own conventions. This doc is the batch-trained tabular ML production reference.
