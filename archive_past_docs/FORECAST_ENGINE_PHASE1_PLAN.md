# FORECAST ENGINE — PHASE 1 IMPLEMENTATION PLAN

**Status:** Pre-implementation design document
**Last updated:** April 6, 2026
**Purpose:** Define the modular, multi-method forecasting architecture for MVP

---

## EXECUTIVE SUMMARY

We are building a **modular ensemble forecasting system** with 6 independent, substantive prediction methods. Each method is:
- **Powerful on its own** — can produce accurate forecasts independently
- **Fundamentally different** — answers a different question about demand
- **Non-overlapping at the core** — different mathematical foundations, not just variations of the same approach

The methods aggregate into a unified forecast **without pre-assigned weights**. Weights will be determined empirically during backtest phase on real data.

**AI placement:** Not in forecast generation (unnecessary complexity, reduced transparency). AI serves the decision layer — explaining forecasts, flagging anomalies, guiding buyer overrides.

---

## THE 6 INDEPENDENT FORECASTING METHODS

### METHOD 1: STATISTICAL TIME SERIES DECOMPOSITION (ETS/Holt-Winters)

**What it answers:** "What is the underlying statistical pattern in this SKU's historical demand?"

**Mathematical foundation:**
```
Demand = Level × Trend × Seasonality × Random

Where:
  Level       = baseline demand (where sales "live")
  Trend       = directional change (growing / declining / flat)
  Seasonality = repeating weekly/monthly patterns
  Random      = unexplained noise
```

**Algorithm:** Holt-Winters Exponential Smoothing
- Decomposes 52 weeks of history into these 4 components
- Updates each component with exponential smoothing (recent weeks weighted more heavily)
- Projects all components forward

**Calculation (simplified):**
```
L[t] = α × (Y[t] / S[t-52]) + (1-α) × (L[t-1] + T[t-1])
T[t] = β × (L[t] - L[t-1]) + (1-β) × T[t-1]
S[t] = γ × (Y[t] / L[t]) + (1-γ) × S[t-52]

Forecast = (L[t] + h×T[t]) × S[t+h]

Where:
  α, β, γ = smoothing parameters (0-1)
  h       = forecast horizon (weeks ahead)
  Y[t]    = actual demand at time t
```

**Why this method:**
- Captures annual seasonality (e.g., furniture demand spikes April-Sept)
- Handles stable products with clear patterns
- Produces confidence intervals naturally
- Statistically rigorous, interpretable

**Limitations:**
- Assumes patterns from the past repeat
- Poor on products with structural breaks (new product, discontinued)
- Requires 52+ weeks of clean data

**Library:** `statsmodels.tsa.holtwinters.ExponentialSmoothing`

**Output per SKU:**
```python
{
    "method": "ets",
    "forecast_4w": 45,
    "forecast_8w": 92,
    "confidence_low_4w": 38,
    "confidence_high_4w": 52,
    "model_fit_quality": 0.87,  # R-squared
    "seasonal_indices": {
        "week_1": 0.92,   # Week 1 is 92% of annual average
        "week_14": 1.14,  # Week 14 is 114% of annual average (Easter region)
        ...
    },
    "trend": "STABLE",  # or GROWING / DECLINING
    "trend_slope": 0.3  # weekly units change
}
```

---

### METHOD 2: GLOBAL MACHINE LEARNING MODEL (LightGBM)

**What it answers:** "Given all patterns learned across thousands of products and weeks, what will this SKU sell?"

**Mathematical foundation:**
```
Demand = f(all_features)

Where f() is learned via gradient boosting decision trees,
trained on ALL SKUs × ALL weeks simultaneously
```

**Features fed into the model:**
```
TEMPORAL LAGS:
  sales_lag_1w, sales_lag_4w, sales_lag_13w, sales_lag_26w, sales_lag_52w
  rolling_avg_4w, rolling_avg_13w
  yoy_growth_ratio, trend_momentum

PRODUCT FEATURES:
  sku_id, category_id, subcategory_id
  price_segment (budget/mid/premium), product_age_weeks
  is_mature (>52 weeks), historical_volatility

CALENDAR FEATURES:
  week_of_year, month, day_of_week
  is_orthodox_easter, is_christmas_week, is_black_friday
  is_march_8_week, is_1_decembrie_week
  salary_cycle_phase (early/mid/end_month)
  is_construction_season, is_summer_lull

CATEGORY AGGREGATES:
  category_sales_lag_1w, category_yoy_ratio
  category_seasonal_index, sku_share_of_category_pct

PROMOTION SIGNALS:
  is_on_promotion, discount_pct, weeks_since_last_promo
```

