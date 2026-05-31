# Supply Inventory Forecast Project

Updated: 2026-05-31

This repository is Fyo's retail supply and demand forecasting workspace. The original product was a supply-chain decision engine for a Mobexpert-style retail business, but the active work is now focused on Forecast Engine V2 and the path toward a future Forecast Engine V3.

The most important thing for a new AI/chat to understand:

- The old forecast engine is not the current path.
- Forecast V2 is the current technical baseline.
- The promoted V2 policy is useful but still far below the final accuracy target.
- Current-data iteration has been stopped deliberately.
- The next major improvement should come from richer data and a rethink toward V3, not more blind tuning of the current V2 feature stack.

## Fyo And Project Context

Fyo is a 20-year-old entrepreneur based in Bucharest. He is building AI-powered products and using this retail forecasting project as a serious applied system, not just a demo.

The business setting is furniture and home retail with many SKUs, physical stores, online sales, outlets, campaigns, Black Friday effects, returns, discounts, supplier/stock context, and product lifecycle effects.

The target is not to forecast every low-volume SKU perfectly. The real goal is to forecast financially important products well enough to improve buying, inventory, and planning decisions.

Current modeling focus:

- High-revenue SKUs.
- Chain-level 4-week demand.
- Gross positive physical-product demand.
- Top 1000 high-revenue SKU/windows as the current official V2 evaluation scope.

Long-term target:

- A forecast engine that can drive practical decisions for buyers.
- A model that handles high-revenue products, campaigns, lifecycle, channel differences, and business constraints.
- Eventually, a V3 system with a better data model and modeling architecture than the current V2 research stack.

## Current State In One Page

Current official V2 promoted policy:

```text
Model: 8go_pre_bf_bfc_lift_180
Policy flag: --high-revenue-policy pre_bf_bfc_lift_180 --revenue-rank-limit 1000
Scope: Top 1000 high-revenue SKU/windows
Hit +/-20: 27.4%
Hit +/-30: 39.4%
WMAPE: 47.4%
Bias: -10.5%
Phantom: 41.0%
Decision: PROMOTE_8G_O_GUARDED_POLICY_AND_STOP_CURRENT_DATA_ITERATION
```

Previous high-revenue champion:

```text
Model: 8gf_regular_plus_post_bf_safe
Hit +/-20: 25.3%
Hit +/-30: 36.5%
WMAPE: 51.0%
Bias: -21.3%
Phantom: 41.0%
```

The latest promoted policy improved hit rate, WMAPE, and bias without worsening phantom rate, but absolute accuracy is still not high enough. This is why the project is now preparing for richer data ingestion and V3-level redesign.

Read first:

1. `active_docs/FORECAST_V2_CURRENT_HANDOFF.md`
2. `active_docs/FORECAST_V2_DATA_DICTIONARY_AND_BUSINESS_RULES.md`
3. `active_docs/ITER5AE_V2_PHASE8G_P_FINAL_PROMOTION_PACK.md`
4. `active_docs/FORECAST_V2_ENGINE_AUDIT.md`
5. `FORECAST_V2_REBUILD_PLAN.md`

## Repository Map

### Active Forecast V2 Code

Primary folder:

```text
backend/forecast_engine_v2/
```

Core files:

- `ingestion.py` - imports multi-store CSVs into normalized V2 tables.
- `scorecard.py` - builds actual 4-week targets and computes metrics.
- `regime_labels.py` - labels SKUs/windows by revenue, activity, forecastability, and lifecycle-like regimes.
- `feature_matrix.py` - builds leak-safe feature matrices for V2 models.
- `route_labels.py` - assigns route/context labels. Important: stock labels now mean stock-position/fulfillment context, not sellability.
- `sklearn_direct_model.py` - official sklearn direct 4-week model path and high-revenue policy flags.
- `feature_matrix_cache.py` - cached feature matrix support for faster phase iteration.
- `hierarchy_normalizer.py` - product hierarchy normalization and limited product-name inference.
- `feature_signals.py` - campaign/BF signal classification.
- `stock_ingestion.py` - store stock ingestion.

Recent phase runners:

