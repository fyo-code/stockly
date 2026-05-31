"""ETS/Holt-Winters exponential smoothing forecaster (Method 1).

Fits a multiplicative Holt-Winters model to weekly demand data for a single
SKU-store pair. Produces point forecasts at 4-week and 8-week horizons,
confidence intervals, seasonal indices, and trend classification.

Requirements:
- Minimum 52 weeks of history (one full seasonal cycle)
- statsmodels >= 0.14

Library: statsmodels.tsa.holtwinters.ExponentialSmoothing
"""

import warnings
from typing import Optional

import numpy as np
import pandas as pd
from scipy.stats import norm
from statsmodels.tsa.holtwinters import ExponentialSmoothing

from ..data_models import ETSResult


# --- Configuration ---

MIN_WEEKS_REQUIRED = 52
SEASONAL_PERIOD = 52  # weekly data, annual seasonality
TREND_THRESHOLD = 0.5  # units/week — below this is STABLE


class ETSForecaster:
    """Holt-Winters exponential smoothing forecaster for a single SKU-store.

    Fits a multiplicative model: Demand = Level × Trend × Seasonality × Noise.
    Automatically falls back to additive seasonality if multiplicative fails
    (e.g., when data contains zeros).
    """

    def __init__(
        self,
        seasonal_period: int = SEASONAL_PERIOD,
        min_weeks: int = MIN_WEEKS_REQUIRED,
        trend_threshold: float = TREND_THRESHOLD,
    ):
        self._seasonal_period = seasonal_period
        self._min_weeks = min_weeks
        self._trend_threshold = trend_threshold

    def forecast(
        self,
        weekly_sales: pd.Series,
        sku_id: str = "",
        store_id: str = "",
    ) -> ETSResult:
        """Fit Holt-Winters and produce forecasts.

        Args:
            weekly_sales: Time-indexed Series of weekly net_sold values,
                sorted chronologically. Index should be DatetimeIndex or
                PeriodIndex with weekly frequency.
            sku_id: SKU identifier for the result.
            store_id: Store identifier for the result.

        Returns:
            ETSResult with forecasts, confidence intervals, seasonal indices,
            and trend classification. If the model fails, the error field is
            populated and forecasts fall back to simple averages.
        """
        n_weeks = len(weekly_sales)

        if n_weeks < self._min_weeks:
            return self._fallback_result(
                weekly_sales, sku_id, store_id,
                error=f"Insufficient history: {n_weeks} weeks (need {self._min_weeks})",
            )

        # Prepare data: ensure no negatives, replace zeros for multiplicative model
        sales = weekly_sales.astype(float).copy()
        has_zeros = (sales <= 0).any()

        # Determine seasonal period based on available history
        # statsmodels needs >= 2 full cycles for heuristic initialization
        if n_weeks >= 2 * self._seasonal_period:
            effective_period = self._seasonal_period  # 52 weeks (annual)
        elif n_weeks >= 2 * 26:
            effective_period = 26  # half-year seasonality
        else:
            effective_period = None  # trend-only, no seasonal

        # Try multiplicative first (better for retail), fall back to additive
        model_result = self._fit_model(sales, seasonal="mul", has_zeros=has_zeros, period=effective_period)
        if model_result is None:
            model_result = self._fit_model(sales, seasonal="add", has_zeros=False, period=effective_period)
        if model_result is None and effective_period is not None:
            # Last resort: trend-only (no seasonal)
            model_result = self._fit_model(sales, seasonal=None, has_zeros=False, period=None)

        if model_result is None:
            return self._fallback_result(
                weekly_sales, sku_id, store_id,
                error="Model fitting failed for all configurations",
            )

        fitted_model, seasonal_type = model_result

        # Generate forecasts for 8 weeks ahead
        forecast_values = fitted_model.forecast(8)
        forecast_values = np.maximum(forecast_values, 0)  # clip negatives

        forecast_4w = float(forecast_values[:4].sum())
        forecast_8w = float(forecast_values[:8].sum())

        # Confidence intervals via prediction intervals
        ci_low_4w, ci_high_4w = self._confidence_interval(fitted_model, horizon=4)
        ci_low_8w, ci_high_8w = self._confidence_interval(fitted_model, horizon=8)

        # Model fit quality (R-squared)
        r_squared = self._compute_r_squared(sales, fitted_model.fittedvalues)

        # Seasonal indices
        seasonal_indices = self._extract_seasonal_indices(fitted_model, seasonal_type)

        # Trend classification
        trend, trend_slope = self._classify_trend(fitted_model)

        return ETSResult(
            method="ets",
            sku_id=sku_id,
            store_id=store_id,
            forecast_4w=round(forecast_4w, 1),
            forecast_8w=round(forecast_8w, 1),
            confidence_low_4w=round(ci_low_4w, 1),
            confidence_high_4w=round(ci_high_4w, 1),
            confidence_low_8w=round(ci_low_8w, 1),
            confidence_high_8w=round(ci_high_8w, 1),
            model_fit_quality=round(r_squared, 3),
            seasonal_indices=seasonal_indices,
            trend=trend,
            trend_slope=round(trend_slope, 3),
            weeks_of_history=n_weeks,
            error=None,
        )

    def _fit_model(
        self,
        sales: pd.Series,
        seasonal: Optional[str],
        has_zeros: bool,
        period: Optional[int] = None,
    ) -> Optional[tuple]:
        """Attempt to fit a Holt-Winters model.

        Returns (fitted_model, seasonal_type) or None if fitting fails.
        """
        data = sales.copy()

        if seasonal == "mul" and has_zeros:
            # Multiplicative can't handle zeros — shift data up slightly
            data = data + 1.0

        seasonal_kw = {}
        if seasonal is not None and period is not None:
            seasonal_kw = {"seasonal": seasonal, "seasonal_periods": period}
        else:
            seasonal_kw = {"seasonal": None}

        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                model = ExponentialSmoothing(
                    data,
                    trend="add",
                    initialization_method="estimated",
                    **seasonal_kw,
                )
                fitted = model.fit(optimized=True, remove_bias=True)
                return (fitted, seasonal or "none")
        except Exception:
            return None

    def _confidence_interval(
        self,
        fitted_model,
        horizon: int,
        alpha: float = 0.05,
    ) -> tuple[float, float]:
        """Compute prediction interval for cumulative forecast over horizon.

        Uses residual standard error scaled by sqrt(horizon) as an
        approximation, since statsmodels Holt-Winters doesn't provide
        native prediction intervals.
        """
        residuals = fitted_model.resid
        residual_std = float(np.std(residuals, ddof=1))

        forecast_values = fitted_model.forecast(horizon)
        forecast_values = np.maximum(forecast_values, 0)
        cumulative_forecast = float(forecast_values.sum())

        # Scale SE for cumulative forecast (approx: SE grows with sqrt(h))
        # z_value derived from alpha (default 0.05 → 95% CI → z ≈ 1.96)
        z = norm.ppf(1 - alpha / 2)
        cumulative_se = residual_std * np.sqrt(horizon)

        lower = max(0.0, cumulative_forecast - z * cumulative_se)
        upper = cumulative_forecast + z * cumulative_se

        return lower, upper

    def _compute_r_squared(
        self,
        actual: pd.Series,
        fitted: pd.Series,
    ) -> float:
        """Compute R-squared between actual and fitted values."""
        # Align lengths (fitted may be shorter)
        n = min(len(actual), len(fitted))
        y = actual.values[-n:].astype(float)
        y_hat = fitted.values[-n:].astype(float)

        ss_res = np.sum((y - y_hat) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)

        if ss_tot == 0:
            return 0.0

        r2 = 1.0 - (ss_res / ss_tot)
        return max(0.0, r2)  # clip to 0 if negative (model worse than mean)

    def _extract_seasonal_indices(
        self,
        fitted_model,
        seasonal_type: str,
    ) -> dict[int, float]:
        """Extract seasonal indices (week_of_year -> multiplier).

        For multiplicative: the seasonal component directly.
        For additive: convert to a relative index around 1.0.
        """
        seasonal_component = fitted_model.season
        if seasonal_component is None:
            return {}

        # Last full cycle of seasonal values
        indices = seasonal_component[-self._seasonal_period:].values

        if seasonal_type == "add":
            # Convert additive to multiplicative-like index
            level = fitted_model.level[-1] if fitted_model.level is not None else 1.0
            if level != 0:
                indices = 1.0 + (indices / level)
            else:
                indices = np.ones_like(indices)

        return {
            int(week + 1): round(float(val), 3)
            for week, val in enumerate(indices)
        }

    def _classify_trend(
        self,
        fitted_model,
    ) -> tuple[str, float]:
        """Classify trend as GROWING, DECLINING, or STABLE.

        Uses the last trend component value from the fitted model.
        """
        trend_component = fitted_model.trend
        if trend_component is None or len(trend_component) == 0:
            return "STABLE", 0.0

        # Use average of last 4 weeks of trend for stability
        recent_trend = trend_component[-4:].values
        avg_slope = float(np.mean(recent_trend))

        if avg_slope > self._trend_threshold:
            return "GROWING", avg_slope
        elif avg_slope < -self._trend_threshold:
            return "DECLINING", avg_slope
        else:
            return "STABLE", avg_slope

    def _fallback_result(
        self,
        weekly_sales: pd.Series,
        sku_id: str,
        store_id: str,
        error: str,
    ) -> ETSResult:
        """Produce a naive fallback when model can't be fit.

        Uses simple mean × horizon as forecast.
        """
        n_weeks = len(weekly_sales)
        mean_weekly = float(weekly_sales.mean()) if n_weeks > 0 else 0.0
        std_weekly = float(weekly_sales.std()) if n_weeks > 1 else 0.0

        forecast_4w = round(mean_weekly * 4, 1)
        forecast_8w = round(mean_weekly * 8, 1)

        return ETSResult(
            method="ets",
            sku_id=sku_id,
            store_id=store_id,
            forecast_4w=forecast_4w,
            forecast_8w=forecast_8w,
            confidence_low_4w=round(max(0, (mean_weekly - 1.96 * std_weekly) * 4), 1),
            confidence_high_4w=round((mean_weekly + 1.96 * std_weekly) * 4, 1),
            confidence_low_8w=round(max(0, (mean_weekly - 1.96 * std_weekly) * 8), 1),
            confidence_high_8w=round((mean_weekly + 1.96 * std_weekly) * 8, 1),
            model_fit_quality=0.0,
            seasonal_indices={},
            trend="STABLE",
            trend_slope=0.0,
            weeks_of_history=n_weeks,
            error=error,
        )


