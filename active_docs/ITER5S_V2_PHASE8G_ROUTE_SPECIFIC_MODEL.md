# Iteration 5S - Forecast V2 Phase 8G-D Route-Specific Model

Generated: 2026-05-23 18:26
Route version: `v2_routes_2026_05_21_availability`

## Verdict

Phase 8G-D produced a small diagnostic route-specific improvement, but it is below the promotion gate.

| Metric | Top 1000 control | Raw hit winner | Best 8G-D route candidate |
| --- | --- | --- | --- |
| Best model | sk_blend_post_bf_safe | sk_hgb_squared | 8gd_regular_global_extra |
| Hit +/-20 | 23.4% | 25.3% | 24.4% |
| Delta hit +/-20 | - | +2.0pp | +1.0pp |
| Hit +/-30 | 34.8% | 37.4% | 35.5% |
| WMAPE | 55.7% | 62.6% | 55.6% |
| Bias | -17.0% | -8.3% | -15.0% |
| Phantom rate | 43.5% | 57.8% | 43.6% |

## Aggregate Model Results

| Model | Rows | Qty scored | Hit +/-20 | Delta vs control | Hit +/-30 | WMAPE | Bias | Phantom rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| median_naive | 5,346 | 2,967 | 21.4% | -2.0pp | 32.2% | 57.3% | -18.9% | 69.3% |
| post_bf_safe_naive | 5,346 | 2,967 | 22.2% | -1.1pp | 32.9% | 52.9% | -24.8% | 65.9% |
| sk_hgb_poisson | 5,346 | 2,967 | 21.4% | -2.0pp | 32.4% | 62.1% | -15.8% | 33.9% |
| sk_hgb_squared | 5,346 | 2,967 | 25.3% | +2.0pp | 37.4% | 62.6% | -8.3% | 57.8% |
| sk_extra_trees | 5,346 | 2,967 | 25.3% | +1.9pp | 36.0% | 57.0% | -10.4% | 45.7% |
| sk_blend_post_bf_safe | 5,346 | 2,967 | 23.4% | +0.0pp | 34.8% | 55.7% | -17.0% | 43.5% |
| 8gd_regular_global_extra | 5,346 | 2,967 | 24.4% | +1.0pp | 35.5% | 55.6% | -15.0% | 43.6% |
| 8gd_regular_specialist_extra | 5,346 | 2,967 | 23.9% | +0.6pp | 35.5% | 55.6% | -16.9% | 44.1% |
| 8gd_supplier_available_extra | 5,346 | 2,967 | 24.1% | +0.7pp | 35.1% | 55.6% | -14.9% | 44.1% |
| 8gd_availability_campaign_gated | 5,346 | 2,967 | 24.0% | +0.6pp | 35.0% | 55.7% | -16.4% | 45.7% |

## Revenue Scope Deltas - 8gd_regular_global_extra

| Scope | Rows | Qty scored | Actual revenue | Control hit +/-20 | Candidate hit +/-20 | Hit delta | Control WMAPE | Candidate WMAPE | WMAPE delta | Control phantom | Candidate phantom | Phantom delta |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Top 100 | 475 | 349 | 19,774,645 | 26.6% | 27.2% | +0.6pp | 48.6% | 48.9% | +0.2pp | 62.1% | 65.5% | +3.4pp |
| Top 500 | 2,866 | 1,751 | 59,034,164 | 23.2% | 24.3% | +1.1pp | 55.3% | 55.1% | -0.3pp | 49.3% | 49.7% | +0.3pp |
| Top 1000 | 5,346 | 2,967 | 79,136,333 | 23.4% | 24.4% | +1.0pp | 55.7% | 55.6% | -0.1pp | 43.5% | 43.6% | +0.1pp |

## Route Scores - 8gd_regular_global_extra

