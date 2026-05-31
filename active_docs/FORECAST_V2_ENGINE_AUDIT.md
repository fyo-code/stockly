# Forecast V2 Engine Full Audit

Generated: 2026-05-22

Scope: this audit covers the offline Forecast V2 engine under
`backend/forecast_engine_v2`, the current score reports in `active_docs`, the
SQLite state in `backend/data/supply_chain.db`, and the older live FastAPI
forecast route for integration comparison.

This is intentionally not a fix plan yet. It is a mechanical breakdown of what
the engine does, what it measures, and where the current 24 percent hit-rate
ceiling is probably coming from.

## Executive Verdict

There is no obvious single arithmetic bug that explains the low accuracy. The
engine is mostly leak-safe and the basic formulas are coherent. The bigger
problem is that the system is asking a simple global model to predict a hard,
noisy retail target with weak operational context.

The current best raw Phase 8E result is `sk_extra_trees` at 24.6 percent hit
+/-20. The safer blend is 24.2 percent hit +/-20, 55.6 percent WMAPE, and 44.4
percent phantom rate. Those scores are poor, but they are consistent with the
engine design:

- The target is 4-week chain-level positive units, not true net units.
- Many scored rows are very low volume. Across the 30,891 headline SKU-windows,
  53.1 percent have fewer than 4 actual units and are not quantity-scored. Of
  the scored rows, 30.0 percent are only 4 to 5 units.
- A one-unit miss on 4 actual units is already a 25 percent error, so the
  headline hit +/-20 KPI is very harsh for this population.
- Availability, supplier stock, and route labels are mostly features and
  diagnostics. They do not yet gate the target, censor stockouts, or train
  route-specific objectives.
- Black Friday and campaign behavior owns a large share of the error, but the
  engine has only inferred BF timing and discount proxies, not actual campaign
  SKU membership/calendar mechanics.
- The model objective is not the KPI. The ML regressors optimize squared error
  or Poisson loss, then a coarse postprocess tunes hit +/-20 on prior windows.
- The walk-forward training set has many rows but few independent target
  windows. The model is learning cross-sectional SKU patterns more than robust
  temporal shocks.

There are also two system-level issues separate from model accuracy:

- The live FastAPI app currently fails to import because `backend/api/demand.py`
  imports missing module `engines.demand`.
- The live `/api/forecast` route is still wired to the older
  `backend/forecast_engine` stack, not Forecast V2. Phase 8E/8F work is offline
  research/reporting, not the live app path.

## Current Artifacts And DB State

Latest completed phases:

- Phase 8D supplier stock ingestion: complete.
- Phase 8E supplier/combined availability feature matrix: complete.
- Phase 8E model rerun: complete.
- Phase 8F rotation snapshots: ingested as current snapshot only, not
  historical backtest-safe data.

Current DB row counts observed during this audit:

| Table | Rows / SKUs |
| --- | ---: |
| `raw_sales_transactions_v2` | 2,094,936 rows, 115,615 SKUs |
| `weekly_chain_demand_v2` | 1,226,529 rows, 115,478 SKUs |
| `forecast_v2_regime_labels` | 1,078,378 rows, 100,935 SKUs |
| `stock_monthly_store_v2` | 707,148 rows, 13,351 SKUs |
| `stock_monthly_supplier_v2` | 1,821,659 rows, 76,858 SKUs |
| `stock_rotation_snapshot_v2` | 211,056 rows, 61,121 SKUs |

Important persistence gap:

- `forecast_v2_score_runs` is absent in the current DB state.
- Recent model reports were generated via fast in-memory scoring, not persisted
  row-level score tables.
- That is acceptable for iteration speed, but weak for reproducibility and
  forensic audit.

## System Map

Forecast V2 is an offline engine:

1. Import raw sales files into normalized v2 transaction tables.
2. Aggregate sales into weekly chain/store demand.
3. Build cutoff-specific regime labels.
4. Build naive 4-week predictions.
5. Build actual 4-week targets and score rows.
6. Build leak-safe feature matrices.
7. Add availability and route labels.
8. Train walk-forward direct models.
9. Generate Markdown reports.

The live app path is different:

- `backend/main.py` imports API routers.
- `backend/api/forecast.py` uses the old `backend/forecast_engine` modules.
- `backend/api/demand.py`, `backend/api/sku.py`, and `backend/api/queue.py`
  import `engines.demand`, which is missing.
