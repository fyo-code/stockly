# FORECAST ENGINE BLUEPRINT
*Technical specification — every formula, every step, every decision*
*April 2026*

---

## 0. Overview

This document is the complete technical specification for the demand prediction engine. It covers every data transformation, every formula, every model configuration, and every output field. Nothing is left abstract. An engineer reading this can implement it without asking questions.

**What the engine does:**
Takes raw sales history → produces per-SKU demand forecasts with confidence intervals, recommended order quantities, and financial impact vs the current basic prediction method.

**What it does not do:**
Make autonomous decisions. It produces recommendations. Buyers approve, skip, or override. Those decisions are logged and become future training data.

---

## 1. Data Inputs

### 1.1 Required inputs (Tier 1)

**Sales transactions**
```
Column          Type        Notes
────────────────────────────────────────────────────────────
date            DATE        Daily granularity. Format: YYYY-MM-DD
store_id        STRING      Store identifier
sku_id          STRING      Product identifier — must match catalog
units_sold      INTEGER     Gross units sold (before returns)
units_returned  INTEGER     Returns in same period. Null = 0.
revenue_lei     FLOAT       Gross revenue. Used for financial calculations.
```
Required history: minimum 104 weeks (2 years). 156 weeks (3 years) ideal.

**Product catalog**
```
Column              Type        Notes
────────────────────────────────────────────────────────────
sku_id              STRING      Primary key
sku_name            STRING
department          STRING      Top-level hierarchy (e.g. "Living Room")
category            STRING      Mid-level (e.g. "Sofas")
subcategory         STRING      Lowest level (e.g. "Corner Sofas")
purchase_cost_lei   FLOAT       Unit cost from supplier
retail_price_lei    FLOAT       Standard retail selling price
supplier_id         STRING      Links to supplier table
launch_date         DATE        When this SKU was first available
is_discontinued     BOOLEAN     True = stop forecasting, forecast = 0
```

**Inventory snapshots**
```
Column          Type        Notes
────────────────────────────────────────────────────────────
snapshot_date   DATE        End-of-week date (Sunday)
store_id        STRING
sku_id          STRING
qty_on_hand     INTEGER     Physical stock count at that moment
```
Required for censored demand detection. Weekly snapshots minimum.

### 1.2 Optional inputs (Tier 2 — adds accuracy)

**Promotions**
```
Column          Type        Notes
────────────────────────────────────────────────────────────
sku_id          STRING
promo_start     DATE
promo_end       DATE
discount_pct    FLOAT       0.0–1.0 (e.g. 0.40 = 40% off)
promo_type      STRING      SEASONAL / CLEARANCE / BLACK_FRIDAY / OTHER
```

**Supplier lead times**
```
Column                  Type        Notes
────────────────────────────────────────────────────────────
supplier_id             STRING
sku_id                  STRING      Optional — falls back to supplier default
avg_lead_time_weeks     FLOAT       Actual average (from delivery history)
contractual_lead_weeks  FLOAT       What was promised
```

---

## 2. Data Processing Pipeline

### 2.1 Step 1 — Ingestion and validation

On every new data load, before anything else:

```
VALIDATION RULES:
1. All required columns exist with correct types
2. No future dates in sales data (date <= today)
3. units_sold >= 0 for all rows (no negative gross sales)
4. units_returned >= 0 and units_returned <= units_sold for same date/store/sku
5. Every sku_id in sales exists in product catalog — log and skip mismatches
6. Date coverage: flag if any sku_id has > 4 consecutive missing weeks (possible data export gap)
7. Duplicate check: (date, store_id, sku_id) must be unique — aggregate duplicates, log warning
```

Output: cleaned raw tables in PostgreSQL. Validation errors logged to `ingestion_log` table with timestamp, error type, row count.

---

### 2.2 Step 2 — Aggregation to weekly series

Transform daily rows × multiple stores into one weekly time series per SKU.

**Week definition:** ISO week. Week ending = Sunday. All dates mapped to their Sunday.

```
net_sold_per_row = max(0, units_sold - units_returned)

GROUP BY:
  week_ending = date_trunc('week', date) + interval '6 days'  [maps to Sunday]
  sku_id

AGGREGATE:
  weekly_units_sold     = SUM(units_sold)
  weekly_units_returned = SUM(units_returned)
  weekly_net_sold       = SUM(net_sold_per_row)   ← this is the target variable
  weekly_revenue_lei    = SUM(revenue_lei)
  stores_active         = COUNT(DISTINCT store_id) [how many stores had any sales]
```

Result: one row per (week_ending, sku_id). This is the base time series.

Missing weeks (a SKU had zero sales in a week): insert explicitly with weekly_net_sold = 0. Do not leave gaps. Missing rows cause lag features to calculate incorrectly.

---

### 2.3 Step 3 — Censored demand detection and correction

A week with zero sales could mean: no demand existed, OR stock ran out and demand was invisible.

**Detection:**

For each (week_ending, sku_id) row:

```
1. Check inventory snapshot for that week:
   IF qty_on_hand IS NULL:
     use heuristic (see below)
   ELIF qty_on_hand = 0:
     status = CENSORED
   ELIF qty_on_hand < (rolling_4w_avg × 0.5) AND weekly_net_sold = 0:
     status = CENSORED
   ELIF qty_on_hand < (rolling_4w_avg × 0.25):
     status = PARTIALLY_CENSORED  [partial stock — demand may be understated]
   ELSE:
     status = NORMAL

   Heuristic (no inventory data):
     IF weekly_net_sold = 0
     AND rolling_4w_avg > 1.5           [product normally sells]
     AND prior_week_net_sold = 0        [consecutive zero weeks]
       status = LIKELY_CENSORED         [flagged but not corrected — insufficient evidence]
     ELSE:
       status = NORMAL
```

