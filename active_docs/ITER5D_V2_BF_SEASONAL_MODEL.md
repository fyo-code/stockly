# Iteration 5D — V2 BF-Aware Scikit-Learn Direct Model

Generated: 2026-05-16 23:28

## Phase 6 Summary

- Previous stock-aware best: `sk_hgb_poisson` hit +/-20 = 23.7%; `sk_blend_median` hit +/-20 = 23.5%, hit +/-30 = 35.0%, WMAPE = 60.8%, phantom = 53.8%.
- New best aggregate: `sk_blend_post_bf_safe` hit +/-20 = 24.1%, hit +/-30 = 35.3%, WMAPE = 56.1%, phantom = 48.1%.
- Delta vs original sklearn baseline (`sk_blend_median` 23.2%): +0.9pp hit +/-20.
- Delta vs Phase 5 best (`sk_hgb_poisson` 23.7%): +0.4pp hit +/-20.
- Diagnosis confirmed: `2024-11-25` starts immediately after BF 2024, so trailing 4-week features can be polluted by BF demand.
- `2024-11-25` improved but remains weak. `post_bf_safe_naive` reached 20.0% hit +/-20, WMAPE 66.3%, bias -25.4%, phantom 56.5%; `sk_blend_post_bf_safe` reached 17.0% hit +/-20, WMAPE 87.9%, bias +34.4%, phantom 76.3%.
- Review fix applied before this final run: non-BF recent demand is normalized to a 4-week-equivalent scale before entering the post-BF safe route.

## Aggregate Headline Result

| Model | Eligible | Qty scored | Hit +/-20 | Hit +/-30 | WMAPE | Bias | Phantom rate | Winrate vs median |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| sk_blend_post_bf_safe | 21,045 | 10,275 | 24.1% | 35.3% | 56.1% | -12.5% | 48.1% | 48.6% |
| sk_extra_trees | 21,045 | 10,275 | 23.9% | 35.7% | 58.9% | -5.5% | 46.6% | 53.2% |
| sk_blend_median | 21,045 | 10,275 | 23.8% | 34.9% | 57.7% | -10.5% | 48.2% | 48.1% |
| sk_hgb_poisson | 21,045 | 10,275 | 23.2% | 34.1% | 63.6% | -3.9% | 44.3% | 52.6% |
| sk_hgb_squared | 21,045 | 10,275 | 23.1% | 34.8% | 66.5% | 3.1% | 53.0% | 53.3% |
| post_bf_safe_naive | 21,045 | 10,275 | 20.1% | 30.1% | 56.0% | -27.6% | 65.8% | 4.2% |
| median_naive | 21,045 | 10,275 | 19.8% | 30.1% | 57.4% | -23.2% | 69.9% | - |

## Per-Window Headline Scores

