# Iteration 5F — V2 Routed Model Candidates

Generated: 2026-05-18 17:03
Route version: `v2_routes_2026_05_17`

## Phase Checkpoint

Phase completed: Phase 7B — Routed model candidates

What changed: added route-specific candidate predictions on top of the Phase 6 global model.

Accuracy rerun: yes. The same walk-forward windows were rebuilt with new routed candidates.

| Metric | Phase 6 control | Phase 7B best |
| --- | --- | --- |
| Best model | sk_blend_post_bf_safe | sk_blend_post_bf_safe |
| Hit +/-20 | 24.1% | 24.1% |
| Delta hit +/-20 | - | +0.0pp |
| Hit +/-30 | 35.3% | 35.3% |
| WMAPE | 56.1% | 56.1% |
| Phantom rate | 48.1% | 48.1% |

## Aggregate Candidate Results

| Model | Rows | Qty scored | Hit +/-20 | Delta vs Phase 6 | Hit +/-30 | WMAPE | Bias | Phantom rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| sk_blend_post_bf_safe | 21,045 | 10,275 | 24.1% | +0.0pp | 35.3% | 56.1% | -12.5% | 48.1% |
| route_regular_specialist_blend | 21,045 | 10,275 | 24.1% | -0.0pp | 35.5% | 55.6% | -14.5% | 48.2% |
| sk_extra_trees | 21,045 | 10,275 | 23.9% | -0.2pp | 35.7% | 58.9% | -5.5% | 46.6% |
| sk_blend_median | 21,045 | 10,275 | 23.8% | -0.3pp | 34.9% | 57.7% | -10.5% | 48.2% |
| route_regular_extra_trees | 21,045 | 10,275 | 23.8% | -0.3pp | 35.5% | 55.9% | -14.8% | 47.3% |
| sk_hgb_poisson | 21,045 | 10,275 | 23.2% | -0.9pp | 34.1% | 63.6% | -3.9% | 44.3% |
| route_prior_best_model | 21,045 | 10,275 | 23.2% | -0.9pp | 34.3% | 62.4% | -3.9% | 46.9% |
| sk_hgb_squared | 21,045 | 10,275 | 23.1% | -1.0pp | 34.8% | 66.5% | 3.1% | 53.0% |
| route_prior_bias_calibrated | 21,045 | 10,275 | 23.0% | -1.1pp | 34.1% | 61.5% | -1.3% | 48.3% |
| post_bf_safe_naive | 21,045 | 10,275 | 20.1% | -4.0pp | 30.1% | 56.0% | -27.6% | 65.8% |
| median_naive | 21,045 | 10,275 | 19.8% | -4.3pp | 30.1% | 57.4% | -23.2% | 69.9% |

## Available / Proxy-Regular Slice

| Metric | Phase 6 control | Phase 7B best |
| --- | --- | --- |
| Qty scored | 3,533 | 3,533 |
| Hit +/-20 | 29.8% | 29.8% |
| Delta hit +/-20 | - | +0.0pp |
| Hit +/-30 | 42.9% | 42.9% |
| WMAPE | 46.6% | 46.6% |
| Phantom rate | 65.1% | 65.1% |

## Route Accuracy — sk_blend_post_bf_safe

| Route | Rows | Qty scored | Hit +/-20 | Hit +/-30 | WMAPE | Bias | Phantom rate |
| --- | --- | --- | --- | --- | --- | --- | --- |
| stock_constrained | 53 | 19 | 10.5% | 21.1% | 57.6% | -19.8% | 34.8% |
| bf_campaign_sensitive | 9,947 | 4,948 | 21.4% | 31.9% | 61.9% | -14.6% | 56.2% |
| seasonal_active | 47 | 12 | 33.3% | 33.3% | 72.3% | -37.0% | 38.1% |
| seasonal_quiet | 4 | 0 | - | - | - | - | 0.0% |
| sparse_intermittent | 5,380 | 1,630 | 19.8% | 29.4% | 60.1% | -42.7% | 32.8% |
| lifecycle_decline | 267 | 133 | 25.6% | 35.3% | 65.3% | 1.9% | 75.5% |
| available_regular | 77 | 43 | 37.2% | 53.5% | 29.9% | -10.3% | 78.6% |
| proxy_available_regular | 5,268 | 3,490 | 29.7% | 42.7% | 46.7% | -2.4% | 64.7% |
| availability_unknown | 2 | 0 | - | - | - | - | 100.0% |

