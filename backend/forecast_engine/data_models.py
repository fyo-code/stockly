"""Type definitions for demand forecasting data structures."""

from typing import TypedDict, Optional


class RawSalesTransaction(TypedDict):
    """Single raw sales transaction from source CSV."""
    sku_id: str
    store_id: str
    sale_date: str
    units_sold: int
    units_returned: Optional[int]


class CleanedSalesTransaction(TypedDict):
    """Sales transaction after cleaning."""
    sku_id: str
    store_id: str
    sale_date: str
    units_sold: int
    units_returned: int
    net_sold: int
    is_promotional_week: bool
    is_stockout_week: bool


class WeeklyDemand(TypedDict):
    """Weekly aggregated demand."""
    sku_id: str
    store_id: str
    week_start_date: str
    week_number: int
    year: int
    net_sold: int
    units_returned: int
    num_transaction_days: int
    is_promotional_week: bool
    is_stockout_week: bool
    avg_daily_sales: float


class ForecastOutput(TypedDict):
    """Single forecast point from a method."""
    sku_id: str
    store_id: str
    forecast_week_start: str
    method_name: str
    point_forecast: float
    lower_bound: Optional[float]
    upper_bound: Optional[float]


class ETSResult(TypedDict):
    """Output from ETS/Holt-Winters forecaster for a single SKU-store pair."""
    method: str  # always "ets"
    sku_id: str
    store_id: str
    forecast_4w: float
    forecast_8w: float
    confidence_low_4w: float
    confidence_high_4w: float
    confidence_low_8w: float
    confidence_high_8w: float
    model_fit_quality: float  # R-squared (0-1)
    seasonal_indices: dict[int, float]  # week_of_year -> index
    trend: str  # "GROWING", "DECLINING", or "STABLE"
    trend_slope: float  # weekly units change
    weeks_of_history: int
    error: Optional[str]  # None if successful, error message if model failed


class LGBMResult(TypedDict):
    """Output from LightGBM forecaster for a single SKU-store pair."""
    method: str  # always "lightgbm"
    sku_id: str
    store_id: str
    forecast_4w: float
    forecast_8w: float
    confidence_low_4w: float
    confidence_high_4w: float
    confidence_low_8w: float
    confidence_high_8w: float
    model_fit_quality: float  # R-squared on validation set (0-1)
    feature_importance: dict[str, float]  # top features -> normalized importance
    top_drivers: list[str]  # human-readable explanations
    weeks_of_history: int
    error: Optional[str]  # None if successful, error message if failed


class CategoryRelativeResult(TypedDict):
    """Output from Category-Relative forecaster for a single SKU-store pair."""
    method: str  # always "category_relative"
    sku_id: str
    store_id: str
    forecast_4w: float
    forecast_8w: float
    confidence_low_4w: float
    confidence_high_4w: float
    confidence_low_8w: float
    confidence_high_8w: float
    category_forecast_4w: float  # category-level 4-week forecast
    category_forecast_8w: float
    sku_share_of_category: float  # this SKU's share (0-1)
    sku_performance_vs_category: float  # 1.0 = in line, <1 = underperforming
    category_yoy_ratio: float  # category year-over-year growth
    category_trend: str  # "GROWING", "DECLINING", or "STABLE"
    weeks_of_history: int
    error: Optional[str]


class AnomalyAdjustedResult(TypedDict):
    """Output from Anomaly-Adjusted Baseline forecaster for a single SKU-store pair."""
    method: str  # always "anomaly_adjusted"
    sku_id: str
    store_id: str
    forecast_4w: float
    forecast_8w: float
    confidence_low_4w: float
    confidence_high_4w: float
    confidence_low_8w: float
    confidence_high_8w: float
    clean_baseline: float  # median weekly demand after removing anomalies
    recent_growth_rate: float  # recent clean avg / historical clean avg
    anomalies_detected: int  # number of anomaly weeks flagged
    outliers_detected: int  # number of statistical outliers
    anomaly_weeks: list[str]  # ISO dates of anomaly weeks
    weeks_of_history: int
    error: Optional[str]


