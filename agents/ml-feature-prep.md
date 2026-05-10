<!-- CONTRACT_START
name: ml-feature-prep
description: Prepare a tabular ML modeling table for training. Applies feature hygiene + smart imputation + leak audit + target profiling. Task-type-aware (classification, regression, ranking). Halts on out-of-scope inputs (DL, LLM, CV, sequence) before doing work.
inputs:
  - name: MODELING_TABLE
    type: file
    source: system
    required: true
  - name: ENTITY_LABEL
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
  - name: LEAK_PATTERNS
    type: str
    source: user
    required: false
  - name: ID_COLS
    type: str
    source: user
    required: false
outputs:
  - path: working/feature_hygiene_audit_{{ENTITY_LABEL}}_{{DATE}}.md
    type: markdown
  - path: working/imputation_summary_{{ENTITY_LABEL}}_{{DATE}}.md
    type: markdown
  - path: working/target_profile_{{ENTITY_LABEL}}_{{DATE}}.md
    type: markdown
  - path: working/{{ENTITY_LABEL}}_clean.parquet
    type: data
depends_on: []
knowledge_context:
  - .knowledge/datasets/{active}/schema.md
  - .knowledge/datasets/{active}/quirks.md
pipeline_step: 4.5
CONTRACT_END -->

# Agent: ML Feature Prep

## Purpose
Take a raw modeling table and produce a clean, model-ready feature matrix plus an audit trail. Applies feature hygiene (drop IDs / dates / leakage / high-NaN / zero-variance / non-numeric), smart imputation (recency → max, scores → median, counts → 0), and a target profile. Task-type-aware: classification gets class-balance diagnostics; regression gets distribution-skew diagnostics; ranking gets per-query-length diagnostics.

This agent is the universal entry point for any tabular ML build. It catches the common failure modes (silent leakage, NaN-with-meaning, identifier survival) before the model ever trains.

## Inputs
- `{{MODELING_TABLE}}`: Path to the raw modeling dataframe (CSV, Parquet, or in-memory). Must include `{{TARGET_COL}}`.
- `{{ENTITY_LABEL}}`: Domain entity name for naming/reports (e.g., `account`, `customer`, `transaction`, `subject`, `claim`). Used in output filenames and report headers, NOT logic.
- `{{TARGET_COL}}`: Target column name.
- `{{TASK_TYPE}}`: One of `binary_classification`, `multiclass_classification`, `regression`, `ranking`. Determines which target-profile diagnostics run and what leak patterns are flagged.
- `{{LEAK_PATTERNS}}` (optional): Comma-separated list of suspected leak feature prefixes (e.g., `opp_state_,target_lag_`). Each prefix is dropped from features AND counted in the audit. Use when prior validation surfaced known leaks.
- `{{ID_COLS}}` (optional): Comma-separated list of identifier columns to force-drop. Defaults to feature-hygiene's auto-detect (regex on `*_id`, `id_*`, `uuid`, plus high-cardinality int/object columns).

## Workflow

### Pre-flight: Out-of-scope detection (HALT before any work)

Each detection rule HALTs the agent with a specific message. This prevents wasted compute and silent garbage output on inputs the framework can't handle.

```python
# 1. Image-shaped data check
df = read_modeling_table(MODELING_TABLE)
n_cols = df.shape[1]
numeric_cols = df.select_dtypes(include=['number']).columns
seq_pattern = re.compile(r'^(pixel_|feat_\d+|dim_\d+|x\d+_y\d+)')
seq_named = sum(1 for c in numeric_cols if seq_pattern.match(c))
if n_cols > 1000 and seq_named / n_cols > 0.5:
    HALT(f"Image-shaped data detected ({n_cols} cols, {seq_named} sequentially named). "
         f"Framework targets tabular supervised ML; for CV use a conv-preprocessing pipeline.")

# 2. Long-text column check
for col in df.select_dtypes(include=['object']).columns:
    median_len = df[col].dropna().astype(str).str.len().median()
    if median_len > 100:
        HALT(f"Long-text column detected (`{col}`, median length {median_len:.0f} chars). "
             f"Framework doesn't handle text-as-features without embedding. "
             f"Either embed upstream or use the claude-api skill for an LLM pipeline.")

# 3. Sequence-shaped panel check (only if a time/entity column is detectable)
# Defer this to ml-model-train when DATA_STRUCTURE is supplied; ml-feature-prep can't fully detect.

# 4. Task type check
SUPPORTED_TASKS = {'binary_classification', 'multiclass_classification', 'regression', 'ranking'}
if TASK_TYPE not in SUPPORTED_TASKS:
    HALT(f"Task type `{TASK_TYPE}` is not supervised tabular ML. "
         f"Supported: {sorted(SUPPORTED_TASKS)}. For clustering, anomaly detection, RL, or generative — "
         f"use a separate agent layer.")
```

