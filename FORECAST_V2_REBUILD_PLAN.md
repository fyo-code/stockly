# Forecast V2 Rebuild Plan

Date: 2026-05-09
Updated: 2026-05-11

## 1. Decision Summary

The forecast engine should be rebuilt as a parallel `forecast_v2` track, not by continuing to tune the current median ensemble.

The current engine remains useful as a benchmark, but it should not be the main path toward the accuracy target. Iteration 4 proved that optimizing aggregate WMAPE can reduce individual SKU usefulness: WMAPE improved, but hit +/-20% regressed. The new engine must optimize the business KPI directly.

All new v2 implementation files should live in `backend/forecast_engine_v2/`. The legacy `backend/forecast_engine/` package remains frozen except for benchmark compatibility fixes.

Locked headline target:

> Achieve 80%+ hit +/-20% on forecastable revenue movers at chain level.

This target combines revenue importance and statistical forecastability:

- Start from the SKU set that covers about 80% of rolling 12-month chain revenue.
- Keep SKUs that genuinely move enough to forecast, including seasonal movers.
- Separate sparse expensive items from the headline KPI so they do not make the target mathematically unfair.
- Track the full catalog, but do not claim 80% accuracy on all SKUs.

This is not pure "top revenue" and not pure "high volume." It is the business-relevant middle: products that matter financially and have enough demand signal to model.

## 2. What Changes From The Old Engine

Keep and reuse:

- CSV ingestion approach, after upgrading it for multi-store data.
- Category normalization and sales/return cleaning.
- Romanian calendar features.
- Existing walk-forward backtesting discipline.
- Current Iter 3 / Iter 4 engines as frozen benchmarks.
- Active docs and scorecard habit.

Replace in the v2 candidate path:

- Per-store-first forecasting.
- Median ensemble as the main forecast.
- ETS.
- Uniform per-method bias correction.
- Post-hoc seasonal dampening.
- WMAPE-first acceptance gates.
- Recursive week-by-week forecasting as the primary model target.

New v2 principles:

- Forecast chain total first, then allocate to stores later.
- Predict the next 4-week total directly.
- Use regimes: forecastable revenue movers, seasonal revenue movers, active movers, long-tail active, dormant.
- Use different methods by regime instead of one method pool for every SKU.
- Optimize hit +/-20% on the locked target population first.

## 3. Data Strategy

Available store coverage:

| Store | Type | Years |
|---|---|---|
| Constanta | hyperstore | 2022, 2023, 2024, 2025 |
| Brasov | hyperstore | 2022, 2023, 2024, 2025 |
| Pipera | hyperstore | 2022, 2023, 2024, 2025 |
| Pantelemon | hyperstore | 2022, 2023, 2024, 2025 |
| Baneasa | hyperstore | 2024, 2025 |
| Sibiu | hyperstore | 2022, 2023, 2024, 2025 |
| Oradea | smaller store | 2022, 2023, 2024, 2025 |
| Ploiesti | smaller store | 2023, 2024, 2025 |
| Iasi | hybrid | 2022, 2023, 2024, 2025 |
| Timisoara | smaller store | 2022, 2023, 2024, 2025 |

The old data spec must be corrected: `MAGAZIN` is no longer redundant. It is now a key modeling field and must be preserved as the store identifier.

`DATA COMANDA` is the source of truth for sale timing. The filename/export year is provenance only. If a row appears in a 2024 export but `DATA COMANDA` is in 2023, the row belongs to 2023 for training, scoring, and backtesting.

Store names from `MAGAZIN` should be normalized into canonical store IDs, for example:

- `M & D RETAIL CONSTANTA SRL` -> `constanta`
- `M & D RETAIL PIPERA SRL` -> `pipera`
- `MOBEXPERT BANEASA SRL` -> `baneasa`

The importer must support late-arriving files. New store/year files can be added later and re-ingested without rebuilding the design. Use source-file tracking and transaction-line deduplication so adding `ploiesti_24` or other missing exports updates coverage without double-counting old rows.

The richer CSV fields should be kept when present:

- discount depth
- campaign type, including Black Friday and named campaigns
- campaign start/end when available
- detailed category, class, subcategory
- item size, type, and dimensions
- supplier fields
- returns
- order ID / basket ID

Product text and hierarchy should be treated as model signal, not discarded. `DENUMIRE ARTICOL` is the most detailed product description available and should be parsed for product type, dimensions, variant family, material/color/style tokens where reliable, and size buckets. `CATEGORIE`, `CLASA`, `SUBCLASA`, `GRUPA`, `GRUPA DIRECTII_LICITATII`, and raw `RAION` should all be preserved as categorical hierarchy/channel features.

Campaign interpretation:

- `CAMPANIE` is active on the sale row, but it mixes temporary campaigns with product/program labels such as `FABRO` / `FABRICAT IN ROMANIA` and product-logic labels such as `PATSPRING`.
- `CAMPANIE BF` is the stronger signal for actual Black Friday participation and timing in the current data year.
- Generic `CAMPANIE` values such as `BF 2021 promotii` in a later export should not be treated as proof that the sale happened during Black Friday of the later year.

Feature signal policy:

- Missing optional detail fields must not be treated as proof that the signal is false.
- Every important optional feature should carry a source/confidence field: `observed`, `inferred`, or `unknown`.
- For Black Friday and campaign timing, `observed` means the row/file contains direct evidence such as `CAMPANIE BF`.
- `inferred` means the signal was derived from reliable patterns: known chain/store Black Friday windows, calendar Black Friday timing, discount spikes, same-SKU behavior in richer stores, or repeated cross-store campaign patterns.
- `unknown` means there is not enough reliable evidence either way.
- Baneasa, Pipera, or any lower-detail schema with missing `CAMPANIE BF`, supplier, subclass, or dimension fields must keep those fields as unknown/low-confidence instead of treating them as no campaign, no supplier, no subclass, or no dimensions.
- The model may use inferred signals, but scorecards and audits must be able to separate observed performance from inferred-signal performance.

Data layers to build:

1. Raw immutable transaction import.
2. Cleaned sales transactions.
3. Weekly store demand: one row per SKU, store, week.
4. Weekly chain demand: one row per SKU, week, summed across stores.
5. Store coverage table: which stores are present for each week.
6. Campaign/promo week table.
7. Feature signal registry: observed/inferred/unknown flags for campaign, hierarchy, dimensions, and other optional metadata.
8. Regime labels.
9. V2 predictions.
10. V2 scorecards.

Important coverage rule:

- Because Baneasa only has 2024-2025, year-over-year chain features must use like-for-like store coverage. Do not compare a 2025 chain total including Baneasa to a 2023 chain total where Baneasa is missing and treat the difference as real demand growth.

## 4. Target Population And Regimes

Primary target: `forecastable_revenue_movers`.

Initial definition:

1. Compute trailing 12-month chain revenue by SKU.
2. Sort SKUs by revenue descending.
3. Select the smallest SKU set covering about 80% of chain revenue.
4. Within that revenue set, classify forecastability using rolling 4-week chain demand windows.
5. The headline KPI includes SKUs/windows with enough movement to forecast fairly.

Recommended first-pass regime definitions:

| Regime | Meaning | Forecasting treatment |
|---|---|---|
| forecastable_revenue_movers | Top revenue SKUs with recurring movement signal | Headline KPI, direct 4-week model |
| seasonal_revenue_movers | Revenue-important SKUs with clear active and quiet seasons | Quantity accuracy during active windows; zero/reactivation correctness during quiet windows |
| active_movers | Regular movers outside headline revenue set | Secondary KPI and model validation |
| long_tail_active | Low-volume SKUs that sometimes sell | Sale/no-sale classifier plus low-unit quantity estimate |
| sparse_revenue_items | Expensive but too sparse for fair +/-20% scoring | Track separately; do not include in headline 80% KPI |
| dormant | No meaningful recent or seasonal signal | Forecast zero unless reactivation evidence exists |

