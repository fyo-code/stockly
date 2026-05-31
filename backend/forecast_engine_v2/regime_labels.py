"""Cutoff-specific regime labels for forecast engine v2.

Labels must be recomputed for each training cutoff. The database contains
future actuals, so every query in this module uses only weeks/sales visible as
of `as_of_week`.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "backend" / "data" / "supply_chain.db"
DEFAULT_REPORT = PROJECT_ROOT / "active_docs" / "ITER5A_V2_REGIME_LABELS_AUDIT.md"
RULE_VERSION = "v2_regime_2026_05_11"


@dataclass(frozen=True)
class RegimeThresholds:
    revenue_coverage_target: float = 0.80
    forecastable_active_weeks_52: int = 12
    forecastable_active_4w_windows_52: int = 26
    forecastable_avg_units_per_4w_52: float = 2.0
    seasonal_min_pos_units_52: float = 4.0
    seasonal_min_active_months_104: int = 2
    seasonal_max_active_months_104: int = 7
    seasonal_top3_month_unit_share: float = 0.60
    seasonal_monthly_cv: float = 0.90
    seasonal_min_active_years_104: int = 2
    seasonal_min_recurring_active_months_104: int = 1


REGIME_ORDER = [
    "forecastable_revenue_movers",
    "seasonal_revenue_movers",
    "active_movers",
    "sparse_revenue_items",
    "long_tail_active",
    "dormant",
]


def _parse_monday(value: str) -> pd.Timestamp:
    parsed = pd.Timestamp(value).normalize()
    if parsed.weekday() != 0:
        raise ValueError(f"as_of_week must be a Monday week_start, got {value}")
    return parsed


def _date(value: pd.Timestamp) -> str:
    return value.strftime("%Y-%m-%d")


def _max_week(conn: sqlite3.Connection) -> str:
    row = conn.execute("SELECT MAX(week_start) FROM weekly_chain_demand_v2").fetchone()
    if not row or not row[0]:
        raise RuntimeError("weekly_chain_demand_v2 is empty")
    return str(row[0])


def ensure_regime_table(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS forecast_v2_regime_labels (
            as_of_week TEXT NOT NULL,
            horizon_start TEXT NOT NULL,
            horizon_end TEXT NOT NULL,
            rule_version TEXT NOT NULL,
            sku_id TEXT NOT NULL,
            regime TEXT NOT NULL,
            headline_eligible INTEGER NOT NULL,
            business_target_eligible INTEGER NOT NULL,
            scoring_policy TEXT NOT NULL,
            trailing_52w_revenue REAL NOT NULL,
            trailing_52w_pos_units REAL NOT NULL,
            active_weeks_52 INTEGER NOT NULL,
            active_4w_windows_52 INTEGER NOT NULL,
            avg_units_per_4w_52 REAL NOT NULL,
            revenue_rank INTEGER,
            cumulative_revenue_share REAL,
            is_top_80_revenue INTEGER NOT NULL,
            top80_cutoff_revenue REAL,
            active_months_104 INTEGER NOT NULL,
            top3_month_unit_share_104 REAL NOT NULL,
            monthly_cv_104 REAL NOT NULL,
            active_years_104 INTEGER NOT NULL,
            recurring_active_months_104 INTEGER NOT NULL,
            first_seen_week TEXT,
            last_seen_week TEXT,
            category_norm TEXT,
            product_family_v2 TEXT,
            category_signal_status TEXT,
            revenue_bucket TEXT NOT NULL,
            volume_bucket TEXT NOT NULL,
            thresholds_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            PRIMARY KEY (as_of_week, rule_version, sku_id)
        );

        CREATE INDEX IF NOT EXISTS idx_v2_regime_cutoff
            ON forecast_v2_regime_labels(as_of_week, rule_version, regime);
        CREATE INDEX IF NOT EXISTS idx_v2_regime_headline
            ON forecast_v2_regime_labels(as_of_week, rule_version, headline_eligible);
        """
    )
    conn.commit()


