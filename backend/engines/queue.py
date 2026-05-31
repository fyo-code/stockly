"""
Morning Decision Queue Engine.

Aggregates outputs from all 3 engines (dead stock, supplier, demand)
into a single prioritised action list.

Each queue item follows the same structure:
  WHAT:   [SKU or Supplier] — [problem type]
  WHY:    [one sentence with the data point that triggered this]
  IMPACT: [X lei]
  ACTION: [one specific thing to do]
  STATUS: URGENT | REVIEW | INFO

Queue types:
  DEAD_STOCK           — from dead stock engine
  RETURN_WINDOW_CLOSING — from dead stock engine (supplier return window < 14 days)
  STOCKOUT_RISK        — from supplier engine (V's tool timing wrong)
  SUPPLIER_RED         — from supplier engine (reliability dropped to red)
  DEMAND_DECLINING     — from demand engine (V's tool will over-order)
  OVER_ORDER_RISK      — from demand engine (high return rate inflating demand)

Priority: financial_impact descending.
URGENT items (RETURN_WINDOW_CLOSING, STOCKOUT_RISK) float to top regardless.
"""

from datetime import datetime
from typing import TypedDict

from engines.dead_stock import DeadStockReport
from engines.supplier import SupplierReport
from engines.demand import DemandReport


# ── Types ──────────────────────────────────────────────────────────────────────

class QueueItem(TypedDict):
    queue_type: str
    what: str
    why: str
    financial_impact_lei: float
    recommended_action: str
    status: str          # URGENT | REVIEW | INFO
    sku_id: str | None
    supplier_id: str | None
    details: dict        # engine-specific extra data


class DecisionQueue(TypedDict):
    calculated_at: str
    total_items: int
    urgent_count: int
    review_count: int
    info_count: int
    total_financial_impact_lei: float
    items: list[QueueItem]


# ── Queue Builders ─────────────────────────────────────────────────────────────

def _items_from_dead_stock(report: DeadStockReport) -> list[QueueItem]:
    items: list[QueueItem] = []

    for ds in report["items"]:
        # Return window closing — most urgent
        if ds["return_window_urgent"]:
            items.append(QueueItem(
                queue_type="RETURN_WINDOW_CLOSING",
                what=f"{ds['sku_name']} — RETURN_WINDOW_CLOSING",
                why=f"Return window closes in {ds['return_window_days_remaining']} days. "
                    f"{ds['units_in_stock']} units sitting idle for {ds['days_inactive']} days.",
                financial_impact_lei=ds["capital_at_risk_lei"],
                recommended_action=f"Initiate return to supplier. Recovers {ds['budget_unlock_lei']:,.0f} lei in budget.",
                status="URGENT",
                sku_id=ds["sku_id"],
                supplier_id=ds["supplier_id"],
                details={
                    "store_id": ds["store_id"],
                    "days_inactive": ds["days_inactive"],
                    "trajectory": ds["trajectory"],
                    "return_window_days_remaining": ds["return_window_days_remaining"],
                },
            ))
        # General dead stock
        elif ds["capital_at_risk_lei"] > 5000:  # only surface items above 5k lei
            status = "REVIEW" if ds["days_inactive"] > 120 else "INFO"
            items.append(QueueItem(
                queue_type="DEAD_STOCK",
                what=f"{ds['sku_name']} — DEAD_STOCK",
                why=f"{ds['days_inactive']} days inactive, {ds['units_in_stock']} units in stock. "
                    f"Trajectory: {ds['trajectory']}.",
                financial_impact_lei=ds["capital_at_risk_lei"],
                recommended_action=(
                    f"Return window still open — {ds['return_window_days_remaining']} days remaining. Plan return."
                    if ds["return_window_open"]
                    else "Return window closed. Consider clearance sale or write-off."
                ),
                status=status,
                sku_id=ds["sku_id"],
                supplier_id=ds["supplier_id"],
                details={
                    "store_id": ds["store_id"],
                    "days_inactive": ds["days_inactive"],
                    "trajectory": ds["trajectory"],
                    "return_window_open": ds["return_window_open"],
                },
            ))

    return items


