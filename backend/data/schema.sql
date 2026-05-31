-- Supply Chain Decision Engine — SQLite Schema
-- Generic: no Mobexpert-specific assumptions. Works for any retailer.

PRAGMA foreign_keys = ON;

-- ── Suppliers ──────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS suppliers (
    supplier_id                TEXT PRIMARY KEY,
    supplier_name              TEXT NOT NULL,
    country                    TEXT NOT NULL,
    default_return_window_days INTEGER NOT NULL DEFAULT 90,
    preferred_language         TEXT
);

-- ── SKUs ───────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS skus (
    sku_id             TEXT PRIMARY KEY,
    sku_name           TEXT NOT NULL,
    category           TEXT NOT NULL,
    supplier_id        TEXT NOT NULL REFERENCES suppliers(supplier_id),
    selling_price_lei  REAL NOT NULL,
    purchase_cost_lei  REAL NOT NULL
);

-- ── Stores ─────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS stores (
    store_id   TEXT PRIMARY KEY,
    store_name TEXT
);

-- ── Sales ──────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS sales (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    sku_id             TEXT NOT NULL REFERENCES skus(sku_id),
    store_id           TEXT NOT NULL,
    sale_date          TEXT NOT NULL,  -- ISO date YYYY-MM-DD
    units_sold         INTEGER NOT NULL DEFAULT 0,
    units_returned     INTEGER NOT NULL DEFAULT 0,
    return_reason      TEXT,
    selling_price_lei  REAL NOT NULL,
    purchase_cost_lei  REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sales_sku_date ON sales(sku_id, sale_date);
CREATE INDEX IF NOT EXISTS idx_sales_date ON sales(sale_date);

-- ── Inventory ──────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS inventory (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    sku_id             TEXT NOT NULL REFERENCES skus(sku_id),
    store_id           TEXT NOT NULL,
    units_in_stock     INTEGER NOT NULL DEFAULT 0,
    last_delivery_date TEXT,  -- ISO date
    supplier_id        TEXT REFERENCES suppliers(supplier_id),
    UNIQUE(sku_id, store_id)
);

-- ── Supplier Orders ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS supplier_orders (
    order_id                TEXT PRIMARY KEY,
    supplier_id             TEXT NOT NULL REFERENCES suppliers(supplier_id),
    sku_id                  TEXT NOT NULL REFERENCES skus(sku_id),
    order_date              TEXT NOT NULL,
    promised_delivery_date  TEXT NOT NULL,
    actual_delivery_date    TEXT,       -- NULL if not yet delivered
    units_ordered           INTEGER NOT NULL,
    units_delivered         INTEGER
);

CREATE INDEX IF NOT EXISTS idx_orders_supplier ON supplier_orders(supplier_id);
CREATE INDEX IF NOT EXISTS idx_orders_sku ON supplier_orders(sku_id);

-- ── Budget Envelopes ───────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS budget_envelopes (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    category   TEXT NOT NULL,
    period     TEXT NOT NULL,  -- e.g. '2026-03' (YYYY-MM)
    budget_lei REAL NOT NULL,
    spent_lei  REAL NOT NULL DEFAULT 0,
    UNIQUE(category, period)
);

-- ── Buyer Decisions (logged from Morning Queue actions) ───────────────────────
CREATE TABLE IF NOT EXISTS decisions (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    sku_id            TEXT NOT NULL REFERENCES skus(sku_id),
    queue_type        TEXT NOT NULL,       -- RETURN_WINDOW_CLOSING | STOCKOUT_RISK | DEAD_STOCK | DEMAND_DECLINING | OVER_ORDER_RISK
    action            TEXT NOT NULL,       -- approve | skip | override
    override_qty      INTEGER,             -- only when action = 'override'
    override_reason   TEXT,                -- optional reason for override
    recommended_qty   INTEGER,             -- what the engine suggested
    financial_impact_lei REAL,             -- impact at time of decision
    decided_at        TEXT NOT NULL DEFAULT (datetime('now')),
    decided_by        TEXT NOT NULL DEFAULT 'buyer'
);

CREATE INDEX IF NOT EXISTS idx_decisions_sku ON decisions(sku_id);
CREATE INDEX IF NOT EXISTS idx_decisions_date ON decisions(decided_at);

-- ── Pre-calculated Results (written by nightly engines) ────────────────────────
CREATE TABLE IF NOT EXISTS dead_stock_results (
    id                        INTEGER PRIMARY KEY AUTOINCREMENT,
    calculated_at             TEXT NOT NULL,
    sku_id                    TEXT NOT NULL REFERENCES skus(sku_id),
    store_id                  TEXT NOT NULL,
    days_inactive             INTEGER NOT NULL,
    units_in_stock            INTEGER NOT NULL,
    capital_at_risk_lei       REAL NOT NULL,
    dead_stock_score          REAL NOT NULL,
    trajectory                TEXT NOT NULL,  -- SUDDEN_STOP | LIFECYCLE_DECLINE | NEVER_MOVED
    return_window_open        INTEGER NOT NULL DEFAULT 0,  -- bool
    return_window_days_remaining INTEGER,
    return_window_urgent      INTEGER NOT NULL DEFAULT 0   -- bool
);

CREATE TABLE IF NOT EXISTS supplier_reliability_results (
    id                          INTEGER PRIMARY KEY AUTOINCREMENT,
    calculated_at               TEXT NOT NULL,
    supplier_id                 TEXT NOT NULL REFERENCES suppliers(supplier_id),
    reliability_score           REAL NOT NULL,
    status                      TEXT NOT NULL,  -- GREEN | YELLOW | RED
    avg_promised_lead_time_days REAL,
    avg_actual_lead_time_days   REAL,
    lead_time_gap_days          REAL,
    delivery_consistency_std    REAL,
    trend                       TEXT,           -- IMPROVING | STABLE | WORSENING
    recent_avg_variance_days    REAL,
    historical_avg_variance_days REAL
);

CREATE TABLE IF NOT EXISTS demand_results (
    id                       INTEGER PRIMARY KEY AUTOINCREMENT,
    calculated_at            TEXT NOT NULL,
    sku_id                   TEXT NOT NULL REFERENCES skus(sku_id),
    apparent_demand_monthly  REAL,
    real_demand_monthly      REAL,
    return_rate              REAL,
    return_flag              INTEGER NOT NULL DEFAULT 0,  -- bool
    trend_status             TEXT,   -- GROWING | STABLE | DECLINING
    trend_slope              REAL,
    forecast_4_weeks         REAL,
    forecast_8_weeks         REAL,
    v_tool_estimate_4_weeks  REAL,
    gap_units                REAL,
    gap_lei                  REAL
);
