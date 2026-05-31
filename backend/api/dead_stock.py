"""
Dead Stock API routes.

Endpoints:
  GET /api/dead-stock          — full dead stock report (all SKUs, all stores)
  GET /api/dead-stock/summary  — just the headline numbers for the dashboard card
"""

import logging
from datetime import date

import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from db import get_conn
from engines.dead_stock import calculate_dead_stock, DeadStockReport

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/dead-stock", tags=["dead-stock"])


def _load_dataframes():
    """Load required tables into DataFrames."""
    conn = get_conn()
    try:
        sales_df     = pd.read_sql("SELECT sku_id, store_id, sale_date, units_sold, units_returned FROM sales", conn)
        inventory_df = pd.read_sql("SELECT sku_id, store_id, units_in_stock, last_delivery_date, supplier_id FROM inventory", conn)
        skus_df      = pd.read_sql("SELECT sku_id, sku_name, category, supplier_id, purchase_cost_lei FROM skus", conn)
        suppliers_df = pd.read_sql("SELECT supplier_id, default_return_window_days FROM suppliers", conn)
    finally:
        conn.close()
    return sales_df, inventory_df, skus_df, suppliers_df


@router.get("", response_model=None)
def get_dead_stock_report(
    category: str | None = Query(None, description="Filter by category"),
    store_id: str | None = Query(None, description="Filter by store"),
    min_days_inactive: int = Query(60, description="Minimum days inactive"),
    limit: int = Query(100, description="Max items to return"),
):
    """
    Full dead stock report ranked by capital at risk.
    Used by the dead stock detail view and morning queue.
    """
    try:
        sales_df, inventory_df, skus_df, suppliers_df = _load_dataframes()
        report = calculate_dead_stock(sales_df, inventory_df, skus_df, suppliers_df)
    except Exception as e:
        log.error("Dead stock calculation failed: %s", e)
        raise HTTPException(status_code=500, detail="Calculation failed")

    items = report["items"]

    # Apply filters
    if category:
        items = [i for i in items if i["category"] == category]
    if store_id:
        items = [i for i in items if i["store_id"] == store_id]
    if min_days_inactive != 60:
        items = [i for i in items if i["days_inactive"] >= min_days_inactive]

    return {
        "calculated_at": report["calculated_at"],
        "total_dead_stock_lei": report["total_dead_stock_lei"],
        "total_budget_unlock_lei": report["total_budget_unlock_lei"],
        "sku_count": report["sku_count"],
        "urgent_return_count": report["urgent_return_count"],
        "items": items[:limit],
        "total_items": len(items),
    }


@router.get("/summary")
def get_dead_stock_summary():
    """
    Headline numbers for the dashboard card:
    total dead stock lei, budget unlock, urgent returns count.
    """
    try:
        sales_df, inventory_df, skus_df, suppliers_df = _load_dataframes()
        report = calculate_dead_stock(sales_df, inventory_df, skus_df, suppliers_df)
    except Exception as e:
        log.error("Dead stock summary failed: %s", e)
        raise HTTPException(status_code=500, detail="Calculation failed")

    urgent = [i for i in report["items"] if i["return_window_urgent"]]
    top3 = report["items"][:3]

    return {
        "calculated_at": report["calculated_at"],
        "total_dead_stock_lei": report["total_dead_stock_lei"],
        "total_budget_unlock_lei": report["total_budget_unlock_lei"],
        "sku_count": report["sku_count"],
        "urgent_return_count": report["urgent_return_count"],
        "top_offenders": [
            {
                "sku_id": i["sku_id"],
                "sku_name": i["sku_name"],
                "capital_at_risk_lei": i["capital_at_risk_lei"],
                "days_inactive": i["days_inactive"],
                "trajectory": i["trajectory"],
                "return_window_urgent": i["return_window_urgent"],
            }
            for i in top3
        ],
    }
