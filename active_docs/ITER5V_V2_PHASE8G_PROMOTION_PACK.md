# Iteration 5V - Forecast V2 Phase 8G-G Promotion Pack

Generated: 2026-05-24 16:40
Route version: `v2_routes_2026_05_21_availability`

## Decision

Decision: `PROMOTE_HIGH_REVENUE_CHAMPION_WITH_MONITORS`.

Promote `8gf_regular_plus_post_bf_safe` as the current high-revenue Top 1000 champion candidate, and wire it into the main v2 scoring/export path behind an explicit high-revenue policy flag. The decision accepts the monitoring caveats listed below instead of pretending they are clean passes.

| Metric | Safer control | Champion | Delta |
| --- | --- | --- | --- |
| Model | sk_blend_post_bf_safe | 8gf_regular_plus_post_bf_safe | - |
| Hit +/-20 | 23.4% | 25.3% | +2.0pp |
| Hit +/-30 | 34.8% | 36.5% | +1.7pp |
| WMAPE | 55.7% | 51.0% | -4.7pp |
| Bias | -17.0% | -21.3% | -4.3pp |
| Phantom rate | 43.5% | 41.0% | -2.5pp |

## Promotion Gates And Monitoring

| Kind | Status | Gate | Observed | Note |
| --- | --- | --- | --- | --- |
| BLOCKING | PASS | Top 1000 hit +/-20 improves by at least +1.5pp vs safer control | +2.0pp | Primary high-revenue promotion gate. |
| BLOCKING | PASS | Top 1000 WMAPE does not worsen by more than +0.5pp | -4.7pp | Candidate improves WMAPE materially. |
| BLOCKING | PASS | Top 1000 phantom rate does not worsen by more than +0.5pp | -2.5pp | Candidate improves phantom rate materially. |
| BLOCKING | PASS | Champion beats both 8G-D and 8G-E components on hit +/-20 | 25.3% | Prevents promoting a non-stacked composition. |
| BLOCKING | PASS | Top 500 revenue scope does not regress | +2.3pp | Most useful commercial scope improved. |
| BLOCKING | PASS | Top 100 revenue scope does not regress on hit +/-20 | +1.1pp | Top 100 gain is modest; WMAPE still improves strongly. |
| BLOCKING | PASS | 2024-11-25 BF/post-BF stress window remains protected | -68.8pp | This was the main catastrophic BF failure window. |
| MONITORING | MONITOR | Available/proxy regular phantom rate | +1.3pp | Accepted caveat: regular quantity accuracy improves, but phantom nudges upward on this slice. |
| MONITORING | MONITOR | Largest non-stress window WMAPE regression | +1.8pp | Diagnostic caveat only; promotion is driven by aggregate high-revenue gates and named BF stress protection. |

## Baseline Robustness

| Baseline | Baseline hit +/-20 | Champion hit +/-20 | Hit delta | Baseline hit +/-30 | Champion hit +/-30 | Hit30 delta | Baseline WMAPE | Champion WMAPE | WMAPE delta | Baseline phantom | Champion phantom | Phantom delta | Baseline bias | Champion bias |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| sk_blend_post_bf_safe | 23.4% | 25.3% | +2.0pp | 34.8% | 36.5% | +1.7pp | 55.7% | 51.0% | -4.7pp | 43.5% | 41.0% | -2.5pp | -17.0% | -21.3% |
| 8gd_regular_global_extra | 24.4% | 25.3% | +0.9pp | 35.5% | 36.5% | +1.0pp | 55.6% | 51.0% | -4.6pp | 43.6% | 41.0% | -2.6pp | -15.0% | -21.3% |
| 8ge_post_bf_hard_safe | 24.3% | 25.3% | +1.0pp | 35.9% | 36.5% | +0.6pp | 51.1% | 51.0% | -0.1pp | 40.9% | 41.0% | +0.1pp | -23.2% | -21.3% |
| sk_extra_trees | 25.3% | 25.3% | +0.0pp | 36.0% | 36.5% | +0.5pp | 57.0% | 51.0% | -6.0pp | 45.7% | 41.0% | -4.7pp | -10.4% | -21.3% |
| sk_hgb_squared | 25.3% | 25.3% | -0.0pp | 37.4% | 36.5% | -0.9pp | 62.6% | 51.0% | -11.6pp | 57.8% | 41.0% | -16.9pp | -8.3% | -21.3% |
| post_bf_safe_naive | 22.2% | 25.3% | +3.1pp | 32.9% | 36.5% | +3.6pp | 52.9% | 51.0% | -1.9pp | 65.9% | 41.0% | -24.9pp | -24.8% | -21.3% |
| median_naive | 21.4% | 25.3% | +3.9pp | 32.2% | 36.5% | +4.3pp | 57.3% | 51.0% | -6.3pp | 69.3% | 41.0% | -28.3pp | -18.9% | -21.3% |

