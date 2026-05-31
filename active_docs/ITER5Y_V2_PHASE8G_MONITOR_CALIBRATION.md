# Iteration 5Y - V2 Phase 8G-J Monitor Calibration

Generated: 2026-05-26 15:08
Route version: `v2_routes_2026_05_21_availability`

## Decision

Decision: `RESEARCH_CANDIDATE_FOR_OFFICIAL_VALIDATION`.

`8gj_bfc_nonpost_lift_150` is a promising monitored-caveat research candidate. It was selected on the known Phase 8G validation windows, so it must not replace the official champion until it is wired and rerun through the official 8G-I validation/export path.

| Metric | 8G-I champion | Best 8G-J candidate | Delta vs champion |
| --- | --- | --- | --- |
| Model | 8gf_regular_plus_post_bf_safe | 8gj_bfc_nonpost_lift_150 | - |
| Hit +/-20 | 25.3% | 27.2% | +1.9pp |
| Hit +/-30 | 36.5% | 39.2% | +2.7pp |
| WMAPE | 51.0% | 49.3% | -1.7pp |
| Bias | -21.3% | -9.3% | +12.0pp |
| Phantom | 41.0% | 41.0% | +0.0pp |

## Pre-Official Gate Replay

| Gate | Required | Observed | Status |
| --- | --- | --- | --- |
| Top 1000 hit +/-20 | >= +1.5pp vs control | +3.9pp | PASS |
| Top 1000 WMAPE | <= +0.5pp vs control | -6.4pp | PASS |
| Top 1000 phantom | <= +0.5pp vs control | -2.5pp | PASS |
| Top 500 hit +/-20 | >= 0.0pp vs control | +4.5pp | PASS |
| Top 100 hit +/-20 | >= 0.0pp vs control | +2.9pp | PASS |
| 2024-11-25 WMAPE | < control | -68.8pp | PASS |

## Candidate Results

| Model | Rows | Qty scored | Hit +/-20 | Delta vs control | Delta vs 8G-I | Hit +/-30 | WMAPE | WMAPE delta vs 8G-I | Bias | Bias delta vs 8G-I | Phantom | Phantom delta vs 8G-I |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| sk_blend_post_bf_safe | 5,346 | 2,967 | 23.4% | +0.0pp | -2.0pp | 34.8% | 55.7% | +4.7pp | -17.0% | +4.3pp | 43.5% | +2.5pp |
| 8gf_regular_plus_post_bf_safe | 5,346 | 2,967 | 25.3% | +2.0pp | +0.0pp | 36.5% | 51.0% | +0.0pp | -21.3% | +0.0pp | 41.0% | +0.0pp |
| 8gf_guarded_regular_plus_post_bf_safe | 5,346 | 2,967 | 24.5% | +1.1pp | -0.8pp | 35.7% | 51.2% | +0.2pp | -22.4% | -1.1pp | 40.9% | -0.1pp |
| 8gj_regular_control_blend_10 | 5,346 | 2,967 | 25.1% | +1.8pp | -0.2pp | 36.5% | 51.0% | -0.0pp | -21.5% | -0.2pp | 41.0% | +0.0pp |
| 8gj_regular_control_blend_25 | 5,346 | 2,967 | 25.0% | +1.7pp | -0.3pp | 36.3% | 51.0% | -0.0pp | -21.8% | -0.5pp | 41.0% | +0.0pp |
| 8gj_regular_control_blend_40 | 5,346 | 2,967 | 24.7% | +1.4pp | -0.6pp | 36.3% | 51.0% | -0.0pp | -22.1% | -0.8pp | 41.0% | +0.0pp |
| 8gj_bfc_nonpost_lift_110 | 5,346 | 2,967 | 26.0% | +2.6pp | +0.6pp | 37.2% | 50.2% | -0.8pp | -18.9% | +2.4pp | 41.0% | +0.0pp |
| 8gj_bfc_nonpost_lift_120 | 5,346 | 2,967 | 26.4% | +3.0pp | +1.1pp | 38.1% | 49.7% | -1.4pp | -16.5% | +4.8pp | 41.0% | +0.0pp |
| 8gj_bfc_nonpost_lift_130 | 5,346 | 2,967 | 27.1% | +3.7pp | +1.8pp | 38.8% | 49.4% | -1.7pp | -14.1% | +7.2pp | 41.0% | +0.0pp |
| 8gj_bfc_nonpost_lift_140 | 5,346 | 2,967 | 27.2% | +3.8pp | +1.9pp | 38.9% | 49.2% | -1.8pp | -11.7% | +9.6pp | 41.0% | +0.0pp |
| 8gj_bfc_nonpost_lift_150 | 5,346 | 2,967 | 27.2% | +3.9pp | +1.9pp | 39.2% | 49.3% | -1.7pp | -9.3% | +12.0pp | 41.0% | +0.0pp |

## Revenue Scope Replay - 8gj_bfc_nonpost_lift_150

