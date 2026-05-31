"""Forecast v2 chain-level naive benchmarks and scorecard.

This is the measurement foundation before model training. It scores simple
chain-level 4-week baselines on cutoff-specific regime labels.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from .regime_labels import RULE_VERSION, build_regime_labels, write_regime_labels
except ImportError:  # Allows direct script execution.
    from regime_labels import RULE_VERSION, build_regime_labels, write_regime_labels


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "backend" / "data" / "supply_chain.db"
DEFAULT_REPORT = PROJECT_ROOT / "active_docs" / "ITER5A_V2_NAIVE_SCORECARD.md"

MODEL_NAMES = ["zero", "last4", "roll8_mean", "roll13_mean", "seasonal52", "median_naive"]


@dataclass(frozen=True)
class ScorecardConfig:
    horizon_weeks: int = 4
    material_units_threshold: float = 4.0
    phantom_threshold: float = 1.0
    sale_threshold: float = 1.0


def _parse_monday(value: str) -> pd.Timestamp:
    parsed = pd.Timestamp(value).normalize()
    if parsed.weekday() != 0:
        raise ValueError(f"target_start must be a Monday week_start, got {value}")
    return parsed


def _date(value: pd.Timestamp) -> str:
    return value.strftime("%Y-%m-%d")


def _run_id(target_start: pd.Timestamp, model_label: str) -> str:
    return f"{model_label}_{_date(target_start)}"


def ensure_scorecard_tables(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS forecast_v2_score_runs (
            run_id TEXT PRIMARY KEY,
            run_type TEXT NOT NULL,
            model_label TEXT NOT NULL,
            train_cutoff TEXT NOT NULL,
            target_start TEXT NOT NULL,
            target_end TEXT NOT NULL,
            horizon_weeks INTEGER NOT NULL,
            regime_version TEXT NOT NULL,
            thresholds_json TEXT NOT NULL,
            phantom_threshold REAL NOT NULL,
            material_units_threshold REAL NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS forecast_v2_predictions (
            run_id TEXT NOT NULL,
            model_name TEXT NOT NULL,
            sku_id TEXT NOT NULL,
            target_start TEXT NOT NULL,
            target_end TEXT NOT NULL,
            pred_units_4w REAL NOT NULL,
            prediction_source TEXT NOT NULL,
            model_version TEXT NOT NULL,
            PRIMARY KEY (run_id, model_name, sku_id)
        );

        CREATE TABLE IF NOT EXISTS forecast_v2_actuals_4w (
            run_id TEXT NOT NULL,
            sku_id TEXT NOT NULL,
            target_start TEXT NOT NULL,
            target_end TEXT NOT NULL,
            actual_pos_units_4w REAL NOT NULL,
            actual_net_units_4w REAL NOT NULL,
            actual_net_revenue_4w REAL NOT NULL,
            negative_unit_weeks INTEGER NOT NULL,
            bf_txn_count INTEGER NOT NULL,
            bf_observed_txn_count INTEGER NOT NULL,
            bf_inferred_txn_count INTEGER NOT NULL,
            campaign_observed_txn_count INTEGER NOT NULL,
            unknown_campaign_label_txn_count INTEGER NOT NULL,
            PRIMARY KEY (run_id, sku_id)
        );

        CREATE TABLE IF NOT EXISTS forecast_v2_score_rows (
            run_id TEXT NOT NULL,
            model_name TEXT NOT NULL,
            sku_id TEXT NOT NULL,
            regime TEXT NOT NULL,
            headline_eligible INTEGER NOT NULL,
            business_target_eligible INTEGER NOT NULL,
            scoring_policy TEXT NOT NULL,
            revenue_bucket TEXT NOT NULL,
            volume_bucket TEXT NOT NULL,
            category_norm TEXT,
            product_family_v2 TEXT,
            category_signal_status TEXT,
            campaign_bucket TEXT NOT NULL,
            actual_units REAL NOT NULL,
            actual_net_units REAL NOT NULL,
            actual_revenue REAL NOT NULL,
            pred_units REAL NOT NULL,
            abs_error REAL NOT NULL,
            signed_error REAL NOT NULL,
            abs_pct_error REAL,
            hit20 INTEGER,
            hit30 INTEGER,
            under20 INTEGER,
            over20 INTEGER,
            quantity_scored INTEGER NOT NULL,
            phantom INTEGER NOT NULL,
            pred_sale INTEGER NOT NULL,
            actual_sale INTEGER NOT NULL,
            missing_prediction INTEGER NOT NULL,
            PRIMARY KEY (run_id, model_name, sku_id)
        );

        CREATE TABLE IF NOT EXISTS forecast_v2_scorecard_slices (
            run_id TEXT NOT NULL,
            model_name TEXT NOT NULL,
            slice_type TEXT NOT NULL,
            slice_value TEXT NOT NULL,
            n_population INTEGER NOT NULL,
            n_quantity_scored INTEGER NOT NULL,
            n_zero_actual INTEGER NOT NULL,
            n_phantom INTEGER NOT NULL,
            actual_units REAL NOT NULL,
            pred_units REAL NOT NULL,
            wmape REAL,
            hit20 REAL,
            hit30 REAL,
            bias_pct REAL,
            phantom_rate REAL,
            under20_rate REAL,
            over20_rate REAL,
            winrate_vs_median_naive REAL,
            PRIMARY KEY (run_id, model_name, slice_type, slice_value)
        );

        CREATE INDEX IF NOT EXISTS idx_v2_score_rows_run_regime
            ON forecast_v2_score_rows(run_id, model_name, regime);
        CREATE INDEX IF NOT EXISTS idx_v2_score_slices_run
            ON forecast_v2_scorecard_slices(run_id, model_name, slice_type);
        """
    )
    conn.commit()


