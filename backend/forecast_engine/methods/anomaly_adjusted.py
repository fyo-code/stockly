"""Anomaly-Adjusted Baseline forecaster (Method 4).

Establishes a "true baseline" demand by identifying and removing promotional
spikes, outliers, and inventory distortions from the historical record.
Projects the clean baseline forward with a recent growth rate.

Formula:
    Clean_Baseline = Median(history - anomalies - outliers)
    Forecast = Clean_Baseline × Growth_Rate × horizon

Requirements:
- Minimum 13 weeks of history (one full rolling window)
- Works best with 26+ weeks
"""

from typing import Optional

import numpy as np
import pandas as pd
from scipy.stats import norm

from ..data_models import AnomalyAdjustedResult


# --- Configuration ---

MIN_WEEKS_REQUIRED = 13
ROLLING_WINDOW = 13       # weeks for rolling average baseline
PROMO_THRESHOLD = 2.5     # deviation ratio to flag as promotional (normal SKUs)
PROMO_THRESHOLD_SPARSE = 3.5  # relaxed threshold for sparse SKUs (avg < 3 units/week)
SPARSE_WEEKLY_AVG = 3.0   # threshold: below this, SKU is "sparse"
OUTLIER_THRESHOLD = 3.0   # deviation ratio to flag as statistical outlier
RECENT_WINDOW = 13        # weeks for "recent" growth rate calculation

# Routing: SMOOTH SKUs only. LUMPY SKUs (>80% zero-weeks) mirror Croston's
# routing threshold (INTERMITTENT_THRESHOLD = 0.80). On LUMPY series the
# rolling average collapses to ~0 and real demand weeks get flagged as
# anomalies, producing clean-baseline=0 predictions (Iter 2 root cause:
# 97.3% of AA predictions were exactly 0 — PROGRESS.md, Iter 3 Fix #2).
SMOOTH_MAX_ZERO_PCT = 0.80


# --- Forecaster ---


class AnomalyAdjustedForecaster:
    """Robust baseline forecaster that strips anomalies before projecting.

    Steps:
    1. Compute rolling average (13-week window)
    2. Flag weeks where sales deviate > threshold from rolling avg
    3. Separate: promotional spikes (above) vs outliers (above or below)
    4. Calculate clean baseline = median of non-flagged weeks
    5. Growth rate = recent clean avg / historical clean avg
    6. Forecast = clean_baseline × growth_rate × horizon
    """

    def __init__(
        self,
        min_weeks: int = MIN_WEEKS_REQUIRED,
        rolling_window: int = ROLLING_WINDOW,
        promo_threshold: float = PROMO_THRESHOLD,
        promo_threshold_sparse: float = PROMO_THRESHOLD_SPARSE,
        sparse_weekly_avg: float = SPARSE_WEEKLY_AVG,
        outlier_threshold: float = OUTLIER_THRESHOLD,
        recent_window: int = RECENT_WINDOW,
    ):
        self._min_weeks = min_weeks
        self._rolling_window = rolling_window
        self._promo_threshold = promo_threshold
        self._promo_threshold_sparse = promo_threshold_sparse
        self._sparse_weekly_avg = sparse_weekly_avg
        self._outlier_threshold = outlier_threshold
        self._recent_window = recent_window

    def forecast(
        self,
        weekly_sales: pd.Series,
        sku_id: str = "",
        store_id: str = "",
    ) -> AnomalyAdjustedResult:
        """Fit anomaly-adjusted baseline and produce forecasts.

        Args:
            weekly_sales: Time-indexed Series of weekly net_sold values,
                sorted chronologically.
            sku_id: SKU identifier.
            store_id: Store identifier.

        Returns:
            AnomalyAdjustedResult with clean baseline forecast.
        """
        n_weeks = len(weekly_sales)

        if n_weeks < self._min_weeks:
            return self._fallback_result(
                weekly_sales, sku_id, store_id,
                error=f"Insufficient history: {n_weeks} weeks (need {self._min_weeks})",
            )

        sales = weekly_sales.astype(float).copy()

        # Adaptive threshold: sparse SKUs (avg < 3 units/week) get relaxed threshold
        avg_weekly = float(sales.mean())
        effective_promo_threshold = (
            self._promo_threshold_sparse
            if avg_weekly < self._sparse_weekly_avg
            else self._promo_threshold
        )

        # Step 1: Rolling average baseline
        rolling_avg = sales.rolling(
            window=self._rolling_window, min_periods=4, center=False
        ).mean()

        # Step 2+3: Flag anomalies
        deviation = (sales - rolling_avg).abs() / rolling_avg.replace(0, np.nan)

        is_promo = (deviation > effective_promo_threshold) & (sales > rolling_avg)
        is_outlier = (deviation > self._outlier_threshold) & ~is_promo
        is_anomaly = is_promo | is_outlier

        # Handle NaN from initial rolling window — not anomalies
        is_anomaly = is_anomaly.fillna(False)
        is_promo = is_promo.fillna(False)
        is_outlier = is_outlier.fillna(False)

        n_promo = int(is_promo.sum())
        n_outlier = int(is_outlier.sum())

        # Collect anomaly week dates
        anomaly_weeks = []
        if hasattr(weekly_sales.index, 'strftime'):
            anomaly_weeks = weekly_sales.index[is_anomaly].strftime("%Y-%m-%d").tolist()
        else:
            anomaly_weeks = [str(d) for d in weekly_sales.index[is_anomaly]]

        # Step 4: Clean baseline = median of non-anomaly weeks
        clean_sales = sales[~is_anomaly]

        if len(clean_sales) < 4:
            return self._fallback_result(
                weekly_sales, sku_id, store_id,
                error=f"Too many anomalies: only {len(clean_sales)} clean weeks remain",
            )

        clean_baseline = float(clean_sales.median())

        # Step 5: Growth rate from clean data
        # Recent clean avg vs historical clean avg
        recent_mask = (~is_anomaly) & (
            sales.index.isin(sales.index[-self._recent_window:])
        )
        recent_clean = sales[recent_mask]
        historical_clean = clean_sales

        recent_clean_avg = (
            float(recent_clean.median()) if len(recent_clean) >= 4
            else clean_baseline
        )
        historical_clean_avg = float(historical_clean.median())

        growth_rate = (
            recent_clean_avg / historical_clean_avg
            if historical_clean_avg > 0 else 1.0
        )

        # Step 6: Forecast
        forecast_weekly = clean_baseline * growth_rate
        forecast_4w = forecast_weekly * 4
        forecast_8w = forecast_weekly * 8

        # Confidence intervals from clean data variability
        clean_std = float(clean_sales.std(ddof=1)) if len(clean_sales) > 1 else 0.0
        ci_low_4w, ci_high_4w = self._confidence_interval(
            forecast_4w, clean_std, horizon=4
        )
        ci_low_8w, ci_high_8w = self._confidence_interval(
            forecast_8w, clean_std, horizon=8
        )

        return AnomalyAdjustedResult(
            method="anomaly_adjusted",
            sku_id=sku_id,
            store_id=store_id,
            forecast_4w=round(forecast_4w, 1),
            forecast_8w=round(forecast_8w, 1),
            confidence_low_4w=round(ci_low_4w, 1),
            confidence_high_4w=round(ci_high_4w, 1),
            confidence_low_8w=round(ci_low_8w, 1),
            confidence_high_8w=round(ci_high_8w, 1),
            clean_baseline=round(clean_baseline, 1),
            recent_growth_rate=round(growth_rate, 3),
            anomalies_detected=n_promo,
            outliers_detected=n_outlier,
            anomaly_weeks=anomaly_weeks,
            weeks_of_history=n_weeks,
            error=None,
        )

    def _confidence_interval(
        self,
        cumulative_forecast: float,
        weekly_std: float,
        horizon: int,
        alpha: float = 0.05,
    ) -> tuple[float, float]:
        """Prediction interval from clean-data standard deviation."""
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
    ) -> AnomalyAdjustedResult:
        """Naive fallback when anomaly detection can't run."""
        n = len(weekly_sales)
        mean_weekly = float(weekly_sales.mean()) if n > 0 else 0.0

        return AnomalyAdjustedResult(
            method="anomaly_adjusted",
            sku_id=sku_id,
            store_id=store_id,
            forecast_4w=round(mean_weekly * 4, 1),
            forecast_8w=round(mean_weekly * 8, 1),
            confidence_low_4w=0.0,
            confidence_high_4w=round(mean_weekly * 4 * 2, 1),
            confidence_low_8w=0.0,
            confidence_high_8w=round(mean_weekly * 8 * 2, 1),
            clean_baseline=round(mean_weekly, 1),
            recent_growth_rate=1.0,
            anomalies_detected=0,
            outliers_detected=0,
            anomaly_weeks=[],
            weeks_of_history=n,
            error=error,
        )


