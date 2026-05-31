# Forecast Engine — Iteration Log

*Every test, every result, every change. Nothing gets lost.*

---

## Iteration 1 — Phase 1K Baseline (2026-04-21)

### Setup
- **Training data:** Jun 2023 – Oct 2024 (Fast_Movers_45_SKUs_Jun23_Oct24.csv)
- **Holdout data:** Nov – Dec 2024 (Report_20_SKUs_Nov_Dec_2024.csv)
- **SKUs tested:** 20 A-tier products (mattresses, somiere, furniture, accessories)
- **Store:** Baneasa (single store)
- **Purpose:** First-ever validation of the 6-method ensemble on real Mobexpert data

### Methods Used
| Method | Status | Min Required | Data Available | Notes |
|--------|--------|-------------|----------------|-------|
| ETS (Holt-Winters) | Ran on 12/20 | 52 weeks | 15–47 weeks | Failed on 8 SKUs — insufficient history |
| LightGBM | Ran on 20/20 | 100 total rows | 614 rows | Missing lag_52w for most SKUs, only 20 SKUs for cross-learning |
| Category-Relative | 0/20 | 2+ SKUs/category | — | Category column not passed through pipeline — didn't run at all |
| Anomaly-Adjusted | Ran on 20/20 | 13 weeks | 15–47 weeks | Too aggressive — stripped intermittent sales as anomalies |
| Multi-Scale Lag | Ran on 20/20 | 8 weeks | 15–47 weeks | Only 3 of 5 lag scales available (1w, 4w, 13w) |
| Calendar Events | Ran on 13/20 | 26 weeks effective | 15–47 weeks | Seasonal indices built on single data points = noise |

### Results — Unit Predictions vs Actuals (Nov + Dec 2024)

| SKU | Actual Units | Predicted Units | Error | Error % | Verdict |
|-----|-------------|-----------------|-------|---------|---------|
| BL13CT111 | 78 | 41.3 | -36.7 | -47% | UNDER — missed Q4 gifting spike |
| 46COMFORT160200 | 26 | 29.4 | +3.4 | +13% | GOOD |
| 46COMFORTPLUS160200 | 21 | 18.9 | -2.1 | -10% | GOOD |
| MFSOMIERABASIC090190 | 18 | 32.0 | +14.0 | +78% | OVER — Dec demand collapsed |
| MFNEWYORK180200 | 17 | 13.6 | -3.4 | -20% | OK |
| MFSOMIERABASIC160190 | 15 | 23.2 | +8.2 | +55% | OVER — Dec collapsed to 2 units |
| MFNEWYORK160200 | 13 | 11.1 | -1.9 | -15% | GOOD |
| 46COMFORT160200EUROTOP | 12 | 10.4 | -1.6 | -13% | GOOD |
| MFCHICAGO180200 | 11 | 6.0 | -5.0 | -45% | UNDER |
| 46COMFORTPLUS180200 | 10 | 16.2 | +6.2 | +62% | OVER |
| MFCHICAGO160200 | 9 | 8.0 | -1.0 | -11% | GOOD |
| MFWOODLAKE180200 | 8 | 10.4 | +2.4 | +30% | OVER-ish |
| 46COMFORT180200 | 8 | 6.9 | -1.1 | -14% | GOOD |
| FPD038 | 6 | 9.8 | +3.8 | +63% | OVER — Dec had 0 sales |
| KARP078 | 5 | 6.6 | +1.6 | +32% | OVER-ish |
| MFSALTEASERTA16020030ANI | 4 | 11.4 | +7.4 | +185% | MISS — product stopped selling |
| SMS761AB | 4 | 9.4 | +5.4 | +135% | MISS |
| SMS730CDAG | 3 | 8.7 | +5.7 | +190% | MISS |
| FRE02P41 | 0 | 9.2 | +9.2 | ∞ | MISS — zero actual sales |
| SMS717AG | 0 | 6.9 | +6.9 | ∞ | MISS — zero actual sales |

### Aggregate Metrics
- **Total units:** Actual 268, Predicted 289.4 → **+3% error** (aggregate cancellation)
- **Total revenue:** Actual 536,831 RON, Predicted 641,430 RON → **19% error**
- **WMAPE:** 56.6% (individual SKU level, excluding zero-sales SKUs)
- **Hit rate ±20%:** 39% of SKUs (7 of 18 with sales)
- **Hit rate ±50%:** 61% of SKUs (11 of 18 with sales)

