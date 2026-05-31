# Forecast V2 Current Handoff

Last updated: 2026-05-28

## Plain-English State

We are building the retail forecast engine for Mobexpert-style multi-store sales. The current v2 track forecasts chain-level SKU demand for the next 4 weeks, then scores rolling historical target windows against actual demand.

The old median ensemble is no longer the main path. Forecast v2 is a separate rebuild under `backend/forecast_engine_v2/`, focused on forecastable revenue movers, direct 4-week chain forecasts, regime/routing logic, and leak-safe data features.

The headline target is still ambitious: 80%+ hit rate within +/-20% on forecastable revenue movers. Current results are far below that, so every new phase should improve measurement quality or attack a specific failure mode. Do not add generic global features blindly.

## Current Official Accuracy

Latest full-headline availability rerun: Phase 8E availability-aware sklearn direct model.

Best raw hit-rate model:

- Model: `sk_extra_trees`
- Hit +/-20: 24.6%
- Hit +/-30: 35.5%
- WMAPE: 58.3%
- Phantom rate: 44.2%

Safer operational control:

- Model: `sk_blend_post_bf_safe`
- Hit +/-20: 24.2%
- Hit +/-30: 35.3%
- WMAPE: 55.6%
- Phantom rate: 44.4%

Interpretation: supplier availability data helped phantom demand and added real feature coverage, but it did not create a meaningful hit-rate jump. The global model is still not using availability strongly enough.

Latest high-revenue official validation: Phase 8G-P final promotion pack and official guarded-policy export.

Current Top 1000 high-revenue promoted policy:

- Model: `8go_pre_bf_bfc_lift_180`
- Policy flag: `--high-revenue-policy pre_bf_bfc_lift_180 --revenue-rank-limit 1000`
- Hit +/-20: 27.4%
- Hit +/-30: 39.4%
- WMAPE: 47.4%
- Phantom rate: 41.0%
- Bias: -10.5%

Previous Top 1000 high-revenue champion:

- Model: `8gf_regular_plus_post_bf_safe`
- Hit +/-20: 25.3%
- Hit +/-30: 36.5%
- WMAPE: 51.0%
- Phantom rate: 41.0%
- Bias: -21.3%

Same-run safer control for Top 1000:

- Model: `sk_blend_post_bf_safe`
- Hit +/-20: 23.4%
- Hit +/-30: 34.8%
- WMAPE: 55.7%
- Phantom rate: 43.5%
- Bias: -17.0%

Interpretation: the guarded campaign policy is now the promoted Top 1000 high-revenue policy. It improves over the previous champion by +2.1pp hit +/-20 and -3.6pp WMAPE, with phantom unchanged and bias materially less underpredicted. It is still a high-revenue scoped policy, not a full-catalog/global promotion.

Latest calibrated-policy validation: Phase 8G-K official calibrated policy validation/export.

Calibrated candidate:

- Model: `8gj_bfc_nonpost_lift_150`
- Hit +/-20: 27.2%
- Hit +/-30: 39.2%
- WMAPE: 49.3%
- Phantom rate: 41.0%
- Bias: -9.3%

Decision:

- `KEEP_8G_I_CHAMPION`

Reason: the calibrated candidate improves aggregate accuracy but fails window stability. The worst non-stress regression is `2024-12-30`, where WMAPE worsens from 58.3% to 73.7% versus the 8G-I champion (+15.4pp), hit +/-20 falls from 21.3% to 19.7%, and bias swings from -9.0% to +25.9%.

Interpretation: the 1.50 BF/campaign lift is directionally useful but too blunt to promote. The official high-revenue policy remains `8gf_regular_plus_post_bf_safe`.

Latest business-semantics audit: Phase 8G-L.

Decision:

- `KEEP_CURRENT_CHAMPION_AND_RELABEL_STOCK_SEMANTICS`

Reason: Mobexpert stock should not be treated as hard sellability. Active/orderable/listed SKU status is the missing sellability signal. Stock quantities are still useful as fulfillment/friction/context, but route labels like `available_regular` and `stock_constrained` should stop implying whether the product can be sold.

Stock-soft simulation result:

