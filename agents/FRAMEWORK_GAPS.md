# Framework Gaps & Wishlist

**Last updated:** 2026-05-09

This file tracks what the ML framework deliberately does NOT cover, what's queued for future work, and what would need substantial rework to support. It's the consolidated answer to "what halts when I try to use this for X?"

The framework's positive scope: **batch-trained tabular supervised ML** — classification (binary / multi-class), regression, ranking — across panel / cross-sectional / single-entity time-series data, on tree-based and linear algorithms.

Anything outside that scope falls into one of the buckets below.

---

## Tier 1: Hard out-of-scope (HALT and redirect)

These trigger explicit HALT conditions in the agents. The framework refuses to silently degrade — it points the user at a different tool.

### 1. Deep learning training loops
**Where it halts:** `ml-model-train` Phase 0, `ml-feature-prep` pre-flight (image-shaped data check)
**Halt message:** "Algorithm `neural_net` / `transformer` / `cnn` / `rnn` / `lstm` / `bert` / `gpt` / `mlp` not supported."
**Why it's hard:** Different training loop (PyTorch / TF iteration patterns), different feature handling (images, sequences, tokens), different SHAP path (gradient × input or integrated gradients, not TreeSHAP).
**What would close it:** A parallel `ml-train-deep` agent layer with skills for batch construction, learning-rate schedules, mixed-precision training, gradient-based attribution. Probably 6–10 new skills + 3 new agents. Major project.

### 2. LLM fine-tuning / inference
**Where it halts:** `ml-model-train` Phase 0
**Halt message:** "For LLMs, use the `claude-api` skill."
**Why it's hard:** No training set in the same sense (instructions + examples vs (X, y) tabular), different evaluation (no PR-AUC / R² — uses LLM-judge or human-eval), different decision frames.
**What would close it:** The `claude-api` skill already exists for LLM API usage. A separate `ml-llm-finetune` agent layer for LoRA / RLHF / DPO fine-tuning would be a new project.

### 3. Computer vision
**Where it halts:** `ml-feature-prep` pre-flight (image-shaped data: `>1000 columns AND >50% match pixel/feat/dim/x*y* naming patterns`)
**Halt message:** "Image-shaped data detected. CV needs a separate agent layer with conv preprocessing and image augmentation."
**Why it's hard:** Different feature pipeline (image augmentation, conv preprocessing, transfer learning from ImageNet/CLIP), different evaluation (mAP, IoU for detection; pixel accuracy for segmentation).
**What would close it:** Parallel CV agent layer with skills for augmentation, transfer learning, detection / segmentation eval. Heavily overlaps with deep learning gap.

### 4. Sequence / transformer models for tabular sequence data
**Where it halts:** `ml-feature-prep` pre-flight (sequence-shaped panel: `rows-per-entity > 1000`)
**Halt message:** "Sequence-shaped panel detected. For sequence models, use a sequence-modeling agent layer (LSTM/transformer) or aggregate to coarser snapshots first."
**Why it's hard:** Different architecture (attention, recurrence), different CV split (sliding windows on sequences, not panel snapshots), different feature engineering (positional encodings).
**What would close it:** Sequence-modeling agent layer. Partial workaround today: aggregate fine-grained data into coarse snapshots and use `ml-model-train` on that.

### 5. Reinforcement learning
**Where it halts:** `ml-model-train` Phase 0
**Halt message:** "Task type `reinforcement_learning` not supervised tabular ML. Use a domain-specific agent."
**Why it's hard:** No static dataset (online environment + reward signal), different training loop (policy gradient, Q-learning, actor-critic), different eval (cumulative reward, regret).
**What would close it:** A separate RL agent layer. Major project.

### 6. Online / streaming learning
**Where it halts:** `ml-model-train` Phase 0
**Halt message:** "Streaming/online learning not supported. Use a streaming-ML agent layer (River, Vowpal Wabbit) or batch-ify your data."
**Why it's hard:** Continuous model updates vs batch retrains, concept-drift adaptation, different state management.
**What would close it:** Streaming-ML agent layer. Smaller than DL but distinct architecture.

### 7. Generative models
**Where it halts:** `ml-model-train` Phase 0
**Halt message:** "Task type `generative` not supervised tabular ML."
**Why it's hard:** No labeled target (or self-supervised target), different evaluation (FID, perplexity, human judgment), different sampling at inference.
**What would close it:** Domain-specific layer (separate for text, image, structured).

