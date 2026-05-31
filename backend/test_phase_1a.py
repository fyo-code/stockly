#!/usr/bin/env python3
"""Test Phase 1A: Data Ingestion & Cleaning pipeline."""

import sys
import pandas as pd
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from forecast_engine import (
    load_sales_data,
    clean_sales_data,
    detect_promotional_spikes,
    detect_stockouts,
)


def main():
    print("\n" + "=" * 60)
    print("Phase 1A.5-1A.6: Testing Data Pipeline")
    print("=" * 60)

    # Load test data
    csv_path = Path(__file__).parent.parent / "data_samples" / "sales_data.csv"
    
    if not csv_path.exists():
        print(f"❌ Test data not found at {csv_path}")
        return False

    # 1A.1: Load and validate
    try:
        df = load_sales_data(str(csv_path))
        print(f"✓ 1A.1 Loaded {len(df)} rows from sales_data.csv")
        print(f"   Columns: {list(df.columns)}")
        print(f"   Unique SKUs: {df['sku_id'].nunique()}, Stores: {df['store_id'].nunique()}")
    except Exception as e:
        print(f"❌ 1A.1 FAILED: {e}")
        return False

    # 1A.2: Clean and detect anomalies
    try:
        df_clean = clean_sales_data(df)
        df_clean = detect_promotional_spikes(df_clean)
        df_clean = detect_stockouts(df_clean)
        print(f"✓ 1A.2 Cleaned data with anomaly detection")
        print(f"   Promotional weeks: {df_clean['is_promotional_week'].sum()}")
        print(f"   Stockout weeks: {df_clean['is_stockout_week'].sum()}")
    except Exception as e:
        print(f"❌ 1A.2 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

    # 1A.5: Weekly aggregation
    try:
        df_clean["week_start"] = df_clean["sale_date"].dt.to_period("W").dt.start_time
        weekly = (
            df_clean.groupby(["sku_id", "store_id", "week_start"])
            .agg(
                net_sold=("net_sold", "sum"),
                units_returned=("units_returned", "sum"),
                num_transaction_days=("sale_date", "nunique"),
                is_promotional_week=("is_promotional_week", "any"),
                is_stockout_week=("is_stockout_week", "any"),
            )
            .reset_index()
        )
        
        weekly["avg_daily_sales"] = weekly["net_sold"] / weekly["num_transaction_days"]
        weeks_per_combo = weekly.groupby(["sku_id", "store_id"]).size()
        
        print(f"✓ 1A.5 Aggregated to {len(weekly)} weekly records")
        print(f"   SKU-store combos: {weeks_per_combo.shape[0]}")
        print(f"   Weeks per combo: min={weeks_per_combo.min()}, max={weeks_per_combo.max()}")
    except Exception as e:
        print(f"❌ 1A.5 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

    # 1A.6: Verification
    try:
        total_original = df_clean["net_sold"].sum()
        total_weekly = weekly["net_sold"].sum()
        
        if total_original != total_weekly:
            print(f"❌ Data loss: {total_original} vs {total_weekly}")
            return False
            
        nulls = weekly.isnull().sum().sum()
        negatives = (weekly[["net_sold", "units_returned", "avg_daily_sales"]] < 0).sum().sum()
        
        print(f"✓ 1A.6 Verification complete")
        print(f"   No data loss: {total_original} units preserved")
        print(f"   Null values: {nulls}, Negative values: {negatives}")
        print(f"   Date range: {weekly['week_start'].min().date()} to {weekly['week_start'].max().date()}")
    except Exception as e:
        print(f"❌ 1A.6 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n" + "=" * 60)
    print("✅ Phase 1A.5-1A.6 Tests PASSED")
    print("=" * 60)
    print("\n📊 Weekly Demand Ready:")
    print(f"   {weekly.shape[0]} weekly records")
    print(f"   {weeks_per_combo.shape[0]} SKU-store combinations")
    print(f"   Total net_sold: {weekly['net_sold'].sum():,.0f} units")
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
