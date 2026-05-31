"""Scikit-learn direct 4-week chain-level models for forecast engine v2."""

from __future__ import annotations

import argparse
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import ExtraTreesRegressor, HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OrdinalEncoder

try:
    from .feature_matrix import (
        CATEGORICAL_FEATURES,
        DEFAULT_TARGET_STARTS,
        NUMERIC_FEATURES,
        build_feature_matrix,
    )
    from .route_labels import add_route_labels
    from .scorecard import DB_PATH, ScorecardConfig, build_slices, score_model_predictions_fast
except ImportError:  # Allows direct script execution.
    from feature_matrix import CATEGORICAL_FEATURES, DEFAULT_TARGET_STARTS, NUMERIC_FEATURES, build_feature_matrix
    from route_labels import add_route_labels
    from scorecard import DB_PATH, ScorecardConfig, build_slices, score_model_predictions_fast


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REPORT = PROJECT_ROOT / "active_docs" / "ITER5N_V2_PHASE8E_AVAILABILITY_MODEL.md"
TARGET_COL = "actual_pos_units_4w"
HIGH_REVENUE_CHAMPION_MODEL = "8gf_regular_plus_post_bf_safe"
HIGH_REVENUE_CHAMPION_SOURCE = "v2_high_revenue_policy"
HIGH_REVENUE_CHAMPION_VERSION = "high_revenue_policy_v1_2026_05_24"
HIGH_REVENUE_CALIBRATED_MODEL = "8gj_bfc_nonpost_lift_150"
HIGH_REVENUE_CALIBRATED_SOURCE = "v2_high_revenue_policy"
HIGH_REVENUE_CALIBRATED_VERSION = "high_revenue_policy_v2_2026_05_26"
HIGH_REVENUE_GUARDED_CAMPAIGN_MODEL = "8go_pre_bf_bfc_lift_180"
HIGH_REVENUE_GUARDED_CAMPAIGN_SOURCE = "v2_high_revenue_policy"
HIGH_REVENUE_GUARDED_CAMPAIGN_VERSION = "high_revenue_policy_v3_2026_05_28"
HIGH_REVENUE_POLICY_CHOICES = ["none", "champion", "bfc_lift_150", "pre_bf_bfc_lift_180"]
PHASE8_BASELINE_HIT20 = 0.241
PHASE8_BASELINE_HIT30 = 0.353
PHASE8_BASELINE_WMAPE = 0.561
PHASE8_BASELINE_PHANTOM = 0.481

LABEL_COLUMNS = [
    "as_of_week",
    "horizon_start",
    "horizon_end",
    "rule_version",
    "sku_id",
    "regime",
    "headline_eligible",
    "business_target_eligible",
    "scoring_policy",
    "trailing_52w_revenue",
    "trailing_52w_pos_units",
    "active_weeks_52",
    "active_4w_windows_52",
    "avg_units_per_4w_52",
    "revenue_rank",
    "cumulative_revenue_share",
    "is_top_80_revenue",
    "top80_cutoff_revenue",
    "active_months_104",
    "top3_month_unit_share_104",
    "monthly_cv_104",
    "active_years_104",
    "recurring_active_months_104",
    "first_seen_week",
    "last_seen_week",
    "category_norm",
    "product_family_v2",
    "category_signal_status",
    "revenue_bucket",
    "volume_bucket",
    "thresholds_json",
    "created_at",
]

ACTUAL_COLUMNS = [
    "sku_id",
    "target_start",
    "target_end",
    "actual_pos_units_4w",
    "actual_net_units_4w",
    "actual_net_revenue_4w",
    "negative_unit_weeks",
    "bf_txn_count",
    "bf_observed_txn_count",
    "bf_inferred_txn_count",
    "campaign_observed_txn_count",
    "unknown_campaign_label_txn_count",
]