**Training:**
```
Training data:
  Each row = SKU × week
  Features = above 40+ dimensions
  Target = actual sales that week

Training runs on all historical weeks across all SKUs
Model learns: "sofas + Easter + April + young_product = spike"
```

**Why this method:**
- Learns cross-SKU patterns (new sofas inherit category patterns)
- Handles promotions, new products, complex dynamics
- Feature importance shows what drives demand (explainable)
- Often beats statistical methods on real messy data

**Limitations:**
- Black box (harder to explain why specific number)
- Requires large training dataset (ideally 100+ SKUs × 52+ weeks)
- Prone to overfitting if not validated properly

**Library:** `lightgbm`

**Output per SKU:**
```python
{
    "method": "lightgbm",
    "forecast_4w": 42,
    "forecast_8w": 88,
    "confidence_low_4w": 35,
    "confidence_high_4w": 49,
    "model_fit_quality": 0.92,  # Cross-validation RMSE
    "feature_importance": {
        "sales_lag_52w": 0.24,           # Most important
        "category_yoy_ratio": 0.18,
        "is_easter_week": 0.12,
        "product_age_weeks": 0.10,
        ...
    },
    "top_drivers": [
        "Same week last year: 21 units",
        "Category trend: +8% YoY",
        "Product age: 18 weeks (maturing)"
    ]
}
```

---

### METHOD 3: CATEGORY-DRIVEN RELATIVE PERFORMANCE

**What it answers:** "How is this SKU performing relative to its category, and what does that tell us about future demand?"

**Mathematical foundation:**
```
SKU_Forecast = Category_Forecast × SKU_Share_of_Category

Where:
  Category_Forecast         = forecast for entire category
  SKU_Share_of_Category     = this SKU's typical % of category sales
```

**Calculation steps:**

**Step 1: Category-level forecast**
```
category_rolling_avg_4w = sum(all_skus_in_category_sales_last_4_weeks) / 4

category_rolling_avg_52w = sum(all_skus_in_category_sales_same_52weeks) / 52

category_yoy_ratio = category_rolling_avg_4w / category_rolling_avg_52w

category_forecast_4w = category_rolling_avg_4w × category_yoy_ratio
```

**Example:**
```
Sofa category this year:
  4-week rolling avg = 500 units/week
  Same period last year = 450 units/week
  YoY ratio = 500 / 450 = 1.11 (category up 11%)

Category forecast = 500 × 1.11 = 555 units/week × 4 weeks = 2,220 units
```

**Step 2: SKU's share of category**
```
sku_sales_4w = sum(sku_sales_last_4_weeks)
category_sales_4w = sum(all_category_sales_last_4_weeks)

sku_share = sku_sales_4w / category_sales_4w

Example:
  SKU-100 sales last 4 weeks = 80 units
  Total sofa category last 4 weeks = 500 units
  SKU share = 80 / 500 = 16%
```

**Step 3: SKU forecast**
```
sku_forecast_4w = category_forecast_4w × sku_share

sku_forecast_4w = 2,220 × 0.16 = 355 units
```

**Step 4: Performance relative to category**
```
sku_rolling_avg_4w = 80 / 4 = 20 units/week
category_rolling_avg_4w = 500 / 4 = 125 units/week
category_yoy = 1.11

If SKU grew at same rate as category:
  expected_sku = 20 × 1.11 = 22.2 units/week

Actual vs expected:
  actual = 20 (stable)
  expected = 22.2 (should be growing with category)
  relative_performance = 20 / 22.2 = 0.90 (SKU underperforming category by 10%)
```

**Why this method:**
- Captures market dynamics (whole category up → individual SKU should be up)
- Prevents false signals (SKU flat while category grows = actual underperformance)
- Works for new products (inherit category growth, adjust by category share)
- Accounts for structural market changes

**Limitations:**
- Assumes SKU's share of category is stable (breaks if product repositioning)
- Less accurate on niche SKUs (small sample noise)
- Doesn't capture SKU-specific drivers

**Output per SKU:**
```python
{
    "method": "category_relative",
    "forecast_4w": 88,
    "forecast_8w": 172
    "category_forecast_4w": 555,
    "sku_share_of_category": 0.158,
    "sku_performance_vs_category": 0.90,  # 90% of expected (underperforming by 10%)
    "category_yoy_ratio": 1.11,
    "category_trend": "GROWING",
    "explanation": "Category is up 11% YoY, but SKU is up only 8% (underperforming relative to category)"
}
```

---

### METHOD 4: ANOMALY-ADJUSTED BASELINE (Robust Demand Estimation)

**What it answers:** "What would demand be if we remove spikes, anomalies, and distortions from the historical record?"

