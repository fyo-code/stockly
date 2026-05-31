"""Phase 8G-D high-revenue route-specific model candidates for forecast v2."""

from __future__ import annotations

import argparse
import sqlite3
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from .feature_matrix import CATEGORICAL_FEATURES, DEFAULT_TARGET_STARTS, NUMERIC_FEATURES
    from .feature_matrix_cache import DEFAULT_CACHE_DIR, load_or_build_feature_matrix
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
    from feature_matrix import CATEGORICAL_FEATURES, DEFAULT_TARGET_STARTS, NUMERIC_FEATURES
    from feature_matrix_cache import DEFAULT_CACHE_DIR, load_or_build_feature_matrix
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
DEFAULT_REPORT = PROJECT_ROOT / "active_docs" / "ITER5S_V2_PHASE8G_ROUTE_SPECIFIC_MODEL.md"

PHASE8E_CONTROL = "sk_blend_post_bf_safe"
REGULAR_ROUTES = {"available_regular", "proxy_available_regular"}
REVENUE_SCOPES = [("top_100", 100), ("top_500", 500), ("top_1000", 1000)]
ORDERED_MODELS = [
    "median_naive",
    "post_bf_safe_naive",
    "sk_hgb_poisson",
    "sk_hgb_squared",
    "sk_extra_trees",
    PHASE8E_CONTROL,
    "8gd_regular_global_extra",
    "8gd_regular_specialist_extra",
    "8gd_supplier_available_extra",
    "8gd_availability_campaign_gated",
]
PREDICTION_MODELS = [model for model in ORDERED_MODELS if model != "median_naive"]


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


def _chronological(target_starts: list[str]) -> list[str]:
    return [value for _, value in sorted((pd.Timestamp(value), value) for value in target_starts)]


def _metrics(rows: pd.DataFrame) -> dict[str, object]:
    scored = rows[rows["quantity_scored"] == 1]
    actual_sum = float(scored["actual_units"].sum())
    zero_actual = rows[rows["actual_units"] == 0]
    return {
        "rows": int(len(rows)),
        "scored": int(len(scored)),
        "actual_units": actual_sum,
        "actual_revenue": float(rows["actual_revenue"].sum()) if "actual_revenue" in rows.columns else None,
        "pred_units": float(scored["pred_units"].sum()) if not scored.empty else 0.0,
        "hit20": float(scored["hit20"].mean()) if not scored.empty else None,
        "hit30": float(scored["hit30"].mean()) if not scored.empty else None,
        "wmape": float(scored["abs_error"].sum() / actual_sum) if actual_sum > 0 else None,
        "bias": float(scored["signed_error"].sum() / actual_sum) if actual_sum > 0 else None,
        "phantom_rate": float(zero_actual["phantom"].mean()) if len(zero_actual) else None,
    }


def _scope_mask(rows: pd.DataFrame, rank_limit: int | None) -> pd.Series:
    if rank_limit is None:
        return pd.Series(True, index=rows.index)
    return pd.to_numeric(rows["revenue_rank"], errors="coerce") <= rank_limit


def _scope_label(scope_name: str) -> str:
    return {"top_100": "Top 100", "top_500": "Top 500", "top_1000": "Top 1000"}.get(scope_name, scope_name)


def _regular_mask(frame: pd.DataFrame) -> pd.Series:
    return frame["primary_route"].isin(REGULAR_ROUTES) & (frame["calendar_route_context"] == "normal_calendar")


def _supplier_available_mask(frame: pd.DataFrame) -> pd.Series:
    return (
        (pd.to_numeric(frame.get("store_or_supplier_available_before_target", 0), errors="coerce").fillna(0) == 1)
        & (pd.to_numeric(frame.get("combined_stock_observed_prev_month", 0), errors="coerce").fillna(0) == 1)
        & (frame["calendar_route_context"] == "normal_calendar")
        & (frame["primary_route"] != "bf_campaign_sensitive")
    )


