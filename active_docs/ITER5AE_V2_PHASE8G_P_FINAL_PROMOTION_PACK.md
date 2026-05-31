# Iteration 5AE - V2 Phase 8G-P Final Promotion Pack

Generated: 2026-05-28 14:54
Route version: `v2_routes_2026_05_26_stock_position`

## Decision

Decision: `PROMOTE_8G_O_GUARDED_POLICY_AND_STOP_CURRENT_DATA_ITERATION`.

The guarded pre-BF campaign candidate reproduces the 8G-O gain through the official sklearn path and clears the final gates. Promote it as the new explicit Top 1000 high-revenue policy, then stop current-data model iteration until new data arrives.

| Metric | Control | 8G-I champion | 8G-O guarded candidate | 8G-O vs 8G-I |
| --- | --- | --- | --- | --- |
| Model | sk_blend_post_bf_safe | 8gf_regular_plus_post_bf_safe | 8go_pre_bf_bfc_lift_180 | - |
| Hit +/-20 | 23.4% | 25.3% | 27.4% | +2.1pp |
| Hit +/-30 | 34.8% | 36.5% | 39.4% | +2.9pp |
| WMAPE | 55.7% | 51.0% | 47.4% | -3.6pp |
| Bias | -17.0% | -21.3% | -10.5% | +10.7pp |
| Phantom | 43.5% | 41.0% | 41.0% | +0.0pp |

## Policy Safety Checks

| Check | Expected | Observed | Status |
| --- | --- | --- | --- |
| Default policy emits guarded candidate | no | no | PASS |
| Guarded policy emits guarded candidate | yes | yes | PASS |
| Guarded policy includes 8G-I champion for comparison | yes | yes | PASS |
| Guarded policy blocked without Top 1000-or-lower rank scope | yes | yes | PASS |
| Same-run control hit +/-20 unchanged by policy flag | 0.0pp delta | +0.0pp | PASS |

## Final Promotion Gates

| Gate | Required | Observed | Status |
| --- | --- | --- | --- |
| Top 1000 hit +/-20 vs 8G-I | >= +1.0pp | +2.1pp | PASS |
| Top 1000 WMAPE vs 8G-I | <= 0.0pp | -3.6pp | PASS |
| Top 1000 bias vs 8G-I | > 0.0pp | +10.7pp | PASS |
| Top 1000 phantom vs 8G-I | <= 0.0pp | +0.0pp | PASS |
| Top 500 hit +/-20 vs 8G-I | >= 0.0pp | +2.6pp | PASS |
| Top 100 hit +/-20 vs 8G-I | >= 0.0pp | +4.3pp | PASS |
| 2024-11-25 WMAPE vs 8G-I | <= 0.0pp | +0.0pp | PASS |
| Largest non-stress WMAPE regression vs 8G-I (2024-08-26) | <= +2.0pp | +0.0pp | PASS |
| Top 1000 hit +/-20 vs control | >= +1.5pp | +4.1pp | PASS |
| Top 1000 WMAPE vs control | <= +0.5pp | -8.3pp | PASS |

## Official Aggregate Models

| Model | Rows | Qty scored | Hit +/-20 | Delta vs control | Hit +/-30 | WMAPE | Bias | Phantom |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| sk_blend_post_bf_safe | 5,346 | 2,967 | 23.4% | +0.0pp | 34.8% | 55.7% | -17.0% | 43.5% |
| 8gf_regular_plus_post_bf_safe | 5,346 | 2,967 | 25.3% | +2.0pp | 36.5% | 51.0% | -21.3% | 41.0% |
| 8go_pre_bf_bfc_lift_180 | 5,346 | 2,967 | 27.4% | +4.1pp | 39.4% | 47.4% | -10.5% | 41.0% |
| sk_extra_trees | 5,346 | 2,967 | 25.3% | +1.9pp | 36.0% | 57.0% | -10.4% | 45.7% |
| sk_hgb_squared | 5,346 | 2,967 | 25.3% | +2.0pp | 37.4% | 62.6% | -8.3% | 57.8% |
| post_bf_safe_naive | 5,346 | 2,967 | 22.2% | -1.1pp | 32.9% | 52.9% | -24.8% | 65.9% |
| median_naive | 5,346 | 2,967 | 21.4% | -2.0pp | 32.2% | 57.3% | -18.9% | 69.3% |
| sk_blend_median | 5,346 | 2,967 | 23.3% | -0.0pp | 34.6% | 57.3% | -15.4% | 43.6% |
| sk_hgb_poisson | 5,346 | 2,967 | 21.4% | -2.0pp | 32.4% | 62.1% | -15.8% | 33.9% |

