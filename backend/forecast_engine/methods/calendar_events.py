"""Calendar Events forecaster (Method 6).

Combines two signals for demand forecasting:

1. **Seasonal index** — week-of-year pattern learned from historical sales.
   Captures stable annual rhythms (e.g. Christmas spike, summer lull).

2. **Calendar event multipliers** — Romanian public holidays, Black Friday,
   Orthodox Easter, and market season multipliers (construction season,
   salary cycles), sourced from Phase 1B's calendar engine.

Formula (per future week w):
    weekly_forecast[w] = base_demand × seasonal_index[week_of_year(w)] × event_multiplier[w]

The base demand is the recent clean median (last 13 weeks, promotions removed)
to anchor the forecast on current demand level, not historical average.

Requirements:
- Minimum 8 weeks of history (enough to compute base demand)
- 26+ weeks recommended for meaningful seasonal indices
"""

from datetime import date, timedelta
from typing import Optional

import numpy as np
import pandas as pd
from scipy.stats import norm

from ..calendar_features import get_week_calendar_features
from ..config import EVENT_MULTIPLIERS
from ..data_models import CalendarResult
from ..seasonality import compute_seasonal_indices


# --- Configuration ---

MIN_WEEKS_REQUIRED = 8
PROMO_THRESHOLD = 2.5       # × rolling mean → week flagged as promotional
RECENT_WINDOW = 13          # weeks to use for clean base demand
SEASONAL_MIN_WEEKS = 26     # minimum weeks for reliable seasonal indices
FORECAST_HORIZON = 8        # total weeks to forecast ahead
CONSISTENCY_ALPHA = 0.05    # for 95% confidence intervals


# --- Pure functions ---


def compute_seasonal_indices_for_sku(
    weekly_sales: pd.Series,
) -> dict[int, float]:
    """Compute seasonal index per ISO week-of-year for a single SKU.

    Wraps the shared `compute_seasonal_indices()` utility for use with a
    plain pd.Series (time-indexed by week_start_date).

    Args:
        weekly_sales: Time-indexed Series of net_sold values.

    Returns:
        Dict mapping ISO week number (1–53) → seasonal index.
        Returns all 1.0 if series has fewer than SEASONAL_MIN_WEEKS.
    """
    if len(weekly_sales) < SEASONAL_MIN_WEEKS:
        return {w: 1.0 for w in range(1, 54)}

    df = pd.DataFrame({
        "sku_id": "SKU",
        "week_start_date": weekly_sales.index,
        "net_sold": weekly_sales.values,
    })

    indices_df = compute_seasonal_indices(df, group_col="sku_id", min_weeks=SEASONAL_MIN_WEEKS)
    if indices_df.empty:
        return {w: 1.0 for w in range(1, 54)}

    return dict(zip(
        indices_df["week_of_year"].astype(int),
        indices_df["seasonal_index"].astype(float),
    ))


def strip_promotional_weeks(weekly_sales: pd.Series) -> pd.Series:
    """Remove promotional spikes using rolling median comparison.

    A week is flagged as promotional if sales > PROMO_THRESHOLD × 13-week
    rolling median. Flagged weeks are replaced with the rolling median value.

    Args:
        weekly_sales: Time-indexed Series.

    Returns:
        New Series with promo spikes replaced by local median.
    """
    if len(weekly_sales) < 4:
        return weekly_sales.copy()

    rolling_med = weekly_sales.rolling(13, min_periods=3, center=True).median()
    rolling_med = rolling_med.fillna(weekly_sales.median())

    is_promo = weekly_sales > (rolling_med * PROMO_THRESHOLD)
    clean = weekly_sales.copy()
    clean[is_promo] = rolling_med[is_promo]
    return clean


def apply_event_multipliers(
    base_demand: float,
    week_start: date,
) -> tuple[float, str | None, float]:
    """Apply Romanian calendar event multiplier to a weekly base demand.

    Uses Phase 1B's `get_week_calendar_features()` which combines event,
    season, and salary cycle multipliers into a single combined multiplier.

    Args:
        base_demand: Weekly demand before calendar adjustment.
        week_start: Monday of the target week.

    Returns:
        Tuple of (adjusted_demand, event_name_or_None, combined_multiplier).
    """
    features = get_week_calendar_features(week_start)
    adjusted = base_demand * features.combined_multiplier
    event_name = features.holiday_name if features.is_holiday else None
    return adjusted, event_name, float(features.combined_multiplier)


# --- Forecaster ---


