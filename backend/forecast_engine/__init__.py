"""Forecast Engine v2.0 - Ensemble demand prediction system.

The Forecast Engine provides a modular, ensemble-based approach to demand forecasting
for supply chain optimization. It handles data ingestion, cleaning, and combines multiple
independent forecasting methods for robust predictions.

Key modules:
- ingestion: Load and validate raw sales data from CSV/Excel sources
- cleaning: Strip returns, detect anomalies, handle missing data
- data_models: Type definitions for sales transactions and demand structures
- calendar: Romanian holidays, Orthodox Easter, salary cycles, market seasons
- seasonality: Seasonal index computation from historical data
- config: Hardcoded event multipliers and market cycle definitions
- methods.ets_model: Holt-Winters exponential smoothing forecaster (Method 1)
- methods.lgbm_model: LightGBM global ML forecaster (Method 2)
- methods.category_relative: Category-driven relative performance forecaster (Method 3)
- methods.anomaly_adjusted: Anomaly-adjusted baseline forecaster (Method 4)
- methods.multi_scale_lag: Multi-scale temporal momentum forecaster (Method 5)
- methods.calendar_events: Calendar + seasonal events forecaster (Method 6)
- aggregation: Ensemble combiner — median/trimmed mean across all methods
"""

__version__ = "2.0.0"

from .ingestion import load_sales_data, validate_sales_data
from .cleaning import (
    clean_sales_data,
    detect_promotional_spikes,
    detect_stockouts,
)
from .calendar_features import (
    orthodox_easter,
    get_holidays_for_year,
    get_calendar_features,
    get_week_calendar_features,
)
from .seasonality import (
    compute_seasonal_indices,
    enrich_weekly_data_with_calendar,
)
from .methods.ets_model import ETSForecaster, forecast_all_skus
from .methods.lgbm_model import (
    LGBMForecaster,
    engineer_features,
    forecast_all_skus_lgbm,
)
from .methods.category_relative import (
    CategoryRelativeForecaster,
    forecast_all_skus_category_relative,
)
from .methods.anomaly_adjusted import (
    AnomalyAdjustedForecaster,
    forecast_all_skus_anomaly_adjusted,
)
from .methods.multi_scale_lag import (
    MultiScaleLagForecaster,
    calculate_lags,
    calculate_momentum_ratios,
    classify_trend_consistency,
    forecast_all_skus_multi_scale_lag,
)
from .methods.calendar_events import (
    CalendarEventsForecaster,
    forecast_all_skus_calendar_events,
    apply_event_multipliers,
)
from .aggregation import (
    EnsembleForecaster,
    combine_methods,
    aggregate_median,
    aggregate_trimmed_mean,
    aggregate_equal_weight,
    classify_disagreement,
)

__all__ = [
    "__version__",
    "load_sales_data",
    "validate_sales_data",
    "clean_sales_data",
    "detect_promotional_spikes",
    "detect_stockouts",
    "orthodox_easter",
    "get_holidays_for_year",
    "get_calendar_features",
    "get_week_calendar_features",
    "compute_seasonal_indices",
    "enrich_weekly_data_with_calendar",
    "ETSForecaster",
    "forecast_all_skus",
    "LGBMForecaster",
    "engineer_features",
    "forecast_all_skus_lgbm",
    "CategoryRelativeForecaster",
    "forecast_all_skus_category_relative",
    "AnomalyAdjustedForecaster",
    "forecast_all_skus_anomaly_adjusted",
    "MultiScaleLagForecaster",
    "calculate_lags",
    "calculate_momentum_ratios",
    "classify_trend_consistency",
    "forecast_all_skus_multi_scale_lag",
    "CalendarEventsForecaster",
    "forecast_all_skus_calendar_events",
    "apply_event_multipliers",
    "EnsembleForecaster",
    "combine_methods",
    "aggregate_median",
    "aggregate_trimmed_mean",
    "aggregate_equal_weight",
    "classify_disagreement",
]