def _load_weekly(conn: sqlite3.Connection, start_week: str, end_week_exclusive: str) -> pd.DataFrame:
    df = pd.read_sql_query(
        """
        SELECT sku_id, week_start, net_units, net_revenue
        FROM weekly_chain_demand_v2
        WHERE week_start >= ? AND week_start < ?
        """,
        conn,
        params=(start_week, end_week_exclusive),
        parse_dates=["week_start"],
    )
    if df.empty:
        return df
    df["pos_units"] = df["net_units"].clip(lower=0)
    return df


def _sum_units(df: pd.DataFrame, start: pd.Timestamp, end_exclusive: pd.Timestamp) -> pd.Series:
    if df.empty:
        return pd.Series(dtype=float)
    subset = df[(df["week_start"] >= start) & (df["week_start"] < end_exclusive)]
    if subset.empty:
        return pd.Series(dtype=float)
    return subset.groupby("sku_id")["pos_units"].sum()


def build_naive_predictions(
    conn: sqlite3.Connection,
    labels: pd.DataFrame,
    target_start: pd.Timestamp,
    config: ScorecardConfig,
) -> pd.DataFrame:
    target_end_exclusive = target_start + pd.Timedelta(weeks=config.horizon_weeks)
    load_start = target_start - pd.Timedelta(weeks=52)
    weekly = _load_weekly(conn, _date(load_start), _date(target_end_exclusive))
    skus = labels[["sku_id"]].copy()

    sums = pd.DataFrame({"sku_id": skus["sku_id"]})
    sums["zero"] = 0.0
    sums["last4"] = sums["sku_id"].map(
        _sum_units(weekly, target_start - pd.Timedelta(weeks=4), target_start)
    ).fillna(0.0)
    sums["roll8_mean"] = sums["sku_id"].map(
        _sum_units(weekly, target_start - pd.Timedelta(weeks=8), target_start)
    ).fillna(0.0) / 8.0 * 4.0
    sums["roll13_mean"] = sums["sku_id"].map(
        _sum_units(weekly, target_start - pd.Timedelta(weeks=13), target_start)
    ).fillna(0.0) / 13.0 * 4.0
    sums["seasonal52"] = sums["sku_id"].map(
        _sum_units(
            weekly,
            target_start - pd.Timedelta(weeks=52),
            target_start - pd.Timedelta(weeks=52) + pd.Timedelta(weeks=config.horizon_weeks),
        )
    ).fillna(0.0)
    sums["median_naive"] = sums[["last4", "roll13_mean", "seasonal52"]].median(axis=1)

    rows: list[dict[str, object]] = []
    target_end = target_end_exclusive - pd.Timedelta(days=1)
    for model_name in MODEL_NAMES:
        for sku_id, pred in zip(sums["sku_id"], sums[model_name]):
            rows.append(
                {
                    "model_name": model_name,
                    "sku_id": sku_id,
                    "target_start": _date(target_start),
                    "target_end": _date(target_end),
                    "pred_units_4w": float(max(pred, 0.0)),
                    "prediction_source": "v2_naive_chain_weekly",
                    "model_version": "v2_naive_2026_05_11",
                }
            )
    return pd.DataFrame(rows)