## Revenue Scope Robustness

| Scope | Rows | Qty scored | Actual revenue | Control hit +/-20 | Champion hit +/-20 | Hit delta | Control WMAPE | Champion WMAPE | WMAPE delta | Control phantom | Champion phantom | Phantom delta |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Top 100 | 475 | 349 | 19,774,645 | 26.6% | 27.8% | +1.1pp | 48.6% | 43.0% | -5.7pp | 62.1% | 62.1% | +0.0pp |
| Top 250 | 1,373 | 943 | 39,557,500 | 24.2% | 27.4% | +3.2pp | 53.5% | 46.6% | -6.9pp | 58.8% | 55.7% | -3.1pp |
| Top 500 | 2,866 | 1,751 | 59,034,164 | 23.2% | 25.5% | +2.3pp | 55.3% | 49.9% | -5.4pp | 49.3% | 46.7% | -2.6pp |
| Top 750 | 4,140 | 2,384 | 70,548,177 | 23.3% | 25.4% | +2.1pp | 55.7% | 50.5% | -5.1pp | 45.2% | 42.3% | -2.8pp |
| Top 1000 | 5,346 | 2,967 | 79,136,333 | 23.4% | 25.3% | +2.0pp | 55.7% | 51.0% | -4.7pp | 43.5% | 41.0% | -2.5pp |

## Route Robustness

| Route | Rows | Qty scored | Control hit +/-20 | Champion hit +/-20 | Hit delta | Control WMAPE | Champion WMAPE | WMAPE delta | Control bias | Champion bias | Control phantom | Champion phantom | Phantom delta |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| stock_constrained | 886 | 492 | 25.8% | 26.8% | +1.0pp | 50.7% | 44.5% | -6.2pp | -8.0% | -16.5% | 47.1% | 44.9% | -2.2pp |
| bf_campaign_sensitive | 2,134 | 1,184 | 16.6% | 18.6% | +1.9pp | 65.4% | 57.4% | -7.9pp | -20.2% | -31.2% | 51.6% | 46.2% | -5.4pp |
| seasonal_active | 9 | 4 | 0.0% | 0.0% | +0.0pp | 78.9% | 78.9% | +0.0pp | -56.2% | -56.2% | 50.0% | 50.0% | +0.0pp |
| seasonal_quiet | 1 | 0 | - | - | - | - | - | - | - | - | - | - | - |
| sparse_intermittent | 738 | 215 | 17.7% | 17.7% | +0.0pp | 66.1% | 66.1% | +0.0pp | -49.9% | -49.9% | 20.8% | 20.8% | +0.0pp |
| lifecycle_decline | 49 | 23 | 52.2% | 52.2% | +0.0pp | 47.0% | 47.0% | +0.0pp | -20.6% | -20.6% | 75.0% | 75.0% | +0.0pp |
| available_regular | 986 | 703 | 32.4% | 35.1% | +2.7pp | 41.5% | 41.1% | -0.4pp | -9.5% | -3.7% | 84.6% | 87.2% | +2.6pp |
| proxy_available_regular | 476 | 323 | 25.4% | 28.8% | +3.4pp | 47.9% | 47.9% | -0.0pp | -17.5% | -11.8% | 48.6% | 48.6% | +0.0pp |
| availability_unknown | 67 | 23 | 39.1% | 39.1% | +0.0pp | 38.7% | 38.7% | +0.0pp | -9.4% | -9.4% | 32.1% | 32.1% | +0.0pp |

## Window Robustness

