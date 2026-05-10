# Skill: SHAP Rep-Facing Explanations

## Purpose

Verify that per-account SHAP attributions produce sales-rep-readable
"why this account" explanations. Operationalizes the gap between a SHAP
matrix (raw signal) and a deployable tooltip (rep-facing narrative).

## When to Use

- Before shipping per-account SHAP tooltips to sales / CSM / ops users
- When stakeholders ask "what does the model think drives this?"
- After `shapley-values/skill.md` (which produces the SHAP matrix) but before UI work
- Pairs with: `shapley-values/skill.md`, `ensemble-calibration/skill.md`

**When NOT to use:**
- Backend-only model (no human-facing explanation needed)
- SHAP library is broken in the env (use `library-compat-smoke-test/skill.md`'s `pred_contribs` fallback first)

## Instructions

### Step 1: Pick 5 Diverse Anchor Accounts

The 5-account stress test is calibrated to surface different failure modes.
Pick one account per profile, all with `target = 1` (known converters):

| # | Profile | Selection criteria |
|---|---------|---------------------|
| 1 | Large account + recent activity | Top quintile of size feature + recent activity feature within 180d |
| 2 | Has open opportunity | Open opp flag = 1 at converting snapshot |
| 3 | Power user signal | Top quintile of usage feature + healthy engagement score |
| 4 | Atypical converter | Bottom quintile of size feature but still converted |
| 5 | Multi-product engagement | Already owns related product / cross-product flag = 1 |

```python
def select_anchors(candidates: pd.DataFrame) -> list[dict]:
    anchors, used = [], set()
    # Profile 1
    pool = candidates[
        (candidates["size_feat"] >= candidates["size_feat"].quantile(0.85))
        & (candidates["recent_activity_days"] <= 180)
    ]
    if len(pool):
        anchors.append({"profile": "Large + recent", "row": pool.iloc[0]})
        used.add(pool.iloc[0]["account_id"])
    # ... profiles 2–5 ...
    return anchors
```

| Rule | Severity |
|------|----------|
| All 5 profiles filled | WARNING if any profile has no candidate (model may not generalize across customer types) |
| Anchors are converted (`target=1`) | BLOCKER if not — explanations on unconverted accounts have no ground truth |
| Account IDs differ across anchors | BLOCKER if reusing |

### Step 2: Score + Extract Top-3 SHAP Per Anchor

For each anchor, score the converting snapshot using the trained ensemble and
pull SHAP top-3 from the seed-averaged matrix:

```python
# Pull the full modeling row
sub = df_full[
    (df_full["snapshot_date"] == anchor["snapshot"])
    & (df_full["account_id"] == anchor["account_id"])
]
X_clean, _, _ = hygiene(sub, product=product)
proba = ensemble_predict(artifacts, X_clean)
shap_res, avg_shap = compute_shap(artifacts, X_clean, product=product)
top_drivers = per_account_top_drivers(avg_shap, shap_res.feature_cols, n_top=3)
```

| Rule | Severity |
|------|----------|
| Use top-3, not top-5 / top-25 | INFO — top-3 is most stable across seeds, matches sales attention span |
| SHAP averaged across all ensemble seeds | BLOCKER if single-seed (rank instability) |
| Per-row, not global | BLOCKER if reporting global importance per account |

### Step 3: Write Natural-Language Interpretation Per Driver

Map `(feature, value, shap_value)` → a sentence a rep would understand. Use a
keyword-matching template, not a free-form LLM (deterministic, auditable):

```python
def interpret_driver(feature: str, value, shap_value: float) -> str:
    direction = "increases" if shap_value > 0 else "decreases"
    f = feature.lower()
    if "days_since_last_event" in f:
        v = float(value) if pd.notna(value) else None
        if v is not None and v <= 180:
            return f"Last event {int(v)} days ago — recent activity {direction} cross-sell likelihood"
        elif v is not None:
            return f"Last event {int(v)} days ago"
        return "No recent activity data"
    if "revenue_pit" in f:
        return f"Revenue = ${float(value):,.0f} (account size signal)" if pd.notna(value) else "Revenue unknown"
    if "has_open_deal" in f and "flg" in f:
        return ("Open deal in pipeline — strong cross-sell readiness signal"
                if value == 1 else "No open deal")
    if "lifetime_deal_count" in f:
        return f"{int(value) if pd.notna(value) else 0} lifetime deals (engagement history)"
    # ... more mappings ...
    return f"{feature} = {value}"
```

| Rule | Severity |
|------|----------|
| Cover top 20 features by global importance | BLOCKER if any anchor's top-3 hits an uncovered feature |
| Include feature value in the sentence (not just feature name) | BLOCKER — reps read values |
| Direction word ("increases"/"decreases") matches SHAP sign | BLOCKER if inverted |
| Sentences ≤ 80 chars (UI-friendly) | WARNING if longer |

### Step 4: Auto-Judge Readability — Rep-Friendly Keyword Match

A simple heuristic: count how many top-3 features match a rep-friendly
keyword list. If ≥ 2 of 3, the explanation is "sensible."

```python
REP_FRIENDLY_KEYWORDS = (
    "event", "revenue", "open_deal", "lifetime_deal_count", "engagement_score",
    "tier", "active_product", "already_owns", "invoice", "documents",
    "engagement", "segment",
)

def is_sensible(top_3_features: list[str]) -> bool:
    joined = " ".join(f.lower() for f in top_3_features)
    return sum(1 for kw in REP_FRIENDLY_KEYWORDS if kw in joined) >= 2
```

Customize the keyword list per domain. Cross-sell uses different keywords
than churn or fraud.

### Step 5: Decision Rule

| Sensible anchors | Verdict | Action |
|------------------|---------|--------|
| 5 / 5 | DEPLOYABLE | Ship the rep-facing tooltip |
| 4 / 5 | DEPLOYABLE WITH CAVEATS | Investigate the 1 weird case; ship if it's an artifact of the small anchor |
| 2–3 / 5 | PARTIAL | Ship probabilities only; flag specific weird cases for feature investigation |
| ≤ 1 / 5 | UNRELIABLE | Do not ship rep-facing tooltips. Use probability + global driver list as alternative |

### Step 6: Produce Markdown Report

Render one section per anchor:

```markdown
### Anchor 1: Large account + recent activity

- Account: `acct_id_xxx`
- Converting snapshot: 2025-09-30
- Predicted score: 0.014
- Actual outcome: SQL'd within 180d (target=1)

Top 3 SHAP drivers:
1. `lifetime_deal_count` = 3 (SHAP +0.84) — 3 lifetime deals (engagement history)
2. `days_since_last_event` = 77 (SHAP +0.36) — Last event 77 days ago (recent activity)
3. `lifetime_deals_product_a` = 1 (SHAP +0.34) — 1 lifetime Product A deal (cross-product)

**Sales-rep readability check: ✓ Sensible**
```

### Step 7: Implementation Pattern for Production UI

Once verdict is DEPLOYABLE, the production UI consumes:

```json
{
  "account_id": "...",
  "score": 0.0146,
  "rank": 1,
  "explanations": [
    {
      "feature": "lifetime_deals_product_b",
      "value": 3,
      "shap": 0.84,
      "narrative": "3 lifetime opportunities (engagement history)"
    },
    ...
  ]
}
```

| Implementation rule | Severity |
|---------------------|----------|
| Show top 3, never more (UI clutter, rank instability beyond top-3) | BLOCKER |
| Include value in the displayed text | BLOCKER |
| Sort by absolute SHAP (signed for direction) | INFO |
| Hide drivers with `abs(shap) < 0.05` (noise floor) | INFO |
| Re-run anchor stress test after every retrain | WARNING if skipped |

## Anti-Patterns

1. **Showing top-25 features.** Reps don't read 25 things; UI clutter; ranks 4+ are seed-noise. Top-3 only.
2. **Free-form LLM-generated explanations.** Non-deterministic, hard to audit, can hallucinate causal claims. Use a keyword-mapping template.
3. **Skipping the anchor stress test.** A "global SHAP looks fine" check doesn't prove per-account explanations are sensible. Stress test 5 diverse profiles.
4. **Skipping the value in the sentence.** "AUM increases prediction" is uninterpretable. "AUM = $5B (large account)" is actionable.
5. **Wrong direction word.** "Open opp DECREASES likelihood" because of sign inversion → reps lose trust permanently.
6. **Anchors all from one profile.** "All 5 anchors are large accounts" doesn't test the model on smaller/atypical converters.
7. **Reporting deployable when 4/5 are sensible without investigating the 5th.** The 5th is the canary — it usually reveals an artifact feature in the top features.
8. **Single-seed SHAP for explanations.** Top-3 is more stable across seeds, but still fluctuates with one seed. Average across the ensemble.

## Connections to Other Skills

- `shapley-values/skill.md` — produces the SHAP matrix this skill verifies
- `library-compat-smoke-test/skill.md` — confirms the SHAP path works before this skill is meaningful
- `ensemble-calibration/skill.md` — averaging across seeds is shared pattern
- `ml-baseline-gate/skill.md` — both are "is this thing actually shippable" gates at different points in the pipeline