This classification must be recalculated from the full multi-store chain dataset. The thresholds should be printed in the first scorecard and can be adjusted once the real distribution is visible.

## 5. Modeling Methodology

### 5.1 Forecast Unit

Phase 1 forecast unit:

> SKU chain total for the next 4 weeks.

Do not forecast each store separately in phase 1. Store-level allocation comes after chain-level accuracy is proven.

### 5.2 Primary Model

For forecastable revenue movers:

- Use a direct 4-week LightGBM count model, preferably Tweedie or Poisson-style objective.
- Target is `chain_units_next_4w`, not weekly units.
- Train on chain-level weekly snapshots.
- Predict two adjacent 4-week blocks for a two-month test.

Core feature groups:

- Own demand lags: 1, 2, 4, 8, 13, 26, 52 weeks.
- Rolling demand: 4, 8, 13, 26 week means and volatility.
- Same-period-last-year demand.
- Category/subcategory/class demand and trend.
- Store breadth: number of stores selling recently.
- Hyperstore share and mall-store share.
- Bucharest hyperstore signal: Baneasa, Pipera, Pantelemon.
- Discount depth.
- Campaign type and campaign timing.
- Calendar: month, week-of-year, holidays, Black Friday, salary periods, construction/summer season.
- Product attributes: size, dimensions, type, class, detailed category when available.
- Returns and net demand.

### 5.3 Seasonal Movers

Seasonal movers stay inside the business target when they are revenue-important and move predictably in season.

Scoring must distinguish:

- Active-season quantity accuracy: hit +/-20%.
- Quiet-season correctness: did the model correctly avoid phantom demand?
- Reactivation correctness: did the model detect that a seasonal SKU wakes up again?

Do not treat every quiet-season zero as a forecasting failure.

### 5.4 Long Tail And Dormant SKUs

For long-tail active SKUs:

- First model: probability of any sale in the next 4 weeks.
- Second model: conditional low-unit quantity if sale probability is high enough.
- Main purpose: reduce phantom demand.

For dormant SKUs:

- Forecast zero by default.
- Allow reactivation only when evidence exists: same-season prior-year sales, active campaign, renewed store breadth, or stock/availability return if stock data exists.

### 5.5 Store Allocation, Later

After chain-level forecasts win:

- Allocate chain forecast back to stores.
- Use recent store share, same-period-last-year store share, store type, local campaign/stock signals, and store-specific trend.
- Store-level accuracy is phase 2, not the first target.

## 6. Testing Methodology

Keep the previous train/predict/compare loop, but separate tuning from official claims.

### 6.1 Inner Loop

Purpose: model selection, feature selection, regime threshold tuning.

Use rolling historical windows. Example:

- Train through Dec 2023, predict Jan-Feb 2024.
- Train through Feb 2024, predict Mar-Apr 2024.
- Train through Apr 2024, predict May-Jun 2024.
- Train through Jun 2024, predict Jul-Aug 2024.
- Train through Aug 2024, predict Sep-Oct 2024.
- Train through Oct 2024, predict Nov-Dec 2024.

Use these windows to reject weak ideas quickly.

### 6.2 Outer Loop

Purpose: official result.

Use one untouched blind two-month window after model selection.

Example cadence:

- Iter 5: train through Dec 2024, predict Jan-Feb 2025.
- Iter 6: train through Feb 2025, predict Mar-Apr 2025.
- Iter 7: train through Apr 2025, predict May-Jun 2025.
- Iter 8: train through Jun 2025, predict Jul-Aug 2025 if actuals exist.

Never tune on the same window used to claim improvement.

### 6.3 Scorecard

Every iteration must report:

- forecastable revenue mover hit +/-20
- forecastable revenue mover hit +/-30
- seasonal mover active-window hit +/-20
- seasonal mover quiet-window zero correctness
- active mover hit +/-20
- long-tail sale/no-sale precision and recall
- phantom demand rate
- underprediction rate
- overprediction rate
- wins vs naive seasonal
- WMAPE and bias as diagnostics only
- accuracy by revenue bucket
- accuracy by volume bucket
- accuracy by category/subcategory/class
- accuracy by store type coverage
- accuracy during campaign and non-campaign windows

Acceptance gate before any app/API cutover:

- V2 beats frozen Iter 3 and Iter 4 on forecastable revenue mover hit +/-20.
- V2 reaches or approaches 80% hit +/-20 on the headline population.
- The result holds across two consecutive blind two-month windows.
- Phantom demand does not materially worsen.

## 7. Implementation Sequence

### Iteration 5A: Data Foundation And Measurement Reset

Goal: create the truth base before modeling.

Tasks:

1. Update the CSV/data spec for multi-store and richer fields.
2. Upgrade ingestion so `MAGAZIN` becomes `store_id`, not a hardcoded store.
3. Add store type metadata.
4. Ingest all available 2022-2025 store files.
5. Build weekly store demand.
6. Build weekly chain demand.
7. Build store coverage and like-for-like coverage logic.
8. Build v2 hierarchy normalizer so `CATEGORIE`, `CLASA`, `SUBCLASA`, `GRUPA`, `RAION`, and product-name text can reduce the large `NECUNOSCUT` bucket, especially in lower-detail Pipera-style files.
9. Build the observed/inferred/unknown feature signal layer for campaign/BF timing, hierarchy, dimensions, and other optional fields.
10. Build cutoff-specific regime labels.
11. Build v2 scorecard.
12. Run v2-native naive benchmarks through the new scorecard.
13. Treat frozen Iter 3 / Iter 4 as historical context until they are adapted to the same chain-level population, horizon, and target windows.

Expected outcome:

- No major model accuracy gain yet.
- Clean data foundation and a trustworthy measurement layer.

### Iteration 5B: First V2 Candidate

Goal: first direct 4-week model for forecastable revenue movers.

Tasks:

1. Build direct 4-week LightGBM Tweedie candidate.
2. Train only on chain-level demand.
3. Score against inner-loop windows.
4. Run one blind two-month outer-loop prediction.
5. Compare against frozen Iter 3, frozen Iter 4, and naive seasonal.

Expected outcome:

- Significant improvement versus old engine on forecastable revenue movers.
- First realistic estimate of how close the 80% target is.

### Iteration 6: Seasonal And Long-Tail Routing

Goal: stop treating all demand patterns as one problem.

Tasks:

1. Add seasonal mover treatment.
2. Add long-tail sale/no-sale classifier.
3. Add dormant reactivation rules.
4. Re-score phantom demand and reactivation accuracy.

Expected outcome:

- Lower phantom demand.
- Better seasonal behavior.
- Cleaner headline hit rate.

### Iteration 7: Feature Refinement

Goal: use the richer fields fully.

Tasks:

1. Add campaign depth and timing features.
2. Add product dimensions/type features.
3. Add stronger category/class hierarchy features.
4. Add better store-breadth and hyperstore/mall-store features.
5. Add stock/censoring logic if stock or availability data is available.

Expected outcome:

- Push forecastable revenue movers closer to or above 80%.

### Iteration 8+: Store Allocation

Goal: preserve chain accuracy while producing store-level usefulness.

Tasks:

1. Allocate chain forecast to stores.
2. Compare allocation methods.
3. Score store-level hit +/-20 as a secondary KPI.
4. Only then consider app/API integration.

## 8. What Changed From Earlier Plans

