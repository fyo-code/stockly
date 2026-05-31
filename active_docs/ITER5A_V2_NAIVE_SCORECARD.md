# Iteration 5A — V2 Naive Benchmark Scorecard

Generated: 2026-05-11 17:15

Runs: `v2_naive_2024-12-30`, `v2_naive_2025-02-24`

## Headline Forecastable Revenue Movers

| Run | Model | Eligible | Qty scored | Hit +/-20 | Hit +/-30 | WMAPE | Bias | Phantom rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| v2_naive_2024-12-30 | last4 | 2,345 | 907 | 14.1% | 21.3% | 94.0% | 5.1% | 49.4% |
| v2_naive_2024-12-30 | median_naive | 2,345 | 907 | 20.2% | 29.8% | 69.3% | 3.2% | 68.1% |
| v2_naive_2024-12-30 | roll13_mean | 2,345 | 907 | 21.6% | 30.5% | 78.6% | 35.6% | 73.2% |
| v2_naive_2024-12-30 | roll8_mean | 2,345 | 907 | 19.5% | 30.2% | 94.4% | 57.8% | 74.0% |
| v2_naive_2024-12-30 | seasonal52 | 2,345 | 907 | 16.8% | 23.5% | 81.3% | -13.6% | 74.7% |
| v2_naive_2024-12-30 | zero | 2,345 | 907 | 0.0% | 0.0% | 100.0% | -100.0% | 0.0% |
| v2_naive_2025-02-24 | last4 | 2,296 | 977 | 20.8% | 29.6% | 62.3% | -15.9% | 64.4% |
| v2_naive_2025-02-24 | median_naive | 2,296 | 977 | 23.7% | 33.3% | 53.8% | -26.0% | 70.7% |
| v2_naive_2025-02-24 | roll13_mean | 2,296 | 977 | 20.2% | 30.2% | 63.0% | -16.8% | 65.9% |
| v2_naive_2025-02-24 | roll8_mean | 2,296 | 977 | 20.3% | 31.1% | 56.6% | -20.3% | 67.9% |
| v2_naive_2025-02-24 | seasonal52 | 2,296 | 977 | 17.3% | 23.8% | 69.0% | -18.7% | 76.2% |
| v2_naive_2025-02-24 | zero | 2,296 | 977 | 0.0% | 0.0% | 100.0% | -100.0% | 0.0% |

## Median Naive By Regime

| Run | Regime | Population | Qty scored | Hit +/-20 | WMAPE | Phantom rate |
| --- | --- | --- | --- | --- | --- | --- |
| v2_naive_2024-12-30 | active_movers | 1,395 | 455 | 19.8% | 63.1% | 68.4% |
| v2_naive_2024-12-30 | dormant | 31,879 | 30 | 0.0% | 100.0% | 0.0% |
| v2_naive_2024-12-30 | forecastable_revenue_movers | 2,345 | 907 | 20.2% | 69.3% | 68.1% |
| v2_naive_2024-12-30 | long_tail_active | 40,208 | 1,196 | 6.1% | 89.7% | 7.6% |
| v2_naive_2024-12-30 | seasonal_revenue_movers | 632 | 25 | 4.0% | 83.7% | 18.0% |
| v2_naive_2024-12-30 | sparse_revenue_items | 5,182 | 194 | 7.2% | 94.6% | 17.5% |
| v2_naive_2025-02-24 | active_movers | 1,394 | 420 | 16.9% | 61.6% | 63.9% |
| v2_naive_2025-02-24 | dormant | 34,787 | 31 | 0.0% | 100.0% | 0.0% |
| v2_naive_2025-02-24 | forecastable_revenue_movers | 2,296 | 977 | 23.7% | 53.8% | 70.7% |
| v2_naive_2025-02-24 | long_tail_active | 40,243 | 1,024 | 3.8% | 86.5% | 6.8% |
| v2_naive_2025-02-24 | seasonal_revenue_movers | 606 | 15 | 6.7% | 67.3% | 15.7% |
| v2_naive_2025-02-24 | sparse_revenue_items | 5,357 | 239 | 3.3% | 81.3% | 13.3% |

## Notes

- This is a v2-native chain-level benchmark, not a legacy Iter 3/4 comparison.
- Regime labels are recomputed with only data before each target window.
- Quantity hit metrics use material actual windows only: `actual_units >= 4`.
- Zero-heavy regimes should be judged by phantom/zero behavior, not headline hit rate.
