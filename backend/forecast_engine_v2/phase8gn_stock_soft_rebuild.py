"""Phase 8G-N stock-soft retrain and stock-feature ablation for forecast v2."""

from __future__ import annotations

import argparse
import sqlite3
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OrdinalEncoder

try:
    from .feature_matrix import CATEGORICAL_FEATURES, DEFAULT_TARGET_STARTS, NUMERIC_FEATURES
    from .feature_matrix_cache import DEFAULT_CACHE_DIR, load_or_build_feature_matrix
    from .phase8g_route_specific_model import _chronological, _metrics, _scope_mask, _table
    from .route_labels import ROUTE_VERSION, add_route_labels
    from .scorecard import DB_PATH, ScorecardConfig, score_model_predictions_fast
    from .sklearn_direct_model import (
        HIGH_REVENUE_CHAMPION_MODEL,
        TARGET_COL,
        _actuals_for_score,
        _apply_postprocess,
        _baseline_predictions,
        _cap_post_bf_predictions,
        _labels_for_score,
        _model_registry,
        _post_bf_safe_naive,
        _prediction_frame,
        _tune_postprocess,
    )
except ImportError:  # Allows direct script execution.
    from feature_matrix import CATEGORICAL_FEATURES, DEFAULT_TARGET_STARTS, NUMERIC_FEATURES
    from feature_matrix_cache import DEFAULT_CACHE_DIR, load_or_build_feature_matrix
    from phase8g_route_specific_model import _chronological, _metrics, _scope_mask, _table
    from route_labels import ROUTE_VERSION, add_route_labels
    from scorecard import DB_PATH, ScorecardConfig, score_model_predictions_fast
    from sklearn_direct_model import (
        HIGH_REVENUE_CHAMPION_MODEL,
        TARGET_COL,
        _actuals_for_score,
        _apply_postprocess,
        _baseline_predictions,
        _cap_post_bf_predictions,
        _labels_for_score,
        _model_registry,
        _post_bf_safe_naive,
        _prediction_frame,
        _tune_postprocess,
    )


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REPORT = PROJECT_ROOT / "active_docs" / "ITER5AC_V2_PHASE8G_N_STOCK_SOFT_REBUILD.md"
DEFAULT_SCORE_ROWS_CSV = PROJECT_ROOT / "active_docs" / "ITER5AC_V2_PHASE8G_N_SCORE_ROWS.csv"

CONTROL_MODEL = "sk_blend_post_bf_safe"
STOCK_SOFT_FULL = "8gn_stock_soft_full_features"
NO_STOCK_CURRENT = "8gn_no_stock_features_current_route"
NO_STOCK_SOFT = "8gn_no_stock_features_stock_soft"
CURRENT_CHAMPION = HIGH_REVENUE_CHAMPION_MODEL
REVENUE_SCOPES = [100, 250, 500, 750, 1000]
REGULAR_ROUTES = {"available_regular", "proxy_available_regular"}
STOCK_TERMS = ("stock", "availability")
ORDERED_MODELS = [
    "median_naive",
    "post_bf_safe_naive",
    "sk_extra_trees",
    CONTROL_MODEL,
    CURRENT_CHAMPION,
    STOCK_SOFT_FULL,
    NO_STOCK_CURRENT,
    NO_STOCK_SOFT,
]


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


def _delta(candidate: object, baseline: object) -> float | None:
    if candidate is None or baseline is None or pd.isna(candidate) or pd.isna(baseline):
        return None
    return float(candidate) - float(baseline)


def _is_stock_feature(name: str) -> bool:
    lowered = name.lower()
    return any(term in lowered for term in STOCK_TERMS)


def _feature_profile(remove_stock_features: bool) -> tuple[list[str], list[str]]:
    if not remove_stock_features:
        return list(NUMERIC_FEATURES), list(CATEGORICAL_FEATURES)
    numeric = [col for col in NUMERIC_FEATURES if not _is_stock_feature(col)]
    categorical = [col for col in CATEGORICAL_FEATURES if not _is_stock_feature(col)]
    return numeric, categorical


