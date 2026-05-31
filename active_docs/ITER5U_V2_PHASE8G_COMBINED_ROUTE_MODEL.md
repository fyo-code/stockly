# Iteration 5U - Forecast V2 Phase 8G-F Combined Route Model

Generated: 2026-05-24 16:22
Route version: `v2_routes_2026_05_21_availability`

## Verdict

Phase 8G-F produced a promotable combined Top 1000 candidate under the current gates.

| Metric | Top 1000 control | 8G-D component | 8G-E component | Best 8G-F combined |
| --- | --- | --- | --- | --- |
| Best model | sk_blend_post_bf_safe | 8gd_regular_global_extra | 8ge_post_bf_hard_safe | 8gf_regular_plus_post_bf_safe |
| Hit +/-20 | 23.4% | 24.4% | 24.3% | 25.3% |
| Delta hit +/-20 | - | - | - | +2.0pp |
| Hit +/-30 | 34.8% | 35.5% | 35.9% | 36.5% |
| WMAPE | 55.7% | 55.6% | 51.1% | 51.0% |
| Bias | -17.0% | -15.0% | -23.2% | -21.3% |
| Phantom rate | 43.5% | 43.6% | 40.9% | 41.0% |

## Aggregate Model Results

| Model | Rows | Qty scored | Hit +/-20 | Delta vs control | Hit +/-30 | WMAPE | Bias | Phantom rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| median_naive | 5,346 | 2,967 | 21.4% | -2.0pp | 32.2% | 57.3% | -18.9% | 69.3% |
| post_bf_safe_naive | 5,346 | 2,967 | 22.2% | -1.1pp | 32.9% | 52.9% | -24.8% | 65.9% |
| sk_hgb_squared | 5,346 | 2,967 | 25.3% | +2.0pp | 37.4% | 62.6% | -8.3% | 57.8% |
| sk_extra_trees | 5,346 | 2,967 | 25.3% | +1.9pp | 36.0% | 57.0% | -10.4% | 45.7% |
| sk_blend_post_bf_safe | 5,346 | 2,967 | 23.4% | +0.0pp | 34.8% | 55.7% | -17.0% | 43.5% |
| 8gd_regular_global_extra | 5,346 | 2,967 | 24.4% | +1.0pp | 35.5% | 55.6% | -15.0% | 43.6% |
| 8ge_post_bf_hard_safe | 5,346 | 2,967 | 24.3% | +0.9pp | 35.9% | 51.1% | -23.2% | 40.9% |
| 8gf_regular_plus_post_bf_safe | 5,346 | 2,967 | 25.3% | +2.0pp | 36.5% | 51.0% | -21.3% | 41.0% |
| 8gf_regular_plus_bf_calendar_safe | 5,346 | 2,967 | 24.8% | +1.5pp | 35.7% | 51.9% | -19.5% | 51.5% |
| 8gf_guarded_regular_plus_post_bf_safe | 5,346 | 2,967 | 24.5% | +1.1pp | 35.7% | 51.2% | -22.4% | 40.9% |

## Direct Component Comparison - 8gf_regular_plus_post_bf_safe

| Baseline | Baseline hit +/-20 | Candidate hit +/-20 | Hit delta | Baseline WMAPE | Candidate WMAPE | WMAPE delta | Baseline phantom | Candidate phantom | Phantom delta |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| sk_blend_post_bf_safe | 23.4% | 25.3% | +2.0pp | 55.7% | 51.0% | -4.7pp | 43.5% | 41.0% | -2.5pp |
| 8gd_regular_global_extra | 24.4% | 25.3% | +0.9pp | 55.6% | 51.0% | -4.6pp | 43.6% | 41.0% | -2.6pp |
| 8ge_post_bf_hard_safe | 24.3% | 25.3% | +1.0pp | 51.1% | 51.0% | -0.1pp | 40.9% | 41.0% | +0.1pp |

## Revenue Scope Deltas - 8gf_regular_plus_post_bf_safe

| Scope | Rows | Qty scored | Actual revenue | Control hit +/-20 | Candidate hit +/-20 | Hit delta | Control WMAPE | Candidate WMAPE | WMAPE delta | Control phantom | Candidate phantom | Phantom delta |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Top 100 | 475 | 349 | 19,774,645 | 26.6% | 27.8% | +1.1pp | 48.6% | 43.0% | -5.7pp | 62.1% | 62.1% | +0.0pp |
| Top 500 | 2,866 | 1,751 | 59,034,164 | 23.2% | 25.5% | +2.3pp | 55.3% | 49.9% | -5.4pp | 49.3% | 46.7% | -2.6pp |
| Top 1000 | 5,346 | 2,967 | 79,136,333 | 23.4% | 25.3% | +2.0pp | 55.7% | 51.0% | -4.7pp | 43.5% | 41.0% | -2.5pp |

## Critical Slice Deltas - 8gf_regular_plus_post_bf_safe