def _load_universe(conn: sqlite3.Connection, as_of_week: str) -> pd.DataFrame:
    return pd.read_sql_query(
        """
        SELECT sku_id, MIN(week_start) AS first_seen_week, MAX(week_start) AS last_seen_week
        FROM weekly_chain_demand_v2
        WHERE week_start <= ?
        GROUP BY sku_id
        """,
        conn,
        params=(as_of_week,),
    )


def _load_history(conn: sqlite3.Connection, start_week: str, as_of_week: str) -> pd.DataFrame:
    df = pd.read_sql_query(
        """
        SELECT sku_id, week_start, net_units, net_revenue
        FROM weekly_chain_demand_v2
        WHERE week_start BETWEEN ? AND ?
        """,
        conn,
        params=(start_week, as_of_week),
        parse_dates=["week_start"],
    )
    if df.empty:
        return df
    df["pos_units"] = df["net_units"].clip(lower=0)
    return df


def _load_category_lookup(conn: sqlite3.Connection, start_date: str, sale_cutoff_date: str) -> pd.DataFrame:
    recent = pd.read_sql_query(
        """
        SELECT
            sku_id,
            COALESCE(category_norm, 'NECUNOSCUT') AS category_norm,
            COALESCE(product_family_v2, category_norm, 'NECUNOSCUT') AS product_family_v2,
            COALESCE(category_signal_status, 'unknown') AS category_signal_status,
            SUM(net_revenue) AS revenue
        FROM raw_sales_transactions_v2
        WHERE sale_date BETWEEN ? AND ? AND is_non_product = 0
        GROUP BY sku_id, category_norm, product_family_v2, category_signal_status
        """,
        conn,
        params=(start_date, sale_cutoff_date),
    )
    fallback = pd.read_sql_query(
        """
        SELECT
            sku_id,
            COALESCE(category_norm, 'NECUNOSCUT') AS category_norm,
            COALESCE(product_family_v2, category_norm, 'NECUNOSCUT') AS product_family_v2,
            COALESCE(category_signal_status, 'unknown') AS category_signal_status,
            SUM(net_revenue) AS revenue
        FROM raw_sales_transactions_v2
        WHERE sale_date <= ? AND is_non_product = 0
        GROUP BY sku_id, category_norm, product_family_v2, category_signal_status
        """,
        conn,
        params=(sale_cutoff_date,),
    )
    combined = pd.concat([recent.assign(priority=0), fallback.assign(priority=1)], ignore_index=True)
    if combined.empty:
        return pd.DataFrame(columns=["sku_id", "category_norm", "product_family_v2", "category_signal_status"])
    combined["revenue_abs"] = combined["revenue"].abs()
    combined.sort_values(["sku_id", "priority", "revenue_abs"], ascending=[True, True, False], inplace=True)
    return combined.drop_duplicates("sku_id")[
        ["sku_id", "category_norm", "product_family_v2", "category_signal_status"]
    ]


def _rolling_4w_activity(last52: pd.DataFrame, universe: pd.DataFrame, weeks52: list[pd.Timestamp]) -> pd.DataFrame:
    week_to_idx = {week: idx for idx, week in enumerate(weeks52)}
    rows: list[dict[str, object]] = []
    grouped = last52[last52["pos_units"] > 0].groupby("sku_id")
    for sku_id, group in grouped:
        arr = np.zeros(len(weeks52), dtype=float)
        for week, units in zip(group["week_start"], group["pos_units"]):
            idx = week_to_idx.get(pd.Timestamp(week))
            if idx is not None:
                arr[idx] += float(units)
        rolling = np.convolve(arr, np.ones(4, dtype=float), mode="valid") if len(arr) >= 4 else np.array([])
        rows.append(
            {
                "sku_id": sku_id,
                "active_4w_windows_52": int((rolling > 0).sum()),
                "avg_units_per_4w_52": float(arr.sum() / 13.0),
            }
        )
    result = pd.DataFrame(rows)
    if result.empty:
        result = pd.DataFrame(columns=["sku_id", "active_4w_windows_52", "avg_units_per_4w_52"])
    result = universe[["sku_id"]].merge(result, on="sku_id", how="left")
    result["active_4w_windows_52"] = result["active_4w_windows_52"].fillna(0).astype(int)
    result["avg_units_per_4w_52"] = result["avg_units_per_4w_52"].fillna(0.0)
    return result