- Therefore importing `backend/main.py` currently fails.

## Ingestion Calculations

Main file: `backend/forecast_engine_v2/ingestion.py`.

For each sales CSV row:

- SKU, store, category, product family, hierarchy, and supplier fields are read
  from normalized CSV headers.
- `sale_date` is chosen as order date if present, otherwise invoice date.
- `sale_date_source` records whether the date came from order date or invoice
  date fallback.
- `quantity` is `CANTITATE FACTURATA`.
- `line_value` is `VALOARE FACTURATA`.
- `gross_units = max(quantity, 0)`.
- `returned_units = abs(quantity)` if quantity is negative, else 0.
- `net_units = gross_units - returned_units`.
- Revenue follows the same gross/returned/net pattern.
- Black Friday and campaign fields are converted into observed/inferred/unknown
  signals.
- Non-product rows are marked and excluded from many downstream target queries.

This design is reasonable, but the date fallback matters. If many older rows
use invoice date rather than order date, demand timing can be shifted by days or
weeks. That can damage a 4-week target even when total demand is correct.

## Weekly Demand Layer

The engine scores chain-level demand from `weekly_chain_demand_v2`.

Key implication: all stores are collapsed into one chain SKU-week record. This
helps when store-level stock is incomplete, but it hides store-specific
availability. A SKU may be available in one store and constrained in another;
the model sees a single chain quantity.

The scoring target uses positive-clipped weekly units:

- `pos_units = max(net_units, 0)` at the weekly row level.
- Future actual target is the sum of `pos_units` over the target horizon.

This means negative weeks do not offset positive weeks in the score target. The
engine also tracks `actual_net_units_4w`, but hit +/-20 is based on
`actual_pos_units_4w`.

That may be the right business definition if the goal is gross customer demand,
but it is not the same as net sell-through after returns.

## Regime Label Calculations

Main file: `backend/forecast_engine_v2/regime_labels.py`.

For each `as_of_week`, labels use only history up to the cutoff.

Core measures:

- `trailing_52w_revenue`: net revenue over the trailing 52 weeks.
- `trailing_52w_pos_units`: positive units over the trailing 52 weeks.
- `active_weeks_52`: weeks with positive demand in the trailing 52 weeks.
- `active_4w_windows_52`: count of active rolling 4-week windows.
- `avg_units_per_4w_52`: trailing 52-week units normalized to 4 weeks.
- `active_months_104`, `top3_month_unit_share_104`, `monthly_cv_104`,
  `active_years_104`, and `recurring_active_months_104`: longer seasonal and
  recurrence signals.
- Revenue rank and cumulative revenue share are computed from trailing 52-week
  revenue.

Headline eligibility:

- SKU must be in the top 80 percent cumulative trailing revenue set.
- `active_weeks_52 >= 12`.
- `active_4w_windows_52 >= 26`.
- `avg_units_per_4w_52 >= 2.0`.

Regimes are assigned roughly from inactive/weak to stronger demand:

- `dormant`
- `long_tail_active`
- `sparse_revenue_items`
- `active_movers`
- `seasonal_revenue_movers`
- `forecastable_revenue_movers`

Audit note: this is sales/revenue based. It does not know whether historical
low demand was true demand weakness or stock/campaign/lifecycle censorship.
That makes the headline population clean in a revenue sense, but not
necessarily clean in an operational forecasting sense.

## Naive Prediction Calculations

Main file: `backend/forecast_engine_v2/scorecard.py`.

Each target is a Monday `target_start` and a 4-week horizon.

For each SKU:

- `zero = 0`.
- `last4 = sum(pos_units)` over the 4 weeks immediately before
  `target_start`.
- `roll8_mean = sum(pos_units over prior 8 weeks) / 8 * 4`.
- `roll13_mean = sum(pos_units over prior 13 weeks) / 13 * 4`.
- `seasonal52 = sum(pos_units)` over the same 4-week calendar slot 52 weeks
  earlier.
- `median_naive = median(last4, roll13_mean, seasonal52)`.

The median naive is intentionally simple and robust. It is also too blunt for
campaigns, stockouts, discontinuations, and new/ramping SKUs.

## Actual Target And Score Calculations