- Current champion `8gf_regular_plus_post_bf_safe`: hit +/-20 25.3%, WMAPE 51.0%
- Demand-regular stock-soft candidate: hit +/-20 25.7%, WMAPE 50.9%

Interpretation: stock-soft semantics are directionally better, but the gain is too small to replace the champion. Before further promotion work, clean invalid discounts and reframe stock-derived labels as fulfillment/stock-position context.

## Completed Latest Phases

### Phase 8G-A - High-Revenue Benchmark

High-revenue slicing was added in `backend/forecast_engine_v2/phase8g_high_revenue_benchmark.py`.

Report:

- `active_docs/ITER5P_V2_PHASE8G_HIGH_REVENUE_BENCHMARK.md`

Key numbers:

- Phase 8E safer control reproduced: hit +/-20 24.2%, WMAPE 55.6%, phantom 44.4%
- Top 1000 safer control: hit +/-20 24.8%
- Clean Top 1000 regular/proxy-regular slice: best current model `sk_extra_trees` hit +/-20 32.3%, WMAPE 45.5%, bias 2.1%

Interpretation: the first real win is slice-specific, not headline-wide. The current data can perform much better on cleaner high-revenue regular rows, but the model still needs route-specific handling.

### Phase 8G-B - High-Revenue Stock Coverage Audit

Stock coverage audit was added in `backend/forecast_engine_v2/phase8g_stock_coverage_audit.py`.

Report:

- `active_docs/ITER5Q_V2_PHASE8G_STOCK_COVERAGE_AUDIT.md`

Key numbers for Top 1000 rows:

- Store previous-month observed coverage: 0.4%
- Supplier previous-month observed coverage: 70.6%
- Rows with recent store sales but no previous-month store-stock row: 5,324 / 5,346

Interpretation: monthly store stock is too sparse to drive the next modeling phase. Supplier stock should be the primary historical availability signal.

### Phase 8G-C - Campaign Field Audit And Feature Upgrade

Campaign history features were added in `backend/forecast_engine_v2/feature_matrix.py`.

Audit runner:

- `backend/forecast_engine_v2/phase8g_campaign_field_audit.py`

Report:

- `active_docs/ITER5R_V2_PHASE8G_CAMPAIGN_FIELD_AUDIT.md`

Important safety rules:

- Campaign history features use only raw sales where `sale_date < target_start`
- Product/program labels are excluded from campaign exposure features and kept as a separate signal
- Non-BF campaign features exclude rows flagged as BF campaigns, not just rows inside BF timing windows
- Target-window campaign buckets remain diagnostic only

Top 1000 campaign exposure:

- Any campaign history in prior 13 weeks: 69.1%
- Non-BF campaign history in prior 13 weeks: 30.8%
- BF transaction history in prior 13 weeks: 35.3%
- Clean Top 1000 regular/proxy-regular rows with campaign history: 70.7%

Interpretation: even the “regular” win is not campaign-free. Next modeling must handle supplier availability and campaign/BF sensitivity explicitly.

### Phase 8G-D - Route-Specific High-Revenue Model

Route-specific Top 1000 modeling was added in:

- `backend/forecast_engine_v2/phase8g_route_specific_model.py`

DB-aware feature caching was added in:

- `backend/forecast_engine_v2/feature_matrix_cache.py`

Report:

- `active_docs/ITER5S_V2_PHASE8G_ROUTE_SPECIFIC_MODEL.md`

Key Top 1000 results:

- Control `sk_blend_post_bf_safe`: hit +/-20 23.4%, WMAPE 55.7%, phantom 43.5%
- Raw hit winner `sk_hgb_squared`: hit +/-20 25.3%, but WMAPE 62.6% and phantom 57.8%, so not promotable
- Best route candidate `8gd_regular_global_extra`: hit +/-20 24.4%, WMAPE 55.6%, phantom 43.6%

Interpretation: 8G-D produced a small diagnostic route-specific improvement below the promotion gate. Regular rows are now much clearer: available_regular hit +/-20 is 35.1%, proxy_available_regular is 28.8%. The blocking problem is still BF/campaign-sensitive demand, especially the 2024-11-25 window.

