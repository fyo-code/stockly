# Iteration 5Z - V2 Phase 8G-K Official Calibrated Policy Validation

Generated: 2026-05-26 17:34
Route version: `v2_routes_2026_05_21_availability`

## Decision

Decision: `KEEP_8G_I_CHAMPION`.

This is official rolling backtest/export validation through the main sklearn path. The calibrated candidate improves the aggregate score, but fails the window-stability gate; keep the 8G-I champion as the official high-revenue policy for now.

| Metric | Official control | 8G-I champion | 8G-K calibrated | 8G-K vs 8G-I |
| --- | --- | --- | --- | --- |
| Model | sk_blend_post_bf_safe | 8gf_regular_plus_post_bf_safe | 8gj_bfc_nonpost_lift_150 | - |
| Hit +/-20 | 23.4% | 25.3% | 27.2% | +1.9pp |
| Hit +/-30 | 34.8% | 36.5% | 39.2% | +2.7pp |
| WMAPE | 55.7% | 51.0% | 49.3% | -1.7pp |
| Bias | -17.0% | -21.3% | -9.3% | +12.0pp |
| Phantom | 43.5% | 41.0% | 41.0% | +0.0pp |

## Policy Safety Checks

| Check | Expected | Observed | Status |
| --- | --- | --- | --- |
| Default policy emits calibrated candidate | no | no | PASS |
| Candidate policy emits calibrated candidate | yes | yes | PASS |
| Candidate policy also emits 8G-I champion for comparison | yes | yes | PASS |
| Candidate policy blocked without Top 1000-or-lower rank scope | yes | yes | PASS |
| Same-run control hit +/-20 unchanged by policy flag | 0.0pp delta | +0.0pp | PASS |

## Promotion Gates

| Gate | Required | Observed | Status |
| --- | --- | --- | --- |
| Top 1000 hit +/-20 | >= +1.5pp vs control | +3.9pp | PASS |
| Top 1000 WMAPE | <= +0.5pp vs control | -6.4pp | PASS |
| Top 1000 phantom | <= +0.5pp vs control | -2.5pp | PASS |
| Top 500 hit +/-20 | >= 0.0pp vs control | +4.5pp | PASS |
| Top 100 hit +/-20 | >= 0.0pp vs control | +2.9pp | PASS |
| 2024-11-25 WMAPE | < control | -68.8pp | PASS |
| Candidate hit +/-20 vs 8G-I | > 8G-I | +1.9pp | PASS |
| Candidate WMAPE vs 8G-I | <= 8G-I | -1.7pp | PASS |
| Largest non-stress WMAPE regression vs 8G-I (2024-12-30) | <= +2.0pp | +15.4pp | FAIL |

## Required Monitors

| Monitor | Rows | Qty scored | Actual revenue | 8G-I hit +/-20 | 8G-K hit +/-20 | Hit delta | 8G-I hit +/-30 | 8G-K hit +/-30 | 8G-I WMAPE | 8G-K WMAPE | WMAPE delta | 8G-I bias | 8G-K bias | Bias delta | 8G-I phantom | 8G-K phantom | Phantom delta |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| All Top 1000 | 5,346 | 2,967 | 79,136,333 | 25.3% | 27.2% | +1.9pp | 36.5% | 39.2% | 51.0% | 49.3% | -1.7pp | -21.3% | -9.3% | +12.0pp | 41.0% | 41.0% | +0.0pp |
| Available/proxy regular | 1,462 | 1,026 | 22,650,364 | 33.1% | 33.1% | +0.0pp | 45.3% | 45.3% | 43.1% | 43.1% | +0.0pp | -6.0% | -6.0% | +0.0pp | 68.4% | 68.4% | +0.0pp |
| Available regular | 986 | 703 | 15,441,693 | 35.1% | 35.1% | +0.0pp | 48.1% | 48.1% | 41.1% | 41.1% | +0.0pp | -3.7% | -3.7% | +0.0pp | 87.2% | 87.2% | +0.0pp |
| BF/campaign-sensitive route | 2,134 | 1,184 | 33,838,656 | 18.6% | 23.4% | +4.8pp | 27.8% | 34.5% | 57.4% | 53.8% | -3.6pp | -31.2% | -5.5% | +25.7pp | 46.2% | 46.2% | +0.0pp |
| 2025-03-24 monitor window | 621 | 328 | 7,894,646 | 28.4% | 28.4% | +0.0pp | 44.5% | 44.5% | 42.1% | 42.1% | +0.0pp | -4.4% | -4.4% | +0.0pp | 42.1% | 42.1% | +0.0pp |
| 2024-12-30 largest non-stress WMAPE regression | 661 | 315 | 7,688,500 | 21.3% | 19.7% | -1.6pp | 33.3% | 32.1% | 58.3% | 73.7% | +15.4pp | -9.0% | 25.9% | +34.9pp | 38.1% | 38.1% | +0.0pp |
| 2024-11-25 stress window | 684 | 253 | 5,426,480 | 17.8% | 17.8% | +0.0pp | 23.3% | 23.3% | 70.9% | 70.9% | +0.0pp | 38.0% | 38.0% | +0.0pp | 57.1% | 57.1% | +0.0pp |

