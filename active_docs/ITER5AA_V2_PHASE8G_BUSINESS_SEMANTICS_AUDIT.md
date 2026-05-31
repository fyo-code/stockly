# Iteration 5AA - V2 Phase 8G-L Business Semantics Audit

Generated: 2026-05-26 18:57

## Decision

Decision: `KEEP_CURRENT_CHAMPION_AND_RELABEL_STOCK_SEMANTICS`.

Mobexpert stock should not be interpreted as a hard can-sell / cannot-sell gate. Active/orderable SKU status is the missing sellability signal. Existing stock quantities may still be useful, but only as fulfillment/friction/context signals.

The audit below does not change production behavior. It checks whether the current Top 1000 champion depends on stock-as-availability semantics and whether a stock-soft policy looks promising using the official 8G-K exported rows.
Important scope note: this is a route-blending sensitivity check over exported predictions. It does not retrain models, ablate stock features from the base estimators, or prove how much the fitted trees depend on stock features.
Promotion screen for this audit: candidate hit +/-20 must improve by more than +0.5pp versus the current champion while WMAPE is non-worse. The best stock-soft candidate improved hit +/-20 by +0.4pp and WMAPE by -0.2pp, so it is directional but below the promotion screen.

## Raw Data Semantics Audit

| Area | Count | Observed detail | Assessment |
| --- | --- | --- | --- |
| Returns are ingested | 80,495 | 310,542.3 returned units / 7.7% of gross positive units | Important but not ignored; target currently predicts positive units, not net units. |
| Return value sign alignment | 1 | 80,367 negative-quantity rows also have negative value | Only rows with negative quantity and positive value are a likely revenue-sign issue. |
| Discounts are ingested | 1,349,006 | 22.3% avg finite fractional discount; 172 finite >1 rows; 61 infinite rows | Used as lag/campaign memory, but needs invalid-value cleanup plus scale normalization checks. |
| Weekly discount aggregates poisoned by infinity | 61 | 61 max-discount weekly rows are infinite | Small row count, but must be cleaned because tree models can react badly to infinite values. |
| Campaign/BF fields are present | 1,004,879 | 124,133 observed BF rows; 110,432 inferred BF rows | Used as history; still missing future campaign membership / SKU assignment plan. |
| VECHIME / collection age exists only in stock snapshots | 63,451 | 39,569 SKUs with collection age; 13,987 rows with stock-entry date | Useful, but not currently safe as historical backtest input unless as-of dates are available. |

## Stock-Semantics Policy Simulation

| Candidate | Rows | Qty scored | Hit +/-20 | Delta vs champion | Hit +/-30 | WMAPE | WMAPE delta | Bias | Phantom | Meaning |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 8gf_regular_plus_post_bf_safe | 5,346 | 2,967 | 25.3% | +0.0pp | 36.5% | 51.0% | +0.0pp | -21.3% | 41.0% | official current champion |
| 8gl_champion_without_regular_stock_gate | 5,346 | 2,967 | 24.3% | -1.0pp | 35.9% | 51.1% | +0.1pp | -23.2% | 40.9% | removes regular-route stock gate replacement |
| 8gl_demand_regular_plus_post_bf_safe | 5,346 | 2,967 | 25.7% | +0.4pp | 36.9% | 50.9% | -0.2pp | -19.8% | 41.2% | uses demand regularity, not stock availability, for extra-trees replacement |
| 8gl_demand_regular_no_campaign_plus_post_bf_safe | 5,346 | 2,967 | 24.4% | -0.9pp | 35.7% | 51.2% | +0.2pp | -22.3% | 41.1% | same, but excludes recent campaign/BF history |
| 8gl_stock_constrained_as_regular_plus_post_bf_safe | 5,346 | 2,967 | 25.5% | +0.2pp | 36.7% | 50.9% | -0.1pp | -20.7% | 41.2% | treats stock-constrained regular-demand rows as sellable regular rows |

## Current Route Diagnostic

| Route | Rows | Qty scored | Champion hit +/-20 | Control hit +/-20 | ExtraTrees hit +/-20 | Champion WMAPE | Control WMAPE | ExtraTrees WMAPE | Champion bias |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| bf_campaign_sensitive | 2,134 | 1,184 | 18.6% | 16.6% | 18.9% | 57.4% | 65.4% | 68.3% | -31.2% |
| available_regular | 986 | 703 | 35.1% | 32.4% | 35.1% | 41.1% | 41.5% | 41.1% | -3.7% |
| stock_constrained | 886 | 492 | 26.8% | 25.8% | 26.2% | 44.5% | 50.7% | 51.3% | -16.5% |
| sparse_intermittent | 738 | 215 | 17.7% | 17.7% | 18.6% | 66.1% | 66.1% | 66.4% | -49.9% |
| proxy_available_regular | 476 | 323 | 28.8% | 25.4% | 28.8% | 47.9% | 47.9% | 47.9% | -11.8% |
| availability_unknown | 67 | 23 | 39.1% | 39.1% | 30.4% | 38.7% | 38.7% | 42.4% | -9.4% |
| lifecycle_decline | 49 | 23 | 52.2% | 52.2% | 43.5% | 47.0% | 47.0% | 43.9% | -20.6% |
| seasonal_active | 9 | 4 | 0.0% | 0.0% | 0.0% | 78.9% | 78.9% | 69.6% | -56.2% |
| seasonal_quiet | 1 | 0 | - | - | - | - | - | - | - |

