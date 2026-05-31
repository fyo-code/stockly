# Iteration 5X - V2 Phase 8G-I Official Policy Validation

Generated: 2026-05-26 11:22
Route version: `v2_routes_2026_05_21_availability`

## Decision

Decision: `PROMOTE_WITH_MONITORS`.

This is confirmatory backtest/export validation of the wired policy, not a fresh holdout. Blocking gates pass, monitors are still required, and the champion remains scoped to Top 1000 high-revenue runs behind the explicit policy flag.

| Metric | Official control | Official champion | Delta |
| --- | --- | --- | --- |
| Model | sk_blend_post_bf_safe | 8gf_regular_plus_post_bf_safe | - |
| Hit +/-20 | 23.4% | 25.3% | +2.0pp |
| Hit +/-30 | 34.8% | 36.5% | +1.7pp |
| WMAPE | 55.7% | 51.0% | -4.7pp |
| Bias | -17.0% | -21.3% | -4.3pp |
| Phantom | 43.5% | 41.0% | -2.5pp |

## Policy Safety Checks

| Check | Expected | Observed | Status |
| --- | --- | --- | --- |
| Default policy emits champion | no | no | PASS |
| Champion policy emits champion | yes | yes | PASS |
| Champion blocked without Top 1000-or-lower rank scope | yes | yes | PASS |
| Same-run control hit +/-20 unchanged by policy flag | 0.0pp delta | +0.0pp | PASS |

## Promotion Gates

| Gate | Required | Observed | Status |
| --- | --- | --- | --- |
| Top 1000 hit +/-20 | >= +1.5pp | +2.0pp | PASS |
| Top 1000 WMAPE | <= +0.5pp | -4.7pp | PASS |
| Top 1000 phantom | <= +0.5pp | -2.5pp | PASS |
| Top 500 hit +/-20 | >= 0.0pp | +2.3pp | PASS |
| Top 100 hit +/-20 | >= 0.0pp | +1.1pp | PASS |
| 2024-11-25 WMAPE | < control | -68.8pp | PASS |

## Required Monitors

| Monitor | Status | Observed | Why it matters |
| --- | --- | --- | --- |
| Overall bias | monitor | -4.3pp | Champion is more underpredictive; this is accepted, not ignored. |
| Available/proxy regular phantom | monitor | +1.3pp | Regular hit improves, but zero-actual false-positive risk rises. |
| Available regular phantom | monitor | +2.6pp | Largest route-level phantom caveat inside regular rows. |
| Largest non-stress window WMAPE regression | monitor | 2025-03-24: +1.8pp | This is diagnostic; 2024-11-25 is the named stress gate. |

## Official Aggregate Models

| Model | Rows | Qty scored | Hit +/-20 | Delta vs control | Hit +/-30 | WMAPE | Bias | Phantom |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 8gf_regular_plus_post_bf_safe | 5,346 | 2,967 | 25.3% | +2.0pp | 36.5% | 51.0% | -21.3% | 41.0% |
| median_naive | 5,346 | 2,967 | 21.4% | -2.0pp | 32.2% | 57.3% | -18.9% | 69.3% |
| post_bf_safe_naive | 5,346 | 2,967 | 22.2% | -1.1pp | 32.9% | 52.9% | -24.8% | 65.9% |
| sk_blend_median | 5,346 | 2,967 | 23.3% | -0.0pp | 34.6% | 57.3% | -15.4% | 43.6% |
| sk_blend_post_bf_safe | 5,346 | 2,967 | 23.4% | +0.0pp | 34.8% | 55.7% | -17.0% | 43.5% |
| sk_extra_trees | 5,346 | 2,967 | 25.3% | +1.9pp | 36.0% | 57.0% | -10.4% | 45.7% |
| sk_hgb_poisson | 5,346 | 2,967 | 21.4% | -2.0pp | 32.4% | 62.1% | -15.8% | 33.9% |
| sk_hgb_squared | 5,346 | 2,967 | 25.3% | +2.0pp | 37.4% | 62.6% | -8.3% | 57.8% |

## Revenue Scope Validation

| Scope | Rows | Qty scored | Actual revenue | Control hit +/-20 | Champion hit +/-20 | Hit delta | Control hit +/-30 | Champion hit +/-30 | Control WMAPE | Champion WMAPE | WMAPE delta | Control bias | Champion bias | Control phantom | Champion phantom | Phantom delta |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Top 100 | 475 | 349 | 19,774,645 | 26.6% | 27.8% | +1.1pp | 39.0% | 39.8% | 48.6% | 43.0% | -5.7pp | -3.7% | -9.6% | 62.1% | 62.1% | +0.0pp |
| Top 250 | 1,373 | 943 | 39,557,500 | 24.2% | 27.4% | +3.2pp | 35.5% | 38.7% | 53.5% | 46.6% | -6.9pp | -12.8% | -18.6% | 58.8% | 55.7% | -3.1pp |
| Top 500 | 2,866 | 1,751 | 59,034,164 | 23.2% | 25.5% | +2.3pp | 35.0% | 37.1% | 55.3% | 49.9% | -5.4pp | -14.1% | -18.9% | 49.3% | 46.7% | -2.6pp |
| Top 750 | 4,140 | 2,384 | 70,548,177 | 23.3% | 25.4% | +2.1pp | 34.8% | 36.5% | 55.7% | 50.5% | -5.1pp | -15.3% | -20.0% | 45.2% | 42.3% | -2.8pp |
| Top 1000 | 5,346 | 2,967 | 79,136,333 | 23.4% | 25.3% | +2.0pp | 34.8% | 36.5% | 55.7% | 51.0% | -4.7pp | -17.0% | -21.3% | 43.5% | 41.0% | -2.5pp |

