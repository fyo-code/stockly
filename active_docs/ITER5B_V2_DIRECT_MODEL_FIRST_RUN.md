# Iteration 5B — V2 Direct Model First Run

Generated: 2026-05-12 11:15

## Result

| Model | Eligible | Qty scored | Hit +/-20 | Hit +/-30 | WMAPE | Bias | Phantom rate | Winrate vs median |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| direct_empirical_v1 | 18,306 | 8,845 | 22.2% | 33.1% | 66.4% | 4.3% | 86.1% | 57.1% |
| median_naive | 18,306 | 8,845 | 19.7% | 29.9% | 58.6% | -24.7% | 70.2% | - |

## Per-Window Headline Scores

| Target start | Model | Eligible | Qty scored | Hit +/-20 | Hit +/-30 | WMAPE | Bias | Phantom rate | Winrate vs median | Train windows |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2024-08-26 | direct_empirical_v1 | 2,204 | 1,207 | 24.3% | 35.7% | 55.0% | -16.4% | 77.9% | 64.0% | 4 |
| 2024-08-26 | median_naive | 2,204 | 1,207 | 19.1% | 30.7% | 53.2% | -34.7% | 67.5% | - | - |
| 2024-09-23 | direct_empirical_v1 | 2,265 | 1,175 | 24.3% | 36.3% | 56.8% | -4.4% | 79.2% | 58.8% | 5 |
| 2024-09-23 | median_naive | 2,265 | 1,175 | 23.6% | 34.1% | 51.4% | -27.4% | 67.7% | - | - |
| 2024-10-28 | direct_empirical_v1 | 2,287 | 1,628 | 19.1% | 29.6% | 53.7% | -38.8% | 77.7% | 78.6% | 6 |
| 2024-10-28 | median_naive | 2,287 | 1,628 | 11.9% | 19.3% | 59.4% | -53.9% | 60.2% | - | - |
| 2024-11-25 | direct_empirical_v1 | 2,327 | 822 | 13.1% | 20.6% | 115.8% | 67.8% | 91.1% | 24.1% | 7 |
| 2024-11-25 | median_naive | 2,327 | 822 | 19.0% | 28.1% | 83.6% | 25.3% | 80.7% | - | - |
| 2024-12-30 | direct_empirical_v1 | 2,345 | 907 | 19.2% | 28.0% | 104.5% | 74.5% | 89.4% | 41.9% | 8 |
| 2024-12-30 | median_naive | 2,345 | 907 | 20.2% | 29.8% | 69.3% | 3.2% | 68.1% | - | - |
| 2025-01-27 | direct_empirical_v1 | 2,303 | 1,073 | 26.0% | 37.0% | 73.6% | 43.3% | 85.8% | 48.5% | 9 |
| 2025-01-27 | median_naive | 2,303 | 1,073 | 22.8% | 34.6% | 54.4% | -6.3% | 67.1% | - | - |
| 2025-02-24 | direct_empirical_v1 | 2,296 | 977 | 25.8% | 37.4% | 58.3% | -1.1% | 88.6% | 59.6% | 10 |
| 2025-02-24 | median_naive | 2,296 | 977 | 23.7% | 33.3% | 53.8% | -26.0% | 70.7% | - | - |
| 2025-03-24 | direct_empirical_v1 | 2,279 | 1,056 | 24.6% | 38.3% | 46.3% | -5.8% | 89.1% | 59.8% | 11 |
| 2025-03-24 | median_naive | 2,279 | 1,056 | 21.6% | 34.8% | 48.9% | -24.1% | 70.8% | - | - |

## Learned Model Per Window

| Target start | Train windows | Train rows | Blend | Global factor | Train hit +/-20 | Train WMAPE |
| --- | --- | --- | --- | --- | --- | --- |
| 2024-08-26 | 4 | 8,252 | last4=0.3, roll13_mean=0.6, seasonal52=0.1 | 1.11 | 23.0% | 54.7% |
| 2024-09-23 | 5 | 10,456 | last4=0.3, roll13_mean=0.6, seasonal52=0.1 | 1.18 | 21.9% | 54.1% |
| 2024-10-28 | 6 | 12,721 | last4=0.3, roll13_mean=0.6, seasonal52=0.1 | 1.21 | 22.3% | 53.3% |
| 2024-11-25 | 7 | 15,008 | roll13_mean=0.8, seasonal52=0.2 | 1.42 | 19.9% | 54.5% |
| 2024-12-30 | 8 | 17,335 | roll13_mean=0.8, seasonal52=0.2 | 1.34 | 20.1% | 56.4% |
| 2025-01-27 | 9 | 19,680 | last4=0.1, roll13_mean=0.7, seasonal52=0.2 | 1.26 | 20.1% | 57.7% |
| 2025-02-24 | 10 | 21,983 | last4=0.1, roll13_mean=0.7, seasonal52=0.2 | 1.21 | 20.9% | 57.8% |
| 2025-03-24 | 11 | 24,279 | last4=0.1, roll13_mean=0.7, seasonal52=0.2 | 1.21 | 21.0% | 57.6% |

## Skipped Windows

`2024-04-29`, `2024-05-27`, `2024-07-01`, `2024-07-29`

## Notes

- This is a direct 4-week chain-level candidate, but not the final LightGBM-style model.
- It learns only from prior walk-forward windows, so each scored target remains blind.
- The model uses a weighted direct blend of `last4`, `roll13_mean`, and `seasonal52`, then applies shrinkage-calibrated SKU/family/category factors.
- The fast score path avoids writing row-level experiment results to SQLite. Persist only official finalists.
- The local environment currently has pandas/numpy, but no sklearn, and LightGBM imports through an unstable NumPy/matplotlib ABI path. This run therefore uses the dependency-free empirical model.