def _campaign_mask(frame: pd.DataFrame) -> pd.Series:
    campaign_history = pd.to_numeric(frame.get("campaign_txn_13w", 0), errors="coerce").fillna(0) > 0
    bf_history = pd.to_numeric(frame.get("bf_txn_13w", 0), errors="coerce").fillna(0) > 0
    return (frame["primary_route"] == "bf_campaign_sensitive") | campaign_history | bf_history


def _stock_constrained_mask(frame: pd.DataFrame) -> pd.Series:
    return frame["primary_route"] == "stock_constrained"


def _fit_specialist(
    train: pd.DataFrame,
    eval_frame: pd.DataFrame,
    train_mask: pd.Series,
    estimator: object,
    config: ScorecardConfig,
    min_rows: int = 250,
    min_windows: int = 3,
) -> np.ndarray | None:
    routed_train = train[train_mask].copy()
    if routed_train["target_start"].nunique() < min_windows or len(routed_train) < min_rows:
        return None
    if float(routed_train[TARGET_COL].sum()) <= 0:
        return None
    pipeline = _fit_pipeline(estimator)
    x_train = routed_train[NUMERIC_FEATURES + CATEGORICAL_FEATURES]
    y_train = routed_train[TARGET_COL].to_numpy(dtype=float)
    pipeline.fit(x_train, y_train)
    raw_train_pred = np.clip(pipeline.predict(x_train), 0.0, None)
    post = _tune_postprocess(y_train, raw_train_pred, config.material_units_threshold)
    raw_eval_pred = np.clip(pipeline.predict(eval_frame[NUMERIC_FEATURES + CATEGORICAL_FEATURES]), 0.0, None)
    return _apply_postprocess(raw_eval_pred, post)


def _prediction_map(
    train: pd.DataFrame,
    eval_frame: pd.DataFrame,
    random_state: int,
    config: ScorecardConfig,
) -> tuple[dict[str, np.ndarray], dict[str, object]]:
    x_train = train[NUMERIC_FEATURES + CATEGORICAL_FEATURES]
    y_train = train[TARGET_COL].to_numpy(dtype=float)
    x_eval = eval_frame[NUMERIC_FEATURES + CATEGORICAL_FEATURES]
    registry = _model_registry(random_state)
    pred_map: dict[str, np.ndarray] = {
        "median_naive": eval_frame["median_naive"].fillna(0.0).clip(lower=0.0).to_numpy(dtype=float),
    }
    diagnostics: dict[str, object] = {}

    for model_name, estimator in registry.items():
        pipeline = _fit_pipeline(estimator)
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
    pred_map[PHASE8E_CONTROL] = np.nanmedian(np.vstack(safe_blend_inputs), axis=0)

    regular_extra = _fit_specialist(
        train,
        eval_frame,
        _regular_mask(train),
        registry["sk_extra_trees"],
        config,
        min_rows=250,
    )
    campaign_extra = _fit_specialist(
        train,
        eval_frame,
        _campaign_mask(train),
        registry["sk_extra_trees"],
        config,
        min_rows=300,
    )
    stock_extra = _fit_specialist(
        train,
        eval_frame,
        _stock_constrained_mask(train),
        registry["sk_extra_trees"],
        config,
        min_rows=150,
    )
    diagnostics["regular_specialist_available"] = regular_extra is not None
    diagnostics["campaign_specialist_available"] = campaign_extra is not None
    diagnostics["stock_specialist_available"] = stock_extra is not None

    regular_eval = _regular_mask(eval_frame).to_numpy(dtype=bool)
    supplier_eval = _supplier_available_mask(eval_frame).to_numpy(dtype=bool)
    campaign_eval = _campaign_mask(eval_frame).to_numpy(dtype=bool)
    stock_eval = _stock_constrained_mask(eval_frame).to_numpy(dtype=bool)

    pred = pred_map[PHASE8E_CONTROL].copy()
    pred[regular_eval] = pred_map["sk_extra_trees"][regular_eval]
    pred_map["8gd_regular_global_extra"] = np.clip(pred, 0.0, None)

    pred = pred_map[PHASE8E_CONTROL].copy()
    if regular_extra is not None:
        pred[regular_eval] = regular_extra[regular_eval]
    pred_map["8gd_regular_specialist_extra"] = np.clip(pred, 0.0, None)

    pred = pred_map[PHASE8E_CONTROL].copy()
    pred[supplier_eval] = pred_map["sk_extra_trees"][supplier_eval]
    pred_map["8gd_supplier_available_extra"] = np.clip(pred, 0.0, None)

    pred = pred_map[PHASE8E_CONTROL].copy()
    if regular_extra is not None:
        pred[regular_eval] = np.nanmedian(
            np.vstack([regular_extra[regular_eval], pred_map["sk_extra_trees"][regular_eval]]),
            axis=0,
        )
    if campaign_extra is not None and campaign_eval.any():
        pred[campaign_eval] = np.nanmedian(
            np.vstack(
                [
                    campaign_extra[campaign_eval],
                    pred_map[PHASE8E_CONTROL][campaign_eval],
                    pred_map["post_bf_safe_naive"][campaign_eval],
                ]
            ),
            axis=0,
        )
    if stock_extra is not None and stock_eval.any():
        pred[stock_eval] = np.nanmedian(
            np.vstack(
                [
                    stock_extra[stock_eval],
                    pred_map[PHASE8E_CONTROL][stock_eval],
                    pred_map["median_naive"][stock_eval],
                ]
            ),
            axis=0,
        )
    pred_map["8gd_availability_campaign_gated"] = np.clip(pred, 0.0, None)
    return pred_map, diagnostics


