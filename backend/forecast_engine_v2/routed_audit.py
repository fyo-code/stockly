"""Phase 7A routed audit for forecast engine v2.

This rebuilds the Phase 6 walk-forward predictions in memory, attaches
forecast-time-safe route labels, and reports accuracy by route. It does not
persist predictions or change model behavior.
"""

from __future__ import annotations

import argparse
import sqlite3
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from .feature_matrix import DEFAULT_TARGET_STARTS, NUMERIC_FEATURES, CATEGORICAL_FEATURES, build_feature_matrix
    from .route_labels import ROUTE_ORDER, ROUTE_VERSION, add_route_labels
    from .scorecard import DB_PATH, ScorecardConfig, score_model_predictions_fast
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
    from feature_matrix import DEFAULT_TARGET_STARTS, NUMERIC_FEATURES, CATEGORICAL_FEATURES, build_feature_matrix
    from route_labels import ROUTE_ORDER, ROUTE_VERSION, add_route_labels
    from scorecard import DB_PATH, ScorecardConfig, score_model_predictions_fast
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
DEFAULT_REPORT = PROJECT_ROOT / "active_docs" / "ITER5E_V2_ROUTED_AUDIT.md"
PHASE6_BEST_MODEL = "sk_blend_post_bf_safe"
PHASE6_HIT20 = 0.241
PHASE6_HIT30 = 0.353
PHASE6_WMAPE = 0.561
PHASE6_PHANTOM = 0.481


def _fmt_pct(value: object) -> str:
    if value is None or pd.isna(value):
        return "-"
    return f"{float(value) * 100:.1f}%"


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
        "zero_actual": int(len(zero_actual)),
        "actual_units": actual_sum,
        "pred_units": pred_sum,
        "actual_revenue": float(group["actual_revenue"].sum()),
        "hit20": float(scored["hit20"].mean()) if not scored.empty else None,
        "hit30": float(scored["hit30"].mean()) if not scored.empty else None,
        "wmape": float(scored["abs_error"].sum() / actual_sum) if actual_sum > 0 else None,
        "bias": float(scored["signed_error"].sum() / actual_sum) if actual_sum > 0 else None,
        "phantom_rate": float(zero_actual["phantom"].mean()) if len(zero_actual) else None,
    }


def _score_phase6_rows(
    matrix: pd.DataFrame,
    target_starts: list[str],
    min_train_windows: int,
    random_state: int,
    config: ScorecardConfig,
) -> tuple[pd.DataFrame, list[str]]:
    all_score_rows: list[pd.DataFrame] = []
    skipped: list[str] = []

    route_cols = [
        "sku_id",
        "target_start",
        "primary_route",
        "availability_confidence",
        "intermittency_bucket",
        "route_reason",
        "route_signal_status",
        "scoring_policy_routed",
        "route_version",
        "calendar_route_context",
        "sku_bf_contamination_context",
    ]

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

        fitted_eval: dict[str, np.ndarray] = {}
        for model_name, estimator in _model_registry(random_state).items():
            pipeline = _fit_pipeline(estimator)
            pipeline.fit(x_train, y_train)
            raw_train_pred = np.clip(pipeline.predict(x_train), 0.0, None)
            post = _tune_postprocess(y_train, raw_train_pred, config.material_units_threshold)
            raw_eval_pred = np.clip(pipeline.predict(x_eval), 0.0, None)
            eval_pred = _apply_postprocess(raw_eval_pred, post)
            fitted_eval[model_name] = eval_pred
            predictions.append(_prediction_frame(model_name, eval_frame, eval_pred))

        blend_inputs = [
            fitted_eval["sk_hgb_poisson"],
            fitted_eval["sk_extra_trees"],
            eval_frame["median_naive"].to_numpy(dtype=float),
        ]
        blend_pred = np.nanmedian(np.vstack(blend_inputs), axis=0)
        predictions.append(_prediction_frame("sk_blend_median", eval_frame, blend_pred))

        post_bf_safe_naive = _post_bf_safe_naive(eval_frame)
        predictions.append(_prediction_frame("post_bf_safe_naive", eval_frame, post_bf_safe_naive))
        safe_blend_inputs = [
            _cap_post_bf_predictions(fitted_eval["sk_hgb_poisson"], eval_frame),
            _cap_post_bf_predictions(fitted_eval["sk_extra_trees"], eval_frame),
            post_bf_safe_naive,
        ]
        safe_blend_pred = np.nanmedian(np.vstack(safe_blend_inputs), axis=0)
        predictions.append(_prediction_frame(PHASE6_BEST_MODEL, eval_frame, safe_blend_pred))

        run_id = f"routed_audit_phase6_{target_start}"
        score_rows, _ = score_model_predictions_fast(
            _labels_for_score(eval_frame),
            pd.concat(predictions, ignore_index=True),
            _actuals_for_score(eval_frame),
            run_id,
            config=config,
            baseline_predictions=_baseline_predictions(eval_frame),
        )
        score_rows["target_start"] = target_start
        score_rows = score_rows.merge(eval_frame[route_cols], on=["sku_id", "target_start"], how="left")
        all_score_rows.append(score_rows)

    combined = pd.concat(all_score_rows, ignore_index=True) if all_score_rows else pd.DataFrame()
    return combined, skipped


