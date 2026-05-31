"""Forecast-time route labels for forecast engine v2.

Routes are used for diagnostics and later route-specific model selection.
They must be derivable before the target window starts.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


ROUTE_VERSION = "v2_routes_2026_05_26_stock_position"

ROUTE_ORDER = [
    "stock_constrained",
    "bf_campaign_sensitive",
    "seasonal_active",
    "seasonal_quiet",
    "sparse_intermittent",
    "lifecycle_decline",
    "available_regular",
    "proxy_available_regular",
    "dormant_or_reactivation",
    "availability_unknown",
]


def _series(frame: pd.DataFrame, column: str, default: float = 0.0) -> pd.Series:
    if column in frame.columns:
        return pd.to_numeric(frame[column], errors="coerce").fillna(default)
    return pd.Series(default, index=frame.index, dtype=float)


def add_route_labels(matrix: pd.DataFrame) -> pd.DataFrame:
    """Attach leak-safe routing labels to a feature matrix."""

    routed = matrix.copy()
    idx = routed.index
    pos_units_13w = _series(routed, "pos_units_13w")
    recent_4w_demand = pos_units_13w / 13.0 * 4.0
    active_weeks_52 = _series(routed, "active_weeks_52")
    avg_units_4w = _series(routed, "avg_units_per_4w_52")
    monthly_cv = _series(routed, "monthly_cv_104")
    top3_month_share = _series(routed, "top3_month_unit_share_104")
    active_months = _series(routed, "active_months_104")
    active_years = _series(routed, "active_years_104")
    recurring_months = _series(routed, "recurring_active_months_104")
    store_stock_observed = _series(routed, "stock_observed_prev_month")
    store_stock_prev = _series(routed, "stock_prev_month_qty")
    supplier_stock_observed = _series(routed, "supplier_stock_observed_prev_month")
    supplier_stock_prev = _series(routed, "supplier_stock_prev_month_qty")
    combined_stock_observed = _series(
        routed,
        "combined_stock_observed_prev_month",
        default=np.nan,
    )
    combined_stock_prev = _series(
        routed,
        "combined_stock_prev_month_qty",
        default=np.nan,
    )
    stock_observed = combined_stock_observed.where(combined_stock_observed.notna(), store_stock_observed)
    stock_prev = combined_stock_prev.where(combined_stock_prev.notna(), store_stock_prev)
    likely_stockout = _series(routed, "likely_true_stockout_before_target", default=np.nan)
    likely_stockout = likely_stockout.where(
        likely_stockout.notna(),
        _series(routed, "likely_stockout_before_target"),
    )
    stock_months_observed = np.maximum(
        _series(routed, "stock_months_observed_6m"),
        _series(routed, "supplier_stock_months_observed_6m"),
    )
    sales_with_low_stock = np.maximum(
        _series(routed, "sales_with_low_ending_stock"),
        _series(routed, "sales_with_low_combined_stock"),
    )
    bf_unit_share_4w = _series(routed, "bf_unit_share_4w")
    bf_txn_share_13w = _series(routed, "bf_txn_share_13w")
    target_bf = _series(routed, "target_is_bf_window")
    target_pre_bf = _series(routed, "target_is_pre_bf_4w")
    target_post_bf = _series(routed, "target_is_post_bf_4w")
    horizon_bf = _series(routed, "horizon_bf_overlap_days")
    horizon_post_bf = _series(routed, "horizon_post_bf_overlap_days")
    last4_to_roll13 = _series(routed, "last4_to_roll13")
    roll13 = _series(routed, "roll13_mean")
    seasonal52 = _series(routed, "seasonal52")
    zero_week_share_52 = 1.0 - (active_weeks_52.clip(lower=0, upper=52) / 52.0)
    avg_demand_interval_weeks = np.where(active_weeks_52 > 0, 52.0 / active_weeks_52, 999.0)

    store_or_supplier_available = _series(routed, "store_or_supplier_available_before_target")
    observed_available = (
        (stock_observed == 1)
        & (
            (stock_prev > np.maximum(1.0, recent_4w_demand * 0.75))
            | (store_or_supplier_available == 1)
            | (supplier_stock_prev > np.maximum(1.0, recent_4w_demand * 0.75))
        )
    )
    observed_constrained = (
        (stock_observed == 1)
        & (
            (likely_stockout == 1)
            | ((stock_prev <= np.maximum(1.0, recent_4w_demand * 0.5)) & (pos_units_13w > 0))
            | (sales_with_low_stock == 1)
        )
    )
    stock_unobserved = (stock_observed == 0) & (stock_months_observed == 0)
    proxy_available = (
        stock_unobserved
        & (active_weeks_52 >= 24)
        & (avg_units_4w >= 2.0)
        & (zero_week_share_52 < 0.55)
    )
    observed_unclear = (stock_observed == 1) & ~(observed_available | observed_constrained)

    stock_position_confidence = np.select(
        [observed_available, observed_constrained, observed_unclear, proxy_available, stock_unobserved],
        [
            "observed_positive_stock_position",
            "observed_low_stock_position",
            "observed_unclear_stock_position",
            "proxy_recurring_demand_no_stock_context",
            "stock_position_unobserved",
        ],
        default="stock_position_unknown",
    )
    routed["stock_position_confidence"] = stock_position_confidence
    routed["availability_confidence"] = stock_position_confidence

    routed["zero_week_share_52"] = zero_week_share_52
    routed["avg_demand_interval_weeks_52"] = avg_demand_interval_weeks
    routed["intermittency_bucket"] = np.select(
        [
            (active_weeks_52 >= 36) & (monthly_cv < 0.70),
            (active_weeks_52 >= 24) & (zero_week_share_52 < 0.55),
            (active_weeks_52 >= 10) & (zero_week_share_52 < 0.80),
            active_weeks_52 > 0,
        ],
        ["regular", "moderately_intermittent", "sparse_intermittent", "highly_intermittent"],
        default="dormant",
    )

    seasonal = (
        (active_months >= 2)
        & (active_months <= 7)
        & (top3_month_share >= 0.60)
        & (monthly_cv >= 0.90)
        & (active_years >= 2)
        & (recurring_months >= 1)
    )
    seasonal_active = seasonal & ((seasonal52 > 0) | (pos_units_13w > 0))
    seasonal_quiet = seasonal & ~seasonal_active
    bf_sensitive = (
        (target_bf == 1)
        | (target_pre_bf == 1)
        | (target_post_bf == 1)
        | (horizon_bf > 0)
        | (horizon_post_bf > 0)
        | (bf_unit_share_4w >= 0.35)
        | (bf_txn_share_13w >= 0.20)
    )
    dormant_reactivation = (active_weeks_52 <= 4) & ((seasonal52 > 0) | (pos_units_13w > 0))
    sparse = (
        routed["intermittency_bucket"].isin(["sparse_intermittent", "highly_intermittent"])
        | ((avg_units_4w < 3.0) & (zero_week_share_52 >= 0.45))
    ) & ~dormant_reactivation
    lifecycle_decline = (
        (roll13 >= 2.0)
        & (last4_to_roll13 < 0.50)
        & (seasonal52 <= np.maximum(1.0, roll13 * 0.50))
        & ~seasonal
    )
    available_regular = observed_available & ~sparse
    proxy_available_regular = proxy_available & ~sparse & (avg_units_4w >= 2.0)

    route = pd.Series("availability_unknown", index=idx, dtype=object)
    route_reason = pd.Series("insufficient reliable pre-target signal", index=idx, dtype=object)
    route_signal_status = pd.Series("unknown", index=idx, dtype=object)
    routed["calendar_route_context"] = np.select(
        [
            target_bf == 1,
            target_post_bf == 1,
            target_pre_bf == 1,
            horizon_bf > 0,
            horizon_post_bf > 0,
        ],
        ["bf_window", "post_bf_window", "pre_bf_window", "horizon_overlaps_bf", "horizon_overlaps_post_bf"],
        default="normal_calendar",
    )
    routed["sku_bf_contamination_context"] = np.select(
        [
            bf_unit_share_4w >= 0.35,
            bf_txn_share_13w >= 0.20,
        ],
        ["recent_units_bf_contaminated", "recent_transactions_bf_contaminated"],
        default="no_bf_contamination_signal",
    )

    def assign(mask: pd.Series, label: str, reason: str, status: str) -> None:
        open_mask = mask & (route == "availability_unknown")
        route.loc[open_mask] = label
        route_reason.loc[open_mask] = reason
        route_signal_status.loc[open_mask] = status

    assign(observed_constrained, "stock_constrained", "observed prior stock is low/zero versus recent demand; not a sellability gate", "observed")
    assign(bf_sensitive, "bf_campaign_sensitive", "BF/pre-BF/post-BF calendar or BF-contaminated recent history", "inferred")
    assign(seasonal_active, "seasonal_active", "seasonal SKU appears active for the target period", "inferred")
    assign(seasonal_quiet, "seasonal_quiet", "seasonal SKU appears outside active demand period", "inferred")
    assign(dormant_reactivation, "dormant_or_reactivation", "mostly dormant SKU with recent or seasonal reactivation evidence", "inferred")
    assign(sparse, "sparse_intermittent", "low occurrence / high zero-week-share demand pattern", "inferred")
    assign(lifecycle_decline, "lifecycle_decline", "recent demand is materially below rolling demand and seasonal analog", "inferred")
    assign(available_regular, "available_regular", "positive stock position observed with recurring demand signal; SKU may still sell without this stock", "observed")
    assign(proxy_available_regular, "proxy_available_regular", "recurring demand signal with no hard stock-position constraint", "proxy")

    routed["primary_route"] = route
    routed["route_reason"] = route_reason
    routed["route_signal_status"] = route_signal_status
    routed["scoring_policy_routed"] = routed["primary_route"].map(
        {
            "available_regular": "stock_position_regular_quantity",
            "proxy_available_regular": "proxy_stock_position_regular_quantity",
            "stock_constrained": "low_stock_position_context_quantity",
            "bf_campaign_sensitive": "campaign_sensitive_quantity",
            "seasonal_active": "seasonal_active_quantity",
            "seasonal_quiet": "seasonal_quiet_phantom_reactivation",
            "sparse_intermittent": "intermittent_sale_then_quantity",
            "lifecycle_decline": "lifecycle_decline_quantity",
            "dormant_or_reactivation": "reactivation_detection",
            "availability_unknown": "low_stock_position_confidence_quantity",
        }
    )
    routed["route_version"] = ROUTE_VERSION
    return routed