def _route_cols(frame: pd.DataFrame) -> list[str]:
    cols = [
        "sku_id",
        "target_start",
        "revenue_rank",
        "primary_route",
        "availability_confidence",
        "calendar_route_context",
        "sku_bf_contamination_context",
        "combined_stock_observed_prev_month",
        "store_or_supplier_available_before_target",
        "likely_true_stockout_before_target",
        "campaign_txn_13w",
        "non_bf_campaign_txn_13w",
        "bf_txn_13w",
        "campaign_unit_share_13w",
    ]
    return [col for col in cols if col in frame.columns]


def run_phase8gd(
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

    for target_start in target_starts:
        train = matrix[pd.to_datetime(matrix["target_start"]) < pd.Timestamp(target_start)].copy()
        eval_frame = matrix[matrix["target_start"] == target_start].copy()
        if train["target_start"].nunique() < min_train_windows or eval_frame.empty:
            skipped.append(target_start)
            continue

        pred_map, diag = _prediction_map(train, eval_frame, random_state, config)
        predictions = [
            _prediction_frame(model_name, eval_frame, pred_map[model_name])
            for model_name in PREDICTION_MODELS
            if model_name in pred_map
        ]
        score_rows, _ = score_model_predictions_fast(
            _labels_for_score(eval_frame),
            pd.concat(predictions, ignore_index=True),
            _actuals_for_score(eval_frame),
            f"phase8gd_route_specific_{target_start}",
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
                "regular_rows": int(_regular_mask(eval_frame).sum()),
                "campaign_rows": int(_campaign_mask(eval_frame).sum()),
                "supplier_available_rows": int(_supplier_available_mask(eval_frame).sum()),
                **diag,
            }
        )

    score_rows = pd.concat(all_score_rows, ignore_index=True) if all_score_rows else pd.DataFrame()
    return matrix, score_rows, skipped, diagnostics, cache_path, cache_hit