def _fit_pipeline(estimator: object, numeric_features: list[str], categorical_features: list[str]) -> Pipeline:
    numeric_pipe = Pipeline(steps=[("imputer", SimpleImputer(strategy="median"))])
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
    preprocessor = ColumnTransformer(
        transformers=[
            ("num", numeric_pipe, numeric_features),
            ("cat", categorical_pipe, categorical_features),
        ],
        remainder="drop",
    )
    return Pipeline(steps=[("preprocess", preprocessor), ("model", estimator)])


def _post_bf_stress_mask(frame: pd.DataFrame) -> np.ndarray:
    post_bf = pd.to_numeric(frame.get("target_is_post_bf_4w", 0), errors="coerce").fillna(0) == 1
    recent_bf = pd.to_numeric(frame.get("bf_unit_share_4w", 0), errors="coerce").fillna(0) > 0
    return (post_bf & recent_bf).to_numpy(dtype=bool)


def _current_regular_mask(frame: pd.DataFrame) -> np.ndarray:
    routes = frame.get("primary_route", pd.Series("", index=frame.index)).astype(str)
    context = frame.get("calendar_route_context", pd.Series("normal_calendar", index=frame.index)).astype(str)
    return (routes.isin(REGULAR_ROUTES) & (context == "normal_calendar")).to_numpy(dtype=bool)


def _demand_regular_mask(frame: pd.DataFrame) -> np.ndarray:
    active_weeks = pd.to_numeric(frame.get("active_weeks_52", 0), errors="coerce").fillna(0)
    avg_units = pd.to_numeric(frame.get("avg_units_per_4w_52", 0), errors="coerce").fillna(0)
    context = frame.get("calendar_route_context", pd.Series("normal_calendar", index=frame.index)).astype(str)
    return ((active_weeks >= 24) & (avg_units >= 2.0) & (context == "normal_calendar")).to_numpy(dtype=bool)


def _prediction_map(
    train: pd.DataFrame,
    eval_frame: pd.DataFrame,
    random_state: int,
    config: ScorecardConfig,
    remove_stock_features: bool,
) -> dict[str, np.ndarray]:
    numeric_features, categorical_features = _feature_profile(remove_stock_features)
    x_train = train[numeric_features + categorical_features]
    y_train = train[TARGET_COL].to_numpy(dtype=float)
    x_eval = eval_frame[numeric_features + categorical_features]
    pred_map: dict[str, np.ndarray] = {
        "median_naive": eval_frame["median_naive"].fillna(0.0).clip(lower=0.0).to_numpy(dtype=float),
    }
    for model_name, estimator in _model_registry(random_state).items():
        pipeline = _fit_pipeline(estimator, numeric_features, categorical_features)
        pipeline.fit(x_train, y_train)
        raw_train_pred = np.clip(pipeline.predict(x_train), 0.0, None)
        post = _tune_postprocess(y_train, raw_train_pred, config.material_units_threshold)
        raw_eval_pred = np.clip(pipeline.predict(x_eval), 0.0, None)
        pred_map[model_name] = _apply_postprocess(raw_eval_pred, post)

    pred_map["post_bf_safe_naive"] = _post_bf_safe_naive(eval_frame)
    safe_blend_inputs = [
        _cap_post_bf_predictions(pred_map["sk_hgb_poisson"], eval_frame),
        _cap_post_bf_predictions(pred_map["sk_extra_trees"], eval_frame),
        pred_map["post_bf_safe_naive"],
    ]
    pred_map[CONTROL_MODEL] = np.nanmedian(np.vstack(safe_blend_inputs), axis=0)
    return pred_map


def _compose_candidate(
    eval_frame: pd.DataFrame,
    pred_map: dict[str, np.ndarray],
    regular_mask: np.ndarray,
) -> np.ndarray:
    pred = pred_map[CONTROL_MODEL].copy()
    pred[regular_mask] = pred_map["sk_extra_trees"][regular_mask]
    post_bf = _post_bf_stress_mask(eval_frame)
    pred[post_bf] = pred_map["post_bf_safe_naive"][post_bf]
    return np.clip(pred, 0.0, None)


def _route_cols(frame: pd.DataFrame) -> list[str]:
    cols = [
        "sku_id",
        "target_start",
        "revenue_rank",
        "primary_route",
        "stock_position_confidence",
        "availability_confidence",
        "calendar_route_context",
        "active_weeks_52",
        "avg_units_per_4w_52",
        "campaign_txn_13w",
        "bf_txn_13w",
        "bf_unit_share_4w",
        "stock_observed_prev_month",
        "stock_prev_month_qty",
        "supplier_stock_observed_prev_month",
        "supplier_stock_prev_month_qty",
        "combined_stock_observed_prev_month",
        "combined_stock_prev_month_qty",
    ]
    return [col for col in cols if col in frame.columns]