### 8. Unsupervised learning (clustering, dimensionality reduction, anomaly detection)
**Where it halts:** `ml-model-train` Phase 0
**Halt message:** "Use a separate unsupervised-ML agent layer for clustering or anomaly detection."
**Why it's hard:** No target → no PR-AUC / R² / NDCG, different gates (silhouette score, reconstruction error, anomaly recall), different evaluation paradigm.
**What would close it:** Smaller than the DL gap — could probably be done with 3–4 new skills + 1 new agent. Worth doing if/when needed.

### 9. Real-time inference
**Where it halts:** `ml-productionize` pre-flight (sub-minute schedule check)
**Halt message:** "Sub-minute scheduling suggests real-time inference. For real-time, use a model server (TorchServe, BentoML, SageMaker Endpoint)."
**Why it's hard:** Latency requirements (< 100ms typical), feature-store integration (Feast, Tecton), different serving infra (model servers, not batch DAGs).
**What would close it:** Production-ML for real-time is a separate concern. Framework's scope is batch.

---

## Tier 2: Soft gaps (not halts, but recognized weak points)

These work, but with caveats. Worth mentioning to users so they know what they're getting.

### 10. Multi-class with > 10 classes
**Status:** Supported via `multiclass_classification`, but gates may behave oddly with very imbalanced multi-class.
**Caveat:** macro-F1 default may not be the right primary metric for >10 imbalanced classes; consider weighted-F1 or per-class PR-AUC.
**What would help:** A skill specifically for "high-cardinality multi-class" with metric routing.

### 11. Quantile / probabilistic regression
**Status:** Supported as standard regression. Prediction intervals are NOT calibrated.
**Caveat:** `ml-model-train` regression path returns point predictions only. Bands in `forecast` template are based on residual std, not proper quantile regression or conformal prediction.
**What would help:** A `quantile-regression` skill with calibrated interval support (LightGBM quantile, conformal prediction wrapper).

### 12. Survival analysis (time-to-event)
**Status:** Not supported as a first-class task type. Workaround: discretize time into bins, treat as classification.
**Caveat:** Discretization loses censoring information (the key feature of survival data).
**What would help:** A `time_to_event` task type with skills for Cox proportional hazards, accelerated failure time models, integrated Brier score.

### 13. Multi-target / multi-output prediction
**Status:** Not supported directly. Workaround: train one model per target.
**Caveat:** Loses correlation structure between targets. For tightly-correlated targets (e.g., predicting next-month revenue AND next-month transactions), joint models often beat one-per-target.
**What would help:** A `multi_output_regression` task type. Most tree libraries support it natively.

### 14. Feature stores / online feature serving
**Status:** Not addressed. `ml-feature-prep` assumes a static modeling table.
**Caveat:** Production deployments needing real-time features (Feast, Tecton) need separate plumbing.
**What would help:** A `feature_store_integration` skill. Mostly a productionize-side concern.

### 15. Causal inference
**Status:** Not addressed. The framework does prediction, not causation.
**Caveat:** SHAP values explain predictions, not causal effects. Users sometimes confuse the two — leads to bad decisions ("AUM SHAP = +0.5 → therefore raising AUM causes conversion").
**What would help:** A `causal_inference` agent layer (DoWhy, EconML wrappers) for users who actually need causal estimates rather than predictions. Major project.

### 16. Fairness / bias auditing
**Status:** Not addressed. No protected-class checks, no disparate-impact audits.
**Caveat:** Pricing, lending, hiring, credit, insurance models have regulatory fairness requirements not covered here.
**What would help:** A `fairness-audit` skill (Fairlearn, Aequitas wrappers) that runs after `ml-ship-decision`.

### 17. Drift monitoring beyond DQ
**Status:** Partial — `AGENTS_ML.md §9` covers volume / completeness / distribution drift in DQ checks. NOT covered: feature drift detection, prediction drift detection, concept drift detection, automated retraining triggers.
**What would help:** A `drift-monitoring` skill (Evidently / WhyLabs / Arize wrappers) that runs as a separate scheduled DAG.

### 18. Model registry / lineage tracking
**Status:** Not addressed. Models are pickled to S3/GCS; no MLflow / W&B / Neptune integration.
**Caveat:** "Which features did model_version 2026-05-08 use?" requires reading the pickle. No version diff tooling.
**What would help:** An `mlflow-integration` skill or similar.