SCORE_ROW_CONTEXT_COLUMNS = [
    "target_start",
    "revenue_rank",
    "trailing_52w_revenue",
    "trailing_52w_pos_units",
    "active_weeks_52",
    "avg_units_per_4w_52",
    "primary_route",
    "stock_position_confidence",
    "availability_route",
    "calendar_route_context",
    "supplier_stock_observed_prev_month",
    "supplier_stock_prev_month_qty",
    "stock_observed_prev_month",
    "stock_prev_month_qty",
    "combined_stock_observed_prev_month",
    "combined_stock_prev_month_qty",
    "campaign_txn_4w",
    "campaign_txn_13w",
    "campaign_units_13w",
    "bf_txn_4w",
    "bf_txn_13w",
    "bf_unit_share_4w",
    "target_is_post_bf_4w",
    "target_is_bf_window",
]


@dataclass(frozen=True)
class Postprocess:
    factor: float
    zero_floor: float
    train_hit20: float | None
    train_wmape: float | None
    train_phantom_rate: float | None


def _fmt_pct(value: object) -> str:
    if value is None or pd.isna(value):
        return "-"
    return f"{float(value) * 100:.1f}%"


def _fmt_num(value: object, digits: int = 2) -> str:
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


def _preprocessor() -> ColumnTransformer:
    numeric_pipe = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
        ]
    )
    categorical_pipe = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            (
                "encoder",
                OrdinalEncoder(
                    handle_unknown="use_encoded_value",
                    unknown_value=-1,
                    encoded_missing_value=-1,
                ),
            ),
        ]
    )
    return ColumnTransformer(
        transformers=[
            ("num", numeric_pipe, NUMERIC_FEATURES),
            ("cat", categorical_pipe, CATEGORICAL_FEATURES),
        ],
        remainder="drop",
    )


def _model_registry(random_state: int) -> dict[str, object]:
    return {
        "sk_hgb_poisson": HistGradientBoostingRegressor(
            loss="poisson",
            max_iter=300,
            learning_rate=0.035,
            max_leaf_nodes=31,
            min_samples_leaf=25,
            l2_regularization=0.05,
            early_stopping=True,
            validation_fraction=0.15,
            random_state=random_state,
        ),
        "sk_hgb_squared": HistGradientBoostingRegressor(
            loss="squared_error",
            max_iter=300,
            learning_rate=0.035,
            max_leaf_nodes=31,
            min_samples_leaf=25,
            l2_regularization=0.05,
            early_stopping=True,
            validation_fraction=0.15,
            random_state=random_state,
        ),
        "sk_extra_trees": ExtraTreesRegressor(
            n_estimators=260,
            min_samples_leaf=8,
            max_features=0.80,
            random_state=random_state,
            n_jobs=-1,
        ),
    }


def _fit_pipeline(estimator: object) -> Pipeline:
    return Pipeline(
        steps=[
            ("preprocess", _preprocessor()),
            ("model", estimator),
        ]
    )


def _apply_postprocess(raw_pred: np.ndarray, post: Postprocess) -> np.ndarray:
    pred = np.clip(raw_pred.astype(float), 0.0, None) * post.factor
    pred[pred < post.zero_floor] = 0.0
    return pred


def _score_arrays(actual: np.ndarray, pred: np.ndarray, material_threshold: float) -> tuple[float | None, float | None, float | None]:
    scored = actual >= material_threshold
    if not scored.any():
        return None, None, None
    scored_actual = actual[scored]
    scored_pred = pred[scored]
    abs_error = np.abs(scored_pred - scored_actual)
    hit20 = float(np.mean(abs_error / scored_actual <= 0.20))
    wmape = float(abs_error.sum() / scored_actual.sum()) if scored_actual.sum() > 0 else None
    zero_actual = actual == 0
    phantom = float(np.mean(pred[zero_actual] >= 1.0)) if zero_actual.any() else None
    return hit20, wmape, phantom