def build_actuals(
    conn: sqlite3.Connection,
    labels: pd.DataFrame,
    target_start: pd.Timestamp,
    config: ScorecardConfig,
) -> pd.DataFrame:
    target_end_exclusive = target_start + pd.Timedelta(weeks=config.horizon_weeks)
    target_end = target_end_exclusive - pd.Timedelta(days=1)
    weekly = _load_weekly(conn, _date(target_start), _date(target_end_exclusive))

    if weekly.empty:
        actual = pd.DataFrame({"sku_id": labels["sku_id"]})
        actual["actual_pos_units_4w"] = 0.0
        actual["actual_net_units_4w"] = 0.0
        actual["actual_net_revenue_4w"] = 0.0
        actual["negative_unit_weeks"] = 0
    else:
        agg = weekly.groupby("sku_id").agg(
            actual_pos_units_4w=("pos_units", "sum"),
            actual_net_units_4w=("net_units", "sum"),
            actual_net_revenue_4w=("net_revenue", "sum"),
            negative_unit_weeks=("net_units", lambda s: int((s < 0).sum())),
        ).reset_index()
        actual = labels[["sku_id"]].merge(agg, on="sku_id", how="left")
        for col in ("actual_pos_units_4w", "actual_net_units_4w", "actual_net_revenue_4w"):
            actual[col] = actual[col].fillna(0.0)
        actual["negative_unit_weeks"] = actual["negative_unit_weeks"].fillna(0).astype(int)

    raw = pd.read_sql_query(
        """
        SELECT
            sku_id,
            SUM(CASE WHEN is_bf_timing = 1 THEN 1 ELSE 0 END) AS bf_txn_count,
            SUM(CASE WHEN is_bf_observed = 1 THEN 1 ELSE 0 END) AS bf_observed_txn_count,
            SUM(CASE WHEN is_bf_inferred = 1 THEN 1 ELSE 0 END) AS bf_inferred_txn_count,
            SUM(CASE WHEN campaign_signal_status = 'observed' THEN 1 ELSE 0 END) AS campaign_observed_txn_count,
            SUM(CASE WHEN bf_signal_source IN (
                'campaign_label_without_timing_evidence',
                'campaign_bf_outside_timing_window',
                'campaign_bf_without_timing_evidence'
            ) THEN 1 ELSE 0 END) AS unknown_campaign_label_txn_count
        FROM raw_sales_transactions_v2
        WHERE sale_date BETWEEN ? AND ? AND is_non_product = 0
        GROUP BY sku_id
        """,
        conn,
        params=(_date(target_start), _date(target_end)),
    )
    actual = actual.merge(raw, on="sku_id", how="left")
    for col in (
        "bf_txn_count",
        "bf_observed_txn_count",
        "bf_inferred_txn_count",
        "campaign_observed_txn_count",
        "unknown_campaign_label_txn_count",
    ):
        actual[col] = actual[col].fillna(0).astype(int)
    actual["target_start"] = _date(target_start)
    actual["target_end"] = _date(target_end)
    return actual


