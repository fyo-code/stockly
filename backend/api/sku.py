"""
SKU Deep Dive API routes.

Endpoints:
  GET /api/sku/search?q=   — fuzzy search SKUs by name or ID (autocomplete)
  GET /api/sku/{sku_id}    — full aggregated SKU profile from all engines
"""

import logging

import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from db import get_conn
from engines.dead_stock import calculate_dead_stock
from engines.supplier import calculate_supplier_reliability
from engines.demand import calculate_demand

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/sku", tags=["sku"])


def _load_all():
    """Load all DataFrames needed across engines."""
    conn = get_conn()
    try:
        sales_df     = pd.read_sql("SELECT sku_id, store_id, sale_date, units_sold, units_returned FROM sales", conn)
        inventory_df = pd.read_sql("SELECT sku_id, store_id, units_in_stock, last_delivery_date, supplier_id FROM inventory", conn)
        skus_df      = pd.read_sql("SELECT sku_id, sku_name, category, supplier_id, selling_price_lei, purchase_cost_lei FROM skus", conn)
        suppliers_df = pd.read_sql("SELECT supplier_id, supplier_name, default_return_window_days FROM suppliers", conn)
        orders_df    = pd.read_sql("SELECT * FROM supplier_orders", conn)
    finally:
        conn.close()
    return sales_df, inventory_df, skus_df, suppliers_df, orders_df


# ── Search ─────────────────────────────────────────────────────────────────────

@router.get("/search")
def search_skus(q: str = Query(..., min_length=1, description="Search term")):
    """
    Autocomplete search by SKU name or ID. Returns up to 20 matches.
    Used by the SKU search bar in the nav and deep dive page.
    """
    conn = get_conn()
    try:
        term = f"%{q.strip()}%"
        rows = conn.execute(
            "SELECT sku_id, sku_name, category FROM skus "
            "WHERE LOWER(sku_name) LIKE LOWER(?) OR LOWER(sku_id) LIKE LOWER(?) "
            "ORDER BY sku_name LIMIT 20",
            (term, term),
        ).fetchall()
    finally:
        conn.close()

    return {
        "results": [
            {"sku_id": r[0], "sku_name": r[1], "category": r[2]}
            for r in rows
        ]
    }


# ── Full SKU Profile ───────────────────────────────────────────────────────────

