"""
Supplier Reliability Scoring Engine.

Pure function: takes DataFrames in, returns results out. No DB calls.

Per supplier calculates:
- avg promised vs actual lead times
- lead_time_gap: how many days late on average
- delivery_consistency: std dev of variance (predictability)
- trend: IMPROVING | STABLE | WORSENING (recent 6 orders vs historical)
- composite reliability score 0-100 → GREEN (>=75) | YELLOW (50-74) | RED (<50)

Critical output:
- stockout_risk_skus: SKUs where V's tool used wrong lead time,
  flagged with exact message quantifying the gap
"""

from datetime import datetime
from typing import TypedDict

import numpy as np
import pandas as pd


# ── Types ──────────────────────────────────────────────────────────────────────

class StockoutRisk(TypedDict):
    sku_id: str
    sku_name: str
    promised_lead_time_days: float
    actual_lead_time_days: float
    days_overdue: float
    message: str


class SupplierResult(TypedDict):
    supplier_id: str
    supplier_name: str
    reliability_score: float
    status: str                        # GREEN | YELLOW | RED
    avg_promised_lead_time_days: float
    avg_actual_lead_time_days: float
    lead_time_gap_days: float
    delivery_consistency_std: float
    trend: str                         # IMPROVING | STABLE | WORSENING
    recent_avg_variance_days: float
    historical_avg_variance_days: float
    order_count: int
    stockout_risk_skus: list[StockoutRisk]


class SupplierReport(TypedDict):
    calculated_at: str
    suppliers: list[SupplierResult]
    red_count: int
    yellow_count: int
    green_count: int
    total_stockout_risk_skus: int


# ── Constants ──────────────────────────────────────────────────────────────────

TREND_WORSENING_THRESHOLD = 2.0    # days delta to call WORSENING
TREND_IMPROVING_THRESHOLD = -2.0   # days delta to call IMPROVING
RECENT_ORDERS_COUNT = 6            # how many recent orders define "recent"
MIN_ORDERS_FOR_SCORING = 3         # need at least this many to score reliably
STOCKOUT_RISK_GAP_THRESHOLD = 5    # flag if actual lead time > promised by 5+ days


# ── Score Calculation ──────────────────────────────────────────────────────────

def _compute_score(
    lead_time_gap: float,
    consistency_std: float,
    trend_delta: float,
) -> float:
    """
    Composite reliability score 0-100.
    Penalises lateness (up to -40), inconsistency (up to -30), worsening trend.
    """
    score = 100.0
    score -= min(40.0, lead_time_gap * 2)
    score -= min(30.0, consistency_std * 1.5)
    score -= max(0.0, trend_delta) * 3
    return round(max(0.0, min(100.0, score)), 1)


def _score_to_status(score: float) -> str:
    if score >= 75:
        return "GREEN"
    if score >= 50:
        return "YELLOW"
    return "RED"


# ── Main Engine ────────────────────────────────────────────────────────────────