| Target start | Qty scored | Control hit +/-20 | Champion hit +/-20 | Hit delta | Control WMAPE | Champion WMAPE | WMAPE delta | Control bias | Champion bias | Control phantom | Champion phantom |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2024-08-26 | 427 | 25.3% | 27.9% | +2.6pp | 47.5% | 46.2% | -1.3pp | -29.3% | -26.9% | 31.1% | 31.1% |
| 2024-09-23 | 428 | 34.1% | 35.7% | +1.6pp | 46.0% | 45.8% | -0.3pp | -0.6% | 4.5% | 49.5% | 49.5% |
| 2024-10-28 | 546 | 15.8% | 15.8% | +0.0pp | 54.9% | 54.9% | +0.0pp | -50.8% | -50.8% | 31.3% | 31.3% |
| 2024-11-25 | 253 | 6.7% | 17.8% | +11.1pp | 139.8% | 70.9% | -68.8pp | 133.0% | 38.0% | 70.7% | 57.1% |
| 2024-12-30 | 315 | 21.0% | 21.3% | +0.3pp | 58.5% | 58.3% | -0.1pp | -9.3% | -9.0% | 37.2% | 38.1% |
| 2025-01-27 | 352 | 24.1% | 24.1% | +0.0pp | 49.3% | 49.4% | +0.1pp | -22.0% | -21.8% | 30.1% | 30.1% |
| 2025-02-24 | 318 | 29.2% | 32.4% | +3.1pp | 43.8% | 43.2% | -0.6pp | -22.9% | -17.0% | 37.2% | 37.2% |
| 2025-03-24 | 328 | 28.0% | 28.4% | +0.3pp | 40.3% | 42.1% | +1.8pp | -8.7% | -4.4% | 42.1% | 42.1% |

## Zero-Actual / Phantom Robustness

| Baseline | Zero-actual rows | Baseline phantom | Champion phantom | Phantom delta | Baseline pred-sale rate | Champion pred-sale rate | Baseline pred units on zero actual | Champion pred units on zero actual | Baseline avg pred units | Champion avg pred units |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| sk_blend_post_bf_safe | 771 | 43.5% | 41.0% | -2.5pp | 43.5% | 41.0% | 2,669.9 | 2,395.8 | 3.46 | 3.11 |
| 8gd_regular_global_extra | 771 | 43.6% | 41.0% | -2.6pp | 43.6% | 41.0% | 2,735.7 | 2,395.8 | 3.55 | 3.11 |
| 8ge_post_bf_hard_safe | 771 | 40.9% | 41.0% | +0.1pp | 40.9% | 41.0% | 2,330.0 | 2,395.8 | 3.02 | 3.11 |
| sk_extra_trees | 771 | 45.7% | 41.0% | -4.7pp | 45.7% | 41.0% | 3,569.3 | 2,395.8 | 4.63 | 3.11 |
| sk_hgb_squared | 771 | 57.8% | 41.0% | -16.9pp | 57.8% | 41.0% | 4,035.4 | 2,395.8 | 5.23 | 3.11 |

## Skipped Windows

`2024-04-29`, `2024-05-27`, `2024-07-01`, `2024-07-29`

## Notes

- Revenue-rank limit: Top 1000. Primary promotion gate scope: Top 1000.
- Feature matrix rows: 8,227.
- Feature matrix cache: `/Users/fyodorgolovin/Downloads/Supply-Inventory v1.0 codex/backend/data/forecast_v2_feature_cache/feature_matrix_headline_top1000_aa54e4e2fe0a.pkl` (hit; refresh requested: no).
- This promotion is high-revenue scoped. It is not a full-headline or low-volume SKU promotion.
- Candidate training still uses only earlier target windows.
- Route/campaign/BF gates are forecast-time-safe.
- Known caveat: the champion improves WMAPE and phantom overall, but it is more underpredictive than the safer control.
- Known caveat: available/proxy regular quantity hit improves, but regular-slice phantom rate nudges up slightly. This is accepted as a monitoring item, not a blocking promotion gate.
- Known caveat: one non-stress window has a small WMAPE regression. Window robustness is diagnostic except for the named 2024-11-25 BF/post-BF stress gate.
- Phase 8F current snapshots remain excluded from historical backtests.
