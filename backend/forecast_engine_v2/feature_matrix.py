"""Leak-safe feature matrix for forecast engine v2 direct 4-week models."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from .regime_labels import RULE_VERSION, build_regime_labels, write_regime_labels
    from .scorecard import DB_PATH, ScorecardConfig, build_actuals, build_naive_predictions
except ImportError:  # Allows direct script execution.
    from regime_labels import RULE_VERSION, build_regime_labels, write_regime_labels
    from scorecard import DB_PATH, ScorecardConfig, build_actuals, build_naive_predictions


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REPORT = PROJECT_ROOT / "active_docs" / "ITER5N_V2_PHASE8E_AVAILABILITY_FEATURE_MATRIX.md"
DEFAULT_TARGET_STARTS = [
    "2024-04-29",
    "2024-05-27",
    "2024-07-01",
    "2024-07-29",
    "2024-08-26",
    "2024-09-23",
    "2024-10-28",
    "2024-11-25",
    "2024-12-30",
    "2025-01-27",
    "2025-02-24",
    "2025-03-24",
]

BF_WINDOWS = {
    2022: ("2022-11-09", "2022-11-20"),
    2023: ("2023-11-06", "2023-11-19"),
    2024: ("2024-11-04", "2024-11-24"),
    2025: ("2025-11-03", "2025-11-23"),
}

MAX_VALID_DISCOUNT_PCT = 1.0

CATEGORICAL_FEATURES = [
    "category_norm",
    "product_family_v2",
    "category_signal_status",
    "revenue_bucket",
    "volume_bucket",
    "stock_signal_status",
    "stock_coverage_bucket",
    "supplier_stock_signal_status",
    "supplier_stock_coverage_bucket",
    "combined_stock_coverage_bucket",
]

NUMERIC_FEATURES = [
    "target_month",
    "target_quarter",
    "target_weekofyear",
    "target_is_q4",
    "target_is_black_friday_month",
    "target_is_bf_window",
    "target_is_pre_bf_4w",
    "target_is_post_bf_4w",
    "target_days_from_bf_start",
    "target_days_from_bf_end",
    "horizon_bf_overlap_days",
    "horizon_pre_bf_overlap_days",
    "horizon_post_bf_overlap_days",
    "trailing_52w_revenue",
    "trailing_52w_pos_units",
    "active_weeks_52",
    "active_4w_windows_52",
    "avg_units_per_4w_52",
    "revenue_rank",
    "cumulative_revenue_share",
    "active_months_104",
    "top3_month_unit_share_104",
    "monthly_cv_104",
    "active_years_104",
    "recurring_active_months_104",
    "last4",
    "roll8_mean",
    "roll13_mean",
    "seasonal52",
    "median_naive",
    "last4_to_roll13",
    "seasonal_to_roll13",
    "median_to_avg4w",
    "pos_units_4w",
    "pos_units_8w",
    "pos_units_13w",
    "pos_units_26w",
    "pos_units_52w",
    "revenue_4w",
    "revenue_13w",
    "revenue_52w",
    "transactions_4w",
    "transactions_13w",
    "avg_unit_price_13w",
    "avg_unit_price_52w",
    "return_rate_units_13w",
    "return_rate_units_52w",
    "avg_discount_4w",
    "avg_discount_13w",
    "max_discount_13w",
    "campaign_txn_4w",
    "campaign_txn_13w",
    "campaign_txn_52w",
    "campaign_units_4w",
    "campaign_units_13w",
    "campaign_units_52w",
    "campaign_revenue_13w",
    "campaign_revenue_52w",
    "non_bf_campaign_txn_13w",
    "non_bf_campaign_units_13w",
    "campaign_unit_share_13w",
    "campaign_revenue_share_13w",
    "non_bf_campaign_unit_share_13w",
    "campaign_active_weeks_13w",
    "campaign_active_weeks_52w",
    "product_program_txn_13w",
    "avg_campaign_discount_13w",
    "max_campaign_discount_13w",
    "days_since_campaign_txn",
    "days_since_bf_txn",
    "bf_txn_4w",
    "bf_txn_8w",
    "bf_txn_13w",
    "bf_units_4w",
    "bf_units_8w",
    "bf_units_13w",
    "non_bf_pos_units_4w",
    "non_bf_pos_units_13w",
    "non_bf_pos_units_4w_equiv",
    "non_bf_pos_units_13w_equiv",
    "bf_unit_share_4w",
    "bf_unit_share_13w",
    "bf_txn_share_4w",
    "bf_txn_share_13w",
    "last4_non_bf_to_last4",
    "post_bf_last4_bf_unit_share",
    "post_bf_last4_to_roll13",
    "online_txn_share_13w",
    "outlet_txn_share_13w",
    "max_stores_selling_13w",
    "max_hyperstores_selling_13w",
    "max_smaller_stores_selling_13w",
    "stock_prev_month_qty",
    "stock_two_months_before_qty",
    "stock_three_months_before_qty",
    "stock_trailing_3m_avg",
    "stock_trailing_3m_trend",
    "stock_months_observed_6m",
    "stock_zero_months_6m",
    "stock_observed_prev_month",
    "in_stock_before_target",
    "likely_stockout_before_target",
    "stock_coverage_ratio_4w",
    "stock_coverage_ratio_13w",
    "chain_stock_qty_before_target",
    "stores_with_stock_prev_month",
    "hyperstores_with_stock_prev_month",
    "stores_observed_stock_prev_month",
    "no_sales_despite_stock",
    "sales_with_low_ending_stock",
    "supplier_stock_prev_month_qty",
    "supplier_stock_two_months_before_qty",
    "supplier_stock_three_months_before_qty",
    "supplier_stock_trailing_3m_avg",
    "supplier_stock_trailing_3m_trend",
    "supplier_stock_months_observed_6m",
    "supplier_stock_zero_months_6m",
    "supplier_stock_observed_prev_month",
    "supplier_available_before_target",
    "supplier_stock_value_prev_month",
    "supplier_stock_value_trailing_3m_avg",
    "suppliers_observed_prev_month",
    "suppliers_with_stock_prev_month",
    "combined_stock_prev_month_qty",
    "combined_stock_observed_prev_month",
    "combined_stock_coverage_ratio_4w",
    "combined_stock_coverage_ratio_13w",
    "store_or_supplier_available_before_target",
    "likely_true_stockout_before_target",
    "no_sales_despite_combined_stock",
    "sales_with_low_combined_stock",
]


def _date(value: pd.Timestamp) -> str:
    return value.strftime("%Y-%m-%d")


def _table(headers: list[str], rows: list[list[str]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(lines)


def _sqlite_table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


def _load_labels(conn: sqlite3.Connection, target_start: str) -> pd.DataFrame:
    start = pd.Timestamp(target_start)
    as_of_week = _date(start - pd.Timedelta(weeks=1))
    if _sqlite_table_exists(conn, "forecast_v2_regime_labels"):
        labels = pd.read_sql_query(
            """
            SELECT *
            FROM forecast_v2_regime_labels
            WHERE as_of_week = ? AND rule_version = ?
            """,
            conn,
            params=(as_of_week, RULE_VERSION),
        )
        if not labels.empty:
            return labels
    labels = build_regime_labels(conn, as_of_week)
    write_regime_labels(conn, labels)
    return labels


def _load_naive_wide(
    conn: sqlite3.Connection,
    labels: pd.DataFrame,
    target_start: str,
    config: ScorecardConfig,
) -> pd.DataFrame:
    run_id_row = None
    if _sqlite_table_exists(conn, "forecast_v2_score_runs"):
        run_id_row = conn.execute(
            """
            SELECT run_id
            FROM forecast_v2_score_runs
            WHERE model_label = 'v2_naive_fullgrid' AND target_start = ?
            """,
            (target_start,),
        ).fetchone()
    if run_id_row:
        predictions = pd.read_sql_query(
            """
            SELECT sku_id, model_name, pred_units_4w
            FROM forecast_v2_predictions
            WHERE run_id = ?
            """,
            conn,
            params=(run_id_row[0],),
        )
    else:
        predictions = build_naive_predictions(conn, labels, pd.Timestamp(target_start), config)[
            ["sku_id", "model_name", "pred_units_4w"]
        ]

    wide = (
        predictions.pivot_table(
            index="sku_id",
            columns="model_name",
            values="pred_units_4w",
            aggfunc="first",
        )
        .reset_index()
        .rename_axis(columns=None)
    )
    for col in ("last4", "roll8_mean", "roll13_mean", "seasonal52", "median_naive"):
        if col not in wide.columns:
            wide[col] = 0.0
    return wide


def _load_actuals(
    conn: sqlite3.Connection,
    labels: pd.DataFrame,
    target_start: str,
    config: ScorecardConfig,
) -> pd.DataFrame:
    run_id_row = None
    if _sqlite_table_exists(conn, "forecast_v2_score_runs"):
        run_id_row = conn.execute(
            """
            SELECT run_id
            FROM forecast_v2_score_runs
            WHERE model_label = 'v2_naive_fullgrid' AND target_start = ?
            """,
            (target_start,),
        ).fetchone()
    if run_id_row:
        actuals = pd.read_sql_query(
            """
            SELECT *
            FROM forecast_v2_actuals_4w
            WHERE run_id = ?
            """,
            conn,
            params=(run_id_row[0],),
        )
        if not actuals.empty:
            return actuals
    return build_actuals(conn, labels, pd.Timestamp(target_start), config)


def _load_weekly_history(conn: sqlite3.Connection, target_start: str) -> pd.DataFrame:
    start = pd.Timestamp(target_start)
    load_start = start - pd.Timedelta(weeks=52)
    weekly = pd.read_sql_query(
        """
        SELECT
            sku_id,
            week_start,
            gross_units,
            returned_units,
            net_units,
            net_revenue,
            num_transactions,
            num_stores_selling,
            num_hyperstores_selling,
            num_smaller_stores_selling,
            avg_discount_pct,
            max_discount_pct,
            bf_transaction_count,
            online_transaction_count,
            outlet_transaction_count
        FROM weekly_chain_demand_v2
        WHERE week_start >= ? AND week_start < ?
        """,
        conn,
        params=(_date(load_start), target_start),
        parse_dates=["week_start"],
    )
    if weekly.empty:
        return weekly
    weekly["avg_discount_pct"] = _clean_discount_series(weekly["avg_discount_pct"])
    weekly["max_discount_pct"] = _clean_discount_series(weekly["max_discount_pct"])
    weekly["pos_units"] = weekly["net_units"].clip(lower=0.0)
    return weekly


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    return _sqlite_table_exists(conn, table_name)


def _month_start(value: pd.Timestamp) -> str:
    return value.replace(day=1).strftime("%Y-%m-%d")


def _previous_stock_months(target_start: str, months: int = 6) -> list[str]:
    start = pd.Timestamp(target_start).normalize()
    first_of_month = start.replace(day=1)
    previous_month = first_of_month - pd.DateOffset(months=1)
    return [_month_start(previous_month - pd.DateOffset(months=idx)) for idx in range(months)]


def _load_monthly_stock_history(conn: sqlite3.Connection, target_start: str) -> pd.DataFrame:
    if not _table_exists(conn, "stock_monthly_store_v2"):
        return pd.DataFrame()
    months = _previous_stock_months(target_start, months=6)
    placeholders = ", ".join("?" for _ in months)
    return pd.read_sql_query(
        f"""
        SELECT sku_id, store_id, store_type, stock_month, stock_qty
        FROM stock_monthly_store_v2
        WHERE stock_month IN ({placeholders})
        """,
        conn,
        params=months,
        parse_dates=["stock_month"],
    )


def _load_monthly_supplier_stock_history(conn: sqlite3.Connection, target_start: str) -> pd.DataFrame:
    if not _table_exists(conn, "stock_monthly_supplier_v2"):
        return pd.DataFrame()
    months = _previous_stock_months(target_start, months=6)
    placeholders = ", ".join("?" for _ in months)
    return pd.read_sql_query(
        f"""
        SELECT
            sku_id,
            supplier_key,
            stock_month,
            supplier_stock_qty,
            supplier_stock_value
        FROM stock_monthly_supplier_v2
        WHERE stock_month IN ({placeholders})
          AND mapping_confidence = 'exact_unique'
          AND sku_id IS NOT NULL
        """,
        conn,
        params=months,
        parse_dates=["stock_month"],
    )


def _safe_ratio(num: pd.Series, denom: pd.Series) -> pd.Series:
    return np.where(denom.abs() > 1e-9, num / denom, 0.0)


def _clean_discount_series(values: pd.Series) -> pd.Series:
    """Return only fraction-scale discounts that are safe model inputs."""
    numeric = pd.to_numeric(values, errors="coerce")
    numeric = numeric.where(np.isfinite(numeric), np.nan)
    return numeric.where((numeric >= 0.0) & (numeric <= MAX_VALID_DISCOUNT_PCT), np.nan)


def _clean_numeric_series(values: pd.Series, default: float = 0.0) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce")
    numeric = numeric.where(np.isfinite(numeric), np.nan)
    return numeric.fillna(default)


def _bf_window_for_year(year: int) -> tuple[pd.Timestamp, pd.Timestamp]:
    if year in BF_WINDOWS:
        start, end = BF_WINDOWS[year]
    else:
        # Fallback for future years: use the same Monday-to-Sunday pattern as 2025.
        start = f"{year}-11-03"
        end = f"{year}-11-23"
    return pd.Timestamp(start), pd.Timestamp(end) + pd.Timedelta(days=1)


def _overlap_days(
    left_start: pd.Timestamp,
    left_end: pd.Timestamp,
    right_start: pd.Timestamp,
    right_end: pd.Timestamp,
) -> int:
    start = max(left_start, right_start)
    end = min(left_end, right_end)
    return max(0, int((end - start).days))


def _target_bf_features(target_start: str) -> dict[str, float]:
    start = pd.Timestamp(target_start).normalize()
    horizon_end = start + pd.Timedelta(days=28)
    bf_start, bf_end_exclusive = _bf_window_for_year(start.year)
    bf_end_inclusive = bf_end_exclusive - pd.Timedelta(days=1)
    pre_start = bf_start - pd.Timedelta(days=28)
    post_end = bf_end_exclusive + pd.Timedelta(days=28)

    return {
        "target_is_bf_window": float(bf_start <= start < bf_end_exclusive),
        "target_is_pre_bf_4w": float(pre_start <= start < bf_start),
        "target_is_post_bf_4w": float(bf_end_exclusive <= start < post_end),
        "target_days_from_bf_start": float((start - bf_start).days),
        "target_days_from_bf_end": float((start - bf_end_inclusive).days),
        "horizon_bf_overlap_days": float(_overlap_days(start, horizon_end, bf_start, bf_end_exclusive)),
        "horizon_pre_bf_overlap_days": float(_overlap_days(start, horizon_end, pre_start, bf_start)),
        "horizon_post_bf_overlap_days": float(_overlap_days(start, horizon_end, bf_end_exclusive, post_end)),
    }


def _non_bf_calendar_weeks(window_start: pd.Timestamp, window_end: pd.Timestamp) -> int:
    week_starts = pd.date_range(window_start, window_end - pd.Timedelta(days=1), freq="7D")
    count = 0
    for week_start in week_starts:
        bf_start, bf_end = _bf_window_for_year(int(week_start.year))
        week_end = week_start + pd.Timedelta(days=7)
        if _overlap_days(week_start, week_end, bf_start, bf_end) == 0:
            count += 1
    return count


def _window_features(weekly: pd.DataFrame, target_start: str, labels: pd.DataFrame) -> pd.DataFrame:
    result = labels[["sku_id"]].copy()
    if weekly.empty:
        return result

    start = pd.Timestamp(target_start)
    specs = {
        "4w": start - pd.Timedelta(weeks=4),
        "8w": start - pd.Timedelta(weeks=8),
        "13w": start - pd.Timedelta(weeks=13),
        "26w": start - pd.Timedelta(weeks=26),
        "52w": start - pd.Timedelta(weeks=52),
    }

    for suffix, window_start in specs.items():
        subset = weekly[weekly["week_start"] >= window_start].copy()
        non_bf_weeks = _non_bf_calendar_weeks(window_start, start)
        result[f"non_bf_calendar_weeks_{suffix}"] = float(non_bf_weeks)
        if subset.empty:
            continue
        subset["is_bf_week"] = (subset["bf_transaction_count"].fillna(0.0) > 0).astype(float)
        subset["bf_pos_units"] = np.where(subset["is_bf_week"] == 1, subset["pos_units"], 0.0)
        subset["non_bf_pos_units"] = np.where(subset["is_bf_week"] == 1, 0.0, subset["pos_units"])
        agg = subset.groupby("sku_id").agg(
            **{
                f"pos_units_{suffix}": ("pos_units", "sum"),
                f"revenue_{suffix}": ("net_revenue", "sum"),
                f"gross_units_{suffix}": ("gross_units", "sum"),
                f"returned_units_{suffix}": ("returned_units", "sum"),
                f"transactions_{suffix}": ("num_transactions", "sum"),
                f"avg_discount_{suffix}": ("avg_discount_pct", "mean"),
                f"max_discount_{suffix}": ("max_discount_pct", "max"),
                f"bf_txn_{suffix}": ("bf_transaction_count", "sum"),
                f"bf_units_{suffix}": ("bf_pos_units", "sum"),
                f"non_bf_pos_units_{suffix}": ("non_bf_pos_units", "sum"),
                f"online_txn_{suffix}": ("online_transaction_count", "sum"),
                f"outlet_txn_{suffix}": ("outlet_transaction_count", "sum"),
                f"max_stores_selling_{suffix}": ("num_stores_selling", "max"),
                f"max_hyperstores_selling_{suffix}": ("num_hyperstores_selling", "max"),
                f"max_smaller_stores_selling_{suffix}": ("num_smaller_stores_selling", "max"),
            }
        ).reset_index()
        result = result.merge(agg, on="sku_id", how="left")

    for col in result.columns:
        if col != "sku_id":
            result[col] = result[col].fillna(0.0)

    for suffix in ("13w", "52w"):
        revenue = result.get(f"revenue_{suffix}", pd.Series(0.0, index=result.index))
        units = result.get(f"pos_units_{suffix}", pd.Series(0.0, index=result.index))
        gross_units = result.get(f"gross_units_{suffix}", pd.Series(0.0, index=result.index))
        returned_units = result.get(f"returned_units_{suffix}", pd.Series(0.0, index=result.index))
        transactions = result.get(f"transactions_{suffix}", pd.Series(0.0, index=result.index))
        online = result.get(f"online_txn_{suffix}", pd.Series(0.0, index=result.index))
        outlet = result.get(f"outlet_txn_{suffix}", pd.Series(0.0, index=result.index))
        result[f"avg_unit_price_{suffix}"] = _safe_ratio(revenue, units)
        result[f"return_rate_units_{suffix}"] = _safe_ratio(returned_units, gross_units)
        result[f"online_txn_share_{suffix}"] = _safe_ratio(online, transactions)
        result[f"outlet_txn_share_{suffix}"] = _safe_ratio(outlet, transactions)

    for suffix in ("4w", "13w"):
        bf_units = result.get(f"bf_units_{suffix}", pd.Series(0.0, index=result.index))
        units = result.get(f"pos_units_{suffix}", pd.Series(0.0, index=result.index))
        non_bf_units = result.get(f"non_bf_pos_units_{suffix}", pd.Series(0.0, index=result.index))
        non_bf_weeks = result.get(f"non_bf_calendar_weeks_{suffix}", pd.Series(0.0, index=result.index))
        bf_txn = result.get(f"bf_txn_{suffix}", pd.Series(0.0, index=result.index))
        transactions = result.get(f"transactions_{suffix}", pd.Series(0.0, index=result.index))
        result[f"bf_unit_share_{suffix}"] = _safe_ratio(bf_units, units)
        result[f"bf_txn_share_{suffix}"] = _safe_ratio(bf_txn, transactions)
        result[f"non_bf_pos_units_{suffix}_equiv"] = _safe_ratio(non_bf_units, non_bf_weeks) * 4.0

    return result


def _campaign_history_features(conn: sqlite3.Connection, target_start: str, labels: pd.DataFrame) -> pd.DataFrame:
    result = labels[["sku_id"]].copy()
    campaign_cols = [
        "campaign_txn_4w",
        "campaign_txn_13w",
        "campaign_txn_52w",
        "campaign_units_4w",
        "campaign_units_13w",
        "campaign_units_52w",
        "campaign_revenue_13w",
        "campaign_revenue_52w",
        "non_bf_campaign_txn_13w",
        "non_bf_campaign_units_13w",
        "campaign_active_weeks_13w",
        "campaign_active_weeks_52w",
        "product_program_txn_13w",
        "avg_campaign_discount_13w",
        "max_campaign_discount_13w",
    ]
    for col in campaign_cols:
        result[col] = 0.0
    result["days_since_campaign_txn"] = 999.0
    result["days_since_bf_txn"] = 999.0

    sku_ids = labels["sku_id"].dropna().astype(str).drop_duplicates().tolist()
    if not sku_ids:
        return result

    start = pd.Timestamp(target_start)
    window_4w = start - pd.Timedelta(weeks=4)
    window_13w = start - pd.Timedelta(weeks=13)
    window_52w = start - pd.Timedelta(weeks=52)
    conn.execute("PRAGMA temp_store = MEMORY")
    conn.execute("DROP TABLE IF EXISTS temp_forecast_v2_campaign_skus")
    conn.execute("CREATE TEMP TABLE temp_forecast_v2_campaign_skus (sku_id TEXT PRIMARY KEY)")
    conn.executemany(
        "INSERT OR IGNORE INTO temp_forecast_v2_campaign_skus (sku_id) VALUES (?)",
        [(sku_id,) for sku_id in sku_ids],
    )
    agg = pd.read_sql_query(
        """
        SELECT
            raw.sku_id,
            SUM(CASE WHEN raw.sale_date >= ? AND raw.campaign_signal_status = 'observed' AND COALESCE(raw.is_product_program, 0) = 0 THEN 1 ELSE 0 END) AS campaign_txn_4w,
            SUM(CASE WHEN raw.sale_date >= ? AND raw.campaign_signal_status = 'observed' AND COALESCE(raw.is_product_program, 0) = 0 THEN 1 ELSE 0 END) AS campaign_txn_13w,
            SUM(CASE WHEN raw.sale_date >= ? AND raw.campaign_signal_status = 'observed' AND COALESCE(raw.is_product_program, 0) = 0 THEN 1 ELSE 0 END) AS campaign_txn_52w,
            SUM(CASE WHEN raw.sale_date >= ? AND raw.campaign_signal_status = 'observed' AND COALESCE(raw.is_product_program, 0) = 0 THEN MAX(COALESCE(raw.net_units, 0), 0) ELSE 0 END) AS campaign_units_4w,
            SUM(CASE WHEN raw.sale_date >= ? AND raw.campaign_signal_status = 'observed' AND COALESCE(raw.is_product_program, 0) = 0 THEN MAX(COALESCE(raw.net_units, 0), 0) ELSE 0 END) AS campaign_units_13w,
            SUM(CASE WHEN raw.sale_date >= ? AND raw.campaign_signal_status = 'observed' AND COALESCE(raw.is_product_program, 0) = 0 THEN MAX(COALESCE(raw.net_units, 0), 0) ELSE 0 END) AS campaign_units_52w,
            SUM(CASE WHEN raw.sale_date >= ? AND raw.campaign_signal_status = 'observed' AND COALESCE(raw.is_product_program, 0) = 0 THEN COALESCE(raw.net_revenue, 0) ELSE 0 END) AS campaign_revenue_13w,
            SUM(CASE WHEN raw.sale_date >= ? AND raw.campaign_signal_status = 'observed' AND COALESCE(raw.is_product_program, 0) = 0 THEN COALESCE(raw.net_revenue, 0) ELSE 0 END) AS campaign_revenue_52w,
            SUM(CASE WHEN raw.sale_date >= ? AND raw.campaign_signal_status = 'observed' AND COALESCE(raw.is_product_program, 0) = 0 AND COALESCE(raw.is_bf_campaign, 0) = 0 THEN 1 ELSE 0 END) AS non_bf_campaign_txn_13w,
            SUM(CASE WHEN raw.sale_date >= ? AND raw.campaign_signal_status = 'observed' AND COALESCE(raw.is_product_program, 0) = 0 AND COALESCE(raw.is_bf_campaign, 0) = 0 THEN MAX(COALESCE(raw.net_units, 0), 0) ELSE 0 END) AS non_bf_campaign_units_13w,
            COUNT(DISTINCT CASE WHEN raw.sale_date >= ? AND raw.campaign_signal_status = 'observed' AND COALESCE(raw.is_product_program, 0) = 0 THEN raw.week_start END) AS campaign_active_weeks_13w,
            COUNT(DISTINCT CASE WHEN raw.sale_date >= ? AND raw.campaign_signal_status = 'observed' AND COALESCE(raw.is_product_program, 0) = 0 THEN raw.week_start END) AS campaign_active_weeks_52w,
            SUM(CASE WHEN raw.sale_date >= ? AND COALESCE(raw.is_product_program, 0) = 1 THEN 1 ELSE 0 END) AS product_program_txn_13w,
            AVG(CASE WHEN raw.sale_date >= ? AND raw.campaign_signal_status = 'observed' AND COALESCE(raw.is_product_program, 0) = 0 AND raw.discount_pct >= 0 AND raw.discount_pct <= 1 THEN raw.discount_pct END) AS avg_campaign_discount_13w,
            MAX(CASE WHEN raw.sale_date >= ? AND raw.campaign_signal_status = 'observed' AND COALESCE(raw.is_product_program, 0) = 0 AND raw.discount_pct >= 0 AND raw.discount_pct <= 1 THEN raw.discount_pct END) AS max_campaign_discount_13w,
            MAX(CASE WHEN raw.campaign_signal_status = 'observed' AND COALESCE(raw.is_product_program, 0) = 0 THEN raw.sale_date END) AS last_campaign_date,
            MAX(CASE WHEN COALESCE(raw.is_bf_timing, 0) = 1 THEN raw.sale_date END) AS last_bf_date
        FROM raw_sales_transactions_v2 AS raw INDEXED BY idx_raw_v2_sku_date
        JOIN temp_forecast_v2_campaign_skus AS skus
            ON skus.sku_id = raw.sku_id
        WHERE raw.sale_date >= ?
            AND raw.sale_date < ?
            AND raw.is_non_product = 0
        GROUP BY raw.sku_id
        """,
        conn,
        params=(
            _date(window_4w),
            _date(window_13w),
            _date(window_52w),
            _date(window_4w),
            _date(window_13w),
            _date(window_52w),
            _date(window_13w),
            _date(window_52w),
            _date(window_13w),
            _date(window_13w),
            _date(window_13w),
            _date(window_52w),
            _date(window_13w),
            _date(window_13w),
            _date(window_13w),
            _date(window_52w),
            target_start,
        ),
        parse_dates=["last_campaign_date", "last_bf_date"],
    )
    conn.execute("DROP TABLE IF EXISTS temp_forecast_v2_campaign_skus")

    if agg.empty:
        return result

    last_campaign = agg.set_index("sku_id")["last_campaign_date"]
    last_bf = agg.set_index("sku_id")["last_bf_date"]
    agg = agg.drop(columns=["last_campaign_date", "last_bf_date"])
    result = result.drop(
        columns=[col for col in agg.columns if col != "sku_id" and col in result.columns],
        errors="ignore",
    ).merge(agg, on="sku_id", how="left")
    result["days_since_campaign_txn"] = result["sku_id"].map((start - last_campaign).dt.days).fillna(999.0)
    result["days_since_bf_txn"] = result["sku_id"].map((start - last_bf).dt.days).fillna(999.0)

    for col in result.columns:
        if col != "sku_id":
            result[col] = pd.to_numeric(result[col], errors="coerce").fillna(0.0)
    return result


def _stock_features(stock: pd.DataFrame, target_start: str, labels: pd.DataFrame) -> pd.DataFrame:
    result = labels[["sku_id"]].copy()
    stock_cols = [
        "stock_prev_month_qty",
        "stock_two_months_before_qty",
        "stock_three_months_before_qty",
        "stock_trailing_3m_avg",
        "stock_trailing_3m_trend",
        "stock_months_observed_6m",
        "stock_zero_months_6m",
        "stock_observed_prev_month",
        "in_stock_before_target",
        "likely_stockout_before_target",
        "chain_stock_qty_before_target",
        "stores_with_stock_prev_month",
        "hyperstores_with_stock_prev_month",
        "stores_observed_stock_prev_month",
    ]
    for col in stock_cols:
        result[col] = 0.0
    result["stock_signal_status"] = "missing"
    result["stock_coverage_bucket"] = "missing"

    if stock.empty:
        return result

    stock = stock.copy()
    stock["stock_month_str"] = stock["stock_month"].dt.strftime("%Y-%m-%d")
    months = _previous_stock_months(target_start, months=6)
    prev_month, two_months_before, three_months_before = months[0], months[1], months[2]

    monthly_chain = (
        stock.groupby(["sku_id", "stock_month_str"], as_index=False)
        .agg(
            month_stock_qty=("stock_qty", "sum"),
            stores_observed=("store_id", "nunique"),
            stores_with_stock=("store_id", lambda s: 0),
        )
    )
    positive_store_counts = (
        stock[stock["stock_qty"] > 0]
        .groupby(["sku_id", "stock_month_str"])
        .agg(
            stores_with_stock=("store_id", "nunique"),
            hyperstores_with_stock=("store_id", lambda s: 0),
        )
        .reset_index()
    )
    positive_hyper = (
        stock[(stock["stock_qty"] > 0) & (stock["store_type"] == "hyperstore")]
        .groupby(["sku_id", "stock_month_str"])["store_id"]
        .nunique()
        .rename("hyperstores_with_stock")
        .reset_index()
    )
    positive_store_counts = positive_store_counts.drop(columns=["hyperstores_with_stock"]).merge(
        positive_hyper, on=["sku_id", "stock_month_str"], how="left"
    )
    monthly_chain = monthly_chain.drop(columns=["stores_with_stock"]).merge(
        positive_store_counts, on=["sku_id", "stock_month_str"], how="left"
    )
    monthly_chain["stores_with_stock"] = monthly_chain["stores_with_stock"].fillna(0)
    monthly_chain["hyperstores_with_stock"] = monthly_chain["hyperstores_with_stock"].fillna(0)

    pivot = monthly_chain.pivot_table(
        index="sku_id",
        columns="stock_month_str",
        values="month_stock_qty",
        aggfunc="first",
    )
    prev = pivot[prev_month] if prev_month in pivot.columns else pd.Series(dtype=float)
    two = pivot[two_months_before] if two_months_before in pivot.columns else pd.Series(dtype=float)
    three = pivot[three_months_before] if three_months_before in pivot.columns else pd.Series(dtype=float)

    observed_counts = monthly_chain.groupby("sku_id")["stock_month_str"].nunique().rename("stock_months_observed_6m")
    zero_counts = (
        monthly_chain[monthly_chain["month_stock_qty"] <= 0]
        .groupby("sku_id")["stock_month_str"]
        .nunique()
        .rename("stock_zero_months_6m")
    )
    prev_counts = monthly_chain[monthly_chain["stock_month_str"] == prev_month].set_index("sku_id")

    result["stock_prev_month_qty"] = result["sku_id"].map(prev).fillna(0.0)
    result["stock_two_months_before_qty"] = result["sku_id"].map(two).fillna(0.0)
    result["stock_three_months_before_qty"] = result["sku_id"].map(three).fillna(0.0)
    result["stock_trailing_3m_avg"] = (
        result[["stock_prev_month_qty", "stock_two_months_before_qty", "stock_three_months_before_qty"]].mean(axis=1)
    )
    result["stock_trailing_3m_trend"] = result["stock_prev_month_qty"] - result["stock_trailing_3m_avg"]
    result["stock_months_observed_6m"] = result["sku_id"].map(observed_counts).fillna(0.0)
    result["stock_zero_months_6m"] = result["sku_id"].map(zero_counts).fillna(0.0)
    result["stock_observed_prev_month"] = result["sku_id"].isin(prev_counts.index).astype(float)
    result["in_stock_before_target"] = (result["stock_prev_month_qty"] > 0).astype(float)
    result["likely_stockout_before_target"] = (
        (result["stock_observed_prev_month"] == 1) & (result["stock_prev_month_qty"] <= 0)
    ).astype(float)
    result["chain_stock_qty_before_target"] = result["stock_prev_month_qty"]
    result["stores_with_stock_prev_month"] = result["sku_id"].map(prev_counts["stores_with_stock"]).fillna(0.0)
    result["hyperstores_with_stock_prev_month"] = result["sku_id"].map(prev_counts["hyperstores_with_stock"]).fillna(0.0)
    result["stores_observed_stock_prev_month"] = result["sku_id"].map(prev_counts["stores_observed"]).fillna(0.0)
    result["stock_signal_status"] = np.where(result["stock_months_observed_6m"] > 0, "observed", "missing")
    result["stock_coverage_bucket"] = np.select(
        [
            result["stock_signal_status"] == "missing",
            result["stores_observed_stock_prev_month"] >= 5,
            result["stores_observed_stock_prev_month"] >= 2,
            result["stores_observed_stock_prev_month"] >= 1,
        ],
        ["missing", "broad_store_context", "partial_store_context", "single_store_context"],
        default="missing_prev_month",
    )
    return result


def _supplier_stock_features(supplier_stock: pd.DataFrame, target_start: str, labels: pd.DataFrame) -> pd.DataFrame:
    result = labels[["sku_id"]].copy()
    supplier_cols = [
        "supplier_stock_prev_month_qty",
        "supplier_stock_two_months_before_qty",
        "supplier_stock_three_months_before_qty",
        "supplier_stock_trailing_3m_avg",
        "supplier_stock_trailing_3m_trend",
        "supplier_stock_months_observed_6m",
        "supplier_stock_zero_months_6m",
        "supplier_stock_observed_prev_month",
        "supplier_available_before_target",
        "supplier_stock_value_prev_month",
        "supplier_stock_value_trailing_3m_avg",
        "suppliers_observed_prev_month",
        "suppliers_with_stock_prev_month",
    ]
    for col in supplier_cols:
        result[col] = 0.0
    result["supplier_stock_signal_status"] = "missing"
    result["supplier_stock_coverage_bucket"] = "missing"

    if supplier_stock.empty:
        return result

    supplier_stock = supplier_stock.copy()
    supplier_stock["stock_month_str"] = supplier_stock["stock_month"].dt.strftime("%Y-%m-%d")
    supplier_stock["supplier_stock_value"] = supplier_stock["supplier_stock_value"].fillna(0.0)
    months = _previous_stock_months(target_start, months=6)
    prev_month, two_months_before, three_months_before = months[0], months[1], months[2]

    monthly_chain = (
        supplier_stock.groupby(["sku_id", "stock_month_str"], as_index=False)
        .agg(
            month_supplier_stock_qty=("supplier_stock_qty", "sum"),
            month_supplier_stock_value=("supplier_stock_value", "sum"),
            suppliers_observed=("supplier_key", "nunique"),
        )
    )
    positive_supplier_counts = (
        supplier_stock[supplier_stock["supplier_stock_qty"] > 0]
        .groupby(["sku_id", "stock_month_str"])["supplier_key"]
        .nunique()
        .rename("suppliers_with_stock")
        .reset_index()
    )
    monthly_chain = monthly_chain.merge(positive_supplier_counts, on=["sku_id", "stock_month_str"], how="left")
    monthly_chain["suppliers_with_stock"] = monthly_chain["suppliers_with_stock"].fillna(0.0)

    qty_pivot = monthly_chain.pivot_table(
        index="sku_id",
        columns="stock_month_str",
        values="month_supplier_stock_qty",
        aggfunc="first",
    )
    value_pivot = monthly_chain.pivot_table(
        index="sku_id",
        columns="stock_month_str",
        values="month_supplier_stock_value",
        aggfunc="first",
    )
    prev = qty_pivot[prev_month] if prev_month in qty_pivot.columns else pd.Series(dtype=float)
    two = qty_pivot[two_months_before] if two_months_before in qty_pivot.columns else pd.Series(dtype=float)
    three = qty_pivot[three_months_before] if three_months_before in qty_pivot.columns else pd.Series(dtype=float)
    prev_value = value_pivot[prev_month] if prev_month in value_pivot.columns else pd.Series(dtype=float)
    two_value = value_pivot[two_months_before] if two_months_before in value_pivot.columns else pd.Series(dtype=float)
    three_value = value_pivot[three_months_before] if three_months_before in value_pivot.columns else pd.Series(dtype=float)

    observed_counts = (
        monthly_chain.groupby("sku_id")["stock_month_str"].nunique().rename("supplier_stock_months_observed_6m")
    )
    zero_counts = (
        monthly_chain[monthly_chain["month_supplier_stock_qty"] <= 0]
        .groupby("sku_id")["stock_month_str"]
        .nunique()
        .rename("supplier_stock_zero_months_6m")
    )
    prev_counts = monthly_chain[monthly_chain["stock_month_str"] == prev_month].set_index("sku_id")

    result["supplier_stock_prev_month_qty"] = result["sku_id"].map(prev).fillna(0.0)
    result["supplier_stock_two_months_before_qty"] = result["sku_id"].map(two).fillna(0.0)
    result["supplier_stock_three_months_before_qty"] = result["sku_id"].map(three).fillna(0.0)
    result["supplier_stock_trailing_3m_avg"] = result[
        [
            "supplier_stock_prev_month_qty",
            "supplier_stock_two_months_before_qty",
            "supplier_stock_three_months_before_qty",
        ]
    ].mean(axis=1)
    result["supplier_stock_trailing_3m_trend"] = (
        result["supplier_stock_prev_month_qty"] - result["supplier_stock_trailing_3m_avg"]
    )
    result["supplier_stock_months_observed_6m"] = result["sku_id"].map(observed_counts).fillna(0.0)
    result["supplier_stock_zero_months_6m"] = result["sku_id"].map(zero_counts).fillna(0.0)
    result["supplier_stock_observed_prev_month"] = result["sku_id"].isin(prev_counts.index).astype(float)
    result["supplier_available_before_target"] = (result["supplier_stock_prev_month_qty"] > 0).astype(float)
    result["supplier_stock_value_prev_month"] = result["sku_id"].map(prev_value).fillna(0.0)
    result["supplier_stock_value_trailing_3m_avg"] = pd.concat(
        [
            result["sku_id"].map(prev_value).fillna(0.0),
            result["sku_id"].map(two_value).fillna(0.0),
            result["sku_id"].map(three_value).fillna(0.0),
        ],
        axis=1,
    ).mean(axis=1)
    result["suppliers_observed_prev_month"] = result["sku_id"].map(prev_counts["suppliers_observed"]).fillna(0.0)
    result["suppliers_with_stock_prev_month"] = result["sku_id"].map(prev_counts["suppliers_with_stock"]).fillna(0.0)
    result["supplier_stock_signal_status"] = np.where(
        result["supplier_stock_months_observed_6m"] > 0,
        "observed",
        "missing",
    )
    result["supplier_stock_coverage_bucket"] = np.select(
        [
            result["supplier_stock_signal_status"] == "missing",
            result["supplier_stock_observed_prev_month"] == 0,
            result["supplier_stock_prev_month_qty"] > 0,
            result["supplier_stock_prev_month_qty"] <= 0,
        ],
        ["missing", "history_no_prev_month", "positive_supplier_stock", "zero_supplier_stock"],
        default="missing",
    )
    return result


def build_feature_snapshot(
    conn: sqlite3.Connection,
    target_start: str,
    population: str = "headline",
    config: ScorecardConfig | None = None,
    revenue_rank_limit: int | None = None,
) -> pd.DataFrame:
    config = config or ScorecardConfig()
    start = pd.Timestamp(target_start)
    labels = _load_labels(conn, target_start)
    if population == "headline":
        labels = labels[labels["headline_eligible"] == 1].copy()
    elif population == "business_target":
        labels = labels[labels["business_target_eligible"] == 1].copy()
    elif population != "all":
        raise ValueError("population must be headline, business_target, or all")
    if revenue_rank_limit is not None:
        labels = labels[pd.to_numeric(labels["revenue_rank"], errors="coerce") <= revenue_rank_limit].copy()

    naive = _load_naive_wide(conn, labels, target_start, config)
    actuals = _load_actuals(conn, labels, target_start, config)
    weekly = _load_weekly_history(conn, target_start)
    monthly_stock = _load_monthly_stock_history(conn, target_start)
    monthly_supplier_stock = _load_monthly_supplier_stock_history(conn, target_start)
    history_features = _window_features(weekly, target_start, labels)
    campaign_features = _campaign_history_features(conn, target_start, labels)
    stock_features = _stock_features(monthly_stock, target_start, labels)
    supplier_stock_features = _supplier_stock_features(monthly_supplier_stock, target_start, labels)

    frame = labels.merge(naive, on="sku_id", how="left")
    frame = frame.merge(history_features, on="sku_id", how="left")
    frame = frame.merge(campaign_features, on="sku_id", how="left")
    frame = frame.merge(stock_features, on="sku_id", how="left")
    frame = frame.merge(supplier_stock_features, on="sku_id", how="left")
    frame = frame.merge(actuals, on="sku_id", how="left")
    frame = frame.copy()

    frame["target_start"] = target_start
    frame["target_month"] = int(start.month)
    frame["target_quarter"] = int(start.quarter)
    frame["target_weekofyear"] = int(start.isocalendar().week)
    frame["target_is_q4"] = int(start.quarter == 4)
    frame["target_is_black_friday_month"] = int(start.month == 11)
    for col, value in _target_bf_features(target_start).items():
        frame[col] = value

    for col in ("last4", "roll8_mean", "roll13_mean", "seasonal52", "median_naive"):
        frame[col] = frame[col].fillna(0.0)
    frame["last4_to_roll13"] = _safe_ratio(frame["last4"], frame["roll13_mean"])
    frame["seasonal_to_roll13"] = _safe_ratio(frame["seasonal52"], frame["roll13_mean"])
    frame["median_to_avg4w"] = _safe_ratio(frame["median_naive"], frame["avg_units_per_4w_52"])
    for col in (
        "pos_units_4w",
        "pos_units_13w",
        "bf_units_4w",
        "bf_units_13w",
        "non_bf_pos_units_4w",
        "non_bf_pos_units_13w",
        "non_bf_pos_units_4w_equiv",
        "non_bf_pos_units_13w_equiv",
        "bf_unit_share_4w",
        "bf_unit_share_13w",
        "stock_prev_month_qty",
        "stock_observed_prev_month",
        "stock_months_observed_6m",
        "supplier_stock_prev_month_qty",
        "supplier_stock_observed_prev_month",
        "supplier_stock_months_observed_6m",
        "campaign_units_13w",
        "campaign_revenue_13w",
        "non_bf_campaign_units_13w",
    ):
        if col not in frame.columns:
            frame[col] = 0.0
        frame[col] = pd.to_numeric(frame[col], errors="coerce").fillna(0.0)
    frame["campaign_unit_share_13w"] = _safe_ratio(frame["campaign_units_13w"], frame["pos_units_13w"])
    frame["campaign_revenue_share_13w"] = _safe_ratio(frame["campaign_revenue_13w"], frame["revenue_13w"])
    frame["non_bf_campaign_unit_share_13w"] = _safe_ratio(
        frame["non_bf_campaign_units_13w"],
        frame["pos_units_13w"],
    )
    frame["last4_non_bf_to_last4"] = _safe_ratio(frame["non_bf_pos_units_4w"], frame["pos_units_4w"])
    frame["post_bf_last4_bf_unit_share"] = frame["target_is_post_bf_4w"] * frame["bf_unit_share_4w"]
    frame["post_bf_last4_to_roll13"] = frame["target_is_post_bf_4w"] * frame["last4_to_roll13"]
    recent_4w_demand = frame["pos_units_13w"] / 13.0 * 4.0
    frame["stock_coverage_ratio_4w"] = _safe_ratio(frame["stock_prev_month_qty"], recent_4w_demand)
    frame["stock_coverage_ratio_13w"] = _safe_ratio(frame["stock_prev_month_qty"], frame["pos_units_13w"])
    frame["no_sales_despite_stock"] = (
        (frame["stock_prev_month_qty"] > 0) & (frame["pos_units_13w"] <= 0)
    ).astype(float)
    frame["sales_with_low_ending_stock"] = (
        (frame["pos_units_13w"] > 0)
        & (frame["stock_observed_prev_month"] == 1)
        & (frame["stock_prev_month_qty"] <= np.maximum(1.0, recent_4w_demand * 0.5))
    ).astype(float)
    frame["combined_stock_prev_month_qty"] = frame["stock_prev_month_qty"] + frame["supplier_stock_prev_month_qty"]
    frame["combined_stock_observed_prev_month"] = (
        (frame["stock_observed_prev_month"] == 1) | (frame["supplier_stock_observed_prev_month"] == 1)
    ).astype(float)
    frame["combined_stock_coverage_ratio_4w"] = _safe_ratio(frame["combined_stock_prev_month_qty"], recent_4w_demand)
    frame["combined_stock_coverage_ratio_13w"] = _safe_ratio(frame["combined_stock_prev_month_qty"], frame["pos_units_13w"])
    frame["store_or_supplier_available_before_target"] = (
        (frame["stock_prev_month_qty"] > 0) | (frame["supplier_stock_prev_month_qty"] > 0)
    ).astype(float)
    low_store_stock = (frame["stock_observed_prev_month"] == 0) | (
        frame["stock_prev_month_qty"] <= np.maximum(1.0, recent_4w_demand * 0.5)
    )
    low_supplier_stock = (frame["supplier_stock_observed_prev_month"] == 1) & (
        frame["supplier_stock_prev_month_qty"] <= np.maximum(1.0, recent_4w_demand * 0.5)
    )
    frame["likely_true_stockout_before_target"] = (
        (frame["pos_units_13w"] > 0)
        & (frame["combined_stock_observed_prev_month"] == 1)
        & low_store_stock
        & low_supplier_stock
    ).astype(float)
    frame["no_sales_despite_combined_stock"] = (
        (frame["combined_stock_prev_month_qty"] > 0) & (frame["pos_units_13w"] <= 0)
    ).astype(float)
    frame["sales_with_low_combined_stock"] = (
        (frame["pos_units_13w"] > 0)
        & (frame["combined_stock_observed_prev_month"] == 1)
        & (frame["combined_stock_prev_month_qty"] <= np.maximum(1.0, recent_4w_demand * 0.5))
    ).astype(float)
    frame["combined_stock_coverage_bucket"] = np.select(
        [
            frame["combined_stock_observed_prev_month"] == 0,
            frame["likely_true_stockout_before_target"] == 1,
            frame["store_or_supplier_available_before_target"] == 1,
            frame["combined_stock_prev_month_qty"] <= 0,
        ],
        ["missing", "likely_stockout", "available", "observed_zero"],
        default="observed_unclear",
    )

    for col in NUMERIC_FEATURES:
        if col not in frame.columns:
            frame[col] = 0.0
        frame[col] = _clean_numeric_series(frame[col])

    for col in CATEGORICAL_FEATURES:
        if col not in frame.columns:
            frame[col] = "unknown"
        frame[col] = frame[col].fillna("unknown").astype(str)

    for col in ("actual_pos_units_4w", "actual_net_units_4w", "actual_net_revenue_4w"):
        frame[col] = _clean_numeric_series(frame[col])

    return frame


def build_feature_matrix(
    conn: sqlite3.Connection,
    target_starts: list[str],
    population: str = "headline",
    config: ScorecardConfig | None = None,
    revenue_rank_limit: int | None = None,
) -> pd.DataFrame:
    frames = [
        build_feature_snapshot(
            conn,
            target_start,
            population=population,
            config=config,
            revenue_rank_limit=revenue_rank_limit,
        )
        for target_start in target_starts
    ]
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def build_report(matrix: pd.DataFrame) -> str:
    rows = []
    stock_rows = []
    for target_start, group in matrix.groupby("target_start"):
        rows.append(
            [
                str(target_start),
                f"{len(group):,}",
                f"{int((group['actual_pos_units_4w'] >= 4).sum()):,}",
                f"{group['actual_pos_units_4w'].sum():,.1f}",
                f"{group['median_naive'].sum():,.1f}",
            ]
        )
        if "stock_signal_status" in group.columns:
            observed = int((group["stock_signal_status"] == "observed").sum())
            in_stock = int((group.get("in_stock_before_target", 0) == 1).sum())
            stockout = int((group.get("likely_stockout_before_target", 0) == 1).sum())
            supplier_observed = int((group.get("supplier_stock_signal_status", "") == "observed").sum())
            supplier_positive = int((group.get("supplier_available_before_target", 0) == 1).sum())
            combined_available = int((group.get("store_or_supplier_available_before_target", 0) == 1).sum())
            true_stockout = int((group.get("likely_true_stockout_before_target", 0) == 1).sum())
            stock_rows.append(
                [
                    str(target_start),
                    f"{observed:,}",
                    f"{observed / len(group) * 100:.1f}%" if len(group) else "-",
                    f"{in_stock:,}",
                    f"{stockout:,}",
                    f"{supplier_observed:,}",
                    f"{supplier_observed / len(group) * 100:.1f}%" if len(group) else "-",
                    f"{supplier_positive:,}",
                    f"{combined_available:,}",
                    f"{true_stockout:,}",
                ]
            )
    return "\n".join(
        [
            "# Iteration 5N — V2 Phase 8E Availability Feature Matrix Audit",
            "",
            "## Snapshot Coverage",
            "",
            _table(["Target start", "Rows", "Qty scored rows", "Actual units", "Median naive units"], rows),
            "",
            "## Feature Counts",
            "",
            _table(
                ["Feature group", "Count"],
                [
                    ["Numeric", str(len(NUMERIC_FEATURES))],
                    ["Categorical", str(len(CATEGORICAL_FEATURES))],
                    ["Total rows", f"{len(matrix):,}"],
                ],
            ),
            "",
            "## Stock Feature Coverage",
            "",
            _table(
                [
                    "Target start",
                    "Rows with store stock history",
                    "Store stock coverage",
                    "Store in-stock",
                    "Store likely stockout",
                    "Rows with supplier stock history",
                    "Supplier stock coverage",
                    "Supplier positive",
                    "Store or supplier available",
                    "Likely true stockout",
                ],
                stock_rows,
            ),
            "",
            "## Notes",
            "",
            "- Each row is one SKU and one 4-week target window.",
            "- Features use only data before `target_start`.",
            "- Monthly store and supplier stock features use only completed months before each `target_start`; current snapshot files are excluded from historical backtests.",
            "- Supplier stock features use only `exact_unique` product-name-to-SKU mappings. Ambiguous and unmapped supplier rows are excluded from official feature values.",
            "- The default population is `forecastable_revenue_movers` only.",
        ]
    ) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Build forecast v2 feature matrix audit.")
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--population", default="headline", choices=["headline", "business_target", "all"])
    parser.add_argument("--target-start", action="append", default=None)
    parser.add_argument("--revenue-rank-limit", type=int, default=None)
    args = parser.parse_args()

    conn = sqlite3.connect(args.db)
    try:
        matrix = build_feature_matrix(
            conn,
            target_starts=args.target_start or DEFAULT_TARGET_STARTS,
            population=args.population,
            revenue_rank_limit=args.revenue_rank_limit,
        )
    finally:
        conn.close()

    report = build_report(matrix)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report, encoding="utf-8")
    print(report)
    print(f"Wrote {args.report}")


if __name__ == "__main__":
    main()