## Revenue Scope Validation - 8G-O vs 8G-I

| Scope | Rows | Qty scored | Actual revenue | 8G-I hit +/-20 | 8G-O hit +/-20 | Hit delta | 8G-I hit +/-30 | 8G-O hit +/-30 | 8G-I WMAPE | 8G-O WMAPE | WMAPE delta | 8G-I bias | 8G-O bias | Bias delta | 8G-I phantom | 8G-O phantom | Phantom delta |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Top 100 | 475 | 349 | 19,774,645 | 27.8% | 32.1% | +4.3pp | 39.8% | 45.6% | 43.0% | 39.6% | -3.4pp | -9.6% | -1.1% | +8.5pp | 62.1% | 62.1% | +0.0pp |
| Top 250 | 1,373 | 943 | 39,557,500 | 27.4% | 31.0% | +3.6pp | 38.7% | 43.3% | 46.6% | 43.1% | -3.5pp | -18.6% | -9.0% | +9.6pp | 55.7% | 55.7% | +0.0pp |
| Top 500 | 2,866 | 1,751 | 59,034,164 | 25.5% | 28.1% | +2.6pp | 37.1% | 40.5% | 49.9% | 46.2% | -3.7pp | -18.9% | -9.0% | +9.9pp | 46.7% | 46.7% | +0.0pp |
| Top 750 | 4,140 | 2,384 | 70,548,177 | 25.4% | 28.4% | +3.1pp | 36.5% | 40.4% | 50.5% | 46.9% | -3.7pp | -20.0% | -10.1% | +9.9pp | 42.3% | 42.3% | +0.0pp |
| Top 1000 | 5,346 | 2,967 | 79,136,333 | 25.3% | 27.4% | +2.1pp | 36.5% | 39.4% | 51.0% | 47.4% | -3.6pp | -21.3% | -10.5% | +10.7pp | 41.0% | 41.0% | +0.0pp |

## Critical Slice Validation - 8G-O vs 8G-I

| Slice | Rows | Qty scored | Actual revenue | 8G-I hit +/-20 | 8G-O hit +/-20 | Hit delta | 8G-I hit +/-30 | 8G-O hit +/-30 | 8G-I WMAPE | 8G-O WMAPE | WMAPE delta | 8G-I bias | 8G-O bias | Bias delta | 8G-I phantom | 8G-O phantom | Phantom delta |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Available/proxy regular | 1,462 | 1,026 | 22,650,364 | 33.1% | 33.1% | +0.0pp | 45.3% | 45.3% | 43.1% | 43.1% | +0.0pp | -6.0% | -6.0% | +0.0pp | 68.4% | 68.4% | +0.0pp |
| BF/campaign-sensitive route | 2,134 | 1,184 | 33,838,656 | 18.6% | 23.9% | +5.3pp | 27.8% | 35.1% | 57.4% | 49.6% | -7.8pp | -31.2% | -8.3% | +22.9pp | 46.2% | 46.2% | +0.0pp |
| Pre-BF BF/campaign-sensitive | 586 | 465 | 16,915,309 | 15.7% | 29.2% | +13.5pp | 23.7% | 42.4% | 56.1% | 43.0% | -13.1pp | -51.7% | -13.2% | +38.5pp | 35.2% | 35.2% | +0.0pp |
| Normal-calendar BF/campaign-sensitive | 966 | 509 | 12,396,579 | 21.6% | 21.6% | +0.0pp | 33.2% | 33.2% | 54.7% | 54.7% | +0.0pp | -18.3% | -18.3% | +0.0pp | 39.2% | 39.2% | +0.0pp |
| Any campaign/BF history 13w | 4,245 | 2,351 | 63,056,072 | 24.7% | 26.8% | +2.2pp | 35.9% | 39.0% | 51.5% | 47.5% | -4.0pp | -19.5% | -9.9% | +9.7pp | 45.3% | 45.3% | +0.0pp |
| Post-BF stress rows | 639 | 252 | 5,402,089 | 17.9% | 17.9% | +0.0pp | 23.4% | 23.4% | 70.9% | 70.9% | +0.0pp | 37.9% | 37.9% | +0.0pp | 73.1% | 73.1% | +0.0pp |
| 2024-11-25 stress window | 684 | 253 | 5,426,480 | 17.8% | 17.8% | +0.0pp | 23.3% | 23.3% | 70.9% | 70.9% | +0.0pp | 38.0% | 38.0% | +0.0pp | 57.1% | 57.1% | +0.0pp |
| 2024-12-30 guard window | 661 | 315 | 7,688,500 | 21.3% | 21.3% | +0.0pp | 33.3% | 33.3% | 58.3% | 58.3% | +0.0pp | -9.0% | -9.0% | +0.0pp | 38.1% | 38.1% | +0.0pp |
| 2025-01-27 guard window | 646 | 352 | 9,089,493 | 24.1% | 24.1% | +0.0pp | 37.2% | 37.2% | 49.4% | 49.4% | +0.0pp | -21.8% | -21.8% | +0.0pp | 30.1% | 30.1% | +0.0pp |
| 2025-03-24 monitor window | 621 | 328 | 7,894,646 | 28.4% | 28.4% | +0.0pp | 44.5% | 44.5% | 42.1% | 42.1% | +0.0pp | -4.4% | -4.4% | +0.0pp | 42.1% | 42.1% | +0.0pp |

