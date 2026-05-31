# Iteration 3 — Per-Step Audit Log

_Generated 2026-04-25. Mirrors the level of per-step detail Iter 2 captured, so when Mar–Apr 2025 actuals arrive we can attribute any accuracy change to a specific cause._

---

## 1. Pre-Run State

| Item | Value |
|---|---|
| DB | `backend/data/supply_chain.db` |
| Existing `sales` rows | 96,989 (2024-01-01 → 2024-12-31) |
| Existing `weekly_demand` rows | 83,298 (2023-12-25 → 2024-12-30) |
| Existing `abc_tiers` A-tier count | **6,358 — Iter 2 SKU set, kept as control** |
| Iter 2 predictions on disk | `iter2_predictions_latest.csv` (35 cols, no `naive_seasonal`) |

---

## 2. Data Ingestion (Jan–Feb 2025)

Command: `PYTHONPATH=backend python3 backend/forecast_engine/ingestion_mobexpert.py sales_2025_Jan_Feb_chronological.csv`

| Metric | Result |
|---|---|
| Rows inserted | 14,176 |
| Rows filtered (service rows / null dates / etc.) | 901 |
| New unique SKUs in CSV | 8,642 |
| Conservation check (units) | sales=242,361 = weekly=242,361 ✓ |
| Conservation check (revenue) | sales=138,619,482.32 = weekly=138,619,482.32 ✓ |

Post-ingestion DB:
- `sales`: 111,165 rows, 2024-01-01 → 2025-02-28
- `weekly_demand`: 95,878 rows, 2023-12-25 → 2025-02-24, 62 distinct weeks
- `abc_tiers`: untouched, **6,358 A-tier SKUs preserved** (experimental control)
- 2,058 of 6,358 A-tier SKUs had non-zero Jan–Feb 2025 weekly rows
- Note: 2023 (`sales_2023.csv`) NOT re-ingested — confirmed bonus/incomplete; would have only affected the `naive_seasonal` lookup for SKUs missing 2024 history; not worth the risk of introducing partial-period bias

---

## 3. Engine Run

Command: `PYTHONPATH=backend python3 backend/forecast_engine/backtesting.py predict --iteration iter3`

Total wall time: **~5 min** (Iter 2 was ~3 min — extra time is mostly ETS at 2:07).

### 3.1 Pipeline pre-flight

| Check | Result |
|---|---|
| ENABLED_METHODS check | `Archived methods (excluded from ensemble): lightgbm` ✓ Fix #1 active |
| Recency filter | Applied (10w window). No log line emitted → 0 silent SKUs OR all silent SKUs had no other rows. The `methods_succeeded=0` count (1,750 SKUs, see §3.3) probably includes silent zero-forecast rows. |

### 3.2 Per-method execution

| Method | Coverage (rows produced) | Real successes (no error) | Time | Notes |
|---|---:|---:|---:|---|
| ETS | 6,358 (100%) | **1,154 (18.2%)** | 126.7s | Up from Iter 2's 1%. Most of the rest fell back to naive mean inside the method (statsmodels Holt-Winters fails on near-zero series). |
| Anomaly-Adjusted | 3,886 (61.1%) | 1,883 (29.6%) | 6.3s | **Fix #2 active**: routed to SMOOTH only (zero_pct ≤ 0.80). 2,472 LUMPY SKUs skipped — perfect partition with Croston's. |
| Multi-Scale Lag | 6,358 (100%) | **4,608 (72.5%)** | 13.3s | Highest real-success rate — workhorse method. |
| Calendar Events | 6,358 (100%) | 164 (2.6%) | 24.0s | Very low success rate; method needs ≥26 weeks per SKU AND non-zero seasonality signal — most A-tier SKUs don't qualify. Same as Iter 2. |
| LightGBM | **0 (ARCHIVED)** | — | — | **Fix #1 active**. Removed from output CSV entirely. |
| Category-Relative | 6,358 (100%) | 1,760 (27.7%) | 96.7s | |
| Naive Seasonal | 6,358 (100%) | **670 (10.5%)** | 12.8s | **Fix #3 active**. "Success" requires ≥56 weeks per-SKU history after `asfreq` weekly fill. Many A-tier SKUs only entered the data partway through 2024, so their per-SKU history is shorter than 56 weeks → they fall back to rolling mean. **This is a real limitation worth noting** — naive_seasonal as in-ensemble method only contributes a true same-period-last-year reading on 10.5% of SKUs. |
| Croston's | 2,472 (38.9%) | 2,062 (32.4%) | 4.4s | LUMPY only. Together with AA covers 6,358 = clean partition. |