### Phase 8G-E - BF/Campaign-Sensitive Model

BF/campaign-sensitive candidate runner was added in:

- `backend/forecast_engine_v2/phase8g_campaign_sensitive_model.py`

Report:

- `active_docs/ITER5T_V2_PHASE8G_CAMPAIGN_SENSITIVE_MODEL.md`

Best candidate:

- `8ge_post_bf_hard_safe`

Top 1000 result:

- Control: hit +/-20 23.4%, WMAPE 55.7%, phantom 43.5%
- Candidate: hit +/-20 24.3%, WMAPE 51.1%, phantom 40.9%
- Tradeoff: bias worsened from -17.0% to -23.2%

Critical stress result:

- `2024-11-25` improved from hit +/-20 6.7% to 17.8%
- WMAPE improved from 139.8% to 70.9%
- Bias improved from +133.0% to +38.0%

Interpretation: the post-BF hard-safe path attacks the exact failure mode, but it is still not enough by itself. BF/campaign-sensitive route improved from 16.6% to 18.6% hit +/-20 and remains far below the regular route.

### Phase 8G-F - Combined Route Model

Combined route candidate runner was added in:

- `backend/forecast_engine_v2/phase8g_combined_route_model.py`

Report:

- `active_docs/ITER5U_V2_PHASE8G_COMBINED_ROUTE_MODEL.md`

Best candidate:

- `8gf_regular_plus_post_bf_safe`

Top 1000 result:

- Control: hit +/-20 23.4%, hit +/-30 34.8%, WMAPE 55.7%, phantom 43.5%
- Candidate: hit +/-20 25.3%, hit +/-30 36.5%, WMAPE 51.0%, phantom 41.0%
- Delta: +2.0pp hit +/-20, -4.7pp WMAPE, -2.5pp phantom

Component comparison:

- `8gd_regular_global_extra`: hit +/-20 24.4%, WMAPE 55.6%, phantom 43.6%
- `8ge_post_bf_hard_safe`: hit +/-20 24.3%, WMAPE 51.1%, phantom 40.9%
- `8gf_regular_plus_post_bf_safe`: hit +/-20 25.3%, WMAPE 51.0%, phantom 41.0%

Critical slice results:

- Available/proxy regular: hit +/-20 improved from 30.2% to 33.1%
- BF/campaign-sensitive route: hit +/-20 improved from 16.6% to 18.6%
- Any campaign/BF history: hit +/-20 improved from 22.4% to 24.7%
- `2024-11-25` stress window stayed protected: hit +/-20 17.8%, WMAPE 70.9%

Interpretation: this is the first stackable high-revenue win. The combined candidate beats the safer blend and both individual route components while improving WMAPE and phantom. It is a Top 1000 high-revenue champion candidate, not yet wired into the main v2 scoring/export path.

### Phase 8G-G - Promotion / Robustness Pack

Promotion runner was added in:

- `backend/forecast_engine_v2/phase8g_promotion_pack.py`

Report:

- `active_docs/ITER5V_V2_PHASE8G_PROMOTION_PACK.md`

Decision:

- `PROMOTE_HIGH_REVENUE_CHAMPION_WITH_MONITORS`

Promotion target:

- `8gf_regular_plus_post_bf_safe`

Top 1000 decision numbers:

- Control: hit +/-20 23.4%, hit +/-30 34.8%, WMAPE 55.7%, phantom 43.5%, bias -17.0%
- Champion: hit +/-20 25.3%, hit +/-30 36.5%, WMAPE 51.0%, phantom 41.0%, bias -21.3%

Robustness summary:

- Top 100: hit +/-20 +1.1pp, WMAPE -5.7pp
- Top 250: hit +/-20 +3.2pp, WMAPE -6.9pp
- Top 500: hit +/-20 +2.3pp, WMAPE -5.4pp
- Top 1000: hit +/-20 +2.0pp, WMAPE -4.7pp
- Zero-actual rows: phantom improved from 43.5% to 41.0%
- 2024-11-25 stress window: hit +/-20 improved from 6.7% to 17.8%, WMAPE from 139.8% to 70.9%

Caveats:

- The champion is more underpredictive than the safer control: bias -21.3% vs -17.0%
- Available/proxy regular phantom rose by +1.3pp even though hit +/-20 improved from 30.2% to 33.1%
- Largest non-stress window WMAPE regression is +1.8pp
- This is a high-revenue Top 1000 promotion, not a full-headline or low-volume SKU promotion

Interpretation: the candidate passed blocking promotion gates for the high-revenue path, with explicit monitoring caveats accepted. The next step is implementation wiring, not more candidate-searching.

### Phase 8G-H - Main V2 Policy Wiring

High-revenue champion policy wiring was added in:

- `backend/forecast_engine_v2/sklearn_direct_model.py`

Report:

- `active_docs/ITER5W_V2_PHASE8G_HIGH_REVENUE_POLICY_WIRING.md`

New CLI options:

- `--revenue-rank-limit`
- `--high-revenue-policy {none,champion}`

Behavior:

- Default remains `--high-revenue-policy none`; existing direct sklearn/control behavior is unchanged unless explicitly enabled.
- `--high-revenue-policy champion --revenue-rank-limit 1000` emits `8gf_regular_plus_post_bf_safe`.
- Champion mode fails fast unless `--revenue-rank-limit` is 1000 or lower.
- The 8G-H report shows delta vs same-run `sk_blend_post_bf_safe` control, not the old Phase 8E baseline.
- Champion prediction source: `v2_high_revenue_policy`.
- Champion model version: `high_revenue_policy_v1_2026_05_24`.

Official Top 1000 result:

- `8gf_regular_plus_post_bf_safe`: hit +/-20 25.3%, hit +/-30 36.5%, WMAPE 51.0%, phantom 41.0%, bias -21.3%
- This matches the 8G-G promotion report.

Lowlight:

- The official uncached runner is slow because it rebuilds the full feature matrix. Use cached phase runners for iteration and the official path for validation/export.

Interpretation: the champion is now wired into the main v2 sklearn scoring path behind an explicit high-revenue policy flag. Next step is official validation/export reporting, not new modeling yet.

### Phase 8G-I - Official Policy Validation / Export

Official validation runner was added in:

- `backend/forecast_engine_v2/phase8g_official_policy_validation.py`

Report:

- `active_docs/ITER5X_V2_PHASE8G_OFFICIAL_POLICY_VALIDATION.md`

Score-row export:

- `active_docs/ITER5X_V2_PHASE8G_OFFICIAL_POLICY_SCORE_ROWS.csv`

Decision:

- `PROMOTE_WITH_MONITORS`

Policy safety checks:

- Default `--high-revenue-policy none` does not emit `8gf_regular_plus_post_bf_safe`
- Champion mode emits the champion
- Champion mode fails fast without `--revenue-rank-limit 1000` or lower
- Same-run control hit +/-20 is unchanged by the policy flag
- The 8G-I runner itself is now fixed to exactly Top 1000 scope so the official report cannot mislabel stricter rank-limit runs

Official Top 1000 result:

- Control: hit +/-20 23.4%, hit +/-30 34.8%, WMAPE 55.7%, phantom 43.5%, bias -17.0%
- Champion: hit +/-20 25.3%, hit +/-30 36.5%, WMAPE 51.0%, phantom 41.0%, bias -21.3%

Critical slices:

- Top 100: +1.1pp hit +/-20, WMAPE -5.7pp
- Top 500: +2.3pp hit +/-20, WMAPE -5.4pp
- Available/proxy regular: hit +/-20 30.2% to 33.1%, but phantom 67.1% to 68.4%
- BF/campaign-sensitive route: hit +/-20 16.6% to 18.6%, WMAPE 65.4% to 57.4%
- 2024-11-25 stress: hit +/-20 6.7% to 17.8%, WMAPE 139.8% to 70.9%

Interpretation: official export validation confirms the 8G-H wiring is real and scoped correctly. The next work should attack the monitoring caveats: underprediction bias, regular-slice phantom, and the small 2025-03-24 WMAPE regression.

Review note: the official report now separates blocking gates from required monitors and calls the run confirmatory rolling backtest/export validation, not independent future holdout validation.

### Phase 8G-J - Monitor Calibration Research

