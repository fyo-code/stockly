"""LightGBM global machine learning forecaster (Method 2).

Trains a single gradient boosting model on ALL SKU-store pairs simultaneously,
learning cross-SKU patterns from temporal lags, calendar features, and product
characteristics. Produces point forecasts at 4-week and 8-week horizons with
feature importance for explainability.

Requirements:
- lightgbm >= 4.0
- Minimum 100 training rows across all SKUs combined

Library: lightgbm
"""

import warnings
from typing import Optional

import numpy as np
import pandas as pd
import lightgbm as lgb
from scipy.stats import norm

from ..data_models import LGBMResult
from ..calendar_features import get_week_calendar_features
from ..seasonality import enrich_weekly_data_with_calendar


# --- Configuration ---

MIN_TRAINING_ROWS = 100
VALIDATION_FRACTION = 0.2
EARLY_STOPPING_ROUNDS = 50

DEFAULT_PARAMS = {
    "objective": "regression",
    "metric": "rmse",
    "boosting_type": "gbdt",
    "num_leaves": 31,
    "learning_rate": 0.05,
    "feature_fraction": 0.8,
    "bagging_fraction": 0.8,
    "bagging_freq": 5,
    "verbose": -1,
    "min_child_samples": 10,
    "seed": 42,
}

TEMPORAL_FEATURES = [
    "sales_lag_1w", "sales_lag_2w", "sales_lag_4w",
    "sales_lag_13w", "sales_lag_26w", "sales_lag_52w",
    "rolling_avg_4w", "rolling_avg_13w",
    "yoy_growth_ratio", "trend_momentum",
]

PRODUCT_FEATURES = [
    "product_age_weeks", "is_mature", "historical_volatility",
]

CALENDAR_FEATURES = [
    "week_of_year", "month",
    "is_holiday", "event_multiplier",
    "is_construction_season", "is_summer_lull", "is_salary_period",
    "season_multiplier", "salary_multiplier", "combined_multiplier",
]

PROMOTION_FEATURES = [
    "is_promotional_week", "is_stockout_week",
    "weeks_since_last_promo",
]

CATEGORY_FEATURES = [
    "category_sales_lag_1w", "category_yoy_ratio",
    "sku_share_of_category_pct",
]


# --- Feature Engineering ---