**Correction for CENSORED weeks:**

Replace `weekly_net_sold` with an imputed value:

```
rolling_4w_avg_before_stockout = MEAN of the last 4 non-CENSORED weeks before this week
  (look backward until 4 clean weeks are found, max lookback = 13 weeks)

IF rolling_4w_avg_before_stockout IS NOT NULL:
  imputed_demand = rolling_4w_avg_before_stockout
ELSE:
  imputed_demand = category_weekly_avg_for_this_week_of_year
  [fallback: use category pattern when no recent history]

weekly_net_sold_clean = ROUND(imputed_demand)
censored_flag = TRUE
```

PARTIALLY_CENSORED weeks: do not replace, keep original value, set flag. The model will learn to treat partial censoring with lower confidence.

LIKELY_CENSORED weeks: keep original value but flag. Do not auto-correct without inventory evidence.

---

### 2.4 Step 4 — Promotional spike detection

Identifies weeks where demand was inflated by a discount event, not organic.

**Detection:**

```
rolling_13w_median = MEDIAN of weekly_net_sold_clean for the 13 weeks before this week
  [using median not mean — robust to earlier spikes corrupting the baseline]

spike_threshold = rolling_13w_median × 2.5
  [2.5x median is promotional territory. Below this = normal variance.]

IF weekly_net_sold_clean > spike_threshold:
  promotional_flag = TRUE
ELIF promo table is available AND this week has active_discount_pct > 0.15:
  promotional_flag = TRUE   [> 15% discount is considered a promotion]
ELSE:
  promotional_flag = FALSE
```

**What happens to promotional weeks:**

For training purposes: exclude from main model training. Promotional demand is structurally different — the model should not learn "demand is 5x normal" as a pattern that will repeat.

They are not deleted. They are stored with `is_promotional = TRUE`. A separate promotion lift model can be built later to quantify: "for a 40% discount in the Sofas category, demand lifts by 3.2x on average." For now, the conservative approach is exclusion.

---

### 2.5 Step 5 — Product lifecycle classification

Every SKU gets a lifecycle tag. Models differ per lifecycle.

```
product_age_weeks = (current_date - launch_date) / 7

Compute recent_trend_slope:
  x = [0, 1, 2, ..., 12]
  y = weekly_net_sold_clean for last 13 non-censored, non-promotional weeks
  slope, intercept = linregress(x, y)
  trend_pct_per_week = slope / mean(y)  [slope as % of average — normalised]

LIFECYCLE CLASSIFICATION:
  IF is_discontinued = TRUE:
    lifecycle = EOL

  ELIF product_age_weeks < 26:
    lifecycle = NEW

  ELIF product_age_weeks < 78 AND trend_pct_per_week > 0.02:
    lifecycle = GROWING     [< 18 months old AND growing > 2%/week]

  ELIF trend_pct_per_week < -0.03 AND this condition holds for >= 3 consecutive months:
    lifecycle = DECLINING   [declining > 3%/week for 3+ months]

  ELSE:
    lifecycle = MATURE       [default for established, stable products]
```

---

## 3. Feature Engineering

This runs after cleaning. For each (week_ending, sku_id) row in the training window, compute all features below. The result is a flat table where each row = one SKU × one week, with all features + the target (weekly_net_sold_clean).

### 3.1 Lag features

```
lag_1w   = weekly_net_sold_clean at (week_ending - 1 week)
lag_2w   = weekly_net_sold_clean at (week_ending - 2 weeks)
lag_4w   = weekly_net_sold_clean at (week_ending - 4 weeks)
lag_8w   = weekly_net_sold_clean at (week_ending - 8 weeks)
lag_13w  = weekly_net_sold_clean at (week_ending - 13 weeks)
lag_26w  = weekly_net_sold_clean at (week_ending - 26 weeks)
lag_52w  = weekly_net_sold_clean at (week_ending - 52 weeks)
lag_104w = weekly_net_sold_clean at (week_ending - 104 weeks)  [if 2+ years of data]

NULL handling: if the lag week doesn't exist (beginning of history), set to 0.
This is preferable to dropping rows — the model learns that 0 = "no history available".
```

### 3.2 Rolling statistics

```
rolling_mean_4w  = MEAN of weekly_net_sold_clean for weeks [t-1, t-2, t-3, t-4]
rolling_mean_13w = MEAN of weekly_net_sold_clean for weeks [t-1 through t-13]
rolling_mean_26w = MEAN of weekly_net_sold_clean for weeks [t-1 through t-26]
rolling_std_4w   = STDDEV of weekly_net_sold_clean for weeks [t-1, t-2, t-3, t-4]
  [measures volatility — high std = noisy SKU = wider confidence intervals]
rolling_max_13w  = MAX of weekly_net_sold_clean for last 13 weeks
rolling_min_13w  = MIN of weekly_net_sold_clean for last 13 weeks

Important: all rolling calculations exclude CENSORED and PROMOTIONAL weeks.
If fewer than 2 clean weeks available for a window: set to NULL (not 0).
```

### 3.3 Trend and ratio features

