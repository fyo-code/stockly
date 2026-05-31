"""Multi-Scale Lag Analysis forecaster (Method 5).

Analyses demand at 5 temporal resolutions — 1w, 4w, 13w, 26w, 52w —
and combines them into a momentum-weighted forecast. Short-term lags
capture recent trend direction; longer lags provide the stable baseline.

Formula:
    Forecast = Weighted sum of lag averages
    Weights: recent lags get higher weight when momentum is consistent;
             longer lags dominate when short-term is volatile/noisy.

Trend consistency classification:
    STRONG_GROWTH   — all momentum ratios > 1.03 (consistent upward)
    STRONG_DECLINE  — all momentum ratios < 0.97 (consistent downward)
    STABLE          — all ratios within ±3%
    UNSTABLE        — mixed signals across scales

Requirements:
- Minimum 8 weeks of history (to compute at least lag_4w and lag_1w)
- 26+ weeks for lag_26w; 52+ for lag_52w (shorter histories use what's available)
"""

from typing import Optional

import numpy as np
import pandas as pd
from scipy.stats import norm

from ..data_models import MultiScaleLagResult


# --- Configuration ---

MIN_WEEKS_REQUIRED = 8
MOMENTUM_THRESHOLD = 0.03   # ±3% → momentum counts as directional
CONSISTENCY_ALPHA = 0.05    # for CI calculation

# Lag window sizes (weeks)
LAG_WINDOWS = [1, 4, 13, 26, 52]

# Default weights for each lag window in the forecast blend.
# Weights sum to 1. They are adjusted dynamically based on trend consistency.
DEFAULT_LAG_WEIGHTS = {
    1: 0.30,
    4: 0.30,
    13: 0.20,
    26: 0.15,
    52: 0.05,
}


# --- Pure functions ---


