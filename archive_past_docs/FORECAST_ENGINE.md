# FORECAST_ENGINE.md — Demand Prediction Engine Design
*Written: April 2026*

---

## What this file is

This is the design document for the real demand prediction engine — the core of this product. Read this before touching any forecasting code.

It captures: why we're building it, what the current engine does (and why it's not enough), what the real engine must do, how to build it, and what infrastructure it runs on.

---

## Why this is the core product

The entire application — dead stock detection, supplier scoring, scenario simulation, the decision queue — all of it is downstream of one question: **how many units will customers want next month?**

If that number is wrong, every other feature is wrong. Dead stock calculations wrong. Reorder quantities wrong. Scenario simulations wrong. The accuracy of the prediction engine is the accuracy of the product.

The current approach Mobexpert uses (and what we called "Basic prediction"): take the same month last year, divide by days, multiply by 28. This produces 25-35% error on average. It ignores trend direction, return-adjusted real demand, and any seasonal pattern finer than "same month last year."

Beating that by 20% on a 50M lei purchasing budget = 2-3M lei in reduced over-ordering and avoided stockouts per year. That's the business case. The engine doesn't need to be perfect — it needs to be measurably better.

---

## What the current engine actually does (and why it's not enough)

Located in `backend/engines/demand.py`.

Steps:
1. Strip returns → `net_sold = units_sold - units_returned`
2. Take last 8 weeks of weekly sales
3. Run linear regression on those 8 points
4. Extend that line forward 4 and 8 weeks

This is trend detection, not forecasting. Problems:
- 8 weeks of a straight line cannot see annual seasonality
- Linear extrapolation breaks immediately on any curve (plateau, reversal, spike)
- Every SKU is calculated in isolation — no cross-SKU learning
- No confidence — every forecast is a single number with no uncertainty
- No promotion handling — a Black Friday spike looks like a "demand surge" and poisons the trend
- No censored demand correction — zero sales when stock is empty looks like zero demand

The Basic prediction it's compared against uses last year same month gross sales. Our current engine uses last 8 weeks extended as a line. Neither is forecasting. Both are backward extrapolation.

---

## What the real engine must do

### The demo scenario — two ways to prove it works

**Scenario A: Accuracy proof**
Train on all data up to December 31, 2025. Generate forecasts for January–February 2026. Compare forecast vs what actually sold. Report: "Our engine was within 20% of actual on X% of SKUs. Basic prediction was within 20% on Y% of SKUs."

**Scenario B: Financial impact proof**
For the same backtest period: calculate what orders would have been placed using basic prediction vs our engine. Compare both against actual sales. Calculate over-ordering cost and stockout cost for each approach. Report: "Basic prediction would have cost X lei in excess inventory and Y lei in lost sales. Our engine reduces that by Z lei."

Both scenarios run on the same engine. Same backtest, two presentations.

### Core requirements

1. **Handles seasonality** — not just trend direction. Annual patterns. Romanian calendar.
2. **Learns across SKUs** — a new product borrows signal from similar established products in the same category.
3. **Corrects for censored demand** — when stock = 0 and sales = 0, that's not zero demand.
4. **Handles promotional spikes** — a 40% discount event is not organic demand and should not pollute the model.
5. **Produces confidence intervals** — forecast of 80 units ± 15 is more honest and useful than just 80.
6. **Is explainable** — can say why it produced a specific number in plain language.
7. **Is backtestable** — accuracy is verifiable, not claimed.

---

## Data required

### Tier 1 — Non-negotiable

| Dataset | Columns needed | Notes |
|---------|---------------|-------|
| Sales transactions | date, store_id, sku_id, qty_sold, revenue | 3 years minimum. Daily granularity preferred, weekly acceptable |
| Returns | date, store_id, sku_id, qty_returned | Can be negative lines in sales. Separate report also fine. |
| Product catalog | sku_id, name, category, subcategory, purchase_cost, retail_price, supplier_id | Current state |
| Category hierarchy | department → category → subcategory mapping | Needed for cross-SKU learning |

### Tier 2 — High value, get if possible

| Dataset | Columns needed | Why it matters |
|---------|---------------|---------------|
| Inventory snapshots | date, store_id, sku_id, qty_on_hand (weekly) | Detects censored demand — zero sales when stock is zero is not zero demand |
| Price/promotion history | sku_id, date_from, date_to, original_price, sale_price | Separates organic demand from promotion-driven spikes |
| Product lifecycle dates | sku_id, launch_date, discontinuation_date | New products need different treatment — borrow from category, not personal history |

### Tier 3 — Build ourselves

| Dataset | Source |
|---------|--------|
| Romanian holiday calendar | Built once in code. Orthodox Easter, Christmas, Black Friday, March 8, 1 Decembrie, National Day |
| Salary cycle position | Built from date — Romanian salaries paid ~10th and ~25th of month |
| Construction season flag | April–September. Furniture demand correlates with renovation activity |

