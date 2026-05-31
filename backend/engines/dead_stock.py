"""
Dead Stock Detection Engine.

Pure function: takes DataFrames in, returns results out. No DB calls.

Outputs per SKU per store:
- days_inactive: days since last real sale (net of returns)
- capital_at_risk_lei: units_in_stock × purchase_cost
- dead_stock_score: days_inactive × capital_at_risk (priority ranking)
- trajectory: SUDDEN_STOP | LIFECYCLE_DECLINE | NEVER_MOVED
- return_window_open: whether supplier return window is still open
- return_window_days_remaining: days until window closes
- return_window_urgent: True if < 14 days remaining
- budget_unlock_lei: capital that would be freed if returned to supplier
"""

from datetime import date, datetime
from typing import TypedDict

import numpy as np
import pandas as pd


# ── Types ──────────────────────────────────────────────────────────────────────

class DeadStockItem(TypedDict):
    sku_id: str
    sku_name: str
    store_id: str
    category: str
    supplier_id: str
    days_inactive: int
    units_in_stock: int
    purchase_cost_lei: float
    capital_at_risk_lei: float
    dead_stock_score: float
    trajectory: str
    return_window_open: bool
    return_window_days_remaining: int | None
    return_window_urgent: bool
    budget_unlock_lei: float


class DeadStockReport(TypedDict):
    calculated_at: str
    total_dead_stock_lei: float
    total_budget_unlock_lei: float
    items: list[DeadStockItem]
    sku_count: int
    urgent_return_count: int


# ── Constants ──────────────────────────────────────────────────────────────────

INACTIVE_THRESHOLD_DAYS = 60       # SKU inactive for 60+ days = dead stock
RETURN_WINDOW_URGENT_DAYS = 14     # Flag when < 14 days left to return
NEVER_MOVED_MAX_LIFETIME_UNITS = 5 # Lifetime sales below this = NEVER_MOVED
SUDDEN_STOP_LOOKBACK_WEEKS = 12    # How far back to look for "was selling"
SUDDEN_STOP_ACTIVE_WEEKS = 8       # Must have sold in at least this many weeks to qualify


# ── Trajectory Classification ──────────────────────────────────────────────────

def _classify_trajectory(
    sku_id: str,
    store_id: str,
    sales_df: pd.DataFrame,
    as_of: date,
) -> str:
    """
    Classify why a SKU stopped selling.
    Requires columns: sku_id, store_id, sale_date, units_sold, units_returned
    """
    sku_sales = sales_df[
        (sales_df["sku_id"] == sku_id) & (sales_df["store_id"] == store_id)
    ].copy()

    if sku_sales.empty:
        return "NEVER_MOVED"

    sku_sales["sale_date"] = pd.to_datetime(sku_sales["sale_date"])
    sku_sales["net_sold"] = sku_sales["units_sold"] - sku_sales["units_returned"]

    total_lifetime = sku_sales["net_sold"].sum()
    if total_lifetime <= NEVER_MOVED_MAX_LIFETIME_UNITS:
        return "NEVER_MOVED"

    # Weekly sales — was it selling steadily before stopping?
    sku_sales = sku_sales.set_index("sale_date").sort_index()
    weekly = sku_sales["net_sold"].resample("W").sum()

    cutoff = pd.Timestamp(as_of) - pd.Timedelta(weeks=SUDDEN_STOP_LOOKBACK_WEEKS)
    recent = weekly[weekly.index >= cutoff]

    if recent.empty:
        return "LIFECYCLE_DECLINE"

    weeks_with_sales = (recent > 0).sum()

    # Was actively selling in many weeks before going quiet?
    if weeks_with_sales >= SUDDEN_STOP_ACTIVE_WEEKS:
        return "SUDDEN_STOP"

    return "LIFECYCLE_DECLINE"


# ── Return Window ──────────────────────────────────────────────────────────────

def _return_window_status(
    last_delivery_date: str | None,
    return_window_days: int,
    as_of: date,
) -> tuple[bool, int | None, bool]:
    """
    Returns (is_open, days_remaining, is_urgent).
    Window starts from last delivery date.
    """
    if not last_delivery_date:
        return False, None, False

    try:
        delivery = datetime.strptime(last_delivery_date, "%Y-%m-%d").date()
    except ValueError:
        return False, None, False

    window_closes = delivery + pd.Timedelta(days=return_window_days)
    window_closes_date = window_closes.date() if hasattr(window_closes, "date") else window_closes
    days_remaining = (window_closes_date - as_of).days

    if days_remaining <= 0:
        return False, 0, False

    is_urgent = days_remaining <= RETURN_WINDOW_URGENT_DAYS
    return True, days_remaining, is_urgent


# ── Main Engine ────────────────────────────────────────────────────────────────