| Slice | Rows | Qty scored | Control hit +/-20 | Candidate hit +/-20 | Hit delta | Control WMAPE | Candidate WMAPE | WMAPE delta | Control bias | Candidate bias | Control phantom | Candidate phantom |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Top 1000 | 5,346 | 2,967 | 23.4% | 25.3% | +2.0pp | 55.7% | 51.0% | -4.7pp | -17.0% | -21.3% | 43.5% | 41.0% |
| Available/proxy regular | 1,462 | 1,026 | 30.2% | 33.1% | +2.9pp | 43.4% | 43.1% | -0.3pp | -11.8% | -6.0% | 67.1% | 68.4% |
| BF/campaign-sensitive route | 2,134 | 1,184 | 16.6% | 18.6% | +1.9pp | 65.4% | 57.4% | -7.9pp | -20.2% | -31.2% | 51.6% | 46.2% |
| Any campaign/BF history | 4,245 | 2,351 | 22.4% | 24.7% | +2.3pp | 58.2% | 51.5% | -6.8pp | -12.2% | -19.5% | 48.7% | 45.3% |
| 2024-11-25 stress | 684 | 253 | 6.7% | 17.8% | +11.1pp | 139.8% | 70.9% | -68.8pp | 133.0% | 38.0% | 70.7% | 57.1% |

## Route Scores - 8gf_regular_plus_post_bf_safe

| Route | Rows | Qty scored | Hit +/-20 | Hit +/-30 | WMAPE | Bias | Phantom rate |
| --- | --- | --- | --- | --- | --- | --- | --- |
| stock_constrained | 886 | 492 | 26.8% | 40.9% | 44.5% | -16.5% | 44.9% |
| bf_campaign_sensitive | 2,134 | 1,184 | 18.6% | 27.8% | 57.4% | -31.2% | 46.2% |
| seasonal_active | 9 | 4 | 0.0% | 0.0% | 78.9% | -56.2% | 50.0% |
| seasonal_quiet | 1 | 0 | - | - | - | - | - |
| sparse_intermittent | 738 | 215 | 17.7% | 28.4% | 66.1% | -49.9% | 20.8% |
| lifecycle_decline | 49 | 23 | 52.2% | 56.5% | 47.0% | -20.6% | 75.0% |
| available_regular | 986 | 703 | 35.1% | 48.1% | 41.1% | -3.7% | 87.2% |
| proxy_available_regular | 476 | 323 | 28.8% | 39.3% | 47.9% | -11.8% | 48.6% |
| availability_unknown | 67 | 23 | 39.1% | 60.9% | 38.7% | -9.4% | 32.1% |

## Window Scores - 8gf_regular_plus_post_bf_safe

| Target start | Qty scored | Hit +/-20 | Hit +/-30 | WMAPE | Bias | Phantom rate |
| --- | --- | --- | --- | --- | --- | --- |
| 2024-08-26 | 427 | 27.9% | 37.5% | 46.2% | -26.9% | 31.1% |
| 2024-09-23 | 428 | 35.7% | 48.1% | 45.8% | 4.5% | 49.5% |
| 2024-10-28 | 546 | 15.8% | 24.7% | 54.9% | -50.8% | 31.3% |
| 2024-11-25 | 253 | 17.8% | 23.3% | 70.9% | 38.0% | 57.1% |
| 2024-12-30 | 315 | 21.3% | 33.3% | 58.3% | -9.0% | 38.1% |
| 2025-01-27 | 352 | 24.1% | 37.2% | 49.4% | -21.8% | 30.1% |
| 2025-02-24 | 318 | 32.4% | 44.3% | 43.2% | -17.0% | 37.2% |
| 2025-03-24 | 328 | 28.4% | 44.5% | 42.1% | -4.4% | 42.1% |

## Combination Diagnostics

| Target start | Train windows | Eval rows | Regular rows | Guarded regular rows | Campaign rows | BF-calendar rows | Post-BF stress rows |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2024-08-26 | 4 | 705 | 378 | 95 | 504 | 0 | 0 |
| 2024-09-23 | 5 | 700 | 376 | 106 | 486 | 0 | 0 |
| 2024-10-28 | 6 | 688 | 0 | 0 | 650 | 688 | 0 |
| 2024-11-25 | 7 | 684 | 0 | 0 | 681 | 684 | 639 |
| 2024-12-30 | 8 | 661 | 15 | 2 | 641 | 629 | 0 |
| 2025-01-27 | 9 | 646 | 11 | 4 | 625 | 619 | 0 |
| 2025-02-24 | 10 | 641 | 348 | 110 | 424 | 0 | 0 |
| 2025-03-24 | 11 | 621 | 334 | 105 | 414 | 0 | 0 |

## Skipped Windows

`2024-04-29`, `2024-05-27`, `2024-07-01`, `2024-07-29`

## Notes

- Revenue-rank limit: Top 1000.
- Feature matrix rows: 8,227.
- Feature matrix cache: `/Users/fyodorgolovin/Downloads/Supply-Inventory v1.0 codex/backend/data/forecast_v2_feature_cache/feature_matrix_headline_top1000_aa54e4e2fe0a.pkl` (hit).
- `8gf_regular_plus_post_bf_safe` uses the 8G-D regular extra-trees replacement, then overrides post-BF stress rows with the 8G-E hard-safe fallback.
- `8gf_regular_plus_bf_calendar_safe` is a broader BF-calendar guard; it is expected to be safer only if broad campaign windows are overpredicted.
- `8gf_guarded_regular_plus_post_bf_safe` only applies the regular extra-trees replacement on regular rows without campaign/BF history.
- All model training uses only earlier target windows.
- Route and campaign gates are forecast-time-safe; target-window campaign buckets are not model features.
- Phase 8F current snapshots remain excluded from historical backtests.