```
yoy_ratio = rolling_mean_4w / lag_52w_rolling_4w
  where lag_52w_rolling_4w = MEAN of weekly_net_sold_clean for weeks [t-53, t-54, t-55, t-56]
  [current 4-week average vs same 4-week period exactly one year ago]

yoy_ratio_2y = rolling_mean_4w / lag_104w_rolling_4w   [vs 2 years ago, if available]
  where lag_104w_rolling_4w = MEAN of weekly_net_sold_clean for weeks [t-105, t-106, t-107, t-108]

trend_short = rolling_mean_4w / rolling_mean_13w
  [is the recent 4 weeks running above or below the 13-week medium-term average?]
  [> 1 = recent momentum is up, < 1 = recent momentum is down]

trend_long = rolling_mean_13w / rolling_mean_26w
  [is the medium-term above or below the 6-month baseline?]

NULL/division-by-zero handling for all ratio features:
  IF denominator = 0 OR NULL: set ratio = 1.0  [neutral — no signal]

Outlier capping for all ratio features:
  Clip to range [0.05, 20.0]
  A ratio outside this range is either a data error or a once-in-decade event.
```

### 3.4 Romanian calendar features

Precomputed for every date in the data range. Stored in a lookup table `romanian_calendar`.

```
week_of_year        INTEGER     ISO week number, 1–52
month               INTEGER     1–12
quarter             INTEGER     1–4

is_orthodox_easter  BOOLEAN
  Computed using: Meeus/Jones/Butcher algorithm for Julian Easter,
  then add 13 days to convert to Gregorian calendar.
  Flag the week containing that Sunday.
  Also flag: is_orthodox_easter_minus1w (shopping peak BEFORE Easter)

is_christmas_week   BOOLEAN     week_of_year IN (51, 52)
is_pre_christmas    BOOLEAN     week_of_year IN (48, 49, 50)  [gift-buying ramp]

is_black_friday     BOOLEAN
  Last Friday of November ± 3 days = the Black Friday week.

is_black_friday_plus1  BOOLEAN
  Week after Black Friday. Returns surge + continued sales from late shoppers.

is_march_8_week     BOOLEAN     Week containing March 8.
  [Women's Day — significant gift-buying spike in Romanian retail]

is_1_decembrie_week BOOLEAN     Week containing December 1.
  [Romanian National Day — modest but real retail effect]

is_construction_season  BOOLEAN   month IN (4, 5, 6, 7, 8, 9)
  [April–September. Renovation and new home purchases are concentrated here.
   Furniture sales correlate with construction/moving activity.]

salary_early        BOOLEAN     day_of_month BETWEEN 8 AND 14
salary_late         BOOLEAN     day_of_month BETWEEN 23 AND 29
  [Romanian salaries typically paid ~10th and ~25th of month.
   Consumer purchases spike in the 3-4 days after payment.
   Map the week: if the salary payment day falls in this week, flag it.]

is_summer_lull      BOOLEAN     month IN (7, 8)
  [July–August sees lower discretionary retail in Romanian market]
```

### 3.5 Product features

```
category_id         Categorical     Label-encoded integer
subcategory_id      Categorical     Label-encoded integer
department_id       Categorical     Label-encoded integer

price_segment       Categorical     0 = budget, 1 = mid, 2 = premium
  Computed per category:
    budget  = retail_price_lei < 33rd percentile of category prices
    premium = retail_price_lei > 67th percentile of category prices
    mid     = between 33rd and 67th percentile

log_product_age     FLOAT           log(product_age_weeks + 1)
  [log transform because effect of age is diminishing — week 1 vs 5 matters
   more than week 200 vs 204. Log captures this nonlinearity.]

is_mature           BOOLEAN         product_age_weeks > 78

log_purchase_cost   FLOAT           log(purchase_cost_lei + 1)
  [scale-normalises price — 1000 lei vs 1200 lei matters less
   than 50 lei vs 250 lei]

price_ratio_to_category   FLOAT
  = retail_price_lei / MEDIAN(retail_price_lei) over all SKUs in same category
  [is this SKU cheap or expensive relative to its category peers?]
  Clip to [0.1, 10.0]
```

### 3.6 Category-level features

Computed at category level, then joined to each SKU row. These are what enable cross-SKU learning — a SKU with sparse history benefits from the full category's signal.

```
cat_rolling_mean_4w     FLOAT
  = SUM of rolling_mean_4w across all non-EOL SKUs in same category

cat_lag_52w_rolling_4w  FLOAT
  = SUM of lag_52w_rolling_4w across all non-EOL SKUs in same category

cat_yoy_ratio           FLOAT
  = cat_rolling_mean_4w / cat_lag_52w_rolling_4w
  [is the whole category growing or shrinking vs last year?]
  NULL handling: set to 1.0

cat_trend_short         FLOAT
  = category-level rolling_mean_4w / category-level rolling_mean_13w

cat_seasonal_index      FLOAT
  Computed per (category, week_of_year):
    For each week_of_year w:
      cat_seasonal_index[w] = MEAN(weekly_net_sold for all weeks with this week_of_year)
                              / MEAN(weekly_net_sold across all weeks)
  [> 1 means this week_of_year is historically above average for this category]
  [< 1 means below average]
  This is the key feature for capturing within-year seasonality at category level.

sku_category_share_13w  FLOAT
  = rolling_mean_13w (this SKU) / cat_rolling_mean_13w (all SKUs in category)
  [what fraction of the category does this SKU typically represent?]
  Used in: NEW product forecasting (see Section 5.3)
  NULL/zero denominator: set to 0
```

### 3.7 Promotion features (if promo data available)