**Mathematical foundation:**
```
Clean_Historical_Demand = Raw_Demand - Promotional_Spikes - Outliers - Inventory_Issues
Clean_Baseline = Median(Clean_Historical_Demand)
Forecast = Clean_Baseline × Growth_Rate
```

**Algorithm:**

**Step 1: Identify and flag anomalies**
```
For each week in history:

Rolling average (13-week) = avg(sales weeks t-13 to t)
Deviation = |sales[t] - rolling_avg| / rolling_avg

If deviation > 2.5:
  Flag as ANOMALY (outlier or promotional event)
```

**Example:**
```
Week 10 normal sales = 30 units
13-week rolling avg = 28 units
Week 10 actual = 50 units (Easter promotion)

Deviation = |50 - 28| / 28 = 0.786 = 78.6% above normal
Flag: [PROMOTIONAL]
```

**Step 2: Separate promotional vs baseline demand**
```
If week is flagged PROMOTIONAL:
  baseline_estimate = rolling_avg (what would have sold without promo)
Else:
  baseline_estimate = actual_sales
```

**Step 3: Calculate clean baseline**
```
clean_weeks = [weeks where not PROMOTIONAL and not OUTLIER]
clean_baseline = MEDIAN(sales[clean_weeks])

Use MEDIAN not MEAN to reduce outlier influence
```

**Step 4: Growth rate on clean data**
```
recent_clean_avg = MEDIAN(sales[clean_weeks, last 13 weeks])
historical_clean_avg = MEDIAN(sales[clean_weeks, all history])

growth_rate = recent_clean_avg / historical_clean_avg

forecast_4w = clean_baseline × growth_rate × 4
```

**Example:**
```
History (removing promotions):
  Clean baseline (median) = 28 units/week
  Recent 13 weeks (cleaned) = 30 units/week
  Growth rate = 30 / 28 = 1.07 (7% growth)

Forecast for next 4 weeks = 28 × 1.07 × 4 = 120 units
```

**Why this method:**
- Establishes "true baseline" free from distortions
- Promotional events don't poison the forecast
- Handles all-time-high seasons (promo identified, isolated)
- Conservative, robust approach

**Limitations:**
- Assumes anomalies are removable (complex promotions may be structural)
- MEDIAN works well but may discard important information
- Requires good promotion/inventory data for flagging

**Output per SKU:**
```python
{
    "method": "anomaly_adjusted",
    "forecast_4w": 112,
    "forecast_8w": 224,
    "clean_baseline": 28.0,
    "recent_growth_rate": 1.07,
    "anomalies_detected": 5,
    "anomaly_weeks": ["2025-04-10", "2025-11-28", ...],  # Easter, Black Friday
    "outliers_detected": 2,
    "explanation": "5 promotional weeks removed from baseline. Clean baseline: 28 units/week. Recent growth 7%."
}
```

---

### METHOD 5: MULTI-SCALE LAG ANALYSIS (Temporal Momentum)

**What it answers:** "What do multiple time-scale comparisons tell us about demand momentum and sustainability?"

**Mathematical foundation:**
```
Demand_Signal = f(lag_1w, lag_4w, lag_13w, lag_26w, lag_52w)

Different lags capture different momentum:
  lag_1w   → immediate week-to-week momentum
  lag_4w   → month-ago baseline
  lag_13w  → quarter-ago baseline
  lag_26w  → half-year comparison
  lag_52w  → year-ago seasonality anchor
```

**Calculation:**

**Step 1: Calculate lag ratios (growth at each scale)**
```
momentum_1w = rolling_avg_1w / rolling_avg_4w
              (are we accelerating week-to-week?)

momentum_4w = rolling_avg_4w / rolling_avg_13w
              (is the recent month faster than the quarter?)

momentum_13w = rolling_avg_13w / rolling_avg_26w
               (is this quarter faster than last half-year?)

momentum_26w = rolling_avg_26w / rolling_avg_52w
               (is the half-year faster than last year?)

Example:
  This week's sales = 35 units
  4-week rolling avg = 32 units/week
  13-week rolling avg = 30 units/week
  26-week rolling avg = 28 units/week
  52-week rolling avg (last year) = 25 units/week

  momentum_1w = 35 / 32 = 1.094 (accelerating week-to-week)
  momentum_4w = 32 / 30 = 1.067 (month faster than quarter)
  momentum_13w = 30 / 28 = 1.071 (quarter faster than half-year)
  momentum_26w = 28 / 25 = 1.120 (half-year up from last year)
```

**Step 2: Trend consistency check**
```
If all momentum ratios > 1.0:
  Signal: STRONG_GROWTH (consistent acceleration across all scales)

If all momentum ratios < 1.0:
  Signal: STRONG_DECLINE (consistent deceleration across all scales)

If mixed (some > 1.0, some < 1.0):
  Signal: UNSTABLE or REVERTING (momentum shifting)
```

