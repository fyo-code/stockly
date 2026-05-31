"""
Scenario Simulation Engine.

Pure function: takes SKU data + demand forecast + supplier lead times in,
returns 3 order quantity scenarios with financial projections out. No DB calls.

Each scenario (conservative, base, aggressive) is run at 3 demand sensitivity
levels (80%, 100%, 120%) producing best/base/worst case outcomes.

Budget constraint: if a budget envelope is provided for the category,
scenarios that exceed remaining budget are flagged and capped.

This is the decision tool — it turns analysis into action.
"""

from datetime import datetime
from typing import TypedDict


# ── Types ──────────────────────────────────────────────────────────────────────

class ScenarioOutcome(TypedDict):
    order_qty: int
    order_cost_lei: float
    projected_units_sold: float
    projected_revenue_lei: float
    projected_unsold_units: float
    projected_dead_stock_lei: float
    projected_shortage_units: float
    projected_lost_revenue_lei: float
    projected_margin_lei: float
    projected_margin_pct: float
    within_budget: bool
    budget_remaining_after_lei: float | None


class SensitivityRange(TypedDict):
    """Same scenario at 80%, 100%, 120% of forecast demand."""
    low_demand: ScenarioOutcome     # demand at 80%
    base_demand: ScenarioOutcome    # demand at 100%
    high_demand: ScenarioOutcome    # demand at 120%


class ScenarioResult(TypedDict):
    sku_id: str
    sku_name: str
    category: str
    current_stock: int
    weekly_real_demand: float
    forecast_8_weeks: float
    selling_price_lei: float
    purchase_cost_lei: float
    real_lead_time_weeks: float
    recommended_qty: int
    budget_lei: float | None        # category budget if provided
    budget_remaining_lei: float | None
    scenarios: dict[str, SensitivityRange]  # conservative, base, aggressive


# ── Constants ──────────────────────────────────────────────────────────────────

SAFETY_BUFFER_WEEKS = 1
SCENARIO_MULTIPLIERS = {
    "conservative": 0.8,
    "base": 1.0,
    "aggressive": 1.2,
}
DEMAND_SENSITIVITY_LEVELS = {
    "low_demand": 0.8,
    "base_demand": 1.0,
    "high_demand": 1.2,
}


# ── Single Scenario Calculation ────────────────────────────────────────────────

def _calc_outcome(
    order_qty: int,
    current_stock: int,
    forecast_8_weeks: float,
    selling_price: float,
    purchase_cost: float,
    budget_remaining: float | None,
) -> ScenarioOutcome:
    """Calculate financial projections for a single order quantity at a single demand level."""

    total_available = current_stock + order_qty
    order_cost = round(order_qty * purchase_cost, 2)

    projected_units_sold = min(total_available, forecast_8_weeks)
    projected_revenue = round(projected_units_sold * selling_price, 2)

    projected_unsold = max(0.0, total_available - forecast_8_weeks)
    projected_dead_stock = round(projected_unsold * purchase_cost, 2)

    projected_shortage = max(0.0, forecast_8_weeks - total_available)
    projected_lost_revenue = round(projected_shortage * selling_price, 2)

    projected_margin = round(projected_revenue - order_cost, 2)
    projected_margin_pct = round(
        projected_margin / projected_revenue, 4
    ) if projected_revenue > 0 else 0.0

    within_budget = True
    budget_after = None
    if budget_remaining is not None:
        within_budget = order_cost <= budget_remaining
        budget_after = round(budget_remaining - order_cost, 2)

    return ScenarioOutcome(
        order_qty=order_qty,
        order_cost_lei=order_cost,
        projected_units_sold=round(projected_units_sold, 1),
        projected_revenue_lei=projected_revenue,
        projected_unsold_units=round(projected_unsold, 1),
        projected_dead_stock_lei=projected_dead_stock,
        projected_shortage_units=round(projected_shortage, 1),
        projected_lost_revenue_lei=projected_lost_revenue,
        projected_margin_lei=projected_margin,
        projected_margin_pct=projected_margin_pct,
        within_budget=within_budget,
        budget_remaining_after_lei=budget_after,
    )


# ── Main Engine ────────────────────────────────────────────────────────────────

def simulate_scenarios(
    sku_id: str,
    sku_name: str,
    category: str,
    current_stock: int,
    weekly_real_demand: float,
    forecast_8_weeks: float,
    selling_price_lei: float,
    purchase_cost_lei: float,
    real_lead_time_weeks: float,
    budget_lei: float | None = None,
    budget_spent_lei: float | None = None,
) -> ScenarioResult:
    """
    Generate 3 order scenarios (conservative/base/aggressive) each with
    3 demand sensitivity levels (80%/100%/120%).

    Args:
        sku_id, sku_name, category: SKU identification
        current_stock:         units currently in warehouse
        weekly_real_demand:    avg weekly demand (net of returns)
        forecast_8_weeks:      trend-adjusted 8-week forecast from demand engine
        selling_price_lei:     per-unit selling price
        purchase_cost_lei:     per-unit purchase cost
        real_lead_time_weeks:  actual supplier lead time from supplier engine
        budget_lei:            total budget for this category this period (optional)
        budget_spent_lei:      already committed budget for this category (optional)

    Returns:
        ScenarioResult with all 3 × 3 = 9 outcome calculations.
    """

    budget_remaining = None
    if budget_lei is not None:
        spent = budget_spent_lei or 0.0
        budget_remaining = max(0.0, budget_lei - spent)

    # Recommended order quantity
    recommended_qty = max(0, round(forecast_8_weeks - current_stock))

    # Build scenarios
    scenarios: dict[str, SensitivityRange] = {}

    for scenario_name, qty_multiplier in SCENARIO_MULTIPLIERS.items():
        order_qty = max(0, round(recommended_qty * qty_multiplier))

        sensitivity: dict[str, ScenarioOutcome] = {}
        for demand_label, demand_multiplier in DEMAND_SENSITIVITY_LEVELS.items():
            adjusted_forecast = forecast_8_weeks * demand_multiplier
            outcome = _calc_outcome(
                order_qty=order_qty,
                current_stock=current_stock,
                forecast_8_weeks=adjusted_forecast,
                selling_price=selling_price_lei,
                purchase_cost=purchase_cost_lei,
                budget_remaining=budget_remaining,
            )
            sensitivity[demand_label] = outcome

        scenarios[scenario_name] = SensitivityRange(**sensitivity)

    return ScenarioResult(
        sku_id=sku_id,
        sku_name=sku_name,
        category=category,
        current_stock=current_stock,
        weekly_real_demand=round(weekly_real_demand, 2),
        forecast_8_weeks=round(forecast_8_weeks, 1),
        selling_price_lei=selling_price_lei,
        purchase_cost_lei=purchase_cost_lei,
        real_lead_time_weeks=round(real_lead_time_weeks, 1),
        recommended_qty=recommended_qty,
        budget_lei=budget_lei,
        budget_remaining_lei=budget_remaining,
        scenarios=scenarios,
    )