Monitor calibration runner was added in:

- `backend/forecast_engine_v2/phase8g_monitor_calibration.py`

Report:

- `active_docs/ITER5Y_V2_PHASE8G_MONITOR_CALIBRATION.md`

Decision:

- `RESEARCH_CANDIDATE_FOR_OFFICIAL_VALIDATION`

Best research candidate:

- `8gj_bfc_nonpost_lift_150`

Candidate logic:

- Start from the official 8G-I champion predictions.
- Multiply only `bf_campaign_sensitive` rows outside post-BF calendar context when the champion prediction is at least 3 units.
- The selected lift is 1.50.

Research result versus the official 8G-I champion:

- Hit +/-20: 25.3% to 27.2%
- Hit +/-30: 36.5% to 39.2%
- WMAPE: 51.0% to 49.3%
- Bias: -21.3% to -9.3%
- Phantom: unchanged at 41.0%

Monitor result:

- BF/campaign-sensitive route improves: hit +/-20 18.6% to 23.4%, WMAPE 57.4% to 53.8%, bias -31.2% to -5.5%
- Available/proxy regular is unchanged: hit +/-20 33.1%, phantom 68.4%
- Available regular phantom is unchanged at 87.2%
- 2025-03-24 WMAPE regression is unchanged
- 2024-11-25 stress window is unchanged and still protected

Review caveat:

- This is validation-window tuning on the known Phase 8G backtest windows, not independent future holdout evidence and not official wiring. It must be wired into `sklearn_direct_model.py` and rerun through the official 8G-I validation/export path before replacing the current champion.

### Phase 8G-K - Official Calibrated Policy Validation

Official calibrated policy support was added in:

- `backend/forecast_engine_v2/sklearn_direct_model.py`

Official validation/export runner:

- `backend/forecast_engine_v2/phase8g_official_calibrated_policy.py`

Report:

- `active_docs/ITER5Z_V2_PHASE8G_OFFICIAL_CALIBRATED_POLICY.md`

Score-row export:

- `active_docs/ITER5Z_V2_PHASE8G_OFFICIAL_CALIBRATED_SCORE_ROWS.csv`

New optional policy:

- `--high-revenue-policy bfc_lift_150 --revenue-rank-limit 1000`

Behavior:

- Default remains `--high-revenue-policy none`.
- The official 8G-I champion remains available under `--high-revenue-policy champion`.
- The calibrated candidate emits only under `bfc_lift_150`.
- Any non-`none` high-revenue policy fails fast unless `--revenue-rank-limit` is 1000 or lower.

Official aggregate result:

- 8G-I champion: hit +/-20 25.3%, hit +/-30 36.5%, WMAPE 51.0%, phantom 41.0%, bias -21.3%
- 8G-K calibrated: hit +/-20 27.2%, hit +/-30 39.2%, WMAPE 49.3%, phantom 41.0%, bias -9.3%

Decision:

- `KEEP_8G_I_CHAMPION`

Blocking gate:

- Largest non-stress WMAPE regression vs 8G-I must be <= +2.0pp.
- Observed worst window is `2024-12-30`: +15.4pp WMAPE regression.

Interpretation: do not promote `8gj_bfc_nonpost_lift_150` as-is. A smaller or more guarded BF/campaign lift may still be worth one final narrow test, but the current exact candidate overcorrects some non-stress campaign periods.

### Phase 8G-L - Business Semantics Audit

Business-semantics audit runner:

- `backend/forecast_engine_v2/phase8g_business_semantics_audit.py`

Report:

- `active_docs/ITER5AA_V2_PHASE8G_BUSINESS_SEMANTICS_AUDIT.md`

Decision:

- `KEEP_CURRENT_CHAMPION_AND_RELABEL_STOCK_SEMANTICS`

Raw data findings:

- Returns are ingested: 80,495 return rows and 310,542 returned units, about 7.7% of gross positive units.
- Return value signs are mostly aligned: only 1 negative-quantity row had positive `VALOARE FACTURATA`.
- Discounts are ingested and used, but 61 raw `Reducere %` rows are infinite and reached weekly aggregates. Another 172 finite discount rows are >1 and need scale validation/normalization.
- Campaign/BF fields are present and used as historical signals: 1,004,879 observed campaign rows, 124,133 observed BF rows, and 110,432 inferred BF rows.
- `VECHIME IN COLECTIE` exists in stock snapshot data, but not as complete historical-as-of backtest data.