def run_phase8gn(
    conn: sqlite3.Connection,
    target_starts: list[str],
    min_train_windows: int,
    random_state: int,
    revenue_rank_limit: int,
    cache_dir: Path,
    refresh_cache: bool,
    config: ScorecardConfig | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, list[str], list[dict[str, object]], Path, bool]:
    config = config or ScorecardConfig()
    target_starts = _chronological(target_starts)
    matrix, cache_path, cache_hit = load_or_build_feature_matrix(
        conn,
        target_starts=target_starts,
        population="headline",
        config=config,
        revenue_rank_limit=revenue_rank_limit,
        cache_dir=cache_dir,
        refresh=refresh_cache,
    )
    matrix = add_route_labels(matrix)
    all_score_rows: list[pd.DataFrame] = []
    skipped: list[str] = []
    diagnostics: list[dict[str, object]] = []

    full_numeric, full_categorical = _feature_profile(False)
    no_stock_numeric, no_stock_categorical = _feature_profile(True)

    for target_start in target_starts:
        train = matrix[pd.to_datetime(matrix["target_start"]) < pd.Timestamp(target_start)].copy()
        eval_frame = matrix[matrix["target_start"] == target_start].copy()
        if train["target_start"].nunique() < min_train_windows or eval_frame.empty:
            skipped.append(target_start)
            continue

        full_pred = _prediction_map(train, eval_frame, random_state, config, remove_stock_features=False)
        no_stock_pred = _prediction_map(train, eval_frame, random_state, config, remove_stock_features=True)
        current_regular = _current_regular_mask(eval_frame)
        demand_regular = _demand_regular_mask(eval_frame)
        post_bf = _post_bf_stress_mask(eval_frame)

        predictions = [
            _prediction_frame("post_bf_safe_naive", eval_frame, full_pred["post_bf_safe_naive"]),
            _prediction_frame("sk_extra_trees", eval_frame, full_pred["sk_extra_trees"]),
            _prediction_frame(CONTROL_MODEL, eval_frame, full_pred[CONTROL_MODEL]),
            _prediction_frame(CURRENT_CHAMPION, eval_frame, _compose_candidate(eval_frame, full_pred, current_regular)),
            _prediction_frame(STOCK_SOFT_FULL, eval_frame, _compose_candidate(eval_frame, full_pred, demand_regular)),
            _prediction_frame(NO_STOCK_CURRENT, eval_frame, _compose_candidate(eval_frame, no_stock_pred, current_regular)),
            _prediction_frame(NO_STOCK_SOFT, eval_frame, _compose_candidate(eval_frame, no_stock_pred, demand_regular)),
        ]
        score_rows, _ = score_model_predictions_fast(
            _labels_for_score(eval_frame),
            pd.concat(predictions, ignore_index=True),
            _actuals_for_score(eval_frame),
            f"phase8gn_stock_soft_{target_start}",
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
                "current_regular_rows": int(current_regular.sum()),
                "demand_regular_rows": int(demand_regular.sum()),
                "extra_demand_regular_rows": int((demand_regular & ~current_regular).sum()),
                "post_bf_rows": int(post_bf.sum()),
                "full_feature_count": int(len(full_numeric) + len(full_categorical)),
                "no_stock_feature_count": int(len(no_stock_numeric) + len(no_stock_categorical)),
            }
        )

    score_rows = pd.concat(all_score_rows, ignore_index=True) if all_score_rows else pd.DataFrame()
    return matrix, score_rows, skipped, diagnostics, cache_path, cache_hit


def _model_metrics(score_rows: pd.DataFrame, model_name: str) -> dict[str, object]:
    return _metrics(score_rows[score_rows["model_name"] == model_name].copy())