class CalendarEventsForecaster:
    """Seasonal + Romanian calendar event forecaster.

    Steps:
    1. Strip promotional spikes from history → clean series
    2. Compute seasonal index per week-of-year from clean history
    3. Compute clean base demand (median of most recent RECENT_WINDOW clean weeks)
    4. For each future week (1..8):
       a. seasonal_index = index for that ISO week
       b. calendar_multiplier = event + season + salary combined multiplier
       c. weekly_forecast = base_demand × seasonal_index × calendar_multiplier
    5. Sum weeks 1-4 → forecast_4w, 1-8 → forecast_8w
    6. Confidence intervals from clean series historical std
    """

    def __init__(
        self,
        min_weeks: int = MIN_WEEKS_REQUIRED,
        recent_window: int = RECENT_WINDOW,
    ):
        self._min_weeks = min_weeks
        self._recent_window = recent_window

    def forecast(
        self,
        weekly_sales: pd.Series,
        sku_id: str = "",
        store_id: str = "",
    ) -> CalendarResult:
        """Produce calendar-adjusted forecast for one SKU-store.

        Args:
            weekly_sales: Time-indexed Series of weekly net_sold values,
                sorted chronologically with DatetimeIndex.
            sku_id: SKU identifier.
            store_id: Store identifier.

        Returns:
            CalendarResult with seasonal + event adjusted forecast.
        """
        n_weeks = len(weekly_sales)

        if n_weeks < self._min_weeks:
            return self._fallback_result(
                weekly_sales, sku_id, store_id,
                error=f"Insufficient history: {n_weeks} weeks (need {self._min_weeks})",
            )

        # Step 1: Strip promotional spikes
        clean_sales = strip_promotional_weeks(weekly_sales.astype(float))

        # Step 2: Seasonal indices per week-of-year
        seasonal_indices = compute_seasonal_indices_for_sku(clean_sales)

        # Step 3: Clean base demand — median of recent clean weeks
        recent_clean = clean_sales.iloc[-min(self._recent_window, n_weeks):]
        base_demand = float(recent_clean.median())
        if base_demand <= 0:
            base_demand = float(clean_sales.median())
        if base_demand <= 0:
            return self._fallback_result(
                weekly_sales, sku_id, store_id,
                error="Zero or negative base demand after cleaning",
            )

        # Step 4: Weekly forecasts for next 8 weeks
        last_date = weekly_sales.index[-1]
        if hasattr(last_date, "date"):
            last_date = last_date.date()

        # Align to Monday
        last_monday = last_date - timedelta(days=last_date.weekday())

        weekly_forecasts: list[float] = []
        seasonal_indices_used: list[float] = []
        peak_event_name: str | None = None
        peak_event_multiplier: float = 1.0

        for week_offset in range(1, FORECAST_HORIZON + 1):
            future_week_start = last_monday + timedelta(weeks=week_offset)

            # ISO week of year (1–53)
            iso_week = future_week_start.isocalendar()[1]
            s_index = seasonal_indices.get(iso_week, 1.0)
            seasonal_indices_used.append(s_index)

            # Calendar event multiplier
            adj_demand, event_name, combined_mult = apply_event_multipliers(
                base_demand, future_week_start
            )
            # adj_demand already includes seasonal index implicitly via combined_mult,
            # so we apply both multiplicatively:
            weekly_forecast = base_demand * s_index * combined_mult
            weekly_forecasts.append(weekly_forecast)

            # Track peak event
            if event_name and combined_mult > peak_event_multiplier:
                peak_event_multiplier = combined_mult
                peak_event_name = event_name

        # Step 5: Aggregate
        forecast_4w = float(sum(weekly_forecasts[:4]))
        forecast_8w = float(sum(weekly_forecasts))

        avg_seasonal_index_4w = float(np.mean(seasonal_indices_used[:4]))
        avg_seasonal_index_8w = float(np.mean(seasonal_indices_used))

        # Step 6: CI from historical std
        hist_std = float(clean_sales.std(ddof=1)) if n_weeks > 1 else 0.0
        ci_low_4w, ci_high_4w = self._confidence_interval(forecast_4w, hist_std, horizon=4)
        ci_low_8w, ci_high_8w = self._confidence_interval(forecast_8w, hist_std, horizon=8)

        return CalendarResult(
            method="calendar_events",
            sku_id=sku_id,
            store_id=store_id,
            forecast_4w=round(forecast_4w, 1),
            forecast_8w=round(forecast_8w, 1),
            confidence_low_4w=round(ci_low_4w, 1),
            confidence_high_4w=round(ci_high_4w, 1),
            confidence_low_8w=round(ci_low_8w, 1),
            confidence_high_8w=round(ci_high_8w, 1),
            base_demand_weekly=round(base_demand, 2),
            avg_seasonal_index_4w=round(avg_seasonal_index_4w, 4),
            avg_seasonal_index_8w=round(avg_seasonal_index_8w, 4),
            peak_event=peak_event_name,
            peak_event_multiplier=round(peak_event_multiplier, 4),
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
        """Prediction interval: forecast ± z × std × sqrt(horizon)."""
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
    ) -> CalendarResult:
        """Naive fallback when insufficient data."""
        n = len(weekly_sales)
        mean_weekly = float(weekly_sales.mean()) if n > 0 else 0.0

        return CalendarResult(
            method="calendar_events",
            sku_id=sku_id,
            store_id=store_id,
            forecast_4w=round(mean_weekly * 4, 1),
            forecast_8w=round(mean_weekly * 8, 1),
            confidence_low_4w=0.0,
            confidence_high_4w=round(mean_weekly * 4 * 2, 1),
            confidence_low_8w=0.0,
            confidence_high_8w=round(mean_weekly * 8 * 2, 1),
            base_demand_weekly=mean_weekly,
            avg_seasonal_index_4w=1.0,
            avg_seasonal_index_8w=1.0,
            peak_event=None,
            peak_event_multiplier=1.0,
            weeks_of_history=n,
            error=error,
        )


# --- Batch runner ---


def forecast_all_skus_calendar_events(
    weekly_demand: pd.DataFrame,
    sku_col: str = "sku_id",
    store_col: str = "store_id",
    date_col: str = "week_start_date",
    sales_col: str = "net_sold",
) -> list[CalendarResult]:
    """Run Calendar Events forecaster across all SKU-store pairs.

    Args:
        weekly_demand: DataFrame with weekly aggregated demand.
        sku_col, store_col, date_col, sales_col: Column names.

    Returns:
        List of CalendarResult, one per SKU-store pair.
    """
    df = weekly_demand.copy()
    if not pd.api.types.is_datetime64_any_dtype(df[date_col]):
        df[date_col] = pd.to_datetime(df[date_col])

    forecaster = CalendarEventsForecaster()
    results: list[CalendarResult] = []

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
