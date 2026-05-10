# Skill: Rolling Backtest

## Purpose

Evaluate deployment-time quality by scoring every historical observable
snapshot with the trained model and comparing to actual outcomes at
`snapshot + horizon`. Different from CV (training-time quality); this is
"would this model have been useful in production at time T?"

## When to Use

- After model is trained, before stakeholder communication
- Communicating expected production behavior — single OOT point estimate
  doesn't show stability over time
- Detecting concept drift / seasonality that a single CV fold or single
  OOT window would miss
- Pairs with: `hybrid-cv/skill.md`, `oot-window-selection/skill.md`

**When NOT to use:**
- Cross-sectional models (no time dimension) — backtest doesn't apply
- Very small history (< 6 snapshots) — too few points to plot a trend

## Instructions

### Step 1: Pick Observable Snapshots

The eligible backtest range is:

```
backtest_start = max(min(snapshot_date), train_period_start + warm_up_period)
backtest_end   = build_date − horizon (in days)
```

| Rule | Severity |
|------|----------|
| Each backtest snapshot has observable target (`snapshot + H ≤ build_date`) | BLOCKER |
| ≥ 6 backtest snapshots | WARNING if fewer — trend is unclear |
| Backtest covers train AND OOT periods | INFO — train snapshots verify in-sample skill, OOT snapshots verify generalization |

For a 2026-05-06 build with 180d horizon and 28 monthly snapshots:
- backtest_start = 2024-07-31 (covers full year before earliest OOT snapshot)
- backtest_end = 2025-10-31 (last 180d-observable)
- 16 monthly snapshots

### Step 2: Score Each Snapshot

For each snapshot in the backtest range:

1. Filter to eligible accounts at that snapshot
2. Apply the same feature hygiene + imputation as production scoring
3. Predict with the trained ensemble
4. Compare predictions to `target_{H}d` (which is observable)

```python
def rolling_backtest(df, artifacts, product, snapshots, horizon=180):
    elig_col = f"elig_{product}_final_flg"
    target_col = f"target_{product}_sql_{horizon}d"
    rows = []
    for snap_raw in snapshots:
        snap = pd.Timestamp(snap_raw)  # cast np.datetime64 → pd.Timestamp
        sub = df[(df["snapshot_date"] == snap) & (df[elig_col] == 1)].copy()
        sub = sub.dropna(subset=[target_col])
        if len(sub) == 0 or sub[target_col].sum() == 0:
            continue
        X_clean, _, _ = hygiene(sub, product=product)
        proba = ensemble_predict(artifacts, X_clean)
        y = sub[target_col].values.astype(int)
        rows.append({
            "snapshot": snap.strftime("%Y-%m-%d"),
            "n_eligible": len(sub),
            "n_positive": int(y.sum()),
            "positive_rate": float(y.mean()),
            "pr_auc": float(average_precision_score(y, proba)),
            "p_at_25": precision_at_k(y, proba, 25),
            "p_at_50": precision_at_k(y, proba, 50),
            "recall_top_20pct": recall_at_top_pct(y, proba, 0.20),
        })
    return pd.DataFrame(rows)
```

### Step 3: Per-Snapshot Metrics

For each snapshot, compute and emit:

| Metric | Why |
|--------|-----|
| `n_eligible`, `n_positive`, `positive_rate` | Cohort context — small positive counts make metrics noisy |
| `pr_auc` | Primary metric; lift over snapshot's `positive_rate` is the deployment-relevant signal |
| `precision@25`, `precision@50` | Sales rep reality — top N is what gets worked |
| `recall@top-20%` | What fraction of converters does the top-quintile catch |

### Step 4: Render Per-Snapshot Table + Trend Statistics

