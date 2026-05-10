# Agent Index

## System Variables (auto-resolved)
| Variable | Value | Used in |
|----------|-------|---------|
| `{{DATE}}` | Current date, YYYY-MM-DD | All agent output filenames |
| `{{DATASET_NAME}}` | Short name derived from data path or user input | File naming, report headers |
| `{{BUSINESS_CONTEXT_TITLE}}` | Short title derived from `{{BUSINESS_CONTEXT}}` | Question brief header |
| `{{RUN_ID}}` | Unique run identifier (YYYY-MM-DD_question-slug) | Run Pipeline, Resume Pipeline |
| `{{RUN_DIR}}` | Per-run output directory path | All agents during pipeline |
| `{{SQL_PATTERNS}}` | Archaeology-retrieved SQL patterns | Analysis agents |
| `{{CORRECTIONS}}` | Logged corrections for current context | Analysis agents |
| `{{LEARNINGS}}` | Category-specific learnings | Question Framing, Storytelling |
| `{{ENTITY_INDEX}}` | Disambiguation index | Question Router |
| `{{ORG_CONTEXT}}` | Business context (glossary, products, teams) | Question Framing, Storytelling |
| `{{THEME}}` | Active theme name | Chart Maker, Deck Creator |
| `{{CONTEXT}}` | Presentation context (workshop/talk/analysis) | Story Architect, Deck Creator |
| `{{STORYBOARD}}` | Story Architect output | Chart Maker, Storytelling |
| `{{FIX_REPORT}}` | Visual Design Critic feedback | Chart Maker (fix pass) |
| `{{DECK_FILE}}` | Generated deck path | Visual Design Critic |
| `{{CONFIDENCE_GRADE}}` | Validation confidence score (A-F) | Storytelling, Deck Creator |
| `{{ENTITY_LABEL}}` | Domain entity name for naming/reports (account, customer, claim, etc.) | ML agents (feature-prep, model-train, ship-decision) |
| `{{TARGET_COL}}` | Target column name in the modeling table | ML agents |
| `{{ENTITY_COL}}` | Entity grain column for GroupKFold (e.g., account_id) | ML agents (panel + cross-sectional structures) |
| `{{TIME_COL}}` | Snapshot/event-time column | ML agents (panel + time-series structures) |
| `{{HORIZON_DAYS}}` | Forward-window length for censored targets | ML agents (when target is forward-censored) |
| `{{TASK_TYPE}}` | binary_classification / multiclass_classification / regression / ranking | ML agents — selects metrics, calibration, gates |
| `{{DATA_STRUCTURE}}` | entity_time_panel / cross_sectional / time_series_single_entity | ML model-train — selects CV strategy |
| `{{ALGORITHM}}` | xgboost / lightgbm / catboost / random_forest / linear / logistic | ML model-train + ship-decision — routes SHAP method, calibration choice |
| `{{DECISION_FRAME}}` | cross_sell / churn / fraud / forecast / pricing / recommendation / generic | ML ship-decision — selects BUILD_RESULTS.md template |
| `{{MIN_TEST_POSITIVES}}` / `{{WARN_TEST_POSITIVES}}` | Sample-size halt thresholds (auto-computed from train_pos by default) | ML model-train |
| `{{PRIMARY_METRIC}}` | Override default primary metric per task type | ML model-train |
| `{{BASELINE_GATE_RATIO}}` | Minimum lift over random baseline (default 1.5) | ML model-train + ship-decision |
| `{{N_TRIALS}}` | Optuna trial budget (default 50) | ML model-train |
| `{{N_SEEDS}}` | Ensemble seed count (default 10) | ML model-train, ship-decision (carried via TRAINED_MODEL_DIR) |
| `{{ID_COLS}}` | Identifier columns to force-drop (defaults to feature-hygiene auto-detect) | ML feature-prep |
| `{{LEAK_PATTERNS}}` | Comma-separated leak feature prefixes | ML feature-prep |
| `{{MIN_SHAP_STABILITY}}` | SHAP top-5 hard halt threshold (default 0.50) | ML model-train |
| `{{BASELINE_FEATURES}}` | 5–7 hand-picked features for LogReg-5 comparison gate | ML ship-decision |
| `{{HEURISTIC_BASELINE}}` | Single-feature rule baseline (auto-detect if not supplied) | ML ship-decision |
| `{{BACKTEST_SNAPSHOTS}}` | Comma-separated dates for rolling backtest (auto-detect default) | ML ship-decision |
| `{{REPORT_TEMPLATE}}` | Path to custom BUILD_RESULTS template (overrides DECISION_FRAME default) | ML ship-decision |
| `{{TRAINED_MODEL_DIR}}` | Output dir from ml-model-train (consumed by ship-decision) | ML ship-decision |
| `{{MODELING_TABLE}}` | Path to modeling dataframe (clean from feature-prep, or raw) | All 3 ML agents |
| `{{WARM_START_PARAMS}}` | Path to prior product's best_params.pkl (warm-starts Optuna) | ML model-train |
| `{{WAREHOUSE}}` | snowflake / bigquery / postgres / redshift / databricks | ML productionize — selects atomic-write template |
| `{{ORCHESTRATOR}}` | airflow / dagster / prefect / step_functions | ML productionize — selects DAG template |
| `{{MODEL_STORE}}` | s3 / gcs / azure_blob / local | ML productionize — selects artifact upload pattern |
| `{{WATERMARK_STORE}}` | warehouse_table / dynamodb / s3_file / redis | ML productionize — selects watermark backend |
| `{{DQ_TOOL}}` | soda / great_expectations / dbt_test / custom_sql | ML productionize — selects DQ check format |
| `{{TARGET_TABLE_NAME}}` | Production wide-results table name | ML productionize |
| `{{SCHEDULE_CRON}}` | Cron expression for predict DAG (default `0 6 * * *`) | ML productionize |
| `{{MODEL_VERSION}}` | Production model version (drives watermark + S3 key) | ML productionize |
| `{{BUILD_RESULTS}}` | Path to BUILD_RESULTS.md from ml-ship-decision | ML productionize |

