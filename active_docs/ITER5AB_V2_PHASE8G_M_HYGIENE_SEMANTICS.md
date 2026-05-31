# Iteration 5AB - V2 Phase 8G-M Hygiene And Business Semantics

Generated: 2026-05-27 00:09
Route version: `v2_routes_2026_05_26_stock_position`

## Decision

Decision: `HYGIENE_PASS_KEEP_CHAMPION_BASELINE`.

Discount features now exclude non-finite values and finite values above fraction scale. Stock-derived route wording is reframed as stock-position / fulfillment context, not can-sell availability. The gross positive demand target remains unchanged, while returns stay available as diagnostic features.

## Raw Data Hygiene

| Area | Rows / units | Invalid/anomalous | Action |
| --- | --- | --- | --- |
| Raw discount rows | 2,007,007 | 172 finite >1; 61 infinite; max finite 186,276.8 | Excluded from model discount features unless later database evidence proves a percent-scale convention. |
| Weekly discount aggregates | 1,226,529 | 136 avg >1; 141 max >1; 61/61 avg/max infinite | Sanitized in the feature builder so old DB aggregates cannot poison model inputs. |
| Returns | 310,542.3 returned units | 7.7% of gross positive units; 1 negative-qty positive-value rows | Kept separate from gross demand target; return-rate features remain diagnostics/context. |

## Feature Matrix Hygiene

| Check | Observed | Status |
| --- | --- | --- |
| Rows | 8,227 | INFO |
| Numeric feature columns | 131 | INFO |
| Non-finite numeric cells | 0 | PASS |
| Discount feature cells > 1 | 0 | PASS |
| Max discount feature value | 95.0% | PASS |
| Max 13w / 52w return rate | 100.0% / 45.7% | INFO |

## Official Top 1000 Rerun

| Metric | Previous champion | Cleaned champion | Delta |
| --- | --- | --- | --- |
| Hit +/-20 | 25.3% | 25.3% | +0.0pp |
| WMAPE | 51.0% | 51.0% | +0.0pp |
| Phantom | 41.0% | 41.0% | -0.0pp |

| Model | Rows | Qty scored | Hit +/-20 | Delta vs control | Hit +/-30 | WMAPE | Bias | Phantom |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| sk_blend_post_bf_safe | 5,346 | 2,967 | 23.4% | +0.0pp | 34.8% | 55.7% | -17.0% | 43.5% |
| 8gf_regular_plus_post_bf_safe | 5,346 | 2,967 | 25.3% | +2.0pp | 36.5% | 51.0% | -21.3% | 41.0% |
| sk_extra_trees | 5,346 | 2,967 | 25.3% | +1.9pp | 36.0% | 57.0% | -10.4% | 45.7% |
| post_bf_safe_naive | 5,346 | 2,967 | 22.2% | -1.1pp | 32.9% | 52.9% | -24.8% | 65.9% |
| median_naive | 5,346 | 2,967 | 21.4% | -2.0pp | 32.2% | 57.3% | -18.9% | 69.3% |

## Window Check

| Target start | Qty scored | Control hit +/-20 | Champion hit +/-20 | Hit delta | Control WMAPE | Champion WMAPE | WMAPE delta | Champion phantom |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2024-08-26 | 427 | 25.3% | 27.9% | +2.6pp | 47.5% | 46.2% | -1.3pp | 31.1% |
| 2024-09-23 | 428 | 34.1% | 35.7% | +1.6pp | 46.0% | 45.8% | -0.3pp | 49.5% |
| 2024-10-28 | 546 | 15.8% | 15.8% | +0.0pp | 54.9% | 54.9% | +0.0pp | 31.3% |
| 2024-11-25 | 253 | 6.7% | 17.8% | +11.1pp | 139.8% | 70.9% | -68.8pp | 57.1% |
| 2024-12-30 | 315 | 21.0% | 21.3% | +0.3pp | 58.5% | 58.3% | -0.1pp | 38.1% |
| 2025-01-27 | 352 | 24.1% | 24.1% | +0.0pp | 49.3% | 49.4% | +0.1pp | 30.1% |
| 2025-02-24 | 318 | 29.2% | 32.4% | +3.1pp | 43.8% | 43.2% | -0.6pp | 37.2% |
| 2025-03-24 | 328 | 28.0% | 28.4% | +0.3pp | 40.3% | 42.1% | +1.8pp | 42.1% |

## Interpretation

- Phase 8G-M is a correctness phase, not a promotion phase.
- If the cleaned champion does not materially improve, the cleaned feature path still becomes the baseline for 8G-N because it removes known bad discount math.
- Current stock features remain usable only as stock-position / fulfillment context. They must not be described as proof that an SKU could or could not sell.
- The target remains positive sold units because returns represent post-sale behavior, not missing demand.

## Outputs

- Score rows: `/Users/fyodorgolovin/Downloads/Supply-Inventory v1.0 codex/active_docs/ITER5AB_V2_PHASE8G_M_SCORE_ROWS.csv`.
- Skipped windows: `2024-04-29`, `2024-05-27`, `2024-07-01`, `2024-07-29`.