## Route Validation - 8G-O vs 8G-I

| Route | Rows | Qty scored | Actual revenue | 8G-I hit +/-20 | 8G-O hit +/-20 | Hit delta | 8G-I hit +/-30 | 8G-O hit +/-30 | 8G-I WMAPE | 8G-O WMAPE | WMAPE delta | 8G-I bias | 8G-O bias | Bias delta | 8G-I phantom | 8G-O phantom | Phantom delta |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| stock_constrained | 886 | 492 | 15,083,936 | 26.8% | 26.8% | +0.0pp | 40.9% | 40.9% | 44.5% | 44.5% | +0.0pp | -16.5% | -16.5% | +0.0pp | 44.9% | 44.9% | +0.0pp |
| bf_campaign_sensitive | 2,134 | 1,184 | 33,838,656 | 18.6% | 23.9% | +5.3pp | 27.8% | 35.1% | 57.4% | 49.6% | -7.8pp | -31.2% | -8.3% | +22.9pp | 46.2% | 46.2% | +0.0pp |
| seasonal_active | 9 | 4 | 93,282 | 0.0% | 0.0% | +0.0pp | 0.0% | 0.0% | 78.9% | 78.9% | +0.0pp | -56.2% | -56.2% | +0.0pp | 50.0% | 50.0% | +0.0pp |
| seasonal_quiet | 1 | 0 | 1,728 | - | - | - | - | - | - | - | - | - | - | - | - | - | - |
| sparse_intermittent | 738 | 215 | 6,724,248 | 17.7% | 17.7% | +0.0pp | 28.4% | 28.4% | 66.1% | 66.1% | +0.0pp | -49.9% | -49.9% | +0.0pp | 20.8% | 20.8% | +0.0pp |
| lifecycle_decline | 49 | 23 | 425,637 | 52.2% | 52.2% | +0.0pp | 56.5% | 56.5% | 47.0% | 47.0% | +0.0pp | -20.6% | -20.6% | +0.0pp | 75.0% | 75.0% | +0.0pp |
| available_regular | 986 | 703 | 15,441,693 | 35.1% | 35.1% | +0.0pp | 48.1% | 48.1% | 41.1% | 41.1% | +0.0pp | -3.7% | -3.7% | +0.0pp | 87.2% | 87.2% | +0.0pp |
| proxy_available_regular | 476 | 323 | 7,208,670 | 28.8% | 28.8% | +0.0pp | 39.3% | 39.3% | 47.9% | 47.9% | +0.0pp | -11.8% | -11.8% | +0.0pp | 48.6% | 48.6% | +0.0pp |
| availability_unknown | 67 | 23 | 318,482 | 39.1% | 39.1% | +0.0pp | 60.9% | 60.9% | 38.7% | 38.7% | +0.0pp | -9.4% | -9.4% | +0.0pp | 32.1% | 32.1% | +0.0pp |

## Window Validation - 8G-O vs 8G-I