def _items_from_supplier(report: SupplierReport) -> list[QueueItem]:
    items: list[QueueItem] = []

    for sup in report["suppliers"]:
        # RED supplier
        if sup["status"] == "RED":
            items.append(QueueItem(
                queue_type="SUPPLIER_RED",
                what=f"{sup['supplier_name']} — SUPPLIER_RED",
                why=f"Reliability score dropped to {sup['reliability_score']:.0f}/100. "
                    f"Average {sup['lead_time_gap_days']:.0f} days late. Trend: {sup['trend']}.",
                financial_impact_lei=0,  # no direct lei figure — but surfaces urgency
                recommended_action="Review supplier contract. Consider backup supplier for critical SKUs.",
                status="URGENT",
                sku_id=None,
                supplier_id=sup["supplier_id"],
                details={
                    "reliability_score": sup["reliability_score"],
                    "lead_time_gap_days": sup["lead_time_gap_days"],
                    "trend": sup["trend"],
                },
            ))

        # Stockout risk from lead time gap
        for sku_risk in sup["stockout_risk_skus"]:
            items.append(QueueItem(
                queue_type="STOCKOUT_RISK",
                what=f"{sku_risk['sku_name']} — STOCKOUT_RISK",
                why=sku_risk["message"],
                financial_impact_lei=0,  # could be enriched with selling price × shortage
                recommended_action=f"Place order {sku_risk['days_overdue']:.0f} days earlier than V's tool suggests.",
                status="URGENT",
                sku_id=sku_risk["sku_id"],
                supplier_id=sup["supplier_id"],
                details={
                    "supplier_name": sup["supplier_name"],
                    "promised_lead_time_days": sku_risk["promised_lead_time_days"],
                    "actual_lead_time_days": sku_risk["actual_lead_time_days"],
                },
            ))

    return items


def _items_from_demand(report: DemandReport) -> list[QueueItem]:
    items: list[QueueItem] = []

    for d in report["results"]:
        # Declining demand — V will over-order
        if d["trend_status"] == "DECLINING" and d["gap_lei"] > 2000:
            items.append(QueueItem(
                queue_type="DEMAND_DECLINING",
                what=f"{d['sku_name']} — DEMAND_DECLINING",
                why=f"Demand declining (slope: {d['trend_slope']:.1f}/week). "
                    f"V's tool would order {d['v_tool_estimate_4_weeks']:.0f} units, "
                    f"real forecast is {d['forecast_4_weeks']:.0f}. Gap: {d['gap_units']:.0f} units.",
                financial_impact_lei=d["gap_lei"],
                recommended_action=f"Reduce order by {d['gap_units']:.0f} units. Saves {d['gap_lei']:,.0f} lei.",
                status="REVIEW",
                sku_id=d["sku_id"],
                supplier_id=None,
                details={
                    "trend_slope": d["trend_slope"],
                    "forecast_4_weeks": d["forecast_4_weeks"],
                    "v_tool_estimate": d["v_tool_estimate_4_weeks"],
                },
            ))

        # High return rate inflating demand
        if d["return_flag"] and d["gap_lei"] > 1000:
            items.append(QueueItem(
                queue_type="OVER_ORDER_RISK",
                what=f"{d['sku_name']} — OVER_ORDER_RISK",
                why=f"Return rate {d['return_rate']:.0%}. Apparent demand: "
                    f"{d['apparent_demand_monthly']:.0f}/mo, real demand: "
                    f"{d['real_demand_monthly']:.0f}/mo.",
                financial_impact_lei=d["gap_lei"],
                recommended_action="Investigate return reasons before reordering. "
                    "Possible product issue, not demand issue.",
                status="REVIEW",
                sku_id=d["sku_id"],
                supplier_id=None,
                details={
                    "return_rate": d["return_rate"],
                    "apparent_demand": d["apparent_demand_monthly"],
                    "real_demand": d["real_demand_monthly"],
                },
            ))

    return items


# ── Main Engine ────────────────────────────────────────────────────────────────

def build_decision_queue(
    dead_stock_report: DeadStockReport,
    supplier_report: SupplierReport,
    demand_report: DemandReport,
) -> DecisionQueue:
    """
    Aggregate all engine outputs into a single prioritised decision queue.

    Priority logic:
    1. URGENT items sorted by financial_impact descending
    2. REVIEW items sorted by financial_impact descending
    3. INFO items sorted by financial_impact descending
    """

    all_items: list[QueueItem] = []
    all_items.extend(_items_from_dead_stock(dead_stock_report))
    all_items.extend(_items_from_supplier(supplier_report))
    all_items.extend(_items_from_demand(demand_report))

    # Sort: URGENT first, then REVIEW, then INFO. Within each, by financial impact desc.
    priority_order = {"URGENT": 0, "REVIEW": 1, "INFO": 2}
    all_items.sort(
        key=lambda x: (priority_order.get(x["status"], 3), -x["financial_impact_lei"])
    )

    urgent = sum(1 for i in all_items if i["status"] == "URGENT")
    review = sum(1 for i in all_items if i["status"] == "REVIEW")
    info   = sum(1 for i in all_items if i["status"] == "INFO")
    total_impact = round(sum(i["financial_impact_lei"] for i in all_items), 2)

    return DecisionQueue(
        calculated_at=datetime.utcnow().isoformat(),
        total_items=len(all_items),
        urgent_count=urgent,
        review_count=review,
        info_count=info,
        total_financial_impact_lei=total_impact,
        items=all_items,
    )
