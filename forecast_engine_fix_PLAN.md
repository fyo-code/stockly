# SKU-Accuracy Rebuild Plan

**Summary**

Rebuild forecasting as a new `v2` track, not as another tweak to the current ensemble. Optimize for `4-week chain-total SKU accuracy` first, because that is the cleanest way to add signal and make the 80% target meaningful. Keep the current engine frozen as a benchmark only.

The headline target will **not** apply to all A-tier SKUs. It will apply to a new `core movers` segment, because A-tier is revenue-ranked and contains many sparse or seasonal SKUs that are commercially important but not predictable at ±20% every month. The current repo evidence already shows the existing median-ensemble architecture has likely reached its SKU-accuracy ceiling.

**Key Decisions**

1. `Forecast unit`: one forecast per `SKU across all stores combined` for the first serious rebuild.
Why: chain aggregation multiplies signal and removes the worst one-store sparsity problem. Store-level forecasting becomes phase 2 after chain-total accuracy is proven.

2. `Primary target`: `4-week total units`, not 8-week.
Why: it matches buyer action windows and is materially easier to optimize precisely.

3. `Headline population`: `core movers`, defined as:
`median actual chain sales >= 20 units / 4 weeks` across the rolling backtest windows, and `non-zero sales in at least 5 of the last 6 scored windows`.
Why: this is the population where 80% hit rate is hard but realistic.

4. `Secondary populations`:
`active movers`: median actual `8-19 units / 4 weeks`, non-zero in at least `4/6` windows.
`long-tail active`: median actual `1-7 units / 4 weeks`.
`dormant`: zero in recent `8 weeks` or non-zero in fewer than `3/6` windows.
Why: each regime has different signal density and needs a different modeling rule.

5. `Build path`: parallel `v2` track.
Why: highest accuracy comes from a cleaner experimental system, but the current ingestion/backtesting scaffolding is still valuable. Hard reset would waste good infrastructure; in-place refactor would blur benchmarks.

**Implementation Changes**

1. **Reset measurement before model work**
Add a new scorecard in the backtester that reports:
`hit±20`, `hit±30`, `phantom-demand rate`, `underprediction rate`, and `wins vs naive`, all by regime.
Make `core movers hit±20` the gating metric.
Keep `WMAPE` and bias as secondary diagnostics only.
Why: the current optimizer is solving the wrong problem.

2. **Create a chain-total training dataset**
Build a weekly `SKU-chain` training table from all stores combined.
Use:
sales and returns, weekly aggregation, category, calendar features, discount flags, stock/censor flags, and store-breadth features like `number_of_stores_selling`.
Do not use store-specific forecasts in v2 phase 1.
Why: we want a single, denser demand series per SKU before splitting demand back down.

3. **Freeze the current ensemble as benchmark**
Do not tune the current median ensemble anymore except for bug fixes needed to run comparisons.
Benchmark panel for every iteration:
`naive seasonal`, `current Iter 3 frozen`, `current Iter 4 frozen`, `v2 candidate`.
Why: we need clean attribution of gains.

4. **Replace “one model for all SKUs” with regime-based forecasting**
Use separate rules by regime:
`core movers`: direct 4-week count model, primary candidate `LightGBM Tweedie` or Poisson-style count objective, trained on chain-total rows.
`active movers`: direct 4-week model plus naive seasonal baseline; choose the better prediction source per regime by rolling-window score.
`long-tail active`: binary `any-sale-in-next-4-weeks` classifier plus conditional quantity model if sale occurs.
`dormant`: zero forecast unless reactivation features strongly fire.
Why: sparse furniture demand is not one forecasting problem.

5. **Make the primary model direct, not recursive**
Train v2 to predict the `next 4-week total directly`, rather than forecasting week-by-week and summing.
Use weekly lags and rolling history as features, but make the target the 4-week block.
Why: your business KPI is 4-week total accuracy, and recursive weekly forecasting compounds noise.

6. **Bring LightGBM back only where it belongs**
Re-enable LightGBM only for `core movers` and `active movers`.
Use features from:
own lags, rolling means, seasonal calendar flags, category totals, discount flags, stock/censor flags, store breadth, and price if available.
Do not send long-tail sparse SKUs through the same regressor.
Why: LightGBM was archived for hurting full-population WMAPE, not for failing on dense high-signal SKUs.

