# MVP_SPEC.md — Exact MVP Features & Build Blueprint

## What The MVP Is

A web application with four core features. Clean, fast, usable daily. Connects to data exports from Pentaho. No direct database connection at this stage — data arrives as CSV or Excel files, gets processed and stored in our own PostgreSQL database, frontend reads from our database.

Built on synthetic data now. When Pentaho exports arrive, plug them into the existing pipeline — architecture must support this without rebuilding.

The product must feel like a real tool a buyer uses every morning, not a demo dashboard.

---

## The Core Problem The MVP Solves

Businesses do not know the right quantity to order because they do not know:
1. Real demand — what customers actually kept versus what was returned
2. Demand direction — is this SKU growing or declining right now
3. Real lead times — what suppliers actually deliver versus what they promise
4. What is already dead — capital sitting in warehouses not moving

Every feature of the MVP addresses one or more of these four unknowns.

---

## Feature 1: Real Demand Calculator + Trend Detection

### Purpose
The engine underneath everything else. Calculates true demand per SKU by stripping returns and detecting trend direction. Feeds Features 2, 3, and 4.

### Data Required
- SKU ID
- Sale date
- Units sold
- Units returned
- Return reason (if available — optional)
- Store ID

### Calculations

**Real demand per SKU per week:**
```
real_demand = units_sold - units_returned
```

**Return rate:**
```
return_rate = units_returned / units_sold
```
Flag SKU if return_rate > 0.20 (configurable threshold).
Do not automatically reduce order quantity based on returns alone.
Flag for investigation — return reason determines action, not return rate alone.

**Trend detection — 8-week rolling window:**
```
Take last 8 weeks of real_demand values
Calculate linear regression slope across those 8 points
if slope > +threshold: status = "GROWING"
if slope < -threshold: status = "DECLINING"
else: status = "STABLE"
```
Threshold suggestion: 5% of average weekly demand. Tune once real data arrives.

**Trend-adjusted forward forecast:**
```
base_weekly_demand = average of last 8 weeks real demand
weekly_trend = slope from regression
forecast_week_N = base_weekly_demand + (weekly_trend × N)
forecast_4_weeks = sum of forecast_week_1 through forecast_week_4
forecast_8_weeks = sum of forecast_week_1 through forecast_week_8
```