## Critical Slice Validation

| Slice | Rows | Qty scored | Actual revenue | Control hit +/-20 | Champion hit +/-20 | Hit delta | Control hit +/-30 | Champion hit +/-30 | Control WMAPE | Champion WMAPE | WMAPE delta | Control bias | Champion bias | Control phantom | Champion phantom | Phantom delta |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Available/proxy regular | 1,462 | 1,026 | 22,650,364 | 30.2% | 33.1% | +2.9pp | 43.5% | 45.3% | 43.4% | 43.1% | -0.3pp | -11.8% | -6.0% | 67.1% | 68.4% | +1.3pp |
| BF/campaign-sensitive route | 2,134 | 1,184 | 33,838,656 | 16.6% | 18.6% | +1.9pp | 25.6% | 27.8% | 65.4% | 57.4% | -7.9pp | -20.2% | -31.2% | 51.6% | 46.2% | -5.4pp |
| Any campaign/BF history 13w | 4,245 | 2,351 | 63,056,072 | 22.4% | 24.7% | +2.3pp | 33.6% | 35.9% | 58.2% | 51.5% | -6.8pp | -12.2% | -19.5% | 48.7% | 45.3% | -3.4pp |
| Post-BF stress rows | 639 | 252 | 5,402,089 | 6.7% | 17.9% | +11.1pp | 11.1% | 23.4% | 139.9% | 70.9% | -69.0pp | 133.1% | 37.9% | 91.7% | 73.1% | -18.5pp |
| 2024-11-25 stress window | 684 | 253 | 5,426,480 | 6.7% | 17.8% | +11.1pp | 11.1% | 23.3% | 139.8% | 70.9% | -68.8pp | 133.0% | 38.0% | 70.7% | 57.1% | -13.6pp |

## Route Validation

| Route | Rows | Qty scored | Actual revenue | Control hit +/-20 | Champion hit +/-20 | Hit delta | Control hit +/-30 | Champion hit +/-30 | Control WMAPE | Champion WMAPE | WMAPE delta | Control bias | Champion bias | Control phantom | Champion phantom | Phantom delta |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| stock_constrained | 886 | 492 | 15,083,936 | 25.8% | 26.8% | +1.0pp | 39.8% | 40.9% | 50.7% | 44.5% | -6.2pp | -8.0% | -16.5% | 47.1% | 44.9% | -2.2pp |
| bf_campaign_sensitive | 2,134 | 1,184 | 33,838,656 | 16.6% | 18.6% | +1.9pp | 25.6% | 27.8% | 65.4% | 57.4% | -7.9pp | -20.2% | -31.2% | 51.6% | 46.2% | -5.4pp |
| seasonal_active | 9 | 4 | 93,282 | 0.0% | 0.0% | +0.0pp | 0.0% | 0.0% | 78.9% | 78.9% | +0.0pp | -56.2% | -56.2% | 50.0% | 50.0% | +0.0pp |
| seasonal_quiet | 1 | 0 | 1,728 | - | - | - | - | - | - | - | - | - | - | - | - | - |
| sparse_intermittent | 738 | 215 | 6,724,248 | 17.7% | 17.7% | +0.0pp | 28.4% | 28.4% | 66.1% | 66.1% | +0.0pp | -49.9% | -49.9% | 20.8% | 20.8% | +0.0pp |
| lifecycle_decline | 49 | 23 | 425,637 | 52.2% | 52.2% | +0.0pp | 56.5% | 56.5% | 47.0% | 47.0% | +0.0pp | -20.6% | -20.6% | 75.0% | 75.0% | +0.0pp |
| available_regular | 986 | 703 | 15,441,693 | 32.4% | 35.1% | +2.7pp | 47.1% | 48.1% | 41.5% | 41.1% | -0.4pp | -9.5% | -3.7% | 84.6% | 87.2% | +2.6pp |
| proxy_available_regular | 476 | 323 | 7,208,670 | 25.4% | 28.8% | +3.4pp | 35.6% | 39.3% | 47.9% | 47.9% | -0.0pp | -17.5% | -11.8% | 48.6% | 48.6% | +0.0pp |
| availability_unknown | 67 | 23 | 318,482 | 39.1% | 39.1% | +0.0pp | 60.9% | 60.9% | 38.7% | 38.7% | +0.0pp | -9.4% | -9.4% | 32.1% | 32.1% | +0.0pp |