**Step 3: Forecast based on multi-scale momentum**
```
Use weighted combination of lags:

forecast_4w = (lag_1w × 0.2) + (lag_4w × 0.3) + (lag_13w × 0.3) + (lag_26w × 0.1) + (lag_52w × 0.1)

Weights: recent weeks matter more, but also anchor to yearly pattern
```

**Example:**
```
Lags (weekly):
  lag_1w = 35
  lag_4w = 32
  lag_13w = 30
  lag_26w = 28
  lag_52w = 25

Weighted forecast = (35×0.2) + (32×0.3) + (30×0.3) + (28×0.1) + (25×0.1)
                  = 7.0 + 9.6 + 9.0 + 2.8 + 2.5
                  = 30.9 units/week × 4 weeks
                  = 123.6 units for next 4 weeks
```

**Why this method:**
- Captures momentum at different time scales
- False signals identified (e.g., week-to-week spike, but monthly stable)
- Detects trend reversals (momentum shifting)
- Simple, interpretable

**Limitations:**
- Backward-looking (extrapolates recent patterns)
- Poor on structural breaks (new marketing campaign changes demand)
- Doesn't account for calendar or external events

**Output per SKU:**
```python
{
    "method": "multi_scale_lag",
    "forecast_4w": 124,
    "forecast_8w": 248,
    "momentum_signals": {
        "lag_1w": 35,
        "lag_4w": 32,
        "lag_13w": 30,
        "lag_26w": 28,
        "lag_52w": 25,
    },
    "momentum_ratios": {
        "momentum_1w": 1.094,   # week-to-week acceleration
        "momentum_4w": 1.067,   # month vs quarter
        "momentum_13w": 1.071,  # quarter vs half-year
        "momentum_26w": 1.120,  # half-year vs year
    },
    "trend_signal": "STRONG_GROWTH",
    "explanation": "Consistent growth across all time scales. Sales accelerating week-to-week, month faster than quarter, quarter faster than half-year."
}
```

---

### METHOD 6: CALENDAR & EXTERNAL EVENTS (Romanian Market Seasonality)

**What it answers:** "What do known external patterns tell us demand will be at specific times of year?"

**Mathematical foundation:**
```
Forecast = Base_Demand × Seasonal_Index × Event_Multiplier

Where seasonal patterns are derived from observed historical patterns
tied to calendar events and Romanian market cycles
```

**Algorithm:**

**Step 1: Build seasonal indices per week-of-year**
```
For each week 1-52 across all years of history:
  seasonal_index[week_i] = average_sales[week_i] / annual_average_sales

Example (Sofas):
  Week 14 (Easter): 500 units (annual avg: 350) → index = 1.43
  Week 15 (post-Easter): 250 units → index = 0.71
  Week 33 (summer lull): 200 units → index = 0.57
  Week 43 (renovation season ends): 420 units → index = 1.20
```

**Step 2: Build event calendar (Romanian-specific)**
```
EVENTS HARDCODED:
  Orthodox Easter (varies yearly, computed): +40% demand spike (gifting)
  Christmas (Dec 25 + week after): +60% spike
  Black Friday (last Friday Nov ± 1 week): +35% spike (discounts)
  March 8 (Women's Day): +25% spike (gifting)
  1 December (National Day): +20% spike (renovations / home gifts)

MARKET CYCLES:
  April-September: +15% (construction season, renovations)
  July-August: -20% (summer vacation, lower retail activity)
  Salary cycle (10th, 25th of month): +10% adjacent days (people have cash)
```

**Step 3: Identify current/upcoming season**
```
Today = April 15, 2026

What season are we in?
  ✓ Construction season (April-Sept): +15%
  ✗ Summer lull (July-Aug)
  ✗ Holiday season

Upcoming events?
  Easter 2026: April 19 (week 16) → forecast Easter week as 1.43× base
```

**Step 4: Apply multipliers**
```
Base demand for SKU-100 sofas = 30 units/week (annual average)

Week 16 (Easter week):
  Easter multiplier = 1.43
  Construction season multiplier = 1.15
  Combined = 1.43 × 1.15 = 1.645

  forecast = 30 × 1.645 = 49.4 units (high)

Week 32 (July, summer lull):
  Summer lull multiplier = 0.80
  Construction season multiplier = 1.15 (overlaps)
  Combined = 0.80 × 1.15 = 0.92

  forecast = 30 × 0.92 = 27.6 units (stable)
```

**Why this method:**
- Captures market-specific patterns (Romanian calendar is unique)
- Explainable (events are known, repeatable)
- Works for any product type (same calendar applies)
- Accounts for salary cycles, holidays, renovation seasons