| Target start | Model | Qty scored | Hit +/-20 | Hit +/-30 | WMAPE | Bias | Phantom rate | Winrate vs median |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2024-08-26 | median_naive | 1,424 | 20.1% | 31.0% | 52.0% | -33.7% | 68.2% | - |
| 2024-08-26 | post_bf_safe_naive | 1,424 | 20.1% | 31.0% | 52.0% | -33.7% | 68.2% | 0.0% |
| 2024-08-26 | sk_hgb_poisson | 1,424 | 23.6% | 36.2% | 49.5% | -24.1% | 33.3% | 52.2% |
| 2024-08-26 | sk_hgb_squared | 1,424 | 21.1% | 33.8% | 53.6% | -25.8% | 30.5% | 48.4% |
| 2024-08-26 | sk_extra_trees | 1,424 | 26.7% | 40.2% | 48.0% | -15.3% | 40.0% | 56.7% |
| 2024-08-26 | sk_blend_median | 1,424 | 24.6% | 37.9% | 48.5% | -24.0% | 40.0% | 47.3% |
| 2024-08-26 | sk_blend_post_bf_safe | 1,424 | 24.6% | 37.9% | 48.5% | -24.0% | 40.0% | 47.3% |
| 2024-09-23 | median_naive | 1,367 | 24.6% | 35.4% | 50.4% | -24.2% | 67.2% | - |
| 2024-09-23 | post_bf_safe_naive | 1,367 | 24.6% | 35.4% | 50.4% | -24.2% | 67.2% | 0.0% |
| 2024-09-23 | sk_hgb_poisson | 1,367 | 28.5% | 40.5% | 48.7% | -2.0% | 46.7% | 54.3% |
| 2024-09-23 | sk_hgb_squared | 1,367 | 29.7% | 42.9% | 54.0% | 5.2% | 62.2% | 56.0% |
| 2024-09-23 | sk_extra_trees | 1,367 | 29.1% | 42.1% | 50.2% | 7.5% | 59.0% | 53.5% |
| 2024-09-23 | sk_blend_median | 1,367 | 28.5% | 40.7% | 47.7% | -4.9% | 56.6% | 50.4% |
| 2024-09-23 | sk_blend_post_bf_safe | 1,367 | 28.5% | 40.7% | 47.7% | -4.9% | 56.6% | 50.4% |
| 2024-10-28 | median_naive | 1,858 | 13.1% | 20.3% | 57.7% | -51.8% | 59.7% | - |
| 2024-10-28 | post_bf_safe_naive | 1,858 | 13.1% | 20.3% | 57.7% | -51.8% | 59.7% | 0.0% |
| 2024-10-28 | sk_hgb_poisson | 1,858 | 21.9% | 32.9% | 51.5% | -39.9% | 40.6% | 73.4% |
| 2024-10-28 | sk_hgb_squared | 1,858 | 21.0% | 34.2% | 50.5% | -37.4% | 46.9% | 75.3% |
| 2024-10-28 | sk_extra_trees | 1,858 | 19.8% | 31.2% | 51.3% | -41.3% | 42.6% | 70.0% |
| 2024-10-28 | sk_blend_median | 1,858 | 20.3% | 30.6% | 51.7% | -43.2% | 42.9% | 66.5% |
| 2024-10-28 | sk_blend_post_bf_safe | 1,858 | 20.3% | 30.6% | 51.7% | -43.2% | 42.9% | 66.5% |
| 2024-11-25 | median_naive | 989 | 16.8% | 26.6% | 79.6% | 16.1% | 80.1% | - |
| 2024-11-25 | post_bf_safe_naive | 989 | 20.0% | 26.6% | 66.3% | -25.4% | 56.5% | 43.9% |
| 2024-11-25 | sk_hgb_poisson | 989 | 7.9% | 11.5% | 143.7% | 102.1% | 75.6% | 17.9% |
| 2024-11-25 | sk_hgb_squared | 989 | 6.9% | 12.2% | 143.5% | 107.6% | 83.7% | 17.8% |
| 2024-11-25 | sk_extra_trees | 989 | 13.7% | 18.6% | 103.9% | 54.0% | 77.3% | 24.3% |
| 2024-11-25 | sk_blend_median | 989 | 14.1% | 18.9% | 102.9% | 52.8% | 76.9% | 22.6% |
| 2024-11-25 | sk_blend_post_bf_safe | 989 | 17.0% | 23.3% | 87.9% | 34.4% | 76.3% | 27.6% |
| 2024-12-30 | median_naive | 1,078 | 20.0% | 30.7% | 66.7% | 6.5% | 69.8% | - |
| 2024-12-30 | post_bf_safe_naive | 1,078 | 20.0% | 30.7% | 66.7% | 6.5% | 69.8% | 0.0% |
| 2024-12-30 | sk_hgb_poisson | 1,078 | 22.6% | 32.3% | 79.2% | 25.6% | 33.2% | 46.5% |
| 2024-12-30 | sk_hgb_squared | 1,078 | 23.6% | 32.7% | 89.0% | 42.1% | 47.8% | 47.7% |
| 2024-12-30 | sk_extra_trees | 1,078 | 23.3% | 35.3% | 78.2% | 30.6% | 38.2% | 49.7% |
| 2024-12-30 | sk_blend_median | 1,078 | 22.8% | 34.0% | 72.8% | 21.1% | 37.3% | 43.0% |
| 2024-12-30 | sk_blend_post_bf_safe | 1,078 | 22.8% | 34.0% | 72.8% | 21.1% | 37.3% | 43.0% |
| 2025-01-27 | median_naive | 1,231 | 23.2% | 34.6% | 56.4% | -8.7% | 66.9% | - |
| 2025-01-27 | post_bf_safe_naive | 1,231 | 23.2% | 34.6% | 56.4% | -8.7% | 66.9% | 0.0% |
| 2025-01-27 | sk_hgb_poisson | 1,231 | 25.6% | 38.2% | 57.2% | -15.9% | 29.6% | 51.2% |
| 2025-01-27 | sk_hgb_squared | 1,231 | 26.1% | 39.4% | 61.6% | -4.3% | 37.2% | 55.8% |
| 2025-01-27 | sk_extra_trees | 1,231 | 26.0% | 39.5% | 56.4% | -9.3% | 33.7% | 51.6% |
| 2025-01-27 | sk_blend_median | 1,231 | 25.7% | 39.0% | 53.9% | -13.9% | 35.9% | 44.2% |
| 2025-01-27 | sk_blend_post_bf_safe | 1,231 | 25.7% | 39.0% | 53.9% | -13.9% | 35.9% | 44.2% |
| 2025-02-24 | median_naive | 1,123 | 21.4% | 32.1% | 53.6% | -23.5% | 69.6% | - |
| 2025-02-24 | post_bf_safe_naive | 1,123 | 21.4% | 32.1% | 53.6% | -23.5% | 69.6% | 0.0% |
| 2025-02-24 | sk_hgb_poisson | 1,123 | 26.7% | 37.0% | 54.0% | -7.7% | 46.0% | 51.5% |
| 2025-02-24 | sk_hgb_squared | 1,123 | 25.2% | 36.1% | 59.4% | -1.1% | 46.9% | 50.4% |
| 2025-02-24 | sk_extra_trees | 1,123 | 24.9% | 37.7% | 52.7% | -7.0% | 36.2% | 50.8% |
| 2025-02-24 | sk_blend_median | 1,123 | 26.9% | 37.3% | 52.2% | -10.0% | 46.3% | 46.9% |
| 2025-02-24 | sk_blend_post_bf_safe | 1,123 | 26.9% | 37.3% | 52.2% | -10.0% | 46.3% | 46.9% |
| 2025-03-24 | median_naive | 1,205 | 21.7% | 33.7% | 46.4% | -21.8% | 69.0% | - |
| 2025-03-24 | post_bf_safe_naive | 1,205 | 21.7% | 33.7% | 46.4% | -21.8% | 69.0% | 0.0% |
| 2025-03-24 | sk_hgb_poisson | 1,205 | 26.3% | 39.2% | 47.8% | -14.2% | 37.1% | 55.4% |
| 2025-03-24 | sk_hgb_squared | 1,205 | 29.3% | 42.0% | 48.6% | 1.6% | 53.8% | 56.4% |
| 2025-03-24 | sk_extra_trees | 1,205 | 26.6% | 38.6% | 46.4% | -11.0% | 36.3% | 53.4% |
| 2025-03-24 | sk_blend_median | 1,205 | 27.1% | 38.7% | 45.2% | -13.1% | 39.5% | 48.8% |
| 2025-03-24 | sk_blend_post_bf_safe | 1,205 | 27.1% | 38.7% | 45.2% | -13.1% | 39.5% | 48.8% |