def forecast_all_skus(
    weekly_demand: pd.DataFrame,
    sku_col: str = "sku_id",
    store_col: str = "store_id",
    date_col: str = "week_start_date",
    sales_col: str = "net_sold",
) -> list[ETSResult]:
    """Run ETS forecaster across all SKU-store pairs in a DataFrame.

    Args:
        weekly_demand: DataFrame with weekly aggregated demand. Must contain
            columns for sku_id, store_id, week_start_date, net_sold.
        sku_col: Name of the SKU column.
        store_col: Name of the store column.
        date_col: Name of the date column.
        sales_col: Name of the sales column.

    Returns:
        List of ETSResult dicts, one per SKU-store pair.
    """
    df = weekly_demand.copy()

    if not pd.api.types.is_datetime64_any_dtype(df[date_col]):
        df[date_col] = pd.to_datetime(df[date_col])

    forecaster = ETSForecaster()
    results: list[ETSResult] = []

    for (sku, store), group in df.groupby([sku_col, store_col]):
        group_sorted = group.sort_values(date_col)
        sales_series = group_sorted.set_index(date_col)[sales_col]
        sales_series = sales_series.asfreq("W-MON", fill_value=0)

        result = forecaster.forecast(
            weekly_sales=sales_series,
            sku_id=str(sku),
            store_id=str(store),
        )
        results.append(result)

    return results
