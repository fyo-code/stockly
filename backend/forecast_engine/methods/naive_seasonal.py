"""Naive Seasonal Baseline forecaster (Iter 3 Fix #3).

Same-period-last-year forecast. For a SKU whose last training week is W,
predicts the next H weeks as the units sold in the H weeks starting 52 weeks
before W + 1. This anchors the ensemble to observed reality and benchmarks
whether the sophisticated methods are actually adding value — in Iter 2 the
ensemble lost head-to-head to this naive baseline (79.9% vs 121.1% WMAPE,
PROGRESS.md).

Routing: everyone. Confidence intervals derived from week-to-week variability
in the matched prior-year window.
"""

from typing import Optional, TypedDict

import numpy as np
import pandas as pd
from scipy.stats import norm


# --- Configuration ---

MIN_PRIOR_WEEKS = 4      # require at least 4 of the 8 matched prior-year weeks
LOOKBACK_WEEKS = 52      # same-week-last-year


# --- Result model ---


class NaiveSeasonalResult(TypedDict):
    method: str  # always "naive_seasonal"
    sku_id: str
    store_id: str
    forecast_4w: float
    forecast_8w: float
    confidence_low_4w: float
    confidence_high_4w: float
    confidence_low_8w: float
    confidence_high_8w: float
    matched_prior_weeks_4w: int  # how many of the 4 target weeks had prior-year data
    matched_prior_weeks_8w: int
    weeks_of_history: int
    error: Optional[str]


# --- Forecaster ---


class NaiveSeasonalForecaster:
    """Reads same-period-last-year sales and uses them as the forecast."""

    def __init__(
        self,
        lookback_weeks: int = LOOKBACK_WEEKS,
        min_prior_weeks: int = MIN_PRIOR_WEEKS,
    ):
        self._lookback = lookback_weeks
        self._min_prior = min_prior_weeks

    def forecast(
        self,
        weekly_sales: pd.Series,
        sku_id: str = "",
        store_id: str = "",
    ) -> NaiveSeasonalResult:
        n = len(weekly_sales)

        if n < self._lookback + self._min_prior:
            return self._fallback(
                weekly_sales, sku_id, store_id,
                error=f"Insufficient history: {n} weeks (need {self._lookback + self._min_prior})",
            )

        sales = weekly_sales.astype(float)
        # Last index in the training series defines the "now" boundary.
        last_idx = n - 1
        # Target prediction windows are weeks [last_idx + 1 ... last_idx + H].
        # Their matched prior-year weeks sit at [last_idx + 1 - 52 ... last_idx + H - 52].
        base = last_idx + 1 - self._lookback

        def window_stats(horizon: int) -> tuple[float, float, int]:
            start = base
            end = base + horizon
            if start < 0 or end > n:
                # Clip to available history.
                start = max(0, start)
                end = min(n, end)
            matched = sales.iloc[start:end].values if end > start else np.array([])
            if len(matched) == 0:
                return 0.0, 0.0, 0
            # Scale up if we had to clip (e.g. only 3 of 4 weeks available).
            scale = horizon / len(matched)
            total = float(matched.sum()) * scale
            std = float(matched.std(ddof=1)) if len(matched) > 1 else 0.0
            return total, std, len(matched)

        f4, std4, matched4 = window_stats(4)
        f8, std8, matched8 = window_stats(8)

        if matched4 < self._min_prior and matched8 < self._min_prior:
            return self._fallback(
                weekly_sales, sku_id, store_id,
                error=f"Too few matched prior-year weeks (4w:{matched4}, 8w:{matched8})",
            )

        lo4, hi4 = self._ci(f4, std4, horizon=4)
        lo8, hi8 = self._ci(f8, std8, horizon=8)

        return NaiveSeasonalResult(
            method="naive_seasonal",
            sku_id=sku_id,
            store_id=store_id,
            forecast_4w=round(f4, 1),
            forecast_8w=round(f8, 1),
            confidence_low_4w=round(lo4, 1),
            confidence_high_4w=round(hi4, 1),
            confidence_low_8w=round(lo8, 1),
            confidence_high_8w=round(hi8, 1),
            matched_prior_weeks_4w=matched4,
            matched_prior_weeks_8w=matched8,
            weeks_of_history=n,
            error=None,
        )

    @staticmethod
    def _ci(point: float, weekly_std: float, horizon: int, alpha: float = 0.05) -> tuple[float, float]:
        z = norm.ppf(1 - alpha / 2)
        se = weekly_std * np.sqrt(horizon)
        return max(0.0, point - z * se), point + z * se

    def _fallback(
        self,
        weekly_sales: pd.Series,
        sku_id: str,
        store_id: str,
        error: str,
    ) -> NaiveSeasonalResult:
        n = len(weekly_sales)
        mean_weekly = float(weekly_sales.mean()) if n > 0 else 0.0
        return NaiveSeasonalResult(
            method="naive_seasonal",
            sku_id=sku_id,
            store_id=store_id,
            forecast_4w=round(mean_weekly * 4, 1),
            forecast_8w=round(mean_weekly * 8, 1),
            confidence_low_4w=0.0,
            confidence_high_4w=round(mean_weekly * 4 * 2, 1),
            confidence_low_8w=0.0,
            confidence_high_8w=round(mean_weekly * 8 * 2, 1),
            matched_prior_weeks_4w=0,
            matched_prior_weeks_8w=0,
            weeks_of_history=n,
            error=error,
        )


# --- Batch runner ---


def forecast_all_skus_naive_seasonal(
    weekly_demand: pd.DataFrame,
    sku_col: str = "sku_id",
    store_col: str = "store_id",
    date_col: str = "week_start_date",
    sales_col: str = "net_sold",
) -> list[NaiveSeasonalResult]:
    """Run naive same-period-last-year forecaster across all SKU-store pairs."""
    df = weekly_demand.copy()
    if not pd.api.types.is_datetime64_any_dtype(df[date_col]):
        df[date_col] = pd.to_datetime(df[date_col])

    forecaster = NaiveSeasonalForecaster()
    results: list[NaiveSeasonalResult] = []

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
