# Iteration 5H — V2 Error Decomposition And Oracle Ceiling

Generated: 2026-05-19 23:17
Route version: `v2_routes_2026_05_17`

## Phase Checkpoint

Phase completed: Phase 7D — Error decomposition / oracle ceiling

What changed: no production model behavior changed. This phase measures where the current control fails and how high accuracy could go if we could perfectly choose among already-tested candidates.

Accuracy rerun: yes. Rebuilt the Phase 7C measurement set using `35` analog neighbors, then added oracle rows in memory.

| Metric | Current control | Oracle all tested | Oracle gap |
| --- | --- | --- | --- |
| Model | sk_blend_post_bf_safe | oracle_all_tested | - |
| Hit +/-20 | 24.1% | 47.0% | +22.9pp |
| Hit +/-30 | 35.3% | 58.6% | - |
| WMAPE | 56.1% | 35.9% | - |
| Phantom rate | 48.1% | 34.7% | - |

## Model And Oracle Ceiling

| Model | Rows | Qty scored | Hit +/-20 | Delta vs control | Hit +/-30 | WMAPE | Bias | Phantom rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| median_naive | 21,045 | 10,275 | 19.8% | -4.3pp | 30.1% | 57.4% | -23.2% | 69.9% |
| post_bf_safe_naive | 21,045 | 10,275 | 20.1% | -4.0pp | 30.1% | 56.0% | -27.6% | 65.8% |
| sk_hgb_poisson | 21,045 | 10,275 | 23.2% | -0.9pp | 34.1% | 63.6% | -3.9% | 44.3% |
| sk_hgb_squared | 21,045 | 10,275 | 23.1% | -1.0pp | 34.8% | 66.5% | 3.1% | 53.0% |
| sk_extra_trees | 21,045 | 10,275 | 23.9% | -0.2pp | 35.7% | 58.9% | -5.5% | 46.6% |
| sk_blend_median | 21,045 | 10,275 | 23.8% | -0.3pp | 34.9% | 57.7% | -10.5% | 48.2% |
| sk_blend_post_bf_safe | 21,045 | 10,275 | 24.1% | +0.0pp | 35.3% | 56.1% | -12.5% | 48.1% |
| analog_regular_units | 21,045 | 10,275 | 21.8% | -2.3pp | 32.6% | 60.1% | -29.0% | 51.4% |
| analog_regular_ratio | 21,045 | 10,275 | 22.1% | -2.0pp | 32.7% | 57.3% | -21.9% | 50.4% |
| analog_regular_residual | 21,045 | 10,275 | 22.2% | -1.9pp | 33.2% | 57.2% | -20.4% | 49.1% |
| analog_regular_blend | 21,045 | 10,275 | 22.4% | -1.7pp | 33.6% | 56.7% | -20.8% | 49.8% |
| oracle_base_models | 21,045 | 10,275 | 43.1% | +19.0pp | 55.0% | 38.6% | -16.0% | 34.8% |
| oracle_all_tested | 21,045 | 10,275 | 47.0% | +22.9pp | 58.6% | 35.9% | -18.8% | 34.7% |

## Error By Route

| Route | Rows | Qty scored | Revenue share | Actual units | Hit +/-20 | Hit +/-30 | WMAPE | Bias | Phantom rate | Abs error share |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| stock_constrained | 53 | 19 | 0.1% | 171.0 | 10.5% | 21.1% | 57.6% | -19.8% | 34.8% | 0.1% |
| bf_campaign_sensitive | 9,947 | 4,948 | 52.7% | 83,703.1 | 21.4% | 31.9% | 61.9% | -14.6% | 56.2% | 57.0% |
| seasonal_active | 47 | 12 | 0.1% | 91.0 | 33.3% | 33.3% | 72.3% | -37.0% | 38.1% | 0.1% |
| seasonal_quiet | 4 | 0 | 0.0% | 0.0 | - | - | - | - | 0.0% | 0.0% |
| sparse_intermittent | 5,380 | 1,630 | 14.6% | 15,364.8 | 19.8% | 29.4% | 60.1% | -42.7% | 32.8% | 10.2% |
| lifecycle_decline | 267 | 133 | 0.8% | 2,367.0 | 25.6% | 35.3% | 65.3% | 1.9% | 75.5% | 1.7% |
| available_regular | 77 | 43 | 0.1% | 344.0 | 37.2% | 53.5% | 29.9% | -10.3% | 78.6% | 0.1% |
| proxy_available_regular | 5,268 | 3,490 | 31.5% | 59,955.6 | 29.7% | 42.7% | 46.7% | -2.4% | 64.7% | 30.8% |
| availability_unknown | 2 | 0 | 0.0% | 0.0 | - | - | - | - | 100.0% | 0.0% |

## Oracle Gain By Route