### Revenue Comparison
- **Predicted:** 641,430 RON
- **Actual:** 536,831 RON
- **Gap:** +104,599 RON (19% over)
- Revenue overestimate driven by: predicting sales on 2 zero-sales SKUs (37k RON phantom revenue), and overestimating furniture pieces (SMS range, MFSALTEASERTA)

### Root Causes Identified
1. **No December 2023 in training data** — most SKUs started mid-late 2023, engine never saw a full Q4 cycle
2. **Intermittent/lumpy demand not modeled** — SMS730CDAG, SMS761AB, FRE02P41, SMS717AG sell 0-3 units/week with many zeros; all methods assume continuous demand
3. **BL13CT111 seasonal miss** — pillow/accessory Q4 gifting spike invisible without full seasonal cycle
4. **Category-Relative broken** — didn't run due to pipeline issue (category column not passed to weekly data)
5. **Anomaly-Adjusted too aggressive** — stripping too much data as anomalies when sales are naturally sparse
6. **Dec ≠ Nov** — engine splits 8w forecast linearly as 4w+4w, but December demand is structurally different from November for most products

### Decisions Made After Iteration 1

**Architecture fixes (Phase 1 — execute before Iteration 2):**
1. Fix Category-Relative pipeline — join category column into weekly aggregation
2. Add Croston's method for intermittent SKUs (>40% zero-weeks): SMS730CDAG, SMS761AB, FRE02P41, SMS717AG
3. Add Nov–Dec 2024 to training data (first full Q4 cycle)
4. Separate Nov and Dec forecast profiles — stop splitting 8w linearly, apply month-specific calendar weights
5. Relax Anomaly-Adjusted threshold from 2.5x to 3.5x for SKUs with weekly avg < 3 units
6. ETS fallback mode: if 26–51 weeks available, run without seasonal component instead of hard-failing

**Classification decision:**
- Keep ABC (revenue priority) as SKU selection filter
- Add second axis: Demand Pattern (Smooth vs Lumpy, based on % zero-weeks)
- Method routing by this 2-axis grid, not by ABC tier alone
- Third axis (seasonality strength) to be derived from Phase 2 data

**Testing strategy (Phase 2):**
- Use controlled exposure, not bulk data feed
- Slide training window forward 2 months per iteration, always compare to actuals before extending
- Planned windows: Iter 2 (train →Dec 2024, predict Jan–Feb 2025), Iter 3 (→Feb 2025, predict Mar–Apr), Iter 4 (→Apr 2025, predict May–Jun)

---

## Iteration 2 — Phase 1 Fixes + First 2025 Test *(pending)*

### Changes Made From Iteration 1
- [ ] Category-Relative pipeline fixed
- [ ] Croston's method added for lumpy SKUs
- [ ] Training data extended to Dec 2024
- [ ] Nov/Dec forecast profiles separated
- [ ] Anomaly-Adjusted threshold relaxed for sparse SKUs
- [ ] ETS fallback mode for 26–51 week SKUs

### Setup
- Training data: Jun 2023 – Dec 2024
- Holdout: Jan – Feb 2025
- SKUs: same 20 A-tier

### Results
*(To be filled after Fyo provides Jan–Feb 2025 actuals)*

---

## Pattern Tracker

*Recurring patterns across iterations — things that keep showing up.*

| Pattern | First Seen | Iterations | Status |
|---------|-----------|------------|--------|
| Dec demand drops sharply vs Nov for furniture | Iter 1 | 1 | Fix: month-specific calendar weights |
| Intermittent SKUs get grossly overestimated | Iter 1 | 1 | Fix: Croston's method routing |
| BL13CT111 (accessories) has strong Q4 seasonality | Iter 1 | 1 | Fix: full year training data |
| Aggregate accuracy masks individual SKU errors | Iter 1 | 1 | Monitor: always report WMAPE + hit rate, not just total |
| Category-Relative never ran | Iter 1 | 1 | Fix: pipeline join |
| ETS hard-fails on <52w SKUs | Iter 1 | 1 | Fix: fallback to no-seasonal mode |

---

## File Locations
- Iteration log (this file): `active_docs/FORECAST_ENGINE_ITERATIONS.md`
- Blueprint: `active_docs/FORECAST_ENGINE_V2.0_BLUEPRINT.md`
- Progress tracker: `PROGRESS.md` (root)
- Training CSVs: `forecast_data/`
- Actuals CSVs: `forecast_data/`