def _tune_postprocess(
    actual: np.ndarray,
    raw_pred: np.ndarray,
    material_threshold: float,
) -> Postprocess:
    best: tuple[float, float, float, float, float, float | None, float | None, float | None] | None = None
    for factor in np.arange(0.50, 1.51, 0.05):
        for zero_floor in (0.0, 0.5, 1.0, 1.5, 2.0, 3.0):
            pred = np.clip(raw_pred, 0.0, None) * factor
            pred[pred < zero_floor] = 0.0
            hit20, wmape, phantom = _score_arrays(actual, pred, material_threshold)
            if hit20 is None:
                continue
            wmape_cmp = wmape if wmape is not None else float("inf")
            phantom_cmp = phantom if phantom is not None else float("inf")
            candidate = (hit20, -phantom_cmp, -wmape_cmp, -abs(1.0 - factor), factor, zero_floor, wmape, phantom)
            if best is None or candidate[:4] > best[:4]:
                best = candidate
    if best is None:
        return Postprocess(1.0, 0.0, None, None, None)
    return Postprocess(
        factor=float(best[4]),
        zero_floor=float(best[5]),
        train_hit20=float(best[0]),
        train_wmape=None if best[6] is None else float(best[6]),
        train_phantom_rate=None if best[7] is None else float(best[7]),
    )


def _baseline_predictions(eval_frame: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "model_name": "median_naive",
            "sku_id": eval_frame["sku_id"],
            "pred_units_4w": eval_frame["median_naive"].fillna(0.0).clip(lower=0.0),
            "prediction_source": "v2_naive_chain_weekly",
            "model_version": "v2_naive_2026_05_11",
        }
    )


def _safe_ratio(num: pd.Series, denom: pd.Series) -> pd.Series:
    return np.where(denom.abs() > 1e-9, num / denom, 0.0)


def _post_bf_safe_naive(eval_frame: pd.DataFrame) -> np.ndarray:
    non_bf_last4 = eval_frame.get("non_bf_pos_units_4w_equiv", pd.Series(0.0, index=eval_frame.index)).fillna(0.0)
    roll13 = eval_frame.get("roll13_mean", pd.Series(0.0, index=eval_frame.index)).fillna(0.0)
    seasonal52 = eval_frame.get("seasonal52", pd.Series(0.0, index=eval_frame.index)).fillna(0.0)
    median_naive = eval_frame.get("median_naive", pd.Series(0.0, index=eval_frame.index)).fillna(0.0)
    safe = np.nanmedian(np.vstack([non_bf_last4, roll13, seasonal52]), axis=0)
    pred = median_naive.to_numpy(dtype=float).copy()
    post_bf = eval_frame.get("target_is_post_bf_4w", pd.Series(0.0, index=eval_frame.index)).fillna(0.0) == 1
    contaminated = eval_frame.get("bf_unit_share_4w", pd.Series(0.0, index=eval_frame.index)).fillna(0.0) > 0
    mask = (post_bf & contaminated).to_numpy(dtype=bool)
    pred[mask] = safe[mask]
    return np.clip(pred, 0.0, None)


def _cap_post_bf_predictions(pred: np.ndarray, eval_frame: pd.DataFrame) -> np.ndarray:
    capped = np.clip(pred.astype(float), 0.0, None).copy()
    safe_naive = _post_bf_safe_naive(eval_frame)
    roll13 = eval_frame.get("roll13_mean", pd.Series(0.0, index=eval_frame.index)).fillna(0.0).to_numpy(dtype=float)
    seasonal52 = eval_frame.get("seasonal52", pd.Series(0.0, index=eval_frame.index)).fillna(0.0).to_numpy(dtype=float)
    cap = np.maximum.reduce([safe_naive, roll13, seasonal52]) * 1.20
    cap = np.maximum(cap, 1.0)
    post_bf = eval_frame.get("target_is_post_bf_4w", pd.Series(0.0, index=eval_frame.index)).fillna(0.0) == 1
    contaminated = eval_frame.get("bf_unit_share_4w", pd.Series(0.0, index=eval_frame.index)).fillna(0.0) > 0
    high_recent_ratio = eval_frame.get("last4_to_roll13", pd.Series(0.0, index=eval_frame.index)).fillna(0.0) > 1.25
    mask = (post_bf & contaminated & high_recent_ratio).to_numpy(dtype=bool)
    capped[mask] = np.minimum(capped[mask], cap[mask])
    return capped


