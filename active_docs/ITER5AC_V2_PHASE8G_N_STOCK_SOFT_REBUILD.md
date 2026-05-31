# Iteration 5AC - V2 Phase 8G-N Stock-Soft Rebuild

Generated: 2026-05-27 19:30
Route version: `v2_routes_2026_05_26_stock_position`

## Decision

Decision: `KEEP_CURRENT_CHAMPION`.

No stock-soft or stock-ablation candidate cleared the gates. Keep the current champion and stop treating stock as sellability, but do not promote a new stock-soft policy yet.

| Metric | Current champion | Best stock-soft/ablation candidate |
| --- | --- | --- |
| Model | 8gf_regular_plus_post_bf_safe | 8gn_stock_soft_full_features |
| Hit +/-20 | 25.3% | 25.7% |
| Hit delta | - | +0.4pp |
| Hit +/-30 | 36.5% | 36.9% |
| WMAPE | 51.0% | 50.9% |
| WMAPE delta | - | -0.2pp |
| Bias | -21.3% | -19.8% |
| Phantom | 41.0% | 41.2% |
| Phantom delta | - | +0.3pp |

## Promotion Gates

| Gate | Required | Observed | Status |
| --- | --- | --- | --- |
| Hit +/-20 vs champion | >= +0.5pp | +0.4pp | FAIL |
| WMAPE vs champion | <= 0.0pp | -0.2pp | PASS |
| Phantom vs champion | <= +0.5pp | +0.3pp | PASS |
| Largest window WMAPE regression (2024-12-30) | <= +2.0pp | +0.4pp | PASS |

## Aggregate Model Results

| Model | Rows | Qty scored | Hit +/-20 | Delta vs champion | Hit +/-30 | WMAPE | WMAPE delta | Bias | Phantom | Phantom delta |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| median_naive | 5,346 | 2,967 | 21.4% | -3.9pp | 32.2% | 57.3% | +6.3pp | -18.9% | 69.3% | +28.3pp |
| post_bf_safe_naive | 5,346 | 2,967 | 22.2% | -3.1pp | 32.9% | 52.9% | +1.9pp | -24.8% | 65.9% | +24.9pp |
| sk_extra_trees | 5,346 | 2,967 | 25.3% | -0.0pp | 36.0% | 57.0% | +6.0pp | -10.4% | 45.7% | +4.7pp |
| sk_blend_post_bf_safe | 5,346 | 2,967 | 23.4% | -2.0pp | 34.8% | 55.7% | +4.7pp | -17.0% | 43.5% | +2.5pp |
| 8gf_regular_plus_post_bf_safe | 5,346 | 2,967 | 25.3% | +0.0pp | 36.5% | 51.0% | +0.0pp | -21.3% | 41.0% | +0.0pp |
| 8gn_stock_soft_full_features | 5,346 | 2,967 | 25.7% | +0.4pp | 36.9% | 50.9% | -0.2pp | -19.8% | 41.2% | +0.3pp |
| 8gn_no_stock_features_current_route | 5,346 | 2,967 | 24.7% | -0.6pp | 36.6% | 51.4% | +0.4pp | -21.4% | 42.0% | +1.0pp |
| 8gn_no_stock_features_stock_soft | 5,346 | 2,967 | 25.0% | -0.3pp | 37.1% | 51.3% | +0.3pp | -19.9% | 42.2% | +1.2pp |

## Revenue Scope Validation - 8gn_stock_soft_full_features

| Scope | Rows | Qty scored | Actual revenue | Champion hit +/-20 | Candidate hit +/-20 | Hit delta | Champion WMAPE | Candidate WMAPE | WMAPE delta | Champion phantom | Candidate phantom | Phantom delta |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Top 100 | 475 | 349 | 19,774,645 | 27.8% | 28.1% | +0.3pp | 43.0% | 42.7% | -0.2pp | 62.1% | 62.1% | +0.0pp |
| Top 250 | 1,373 | 943 | 39,557,500 | 27.4% | 27.7% | +0.3pp | 46.6% | 46.4% | -0.2pp | 55.7% | 55.7% | +0.0pp |
| Top 500 | 2,866 | 1,751 | 59,034,164 | 25.5% | 26.0% | +0.6pp | 49.9% | 49.6% | -0.3pp | 46.7% | 47.4% | +0.7pp |
| Top 750 | 4,140 | 2,384 | 70,548,177 | 25.4% | 25.7% | +0.3pp | 50.5% | 50.3% | -0.2pp | 42.3% | 42.7% | +0.4pp |
| Top 1000 | 5,346 | 2,967 | 79,136,333 | 25.3% | 25.7% | +0.4pp | 51.0% | 50.9% | -0.2pp | 41.0% | 41.2% | +0.3pp |

## Critical Slice Validation - 8gn_stock_soft_full_features

