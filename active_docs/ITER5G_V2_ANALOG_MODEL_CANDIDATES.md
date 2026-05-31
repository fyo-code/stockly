# Iteration 5G — V2 Analog Model Candidates

Generated: 2026-05-18 19:38
Route version: `v2_routes_2026_05_17`

## Phase Checkpoint

Phase completed: Phase 7C — Analog/neighbor candidates

What changed: tested local-neighbor predictions for available/proxy-regular movers.

Accuracy rerun: yes. Analog candidates used `35` nearest prior SKU-window neighbors.

| Metric | Phase 6 control | Phase 7C best |
| --- | --- | --- |
| Best model | sk_blend_post_bf_safe | sk_blend_post_bf_safe |
| Hit +/-20 | 24.1% | 24.1% |
| Delta hit +/-20 | - | +0.0pp |
| Hit +/-30 | 35.3% | 35.3% |
| WMAPE | 56.1% | 56.1% |
| Phantom rate | 48.1% | 48.1% |

## Aggregate Candidate Results

| Model | Rows | Qty scored | Hit +/-20 | Delta vs control | Hit +/-30 | WMAPE | Bias | Phantom rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| sk_blend_post_bf_safe | 21,045 | 10,275 | 24.1% | +0.0pp | 35.3% | 56.1% | -12.5% | 48.1% |
| sk_extra_trees | 21,045 | 10,275 | 23.9% | -0.2pp | 35.7% | 58.9% | -5.5% | 46.6% |
| sk_blend_median | 21,045 | 10,275 | 23.8% | -0.3pp | 34.9% | 57.7% | -10.5% | 48.2% |
| sk_hgb_poisson | 21,045 | 10,275 | 23.2% | -0.9pp | 34.1% | 63.6% | -3.9% | 44.3% |
| sk_hgb_squared | 21,045 | 10,275 | 23.1% | -1.0pp | 34.8% | 66.5% | 3.1% | 53.0% |
| analog_regular_blend | 21,045 | 10,275 | 22.4% | -1.7pp | 33.6% | 56.7% | -20.8% | 49.8% |
| analog_regular_residual | 21,045 | 10,275 | 22.2% | -1.9pp | 33.2% | 57.2% | -20.4% | 49.1% |
| analog_regular_ratio | 21,045 | 10,275 | 22.1% | -2.0pp | 32.7% | 57.3% | -21.9% | 50.4% |
| analog_regular_units | 21,045 | 10,275 | 21.8% | -2.3pp | 32.6% | 60.1% | -29.0% | 51.4% |
| post_bf_safe_naive | 21,045 | 10,275 | 20.1% | -4.0pp | 30.1% | 56.0% | -27.6% | 65.8% |
| median_naive | 21,045 | 10,275 | 19.8% | -4.3pp | 30.1% | 57.4% | -23.2% | 69.9% |

## Available / Proxy-Regular Slice

| Metric | Phase 6 control | Phase 7C best |
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

## Analog Source Diagnostics

| Target start | Train windows | Eval rows | Regular eval rows | Analog source counts |
| --- | --- | --- | --- | --- |
| 2024-08-26 | 4 | 2,602 | 1,204 | category:659, product_family:529, regular_global:16 |
| 2024-09-23 | 5 | 2,623 | 1,238 | category:606, product_family:614, regular_global:18 |
| 2024-10-28 | 6 | 2,630 | 0 | - |
| 2024-11-25 | 7 | 2,692 | 0 | - |
| 2024-12-30 | 8 | 2,659 | 115 | category:45, product_family:70 |
| 2025-01-27 | 9 | 2,638 | 96 | category:41, product_family:55 |
| 2025-02-24 | 10 | 2,605 | 1,344 | category:650, product_family:693, regular_global:1 |
| 2025-03-24 | 11 | 2,596 | 1,348 | category:575, product_family:772, regular_global:1 |

## Verdict

Phase 7C did not beat the Phase 6 control on hit +/-20. Do not promote the analog candidate.

## Skipped Windows

`2024-04-29`, `2024-05-27`, `2024-07-01`, `2024-07-29`

## Notes

- Matrix rows routed: 30,891.
- Neighbor pools use only earlier target windows.
- Analog replacement is limited to `available_regular` and `proxy_available_regular` routes.
- Current snapshot stock remains excluded from historical backtests.
