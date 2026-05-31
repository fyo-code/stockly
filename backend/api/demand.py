"""
Demand + Trend API routes.

Endpoints:
  GET /api/demand              — all SKU demand results
  GET /api/demand/summary      — headline numbers for dashboard
  GET /api/demand/{sku_id}     — single SKU detail
"""

import logging

import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from db import get_conn
from engines.demand import calculate_demand

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/demand", tags=["demand"])


def _load_dataframes():
    conn = get_conn()
    try:
        sales_df = pd.read_sql(
            "SELECT sku_id, store_id, sale_date, units_sold, units_returned FROM sales", conn
        )
        skus_df = pd.read_sql(
            "SELECT sku_id, sku_name, category, purchase_cost_lei FROM skus", conn
        )
    finally:
        conn.close()
    return sales_df, skus_df


@router.get("")
def get_demand_report(
    trend: str | None = Query(None, description="Filter: GROWING | STABLE | DECLINING"),
    category: str | None = Query(None, description="Filter by category"),
    return_flag: bool | None = Query(None, description="Filter high-return SKUs only"),
    limit: int = Query(100),
):
    """Full demand report for all SKUs. Used by SKU search and category overview."""
    try:
        sales_df, skus_df = _load_dataframes()
        report = calculate_demand(sales_df, skus_df)
    except Exception as e:
        log.error("Demand calculation failed: %s", e)
        raise HTTPException(status_code=500, detail="Calculation failed")

    results = report["results"]
    if trend:
        results = [r for r in results if r["trend_status"] == trend.upper()]
    if category:
        results = [r for r in results if r["category"] == category]
    if return_flag is not None:
        results = [r for r in results if r["return_flag"] == return_flag]

    # Sort by gap_lei descending — biggest over-order risk first
    results = sorted(results, key=lambda x: abs(x["gap_lei"]), reverse=True)

    return {
        "calculated_at": report["calculated_at"],
        "total_skus_analysed": report["total_skus_analysed"],
        "growing_count": report["growing_count"],
        "declining_count": report["declining_count"],
        "stable_count": report["stable_count"],
        "high_return_count": report["high_return_count"],
        "total_overorder_risk_lei": report["total_overorder_risk_lei"],
        "results": results[:limit],
        "total_results": len(results),
    }


@router.get("/summary")
def get_demand_summary():
    """
    Headline numbers for the dashboard KPI bar.
    Returns trend distribution and total over-order risk in lei.
    """
    try:
        sales_df, skus_df = _load_dataframes()
        report = calculate_demand(sales_df, skus_df)
    except Exception as e:
        log.error("Demand summary failed: %s", e)
        raise HTTPException(status_code=500, detail="Calculation failed")

    # Top 3 over-order risks (declining SKUs with biggest gap)
    overorder = sorted(
        [r for r in report["results"] if r["trend_status"] == "DECLINING" and r["gap_lei"] > 0],
        key=lambda x: x["gap_lei"], reverse=True
    )[:3]

    # Top 3 high return SKUs
    high_return = sorted(
        [r for r in report["results"] if r["return_flag"]],
        key=lambda x: x["return_rate"], reverse=True
    )[:3]

    return {
        "calculated_at": report["calculated_at"],
        "total_skus_analysed": report["total_skus_analysed"],
        "growing_count": report["growing_count"],
        "declining_count": report["declining_count"],
        "stable_count": report["stable_count"],
        "high_return_count": report["high_return_count"],
        "total_overorder_risk_lei": report["total_overorder_risk_lei"],
        "top_overorder_risks": overorder,
        "top_high_return_skus": high_return,
    }


@router.get("/forecast-summary")
def get_forecast_summary():
    """
    Aggregated forecast summary for the Demand Forecasting tab.
    Returns headline KPIs, top growing/declining SKUs, and high-return SKUs.
    """
    try:
        sales_df, skus_df = _load_dataframes()
        report = calculate_demand(sales_df, skus_df)
    except Exception as e:
        log.error("Forecast summary failed: %s", e)
        raise HTTPException(status_code=500, detail="Calculation failed")

    results = report["results"]

    growing = sorted(
        [r for r in results if r["trend_status"] == "GROWING"],
        key=lambda x: x["real_demand_monthly"], reverse=True
    )[:10]

    declining = sorted(
        [r for r in results if r["trend_status"] == "DECLINING"],
        key=lambda x: abs(x["gap_lei"]), reverse=True
    )[:10]

    high_return = sorted(
        [r for r in results if r["return_flag"]],
        key=lambda x: x["return_rate"], reverse=True
    )[:10]

    return {
        "calculated_at": report["calculated_at"],
        "total_skus_analysed": report["total_skus_analysed"],
        "growing_count": report["growing_count"],
        "stable_count": report["stable_count"],
        "declining_count": report["declining_count"],
        "high_return_count": report["high_return_count"],
        "total_overorder_risk_lei": report["total_overorder_risk_lei"],
        "top_growing_skus": growing,
        "top_declining_skus": declining,
        "top_high_return_skus": high_return,
    }


@router.get("/{sku_id}")
def get_sku_demand(sku_id: str):
    """Single SKU demand profile. Used by SKU detail view and scenario simulation."""
    try:
        sales_df, skus_df = _load_dataframes()
        report = calculate_demand(sales_df, skus_df)
    except Exception as e:
        log.error("SKU demand failed: %s", e)
        raise HTTPException(status_code=500, detail="Calculation failed")

    match = next((r for r in report["results"] if r["sku_id"] == sku_id), None)
    if not match:
        raise HTTPException(status_code=404, detail="SKU not found or insufficient data")

    return match