def calculate_dead_stock(
    sales_df: pd.DataFrame,
    inventory_df: pd.DataFrame,
    skus_df: pd.DataFrame,
    suppliers_df: pd.DataFrame,
    as_of: date | None = None,
) -> DeadStockReport:
    """
    Identify dead stock across all SKUs and stores.

    Args:
        sales_df:      columns: sku_id, store_id, sale_date, units_sold, units_returned
        inventory_df:  columns: sku_id, store_id, units_in_stock, last_delivery_date, supplier_id
        skus_df:       columns: sku_id, sku_name, category, supplier_id, purchase_cost_lei
        suppliers_df:  columns: supplier_id, default_return_window_days
        as_of:         reference date (defaults to today)

    Returns:
        DeadStockReport with all dead stock items ranked by dead_stock_score desc.
    """
    if as_of is None:
        as_of = date.today()

    # Compute last sale date per sku+store (only where net_sold > 0)
    sales = sales_df.copy()
    sales["sale_date"] = pd.to_datetime(sales["sale_date"])
    sales["net_sold"] = sales["units_sold"] - sales["units_returned"].fillna(0)

    last_sale = (
        sales[sales["net_sold"] > 0]
        .groupby(["sku_id", "store_id"])["sale_date"]
        .max()
        .reset_index()
        .rename(columns={"sale_date": "last_sale_date"})
    )

    # Join inventory with last sale
    inv = inventory_df.merge(last_sale, on=["sku_id", "store_id"], how="left")

    # Only consider rows with stock > 0
    inv = inv[inv["units_in_stock"] > 0].copy()

    # Calculate days inactive
    as_of_ts = pd.Timestamp(as_of)
    inv["last_sale_date"] = pd.to_datetime(inv["last_sale_date"])
    inv["days_inactive"] = (as_of_ts - inv["last_sale_date"]).dt.days.fillna(9999).astype(int)

    # Filter to inactive threshold
    dead = inv[inv["days_inactive"] >= INACTIVE_THRESHOLD_DAYS].copy()

    if dead.empty:
        return DeadStockReport(
            calculated_at=datetime.utcnow().isoformat(),
            total_dead_stock_lei=0.0,
            total_budget_unlock_lei=0.0,
            items=[],
            sku_count=0,
            urgent_return_count=0,
        )

    # Join SKU info
    dead = dead.merge(
        skus_df[["sku_id", "sku_name", "category", "supplier_id", "purchase_cost_lei"]],
        on="sku_id",
        how="left",
        suffixes=("", "_sku"),
    )

    # Use supplier_id from inventory if available, else from skus
    dead["supplier_id"] = dead["supplier_id"].fillna(dead.get("supplier_id_sku", ""))

    # Join supplier return window
    dead = dead.merge(
        suppliers_df[["supplier_id", "default_return_window_days"]],
        on="supplier_id",
        how="left",
    )
    dead["default_return_window_days"] = dead["default_return_window_days"].fillna(90).astype(int)

    # Calculate financials
    dead["capital_at_risk_lei"] = (
        dead["units_in_stock"] * dead["purchase_cost_lei"]
    ).round(2)
    dead["dead_stock_score"] = (
        dead["days_inactive"] * dead["capital_at_risk_lei"]
    ).round(2)

    # Build result items
    items: list[DeadStockItem] = []

    for _, row in dead.iterrows():
        is_open, days_remaining, is_urgent = _return_window_status(
            row.get("last_delivery_date"),
            int(row["default_return_window_days"]),
            as_of,
        )
        budget_unlock = float(row["capital_at_risk_lei"]) if is_open else 0.0
        trajectory = _classify_trajectory(
            row["sku_id"], row["store_id"], sales_df, as_of
        )

        items.append(DeadStockItem(
            sku_id=row["sku_id"],
            sku_name=str(row.get("sku_name", "")),
            store_id=row["store_id"],
            category=str(row.get("category", "")),
            supplier_id=str(row.get("supplier_id", "")),
            days_inactive=int(row["days_inactive"]),
            units_in_stock=int(row["units_in_stock"]),
            purchase_cost_lei=float(row["purchase_cost_lei"]),
            capital_at_risk_lei=float(row["capital_at_risk_lei"]),
            dead_stock_score=float(row["dead_stock_score"]),
            trajectory=trajectory,
            return_window_open=is_open,
            return_window_days_remaining=days_remaining,
            return_window_urgent=is_urgent,
            budget_unlock_lei=budget_unlock,
        ))

    # Sort by score descending
    items.sort(key=lambda x: x["dead_stock_score"], reverse=True)

    total_lei = round(sum(i["capital_at_risk_lei"] for i in items), 2)
    budget_unlock = round(sum(i["budget_unlock_lei"] for i in items), 2)
    urgent_count = sum(1 for i in items if i["return_window_urgent"])

    return DeadStockReport(
        calculated_at=datetime.utcnow().isoformat(),
        total_dead_stock_lei=total_lei,
        total_budget_unlock_lei=budget_unlock,
        items=items,
        sku_count=len(set(i["sku_id"] for i in items)),
        urgent_return_count=urgent_count,
    )
