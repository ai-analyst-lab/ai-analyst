# Skill: ML Baseline Gate

## Purpose

Justify model complexity by comparing the candidate model to a 5-feature
logistic regression and a single-feature heuristic. Catches the failure mode
where a complex model's apparent lift is actually 5 hand-picked features
doing all the work — the extra 100 features just add noise the boost averages over.

## When to Use

- Before shipping ANY classifier to production — a standing pre-deployment gate
- After Bayesian tuning passes the 1.5× random baseline gate (this is the SECOND gate)
- When stakeholders ask "is this model worth the complexity?"
- Pairs with: `bayesian-tuning/skill.md`

**When NOT to use:**
- Pure research / exploration where deployment isn't planned
- Model is already linear (LogReg / Lasso) — already at the baseline tier

## Instructions

### Step 1: Pick the Hand-Picked Baseline Features

Choose 3–7 features that domain experts would name as "the obvious signals" for the target. Use one of these heuristics:

- The top 3–5 features by SHAP importance from the candidate model
- Features stakeholders mention when asked "what would you check on an account?"
- Cross-product engagement signals known to predict cross-sell

| Rule | Severity |
|------|----------|
| 3–7 features (not too many — defeats the simplicity test) | WARNING if > 10 |
| Mix categorical and numeric | INFO |
| At least one "engagement" signal (open opp, prior touches, recent activity) | INFO |
| At least one "size" signal (AUM, revenue, employee count) | INFO |

### Step 2: Train LogReg-K with Same Train/OOT Split

Use the SAME train period, OOT window, eligibility filter, and imputation as the candidate model — only the feature set differs.

```python
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

# Apply same hygiene-style fillna(0)+imputation as candidate model
X_tr_imp = transform_imputation(df_train[features], stats)
X_oot_imp = transform_imputation(df_oot[features], stats)
scaler = StandardScaler().fit(X_tr_imp)
X_tr_std = scaler.transform(X_tr_imp)
X_oot_std = scaler.transform(X_oot_imp)

clf = LogisticRegression(class_weight="balanced", max_iter=1000, random_state=0)
clf.fit(X_tr_std, y_train.values)
p_oot = clf.predict_proba(X_oot_std)[:, 1]
```

| Rule | Severity |
|------|----------|
| Same train/OOT/eligibility as candidate | BLOCKER if differs |
| Same imputation strategy | BLOCKER if differs |
| Standardize features (LogReg is scale-sensitive) | BLOCKER if not standardized |
| `class_weight='balanced'` for imbalanced targets | WARNING if not |

### Step 3: Compute Single-Feature Heuristic Baseline

Pick the highest-correlation single feature (often a binary "open opp" or "engaged" flag). Predict directly from the feature:

```python
flag = df_oot[heuristic_feature].fillna(0).astype(int).values
heuristic_pr_auc = average_precision_score(y_oot, flag)
heuristic_roc_auc = roc_auc_score(y_oot, flag) if y_oot.sum() > 0 else 0.0
```

This is the "absolute floor" — anything more sophisticated must beat this clearly.

### Step 4: Compare PR-AUC Ratios

Compute three ratios:

```python
xgb_vs_logreg = candidate_pr_auc / max(logreg_pr_auc, 1e-9)
xgb_vs_heuristic = candidate_pr_auc / max(heuristic_pr_auc, 1e-9)
logreg_vs_heuristic = logreg_pr_auc / max(heuristic_pr_auc, 1e-9)
```

### Step 5: Apply the Decision Rule

| Ratio (candidate vs LogReg-K) | Verdict | Recommendation |
|-------------------------------|---------|-----------------|
| ≥ 1.5× | **SHIP candidate** | Complexity is justified; the extra features add real signal |
| 1.2× – 1.5× | **MARGINAL** | Document as risk; consider shipping LogReg-K as fallback or production model |
| 1.0× – 1.2× | **DEMOTE** | Ship LogReg-K instead; candidate's complexity isn't earning its keep |
| < 1.0× | **REJECT candidate** | LogReg-K beats it — investigate features or data quality |

**Auxiliary check — heuristic floor:**

| Ratio (candidate vs heuristic) | Verdict |
|--------------------------------|---------|
| ≥ 3× | Candidate is doing more than the obvious one-line rule |
| < 2× | RED FLAG — model is barely beating "if open_opp_flag then 1 else 0" |

### Step 6: Document Verdict in the Eval Report

Render this section in the eval report:

```markdown
## Complexity Justification (ML Baseline Gate)

| Model | Features | OOT PR-AUC | OOT ROC-AUC | vs candidate |
|-------|----------|------------|-------------|--------------|
| Candidate | N | XX | YY | — |
| LogReg-K | K | xx | yy | candidate is Z.ZZ× |
| Heuristic (single-feature) | 1 | xx | yy | candidate is W.WW× |

**Verdict:** SHIP / MARGINAL / DEMOTE
**Rationale:** [1–2 sentences]
```

Include the LogReg coefficients — they're a rough sanity check on whether the model is using features in the expected direction.

### Step 7: Handle the MARGINAL Verdict

If candidate is between 1.2× and 1.5× LogReg-K:

1. **Compute confidence interval** — bootstrap PR-AUC over OOT or rerun with K different OOT slices. If the interval includes 1.0×, the gap is sample noise.
2. **Check ROC-AUC** — if LogReg-K's ROC-AUC ≥ candidate's, LogReg-K is the better ranker even though candidate has higher PR-AUC. Strong evidence the gap is precision-recall trading, not skill.
3. **Default to shipping the simpler model** unless the use case explicitly values the candidate's PR-AUC characteristics (e.g., precision at top-50).

## Anti-Patterns

1. **Skipping this gate because "the model passed Bayesian tuning."** Tuning's gate is "is there ANY signal" (1.5× random). This skill's gate is "is the EXTRA complexity earning its keep."
2. **Comparing PR-AUC against a wildly different baseline.** Use the same train/OOT/eligibility/imputation — only differ in feature set. Otherwise the comparison is apples-to-oranges.
3. **Picking 30 features for the LogReg baseline.** Defeats the simplicity test. Stick to 3–7 hand-picked.
4. **Ignoring ROC-AUC when PR-AUC says "ship."** If ROC-AUC of the simpler model is HIGHER, the candidate's PR-AUC win is precision/recall trading, not real skill.
5. **No heuristic baseline.** The single-feature floor catches the egregious case where ML is solving a problem a SQL filter would solve.
6. **Conflating this gate with model selection.** This is a SHIP/DEMOTE decision, not "should we tune more." Different question.
7. **Only running this on the headline product.** If shipping multiple models (Product A + Product B), run on each — they may have different verdicts.

## Connections to Other Skills

- `bayesian-tuning/skill.md` — passes the 1.5× random gate; this skill's 1.5× is over LogReg-K (different baseline, second gate)
- `oot-window-selection/skill.md` — defines the OOT both candidate and baselines are evaluated on
- `feature-hygiene/skill.md` — same imputation rules apply to LogReg as candidate