## Business-Semantic Masks

| Mask | Rows | Qty scored | Champion hit +/-20 | Control hit +/-20 | ExtraTrees hit +/-20 | Champion WMAPE | Control WMAPE | ExtraTrees WMAPE | Champion bias |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Current regular/proxy route | 1,462 | 1,026 | 33.1% | 30.2% | 33.1% | 43.1% | 43.4% | 43.1% | -6.0% |
| Stock-constrained current route | 886 | 492 | 26.8% | 25.8% | 26.2% | 44.5% | 50.7% | 51.3% | -16.5% |
| Demand-regular no stock semantics | 2,871 | 1,860 | 30.9% | 29.2% | 31.5% | 44.7% | 44.8% | 44.4% | -8.8% |
| Demand-regular no campaign/BF | 605 | 403 | 33.5% | 32.3% | 33.3% | 43.3% | 42.5% | 43.3% | -5.7% |
| Stock-constrained but demand-regular | 525 | 335 | 31.6% | 31.6% | 33.1% | 39.6% | 39.6% | 38.5% | -7.6% |
| Post-BF stress override | 639 | 252 | 17.9% | 6.7% | 7.5% | 70.9% | 139.9% | 165.8% | 37.9% |

## Window Check - Demand-Regular Stock-Soft Candidate

| Target start | Qty scored | Champion hit +/-20 | Candidate hit +/-20 | Hit delta | Champion WMAPE | Candidate WMAPE | WMAPE delta | Champion bias | Candidate bias |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2024-08-26 | 427 | 27.9% | 28.3% | +0.5pp | 46.2% | 46.0% | -0.2pp | -26.9% | -26.6% |
| 2024-09-23 | 428 | 35.7% | 35.0% | -0.7pp | 45.8% | 45.4% | -0.4pp | 4.5% | 6.0% |
| 2024-10-28 | 546 | 15.8% | 15.8% | +0.0pp | 54.9% | 54.9% | +0.0pp | -50.8% | -50.8% |
| 2024-11-25 | 253 | 17.8% | 17.8% | +0.0pp | 70.9% | 70.9% | +0.0pp | 38.0% | 38.0% |
| 2024-12-30 | 315 | 21.3% | 24.1% | +2.9pp | 58.3% | 58.7% | +0.4pp | -9.0% | 2.7% |
| 2025-01-27 | 352 | 24.1% | 26.1% | +2.0pp | 49.4% | 48.3% | -1.1pp | -21.8% | -19.9% |
| 2025-02-24 | 318 | 32.4% | 31.4% | -0.9pp | 43.2% | 43.4% | +0.2pp | -17.0% | -15.4% |
| 2025-03-24 | 328 | 28.4% | 28.4% | +0.0pp | 42.1% | 41.8% | -0.3pp | -4.4% | -3.3% |

## Interpretation

- Discounts were not ignored: they are ingested and used as lag/campaign-history features. They are under-modeled as future price/promotion intent, and 61 infinite raw discount rows should be cleaned.
- Discount cleanup should also inspect finite `discount_pct > 1` rows. They may be valid percent-scale values rather than bad rows, but they should not silently mix with fraction-scale discount values.
- Returns were not ignored: negative quantities become returned units, and return-rate lag features exist. The main target is positive sold units, so returns do not reduce demand target. That is acceptable for gross demand, but net units/revenue should be a separate business output.
- Campaign fields were used heavily as historical signals. The remaining gap is not `CAMPANIE` availability; it is future SKU campaign membership, intensity, and whether a BF label means planned BF SKU versus later campaign assignment.
- `VECHIME IN COLECTIE` exists in stock snapshot data and is stored in `stock_snapshot_store_v2`, but it is not used in official historical backtests because most available rows are current/snapshot-like rather than reliable historical-as-of features.
- Stock semantics need correction. Current labels such as `available_regular` and `stock_constrained` should be treated as historical stock-position context, not true sellability. The missing high-value field is active/orderable/listed SKU status by date.

## Recommended Next Action

- Do not promote another stock-gated candidate yet.
- First, clean invalid discount values and rename/reframe stock-derived route language as fulfillment context.
- Then run one stock-soft Top 1000 rebuild where regular-demand routing is based on demand regularity and active SKU assumptions, not positive stock.
- If that rebuild improves or matches the current champion without stock-as-sellability assumptions, continue with guarded BF/campaign lift. If it fails, keep the 8G-I champion and wait for active/orderable SKU data.

## Sources

- Official score rows: `/Users/fyodorgolovin/Downloads/Supply-Inventory v1.0 codex/active_docs/ITER5Z_V2_PHASE8G_OFFICIAL_CALIBRATED_SCORE_ROWS.csv`.
- Raw DB tables: `raw_sales_transactions_v2`, `weekly_chain_demand_v2`, `stock_snapshot_store_v2`.
