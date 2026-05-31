"""Seasonal index computation from historical sales data.

Computes week-of-year seasonal indices per SKU or category,
used by Method 6 (Calendar Events) and the ensemble aggregator.
"""

import pandas as pd
import numpy as np

from .calendar_features import get_week_calendar_features


def compute_seasonal_indices(
    weekly_sales: pd.DataFrame,
    group_col: str = "sku_id",
    min_weeks: int = 26,
) -> pd.DataFrame:
    """Compute seasonal index per week-of-year for each group.

    seasonal_index[week] = avg_sales_in_week / annual_avg_sales

    An index of 1.0 means average. Above 1.0 = above-average demand.
    Below 1.0 = below-average demand.

    Args:
        weekly_sales: DataFrame with columns [group_col, 'week_start_date', 'net_sold'].
            week_start_date must be datetime or parseable.
        group_col: Column to group by ('sku_id', 'category', etc.).
        min_weeks: Minimum weeks of history required per group. Groups with
            fewer weeks get neutral indices (all 1.0).

    Returns:
        DataFrame with columns [group_col, 'week_of_year', 'seasonal_index',
        'sample_weeks', 'avg_weekly_sales'].
    """
    df = weekly_sales.copy()

    if not pd.api.types.is_datetime64_any_dtype(df["week_start_date"]):
        df["week_start_date"] = pd.to_datetime(df["week_start_date"])

    df["week_of_year"] = df["week_start_date"].dt.isocalendar().week.astype(int)

    results = []

    for group_key, group_data in df.groupby(group_col):
        total_weeks = len(group_data)

        if total_weeks < min_weeks:
            # Not enough data — return neutral indices
            for woy in range(1, 54):
                results.append({
                    group_col: group_key,
                    "week_of_year": woy,
                    "seasonal_index": 1.0,
                    "sample_weeks": 0,
                    "avg_weekly_sales": 0.0,
                })
            continue

        annual_avg = group_data["net_sold"].mean()
        if annual_avg == 0:
            # Zero sales across all history — neutral indices
            for woy in range(1, 54):
                results.append({
                    group_col: group_key,
                    "week_of_year": woy,
                    "seasonal_index": 1.0,
                    "sample_weeks": 0,
                    "avg_weekly_sales": 0.0,
                })
            continue

        week_stats = group_data.groupby("week_of_year")["net_sold"].agg(
            ["mean", "count"]
        ).reset_index()

        week_stats.columns = ["week_of_year", "avg_weekly_sales", "sample_weeks"]
        week_stats["seasonal_index"] = week_stats["avg_weekly_sales"] / annual_avg
        week_stats[group_col] = group_key

        # Fill missing weeks with 1.0
        all_weeks = pd.DataFrame({"week_of_year": range(1, 54)})
        week_stats = all_weeks.merge(week_stats, on="week_of_year", how="left")
        week_stats[group_col] = week_stats[group_col].fillna(group_key)
        week_stats["seasonal_index"] = week_stats["seasonal_index"].fillna(1.0)
        week_stats["sample_weeks"] = week_stats["sample_weeks"].fillna(0).astype(int)
        week_stats["avg_weekly_sales"] = week_stats["avg_weekly_sales"].fillna(0.0)

        results.append(week_stats)

    if not results:
        return pd.DataFrame(columns=[group_col, "week_of_year", "seasonal_index",
                                     "sample_weeks", "avg_weekly_sales"])

    # Handle mixed list (some dicts from < min_weeks, some DataFrames)
    dfs = []
    rows = []
    for r in results:
        if isinstance(r, pd.DataFrame):
            dfs.append(r)
        else:
            rows.append(r)

    if rows:
        dfs.append(pd.DataFrame(rows))

    return pd.concat(dfs, ignore_index=True)


def enrich_weekly_data_with_calendar(
    weekly_sales: pd.DataFrame,
) -> pd.DataFrame:
    """Add calendar feature columns to a weekly sales DataFrame.

    Adds: is_holiday, holiday_name, event_multiplier, is_construction_season,
    is_summer_lull, is_salary_period, season_multiplier, salary_multiplier,
    combined_multiplier.

    Args:
        weekly_sales: DataFrame with 'week_start_date' column (datetime or str).

    Returns:
        New DataFrame with calendar feature columns appended.
    """
    df = weekly_sales.copy()

    if not pd.api.types.is_datetime64_any_dtype(df["week_start_date"]):
        df["week_start_date"] = pd.to_datetime(df["week_start_date"])

    # Get unique weeks to avoid recomputing
    unique_weeks = df["week_start_date"].dt.date.unique()

    features_map = {}
    for week_date in unique_weeks:
        features = get_week_calendar_features(week_date)
        features_map[week_date] = features._asdict()

    # Map features back to DataFrame
    df["_week_date"] = df["week_start_date"].dt.date

    feature_df = pd.DataFrame.from_dict(features_map, orient="index")
    feature_df.index.name = "_week_date"
    feature_df = feature_df.reset_index()

    df = df.merge(feature_df, on="_week_date", how="left")
    df = df.drop(columns=["_week_date"])

    return df