- `phase8gm_hygiene_semantics.py` - discount hygiene, return diagnostics, stock semantics cleanup.
- `phase8gn_stock_soft_rebuild.py` - stock-soft/no-stock retraining variants.
- `phase8go_guarded_campaign_calibration.py` - guarded pre-BF campaign calibration.
- `phase8gp_final_promotion_pack.py` - final promotion-pack validation for current V2 policy.

Earlier V2 phase runners:

- `phase8g_high_revenue_benchmark.py`
- `phase8g_stock_coverage_audit.py`
- `phase8g_campaign_field_audit.py`
- `phase8g_route_specific_model.py`
- `phase8g_campaign_sensitive_model.py`
- `phase8g_combined_route_model.py`
- `phase8g_promotion_pack.py`
- `phase8g_official_policy_validation.py`
- `phase8g_monitor_calibration.py`
- `phase8g_official_calibrated_policy.py`
- `phase8g_business_semantics_audit.py`

### Legacy Forecast Engine

Folder:

```text
backend/forecast_engine/
```

Status:

- Legacy benchmark only.
- Do not use it as the main path for new forecast work.
- It includes the older median ensemble / WMAPE-first approach and old iteration history.
- Useful for comparison and historical context, not for the next modeling direction.

### Product MVP / API / Frontend

Folders:

```text
backend/api/
backend/engines/
frontend/
```

Status:

- These belong to the original MVP decision-engine app: dead stock, supplier reliability, demand tab, queue, SKU deep dive, scenario, AI explanations.
- Forecast V2 is currently an offline research/scoring engine, not fully wired into the live API path.
- `active_docs/FORECAST_V2_ENGINE_AUDIT.md` notes that the live `/api/forecast` route still points to older forecast code.

### Data

Main SQLite DB:

```text
backend/data/supply_chain.db
```

Important folders:

- `forecast_data/` - early forecast CSVs and technical CSV spec.
- `9 stores full info ( pipera not full)/` - multi-store sales exports.
- `stock_related_data/` - store/supplier/stock/lifecycle stock files.
- `new_stock_data_20may/` - supplier/stock package audited in Phase 8A.
- `backend/data/forecast_v2_feature_cache/` - cached V2 feature matrices.
- `active_docs/` - active reports, current handoffs, scorecards, audits, and specs.
- `archive_past_docs/` - older archived docs.

## Main Documentation Reading Order

Use this order when opening a new chat or starting V3 planning.

### 1. Current Status

Read:

- `active_docs/FORECAST_V2_CURRENT_HANDOFF.md`

This is the best single file for the current V2 state. It contains the latest promoted policy, recent phase summaries, final decision, and stop condition.

### 2. Business/Data Semantics

Read:

- `active_docs/FORECAST_V2_DATA_DICTIONARY_AND_BUSINESS_RULES.md`
- `active_docs/FORECAST_V2_SALES_EXPORT_COMPLETENESS_CHECKLIST.md`
- `forecast_data/csv_spec.md`

Important: the data dictionary is newer and should win over the older CSV spec when business interpretation conflicts.

### 3. Final V2 Promotion Result

Read:

- `active_docs/ITER5AE_V2_PHASE8G_P_FINAL_PROMOTION_PACK.md`

This is the final current-data V2 promotion report. It explains why `8go_pre_bf_bfc_lift_180` was promoted and why current-data iteration should stop.

### 4. Full Engine Audit

Read:

- `active_docs/FORECAST_V2_ENGINE_AUDIT.md`

This is the full mechanical audit of V2: ingestion, target, score formulas, model behavior, risks, and why the low hit rate is not explained by one simple arithmetic bug.

### 5. Original V2 Rebuild Strategy

Read:

- `FORECAST_V2_REBUILD_PLAN.md`

This explains why V2 was created and why the old WMAPE/median-ensemble path was abandoned.

### 6. Project Timeline

Read:

- `PROGRESS.md`
- `active_docs/FORECAST_ENGINE_ITERATIONS.md`

Use these for the long build history. They include older MVP phases and forecast iterations. They are useful, but for current modeling decisions prefer the newer V2 reports.

## Methodology Evolution

### Original MVP

The repository started as a supply-chain decision engine:

- Dead stock detection.
- Supplier reliability scoring.
- Demand and trend analysis.
- Scenario simulation.
- Morning decision queue.
- SKU deep dive pages.
- Decision logging.
- AI explanation layer.

This app is valuable as product context, but it is not the current forecast research path.

### Forecast Engine Iterations Before V2

Early forecast work tested real Mobexpert sales windows with a smaller SKU set. The first meaningful tests showed a key problem:

- Aggregate accuracy could look acceptable.
- Individual SKU accuracy was weak.
- Optimizing WMAPE improved some aggregate numbers but did not produce useful SKU-level predictions.

Important decision:

- WMAPE became a diagnostic metric, not the primary acceptance gate.
- Hit rate within +/-20% and +/-30% became central because the buyer needs SKU-level usefulness, not only good total volume.

### Why Forecast V2 Was Built

V2 was built because the old engine path had the wrong optimization shape.

Old approach problems:

- WMAPE-first decisions.
- Per-store-first forecasting too early.
- Median ensemble as the main method.
- Uniform bias correction.
- Post-hoc seasonal dampening.
- Too much focus on aggregate performance.
- Too little focus on forecastable high-revenue SKU/windows.

V2 principles:

- Separate V2 under `backend/forecast_engine_v2/`.
- Chain-level forecast first, store allocation later.
- Direct next-4-week target instead of recursive week-by-week forecasting.
- Regime/routing logic.
- Rolling-window backtesting.
- Leak-safe features.
- Hit +/-20 on business-relevant high-revenue movers as the main KPI.

## Forecast V2 Technical Design

### Forecast Unit

V2 forecasts:

```text
SKU chain total demand for the next 4 weeks
```

It does not currently forecast store-level units as the primary target.

### Target Definition

Current official demand target:

```text
gross positive physical-product units
```

Reason:

- Returns are post-sale behavior, not the same thing as no demand.
- Negative return rows are tracked separately.
- Services are not part of physical product demand.

Target and scoring come from `scorecard.py`.

### Date Logic

Preferred demand date:

```text
DATA COMANDA
```

Fallback:

```text
DATA
```

Business meaning:

- `DATA COMANDA` is when the customer placed the order.
- `DATA` is invoice/check date, often delivery/final payment date.
- Custom orders can have large lag between the two.
- V2 stores `sale_date_source`, `used_invoice_date_fallback`, and `invoice_lag_days`.

Important underused signal:

- Invoice/order lag is captured but not yet deeply modeled as custom/order-delay behavior.

### Score Metrics

For quantity-scored rows:

- `hit +/-20`: absolute percent error <= 20%.
- `hit +/-30`: absolute percent error <= 30%.
- `WMAPE`: total absolute error divided by total actual units.
- `bias`: total signed error divided by total actual units.

For zero-actual rows:

- `phantom`: actual units = 0 and predicted units >= 1.

Quantity scoring uses rows with enough actual units. Very low actuals are harsh: one unit of error on four actual units is already a 25% error.

### Model Family

Current official model path:

- scikit-learn direct 4-week regressors.
- ExtraTrees and HistGradientBoosting candidates.
- Postprocessing/policy logic for high-revenue route behavior.
- Explicit high-revenue policy flags in `sklearn_direct_model.py`.

The promoted V2 policy is not a pure ML model. It is an official high-revenue policy layered on top of the model outputs:

```text
--high-revenue-policy pre_bf_bfc_lift_180 --revenue-rank-limit 1000
```

This is intentional. The current ML model alone did not solve the pre-BF/campaign underprediction problem.

## Key Decisions And Corrections

### Decision: Stop Optimizing The Old Engine

Reason:

- The old engine could improve WMAPE while hurting SKU-level hit rate.
- It did not align tightly enough with the business KPI.

Correction:

- Freeze the old engine as a benchmark.
- Move serious work to `backend/forecast_engine_v2/`.

### Decision: Forecast High-Revenue Products First

Reason:

- Fyo's goal is not low-volume SKU perfection.
- Forecasting high-revenue products creates the most business value.
- Low-volume rows can make +/-20 accuracy mathematically unfair.

Correction:

- Phase 8G introduced Top 1000 high-revenue evaluation.
- Current official policy is Top 1000 scoped.

### Mistake Corrected: Stock Was Treated Too Much Like Availability/Sellability

Business clarification:

- At Mobexpert, a SKU can sell even if not physically in store/supplier/warehouse stock.
- If the SKU is active/orderable/listed, it can be sold.

Correction:

- Stock is now described as `stock_position` / `fulfillment_context`, not sellability.
- Stock-derived route language was reframed in Phase 8G-M.
- Active/orderable/listed history is now considered a critical missing data need.

Read:

- `active_docs/ITER5AA_V2_PHASE8G_BUSINESS_SEMANTICS_AUDIT.md`
- `active_docs/ITER5AB_V2_PHASE8G_M_HYGIENE_SEMANTICS.md`

### Mistake Corrected: Discount Hygiene

Finding:

- Some discount rows contained infinite or impossible values.
- These reached weekly aggregates and could poison feature averages/maxes.

Correction:

- Non-finite discounts and finite values above fraction scale are excluded from model discount features.
- Cleaned champion reproduced the same score, so this was correctness work, not a promoted accuracy gain.

Read:

- `active_docs/ITER5AB_V2_PHASE8G_M_HYGIENE_SEMANTICS.md`

### Mistake Corrected: Broad BF/Campaign Lift Was Too Blunt

Finding:

- A broad campaign/BF lift improved aggregate score but created unstable window regressions.
- The worst regression was around `2024-12-30` in the calibrated 1.50 lift test.

Correction:

- Do not promote broad campaign lifts.
- Promote only guarded pre-BF campaign-sensitive lift logic that did not damage guard windows.

Read:

- `active_docs/ITER5Z_V2_PHASE8G_OFFICIAL_CALIBRATED_POLICY.md`
- `active_docs/ITER5AD_V2_PHASE8G_O_GUARDED_CAMPAIGN_CALIBRATION.md`
- `active_docs/ITER5AE_V2_PHASE8G_P_FINAL_PROMOTION_PACK.md`

### Decision: Stop Current-Data Iteration

Reason:

- Stock-soft retraining only reached +0.4pp hit +/-20 and missed the promotion gate.
- Guarded campaign calibration gave the last meaningful current-data win.
- Further blind iteration is likely low-value without richer data.

Correction:

- Current official policy was promoted.
- Next work should use new richer data and/or a V3 redesign.

## V2 Build Timeline

This timeline is intentionally more detailed for recent work and more compressed for older work.

### Early MVP And Legacy Forecast Work

- March 2026: built the original supply-chain MVP with dead stock, supplier reliability, scenario simulation, decision queue, frontend pages, API routes, and AI explanations.
- April 2026: shifted attention from demo functionality to real forecast accuracy on Mobexpert sales data.
- Iterations 2-4: tested the older forecast engine and learned that aggregate accuracy and WMAPE could be misleading for SKU-level usefulness.
- May 2026: decided to rebuild Forecast V2 as a separate track.

Read:

- `PROGRESS.md`
- `active_docs/FORECAST_ENGINE_ITERATIONS.md`
- `FORECAST_V2_REBUILD_PLAN.md`

### Forecast V2 Foundation

V2 introduced:

- Multi-store CSV ingestion.
- Raw immutable-ish transaction storage.
- Weekly store and chain demand tables.
- Regime labels.
- Direct 4-week targets.
- Rolling historical validation windows.
- Leak-safe feature matrices.
- High-revenue and forecastability logic.

Important files:

- `backend/forecast_engine_v2/ingestion.py`
- `backend/forecast_engine_v2/regime_labels.py`
- `backend/forecast_engine_v2/scorecard.py`
- `backend/forecast_engine_v2/feature_matrix.py`

### Phase 8A-8C: New Data And Store Stock

Files:

- `active_docs/ITER5J_V2_NEW_DATA_AUDIT.md`
- `active_docs/ITER5K_V2_PHASE8B_BANEASA_2022_INGESTION.md`
- `active_docs/ITER5L_V2_PHASE8C_MONTHLY_STORE_STOCK.md`

What happened:

- New stock/data package was audited.
- Baneasa 2022 ingestion was added to improve coverage.
- Monthly store stock ingestion was added.

Main lesson:

- More data helped coverage, but store stock was too sparse and uneven to be the central availability signal.

### Phase 8D-8F: Supplier Stock, Availability Features, Rotation Snapshot

Files:

- `active_docs/ITER5M_V2_PHASE8D_SUPPLIER_STOCK.md`
- `active_docs/ITER5N_V2_PHASE8E_AVAILABILITY_FEATURE_MATRIX.md`
- `active_docs/ITER5N_V2_PHASE8E_AVAILABILITY_MODEL.md`
- `active_docs/ITER5O_V2_PHASE8F_ROTATION_SNAPSHOT.md`

What happened:

- Supplier stock was ingested and mapped to SKUs where exact unique mappings were safe.
- Supplier/combined stock-position features were added to the feature matrix.
- The model was rerun with these features.
- Rotation snapshot data was ingested as current snapshot only.

Main lesson:

- Supplier stock coverage was much stronger than store stock.
- Availability/stock-position features improved diagnostics but did not create a big hit-rate jump.
- Rotation snapshot data cannot be used in historical backtests unless historical-as-of dates exist.

### Phase 8G: High-Revenue Final Push

Phase 8G is the key recent wave. It moved the project from roughly 24% hit +/-20 into the final promoted Top 1000 high-revenue policy at 27.4%.

The important reports are listed below in chronological order.

## Recent Phase Summary

### Phase 8G-A: High-Revenue Benchmark

File:

- `active_docs/ITER5P_V2_PHASE8G_HIGH_REVENUE_BENCHMARK.md`

Key finding:

- Clean Top 1000 regular/proxy-regular slice hit +/-20 reached 32.3%.
- This proved the model could do better on cleaner high-revenue subsets.

### Phase 8G-B: Stock Coverage Audit

File:

- `active_docs/ITER5Q_V2_PHASE8G_STOCK_COVERAGE_AUDIT.md`

Key finding:

- Store stock history was too sparse.
- Supplier stock coverage was much stronger.

### Phase 8G-C: Campaign Field Audit

File:

- `active_docs/ITER5R_V2_PHASE8G_CAMPAIGN_FIELD_AUDIT.md`

Key finding:

- Campaign/BF history is present and important.
- Even "regular" rows often had campaign history.

### Phase 8G-D/E/F: Route And Campaign Models

Files:

- `active_docs/ITER5S_V2_PHASE8G_ROUTE_SPECIFIC_MODEL.md`
- `active_docs/ITER5T_V2_PHASE8G_CAMPAIGN_SENSITIVE_MODEL.md`
- `active_docs/ITER5U_V2_PHASE8G_COMBINED_ROUTE_MODEL.md`

Key finding:

- Route-specific handling created the first stackable high-revenue win.
- BF/campaign-sensitive demand was still the hardest route.

### Phase 8G-G/H/I: Promotion, Wiring, Official Validation

Files:

- `active_docs/ITER5V_V2_PHASE8G_PROMOTION_PACK.md`
- `active_docs/ITER5W_V2_PHASE8G_HIGH_REVENUE_POLICY_WIRING.md`
- `active_docs/ITER5X_V2_PHASE8G_OFFICIAL_POLICY_VALIDATION.md`

Key result:

- `8gf_regular_plus_post_bf_safe` became the official high-revenue champion.

### Phase 8G-J/K: Calibration Attempt And Rejection

Files:

- `active_docs/ITER5Y_V2_PHASE8G_MONITOR_CALIBRATION.md`
- `active_docs/ITER5Z_V2_PHASE8G_OFFICIAL_CALIBRATED_POLICY.md`

Key result:

- `8gj_bfc_nonpost_lift_150` improved aggregate metrics but failed stability gates.
- It was not promoted.

### Phase 8G-L/M: Business Semantics And Hygiene

Files:

- `active_docs/ITER5AA_V2_PHASE8G_BUSINESS_SEMANTICS_AUDIT.md`
- `active_docs/ITER5AB_V2_PHASE8G_M_HYGIENE_SEMANTICS.md`