- The headline target changed from generic active movers to forecastable revenue movers.
- Pure 80% revenue coverage was rejected because it includes expensive sparse SKUs that cannot fairly hit +/-20%.
- Pure high movers was rejected because it can optimize for frequent but financially less important products.
- Seasonal movers stay eligible when they are revenue-important and actually move in season.
- Chain-level forecasting is mandatory before store-level allocation.
- Like-for-like store coverage was added because Baneasa is missing 2022-2023.
- Stock/censoring is valuable but not required to start the first v2 benchmark.
- WMAPE is demoted to diagnostic status.
- The current ensemble is frozen as a benchmark, not improved further as the main path.
- The plan now explicitly allows pattern-based inferred features for lower-detail data, but only with source/confidence flags so inferred campaign, BF, hierarchy, or dimension signals are never confused with directly observed fields.

## 9. Immediate Next Step

Continue from the BF-aware Iteration 5D checkpoint.

Completed Iteration 5B step:

- Added a fast summary/no-persist scoring path for model tuning.
- Built and scored `direct_empirical_v1`, a dependency-free direct 4-week chain-level empirical model.
- Result: hit +/-20 improved from 19.7% (`median_naive`) to 22.2% on the scored walk-forward windows, but WMAPE and phantom demand worsened.
- Confirmed `scikit-learn` is available in the project venv and made it explicit in `backend/requirements.txt`.
- Built a reusable v2 feature matrix with lag baselines, rolling demand, category/product family, discounts, BF/campaign/store-breadth signals, and calendar features.
- Built and scored first sklearn direct models. Best aggregate hit-rate result so far is `sk_blend_median`: hit +/-20 = 23.2%, hit +/-30 = 34.2%, WMAPE = 62.3%, phantom rate = 54.6%. This beats median naive on hit rate and phantom demand but not WMAPE.

Plan adjustment after the first sklearn result:

> Do not keep tuning empirical calibration as the main path. Use it only as a diagnostic baseline. The sklearn path is now the main modeling path, but the first run shows a clear seasonal/BF failure that must be fixed before broad model tuning.

The 2024-11-25 BF/post-BF failure has now been diagnosed and partially reduced. The next concrete engineering task is:

> Run Phase 7 target-population cleanup and censoring: separate available forecastable movers from stock-constrained/BF-sensitive movers, report accuracy by slice, and decide whether clearly unavailable/censored SKU-windows should be excluded from the headline accuracy KPI while still being reported as lost-demand/business-risk volume.

Completed stock-aware checkpoint on 2026-05-16:

- Rebuilt sales ingestion for richer Pipera/Militari-style files.
- Added `DATA` invoice-date fallback when `DATA COMANDA` is missing, with `sale_date_source`, `order_date`, `invoice_date`, and `invoice_lag_days` preserved.
- Preserved `DIMENSIUNI`, `GRUPA_PRODUSE`, `CAMPANIE SELECTATA`, and loyalty-points fields.
- Added Militari as a hyperstore and avoided double-counting legacy Pipera files when enhanced Pipera files exist.
- Rebuilt v2 sales tables: 3,097,093 source rows seen, 1,861,884 raw rows inserted, 296,797 rows recovered through invoice-date fallback, 3 duplicate transaction lines, 87,631 non-product rows excluded from demand.
- Added v2 stock ingestion in `backend/forecast_engine_v2/stock_ingestion.py`.
- Loaded 549,677 monthly store stock records and 286,842 current snapshot/stock-age records.
- Marked monthly stock as historical/backtest-safe and snapshot files as `current_snapshot` only.
- Added leak-safe stock features to the feature matrix using only the previous completed stock month before each target window.
- Stock-aware feature matrix now has 30,891 headline rows, 66 numeric features, and 7 categorical features.
- Stock coverage is much lower than expected: monthly stock overlaps only 8,408 of 110,512 sales SKUs, and only 2.3-2.8% of headline SKU-window rows have stock history.
- Stock-aware model result: best hit +/-20 is `sk_hgb_poisson` at 23.7%. The blend model is 23.5% hit +/-20, 35.0% hit +/-30, 60.8% WMAPE, and 53.8% phantom rate.
- Compared with the prior `sk_blend_median` baseline of 23.2% hit +/-20, the blend improved only +0.3pp. This is directionally positive but not a meaningful step toward 80%.
- The 2024-11-25 BF/post-BF window remains the main break: `sk_blend_median` hit +/-20 is 7.7%, WMAPE is 137.6%, bias is +93.8%, and phantom rate is 79.3%.

Previous plan adjustment before Phase 6:

> Do not spend the next cycle on generic model tuning. The stock feature route has too little coverage to move aggregate accuracy today. The next cycle must fix BF/post-BF behavior and campaign-window routing first, while separately asking for better stock-code coverage or SKU mapping if stock is expected to become a major accuracy lever.

Completed BF-aware checkpoint on 2026-05-16:

- Added explicit BF calendar/window-overlap features to `backend/forecast_engine_v2/feature_matrix.py`: pre-BF, BF, and post-BF target flags; days from BF; BF/pre-BF/post-BF horizon overlap days.
- Added BF-contaminated-history features: BF units and transaction share in trailing history, raw and 4-week-equivalent non-BF recent units, and post-BF contamination ratios.
- Added conservative post-BF candidates in `backend/forecast_engine_v2/sklearn_direct_model.py`: `post_bf_safe_naive` and `sk_blend_post_bf_safe`.
- BF-aware feature matrix now has 30,891 headline rows, 90 numeric features, and 7 categorical features.
- Best aggregate Phase 6 result is `sk_blend_post_bf_safe`: hit +/-20 = 24.1%, hit +/-30 = 35.3%, WMAPE = 56.1%, phantom rate = 48.1%.
- Compared with the original sklearn baseline of 23.2% hit +/-20, this is +0.9pp. Compared with the stock-aware Phase 5 best of 23.7%, this is +0.4pp.
- The 2024-11-25 failure improved but is not fixed. `post_bf_safe_naive` reached 20.0% hit +/-20, WMAPE 66.3%, bias -25.4%, phantom 56.5%; `sk_blend_post_bf_safe` reached 17.0% hit +/-20, WMAPE 87.9%, bias +34.4%, phantom 76.3%. This is far better than Phase 5 `sk_blend_median` WMAPE 137.6% and bias +93.8%, but still too weak for the 80% target path.
- Review correction: the post-BF safe route now uses 4-week-equivalent non-BF demand, not raw partial-window non-BF demand, so it does not mix incompatible scales.
- New reports:
  - `active_docs/ITER5D_V2_BF_FEATURE_MATRIX.md`
  - `active_docs/ITER5D_V2_BF_SEASONAL_MODEL.md`

Updated plan adjustment:

> BF-aware features and routing help, but the remaining gap is not a generic model-family issue. The next highest-value step is target/censoring cleanup: measure accuracy separately for available forecastable demand, stock-constrained demand, BF-sensitive demand, and other headline movers. If hit +/-20 is still below 40% after fair slicing, pause modeling and prioritize missing stock/SKU mapping and supplier availability data.

Completed routed-audit checkpoint on 2026-05-17:

- Added forecast-time-safe route labels in `backend/forecast_engine_v2/route_labels.py`.
- Added Phase 7A routed audit runner in `backend/forecast_engine_v2/routed_audit.py`.
- Report saved to `active_docs/ITER5E_V2_ROUTED_AUDIT.md`.
- Accuracy rerun: no new model behavior. Phase 6 predictions were rebuilt in memory only to attach route labels, and the aggregate result reproduced exactly: `sk_blend_post_bf_safe` hit +/-20 = 24.1%, hit +/-30 = 35.3%, WMAPE = 56.1%, phantom rate = 48.1%.
- Routed finding: available + proxy available rows score 29.8% hit +/-20 and 46.6% WMAPE. This is materially better than the blended headline, but still below the 35% gate, so the regular/proxy-available model path also needs improvement.
- BF/campaign-sensitive rows score 21.4% hit +/-20 and 61.9% WMAPE. Sparse intermittent rows score 19.8% hit +/-20 and 60.1% WMAPE.