```
is_on_promotion         BOOLEAN     active promotion in the promo table for this week
discount_pct            FLOAT       0.0–1.0. Set to 0.0 if not on promotion.
weeks_since_last_promo  INTEGER
  Count of weeks since last is_on_promotion = TRUE.
  Cap at 52. Set to 52 if never promoted.
promo_frequency_52w     FLOAT
  = COUNT of promotional weeks in the last 52 weeks / 52
  [how often does this SKU go on sale? Frequent promo SKUs behave differently.]
```

---

## 4. Models

### 4.1 Model A — ETS (Exponential Smoothing)

**Applies to:** lifecycle = MATURE or GROWING, with >= 52 weeks of clean history.

**Library:** `statsmodels.tsa.holtwinters.ExponentialSmoothing`

**Per-SKU. Runs independently for each qualifying SKU.**

Input: array of `weekly_net_sold_clean` values, in chronological order, CENSORED and PROMOTIONAL weeks already imputed or excluded.

Configuration:
```python
from statsmodels.tsa.holtwinters import ExponentialSmoothing

model = ExponentialSmoothing(
    endog        = weekly_net_sold_array,
    trend        = 'add',      # additive trend
    seasonal     = 'add',      # additive seasonality
    seasonal_periods = 52,     # annual cycle
    damped_trend = True,       # prevents explosive trend extrapolation on short windows
    initialization_method = 'estimated'   # statsmodels estimates optimal init params
)

fit = model.fit(
    optimized    = True,       # auto-optimize alpha, beta, gamma, phi via MLE
    use_brute    = True        # use grid search for initial values before gradient descent
)

forecast_array = fit.forecast(steps=8)  # generate 8 weeks forward
```

**Why additive, not multiplicative:**
Multiplicative seasonality = seasonal effect is proportional to level. For a SKU that averages 3 units/week, multiplicative can produce fractional or zero forecasts in off-season. Additive is safer for low-velocity retail SKUs.

**Why damped trend:**
`damped_trend=True` adds a damping parameter `phi` (0 < phi < 1) that causes the trend to decay toward zero as the horizon lengthens. Without damping, a 2-unit/week uptrend detected from 8 weeks of data extrapolates to +200 units by week 100. Damping makes long-horizon forecasts converge to the recent level rather than exploding.

**Failure handling:**
If ETS optimization fails to converge (common on noisy or very sparse series):
```python
try:
    fit = model.fit(optimized=True)
except:
    # Fallback: naive seasonal forecast
    forecast_array = [
        lag_52w_value_for_week_n * cat_yoy_ratio
        for n in range(1, 9)
    ]
    ets_failed = True
```

---

### 4.2 Model B — LightGBM Global Model

**Applies to:** all SKUs with lifecycle = MATURE or GROWING.

**One model trained across ALL SKUs simultaneously.** Each SKU contributes many training rows (one per week in training window). The model learns patterns that generalise across SKUs — which features predict demand increases, how seasonality differs by category, how price segment affects promotional sensitivity.

**Training dataset:**
- Rows: all (sku_id × week) combinations in the training window
- Exclude: CENSORED weeks (already cleaned), PROMOTIONAL weeks, lifecycle = NEW or EOL
- Features: all features from Section 3
- Target: `weekly_net_sold_clean`

**LightGBM parameters:**
```python
import lightgbm as lgb

params = {
    'objective':        'regression_l1',  # MAE loss — robust to remaining outliers
    'metric':           'mae',
    'num_leaves':       63,               # max leaves per tree. 63 is a good default for tabular retail.
    'learning_rate':    0.05,             # low LR + many trees = better generalisation than high LR + few trees
    'n_estimators':     2000,             # large — early stopping will cut this down
    'min_child_samples': 20,             # min samples per leaf — prevents overfitting on rare patterns
    'feature_fraction': 0.8,             # use 80% of features per tree — reduces overfitting, adds variance
    'bagging_fraction': 0.8,             # use 80% of rows per tree
    'bagging_freq':     5,               # apply bagging every 5 trees
    'reg_alpha':        0.1,             # L1 regularisation
    'reg_lambda':       0.1,             # L2 regularisation
    'verbose':         -1                # silent
}
```

**Train/validation split:**
```
Training set:  all rows where week_ending < cutoff_date - 8 weeks
Validation set: all rows where week_ending >= cutoff_date - 8 weeks
                AND week_ending < cutoff_date

IMPORTANT: this is a time-based split, not random.
Never shuffle and split randomly for time series.
Doing so leaks future information into training.

Early stopping: stop when validation MAE stops improving for 50 consecutive rounds.
```

**Generating forecasts:**

LightGBM cannot natively roll forecasts forward. To forecast week t+1, you need lag_1w = actual sales at week t. But you don't have that at prediction time.

Solution — recursive forecasting:
```
week t   = last known actual week
week t+1 = model(features built using actual data up to t)
week t+2 = model(features built using actual data up to t, and forecast for t+1)
week t+3 = model(features built using actual data up to t, and forecasts for t+1, t+2)
...up to t+8

At each step, lag features that reference future weeks use the previously generated forecast.
lag_52w and other long-range lags remain actual historical values throughout.
```

This causes error accumulation in short lags (lag_1w, lag_2w) for longer horizons. This is expected and is why confidence intervals widen with horizon length.

---

### 4.3 NEW Product Model

**Applies to:** lifecycle = NEW (product_age_weeks < 26)

Not enough history to run ETS or LightGBM reliably. Use a rule-based approach that borrows from the category.

