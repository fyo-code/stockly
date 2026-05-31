# Iteration 5E — V2 Routed Audit

Generated: 2026-05-17 14:02
Route version: `v2_routes_2026_05_17`

## Phase Checkpoint

Phase completed: Phase 7A — Routed Audit

What changed: added forecast-time route labels and sliced the existing Phase 6 model performance by route.

Accuracy rerun: no new model behavior. Phase 6 predictions were rebuilt in memory only to attach route labels.

| Metric | Phase 6 baseline | Phase 7A routed audit reproduction |
| --- | --- | --- |
| Best model | sk_blend_post_bf_safe | sk_blend_post_bf_safe |
| Hit +/-20 | 24.1% | 24.1% |
| Hit +/-30 | 35.3% | 35.3% |
| WMAPE | 56.1% | 56.1% |
| Phantom rate | 48.1% | 48.1% |

## Model Reproduction Check

| Model | Rows | Qty scored | Hit +/-20 | Hit +/-30 | WMAPE | Bias | Phantom rate |
| --- | --- | --- | --- | --- | --- | --- | --- |
| sk_blend_post_bf_safe | 21,045 | 10,275 | 24.1% | 35.3% | 56.1% | -12.5% | 48.1% |
| median_naive | 21,045 | 10,275 | 19.8% | 30.1% | 57.4% | -23.2% | 69.9% |
| post_bf_safe_naive | 21,045 | 10,275 | 20.1% | 30.1% | 56.0% | -27.6% | 65.8% |
| sk_blend_median | 21,045 | 10,275 | 23.8% | 34.9% | 57.7% | -10.5% | 48.2% |
| sk_extra_trees | 21,045 | 10,275 | 23.9% | 35.7% | 58.9% | -5.5% | 46.6% |
| sk_hgb_poisson | 21,045 | 10,275 | 23.2% | 34.1% | 63.6% | -3.9% | 44.3% |
| sk_hgb_squared | 21,045 | 10,275 | 23.1% | 34.8% | 66.5% | 3.1% | 53.0% |

## Route Accuracy

| Route | Rows | Qty scored | Revenue share all rows | Scored actual units | Hit +/-20 | Hit +/-30 | WMAPE | Bias | Phantom rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| stock_constrained | 53 | 19 | 0.1% | 171.0 | 10.5% | 21.1% | 57.6% | -19.8% | 34.8% |
| bf_campaign_sensitive | 9,947 | 4,948 | 52.7% | 83,703.1 | 21.4% | 31.9% | 61.9% | -14.6% | 56.2% |
| seasonal_active | 47 | 12 | 0.1% | 91.0 | 33.3% | 33.3% | 72.3% | -37.0% | 38.1% |
| seasonal_quiet | 4 | 0 | 0.0% | 0.0 | - | - | - | - | 0.0% |
| sparse_intermittent | 5,380 | 1,630 | 14.6% | 15,364.8 | 19.8% | 29.4% | 60.1% | -42.7% | 32.8% |
| lifecycle_decline | 267 | 133 | 0.8% | 2,367.0 | 25.6% | 35.3% | 65.3% | 1.9% | 75.5% |
| available_regular | 77 | 43 | 0.1% | 344.0 | 37.2% | 53.5% | 29.9% | -10.3% | 78.6% |
| proxy_available_regular | 5,268 | 3,490 | 31.5% | 59,955.6 | 29.7% | 42.7% | 46.7% | -2.4% | 64.7% |
| availability_unknown | 2 | 0 | 0.0% | 0.0 | - | - | - | - | 100.0% |

## Availability Accuracy

| Availability | Rows | Qty scored | Revenue share all rows | Scored actual units | Hit +/-20 | Hit +/-30 | WMAPE | Bias | Phantom rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| availability_unknown | 9 | 0 | 0.0% | 0.0 | - | - | - | - | 11.1% |
| observed_available | 443 | 171 | 0.9% | 1,240.0 | 26.3% | 38.6% | 46.0% | -25.4% | 60.7% |
| observed_constrained | 53 | 19 | 0.1% | 171.0 | 10.5% | 21.1% | 57.6% | -19.8% | 34.8% |
| observed_unclear | 17 | 7 | 0.0% | 47.0 | 28.6% | 57.1% | 33.6% | -29.4% | 60.0% |
| proxy_available | 11,360 | 7,184 | 71.3% | 130,705.5 | 26.3% | 38.2% | 54.6% | -5.7% | 68.2% |
| stock_unobserved | 9,163 | 2,894 | 27.6% | 29,833.0 | 18.6% | 28.0% | 63.0% | -41.4% | 39.4% |