If any HALT fires, write the message to `working/scope_check_{{ENTITY_LABEL}}_{{DATE}}.md` and stop. No other outputs.

### Step 1: Profile target

Apply target-engineering skill (`.claude/skills/target-engineering/skill.md`) to characterize the target column. Routing by task type:

**binary_classification:**
- Class balance: `(target == 1).mean()`
- Severity: WARNING if minority < 15%, INFO if 15–35%, INFO if 35–50%
- Per-period balance if a time column is detected

**multiclass_classification:**
- Per-class count and rate
- Severity: WARNING if any class < 5% of total, BLOCKER if any class has < 10 samples

**regression:**
- Skew (`df[target].skew()`)
- Kurtosis (`df[target].kurtosis()`)
- 1st/99th percentile and IQR
- NaN rate, infinite-value count
- Severity: WARNING if abs(skew) > 2, BLOCKER if abs(skew) > 4 or any infinite values

**ranking:**
- Queries per group (count of rows per query_id if column detected)
- Relevance distribution (target value frequency)
- Severity: WARNING if median query length < 5

Write target profile to `working/target_profile_{{ENTITY_LABEL}}_{{DATE}}.md`.

### Step 2: Apply feature hygiene

Apply feature-hygiene skill (`.claude/skills/feature-hygiene/skill.md`) in order:

1. Drop explicit exclusions: `{{TARGET_COL}}`, derived target columns (any column whose name contains `{{TARGET_COL}}` as substring, e.g., `target_lag_1`), `{{ID_COLS}}` if provided.
2. Drop identifier columns (auto-detect via regex `*_id`, `id_*`, `uuid`; plus high-cardinality int/object check `nunique() / len(X) > 0.8`).
3. Drop date/timestamp columns (suffix `_date`, `_datetime`, `_timestamp`; or dtype datetime64/timedelta64).
4. Drop user-supplied `{{LEAK_PATTERNS}}` (each prefix → drop matching columns).
5. Drop non-numeric columns (keep int/float/bool only).
6. Drop high-NaN columns (>90% NaN by default; configurable later).
7. Drop zero-variance columns (`nunique() <= 1`).
8. Clean feature names (regex strip non-word chars, collapse underscores).

Severity gates per skill spec. **HALT on any unresolved BLOCKER** (e.g., identifier column survived explicit drops — likely a leakage vector).

Write audit table to `working/feature_hygiene_audit_{{ENTITY_LABEL}}_{{DATE}}.md`.

### Step 3: Apply smart imputation

Apply smart-imputation skill (`.claude/skills/smart-imputation/skill.md`):

1. Classify columns by name pattern:
   - Recency: `*_months_since_*`, `*_days_since_*`, `*_time_since_*` → fill with **observed max**
   - Scores: `*_score`, `*_probability_*`, `*_rating` → fill with **median**
   - Counts/flags/financials: `count_*`, `*_cnt_*`, `*_flg`, `revenue_*`, `arr_*` → fill with **0**
   - Other: → fill with **0** (safety net)
2. Capture pre-fill NaN locations for optional `_is_nan` indicators (only add if 10–80% missing rate AND class-correlation differential > 5pp).

Note: imputation FIT statistics here are global (full table). When this output is consumed by `ml-model-train`, that agent will refit imputation per-fold on the train slice — that's correct per the feature-hygiene skill anti-pattern. This agent's imputation is a sanity-check + first-pass clean copy.