def _seasonality_metrics(history104: pd.DataFrame, universe: pd.DataFrame) -> pd.DataFrame:
    active = history104[history104["pos_units"] > 0].copy()
    if active.empty:
        metrics = universe[["sku_id"]].copy()
        for col in ("active_months_104", "active_years_104", "recurring_active_months_104"):
            metrics[col] = 0
        metrics["top3_month_unit_share_104"] = 0.0
        metrics["monthly_cv_104"] = 0.0
        return metrics

    active["month"] = active["week_start"].dt.month
    active["year"] = active["week_start"].dt.year
    month_units = active.groupby(["sku_id", "month"], as_index=False)["pos_units"].sum()
    active_years = active.groupby("sku_id")["year"].nunique().rename("active_years_104")
    recurring = (
        active.groupby(["sku_id", "month"])["year"].nunique()
        .reset_index(name="years_active")
        .query("years_active >= 2")
        .groupby("sku_id")["month"].count()
        .rename("recurring_active_months_104")
    )

    rows: list[dict[str, object]] = []
    for sku_id, group in month_units.groupby("sku_id"):
        arr = np.zeros(12, dtype=float)
        for month, units in zip(group["month"], group["pos_units"]):
            arr[int(month) - 1] = float(units)
        total = float(arr.sum())
        top3_share = float(np.sort(arr)[-3:].sum() / total) if total > 0 else 0.0
        mean = float(arr.mean())
        cv = float(arr.std(ddof=0) / mean) if mean > 0 else 0.0
        rows.append(
            {
                "sku_id": sku_id,
                "active_months_104": int((arr > 0).sum()),
                "top3_month_unit_share_104": top3_share,
                "monthly_cv_104": cv,
            }
        )

    metrics = pd.DataFrame(rows)
    metrics = metrics.merge(active_years.reset_index(), on="sku_id", how="left")
    metrics = metrics.merge(recurring.reset_index(), on="sku_id", how="left")
    metrics = universe[["sku_id"]].merge(metrics, on="sku_id", how="left")
    metrics["active_months_104"] = metrics["active_months_104"].fillna(0).astype(int)
    metrics["active_years_104"] = metrics["active_years_104"].fillna(0).astype(int)
    metrics["recurring_active_months_104"] = metrics["recurring_active_months_104"].fillna(0).astype(int)
    metrics["top3_month_unit_share_104"] = metrics["top3_month_unit_share_104"].fillna(0.0)
    metrics["monthly_cv_104"] = metrics["monthly_cv_104"].fillna(0.0)
    return metrics


def _revenue_bucket(rank: object, is_top80: bool) -> str:
    if pd.isna(rank):
        return "no_revenue"
    rank_int = int(rank)
    if rank_int <= 100:
        return "top_100"
    if rank_int <= 500:
        return "101_500"
    if rank_int <= 1000:
        return "501_1000"
    if rank_int <= 5000:
        return "1001_5000"
    if is_top80:
        return "rest_to_80pct"
    return "outside_80pct"


def _volume_bucket(units: float) -> str:
    if units <= 0:
        return "zero_52w"
    if units < 4:
        return "1_3_units_52w"
    if units < 13:
        return "4_12_units_52w"
    if units < 52:
        return "13_51_units_52w"
    if units < 156:
        return "52_155_units_52w"
    return "156_plus_units_52w"


