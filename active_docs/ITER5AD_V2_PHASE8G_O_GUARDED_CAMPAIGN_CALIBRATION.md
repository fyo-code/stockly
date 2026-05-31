# Iteration 5AD - V2 Phase 8G-O Guarded Campaign/BF Calibration

Generated: 2026-05-28 14:25
Route version: `v2_routes_2026_05_26_stock_position`

## Decision

Decision: `PROMOTE_GUARDED_CAMPAIGN_CANDIDATE`.

The guarded candidate clears the phase gates by lifting only pre-BF BF/campaign-sensitive rows and leaving the 2024-12-30 / 2025-01-27 normal-calendar rows untouched.

| Metric | Current champion | Best guarded candidate | Delta |
| --- | --- | --- | --- |
| Model | 8gf_regular_plus_post_bf_safe | 8go_pre_bf_bfc_lift_180 | - |
| Calibration rows touched | - | 480 | - |
| Hit +/-20 | 25.3% | 27.4% | +2.1pp |
| Hit +/-30 | 36.5% | 39.4% | +2.9pp |
| WMAPE | 51.0% | 47.4% | -3.6pp |
| Bias | -21.3% | -10.5% | +10.7pp |
| Phantom | 41.0% | 41.0% | +0.0pp |

## Promotion Gates

| Gate | Required | Observed | Status |
| --- | --- | --- | --- |
| Hit +/-20 vs champion | >= +1.0pp, or >= +0.5pp with WMAPE/bias improvement | +2.1pp | PASS |
| WMAPE vs champion | <= 0.0pp | -3.6pp | PASS |
| Bias vs champion | > 0.0pp is improvement | +10.7pp | PASS |
| Phantom vs champion | <= 0.0pp | +0.0pp | PASS |
| Largest non-stress WMAPE regression (2024-08-26) | <= +2.0pp | +0.0pp | PASS |

## Candidate Results

| Model | Rows | Qty scored | Hit +/-20 | Delta vs champion | Hit +/-30 | WMAPE | WMAPE delta | Bias | Bias delta | Phantom | Phantom delta |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| sk_blend_post_bf_safe | 5,346 | 2,967 | 23.4% | -2.0pp | 34.8% | 55.7% | +4.7pp | -17.0% | +4.3pp | 43.5% | +2.5pp |
| 8gf_regular_plus_post_bf_safe | 5,346 | 2,967 | 25.3% | +0.0pp | 36.5% | 51.0% | +0.0pp | -21.3% | +0.0pp | 41.0% | +0.0pp |
| 8go_pre_bf_bfc_lift_130 | 5,346 | 2,967 | 26.6% | +1.3pp | 38.5% | 48.7% | -2.3pp | -17.2% | +4.0pp | 41.0% | +0.0pp |
| 8go_pre_bf_bfc_lift_140 | 5,346 | 2,967 | 26.8% | +1.5pp | 38.8% | 48.2% | -2.8pp | -15.9% | +5.4pp | 41.0% | +0.0pp |
| 8go_pre_bf_bfc_lift_150 | 5,346 | 2,967 | 27.0% | +1.7pp | 39.3% | 47.8% | -3.2pp | -14.6% | +6.7pp | 41.0% | +0.0pp |
| 8go_pre_bf_bfc_lift_160 | 5,346 | 2,967 | 27.1% | +1.8pp | 39.3% | 47.5% | -3.5pp | -13.2% | +8.1pp | 41.0% | +0.0pp |
| 8go_pre_bf_bfc_lift_180 | 5,346 | 2,967 | 27.4% | +2.1pp | 39.4% | 47.4% | -3.6pp | -10.5% | +10.7pp | 41.0% | +0.0pp |
| 8go_pre_bf_bfc_lift_200 | 5,346 | 2,967 | 27.2% | +1.9pp | 39.4% | 47.7% | -3.3pp | -7.9% | +13.4pp | 41.0% | +0.0pp |
| 8go_pre_bf_bfc_lift_150_floor5 | 5,346 | 2,967 | 26.7% | +1.4pp | 38.8% | 48.0% | -3.0pp | -14.9% | +6.4pp | 41.0% | +0.0pp |
| 8go_pre_bf_bfc_lift_180_floor5 | 5,346 | 2,967 | 27.1% | +1.8pp | 38.7% | 47.7% | -3.3pp | -11.1% | +10.2pp | 41.0% | +0.0pp |
| 8go_nonpost_ex_decjan_lift_150 | 5,346 | 2,967 | 27.0% | +1.7pp | 39.3% | 47.8% | -3.2pp | -14.6% | +6.7pp | 41.0% | +0.0pp |
| 8go_nonpost_ex_decjan_lift_180 | 5,346 | 2,967 | 27.4% | +2.1pp | 39.4% | 47.4% | -3.6pp | -10.5% | +10.7pp | 41.0% | +0.0pp |

