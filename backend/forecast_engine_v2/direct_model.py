"""First forecast v2 direct 4-week chain-level model candidate.

This module intentionally avoids optional ML dependencies. It learns a direct
4-week blend and calibration from prior walk-forward windows, then scores the
candidate with the v2 scorecard without persisting millions of experiment rows.
"""

from __future__ import annotations

import argparse
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from .regime_labels import RULE_VERSION, build_regime_labels
    from .scorecard import (
        DB_PATH,
        ScorecardConfig,
        build_actuals,
        build_naive_predictions,
        build_slices,
        score_model_predictions_fast,
    )
except ImportError:  # Allows direct script execution.
    from regime_labels import RULE_VERSION, build_regime_labels
    from scorecard import (
        DB_PATH,
        ScorecardConfig,
        build_actuals,
        build_naive_predictions,
        build_slices,
        score_model_predictions_fast,
    )


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REPORT = PROJECT_ROOT / "active_docs" / "ITER5B_V2_DIRECT_MODEL_FIRST_RUN.md"
MODEL_NAME = "direct_empirical_v1"
BASE_MODEL_COLS = ["last4", "roll13_mean", "seasonal52"]
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


@dataclass(frozen=True)
class EmpiricalModel:
    weights: dict[str, float]
    global_factor: float
    sku_factor: pd.Series
    family_factor: pd.Series
    category_factor: pd.Series
    train_windows: int
    train_rows: int
    train_hit20: float | None
    train_wmape: float | None


def _date(value: pd.Timestamp) -> str:
    return value.strftime("%Y-%m-%d")


def _target_run_id(target_start: str) -> str:
    return f"direct_empirical_v1_{target_start}"


def _fmt_pct(value: object) -> str:
    if value is None or pd.isna(value):
        return "-"
    return f"{float(value) * 100:.1f}%"


def _fmt_num(value: object, digits: int = 1) -> str:
    if value is None or pd.isna(value):
        return "-"
    return f"{float(value):,.{digits}f}"


def _weighted_base(df: pd.DataFrame, weights: dict[str, float]) -> pd.Series:
    base = pd.Series(0.0, index=df.index)
    for col, weight in weights.items():
        base = base + df[col].fillna(0.0).clip(lower=0.0) * weight
    return base.clip(lower=0.0)


def _candidate_weights(step: float = 0.1) -> list[dict[str, float]]:
    steps = int(round(1.0 / step))
    candidates: list[dict[str, float]] = []
    for last4 in range(steps + 1):
        for roll13 in range(steps + 1 - last4):
            seasonal = steps - last4 - roll13
            candidates.append(
                {
                    "last4": last4 / steps,
                    "roll13_mean": roll13 / steps,
                    "seasonal52": seasonal / steps,
                }
            )
    return candidates


def _metric_tuple(actual: pd.Series, pred: pd.Series) -> tuple[float, float, float]:
    scored = actual >= 4.0
    if not scored.any():
        return (0.0, float("inf"), float("inf"))
    scored_actual = actual[scored].astype(float)
    scored_pred = pred[scored].astype(float)
    ape = (scored_pred - scored_actual).abs() / scored_actual
    hit20 = float((ape <= 0.20).mean())
    wmape = float((scored_pred - scored_actual).abs().sum() / scored_actual.sum())
    bias = abs(float((scored_pred - scored_actual).sum() / scored_actual.sum()))
    return (hit20, wmape, bias)


def _load_training_rows(conn: sqlite3.Connection, before_target_start: str) -> pd.DataFrame:
    rows = pd.read_sql_query(
        """
        SELECT
            runs.target_start,
            score.sku_id,
            score.model_name,
            score.actual_units,
            score.pred_units,
            score.headline_eligible,
            score.regime,
            COALESCE(score.category_norm, 'NECUNOSCUT') AS category_norm,
            COALESCE(score.product_family_v2, score.category_norm, 'NECUNOSCUT') AS product_family_v2
        FROM forecast_v2_score_rows AS score
        JOIN forecast_v2_score_runs AS runs
            ON runs.run_id = score.run_id
        WHERE runs.model_label = 'v2_naive_fullgrid'
            AND runs.target_start < ?
            AND score.headline_eligible = 1
            AND score.model_name IN ('last4', 'roll13_mean', 'seasonal52', 'median_naive')
        """,
        conn,
        params=(before_target_start,),
    )
    if rows.empty:
        return rows

    index_cols = [
        "target_start",
        "sku_id",
        "actual_units",
        "headline_eligible",
        "regime",
        "category_norm",
        "product_family_v2",
    ]
    pivoted = (
        rows.pivot_table(
            index=index_cols,
            columns="model_name",
            values="pred_units",
            aggfunc="first",
        )
        .reset_index()
        .rename_axis(columns=None)
    )
    for col in BASE_MODEL_COLS + ["median_naive"]:
        if col not in pivoted.columns:
            pivoted[col] = 0.0
    return pivoted