## Official Aggregate Models

| Model | Rows | Qty scored | Hit +/-20 | Delta vs control | Hit +/-30 | WMAPE | Bias | Phantom |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| sk_blend_post_bf_safe | 5,346 | 2,967 | 23.4% | +0.0pp | 34.8% | 55.7% | -17.0% | 43.5% |
| 8gf_regular_plus_post_bf_safe | 5,346 | 2,967 | 25.3% | +2.0pp | 36.5% | 51.0% | -21.3% | 41.0% |
| 8gj_bfc_nonpost_lift_150 | 5,346 | 2,967 | 27.2% | +3.9pp | 39.2% | 49.3% | -9.3% | 41.0% |
| sk_extra_trees | 5,346 | 2,967 | 25.3% | +1.9pp | 36.0% | 57.0% | -10.4% | 45.7% |
| sk_hgb_squared | 5,346 | 2,967 | 25.3% | +2.0pp | 37.4% | 62.6% | -8.3% | 57.8% |
| post_bf_safe_naive | 5,346 | 2,967 | 22.2% | -1.1pp | 32.9% | 52.9% | -24.8% | 65.9% |
| median_naive | 5,346 | 2,967 | 21.4% | -2.0pp | 32.2% | 57.3% | -18.9% | 69.3% |
| sk_blend_median | 5,346 | 2,967 | 23.3% | -0.0pp | 34.6% | 57.3% | -15.4% | 43.6% |
| sk_hgb_poisson | 5,346 | 2,967 | 21.4% | -2.0pp | 32.4% | 62.1% | -15.8% | 33.9% |

## Revenue Scope Validation - Candidate vs Control

| Scope | Rows | Qty scored | Actual revenue | Control hit +/-20 | Candidate hit +/-20 | Hit delta | Control hit +/-30 | Candidate hit +/-30 | Control WMAPE | Candidate WMAPE | WMAPE delta | Control bias | Candidate bias | Bias delta | Control phantom | Candidate phantom | Phantom delta |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Top 100 | 475 | 349 | 19,774,645 | 26.6% | 29.5% | +2.9pp | 39.0% | 43.0% | 48.6% | 42.3% | -6.3pp | -3.7% | 1.1% | +4.8pp | 62.1% | 62.1% | +0.0pp |
| Top 250 | 1,373 | 943 | 39,557,500 | 24.2% | 30.1% | +5.9pp | 35.5% | 42.8% | 53.5% | 45.5% | -8.0pp | -12.8% | -7.5% | +5.3pp | 58.8% | 55.7% | -3.1pp |
| Top 500 | 2,866 | 1,751 | 59,034,164 | 23.2% | 27.7% | +4.5pp | 35.0% | 40.4% | 55.3% | 48.7% | -6.7pp | -14.1% | -7.3% | +6.9pp | 49.3% | 46.7% | -2.6pp |
| Top 750 | 4,140 | 2,384 | 70,548,177 | 23.3% | 27.9% | +4.6pp | 34.8% | 39.8% | 55.7% | 49.0% | -6.7pp | -15.3% | -8.1% | +7.2pp | 45.2% | 42.3% | -2.8pp |
| Top 1000 | 5,346 | 2,967 | 79,136,333 | 23.4% | 27.2% | +3.9pp | 34.8% | 39.2% | 55.7% | 49.3% | -6.4pp | -17.0% | -9.3% | +7.7pp | 43.5% | 41.0% | -2.5pp |

## Critical Slice Validation - Candidate vs 8G-I