| Route | Qty scored | Control hit +/-20 | Oracle hit +/-20 | Delta | Control WMAPE | Oracle WMAPE |
| --- | --- | --- | --- | --- | --- | --- |
| stock_constrained | 19 | 10.5% | 47.4% | +36.8pp | 57.6% | 32.2% |
| bf_campaign_sensitive | 4,948 | 21.4% | 39.2% | +17.8pp | 61.9% | 42.6% |
| seasonal_active | 12 | 33.3% | 33.3% | +0.0pp | 72.3% | 59.3% |
| seasonal_quiet | 0 | - | - | - | - | - |
| sparse_intermittent | 1,630 | 19.8% | 36.3% | +16.5pp | 60.1% | 45.5% |
| lifecycle_decline | 133 | 25.6% | 47.4% | +21.8pp | 65.3% | 39.7% |
| available_regular | 43 | 37.2% | 69.8% | +32.6pp | 29.9% | 13.7% |
| proxy_available_regular | 3,490 | 29.7% | 62.9% | +33.1pp | 46.7% | 24.0% |
| availability_unknown | 0 | - | - | - | - | - |

## Error By Availability

| Availability | Rows | Qty scored | Revenue share | Actual units | Hit +/-20 | Hit +/-30 | WMAPE | Bias | Phantom rate | Abs error share |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| availability_unknown | 9 | 0 | 0.0% | 0.0 | - | - | - | - | 11.1% | 0.0% |
| observed_available | 443 | 171 | 0.9% | 1,240.0 | 26.3% | 38.6% | 46.0% | -25.4% | 60.7% | 0.6% |
| observed_constrained | 53 | 19 | 0.1% | 171.0 | 10.5% | 21.1% | 57.6% | -19.8% | 34.8% | 0.1% |
| observed_unclear | 17 | 7 | 0.0% | 47.0 | 28.6% | 57.1% | 33.6% | -29.4% | 60.0% | 0.0% |
| proxy_available | 11,360 | 7,184 | 71.3% | 130,705.5 | 26.3% | 38.2% | 54.6% | -5.7% | 68.2% | 78.6% |
| stock_unobserved | 9,163 | 2,894 | 27.6% | 29,833.0 | 18.6% | 28.0% | 63.0% | -41.4% | 39.4% | 20.7% |

## Error By Intermittency

| Intermittency | Rows | Qty scored | Revenue share | Actual units | Hit +/-20 | Hit +/-30 | WMAPE | Bias | Phantom rate | Abs error share |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| moderately_intermittent | 8,578 | 4,828 | 45.3% | 66,988.6 | 25.9% | 37.9% | 56.7% | -11.6% | 66.7% | 41.8% |
| regular | 2,982 | 2,461 | 26.4% | 64,543.9 | 27.4% | 39.0% | 52.3% | 0.3% | 92.0% | 37.1% |
| sparse_intermittent | 9,485 | 2,986 | 28.3% | 30,464.0 | 18.6% | 28.0% | 62.9% | -41.6% | 39.5% | 21.1% |

## Error By Window

| Target start | Qty scored | Actual units | Hit +/-20 | Hit +/-30 | WMAPE | Bias | Phantom rate | Abs error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2024-08-26 | 1,424 | 20,259.2 | 24.6% | 37.9% | 48.5% | -24.0% | 40.0% | 9,832.8 |
| 2024-09-23 | 1,367 | 19,847.7 | 28.5% | 40.7% | 47.7% | -4.9% | 56.6% | 9,457.7 |
| 2024-10-28 | 1,858 | 39,501.6 | 20.3% | 30.6% | 51.7% | -43.2% | 42.9% | 20,423.8 |
| 2024-11-25 | 989 | 17,197.3 | 17.0% | 23.3% | 87.9% | 34.4% | 76.3% | 15,112.2 |
| 2024-12-30 | 1,078 | 14,355.2 | 22.8% | 34.0% | 72.8% | 21.1% | 37.3% | 10,455.6 |
| 2025-01-27 | 1,231 | 16,846.4 | 25.7% | 39.0% | 53.9% | -13.9% | 35.9% | 9,086.2 |
| 2025-02-24 | 1,123 | 16,296.2 | 26.9% | 37.3% | 52.2% | -10.0% | 46.3% | 8,514.1 |
| 2025-03-24 | 1,205 | 17,692.8 | 27.1% | 38.7% | 45.2% | -13.1% | 39.5% | 7,998.3 |

## Error Bands

| Band | Rows | Row share | Actual units | Abs error | Abs error share |
| --- | --- | --- | --- | --- | --- |
| hit_0_20 | 2,477 | 24.1% | 31,557.9 | 3,256.4 | 3.6% |
| near_20_30 | 1,148 | 11.2% | 16,800.6 | 4,273.5 | 4.7% |
| miss_30_50 | 2,217 | 21.6% | 38,122.6 | 15,202.3 | 16.7% |
| miss_50_100 | 3,299 | 32.1% | 65,429.4 | 45,960.5 | 50.6% |
| miss_100_plus | 1,134 | 11.0% | 10,086.1 | 22,188.0 | 24.4% |