def _load_labels(conn: sqlite3.Connection, target_start: str) -> pd.DataFrame:
    start = pd.Timestamp(target_start)
    as_of_week = _date(start - pd.Timedelta(weeks=1))
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
    return build_regime_labels(conn, as_of_week)


def _load_eval_naive_predictions(
    conn: sqlite3.Connection,
    labels: pd.DataFrame,
    target_start: str,
    config: ScorecardConfig,
) -> pd.DataFrame:
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
                AND model_name IN ('last4', 'roll13_mean', 'seasonal52', 'median_naive')
            """,
            conn,
            params=(run_id_row[0],),
        )
    else:
        predictions = build_naive_predictions(conn, labels, pd.Timestamp(target_start), config)[
            ["sku_id", "model_name", "pred_units_4w"]
        ]

    pivoted = (
        predictions.pivot_table(
            index="sku_id",
            columns="model_name",
            values="pred_units_4w",
            aggfunc="first",
        )
        .reset_index()
        .rename_axis(columns=None)
    )
    for col in BASE_MODEL_COLS + ["median_naive"]:
        if col not in pivoted.columns:
            pivoted[col] = 0.0
    return pivoted


def _load_actuals(
    conn: sqlite3.Connection,
    labels: pd.DataFrame,
    target_start: str,
    config: ScorecardConfig,
) -> pd.DataFrame:
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


def _choose_weights(train: pd.DataFrame) -> tuple[dict[str, float], float | None, float | None]:
    headline = train[train["headline_eligible"] == 1].copy()
    if headline.empty:
        return {"last4": 1 / 3, "roll13_mean": 1 / 3, "seasonal52": 1 / 3}, None, None

    best: tuple[float, float, float, dict[str, float]] | None = None
    actual = headline["actual_units"].astype(float)
    for weights in _candidate_weights():
        pred = _weighted_base(headline, weights)
        hit20, wmape, bias = _metric_tuple(actual, pred)
        candidate = (hit20, -wmape, -bias, weights)
        if best is None or candidate[:3] > best[:3]:
            best = candidate

    assert best is not None
    weights = best[3]
    hit20, wmape, _ = _metric_tuple(actual, _weighted_base(headline, weights))
    return weights, hit20, wmape


def _group_factor(
    frame: pd.DataFrame,
    key: str,
    global_factor: float,
    prior_units: float,
    min_rows: int,
) -> pd.Series:
    usable = frame[(frame["base_units"] > 0) & (frame["actual_units"] >= 4.0)].copy()
    if usable.empty:
        return pd.Series(dtype=float)
    agg = usable.groupby(key).agg(
        actual_units=("actual_units", "sum"),
        base_units=("base_units", "sum"),
        rows=("sku_id", "count"),
    )
    agg = agg[agg["rows"] >= min_rows]
    if agg.empty:
        return pd.Series(dtype=float)
    factor = (agg["actual_units"] + prior_units * global_factor) / (agg["base_units"] + prior_units)
    return factor.clip(lower=0.35, upper=2.50)


def fit_empirical_model(train: pd.DataFrame) -> EmpiricalModel:
    weights, train_hit20, train_wmape = _choose_weights(train)
    model_train = train[train["headline_eligible"] == 1].copy()
    model_train["base_units"] = _weighted_base(model_train, weights)
    scored = model_train[(model_train["actual_units"] >= 4.0) & (model_train["base_units"] > 0)]
    if scored.empty:
        global_factor = 1.0
    else:
        global_factor = float(scored["actual_units"].sum() / scored["base_units"].sum())
    global_factor = float(np.clip(global_factor, 0.35, 2.50))

    return EmpiricalModel(
        weights=weights,
        global_factor=global_factor,
        sku_factor=_group_factor(model_train, "sku_id", global_factor, prior_units=8.0, min_rows=2),
        family_factor=_group_factor(model_train, "product_family_v2", global_factor, prior_units=25.0, min_rows=8),
        category_factor=_group_factor(model_train, "category_norm", global_factor, prior_units=60.0, min_rows=20),
        train_windows=int(train["target_start"].nunique()),
        train_rows=int(len(model_train)),
        train_hit20=train_hit20,
        train_wmape=train_wmape,
    )


def predict_empirical(labels: pd.DataFrame, naive_wide: pd.DataFrame, model: EmpiricalModel) -> pd.DataFrame:
    frame = labels[
        ["sku_id", "category_norm", "product_family_v2"]
    ].merge(naive_wide, on="sku_id", how="left")
    for col in BASE_MODEL_COLS + ["median_naive"]:
        frame[col] = frame[col].fillna(0.0)

    frame["base_units"] = _weighted_base(frame, model.weights)
    sku_factor = frame["sku_id"].map(model.sku_factor)
    family_factor = frame["product_family_v2"].map(model.family_factor)
    category_factor = frame["category_norm"].map(model.category_factor)
    fallback = pd.Series(model.global_factor, index=frame.index)

    factor = fallback.copy()
    has_category = category_factor.notna()
    factor.loc[has_category] = 0.65 * category_factor.loc[has_category] + 0.35 * model.global_factor
    has_family = family_factor.notna()
    factor.loc[has_family] = (
        0.65 * family_factor.loc[has_family]
        + 0.25 * category_factor.loc[has_family].fillna(model.global_factor)
        + 0.10 * model.global_factor
    )
    has_sku = sku_factor.notna()
    factor.loc[has_sku] = (
        0.55 * sku_factor.loc[has_sku]
        + 0.25 * family_factor.loc[has_sku].fillna(model.global_factor)
        + 0.15 * category_factor.loc[has_sku].fillna(model.global_factor)
        + 0.05 * model.global_factor
    )

    frame["pred_units_4w"] = (frame["base_units"] * factor.clip(lower=0.20, upper=3.00)).clip(lower=0.0)
    return pd.DataFrame(
        {
            "model_name": MODEL_NAME,
            "sku_id": frame["sku_id"],
            "pred_units_4w": frame["pred_units_4w"],
            "prediction_source": "v2_direct_empirical_walk_forward",
            "model_version": "direct_empirical_v1_2026_05_12",
        }
    )


def _baseline_predictions(naive_wide: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "model_name": "median_naive",
            "sku_id": naive_wide["sku_id"],
            "pred_units_4w": naive_wide["median_naive"].fillna(0.0).clip(lower=0.0),
            "prediction_source": "v2_naive_chain_weekly",
            "model_version": "v2_naive_2026_05_11",
        }
    )


def _table(headers: list[str], rows: list[list[str]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(lines)


def build_report(
    per_window_slices: pd.DataFrame,
    aggregate_slices: pd.DataFrame,
    model_fits: dict[str, EmpiricalModel],
    skipped: list[str],
) -> str:
    headline = per_window_slices[
        (per_window_slices["slice_type"] == "headline")
        & (per_window_slices["slice_value"] == "forecastable_revenue_movers")
        & (per_window_slices["model_name"].isin([MODEL_NAME, "median_naive"]))
    ].copy()

    rows = []
    for _, row in headline.sort_values(["run_id", "model_name"]).iterrows():
        fit = model_fits.get(str(row["run_id"]))
        rows.append(
            [
                str(row["run_id"]).replace("direct_empirical_v1_", ""),
                str(row["model_name"]),
                f"{int(row['n_population']):,}",
                f"{int(row['n_quantity_scored']):,}",
                _fmt_pct(row["hit20"]),
                _fmt_pct(row["hit30"]),
                _fmt_pct(row["wmape"]),
                _fmt_pct(row["bias_pct"]),
                _fmt_pct(row["phantom_rate"]),
                _fmt_pct(row["winrate_vs_median_naive"]) if row["model_name"] == MODEL_NAME else "-",
                str(fit.train_windows) if fit and row["model_name"] == MODEL_NAME else "-",
            ]
        )

    aggregate = aggregate_slices[
        (aggregate_slices["slice_type"] == "headline")
        & (aggregate_slices["slice_value"] == "forecastable_revenue_movers")
        & (aggregate_slices["model_name"].isin([MODEL_NAME, "median_naive"]))
    ].copy()
    aggregate_rows = []
    for _, row in aggregate.sort_values("model_name").iterrows():
        aggregate_rows.append(
            [
                str(row["model_name"]),
                f"{int(row['n_population']):,}",
                f"{int(row['n_quantity_scored']):,}",
                _fmt_pct(row["hit20"]),
                _fmt_pct(row["hit30"]),
                _fmt_pct(row["wmape"]),
                _fmt_pct(row["bias_pct"]),
                _fmt_pct(row["phantom_rate"]),
                _fmt_pct(row["winrate_vs_median_naive"]) if row["model_name"] == MODEL_NAME else "-",
            ]
        )

    fit_rows = []
    for run_id, fit in sorted(model_fits.items()):
        fit_rows.append(
            [
                run_id.replace("direct_empirical_v1_", ""),
                str(fit.train_windows),
                f"{fit.train_rows:,}",
                ", ".join(f"{name}={weight:.1f}" for name, weight in fit.weights.items() if weight > 0),
                _fmt_num(fit.global_factor, 2),
                _fmt_pct(fit.train_hit20),
                _fmt_pct(fit.train_wmape),
            ]
        )

    return "\n".join(
        [
            "# Iteration 5B — V2 Direct Model First Run",
            "",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            "## Result",
            "",
            _table(
                [
                    "Model",
                    "Eligible",
                    "Qty scored",
                    "Hit +/-20",
                    "Hit +/-30",
                    "WMAPE",
                    "Bias",
                    "Phantom rate",
                    "Winrate vs median",
                ],
                aggregate_rows,
            ),
            "",
            "## Per-Window Headline Scores",
            "",
            _table(
                [
                    "Target start",
                    "Model",
                    "Eligible",
                    "Qty scored",
                    "Hit +/-20",
                    "Hit +/-30",
                    "WMAPE",
                    "Bias",
                    "Phantom rate",
                    "Winrate vs median",
                    "Train windows",
                ],
                rows,
            ),
            "",
            "## Learned Model Per Window",
            "",
            _table(
                ["Target start", "Train windows", "Train rows", "Blend", "Global factor", "Train hit +/-20", "Train WMAPE"],
                fit_rows,
            ),
            "",
            "## Skipped Windows",
            "",
            ", ".join(f"`{window}`" for window in skipped) if skipped else "None.",
            "",
            "## Notes",
            "",
            "- This is a direct 4-week chain-level candidate, but not the final LightGBM-style model.",
            "- It learns only from prior walk-forward windows, so each scored target remains blind.",
            "- The model uses a weighted direct blend of `last4`, `roll13_mean`, and `seasonal52`, then applies shrinkage-calibrated SKU/family/category factors.",
            "- The fast score path avoids writing row-level experiment results to SQLite. Persist only official finalists.",
            "- The local environment currently has pandas/numpy, but no sklearn, and LightGBM imports through an unstable NumPy/matplotlib ABI path. This run therefore uses the dependency-free empirical model.",
        ]
    ) + "\n"


def run_direct_model(
    conn: sqlite3.Connection,
    target_starts: list[str],
    min_train_windows: int,
    config: ScorecardConfig | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, EmpiricalModel], list[str]]:
    config = config or ScorecardConfig()
    all_slices: list[pd.DataFrame] = []
    all_score_rows: list[pd.DataFrame] = []
    model_fits: dict[str, EmpiricalModel] = {}
    skipped: list[str] = []

    for target_start in target_starts:
        train = _load_training_rows(conn, target_start)
        if train["target_start"].nunique() < min_train_windows:
            skipped.append(target_start)
            continue

        labels = _load_labels(conn, target_start)
        naive_wide = _load_eval_naive_predictions(conn, labels, target_start, config)
        actuals = _load_actuals(conn, labels, target_start, config)
        model = fit_empirical_model(train)
        predictions = predict_empirical(labels, naive_wide, model)
        baseline = _baseline_predictions(naive_wide)
        run_id = _target_run_id(target_start)
        score_rows, slices = score_model_predictions_fast(
            labels,
            predictions,
            actuals,
            run_id,
            config=config,
            baseline_predictions=baseline,
        )
        all_score_rows.append(score_rows)
        all_slices.append(slices)
        model_fits[run_id] = model

    combined_rows = pd.concat(all_score_rows, ignore_index=True) if all_score_rows else pd.DataFrame()
    combined_slices = pd.concat(all_slices, ignore_index=True) if all_slices else pd.DataFrame()
    if combined_rows.empty:
        aggregate_slices = pd.DataFrame()
    else:
        aggregate_rows = combined_rows.copy()
        aggregate_rows["sku_id"] = aggregate_rows["run_id"].astype(str) + "|" + aggregate_rows["sku_id"].astype(str)
        aggregate_rows["run_id"] = "aggregate"
        aggregate_slices = build_slices(aggregate_rows, "aggregate")
    return combined_slices, aggregate_slices, model_fits, skipped


def main() -> None:
    parser = argparse.ArgumentParser(description="Run forecast v2 direct empirical model.")
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--target-start", action="append", default=None)
    parser.add_argument("--min-train-windows", type=int, default=4)
    args = parser.parse_args()

    target_starts = args.target_start or DEFAULT_TARGET_STARTS
    conn = sqlite3.connect(args.db)
    try:
        slices, aggregate, model_fits, skipped = run_direct_model(
            conn,
            target_starts=target_starts,
            min_train_windows=args.min_train_windows,
        )
    finally:
        conn.close()

    report = build_report(slices, aggregate, model_fits, skipped)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report, encoding="utf-8")
    print(report)
    print(f"Wrote {args.report}")


if __name__ == "__main__":
    main()