```
Step 1: Define the sibling group
  sibling_skus = all SKUs where:
    subcategory = this SKU's subcategory
    AND price_segment = this SKU's price_segment
    AND lifecycle = MATURE
    AND product_age_weeks > 78

Step 2: Compute sibling seasonal curve
  For each week_of_year w (1–52):
    sibling_vals_for_w = [net_sold for all weeks_of_year=w across all sibling SKUs]
    sibling_seasonal_index[w] = MEAN(sibling_vals_for_w) / MEAN(all sibling_vals)

Step 3: Compute new SKU's recent baseline
  recent_clean_weeks = last 4 weeks where:
    weekly_net_sold > 0 AND is_censored = FALSE AND is_promotional = FALSE

  IF COUNT(recent_clean_weeks) >= 2:
    baseline = MEAN(weekly_net_sold for recent_clean_weeks)
  ELSE:
    baseline = cat_rolling_mean_4w × sku_typical_category_share
    [if product is so new it barely has 2 weeks of clean data,
     fall back to category-based estimate]

Step 4: Apply ramp multiplier
  IF product_age_weeks < 8:
    ramp_factor = 0.60   [very new — still building awareness]
  ELIF product_age_weeks < 13:
    ramp_factor = 0.75
  ELIF product_age_weeks < 20:
    ramp_factor = 0.90
  ELSE:
    ramp_factor = 1.00   [approaching 26 weeks — nearly graduated to main model]

Step 5: Generate forecast
  forecast[week_n] = baseline × sibling_seasonal_index[week_of_year(week_n)] × ramp_factor
```

---

### 4.4 DECLINING Product Model

**Applies to:** lifecycle = DECLINING (not yet EOL)

```
Step 1: Compute decline rate
  y = weekly_net_sold_clean for last 13 non-censored, non-promotional weeks
  x = [0, 1, 2, ..., 12]
  slope, intercept = linregress(x, y)

  avg_weekly = MEAN(y)
  weekly_decline_rate = slope / avg_weekly   [negative number, e.g. -0.06 = -6%/week]

  Cap: IF weekly_decline_rate < -0.12:
    weekly_decline_rate = -0.12   [max 12% decline per week]
    [prevent forecast from hitting zero in 2-3 weeks on short-term noise]

Step 2: Generate forecast
  last_known_weekly = rolling_mean_4w  [smoothed recent level]

  FOR n in 1..8:
    forecast[n] = max(0, last_known_weekly × (1 + weekly_decline_rate) ^ n)
    [exponential decay — each week compounds the decline]
```

---

### 4.5 EOL Product Model

```
forecast[n] = 0  for all n

is_discontinued_flag = TRUE
Suppress from order recommendations entirely.
Flag existing stock as candidate for dead stock review.
```

---

## 5. Ensemble

Combines ETS and LightGBM forecasts into a final weighted forecast.

### 5.1 Compute per-SKU accuracy weights

Run after backtesting (Section 7). For each SKU:

```
wmape_ets[sku]   = backtested WMAPE for ETS on this SKU
wmape_lgbm[sku]  = backtested WMAPE for LightGBM on this SKU

CASE 1: Both models available
  weight_ets[sku]  = wmape_lgbm / (wmape_ets + wmape_lgbm)
  weight_lgbm[sku] = wmape_ets  / (wmape_ets + wmape_lgbm)
  [better model = lower WMAPE = higher weight, because you divide by the OTHER's error]

CASE 2: ETS failed for this SKU
  weight_ets[sku]  = 0.0
  weight_lgbm[sku] = 1.0

CASE 3: < 52 weeks of history (ETS and LightGBM both unreliable)
  Use NEW product model output. No ensemble.

CASE 4: No backtesting data yet (first run)
  weight_ets[sku]  = 0.35
  weight_lgbm[sku] = 0.65
  [LightGBM default slightly higher — it handles cold-start better]
```

### 5.2 Final forecast

```
FOR each week n in 1..8:
  ensemble_forecast[sku][n] =
    (weight_ets[sku] × ets_forecast[sku][n])
    + (weight_lgbm[sku] × lgbm_forecast[sku][n])

  ensemble_forecast[sku][n] = max(0, ROUND(ensemble_forecast[sku][n]))
```

### 5.3 Category-level reconciliation

After all SKU forecasts are generated, check consistency within categories.

```
FOR each category:
  sum_sku_forecasts = SUM(ensemble_forecast[sku][1..4]) for all SKUs in category
  cat_ets_forecast  = ETS forecast on the CATEGORY total time series (run separately)

  reconciliation_ratio = cat_ets_forecast / sum_sku_forecasts

  IF 0.80 <= reconciliation_ratio <= 1.20:
    Apply proportional correction:
    FOR each SKU in category:
      adjusted = ensemble_forecast[sku] × reconciliation_ratio^0.3
      [^0.3 = partial correction. Don't fully force SKUs to match category.
       Just nudge them. Full forcing (^1.0) destroys individual SKU signals.]

  ELIF reconciliation_ratio < 0.80 OR reconciliation_ratio > 1.20:
    DO NOT auto-correct.
    Set reconciliation_flag = 'REVIEW_REQUIRED' on all SKUs in this category.
    [Large discrepancy = something is wrong. Flag for manual review rather than silently adjusting.]
```

---

## 6. Bias Correction

After backtesting, detect and correct systematic over/under-forecasting per category.

### 6.1 Compute bias per category