| Slice | Rows | Qty scored | Actual revenue | 8G-I hit +/-20 | Candidate hit +/-20 | Hit delta | 8G-I hit +/-30 | Candidate hit +/-30 | 8G-I WMAPE | Candidate WMAPE | WMAPE delta | 8G-I bias | Candidate bias | Bias delta | 8G-I phantom | Candidate phantom | Phantom delta |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Available/proxy regular | 1,462 | 1,026 | 22,650,364 | 33.1% | 33.1% | +0.0pp | 45.3% | 45.3% | 43.1% | 43.1% | +0.0pp | -6.0% | -6.0% | +0.0pp | 68.4% | 68.4% | +0.0pp |
| Available regular | 986 | 703 | 15,441,693 | 35.1% | 35.1% | +0.0pp | 48.1% | 48.1% | 41.1% | 41.1% | +0.0pp | -3.7% | -3.7% | +0.0pp | 87.2% | 87.2% | +0.0pp |
| BF/campaign-sensitive route | 2,134 | 1,184 | 33,838,656 | 18.6% | 23.4% | +4.8pp | 27.8% | 34.5% | 57.4% | 53.8% | -3.6pp | -31.2% | -5.5% | +25.7pp | 46.2% | 46.2% | +0.0pp |
| Any campaign/BF history 13w | 4,245 | 2,351 | 63,056,072 | 24.7% | 26.6% | +2.0pp | 35.9% | 38.6% | 51.5% | 50.3% | -1.2pp | -19.5% | -6.0% | +13.5pp | 45.3% | 45.3% | +0.0pp |
| Post-BF stress rows | 639 | 252 | 5,402,089 | 17.9% | 17.9% | +0.0pp | 23.4% | 23.4% | 70.9% | 70.9% | +0.0pp | 37.9% | 37.9% | +0.0pp | 73.1% | 73.1% | +0.0pp |
| 2024-11-25 stress window | 684 | 253 | 5,426,480 | 17.8% | 17.8% | +0.0pp | 23.3% | 23.3% | 70.9% | 70.9% | +0.0pp | 38.0% | 38.0% | +0.0pp | 57.1% | 57.1% | +0.0pp |
| 2025-03-24 monitor window | 621 | 328 | 7,894,646 | 28.4% | 28.4% | +0.0pp | 44.5% | 44.5% | 42.1% | 42.1% | +0.0pp | -4.4% | -4.4% | +0.0pp | 42.1% | 42.1% | +0.0pp |

## Route Validation - Candidate vs 8G-I

| Route | Rows | Qty scored | Actual revenue | 8G-I hit +/-20 | Candidate hit +/-20 | Hit delta | 8G-I hit +/-30 | Candidate hit +/-30 | 8G-I WMAPE | Candidate WMAPE | WMAPE delta | 8G-I bias | Candidate bias | Bias delta | 8G-I phantom | Candidate phantom | Phantom delta |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| stock_constrained | 886 | 492 | 15,083,936 | 26.8% | 26.8% | +0.0pp | 40.9% | 40.9% | 44.5% | 44.5% | +0.0pp | -16.5% | -16.5% | +0.0pp | 44.9% | 44.9% | +0.0pp |
| bf_campaign_sensitive | 2,134 | 1,184 | 33,838,656 | 18.6% | 23.4% | +4.8pp | 27.8% | 34.5% | 57.4% | 53.8% | -3.6pp | -31.2% | -5.5% | +25.7pp | 46.2% | 46.2% | +0.0pp |
| seasonal_active | 9 | 4 | 93,282 | 0.0% | 0.0% | +0.0pp | 0.0% | 0.0% | 78.9% | 78.9% | +0.0pp | -56.2% | -56.2% | +0.0pp | 50.0% | 50.0% | +0.0pp |
| seasonal_quiet | 1 | 0 | 1,728 | - | - | - | - | - | - | - | - | - | - | - | - | - | - |
| sparse_intermittent | 738 | 215 | 6,724,248 | 17.7% | 17.7% | +0.0pp | 28.4% | 28.4% | 66.1% | 66.1% | +0.0pp | -49.9% | -49.9% | +0.0pp | 20.8% | 20.8% | +0.0pp |
| lifecycle_decline | 49 | 23 | 425,637 | 52.2% | 52.2% | +0.0pp | 56.5% | 56.5% | 47.0% | 47.0% | +0.0pp | -20.6% | -20.6% | +0.0pp | 75.0% | 75.0% | +0.0pp |
| available_regular | 986 | 703 | 15,441,693 | 35.1% | 35.1% | +0.0pp | 48.1% | 48.1% | 41.1% | 41.1% | +0.0pp | -3.7% | -3.7% | +0.0pp | 87.2% | 87.2% | +0.0pp |
| proxy_available_regular | 476 | 323 | 7,208,670 | 28.8% | 28.8% | +0.0pp | 39.3% | 39.3% | 47.9% | 47.9% | +0.0pp | -11.8% | -11.8% | +0.0pp | 48.6% | 48.6% | +0.0pp |
| availability_unknown | 67 | 23 | 318,482 | 39.1% | 39.1% | +0.0pp | 60.9% | 60.9% | 38.7% | 38.7% | +0.0pp | -9.4% | -9.4% | +0.0pp | 32.1% | 32.1% | +0.0pp |

## Window Validation - Candidate vs 8G-I