```markdown
| snapshot | n_elig | n_pos | rate | PR-AUC | lift | P@25 | P@50 | recall_top20 |
|----------|--------|-------|------|--------|------|------|------|--------------|
| 2024-07-31 | 1565 | 11 | 0.0070 | 0.6131 | 87× | 0.28 | 0.18 | 1.00 |
| 2024-08-31 | 1568 | 14 | 0.0089 | 0.5608 | 63× | 0.32 | 0.24 | 1.00 |
| ...
| 2025-10-31 | 1502 | 13 | 0.0087 | 0.1536 | 18× | 0.12 | 0.18 | 0.92 |

Average PR-AUC: 0.44; min: 0.15; max: 0.61
```

Plus summary stats:

```python
summary = {
    "avg_pr_auc": bt["pr_auc"].mean(),
    "min_pr_auc": bt["pr_auc"].min(),
    "max_pr_auc": bt["pr_auc"].max(),
    "trend_slope": np.polyfit(np.arange(len(bt)), bt["pr_auc"].values, 1)[0],
    "n_snapshots_above_1.5x_random": (bt["pr_auc"] > 1.5 * bt["positive_rate"]).sum(),
}
```

| Diagnostic | Severity |
|------------|----------|
| Trend slope < -0.05 PR-AUC per year | WARNING — concept drift; consider retraining cadence |
| Min PR-AUC < random baseline (positive rate) | BLOCKER — model fails entirely in some snapshots |
| Std(PR-AUC) > 0.15 | WARNING — high variability; confidence band wide |
| Most recent 3 snapshots ≥ 1.5× random | INFO — model still useful at deployment time |

### Step 5: Plot the Curve (Optional)

For stakeholder communication, render the per-snapshot PR-AUC over time:

```python
import matplotlib.pyplot as plt
fig, ax = plt.subplots(figsize=(10, 4))
ax.plot(bt["snapshot"], bt["pr_auc"], marker="o", label="Model")
ax.plot(bt["snapshot"], 1.5 * bt["positive_rate"], "--", label="1.5× random gate")
ax.set_ylabel("PR-AUC")
ax.legend()
fig.savefig(out_dir / "backtest_pr_auc_over_time.png", dpi=150, bbox_inches="tight")
```

### Step 6: Document the Verdict

Append to the model's eval report:

```markdown
## Rolling Backtest (snapshot-by-snapshot)

| Metric | Value |
|--------|-------|
| Snapshots evaluated | 16 (2024-07-31 → 2025-10-31) |
| Avg PR-AUC | 0.44 |
| Min PR-AUC | 0.15 (2025-09-30) |
| Max PR-AUC | 0.61 (2024-07-31) |
| Snapshots ≥ 1.5× random | 16 / 16 |
| Trend slope | -0.02 PR-AUC/year (mild degradation) |

**Verdict:** Stable deployment quality with mild seasonal variance. Recommend
quarterly retrain cadence to refresh against the cohort.
```

## Anti-Patterns

1. **Reporting only OOT PR-AUC.** A single window can be lucky or unlucky. Backtest reveals the band.
2. **Backtesting ON the training data without acknowledging it.** In-sample backtest snapshots show the model "remembers" — useful for sanity check, but not deployment quality. Mark them.
3. **Skipping eligibility filter on backtest rows.** Production scoring filters; backtest must too. Otherwise the metric overstates deployment performance on ineligible accounts.
4. **Backtesting on snapshots within H days of build (censored).** Targets are NULL → can't compute PR-AUC. See `oot-window-selection/skill.md`.
5. **Comparing PR-AUC across snapshots without comparing positive rates.** PR-AUC's interpretation depends on the snapshot's positive rate. Always show both.
6. **Smoothing the trend before showing it.** Stakeholders read raw points and outliers; smoothing hides important snapshots.
7. **Running backtest only at deployment time.** Re-run after every retrain; it's the deployment-quality version of CV.

## Connections to Other Skills

- `oot-window-selection/skill.md` — defines `build_date − H` boundary used here
- `hybrid-cv/skill.md` / `forward-chaining-cv/skill.md` — backtest is the deployment counterpart of CV
- `ensemble-calibration/skill.md` — backtest scores with the calibrated ensemble (not single model)
- `feature-hygiene/skill.md` — same hygiene pipeline applied to each backtest snapshot