Key result:

- Stock was reframed as fulfillment context.
- Discounts were sanitized.
- Returns stayed separate from gross demand.

### Phase 8G-N: Stock-Soft Variants

File:

- `active_docs/ITER5AC_V2_PHASE8G_N_STOCK_SOFT_REBUILD.md`

Key result:

- Best variant improved hit +/-20 from 25.3% to 25.7%, but missed the +0.5pp gate.
- Stock-feature ablation was worse.
- Decision: stop stock iteration until active/orderable/listed history arrives.

### Phase 8G-O/P: Guarded Campaign Calibration And Final Promotion

Files:

- `active_docs/ITER5AD_V2_PHASE8G_O_GUARDED_CAMPAIGN_CALIBRATION.md`
- `active_docs/ITER5AE_V2_PHASE8G_P_FINAL_PROMOTION_PACK.md`

Key result:

- `8go_pre_bf_bfc_lift_180` promoted.
- Final current-data iteration stopped.

### May 29-31: Export Checklist And Data Semantics Handoff

Files:

- `active_docs/FORECAST_V2_SALES_EXPORT_COMPLETENESS_CHECKLIST.md`
- `active_docs/FORECAST_V2_DATA_DICTIONARY_AND_BUSINESS_RULES.md`

What happened:

- Fyo started preparing richer all-store/year exports for the next modeling wave.
- The export checklist was split into P1/P2 because the database cube crashes when too many columns are selected.
- `COD ARTICOL`, `MAGAZIN`, and `DATA` are required in both P1 and P2 for safer merging.
- A full business/data dictionary was created and updated with column meanings, open questions, and underused-signal assessment.

Main lesson:

- The next jump should come from correctly using richer data: active/listing status, online/offline/outlet route, lifecycle, product text, dimensions, order lag, montage/custom-friction, campaign membership, and price/discount history.

## Data Semantics Most Likely To Matter For V3

The newest data dictionary should be treated as the source of truth:

- `active_docs/FORECAST_V2_DATA_DICTIONARY_AND_BUSINESS_RULES.md`

Important current clarifications:

- `VALOARE FACTURATA` is the final amount paid by the customer. It includes discounts and VAT.
- The provided CSVs do not expose first/second payment splits for custom orders.
- `CANTITATE FACTURATA` negative means returns.
- Demand target should remain gross positive units; returns are separate context.
- `DATA COMANDA` is order date; `DATA` is invoice/check/delivery/final-payment-like date and a fallback when order date is missing.
- `GRUPA MEDIU VANZARE` separates `OFFLINE`, `ONLINE`, and `OUTLET`.
- `RAION` is product area/gamma, except `ONLINE` means online context.
- `DENUMIRE ARTICOL` is underused. It is stored and partly parsed, but not yet deeply exploited for product type/material/family/similarity.
- `ACTIV` and `ACTIV ONLINE` are likely critical, but it is still unknown whether they are historical-as-of sale date or current export status.
- `VECHIME IN COLECTIE` is likely critical lifecycle data, but it must be historical-as-of to use safely in backtests.
- `NECESITA MONTAJ` is useful friction/context, but exact code meanings still need clarification.

Open questions are maintained at the bottom of:

- `active_docs/FORECAST_V2_DATA_DICTIONARY_AND_BUSINESS_RULES.md`

## Data Exports Currently Being Prepared

Fyo is exporting richer sales data by store/year. The database export UI crashes if too many columns are selected, so exports are split into P1 and P2.

Checklist:

- `active_docs/FORECAST_V2_SALES_EXPORT_COMPLETENESS_CHECKLIST.md`

Rules:

- Include `COD ARTICOL`, `MAGAZIN`, and `DATA` in both P1 and P2 for safer merging.
- Measures are expected: `REDUCERE`, `CANTITATE FACTURATA`, `VALOARE FACTURATA`.
- Filter-only fields may include `AN`, `CLIENT SPECIFIC`, and `GRUPA DIRECTII_LICITATII`.

Standard P1 columns:

```text
COD ARTICOL
DATA
FURNIZOR
FURNIZOR EXT
GRUPA
GRUPA MEDIU VANZARE
GRUPA_PRODUSE
ID FURNIZOR
MAGAZIN
NECESITA MONTAJ
NR COMANDA
STIL
```