def calculate_supplier_reliability(
    orders_df: pd.DataFrame,
    suppliers_df: pd.DataFrame,
    skus_df: pd.DataFrame,
) -> SupplierReport:
    """
    Score every supplier on delivery reliability.

    Args:
        orders_df:    columns: order_id, supplier_id, sku_id, order_date,
                               promised_delivery_date, actual_delivery_date,
                               units_ordered, units_delivered
        suppliers_df: columns: supplier_id, supplier_name
        skus_df:      columns: sku_id, sku_name

    Returns:
        SupplierReport with all suppliers ranked by reliability_score asc (worst first).
    """
    orders = orders_df.copy()

    # Only score completed orders (actual delivery date known)
    orders = orders[orders["actual_delivery_date"].notna()].copy()

    if orders.empty:
        return SupplierReport(
            calculated_at=datetime.utcnow().isoformat(),
            suppliers=[],
            red_count=0, yellow_count=0, green_count=0,
            total_stockout_risk_skus=0,
        )

    # Parse dates
    for col in ["order_date", "promised_delivery_date", "actual_delivery_date"]:
        orders[col] = pd.to_datetime(orders[col])

    # Per-order metrics
    orders["promised_lead_days"] = (
        orders["promised_delivery_date"] - orders["order_date"]
    ).dt.days

    orders["actual_lead_days"] = (
        orders["actual_delivery_date"] - orders["order_date"]
    ).dt.days

    orders["delivery_variance"] = (
        orders["actual_delivery_date"] - orders["promised_delivery_date"]
    ).dt.days   # positive = late, negative = early

    # SKU name lookup
    sku_names = skus_df.set_index("sku_id")["sku_name"].to_dict()

    results: list[SupplierResult] = []

    for supplier_id, grp in orders.groupby("supplier_id"):
        if len(grp) < MIN_ORDERS_FOR_SCORING:
            continue

        grp_sorted = grp.sort_values("order_date")

        avg_promised = grp_sorted["promised_lead_days"].mean()
        avg_actual   = grp_sorted["actual_lead_days"].mean()
        lead_gap     = round(avg_actual - avg_promised, 2)
        consistency  = round(grp_sorted["delivery_variance"].std(), 2)

        # Trend: recent 6 vs historical
        recent   = grp_sorted.tail(RECENT_ORDERS_COUNT)
        historic = grp_sorted.iloc[:-RECENT_ORDERS_COUNT] if len(grp_sorted) > RECENT_ORDERS_COUNT else grp_sorted

        recent_var   = round(recent["delivery_variance"].mean(), 2)
        historic_var = round(historic["delivery_variance"].mean(), 2)
        trend_delta  = round(recent_var - historic_var, 2)

        if trend_delta > TREND_WORSENING_THRESHOLD:
            trend = "WORSENING"
        elif trend_delta < TREND_IMPROVING_THRESHOLD:
            trend = "IMPROVING"
        else:
            trend = "STABLE"

        score  = _compute_score(lead_gap, consistency if not np.isnan(consistency) else 0, trend_delta)
        status = _score_to_status(score)

        # Stockout risk: SKUs where lead time gap > threshold
        stockout_skus: list[StockoutRisk] = []
        if lead_gap > STOCKOUT_RISK_GAP_THRESHOLD:
            affected_skus = grp_sorted["sku_id"].unique()
            for sku_id in affected_skus:
                sku_name = sku_names.get(sku_id, sku_id)
                stockout_skus.append(StockoutRisk(
                    sku_id=sku_id,
                    sku_name=sku_name,
                    promised_lead_time_days=round(avg_promised, 1),
                    actual_lead_time_days=round(avg_actual, 1),
                    days_overdue=round(lead_gap, 1),
                    message=(
                        f"V's tool calculated reorder based on {round(avg_promised, 0):.0f}-day "
                        f"lead time. Actual average is {round(avg_actual, 0):.0f} days. "
                        f"This order should have been placed {round(lead_gap, 0):.0f} days earlier."
                    ),
                ))

        supplier_name = suppliers_df[
            suppliers_df["supplier_id"] == supplier_id
        ]["supplier_name"].values

        results.append(SupplierResult(
            supplier_id=str(supplier_id),
            supplier_name=str(supplier_name[0]) if len(supplier_name) > 0 else str(supplier_id),
            reliability_score=score,
            status=status,
            avg_promised_lead_time_days=round(avg_promised, 1),
            avg_actual_lead_time_days=round(avg_actual, 1),
            lead_time_gap_days=lead_gap,
            delivery_consistency_std=float(consistency) if not np.isnan(consistency) else 0.0,
            trend=trend,
            recent_avg_variance_days=recent_var,
            historical_avg_variance_days=historic_var,
            order_count=len(grp),
            stockout_risk_skus=stockout_skus,
        ))

    # Sort worst first
    results.sort(key=lambda x: x["reliability_score"])

    red    = sum(1 for r in results if r["status"] == "RED")
    yellow = sum(1 for r in results if r["status"] == "YELLOW")
    green  = sum(1 for r in results if r["status"] == "GREEN")
    total_risk = sum(len(r["stockout_risk_skus"]) for r in results)

    return SupplierReport(
        calculated_at=datetime.utcnow().isoformat(),
        suppliers=results,
        red_count=red,
        yellow_count=yellow,
        green_count=green,
        total_stockout_risk_skus=total_risk,
    )