**Limitations:**
- Assumes historical patterns repeat (new event = surprise)
- Individual event effect learned from limited samples (Easter happens once/year)
- Overlapping events need careful modeling (Easter + construction season)

**Output per SKU:**
```python
{
    "method": "calendar_events",
    "forecast_4w": 98,
    "forecast_8w": 205,
    "seasonal_breakdown": {
        "week_14": {"index": 1.43, "event": "Orthodox Easter", "multiplier": 1.43},
        "week_15": {"index": 0.71, "event": "Post-Easter", "multiplier": 0.71},
        "week_16": {"index": 0.95, "event": "Normal", "multiplier": 1.0},
        "week_17": {"index": 0.95, "event": "Normal", "multiplier": 1.0},
    },
    "current_season": "Construction season (Apr-Sep)",
    "season_multiplier": 1.15,
    "upcoming_events": ["Easter week 16: +43%"],
    "explanation": "Base demand 30/week. Next 4 weeks include Easter week (1.43×), construction season (+15%). Weighted forecast: 98 units."
}
```

---

## AGGREGATION SYSTEM (NO WEIGHTS YET)

**How the 6 methods combine:**

Each method produces a forecast. We aggregate WITHOUT pre-assigned weights.

**Current aggregation approach: Equal-weighted ensemble**

```python
def aggregate_forecasts(methods: List[dict]) -> dict:
    """
    Combine 6 method forecasts with equal weight (no priority)
    """
    forecasts_4w = [m["forecast_4w"] for m in methods]
    forecasts_8w = [m["forecast_8w"] for m in methods]

    # Approach 1: Simple arithmetic mean
    final_forecast_4w = sum(forecasts_4w) / len(forecasts_4w)
    final_forecast_8w = sum(forecasts_8w) / len(forecasts_8w)

    # Approach 2: Median (robust to outliers)
    final_forecast_4w = statistics.median(forecasts_4w)
    final_forecast_8w = statistics.median(forecasts_8w)

    # Approach 3: Trimmed mean (remove highest/lowest, average the rest)
    # Remove highest and lowest to reduce extreme outliers
    sorted_4w = sorted(forecasts_4w)
    trimmed_4w = sorted_4w[1:-1]  # Remove min and max
    final_forecast_4w = sum(trimmed_4w) / len(trimmed_4w)

    return {
        "forecast_4w": final_forecast_4w,
        "forecast_8w": final_forecast_8w,
        "method_forecasts": {m["method"]: m["forecast_4w"] for m in methods},
        "confidence_interval": (min(forecasts_4w), max(forecasts_4w))
    }
```

**Example aggregation:**
```
Method forecasts for SKU-100:

ETS:                45 units
LightGBM:           42 units
Category-relative:  88 units (outlier — category growing fast)
Anomaly-adjusted:  112 units
Multi-scale lag:   124 units
Calendar events:    98 units

Arithmetic mean:     84.8 units
Median:              93.0 units (more robust)
Trimmed mean:        96.0 units (removes outliers: 42, 88)

Choose MEDIAN = 93 units as final forecast
Confidence band = [42, 124] (methods disagree significantly)
```

**Note on discrepancies:**
- Wide confidence band (42-124) signals uncertainty
- Methods disagree because they emphasize different aspects
- This is GOOD — it signals where to investigate
- Next phase (real data testing): learn which methods matter most for THIS product type

---

## PHASE 1 IMPLEMENTATION ROADMAP

### PHASE 1A: DATA INGESTION & CLEANING (Week 1)

**Deliverable:** Ingest function that loads sales data and produces clean weekly demand signals

**What it does:**
- Reads raw sales data: date, sku_id, units_sold, units_returned
- Creates aggregated weekly demand per SKU
- Flags weeks with inventory issues (using snapshots you provide)
- Outputs: clean_sales_weekly with [sku_id, week_ending, units_sold_net, flags]

**Code structure:**
```
backend/forecast_engine/
├── ingestion.py           ← reads raw data, validates
├── cleaning.py            ← flags anomalies, inventory issues
└── data_models.py         ← TypedDict for clean data
```

---

### PHASE 1B: CALENDAR & SEASONAL DATA (Week 1)

**Deliverable:** Romanian calendar features, seasonal indices per product type

**What it does:**
- Hardcode Orthodox Easter dates (varies yearly)
- Mark major holidays: Christmas, Black Friday, March 8, 1 Decembrie
- Create salary cycle feature (10th, 25th of month)
- Build construction season flag (April-Sept for furniture)
- Compute seasonal indices from historical data (once we have it)

**Code structure:**
```
backend/forecast_engine/
├── calendar.py            ← Orthodox Easter, holidays, salary cycles
├── seasonality.py         ← compute seasonal indices per week
└── config.py              ← hardcoded event multipliers
```