| Target start | Rows | Qty scored | Actual revenue | 8G-I hit +/-20 | 8G-O hit +/-20 | Hit delta | 8G-I hit +/-30 | 8G-O hit +/-30 | 8G-I WMAPE | 8G-O WMAPE | WMAPE delta | 8G-I bias | 8G-O bias | Bias delta | 8G-I phantom | 8G-O phantom | Phantom delta |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2024-08-26 | 705 | 427 | 10,378,783 | 27.9% | 27.9% | +0.0pp | 37.5% | 37.5% | 46.2% | 46.2% | +0.0pp | -26.9% | -26.9% | +0.0pp | 31.1% | 31.1% | +0.0pp |
| 2024-09-23 | 700 | 428 | 10,174,878 | 35.7% | 35.7% | +0.0pp | 48.1% | 48.1% | 45.8% | 45.8% | +0.0pp | 4.5% | 4.5% | +0.0pp | 49.5% | 49.5% | +0.0pp |
| 2024-10-28 | 688 | 546 | 20,478,496 | 15.8% | 27.3% | +11.5pp | 24.7% | 40.7% | 54.9% | 43.2% | -11.7pp | -50.8% | -16.4% | +34.4pp | 31.3% | 31.3% | +0.0pp |
| 2024-11-25 | 684 | 253 | 5,426,480 | 17.8% | 17.8% | +0.0pp | 23.3% | 23.3% | 70.9% | 70.9% | +0.0pp | 38.0% | 38.0% | +0.0pp | 57.1% | 57.1% | +0.0pp |
| 2024-12-30 | 661 | 315 | 7,688,500 | 21.3% | 21.3% | +0.0pp | 33.3% | 33.3% | 58.3% | 58.3% | +0.0pp | -9.0% | -9.0% | +0.0pp | 38.1% | 38.1% | +0.0pp |
| 2025-01-27 | 646 | 352 | 9,089,493 | 24.1% | 24.1% | +0.0pp | 37.2% | 37.2% | 49.4% | 49.4% | +0.0pp | -21.8% | -21.8% | +0.0pp | 30.1% | 30.1% | +0.0pp |
| 2025-02-24 | 641 | 318 | 8,005,057 | 32.4% | 32.4% | +0.0pp | 44.3% | 44.3% | 43.2% | 43.2% | +0.0pp | -17.0% | -17.0% | +0.0pp | 37.2% | 37.2% | +0.0pp |
| 2025-03-24 | 621 | 328 | 7,894,646 | 28.4% | 28.4% | +0.0pp | 44.5% | 44.5% | 42.1% | 42.1% | +0.0pp | -4.4% | -4.4% | +0.0pp | 42.1% | 42.1% | +0.0pp |

## Zero-Actual / Phantom Export Check

| Baseline | Zero-actual rows | Baseline phantom | 8G-O phantom | Phantom delta | Baseline pred units on zero actual | 8G-O pred units on zero actual | Baseline avg pred units | 8G-O avg pred units |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| sk_blend_post_bf_safe | 771 | 43.5% | 41.0% | -2.5pp | 2,669.9 | 2,466.9 | 3.46 | 3.20 |
| 8gf_regular_plus_post_bf_safe | 771 | 41.0% | 41.0% | +0.0pp | 2,395.8 | 2,466.9 | 3.11 | 3.20 |
| sk_extra_trees | 771 | 45.7% | 41.0% | -4.7pp | 3,569.3 | 2,466.9 | 4.63 | 3.20 |
| sk_hgb_squared | 771 | 57.8% | 41.0% | -16.9pp | 4,035.4 | 2,466.9 | 5.23 | 3.20 |
| post_bf_safe_naive | 771 | 65.9% | 41.0% | -24.9pp | 2,520.7 | 2,466.9 | 3.27 | 3.20 |
| median_naive | 771 | 69.3% | 41.0% | -28.3pp | 2,711.1 | 2,466.9 | 3.52 | 3.20 |

## Stop / Data Decision

- Current-data stock iteration is exhausted: 8G-N did not promote stock-soft or no-stock variants.
- Current-data campaign iteration produced the final guarded pre-BF candidate; after this promotion pack, more blind current-data tweaking is not the next highest-value move.
- Next useful data: active/orderable/listed SKU history, future campaign membership and planned discounts, historical price levels, customer order status history, and fuller 2022-2025 hyperstore sales coverage.
- Pandemic-era sales can be added later as flagged context, but active/orderable and campaign/price intent are higher-value for the next accuracy ceiling.

## Export Metadata

- Revenue-rank limit: Top 1000.
- 8G-I champion model/version: `8gf_regular_plus_post_bf_safe` / `high_revenue_policy_v1_2026_05_24`.
- 8G-O guarded model/version: `8go_pre_bf_bfc_lift_180` / `high_revenue_policy_v3_2026_05_28`.
- 8G-O prediction source: `v2_high_revenue_policy`.
- Official score-row CSV: `/Users/fyodorgolovin/Downloads/Supply-Inventory v1.0 codex/active_docs/ITER5AE_V2_PHASE8G_P_OFFICIAL_SCORE_ROWS.csv`.
- Default-policy skipped windows: `2024-04-29`, `2024-05-27`, `2024-07-01`, `2024-07-29`.
- Candidate-policy skipped windows: `2024-04-29`, `2024-05-27`, `2024-07-01`, `2024-07-29`.
- Default v2 sklearn behavior remains `--high-revenue-policy none`.
- The promoted candidate requires `--high-revenue-policy pre_bf_bfc_lift_180 --revenue-rank-limit 1000`.
- This is official rolling backtest validation on known Phase 8G windows, not independent future holdout validation.