def build_regime_labels(
    conn: sqlite3.Connection,
    as_of_week: str,
    thresholds: RegimeThresholds | None = None,
) -> pd.DataFrame:
    thresholds = thresholds or RegimeThresholds()
    cutoff = _parse_monday(as_of_week)
    start52 = cutoff - pd.Timedelta(weeks=51)
    start104 = cutoff - pd.Timedelta(weeks=103)
    horizon_start = cutoff + pd.Timedelta(weeks=1)
    horizon_end = horizon_start + pd.Timedelta(days=27)
    sale_cutoff = cutoff + pd.Timedelta(days=6)

    universe = _load_universe(conn, _date(cutoff))
    if universe.empty:
        raise RuntimeError(f"No SKU universe found for cutoff {_date(cutoff)}")

    history104 = _load_history(conn, _date(start104), _date(cutoff))
    last52 = history104[history104["week_start"] >= start52].copy()

    agg52 = last52.groupby("sku_id").agg(
        trailing_52w_revenue=("net_revenue", "sum"),
        trailing_52w_pos_units=("pos_units", "sum"),
        active_weeks_52=("pos_units", lambda s: int((s > 0).sum())),
    ).reset_index()
    df = universe.merge(agg52, on="sku_id", how="left")
    for col in ("trailing_52w_revenue", "trailing_52w_pos_units"):
        df[col] = df[col].fillna(0.0)
    df["active_weeks_52"] = df["active_weeks_52"].fillna(0).astype(int)

    weeks52 = list(pd.date_range(start52, cutoff, freq="W-MON"))
    df = df.merge(_rolling_4w_activity(last52, universe, weeks52), on="sku_id", how="left")
    df = df.merge(_seasonality_metrics(history104, universe), on="sku_id", how="left")
    df = df.merge(_load_category_lookup(conn, _date(start52), _date(sale_cutoff)), on="sku_id", how="left")
    df["category_norm"] = df["category_norm"].fillna("NECUNOSCUT")
    df["product_family_v2"] = df["product_family_v2"].fillna(df["category_norm"])
    df["category_signal_status"] = df["category_signal_status"].fillna("unknown")

    ranked = df[df["trailing_52w_revenue"] > 0].sort_values(
        ["trailing_52w_revenue", "sku_id"], ascending=[False, True]
    ).copy()
    total_revenue = float(ranked["trailing_52w_revenue"].sum())
    if total_revenue > 0:
        ranked["revenue_rank"] = np.arange(1, len(ranked) + 1)
        ranked["cumulative_revenue"] = ranked["trailing_52w_revenue"].cumsum()
        ranked["cumulative_revenue_share"] = ranked["cumulative_revenue"] / total_revenue
        ranked["cumulative_revenue_share_before"] = (
            ranked["cumulative_revenue"] - ranked["trailing_52w_revenue"]
        ) / total_revenue
        ranked["is_top_80_revenue"] = (
            ranked["cumulative_revenue_share_before"] < thresholds.revenue_coverage_target
        ).astype(int)
        top80_cutoff = float(ranked.loc[ranked["is_top_80_revenue"] == 1, "trailing_52w_revenue"].min())
    else:
        ranked["revenue_rank"] = np.nan
        ranked["cumulative_revenue_share"] = np.nan
        ranked["is_top_80_revenue"] = 0
        top80_cutoff = 0.0

    df = df.merge(
        ranked[["sku_id", "revenue_rank", "cumulative_revenue_share", "is_top_80_revenue"]],
        on="sku_id",
        how="left",
    )
    df["is_top_80_revenue"] = df["is_top_80_revenue"].fillna(0).astype(int)
    df["top80_cutoff_revenue"] = top80_cutoff

    forecastable_mask = (
        (df["is_top_80_revenue"] == 1)
        & (df["active_weeks_52"] >= thresholds.forecastable_active_weeks_52)
        & (df["active_4w_windows_52"] >= thresholds.forecastable_active_4w_windows_52)
        & (df["avg_units_per_4w_52"] >= thresholds.forecastable_avg_units_per_4w_52)
    )
    recurring_mask = (
        (df["active_weeks_52"] >= thresholds.forecastable_active_weeks_52)
        & (df["active_4w_windows_52"] >= thresholds.forecastable_active_4w_windows_52)
        & (df["avg_units_per_4w_52"] >= thresholds.forecastable_avg_units_per_4w_52)
    )
    seasonal_mask = (
        (df["is_top_80_revenue"] == 1)
        & ~forecastable_mask
        & (df["trailing_52w_pos_units"] >= thresholds.seasonal_min_pos_units_52)
        & (df["active_months_104"] >= thresholds.seasonal_min_active_months_104)
        & (df["active_months_104"] <= thresholds.seasonal_max_active_months_104)
        & (df["top3_month_unit_share_104"] >= thresholds.seasonal_top3_month_unit_share)
        & (df["monthly_cv_104"] >= thresholds.seasonal_monthly_cv)
        & (df["active_years_104"] >= thresholds.seasonal_min_active_years_104)
        & (df["recurring_active_months_104"] >= thresholds.seasonal_min_recurring_active_months_104)
    )

    df["regime"] = "dormant"
    df.loc[(df["trailing_52w_pos_units"] > 0), "regime"] = "long_tail_active"
    df.loc[(df["is_top_80_revenue"] == 1), "regime"] = "sparse_revenue_items"
    df.loc[(df["is_top_80_revenue"] == 0) & recurring_mask, "regime"] = "active_movers"
    df.loc[seasonal_mask, "regime"] = "seasonal_revenue_movers"
    df.loc[forecastable_mask, "regime"] = "forecastable_revenue_movers"

    df["headline_eligible"] = (df["regime"] == "forecastable_revenue_movers").astype(int)
    df["business_target_eligible"] = df["regime"].isin(
        ["forecastable_revenue_movers", "seasonal_revenue_movers"]
    ).astype(int)
    policy_map = {
        "forecastable_revenue_movers": "quantity_4w_material",
        "seasonal_revenue_movers": "seasonal_active_or_zero",
        "active_movers": "quantity_secondary",
        "sparse_revenue_items": "track_sparse_revenue",
        "long_tail_active": "sale_probability",
        "dormant": "zero_or_reactivation",
    }
    df["scoring_policy"] = df["regime"].map(policy_map)
    df["revenue_bucket"] = [
        _revenue_bucket(rank, bool(top80))
        for rank, top80 in zip(df["revenue_rank"], df["is_top_80_revenue"])
    ]
    df["volume_bucket"] = df["trailing_52w_pos_units"].apply(lambda v: _volume_bucket(float(v)))
    df["as_of_week"] = _date(cutoff)
    df["horizon_start"] = _date(horizon_start)
    df["horizon_end"] = _date(horizon_end)
    df["rule_version"] = RULE_VERSION
    df["thresholds_json"] = json.dumps(asdict(thresholds), sort_keys=True)
    df["created_at"] = datetime.utcnow().isoformat(timespec="seconds")

    columns = [
        "as_of_week", "horizon_start", "horizon_end", "rule_version", "sku_id",
        "regime", "headline_eligible", "business_target_eligible", "scoring_policy",
        "trailing_52w_revenue", "trailing_52w_pos_units", "active_weeks_52",
        "active_4w_windows_52", "avg_units_per_4w_52", "revenue_rank",
        "cumulative_revenue_share", "is_top_80_revenue", "top80_cutoff_revenue",
        "active_months_104", "top3_month_unit_share_104", "monthly_cv_104",
        "active_years_104", "recurring_active_months_104", "first_seen_week",
        "last_seen_week", "category_norm", "product_family_v2", "category_signal_status",
        "revenue_bucket", "volume_bucket", "thresholds_json", "created_at",
    ]
    return df[columns].sort_values(["regime", "revenue_rank", "sku_id"], na_position="last")