**Note on template-only placeholders:** The ML ship-decision agent fills additional `{{PLACEHOLDER}}` strings inside `agents/templates/build_results_*.md` at render time (e.g., `{{PRIMARY_METRIC_VALUE}}`, `{{ANCHOR_VERDICT}}`, `{{BACKTEST_AVG}}`). These are NOT system variables — they're computed-at-render values local to the template substitution step. Don't declare them here.

## Agents
| Agent | Path | Invoke When |
|-------|------|-------------|
| Question Framing | `agents/question-framing.md` | User provides a business problem to analyze |
| Hypothesis | `agents/hypothesis.md` | Questions are framed, need testable hypotheses |
| Data Explorer | `agents/data-explorer.md` | Need to understand what data exists in a source |
| Descriptive Analytics | `agents/descriptive-analytics.md` | Need to analyze a dataset (segmentation, funnels, drivers) |
| Overtime / Trend | `agents/overtime-trend.md` | Need time-series analysis or trend identification |
| Cohort Analysis | `agents/cohort-analysis.md` | Need cohort retention curves, LTV analysis, or vintage comparison |
| Root Cause Investigator | `agents/root-cause-investigator.md` | Initial analysis found an anomaly — need to drill down iteratively to find the specific root cause |
| Opportunity Sizer | `agents/opportunity-sizer.md` | Root cause identified or opportunity found — quantify the business impact with sensitivity analysis |
| Experiment Designer | `agents/experiment-designer.md` | Need to test a causal hypothesis — designs A/B tests or quasi-experimental analyses with power estimation and decision rules |
| Story Architect | `agents/story-architect.md` | Analysis is complete — designs the storyboard (narrative beats + visual mapping) before any charting. Pass `{{CONTEXT}}` for workshop/talk closing sequences. |
| Chart Maker | `agents/chart-maker.md` | Need to generate a specific chart. |
| Visual Design Critic | `agents/visual-design-critic.md` | After Chart Maker generates charts — reviews against SWD checklist. After Deck Creator — reviews slide-level design with `{{DECK_FILE}}` and `{{THEME}}`. |
| Narrative Coherence Reviewer | `agents/narrative-coherence-reviewer.md` | After Story Architect produces the storyboard, before charting — reviews story flow, beat structure, and Closing beats if present |
| Storytelling | `agents/storytelling.md` | Analysis and charts are complete, need a narrative |
| Source Tie-Out | `agents/source-tieout.md` | After Data Explorer, before analysis — verify data loading integrity by comparing pandas direct-read vs DuckDB SQL on foundational metrics. HALT on mismatch. |
| Validation | `agents/validation.md` | Need to verify findings before presenting |
| Deck Creator | `agents/deck-creator.md` | Need to create a presentation from analysis. Supports `{{THEME}}` (analytics-dark) and `{{CONTEXT}}` (workshop/talk closing sequence). |
| Comms Drafter | `agents/comms-drafter.md` | Need stakeholder communications (Slack summary, email brief, exec summary). Non-critical — pipeline continues if this fails. |
| ML Model Evaluation | `agents/ml-model-evaluation.md` | Need to evaluate an ML model on panel data — runs forward-chaining CV with entity-aware splits, produces aggregated metrics, distribution shift diagnostics, and pass/fail verdict against success criteria. |
| ML Feature Prep | `agents/ml-feature-prep.md` | Starting any tabular ML build — applies feature hygiene + smart imputation + leak audit + target profiling. Task-type-aware. Halts on out-of-scope inputs (DL, LLM, CV, sequence). |
| ML Model Train | `agents/ml-model-train.md` | Training a tabular supervised ML model end-to-end. Routes CV / tuning / calibration / SHAP by `TASK_TYPE` × `DATA_STRUCTURE` × `ALGORITHM`. Sample-size-adaptive halt rules. Produces calibrated ensemble + SQLite Optuna study + task-aware eval report. |
| ML Ship Decision | `agents/ml-ship-decision.md` | After ML model is trained — runs ml-baseline-gate + shap-rep-explanations + rolling-backtest. Produces BUILD_RESULTS.md (templated by `DECISION_FRAME`) and structured build_metrics.json. |
| ML Productionize | `agents/ml-productionize.md` | After ml-ship-decision returns SHIP — verifies production readiness and generates a concrete migration plan (file checklist, per-stack customizations) per AGENTS_ML.md. Halts on unsupported stacks, ship-verdict failure, or missing artifacts. |

## Reference Docs

| Doc | Path | Purpose |
|---|---|---|
| AGENTS_ML.md | `agents/AGENTS_ML.md` | Vendor-neutral production-ML pipeline reference. Covers repo architecture, modular SQL, atomic warehouse writes, watermark + auto-backfill, train/predict DAGs, three-output table convention, DQ checks, and stack-adaptation points. Referenced by `ml-productionize`. |
| FRAMEWORK_GAPS.md | `agents/FRAMEWORK_GAPS.md` | Consolidated wishlist + scope statement. Tier 1 (hard out-of-scope, with halt redirects), Tier 2 (soft gaps), Tier 3 (template extensions), Tier 4 (stack extensions). Read first if your use case might not fit. |