def engineer_features(
    weekly_demand: pd.DataFrame,
    sku_col: str = "sku_id",
    store_col: str = "store_id",
    date_col: str = "week_start_date",
    sales_col: str = "net_sold",
    category_col: Optional[str] = None,
) -> pd.DataFrame:
    """Engineer features for LightGBM from weekly demand data.

    Creates temporal lags, rolling averages, calendar features,
    product-level features, and optionally category aggregates.
    LightGBM handles NaN natively, so lag-induced NaNs are kept.

    Args:
        weekly_demand: DataFrame with weekly aggregated demand.
        sku_col: SKU column name.
        store_col: Store column name.
        date_col: Date column name.
        sales_col: Sales column name.
        category_col: Optional category column for category-level features.

    Returns:
        Feature-enriched DataFrame with original columns preserved.
    """
    df = weekly_demand.copy()

    # Normalise date column name for compatibility with enrich_weekly_data_with_calendar
    renamed_date = False
    if date_col != "week_start_date":
        df = df.rename(columns={date_col: "week_start_date"})
        renamed_date = True
        date_col = "week_start_date"

    if not pd.api.types.is_datetime64_any_dtype(df[date_col]):
        df[date_col] = pd.to_datetime(df[date_col])

    df = df.sort_values([sku_col, store_col, date_col]).reset_index(drop=True)
    group_key = [sku_col, store_col]

    # --- Temporal lag features (per SKU-store) ---
    # Point lags: actual sales from N weeks ago
    for lag_weeks in [1, 2, 4, 13, 26, 52]:
        df[f"sales_lag_{lag_weeks}w"] = (
            df.groupby(group_key)[sales_col].shift(lag_weeks)
        )

    # Rolling averages (shifted by 1 week to prevent data leakage)
    df["rolling_avg_4w"] = df.groupby(group_key)[sales_col].transform(
        lambda x: x.shift(1).rolling(4, min_periods=1).mean()
    )
    df["rolling_avg_13w"] = df.groupby(group_key)[sales_col].transform(
        lambda x: x.shift(1).rolling(13, min_periods=1).mean()
    )

    # Year-over-year growth ratio
    df["yoy_growth_ratio"] = (
        df["rolling_avg_4w"] / df["sales_lag_52w"].replace(0, np.nan)
    )

    # Trend momentum: recent acceleration vs medium-term baseline
    df["trend_momentum"] = (
        (df["rolling_avg_4w"] - df["rolling_avg_13w"])
        / df["rolling_avg_13w"].replace(0, np.nan)
    )

    # --- Product features ---
    first_sale = df.groupby(group_key)[date_col].transform("min")
    df["product_age_weeks"] = (
        (df[date_col] - first_sale).dt.days / 7
    ).astype(int)
    df["is_mature"] = (df["product_age_weeks"] > 52).astype(int)

    # Historical volatility: coefficient of variation (expanding window)
    expanding_std = df.groupby(group_key)[sales_col].transform(
        lambda x: x.expanding(min_periods=4).std()
    )
    expanding_mean = df.groupby(group_key)[sales_col].transform(
        lambda x: x.expanding(min_periods=4).mean()
    )
    df["historical_volatility"] = expanding_std / expanding_mean.replace(0, np.nan)

    # --- Calendar features (from Phase 1B) ---
    df = enrich_weekly_data_with_calendar(df)
    # Adds: is_holiday, holiday_name, event_multiplier, is_construction_season,
    #        is_summer_lull, is_salary_period, season_multiplier, salary_multiplier,
    #        combined_multiplier

    # Convert booleans to int for LightGBM
    for bool_col in ["is_holiday", "is_construction_season", "is_summer_lull", "is_salary_period"]:
        if bool_col in df.columns:
            df[bool_col] = df[bool_col].astype(int)

    df["week_of_year"] = df[date_col].dt.isocalendar().week.astype(int)
    df["month"] = df[date_col].dt.month

    # --- Promotion features ---
    if "is_promotional_week" in df.columns:
        df["is_promotional_week"] = df["is_promotional_week"].astype(int)
    else:
        df["is_promotional_week"] = 0

    if "is_stockout_week" in df.columns:
        df["is_stockout_week"] = df["is_stockout_week"].astype(int)
    else:
        df["is_stockout_week"] = 0

    df["weeks_since_last_promo"] = _compute_weeks_since_promo(
        df, group_key, "is_promotional_week"
    )

    # --- Category features (optional) ---
    if category_col and category_col in df.columns:
        df = _add_category_features(df, category_col, date_col, sales_col)
    else:
        for col in CATEGORY_FEATURES:
            df[col] = np.nan

    # Restore original date column name if it was renamed
    if renamed_date:
        df = df.rename(columns={"week_start_date": date_col})

    return df


def _compute_weeks_since_promo(
    df: pd.DataFrame,
    group_key: list[str],
    promo_col: str,
) -> pd.Series:
    """Compute weeks since last promotional week per SKU-store group."""
    result = pd.Series(np.nan, index=df.index)

    for _, group in df.groupby(group_key):
        promo_mask = group[promo_col] == 1
        counter = np.nan

        for idx in group.index:
            if promo_mask.loc[idx]:
                counter = 0.0
            elif not np.isnan(counter):
                counter += 1.0
            result.loc[idx] = counter

    return result


def _add_category_features(
    df: pd.DataFrame,
    category_col: str,
    date_col: str,
    sales_col: str,
) -> pd.DataFrame:
    """Add category-level aggregate features to the DataFrame."""
    # Category total sales per week
    cat_weekly = (
        df.groupby([category_col, date_col])[sales_col]
        .sum()
        .reset_index()
        .rename(columns={sales_col: "_cat_total"})
    )
    cat_weekly = cat_weekly.sort_values([category_col, date_col])

    # Category-level lag and rolling average
    cat_weekly["category_sales_lag_1w"] = (
        cat_weekly.groupby(category_col)["_cat_total"].shift(1)
    )
    cat_rolling_4w = cat_weekly.groupby(category_col)["_cat_total"].transform(
        lambda x: x.shift(1).rolling(4, min_periods=1).mean()
    )
    cat_rolling_52w = cat_weekly.groupby(category_col)["_cat_total"].transform(
        lambda x: x.shift(1).rolling(52, min_periods=4).mean()
    )
    cat_weekly["category_yoy_ratio"] = (
        cat_rolling_4w / cat_rolling_52w.replace(0, np.nan)
    )

    # Merge category lag + yoy back to main df
    df = df.merge(
        cat_weekly[[category_col, date_col, "category_sales_lag_1w", "category_yoy_ratio"]],
        on=[category_col, date_col],
        how="left",
    )

    # SKU share of category (this week's SKU sales / this week's category total)
    df = df.merge(
        cat_weekly[[category_col, date_col, "_cat_total"]],
        on=[category_col, date_col],
        how="left",
    )
    df["sku_share_of_category_pct"] = (
        df[sales_col] / df["_cat_total"].replace(0, np.nan)
    )
    df = df.drop(columns=["_cat_total"])

    return df


