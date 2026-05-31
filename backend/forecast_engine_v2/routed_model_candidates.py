"""Phase 7B routed model candidates for forecast engine v2.

This runner keeps the Phase 6 global model as the control and tests
forecast-time-safe routed candidates. Candidate routing only uses the current
feature snapshot plus earlier target-window performance.
"""

from __future__ import annotations

import argparse
import sqlite3
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
DEFAULT_REPORT = PROJECT_ROOT / "active_docs" / "ITER5F_V2_ROUTED_MODEL_CANDIDATES.md"
PHASE6_CONTROL = "sk_blend_post_bf_safe"
REGULAR_ROUTES = {"available_regular", "proxy_available_regular"}
SELECTOR_POOL = [
    "median_naive",
    "post_bf_safe_naive",
    "sk_hgb_poisson",
    "sk_hgb_squared",
    "sk_extra_trees",
    "sk_blend_median",
    PHASE6_CONTROL,
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


def _table(headers: list[str], rows: list[list[str]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(lines)


def _metrics(group: pd.DataFrame) -> dict[str, object]:
    scored = group[group["quantity_scored"] == 1]
    actual_sum = float(scored["actual_units"].sum())
    pred_sum = float(scored["pred_units"].sum())
    zero_actual = group[group["actual_units"] == 0]
    return {
        "rows": int(len(group)),
        "scored": int(len(scored)),
        "actual_units": actual_sum,
        "pred_units": pred_sum,
        "hit20": float(scored["hit20"].mean()) if not scored.empty else None,
        "hit30": float(scored["hit30"].mean()) if not scored.empty else None,
        "wmape": float(scored["abs_error"].sum() / actual_sum) if actual_sum > 0 else None,
        "bias": float(scored["signed_error"].sum() / actual_sum) if actual_sum > 0 else None,
        "phantom_rate": float(zero_actual["phantom"].mean()) if len(zero_actual) else None,
    }


def _chronological_target_starts(target_starts: list[str]) -> list[str]:
    """Return target starts in chronological order to keep prior-window routing leak-safe."""

    parsed = [(pd.Timestamp(value), value) for value in target_starts]
    return [value for _, value in sorted(parsed, key=lambda item: item[0])]


def _route_cols(frame: pd.DataFrame) -> list[str]:
    candidates = [
        "sku_id",
        "target_start",
        "primary_route",
        "availability_confidence",
        "intermittency_bucket",
        "route_signal_status",
        "calendar_route_context",
        "sku_bf_contamination_context",
    ]
    return [col for col in candidates if col in frame.columns]


def _fit_route_specialist(
    train: pd.DataFrame,
    eval_frame: pd.DataFrame,
    estimator: object,
    route_values: set[str],
    random_state: int,
    config: ScorecardConfig,
) -> np.ndarray | None:
    del random_state
    train_mask = train["primary_route"].isin(route_values)
    routed_train = train[train_mask].copy()
    if routed_train["target_start"].nunique() < 3 or len(routed_train) < 300:
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


def _best_prior_model_by_route(prior_rows: pd.DataFrame, min_scored: int) -> dict[str, str]:
    if prior_rows.empty:
        return {}
    prior = prior_rows[prior_rows["model_name"].isin(SELECTOR_POOL)].copy()
    if prior.empty:
        return {}

    selections: dict[str, str] = {}
    for route, route_rows in prior.groupby("primary_route", dropna=False):
        candidates: list[tuple[float, float, float, str]] = []
        for model_name, group in route_rows.groupby("model_name"):
            metrics = _metrics(group)
            if metrics["scored"] < min_scored or metrics["hit20"] is None:
                continue
            wmape = metrics["wmape"] if metrics["wmape"] is not None else float("inf")
            phantom = metrics["phantom_rate"] if metrics["phantom_rate"] is not None else float("inf")
            candidates.append((float(metrics["hit20"]), -float(wmape), -float(phantom), str(model_name)))
        if candidates:
            candidates.sort(reverse=True)
            selections[str(route)] = candidates[0][3]
    return selections


def _prior_bias_factor_by_route(prior_rows: pd.DataFrame, model_name: str, min_scored: int) -> dict[str, float]:
    if prior_rows.empty:
        return {}
    model_rows = prior_rows[prior_rows["model_name"] == model_name].copy()
    factors: dict[str, float] = {}
    for route, group in model_rows.groupby("primary_route", dropna=False):
        scored = group[group["quantity_scored"] == 1]
        if len(scored) < min_scored:
            continue
        pred_sum = float(scored["pred_units"].sum())
        actual_sum = float(scored["actual_units"].sum())
        if pred_sum <= 0 or actual_sum <= 0:
            continue
        factors[str(route)] = float(np.clip(actual_sum / pred_sum, 0.70, 1.30))
    return factors


def _route_prior_best_prediction(
    eval_frame: pd.DataFrame,
    pred_map: dict[str, np.ndarray],
    selections: dict[str, str],
) -> np.ndarray:
    pred = pred_map[PHASE6_CONTROL].copy()
    for route, model_name in selections.items():
        if model_name not in pred_map:
            continue
        mask = (eval_frame["primary_route"] == route).to_numpy(dtype=bool)
        pred[mask] = pred_map[model_name][mask]
    return np.clip(pred, 0.0, None)


def _route_prior_calibrated_prediction(
    eval_frame: pd.DataFrame,
    base_pred: np.ndarray,
    factors: dict[str, float],
) -> np.ndarray:
    pred = base_pred.copy()
    for route, factor in factors.items():
        mask = (eval_frame["primary_route"] == route).to_numpy(dtype=bool)
        pred[mask] = pred[mask] * factor
    return np.clip(pred, 0.0, None)


def _build_predictions_for_window(
    train: pd.DataFrame,
    eval_frame: pd.DataFrame,
    prior_rows: pd.DataFrame,
    random_state: int,
    config: ScorecardConfig,
) -> tuple[list[pd.DataFrame], dict[str, object]]:
    x_train = train[NUMERIC_FEATURES + CATEGORICAL_FEATURES]
    y_train = train[TARGET_COL].to_numpy(dtype=float)
    x_eval = eval_frame[NUMERIC_FEATURES + CATEGORICAL_FEATURES]

    pred_map: dict[str, np.ndarray] = {
        "median_naive": eval_frame["median_naive"].fillna(0.0).clip(lower=0.0).to_numpy(dtype=float),
    }
    predictions: list[pd.DataFrame] = []
    diagnostics: dict[str, object] = {}

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

    blend_inputs = [
        fitted_eval["sk_hgb_poisson"],
        fitted_eval["sk_extra_trees"],
        pred_map["median_naive"],
    ]
    pred_map["sk_blend_median"] = np.nanmedian(np.vstack(blend_inputs), axis=0)
    predictions.append(_prediction_frame("sk_blend_median", eval_frame, pred_map["sk_blend_median"]))

    pred_map["post_bf_safe_naive"] = _post_bf_safe_naive(eval_frame)
    predictions.append(_prediction_frame("post_bf_safe_naive", eval_frame, pred_map["post_bf_safe_naive"]))

    safe_blend_inputs = [
        _cap_post_bf_predictions(fitted_eval["sk_hgb_poisson"], eval_frame),
        _cap_post_bf_predictions(fitted_eval["sk_extra_trees"], eval_frame),
        pred_map["post_bf_safe_naive"],
    ]
    pred_map[PHASE6_CONTROL] = np.nanmedian(np.vstack(safe_blend_inputs), axis=0)
    predictions.append(_prediction_frame(PHASE6_CONTROL, eval_frame, pred_map[PHASE6_CONTROL]))

    registry = _model_registry(random_state)
    specialist_extra = _fit_route_specialist(
        train,
        eval_frame,
        registry["sk_extra_trees"],
        REGULAR_ROUTES,
        random_state,
        config,
    )
    specialist_poisson = _fit_route_specialist(
        train,
        eval_frame,
        registry["sk_hgb_poisson"],
        REGULAR_ROUTES,
        random_state,
        config,
    )

    regular_mask = eval_frame["primary_route"].isin(REGULAR_ROUTES).to_numpy(dtype=bool)
    if specialist_extra is not None:
        pred = pred_map[PHASE6_CONTROL].copy()
        pred[regular_mask] = specialist_extra[regular_mask]
        predictions.append(_prediction_frame("route_regular_extra_trees", eval_frame, pred))

    specialist_blend_inputs = [
        arr
        for arr in (specialist_extra, specialist_poisson, pred_map["sk_extra_trees"], pred_map["median_naive"])
        if arr is not None
    ]
    if specialist_blend_inputs:
        regular_blend = np.nanmedian(np.vstack(specialist_blend_inputs), axis=0)
        pred = pred_map[PHASE6_CONTROL].copy()
        pred[regular_mask] = regular_blend[regular_mask]
        predictions.append(_prediction_frame("route_regular_specialist_blend", eval_frame, pred))

    selections = _best_prior_model_by_route(prior_rows, min_scored=60)
    prior_best = _route_prior_best_prediction(eval_frame, pred_map, selections)
    predictions.append(_prediction_frame("route_prior_best_model", eval_frame, prior_best))
    diagnostics["prior_model_selections"] = selections

    factors = _prior_bias_factor_by_route(prior_rows, PHASE6_CONTROL, min_scored=60)
    prior_calibrated = _route_prior_calibrated_prediction(eval_frame, pred_map[PHASE6_CONTROL], factors)
    predictions.append(_prediction_frame("route_prior_bias_calibrated", eval_frame, prior_calibrated))
    diagnostics["prior_bias_factors"] = factors

    return predictions, diagnostics


def run_routed_candidates(
    conn: sqlite3.Connection,
    target_starts: list[str],
    min_train_windows: int,
    random_state: int,
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
        train = matrix[matrix["target_start"] < target_start].copy()
        eval_frame = matrix[matrix["target_start"] == target_start].copy()
        if train["target_start"].nunique() < min_train_windows or eval_frame.empty:
            skipped.append(target_start)
            continue

        prior_rows = pd.concat(all_score_rows, ignore_index=True) if all_score_rows else pd.DataFrame()
        if not prior_rows.empty:
            prior_rows = prior_rows[pd.to_datetime(prior_rows["target_start"]) < pd.Timestamp(target_start)].copy()
        predictions, window_diag = _build_predictions_for_window(
            train,
            eval_frame,
            prior_rows,
            random_state,
            config,
        )
        run_id = f"routed_candidates_v1_{target_start}"
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
                **window_diag,
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
    output: list[dict[str, object]] = []
    for model_name, group in score_rows.groupby("model_name"):
        metrics = _metrics(group)
        output.append({"model_name": str(model_name), **metrics})
    output.sort(
        key=lambda row: (
            -1.0 if row["hit20"] is None else float(row["hit20"]),
            -1.0 if row["hit30"] is None else float(row["hit30"]),
            float("-inf") if row["wmape"] is None else -float(row["wmape"]),
            float("-inf") if row["phantom_rate"] is None else -float(row["phantom_rate"]),
        ),
        reverse=True,
    )
    return output


def _model_metric_rows(score_rows: pd.DataFrame, control_hit20: float | None) -> list[list[str]]:
    output = []
    for row in _model_metrics(score_rows):
        delta = None if row["hit20"] is None or control_hit20 is None else float(row["hit20"]) - control_hit20
        output.append(
            [
                str(row["model_name"]),
                f"{int(row['rows']):,}",
                f"{int(row['scored']):,}",
                _fmt_pct(row["hit20"]),
                _fmt_pp(delta),
                _fmt_pct(row["hit30"]),
                _fmt_pct(row["wmape"]),
                _fmt_pct(row["bias"]),
                _fmt_pct(row["phantom_rate"]),
            ]
        )
    return output


def _route_metric_rows(score_rows: pd.DataFrame, model_name: str) -> list[list[str]]:
    rows = []
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
    rows = []
    model_rows = score_rows[score_rows["model_name"] == model_name].copy()
    for target_start, group in model_rows.groupby("target_start"):
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
    rows = []
    for diag in diagnostics:
        selections = diag.get("prior_model_selections") or {}
        factors = diag.get("prior_bias_factors") or {}
        rows.append(
            [
                str(diag["target_start"]),
                str(diag["train_windows"]),
                f"{int(diag['eval_rows']):,}",
                ", ".join(f"{route}:{model}" for route, model in sorted(selections.items())) or "-",
                ", ".join(f"{route}:{float(factor):.2f}" for route, factor in sorted(factors.items())) or "-",
            ]
        )
    return rows


def build_report(
    matrix: pd.DataFrame,
    score_rows: pd.DataFrame,
    aggregate_slices: pd.DataFrame,
    skipped: list[str],
    diagnostics: list[dict[str, object]],
) -> str:
    del aggregate_slices
    if score_rows.empty or "model_name" not in score_rows.columns:
        return "\n".join(
            [
                "# Iteration 5F — V2 Routed Model Candidates",
                "",
                f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                f"Route version: `{ROUTE_VERSION}`",
                "",
                "## Phase Checkpoint",
                "",
                "Phase completed: Phase 7B — Routed model candidates",
                "",
                "Accuracy rerun: no scorable windows. All requested windows were skipped.",
                "",
                "## Skipped Windows",
                "",
                ", ".join(f"`{window}`" for window in skipped) if skipped else "None.",
                "",
            ]
        )

    control_metrics = _metrics(score_rows[score_rows["model_name"] == PHASE6_CONTROL])
    control_hit20 = None if control_metrics["hit20"] is None else float(control_metrics["hit20"])
    model_metric_dicts = _model_metrics(score_rows)
    model_rows = _model_metric_rows(score_rows, control_hit20)
    best_model = str(model_metric_dicts[0]["model_name"]) if model_metric_dicts else PHASE6_CONTROL
    best_metrics = _metrics(score_rows[score_rows["model_name"] == best_model])
    available_best = _metrics(
        score_rows[
            (score_rows["model_name"] == best_model)
            & score_rows["primary_route"].isin(REGULAR_ROUTES)
        ]
    )
    available_control = _metrics(
        score_rows[
            (score_rows["model_name"] == PHASE6_CONTROL)
            & score_rows["primary_route"].isin(REGULAR_ROUTES)
        ]
    )

    if best_metrics["hit20"] is None:
        verdict = "Phase 7B did not produce a scorable candidate."
    elif best_metrics["hit20"] <= control_metrics["hit20"]:
        verdict = (
            "Phase 7B did not improve headline hit +/-20. Keep the diagnostics, but do not promote the routed candidate."
        )
    else:
        verdict = (
            f"Phase 7B improved headline hit +/-20 by "
            f"{_fmt_pp(float(best_metrics['hit20']) - float(control_metrics['hit20']))} versus the Phase 6 control."
        )

    return "\n".join(
        [
            "# Iteration 5F — V2 Routed Model Candidates",
            "",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"Route version: `{ROUTE_VERSION}`",
            "",
            "## Phase Checkpoint",
            "",
            "Phase completed: Phase 7B — Routed model candidates",
            "",
            "What changed: added route-specific candidate predictions on top of the Phase 6 global model.",
            "",
            "Accuracy rerun: yes. The same walk-forward windows were rebuilt with new routed candidates.",
            "",
            _table(
                ["Metric", "Phase 6 control", "Phase 7B best"],
                [
                    ["Best model", PHASE6_CONTROL, best_model],
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
                ["Model", "Rows", "Qty scored", "Hit +/-20", "Delta vs Phase 6", "Hit +/-30", "WMAPE", "Bias", "Phantom rate"],
                model_rows,
            ),
            "",
            "## Available / Proxy-Regular Slice",
            "",
            _table(
                ["Metric", "Phase 6 control", "Phase 7B best"],
                [
                    ["Qty scored", f"{available_control['scored']:,}", f"{available_best['scored']:,}"],
                    ["Hit +/-20", _fmt_pct(available_control["hit20"]), _fmt_pct(available_best["hit20"])],
                    ["Delta hit +/-20", "-", _fmt_pp(float(available_best["hit20"] or 0) - float(available_control["hit20"] or 0))],
                    ["Hit +/-30", _fmt_pct(available_control["hit30"]), _fmt_pct(available_best["hit30"])],
                    ["WMAPE", _fmt_pct(available_control["wmape"]), _fmt_pct(available_best["wmape"])],
                    ["Phantom rate", _fmt_pct(available_control["phantom_rate"]), _fmt_pct(available_best["phantom_rate"])],
                ],
            ),
            "",
            f"## Route Accuracy — {best_model}",
            "",
            _table(
                ["Route", "Rows", "Qty scored", "Hit +/-20", "Hit +/-30", "WMAPE", "Bias", "Phantom rate"],
                _route_metric_rows(score_rows, best_model),
            ),
            "",
            f"## Window Accuracy — {best_model}",
            "",
            _table(
                ["Target start", "Qty scored", "Hit +/-20", "Hit +/-30", "WMAPE", "Bias", "Phantom rate"],
                _window_rows(score_rows, best_model),
            ),
            "",
            "## Online Routing Diagnostics",
            "",
            _table(
                ["Target start", "Train windows", "Eval rows", "Prior route model choices", "Prior route bias factors"],
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
            "- Specialist routes use only rows whose route label is known before the target window.",
            "- `route_prior_best_model` chooses route/model mappings only from earlier scored target windows.",
            "- `route_prior_bias_calibrated` learns route correction factors only from earlier scored target windows.",
            "- Current snapshot stock remains excluded from historical backtests.",
            "",
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run forecast v2 routed model candidates.")
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--target-start", action="append", default=None)
    parser.add_argument("--min-train-windows", type=int, default=4)
    parser.add_argument("--random-state", type=int, default=42)
    args = parser.parse_args()

    config = ScorecardConfig()
    conn = sqlite3.connect(args.db)
    try:
        matrix, score_rows, aggregate, skipped, diagnostics = run_routed_candidates(
            conn,
            target_starts=args.target_start or DEFAULT_TARGET_STARTS,
            min_train_windows=args.min_train_windows,
            random_state=args.random_state,
            config=config,
        )
    finally:
        conn.close()

    report = build_report(matrix, score_rows, aggregate, skipped, diagnostics)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report, encoding="utf-8")
    print(report)
    print(f"Wrote {args.report}")


if __name__ == "__main__":
    main()