def _model_rows(score_rows: pd.DataFrame) -> list[list[str]]:
    champion = _model_metrics(score_rows, CURRENT_CHAMPION)
    order = {name: idx for idx, name in enumerate(ORDERED_MODELS)}
    rows: list[list[str]] = []
    for model_name, group in sorted(
        score_rows.groupby("model_name", dropna=False),
        key=lambda item: order.get(str(item[0]), 99),
    ):
        metrics = _metrics(group)
        rows.append(
            [
                str(model_name),
                f"{metrics['rows']:,}",
                f"{metrics['scored']:,}",
                _fmt_pct(metrics["hit20"]),
                _fmt_pp(_delta(metrics["hit20"], champion["hit20"])),
                _fmt_pct(metrics["hit30"]),
                _fmt_pct(metrics["wmape"]),
                _fmt_pp(_delta(metrics["wmape"], champion["wmape"])),
                _fmt_pct(metrics["bias"]),
                _fmt_pct(metrics["phantom_rate"]),
                _fmt_pp(_delta(metrics["phantom_rate"], champion["phantom_rate"])),
            ]
        )
    return rows


def _scope_rows(score_rows: pd.DataFrame, candidate_model: str) -> list[list[str]]:
    rows: list[list[str]] = []
    champion_rows = score_rows[score_rows["model_name"] == CURRENT_CHAMPION].copy()
    candidate_rows = score_rows[score_rows["model_name"] == candidate_model].copy()
    for rank_limit in REVENUE_SCOPES:
        champion = _metrics(champion_rows[_scope_mask(champion_rows, rank_limit)])
        candidate = _metrics(candidate_rows[_scope_mask(candidate_rows, rank_limit)])
        rows.append(
            [
                f"Top {rank_limit}",
                f"{candidate['rows']:,}",
                f"{candidate['scored']:,}",
                _fmt_num(candidate["actual_revenue"], 0),
                _fmt_pct(champion["hit20"]),
                _fmt_pct(candidate["hit20"]),
                _fmt_pp(_delta(candidate["hit20"], champion["hit20"])),
                _fmt_pct(champion["wmape"]),
                _fmt_pct(candidate["wmape"]),
                _fmt_pp(_delta(candidate["wmape"], champion["wmape"])),
                _fmt_pct(champion["phantom_rate"]),
                _fmt_pct(candidate["phantom_rate"]),
                _fmt_pp(_delta(candidate["phantom_rate"], champion["phantom_rate"])),
            ]
        )
    return rows


def _slice_compare_rows(score_rows: pd.DataFrame, candidate_model: str) -> list[list[str]]:
    base = score_rows[score_rows["model_name"] == candidate_model].copy()
    primary_route = score_rows.get("primary_route", pd.Series("", index=score_rows.index)).astype(str)
    campaign_txn_13w = pd.to_numeric(score_rows.get("campaign_txn_13w", 0), errors="coerce").fillna(0)
    bf_txn_13w = pd.to_numeric(score_rows.get("bf_txn_13w", 0), errors="coerce").fillna(0)
    active_weeks = pd.to_numeric(score_rows.get("active_weeks_52", 0), errors="coerce").fillna(0)
    avg_units = pd.to_numeric(score_rows.get("avg_units_per_4w_52", 0), errors="coerce").fillna(0)
    masks = [
        ("Current regular/proxy route", primary_route.isin(REGULAR_ROUTES)),
        ("Stock-constrained route", primary_route == "stock_constrained"),
        ("Demand-regular no stock gate", (active_weeks >= 24) & (avg_units >= 2.0)),
        ("Any campaign/BF history 13w", (campaign_txn_13w > 0) | (bf_txn_13w > 0)),
        ("2024-11-25 stress window", score_rows["target_start"].astype(str) == "2024-11-25"),
        ("2024-12-30 monitor window", score_rows["target_start"].astype(str) == "2024-12-30"),
    ]
    rows: list[list[str]] = []
    for label, mask in masks:
        champion = _metrics(score_rows[(score_rows["model_name"] == CURRENT_CHAMPION) & mask])
        candidate = _metrics(base[mask[base.index]])
        rows.append(
            [
                label,
                f"{candidate['rows']:,}",
                f"{candidate['scored']:,}",
                _fmt_pct(champion["hit20"]),
                _fmt_pct(candidate["hit20"]),
                _fmt_pp(_delta(candidate["hit20"], champion["hit20"])),
                _fmt_pct(champion["wmape"]),
                _fmt_pct(candidate["wmape"]),
                _fmt_pp(_delta(candidate["wmape"], champion["wmape"])),
                _fmt_pct(champion["phantom_rate"]),
                _fmt_pct(candidate["phantom_rate"]),
                _fmt_pp(_delta(candidate["phantom_rate"], champion["phantom_rate"])),
            ]
        )
    return rows