## Error Direction

| Direction | Rows | Row share | Actual units | Abs error | Abs error share |
| --- | --- | --- | --- | --- | --- |
| hit_20 | 2,477 | 24.1% | 31,557.9 | 3,256.4 | 3.6% |
| over_by_20_plus | 3,015 | 29.3% | 32,939.2 | 34,157.3 | 37.6% |
| under_by_20_plus | 4,783 | 46.5% | 97,499.5 | 53,467.0 | 58.8% |

## Top SKU Error Concentration

| SKU | Route | Category | Family | Windows | Actual units | Pred units | Abs error | Hit +/-20 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| JRL796 | bf_campaign_sensitive | ACCESORII | ACCESORII | 8 | 5,195.4 | 4,823.1 | 2,362.0 | 12.5% |
| PALETMIC | proxy_available_regular | MOBILIER OFFICE | PALETI | 7 | 2,633.0 | 2,032.3 | 1,634.9 | 28.6% |
| QCIP33-02E019 | proxy_available_regular | ACCESORII | QUALITY CERAMIC | 8 | 1,271.0 | 1,070.1 | 999.4 | 12.5% |
| OSM2451 | bf_campaign_sensitive | ACCESORII | OSRAM | 8 | 2,050.0 | 2,099.0 | 986.8 | 37.5% |
| QCIP33-04E019 | proxy_available_regular | ACCESORII | QUALITY CERAMIC | 8 | 1,181.0 | 1,074.1 | 952.4 | 0.0% |
| OSM4981 | bf_campaign_sensitive | ACCESORII | OSRAM | 8 | 1,680.0 | 1,586.7 | 886.7 | 0.0% |
| PALETMARE | proxy_available_regular | MOBILIER OFFICE | PALETI | 7 | 1,998.0 | 1,699.2 | 881.3 | 28.6% |
| QCIP33-03E019 | proxy_available_regular | ACCESORII | QUALITY CERAMIC | 8 | 960.0 | 786.7 | 764.2 | 0.0% |
| RHF06 | bf_campaign_sensitive | MOBILIER DE CASA | RIAN HENG - FAUSTO | 8 | 615.0 | 357.0 | 618.1 | 25.0% |
| SNR25 | bf_campaign_sensitive | MOBILIER DE CASA | 9914200 SUNRISE | 8 | 534.0 | 523.7 | 611.6 | 0.0% |
| QCIP33-33E019 | proxy_available_regular | ACCESORII | QUALITY CERAMIC | 8 | 884.0 | 1,032.9 | 605.6 | 12.5% |
| KBGD01 | bf_campaign_sensitive | ACCESORII | KINGBEST | 8 | 685.0 | 703.3 | 573.8 | 12.5% |
| ESLLEDNL22G9NF | proxy_available_regular | ACCESORII | ESL | 7 | 1,407.0 | 1,035.4 | 569.9 | 0.0% |
| KBGD03 | bf_campaign_sensitive | ACCESORII | KINGBEST | 8 | 583.0 | 572.6 | 561.8 | 0.0% |
| QCIP313002 | proxy_available_regular | ACCESORII | QUALITY CERAMIC | 8 | 720.0 | 553.6 | 517.5 | 12.5% |
| WVE20062 | bf_campaign_sensitive | ACCESORII | WELLMAX | 7 | 380.0 | 729.4 | 504.3 | 0.0% |
| QCIP313006 | proxy_available_regular | ACCESORII | QUALITY CERAMIC | 8 | 728.0 | 648.4 | 483.9 | 0.0% |
| KBGD02 | bf_campaign_sensitive | ACCESORII | KINGBEST | 6 | 621.0 | 500.8 | 474.5 | 0.0% |
| JRL799 | bf_campaign_sensitive | ACCESORII | ROLL SERVICE | 8 | 669.5 | 1,013.4 | 469.4 | 25.0% |
| QCIP309006A | bf_campaign_sensitive | ACCESORII | QUALITY CERAMIC | 8 | 929.0 | 1,017.1 | 441.8 | 37.5% |

## Decision

Even the tested-model oracle is below 50% hit +/-20, so the immediate blocker is not just model selection among current candidates. The next work should focus on data/target decomposition and missing availability signals before another small model wrapper.

## Skipped Windows

`2024-04-29`, `2024-05-27`, `2024-07-01`, `2024-07-29`

## Notes

- Requested target windows: 2024-04-29, 2024-05-27, 2024-07-01, 2024-07-29, 2024-08-26, 2024-09-23, 2024-10-28, 2024-11-25, 2024-12-30, 2025-01-27, 2025-02-24, 2025-03-24.
- Oracle rows are diagnostic only and use actual outcomes to select the best tested prediction per SKU-window.
- Current snapshot stock remains excluded from historical backtests.
- This report should guide whether the next phase is data acquisition, target-population cleanup, or a new objective.