Standard P2 columns usually include the remaining needed fields:

```text
ACTIV
ACTIV ONLINE
CAMPANIE SELECTATA
CATEGORIE
CLASA
DATA COMANDA
DENUMIRE ARTICOL
DIMENSIUNI
ID CLIENT
ID COMANDA
ID FACTURA
OUTLET
RAION
SUBCLASA
SUBSTIL
VECHIME IN COLECTIE
```

## Current Data Gaps That Limit Accuracy

Highest-value missing or incomplete data:

1. Active/orderable/listed SKU history by date.
2. Future campaign membership and planned discounts.
3. Historical price levels and price changes.
4. Fuller 2022-2025 hyperstore sales coverage with richer columns.
5. Lifecycle/as-of product status, especially `VECHIME IN COLECTIE`.
6. Customer order status/history if available.
7. Clarified channel and outlet fields.
8. Reliable online/offline listing status by date.

Stock remains useful, but not as a sellability gate.

## Known Risks And Caveats

- Current V2 score is rolling backtest validation on known windows, not independent future holdout validation.
- The official V2 policy is Top 1000 high-revenue scoped. Do not claim it as full-catalog performance.
- Current snapshot stock/rotation data must not be used in historical backtests.
- `ACTIV`, `ACTIV ONLINE`, and `VECHIME IN COLECTIE` can leak future information if they are current export status rather than historical-as-of fields.
- The live FastAPI app path is not the same as the V2 offline research path.
- The current hit +/-20 score is still low enough that V3 should rethink the system, not just tune V2.

## Useful Commands

Run V2 ingestion dry-run:

```bash
PYTHONPATH=backend python3 backend/forecast_engine_v2/ingestion.py --input "9 stores full info ( pipera not full)" --dry-run
```

Run V2 ingestion rebuild:

```bash
PYTHONPATH=backend python3 backend/forecast_engine_v2/ingestion.py --input "9 stores full info ( pipera not full)" --rebuild
```

Run official high-revenue policy from sklearn path:

```bash
PYTHONPATH=backend python3 backend/forecast_engine_v2/sklearn_direct_model.py --revenue-rank-limit 1000 --high-revenue-policy pre_bf_bfc_lift_180
```

Run final promotion pack:

```bash
PYTHONPATH=backend python3 backend/forecast_engine_v2/phase8gp_final_promotion_pack.py
```

Run data/business semantics audit:

```bash
PYTHONPATH=backend python3 backend/forecast_engine_v2/phase8g_business_semantics_audit.py
```

## V3 Starting Point

V3 should start from the current V2 facts, not from scratch.

Keep from V2:

- Chain-level direct 4-week target discipline.
- Rolling-window backtesting.
- High-revenue focus.
- Leak-safe feature discipline.
- Gross positive demand target with returns separated.
- Campaign/BF caution.
- Business-semantics file and export checklist.

Rethink for V3:

- Stronger data contract around active/orderable/listed state.
- Better route architecture for offline/online/outlet.
- Better product representation using `DENUMIRE ARTICOL`, hierarchy, dimensions, style, lifecycle, and supplier.
- Explicit handling of custom/order-lag behavior from `DATA` vs `DATA COMANDA`.
- Better campaign and price model, ideally using planned future campaign/discount data.
- Better distinction between forecastable demand, promotion demand, custom-order demand, outlet/clearance demand, and low-signal intermittent demand.
- Persisted score rows and reproducible experiment registry, not only Markdown reports.
- Eventual API/app integration once the offline V3 model is materially better.

## Most Important Principle

Do not chase accuracy by blindly adding features.

Every new improvement should answer a specific failure mode:

- Was the product active/orderable?
- Was it online, offline, or outlet?
- Was it in campaign or BF?
- Was price/discount materially different?
- Is the SKU new, mature, declining, or discontinued?
- Is it custom/order-lagged?
- Is it a product family with repeatable behavior?
- Is the row actually a physical product sale?

That is the bridge from the current V2 system to the V3 system Fyo wants to build.