def _campaign_bucket(row: pd.Series) -> str:
    if row["bf_observed_txn_count"] > 0:
        return "bf_observed"
    if row["bf_inferred_txn_count"] > 0:
        return "bf_inferred"
    if row["unknown_campaign_label_txn_count"] > 0:
        return "unknown_campaign_label"
    if row["campaign_observed_txn_count"] > 0:
        return "campaign_observed_non_bf"
    return "non_campaign"


def build_score_rows(
    labels: pd.DataFrame,
    predictions: pd.DataFrame,
    actuals: pd.DataFrame,
    run_id: str,
    config: ScorecardConfig,
) -> pd.DataFrame:
    base = labels.merge(actuals, on="sku_id", how="left")
    base["campaign_bucket"] = base.apply(_campaign_bucket, axis=1)

    rows = base.merge(predictions, on="sku_id", how="left")
    rows["run_id"] = run_id
    rows["pred_units_4w"] = rows["pred_units_4w"].fillna(0.0)
    rows["missing_prediction"] = rows["model_name"].isna().astype(int)
    rows["model_name"] = rows["model_name"].fillna("missing_prediction")
    rows["actual_units"] = rows["actual_pos_units_4w"].fillna(0.0)
    rows["actual_net_units"] = rows["actual_net_units_4w"].fillna(0.0)
    rows["actual_revenue"] = rows["actual_net_revenue_4w"].fillna(0.0)
    rows["pred_units"] = rows["pred_units_4w"].clip(lower=0.0)
    rows["abs_error"] = (rows["pred_units"] - rows["actual_units"]).abs()
    rows["signed_error"] = rows["pred_units"] - rows["actual_units"]
    rows["quantity_scored"] = (rows["actual_units"] >= config.material_units_threshold).astype(int)
    rows["abs_pct_error"] = np.where(
        rows["quantity_scored"] == 1,
        rows["abs_error"] / rows["actual_units"],
        np.nan,
    )
    rows["hit20"] = np.where(rows["quantity_scored"] == 1, (rows["abs_pct_error"] <= 0.20).astype(int), np.nan)
    rows["hit30"] = np.where(rows["quantity_scored"] == 1, (rows["abs_pct_error"] <= 0.30).astype(int), np.nan)
    rows["under20"] = np.where(
        rows["quantity_scored"] == 1,
        (rows["pred_units"] < 0.80 * rows["actual_units"]).astype(int),
        np.nan,
    )
    rows["over20"] = np.where(
        rows["quantity_scored"] == 1,
        (rows["pred_units"] > 1.20 * rows["actual_units"]).astype(int),
        np.nan,
    )
    rows["phantom"] = ((rows["actual_units"] == 0) & (rows["pred_units"] >= config.phantom_threshold)).astype(int)
    rows["pred_sale"] = (rows["pred_units"] >= config.sale_threshold).astype(int)
    rows["actual_sale"] = (rows["actual_units"] > 0).astype(int)

    keep = [
        "run_id", "model_name", "sku_id", "regime", "headline_eligible",
        "business_target_eligible", "scoring_policy", "revenue_bucket",
        "volume_bucket", "category_norm", "product_family_v2",
        "category_signal_status", "campaign_bucket", "actual_units",
        "actual_net_units", "actual_revenue", "pred_units", "abs_error",
        "signed_error", "abs_pct_error", "hit20", "hit30", "under20",
        "over20", "quantity_scored", "phantom", "pred_sale", "actual_sale",
        "missing_prediction",
    ]
    return rows[keep]


