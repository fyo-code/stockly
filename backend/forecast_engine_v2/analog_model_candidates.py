"""Phase 7C analog/neighbor candidates for forecast engine v2.

This tests a different method from the global sklearn regressors: for each
regular mover, find similar historical SKU-window snapshots from earlier
target windows and use their realized outcomes to adjust the forecast.
"""

from __future__ import annotations

import argparse
import sqlite3
from collections import Counter
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from .feature_matrix import CATEGORICAL_FEATURES, DEFAULT_TARGET_STARTS, NUMERIC_FEATURES, build_feature_matrix
    from .route_labels import ROUTE_ORDER, ROUTE_VERSION, add_route_labels
    from .scorecard import DB_PATH, ScorecardConfig, build_slices, score_model_predictions_fast
    from .sklearn_direct_model import (
        TARGET_COL,
        _actuals_for_score,
        _apply_postprocess,
        _baseline_predictions,
        _cap_post_bf_predictions,
        _fit_pipeline,
        _labels_for_score,
        _model_registry,
        _post_bf_safe_naive,
        _prediction_frame,
        _tune_postprocess,
    )
except ImportError:  # Allows direct script execution.
    from feature_matrix import CATEGORICAL_FEATURES, DEFAULT_TARGET_STARTS, NUMERIC_FEATURES, build_feature_matrix
    from route_labels import ROUTE_ORDER, ROUTE_VERSION, add_route_labels
    from scorecard import DB_PATH, ScorecardConfig, build_slices, score_model_predictions_fast
    from sklearn_direct_model import (
        TARGET_COL,
        _actuals_for_score,
        _apply_postprocess,
        _baseline_predictions,
        _cap_post_bf_predictions,
        _fit_pipeline,
        _labels_for_score,
        _model_registry,
        _post_bf_safe_naive,
        _prediction_frame,
        _tune_postprocess,
    )


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REPORT = PROJECT_ROOT / "active_docs" / "ITER5G_V2_ANALOG_MODEL_CANDIDATES.md"
CONTROL_MODEL = "sk_blend_post_bf_safe"
REGULAR_ROUTES = {"available_regular", "proxy_available_regular"}
ANALOG_FEATURES = [
    "median_naive",
    "last4",
    "roll8_mean",
    "roll13_mean",
    "seasonal52",
    "pos_units_4w",
    "pos_units_13w",
    "pos_units_52w",
    "revenue_13w",
    "revenue_52w",
    "transactions_13w",
    "active_weeks_52",
    "active_4w_windows_52",
    "avg_units_per_4w_52",
    "monthly_cv_104",
    "top3_month_unit_share_104",
    "max_stores_selling_13w",
    "max_hyperstores_selling_13w",
    "avg_unit_price_13w",
    "avg_discount_13w",
    "return_rate_units_13w",
    "online_txn_share_13w",
    "outlet_txn_share_13w",
    "target_month",
    "target_quarter",
    "target_is_q4",
    "target_is_black_friday_month",
    "target_is_bf_window",
    "target_is_pre_bf_4w",
    "target_is_post_bf_4w",
    "bf_unit_share_4w",
    "bf_txn_share_13w",
    "stock_observed_prev_month",
    "stock_prev_month_qty",
    "stock_coverage_ratio_13w",
    "stores_with_stock_prev_month",
]
LOG_FEATURES = {
    "median_naive",
    "last4",
    "roll8_mean",
    "roll13_mean",
    "seasonal52",
    "pos_units_4w",
    "pos_units_13w",
    "pos_units_52w",
    "revenue_13w",
    "revenue_52w",
    "transactions_13w",
    "avg_units_per_4w_52",
    "max_stores_selling_13w",
    "max_hyperstores_selling_13w",
    "avg_unit_price_13w",
    "stock_prev_month_qty",
    "stock_coverage_ratio_13w",
    "stores_with_stock_prev_month",
}


def _fmt_pct(value: object) -> str:
    if value is None or pd.isna(value):
        return "-"
    return f"{float(value) * 100:.1f}%"


def _fmt_pp(value: object) -> str:
    if value is None or pd.isna(value):
        return "-"
    return f"{float(value) * 100:+.1f}pp"


def _fmt_num(value: object, digits: int = 1) -> str:
    if value is None or pd.isna(value):
        return "-"
    return f"{float(value):,.{digits}f}"