## Window Validation

| Target start | Rows | Qty scored | Actual revenue | Control hit +/-20 | Champion hit +/-20 | Hit delta | Control hit +/-30 | Champion hit +/-30 | Control WMAPE | Champion WMAPE | WMAPE delta | Control bias | Champion bias | Control phantom | Champion phantom | Phantom delta |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2024-08-26 | 705 | 427 | 10,378,783 | 25.3% | 27.9% | +2.6pp | 37.0% | 37.5% | 47.5% | 46.2% | -1.3pp | -29.3% | -26.9% | 31.1% | 31.1% | +0.0pp |
| 2024-09-23 | 700 | 428 | 10,174,878 | 34.1% | 35.7% | +1.6pp | 47.7% | 48.1% | 46.0% | 45.8% | -0.3pp | -0.6% | 4.5% | 49.5% | 49.5% | +0.0pp |
| 2024-10-28 | 688 | 546 | 20,478,496 | 15.8% | 15.8% | +0.0pp | 24.7% | 24.7% | 54.9% | 54.9% | +0.0pp | -50.8% | -50.8% | 31.3% | 31.3% | +0.0pp |
| 2024-11-25 | 684 | 253 | 5,426,480 | 6.7% | 17.8% | +11.1pp | 11.1% | 23.3% | 139.8% | 70.9% | -68.8pp | 133.0% | 38.0% | 70.7% | 57.1% | -13.6pp |
| 2024-12-30 | 661 | 315 | 7,688,500 | 21.0% | 21.3% | +0.3pp | 32.7% | 33.3% | 58.5% | 58.3% | -0.1pp | -9.3% | -9.0% | 37.2% | 38.1% | +0.9pp |
| 2025-01-27 | 646 | 352 | 9,089,493 | 24.1% | 24.1% | +0.0pp | 36.9% | 37.2% | 49.3% | 49.4% | +0.1pp | -22.0% | -21.8% | 30.1% | 30.1% | +0.0pp |
| 2025-02-24 | 641 | 318 | 8,005,057 | 29.2% | 32.4% | +3.1pp | 39.9% | 44.3% | 43.8% | 43.2% | -0.6pp | -22.9% | -17.0% | 37.2% | 37.2% | +0.0pp |
| 2025-03-24 | 621 | 328 | 7,894,646 | 28.0% | 28.4% | +0.3pp | 45.1% | 44.5% | 40.3% | 42.1% | +1.8pp | -8.7% | -4.4% | 42.1% | 42.1% | +0.0pp |

## Zero-Actual / Phantom Export Check

| Baseline | Zero-actual rows | Baseline phantom | Champion phantom | Phantom delta | Baseline pred units on zero actual | Champion pred units on zero actual | Baseline avg pred units | Champion avg pred units |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| sk_blend_post_bf_safe | 771 | 43.5% | 41.0% | -2.5pp | 2,669.9 | 2,395.8 | 3.46 | 3.11 |
| sk_extra_trees | 771 | 45.7% | 41.0% | -4.7pp | 3,569.3 | 2,395.8 | 4.63 | 3.11 |
| sk_hgb_squared | 771 | 57.8% | 41.0% | -16.9pp | 4,035.4 | 2,395.8 | 5.23 | 3.11 |
| post_bf_safe_naive | 771 | 65.9% | 41.0% | -24.9pp | 2,520.7 | 2,395.8 | 3.27 | 3.11 |
| median_naive | 771 | 69.3% | 41.0% | -28.3pp | 2,711.1 | 2,395.8 | 3.52 | 3.11 |

## Export Metadata

- Revenue-rank limit: Top 1000.
- Champion model: `8gf_regular_plus_post_bf_safe`.
- Champion prediction source: `v2_high_revenue_policy`.
- Champion model version: `high_revenue_policy_v1_2026_05_24`.
- Official score-row CSV: `/Users/fyodorgolovin/Downloads/Supply-Inventory v1.0 codex/active_docs/ITER5X_V2_PHASE8G_OFFICIAL_POLICY_SCORE_ROWS.csv`.
- Default-policy skipped windows: `2024-04-29`, `2024-05-27`, `2024-07-01`, `2024-07-29`.
- Champion-policy skipped windows: `2024-04-29`, `2024-05-27`, `2024-07-01`, `2024-07-29`.
- The default v2 sklearn path remains `--high-revenue-policy none`.
- The champion path requires `--high-revenue-policy champion --revenue-rank-limit 1000`.
- This is confirmatory rolling backtest validation on the known Phase 8G target windows, not independent future holdout validation.
- This report uses row-level output from `backend/forecast_engine_v2/sklearn_direct_model.py`, not the cached research runners.