## Train-Time Postprocessing

| Target start | Model | Train windows | Train rows | Factor | Zero floor | Train hit +/-20 | Train WMAPE | Train phantom |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2024-08-26 | sk_extra_trees | 4 | 9,846 | 1.30 | 3.00 | 41.3% | 38.8% | 24.7% |
| 2024-08-26 | sk_hgb_poisson | 4 | 9,846 | 1.20 | 3.00 | 31.7% | 34.4% | 35.9% |
| 2024-08-26 | sk_hgb_squared | 4 | 9,846 | 1.15 | 3.00 | 31.9% | 37.6% | 32.8% |
| 2024-09-23 | sk_extra_trees | 5 | 12,448 | 1.30 | 3.00 | 41.7% | 38.1% | 27.3% |
| 2024-09-23 | sk_hgb_poisson | 5 | 12,448 | 1.20 | 3.00 | 32.9% | 33.5% | 35.1% |
| 2024-09-23 | sk_hgb_squared | 5 | 12,448 | 1.25 | 3.00 | 30.6% | 43.6% | 47.8% |
| 2024-10-28 | sk_extra_trees | 6 | 15,071 | 1.20 | 3.00 | 42.3% | 35.2% | 23.1% |
| 2024-10-28 | sk_hgb_poisson | 6 | 15,071 | 1.25 | 3.00 | 32.4% | 36.6% | 41.8% |
| 2024-10-28 | sk_hgb_squared | 6 | 15,071 | 1.25 | 3.00 | 31.0% | 41.2% | 45.5% |
| 2024-11-25 | sk_extra_trees | 7 | 17,701 | 1.15 | 3.00 | 42.0% | 34.3% | 24.3% |
| 2024-11-25 | sk_hgb_poisson | 7 | 17,701 | 1.20 | 3.00 | 32.9% | 35.2% | 39.8% |
| 2024-11-25 | sk_hgb_squared | 7 | 17,701 | 1.20 | 3.00 | 31.6% | 39.2% | 45.4% |
| 2024-12-30 | sk_extra_trees | 8 | 20,393 | 1.15 | 3.00 | 41.8% | 34.4% | 22.4% |
| 2024-12-30 | sk_hgb_poisson | 8 | 20,393 | 1.20 | 3.00 | 31.1% | 37.6% | 40.0% |
| 2024-12-30 | sk_hgb_squared | 8 | 20,393 | 1.30 | 3.00 | 31.0% | 42.4% | 50.3% |
| 2025-01-27 | sk_extra_trees | 9 | 23,052 | 1.20 | 3.00 | 41.5% | 35.4% | 23.3% |
| 2025-01-27 | sk_hgb_poisson | 9 | 23,052 | 1.20 | 3.00 | 31.1% | 37.1% | 38.5% |
| 2025-01-27 | sk_hgb_squared | 9 | 23,052 | 1.25 | 3.00 | 29.3% | 42.5% | 48.7% |
| 2025-02-24 | sk_extra_trees | 10 | 25,690 | 1.20 | 3.00 | 42.0% | 35.4% | 23.0% |
| 2025-02-24 | sk_hgb_poisson | 10 | 25,690 | 1.30 | 3.00 | 30.8% | 40.4% | 43.6% |
| 2025-02-24 | sk_hgb_squared | 10 | 25,690 | 1.25 | 3.00 | 29.8% | 42.1% | 45.2% |
| 2025-03-24 | sk_extra_trees | 11 | 28,295 | 1.20 | 3.00 | 42.1% | 35.3% | 22.6% |
| 2025-03-24 | sk_hgb_poisson | 11 | 28,295 | 1.25 | 3.00 | 30.6% | 39.8% | 40.7% |
| 2025-03-24 | sk_hgb_squared | 11 | 28,295 | 1.35 | 3.00 | 29.7% | 45.6% | 55.2% |

## Skipped Windows

`2024-04-29`, `2024-05-27`, `2024-07-01`, `2024-07-29`

## Notes

- Rows are forecastable revenue movers only.
- Every scored target window trains only on earlier target windows.
- Models use the v2 feature matrix: lag baselines, rolling demand, category/product family, discounts, BF/campaign/store-breadth signals, and calendar features.
- Postprocessing factor and zero floor are learned only from prior training windows.
- `median_naive` remains the v2-native benchmark.
