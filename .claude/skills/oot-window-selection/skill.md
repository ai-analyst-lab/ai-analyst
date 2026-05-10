# Skill: OOT Window Selection

## Purpose

Pick an out-of-time (OOT) test window that respects target censoring under
forward-prediction horizons. The default mistake is picking "the most recent
quarter" as OOT — for any target measured H days forward, the last
H days of snapshots have unobservable (NULL) targets and cannot be evaluated.

## When to Use

- Defining an OOT slice for any model with a forward-shifted target
  (`target_180d`, `target_6m_growth`, `churn_within_90d`, etc.)
- Reviewing an existing model's OOT design when distribution shift seems off
- Pairs with: `forward-chaining-cv/skill.md`, `target-engineering/skill.md`

## Instructions

### Step 1: Identify Horizon and Build Date

```
Build date    = the date the source dataset was constructed (often `current_date` at ETL time)
Horizon H     = the forward-window length in days (e.g., 180 for `target_180d`)
Last snapshot = max(snapshot_date) in the dataset
```

Read these from the dataset manifest, build script, or `current_date` fallback at the time of dataset construction.

### Step 2: Compute the Last-Observable Snapshot

The last snapshot whose target is observable is:

```
last_observable_snapshot = build_date - H  (in days)
```

Any snapshot strictly after this date has `target IS NULL` (the target window extends past the build date and cannot be measured).

| Rule | Threshold | Severity |
|------|-----------|----------|
| All OOT rows have observable targets | OOT_max_snapshot ≤ build_date − H | BLOCKER if violated |
| Censored row count is documented | Count of `target IS NULL` rows in source | INFO |
| Build date is recorded in code, not inferred | Hardcoded constant or read from manifest | WARNING if inferred |

**Verify with SQL/pandas before training:**

```sql
select count(*) as observable_rows
from modeling_table
where snapshot_date <= dateadd('day', -180, '<build_date>')
  and target_180d is not null;

select count(*) as censored_rows
from modeling_table
where snapshot_date > dateadd('day', -180, '<build_date>')
  and target_180d is null;
```

### Step 3: Pick OOT Window Entirely Before the Boundary

**Default rule:** OOT = the last K observable snapshots, where K is chosen to give enough positives.

```
OOT_end   = last_observable_snapshot
OOT_start = OOT_end − (K-1) × snapshot_period
```

Typical K:
- Monthly snapshots, 180d horizon, ~80 unique converters/year → K = 4 (4-month OOT)
- Weekly snapshots, 90d horizon → K = 13 (last quarter)
- Quarterly snapshots, 365d horizon → K = 1 (single quarter; widen if positives < 30)

### Step 4: Verify OOT Positive Count

| Rule | Threshold | Severity |
|------|-----------|----------|
| OOT positive count ≥ 30 | If lower, evaluation metrics are dominated by sample noise | WARNING |
| OOT positive count ≥ 10 | Bare minimum for a useful PR-AUC point estimate | BLOCKER if below |
| OOT positive rate within 50–200% of train rate | Class-balance shift threshold | WARNING if outside |

Compute:

```python
oot_pos = ((df['snapshot_date'] >= OOT_START) & 
           (df['snapshot_date'] <= OOT_END) & 
           (df[target_col] == 1)).sum()
```

If positives are too few, widen OOT (more snapshots) or revisit horizon.

### Step 5: Set Train Window Strictly Before OOT

```
TRAIN_END = OOT_START − (1 × snapshot_period)
```

No overlap. No leakage from OOT into train (e.g., an account scored at an OOT snapshot must not also appear in train at an OOT-overlapping snapshot).

If using `GroupKFold` on entity_id within train, accounts CAN appear in both train and OOT — the temporal cut handles leakage, the group split handles entity memorization within train.

### Step 6: Document and Halt-Check

Fill this summary before running training:

```markdown
## OOT Window Design
| Field | Value |
|-------|-------|
| Build date | YYYY-MM-DD |
| Horizon (days) | |
| Last observable snapshot | YYYY-MM-DD (= build − H) |
| OOT window | [YYYY-MM-DD, YYYY-MM-DD] |
| OOT snapshots (count) | |
| OOT eligible rows | |
| OOT positives | |
| Train window | [YYYY-MM-DD, YYYY-MM-DD] |
| Train positives | |
| Censored rows dropped | |
```

**HALT** if OOT positives < 10, or if OOT_max > last_observable.

## Anti-Patterns

1. **"Just use the last quarter."** Without checking the censoring boundary, the most recent quarter often has zero observable positives. Always compute `build_date − H` first.

2. **Imputing missing OOT targets as 0.** The targets aren't missing-at-random; they're unobservable. Setting them to 0 trains the model to predict negatives in the OOT window — backwards.

3. **Using snapshots after `build_date − H` if "most are populated."** A column being 90% populated means the censoring is partial. Drop censored rows entirely; don't model on the observable subset of a partially-censored period (introduces selection bias).

4. **Different OOT period across products in the same project.** If two models share a build, both OOTs should respect the same boundary. Different OOTs → metrics aren't comparable across products.

5. **Choosing OOT = "the most recent N snapshots" without checking horizon.** The right answer is always: "the last N observable snapshots."

## Connections to Other Skills

- `forward-chaining-cv/skill.md` — CV folds within train use the same observable-snapshot rule
- `hybrid-cv/skill.md` — when positives per fold are too few, hybrid uses a single OOT (this skill) plus group-aware CV
- `target-engineering/skill.md` — Step 2a (forward-shift) creates the censoring this skill works around