---

## How the engine works — the full pipeline

### Step 1: Data cleaning

Before any model sees data, three corrections:

**Censored demand correction**
If stock_on_hand < (4-week rolling average × 0.5) in a given week:
- Flag that week as CENSORED for that SKU
- Replace recorded sales with the 4-week rolling average as a proxy
- This prevents the model from learning "demand was zero" when really "stock was zero"

**Promotional spike handling**
If sales in a week > (13-week rolling average × 2.5):
- Flag that week as PROMOTIONAL
- Either exclude from training or model promotion effect separately
- Prevents model from treating a one-off sale event as structural demand growth

**New product / end of life handling**
- Products < 52 weeks old: use category-level seasonality, scale by the SKU's observed share of category
- Products flagged as discontinuing: forecast toward zero, exclude from standard model

---

### Step 2: Feature engineering

For each SKU × week in the training dataset, compute:

**Lag features — the most powerful group**
```
sales_lag_1w       last week's actual sales
sales_lag_4w       4 weeks ago
sales_lag_13w      13 weeks ago (one quarter)
sales_lag_26w      26 weeks ago (half year)
sales_lag_52w      same week last year  ← single most predictive feature
rolling_avg_4w     4-week moving average
rolling_avg_13w    13-week moving average
yoy_ratio          rolling_avg_4w / rolling_avg_52w (growth vs last year)
trend_momentum     rolling_avg_4w / rolling_avg_13w (recent vs medium term)
```

**Romanian calendar features**
```
week_of_year           1–52
month                  1–12
is_orthodox_easter     computed per year (varies from Catholic Easter)
is_christmas_week      week 51–52
is_black_friday        last Friday of November ± 1 week
is_march_8_week        Romanian Women's Day — gifting spike
is_1_decembrie_week    National Day
salary_cycle_phase     early_month / mid_month / end_month
is_construction_season April–September (renovation / new home purchases)
is_summer_lull         July–August (lower retail activity)
```

**Product features**
```
category_id
subcategory_id
price_segment          budget / mid / premium (relative to category median)
product_age_weeks      weeks since launch
is_mature              age > 52 weeks
```

**Category-level aggregates — enables cross-SKU learning**
```
category_sales_lag_1w     whole category last week
category_yoy_ratio        how the category is trending
category_seasonal_index   this week's typical share of annual category sales
sku_share_of_category     this SKU's typical % of its category (rolling 13w)
```

**Price and promotion**
```
discount_pct              how deep is any active promotion
is_on_promotion           binary flag
weeks_since_last_promo    recency of last discount event
```

---

### Step 3: Models

**Model A — ETS (Holt-Winters exponential smoothing)**
- Statistical method. Per-SKU.
- Decomposes history into: base level + trend component + seasonal multipliers per week-of-year
- Projects all three forward
- Works best on: mature SKUs with 52+ weeks of clean history and clear seasonal pattern
- Library: `statsmodels.tsa.holtwinters.ExponentialSmoothing`

**Model B — LightGBM global model**
- Machine learning. One model trained on ALL SKUs simultaneously.
- Each training row = one SKU × one week with all features above
- Target = actual sales that week
- Learns cross-SKU patterns: "all sofas spike in October", "budget SKUs are more promotion-sensitive than premium"
- New products benefit from patterns learned across thousands of existing products
- Works best on: products with promotions, new products, complex patterns, short history
- Library: `lightgbm`

**Model C — Ensemble**
- After backtesting A and B per SKU: weight each by its historical accuracy
- Final forecast = (weight_ets × forecast_ets) + (weight_lgbm × forecast_lgbm)
- Stable mature SKUs → ETS usually wins. Everything complex → LightGBM usually wins.

---

### Step 4: Backtesting (how accuracy is measured)

Walk-forward cross-validation — not a single train/test split:

```
All data: March 2024 ─────────────────────── Feb 2026

Fold 1: Train on weeks 1–52,  predict weeks 53–56   (compare to actual)
Fold 2: Train on weeks 1–60,  predict weeks 61–64   (compare to actual)
Fold 3: Train on weeks 1–68,  predict weeks 69–72   (compare to actual)
...continues until end of data
Average accuracy across all folds = the real accuracy number
```

Accuracy metrics reported:
- **WMAPE** — Weighted Mean Absolute Percentage Error. Weighted by volume so a 50% error on a SKU that sells 2/week counts less than a 20% error on one that sells 200/week.
- **Bias** — are we systematically over or under forecasting? More important than average accuracy.
- **Hit rate at ±20%** — what % of SKUs fell within 20% of actual. The demo headline number.

