# {{ENTITY_LABEL}} Recommendation Model Build Results

**Date:** {{DATE}}
**Algorithm:** {{ALGORITHM}}
**Decision frame:** recommendation

---

## TL;DR

**Ship recommendation: {{SHIP_RECOMMENDATION}}**

- Primary metric (NDCG@10): **{{NDCG_AT_10}}** (random ordering NDCG = {{RANDOM_NDCG_10}}, lift {{LIFT_RATIO}}×)
- NDCG@1: {{NDCG_AT_1}}
- MAP: {{MAP_SCORE}}
- MRR: {{MRR_SCORE}}
- Catalog coverage at top-10: {{COVERAGE_AT_10}}
- Novelty (mean log-popularity inverse) at top-10: {{NOVELTY_AT_10}}

---

## Ranking quality at multiple k

| k | NDCG@k | Precision@k | Recall@k | Random NDCG@k | Lift |
|---|---|---|---|---|---|
| 1 | {{NDCG_1}} | {{P_1}} | {{R_1}} | {{RAND_NDCG_1}} | {{LIFT_1}} |
| 5 | {{NDCG_5}} | {{P_5}} | {{R_5}} | {{RAND_NDCG_5}} | {{LIFT_5}} |
| 10 | {{NDCG_10}} | {{P_10}} | {{R_10}} | {{RAND_NDCG_10}} | {{LIFT_10}} |
| 25 | {{NDCG_25}} | {{P_25}} | {{R_25}} | {{RAND_NDCG_25}} | {{LIFT_25}} |
| 50 | {{NDCG_50}} | {{P_50}} | {{R_50}} | {{RAND_NDCG_50}} | {{LIFT_50}} |

## Coverage and diversity

| Metric | Value | Interpretation |
|---|---|---|
| Catalog coverage @10 | {{COVERAGE_AT_10}} | {{COVERAGE_INTERP}} (% of catalog ever recommended) |
| Long-tail coverage | {{LONGTAIL_COVERAGE}} | {{LONGTAIL_INTERP}} |
| Recommendation diversity (intra-list) | {{INTRA_LIST_DIVERSITY}} | — |
| Novelty (avg item log-popularity) | {{NOVELTY_SCORE}} | — |

## Ordering stability across seeds

- Top-10 list overlap across {{N_SEEDS}} seeds (mean Jaccard): {{TOP10_JACCARD}}
- Kendall's tau between seed rankings: {{KENDALL_TAU}}
- {{ORDERING_VERDICT}} (gate: Jaccard ≥ 0.70 → stable)

## Cohort

| Field | Value |
|---|---|
| Train queries | {{N_TRAIN_QUERIES}} |
| Train items / catalog size | {{N_TRAIN_ITEMS}} |
| Test queries | {{N_TEST_QUERIES}} |
| Test items | {{N_TEST_ITEMS}} |
| Median query length | {{MEDIAN_QUERY_LEN}} |

## Top features (or item-level signals)

{{TOP_FEATURES_TABLE}}

## Anchor stress test (5 query-item pairs)

5 anchor queries across diverse profiles:
1. High-engagement frequent user
2. New / sparse-history user
3. Niche-interest user
4. Multi-interest broad user
5. Cold-start (no prior interactions)

For each: top-3 recommended items + interpretation.

{{ANCHOR_DETAIL_TABLE}}

{{ANCHOR_VERDICT}} ({{ANCHOR_SENSIBLE}}/{{ANCHOR_TOTAL}} sensible)

## Backtest

{{BACKTEST_PER_SNAPSHOT_TABLE}}

Recommendation models are sensitive to:
- Catalog churn (new items / removed items)
- User behavior drift (seasonality, trends)
- Content freshness decay

Recommended retrain cadence: {{RETRAIN_CADENCE}}.

## Risks and known limitations

{{RISK_LIST}}

Recommendation-specific risks:
1. **Filter bubble / popularity bias:** model may concentrate on popular items, hurting long-tail discovery
2. **Cold-start:** new users / items have no embeddings; need fallback strategy (popularity, content-based, item-cluster)
3. **Implicit feedback noise:** clicks ≠ relevance; long-dwell-time / explicit-rating data is cleaner if available

## Ship recommendation

{{SHIP_RECOMMENDATION_DETAIL}}

Integration:
- Inference latency target: {{LATENCY_TARGET}}
- Catalog refresh cadence: {{CATALOG_REFRESH}}
- A/B test config: {{AB_TEST_CONFIG}}