### 3.3 Ensemble + post-processing

| Step | Result |
|---|---|
| Ensemble aggregation (median across non-archived methods) | 6,358 forecasts in 0.7s |
| **Seasonal dampening (Fix #4)** | **770 SKUs (12.1%) flagged seasonal (CV>0.50), all 770 dampened** for prediction window starting **2025-03-03** |
| Methods_succeeded distribution | `0`: **1,750 SKUs** (silent + total failures), `1`: 626, `2`: 1,979, `3`: 952, `4`: 465, `5`: 515, `6`: 71 |
| Avg methods per SKU | 1.9 (Iter 2 was 2.9 — drop is from LightGBM removal + AA/Croston's hard partition) |
| Disagreement (4w) — HIGH / MED / LOW | 3,524 / 326 / 2,508 (HIGH share 55.4% — Iter 2 was 67.4%, modest improvement) |

### 3.4 Output files

- `backend/data/predictions/iter3_predictions_20260425_161754.csv` (timestamped)
- `backend/data/predictions/iter3_predictions_latest.csv` (canonical reference)
- 31 columns (vs Iter 2's 35 — LightGBM cols dropped, naive_seasonal cols added net -3)

---

## 4. Aggregate Prediction Distribution

| Statistic | Iter 2 | Iter 3 | Δ |
|---|---:|---:|---:|
| Mean ensemble forecast (units, 4w) | 6.05 | **2.21** | **−63%** |
| Median | 3.10 | 1.30 | −58% |
| 75th percentile | 4.6 | 2.1 | −54% |
| Max | 745 | 496 | −33% |
| Total units predicted (4w, 6,358 SKUs) | 38,445 | **14,041** | **−63%** |
| Forecasts = 0 | — | 1,761 (27.7%) | — |

**Reading this:** Iter 2's bias was +84.4% over-prediction (PROGRESS.md). Cutting aggregate predictions by 63% is consistent with removing the LightGBM bias anchor and dampening seasonal SKUs. Whether this is the *right* amount of correction or an over-correction we cannot know until Mar–Apr 2025 actuals arrive.

---

## 5. Iter 3 vs Iter 2 (same SKU set, head-to-head)

| Metric | Count | Share |
|---|---:|---:|
| SKUs where Iter 3 < 50% of Iter 2 prediction | **2,661** | 41.9% |
| SKUs where Iter 3 > 150% of Iter 2 prediction | 525 | 8.3% |
| SKUs roughly unchanged (within ±50%) | 3,172 | 49.9% |

The 41.9% with reduced predictions is the LightGBM-bias correction landing. The 8.3% with raised predictions is interesting — likely cases where Iter 2 was anchored low because some methods failed and the median collapsed; Iter 3's `naive_seasonal` and seasonal dampening pulled the median up.

---

## 6. Iter 3 vs in-ensemble Naive Seasonal

This answers: "is the ensemble actually making bets, or just hugging the baseline?"

| Comparison | Result |
|---|---|
| Ensemble within ±25% of naive_seasonal_4w | 818 SKUs (12.9%) |
| Ensemble deviates >50% from naive_seasonal_4w | 4,515 SKUs (71.0%) |
| Median ensemble / naive ratio | 1.13 (ensemble slightly above naive) |
| Mean ensemble / naive ratio | 1.55 |

**Reading this:** The ensemble is genuinely diverging from naive on 71% of SKUs — i.e., it's making real bets, not just rubber-stamping the same-month-last-year number. **Whether those bets pay off is exactly what Mar–Apr 2025 actuals will reveal.** If most of the bets lose vs naive, the engine is actively destroying value for those SKUs and we should rethink. If most win, we have evidence the methods are adding signal.

---

## 7. Known limitations / things to validate when actuals land

1. **`naive_seasonal` only contributes a true same-period-last-year reading on 10.5% of SKUs.** The other 89.5% fall back to rolling mean. To get full coverage we'd need ≥56 weeks of per-SKU history, which means waiting until we have multi-store data or accepting that newer SKUs lack a prior-year anchor.
2. **`silent_filter_applied` and `seasonal_dampening_applied` flags are NOT persisted in the CSV.** They're computed at runtime in memory but `save_predictions` doesn't write them. Acceptable for now (we know the counts from logs: 0 silent in this run, 770 dampened) but should be added to `save_predictions` if we want per-SKU auditability post-run.
3. **ETS still mostly fails** (only 18.2% real success rate) — its statsmodels Holt-Winters fit can't handle near-zero series. Iter 4 candidate: lower the per-SKU `min_weeks` floor for ETS or replace with a simpler exponential smoothing.
4. **Calendar Events at 2.6% real success** — borderline useless. Worth deciding in Iter 4 whether to keep it in the ensemble at all.
5. **Anomaly-Adjusted real success only 29.6% within its SMOOTH partition** — the routing fix prevented LUMPY collapse but a chunk of SMOOTH SKUs still fail (probably due to insufficient post-anomaly clean weeks). Diagnose if this matters after scoring.
6. **The ensemble = 0 count is 1,761 (27.7%)** — much higher than Iter 2's natural-zero rate. This is a *mix* of (a) the recency filter producing zero-forecast rows for silent SKUs and (b) SKUs where every running method also returned ~0. Need to break those two apart in scoring.

---

## 8. Pre-Mar/Apr-2025 Honest Estimate

**Cannot give a number for SKU-level accuracy.** That requires actuals.

What we can say:
- **The engine is more conservative.** Aggregate units predicted dropped from 38,445 to 14,041 (−63%), consistent with the +84% bias correction Iter 2 needed.
- **The methods are partitioned cleanly.** AA + Croston's now cover the 6,358 SKUs without overlap; LightGBM is gone; naive_seasonal is in.
- **The ensemble is making real bets.** 71% of SKUs have ensemble predictions that deviate >50% from the naive same-period-last-year baseline — so if the engine improves vs Iter 2 it'll be because of the methods, not because we collapsed to baseline.
- **Risks I want flagged before scoring:**
  - Ensemble could now be *under-predicting* if the bias correction overshot.
  - The 27.7% zero-forecasts may include SKUs that come back to life in Mar–Apr 2025 — wins on inactive SKU filtering, losses on SKUs that re-emerge after a 10-week silence.
  - ACCESORII (the 77%-of-residual category from Phase A) was NOT touched by any of the 5 fixes specifically — its accuracy will likely still be poor in Iter 3.

**What we expect Mar–Apr 2025 scoring to reveal:**
- WMAPE moves from 121% (Iter 2) toward something between 60% and 90%. Below 60% would be unexpectedly good; above 90% would suggest residual issues we didn't address.
- Hit rate ±20% rises from 14.1% (Iter 2) toward 30–45%. Hit rate above 50% would beat target.
- Naive baseline (computed at scoring time on Mar–Apr 2024 data) likely sits around 70–85% WMAPE — we need to beat it by 10–15% to claim victory.
- ACCESORII residual will dominate per-category error.

---

_End of run log. Phase B complete. Awaiting `sales_2025_Mar_Apr_chronological.csv` from user → Phase C scoring._