```
FOR each category:
  All (forecast, actual) pairs from backtesting for this category:

  bias_pct = MEAN(forecast - actual) / MEAN(actual) × 100

  Examples:
    bias_pct = +14% → model systematically over-forecasts Sofas by 14%
    bias_pct = -8%  → model systematically under-forecasts by 8%

Apply correction IF abs(bias_pct) > 5%:
  bias_correction_factor[category] = 1 - (bias_pct / 100)
  [if over by 14%: factor = 0.86 → multiply all forecasts by 0.86]

Store in: bias_corrections table with category, factor, computed_at
```

### 6.2 Apply correction at forecast time

```
corrected_forecast[sku][n] = ensemble_forecast[sku][n] × bias_correction_factor[category(sku)]
bias_correction_applied = TRUE  [flag in output]
```

---

## 7. Backtesting Framework

This is the proof mechanism. All accuracy claims come from here.

### 7.1 Walk-forward cross-validation

```
full_training_data: weeks 1 through T

Parameters:
  min_training_window = 52 weeks   [need at least 1 year to train]
  fold_step = 8 weeks              [advance 8 weeks per fold]
  forecast_horizon = 4 weeks       [predict 4 weeks ahead per fold]

Generate folds:
  cutoff = week 52
  WHILE cutoff + 4 <= T:
    train_set = all rows where week_ending <= cutoff
    test_set  = all rows where week_ending IN [cutoff+1, cutoff+2, cutoff+3, cutoff+4]

    folds.append((train_set, test_set, cutoff))
    cutoff += fold_step

For each fold:
  1. Retrain ETS on each qualifying SKU using train_set only
  2. Retrain LightGBM on all qualifying SKUs using train_set only
  3. Generate forecasts for test_set weeks
  4. Compare forecasts to actual weekly_net_sold_clean
  5. Store: (sku_id, fold_id, week_ending, forecast, actual)
```

### 7.2 Accuracy metrics

**WMAPE — primary metric (reported per SKU, per category, overall)**
```
For a set of (forecast_i, actual_i) pairs:

  WMAPE = SUM(|forecast_i - actual_i|) / SUM(actual_i) × 100%

  [Weighted by volume. A 50% miss on a SKU selling 2/week contributes
   the same as a 0.8% miss on a SKU selling 120/week. This is correct —
   the high-volume SKU matters more to the business.]

Exclude weeks where actual_i = 0 AND forecast_i = 0 (trivially correct, inflates accuracy)
```

**Bias**
```
bias_pct = MEAN(forecast_i - actual_i) / MEAN(actual_i) × 100%

Positive = over-forecasting (will lead to over-ordering)
Negative = under-forecasting (will lead to stockouts)

Target: |bias_pct| < 5% overall
```

**Hit rates**
```
for threshold in [0.10, 0.20, 0.30]:
  pct_error_i = |forecast_i - actual_i| / actual_i
  hit_rate[threshold] = COUNT(pct_error_i <= threshold) / COUNT(all) × 100%

Reported as: "73% of SKUs within ±20% of actual"
```

**Tracking signal (detects drift per SKU)**
```
For each SKU, over the last 6 backtesting folds:
  cumulative_error = SUM(forecast_i - actual_i)    [signed — tracks direction]
  MAD = MEAN(|forecast_i - actual_i|)               [mean absolute deviation]

  tracking_signal = cumulative_error / MAD

  IF |tracking_signal| > 4:
    model_drift_flag = TRUE for this SKU
    [The model is consistently wrong in the same direction. Retrain or investigate.]
```

---

## 8. Confidence Intervals

**Method: bootstrapped residuals from backtesting**

```
For each SKU:
  residuals = [forecast_i - actual_i for all backtesting pairs]
  residuals_pct = residuals / actual_i   [as percentage of actual]

  residuals_std = STDDEV(residuals_pct)

Confidence interval at horizon h:
  horizon_scaling = sqrt(h)
  [uncertainty grows with horizon — proportional to square root of weeks ahead]

  z_80 = 1.28   [80% confidence interval]
  z_90 = 1.645  [90% confidence interval]

  ci_low_4w  = forecast_4w × max(0, 1 - z_80 × residuals_std × sqrt(4))
  ci_high_4w = forecast_4w × (1 + z_80 × residuals_std × sqrt(4))

  ci_low_8w  = forecast_8w × max(0, 1 - z_90 × residuals_std × sqrt(8))
  ci_high_8w = forecast_8w × (1 + z_90 × residuals_std × sqrt(8))

If not enough backtesting history for this SKU:
  use category-average residuals_std
```

---

## 9. Order Recommendation

From forecast, compute the recommended order quantity for the buyer to review.

```
Inputs:
  forecast_lead_time   = ensemble_forecast for weeks 1 through lead_time_weeks
  forecast_safety      = ensemble_forecast for weeks 1 through (lead_time_weeks + 1)
  current_stock        = qty_on_hand from latest inventory snapshot
  on_order_qty         = quantity already ordered but not yet received (if available, else 0)
  lead_time_weeks      = supplier avg_lead_time_weeks (default: 4 if no supplier data)

Calculations:
  projected_demand_lead_time = SUM(forecast[week 1 through lead_time_weeks])
  projected_demand_safety    = SUM(forecast[week 1 through lead_time_weeks + 1])

  recommended_order_qty = max(0, projected_demand_safety - current_stock - on_order_qty)
  recommended_order_qty = CEIL(recommended_order_qty)  [always round up — avoid undershooting]

  current_stock_weeks = current_stock / rolling_mean_4w
    [how many weeks of stock do we have at current run rate?]

Urgency classification:
  IF current_stock < projected_demand_lead_time:
    urgency = CRITICAL    [will stock out before new order can arrive]
  ELIF current_stock < projected_demand_safety:
    urgency = WARNING     [will cut close — order soon]
  ELIF current_stock > (projected_demand_safety × 3):
    urgency = OVERSTOCK   [holding too much — do not reorder]
  ELSE:
    urgency = OK
```