def _model_rows(score_rows: pd.DataFrame, control_hit20: float | None) -> list[list[str]]:
    rows: list[list[str]] = []
    model_order = {name: idx for idx, name in enumerate(ORDERED_MODELS)}
    for model_name, group in sorted(
        score_rows.groupby("model_name", dropna=False),
        key=lambda item: model_order.get(str(item[0]), 99),
    ):
        metrics = _metrics(group)
        delta = None if metrics["hit20"] is None or control_hit20 is None else float(metrics["hit20"]) - control_hit20
        rows.append(
            [
                str(model_name),
                f"{metrics['rows']:,}",
                f"{metrics['scored']:,}",
                _fmt_pct(metrics["hit20"]),
                _fmt_pp(delta),
                _fmt_pct(metrics["hit30"]),
                _fmt_pct(metrics["wmape"]),
                _fmt_pct(metrics["bias"]),
                _fmt_pct(metrics["phantom_rate"]),
            ]
        )
    return rows


def _scope_rows(score_rows: pd.DataFrame, model_name: str) -> list[list[str]]:
    rows: list[list[str]] = []
    model_rows = score_rows[score_rows["model_name"] == model_name].copy()
    for scope_name, rank_limit in REVENUE_SCOPES:
        scoped = model_rows[_scope_mask(model_rows, rank_limit)]
        metrics = _metrics(scoped)
        rows.append(
            [
                _scope_label(scope_name),
                f"{metrics['rows']:,}",
                f"{metrics['scored']:,}",
                _fmt_num(metrics["actual_revenue"], 0),
                _fmt_pct(metrics["hit20"]),
                _fmt_pct(metrics["hit30"]),
                _fmt_pct(metrics["wmape"]),
                _fmt_pct(metrics["bias"]),
                _fmt_pct(metrics["phantom_rate"]),
            ]
        )
    return rows


def _scope_compare_rows(score_rows: pd.DataFrame, candidate_model: str) -> list[list[str]]:
    rows: list[list[str]] = []
    control_rows = score_rows[score_rows["model_name"] == PHASE8E_CONTROL].copy()
    candidate_rows = score_rows[score_rows["model_name"] == candidate_model].copy()
    for scope_name, rank_limit in REVENUE_SCOPES:
        control = _metrics(control_rows[_scope_mask(control_rows, rank_limit)])
        candidate = _metrics(candidate_rows[_scope_mask(candidate_rows, rank_limit)])
        hit_delta = (
            None
            if control["hit20"] is None or candidate["hit20"] is None
            else float(candidate["hit20"]) - float(control["hit20"])
        )
        wmape_delta = (
            None
            if control["wmape"] is None or candidate["wmape"] is None
            else float(candidate["wmape"]) - float(control["wmape"])
        )
        phantom_delta = (
            None
            if control["phantom_rate"] is None or candidate["phantom_rate"] is None
            else float(candidate["phantom_rate"]) - float(control["phantom_rate"])
        )
        rows.append(
            [
                _scope_label(scope_name),
                f"{candidate['rows']:,}",
                f"{candidate['scored']:,}",
                _fmt_num(candidate["actual_revenue"], 0),
                _fmt_pct(control["hit20"]),
                _fmt_pct(candidate["hit20"]),
                _fmt_pp(hit_delta),
                _fmt_pct(control["wmape"]),
                _fmt_pct(candidate["wmape"]),
                _fmt_pp(wmape_delta),
                _fmt_pct(control["phantom_rate"]),
                _fmt_pct(candidate["phantom_rate"]),
                _fmt_pp(phantom_delta),
            ]
        )
    return rows


def _route_rows(score_rows: pd.DataFrame, model_name: str) -> list[list[str]]:
    rows: list[list[str]] = []
    model_rows = score_rows[score_rows["model_name"] == model_name].copy()
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


def _window_rows(score_rows: pd.DataFrame, model_name: str) -> list[list[str]]:
    rows: list[list[str]] = []
    model_rows = score_rows[score_rows["model_name"] == model_name].copy()
    for target_start, group in model_rows.groupby("target_start", dropna=False):
        metrics = _metrics(group)
        rows.append(
            [
                str(target_start),
                f"{metrics['scored']:,}",
                _fmt_pct(metrics["hit20"]),
                _fmt_pct(metrics["hit30"]),
                _fmt_pct(metrics["wmape"]),
                _fmt_pct(metrics["bias"]),
                _fmt_pct(metrics["phantom_rate"]),
            ]
        )
    return rows