## Window Accuracy — sk_blend_post_bf_safe

| Target start | Qty scored | Hit +/-20 | Hit +/-30 | WMAPE | Bias | Phantom rate |
| --- | --- | --- | --- | --- | --- | --- |
| 2024-08-26 | 1,424 | 24.6% | 37.9% | 48.5% | -24.0% | 40.0% |
| 2024-09-23 | 1,367 | 28.5% | 40.7% | 47.7% | -4.9% | 56.6% |
| 2024-10-28 | 1,858 | 20.3% | 30.6% | 51.7% | -43.2% | 42.9% |
| 2024-11-25 | 989 | 17.0% | 23.3% | 87.9% | 34.4% | 76.3% |
| 2024-12-30 | 1,078 | 22.8% | 34.0% | 72.8% | 21.1% | 37.3% |
| 2025-01-27 | 1,231 | 25.7% | 39.0% | 53.9% | -13.9% | 35.9% |
| 2025-02-24 | 1,123 | 26.9% | 37.3% | 52.2% | -10.0% | 46.3% |
| 2025-03-24 | 1,205 | 27.1% | 38.7% | 45.2% | -13.1% | 39.5% |

## Online Routing Diagnostics

| Target start | Train windows | Eval rows | Prior route model choices | Prior route bias factors |
| --- | --- | --- | --- | --- |
| 2024-08-26 | 4 | 2,602 | - | - |
| 2024-09-23 | 5 | 2,623 | proxy_available_regular:sk_extra_trees, sparse_intermittent:sk_extra_trees | proxy_available_regular:1.21, sparse_intermittent:1.30 |
| 2024-10-28 | 6 | 2,630 | proxy_available_regular:sk_blend_post_bf_safe, sparse_intermittent:sk_extra_trees | proxy_available_regular:1.08, sparse_intermittent:1.30 |
| 2024-11-25 | 7 | 2,692 | bf_campaign_sensitive:sk_hgb_poisson, proxy_available_regular:sk_blend_post_bf_safe, sparse_intermittent:sk_extra_trees | bf_campaign_sensitive:1.30, proxy_available_regular:1.08, sparse_intermittent:1.30 |
| 2024-12-30 | 8 | 2,659 | bf_campaign_sensitive:sk_blend_post_bf_safe, proxy_available_regular:sk_blend_post_bf_safe, sparse_intermittent:sk_extra_trees | bf_campaign_sensitive:1.24, proxy_available_regular:1.08, sparse_intermittent:1.30 |
| 2025-01-27 | 9 | 2,638 | bf_campaign_sensitive:sk_blend_post_bf_safe, lifecycle_decline:sk_hgb_poisson, proxy_available_regular:sk_blend_post_bf_safe, sparse_intermittent:sk_extra_trees | bf_campaign_sensitive:1.16, lifecycle_decline:1.22, proxy_available_regular:1.03, sparse_intermittent:1.30 |
| 2025-02-24 | 10 | 2,605 | bf_campaign_sensitive:sk_blend_post_bf_safe, lifecycle_decline:sk_hgb_poisson, proxy_available_regular:sk_blend_post_bf_safe, sparse_intermittent:sk_extra_trees | bf_campaign_sensitive:1.17, lifecycle_decline:0.98, proxy_available_regular:1.01, sparse_intermittent:1.30 |
| 2025-03-24 | 11 | 2,596 | bf_campaign_sensitive:sk_blend_post_bf_safe, lifecycle_decline:sk_hgb_poisson, proxy_available_regular:sk_blend_post_bf_safe, sparse_intermittent:sk_extra_trees | bf_campaign_sensitive:1.17, lifecycle_decline:0.88, proxy_available_regular:1.01, sparse_intermittent:1.30 |

## Verdict

Phase 7B did not improve headline hit +/-20. Keep the diagnostics, but do not promote the routed candidate.

## Skipped Windows

`2024-04-29`, `2024-05-27`, `2024-07-01`, `2024-07-29`

## Notes

- Matrix rows routed: 30,891.
- Specialist routes use only rows whose route label is known before the target window.
- `route_prior_best_model` chooses route/model mappings only from earlier scored target windows.
- `route_prior_bias_calibrated` learns route correction factors only from earlier scored target windows.
- Current snapshot stock remains excluded from historical backtests.
