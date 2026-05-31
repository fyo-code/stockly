"""Iter 4 Phase B.3 — per-category method routing.

Why this exists:
    The Iter 3 windowed scoreboard showed that some methods are good
    globally but bad on specific categories. ACCESORII alone concentrates
    77% of the engine's residual error, and on ACCESORII specifically:
      - Anomaly-Adjusted: 1.3% hit ±20% rate
      - Category-Relative: 37.9% win-rate vs naive
    Both methods drag the median ensemble for ACCESORII SKUs.

    Removing them globally (Phase B.1) regressed the engine on other
    categories. Removing them only for ACCESORII (this phase) addresses
    the local problem without breaking global accuracy.

Rules format:
    Mapping of category name (case-sensitive, matches the `category` column
    in `weekly_demand`) to a set of method names that are ALLOWED to vote
    for SKUs in that category. SKUs in any category not listed here use
    the full method pool (default behaviour).

Tunability:
    Resist the temptation to add many categories at once. With only 6
    backtest windows, every routing rule is a hypothesis that can overfit.
    Iter 4 v1: ACCESORII only. Add more categories in later iterations as
    the per-window-per-category scoreboard accumulates evidence.
"""

from __future__ import annotations


# All known method names. Used as the default-allowed set for any category
# that doesn't appear in CATEGORY_ROUTING_RULES.
ALL_METHODS: frozenset[str] = frozenset({
    "ets",
    "anomaly_adjusted",
    "multi_scale_lag",
    "calendar_events",
    "category_relative",
    "crostons",
    "naive_seasonal",
    "lightgbm",
})


CATEGORY_ROUTING_RULES: dict[str, frozenset[str]] = {
    # B.3 REJECTED: ACCESORII routing regressed 4/6 windows (mean WMAPE 82.0% vs
    # 78.1% baseline). Shrinking the median pool hurts even when removed methods
    # score poorly on the category — same lesson as B.1. Rules kept here for
    # reference; no entries active.
}


def select_methods_for_category(category: str | None) -> frozenset[str]:
    """Return the set of methods allowed for SKUs in the given category.

    Args:
        category: Category name as it appears in the `weekly_demand.category`
            column. Case-sensitive. None or empty returns the full method pool.

    Returns:
        Frozen set of method names that may vote for SKUs in this category.
    """
    if not category:
        return ALL_METHODS
    return CATEGORY_ROUTING_RULES.get(category, ALL_METHODS)


def routing_label_for_category(category: str | None) -> str:
    """Human-readable label for which routing rule fired (for audit logs).

    Returns "default" if no category-specific rule applies.
    """
    if not category:
        return "default"
    if category in CATEGORY_ROUTING_RULES:
        return f"category={category}"
    return "default"