def calculate_lags(sales_series: pd.Series) -> dict[int, float]:
    """Compute rolling average for each lag window.

    For each window size, averages the most recent N weeks.
    Returns only windows that have enough data (at least half the window).

    Args:
        sales_series: Time-indexed Series, sorted chronologically.

    Returns:
        Dict mapping window size → rolling average (float).
        Missing windows are omitted from the dict.
    """
    n = len(sales_series)
    lags: dict[int, float] = {}

    for window in LAG_WINDOWS:
        if n >= max(1, window // 2):  # need at least half the window
            actual_window = min(window, n)
            lags[window] = float(sales_series.iloc[-actual_window:].mean())

    return lags


def calculate_momentum_ratios(lags: dict[int, float]) -> dict[str, float]:
    """Compute momentum ratios between consecutive lag scales.

    Ratios > 1.0 indicate acceleration (short-term > long-term).
    Ratios < 1.0 indicate deceleration.

    Args:
        lags: Dict from calculate_lags().

    Returns:
        Dict with keys: "short" (1w/4w), "medium" (4w/13w), "long" (13w/26w).
        A ratio is omitted if either lag is unavailable or denominator is zero.
    """
    ratios: dict[str, float] = {}

    pairs = [
        ("short",  1,  4),
        ("medium", 4,  13),
        ("long",   13, 26),
    ]

    for name, numerator_key, denominator_key in pairs:
        if numerator_key in lags and denominator_key in lags:
            denom = lags[denominator_key]
            if denom > 0:
                ratios[name] = lags[numerator_key] / denom
            else:
                ratios[name] = 1.0  # neutral when denominator is zero

    return ratios


def classify_trend_consistency(ratios: dict[str, float]) -> str:
    """Classify trend direction based on momentum ratio agreement.

    Args:
        ratios: Dict from calculate_momentum_ratios().

    Returns:
        One of: "STRONG_GROWTH", "STRONG_DECLINE", "STABLE", "UNSTABLE"
    """
    if not ratios:
        return "STABLE"

    values = list(ratios.values())

    all_growth  = all(r > 1.0 + MOMENTUM_THRESHOLD for r in values)
    all_decline = all(r < 1.0 - MOMENTUM_THRESHOLD for r in values)
    all_stable  = all(abs(r - 1.0) <= MOMENTUM_THRESHOLD for r in values)

    if all_growth:
        return "STRONG_GROWTH"
    if all_decline:
        return "STRONG_DECLINE"
    if all_stable:
        return "STABLE"
    return "UNSTABLE"


def blend_lags(
    lags: dict[int, float],
    trend_consistency: str,
) -> float:
    """Combine lag averages into a single weekly forecast.

    Weight adjustment rules:
    - STRONG_GROWTH / STRONG_DECLINE: upweight short lags (1w, 4w) by 1.5x,
      downweight long lags (26w, 52w) by 0.5x, then renormalise.
    - UNSTABLE: upweight long lags (13w, 26w, 52w) by 1.5x to smooth noise.
    - STABLE: use default weights unchanged.

    Args:
        lags: Dict from calculate_lags().
        trend_consistency: String from classify_trend_consistency().

    Returns:
        Weighted average of available lag averages.
    """
    weights = DEFAULT_LAG_WEIGHTS.copy()

    if trend_consistency in ("STRONG_GROWTH", "STRONG_DECLINE"):
        # Momentum is real — trust recent signal
        weights[1]  = weights[1]  * 1.5
        weights[4]  = weights[4]  * 1.5
        weights[26] = weights[26] * 0.5
        weights[52] = weights[52] * 0.5
    elif trend_consistency == "UNSTABLE":
        # Signal is mixed — trust stable long-term baseline
        weights[13] = weights[13] * 1.5
        weights[26] = weights[26] * 1.5
        weights[52] = weights[52] * 1.5
        weights[1]  = weights[1]  * 0.6
        weights[4]  = weights[4]  * 0.6

    # Keep only weights for available lags and renormalise
    active = {w: weights[w] for w in weights if w in lags}
    total = sum(active.values())

    if total == 0 or not active:
        # Fallback: simple mean
        return float(np.mean(list(lags.values())))

    forecast = sum(lags[w] * active[w] / total for w in active)
    return float(forecast)


# --- Forecaster ---


class MultiScaleLagForecaster:
    """Multi-scale temporal momentum forecaster.

    Steps:
    1. Compute rolling averages at 1w, 4w, 13w, 26w, 52w scales
    2. Calculate momentum ratios between adjacent scales
    3. Classify trend consistency
    4. Blend lags into weekly forecast (weight-adjusted by consistency)
    5. Scale to 4w and 8w horizons
    6. Confidence interval from historical standard deviation
    """

    def __init__(
        self,
        min_weeks: int = MIN_WEEKS_REQUIRED,
    ):
        self._min_weeks = min_weeks

    def forecast(
        self,
        weekly_sales: pd.Series,
        sku_id: str = "",
        store_id: str = "",
    ) -> MultiScaleLagResult:
        """Produce multi-scale lag forecast for one SKU-store.

        Args:
            weekly_sales: Time-indexed Series of weekly net_sold values,
                sorted chronologically.
            sku_id: SKU identifier.
            store_id: Store identifier.

        Returns:
            MultiScaleLagResult with momentum-weighted forecast.
        """
        n_weeks = len(weekly_sales)

        if n_weeks < self._min_weeks:
            return self._fallback_result(
                weekly_sales, sku_id, store_id,
                error=f"Insufficient history: {n_weeks} weeks (need {self._min_weeks})",
            )

        sales = weekly_sales.astype(float).copy()

        # Step 1: Lags
        lags = calculate_lags(sales)

        if not lags:
            return self._fallback_result(
                weekly_sales, sku_id, store_id,
                error="Could not compute any lag averages",
            )

        # Step 2: Momentum ratios
        ratios = calculate_momentum_ratios(lags)

        # Step 3: Trend consistency
        trend_consistency = classify_trend_consistency(ratios)

        # Step 4+5: Blend → weekly → horizon forecasts
        forecast_weekly = blend_lags(lags, trend_consistency)
        forecast_4w = forecast_weekly * 4
        forecast_8w = forecast_weekly * 8

        # Step 6: Confidence intervals from historical std
        hist_std = float(sales.std(ddof=1)) if n_weeks > 1 else 0.0
        ci_low_4w, ci_high_4w = self._confidence_interval(forecast_4w, hist_std, horizon=4)
        ci_low_8w, ci_high_8w = self._confidence_interval(forecast_8w, hist_std, horizon=8)

        return MultiScaleLagResult(
            method="multi_scale_lag",
            sku_id=sku_id,
            store_id=store_id,
            forecast_4w=round(forecast_4w, 1),
            forecast_8w=round(forecast_8w, 1),
            confidence_low_4w=round(ci_low_4w, 1),
            confidence_high_4w=round(ci_high_4w, 1),
            confidence_low_8w=round(ci_low_8w, 1),
            confidence_high_8w=round(ci_high_8w, 1),
            lag_1w=round(lags.get(1, 0.0), 2),
            lag_4w=round(lags.get(4, 0.0), 2),
            lag_13w=round(lags.get(13, 0.0), 2),
            lag_26w=round(lags.get(26, 0.0), 2),
            lag_52w=round(lags.get(52, 0.0), 2),
            momentum_short=round(ratios.get("short", 1.0), 4),
            momentum_medium=round(ratios.get("medium", 1.0), 4),
            momentum_long=round(ratios.get("long", 1.0), 4),
            trend_consistency=trend_consistency,
            weeks_of_history=n_weeks,
            error=None,
        )

    def _confidence_interval(
        self,
        cumulative_forecast: float,
        weekly_std: float,
        horizon: int,
        alpha: float = CONSISTENCY_ALPHA,
    ) -> tuple[float, float]:
        """Prediction interval from historical standard deviation."""
        z = norm.ppf(1 - alpha / 2)
        se = weekly_std * np.sqrt(horizon)
        lower = max(0.0, cumulative_forecast - z * se)
        upper = cumulative_forecast + z * se
        return lower, upper

    def _fallback_result(
        self,
        weekly_sales: pd.Series,
        sku_id: str,
        store_id: str,
        error: str,
    ) -> MultiScaleLagResult:
        """Naive fallback when insufficient data."""
        n = len(weekly_sales)
        mean_weekly = float(weekly_sales.mean()) if n > 0 else 0.0

        return MultiScaleLagResult(
            method="multi_scale_lag",
            sku_id=sku_id,
            store_id=store_id,
            forecast_4w=round(mean_weekly * 4, 1),
            forecast_8w=round(mean_weekly * 8, 1),
            confidence_low_4w=0.0,
            confidence_high_4w=round(mean_weekly * 4 * 2, 1),
            confidence_low_8w=0.0,
            confidence_high_8w=round(mean_weekly * 8 * 2, 1),
            lag_1w=mean_weekly,
            lag_4w=mean_weekly,
            lag_13w=0.0,
            lag_26w=0.0,
            lag_52w=0.0,
            momentum_short=1.0,
            momentum_medium=1.0,
            momentum_long=1.0,
            trend_consistency="STABLE",
            weeks_of_history=n,
            error=error,
        )


# --- Batch runner ---


def forecast_all_skus_multi_scale_lag(
    weekly_demand: pd.DataFrame,
    sku_col: str = "sku_id",
    store_col: str = "store_id",
    date_col: str = "week_start_date",
    sales_col: str = "net_sold",
) -> list[MultiScaleLagResult]:
    """Run Multi-Scale Lag forecaster across all SKU-store pairs.

    Args:
        weekly_demand: DataFrame with weekly aggregated demand.
        sku_col, store_col, date_col, sales_col: Column names.

    Returns:
        List of MultiScaleLagResult, one per SKU-store pair.
    """
    df = weekly_demand.copy()
    if not pd.api.types.is_datetime64_any_dtype(df[date_col]):
        df[date_col] = pd.to_datetime(df[date_col])

    forecaster = MultiScaleLagForecaster()
    results: list[MultiScaleLagResult] = []

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