Main file: `backend/forecast_engine_v2/scorecard.py`.

For each target SKU:

- `actual_pos_units_4w = sum(max(net_units, 0))` over target weeks.
- `actual_net_units_4w = sum(net_units)` over target weeks.
- `actual_net_revenue_4w = sum(net_revenue)` over target weeks.
- `negative_unit_weeks = count(weeks where net_units < 0)`.
- BF/campaign transaction counts are collected from raw transactions inside
  the target date range.

For each prediction:

- `actual_units = actual_pos_units_4w`.
- `pred_units = max(pred_units_4w, 0)`.
- `abs_error = abs(pred_units - actual_units)`.
- `signed_error = pred_units - actual_units`.
- `quantity_scored = actual_units >= 4.0`.
- `abs_pct_error = abs_error / actual_units` only for quantity-scored rows.
- `hit20 = abs_pct_error <= 0.20`.
- `hit30 = abs_pct_error <= 0.30`.
- `under20 = pred_units < 0.80 * actual_units`.
- `over20 = pred_units > 1.20 * actual_units`.
- `phantom = actual_units == 0 and pred_units >= 1.0`.
- `pred_sale = pred_units >= 1.0`.
- `actual_sale = actual_units > 0`.

Aggregate metrics:

- `hit +/-20 = mean(hit20)` over quantity-scored rows.
- `hit +/-30 = mean(hit30)` over quantity-scored rows.
- `WMAPE = sum(abs_error) / sum(actual_units)` over quantity-scored rows.
- `bias = sum(signed_error) / sum(actual_units)` over quantity-scored rows.
- `phantom_rate = mean(phantom)` over zero-actual rows.
- `winrate_vs_median_naive = share of scored rows where model abs error is
  lower than median naive abs error`.

The KPI is row-count based, not revenue-weighted. One tiny SKU-window counts as
much as one major SKU-window for hit +/-20.

## Target Difficulty Check

I queried the current DB using all 12 default target windows and headline
labels.

Distribution of actual 4-week positive units:

| Bucket | Rows | Share | Scored rows | Avg actual |
| --- | ---: | ---: | ---: | ---: |
| 0 units | 5,963 | 19.3% | 0 | 0.00 |
| 1 to 3 units | 10,448 | 33.8% | 0 | 1.89 |
| 4 to 5 units | 4,350 | 14.1% | 4,350 | 4.41 |
| 6 to 9 units | 4,385 | 14.2% | 4,385 | 7.20 |
| 10 to 19 units | 3,379 | 10.9% | 3,379 | 13.23 |
| 20 to 49 units | 1,741 | 5.6% | 1,741 | 29.48 |
| 50+ units | 625 | 2.0% | 625 | 117.06 |

Implications:

- More than half of headline rows are not quantity-scored because future demand
  is below 4 units.
- 30.0 percent of scored rows are 4 to 5 units.
- For 4 actual units, the model must predict from 3.2 to 4.8 units to hit
  +/-20. A one-unit miss fails.
- For 5 actual units, the model must predict from 4 to 6 units. Again, a
  one-unit miss can decide the KPI.

Per-window scored rows:

| Target start | Headline rows | Scored rows | Scored share | Scored rows at 4-5 units | Share of scored at 4-5 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2024-04-29 | 2,375 | 938 | 39.5% | 328 | 35.0% |
| 2024-05-27 | 2,434 | 1,057 | 43.4% | 333 | 31.5% |
| 2024-07-01 | 2,501 | 1,061 | 42.4% | 359 | 33.8% |
| 2024-07-29 | 2,536 | 1,149 | 45.3% | 404 | 35.2% |
| 2024-08-26 | 2,602 | 1,424 | 54.7% | 410 | 28.8% |
| 2024-09-23 | 2,623 | 1,367 | 52.1% | 398 | 29.1% |
| 2024-10-28 | 2,630 | 1,858 | 70.6% | 298 | 16.0% |
| 2024-11-25 | 2,692 | 989 | 36.7% | 351 | 35.5% |
| 2024-12-30 | 2,659 | 1,078 | 40.5% | 332 | 30.8% |
| 2025-01-27 | 2,638 | 1,231 | 46.7% | 390 | 31.7% |
| 2025-02-24 | 2,605 | 1,123 | 43.1% | 363 | 32.3% |
| 2025-03-24 | 2,596 | 1,205 | 46.4% | 384 | 31.9% |