Policy simulation:

- Removing regular-route stock-gate replacement drops the champion from 25.3% to 24.3% hit +/-20.
- Demand-regular stock-soft candidate improves only slightly to 25.7% hit +/-20 and 50.9% WMAPE.
- This was route-blending sensitivity over exported predictions, not a retrained stock-feature ablation.
- Treating stock-constrained regular-demand rows as regular improves slightly to 25.5% hit +/-20 and 50.9% WMAPE.

Interpretation:

- The current champion remains the official Top 1000 policy.
- Stock-derived features should be reworded and reframed as fulfillment/stock-position context, not sellability.
- The missing high-value data is active/orderable/listed SKU status by date.

### Phase 8D - Supplier Monthly Stock

Supplier stock files for 2022-2025 were ingested into normalized v2 tables:

- `stock_monthly_supplier_v2`
- `supplier_stock_sku_map_v2`

Important numbers:

- 1,821,659 unique supplier/month/product records
- 76,858 exact-unique mapped SKUs
- 1,819 ambiguous supplier product keys
- 46,315 unmapped supplier product keys

Only `exact_unique` mappings are safe for official historical model features.

### Phase 8E - Availability Features And Model Rerun

Leak-safe supplier and combined availability features were added to the v2 feature matrix.

Feature matrix now has:

- 30,891 rows
- 111 numeric features
- 10 categorical features

Availability coverage:

- Store stock history remains weak: about 2.3-2.8% of headline rows
- Supplier stock history is strong: about 77.4-80.7% of headline rows
- Supplier features use only stock months before each target window

Code changed in:

- `backend/forecast_engine_v2/feature_matrix.py`
- `backend/forecast_engine_v2/route_labels.py`

Reports:

- `active_docs/ITER5N_V2_PHASE8E_AVAILABILITY_FEATURE_MATRIX.md`
- `active_docs/ITER5N_V2_PHASE8E_AVAILABILITY_MODEL.md`

### Phase 8F - Rotation Snapshot

Rotation snapshot files were ingested for current/future diagnostics only.

Table created:

- `stock_rotation_snapshot_v2`

Imported:

- 211,056 current-snapshot rows
- 61,121 unique SKUs
- 4 stores: Constanta, Militari, Pipera, Sibiu
- Snapshot date: 2026-05-21

Critical safety rule: these rows are marked `current_snapshot`. They must not be used in official historical backtests because the files do not contain historical as-of dates.

Report:

- `active_docs/ITER5O_V2_PHASE8F_ROTATION_SNAPSHOT.md`

## Important Prior Findings

The current model family has a low ceiling. Phase 7D tested an oracle that could choose the best already-tested candidate per SKU-window using actual outcomes. Even that only reached:

- Hit +/-20: 47.0%
- Hit +/-30: 58.6%
- WMAPE: 35.9%
- Phantom rate: 34.7%

This means routing among current candidates cannot reach the 80% target. The next improvements need better objective design, stronger route-specific training, better availability/campaign handling, or target cleanup.

Main error concentration from prior decomposition:

- BF/campaign-sensitive rows drive the largest share of error.
- Proxy-available regular rows are the second major error bucket.
- Sparse/intermittent rows matter, but are not the whole problem.
- Underprediction is a major failure mode.

Artifact cleanup alone did not fix accuracy. Removing obvious pallet/service/logistics-like SKUs left hit +/-20 essentially unchanged.

## Current Next Phase

No further current-data modeling phase is recommended right now.

Do not jump back to blind global feature additions. 8G-L corrected the stock business semantics, 8G-M cleaned discount hygiene plus route wording without changing the official champion score, 8G-N showed stock-soft retraining is not strong enough to promote, 8G-O found a guarded pre-BF campaign lift candidate, and 8G-P wired/validated that candidate as the promoted Top 1000 high-revenue policy.

Completed Phase 8G-M:

1. Cleaned invalid discount values in future ingestion and current feature generation.
2. Verified the cleaned Top 1000 matrix has 0 non-finite numeric cells and 0 discount feature cells above 1.
3. Reframed stock-derived route semantics from availability/sellability to fulfillment/stock-position context.
4. Re-ran the official Top 1000 champion path and reproduced `8gf_regular_plus_post_bf_safe`: hit +/-20 25.3%, hit +/-30 36.5%, WMAPE 51.0%, phantom 41.0%, bias -21.3%.
5. Decision: `HYGIENE_PASS_KEEP_CHAMPION_BASELINE`.

Completed Phase 8G-N:

1. Added `backend/forecast_engine_v2/phase8gn_stock_soft_rebuild.py`.
2. Tested `8gn_stock_soft_full_features`, `8gn_no_stock_features_current_route`, and `8gn_no_stock_features_stock_soft`.
3. Best candidate was `8gn_stock_soft_full_features`: hit +/-20 25.7%, WMAPE 50.9%, phantom 41.2% versus champion hit +/-20 25.3%, WMAPE 51.0%, phantom 41.0%.
4. Decision: `KEEP_CURRENT_CHAMPION`; the +0.4pp hit gain missed the +0.5pp promotion gate.
5. Stock-feature ablation was worse, so current-data stock iteration should stop until active/orderable/listed SKU history arrives.

Completed Phase 8G-O:

1. Added `backend/forecast_engine_v2/phase8go_guarded_campaign_calibration.py`.
2. Best candidate: `8go_pre_bf_bfc_lift_180`.
3. Candidate logic: lift only BF/campaign-sensitive rows in the pre-BF calendar window when champion prediction is at least 3 units; 480 rows touched.
4. Aggregate result versus champion: hit +/-20 25.3% to 27.4%, WMAPE 51.0% to 47.4%, bias -21.3% to -10.5%, phantom unchanged at 41.0%.
5. Decision: `PROMOTE_GUARDED_CAMPAIGN_CANDIDATE` into final promotion-pack validation.

Completed Phase 8G-P:

1. Added `backend/forecast_engine_v2/phase8gp_final_promotion_pack.py`.
2. Updated `backend/forecast_engine_v2/sklearn_direct_model.py` with explicit policy `--high-revenue-policy pre_bf_bfc_lift_180`.
3. Official model emitted: `8go_pre_bf_bfc_lift_180`.
4. Official score: hit +/-20 27.4%, hit +/-30 39.4%, WMAPE 47.4%, bias -10.5%, phantom 41.0%.
5. Delta versus previous champion: +2.1pp hit +/-20, -3.6pp WMAPE, +10.7pp bias improvement, phantom unchanged.
6. Final gates passed across Top 100 / 500 / 1000 and the guard windows. `2024-12-30` and `2025-01-27` were unchanged, avoiding the broad 8G-K lift failure.
7. Decision: `PROMOTE_8G_O_GUARDED_POLICY_AND_STOP_CURRENT_DATA_ITERATION`.
8. Next useful work requires new data: active/orderable/listed SKU history, future campaign membership/planned discounts, historical price levels, customer order status history, and fuller 2022-2025 hyperstore sales coverage.

## Historical Safety Rules

- Use only data available before each target window.
- Monthly store/supplier stock features must use the previous completed stock month.
- Use supplier stock only through `exact_unique` SKU mappings unless an explicit ambiguity-resolution phase has been completed.
- Do not use `current_snapshot` rotation rows in historical scorecards.
- Keep WMAPE as a diagnostic, not the primary optimization target.
- Do not claim improvement from a partial window or cherry-picked target period. Use the agreed rolling windows.

## Useful Files

Main status files:

- `PROGRESS.md`
- `FORECAST_V2_REBUILD_PLAN.md`

Latest reports:

- `active_docs/ITER5M_V2_PHASE8D_SUPPLIER_STOCK.md`
- `active_docs/ITER5N_V2_PHASE8E_AVAILABILITY_FEATURE_MATRIX.md`
- `active_docs/ITER5N_V2_PHASE8E_AVAILABILITY_MODEL.md`
- `active_docs/ITER5O_V2_PHASE8F_ROTATION_SNAPSHOT.md`
- `active_docs/ITER5P_V2_PHASE8G_HIGH_REVENUE_BENCHMARK.md`
- `active_docs/ITER5Q_V2_PHASE8G_STOCK_COVERAGE_AUDIT.md`
- `active_docs/ITER5R_V2_PHASE8G_CAMPAIGN_FIELD_AUDIT.md`
- `active_docs/ITER5S_V2_PHASE8G_ROUTE_SPECIFIC_MODEL.md`
- `active_docs/ITER5T_V2_PHASE8G_CAMPAIGN_SENSITIVE_MODEL.md`
- `active_docs/ITER5U_V2_PHASE8G_COMBINED_ROUTE_MODEL.md`
- `active_docs/ITER5V_V2_PHASE8G_PROMOTION_PACK.md`
- `active_docs/ITER5W_V2_PHASE8G_HIGH_REVENUE_POLICY_WIRING.md`
- `active_docs/ITER5X_V2_PHASE8G_OFFICIAL_POLICY_VALIDATION.md`
- `active_docs/ITER5Y_V2_PHASE8G_MONITOR_CALIBRATION.md`
- `active_docs/ITER5Z_V2_PHASE8G_OFFICIAL_CALIBRATED_POLICY.md`
- `active_docs/ITER5AA_V2_PHASE8G_BUSINESS_SEMANTICS_AUDIT.md`
- `active_docs/ITER5AB_V2_PHASE8G_M_HYGIENE_SEMANTICS.md`
- `active_docs/ITER5AC_V2_PHASE8G_N_STOCK_SOFT_REBUILD.md`
- `active_docs/ITER5AD_V2_PHASE8G_O_GUARDED_CAMPAIGN_CALIBRATION.md`
- `active_docs/ITER5AE_V2_PHASE8G_P_FINAL_PROMOTION_PACK.md`

Likely code entry points:

- `backend/forecast_engine_v2/feature_matrix.py`
- `backend/forecast_engine_v2/route_labels.py`
- `backend/forecast_engine_v2/sklearn_direct_model.py`
- `backend/forecast_engine_v2/phase8g_high_revenue_benchmark.py`
- `backend/forecast_engine_v2/phase8g_stock_coverage_audit.py`
- `backend/forecast_engine_v2/phase8g_campaign_field_audit.py`
- `backend/forecast_engine_v2/phase8g_route_specific_model.py`
- `backend/forecast_engine_v2/phase8g_campaign_sensitive_model.py`
- `backend/forecast_engine_v2/phase8g_combined_route_model.py`
- `backend/forecast_engine_v2/phase8g_promotion_pack.py`
- `backend/forecast_engine_v2/phase8g_official_policy_validation.py`
- `backend/forecast_engine_v2/phase8g_monitor_calibration.py`
- `backend/forecast_engine_v2/phase8g_official_calibrated_policy.py`
- `backend/forecast_engine_v2/phase8g_business_semantics_audit.py`
- `backend/forecast_engine_v2/phase8gm_hygiene_semantics.py`
- `backend/forecast_engine_v2/phase8gn_stock_soft_rebuild.py`
- `backend/forecast_engine_v2/phase8go_guarded_campaign_calibration.py`
- `backend/forecast_engine_v2/phase8gp_final_promotion_pack.py`
- `backend/forecast_engine_v2/feature_matrix_cache.py`
- `backend/forecast_engine_v2/phase8d_supplier_stock.py`
- `backend/forecast_engine_v2/phase8f_rotation_snapshot.py`

Runtime note:

- Use `backend/venv/bin/python` for v2 modeling runs.
- The project has `scikit-learn 1.8.0` in the local venv.
- LightGBM is still unstable in the current Python environment because of a NumPy/matplotlib ABI path, so leave it aside unless the environment is fixed.

## One-Sentence Handoff

Forecast v2 now promotes the Top 1000 high-revenue guarded policy `8go_pre_bf_bfc_lift_180` at 27.4% hit +/-20 and 47.4% WMAPE; 8G-P passed the final gates and the correct next step is new data acquisition, not more blind current-data feature/model tweaking.
