"""Croston's method for intermittent demand forecasting (Method 7).

Standard method for SKUs with sporadic, lumpy demand patterns — items that
sell zero units in many weeks but have occasional bursts. Common in furniture
retail where a specific model might sell only a few times per month.

Croston's separates the time series into two components:
1. Demand sizes (non-zero values only)
2. Inter-demand intervals (gaps between non-zero weeks)

Each component is smoothed independently with simple exponential smoothing.
The forecast = smoothed demand size / smoothed inter-arrival interval.

Variant: Syntetos-Boylan Approximation (SBA) — applies a bias correction
factor to Croston's, which tends to overestimate intermittent demand.

Routing rule: Use this method when zero_week_pct > 0.80 (>80% of weeks
have zero sales). At 40-80%, standard methods still work for furniture.

Requirements:
- Minimum 8 weeks of history
- At least 3 non-zero demand events (otherwise too little signal)
"""

from typing import Optional

import numpy as np
import pandas as pd
from scipy.stats import norm

from ..data_models import CrostonsResult


# --- Configuration ---

MIN_WEEKS_REQUIRED = 8
MIN_DEMAND_EVENTS = 3       # minimum non-zero weeks
SMOOTHING_ALPHA = 0.15      # exponential smoothing parameter
SBA_CORRECTION = True       # use Syntetos-Boylan bias correction
INTERMITTENT_THRESHOLD = 0.80  # >80% zero-weeks → truly intermittent


class CrostonsForecaster:
    """Croston's method with optional SBA bias correction.

    Steps:
    1. Extract non-zero demand values and their positions
    2. Compute inter-demand intervals (gaps between non-zero weeks)
    3. Apply exponential smoothing to demand sizes
    4. Apply exponential smoothing to inter-demand intervals
    5. Forecast rate = smoothed demand / smoothed interval
    6. Optional: SBA correction factor (1 - alpha/2) to reduce overestimation
    """

    def __init__(
        self,
        alpha: float = SMOOTHING_ALPHA,
        min_weeks: int = MIN_WEEKS_REQUIRED,
        min_events: int = MIN_DEMAND_EVENTS,
        use_sba: bool = SBA_CORRECTION,
    ):
        self._alpha = alpha
        self._min_weeks = min_weeks
        self._min_events = min_events
        self._use_sba = use_sba

    def forecast(
        self,
        weekly_sales: pd.Series,
        sku_id: str = "",
        store_id: str = "",
    ) -> CrostonsResult:
        """Produce intermittent demand forecast for one SKU-store.

        Args:
            weekly_sales: Time-indexed Series of weekly demand values,
                sorted chronologically. Zeros represent no-demand weeks.
            sku_id: SKU identifier.
            store_id: Store identifier.

        Returns:
            CrostonsResult with demand rate forecast.
        """
        n_weeks = len(weekly_sales)

        if n_weeks < self._min_weeks:
            return self._error_result(
                sku_id, store_id, n_weeks,
                f"Insufficient history: {n_weeks} weeks (need {self._min_weeks})",
            )

        sales = weekly_sales.astype(float).values
        zero_pct = float(np.sum(sales <= 0)) / n_weeks

        # Find non-zero demand events
        nonzero_mask = sales > 0
        nonzero_indices = np.where(nonzero_mask)[0]
        demand_sizes = sales[nonzero_mask]
        num_events = len(demand_sizes)

        if num_events < self._min_events:
            return self._error_result(
                sku_id, store_id, n_weeks,
                f"Too few demand events: {num_events} (need {self._min_events})",
            )

        # Compute inter-demand intervals
        # First interval = index of first non-zero + 1 (weeks from start)
        intervals = np.diff(nonzero_indices).astype(float)
        # Prepend the first interval (weeks from start to first demand)
        first_interval = float(nonzero_indices[0] + 1)
        intervals = np.concatenate([[first_interval], intervals])

        # Exponential smoothing on demand sizes
        smoothed_demand = demand_sizes[0]
        for d in demand_sizes[1:]:
            smoothed_demand = self._alpha * d + (1 - self._alpha) * smoothed_demand

        # Exponential smoothing on inter-demand intervals
        smoothed_interval = intervals[0]
        for q in intervals[1:]:
            smoothed_interval = self._alpha * q + (1 - self._alpha) * smoothed_interval

        # Prevent division by zero
        if smoothed_interval <= 0:
            smoothed_interval = 1.0

        # Demand rate per week
        demand_rate = smoothed_demand / smoothed_interval

        # SBA bias correction
        if self._use_sba:
            demand_rate *= (1 - self._alpha / 2)

        # Forecasts
        forecast_4w = demand_rate * 4
        forecast_8w = demand_rate * 8

        # Confidence intervals
        # Based on variance of demand sizes and intervals
        demand_std = float(np.std(demand_sizes, ddof=1)) if num_events > 1 else float(np.mean(demand_sizes)) * 0.5
        ci_low_4w, ci_high_4w = self._confidence_interval(forecast_4w, demand_std, smoothed_interval, 4)
        ci_low_8w, ci_high_8w = self._confidence_interval(forecast_8w, demand_std, smoothed_interval, 8)

        return CrostonsResult(
            method="crostons",
            sku_id=sku_id,
            store_id=store_id,
            forecast_4w=round(forecast_4w, 1),
            forecast_8w=round(forecast_8w, 1),
            confidence_low_4w=round(ci_low_4w, 1),
            confidence_high_4w=round(ci_high_4w, 1),
            confidence_low_8w=round(ci_low_8w, 1),
            confidence_high_8w=round(ci_high_8w, 1),
            mean_demand_size=round(float(smoothed_demand), 2),
            mean_inter_arrival=round(float(smoothed_interval), 2),
            demand_rate_per_week=round(float(demand_rate), 4),
            zero_week_pct=round(zero_pct, 3),
            num_demand_events=num_events,
            weeks_of_history=n_weeks,
            error=None,
        )

    def _confidence_interval(
        self,
        cumulative_forecast: float,
        demand_std: float,
        mean_interval: float,
        horizon: int,
        alpha: float = 0.05,
    ) -> tuple[float, float]:
        """CI for intermittent demand — wider than continuous methods."""
        z = norm.ppf(1 - alpha / 2)
        # Scale std by expected number of demand events in horizon
        expected_events = horizon / mean_interval
        se = demand_std * np.sqrt(max(expected_events, 1))
        lower = max(0.0, cumulative_forecast - z * se)
        upper = cumulative_forecast + z * se
        return lower, upper

    def _error_result(
        self,
        sku_id: str,
        store_id: str,
        weeks: int,
        error: str,
    ) -> CrostonsResult:
        return CrostonsResult(
            method="crostons",
            sku_id=sku_id,
            store_id=store_id,
            forecast_4w=0.0,
            forecast_8w=0.0,
            confidence_low_4w=0.0,
            confidence_high_4w=0.0,
            confidence_low_8w=0.0,
            confidence_high_8w=0.0,
            mean_demand_size=0.0,
            mean_inter_arrival=0.0,
            demand_rate_per_week=0.0,
            zero_week_pct=0.0,
            num_demand_events=0,
            weeks_of_history=weeks,
            error=error,
        )