class MultiScaleLagResult(TypedDict):
    """Output from Multi-Scale Lag forecaster for a single SKU-store pair."""
    method: str  # always "multi_scale_lag"
    sku_id: str
    store_id: str
    forecast_4w: float
    forecast_8w: float
    confidence_low_4w: float
    confidence_high_4w: float
    confidence_low_8w: float
    confidence_high_8w: float
    lag_1w: float   # most recent week avg
    lag_4w: float   # 4-week rolling avg
    lag_13w: float  # 13-week rolling avg
    lag_26w: float  # 26-week rolling avg
    lag_52w: float  # 52-week rolling avg (or None if insufficient)
    momentum_short: float   # lag_1w / lag_4w — very short-term momentum
    momentum_medium: float  # lag_4w / lag_13w — medium-term momentum
    momentum_long: float    # lag_13w / lag_26w — long-term momentum
    trend_consistency: str  # "STRONG_GROWTH", "STRONG_DECLINE", "STABLE", "UNSTABLE"
    weeks_of_history: int
    error: Optional[str]


class CalendarResult(TypedDict):
    """Output from Calendar Events forecaster for a single SKU-store pair."""
    method: str  # always "calendar_events"
    sku_id: str
    store_id: str
    forecast_4w: float
    forecast_8w: float
    confidence_low_4w: float
    confidence_high_4w: float
    confidence_low_8w: float
    confidence_high_8w: float
    base_demand_weekly: float       # clean baseline (median of recent clean weeks)
    avg_seasonal_index_4w: float    # average seasonal index across next 4 weeks
    avg_seasonal_index_8w: float    # average seasonal index across next 8 weeks
    peak_event: Optional[str]       # highest-multiplier event in forecast window (or None)
    peak_event_multiplier: float    # multiplier of that event (1.0 if no event)
    weeks_of_history: int
    error: Optional[str]


class MethodBreakdown(TypedDict):
    """Per-method summary within ensemble output."""
    forecast_4w: float
    forecast_8w: float
    confidence_low_4w: float
    confidence_high_4w: float
    confidence_low_8w: float
    confidence_high_8w: float
    error: Optional[str]


class CrostonsResult(TypedDict):
    """Output from Croston's method for intermittent demand SKUs."""
    method: str  # always "crostons"
    sku_id: str
    store_id: str
    forecast_4w: float
    forecast_8w: float
    confidence_low_4w: float
    confidence_high_4w: float
    confidence_low_8w: float
    confidence_high_8w: float
    mean_demand_size: float      # average non-zero demand
    mean_inter_arrival: float    # average weeks between demands
    demand_rate_per_week: float  # mean_demand_size / mean_inter_arrival
    zero_week_pct: float         # % of weeks with zero demand
    num_demand_events: int       # how many non-zero weeks
    weeks_of_history: int
    error: Optional[str]


class EnsembleForecastResult(TypedDict):
    """Final ensemble forecast combining all methods for a single SKU-store pair."""
    sku_id: str
    store_id: str
    forecast_4w: float
    forecast_8w: float
    confidence_low_4w: float
    confidence_high_4w: float
    confidence_low_8w: float
    confidence_high_8w: float
    method_breakdown: dict[str, MethodBreakdown]  # method_name -> summary
    methods_succeeded: int      # how many methods contributed (0-6)
    methods_failed: int         # how many methods returned errors
    method_disagreement_4w: str  # "LOW", "MEDIUM", "HIGH" based on CV
    method_disagreement_8w: str
    aggregation_method: str     # "median" or "trimmed_mean"
    generated_at: str           # ISO timestamp


class EnsembleWeights(TypedDict):
    """Weights for ensemble methods."""
    exponential_smoothing: float
    lightgbm: float
    category_relative: float
    anomaly_adjusted: float
    multi_scale_lag: float
    calendar_events: float