Completed routed-model checkpoint on 2026-05-18:

- Added Phase 7B routed candidate runner in `backend/forecast_engine_v2/routed_model_candidates.py`.
- Report saved to `active_docs/ITER5F_V2_ROUTED_MODEL_CANDIDATES.md`.
- Tested route-specific regular/proxy-available sklearn specialists, prior-window best-model routing by route, and prior-window route bias calibration.
- Accuracy rerun: main hit +/-20 did not improve. Phase 6 control `sk_blend_post_bf_safe` remains the control at 24.1% hit +/-20, 35.3% hit +/-30, 56.1% WMAPE, and 48.1% phantom rate.
- The closest routed candidate `route_regular_specialist_blend` rounded to the same 24.1% hit +/-20, improved hit +/-30 to 35.5%, improved WMAPE to 55.6%, and had 48.2% phantom rate. After fixing the report ranking to use raw metrics instead of rounded display strings, `sk_blend_post_bf_safe` remains the best model by hit +/-20. The available/proxy-regular slice did not improve on the primary KPI: hit +/-20 remains 29.8%.

Plan adjustment after Phase 7B:

> Do not spend another cycle wrapping the same global sklearn predictions with small route-specific selectors. They slightly improve aggregate error size but do not improve the main SKU hit +/-20 KPI. The next modeling step must change the prediction objective or candidate-selection logic for regular movers: test local-neighbor/analog retrieval, SKU-family analog baselines, or interval-aware candidate selection optimized directly for hit +/-20. Keep `sk_blend_post_bf_safe` as the current control until a candidate clearly beats 24.1% hit +/-20 and improves the regular/proxy slice above 29.8%.

Completed analog-model checkpoint on 2026-05-18:

- Added Phase 7C analog candidate runner in `backend/forecast_engine_v2/analog_model_candidates.py`.
- Report saved to `active_docs/ITER5G_V2_ANALOG_MODEL_CANDIDATES.md`.
- Tested local-neighbor forecasts for available/proxy-regular movers using only earlier target-window SKU snapshots.
- Neighbor pools were selected by product family first, category second, and regular-global fallback last. Analog replacement was limited to `available_regular` and `proxy_available_regular`.
- Accuracy rerun: analog candidates did not beat the Phase 6 control. `sk_blend_post_bf_safe` remains best at 24.1% hit +/-20, 35.3% hit +/-30, 56.1% WMAPE, and 48.1% phantom rate.
- Analog candidates performed worse: `analog_regular_blend` hit +/-20 = 22.4%, `analog_regular_residual` = 22.2%, `analog_regular_ratio` = 22.1%, and `analog_regular_units` = 21.8%.

Plan adjustment after Phase 7C:

> Pause new model-candidate implementation until we run a proper error decomposition / oracle ceiling analysis. Two different attempts to improve regular movers, route-specific specialists and local analog matching, failed to improve hit +/-20. The next task is to quantify the failure modes: how much is caused by BF/campaign windows, sparse/intermittent rows, lifecycle changes, missing stock/availability, SKU code/history fragmentation, and target noise. This should decide whether the next win comes from better data, different target definitions, or a fundamentally different forecasting objective.

Completed error-decomposition checkpoint on 2026-05-19:

- Added Phase 7D decomposition runner in `backend/forecast_engine_v2/error_decomposition.py`.
- Report saved to `active_docs/ITER5H_V2_ERROR_DECOMPOSITION.md`.
- No production model behavior changed. The runner rebuilds the existing measurement set and adds diagnostic oracle rows that use actual outcomes to choose the best already-tested prediction per SKU-window.
- Current control remains `sk_blend_post_bf_safe`: hit +/-20 = 24.1%, hit +/-30 = 35.3%, WMAPE = 56.1%, phantom rate = 48.1%.
- Tested-model oracle ceiling: hit +/-20 = 47.0%, hit +/-30 = 58.6%, WMAPE = 35.9%, phantom rate = 34.7%. This means perfect selection among the current candidates is still nowhere near the 80% target.
- Error concentration by route: BF/campaign-sensitive rows account for 57.0% of scored absolute error; proxy-available-regular rows account for 30.8%; sparse-intermittent rows account for 10.2%.
- Underprediction is the larger failure mode: 46.5% of scored rows are underpredicted by more than 20%, carrying 58.8% of absolute error. Overprediction above 20% covers 29.3% of scored rows and 37.6% of absolute error.
- The largest-error SKU list is dominated by BF/campaign-sensitive and proxy-available accessory/pallet/product-family rows such as `JRL796`, `PALETMIC`, `QCIP33-*`, `OSM*`, and `PALETMARE`. These may need special handling or exclusion from the headline furniture SKU KPI if they are operational artifacts, service-like items, pallet/logistics items, or campaign-driven consumable/accessory demand.

Plan adjustment after Phase 7D:

> Do not continue with another small model-candidate phase yet. The tested-model oracle ceiling proves that the current feature/model family cannot reach the 80% target by routing alone. Phase 7E should be a data and target cleanup phase: inspect top-error SKUs/families, classify operational artifacts versus true forecastable products, strengthen campaign and stock availability fields from Pentaho, and decide whether special rows like pallets/high-volume accessories belong in the headline KPI. Only after that should we train the next model candidate.

Completed target-cleanup checkpoint on 2026-05-19:

- Added Phase 7E target cleanup runner in `backend/forecast_engine_v2/target_cleanup_audit.py`.
- Report saved to `active_docs/ITER5I_V2_TARGET_CLEANUP_AUDIT.md`.
- No production model behavior changed. The run rebuilt the diagnostic score rows and classified errors into cleanup/data-action buckets.
- Current control remains `sk_blend_post_bf_safe`: hit +/-20 = 24.1%, hit +/-30 = 35.3%, WMAPE = 56.1%, phantom rate = 48.1%.
- Artifact-token review is not enough. Removing obvious pallet/service/logistics-like candidates leaves hit +/-20 at 24.1%, so the low accuracy is not mainly caused by a few dirty operational SKUs.
- Main error/data buckets: campaign-calendar-required rows carry 52.8% of revenue and 55.4% of scored absolute error; stock-availability-required rows carry 31.4% of revenue and 29.6% of absolute error; lifecycle/stock-policy rows carry 15.5% of revenue and 12.0% of absolute error.
- Top priority Pentaho extracts are monthly store stock, monthly supplier/importer stock, stock-age snapshots, supplier stock-age snapshots, detailed order history, detailed sales/campaign history, product master/lifecycle data, receipts/NIR, replenishment orders, reserved stock, and delivery-management data.

Plan adjustment after Phase 7E:

> Pause new model wrappers until the Phase 7E data gaps are addressed. The next engineering phase should ingest the requested Pentaho stock/campaign/lifecycle/receipt data, rebuild leak-safe features, and rerun the same scorecard. Only then should the forecast design be reconsidered again with stronger signals.

Completed Phase 8A on 2026-05-20:

- Added new data validation audit in `backend/forecast_engine_v2/new_data_audit.py`.
- Report saved to `active_docs/ITER5J_V2_NEW_DATA_AUDIT.md`.
- No model behavior changed and no forecast tables were mutated.
- Result: monthly store stock for Constanta/Iasi/Oradea is clean and directly ingestible; supplier stock is the largest new lever but requires exact product-name SKU mapping with confidence flags; rotation files remain current-snapshot only for official backtests.

Completed Phase 8B on 2026-05-20:

- Updated sales ingestion to infer store from filename for single-store exports that omit `MAGAZIN`.
- Added Baneasa 2022 ingestion runner/report in `backend/forecast_engine_v2/phase8b_baneasa_ingestion.py`.
- Report saved to `active_docs/ITER5K_V2_PHASE8B_BANEASA_2022_INGESTION.md`.
- Imported `baneasa_sales22.csv`: 233,245 rows seen, 233,052 inserted, 193 duplicates skipped, 0 filtered, 115,891 rows using `DATA` invoice-date fallback, 0 missing effective sale dates.
- Rebuilt weekly v2 demand tables: raw rows now 2,094,936, weekly store rows 1,619,031, weekly chain rows 1,226,529.
- Cleared stale forecast score/regime tables because the sales foundation changed.
- Accuracy was not rerun. The last official control baseline remains hit +/-20 = 24.1%, hit +/-30 = 35.3%, WMAPE = 56.1%, phantom rate = 48.1%.

Completed Phase 8C on 2026-05-21:

- Added monthly store-stock ingestion runner in `backend/forecast_engine_v2/phase8c_monthly_store_stock.py`.
- Report saved to `active_docs/ITER5L_V2_PHASE8C_MONTHLY_STORE_STOCK.md`.
- Imported the missing historical monthly store stock for Constanta, Iasi, and Oradea from `new_stock_data_20may/`.
- Added 157,471 monthly stock records: Constanta 67,639 records / 4,752 SKUs, Iasi 52,890 records / 4,705 SKUs, Oradea 36,942 records / 3,048 SKUs.
- Monthly store-stock coverage is now 707,148 records, 13,351 SKUs, 11 stores, covering 2022-01 through 2025-12.
- Source stock SKU overlap with sales SKUs is strong for these files: Constanta 89.2%, Iasi 94.9%, Oradea 96.4%.
- Accuracy was not rerun. This phase adds historical store-stock context only; model accuracy should be measured after Phase 8E joins store/supplier availability into the feature matrix.
- Store-stock context on the fast forecastable proxy remains only about 2.9-3.2%, so Phase 8D supplier stock remains the bigger availability lever.

Completed Phase 8D on 2026-05-21:

- Added supplier monthly stock ingestion runner in `backend/forecast_engine_v2/phase8d_supplier_stock.py`.
- Report saved to `active_docs/ITER5M_V2_PHASE8D_SUPPLIER_STOCK.md`.
- Created normalized tables `stock_monthly_supplier_v2` and `supplier_stock_sku_map_v2`.
- Imported supplier stock files for 2022-2025 into 1,821,659 unique supplier/month/product records after duplicate source keys were aggregated.
- Built confidence-controlled product-name mappings: 76,858 exact-unique mapped SKUs, 1,819 ambiguous product keys, and 46,315 unmapped product keys.
- Exact supplier-stock context covers roughly 63.6-70.9% of the fast forecastable target SKU population by target window; positive supplier stock covers roughly 58.1-63.0%.
- Accuracy was not rerun. This phase only adds supplier availability data; the model should be rerun after Phase 8E adds supplier/combined stock features to the feature matrix.

Completed Phase 8E on 2026-05-21:

- Added leak-safe supplier and combined stock features in `backend/forecast_engine_v2/feature_matrix.py`.
- Updated `backend/forecast_engine_v2/route_labels.py` so route availability can use combined store-or-supplier stock instead of treating missing store stock as fully unknown when supplier stock exists.
- Feature report saved to `active_docs/ITER5N_V2_PHASE8E_AVAILABILITY_FEATURE_MATRIX.md`.
- Model report saved to `active_docs/ITER5N_V2_PHASE8E_AVAILABILITY_MODEL.md`.
- Feature matrix now has 30,891 rows, 111 numeric features, and 10 categorical features.
- Store stock coverage remains weak at 2.3-2.8% of headline rows, but exact supplier-stock history covers 77.4-80.7% of headline rows by target window.
- Accuracy rerun result: best raw hit +/-20 is `sk_extra_trees` at 24.6%, hit +/-30 35.5%, WMAPE 58.3%, phantom 44.2%. This is +0.5pp hit +/-20 versus the 24.1% control, but WMAPE worsened.
- Safer availability-aware blend result: `sk_blend_post_bf_safe` scored hit +/-20 24.2%, hit +/-30 35.3%, WMAPE 55.6%, phantom 44.4%. This is only +0.1pp hit +/-20, but improves WMAPE and phantom rate versus the previous control.
- Decision: supplier stock is now in the model, but the global model is still not using availability strongly enough to create a large hit-rate jump. Next modeling work should use availability-specific routing/training or separate stock-constrained demand rather than just adding more global features.
- Engineering note: feature generation is slow after supplier joins. Before many more modeling loops, add cached feature-matrix artifacts or a materialized feature table.

Completed Phase 8F on 2026-05-21:

- Added rotation snapshot ingestion runner in `backend/forecast_engine_v2/phase8f_rotation_snapshot.py`.
- Report saved to `active_docs/ITER5O_V2_PHASE8F_ROTATION_SNAPSHOT.md`.
- Created `stock_rotation_snapshot_v2` for current/future diagnostics.
- Imported four rotation snapshot files for Constanta, Militari, Pipera, and Sibiu.
- Result: 211,056 current-snapshot rows, 61,121 unique SKUs, 4 stores, snapshot date 2026-05-21.
- Sales overlap is high: Constanta 81.7%, Militari 81.9%, Pipera 79.9%, Sibiu 82.5%. Headline overlap is about 3.3k SKUs per store.
- Historical safety decision: all rotation rows are marked `current_snapshot`. They must not be used in official historical backtests unless future exports include historical as-of dates.
- Accuracy was not rerun. Official Phase 8E best raw hit +/-20 remains 24.6%; safer blend remains hit +/-20 24.2%, WMAPE 55.6%, phantom 44.4%.

Completed Phase 8G-A on 2026-05-23:

- Added high-revenue benchmark runner in `backend/forecast_engine_v2/phase8g_high_revenue_benchmark.py`.
- Report saved to `active_docs/ITER5P_V2_PHASE8G_HIGH_REVENUE_BENCHMARK.md`.
- The safer Phase 8E control reproduced at hit +/-20 24.2%, WMAPE 55.6%, phantom 44.4%.
- High-revenue scope alone did not solve the model: Top 1000 control hit +/-20 was 24.8%.
- First serious win: the forecast-safe clean Top 1000 regular/proxy-regular slice reached 32.3% hit +/-20 with `sk_extra_trees`, WMAPE 45.5%, and bias 2.1%. This is not headline accuracy yet, but it proves the current data can support a materially better slice.

Completed Phase 8G-B on 2026-05-23:

- Added high-revenue stock coverage audit in `backend/forecast_engine_v2/phase8g_stock_coverage_audit.py`.
- Report saved to `active_docs/ITER5Q_V2_PHASE8G_STOCK_COVERAGE_AUDIT.md`.
- Top 1000 store previous-month observed coverage is only 0.4%; supplier previous-month observed coverage is 70.6%.
- 5,324 / 5,346 Top 1000 rows have recent store sales but no previous-month store-stock row.
- Decision: do not block next modeling on monthly store stock. Use supplier stock as the main historical availability signal; keep store stock as a narrow high-confidence signal.

Completed Phase 8G-C on 2026-05-23:

- Added forecast-time-safe campaign history features in `backend/forecast_engine_v2/feature_matrix.py`.
- Added campaign-field audit runner in `backend/forecast_engine_v2/phase8g_campaign_field_audit.py`.
- Report saved to `active_docs/ITER5R_V2_PHASE8G_CAMPAIGN_FIELD_AUDIT.md`.
- Campaign exposure features use only raw sales where `sale_date < target_start`.
- Product/program labels are excluded from campaign exposure and kept as a separate product-program signal.
- Non-BF campaign features exclude rows flagged as BF campaigns, not only rows inside BF timing windows.
- Top 1000 campaign exposure is dense: any campaign history in prior 13 weeks = 69.1%, non-BF campaign history = 30.8%, BF transaction history = 35.3%.
- The clean Top 1000 regular/proxy-regular slice still has 70.7% rows with campaign history in the prior 13 weeks. The 32.3% 8G-A win is therefore not a pure no-campaign regular-demand result.
- Engineering note: feature generation is now slow enough that cached/materialized feature matrices should be added before repeated modeling loops.

Completed Phase 8G-D on 2026-05-23:

- Added DB-aware feature-matrix cache helper in `backend/forecast_engine_v2/feature_matrix_cache.py`.
- Added route-specific high-revenue runner in `backend/forecast_engine_v2/phase8g_route_specific_model.py`.
- Report saved to `active_docs/ITER5S_V2_PHASE8G_ROUTE_SPECIFIC_MODEL.md`.
- The cache key now includes DB path/size/mtime/schema/user version and `ScorecardConfig`, so future reruns will not silently reuse stale features after ingestion or DB changes.
- This was a Top 1000 high-revenue experiment, not a full-headline promotion.
- Top 1000 control was `sk_blend_post_bf_safe`: hit +/-20 23.4%, hit +/-30 34.8%, WMAPE 55.7%, phantom 43.5%.
- Raw hit winner `sk_hgb_squared` reached hit +/-20 25.3% (+2.0pp) and hit +/-30 37.4%, but worsened WMAPE to 62.6% and phantom to 57.8%; do not promote.
- Best 8G-D route candidate `8gd_regular_global_extra` reached hit +/-20 24.4% (+1.0pp), hit +/-30 35.5%, WMAPE 55.6%, phantom 43.6%. This is a small diagnostic improvement below the promotion gate.
- Route detail for `8gd_regular_global_extra`: available_regular hit +/-20 35.1%, proxy_available_regular 28.8%, stock_constrained 25.8%, BF/campaign-sensitive only 16.6%.
- The 2024-11-25 BF/post-BF target window remains badly broken: hit +/-20 6.7%, WMAPE 139.8%, bias +133.0%.
- Code review approved after fixing cache invalidation and report overclaiming.

Completed Phase 8G-E on 2026-05-24:

- Added BF/campaign-sensitive runner in `backend/forecast_engine_v2/phase8g_campaign_sensitive_model.py`.
- Report saved to `active_docs/ITER5T_V2_PHASE8G_CAMPAIGN_SENSITIVE_MODEL.md`.
- Used the DB-aware cached Top 1000 feature matrix from Phase 8G-D.
- Tested conservative forecast-time transforms: campaign safe naive, BF-calendar safe naive, campaign conservative pool, and hard post-BF safe fallback.
- Best 8G-E candidate `8ge_post_bf_hard_safe`: Top 1000 hit +/-20 24.3% vs 23.4% control (+0.9pp), WMAPE 51.1% vs 55.7%, phantom 40.9% vs 43.5%, bias -23.2% vs -17.0%.
- Critical stress result: 2024-11-25 improved from hit +/-20 6.7% to 17.8%, WMAPE 139.8% to 70.9%, and bias +133.0% to +38.0%.
- BF/campaign-sensitive route improved from hit +/-20 16.6% to 18.6%, WMAPE 65.4% to 57.4%, but it remains the hard blocker.
- Code review approved: no target leakage, chronological train/eval split, no duplicate median baseline rows, and post-BF hard-safe gating is forecast-time-safe.

Completed Phase 8G-F on 2026-05-24:

- Added combined route runner in `backend/forecast_engine_v2/phase8g_combined_route_model.py`.
- Report saved to `active_docs/ITER5U_V2_PHASE8G_COMBINED_ROUTE_MODEL.md`.
- Used the DB-aware cached Top 1000 feature matrix from Phase 8G-D.
- Tested three composed candidates: regular plus post-BF safe, regular plus broad BF-calendar safe, and guarded-regular plus post-BF safe.
- Best 8G-F candidate `8gf_regular_plus_post_bf_safe`: Top 1000 hit +/-20 25.3% vs 23.4% control (+2.0pp), hit +/-30 36.5% vs 34.8%, WMAPE 51.0% vs 55.7%, phantom 41.0% vs 43.5%.
- The combined candidate beat both individual components: `8gd_regular_global_extra` was 24.4% hit +/-20 and `8ge_post_bf_hard_safe` was 24.3%.
- Revenue-scope detail: Top 100 improved by +1.1pp hit +/-20 and -5.7pp WMAPE; Top 500 improved by +2.3pp hit +/-20 and -5.4pp WMAPE; Top 1000 improved by +2.0pp hit +/-20 and -4.7pp WMAPE.
- Critical slices: available/proxy regular improved from 30.2% to 33.1% hit +/-20; BF/campaign-sensitive route improved from 16.6% to 18.6%; 2024-11-25 remained protected at 17.8% hit +/-20 and 70.9% WMAPE.
- Code review approved: no target leakage, chronological train/eval split intact, metric tables aligned, and route/campaign/BF gates are forecast-time-safe.

Completed Phase 8G-G on 2026-05-24:

- Added promotion/robustness runner in `backend/forecast_engine_v2/phase8g_promotion_pack.py`.
- Report saved to `active_docs/ITER5V_V2_PHASE8G_PROMOTION_PACK.md`.
- Reused the reviewed 8G-F prediction path and DB-aware cached Top 1000 feature matrix.
- Decision: `PROMOTE_HIGH_REVENUE_CHAMPION_WITH_MONITORS`.
- Promote `8gf_regular_plus_post_bf_safe` as the current high-revenue Top 1000 champion candidate behind an explicit high-revenue policy flag, while tracking accepted monitoring caveats.
- Promotion gates passed: Top 1000 hit +/-20 +2.0pp vs safer control, WMAPE -4.7pp, phantom -2.5pp, Top 500 hit +/-20 +2.3pp, Top 100 hit +/-20 +1.1pp, and 2024-11-25 stress WMAPE -68.8pp.
- Zero-actual robustness improved vs control: phantom 43.5% to 41.0%, predicted units on zero-actual rows 2,669.9 to 2,395.8.
- Monitoring caveats: champion is more underpredictive than safer control, bias -21.3% vs -17.0%; available/proxy regular phantom rose +1.3pp while quantity hit improved; largest non-stress window WMAPE regression is +1.8pp.

Completed Phase 8G-H on 2026-05-26:

- Wired the promoted high-revenue champion into `backend/forecast_engine_v2/sklearn_direct_model.py`.
- Report saved to `active_docs/ITER5W_V2_PHASE8G_HIGH_REVENUE_POLICY_WIRING.md`.
- Added CLI options `--revenue-rank-limit` and `--high-revenue-policy {none,champion}`.
- Default policy remains `none`, so existing direct sklearn behavior is preserved unless the champion is explicitly requested.
- When enabled, the official runner emits `8gf_regular_plus_post_bf_safe` with source `v2_high_revenue_policy` and version `high_revenue_policy_v1_2026_05_24`.
- Review fix: champion policy now fails fast unless `--revenue-rank-limit` is 1000 or lower, and the 8G-H report compares delta vs same-run `sk_blend_post_bf_safe` control.
- Official Top 1000 run reproduced the 8G-G promotion numbers: hit +/-20 25.3%, hit +/-30 36.5%, WMAPE 51.0%, phantom 41.0%, bias -21.3%.
- Lowlight: the official uncached runner is slow because it rebuilds the feature matrix. Keep using cached phase runners for modeling loops and the official path for validation/export.

