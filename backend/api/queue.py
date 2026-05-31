"""
Morning Decision Queue + Scenario Simulation API routes.

Endpoints:
  GET  /api/queue              — full morning decision queue
  GET  /api/queue/summary      — headline counts for dashboard
  POST /api/scenario/{sku_id}  — run scenario simulation for a specific SKU
"""

import logging
from datetime import date

import pandas as pd
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from db import get_conn
from engines.dead_stock import calculate_dead_stock
from engines.supplier import calculate_supplier_reliability
from engines.demand import calculate_demand
from engines.queue import build_decision_queue
from engines.scenario import simulate_scenarios

log = logging.getLogger(__name__)
router = APIRouter(tags=["queue-scenario"])


# ── Shared Data Loader ─────────────────────────────────────────────────────────

def _load_all():
    """Load all DataFrames needed by the 3 engines."""
    conn = get_conn()
    try:
        sales_df     = pd.read_sql("SELECT sku_id, store_id, sale_date, units_sold, units_returned FROM sales", conn)
        inventory_df = pd.read_sql("SELECT sku_id, store_id, units_in_stock, last_delivery_date, supplier_id FROM inventory", conn)
        skus_df      = pd.read_sql("SELECT sku_id, sku_name, category, supplier_id, selling_price_lei, purchase_cost_lei FROM skus", conn)
        suppliers_df = pd.read_sql("SELECT supplier_id, supplier_name, default_return_window_days FROM suppliers", conn)
        orders_df    = pd.read_sql("SELECT * FROM supplier_orders", conn)
        budgets_df   = pd.read_sql("SELECT category, period, budget_lei, spent_lei FROM budget_envelopes", conn)
    finally:
        conn.close()
    return sales_df, inventory_df, skus_df, suppliers_df, orders_df, budgets_df


# ── Queue Endpoints ────────────────────────────────────────────────────────────

@router.get("/api/queue")
def get_decision_queue(
    status: str | None = Query(None, description="Filter: URGENT | REVIEW | INFO"),
    queue_type: str | None = Query(None, description="Filter by queue type"),
    limit: int = Query(100),
):
    """Full morning decision queue. The first screen the buyer sees."""
    try:
        sales_df, inventory_df, skus_df, suppliers_df, orders_df, _ = _load_all()

        ds_report  = calculate_dead_stock(sales_df, inventory_df, skus_df, suppliers_df)
        sup_report = calculate_supplier_reliability(
            orders_df, suppliers_df[["supplier_id", "supplier_name"]],
            skus_df[["sku_id", "sku_name"]],
        )
        dem_report = calculate_demand(
            sales_df, skus_df[["sku_id", "sku_name", "category", "purchase_cost_lei"]],
        )
        queue = build_decision_queue(ds_report, sup_report, dem_report)
    except Exception as e:
        log.error("Decision queue failed: %s", e)
        raise HTTPException(status_code=500, detail="Queue calculation failed")

    items = queue["items"]
    if status:
        items = [i for i in items if i["status"] == status.upper()]
    if queue_type:
        items = [i for i in items if i["queue_type"] == queue_type.upper()]

    return {
        "calculated_at": queue["calculated_at"],
        "total_items": queue["total_items"],
        "urgent_count": queue["urgent_count"],
        "review_count": queue["review_count"],
        "info_count": queue["info_count"],
        "total_financial_impact_lei": queue["total_financial_impact_lei"],
        "items": items[:limit],
        "showing": min(limit, len(items)),
    }