# --- Model ---


class LGBMForecaster:
    """Global LightGBM forecaster that learns patterns across all SKU-store pairs.

    Trains a single gradient boosting model on all historical data simultaneously.
    Learns cross-SKU patterns, seasonal effects, and momentum signals.
    Uses recursive multi-step prediction for 4-week and 8-week horizons.
    """

    def __init__(
        self,
        params: Optional[dict] = None,
        min_training_rows: int = MIN_TRAINING_ROWS,
        validation_fraction: float = VALIDATION_FRACTION,
    ):
        self._params = {**DEFAULT_PARAMS, **(params or {})}
        self._min_training_rows = min_training_rows
        self._validation_fraction = validation_fraction
        self._model: Optional[lgb.Booster] = None
        self._feature_names: list[str] = []
        self._residual_std: float = 0.0
        self._val_r_squared: float = 0.0
        self._feature_importance: dict[str, float] = {}

    @property
    def is_trained(self) -> bool:
        return self._model is not None

    def train(
        self,
        featured_df: pd.DataFrame,
        target_col: str = "net_sold",
        date_col: str = "week_start_date",
    ) -> dict:
        """Train LightGBM on feature-engineered DataFrame.

        Uses a temporal split (last N% of rows by date as validation)
        with early stopping to prevent overfitting.

        Args:
            featured_df: DataFrame with features from engineer_features().
            target_col: Column to predict.
            date_col: Date column for temporal ordering.

        Returns:
            Dict with training metrics (n_train, n_val, val_rmse, etc.).

        Raises:
            ValueError: If insufficient training data.
        """
        # Determine which feature columns are actually available
        all_candidate_features = (
            TEMPORAL_FEATURES + PRODUCT_FEATURES
            + CALENDAR_FEATURES + PROMOTION_FEATURES + CATEGORY_FEATURES
        )
        available_features = [
            f for f in all_candidate_features
            if f in featured_df.columns and not featured_df[f].isna().all()
        ]

        # Prepare training data: drop rows with missing target, sort by date
        train_df = featured_df[[date_col, target_col] + available_features].copy()
        train_df = train_df.dropna(subset=[target_col])
        train_df = train_df.sort_values(date_col).reset_index(drop=True)

        if len(train_df) < self._min_training_rows:
            raise ValueError(
                f"Insufficient training data: {len(train_df)} rows "
                f"(need {self._min_training_rows})"
            )

        self._feature_names = available_features

        # Temporal split: earlier rows for training, later rows for validation
        n = len(train_df)
        split_idx = int(n * (1 - self._validation_fraction))
        train_slice = train_df.iloc[:split_idx]
        val_slice = train_df.iloc[split_idx:]

        X_train = train_slice[available_features]
        y_train = train_slice[target_col]
        X_val = val_slice[available_features]
        y_val = val_slice[target_col]

        dtrain = lgb.Dataset(X_train, label=y_train, free_raw_data=False)
        dval = lgb.Dataset(X_val, label=y_val, reference=dtrain, free_raw_data=False)

        # Train with early stopping
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self._model = lgb.train(
                self._params,
                dtrain,
                valid_sets=[dval],
                num_boost_round=500,
                callbacks=[
                    lgb.early_stopping(EARLY_STOPPING_ROUNDS),
                    lgb.log_evaluation(0),
                ],
            )

        # Validation metrics
        val_preds = self._model.predict(X_val)
        residuals = y_val.values - val_preds
        self._residual_std = (
            float(np.std(residuals, ddof=1)) if len(residuals) > 1 else 0.0
        )

        ss_res = float(np.sum(residuals ** 2))
        ss_tot = float(np.sum((y_val.values - y_val.mean()) ** 2))
        self._val_r_squared = max(0.0, 1.0 - ss_res / ss_tot) if ss_tot > 0 else 0.0

        # Feature importance (gain-based, normalised to sum to 1)
        raw_importance = self._model.feature_importance(importance_type="gain")
        total = raw_importance.sum()
        if total > 0:
            self._feature_importance = {
                name: round(float(imp / total), 4)
                for name, imp in zip(self._feature_names, raw_importance)
            }
        else:
            self._feature_importance = {name: 0.0 for name in self._feature_names}

        return {
            "n_train": len(train_slice),
            "n_val": len(val_slice),
            "n_features": len(available_features),
            "best_iteration": self._model.best_iteration,
            "val_rmse": round(float(np.sqrt(np.mean(residuals ** 2))), 3),
            "val_r_squared": round(self._val_r_squared, 4),
            "residual_std": round(self._residual_std, 2),
        }

    def forecast(
        self,
        featured_df: pd.DataFrame,
        sku_id: str,
        store_id: str,
        sku_col: str = "sku_id",
        store_col: str = "store_id",
        date_col: str = "week_start_date",
        sales_col: str = "net_sold",
    ) -> LGBMResult:
        """Generate 4-week and 8-week forecast for a single SKU-store.

        Uses recursive multi-step prediction: each week's prediction
        feeds into the next week's lag features.

        Args:
            featured_df: Feature-enriched DataFrame (from engineer_features).
            sku_id: SKU to forecast.
            store_id: Store to forecast.
            sku_col, store_col, date_col, sales_col: Column names.

        Returns:
            LGBMResult with forecasts, confidence intervals, feature importance.
        """
        if not self.is_trained:
            return self._error_result(sku_id, store_id, 0, "Model not trained")

        mask = (featured_df[sku_col] == sku_id) & (featured_df[store_col] == store_id)
        sku_data = featured_df.loc[mask].sort_values(date_col)

        if sku_data.empty:
            return self._error_result(
                sku_id, store_id, 0,
                f"No data for SKU {sku_id} / store {store_id}",
            )

        n_weeks = len(sku_data)
        last_row = sku_data.iloc[-1]
        last_date = pd.Timestamp(last_row[date_col])

        # Recent sales history for updating lags during recursive prediction
        recent_sales = sku_data[sales_col].values.tolist()

        # Base features from the last known row
        base_features = {
            col: (float(last_row[col]) if pd.notna(last_row[col]) else np.nan)
            for col in self._feature_names
            if col in last_row.index
        }

        # Recursive 8-week prediction
        weekly_predictions = self._recursive_predict(
            base_features, last_date, recent_sales, horizon=8
        )

        forecast_4w = float(sum(weekly_predictions[:4]))
        forecast_8w = float(sum(weekly_predictions[:8]))

        ci_low_4w, ci_high_4w = self._confidence_interval(forecast_4w, horizon=4)
        ci_low_8w, ci_high_8w = self._confidence_interval(forecast_8w, horizon=8)

        top_drivers = self._generate_top_drivers(base_features)

        # Top-10 features by importance
        sorted_importance = dict(sorted(
            self._feature_importance.items(),
            key=lambda x: x[1], reverse=True,
        )[:10])

        return LGBMResult(
            method="lightgbm",
            sku_id=sku_id,
            store_id=store_id,
            forecast_4w=round(forecast_4w, 1),
            forecast_8w=round(forecast_8w, 1),
            confidence_low_4w=round(ci_low_4w, 1),
            confidence_high_4w=round(ci_high_4w, 1),
            confidence_low_8w=round(ci_low_8w, 1),
            confidence_high_8w=round(ci_high_8w, 1),
            model_fit_quality=round(self._val_r_squared, 3),
            feature_importance=sorted_importance,
            top_drivers=top_drivers,
            weeks_of_history=n_weeks,
            error=None,
        )

    # --- Private helpers ---

    def _recursive_predict(
        self,
        base_features: dict,
        last_date: pd.Timestamp,
        recent_sales: list[float],
        horizon: int = 8,
    ) -> list[float]:
        """Generate multi-step forecast via recursive prediction.

        Each step predicts one week ahead, uses that prediction to
        update lag features, then predicts the next week.
        """
        predictions: list[float] = []
        sales_history = list(recent_sales)
        features = dict(base_features)

        for h in range(horizon):
            next_date = last_date + pd.Timedelta(weeks=h + 1)

            # Update calendar features for the future week
            try:
                cal = get_week_calendar_features(next_date.date())
                features["week_of_year"] = int(next_date.isocalendar()[1])
                features["month"] = next_date.month
                features["is_holiday"] = int(cal.is_holiday)
                features["event_multiplier"] = cal.event_multiplier
                features["is_construction_season"] = int(cal.is_construction_season)
                features["is_summer_lull"] = int(cal.is_summer_lull)
                features["is_salary_period"] = int(cal.is_salary_period)
                features["season_multiplier"] = cal.season_multiplier
                features["salary_multiplier"] = cal.salary_multiplier
                features["combined_multiplier"] = cal.combined_multiplier
            except Exception:
                pass  # keep previous calendar features if lookup fails

            # Update temporal lags from sales history
            n = len(sales_history)
            features["sales_lag_1w"] = sales_history[-1] if n >= 1 else np.nan
            features["sales_lag_2w"] = sales_history[-2] if n >= 2 else np.nan
            features["sales_lag_4w"] = sales_history[-4] if n >= 4 else np.nan
            features["sales_lag_13w"] = sales_history[-13] if n >= 13 else np.nan
            features["sales_lag_26w"] = sales_history[-26] if n >= 26 else np.nan
            features["sales_lag_52w"] = sales_history[-52] if n >= 52 else np.nan

            features["rolling_avg_4w"] = (
                float(np.mean(sales_history[-4:])) if n >= 1 else np.nan
            )
            features["rolling_avg_13w"] = (
                float(np.mean(sales_history[-13:])) if n >= 1 else np.nan
            )

            # Derived growth metrics
            lag_52 = features.get("sales_lag_52w")
            avg_4 = features.get("rolling_avg_4w")
            avg_13 = features.get("rolling_avg_13w")

            if _is_valid(lag_52) and lag_52 > 0 and _is_valid(avg_4):
                features["yoy_growth_ratio"] = avg_4 / lag_52
            else:
                features["yoy_growth_ratio"] = np.nan

            if _is_valid(avg_13) and avg_13 > 0 and _is_valid(avg_4):
                features["trend_momentum"] = (avg_4 - avg_13) / avg_13
            else:
                features["trend_momentum"] = np.nan

            # Advance product age
            age = features.get("product_age_weeks")
            if _is_valid(age):
                features["product_age_weeks"] = age + 1
                features["is_mature"] = int(features["product_age_weeks"] > 52)

            # Future weeks: assume no promotion / stockout (unknown)
            features["is_promotional_week"] = 0
            features["is_stockout_week"] = 0
            wslp = features.get("weeks_since_last_promo")
            if _is_valid(wslp):
                features["weeks_since_last_promo"] = wslp + 1

            # Build single-row DataFrame in the exact feature order the model expects
            feature_row = pd.DataFrame([{
                col: features.get(col, np.nan) for col in self._feature_names
            }])
            pred = float(self._model.predict(feature_row)[0])
            pred = max(0.0, pred)

            predictions.append(pred)
            sales_history.append(pred)

        return predictions

    def _confidence_interval(
        self,
        cumulative_forecast: float,
        horizon: int,
        alpha: float = 0.05,
    ) -> tuple[float, float]:
        """Prediction interval for cumulative forecast over horizon weeks.

        Uses residual standard error from validation scaled by sqrt(horizon).
        """
        z = norm.ppf(1 - alpha / 2)
        cumulative_se = self._residual_std * np.sqrt(horizon)

        lower = max(0.0, cumulative_forecast - z * cumulative_se)
        upper = cumulative_forecast + z * cumulative_se
        return lower, upper

    def _generate_top_drivers(
        self,
        features: dict,
        n_drivers: int = 3,
    ) -> list[str]:
        """Generate human-readable explanations from the most important features."""
        if not self._feature_importance:
            return []

        sorted_features = sorted(
            self._feature_importance.items(),
            key=lambda x: x[1],
            reverse=True,
        )[:n_drivers]

        descriptions = {
            "sales_lag_52w": lambda v: f"Same week last year: {v:.0f} units",
            "sales_lag_1w": lambda v: f"Last week sales: {v:.0f} units",
            "rolling_avg_4w": lambda v: f"4-week average: {v:.1f} units/week",
            "rolling_avg_13w": lambda v: f"13-week average: {v:.1f} units/week",
            "yoy_growth_ratio": lambda v: f"YoY growth: {(v - 1) * 100:+.1f}%",
            "trend_momentum": lambda v: f"Trend momentum: {v * 100:+.1f}%",
            "product_age_weeks": lambda v: f"Product age: {v:.0f} weeks",
            "event_multiplier": lambda v: f"Event effect: {v:.2f}x",
            "combined_multiplier": lambda v: f"Calendar effect: {v:.2f}x",
            "week_of_year": lambda v: f"Week {v:.0f} of year",
            "historical_volatility": lambda v: f"Volatility: {v:.2f}",
            "category_yoy_ratio": lambda v: f"Category YoY: {(v - 1) * 100:+.1f}%",
            "sku_share_of_category_pct": lambda v: f"Category share: {v * 100:.1f}%",
        }

        drivers = []
        for feat_name, importance in sorted_features:
            val = features.get(feat_name)
            if not _is_valid(val):
                drivers.append(f"{feat_name}: {importance:.1%} importance")
                continue
            if feat_name in descriptions:
                try:
                    drivers.append(descriptions[feat_name](float(val)))
                except (ValueError, TypeError):
                    drivers.append(f"{feat_name}: {val}")
            else:
                drivers.append(f"{feat_name}: {val}")
        return drivers

    def _error_result(
        self,
        sku_id: str,
        store_id: str,
        weeks: int,
        error: str,
    ) -> LGBMResult:
        """Produce a fallback result when forecast cannot be generated."""
        return LGBMResult(
            method="lightgbm",
            sku_id=sku_id,
            store_id=store_id,
            forecast_4w=0.0,
            forecast_8w=0.0,
            confidence_low_4w=0.0,
            confidence_high_4w=0.0,
            confidence_low_8w=0.0,
            confidence_high_8w=0.0,
            model_fit_quality=0.0,
            feature_importance={},
            top_drivers=[],
            weeks_of_history=weeks,
            error=error,
        )