| Slice | Rows | Qty scored | Champion hit +/-20 | Candidate hit +/-20 | Hit delta | Champion WMAPE | Candidate WMAPE | WMAPE delta | Champion phantom | Candidate phantom | Phantom delta |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Current regular/proxy route | 1,462 | 1,026 | 33.1% | 33.1% | +0.0pp | 43.1% | 43.1% | +0.0pp | 68.4% | 68.4% | +0.0pp |
| Stock-constrained route | 886 | 492 | 26.8% | 27.8% | +1.0pp | 44.5% | 43.8% | -0.7pp | 44.9% | 46.3% | +1.5pp |
| Demand-regular no stock gate | 3,857 | 2,521 | 27.2% | 27.6% | +0.5pp | 49.2% | 49.1% | -0.2pp | 62.6% | 63.2% | +0.6pp |
| Any campaign/BF history 13w | 4,245 | 2,351 | 24.7% | 25.2% | +0.6pp | 51.5% | 51.2% | -0.2pp | 45.3% | 45.3% | +0.0pp |
| 2024-11-25 stress window | 684 | 253 | 17.8% | 17.8% | +0.0pp | 70.9% | 70.9% | +0.0pp | 57.1% | 57.1% | +0.0pp |
| 2024-12-30 monitor window | 661 | 315 | 21.3% | 24.1% | +2.9pp | 58.3% | 58.7% | +0.4pp | 38.1% | 38.1% | +0.0pp |

## Window Validation - 8gn_stock_soft_full_features

| Target start | Qty scored | Champion hit +/-20 | Candidate hit +/-20 | Hit delta | Champion WMAPE | Candidate WMAPE | WMAPE delta | Champion phantom | Candidate phantom | Phantom delta |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2024-08-26 | 427 | 27.9% | 28.3% | +0.5pp | 46.2% | 46.0% | -0.2pp | 31.1% | 32.2% | +1.1pp |
| 2024-09-23 | 428 | 35.7% | 35.0% | -0.7pp | 45.8% | 45.4% | -0.4pp | 49.5% | 50.5% | +1.1pp |
| 2024-10-28 | 546 | 15.8% | 15.8% | +0.0pp | 54.9% | 54.9% | +0.0pp | 31.3% | 31.3% | +0.0pp |
| 2024-11-25 | 253 | 17.8% | 17.8% | +0.0pp | 70.9% | 70.9% | +0.0pp | 57.1% | 57.1% | +0.0pp |
| 2024-12-30 | 315 | 21.3% | 24.1% | +2.9pp | 58.3% | 58.7% | +0.4pp | 38.1% | 38.1% | +0.0pp |
| 2025-01-27 | 352 | 24.1% | 26.1% | +2.0pp | 49.4% | 48.3% | -1.1pp | 30.1% | 30.1% | +0.0pp |
| 2025-02-24 | 318 | 32.4% | 31.4% | -0.9pp | 43.2% | 43.4% | +0.2pp | 37.2% | 37.2% | +0.0pp |
| 2025-03-24 | 328 | 28.4% | 28.4% | +0.0pp | 42.1% | 41.8% | -0.3pp | 42.1% | 42.1% | +0.0pp |

## Route / Feature Diagnostics

| Target start | Train windows | Eval rows | Current regular rows | Demand-regular rows | Extra demand-regular rows | Post-BF rows | Full features | No-stock features |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2024-08-26 | 4 | 705 | 378 | 501 | 123 | 0 | 141 | 100 |
| 2024-09-23 | 5 | 700 | 376 | 499 | 123 | 0 | 141 | 100 |
| 2024-10-28 | 6 | 688 | 0 | 0 | 0 | 0 | 141 | 100 |
| 2024-11-25 | 7 | 684 | 0 | 0 | 0 | 639 | 141 | 100 |
| 2024-12-30 | 8 | 661 | 15 | 475 | 460 | 0 | 141 | 100 |
| 2025-01-27 | 9 | 646 | 11 | 459 | 448 | 0 | 141 | 100 |
| 2025-02-24 | 10 | 641 | 348 | 463 | 115 | 0 | 141 | 100 |
| 2025-03-24 | 11 | 621 | 334 | 474 | 140 | 0 | 141 | 100 |

## Interpretation

- `8gn_stock_soft_full_features` keeps all model features but replaces the regular-route gate with demand regularity, not stock position.
- `8gn_no_stock_features_current_route` retrains base estimators without stock/availability features but keeps the current champion route gate.
- `8gn_no_stock_features_stock_soft` retrains without stock/availability features and uses demand-regular routing.
- The stock-feature ablation removes features containing `stock` or `availability`; stock labels are still attached only for reporting and mask comparison.
- This phase is still a rolling backtest on known windows, not independent future holdout evidence.

## Outputs

- Matrix rows: 8,227.
- Revenue-rank limit: Top 1000.
- Cache path: `/Users/fyodorgolovin/Downloads/Supply-Inventory v1.0 codex/backend/data/forecast_v2_feature_cache/feature_matrix_headline_top1000_75d919119851.pkl`.
- Cache hit: `False`.
- Removed feature count for no-stock ablation: 41.
- Score rows: `/Users/fyodorgolovin/Downloads/Supply-Inventory v1.0 codex/active_docs/ITER5AC_V2_PHASE8G_N_SCORE_ROWS.csv`.
- Skipped windows: `2024-04-29`, `2024-05-27`, `2024-07-01`, `2024-07-29`.