def write_regime_labels(conn: sqlite3.Connection, labels: pd.DataFrame) -> None:
    ensure_regime_table(conn)
    as_of_week = str(labels["as_of_week"].iloc[0])
    rule_version = str(labels["rule_version"].iloc[0])
    conn.execute(
        "DELETE FROM forecast_v2_regime_labels WHERE as_of_week = ? AND rule_version = ?",
        (as_of_week, rule_version),
    )
    labels.to_sql("_forecast_v2_regime_labels_tmp", conn, if_exists="replace", index=False)
    conn.execute(
        """
        INSERT INTO forecast_v2_regime_labels
        SELECT * FROM _forecast_v2_regime_labels_tmp
        """
    )
    conn.execute("DROP TABLE _forecast_v2_regime_labels_tmp")
    conn.commit()


def build_report(labels: pd.DataFrame) -> str:
    total_revenue = labels["trailing_52w_revenue"].sum()
    rows = []
    for regime in REGIME_ORDER:
        subset = labels[labels["regime"] == regime]
        rows.append(
            [
                regime,
                f"{len(subset):,}",
                f"{subset['trailing_52w_revenue'].sum():,.2f}",
                f"{subset['trailing_52w_revenue'].sum() / total_revenue * 100:.1f}%" if total_revenue else "0.0%",
                f"{subset['trailing_52w_pos_units'].sum():,.1f}",
            ]
        )

    bucket_rows = []
    for bucket, subset in labels.groupby("revenue_bucket", dropna=False):
        bucket_rows.append(
            [
                bucket,
                f"{len(subset):,}",
                f"{subset['trailing_52w_revenue'].sum():,.2f}",
            ]
        )

    def table(headers: list[str], body: list[list[str]]) -> str:
        lines = [
            "| " + " | ".join(headers) + " |",
            "| " + " | ".join("---" for _ in headers) + " |",
        ]
        lines.extend("| " + " | ".join(row) + " |" for row in body)
        return "\n".join(lines)

    as_of = labels["as_of_week"].iloc[0]
    top80 = labels[labels["is_top_80_revenue"] == 1]
    return "\n".join(
        [
            "# Iteration 5A — V2 Regime Labels Audit",
            "",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"As-of week: `{as_of}`",
            f"Rule version: `{labels['rule_version'].iloc[0]}`",
            "",
            "## Summary",
            "",
            table(
                ["Regime", "SKUs", "Trailing 52w revenue", "Revenue share", "Trailing 52w units"],
                rows,
            ),
            "",
            "## Top-80 Revenue Set",
            "",
            table(
                ["Metric", "Value"],
                [
                    ["Top-80 SKUs", f"{len(top80):,}"],
                    ["Top-80 revenue", f"{top80['trailing_52w_revenue'].sum():,.2f}"],
                    ["Top-80 cutoff revenue", f"{labels['top80_cutoff_revenue'].iloc[0]:,.2f}"],
                    ["Headline forecastable SKUs", f"{int(labels['headline_eligible'].sum()):,}"],
                    ["Business target SKUs", f"{int(labels['business_target_eligible'].sum()):,}"],
                ],
            ),
            "",
            "## Revenue Buckets",
            "",
            table(["Bucket", "SKUs", "Trailing 52w revenue"], bucket_rows),
            "",
            "## Notes",
            "",
            "- Labels use only `weekly_chain_demand_v2.week_start <= as_of_week`.",
            "- Movement uses clipped positive units so return-only weeks do not create false activity.",
            "- `headline_eligible` currently means `forecastable_revenue_movers`; seasonal movers are tracked as business-target eligible but scored separately.",
        ]
    ) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Build forecast v2 regime labels for a cutoff week.")
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument("--as-of-week", default=None, help="Monday week_start cutoff. Defaults to max v2 week.")
    parser.add_argument("--write", action="store_true", help="Persist labels to forecast_v2_regime_labels.")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()

    conn = sqlite3.connect(args.db)
    try:
        as_of_week = args.as_of_week or _max_week(conn)
        labels = build_regime_labels(conn, as_of_week)
        if args.write:
            write_regime_labels(conn, labels)
        report = build_report(labels)
    finally:
        conn.close()

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report, encoding="utf-8")
    print(report)
    print(f"Wrote {args.report}")


if __name__ == "__main__":
    main()