---

### PHASE 1C: IMPLEMENT METHOD 1 — ETS (Week 2)

**Deliverable:** ETS forecaster that produces forecast + confidence interval for each SKU

**What it does:**
- Takes 52 weeks of clean demand per SKU
- Fits Holt-Winters model
- Produces 4-week + 8-week forecast
- Returns confidence intervals, seasonal indices, trend

**Code structure:**
```
backend/forecast_engine/methods/
├── ets_model.py
│   └── class ETSForecaster:
│       └── def forecast(sku_sales: Series) -> ETSResult
```

---

### PHASE 1D: IMPLEMENT METHOD 2 — LightGBM (Week 2)

**Deliverable:** LightGBM model that trains on all SKUs, predicts for each

**What it does:**
- Feature engineering (lags, calendar, category aggregates, product features)
- Train global LightGBM on all SKUs × weeks
- Predict for each SKU's next 4 and 8 weeks
- Return feature importance (explainability)

**Code structure:**
```
backend/forecast_engine/methods/
├── lgbm_model.py
│   ├── def engineer_features(sales_df) -> DataFrame
│   ├── class LGBMForecaster:
│   │   ├── def train(training_data)
│   │   └── def forecast(sku_features) -> LGBMResult
```

---

### PHASE 1E: IMPLEMENT METHOD 3 — Category-Relative (Week 2)

**Deliverable:** Category-driven forecast using aggregates and SKU share

**What it does:**
- Aggregate category-level sales
- Calculate YoY ratio for entire category
- Determine SKU's share of category
- Forecast: category_forecast × sku_share

**Code structure:**
```
backend/forecast_engine/methods/
├── category_relative.py
│   ├── def aggregate_category(sales_df)
│   ├── def calculate_sku_share(sku_sales, category_sales)
│   ├── class CategoryRelativeForecaster:
│   │   └── def forecast() -> CategoryRelativeResult
```

---

### PHASE 1F: IMPLEMENT METHOD 4 — Anomaly-Adjusted (Week 2)

**Deliverable:** Robust baseline forecast with anomaly detection

**What it does:**
- Identify promotional spikes and outliers
- Remove from baseline calculation
- Calculate clean baseline (median)
- Project with recent growth rate

**Code structure:**
```
backend/forecast_engine/methods/
├── anomaly_adjusted.py
│   ├── def detect_anomalies(sales_series)
│   ├── def calculate_clean_baseline(sales_series)
│   ├── class AnomalyAdjustedForecaster:
│   │   └── def forecast() -> AnomalyResult
```

---

### PHASE 1G: IMPLEMENT METHOD 5 — Multi-Scale Lag (Week 3)

**Deliverable:** Temporal momentum analysis across 5 lag windows

**What it does:**
- Calculate rolling averages at 1w, 4w, 13w, 26w, 52w
- Compute momentum ratios
- Detect trend consistency
- Weighted forecast combining all lags

**Code structure:**
```
backend/forecast_engine/methods/
├── multi_scale_lag.py
│   ├── def calculate_lags(sales_series)
│   ├── def calculate_momentum_ratios(lags)
│   ├── class MultiScaleLagForecaster:
│   │   └── def forecast() -> MultiScaleLagResult
```

---

### PHASE 1H: IMPLEMENT METHOD 6 — Calendar Events (Week 3)

**Deliverable:** Seasonal + event-based forecast using Romanian calendar

**What it does:**
- Compute seasonal index per week-of-year
- Apply event multipliers (Easter, Black Friday, etc.)
- Identify current season (construction, summer lull)
- Calculate event-adjusted forecast

**Code structure:**
```
backend/forecast_engine/methods/
├── calendar_events.py
│   ├── def compute_seasonal_indices(sales_df)
│   ├── def apply_event_multipliers(base_demand, week_num)
│   ├── class CalendarEventsForecaster:
│   │   └── def forecast() -> CalendarResult
```

---

### PHASE 1I: AGGREGATION ENGINE (Week 3)

**Deliverable:** Combines 6 methods into unified forecast (no weights)

**What it does:**
- Collects outputs from all 6 methods
- Aggregates via median / trimmed mean
- Produces confidence interval
- Returns method-by-method breakdown for transparency

**Code structure:**
```
backend/forecast_engine/
├── aggregation.py
│   ├── def aggregate_equal_weight(method_results: List[dict]) -> dict
│   ├── def aggregate_median(method_results: List[dict]) -> dict
│   ├── def aggregate_trimmed_mean(method_results: List[dict]) -> dict
│   ├── class EnsembleForecaster:
│   │   └── def produce_final_forecast() -> EnsembleForecastResult
```