## Revenue Scope Validation - 8go_pre_bf_bfc_lift_180

| Scope | Rows | Qty scored | Actual revenue | Champion hit +/-20 | Candidate hit +/-20 | Hit delta | Champion WMAPE | Candidate WMAPE | WMAPE delta | Champion bias | Candidate bias | Bias delta | Champion phantom | Candidate phantom | Phantom delta |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Top 100 | 475 | 349 | 19,774,645 | 27.8% | 32.1% | +4.3pp | 43.0% | 39.6% | -3.4pp | -9.6% | -1.1% | +8.5pp | 62.1% | 62.1% | +0.0pp |
| Top 250 | 1,373 | 943 | 39,557,500 | 27.4% | 31.0% | +3.6pp | 46.6% | 43.1% | -3.5pp | -18.6% | -9.0% | +9.6pp | 55.7% | 55.7% | +0.0pp |
| Top 500 | 2,866 | 1,751 | 59,034,164 | 25.5% | 28.1% | +2.6pp | 49.9% | 46.2% | -3.7pp | -18.9% | -9.0% | +9.9pp | 46.7% | 46.7% | +0.0pp |
| Top 750 | 4,140 | 2,384 | 70,548,177 | 25.4% | 28.4% | +3.1pp | 50.5% | 46.9% | -3.7pp | -20.0% | -10.1% | +9.9pp | 42.3% | 42.3% | +0.0pp |
| Top 1000 | 5,346 | 2,967 | 79,136,333 | 25.3% | 27.4% | +2.1pp | 51.0% | 47.4% | -3.6pp | -21.3% | -10.5% | +10.7pp | 41.0% | 41.0% | +0.0pp |

## Critical Slice Validation - 8go_pre_bf_bfc_lift_180

| Slice | Rows | Qty scored | Actual revenue | Champion hit +/-20 | Candidate hit +/-20 | Hit delta | Champion WMAPE | Candidate WMAPE | WMAPE delta | Champion bias | Candidate bias | Bias delta | Champion phantom | Candidate phantom | Phantom delta |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Available/proxy regular | 1,462 | 1,026 | 22,650,364 | 33.1% | 33.1% | +0.0pp | 43.1% | 43.1% | +0.0pp | -6.0% | -6.0% | +0.0pp | 68.4% | 68.4% | +0.0pp |
| BF/campaign-sensitive route | 2,134 | 1,184 | 33,838,656 | 18.6% | 23.9% | +5.3pp | 57.4% | 49.6% | -7.8pp | -31.2% | -8.3% | +22.9pp | 46.2% | 46.2% | +0.0pp |
| Pre-BF BF/campaign-sensitive | 586 | 465 | 16,915,309 | 15.7% | 29.2% | +13.5pp | 56.1% | 43.0% | -13.1pp | -51.7% | -13.2% | +38.5pp | 35.2% | 35.2% | +0.0pp |
| Normal-calendar BF/campaign-sensitive | 966 | 509 | 12,396,579 | 21.6% | 21.6% | +0.0pp | 54.7% | 54.7% | +0.0pp | -18.3% | -18.3% | +0.0pp | 39.2% | 39.2% | +0.0pp |
| Any campaign/BF history 13w | 4,245 | 2,351 | 63,056,072 | 24.7% | 26.8% | +2.2pp | 51.5% | 47.5% | -4.0pp | -19.5% | -9.9% | +9.7pp | 45.3% | 45.3% | +0.0pp |
| 2024-11-25 stress window | 684 | 253 | 5,426,480 | 17.8% | 17.8% | +0.0pp | 70.9% | 70.9% | +0.0pp | 38.0% | 38.0% | +0.0pp | 57.1% | 57.1% | +0.0pp |
| 2024-12-30 failed 8G-K window | 661 | 315 | 7,688,500 | 21.3% | 21.3% | +0.0pp | 58.3% | 58.3% | +0.0pp | -9.0% | -9.0% | +0.0pp | 38.1% | 38.1% | +0.0pp |
| 2025-01-27 guard window | 646 | 352 | 9,089,493 | 24.1% | 24.1% | +0.0pp | 49.4% | 49.4% | +0.0pp | -21.8% | -21.8% | -0.0pp | 30.1% | 30.1% | +0.0pp |

