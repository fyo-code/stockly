"""Sales data cleaning and anomaly detection module."""

import pandas as pd
import numpy as np


def clean_sales_data(df: pd.DataFrame) -> pd.DataFrame:
    """Clean sales data by stripping returns.
    
    Calculates net_sold = units_sold - units_returned (clipped to 0 minimum).
    Fills null units_returned with 0.
    """
    df_clean = df.copy()
    df_clean["units_returned"] = df_clean["units_returned"].fillna(0)
    df_clean["net_sold"] = (df_clean["units_sold"] - df_clean["units_returned"]).clip(lower=0)
    df_clean["net_sold"] = df_clean["net_sold"].astype(int)
    return df_clean


def detect_promotional_spikes(
    df: pd.DataFrame,
    threshold: float = 2.5,
    window: int = 13
) -> pd.DataFrame:
    """Detect promotional spikes (sales > rolling_avg * threshold)."""
    df_copy = df.copy()
    
    if not pd.api.types.is_datetime64_any_dtype(df_copy["sale_date"]):
        df_copy["sale_date"] = pd.to_datetime(df_copy["sale_date"])
    
    df_copy = df_copy.sort_values(["sku_id", "store_id", "sale_date"]).reset_index(drop=True)
    
    # Calculate rolling average per SKU-store
    rolling_avgs = []
    for (sku, store), group_idx in df_copy.groupby(["sku_id", "store_id"], sort=False).groups.items():
        group = df_copy.loc[group_idx].copy()
        group["rolling_avg"] = group["net_sold"].rolling(window=window, min_periods=1).mean()
        rolling_avgs.append(group)
    
    df_copy = pd.concat(rolling_avgs, ignore_index=False).sort_index()
    df_copy["is_promotional_week"] = df_copy["net_sold"] > (df_copy["rolling_avg"] * threshold)
    df_copy = df_copy.drop(columns=["rolling_avg"])
    
    return df_copy


def detect_stockouts(
    df: pd.DataFrame,
    min_consecutive_weeks: int = 2
) -> pd.DataFrame:
    """Detect stockout periods (consecutive zero-sales weeks)."""
    df_copy = df.copy()
    
    if not pd.api.types.is_datetime64_any_dtype(df_copy["sale_date"]):
        df_copy["sale_date"] = pd.to_datetime(df_copy["sale_date"])
    
    df_copy = df_copy.sort_values(["sku_id", "store_id", "sale_date"]).reset_index(drop=True)
    df_copy["is_zero_sales"] = df_copy["net_sold"] == 0
    df_copy["is_stockout_week"] = False
    
    for (sku, store), group_idx in df_copy.groupby(["sku_id", "store_id"], sort=False).groups.items():
        group_data = df_copy.loc[group_idx].copy()
        zero_runs = (group_data["is_zero_sales"] != group_data["is_zero_sales"].shift()).cumsum()
        
        for run_id, run_group in group_data[group_data["is_zero_sales"]].groupby(zero_runs[group_data["is_zero_sales"]]):
            if len(run_group) >= min_consecutive_weeks:
                df_copy.loc[run_group.index, "is_stockout_week"] = True
    
    df_copy = df_copy.drop(columns=["is_zero_sales"])
    return df_copy