| Target start | Rows | Qty scored | Actual revenue | 8G-I hit +/-20 | Candidate hit +/-20 | Hit delta | 8G-I hit +/-30 | Candidate hit +/-30 | 8G-I WMAPE | Candidate WMAPE | WMAPE delta | 8G-I bias | Candidate bias | Bias delta | 8G-I phantom | Candidate phantom | Phantom delta |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2024-08-26 | 705 | 427 | 10,378,783 | 27.9% | 27.9% | +0.0pp | 37.5% | 37.5% | 46.2% | 46.2% | +0.0pp | -26.9% | -26.9% | +0.0pp | 31.1% | 31.1% | +0.0pp |
| 2024-09-23 | 700 | 428 | 10,174,878 | 35.7% | 35.7% | +0.0pp | 48.1% | 48.1% | 45.8% | 45.8% | +0.0pp | 4.5% | 4.5% | +0.0pp | 49.5% | 49.5% | +0.0pp |
| 2024-10-28 | 688 | 546 | 20,478,496 | 15.8% | 25.1% | +9.3pp | 24.7% | 40.1% | 54.9% | 44.5% | -10.3pp | -50.8% | -29.3% | +21.5pp | 31.3% | 31.3% | +0.0pp |
| 2024-11-25 | 684 | 253 | 5,426,480 | 17.8% | 17.8% | +0.0pp | 23.3% | 23.3% | 70.9% | 70.9% | +0.0pp | 38.0% | 38.0% | +0.0pp | 57.1% | 57.1% | +0.0pp |
| 2024-12-30 | 661 | 315 | 7,688,500 | 21.3% | 19.7% | -1.6pp | 33.3% | 32.1% | 58.3% | 73.7% | +15.4pp | -9.0% | 25.9% | +34.9pp | 38.1% | 38.1% | +0.0pp |
| 2025-01-27 | 646 | 352 | 9,089,493 | 24.1% | 27.3% | +3.1pp | 37.2% | 37.2% | 49.4% | 53.9% | +4.5pp | -21.8% | 7.6% | +29.4pp | 30.1% | 30.1% | +0.0pp |
| 2025-02-24 | 641 | 318 | 8,005,057 | 32.4% | 32.4% | +0.0pp | 44.3% | 44.3% | 43.2% | 43.2% | +0.0pp | -17.0% | -17.0% | +0.0pp | 37.2% | 37.2% | +0.0pp |
| 2025-03-24 | 621 | 328 | 7,894,646 | 28.4% | 28.4% | +0.0pp | 44.5% | 44.5% | 42.1% | 42.1% | +0.0pp | -4.4% | -4.4% | +0.0pp | 42.1% | 42.1% | +0.0pp |

## Zero-Actual / Phantom Export Check

| Baseline | Zero-actual rows | Baseline phantom | Candidate phantom | Phantom delta | Baseline pred units on zero actual | Candidate pred units on zero actual | Baseline avg pred units | Candidate avg pred units |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| sk_blend_post_bf_safe | 771 | 43.5% | 41.0% | -2.5pp | 2,669.9 | 2,720.6 | 3.46 | 3.53 |
| 8gf_regular_plus_post_bf_safe | 771 | 41.0% | 41.0% | +0.0pp | 2,395.8 | 2,720.6 | 3.11 | 3.53 |
| sk_extra_trees | 771 | 45.7% | 41.0% | -4.7pp | 3,569.3 | 2,720.6 | 4.63 | 3.53 |
| sk_hgb_squared | 771 | 57.8% | 41.0% | -16.9pp | 4,035.4 | 2,720.6 | 5.23 | 3.53 |
| post_bf_safe_naive | 771 | 65.9% | 41.0% | -24.9pp | 2,520.7 | 2,720.6 | 3.27 | 3.53 |
| median_naive | 771 | 69.3% | 41.0% | -28.3pp | 2,711.1 | 2,720.6 | 3.52 | 3.53 |

## Export Metadata

- Revenue-rank limit: Top 1000.
- 8G-I champion model/version: `8gf_regular_plus_post_bf_safe` / `high_revenue_policy_v1_2026_05_24`.
- 8G-K calibrated model/version: `8gj_bfc_nonpost_lift_150` / `high_revenue_policy_v2_2026_05_26`.
- 8G-K prediction source: `v2_high_revenue_policy`.
- Official score-row CSV: `/Users/fyodorgolovin/Downloads/Supply-Inventory v1.0 codex/active_docs/ITER5Z_V2_PHASE8G_OFFICIAL_CALIBRATED_SCORE_ROWS.csv`.
- Default-policy skipped windows: `2024-04-29`, `2024-05-27`, `2024-07-01`, `2024-07-29`.
- Candidate-policy skipped windows: `2024-04-29`, `2024-05-27`, `2024-07-01`, `2024-07-29`.
- The default v2 sklearn path remains `--high-revenue-policy none`.
- The calibrated path requires `--high-revenue-policy bfc_lift_150 --revenue-rank-limit 1000`.
- This is official rolling backtest validation on the known Phase 8G target windows, not independent future holdout validation.
