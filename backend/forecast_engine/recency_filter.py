"""Recency filter — skip SKUs silent for the last N weeks (Iter 3 Fix #5).

Iter 2 root cause: 4,217 of 6,358 predicted A-tier SKUs sold nothing in the
Jan-Feb 2025 window. ABC tier classification (built from full-history revenue)
doesn't predict future activity — long-tail SKUs that went silent months ago
were still being forecast and inflating bias. This filter drops them before
forecasting and re-attaches them to the output as explicit zero-forecasts so
downstream consumers can distinguish "silent" from "missing".
"""

from __future__ import annotations

import logging
from datetime import datetime

import pandas as pd


log = logging.getLogger(__name__)

# Default threshold sits in the middle of the agreed 8-12 week range.
RECENCY_WEEKS = 10


def split_active_silent(
    weekly: pd.DataFrame,
    weeks: int = RECENCY_WEEKS,
    sku_col: str = "sku_id",
    store_col: str = "store_id",
    date_col: str = "week_start_date",
    sales_col: str = "net_sold",
) -> tuple[pd.DataFrame, list[tuple[str, str]]]:
    """Split weekly data into (active_df, silent_keys).

    A (sku, store) is silent if its sum of net_sold across the most recent
    `weeks` weeks of the training window is zero.

    Returns:
        active_df: weekly rows for SKUs that had any sales in the recency window.
        silent_keys: list of (sku_id, store_id) tuples that were filtered out.
    """
    df = weekly.copy()
    if not pd.api.types.is_datetime64_any_dtype(df[date_col]):
        df[date_col] = pd.to_datetime(df[date_col])

    if df.empty:
        return df, []

    cutoff = df[date_col].max() - pd.Timedelta(weeks=weeks - 1)
    recent = df[df[date_col] >= cutoff]

    # All (sku, store) pairs that appear anywhere in training data
    all_pairs = df[[sku_col, store_col]].drop_duplicates()

    recent_totals = (
        recent.groupby([sku_col, store_col])[sales_col]
        .sum()
        .reset_index()
    )

    # Merge to find pairs with no rows in recent window (truly absent = zero sales)
    merged = all_pairs.merge(recent_totals, on=[sku_col, store_col], how="left")
    merged[sales_col] = merged[sales_col].fillna(0)
    silent_pairs = merged[merged[sales_col] <= 0][[sku_col, store_col]]
    silent_keys = [(str(s), str(st)) for s, st in silent_pairs.itertuples(index=False, name=None)]

    if not silent_keys:
        return df, []

    silent_set = set(silent_keys)
    mask = [
        (str(s), str(st)) not in silent_set
        for s, st in zip(df[sku_col], df[store_col])
    ]
    active_df = df[mask].reset_index(drop=True)

    log.info(
        "Recency filter: %d (sku, store) pairs silent in last %d weeks → excluded from forecasting; "
        "%d active pairs retained.",
        len(silent_keys), weeks, active_df[[sku_col, store_col]].drop_duplicates().shape[0],
    )

    return active_df, silent_keys


def silent_zero_forecasts(
    silent_keys: list[tuple[str, str]],
    weeks: int = RECENCY_WEEKS,
) -> list[dict]:
    """Construct zero-forecast ensemble rows for silent SKUs so they remain
    in the output (flagged) instead of disappearing.
    """
    now_iso = datetime.utcnow().isoformat(timespec="seconds")
    rows: list[dict] = []
    for sku, store in silent_keys:
        rows.append({
            "sku_id": sku,
            "store_id": store,
            "forecast_4w": 0.0,
            "forecast_8w": 0.0,
            "confidence_low_4w": 0.0,
            "confidence_high_4w": 0.0,
            "confidence_low_8w": 0.0,
            "confidence_high_8w": 0.0,
            "method_breakdown": {},
            "methods_succeeded": 0,
            "methods_failed": 0,
            "method_disagreement_4w": "LOW",
            "method_disagreement_8w": "LOW",
            "aggregation_method": "recency_filter",
            "generated_at": now_iso,
            "silent_filter_applied": True,
            "silent_window_weeks": weeks,
        })
    return rows