def _labels_for_score(eval_frame: pd.DataFrame) -> pd.DataFrame:
    return eval_frame[[col for col in LABEL_COLUMNS if col in eval_frame.columns]].copy()


def _actuals_for_score(eval_frame: pd.DataFrame) -> pd.DataFrame:
    return eval_frame[[col for col in ACTUAL_COLUMNS if col in eval_frame.columns]].copy()


def _score_row_context(eval_frame: pd.DataFrame) -> pd.DataFrame:
    context_cols = [col for col in SCORE_ROW_CONTEXT_COLUMNS if col in eval_frame.columns]
    context = eval_frame[["sku_id", *context_cols]].copy()
    return context.drop_duplicates(subset=["sku_id"], keep="last")


def _prediction_frame(
    model_name: str,
    eval_frame: pd.DataFrame,
    pred: np.ndarray,
    prediction_source: str = "v2_sklearn_direct",
    model_version: str = "sklearn_direct_v1_2026_05_12",
) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "model_name": model_name,
            "sku_id": eval_frame["sku_id"],
            "pred_units_4w": pred,
            "prediction_source": prediction_source,
            "model_version": model_version,
        }
    )


def _regular_policy_mask(eval_frame: pd.DataFrame) -> np.ndarray:
    routes = eval_frame.get("primary_route", pd.Series("", index=eval_frame.index)).astype(str)
    context = eval_frame.get("calendar_route_context", pd.Series("normal_calendar", index=eval_frame.index)).astype(str)
    return (routes.isin({"available_regular", "proxy_available_regular"}) & (context == "normal_calendar")).to_numpy(dtype=bool)


def _post_bf_stress_mask(eval_frame: pd.DataFrame) -> np.ndarray:
    post_bf = pd.to_numeric(
        eval_frame.get("target_is_post_bf_4w", pd.Series(0.0, index=eval_frame.index)),
        errors="coerce",
    ).fillna(0) == 1
    recent_bf = pd.to_numeric(
        eval_frame.get("bf_unit_share_4w", pd.Series(0.0, index=eval_frame.index)),
        errors="coerce",
    ).fillna(0) > 0
    return (post_bf & recent_bf).to_numpy(dtype=bool)


def _high_revenue_champion_prediction(
    eval_frame: pd.DataFrame,
    safe_blend_pred: np.ndarray,
    extra_trees_pred: np.ndarray,
    post_bf_safe_naive: np.ndarray,
) -> np.ndarray:
    pred = np.clip(safe_blend_pred.astype(float), 0.0, None).copy()
    regular_mask = _regular_policy_mask(eval_frame)
    post_bf_mask = _post_bf_stress_mask(eval_frame)
    pred[regular_mask] = extra_trees_pred[regular_mask]
    pred[post_bf_mask] = post_bf_safe_naive[post_bf_mask]
    return np.clip(pred, 0.0, None)


def _bfc_nonpost_lift_mask(eval_frame: pd.DataFrame, pred: np.ndarray) -> np.ndarray:
    routes = eval_frame.get("primary_route", pd.Series("", index=eval_frame.index)).astype(str)
    context = eval_frame.get("calendar_route_context", pd.Series("normal_calendar", index=eval_frame.index)).astype(str)
    return ((routes == "bf_campaign_sensitive") & (context != "post_bf_window") & (pred >= 3.0)).to_numpy(dtype=bool)


def _high_revenue_calibrated_prediction(eval_frame: pd.DataFrame, champion_pred: np.ndarray) -> np.ndarray:
    pred = np.clip(champion_pred.astype(float), 0.0, None).copy()
    lift_mask = _bfc_nonpost_lift_mask(eval_frame, pred)
    pred[lift_mask] = pred[lift_mask] * 1.50
    return np.clip(pred, 0.0, None)