def _metrics_for_group(group: pd.DataFrame, median_lookup: pd.Series | None) -> dict[str, object]:
    scored = group[group["quantity_scored"] == 1]
    actual_sum = float(scored["actual_units"].sum())
    pred_sum = float(scored["pred_units"].sum())
    zero_actual = group[group["actual_units"] == 0]
    wmape = float(scored["abs_error"].sum() / actual_sum) if actual_sum > 0 else None
    bias = float(scored["signed_error"].sum() / actual_sum) if actual_sum > 0 else None
    phantom_rate = float(zero_actual["phantom"].mean()) if len(zero_actual) else None

    winrate = None
    if median_lookup is not None and not scored.empty:
        median_abs = scored["sku_id"].map(median_lookup)
        valid = median_abs.notna()
        if valid.any():
            winrate = float((scored.loc[valid, "abs_error"] < median_abs.loc[valid]).mean())

    return {
        "n_population": int(len(group)),
        "n_quantity_scored": int(len(scored)),
        "n_zero_actual": int(len(zero_actual)),
        "n_phantom": int(group["phantom"].sum()),
        "actual_units": actual_sum,
        "pred_units": pred_sum,
        "wmape": wmape,
        "hit20": float(scored["hit20"].mean()) if not scored.empty else None,
        "hit30": float(scored["hit30"].mean()) if not scored.empty else None,
        "bias_pct": bias,
        "phantom_rate": phantom_rate,
        "under20_rate": float(scored["under20"].mean()) if not scored.empty else None,
        "over20_rate": float(scored["over20"].mean()) if not scored.empty else None,
        "winrate_vs_median_naive": winrate,
    }


def build_slices(score_rows: pd.DataFrame, run_id: str) -> pd.DataFrame:
    median_lookup = (
        score_rows[score_rows["model_name"] == "median_naive"]
        .set_index("sku_id")["abs_error"]
    )
    slice_specs = [
        ("all", lambda df: [("all", df)]),
        ("headline", lambda df: [("forecastable_revenue_movers", df[df["headline_eligible"] == 1])]),
        ("business_target", lambda df: [("forecastable_plus_seasonal", df[df["business_target_eligible"] == 1])]),
        ("regime", lambda df: list(df.groupby("regime", dropna=False))),
        ("revenue_bucket", lambda df: list(df.groupby("revenue_bucket", dropna=False))),
        ("category_norm", lambda df: list(df.groupby("category_norm", dropna=False))),
        ("campaign_bucket", lambda df: list(df.groupby("campaign_bucket", dropna=False))),
    ]

    rows: list[dict[str, object]] = []
    for model_name, model_df in score_rows.groupby("model_name"):
        median_for_model = None if model_name == "median_naive" else median_lookup
        for slice_type, builder in slice_specs:
            for slice_value, group in builder(model_df):
                if group.empty:
                    continue
                metrics = _metrics_for_group(group, median_for_model)
                rows.append(
                    {
                        "run_id": run_id,
                        "model_name": model_name,
                        "slice_type": slice_type,
                        "slice_value": str(slice_value),
                        **metrics,
                    }
                )
    return pd.DataFrame(rows)


