"""Category-driven relative performance forecaster (Method 3).

Forecasts SKU demand by combining category-level trends with the SKU's
share of its category. Captures market dynamics: if the whole category is
growing, individual SKUs should grow too — and deviations from that
expectation are flagged.

Formula:
    SKU_Forecast = Category_Forecast × SKU_Share_of_Category

Requirements:
- Weekly demand data with a category column
- At least 8 weeks of history per SKU-store
- At least 2 SKUs per category for meaningful share calculation
"""

from typing import Optional

import numpy as np
import pandas as pd

from ..data_models import CategoryRelativeResult


# --- Configuration ---

MIN_WEEKS_REQUIRED = 8
RECENT_WINDOW = 4       # weeks for "recent" rolling averages
BASELINE_WINDOW = 52    # weeks for YoY baseline (or all available)
TREND_THRESHOLD = 0.03  # ±3% YoY → STABLE


# --- Forecaster ---


class CategoryRelativeForecaster:
    """Forecaster that derives SKU demand from category-level dynamics.

    Steps:
    1. Aggregate category-level weekly sales
    2. Compute category YoY growth ratio
    3. Project category forward
    4. Determine each SKU's share of its category
    5. SKU forecast = category forecast × SKU share
    6. Compare actual SKU trend to expected (category-implied) trend
    """

    def __init__(
        self,
        min_weeks: int = MIN_WEEKS_REQUIRED,
        recent_window: int = RECENT_WINDOW,
        baseline_window: int = BASELINE_WINDOW,
        trend_threshold: float = TREND_THRESHOLD,
    ):
        self._min_weeks = min_weeks
        self._recent_window = recent_window
        self._baseline_window = baseline_window
        self._trend_threshold = trend_threshold

    def forecast(
        self,
        weekly_demand: pd.DataFrame,
        sku_id: str,
        store_id: str,
        category_id: str,
        sku_col: str = "sku_id",
        store_col: str = "store_id",
        category_col: str = "category_id",
        date_col: str = "week_start_date",
        sales_col: str = "net_sold",
    ) -> CategoryRelativeResult:
        """Produce a category-relative forecast for one SKU-store.

        Args:
            weekly_demand: Full DataFrame (all SKUs, all stores).
            sku_id: Target SKU.
            store_id: Target store.
            category_id: Category the SKU belongs to.
            sku_col, store_col, category_col, date_col, sales_col: Column names.

        Returns:
            CategoryRelativeResult with forecasts and relative-performance metrics.
        """
        df = weekly_demand.copy()
        if not pd.api.types.is_datetime64_any_dtype(df[date_col]):
            df[date_col] = pd.to_datetime(df[date_col])

        # --- Category-level aggregation ---
        cat_mask = df[category_col] == category_id
        cat_df = df.loc[cat_mask].copy()

        cat_weekly = (
            cat_df.groupby(date_col)[sales_col]
            .sum()
            .sort_index()
        )

        if len(cat_weekly) < self._min_weeks:
            return self._error_result(
                sku_id, store_id, 0,
                f"Category {category_id}: insufficient history "
                f"({len(cat_weekly)} weeks, need {self._min_weeks})",
            )

        # --- SKU-store history ---
        sku_mask = (df[sku_col] == sku_id) & (df[store_col] == store_id)
        sku_df = df.loc[sku_mask].sort_values(date_col)
        n_weeks = len(sku_df)

        if n_weeks < self._min_weeks:
            return self._error_result(
                sku_id, store_id, n_weeks,
                f"Insufficient SKU history: {n_weeks} weeks (need {self._min_weeks})",
            )

        # --- Category forecast ---
        cat_recent_avg = float(cat_weekly.iloc[-self._recent_window:].mean())
        baseline_len = min(self._baseline_window, len(cat_weekly))
        cat_baseline_avg = float(cat_weekly.iloc[-baseline_len:].mean())

        # YoY ratio: compare recent window to same-length window 52 weeks ago
        if len(cat_weekly) >= 52 + self._recent_window:
            cat_yoy_window = cat_weekly.iloc[-(52 + self._recent_window):-52]
            cat_yoy_avg = float(cat_yoy_window.mean()) if len(cat_yoy_window) > 0 else cat_baseline_avg
        else:
            cat_yoy_avg = cat_baseline_avg

        cat_yoy_ratio = (
            cat_recent_avg / cat_yoy_avg if cat_yoy_avg > 0 else 1.0
        )

        # Category forecast = recent average × YoY growth, projected forward
        cat_forecast_weekly = cat_recent_avg * cat_yoy_ratio
        cat_forecast_4w = cat_forecast_weekly * 4
        cat_forecast_8w = cat_forecast_weekly * 8

        # Category trend classification
        if cat_yoy_ratio > 1.0 + self._trend_threshold:
            cat_trend = "GROWING"
        elif cat_yoy_ratio < 1.0 - self._trend_threshold:
            cat_trend = "DECLINING"
        else:
            cat_trend = "STABLE"

        # --- SKU share of category ---
        # Use recent window for share calculation
        sku_recent = sku_df.iloc[-self._recent_window:]
        sku_recent_total = float(sku_recent[sales_col].sum())

        # Category total over same date range
        recent_dates = sku_recent[date_col].values
        cat_recent_total = float(
            cat_df.loc[cat_df[date_col].isin(recent_dates), sales_col].sum()
        )

        sku_share = (
            sku_recent_total / cat_recent_total
            if cat_recent_total > 0 else 0.0
        )

        # --- SKU forecast ---
        forecast_4w = cat_forecast_4w * sku_share
        forecast_8w = cat_forecast_8w * sku_share

        # --- SKU performance vs category ---
        # If SKU grew at the same rate as category, what would we expect?
        sku_recent_avg = float(sku_recent[sales_col].mean())

        if n_weeks >= 52 + self._recent_window:
            sku_yoy_window = sku_df.iloc[-(52 + self._recent_window):-52]
            sku_yoy_avg = float(sku_yoy_window[sales_col].mean()) if len(sku_yoy_window) > 0 else sku_recent_avg
        else:
            sku_yoy_avg = float(sku_df[sales_col].mean())

        expected_sku = sku_yoy_avg * cat_yoy_ratio
        performance_vs_category = (
            sku_recent_avg / expected_sku if expected_sku > 0 else 1.0
        )

        # --- Confidence intervals ---
        # Based on historical variability of SKU's share
        ci_low_4w, ci_high_4w = self._confidence_interval(
            sku_df, cat_df, date_col, sales_col, sku_col, store_id, store_col,
            forecast_4w, horizon=4,
        )
        ci_low_8w, ci_high_8w = self._confidence_interval(
            sku_df, cat_df, date_col, sales_col, sku_col, store_id, store_col,
            forecast_8w, horizon=8,
        )

        return CategoryRelativeResult(
            method="category_relative",
            sku_id=sku_id,
            store_id=store_id,
            forecast_4w=round(forecast_4w, 1),
            forecast_8w=round(forecast_8w, 1),
            confidence_low_4w=round(ci_low_4w, 1),
            confidence_high_4w=round(ci_high_4w, 1),
            confidence_low_8w=round(ci_low_8w, 1),
            confidence_high_8w=round(ci_high_8w, 1),
            category_forecast_4w=round(cat_forecast_4w, 1),
            category_forecast_8w=round(cat_forecast_8w, 1),
            sku_share_of_category=round(sku_share, 4),
            sku_performance_vs_category=round(performance_vs_category, 3),
            category_yoy_ratio=round(cat_yoy_ratio, 3),
            category_trend=cat_trend,
            weeks_of_history=n_weeks,
            error=None,
        )

    def _confidence_interval(
        self,
        sku_df: pd.DataFrame,
        cat_df: pd.DataFrame,
        date_col: str,
        sales_col: str,
        sku_col: str,
        store_id: str,
        store_col: str,
        cumulative_forecast: float,
        horizon: int,
        alpha: float = 0.05,
    ) -> tuple[float, float]:
        """Compute CI from historical variability of SKU weekly sales.

        Uses the standard deviation of weekly sales scaled by sqrt(horizon).
        """
        weekly_sales = sku_df[sales_col].values.astype(float)
        if len(weekly_sales) < 4:
            return max(0.0, cumulative_forecast * 0.5), cumulative_forecast * 1.5

        std = float(np.std(weekly_sales, ddof=1))
        from scipy.stats import norm
        z = norm.ppf(1 - alpha / 2)
        se = std * np.sqrt(horizon)

        lower = max(0.0, cumulative_forecast - z * se)
        upper = cumulative_forecast + z * se
        return lower, upper

    def _error_result(
        self,
        sku_id: str,
        store_id: str,
        weeks: int,
        error: str,
    ) -> CategoryRelativeResult:
        return CategoryRelativeResult(
            method="category_relative",
            sku_id=sku_id,
            store_id=store_id,
            forecast_4w=0.0,
            forecast_8w=0.0,
            confidence_low_4w=0.0,
            confidence_high_4w=0.0,
            confidence_low_8w=0.0,
            confidence_high_8w=0.0,
            category_forecast_4w=0.0,
            category_forecast_8w=0.0,
            sku_share_of_category=0.0,
            sku_performance_vs_category=0.0,
            category_yoy_ratio=0.0,
            category_trend="STABLE",
            weeks_of_history=weeks,
            error=error,
        )