### 19. A/B testing infrastructure
**Status:** Not addressed.
**Caveat:** "Ship V2b vs hold V1" decisions are manual today. No experiment-tracking, no power calc for ML rollouts.
**What would help:** Reuse `experiment-designer` agent (already exists in main repo) and add a skill for ML-specific rollout patterns (canary % rollout, holdback group, statistical significance on conversion delta).

### 20. Calibration validation beyond Platt / isotonic
**Status:** `ensemble-calibration` skill covers Platt (binary) and isotonic (multi-class). Doesn't cover:
- Quantile calibration for regression
- Conformal prediction
- Temperature scaling for neural-net classifiers (out of scope anyway)
**What would help:** Extend the calibration skill OR add a `conformal-prediction` skill.

### 21. SHAP for non-tree algorithms
**Status:** Linear models use coefficient × value approximation. Random forest uses TreeExplainer. NOT covered: `KernelExplainer` for arbitrary models, `DeepExplainer` for neural nets (out of scope), `GradientExplainer`.
**Caveat:** If a future user wants SVM or Gaussian Process models, SHAP path defaults to permutation importance (slow but works).
**What would help:** Extend the `shapley-values` skill with KernelExplainer fallback path.

---

## Tier 3: Domain extensions (templates, not code)

These are easy to add — drop a new template file in `agents/templates/`. No agent code change.

### 22. Domain-specific BUILD_RESULTS templates
Currently shipped: `cross_sell`, `churn`, `fraud`, `forecast`, `pricing`, `recommendation`, `generic`.

Wishlist:
- `lifetime_value` — LTV models with horizon decomposition
- `attribution` — multi-touch attribution
- `next_best_action` — recommendation × decision-tree hybrid
- `demand_forecast` — multi-product / multi-store forecasting (extension of `forecast`)
- `lead_scoring` — variant of `cross_sell` for inbound funnel
- `promotion_targeting` — variant of `pricing`

Adding any of these is a 70-line template file. Cost: ~30 min each.

---

## Tier 4: Stack extensions (production-side)

`ml-productionize` supports specific stack combinations. Adding new ones requires extending pre-flight allowlists and adding adaptation sections to `AGENTS_ML.md`.

Currently supported:
- Warehouses: snowflake, bigquery, postgres, redshift, databricks
- Orchestrators: airflow, dagster, prefect, step_functions
- Model stores: s3, gcs, azure_blob, local
- Watermark stores: warehouse_table, dynamodb, s3_file, redis
- DQ tools: soda, great_expectations, dbt_test, custom_sql

Wishlist:
- **Warehouses**: trino / starburst, mssql, oracle, clickhouse, duckdb (for local dev)
- **Orchestrators**: kubeflow, argo workflows, github actions (for small jobs)
- **Model stores**: model registries (mlflow, w&b) as model store
- **Watermark stores**: file system, etcd
- **DQ tools**: monte-carlo, anomalo, mainline (newer entries)

Adding a stack option = adding a section to `AGENTS_ML.md` + adding to the allowlist in `ml-productionize` pre-flight. ~1–2 hours each.

---

## Maintenance commitments to honor

Risks that grow over time:

1. **Skill drift.** Skills (e.g., `feature-hygiene`) may evolve. Agents reference skills by path; if a skill's section numbering changes, the agent's "per Step N of skill X" becomes wrong. Maintain by re-reading skills before agent updates.

2. **Algorithm × task × structure matrix bloat.** `ml-model-train` routes 60 combinations (4 task types × 3 data structures × 5 algorithms). Most don't get exercised. If a rarely-used path breaks, it could go undetected.
   **Mitigation:** When tier-1 gaps close (DL, etc.), factor `ml-model-train` into per-task sub-agents (`ml-train-classification`, `ml-train-regression`, `ml-train-ranking`) rather than one agent doing everything.

3. **Vendor lock-in via templates.** If `ml-productionize` accumulates ~20 stack-specific templates, maintaining them gets expensive. Consider per-vendor sub-agents instead.

4. **AGENTS_ML.md going stale.** Production patterns evolve (new warehouse features, new DQ tools). Schedule a yearly review.

---

## How to use this file

- **As a user**: scan Tier 1 to know if your problem fits the framework. Scan Tier 2 to know what to expect. Scan Tier 3/4 if you want to extend.
- **As a maintainer**: when adding new capability, check if it closes a wishlist item — update or remove the entry here.
- **When something halts and the agent points here**: that's the framework working as designed. Either redirect to the recommended tool, or implement the gap closure if the use case is frequent enough.