def score_model_predictions_fast(
    labels: pd.DataFrame,
    predictions: pd.DataFrame,
    actuals: pd.DataFrame,
    run_id: str,
    config: ScorecardConfig | None = None,
    baseline_predictions: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Score experiment predictions without writing row-level results.

    This is the tuning path for Iteration 5B. Official audits can still use
    `write_scorecard`, but repeated model experiments should avoid persisting
    millions of rows unless the candidate is worth preserving.
    """
    config = config or ScorecardConfig()
    prediction_frames = [predictions]
    if baseline_predictions is not None and not baseline_predictions.empty:
        prediction_frames.append(baseline_predictions)
    combined_predictions = pd.concat(prediction_frames, ignore_index=True)
    score_rows = build_score_rows(labels, combined_predictions, actuals, run_id, config)
    slices = build_slices(score_rows, run_id)
    return score_rows, slices


def write_scorecard(
    conn: sqlite3.Connection,
    run_id: str,
    labels: pd.DataFrame,
    predictions: pd.DataFrame,
    actuals: pd.DataFrame,
    score_rows: pd.DataFrame,
    slices: pd.DataFrame,
    target_start: pd.Timestamp,
    config: ScorecardConfig,
    model_label: str,
) -> None:
    ensure_scorecard_tables(conn)
    target_end = target_start + pd.Timedelta(weeks=config.horizon_weeks) - pd.Timedelta(days=1)
    train_cutoff = target_start - pd.Timedelta(weeks=1)
    thresholds_json = labels["thresholds_json"].iloc[0]

    conn.execute("DELETE FROM forecast_v2_score_runs WHERE run_id = ?", (run_id,))
    for table in (
        "forecast_v2_predictions",
        "forecast_v2_actuals_4w",
        "forecast_v2_score_rows",
        "forecast_v2_scorecard_slices",
    ):
        conn.execute(f"DELETE FROM {table} WHERE run_id = ?", (run_id,))

    conn.execute(
        """
        INSERT INTO forecast_v2_score_runs (
            run_id, run_type, model_label, train_cutoff, target_start, target_end,
            horizon_weeks, regime_version, thresholds_json, phantom_threshold,
            material_units_threshold, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            run_id,
            "naive_benchmark",
            model_label,
            _date(train_cutoff),
            _date(target_start),
            _date(target_end),
            config.horizon_weeks,
            RULE_VERSION,
            thresholds_json,
            config.phantom_threshold,
            config.material_units_threshold,
            datetime.utcnow().isoformat(timespec="seconds"),
        ),
    )

    predictions_with_run = predictions.copy()
    predictions_with_run["run_id"] = run_id
    predictions_with_run[
        ["run_id", "model_name", "sku_id", "target_start", "target_end", "pred_units_4w", "prediction_source", "model_version"]
    ].to_sql("forecast_v2_predictions", conn, if_exists="append", index=False)

    actuals_with_run = actuals.copy()
    actuals_with_run["run_id"] = run_id
    actuals_with_run[
        [
            "run_id", "sku_id", "target_start", "target_end", "actual_pos_units_4w",
            "actual_net_units_4w", "actual_net_revenue_4w", "negative_unit_weeks",
            "bf_txn_count", "bf_observed_txn_count", "bf_inferred_txn_count",
            "campaign_observed_txn_count", "unknown_campaign_label_txn_count",
        ]
    ].to_sql("forecast_v2_actuals_4w", conn, if_exists="append", index=False)
    score_rows.to_sql("forecast_v2_score_rows", conn, if_exists="append", index=False)
    slices.to_sql("forecast_v2_scorecard_slices", conn, if_exists="append", index=False)
    conn.commit()


def run_naive_scorecard(
    conn: sqlite3.Connection,
    target_start: str,
    model_label: str = "v2_naive",
    config: ScorecardConfig | None = None,
    persist: bool = True,
) -> tuple[str, pd.DataFrame]:
    config = config or ScorecardConfig()
    start = _parse_monday(target_start)
    as_of_week = start - pd.Timedelta(weeks=1)
    run_id = _run_id(start, model_label)

    labels = build_regime_labels(conn, _date(as_of_week))
    if persist:
        write_regime_labels(conn, labels)
    predictions = build_naive_predictions(conn, labels, start, config)
    actuals = build_actuals(conn, labels, start, config)
    score_rows = build_score_rows(labels, predictions, actuals, run_id, config)
    slices = build_slices(score_rows, run_id)
    if persist:
        write_scorecard(conn, run_id, labels, predictions, actuals, score_rows, slices, start, config, model_label)
    return run_id, slices


def _fmt_pct(value: object) -> str:
    if value is None or pd.isna(value):
        return "-"
    return f"{float(value) * 100:.1f}%"