# --- Batch runner ---


def forecast_all_skus_crostons(
    weekly_demand: pd.DataFrame,
    sku_col: str = "sku_id",
    store_col: str = "store_id",
    date_col: str = "week_start_date",
    sales_col: str = "net_sold",
    zero_week_threshold: float = INTERMITTENT_THRESHOLD,
) -> list[CrostonsResult]:
    """Run Croston's method on intermittent SKUs only.

    Only processes SKUs where zero_week_pct > threshold.
    SKUs below threshold are skipped (they should use continuous methods).

    Args:
        weekly_demand: DataFrame with weekly demand.
        zero_week_threshold: Minimum zero-week percentage to qualify (default 0.80).

    Returns:
        List of CrostonsResult, one per qualifying SKU-store pair.
    """
    df = weekly_demand.copy()
    if not pd.api.types.is_datetime64_any_dtype(df[date_col]):
        df[date_col] = pd.to_datetime(df[date_col])

    # Total weeks in dataset
    total_weeks = df[date_col].nunique()

    forecaster = CrostonsForecaster()
    results: list[CrostonsResult] = []

    for (sku, store), group in df.groupby([sku_col, store_col]):
        group_sorted = group.sort_values(date_col)
        sales_series = group_sorted.set_index(date_col)[sales_col]
        sales_series = sales_series.asfreq("W-MON", fill_value=0)

        # Check if this SKU qualifies as intermittent
        zero_pct = float((sales_series <= 0).sum()) / len(sales_series)
        if zero_pct <= zero_week_threshold:
            continue  # Skip — use continuous methods instead

        result = forecaster.forecast(
            weekly_sales=sales_series,
            sku_id=str(sku),
            store_id=str(store),
        )
        results.append(result)

    return results