| Route | Rows | Qty scored | Hit +/-20 | Hit +/-30 | WMAPE | Bias | Phantom rate |
| --- | --- | --- | --- | --- | --- | --- | --- |
| stock_constrained | 886 | 492 | 25.8% | 39.8% | 50.7% | -8.0% | 47.1% |
| bf_campaign_sensitive | 2,134 | 1,184 | 16.6% | 25.6% | 65.4% | -20.2% | 51.6% |
| seasonal_active | 9 | 4 | 0.0% | 0.0% | 78.9% | -56.2% | 50.0% |
| seasonal_quiet | 1 | 0 | - | - | - | - | - |
| sparse_intermittent | 738 | 215 | 17.7% | 28.4% | 66.1% | -49.9% | 20.8% |
| lifecycle_decline | 49 | 23 | 52.2% | 56.5% | 47.0% | -20.6% | 75.0% |
| available_regular | 986 | 703 | 35.1% | 48.1% | 41.1% | -3.7% | 87.2% |
| proxy_available_regular | 476 | 323 | 28.8% | 39.3% | 47.9% | -11.8% | 48.6% |
| availability_unknown | 67 | 23 | 39.1% | 60.9% | 38.7% | -9.4% | 32.1% |

## Window Scores - 8gd_regular_global_extra

| Target start | Qty scored | Hit +/-20 | Hit +/-30 | WMAPE | Bias | Phantom rate |
| --- | --- | --- | --- | --- | --- | --- |
| 2024-08-26 | 427 | 27.9% | 37.5% | 46.2% | -26.9% | 31.1% |
| 2024-09-23 | 428 | 35.7% | 48.1% | 45.8% | 4.5% | 49.5% |
| 2024-10-28 | 546 | 15.8% | 24.7% | 54.9% | -50.8% | 31.3% |
| 2024-11-25 | 253 | 6.7% | 11.1% | 139.8% | 133.0% | 70.7% |
| 2024-12-30 | 315 | 21.3% | 33.3% | 58.3% | -9.0% | 38.1% |
| 2025-01-27 | 352 | 24.1% | 37.2% | 49.4% | -21.8% | 30.1% |
| 2025-02-24 | 318 | 32.4% | 44.3% | 43.2% | -17.0% | 37.2% |
| 2025-03-24 | 328 | 28.4% | 44.5% | 42.1% | -4.4% | 42.1% |

## Training Diagnostics

| Target start | Train windows | Eval rows | Regular rows | Campaign rows | Supplier available rows | Regular specialist | Campaign specialist | Stock specialist |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2024-08-26 | 4 | 705 | 378 | 504 | 424 | yes | yes | yes |
| 2024-09-23 | 5 | 700 | 376 | 486 | 426 | yes | yes | yes |
| 2024-10-28 | 6 | 688 | 0 | 650 | 0 | yes | yes | yes |
| 2024-11-25 | 7 | 684 | 0 | 681 | 0 | yes | yes | yes |
| 2024-12-30 | 8 | 661 | 15 | 641 | 90 | yes | yes | yes |
| 2025-01-27 | 9 | 646 | 11 | 625 | 83 | yes | yes | yes |
| 2025-02-24 | 10 | 641 | 348 | 424 | 387 | yes | yes | yes |
| 2025-03-24 | 11 | 621 | 334 | 414 | 377 | yes | yes | yes |

## Skipped Windows

`2024-04-29`, `2024-05-27`, `2024-07-01`, `2024-07-29`

## Notes

- Revenue-rank limit: Top 1000. This is a high-revenue experiment, not a full-headline promotion.
- Feature matrix rows: 8,227.
- Feature matrix cache: `/Users/fyodorgolovin/Downloads/Supply-Inventory v1.0 codex/backend/data/forecast_v2_feature_cache/feature_matrix_headline_top1000_aa54e4e2fe0a.pkl` (built).
- All model training uses only earlier target windows.
- Route gates use forecast-time route labels, supplier availability features, and cleaned campaign/BF history features.
- Product/program labels are not treated as campaign exposure features.
- Phase 8F current snapshots remain excluded from historical backtests.