## Window Validation - 8go_pre_bf_bfc_lift_180

| Target start | Rows | Qty scored | Actual revenue | Champion hit +/-20 | Candidate hit +/-20 | Hit delta | Champion WMAPE | Candidate WMAPE | WMAPE delta | Champion bias | Candidate bias | Bias delta | Champion phantom | Candidate phantom | Phantom delta |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2024-08-26 | 705 | 427 | 10,378,783 | 27.9% | 27.9% | +0.0pp | 46.2% | 46.2% | +0.0pp | -26.9% | -26.9% | +0.0pp | 31.1% | 31.1% | +0.0pp |
| 2024-09-23 | 700 | 428 | 10,174,878 | 35.7% | 35.7% | +0.0pp | 45.8% | 45.8% | +0.0pp | 4.5% | 4.5% | +0.0pp | 49.5% | 49.5% | +0.0pp |
| 2024-10-28 | 688 | 546 | 20,478,496 | 15.8% | 27.3% | +11.5pp | 54.9% | 43.2% | -11.7pp | -50.8% | -16.4% | +34.4pp | 31.3% | 31.3% | +0.0pp |
| 2024-11-25 | 684 | 253 | 5,426,480 | 17.8% | 17.8% | +0.0pp | 70.9% | 70.9% | +0.0pp | 38.0% | 38.0% | +0.0pp | 57.1% | 57.1% | +0.0pp |
| 2024-12-30 | 661 | 315 | 7,688,500 | 21.3% | 21.3% | +0.0pp | 58.3% | 58.3% | +0.0pp | -9.0% | -9.0% | +0.0pp | 38.1% | 38.1% | +0.0pp |
| 2025-01-27 | 646 | 352 | 9,089,493 | 24.1% | 24.1% | +0.0pp | 49.4% | 49.4% | +0.0pp | -21.8% | -21.8% | -0.0pp | 30.1% | 30.1% | +0.0pp |
| 2025-02-24 | 641 | 318 | 8,005,057 | 32.4% | 32.4% | +0.0pp | 43.2% | 43.2% | +0.0pp | -17.0% | -17.0% | +0.0pp | 37.2% | 37.2% | +0.0pp |
| 2025-03-24 | 621 | 328 | 7,894,646 | 28.4% | 28.4% | +0.0pp | 42.1% | 42.1% | +0.0pp | -4.4% | -4.4% | +0.0pp | 42.1% | 42.1% | +0.0pp |

## Interpretation

- This phase deliberately avoids the broad 8G-K non-post-BF lift that overcorrected 2024-12-30 and 2025-01-27.
- The best candidate is still validation-window calibration on known Phase 8G windows, not independent future holdout evidence.
- The business interpretation is narrow: SKUs already classified as BF/campaign-sensitive need stronger pre-BF demand lift, but not automatic normal-calendar December/January lift.
- This candidate should go to the final promotion pack before replacing the official high-revenue policy.

## Outputs

- Input score rows: `/Users/fyodorgolovin/Downloads/Supply-Inventory v1.0 codex/active_docs/ITER5AC_V2_PHASE8G_N_SCORE_ROWS.csv`.
- Output score rows: `/Users/fyodorgolovin/Downloads/Supply-Inventory v1.0 codex/active_docs/ITER5AD_V2_PHASE8G_O_SCORE_ROWS.csv`.
