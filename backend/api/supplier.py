"""
Supplier Reliability API routes.

Endpoints:
  GET /api/suppliers          — full supplier scoreboard ranked by reliability
  GET /api/suppliers/stockout — all SKUs at stockout risk across all suppliers
  GET /api/suppliers/{id}     — single supplier detail
"""

import logging

import pandas as pd
from fastapi import APIRouter, HTTPException

from db import get_conn
from engines.supplier import calculate_supplier_reliability

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/suppliers", tags=["suppliers"])


def _load_dataframes():
    conn = get_conn()
    try:
        orders_df    = pd.read_sql("SELECT * FROM supplier_orders", conn)
        suppliers_df = pd.read_sql("SELECT supplier_id, supplier_name FROM suppliers", conn)
        skus_df      = pd.read_sql("SELECT sku_id, sku_name FROM skus", conn)
    finally:
        conn.close()
    return orders_df, suppliers_df, skus_df


@router.get("")
def get_supplier_scoreboard():
    """
    Full supplier scoreboard sorted worst → best.
    Used by the supplier scoreboard UI panel.
    """
    try:
        orders_df, suppliers_df, skus_df = _load_dataframes()
        report = calculate_supplier_reliability(orders_df, suppliers_df, skus_df)
    except Exception as e:
        log.error("Supplier reliability failed: %s", e)
        raise HTTPException(status_code=500, detail="Calculation failed")

    return {
        "calculated_at": report["calculated_at"],
        "red_count": report["red_count"],
        "yellow_count": report["yellow_count"],
        "green_count": report["green_count"],
        "total_stockout_risk_skus": report["total_stockout_risk_skus"],
        "suppliers": [
            {
                "supplier_id": s["supplier_id"],
                "supplier_name": s["supplier_name"],
                "reliability_score": s["reliability_score"],
                "status": s["status"],
                "avg_promised_lead_time_days": s["avg_promised_lead_time_days"],
                "avg_actual_lead_time_days": s["avg_actual_lead_time_days"],
                "lead_time_gap_days": s["lead_time_gap_days"],
                "trend": s["trend"],
                "order_count": s["order_count"],
                "stockout_risk_count": len(s["stockout_risk_skus"]),
            }
            for s in report["suppliers"]
        ],
    }


@router.get("/stockout")
def get_stockout_risks():
    """
    All SKUs at stockout risk because V's tool used wrong lead time.
    Used by the morning decision queue for STOCKOUT_RISK alerts.
    """
    try:
        orders_df, suppliers_df, skus_df = _load_dataframes()
        report = calculate_supplier_reliability(orders_df, suppliers_df, skus_df)
    except Exception as e:
        log.error("Stockout risk failed: %s", e)
        raise HTTPException(status_code=500, detail="Calculation failed")

    risks = []
    for s in report["suppliers"]:
        for sku in s["stockout_risk_skus"]:
            risks.append({
                "supplier_id": s["supplier_id"],
                "supplier_name": s["supplier_name"],
                "supplier_status": s["status"],
                **sku,
            })

    return {
        "calculated_at": report["calculated_at"],
        "total_at_risk": len(risks),
        "risks": risks,
    }


@router.get("/{supplier_id}")
def get_supplier_detail(supplier_id: str):
    """Single supplier full detail including all stockout risk SKUs."""
    try:
        orders_df, suppliers_df, skus_df = _load_dataframes()
        report = calculate_supplier_reliability(orders_df, suppliers_df, skus_df)
    except Exception as e:
        log.error("Supplier detail failed: %s", e)
        raise HTTPException(status_code=500, detail="Calculation failed")

    match = next((s for s in report["suppliers"] if s["supplier_id"] == supplier_id), None)
    if not match:
        raise HTTPException(status_code=404, detail="Supplier not found")

    return match