# --- Utility ---


def _is_valid(val) -> bool:
    """Check whether a value is non-None and non-NaN."""
    if val is None:
        return False
    try:
        return not np.isnan(val)
    except (TypeError, ValueError):
        return True


# --- Batch runner ---


def forecast_all_skus_lgbm(
    weekly_demand: pd.DataFrame,
    sku_col: str = "sku_id",
    store_col: str = "store_id",
    date_col: str = "week_start_date",
    sales_col: str = "net_sold",
    category_col: Optional[str] = None,
    params: Optional[dict] = None,
) -> tuple[list[LGBMResult], dict]:
    """Train a global LightGBM model and forecast every SKU-store pair.

    Args:
        weekly_demand: DataFrame with weekly aggregated demand.
        sku_col, store_col, date_col, sales_col: Column names.
        category_col: Optional category column for category features.
        params: Optional LightGBM hyperparameter overrides.

    Returns:
        (results, training_info) — list of LGBMResult dicts and a
        training metrics dict.
    """
    # Step 1: Feature engineering
    featured_df = engineer_features(
        weekly_demand,
        sku_col=sku_col,
        store_col=store_col,
        date_col=date_col,
        sales_col=sales_col,
        category_col=category_col,
    )

    # Step 2: Train global model
    forecaster = LGBMForecaster(params=params)

    try:
        training_info = forecaster.train(
            featured_df,
            target_col=sales_col,
            date_col=date_col,
        )
    except ValueError as e:
        # Not enough data — return error results for every SKU-store
        results = []
        for (sku, store), group in weekly_demand.groupby([sku_col, store_col]):
            results.append(forecaster._error_result(
                str(sku), str(store), len(group), str(e),
            ))
        return results, {"error": str(e)}

    # Step 3: Generate forecasts
    results: list[LGBMResult] = []
    for (sku, store), _ in featured_df.groupby([sku_col, store_col]):
        result = forecaster.forecast(
            featured_df,
            sku_id=str(sku),
            store_id=str(store),
            sku_col=sku_col,
            store_col=store_col,
            date_col=date_col,
            sales_col=sales_col,
        )
        results.append(result)

    return results, training_info