---

### Step 5: Financial impact calculation

```
For each SKU in backtest period:

  basic_order   = v_tool_estimate (same month last year method)
  engine_order  = our forecast
  actual_sales  = what really sold

  Over-order cost:
    if order > actual: cost = (order - actual) × purchase_cost

  Stockout cost (conservative, 1.5× margin on missed revenue):
    if order < actual: cost = (actual - order) × gross_margin × 1.5

  Savings per SKU = (basic_total_cost) - (engine_total_cost)

Sum across all SKUs → total financial impact in lei
```

Output: "Basic prediction approach: X lei in over-ordering + Y lei in stockout losses. Our engine: A lei + B lei. Net improvement: Z lei over the test period."

---

## What the engine outputs per SKU

```json
{
  "sku_id": "SKU-0042",
  "sku_name": "Canapea Coltar Gri 3 locuri",
  "forecast_4_weeks": 23,
  "forecast_8_weeks": 44,
  "confidence_low_4w": 17,
  "confidence_high_4w": 31,
  "model_used": "ensemble",
  "model_accuracy_wmape": 0.13,
  "recommended_order_qty": 18,
  "basic_prediction_4w": 31,
  "delta_vs_basic_units": -8,
  "delta_vs_basic_lei": -2640,
  "drivers": [
    "Same week last year: 21 units",
    "Category trend: +8% YoY",
    "Week 14 seasonal index: +14% above annual average",
    "No active promotion"
  ]
}
```

---

## Infrastructure — what you actually need

### For pilot (one client, one or a few stores)

```
$20/month VPS  OR  your laptop
├── PostgreSQL
│   ├── raw tables: sales, returns, products, inventory_snapshots, promotions
│   └── output tables: demand_results, forecasts, backtest_accuracy, order_recommendations
│
├── Python engine
│   ├── ingestion.py      reads Pentaho CSV exports, validates, loads to PostgreSQL
│   ├── cleaning.py       censored demand correction, outlier flagging
│   ├── features.py       builds the feature matrix from cleaned data
│   ├── ets_model.py      Holt-Winters per SKU
│   ├── lgbm_model.py     LightGBM global model
│   ├── ensemble.py       combines A + B weighted by backtested accuracy
│   ├── backtest.py       walk-forward validation, accuracy reporting
│   └── impact.py         financial impact calculation (lei saved)
│
└── FastAPI + Next.js (already built — forecasts plug into existing API)
```

Weekly workflow:
```
Monday: V exports CSVs from Pentaho
→ ingestion script runs (2 minutes)
→ engine retrains (2–5 minutes)
→ new forecasts in app
→ buyer approves/overrides via decision queue
→ decisions logged (future training data)
```

No streaming. No cloud required. No GPU. A scheduled Python script and PostgreSQL.

### Libraries needed

```
pandas, numpy         already in stack
statsmodels           pip install statsmodels  (ETS)
lightgbm              pip install lightgbm     (gradient boosting)
scikit-learn          pip install scikit-learn (metrics, validation)
scipy                 already in stack
```

Zero API costs for the forecasting engine. Pure local computation.

---

## Realistic accuracy expectations

| Method | WMAPE | Hit rate ±20% |
|--------|-------|---------------|
| Basic prediction (current) | 28–32% | ~45% |
| ETS / Holt-Winters | 16–19% | ~65% |
| LightGBM | 13–16% | ~72% |
| Ensemble | 11–14% | ~78% |

On real Mobexpert data: expect 3–5% worse in each row due to messy data. The improvement vs basic prediction is the number that matters, and it holds.

**Goal: beat basic prediction by 20%+ in WMAPE and show the savings in lei.**

---

## Build order

1. **Backtesting harness** — train/test split, walk-forward folds, WMAPE + hit rate + savings calculation
2. **Data cleaning module** — censored demand detection, outlier flagging
3. **Feature engineering pipeline** — lags, Romanian calendar, category aggregates
4. **ETS engine** — Model A, first real accuracy number
5. **Financial impact report** — the savings calculation that makes the business case
6. **LightGBM engine** — Model B, accuracy improves
7. **Ensemble** — combines both, best accuracy
8. **Ingestion pipeline** — for when real Pentaho data arrives (same interface, real data)

Steps 1–5 = working demo on synthetic data.
Steps 6–8 = production-ready engine.

---

## What this is NOT

- Not a real-time system. Batch, weekly is enough.
- Not autonomous. Engine recommends, buyer decides.
- Not a replacement for the buyer's judgment. It's a decision support tool.
- Not finished when it's accurate. It's finished when buyers trust it enough to act on it.

The logged decisions (approve / skip / override + reason) are the feedback loop. Every decision recorded is a labeled training example for the next version of the model. That is the data moat described in VISION.md.