## Intermittency Accuracy

| Intermittency | Rows | Qty scored | Revenue share all rows | Scored actual units | Hit +/-20 | Hit +/-30 | WMAPE | Bias | Phantom rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| moderately_intermittent | 8,578 | 4,828 | 45.3% | 66,988.6 | 25.9% | 37.9% | 56.7% | -11.6% | 66.7% |
| regular | 2,982 | 2,461 | 26.4% | 64,543.9 | 27.4% | 39.0% | 52.3% | 0.3% | 92.0% |
| sparse_intermittent | 9,485 | 2,986 | 28.3% | 30,464.0 | 18.6% | 28.0% | 62.9% | -41.6% | 39.5% |

## Route Window Details

| Target start | Route | Qty scored | Hit +/-20 | WMAPE | Bias |
| --- | --- | --- | --- | --- | --- |
| 2024-08-26 | lifecycle_decline | 32 | 31.2% | 63.7% | -5.0% |
| 2024-08-26 | proxy_available_regular | 873 | 28.3% | 43.2% | -17.5% |
| 2024-08-26 | sparse_intermittent | 509 | 17.7% | 64.1% | -48.7% |
| 2024-09-23 | proxy_available_regular | 879 | 31.3% | 45.6% | 2.5% |
| 2024-09-23 | sparse_intermittent | 448 | 24.1% | 54.0% | -28.8% |
| 2024-10-28 | bf_campaign_sensitive | 1,854 | 20.3% | 51.7% | -43.1% |
| 2024-11-25 | bf_campaign_sensitive | 982 | 17.0% | 88.1% | 34.7% |
| 2024-12-30 | bf_campaign_sensitive | 983 | 23.0% | 69.5% | 14.4% |
| 2024-12-30 | proxy_available_regular | 60 | 20.0% | 94.9% | 74.3% |
| 2025-01-27 | bf_campaign_sensitive | 1,129 | 25.7% | 52.7% | -19.0% |
| 2025-01-27 | proxy_available_regular | 55 | 29.1% | 60.5% | 29.4% |
| 2025-01-27 | sparse_intermittent | 33 | 24.2% | 48.4% | -42.8% |
| 2025-02-24 | lifecycle_decline | 30 | 23.3% | 72.4% | 48.5% |
| 2025-02-24 | proxy_available_regular | 791 | 29.7% | 47.8% | -1.6% |
| 2025-02-24 | sparse_intermittent | 293 | 18.8% | 66.7% | -50.6% |
| 2025-03-24 | lifecycle_decline | 37 | 27.0% | 50.1% | -36.3% |
| 2025-03-24 | proxy_available_regular | 832 | 30.4% | 42.9% | -5.5% |
| 2025-03-24 | sparse_intermittent | 320 | 17.8% | 55.6% | -43.9% |

## Decision Gate

| Slice | Hit +/-20 | WMAPE | Phantom rate |
| --- | --- | --- | --- |
| available + proxy available | 29.8% | 46.6% | 65.1% |
| BF/campaign sensitive | 21.4% | 61.9% | 56.2% |
| stock constrained | 10.5% | 57.6% | 34.8% |

Available-mover hit +/-20 is below 35%, so Phase 7B should improve the regular/proxy-available model path, not only stock/BF handling.

## Skipped Windows

`2024-04-29`, `2024-05-27`, `2024-07-01`, `2024-07-29`

## Notes

- Matrix rows routed: 30,891.
- Route labels use only pre-target features from the existing feature matrix.
- Current snapshot stock remains excluded from historical backtests.
- Route accuracy is shown for the current Phase 6 best model unless stated otherwise.