def _window_rows(score_rows: pd.DataFrame, candidate_model: str) -> list[list[str]]:
    rows: list[list[str]] = []
    for target_start in sorted(score_rows["target_start"].dropna().astype(str).unique()):
        mask = score_rows["target_start"].astype(str) == target_start
        champion = _metrics(score_rows[(score_rows["model_name"] == CURRENT_CHAMPION) & mask])
        candidate = _metrics(score_rows[(score_rows["model_name"] == candidate_model) & mask])
        rows.append(
            [
                target_start,
                f"{candidate['scored']:,}",
                _fmt_pct(champion["hit20"]),
                _fmt_pct(candidate["hit20"]),
                _fmt_pp(_delta(candidate["hit20"], champion["hit20"])),
                _fmt_pct(champion["wmape"]),
                _fmt_pct(candidate["wmape"]),
                _fmt_pp(_delta(candidate["wmape"], champion["wmape"])),
                _fmt_pct(champion["phantom_rate"]),
                _fmt_pct(candidate["phantom_rate"]),
                _fmt_pp(_delta(candidate["phantom_rate"], champion["phantom_rate"])),
            ]
        )
    return rows


def _diagnostic_rows(diagnostics: list[dict[str, object]]) -> list[list[str]]:
    return [
        [
            str(row["target_start"]),
            str(row["train_windows"]),
            f"{int(row['eval_rows']):,}",
            f"{int(row['current_regular_rows']):,}",
            f"{int(row['demand_regular_rows']):,}",
            f"{int(row['extra_demand_regular_rows']):,}",
            f"{int(row['post_bf_rows']):,}",
            str(row["full_feature_count"]),
            str(row["no_stock_feature_count"]),
        ]
        for row in diagnostics
    ]


def _best_candidate(score_rows: pd.DataFrame) -> tuple[str, dict[str, object]]:
    candidates = [STOCK_SOFT_FULL, NO_STOCK_CURRENT, NO_STOCK_SOFT]
    ranked = []
    for model_name in candidates:
        metrics = _model_metrics(score_rows, model_name)
        ranked.append((model_name, metrics))
    ranked.sort(
        key=lambda item: (
            1.0 if item[1]["hit20"] is None else -float(item[1]["hit20"]),
            float("inf") if item[1]["wmape"] is None else float(item[1]["wmape"]),
            float("inf") if item[1]["phantom_rate"] is None else float(item[1]["phantom_rate"]),
        )
    )
    return ranked[0]


def _promotion_decision(score_rows: pd.DataFrame, candidate_model: str) -> tuple[str, list[list[str]], float | None]:
    champion = _model_metrics(score_rows, CURRENT_CHAMPION)
    candidate = _model_metrics(score_rows, candidate_model)
    worst_window: str | None = None
    worst_wmape_delta: float | None = None
    for target_start in sorted(score_rows["target_start"].dropna().astype(str).unique()):
        mask = score_rows["target_start"].astype(str) == target_start
        c0 = _metrics(score_rows[(score_rows["model_name"] == CURRENT_CHAMPION) & mask])
        c1 = _metrics(score_rows[(score_rows["model_name"] == candidate_model) & mask])
        delta = _delta(c1["wmape"], c0["wmape"])
        if delta is not None and (worst_wmape_delta is None or delta > worst_wmape_delta):
            worst_wmape_delta = delta
            worst_window = target_start

    checks = [
        ("Hit +/-20 vs champion", ">= +0.5pp", _delta(candidate["hit20"], champion["hit20"]), 0.005, "min"),
        ("WMAPE vs champion", "<= 0.0pp", _delta(candidate["wmape"], champion["wmape"]), 0.0, "max"),
        ("Phantom vs champion", "<= +0.5pp", _delta(candidate["phantom_rate"], champion["phantom_rate"]), 0.005, "max"),
        (f"Largest window WMAPE regression ({worst_window or '-'})", "<= +2.0pp", worst_wmape_delta, 0.020, "max"),
    ]
    rows: list[list[str]] = []
    passes = []
    for label, requirement, observed, threshold, mode in checks:
        if observed is None:
            passed = False
        elif mode == "min":
            passed = observed >= threshold
        else:
            passed = observed <= threshold
        passes.append(passed)
        rows.append([label, requirement, _fmt_pp(observed), "PASS" if passed else "FAIL"])
    decision = "PROMOTE_STOCK_SOFT_CANDIDATE" if all(passes) else "KEEP_CURRENT_CHAMPION"
    return decision, rows, worst_wmape_delta