| Scope | Rows | Qty scored | Actual revenue | Baseline hit +/-20 | Candidate hit +/-20 | Hit delta | Baseline WMAPE | Candidate WMAPE | WMAPE delta | Baseline bias | Candidate bias | Bias delta | Baseline phantom | Candidate phantom | Phantom delta |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Top 100 | 475 | 349 | 19,774,645 | 26.6% | 29.5% | +2.9pp | 48.6% | 42.3% | -6.3pp | -3.7% | 1.1% | +4.8pp | 62.1% | 62.1% | +0.0pp |
| Top 250 | 1,373 | 943 | 39,557,500 | 24.2% | 30.1% | +5.9pp | 53.5% | 45.5% | -8.0pp | -12.8% | -7.5% | +5.3pp | 58.8% | 55.7% | -3.1pp |
| Top 500 | 2,866 | 1,751 | 59,034,164 | 23.2% | 27.7% | +4.5pp | 55.3% | 48.7% | -6.7pp | -14.1% | -7.3% | +6.9pp | 49.3% | 46.7% | -2.6pp |
| Top 750 | 4,140 | 2,384 | 70,548,177 | 23.3% | 27.9% | +4.6pp | 55.7% | 49.0% | -6.7pp | -15.3% | -8.1% | +7.2pp | 45.2% | 42.3% | -2.8pp |
| Top 1000 | 5,346 | 2,967 | 79,136,333 | 23.4% | 27.2% | +3.9pp | 55.7% | 49.3% | -6.4pp | -17.0% | -9.3% | +7.7pp | 43.5% | 41.0% | -2.5pp |

## Monitor Replay - 8gj_bfc_nonpost_lift_150 vs 8G-I Champion

| Slice | Rows | Qty scored | Actual revenue | 8G-I hit +/-20 | Candidate hit +/-20 | Hit delta | 8G-I WMAPE | Candidate WMAPE | WMAPE delta | 8G-I bias | Candidate bias | Bias delta | 8G-I phantom | Candidate phantom | Phantom delta |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| All Top 1000 | 5,346 | 2,967 | 79,136,333 | 25.3% | 27.2% | +1.9pp | 51.0% | 49.3% | -1.7pp | -21.3% | -9.3% | +12.0pp | 41.0% | 41.0% | +0.0pp |
| Available/proxy regular | 1,462 | 1,026 | 22,650,364 | 33.1% | 33.1% | +0.0pp | 43.1% | 43.1% | +0.0pp | -6.0% | -6.0% | +0.0pp | 68.4% | 68.4% | +0.0pp |
| Available regular | 986 | 703 | 15,441,693 | 35.1% | 35.1% | +0.0pp | 41.1% | 41.1% | +0.0pp | -3.7% | -3.7% | +0.0pp | 87.2% | 87.2% | +0.0pp |
| BF/campaign-sensitive route | 2,134 | 1,184 | 33,838,656 | 18.6% | 23.4% | +4.8pp | 57.4% | 53.8% | -3.6pp | -31.2% | -5.5% | +25.7pp | 46.2% | 46.2% | +0.0pp |
| 2025-03-24 window | 621 | 328 | 7,894,646 | 28.4% | 28.4% | +0.0pp | 42.1% | 42.1% | +0.0pp | -4.4% | -4.4% | +0.0pp | 42.1% | 42.1% | +0.0pp |
| 2024-11-25 stress | 684 | 253 | 5,426,480 | 17.8% | 17.8% | +0.0pp | 70.9% | 70.9% | +0.0pp | 38.0% | 38.0% | +0.0pp | 57.1% | 57.1% | +0.0pp |

## Skipped Windows

`2024-04-29`, `2024-05-27`, `2024-07-01`, `2024-07-29`

## Notes

- Revenue-rank limit: Top 1000.
- Feature matrix rows: 8,227.
- Feature matrix cache: `/Users/fyodorgolovin/Downloads/Supply-Inventory v1.0 codex/backend/data/forecast_v2_feature_cache/feature_matrix_headline_top1000_aa54e4e2fe0a.pkl` (hit; refresh requested: no).
- 8G-J is a high-revenue research calibration phase, not official wiring.
- Candidate selection is validation-window tuning on the known Phase 8G backtest windows, not independent future holdout evidence.
- The gate table is a pre-official replay over research score rows. It is not a substitute for wiring the candidate into `sklearn_direct_model.py` and rerunning the official 8G-I validation/export path.
- The BF/campaign lift candidates multiply only `bf_campaign_sensitive` rows outside post-BF calendar context when the champion prediction is at least 3 units.
- The regular-control blend candidates were tested to reduce regular phantom risk, but they did not fix the phantom monitor because most zero-actual regular predictions stayed above the sale threshold.
- The best candidate improves underprediction and BF/campaign-sensitive accuracy, but it does not solve the regular phantom monitor or the 2025-03-24 WMAPE regression.
- Any promotion must be wired into `sklearn_direct_model.py` and rerun through the official 8G-I validation/export path before replacing the current champion.