@router.get("/api/queue/summary")
def get_queue_summary():
    """Headline counts for the dashboard — how many items need attention today."""
    try:
        sales_df, inventory_df, skus_df, suppliers_df, orders_df, _ = _load_all()

        ds_report  = calculate_dead_stock(sales_df, inventory_df, skus_df, suppliers_df)
        sup_report = calculate_supplier_reliability(
            orders_df, suppliers_df[["supplier_id", "supplier_name"]],
            skus_df[["sku_id", "sku_name"]],
        )
        dem_report = calculate_demand(
            sales_df, skus_df[["sku_id", "sku_name", "category", "purchase_cost_lei"]],
        )
        queue = build_decision_queue(ds_report, sup_report, dem_report)
    except Exception as e:
        log.error("Queue summary failed: %s", e)
        raise HTTPException(status_code=500, detail="Calculation failed")

    return {
        "calculated_at": queue["calculated_at"],
        "total_items": queue["total_items"],
        "urgent_count": queue["urgent_count"],
        "review_count": queue["review_count"],
        "info_count": queue["info_count"],
        "total_financial_impact_lei": queue["total_financial_impact_lei"],
    }


# ── Scenario Endpoint ──────────────────────────────────────────────────────────

class ScenarioRequest(BaseModel):
    budget_lei: float | None = None
    budget_spent_lei: float | None = None


@router.post("/api/scenario/{sku_id}")
def run_scenario(sku_id: str, body: ScenarioRequest | None = None):
    """
    Run scenario simulation for a specific SKU.
    Combines demand forecast + supplier lead time + current stock + optional budget.
    """
    try:
        sales_df, inventory_df, skus_df, suppliers_df, orders_df, budgets_df = _load_all()

        # Get demand forecast for this SKU
        dem_report = calculate_demand(
            sales_df, skus_df[["sku_id", "sku_name", "category", "purchase_cost_lei"]],
        )
        sku_demand = next((r for r in dem_report["results"] if r["sku_id"] == sku_id), None)
        if not sku_demand:
            raise HTTPException(status_code=404, detail="SKU not found or insufficient demand data")

        # Get SKU metadata
        sku_row = skus_df[skus_df["sku_id"] == sku_id].iloc[0]

        # Get current stock (sum across stores)
        sku_inv = inventory_df[inventory_df["sku_id"] == sku_id]
        current_stock = int(sku_inv["units_in_stock"].sum())

        # Get real lead time from supplier engine
        sup_report = calculate_supplier_reliability(
            orders_df, suppliers_df[["supplier_id", "supplier_name"]],
            skus_df[["sku_id", "sku_name"]],
        )
        supplier_id = str(sku_row["supplier_id"])
        sup_match = next((s for s in sup_report["suppliers"] if s["supplier_id"] == supplier_id), None)
        real_lead_time_weeks = (sup_match["avg_actual_lead_time_days"] / 7) if sup_match else 3.0

        # Budget — from request body or from database
        budget_lei = None
        budget_spent = None
        if body and body.budget_lei is not None:
            budget_lei = body.budget_lei
            budget_spent = body.budget_spent_lei
        elif not budgets_df.empty:
            cat_budget = budgets_df[budgets_df["category"] == sku_demand["category"]]
            if not cat_budget.empty:
                row = cat_budget.iloc[-1]
                budget_lei = float(row["budget_lei"])
                budget_spent = float(row["spent_lei"])

        # Weekly real demand from forecast
        weekly_demand = sku_demand["forecast_8_weeks"] / 8 if sku_demand["forecast_8_weeks"] > 0 else 0

        result = simulate_scenarios(
            sku_id=sku_id,
            sku_name=sku_demand["sku_name"],
            category=sku_demand["category"],
            current_stock=current_stock,
            weekly_real_demand=weekly_demand,
            forecast_8_weeks=sku_demand["forecast_8_weeks"],
            selling_price_lei=float(sku_row["selling_price_lei"]),
            purchase_cost_lei=float(sku_row["purchase_cost_lei"]),
            real_lead_time_weeks=real_lead_time_weeks,
            budget_lei=budget_lei,
            budget_spent_lei=budget_spent,
        )

    except HTTPException:
        raise
    except Exception as e:
        log.error("Scenario simulation failed: %s", e)
        raise HTTPException(status_code=500, detail="Scenario simulation failed")

    return result