Completed Phase 8G-I on 2026-05-26:

- Added official validation/export runner in `backend/forecast_engine_v2/phase8g_official_policy_validation.py`.
- Report saved to `active_docs/ITER5X_V2_PHASE8G_OFFICIAL_POLICY_VALIDATION.md`.
- Official score-row export saved to `active_docs/ITER5X_V2_PHASE8G_OFFICIAL_POLICY_SCORE_ROWS.csv`.
- Exposed optional row-level score rows from `backend/forecast_engine_v2/sklearn_direct_model.py` for validation tooling only; the default four-value API path remains unchanged unless `include_score_rows=True`.
- Decision: `PROMOTE_WITH_MONITORS`, not a clean global promotion.
- Policy safety checks passed: default `--high-revenue-policy none` does not emit `8gf_regular_plus_post_bf_safe`; champion mode emits it; champion mode fails fast without Top 1000-or-lower `--revenue-rank-limit`; same-run control hit +/-20 is unchanged by the policy flag.
- Review fix: the official report now separates blocking promotion gates from required monitors and clearly labels the run as confirmatory rolling backtest/export validation, not independent future holdout validation. The 8G-I runner now requires exactly Top 1000 scope to avoid misleading labels for stricter rank limits.
- Official Top 1000 result remains: control hit +/-20 23.4%, WMAPE 55.7%, phantom 43.5%, bias -17.0%; champion hit +/-20 25.3%, WMAPE 51.0%, phantom 41.0%, bias -21.3%.
- Revenue scopes all pass: Top 100 +1.1pp hit +/-20, Top 250 +3.2pp, Top 500 +2.3pp, Top 750 +2.1pp, Top 1000 +2.0pp.
- Critical slices confirm the tradeoff: available/proxy regular improves from 30.2% to 33.1% hit +/-20 but phantom rises from 67.1% to 68.4%; BF/campaign-sensitive improves from 16.6% to 18.6% and WMAPE drops from 65.4% to 57.4%; 2024-11-25 stress stays protected at 17.8% hit +/-20 and 70.9% WMAPE.
- Lowlight: official validation is slow when run twice through the uncached main sklearn path. Use cached runners for candidate search, then the official validation runner for final proof/export.

Completed Phase 8G-J on 2026-05-26:

- Added monitored-caveat calibration runner in `backend/forecast_engine_v2/phase8g_monitor_calibration.py`.
- Report saved to `active_docs/ITER5Y_V2_PHASE8G_MONITOR_CALIBRATION.md`.
- This is a research calibration phase, not official wiring and not independent holdout evidence.
- Best research candidate: `8gj_bfc_nonpost_lift_150`.
- Candidate logic: multiply only `bf_campaign_sensitive` rows outside post-BF calendar context when the current champion prediction is at least 3 units.
- Result versus the official 8G-I champion: hit +/-20 improves 25.3% to 27.2%, hit +/-30 improves 36.5% to 39.2%, WMAPE improves 51.0% to 49.3%, bias improves -21.3% to -9.3%, and phantom stays 41.0%.
- BF/campaign-sensitive route improves materially: hit +/-20 18.6% to 23.4%, WMAPE 57.4% to 53.8%, bias -31.2% to -5.5%.
- Regular phantom is not solved: available/proxy regular phantom remains 68.4%, and available-regular phantom remains 87.2%.
- The 2025-03-24 non-stress WMAPE regression is not solved: it remains unchanged versus the 8G-I champion.
- Review caveat/fix: the report now says `RESEARCH_CANDIDATE_FOR_OFFICIAL_VALIDATION`, uses `Pre-Official Gate Replay`, and explicitly states the lift was selected on known Phase 8G validation windows.

Completed Phase 8G-K on 2026-05-26:

- Added official calibrated high-revenue policy support in `backend/forecast_engine_v2/sklearn_direct_model.py`.
- Added official calibrated validation/export runner in `backend/forecast_engine_v2/phase8g_official_calibrated_policy.py`.
- Report saved to `active_docs/ITER5Z_V2_PHASE8G_OFFICIAL_CALIBRATED_POLICY.md`.
- Official score-row export saved to `active_docs/ITER5Z_V2_PHASE8G_OFFICIAL_CALIBRATED_SCORE_ROWS.csv`.
- New optional policy: `--high-revenue-policy bfc_lift_150 --revenue-rank-limit 1000`.
- Default behavior remains `--high-revenue-policy none`; the 8G-I champion remains available under `--high-revenue-policy champion`.
- Policy safety checks passed: default policy does not emit the calibrated candidate, candidate policy emits it, candidate policy includes the 8G-I champion for comparison, candidate policy is blocked without Top 1000-or-lower scope, and same-run control hit +/-20 is unchanged by the policy flag.
- Aggregate 8G-K result reproduced the 8G-J research gain: hit +/-20 27.2%, hit +/-30 39.2%, WMAPE 49.3%, bias -9.3%, phantom 41.0%.
- Decision: `KEEP_8G_I_CHAMPION`.
- Reason: the calibrated candidate fails window stability. The worst non-stress regression is `2024-12-30`, where WMAPE worsens from 58.3% to 73.7% versus 8G-I (+15.4pp), hit +/-20 falls from 21.3% to 19.7%, and bias swings from -9.0% to +25.9%.
- Interpretation: the 1.50 BF/campaign lift is directionally useful but too blunt. It fixes underprediction in aggregate and helps `2024-10-28`, but overcorrects other non-stress campaign periods. Do not replace the official 8G-I champion with this exact calibrated policy.

Completed Phase 8G-L on 2026-05-26:

- Added business-semantics audit runner in `backend/forecast_engine_v2/phase8g_business_semantics_audit.py`.
- Report saved to `active_docs/ITER5AA_V2_PHASE8G_BUSINESS_SEMANTICS_AUDIT.md`.
- This was a read-only audit. It did not change production prediction behavior.
- Business correction: Mobexpert stock should not be interpreted as hard sellability. Active/orderable/listed SKU status is the missing sellability signal. Existing stock quantities are still useful, but as fulfillment/friction/stock-position context rather than can-sell / cannot-sell gates.
- Returns were not ignored: v2 ingests negative `CANTITATE FACTURATA`, creates returned-unit and net-unit fields, and includes return-rate lag features. The current target remains positive sold units, so returns do not reduce the gross-demand target.
- Discounts were not ignored: `Reducere %` is ingested and used as lag/campaign discount memory. Underuse remains: the engine does not yet model future discount/promotion intent. Data-quality issues found: 61 raw infinite discount rows reached weekly aggregates, and 172 finite discount rows are >1 and need scale validation/normalization.
- Campaign fields were used: `CAMPANIE` and `CAMPANIE BF` drive historical campaign/BF features. The remaining gap is future SKU campaign membership/intensity and whether a BF label means planned BF SKU, later campaign assignment, or old campaign label.
- `VECHIME IN COLECTIE` exists mainly in stock snapshot tables. It is not used in official historical backtests because most available rows are current/snapshot-like rather than reliable historical-as-of features.
- Stock-soft policy simulation using official 8G-K score rows: `8gl_demand_regular_plus_post_bf_safe` scored 25.7% hit +/-20 and 50.9% WMAPE versus the current champion at 25.3% and 51.0%. This is only route-blending sensitivity over exported predictions, not retraining or stock-feature ablation, and is directionally better but too small to replace the champion.
- Decision: `KEEP_CURRENT_CHAMPION_AND_RELABEL_STOCK_SEMANTICS`.
- Interpretation: the current champion is still the official Top 1000 policy, but future route names/logic should stop implying stock is the ability to sell. Before another promotion, clean invalid discounts and reframe stock features as fulfillment context.