def _table(headers: list[str], rows: list[list[str]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(lines)


def _chronological_target_starts(target_starts: list[str]) -> list[str]:
    parsed = [(pd.Timestamp(value), value) for value in target_starts]
    return [value for _, value in sorted(parsed, key=lambda item: item[0])]


def _metrics(group: pd.DataFrame) -> dict[str, object]:
    scored = group[group["quantity_scored"] == 1]
    actual_sum = float(scored["actual_units"].sum())
    zero_actual = group[group["actual_units"] == 0]
    return {
        "rows": int(len(group)),
        "scored": int(len(scored)),
        "actual_units": actual_sum,
        "pred_units": float(scored["pred_units"].sum()),
        "hit20": float(scored["hit20"].mean()) if not scored.empty else None,
        "hit30": float(scored["hit30"].mean()) if not scored.empty else None,
        "wmape": float(scored["abs_error"].sum() / actual_sum) if actual_sum > 0 else None,
        "bias": float(scored["signed_error"].sum() / actual_sum) if actual_sum > 0 else None,
        "phantom_rate": float(zero_actual["phantom"].mean()) if len(zero_actual) else None,
    }


def _route_cols(frame: pd.DataFrame) -> list[str]:
    candidates = [
        "sku_id",
        "target_start",
        "primary_route",
        "availability_confidence",
        "intermittency_bucket",
        "route_signal_status",
    ]
    return [col for col in candidates if col in frame.columns]


def _base_prediction_frames(
    train: pd.DataFrame,
    eval_frame: pd.DataFrame,
    random_state: int,
    config: ScorecardConfig,
) -> tuple[dict[str, np.ndarray], list[pd.DataFrame]]:
    x_train = train[NUMERIC_FEATURES + CATEGORICAL_FEATURES]
    y_train = train[TARGET_COL].to_numpy(dtype=float)
    x_eval = eval_frame[NUMERIC_FEATURES + CATEGORICAL_FEATURES]
    pred_map: dict[str, np.ndarray] = {
        "median_naive": eval_frame["median_naive"].fillna(0.0).clip(lower=0.0).to_numpy(dtype=float),
    }
    predictions: list[pd.DataFrame] = []

    fitted_eval: dict[str, np.ndarray] = {}
    for model_name, estimator in _model_registry(random_state).items():
        pipeline = _fit_pipeline(estimator)
        pipeline.fit(x_train, y_train)
        raw_train_pred = np.clip(pipeline.predict(x_train), 0.0, None)
        post = _tune_postprocess(y_train, raw_train_pred, config.material_units_threshold)
        raw_eval_pred = np.clip(pipeline.predict(x_eval), 0.0, None)
        eval_pred = _apply_postprocess(raw_eval_pred, post)
        fitted_eval[model_name] = eval_pred
        pred_map[model_name] = eval_pred
        predictions.append(_prediction_frame(model_name, eval_frame, eval_pred))

    pred_map["sk_blend_median"] = np.nanmedian(
        np.vstack([fitted_eval["sk_hgb_poisson"], fitted_eval["sk_extra_trees"], pred_map["median_naive"]]),
        axis=0,
    )
    predictions.append(_prediction_frame("sk_blend_median", eval_frame, pred_map["sk_blend_median"]))

    pred_map["post_bf_safe_naive"] = _post_bf_safe_naive(eval_frame)
    predictions.append(_prediction_frame("post_bf_safe_naive", eval_frame, pred_map["post_bf_safe_naive"]))

    pred_map[CONTROL_MODEL] = np.nanmedian(
        np.vstack(
            [
                _cap_post_bf_predictions(fitted_eval["sk_hgb_poisson"], eval_frame),
                _cap_post_bf_predictions(fitted_eval["sk_extra_trees"], eval_frame),
                pred_map["post_bf_safe_naive"],
            ]
        ),
        axis=0,
    )
    predictions.append(_prediction_frame(CONTROL_MODEL, eval_frame, pred_map[CONTROL_MODEL]))
    return pred_map, predictions


def _prepare_analog_features(train: pd.DataFrame, eval_frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    features = [feature for feature in ANALOG_FEATURES if feature in train.columns and feature in eval_frame.columns]
    train_x = train[features].apply(pd.to_numeric, errors="coerce")
    eval_x = eval_frame[features].apply(pd.to_numeric, errors="coerce")
    medians = train_x.median(numeric_only=True).fillna(0.0)
    train_x = train_x.fillna(medians).fillna(0.0)
    eval_x = eval_x.fillna(medians).fillna(0.0)

    for feature in features:
        if feature in LOG_FEATURES:
            train_x[feature] = np.log1p(train_x[feature].clip(lower=0.0))
            eval_x[feature] = np.log1p(eval_x[feature].clip(lower=0.0))

    means = train_x.mean()
    stds = train_x.std().replace(0.0, 1.0).fillna(1.0)
    return (train_x - means) / stds, (eval_x - means) / stds, features


def _pool_for_row(train: pd.DataFrame, row: pd.Series) -> tuple[pd.Index, str]:
    regular_train = train[train["primary_route"].isin(REGULAR_ROUTES)]
    if regular_train.empty:
        return train.index, "all_train_fallback"

    family = row.get("product_family_v2")
    if pd.notna(family):
        pool = regular_train[regular_train["product_family_v2"] == family].index
        if len(pool) >= 25:
            return pool, "product_family"

    category = row.get("category_norm")
    if pd.notna(category):
        pool = regular_train[regular_train["category_norm"] == category].index
        if len(pool) >= 50:
            return pool, "category"

    if len(regular_train) >= 100:
        return regular_train.index, "regular_global"
    return train.index, "all_train_fallback"


def _analog_regular_predictions(
    train: pd.DataFrame,
    eval_frame: pd.DataFrame,
    control_pred: np.ndarray,
    k_neighbors: int,
) -> tuple[dict[str, np.ndarray], Counter[str]]:
    train_x, eval_x, features = _prepare_analog_features(train, eval_frame)
    del features

    ratio_pred = np.full(len(eval_frame), np.nan, dtype=float)
    residual_pred = np.full(len(eval_frame), np.nan, dtype=float)
    units_pred = np.full(len(eval_frame), np.nan, dtype=float)
    source_counts: Counter[str] = Counter()
    regular_mask = eval_frame["primary_route"].isin(REGULAR_ROUTES).to_numpy(dtype=bool)

    train_actual = train[TARGET_COL].fillna(0.0).to_numpy(dtype=float)
    train_naive = train["median_naive"].fillna(0.0).clip(lower=0.0).to_numpy(dtype=float)
    eval_naive = eval_frame["median_naive"].fillna(0.0).clip(lower=0.0).to_numpy(dtype=float)

    for pos, (idx, row) in enumerate(eval_frame.iterrows()):
        if not regular_mask[pos]:
            continue
        pool_idx, source = _pool_for_row(train, row)
        if len(pool_idx) == 0:
            continue
        source_counts[source] += 1
        pool_positions = train.index.get_indexer(pool_idx)
        pool_positions = pool_positions[pool_positions >= 0]
        if len(pool_positions) == 0:
            continue
        row_x = eval_x.loc[idx].to_numpy(dtype=float)
        pool_x = train_x.iloc[pool_positions].to_numpy(dtype=float)
        distances = np.square(pool_x - row_x).sum(axis=1)
        take = min(k_neighbors, len(pool_positions))
        nearest_local = np.argpartition(distances, take - 1)[:take]
        nearest_positions = pool_positions[nearest_local]
        neighbor_actual = train_actual[nearest_positions]
        neighbor_naive = train_naive[nearest_positions]

        units = float(np.median(neighbor_actual))
        ratios = np.divide(neighbor_actual, np.maximum(neighbor_naive, 1.0))
        ratio = float(np.median(np.clip(ratios, 0.0, 3.0)))
        residual = float(np.median(neighbor_actual - neighbor_naive))
        ratio_value = eval_naive[pos] * ratio
        if eval_naive[pos] < 1.0:
            ratio_value = max(ratio_value, units * 0.50)

        units_pred[pos] = units
        ratio_pred[pos] = ratio_value
        residual_pred[pos] = max(eval_naive[pos] + residual, 0.0)

    outputs: dict[str, np.ndarray] = {}
    for model_name, values in {
        "analog_regular_units": units_pred,
        "analog_regular_ratio": ratio_pred,
        "analog_regular_residual": residual_pred,
    }.items():
        pred = control_pred.copy()
        use = regular_mask & ~np.isnan(values)
        pred[use] = values[use]
        outputs[model_name] = np.clip(pred, 0.0, None)

    blend_values = np.nanmedian(np.vstack([units_pred, ratio_pred, residual_pred, control_pred]), axis=0)
    blend = control_pred.copy()
    use_blend = regular_mask & ~np.isnan(blend_values)
    blend[use_blend] = blend_values[use_blend]
    outputs["analog_regular_blend"] = np.clip(blend, 0.0, None)
    return outputs, source_counts


def run_analog_candidates(
    conn: sqlite3.Connection,
    target_starts: list[str],
    min_train_windows: int,
    random_state: int,
    k_neighbors: int,
    config: ScorecardConfig | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, list[str], list[dict[str, object]]]:
    config = config or ScorecardConfig()
    target_starts = _chronological_target_starts(target_starts)
    matrix = build_feature_matrix(conn, target_starts=target_starts, population="headline", config=config)
    matrix = add_route_labels(matrix)

    all_score_rows: list[pd.DataFrame] = []
    skipped: list[str] = []
    diagnostics: list[dict[str, object]] = []

    for target_start in target_starts:
        target_ts = pd.Timestamp(target_start)
        target_starts_series = pd.to_datetime(matrix["target_start"])
        non_overlapping_train = target_starts_series + pd.Timedelta(weeks=config.horizon_weeks) <= target_ts
        train = matrix[non_overlapping_train].copy()
        eval_frame = matrix[matrix["target_start"] == target_start].copy()
        if train["target_start"].nunique() < min_train_windows or eval_frame.empty:
            skipped.append(target_start)
            continue

        pred_map, predictions = _base_prediction_frames(train, eval_frame, random_state, config)
        analog_preds, source_counts = _analog_regular_predictions(
            train=train,
            eval_frame=eval_frame,
            control_pred=pred_map[CONTROL_MODEL],
            k_neighbors=k_neighbors,
        )
        for model_name, pred in analog_preds.items():
            predictions.append(_prediction_frame(model_name, eval_frame, pred))

        run_id = f"analog_candidates_v1_{target_start}"
        score_rows, _ = score_model_predictions_fast(
            _labels_for_score(eval_frame),
            pd.concat(predictions, ignore_index=True),
            _actuals_for_score(eval_frame),
            run_id,
            config=config,
            baseline_predictions=_baseline_predictions(eval_frame),
        )
        score_rows["target_start"] = target_start
        score_rows = score_rows.merge(eval_frame[_route_cols(eval_frame)], on=["sku_id", "target_start"], how="left")
        all_score_rows.append(score_rows)
        diagnostics.append(
            {
                "target_start": target_start,
                "train_windows": int(train["target_start"].nunique()),
                "eval_rows": int(len(eval_frame)),
                "regular_eval_rows": int(eval_frame["primary_route"].isin(REGULAR_ROUTES).sum()),
                "analog_sources": dict(source_counts),
            }
        )

    combined_rows = pd.concat(all_score_rows, ignore_index=True) if all_score_rows else pd.DataFrame()
    if combined_rows.empty:
        aggregate_slices = pd.DataFrame()
    else:
        aggregate_rows = combined_rows.copy()
        aggregate_rows["sku_id"] = aggregate_rows["run_id"].astype(str) + "|" + aggregate_rows["sku_id"].astype(str)
        aggregate_rows["run_id"] = "aggregate"
        aggregate_slices = build_slices(aggregate_rows, "aggregate")
    return matrix, combined_rows, aggregate_slices, skipped, diagnostics


def _model_metrics(score_rows: pd.DataFrame) -> list[dict[str, object]]:
    if score_rows.empty or "model_name" not in score_rows.columns:
        return []
    rows: list[dict[str, object]] = []
    for model_name, group in score_rows.groupby("model_name"):
        rows.append({"model_name": str(model_name), **_metrics(group)})
    rows.sort(
        key=lambda row: (
            -1.0 if row["hit20"] is None else float(row["hit20"]),
            -1.0 if row["hit30"] is None else float(row["hit30"]),
            float("-inf") if row["wmape"] is None else -float(row["wmape"]),
            float("-inf") if row["phantom_rate"] is None else -float(row["phantom_rate"]),
        ),
        reverse=True,
    )
    return rows


def _model_rows(score_rows: pd.DataFrame, control_hit20: float | None) -> list[list[str]]:
    rows = []
    for metrics in _model_metrics(score_rows):
        delta = None if metrics["hit20"] is None or control_hit20 is None else float(metrics["hit20"]) - control_hit20
        rows.append(
            [
                str(metrics["model_name"]),
                f"{int(metrics['rows']):,}",
                f"{int(metrics['scored']):,}",
                _fmt_pct(metrics["hit20"]),
                _fmt_pp(delta),
                _fmt_pct(metrics["hit30"]),
                _fmt_pct(metrics["wmape"]),
                _fmt_pct(metrics["bias"]),
                _fmt_pct(metrics["phantom_rate"]),
            ]
        )
    return rows


def _best_phase_model(model_metrics: list[dict[str, object]], control_hit20: float | None) -> str:
    """Promote only analog candidates that beat the control on raw hit +/-20."""

    if control_hit20 is None:
        return CONTROL_MODEL
    analog_candidates = [
        row
        for row in model_metrics
        if str(row["model_name"]).startswith("analog_regular_")
        and row["hit20"] is not None
        and float(row["hit20"]) > control_hit20
    ]
    if not analog_candidates:
        return CONTROL_MODEL
    analog_candidates.sort(
        key=lambda row: (
            float(row["hit20"]),
            -1.0 if row["hit30"] is None else float(row["hit30"]),
            float("-inf") if row["wmape"] is None else -float(row["wmape"]),
            float("-inf") if row["phantom_rate"] is None else -float(row["phantom_rate"]),
        ),
        reverse=True,
    )
    return str(analog_candidates[0]["model_name"])


def _route_rows(score_rows: pd.DataFrame, model_name: str) -> list[list[str]]:
    rows = []
    model_rows = score_rows[score_rows["model_name"] == model_name]
    for route in [route for route in ROUTE_ORDER if route in set(model_rows["primary_route"])]:
        metrics = _metrics(model_rows[model_rows["primary_route"] == route])
        rows.append(
            [
                route,
                f"{metrics['rows']:,}",
                f"{metrics['scored']:,}",
                _fmt_pct(metrics["hit20"]),
                _fmt_pct(metrics["hit30"]),
                _fmt_pct(metrics["wmape"]),
                _fmt_pct(metrics["bias"]),
                _fmt_pct(metrics["phantom_rate"]),
            ]
        )
    return rows


def _regular_slice_metrics(score_rows: pd.DataFrame, model_name: str) -> dict[str, object]:
    return _metrics(
        score_rows[(score_rows["model_name"] == model_name) & score_rows["primary_route"].isin(REGULAR_ROUTES)]
    )


def _diagnostic_rows(diagnostics: list[dict[str, object]]) -> list[list[str]]:
    rows = []
    for diag in diagnostics:
        sources = diag.get("analog_sources") or {}
        source_text = ", ".join(f"{key}:{value}" for key, value in sorted(sources.items())) or "-"
        rows.append(
            [
                str(diag["target_start"]),
                str(diag["train_windows"]),
                f"{int(diag['eval_rows']):,}",
                f"{int(diag['regular_eval_rows']):,}",
                source_text,
            ]
        )
    return rows


def build_report(
    matrix: pd.DataFrame,
    score_rows: pd.DataFrame,
    aggregate_slices: pd.DataFrame,
    skipped: list[str],
    diagnostics: list[dict[str, object]],
    k_neighbors: int,
) -> str:
    del aggregate_slices
    if score_rows.empty or "model_name" not in score_rows.columns:
        return "\n".join(
            [
                "# Iteration 5G — V2 Analog Model Candidates",
                "",
                f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                f"Route version: `{ROUTE_VERSION}`",
                "",
                "Accuracy rerun: no scorable windows. All requested windows were skipped.",
                "",
                "## Skipped Windows",
                "",
                ", ".join(f"`{window}`" for window in skipped) if skipped else "None.",
                "",
            ]
        )

    control_metrics = _metrics(score_rows[score_rows["model_name"] == CONTROL_MODEL])
    control_hit20 = None if control_metrics["hit20"] is None else float(control_metrics["hit20"])
    model_metrics = _model_metrics(score_rows)
    best_model = _best_phase_model(model_metrics, control_hit20)
    best_metrics = _metrics(score_rows[score_rows["model_name"] == best_model])
    regular_control = _regular_slice_metrics(score_rows, CONTROL_MODEL)
    regular_best = _regular_slice_metrics(score_rows, best_model)

    if best_metrics["hit20"] is None:
        verdict = "Phase 7C did not produce a scorable candidate."
    elif best_model == CONTROL_MODEL:
        verdict = "Phase 7C did not beat the Phase 6 control on hit +/-20. Do not promote the analog candidate."
    else:
        verdict = (
            f"Phase 7C improved headline hit +/-20 by "
            f"{_fmt_pp(float(best_metrics['hit20']) - float(control_metrics['hit20']))} versus the Phase 6 control."
        )

    return "\n".join(
        [
            "# Iteration 5G — V2 Analog Model Candidates",
            "",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"Route version: `{ROUTE_VERSION}`",
            "",
            "## Phase Checkpoint",
            "",
            "Phase completed: Phase 7C — Analog/neighbor candidates",
            "",
            "What changed: tested local-neighbor predictions for available/proxy-regular movers.",
            "",
            f"Accuracy rerun: yes. Analog candidates used `{k_neighbors}` nearest prior SKU-window neighbors.",
            "",
            _table(
                ["Metric", "Phase 6 control", "Phase 7C best"],
                [
                    ["Best model", CONTROL_MODEL, best_model],
                    ["Hit +/-20", _fmt_pct(control_metrics["hit20"]), _fmt_pct(best_metrics["hit20"])],
                    ["Delta hit +/-20", "-", _fmt_pp(float(best_metrics["hit20"] or 0) - float(control_metrics["hit20"] or 0))],
                    ["Hit +/-30", _fmt_pct(control_metrics["hit30"]), _fmt_pct(best_metrics["hit30"])],
                    ["WMAPE", _fmt_pct(control_metrics["wmape"]), _fmt_pct(best_metrics["wmape"])],
                    ["Phantom rate", _fmt_pct(control_metrics["phantom_rate"]), _fmt_pct(best_metrics["phantom_rate"])],
                ],
            ),
            "",
            "## Aggregate Candidate Results",
            "",
            _table(
                ["Model", "Rows", "Qty scored", "Hit +/-20", "Delta vs control", "Hit +/-30", "WMAPE", "Bias", "Phantom rate"],
                _model_rows(score_rows, control_hit20),
            ),
            "",
            "## Available / Proxy-Regular Slice",
            "",
            _table(
                ["Metric", "Phase 6 control", "Phase 7C best"],
                [
                    ["Qty scored", f"{regular_control['scored']:,}", f"{regular_best['scored']:,}"],
                    ["Hit +/-20", _fmt_pct(regular_control["hit20"]), _fmt_pct(regular_best["hit20"])],
                    ["Delta hit +/-20", "-", _fmt_pp(float(regular_best["hit20"] or 0) - float(regular_control["hit20"] or 0))],
                    ["Hit +/-30", _fmt_pct(regular_control["hit30"]), _fmt_pct(regular_best["hit30"])],
                    ["WMAPE", _fmt_pct(regular_control["wmape"]), _fmt_pct(regular_best["wmape"])],
                    ["Phantom rate", _fmt_pct(regular_control["phantom_rate"]), _fmt_pct(regular_best["phantom_rate"])],
                ],
            ),
            "",
            f"## Route Accuracy — {best_model}",
            "",
            _table(
                ["Route", "Rows", "Qty scored", "Hit +/-20", "Hit +/-30", "WMAPE", "Bias", "Phantom rate"],
                _route_rows(score_rows, best_model),
            ),
            "",
            "## Analog Source Diagnostics",
            "",
            _table(
                ["Target start", "Train windows", "Eval rows", "Regular eval rows", "Analog source counts"],
                _diagnostic_rows(diagnostics),
            ),
            "",
            "## Verdict",
            "",
            verdict,
            "",
            "## Skipped Windows",
            "",
            ", ".join(f"`{window}`" for window in skipped) if skipped else "None.",
            "",
            "## Notes",
            "",
            f"- Matrix rows routed: {len(matrix):,}.",
            "- Neighbor pools use only earlier target windows.",
            "- Analog replacement is limited to `available_regular` and `proxy_available_regular` routes.",
            "- Current snapshot stock remains excluded from historical backtests.",
            "",
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run forecast v2 analog model candidates.")
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--target-start", action="append", default=None)
    parser.add_argument("--min-train-windows", type=int, default=4)
    parser.add_argument("--random-state", type=int, default=42)
    parser.add_argument("--k-neighbors", type=int, default=35)
    args = parser.parse_args()

    config = ScorecardConfig()
    conn = sqlite3.connect(args.db)
    try:
        matrix, score_rows, aggregate, skipped, diagnostics = run_analog_candidates(
            conn,
            target_starts=args.target_start or DEFAULT_TARGET_STARTS,
            min_train_windows=args.min_train_windows,
            random_state=args.random_state,
            k_neighbors=args.k_neighbors,
            config=config,
        )
    finally:
        conn.close()

    report = build_report(matrix, score_rows, aggregate, skipped, diagnostics, args.k_neighbors)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report, encoding="utf-8")
    print(report)
    print(f"Wrote {args.report}")


if __name__ == "__main__":
    main()