@router.get("/{sku_id}")
def get_sku_profile(sku_id: str):
    """
    Aggregated profile for a single SKU pulling from all engines.
    Returns demand forecast, dead stock status (if applicable),
    supplier reliability, current stock, and scenario recommendation.
    Used by the SKU deep dive page.
    """
    try:
        sales_df, inventory_df, skus_df, suppliers_df, orders_df = _load_all()

        # ── SKU metadata ──────────────────────────────────────────────────────
        sku_rows = skus_df[skus_df["sku_id"] == sku_id]
        if sku_rows.empty:
            raise HTTPException(status_code=404, detail="SKU not found")
        sku_row = sku_rows.iloc[0]

        # ── Current stock (summed across all stores) ──────────────────────────
        sku_inv = inventory_df[inventory_df["sku_id"] == sku_id]
        current_stock = int(sku_inv["units_in_stock"].sum()) if not sku_inv.empty else 0
        store_breakdown = [
            {"store_id": str(r["store_id"]), "units_in_stock": int(r["units_in_stock"])}
            for _, r in sku_inv.iterrows()
        ]

        # ── Demand engine ─────────────────────────────────────────────────────
        dem_report = calculate_demand(
            sales_df,
            skus_df[["sku_id", "sku_name", "category", "purchase_cost_lei"]],
        )
        demand = next((r for r in dem_report["results"] if r["sku_id"] == sku_id), None)

        # ── Supplier engine ───────────────────────────────────────────────────
        supplier_id = str(sku_row["supplier_id"]) if pd.notna(sku_row["supplier_id"]) else None
        sup_report = calculate_supplier_reliability(
            orders_df,
            suppliers_df[["supplier_id", "supplier_name"]],
            skus_df[["sku_id", "sku_name"]],
        )
        supplier = next(
            (s for s in sup_report["suppliers"] if s["supplier_id"] == supplier_id),
            None,
        ) if supplier_id else None

        # Extract whether this specific SKU is flagged as stockout risk
        stockout_risk = None
        if supplier:
            stockout_risk = next(
                (r for r in supplier["stockout_risk_skus"] if r["sku_id"] == sku_id),
                None,
            )

        # ── Dead stock engine ─────────────────────────────────────────────────
        ds_report = calculate_dead_stock(sales_df, inventory_df, skus_df, suppliers_df)
        dead_stock_records = [i for i in ds_report["items"] if i["sku_id"] == sku_id]

        # Aggregate dead stock across stores
        dead_stock = None
        if dead_stock_records:
            worst = max(dead_stock_records, key=lambda x: x["capital_at_risk_lei"])
            dead_stock = {
                "is_dead_stock": True,
                "days_inactive": worst["days_inactive"],
                "total_capital_at_risk_lei": sum(r["capital_at_risk_lei"] for r in dead_stock_records),
                "total_budget_unlock_lei": sum(r["budget_unlock_lei"] for r in dead_stock_records),
                "trajectory": worst["trajectory"],
                "return_window_open": bool(any(r["return_window_open"] for r in dead_stock_records)),
                "return_window_urgent": bool(any(r["return_window_urgent"] for r in dead_stock_records)),
                "return_window_days_remaining": worst.get("return_window_days_remaining"),
                "store_breakdown": [
                    {
                        "store_id": r["store_id"],
                        "days_inactive": r["days_inactive"],
                        "units_in_stock": r["units_in_stock"],
                        "capital_at_risk_lei": r["capital_at_risk_lei"],
                        "return_window_open": r["return_window_open"],
                    }
                    for r in dead_stock_records
                ],
            }

        # ── Coverage calculation (if demand available) ────────────────────────
        coverage = None
        if demand and demand["real_demand_monthly"] > 0:
            weekly_demand = demand["forecast_8_weeks"] / 8 if demand["forecast_8_weeks"] > 0 else 0
            if weekly_demand > 0:
                weeks_of_coverage = round(current_stock / weekly_demand, 1)
                lead_time_weeks = (supplier["avg_actual_lead_time_days"] / 7) if supplier else 3.0
                coverage = {
                    "weeks_of_coverage": weeks_of_coverage,
                    "lead_time_weeks": round(lead_time_weeks, 1),
                    "reorder_needed": bool(weeks_of_coverage < lead_time_weeks + 1),
                }

    except HTTPException:
        raise
    except Exception as e:
        log.error("SKU profile failed for %s: %s", sku_id, e)
        raise HTTPException(status_code=500, detail="SKU profile calculation failed")

    return {
        # Metadata
        "sku_id": sku_id,
        "sku_name": str(sku_row["sku_name"]),
        "category": str(sku_row["category"]),
        "purchase_cost_lei": float(sku_row["purchase_cost_lei"]),
        "selling_price_lei": float(sku_row["selling_price_lei"]),

        # Stock
        "current_stock": current_stock,
        "store_breakdown": store_breakdown,
        "coverage": coverage,

        # Demand — None if insufficient data
        "demand": {
            "trend_status": demand["trend_status"],
            "trend_slope": demand["trend_slope"],
            "real_demand_monthly": demand["real_demand_monthly"],
            "apparent_demand_monthly": demand["apparent_demand_monthly"],
            "return_rate": demand["return_rate"],
            "return_flag": demand["return_flag"],
            "forecast_4_weeks": demand["forecast_4_weeks"],
            "forecast_8_weeks": demand["forecast_8_weeks"],
            "v_tool_estimate_4_weeks": demand["v_tool_estimate_4_weeks"],
            "gap_units": demand["gap_units"],
            "gap_lei": demand["gap_lei"],
            "weekly_history": demand["weekly_history"],
            "forecast_weekly": demand["forecast_weekly"],
        } if demand else None,

        # Supplier — None if no supplier or no order history
        "supplier": {
            "supplier_id": supplier["supplier_id"],
            "supplier_name": supplier["supplier_name"],
            "reliability_score": supplier["reliability_score"],
            "status": supplier["status"],
            "avg_promised_lead_time_days": supplier["avg_promised_lead_time_days"],
            "avg_actual_lead_time_days": supplier["avg_actual_lead_time_days"],
            "lead_time_gap_days": supplier["lead_time_gap_days"],
            "trend": supplier["trend"],
            "stockout_risk": stockout_risk,
        } if supplier else None,

        # Dead stock — None if SKU is not dead stock
        "dead_stock": dead_stock,
    }