# --- Batch runner ---


def forecast_all_skus_anomaly_adjusted(
    weekly_demand: pd.DataFrame,
    sku_col: str = "sku_id",
    store_col: str = "store_id",
    date_col: str = "week_start_date",
    sales_col: str = "net_sold",
    smooth_max_zero_pct: float = SMOOTH_MAX_ZERO_PCT,
) -> list[AnomalyAdjustedResult]:
    """Run Anomaly-Adjusted forecaster across SMOOTH SKU-store pairs only.

    Routing: LUMPY SKUs (zero_pct > smooth_max_zero_pct, default 0.80) are
    skipped — Croston's handles them. See Iter 3 Fix #2 in PROGRESS.md.

    Args:
        weekly_demand: DataFrame with weekly aggregated demand.
        sku_col, store_col, date_col, sales_col: Column names.
        smooth_max_zero_pct: Max allowed zero-week share for SMOOTH routing.

    Returns:
        List of AnomalyAdjustedResult, one per SMOOTH SKU-store pair.
    """
    df = weekly_demand.copy()
    if not pd.api.types.is_datetime64_any_dtype(df[date_col]):
        df[date_col] = pd.to_datetime(df[date_col])

    forecaster = AnomalyAdjustedForecaster()
    results: list[AnomalyAdjustedResult] = []
    skipped_lumpy = 0

    for (sku, store), group in df.groupby([sku_col, store_col]):
        group_sorted = group.sort_values(date_col)
        sales_series = group_sorted.set_index(date_col)[sales_col]
        sales_series = sales_series.asfreq("W-MON", fill_value=0)

        # Routing gate — only SMOOTH demand patterns.
        if len(sales_series) > 0:
            zero_pct = float((sales_series <= 0).sum()) / len(sales_series)
            if zero_pct > smooth_max_zero_pct:
                skipped_lumpy += 1
                continue

        result = forecaster.forecast(
            weekly_sales=sales_series,
            sku_id=str(sku),
            store_id=str(store),
        )
        results.append(result)

    if skipped_lumpy:
        import logging
        logging.getLogger(__name__).info(
            "Anomaly-Adjusted routed: %d SMOOTH SKUs processed, %d LUMPY SKUs skipped "
            "(zero_pct > %.2f).",
            len(results), skipped_lumpy, smooth_max_zero_pct,
        )

    return results