def build_report(
    matrix: pd.DataFrame,
    score_rows: pd.DataFrame,
    skipped: list[str],
    diagnostics: list[dict[str, object]],
    cache_path: Path,
    cache_hit: bool,
    revenue_rank_limit: int,
    score_rows_csv: Path,
) -> str:
    if score_rows.empty:
        return "# Iteration 5AC - V2 Phase 8G-N Stock-Soft Rebuild\n\nNo scorable windows were available.\n"

    best_model, best_metrics = _best_candidate(score_rows)
    decision, gate_rows, _ = _promotion_decision(score_rows, best_model)
    champion = _model_metrics(score_rows, CURRENT_CHAMPION)
    full_numeric, full_categorical = _feature_profile(False)
    no_stock_numeric, no_stock_categorical = _feature_profile(True)
    removed_features = sorted(set(full_numeric + full_categorical) - set(no_stock_numeric + no_stock_categorical))
    decision_note = (
        "A stock-soft/no-stock candidate cleared all gates."
        if decision == "PROMOTE_STOCK_SOFT_CANDIDATE"
        else "No stock-soft or stock-ablation candidate cleared the gates. Keep the current champion and stop treating stock as sellability, but do not promote a new stock-soft policy yet."
    )
    return "\n".join(
        [
            "# Iteration 5AC - V2 Phase 8G-N Stock-Soft Rebuild",
            "",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"Route version: `{ROUTE_VERSION}`",
            "",
            "## Decision",
            "",
            f"Decision: `{decision}`.",
            "",
            decision_note,
            "",
            _table(
                ["Metric", "Current champion", "Best stock-soft/ablation candidate"],
                [
                    ["Model", CURRENT_CHAMPION, best_model],
                    ["Hit +/-20", _fmt_pct(champion["hit20"]), _fmt_pct(best_metrics["hit20"])],
                    ["Hit delta", "-", _fmt_pp(_delta(best_metrics["hit20"], champion["hit20"]))],
                    ["Hit +/-30", _fmt_pct(champion["hit30"]), _fmt_pct(best_metrics["hit30"])],
                    ["WMAPE", _fmt_pct(champion["wmape"]), _fmt_pct(best_metrics["wmape"])],
                    ["WMAPE delta", "-", _fmt_pp(_delta(best_metrics["wmape"], champion["wmape"]))],
                    ["Bias", _fmt_pct(champion["bias"]), _fmt_pct(best_metrics["bias"])],
                    ["Phantom", _fmt_pct(champion["phantom_rate"]), _fmt_pct(best_metrics["phantom_rate"])],
                    ["Phantom delta", "-", _fmt_pp(_delta(best_metrics["phantom_rate"], champion["phantom_rate"]))],
                ],
            ),
            "",
            "## Promotion Gates",
            "",
            _table(["Gate", "Required", "Observed", "Status"], gate_rows),
            "",
            "## Aggregate Model Results",
            "",
            _table(
                [
                    "Model",
                    "Rows",
                    "Qty scored",
                    "Hit +/-20",
                    "Delta vs champion",
                    "Hit +/-30",
                    "WMAPE",
                    "WMAPE delta",
                    "Bias",
                    "Phantom",
                    "Phantom delta",
                ],
                _model_rows(score_rows),
            ),
            "",
            f"## Revenue Scope Validation - {best_model}",
            "",
            _table(
                [
                    "Scope",
                    "Rows",
                    "Qty scored",
                    "Actual revenue",
                    "Champion hit +/-20",
                    "Candidate hit +/-20",
                    "Hit delta",
                    "Champion WMAPE",
                    "Candidate WMAPE",
                    "WMAPE delta",
                    "Champion phantom",
                    "Candidate phantom",
                    "Phantom delta",
                ],
                _scope_rows(score_rows, best_model),
            ),
            "",
            f"## Critical Slice Validation - {best_model}",
            "",
            _table(
                [
                    "Slice",
                    "Rows",
                    "Qty scored",
                    "Champion hit +/-20",
                    "Candidate hit +/-20",
                    "Hit delta",
                    "Champion WMAPE",
                    "Candidate WMAPE",
                    "WMAPE delta",
                    "Champion phantom",
                    "Candidate phantom",
                    "Phantom delta",
                ],
                _slice_compare_rows(score_rows, best_model),
            ),
            "",
            f"## Window Validation - {best_model}",
            "",
            _table(
                [
                    "Target start",
                    "Qty scored",
                    "Champion hit +/-20",
                    "Candidate hit +/-20",
                    "Hit delta",
                    "Champion WMAPE",
                    "Candidate WMAPE",
                    "WMAPE delta",
                    "Champion phantom",
                    "Candidate phantom",
                    "Phantom delta",
                ],
                _window_rows(score_rows, best_model),
            ),
            "",
            "## Route / Feature Diagnostics",
            "",
            _table(
                [
                    "Target start",
                    "Train windows",
                    "Eval rows",
                    "Current regular rows",
                    "Demand-regular rows",
                    "Extra demand-regular rows",
                    "Post-BF rows",
                    "Full features",
                    "No-stock features",
                ],
                _diagnostic_rows(diagnostics),
            ),
            "",
            "## Interpretation",
            "",
            "- `8gn_stock_soft_full_features` keeps all model features but replaces the regular-route gate with demand regularity, not stock position.",
            "- `8gn_no_stock_features_current_route` retrains base estimators without stock/availability features but keeps the current champion route gate.",
            "- `8gn_no_stock_features_stock_soft` retrains without stock/availability features and uses demand-regular routing.",
            "- The stock-feature ablation removes features containing `stock` or `availability`; stock labels are still attached only for reporting and mask comparison.",
            "- This phase is still a rolling backtest on known windows, not independent future holdout evidence.",
            "",
            "## Outputs",
            "",
            f"- Matrix rows: {len(matrix):,}.",
            f"- Revenue-rank limit: Top {revenue_rank_limit}.",
            f"- Cache path: `{cache_path}`.",
            f"- Cache hit: `{cache_hit}`.",
            f"- Removed feature count for no-stock ablation: {len(removed_features)}.",
            f"- Score rows: `{score_rows_csv}`.",
            f"- Skipped windows: {', '.join(f'`{item}`' for item in skipped) if skipped else 'None'}.",
        ]
    ) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Phase 8G-N stock-soft retrain and ablation.")
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--score-rows-csv", type=Path, default=DEFAULT_SCORE_ROWS_CSV)
    parser.add_argument("--target-start", action="append", default=None)
    parser.add_argument("--min-train-windows", type=int, default=4)
    parser.add_argument("--random-state", type=int, default=42)
    parser.add_argument("--revenue-rank-limit", type=int, default=1000)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    parser.add_argument("--refresh-cache", action="store_true")
    args = parser.parse_args()

    config = ScorecardConfig()
    conn = sqlite3.connect(args.db)
    try:
        print("8G-N: loading/building cleaned Top 1000 feature matrix...", flush=True)
        matrix, score_rows, skipped, diagnostics, cache_path, cache_hit = run_phase8gn(
            conn,
            target_starts=args.target_start or DEFAULT_TARGET_STARTS,
            min_train_windows=args.min_train_windows,
            random_state=args.random_state,
            revenue_rank_limit=args.revenue_rank_limit,
            cache_dir=args.cache_dir,
            refresh_cache=args.refresh_cache,
            config=config,
        )
    finally:
        conn.close()

    args.score_rows_csv.parent.mkdir(parents=True, exist_ok=True)
    score_rows.to_csv(args.score_rows_csv, index=False)
    report = build_report(
        matrix,
        score_rows,
        skipped,
        diagnostics,
        cache_path,
        cache_hit,
        args.revenue_rank_limit,
        args.score_rows_csv,
    )
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report, encoding="utf-8")
    print(report)
    print(f"Wrote {args.report}")


if __name__ == "__main__":
    main()