Completed Phase 8G-M on 2026-05-27:

- Added hygiene/semantics validation runner in `backend/forecast_engine_v2/phase8gm_hygiene_semantics.py`.
- Report saved to `active_docs/ITER5AB_V2_PHASE8G_M_HYGIENE_SEMANTICS.md`.
- Official score-row export saved to `active_docs/ITER5AB_V2_PHASE8G_M_SCORE_ROWS.csv`.
- Future ingestion now drops non-finite and above-fraction-scale `Reducere %` values; the feature builder also sanitizes existing weekly/campaign discount aggregates from the current DB.
- Cleaned Top 1000 feature matrix check passed: 8,227 rows, 131 numeric feature columns, 0 non-finite numeric cells, 0 discount feature cells above 1, max discount feature value 95.0%.
- Route semantics were reframed from availability/sellability to stock-position / fulfillment context. Route version is now `v2_routes_2026_05_26_stock_position`.
- Return handling remains unchanged for target construction: the model predicts gross positive sold units, while returns stay available as return-rate diagnostics/context.
- Official Top 1000 rerun reproduced the current champion exactly: `8gf_regular_plus_post_bf_safe` hit +/-20 25.3%, hit +/-30 36.5%, WMAPE 51.0%, phantom 41.0%, bias -21.3%.
- Decision: `HYGIENE_PASS_KEEP_CHAMPION_BASELINE`.

Current next phase:

Completed Phase 8G-N on 2026-05-27:

- Added stock-soft retrain/ablation runner in `backend/forecast_engine_v2/phase8gn_stock_soft_rebuild.py`.
- Report saved to `active_docs/ITER5AC_V2_PHASE8G_N_STOCK_SOFT_REBUILD.md`.
- Official score-row export saved to `active_docs/ITER5AC_V2_PHASE8G_N_SCORE_ROWS.csv`.
- Tested three candidates against the official champion: `8gn_stock_soft_full_features`, `8gn_no_stock_features_current_route`, and `8gn_no_stock_features_stock_soft`.
- Best candidate was `8gn_stock_soft_full_features`, which replaces the regular-route stock gate with demand regularity while keeping all model features.
- Aggregate Top 1000 result: champion hit +/-20 25.3%, WMAPE 51.0%, phantom 41.0%; best stock-soft candidate hit +/-20 25.7%, WMAPE 50.9%, phantom 41.2%.
- Decision: `KEEP_CURRENT_CHAMPION`.
- Reason: the candidate improved hit +/-20 by only +0.4pp, below the +0.5pp promotion gate. Stock-feature ablation was worse: no-stock current route hit +/-20 24.7%, and no-stock stock-soft hit +/-20 25.0%.
- Interpretation: stock semantics are corrected, but stock-soft retraining does not unlock a material current-data gain. Do not spend more current-data cycles on stock until active/orderable/listed SKU history arrives.

Current next phase:

Completed Phase 8G-O on 2026-05-28:

- Added guarded campaign/BF calibration runner in `backend/forecast_engine_v2/phase8go_guarded_campaign_calibration.py`.
- Report saved to `active_docs/ITER5AD_V2_PHASE8G_O_GUARDED_CAMPAIGN_CALIBRATION.md`.
- Score-row export saved to `active_docs/ITER5AD_V2_PHASE8G_O_SCORE_ROWS.csv`.
- Best candidate: `8go_pre_bf_bfc_lift_180`.
- Candidate logic: multiply only BF/campaign-sensitive rows in the pre-BF calendar window when the current champion prediction is at least 3 units. This touched 480 rows.
- Aggregate Top 1000 result versus current champion: hit +/-20 25.3% to 27.4% (+2.1pp), hit +/-30 36.5% to 39.4%, WMAPE 51.0% to 47.4%, bias -21.3% to -10.5%, phantom unchanged at 41.0%.
- Safety result: 2024-12-30 and 2025-01-27 are unchanged because the candidate avoids the broad normal-calendar Dec/Jan lift that failed in 8G-K.
- Decision: `PROMOTE_GUARDED_CAMPAIGN_CANDIDATE` into final promotion-pack validation, not direct policy replacement yet.
- Caveat: the lift is forecast-time-safe but validated on one pre-BF window in the current rolling grid, so final promotion must explicitly label that monitoring risk.

Current next phase:

Completed Phase 8G-P on 2026-05-28:

- Added official guarded high-revenue policy support in `backend/forecast_engine_v2/sklearn_direct_model.py`.
- Added final promotion-pack runner in `backend/forecast_engine_v2/phase8gp_final_promotion_pack.py`.
- Report saved to `active_docs/ITER5AE_V2_PHASE8G_P_FINAL_PROMOTION_PACK.md`.
- Official score-row export saved to `active_docs/ITER5AE_V2_PHASE8G_P_OFFICIAL_SCORE_ROWS.csv`.
- New optional policy: `--high-revenue-policy pre_bf_bfc_lift_180 --revenue-rank-limit 1000`.
- Default behavior remains `--high-revenue-policy none`; the previous 8G-I champion remains available for comparison.
- The official guarded policy emits `8go_pre_bf_bfc_lift_180` with source `v2_high_revenue_policy` and version `high_revenue_policy_v3_2026_05_28`.
- Official final result: hit +/-20 27.4%, hit +/-30 39.4%, WMAPE 47.4%, bias -10.5%, phantom 41.0%.
- Delta versus the 8G-I champion: +2.1pp hit +/-20, +2.9pp hit +/-30, -3.6pp WMAPE, +10.7pp bias improvement, phantom unchanged.
- Final gates passed: Top 100 +4.3pp hit +/-20, Top 500 +2.6pp, Top 1000 +2.1pp, `2024-11-25` stress protected, `2024-12-30` and `2025-01-27` guard windows unchanged, and largest non-stress WMAPE regression is +0.0pp.
- Policy safety checks passed: default policy does not emit the guarded candidate, guarded policy emits it, guarded policy includes the 8G-I champion for comparison, guarded policy is blocked without Top 1000-or-lower scope, and same-run control is unchanged.
- Decision: `PROMOTE_8G_O_GUARDED_POLICY_AND_STOP_CURRENT_DATA_ITERATION`.

Current next phase:

> Stop blind current-data modeling. The next material accuracy work should start from new data, especially active/orderable/listed SKU history, future campaign membership/planned discounts, historical price levels, customer order status history, and fuller 2022-2025 hyperstore sales coverage. Current-data stock iteration is exhausted; current-data campaign iteration has produced the final guarded policy.

Completed before this step:

- the multi-store data is ingested,
- chain demand exists,
- hierarchy unknowns are reduced as much as possible from the available fields,
- optional campaign/BF/detail fields are represented as observed, inferred, or unknown,
- cutoff-specific regime labels exist,
- and a v2-native naive scorecard exists for chain-level 4-week benchmarks.
- the v2-native naive scorecard has been run across the full rolling grid.

Before claiming model improvement:

- run all agreed rolling scorecard windows, not just two sample windows,
- compare the candidate against `median_naive` and the other v2-native naive baselines,
- keep legacy Iter 3 / Iter 4 comparisons clearly marked as historical or chain-adapted only.

Execution note:

- Full row-level scorecard persistence is useful for official audits but slow for iterative modeling. Tuning runs should use a fast summary/no-persist mode and only persist row-level results for selected official candidates.
- The local project venv has `scikit-learn 1.8.0`; use the venv Python (`backend/venv/bin/python`) for v2 modeling runs.
- LightGBM still imports through an unstable NumPy/matplotlib ABI path in the global Python environment. Leave LightGBM aside until the sklearn path has exhausted the obvious data/feature issues.
