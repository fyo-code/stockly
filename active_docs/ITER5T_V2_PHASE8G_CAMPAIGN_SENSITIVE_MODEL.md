# Iteration 5T - Forecast V2 Phase 8G-E Campaign-Sensitive Model

Generated: 2026-05-24 16:06
Route version: `v2_routes_2026_05_21_availability`

## Verdict

Phase 8G-E did not unlock the BF/campaign route; it mainly confirms this is the hard blocker.

| Metric | Top 1000 control | Best 8G-E candidate |
| --- | --- | --- |
| Best model | sk_blend_post_bf_safe | 8ge_post_bf_hard_safe |
| Hit +/-20 | 23.4% | 24.3% |
| Delta hit +/-20 | - | +0.9pp |
| Hit +/-30 | 34.8% | 35.9% |
| WMAPE | 55.7% | 51.1% |
| Bias | -17.0% | -23.2% |
| Phantom rate | 43.5% | 40.9% |

## Aggregate Model Results

| Model | Rows | Qty scored | Hit +/-20 | Delta vs control | Hit +/-30 | WMAPE | Bias | Phantom rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| median_naive | 5,346 | 2,967 | 21.4% | -2.0pp | 32.2% | 57.3% | -18.9% | 69.3% |
| post_bf_safe_naive | 5,346 | 2,967 | 22.2% | -1.1pp | 32.9% | 52.9% | -24.8% | 65.9% |
| sk_hgb_squared | 5,346 | 2,967 | 25.3% | +2.0pp | 37.4% | 62.6% | -8.3% | 57.8% |
| sk_extra_trees | 5,346 | 2,967 | 25.3% | +1.9pp | 36.0% | 57.0% | -10.4% | 45.7% |
| sk_blend_post_bf_safe | 5,346 | 2,967 | 23.4% | +0.0pp | 34.8% | 55.7% | -17.0% | 43.5% |
| 8ge_campaign_safe_naive | 5,346 | 2,967 | 22.5% | -0.8pp | 33.5% | 52.4% | -23.3% | 62.8% |
| 8ge_bf_calendar_safe_naive | 5,346 | 2,967 | 23.9% | +0.5pp | 35.1% | 52.0% | -21.4% | 51.4% |
| 8ge_campaign_conservative_pool | 5,346 | 2,967 | 21.7% | -1.7pp | 32.8% | 55.6% | -18.6% | 65.6% |
| 8ge_post_bf_hard_safe | 5,346 | 2,967 | 24.3% | +0.9pp | 35.9% | 51.1% | -23.2% | 40.9% |

## Critical Slice Deltas - 8ge_post_bf_hard_safe

| Slice | Rows | Qty scored | Control hit +/-20 | Candidate hit +/-20 | Hit delta | Control WMAPE | Candidate WMAPE | WMAPE delta | Control bias | Candidate bias |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Top 1000 | 5,346 | 2,967 | 23.4% | 24.3% | +0.9pp | 55.7% | 51.1% | -4.6pp | -17.0% | -23.2% |
| BF/campaign-sensitive route | 2,134 | 1,184 | 16.6% | 18.6% | +1.9pp | 65.4% | 57.4% | -7.9pp | -20.2% | -31.2% |
| Any campaign/BF history | 4,245 | 2,351 | 22.4% | 23.6% | +1.2pp | 58.2% | 51.8% | -6.4pp | -12.2% | -21.1% |
| 2024-11-25 stress | 684 | 253 | 6.7% | 17.8% | +11.1pp | 139.8% | 70.9% | -68.8pp | 133.0% | 38.0% |

## Window Scores - 8ge_post_bf_hard_safe

| Target start | Qty scored | Hit +/-20 | Hit +/-30 | WMAPE | Bias | Phantom rate |
| --- | --- | --- | --- | --- | --- | --- |
| 2024-08-26 | 427 | 25.3% | 37.0% | 47.5% | -29.3% | 31.1% |
| 2024-09-23 | 428 | 34.1% | 47.7% | 46.0% | -0.6% | 49.5% |
| 2024-10-28 | 546 | 15.8% | 24.7% | 54.9% | -50.8% | 31.3% |
| 2024-11-25 | 253 | 17.8% | 23.3% | 70.9% | 38.0% | 57.1% |
| 2024-12-30 | 315 | 21.0% | 32.7% | 58.5% | -9.3% | 37.2% |
| 2025-01-27 | 352 | 24.1% | 36.9% | 49.3% | -22.0% | 30.1% |
| 2025-02-24 | 318 | 29.2% | 39.9% | 43.8% | -22.9% | 37.2% |
| 2025-03-24 | 328 | 28.0% | 45.1% | 40.3% | -8.7% | 42.1% |

## Campaign Diagnostics

| Target start | Train windows | Eval rows | Campaign rows | BF-calendar rows | Post-BF stress rows |
| --- | --- | --- | --- | --- | --- |
| 2024-08-26 | 4 | 705 | 504 | 0 | 0 |
| 2024-09-23 | 5 | 700 | 486 | 0 | 0 |
| 2024-10-28 | 6 | 688 | 650 | 688 | 0 |
| 2024-11-25 | 7 | 684 | 681 | 684 | 639 |
| 2024-12-30 | 8 | 661 | 641 | 629 | 0 |
| 2025-01-27 | 9 | 646 | 625 | 619 | 0 |
| 2025-02-24 | 10 | 641 | 424 | 0 | 0 |
| 2025-03-24 | 11 | 621 | 414 | 0 | 0 |

## Skipped Windows

`2024-04-29`, `2024-05-27`, `2024-07-01`, `2024-07-29`

## Notes

- Revenue-rank limit: Top 1000.
- Feature matrix rows: 8,227.
- Feature matrix cache: `/Users/fyodorgolovin/Downloads/Supply-Inventory v1.0 codex/backend/data/forecast_v2_feature_cache/feature_matrix_headline_top1000_aa54e4e2fe0a.pkl` (hit).
- All model training uses only earlier target windows.
- Candidate transforms are forecast-time masks based on route labels, BF calendar/history, and cleaned campaign history.
- Target-window campaign buckets are not used as model features.
- Phase 8F current snapshots remain excluded from historical backtests.