---

## 10. Financial Impact Calculation

Used in two contexts:
1. **Backtesting**: comparing engine vs basic prediction on historical data
2. **Live**: projected savings of following the engine's recommendation vs staying with basic prediction

### 10.1 Cost model

```
OVER-ORDER COST:
  over_order_units = max(0, order_qty - actual_demand)
  holding_cost_rate = 0.20   [20% annual cost of capital — standard retail assumption]
  weeks_held = estimated_weeks_held_before_clearance (default: 26 weeks if unknown)

  over_order_cost_lei = over_order_units × purchase_cost_lei
                      + over_order_units × purchase_cost_lei × holding_cost_rate × (weeks_held/52)

  Simplified form (acceptable for MVP):
  over_order_cost_lei = over_order_units × purchase_cost_lei × 1.10
  [10% penalty on purchase cost for holding. Conservative estimate.]

STOCKOUT COST:
  stockout_units = max(0, actual_demand - order_qty)
  gross_margin_pct = (retail_price_lei - purchase_cost_lei) / retail_price_lei

  stockout_cost_lei = stockout_units × retail_price_lei × gross_margin_pct × 1.5
  [1.5× multiplier accounts for: lost margin + customer who leaves empty-handed
   may not return. Industry standard is 1.3–2.0×. Use 1.5 as conservative middle.]
```

### 10.2 Comparison calculation

```
FOR each SKU in the comparison period:
  basic_order   = v_tool_estimate_4w      [same month last year ÷ days × 28]
  engine_order  = ensemble_forecast_4w   [our engine's recommendation]
  actual_sales  = actual weekly_net_sold summed over same 4-week period

  basic_cost  = over_order_cost(basic_order, actual_sales)
              + stockout_cost(basic_order, actual_sales)
  engine_cost = over_order_cost(engine_order, actual_sales)
              + stockout_cost(engine_order, actual_sales)

  sku_savings_lei = basic_cost - engine_cost

AGGREGATE:
  total_savings_lei      = SUM(sku_savings_lei) across all SKUs
  total_savings_pct      = total_savings_lei / SUM(basic_cost) × 100%
  skus_improved          = COUNT(sku_savings_lei > 0)
  skus_worse             = COUNT(sku_savings_lei < 0)

  savings_from_less_overorder = SUM(basic_over_order_cost - engine_over_order_cost)
  savings_from_fewer_stockouts = SUM(basic_stockout_cost - engine_stockout_cost)
```

---

## 11. Feature Importance and Explainability

After each LightGBM training run, extract and store feature importance.

```
feature_importance = lgb_model.feature_importance(importance_type='gain')
  ['gain' measures total information gain contributed by each feature across all trees.
   More meaningful than 'split' count for understanding predictive power.]

Store top 20 features with importance scores in: model_metadata table
```

For per-SKU explanation of individual forecasts, use SHAP values:

```python
import shap
explainer = shap.TreeExplainer(lgb_model)
shap_values = explainer.shap_values(feature_row_for_this_sku)

# Top 3 contributing features for this SKU's forecast
top_drivers = sorted(zip(feature_names, shap_values), key=lambda x: abs(x[1]), reverse=True)[:3]
```

These top drivers become the `drivers` field in the output (plain-language descriptions).

Driver template mapping:
```
lag_52w → "Same week last year: {value} units"
cat_yoy_ratio → "Category trend: {+/-X%} vs last year"
cat_seasonal_index → "Week {n} seasonal index: {X}× average"
is_black_friday → "Black Friday week effect"
is_on_promotion → "Active promotion: {discount_pct}% discount"
trend_short → "Recent momentum: {above/below} 13-week average"
```

---

## 12. Full Output Schema

One record per (sku_id, forecast_run_date). Stored in `forecasts` table.

```json
{
  "forecast_run_id":         "2026-01-06-001",
  "forecast_generated_at":   "2026-01-06T08:00:00Z",
  "as_of_week_ending":       "2026-01-05",

  "sku_id":                  "SKU-0042",
  "sku_name":                "Canapea Coltar Gri 3 locuri",
  "category":                "Sofas",
  "subcategory":             "Corner Sofas",
  "lifecycle_phase":         "MATURE",

  "model_used":              "ensemble",
  "ets_weight":              0.41,
  "lgbm_weight":             0.59,
  "ets_available":           true,
  "model_accuracy_wmape_pct": 13.4,
  "model_bias_pct":          1.8,
  "bias_correction_applied": true,
  "bias_correction_factor":  0.97,
  "reconciliation_status":   "OK",

  "forecast_weekly": [
    {"week_ending": "2026-01-12", "forecast": 5, "ci_low": 3, "ci_high": 8},
    {"week_ending": "2026-01-19", "forecast": 6, "ci_low": 3, "ci_high": 9},
    {"week_ending": "2026-01-26", "forecast": 5, "ci_low": 3, "ci_high": 8},
    {"week_ending": "2026-02-02", "forecast": 6, "ci_low": 4, "ci_high": 9},
    {"week_ending": "2026-02-09", "forecast": 6, "ci_low": 3, "ci_high": 9},
    {"week_ending": "2026-02-16", "forecast": 7, "ci_low": 4, "ci_high": 10},
    {"week_ending": "2026-02-23", "forecast": 6, "ci_low": 3, "ci_high": 9},
    {"week_ending": "2026-03-02", "forecast": 7, "ci_low": 4, "ci_high": 11}
  ],

  "forecast_4_weeks":        22,
  "forecast_8_weeks":        48,
  "ci_low_4w":               16,
  "ci_high_4w":              29,
  "ci_low_8w":               28,
  "ci_high_8w":              68,

  "basic_prediction_4w":     31,
  "delta_vs_basic_units":    -9,
  "delta_vs_basic_lei":      -10800,

  "current_stock_units":     8,
  "current_stock_weeks":     1.5,
  "on_order_qty":            0,
  "recommended_order_qty":   18,
  "lead_time_weeks_used":    4,
  "urgency":                 "WARNING",

  "drivers": [
    "Same week last year: 20 units",
    "Category trend: +10% vs last year",
    "Week 2 seasonal index: 1.08× average (above average)"
  ],

  "flags": [],

  "financial_impact": {
    "basic_prediction_cost_lei":  3720,
    "engine_cost_lei":            1240,
    "projected_savings_lei":      2480
  }
}
```