**Comparison against V's tool estimate:**
V's tool uses: (same month last year total) ÷ (days in month) × days in period
Calculate this for comparison. Show both side by side.
Gap = (V's estimate) - (our trend-adjusted forecast)
Express gap in units AND in lei (gap × purchase cost per unit)

### Output Per SKU
```json
{
  "sku_id": "...",
  "apparent_demand_monthly": 120,
  "real_demand_monthly": 74,
  "return_rate": 0.38,
  "return_flag": true,
  "trend_status": "DECLINING",
  "trend_slope": -2.3,
  "forecast_4_weeks": 68,
  "forecast_8_weeks": 130,
  "v_tool_estimate_4_weeks": 120,
  "gap_units": 52,
  "gap_lei": 41600
}
```

---

## Feature 2: Dead Stock Detector

### Purpose
Surface capital sitting idle in the warehouse. Show the total financial impact. Flag supplier return windows before they expire.

### Data Required
- SKU ID
- Last sale date per SKU per store
- Units currently in stock per SKU per store
- Purchase cost per unit
- Delivery date of most recent stock (for return window calculation)
- Supplier return window in days (configurable per supplier, default 90)

### Calculations

**Days inactive:**
```
days_inactive = today - last_meaningful_sale_date
```
Meaningful sale: quantity > 0 for furniture/high value items. Configurable per category.

**Capital at risk:**
```
capital_at_risk = units_in_stock × purchase_cost_per_unit
```

**Dead stock score (for ranking):**
```
dead_stock_score = days_inactive × capital_at_risk
```
Higher score = higher priority. Sort descending.

**Trajectory classification:**
```
sales_last_6_months = [month_1, month_2, month_3, month_4, month_5, month_6]
if last 3 months all zero AND previous 3 months > 0: status = "SUDDEN_STOP"
if consistent decline to zero over 6 months: status = "LIFECYCLE_DECLINE"
if always been low/zero: status = "NEVER_MOVED"
```
SUDDEN_STOP = investigate before clearing. Could be display issue, not demand issue.
LIFECYCLE_DECLINE = plan clearance.
NEVER_MOVED = highest urgency, should never have been ordered.

**Supplier return window:**
```
days_since_delivery = today - most_recent_delivery_date
days_remaining_in_window = supplier_return_window - days_since_delivery
if days_remaining_in_window > 0: return_window_open = true
if days_remaining_in_window <= 14: return_window_urgent = true  (closing soon)
```

**Total dead stock value:**
```
total_dead_stock_lei = sum of capital_at_risk for all SKUs where days_inactive > threshold
```
This is the big number shown at the top of the dashboard. Default threshold: 60 days inactive.

### Output
```json
{
  "total_dead_stock_lei": 847000,
  "sku_count_dead": 43,
  "top_offenders": [
    {
      "sku_id": "...",
      "sku_name": "Sofa Extensibil Luxor",
      "days_inactive": 187,
      "units_in_stock": 12,
      "capital_at_risk_lei": 43200,
      "dead_stock_score": 8078400,
      "trajectory": "LIFECYCLE_DECLINE",
      "return_window_open": true,
      "return_window_days_remaining": 23,
      "return_window_urgent": false
    }
  ]
}
```

---

## Feature 3: Supplier Reliability Scorer

### Purpose
Track actual versus promised supplier delivery performance. Surface reliability scores. Feed real lead times into reorder calculations. Flag SKUs at stockout risk because V's tool is using wrong lead time assumptions.

### Data Required
- Supplier ID
- Supplier name
- SKU IDs supplied by this supplier
- Per order: order date, promised delivery date, actual delivery date, units ordered, units delivered

### Calculations

**Per order delivery variance:**
```
delivery_variance_days = actual_delivery_date - promised_delivery_date
```
Positive = late. Negative = early.

**Average lead times:**
```
avg_promised_lead_time = mean(promised_delivery_date - order_date) across all orders
avg_actual_lead_time = mean(actual_delivery_date - order_date) across all orders
lead_time_gap = avg_actual_lead_time - avg_promised_lead_time
```

**Consistency (standard deviation of variance):**
```
delivery_consistency = standard_deviation(delivery_variance_days across all orders)
```
Low std dev = predictable even if late. High std dev = unreliable and unpredictable.

**Trend (recent vs historical):**
```
recent_orders = last 6 orders
historical_orders = all orders before that
recent_avg_variance = mean(delivery_variance for recent_orders)
historical_avg_variance = mean(delivery_variance for historical_orders)
trend_delta = recent_avg_variance - historical_avg_variance
if trend_delta > 2: trend = "WORSENING"
if trend_delta < -2: trend = "IMPROVING"
else: trend = "STABLE"
```

**Composite reliability score:**
```
score = 100
score -= min(40, lead_time_gap × 2)        # penalize lateness heavily
score -= min(30, delivery_consistency × 1.5) # penalize inconsistency
score -= max(0, trend_delta) × 3            # penalize worsening trend
score = max(0, min(100, score))
```
Score >= 75: GREEN
Score 50-74: YELLOW
Score < 50: RED

**Stockout risk flag — the critical output:**
For every SKU currently flagged by V's tool as needing reorder:
```
if supplier.lead_time_gap > 5:
    days_overdue = lead_time_gap
    flag as STOCKOUT_RISK with message:
    "V's tool calculated reorder based on {promised_lead_time} day lead time. 
     Actual average is {actual_lead_time} days. 
     This order should have been placed {days_overdue} days earlier."
```

### Output Per Supplier
```json
{
  "supplier_id": "...",
  "supplier_name": "Rosetti SRL",
  "reliability_score": 47,
  "status": "RED",
  "avg_promised_lead_time_days": 21,
  "avg_actual_lead_time_days": 34,
  "lead_time_gap_days": 13,
  "delivery_consistency_std_dev": 8.2,
  "trend": "WORSENING",
  "recent_avg_variance_days": 16,
  "historical_avg_variance_days": 10,
  "skus_at_stockout_risk": ["SKU_001", "SKU_047"],
  "order_history": [...]
}
```

---

## Feature 4: Scenario Simulation

### Purpose
Show the PM the financial consequence of different order quantities before they commit. Make the product feel like a decision tool, not a reporting tool.

### Data Required
- Forecasted demand (from Feature 1)
- Current stock level per SKU
- Purchase cost per unit
- Average selling price per unit
- Real lead time (from Feature 3)
- Budget envelope per category (configurable, optional)

### Calculations

**Recommended order quantity:**
```
weeks_of_stock = current_stock / weekly_real_demand
safety_buffer_weeks = 1  # configurable
reorder_weeks_needed = real_lead_time_weeks + safety_buffer_weeks
recommended_qty = max(0, (forecast_8_weeks) - current_stock)
```

**Three scenarios:**
```
scenario_conservative = recommended_qty × 0.8
scenario_base = recommended_qty
scenario_aggressive = recommended_qty × 1.2
```

**For each scenario:**
```
total_available = current_stock + scenario_qty

projected_units_sold = min(total_available, forecast_8_weeks)
projected_revenue = projected_units_sold × selling_price

projected_unsold_units = max(0, total_available - forecast_8_weeks)
projected_dead_stock_lei = projected_unsold_units × purchase_cost

projected_shortage_units = max(0, forecast_8_weeks - total_available)
projected_lost_revenue_lei = projected_shortage_units × selling_price

projected_margin = projected_revenue - (scenario_qty × purchase_cost)
projected_margin_pct = projected_margin / projected_revenue
```

**Demand sensitivity — run each scenario at 80%, 100%, 120% of forecast:**
Produces a range for each outcome metric showing best case, base case, worst case.

### Output
```json
{
  "sku_id": "...",
  "current_stock": 45,
  "forecast_8_weeks": 180,
  "scenarios": {
    "conservative": {
      "order_qty": 108,
      "projected_revenue_lei": 180000,
      "projected_dead_stock_lei": 0,
      "projected_lost_revenue_lei": 22500,
      "projected_margin_lei": 54000,
      "projected_margin_pct": 0.30
    },
    "base": {
      "order_qty": 135,
      "projected_revenue_lei": 202500,
      "projected_dead_stock_lei": 0,
      "projected_lost_revenue_lei": 0,
      "projected_margin_lei": 67500,
      "projected_margin_pct": 0.33
    },
    "aggressive": {
      "order_qty": 162,
      "projected_revenue_lei": 202500,
      "projected_dead_stock_lei": 27000,
      "projected_lost_revenue_lei": 0,
      "projected_margin_lei": 54000,
      "projected_margin_pct": 0.27
    }
  }
}
```

---

## The Morning Decision Queue — The Unifying Feature

All four features feed into a single decision queue. This is the first screen the buyer sees.

Each queue item follows this exact structure:
```
WHAT: [SKU name or Supplier name] — [problem type in caps]
WHY: [one sentence, specific data point that triggered this]
FINANCIAL IMPACT: [X lei] 
RECOMMENDED ACTION: [one specific thing to do]
STATUS: [URGENT / REVIEW / INFO]
```

**Queue item types and their sources:**

DEAD_STOCK → from Feature 2
RETURN_WINDOW_CLOSING → from Feature 2 (supplier return window < 14 days)
STOCKOUT_RISK → from Feature 3 (V's tool timing wrong due to lead time gap)
SUPPLIER_RED → from Feature 3 (reliability score dropped to red)
DEMAND_DECLINING → from Feature 1 (SKU trending down, V's tool will over-order)
OVER_ORDER_RISK → from Feature 1 (high return rate inflating apparent demand)

**Priority ranking:**
Sort by financial_impact_lei descending. Urgency flag overrides for RETURN_WINDOW_CLOSING and STOCKOUT_RISK.

---

## The Dashboard Layout

**Top bar — three KPI numbers always visible:**
- Total dead stock value in lei (updated nightly)
- Number of SKUs with stockout risk from supplier lead time drift
- Number of suppliers in RED status

**Main area — Morning Decision Queue:**
Paginated list of queue items. Each item expandable to show full context and scenario simulation.

**Side panel — quick access:**
- Supplier Scoreboard (all suppliers ranked)
- SKU Search (look up any SKU's full profile)
- Category Overview (demand trends by category)

---

## Synthetic Data Requirements

Until Pentaho exports arrive, build and test on synthetic data. The synthetic data must mirror Pentaho's actual structure.

**Required synthetic datasets:**

`sales_data.csv`
```
sku_id, sku_name, store_id, sale_date, units_sold, units_returned, return_reason, selling_price_lei, purchase_cost_lei, category
```

`inventory_data.csv`
```
sku_id, store_id, units_in_stock, last_delivery_date, supplier_id
```

`supplier_orders.csv`
```
order_id, supplier_id, sku_id, order_date, promised_delivery_date, actual_delivery_date, units_ordered, units_delivered
```

`suppliers.csv`
```
supplier_id, supplier_name, country, default_return_window_days, preferred_language
```

**Synthetic data parameters:**
- 500 SKUs across 5 categories (furniture, bedroom, kitchen, accessories, outdoor)
- 3 stores
- 8 suppliers (mix of Italian, Romanian)
- 24 months of history
- Include realistic patterns: seasonal spikes, 2-3 suppliers with consistent lead time problems, 15-20 SKUs with high return rates, 30-40 SKUs with dead stock, some SKUs with declining demand trend

---

## What Is NOT In The MVP

Do not build these — they belong in later phases:

- Autonomous ordering or any automation that executes without human approval
- Supplier communication (email agents, supplier portal)
- Direct Pentaho SQL connection
- Multi-model ensemble forecasting
- Agricultural-specific forecasting module
- Marketing signal integration
- Proprietary model fine-tuning
- Store-to-store transfer logistics calculations
- Multi-company / multi-tenant architecture (build foundation for it but don't implement)

---

## Definition of Done For MVP

The MVP is done when:

1. All four features work correctly on the synthetic dataset
2. The morning decision queue surfaces at least 3 types of alerts with correct calculations
3. A non-technical user can open the dashboard and immediately understand the dead stock number and what caused it
4. The scenario simulation shows correctly different financial outcomes for the three order quantities
5. The supplier scoreboard correctly identifies which suppliers have lead time gaps and which SKUs are at risk
6. The system works on real data exports with no code changes — just swap the data source