**Output format:**
```python
{
    "sku_id": "SKU-100",
    "sku_name": "Canapea Coltar Gri 3 locuri",
    "forecast_4w": 93,
    "forecast_8w": 186,
    "confidence_low_4w": 42,
    "confidence_high_4w": 124,
    "method_breakdown": {
        "ets": {"forecast_4w": 45, "confidence": (38, 52)},
        "lightgbm": {"forecast_4w": 42, "confidence": (35, 49)},
        "category_relative": {"forecast_4w": 88, "confidence": (75, 101)},
        "anomaly_adjusted": {"forecast_4w": 112, "confidence": (95, 129)},
        "multi_scale_lag": {"forecast_4w": 124, "confidence": (110, 138)},
        "calendar_events": {"forecast_4w": 98, "confidence": (85, 111)},
    },
    "method_disagreement_level": "MEDIUM",  # std dev of forecasts
    "aggregation_method": "median",
    "generated_at": "2026-04-06T10:30:00Z"
}
```

---

### PHASE 1J: API ENDPOINTS (Week 4)

**Deliverable:** FastAPI endpoints to serve forecasts

**Endpoints:**

```
GET /api/forecast/sku/{sku_id}
  → Single SKU forecast (all 6 methods + ensemble)

GET /api/forecast/category/{category_id}
  → All SKUs in category with forecasts

POST /api/forecast/refresh
  → Retrain all models (run weekly)

GET /api/forecast/method/{method_name}/comparison
  → Compare one method across all SKUs
```

---

### PHASE 1K: ACCURACY MEASUREMENT FRAMEWORK (Week 4)

**Deliverable:** Backtesting harness (for later use with real data)

**What it does:**
- Walk-forward validation (train on past, test on future)
- Calculates WMAPE, hit rate ±20%, bias for each method
- Logs accuracy over time
- Enables comparison: basic prediction vs. each method vs. ensemble

**Code structure:**
```
backend/forecast_engine/
├── backtest.py
│   ├── def walk_forward_validation(sales_df, n_folds)
│   ├── def calculate_wmape(forecast, actual)
│   ├── def calculate_hit_rate(forecast, actual, tolerance=0.20)
│   ├── def calculate_bias(forecast, actual)
│   ├── class BacktestRunner:
│   │   └── def run_full_backtest() -> BacktestReport
```

**Output (once real data available):**
```
Backtest Report:

Method                 WMAPE    Hit@±20%   Bias
─────────────────────────────────────────────────
Basic prediction       28%      45%        +3%
ETS                    16%      68%        -1%
LightGBM               14%      72%        +0.5%
Category-relative      18%      65%        -2%
Anomaly-adjusted       14%      71%        -0.2%
Multi-scale lag        15%      69%        +1%
Calendar events        12%      74%        +0.1%
─────────────────────────────────────────────────
Ensemble (median)      11%      78%        -0.3%
```

---

### PHASE 1L: UNIT TESTS (Ongoing)

**Deliverable:** Comprehensive test suite for all 6 methods

**Tests:**
```
backend/forecast_engine/tests/
├── test_ets_model.py
├── test_lgbm_model.py
├── test_category_relative.py
├── test_anomaly_adjusted.py
├── test_multi_scale_lag.py
├── test_calendar_events.py
├── test_aggregation.py
├── test_backtest.py
```

Each test:
- Validates calculation correctness (unit tests)
- Checks output format (schema tests)
- Verifies edge cases (empty data, single week, etc.)

---

## DATA REQUIREMENTS (FOR WHEN YOU HAVE REAL DATA)

**Minimum:**
```
sales_data: [date, sku_id, store_id, units_sold, units_returned]
skus: [sku_id, sku_name, category_id, subcategory_id, purchase_cost, retail_price]
categories: [category_id, category_name]
```

**Preferred (for accuracy):**
```
inventory_snapshots: [date, sku_id, store_id, quantity_on_hand]
promotions: [date_from, date_to, sku_id, discount_pct]
product_lifecycle: [sku_id, launch_date, discontinuation_date]
```

---

## WHY THIS APPROACH

### **Why 6 separate methods?**

1. **Each answers a different question**
   - ETS: "What's the statistical pattern?"
   - LightGBM: "What do similar products tell us?"
   - Category-relative: "How is the market?"
   - Anomaly-adjusted: "What's the true baseline?"
   - Multi-scale lag: "What's the momentum?"
   - Calendar: "What do events predict?"

2. **No single approach is universally best**
   - Seasonal products → ETS dominates
   - New products → LightGBM dominates
   - Growing categories → Category-relative dominates
   - Volatile products → Anomaly-adjusted dominates
   - Trending products → Multi-scale lag dominates
   - Event-driven products → Calendar dominates