7. **Turn stock data into censoring logic, not just reporting**
Use stock and availability to flag weeks where zero sales likely mean constrained demand.
Impute or mask those weeks consistently before training.
Why: otherwise the model learns false zero demand.

8. **Demote or remove broken v1 heuristics from v2**
In v2 phase 1:
disable `uniform bias correction`,
disable `seasonal dampening`,
do not use `ETS` in the candidate path,
do not use the full median ensemble as the main forecast.
Why: repo evidence shows these are improving WMAPE while hurting SKU hit rate, or failing outright on live windows.

9. **Delay app integration**
No frontend or public API change until v2 beats the frozen benchmark on `two consecutive blind 2-month holdouts`.
Add only internal artifacts:
`regime_labels`, `benchmark_summary`, `candidate_predictions`, and `segment_scorecards`.
Why: keep the app stable while the forecasting core is being replaced.

**Iteration Strategy**

Keep your current blind `train -> predict next 2 months -> compare -> iterate` loop. It is the right outer loop. Change the inner loop around it.

Use a two-layer iteration process:

1. `Inner loop`: rolling backtest on historical windows for fast rejection of bad ideas.
Rule: use these windows only for model selection, threshold selection, and feature testing.

2. `Outer loop`: one untouched blind 2-month holdout for the official iteration result.
Rule: never choose the model on the same window you use to claim improvement.

Use this exact cadence per iteration:
1. Freeze the training cutoff.
2. Train all candidate models.
3. Select the v2 candidate using inner rolling windows only.
4. Run one blind next-2-month prediction.
5. Score by regime.
6. Log what changed and only then move the cutoff forward.

Use only one change family per iteration:
examples are `new target`, `new regime routing`, `new features`, `new censoring`, `new data source`.
Why: otherwise you will not know what caused the gain.

**Expected Progress**

1. `Iteration 5A`: measurement reset + chain-total dataset + frozen benchmarks.
Expected gain: little or none in headline accuracy.
Output: trustworthy scorecards and a clean experimental lane.

2. `Iteration 5B`: first direct 4-week chain-total model for core movers.
Expected result: `45-60% hit±20` on core movers if multi-store data is added; lower if still one-store only.
Why: this is the first time the model is actually aligned to the objective.

3. `Iteration 6`: regime routing + any-sale classifier for long-tail + stock censoring.
Expected result: `55-68%` core-mover hit±20, lower phantom-demand rate, better calibration.

4. `Iteration 7`: promo feature cleanup + store-breadth features + threshold tuning by regime.
Expected result: `65-75%` core-mover hit±20.

5. `Iteration 8+`: optional lifecycle/price/discontinuation features, plus better chain promo scope and later store allocation.
Expected result: `72-80%` on core movers if the data is genuinely complete and stable.

**Answer To The 80% Question**

Yes, `80% hit±20` is plausible for `chain-total core movers`.
No, it is not realistic for `all A-tier SKUs`.
No, it is not realistic for `one-store sparse furniture demand` as the main headline target.

A realistic target ladder is:
`core movers`: 60% first, then 70%, then push toward 80%.
`active movers`: 50-65%.
`full A-tier`: 35-45% overall hit±20%, even with a much better system.

**Test Plan**

Every iteration must report:
`core movers hit±20`
`active movers hit±20`
`phantom-demand rate`
`underprediction rate on core movers`
`wins vs naive`
`WMAPE` and bias as secondary

Required benchmark scenarios:
`naive seasonal`
`frozen Iter 3`
`frozen Iter 4`
`v2 candidate`

Required failure scenarios:
promo-heavy windows,
stock-constrained windows,
summer transition windows,
winter dormant -> spring reactivation windows,
high-price low-frequency A-tier SKUs,
multi-store versus single-store comparisons.

**Assumptions**

- Sales, stock, and discount data are available across stores.
- Phase 1 of v2 uses `chain-total` forecasting only; store-level allocation is intentionally deferred.
- If price history, discontinuation flags, assortment availability, or inbound PO/receipt data exist, they should be added in Iteration 7+, not before the first v2 benchmark win.
- The current app should remain on the legacy logic until v2 beats the benchmark on two consecutive blind holdouts.