---

## 13. Database Schema

```sql
-- Clean weekly time series (post-aggregation + cleaning)
CREATE TABLE weekly_demand (
  week_ending       DATE,
  sku_id            VARCHAR,
  units_sold        INTEGER,
  units_returned    INTEGER,
  net_sold          INTEGER,          -- units_sold - units_returned, clipped at 0
  net_sold_clean    FLOAT,            -- after censored demand imputation
  is_censored       BOOLEAN,
  is_promotional    BOOLEAN,
  lifecycle_phase   VARCHAR,          -- NEW / GROWING / MATURE / DECLINING / EOL
  PRIMARY KEY (week_ending, sku_id)
);

-- Feature matrix (one row per sku × week, all engineered features)
CREATE TABLE feature_matrix (
  week_ending          DATE,
  sku_id               VARCHAR,
  -- all lag, rolling, calendar, product, category features as columns
  -- (populated by feature engineering pipeline)
  PRIMARY KEY (week_ending, sku_id)
);

-- Forecasts (output of the engine)
CREATE TABLE forecasts (
  forecast_run_id        VARCHAR,
  forecast_generated_at  TIMESTAMP,
  sku_id                 VARCHAR,
  week_ending_target     DATE,        -- the week being forecast
  forecast_units         INTEGER,
  ci_low                 INTEGER,
  ci_high                INTEGER,
  model_used             VARCHAR,
  PRIMARY KEY (forecast_run_id, sku_id, week_ending_target)
);

-- Backtest results (one row per sku × fold × week)
CREATE TABLE backtest_results (
  fold_id            INTEGER,
  cutoff_date        DATE,
  sku_id             VARCHAR,
  week_ending        DATE,
  forecast           FLOAT,
  actual             FLOAT,
  abs_error          FLOAT,
  pct_error          FLOAT,
  PRIMARY KEY (fold_id, sku_id, week_ending)
);

-- Model accuracy summary (updated after each backtest run)
CREATE TABLE model_accuracy (
  sku_id             VARCHAR,
  model_type         VARCHAR,         -- ETS / LGBM / ENSEMBLE
  wmape_pct          FLOAT,
  bias_pct           FLOAT,
  hit_rate_20        FLOAT,
  tracking_signal    FLOAT,
  model_drift_flag   BOOLEAN,
  computed_at        TIMESTAMP,
  PRIMARY KEY (sku_id, model_type)
);

-- Bias corrections (applied at forecast time)
CREATE TABLE bias_corrections (
  category           VARCHAR PRIMARY KEY,
  bias_correction_factor FLOAT,
  source_bias_pct    FLOAT,
  computed_at        TIMESTAMP
);
```

---

## 14. Processing Schedule

```
WEEKLY (every Monday morning, before buyers start their day):

  1. Ingest Pentaho exports               ~2 min
  2. Aggregate to weekly series           ~1 min
  3. Run censored demand detection        ~2 min
  4. Run promotional spike detection      ~1 min
  5. Update lifecycle classifications     ~1 min
  6. Rebuild feature matrix               ~3 min
  7. Retrain LightGBM                     ~5 min
  8. Retrain ETS per SKU                  ~3 min
  9. Run ensemble, apply bias correction  ~1 min
  10. Generate forecasts for next 8 weeks ~1 min
  11. Compute order recommendations       ~1 min
  12. Update model accuracy metrics       ~2 min

  Total: ~23 minutes. Runs as scheduled Python job (APScheduler or cron).

MONTHLY (first Monday of month):
  - Run full backtesting suite            ~20 min
  - Update bias correction factors
  - Flag SKUs with model drift
  - Update ensemble weights per SKU
```

---

## 15. Accuracy Targets

| Metric | Minimum acceptable | Target |
|--------|-------------------|--------|
| Overall WMAPE | < 22% | < 15% |
| Overall bias | < ±8% | < ±3% |
| Hit rate ±20% | > 60% | > 72% |
| Improvement vs basic prediction | > 15% WMAPE reduction | > 25% |
| High-volume SKU hit rate (top 20% by volume) | > 75% | > 85% |

If minimum acceptable is not met after full backtesting on real data: review feature engineering, check data quality, investigate bias corrections before concluding the model is inadequate.