This does not excuse poor performance, but it changes expectations. An 80
percent hit +/-20 target is unlikely without either a narrower KPI population,
a different KPI, or much richer operational signals.

## Feature Matrix Calculations

Main file: `backend/forecast_engine_v2/feature_matrix.py`.

The feature matrix is built per target start. It loads:

- Cutoff labels.
- Naive predictions.
- Actuals for scoring only.
- 52 weeks of weekly history before the target.
- Previous completed monthly store stock history.
- Previous completed monthly supplier stock history.

Feature groups:

Calendar/BF target features:

- target month, quarter, ISO week, Q4 flag, November flag.
- whether the target starts inside BF, pre-BF, or post-BF windows.
- days from BF start/end.
- number of horizon days overlapping BF, pre-BF, and post-BF windows.

Sales history windows:

- 4w, 8w, 13w, 26w, and 52w positive units.
- 4w, 13w, and 52w revenue.
- gross units, returned units, transaction counts.
- average and max discount.
- online and outlet transaction counts.
- max stores/hyperstores/smaller stores selling.

Derived demand features:

- `avg_unit_price = revenue / pos_units`.
- `return_rate_units = returned_units / gross_units`.
- `online_txn_share = online_txn / transactions`.
- `outlet_txn_share = outlet_txn / transactions`.
- `last4_to_roll13 = last4 / roll13_mean`.
- `seasonal_to_roll13 = seasonal52 / roll13_mean`.
- `median_to_avg4w = median_naive / avg_units_per_4w_52`.

BF contamination features:

- A week is treated as BF-contaminated if `bf_transaction_count > 0`.
- BF units and non-BF units are split for 4w and 13w windows.
- `bf_unit_share = bf_units / pos_units`.
- `bf_txn_share = bf_txn / transactions`.
- `non_bf_pos_units_equiv = non_bf_units / non_bf_calendar_weeks * 4`.
- `post_bf_last4_bf_unit_share = target_is_post_bf_4w * bf_unit_share_4w`.
- `post_bf_last4_to_roll13 = target_is_post_bf_4w * last4_to_roll13`.

Store stock features:

- Uses only prior completed stock months.
- Collapses store-month rows to chain-level SKU-month stock.
- Previous, two-month, and three-month stock quantities.
- 3-month average and trend.
- observed months and zero-stock months in the prior 6 months.
- whether previous month stock was observed and positive.
- likely stockout before target if previous month observed and qty <= 0.
- stores/hyperstores with stock in previous month.
- stock coverage ratios versus recent demand.
- no-sales-despite-stock and sales-with-low-ending-stock flags.

Supplier stock features:

- Uses exact-unique product-name-to-SKU mappings only.
- Collapses supplier rows to SKU-month totals.
- Previous, two-month, and three-month supplier stock quantities.
- 3-month average and trend.
- observed months and zero-stock months in the prior 6 months.
- whether previous month supplier stock was observed and positive.
- previous month supplier stock value and trailing value average.
- suppliers observed and suppliers with positive stock.

Combined availability features:

- `combined_stock_prev_month_qty = store_stock_prev_month_qty + supplier_stock_prev_month_qty`.
- `combined_stock_observed_prev_month = store observed OR supplier observed`.
- `store_or_supplier_available_before_target = store stock > 0 OR supplier stock > 0`.
- coverage ratios against recent 4-week equivalent demand and 13-week demand.
- `likely_true_stockout_before_target` requires recent sales, combined stock
  observed, low/unknown store stock, and low supplier stock.
- `combined_stock_coverage_bucket` is one of missing, likely_stockout,
  available, observed_zero, or observed_unclear.

Audit note: these features are leak-safe, but still coarse. Monthly stock is
not the same as daily sellable availability. It does not include reservations,
inbound receipts, replenishment orders, lead time, or in-horizon stock arrival.

## Route Label Calculations

Main file: `backend/forecast_engine_v2/route_labels.py`.

Routes are leak-safe diagnostic labels derived from pre-target features.

Availability labels:

- `observed_available`: combined/store stock observed and stock is above recent
  demand threshold, or store/supplier availability is positive.
- `observed_constrained`: stock observed and likely stockout, low stock versus
  recent demand, or sales with low ending stock.