def _pre_bf_bfc_lift_mask(eval_frame: pd.DataFrame, pred: np.ndarray) -> np.ndarray:
    routes = eval_frame.get("primary_route", pd.Series("", index=eval_frame.index)).astype(str)
    context = eval_frame.get("calendar_route_context", pd.Series("normal_calendar", index=eval_frame.index)).astype(str)
    return ((routes == "bf_campaign_sensitive") & (context == "pre_bf_window") & (pred >= 3.0)).to_numpy(dtype=bool)


def _high_revenue_guarded_campaign_prediction(eval_frame: pd.DataFrame, champion_pred: np.ndarray) -> np.ndarray:
    pred = np.clip(champion_pred.astype(float), 0.0, None).copy()
    lift_mask = _pre_bf_bfc_lift_mask(eval_frame, pred)
    pred[lift_mask] = pred[lift_mask] * 1.80
    return np.clip(pred, 0.0, None)


def run_sklearn_models(
    conn: sqlite3.Connection,
    target_starts: list[str],
    min_train_windows: int,
    random_state: int,
    revenue_rank_limit: int | None = None,
    high_revenue_policy: str = "none",
    config: ScorecardConfig | None = None,
    include_score_rows: bool = False,
    feature_matrix: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, list[str]] | tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, list[str], pd.DataFrame]:
    config = config or ScorecardConfig()
    if high_revenue_policy not in HIGH_REVENUE_POLICY_CHOICES:
        raise ValueError(f"high_revenue_policy must be one of {', '.join(HIGH_REVENUE_POLICY_CHOICES)}")
    if high_revenue_policy != "none" and (revenue_rank_limit is None or revenue_rank_limit > 1000):
        raise ValueError("high_revenue_policy requires revenue_rank_limit <= 1000")
    matrix = (
        feature_matrix.copy()
        if feature_matrix is not None
        else build_feature_matrix(
            conn,
            target_starts=target_starts,
            population="headline",
            config=config,
            revenue_rank_limit=revenue_rank_limit,
        )
    )
    if high_revenue_policy != "none":
        matrix = add_route_labels(matrix)
    all_score_rows: list[pd.DataFrame] = []
    all_slices: list[pd.DataFrame] = []
    tuning_rows: list[dict[str, object]] = []
    skipped: list[str] = []

    for target_start in target_starts:
        train = matrix[matrix["target_start"] < target_start].copy()
        eval_frame = matrix[matrix["target_start"] == target_start].copy()
        if train["target_start"].nunique() < min_train_windows or eval_frame.empty:
            skipped.append(target_start)
            continue

        x_train = train[NUMERIC_FEATURES + CATEGORICAL_FEATURES]
        y_train = train[TARGET_COL].to_numpy(dtype=float)
        x_eval = eval_frame[NUMERIC_FEATURES + CATEGORICAL_FEATURES]
        predictions: list[pd.DataFrame] = []

        fitted_raw_eval: dict[str, np.ndarray] = {}
        for model_name, estimator in _model_registry(random_state).items():
            pipeline = _fit_pipeline(estimator)
            pipeline.fit(x_train, y_train)
            raw_train_pred = np.clip(pipeline.predict(x_train), 0.0, None)
            post = _tune_postprocess(y_train, raw_train_pred, config.material_units_threshold)
            raw_eval_pred = np.clip(pipeline.predict(x_eval), 0.0, None)
            eval_pred = _apply_postprocess(raw_eval_pred, post)
            fitted_raw_eval[model_name] = eval_pred
            predictions.append(_prediction_frame(model_name, eval_frame, eval_pred))
            tuning_rows.append(
                {
                    "target_start": target_start,
                    "model_name": model_name,
                    "train_windows": int(train["target_start"].nunique()),
                    "train_rows": int(len(train)),
                    "factor": post.factor,
                    "zero_floor": post.zero_floor,
                    "train_hit20": post.train_hit20,
                    "train_wmape": post.train_wmape,
                    "train_phantom_rate": post.train_phantom_rate,
                }
            )

        blend_inputs = [
            fitted_raw_eval["sk_hgb_poisson"],
            fitted_raw_eval["sk_extra_trees"],
            eval_frame["median_naive"].to_numpy(dtype=float),
        ]
        blend_pred = np.nanmedian(np.vstack(blend_inputs), axis=0)
        predictions.append(_prediction_frame("sk_blend_median", eval_frame, blend_pred))
        post_bf_safe_naive = _post_bf_safe_naive(eval_frame)
        predictions.append(_prediction_frame("post_bf_safe_naive", eval_frame, post_bf_safe_naive))
        safe_blend_inputs = [
            _cap_post_bf_predictions(fitted_raw_eval["sk_hgb_poisson"], eval_frame),
            _cap_post_bf_predictions(fitted_raw_eval["sk_extra_trees"], eval_frame),
            post_bf_safe_naive,
        ]
        safe_blend_pred = np.nanmedian(np.vstack(safe_blend_inputs), axis=0)
        predictions.append(_prediction_frame("sk_blend_post_bf_safe", eval_frame, safe_blend_pred))
        if high_revenue_policy != "none":
            champion_pred = _high_revenue_champion_prediction(
                eval_frame,
                safe_blend_pred=safe_blend_pred,
                extra_trees_pred=fitted_raw_eval["sk_extra_trees"],
                post_bf_safe_naive=post_bf_safe_naive,
            )
            predictions.append(
                _prediction_frame(
                    HIGH_REVENUE_CHAMPION_MODEL,
                    eval_frame,
                    champion_pred,
                    prediction_source=HIGH_REVENUE_CHAMPION_SOURCE,
                    model_version=HIGH_REVENUE_CHAMPION_VERSION,
                )
            )
            if high_revenue_policy == "bfc_lift_150":
                calibrated_pred = _high_revenue_calibrated_prediction(eval_frame, champion_pred)
                predictions.append(
                    _prediction_frame(
                        HIGH_REVENUE_CALIBRATED_MODEL,
                        eval_frame,
                        calibrated_pred,
                        prediction_source=HIGH_REVENUE_CALIBRATED_SOURCE,
                        model_version=HIGH_REVENUE_CALIBRATED_VERSION,
                    )
                )
            if high_revenue_policy == "pre_bf_bfc_lift_180":
                guarded_pred = _high_revenue_guarded_campaign_prediction(eval_frame, champion_pred)
                predictions.append(
                    _prediction_frame(
                        HIGH_REVENUE_GUARDED_CAMPAIGN_MODEL,
                        eval_frame,
                        guarded_pred,
                        prediction_source=HIGH_REVENUE_GUARDED_CAMPAIGN_SOURCE,
                        model_version=HIGH_REVENUE_GUARDED_CAMPAIGN_VERSION,
                    )
                )

        run_id = f"sklearn_direct_v1_{target_start}"
        score_rows, slices = score_model_predictions_fast(
            _labels_for_score(eval_frame),
            pd.concat(predictions, ignore_index=True),
            _actuals_for_score(eval_frame),
            run_id,
            config=config,
            baseline_predictions=_baseline_predictions(eval_frame),
        )
        if include_score_rows:
            score_rows = score_rows.merge(_score_row_context(eval_frame), on="sku_id", how="left")
        all_score_rows.append(score_rows)
        all_slices.append(slices)

    combined_rows = pd.concat(all_score_rows, ignore_index=True) if all_score_rows else pd.DataFrame()
    combined_slices = pd.concat(all_slices, ignore_index=True) if all_slices else pd.DataFrame()
    if combined_rows.empty:
        aggregate_slices = pd.DataFrame()
    else:
        aggregate_rows = combined_rows.copy()
        aggregate_rows["sku_id"] = aggregate_rows["run_id"].astype(str) + "|" + aggregate_rows["sku_id"].astype(str)
        aggregate_rows["run_id"] = "aggregate"
        aggregate_slices = build_slices(aggregate_rows, "aggregate")
    result = (combined_slices, aggregate_slices, pd.DataFrame(tuning_rows), skipped)
    if include_score_rows:
        return (*result, combined_rows)
    return result