Write imputation summary to `working/imputation_summary_{{ENTITY_LABEL}}_{{DATE}}.md`.

### Step 4: Write clean parquet

Save the cleaned + imputed dataframe to `working/{{ENTITY_LABEL}}_clean.parquet`. This is the input to `ml-model-train`.

Schema:
- All original ID/time columns retained (so downstream CV split has access)
- Feature columns hygienned + imputed
- Target column unchanged

## Output Format

### `working/feature_hygiene_audit_{{ENTITY_LABEL}}_{{DATE}}.md`

```markdown
# Feature Hygiene Audit — {{ENTITY_LABEL}}
**Date:** {{DATE}}
**Source:** {{MODELING_TABLE}}
**Task type:** {{TASK_TYPE}}

## Summary
- Raw columns: N_RAW
- Final columns: N_FINAL ({{N_RAW - N_FINAL}} dropped, {{(1 - N_FINAL/N_RAW)*100:.1f}}% reduction)
- BLOCKERs: 0 / N
- WARNINGs: N

## Drops by step

| Step | Action | Cols Dropped | Severity |
|------|--------|--------------|----------|
| 1 | Explicit exclusions | N: [first 5, +N more] | INFO |
| 2 | Identifier columns | N: [list] | BLOCKER if N > 0 |
| 3 | Date columns | N: [list] | WARNING if N > 0 |
| 4 | Leakage patterns ({{LEAK_PATTERNS}}) | N: [list] | INFO |
| 5 | Non-numeric | N: [list] | WARNING if N > 5 |
| 6 | High-NaN (>90%) | N: [list with NaN%] | WARNING if N > 10 |
| 7 | Zero variance | N: [list] | INFO |
| 8 | Name cleaning | N renames | INFO |

## BLOCKERs (if any)
[list with explanation per blocker]

## WARNINGs (if any)
[list with explanation]

**Verdict:** PASS / HALT
```

### `working/imputation_summary_{{ENTITY_LABEL}}_{{DATE}}.md`

```markdown
# Imputation Summary — {{ENTITY_LABEL}}

| Category | Pattern | Fill strategy | Cols | Sample fills |
|----------|---------|---------------|------|--------------|
| Recency | months_since_*, days_since_* | observed max | N | col1: 999, col2: 730 |
| Scores | *_score, *_probability_* | median | N | col3: 0.45 |
| Counts/flags | count_*, *_cnt_*, *_flg | 0 | N | — |
| Other | (catch-all) | 0 | N | — |

NaN-indicator candidates (10–80% missing): N cols [list]
```

### `working/target_profile_{{ENTITY_LABEL}}_{{DATE}}.md`

Routed by `{{TASK_TYPE}}` — see Step 1 for content.

### `working/{{ENTITY_LABEL}}_clean.parquet`

Cleaned + imputed dataframe. Consumed by `ml-model-train`.

## Skills Used
- `.claude/skills/feature-hygiene/skill.md` — universal hygiene pipeline
- `.claude/skills/smart-imputation/skill.md` — semantic imputation by column category
- `.claude/skills/target-engineering/skill.md` — Step 3 (raw target profile) and Step 6 (class balance for classification)

## Halt conditions

1. Out-of-scope inputs detected in pre-flight (image data, long text, unsupported task type)
2. Unresolved BLOCKER from feature-hygiene Step 2 (identifier column survived)
3. BLOCKER from target profile (infinite values in regression target, or any class with < 10 samples in multi-class)

## Anti-patterns

1. **Skipping feature hygiene because "the data is clean."** Every dataset has surprises. Always run.
2. **Hardcoding leak patterns.** Use `{{LEAK_PATTERNS}}` input — patterns differ per project.
3. **Treating regression targets like binary.** Use target-engineering Step 3 for regression, not Step 6.
4. **Ignoring the audit BLOCKERs.** Identifier columns surviving = silent memorization in training.

## Connections to other agents
- **Upstream:** Source Tie-Out (verifies data loads correctly before this agent cleans it)
- **Downstream:** `ml-model-train` consumes `{{ENTITY_LABEL}}_clean.parquet`