- `stock_unobserved`: no store or supplier stock history.
- `proxy_available`: no observed stock, but recurring demand is strong enough:
  `active_weeks_52 >= 24`, `avg_units_per_4w_52 >= 2`, and
  `zero_week_share_52 < 0.55`.
- `observed_unclear`: stock observed, but not confidently available or
  constrained.

Intermittency:

- regular if `active_weeks_52 >= 36` and `monthly_cv_104 < 0.70`.
- moderately intermittent if `active_weeks_52 >= 24` and zero-week share < 0.55.
- sparse/highly intermittent for lower activity and higher zero-week share.

Seasonality:

- seasonal if active months over 104 weeks are between 2 and 7, top 3 months
  carry at least 60 percent of units, monthly CV >= 0.90, active years >= 2,
  and there is recurring active-month evidence.

BF/campaign sensitivity:

- target starts in BF/pre-BF/post-BF window, or horizon overlaps BF/post-BF, or
  recent BF unit/transaction shares are high.

Primary route assignment order:

1. `stock_constrained`
2. `bf_campaign_sensitive`
3. `seasonal_active`
4. `seasonal_quiet`
5. `dormant_or_reactivation`
6. `sparse_intermittent`
7. `lifecycle_decline`
8. `available_regular`
9. `proxy_available_regular`
10. `availability_unknown`

This order matters. For example, BF-sensitive rows are routed before
available-regular rows, so a regular SKU inside the BF context becomes
`bf_campaign_sensitive`.

Audit note: route labels currently explain the system; they do not fully
control it. Phase 8G should change that.

## Model Calculations

### Direct Empirical Model

Main file: `backend/forecast_engine_v2/direct_model.py`.

This was an earlier dependency-light candidate.

It learns:

- A convex blend of `last4`, `roll13_mean`, and `seasonal52`.
- Candidate weights are searched in 0.1 increments and must sum to 1.
- Training objective chooses highest train hit +/-20, then lower WMAPE/bias.
- Base prediction is the weighted blend.
- Global factor = total actual units / total base units over scored training
  rows, clipped between 0.35 and 2.50.
- SKU/family/category calibration factors use smoothed actual/base ratios.
- Prediction applies the most specific available factor, with shrinkage back to
  category/global factors.

This model is understandable but too simple for the current problem.

### Sklearn Direct Model

Main file: `backend/forecast_engine_v2/sklearn_direct_model.py`.

Current Phase 8E model path:

- Build the whole feature matrix for target starts.
- For each target window:
  - train on rows with earlier `target_start`.
  - evaluate only the current `target_start`.
  - skip windows until at least 4 prior target windows exist.
- Population is headline only.

Preprocessing:

- Numeric features: median imputation.
- Categorical features: most frequent imputation plus ordinal encoding.
- Unknown categories get encoded as -1.

Models:

- `sk_hgb_poisson`: `HistGradientBoostingRegressor(loss="poisson")`.
- `sk_hgb_squared`: `HistGradientBoostingRegressor(loss="squared_error")`.
- `sk_extra_trees`: Extra Trees regressor with 260 trees, leaf size 8, and
  max features 0.80.

Postprocessing:

- For each model/window, raw predictions are tuned with:
  - multiplicative factor from 0.50 to 1.50 in 0.05 steps.
  - zero floor from 0, 0.5, 1, 1.5, 2, or 3 units.
- Tuning objective picks max train hit +/-20.
- Ties prefer lower train phantom, lower train WMAPE, then factor closer to 1.

Post-BF safeguard:

- If target is post-BF and recent last4 is BF-contaminated, a safe naive value
  is computed from non-BF recent equivalent demand, roll13, and seasonal52.
- ML predictions in contaminated post-BF rows are capped around safe baselines.
- `sk_blend_post_bf_safe` is the median of capped Poisson, capped Extra Trees,
  and the post-BF-safe naive prediction.

Audit note: the model is globally trained across routes. Availability and route
signals exist as features, but the model still learns one broad function for
campaign, regular, intermittent, lifecycle, and constrained cases.

## Score History And What It Says

Phase 8E aggregate:

| Model | Hit +/-20 | Hit +/-30 | WMAPE | Phantom |
| --- | ---: | ---: | ---: | ---: |
| median_naive | 19.8% | 30.1% | 57.4% | 69.9% |
| post_bf_safe_naive | 20.1% | 30.1% | 56.0% | 65.8% |
| sk_hgb_poisson | 24.3% | 35.3% | 58.1% | 36.2% |
| sk_hgb_squared | 24.6% | 36.2% | 61.0% | 52.3% |
| sk_extra_trees | 24.6% | 35.5% | 58.3% | 44.2% |
| sk_blend_median | 24.2% | 35.3% | 55.6% | 44.3% |
| sk_blend_post_bf_safe | 24.2% | 35.3% | 55.6% | 44.4% |

Interpretation:

- ML improves hit +/-20 by about 4.4 to 4.8 percentage points over median naive.
- WMAPE barely improves because the big absolute errors remain.
- Phantom rate improves a lot versus median naive, but remains high.
- Extra Trees is best raw hit-rate, but the safer blend is better on WMAPE and
  slightly safer operationally.

Train/eval gap:

- Extra Trees train hit +/-20 is around 43 to 44 percent across windows.
- Eval hit +/-20 is around 12.6 to 30.7 percent depending on window.
- This is not catastrophic model leakage; it is more likely a combination of
  small-window overfitting, nonstationary retail shocks, and tuning to a brittle
  metric.

Post-BF failure:

- Target `2024-11-25` remains bad.
- `median_naive`: 16.8 percent hit +/-20, 79.6 percent WMAPE, 80.1 percent
  phantom.
- `post_bf_safe_naive`: 20.0 percent hit +/-20, 66.3 percent WMAPE, 56.5
  percent phantom.
- `sk_blend_post_bf_safe`: 15.9 percent hit +/-20, 87.9 percent WMAPE, 74.7
  percent phantom.

The safe heuristic helps the naive path, but the blended ML path still fails
badly in this period. That points to campaign timing and demand pull-forward,
not just generic BF contamination.

## Route And Error Decomposition

From Phase 7E/7H diagnostics:

- BF/campaign-sensitive rows represent about 52.7 percent of revenue and 57.0
  percent of absolute error.
- Proxy-available regular rows represent about 31.5 percent of revenue and
  30.8 percent of absolute error.
- Sparse/intermittent rows have low hit-rate and strong underprediction.
- Stock-constrained observed rows are small in count because historical store
  stock coverage is narrow.

Control performance by route:

| Route | Qty scored | Hit +/-20 | WMAPE | Abs error share |
| --- | ---: | ---: | ---: | ---: |
| bf_campaign_sensitive | 4,948 | 21.4% | 61.9% | 57.0% |
| proxy_available_regular | 3,490 | 29.7% | 46.7% | 30.8% |
| sparse_intermittent | 1,630 | 19.8% | 60.1% | 10.2% |
| lifecycle_decline | 133 | 25.6% | 65.3% | 1.7% |
| stock_constrained | 19 | 10.5% | 57.6% | 0.1% |

Oracle ceiling from tested candidates:

- Current control: 24.1 percent hit +/-20, 56.1 percent WMAPE.
- Oracle over all tested candidates: 47.0 percent hit +/-20, 35.9 percent
  WMAPE.

This is very important: even perfect selection among all current candidate
models does not get close to 80 percent. The blocker is not just "choose a
different already-tested model."

## Main Audit Findings

### 1. Live backend defect

`backend/main.py` cannot import because `backend/api/demand.py` imports missing
module `engines.demand`.

This is a real system problem. It is not the cause of the offline Forecast V2
accuracy, but it means the app path is broken.

### 2. Forecast V2 is not wired into the live forecast API

The live `/api/forecast` route uses the old engine modules:

- ETS
- anomaly adjustment
- multi-scale forecast
- calendar effects
- optional LightGBM/category/Croston
- median/weighted aggregation

It does not use the Phase 8E V2 model or the availability feature matrix.

If someone opens the app and expects the 24.2/24.6 percent V2 model, they are
not using it.

### 3. Current score persistence is weak

Recent Phase 8E results are report artifacts, not persisted DB score rows.
Fast in-memory scoring is fine while experimenting, but the final candidate
needs persisted runs, predictions, actuals, and score rows.

### 4. The target is probably too broad for the KPI

The headline population is "top revenue and recurring enough", but future
target outcomes still include many 0 to 5 unit SKU-windows.