def build_report(
    per_window_slices: pd.DataFrame,
    aggregate_slices: pd.DataFrame,
    tuning: pd.DataFrame,
    skipped: list[str],
    revenue_rank_limit: int | None = None,
    high_revenue_policy: str = "none",
) -> str:
    headline = per_window_slices[
        (per_window_slices["slice_type"] == "headline")
        & (per_window_slices["slice_value"] == "forecastable_revenue_movers")
    ].copy()
    aggregate = aggregate_slices[
        (aggregate_slices["slice_type"] == "headline")
        & (aggregate_slices["slice_value"] == "forecastable_revenue_movers")
    ].copy()

    control_hit20 = None
    if not aggregate.empty:
        control = aggregate[aggregate["model_name"] == "sk_blend_post_bf_safe"]
        if not control.empty:
            control_hit20 = float(control.iloc[0]["hit20"])
    delta_header = "Delta vs control" if high_revenue_policy != "none" else "Delta vs 24.1%"
    report_title = (
        "# Iteration 5W - V2 Phase 8G-H High-Revenue Policy Wiring"
        if high_revenue_policy != "none"
        else "# Iteration 5N — V2 Phase 8E Availability-Aware Scikit-Learn Direct Model"
    )

    aggregate_rows = []
    for _, row in aggregate.sort_values(["hit20", "wmape"], ascending=[False, True]).iterrows():
        hit_delta = (
            float(row["hit20"]) - control_hit20
            if high_revenue_policy != "none" and control_hit20 is not None
            else float(row["hit20"]) - PHASE8_BASELINE_HIT20
        )
        aggregate_rows.append(
            [
                str(row["model_name"]),
                f"{int(row['n_population']):,}",
                f"{int(row['n_quantity_scored']):,}",
                _fmt_pct(row["hit20"]),
                _fmt_pct(hit_delta),
                _fmt_pct(row["hit30"]),
                _fmt_pct(row["wmape"]),
                _fmt_pct(row["bias_pct"]),
                _fmt_pct(row["phantom_rate"]),
                _fmt_pct(row["winrate_vs_median_naive"]) if row["model_name"] != "median_naive" else "-",
            ]
        )

    window_rows = []
    ordered_models = [
        "median_naive",
        "post_bf_safe_naive",
        "sk_hgb_poisson",
        "sk_hgb_squared",
        "sk_extra_trees",
        "sk_blend_median",
        "sk_blend_post_bf_safe",
    ]
    if high_revenue_policy != "none":
        ordered_models.append(HIGH_REVENUE_CHAMPION_MODEL)
    if high_revenue_policy == "bfc_lift_150":
        ordered_models.append(HIGH_REVENUE_CALIBRATED_MODEL)
    if high_revenue_policy == "pre_bf_bfc_lift_180":
        ordered_models.append(HIGH_REVENUE_GUARDED_CAMPAIGN_MODEL)
    headline["model_order"] = headline["model_name"].map({name: idx for idx, name in enumerate(ordered_models)}).fillna(99)
    for _, row in headline.sort_values(["run_id", "model_order"]).iterrows():
        window_rows.append(
            [
                str(row["run_id"]).replace("sklearn_direct_v1_", ""),
                str(row["model_name"]),
                f"{int(row['n_quantity_scored']):,}",
                _fmt_pct(row["hit20"]),
                _fmt_pct(row["hit30"]),
                _fmt_pct(row["wmape"]),
                _fmt_pct(row["bias_pct"]),
                _fmt_pct(row["phantom_rate"]),
                _fmt_pct(row["winrate_vs_median_naive"]) if row["model_name"] != "median_naive" else "-",
            ]
        )

    tuning_rows = []
    if not tuning.empty:
        for _, row in tuning.sort_values(["target_start", "model_name"]).iterrows():
            tuning_rows.append(
                [
                    str(row["target_start"]),
                    str(row["model_name"]),
                    str(int(row["train_windows"])),
                    f"{int(row['train_rows']):,}",
                    _fmt_num(row["factor"]),
                    _fmt_num(row["zero_floor"]),
                    _fmt_pct(row["train_hit20"]),
                    _fmt_pct(row["train_wmape"]),
                    _fmt_pct(row["train_phantom_rate"]),
                ]
            )

    return "\n".join(
        [
            report_title,
            "",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            "## Aggregate Headline Result",
            "",
            _table(
                [
                    "Model",
                    "Eligible",
                    "Qty scored",
                    "Hit +/-20",
                    delta_header,
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
                ["Target start", "Model", "Qty scored", "Hit +/-20", "Hit +/-30", "WMAPE", "Bias", "Phantom rate", "Winrate vs median"],
                window_rows,
            ),
            "",
            "## Train-Time Postprocessing",
            "",
            _table(
                ["Target start", "Model", "Train windows", "Train rows", "Factor", "Zero floor", "Train hit +/-20", "Train WMAPE", "Train phantom"],
                tuning_rows,
            ),
            "",
            "## Skipped Windows",
            "",
            ", ".join(f"`{window}`" for window in skipped) if skipped else "None.",
            "",
            "## Notes",
            "",
            "- Rows are forecastable revenue movers only.",
            f"- Revenue-rank limit: {'none' if revenue_rank_limit is None else f'Top {revenue_rank_limit}'}.",
            f"- High-revenue policy: `{high_revenue_policy}`.",
            "- High-revenue policies are intentionally blocked unless `--revenue-rank-limit` is 1000 or lower.",
            f"- `{HIGH_REVENUE_CHAMPION_MODEL}` is emitted when `--high-revenue-policy champion` or `bfc_lift_150` is used.",
            f"- `{HIGH_REVENUE_CALIBRATED_MODEL}` is emitted only when `--high-revenue-policy bfc_lift_150` is used.",
            f"- `{HIGH_REVENUE_GUARDED_CAMPAIGN_MODEL}` is emitted only when `--high-revenue-policy pre_bf_bfc_lift_180` is used.",
            "- Every scored target window trains only on earlier target windows.",
            "- Models use the v2 feature matrix: lag baselines, rolling demand, category/product family, cleaned discounts, BF/campaign/store-breadth signals, calendar features, and leak-safe store/supplier stock-position features.",
            "- Supplier stock features use only exact-unique product-name-to-SKU mappings and only months before the target window. Stock is fulfillment context, not a hard sellability signal.",
            "- Postprocessing factor and zero floor are learned only from prior training windows.",
            "- `median_naive` remains the v2-native benchmark.",
        ]
    ) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run forecast v2 sklearn direct models.")
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--target-start", action="append", default=None)
    parser.add_argument("--min-train-windows", type=int, default=4)
    parser.add_argument("--random-state", type=int, default=42)
    parser.add_argument("--revenue-rank-limit", type=int, default=None)
    parser.add_argument("--high-revenue-policy", choices=HIGH_REVENUE_POLICY_CHOICES, default="none")
    args = parser.parse_args()

    conn = sqlite3.connect(args.db)
    try:
        slices, aggregate, tuning, skipped = run_sklearn_models(
            conn,
            target_starts=args.target_start or DEFAULT_TARGET_STARTS,
            min_train_windows=args.min_train_windows,
            random_state=args.random_state,
            revenue_rank_limit=args.revenue_rank_limit,
            high_revenue_policy=args.high_revenue_policy,
        )
    finally:
        conn.close()

    report = build_report(
        slices,
        aggregate,
        tuning,
        skipped,
        revenue_rank_limit=args.revenue_rank_limit,
        high_revenue_policy=args.high_revenue_policy,
    )
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report, encoding="utf-8")
    print(report)
    print(f"Wrote {args.report}")


if __name__ == "__main__":
    main()