# --- Batch runner ---


def forecast_all_skus_category_relative(
    weekly_demand: pd.DataFrame,
    sku_col: str = "sku_id",
    store_col: str = "store_id",
    category_col: str = "category_id",
    date_col: str = "week_start_date",
    sales_col: str = "net_sold",
) -> list[CategoryRelativeResult]:
    """Run Category-Relative forecaster across all SKU-store pairs.

    Requires a category_col in the DataFrame. Each SKU is forecast
    relative to its category.

    Args:
        weekly_demand: DataFrame with weekly demand including a category column.
        sku_col, store_col, category_col, date_col, sales_col: Column names.

    Returns:
        List of CategoryRelativeResult, one per SKU-store pair.
    """
    df = weekly_demand.copy()
    if not pd.api.types.is_datetime64_any_dtype(df[date_col]):
        df[date_col] = pd.to_datetime(df[date_col])

    if category_col not in df.columns:
        raise ValueError(
            f"Category column '{category_col}' not found. "
            f"Category-Relative method requires category data."
        )

    # Build SKU → category lookup
    sku_category = (
        df.groupby(sku_col)[category_col]
        .first()
        .to_dict()
    )

    forecaster = CategoryRelativeForecaster()
    results: list[CategoryRelativeResult] = []

    for (sku, store), _ in df.groupby([sku_col, store_col]):
        cat = sku_category.get(sku)
        if cat is None:
            results.append(forecaster._error_result(
                str(sku), str(store), 0, f"No category found for SKU {sku}",
            ))
            continue

        result = forecaster.forecast(
            df,
            sku_id=str(sku),
            store_id=str(store),
            category_id=str(cat),
            sku_col=sku_col,
            store_col=store_col,
            category_col=category_col,
            date_col=date_col,
            sales_col=sales_col,
        )
        results.append(result)

    return results