Hit +/-20 over low counts is extremely unforgiving. This alone can make the
headline hit-rate look worse than the practical business value of the model.

### 5. Objective mismatch

The models optimize regression losses, not hit +/-20. The postprocess tunes
hit-rate after the fact using a global factor and zero floor. That is not enough
to solve a row-level tolerance KPI with mixed low/high-volume SKUs.

### 6. Global model across incompatible routes

Campaign, regular, sparse, lifecycle, and constrained demand are different
forecasting problems. The current ML path mostly asks one model to learn all of
them at once.

Route labels exist, but they are not yet the primary modeling architecture.

### 7. Availability is a feature, not a gating/censoring system

Store and supplier stock features are useful, but the model still treats actual
sales as actual demand. If a SKU sold 0 because it was unavailable, the model
learns 0 demand unless the stock signal is strong enough for the regressor to
infer censorship.

This is the central reason Phase 8G should be availability-gated or
route-specific.

### 8. Supplier stock mapping is safe but limited

Using exact-unique product-name mapping avoids dangerous joins, but it also
means supplier availability is only as good as product-name consistency.

The engine lacks a proper SKU-master bridge for supplier stock.

### 9. Black Friday/campaign handling is heuristic

The engine has BF timing, BF transaction shares, discounts, and target-window
overlap features. It does not have:

- actual campaign calendar,
- SKU campaign membership,
- campaign start/end dates,
- planned promotions,
- discount depth by SKU before target,
- campaign stock allocation,
- demand pull-forward rules.

The 2024-11-25 failure is exactly where these missing signals matter.

### 10. Categorical handling is basic

Ordinal encoding of category/family/status fields is simple and works with tree
models, but it is not rich. Product families with meaningful text patterns,
dimensions, brands, collections, and lifecycle cues are not represented well.

### 11. Training has few independent time windows

By 2024-08-26 the model has 4 prior target windows. By 2024-12-30 it has 8.
That is not much temporal evidence for calendar shocks.

The row count is large, but the independent number of demand regimes over time
is small.

### 12. Current snapshot stock is correctly excluded, but not yet useful for
backtesting

Phase 8F rotation snapshots are marked `current_snapshot`. They should not be
used as historical availability evidence. They are useful for current/live
forecasting, diagnostics, and future route logic, but not for honest 2024/2025
backtests unless historical as-of dates are recovered.

## What Is Probably Not The Main Problem

- Not just dirty SKU artifacts. Phase 7E artifact-token cleanup did not improve
  hit +/-20.
- Not just needing one more generic feature column. Phase 8E added supplier and
  combined availability features and only moved accuracy slightly.
- Not just choosing the right candidate among current model variants. Oracle
  selection among tested candidates tops out at 47 percent hit +/-20.
- Not obvious leakage in the current sklearn path. Features use prior windows
  and prior completed stock months; actuals are present in the matrix for
  scoring but not in the model feature whitelist.

## What This Means

The current forecast engine is a valid research scaffold, but it is not yet a
business-grade forecast engine. The weak point is less "bad math" and more
"wrong decomposition for the business problem."

The next architecture should stop treating every headline SKU-window as the
same type of target. At minimum, the engine needs separate paths for:

- available regular demand,
- BF/campaign demand,
- intermittent/sparse demand,
- lifecycle/decline/reactivation,
- observed stock-constrained demand,
- stock-unobserved low-confidence demand.

Only after that should we judge whether the model class itself is too basic.

## Pre-Decision Notes For Next Phase

The evidence supports the existing Phase 8G direction: availability-gated and
route-specific modeling, not more blind global feature additions.

Before implementing Phase 8G, the cleanest next technical decision is to choose
the first route to optimize:

- `proxy_available_regular` / `available_regular`: best place to prove a
  cleaner regular-demand model can exceed the current 29 to 37 percent route
  hit-rate.
- `bf_campaign_sensitive`: biggest absolute error pool, but likely blocked by
  missing campaign calendar and SKU membership.
- `sparse_intermittent`: needs a different sale-probability then quantity
  structure, not a plain direct regressor.
- `stock_constrained`: conceptually important, but currently too few observed
  historical rows to be the first benchmark.

My read from the audit: start with available/proxy-available regular demand as
the first route-specific benchmark, while keeping BF/campaign as a separate
diagnostic bucket until campaign membership data exists.