def _metrics_table(
    rows: pd.DataFrame,
    group_col: str,
    total_revenue: float,
    order: list[str] | None = None,
) -> list[list[str]]:
    output = []
    grouped = rows.groupby(group_col, dropna=False)
    keys = list(grouped.groups)
    if order:
        keys = [key for key in order if key in grouped.groups] + [key for key in keys if key not in order]
    for key in keys:
        group = grouped.get_group(key)
        metrics = _metrics(group)
        revenue_share = metrics["actual_revenue"] / total_revenue if total_revenue else None
        output.append(
            [
                str(key),
                f"{metrics['rows']:,}",
                f"{metrics['scored']:,}",
                _fmt_pct(revenue_share),
                _fmt_num(metrics["actual_units"]),
                _fmt_pct(metrics["hit20"]),
                _fmt_pct(metrics["hit30"]),
                _fmt_pct(metrics["wmape"]),
                _fmt_pct(metrics["bias"]),
                _fmt_pct(metrics["phantom_rate"]),
            ]
        )
    return output


def build_report(matrix: pd.DataFrame, score_rows: pd.DataFrame, skipped: list[str]) -> str:
    best = score_rows[score_rows["model_name"] == PHASE6_BEST_MODEL].copy()
    median = score_rows[score_rows["model_name"] == "median_naive"].copy()
    total_revenue = float(best["actual_revenue"].sum()) if not best.empty else 0.0
    aggregate_best = _metrics(best)
    aggregate_median = _metrics(median)

    route_rows = _metrics_table(best, "primary_route", total_revenue, ROUTE_ORDER)
    availability_rows = _metrics_table(best, "availability_confidence", total_revenue)
    intermittency_rows = _metrics_table(best, "intermittency_bucket", total_revenue)

    model_rows = []
    for model_name, group in score_rows.groupby("model_name"):
        metrics = _metrics(group)
        model_rows.append(
            [
                str(model_name),
                f"{metrics['rows']:,}",
                f"{metrics['scored']:,}",
                _fmt_pct(metrics["hit20"]),
                _fmt_pct(metrics["hit30"]),
                _fmt_pct(metrics["wmape"]),
                _fmt_pct(metrics["bias"]),
                _fmt_pct(metrics["phantom_rate"]),
            ]
        )
    model_rows.sort(key=lambda row: (row[0] != PHASE6_BEST_MODEL, row[0]))

    window_rows = []
    for (target_start, route), group in best.groupby(["target_start", "primary_route"], dropna=False):
        metrics = _metrics(group)
        if metrics["scored"] < 30:
            continue
        window_rows.append(
            [
                str(target_start),
                str(route),
                f"{metrics['scored']:,}",
                _fmt_pct(metrics["hit20"]),
                _fmt_pct(metrics["wmape"]),
                _fmt_pct(metrics["bias"]),
            ]
        )
    window_rows.sort(key=lambda row: (row[0], row[1]))

    available_mask = best["primary_route"].isin(["available_regular", "proxy_available_regular"])
    available_metrics = _metrics(best[available_mask])
    bf_metrics = _metrics(best[best["primary_route"] == "bf_campaign_sensitive"])
    stock_metrics = _metrics(best[best["primary_route"] == "stock_constrained"])

    if available_metrics["hit20"] is None:
        decision = "Available-mover hit +/-20 cannot be judged yet because no route has enough scored rows."
    elif available_metrics["hit20"] < 0.35:
        decision = (
            "Available-mover hit +/-20 is below 35%, so Phase 7B should improve the regular/proxy-available model path, "
            "not only stock/BF handling."
        )
    else:
        decision = (
            "Available-mover hit +/-20 is materially higher than the blended headline, so mixed/censored population is a major cause of low headline accuracy."
        )

    return "\n".join(
        [
            "# Iteration 5E — V2 Routed Audit",
            "",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"Route version: `{ROUTE_VERSION}`",
            "",
            "## Phase Checkpoint",
            "",
            "Phase completed: Phase 7A — Routed Audit",
            "",
            "What changed: added forecast-time route labels and sliced the existing Phase 6 model performance by route.",
            "",
            "Accuracy rerun: no new model behavior. Phase 6 predictions were rebuilt in memory only to attach route labels.",
            "",
            _table(
                ["Metric", "Phase 6 baseline", "Phase 7A routed audit reproduction"],
                [
                    ["Best model", PHASE6_BEST_MODEL, PHASE6_BEST_MODEL],
                    ["Hit +/-20", _fmt_pct(PHASE6_HIT20), _fmt_pct(aggregate_best["hit20"])],
                    ["Hit +/-30", _fmt_pct(PHASE6_HIT30), _fmt_pct(aggregate_best["hit30"])],
                    ["WMAPE", _fmt_pct(PHASE6_WMAPE), _fmt_pct(aggregate_best["wmape"])],
                    ["Phantom rate", _fmt_pct(PHASE6_PHANTOM), _fmt_pct(aggregate_best["phantom_rate"])],
                ],
            ),
            "",
            "## Model Reproduction Check",
            "",
            _table(
                ["Model", "Rows", "Qty scored", "Hit +/-20", "Hit +/-30", "WMAPE", "Bias", "Phantom rate"],
                model_rows,
            ),
            "",
            "## Route Accuracy",
            "",
            _table(
                [
                    "Route",
                    "Rows",
                    "Qty scored",
                    "Revenue share all rows",
                    "Scored actual units",
                    "Hit +/-20",
                    "Hit +/-30",
                    "WMAPE",
                    "Bias",
                    "Phantom rate",
                ],
                route_rows,
            ),
            "",
            "## Availability Accuracy",
            "",
            _table(
                [
                    "Availability",
                    "Rows",
                    "Qty scored",
                    "Revenue share all rows",
                    "Scored actual units",
                    "Hit +/-20",
                    "Hit +/-30",
                    "WMAPE",
                    "Bias",
                    "Phantom rate",
                ],
                availability_rows,
            ),
            "",
            "## Intermittency Accuracy",
            "",
            _table(
                [
                    "Intermittency",
                    "Rows",
                    "Qty scored",
                    "Revenue share all rows",
                    "Scored actual units",
                    "Hit +/-20",
                    "Hit +/-30",
                    "WMAPE",
                    "Bias",
                    "Phantom rate",
                ],
                intermittency_rows,
            ),
            "",
            "## Route Window Details",
            "",
            _table(["Target start", "Route", "Qty scored", "Hit +/-20", "WMAPE", "Bias"], window_rows),
            "",
            "## Decision Gate",
            "",
            _table(
                ["Slice", "Hit +/-20", "WMAPE", "Phantom rate"],
                [
                    ["available + proxy available", _fmt_pct(available_metrics["hit20"]), _fmt_pct(available_metrics["wmape"]), _fmt_pct(available_metrics["phantom_rate"])],
                    ["BF/campaign sensitive", _fmt_pct(bf_metrics["hit20"]), _fmt_pct(bf_metrics["wmape"]), _fmt_pct(bf_metrics["phantom_rate"])],
                    ["stock constrained", _fmt_pct(stock_metrics["hit20"]), _fmt_pct(stock_metrics["wmape"]), _fmt_pct(stock_metrics["phantom_rate"])],
                ],
            ),
            "",
            decision,
            "",
            "## Skipped Windows",
            "",
            ", ".join(f"`{window}`" for window in skipped) if skipped else "None.",
            "",
            "## Notes",
            "",
            f"- Matrix rows routed: {len(matrix):,}.",
            "- Route labels use only pre-target features from the existing feature matrix.",
            "- Current snapshot stock remains excluded from historical backtests.",
            "- Route accuracy is shown for the current Phase 6 best model unless stated otherwise.",
            "",
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run forecast v2 routed audit.")
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--target-start", action="append", default=None)
    parser.add_argument("--min-train-windows", type=int, default=4)
    parser.add_argument("--random-state", type=int, default=42)
    args = parser.parse_args()

    config = ScorecardConfig()
    conn = sqlite3.connect(args.db)
    try:
        matrix = build_feature_matrix(
            conn,
            target_starts=args.target_start or DEFAULT_TARGET_STARTS,
            population="headline",
            config=config,
        )
    finally:
        conn.close()

    routed_matrix = add_route_labels(matrix)
    score_rows, skipped = _score_phase6_rows(
        routed_matrix,
        target_starts=args.target_start or DEFAULT_TARGET_STARTS,
        min_train_windows=args.min_train_windows,
        random_state=args.random_state,
        config=config,
    )

    report = build_report(routed_matrix, score_rows, skipped)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report, encoding="utf-8")
    print(report)
    print(f"Wrote {args.report}")


if __name__ == "__main__":
    main()