def _fmt_num(value: object, digits: int = 1) -> str:
    if value is None or pd.isna(value):
        return "-"
    return f"{float(value):,.{digits}f}"


def build_report(all_slices: pd.DataFrame, run_ids: list[str]) -> str:
    headline = all_slices[
        (all_slices["slice_type"] == "headline")
        & (all_slices["slice_value"] == "forecastable_revenue_movers")
    ].copy()
    regime = all_slices[all_slices["slice_type"] == "regime"].copy()

    def table(headers: list[str], rows: list[list[str]]) -> str:
        lines = [
            "| " + " | ".join(headers) + " |",
            "| " + " | ".join("---" for _ in headers) + " |",
        ]
        lines.extend("| " + " | ".join(row) + " |" for row in rows)
        return "\n".join(lines)

    headline_rows = []
    for _, row in headline.sort_values(["run_id", "model_name"]).iterrows():
        headline_rows.append(
            [
                row["run_id"],
                row["model_name"],
                f"{int(row['n_population']):,}",
                f"{int(row['n_quantity_scored']):,}",
                _fmt_pct(row["hit20"]),
                _fmt_pct(row["hit30"]),
                _fmt_pct(row["wmape"]),
                _fmt_pct(row["bias_pct"]),
                _fmt_pct(row["phantom_rate"]),
            ]
        )

    regime_rows = []
    summary = (
        regime[regime["model_name"] == "median_naive"]
        .sort_values(["run_id", "slice_value"])
    )
    for _, row in summary.iterrows():
        regime_rows.append(
            [
                row["run_id"],
                row["slice_value"],
                f"{int(row['n_population']):,}",
                f"{int(row['n_quantity_scored']):,}",
                _fmt_pct(row["hit20"]),
                _fmt_pct(row["wmape"]),
                _fmt_pct(row["phantom_rate"]),
            ]
        )

    return "\n".join(
        [
            "# Iteration 5A — V2 Naive Benchmark Scorecard",
            "",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            "Runs: " + ", ".join(f"`{run_id}`" for run_id in run_ids),
            "",
            "## Headline Forecastable Revenue Movers",
            "",
            table(
                ["Run", "Model", "Eligible", "Qty scored", "Hit +/-20", "Hit +/-30", "WMAPE", "Bias", "Phantom rate"],
                headline_rows,
            ),
            "",
            "## Median Naive By Regime",
            "",
            table(
                ["Run", "Regime", "Population", "Qty scored", "Hit +/-20", "WMAPE", "Phantom rate"],
                regime_rows,
            ),
            "",
            "## Notes",
            "",
            "- This is a v2-native chain-level benchmark, not a legacy Iter 3/4 comparison.",
            "- Regime labels are recomputed with only data before each target window.",
            "- Quantity hit metrics use material actual windows only: `actual_units >= 4`.",
            "- Zero-heavy regimes should be judged by phantom/zero behavior, not headline hit rate.",
        ]
    ) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run forecast v2 naive benchmark scorecard.")
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument(
        "--target-start",
        action="append",
        required=True,
        help="Monday start of a 4-week target window. Can be passed multiple times.",
    )
    parser.add_argument("--model-label", default="v2_naive")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args()

    all_slices: list[pd.DataFrame] = []
    run_ids: list[str] = []
    conn = sqlite3.connect(args.db)
    try:
        ensure_scorecard_tables(conn)
        for target_start in args.target_start:
            run_id, slices = run_naive_scorecard(
                conn,
                target_start,
                model_label=args.model_label,
                persist=not args.no_write,
            )
            run_ids.append(run_id)
            all_slices.append(slices)
    finally:
        conn.close()

    combined = pd.concat(all_slices, ignore_index=True) if all_slices else pd.DataFrame()
    report = build_report(combined, run_ids)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report, encoding="utf-8")
    print(report)
    print(f"Wrote {args.report}")


if __name__ == "__main__":
    main()