def _diagnostic_rows(diagnostics: list[dict[str, object]]) -> list[list[str]]:
    return [
        [
            str(row["target_start"]),
            str(row["train_windows"]),
            f"{int(row['eval_rows']):,}",
            f"{int(row['regular_rows']):,}",
            f"{int(row['campaign_rows']):,}",
            f"{int(row['supplier_available_rows']):,}",
            "yes" if row.get("regular_specialist_available") else "no",
            "yes" if row.get("campaign_specialist_available") else "no",
            "yes" if row.get("stock_specialist_available") else "no",
        ]
        for row in diagnostics
    ]


def build_report(
    matrix: pd.DataFrame,
    score_rows: pd.DataFrame,
    skipped: list[str],
    diagnostics: list[dict[str, object]],
    cache_path: Path,
    cache_hit: bool,
    revenue_rank_limit: int,
) -> str:
    if score_rows.empty:
        return "\n".join(
            [
                "# Iteration 5S - Forecast V2 Phase 8G-D Route-Specific Model",
                "",
                f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                "",
                "No scorable windows were available.",
            ]
        ) + "\n"

    control = _metrics(score_rows[score_rows["model_name"] == PHASE8E_CONTROL])
    control_hit20 = None if control["hit20"] is None else float(control["hit20"])
    candidate_metrics = []
    for model_name, group in score_rows.groupby("model_name", dropna=False):
        metrics = _metrics(group)
        candidate_metrics.append({"model_name": str(model_name), **metrics})
    candidate_metrics.sort(
        key=lambda row: (
            -1.0 if row["hit20"] is None else float(row["hit20"]),
            -1.0 if row["hit30"] is None else float(row["hit30"]),
            float("-inf") if row["wmape"] is None else -float(row["wmape"]),
        ),
        reverse=True,
    )
    raw_best_model = str(candidate_metrics[0]["model_name"])
    raw_best = _metrics(score_rows[score_rows["model_name"] == raw_best_model])
    raw_delta = None if raw_best["hit20"] is None or control["hit20"] is None else float(raw_best["hit20"]) - float(control["hit20"])
    route_candidates = [
        row for row in candidate_metrics if str(row["model_name"]).startswith("8gd_")
    ]
    route_best_model = str(route_candidates[0]["model_name"]) if route_candidates else PHASE8E_CONTROL
    route_best = _metrics(score_rows[score_rows["model_name"] == route_best_model])
    route_delta = (
        None
        if route_best["hit20"] is None or control["hit20"] is None
        else float(route_best["hit20"]) - float(control["hit20"])
    )
    route_wmape_delta = (
        None
        if route_best["wmape"] is None or control["wmape"] is None
        else float(route_best["wmape"]) - float(control["wmape"])
    )
    route_phantom_delta = (
        None
        if route_best["phantom_rate"] is None or control["phantom_rate"] is None
        else float(route_best["phantom_rate"]) - float(control["phantom_rate"])
    )
    if (
        route_delta is not None
        and route_delta >= 0.015
        and (route_wmape_delta is None or route_wmape_delta <= 0.005)
        and (route_phantom_delta is None or route_phantom_delta <= 0.005)
    ):
        verdict = "Phase 8G-D produced a promotable route-specific gain under the current gates."
    elif route_delta is not None and route_delta > 0:
        verdict = "Phase 8G-D produced a small diagnostic route-specific improvement, but it is below the promotion gate."
    else:
        verdict = "Phase 8G-D did not beat the Top 1000 route-control with a route-specific candidate."

    return "\n".join(
        [
            "# Iteration 5S - Forecast V2 Phase 8G-D Route-Specific Model",
            "",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"Route version: `{ROUTE_VERSION}`",
            "",
            "## Verdict",
            "",
            verdict,
            "",
            _table(
                ["Metric", "Top 1000 control", "Raw hit winner", "Best 8G-D route candidate"],
                [
                    ["Best model", PHASE8E_CONTROL, raw_best_model, route_best_model],
                    ["Hit +/-20", _fmt_pct(control["hit20"]), _fmt_pct(raw_best["hit20"]), _fmt_pct(route_best["hit20"])],
                    ["Delta hit +/-20", "-", _fmt_pp(raw_delta), _fmt_pp(route_delta)],
                    ["Hit +/-30", _fmt_pct(control["hit30"]), _fmt_pct(raw_best["hit30"]), _fmt_pct(route_best["hit30"])],
                    ["WMAPE", _fmt_pct(control["wmape"]), _fmt_pct(raw_best["wmape"]), _fmt_pct(route_best["wmape"])],
                    ["Bias", _fmt_pct(control["bias"]), _fmt_pct(raw_best["bias"]), _fmt_pct(route_best["bias"])],
                    ["Phantom rate", _fmt_pct(control["phantom_rate"]), _fmt_pct(raw_best["phantom_rate"]), _fmt_pct(route_best["phantom_rate"])],
                ],
            ),
            "",
            "## Aggregate Model Results",
            "",
            _table(
                ["Model", "Rows", "Qty scored", "Hit +/-20", "Delta vs control", "Hit +/-30", "WMAPE", "Bias", "Phantom rate"],
                _model_rows(score_rows, control_hit20),
            ),
            "",
            f"## Revenue Scope Deltas - {route_best_model}",
            "",
            _table(
                [
                    "Scope",
                    "Rows",
                    "Qty scored",
                    "Actual revenue",
                    "Control hit +/-20",
                    "Candidate hit +/-20",
                    "Hit delta",
                    "Control WMAPE",
                    "Candidate WMAPE",
                    "WMAPE delta",
                    "Control phantom",
                    "Candidate phantom",
                    "Phantom delta",
                ],
                _scope_compare_rows(score_rows, route_best_model),
            ),
            "",
            f"## Route Scores - {route_best_model}",
            "",
            _table(
                ["Route", "Rows", "Qty scored", "Hit +/-20", "Hit +/-30", "WMAPE", "Bias", "Phantom rate"],
                _route_rows(score_rows, route_best_model),
            ),
            "",
            f"## Window Scores - {route_best_model}",
            "",
            _table(
                ["Target start", "Qty scored", "Hit +/-20", "Hit +/-30", "WMAPE", "Bias", "Phantom rate"],
                _window_rows(score_rows, route_best_model),
            ),
            "",
            "## Training Diagnostics",
            "",
            _table(
                [
                    "Target start",
                    "Train windows",
                    "Eval rows",
                    "Regular rows",
                    "Campaign rows",
                    "Supplier available rows",
                    "Regular specialist",
                    "Campaign specialist",
                    "Stock specialist",
                ],
                _diagnostic_rows(diagnostics),
            ),
            "",
            "## Skipped Windows",
            "",
            ", ".join(f"`{window}`" for window in skipped) if skipped else "None.",
            "",
            "## Notes",
            "",
            f"- Revenue-rank limit: Top {revenue_rank_limit}. This is a high-revenue experiment, not a full-headline promotion.",
            f"- Feature matrix rows: {len(matrix):,}.",
            f"- Feature matrix cache: `{cache_path}` ({'hit' if cache_hit else 'built'}).",
            "- All model training uses only earlier target windows.",
            "- Route gates use forecast-time route labels, supplier availability features, and cleaned campaign/BF history features.",
            "- Product/program labels are not treated as campaign exposure features.",
            "- Phase 8F current snapshots remain excluded from historical backtests.",
        ]
    ) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run forecast v2 Phase 8G-D route-specific model candidates.")
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
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
        matrix, score_rows, skipped, diagnostics, cache_path, cache_hit = run_phase8gd(
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

    report = build_report(
        matrix,
        score_rows,
        skipped,
        diagnostics,
        cache_path,
        cache_hit,
        args.revenue_rank_limit,
    )
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report, encoding="utf-8")
    print(report)
    print(f"Wrote {args.report}")


if __name__ == "__main__":
    main()