3. **Disagreement signals opportunity**
   - Wide confidence band = something complex is happening
   - Methods disagreeing = worth investigating
   - Disagreement isn't noise, it's information

### **Why no weights yet?**

1. **Premature optimization** — We don't know which method matters until we test on real data
2. **Data-driven learning** — Real data will show which methods work for which product types
3. **Flexibility** — Starting with equal weight allows pivoting based on results
4. **Transparency** — Stakeholders see all methods, not hidden weights

### **Why combine at all?**

1. **Variance reduction** — Six estimates average out noise better than one
2. **Robustness** — If one method fails (e.g., new product, no history), others continue
3. **Explainability** — Method disagreement explains uncertainty
4. **Continuous improvement** — Real data will show which methods to prioritize

---

## AI PLACEMENT IN THE SYSTEM

### **Not for forecast generation**

We do NOT use AI (LLM) for generating forecasts because:

1. **Transparency required** — Buyers need to trust the numbers. "Claude said 95 units" is less trustworthy than "ETS+LightGBM ensemble = 95 units"
2. **Reproducibility** — Statistical + ML models are deterministic. LLMs are not.
3. **Explainability limits** — LLMs can't easily explain "here's why I forecast exactly 95, not 94"
4. **Unnecessary complexity** — We have models designed for this (ETS, LightGBM, etc.)

### **YES for decision support layer**

AI is valuable AFTER forecasting, in the decision layer:

**1. Forecast explanation**
```
"Why did we forecast 95 units instead of 80?"
→ LLM explains: "ETS saw weekly growth (+8%), calendar events (Easter)
   predict spike, category trend is +11% YoY, but multi-scale lag suggests
   stabilization. Ensemble averaged to 95."
```

**2. Anomaly flagging**
```
"ETS forecast 45, but category-relative forecast 88. That's a big gap."
→ LLM analyzes: "Category-relative assumes SKU will grow with category (+11%),
   but ETS sees local decline. This SKU may be underperforming.
   Recommend manual review."
```

**3. Override reasoning**
```
Buyer overrides forecast from 95 → 110, reason: "Easter inventory arrived late"
→ LLM ingests: "Late inventory is a demand constraint, not lack of demand.
   This override signals pent-up demand. Future Easter weeks should forecast higher."
```

**4. Decision support**
```
Queue item: "Approve order of 95 units?"
→ LLM suggests: "Risk: low (confidence 88-102). Benefit: avoids 1.2M lei
   over-order risk vs. basic prediction. Recommend: APPROVE"
```

### **Why not AI for forecasting, but YES for decisions?**

- Forecasting requires precision and reproducibility → use statistical/ML models
- Decision support requires context, explanation, nuance → use LLM for communication
- LLM strength: synthesizing information for human decision-makers
- LLM weakness: producing deterministic numerical predictions

---

## NEXT STEPS

1. **Approve this plan** — confirm 6 methods, aggregation approach, AI placement
2. **Finalize data schema** — once you have real data, validate the ingestion format
3. **Begin Phase 1A** — implement data ingestion and cleaning (Week 1)
4. **Build methods in sequence** — 1B → 1J over 4 weeks
5. **Backtest on real data** — once available, run Phase 1K to find true weights
6. **Iterate** — adjust method weights, remove ineffective approaches, refine

---

## SUMMARY TABLE

| Method | Foundation | Best For | Worst For | Complexity |
|--------|-----------|----------|-----------|------------|
| **ETS** | Statistical decomposition | Seasonal, stable products | New products, structural breaks | Medium |
| **LightGBM** | ML gradient boosting | New products, complex patterns, cross-SKU | Black box, requires large dataset | High |
| **Category-relative** | Market context + share | Growing markets, relative performance | Niche products, category disruption | Low |
| **Anomaly-adjusted** | Robust baseline + growth | Promotional products, outlier removal | Assumes past patterns | Low-Medium |
| **Multi-scale lag** | Temporal momentum | Trending products, momentum detection | Backward-looking, misses events | Low |
| **Calendar events** | Seasonal + Romanian calendar | Event-driven, seasonal, holiday products | Anomalies, new events | Low-Medium |
| **Ensemble** | All methods combined | All products, broad accuracy | No specialization | N/A |

---

## RISK MITIGATION

| Risk | Mitigation |
|------|-----------|
| Real data is messier than expected | Multiple methods handle different data quality issues |
| One method fails on specific product type | 5 others provide fallback forecasts |
| Aggregation averages out good signals | Confidence band shows method disagreement; weights will be tuned on real data |
| Overfitting to historical patterns | Walk-forward validation prevents this |
| Methods become outdated | Continuous backtesting re-ranks methods |

---

**Ready to start Phase 1A. Awaiting approval.**
