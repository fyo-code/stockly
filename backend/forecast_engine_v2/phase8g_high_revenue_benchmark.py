"""Phase 8G-A high-revenue benchmark for forecast engine v2.

This report does not introduce a new model. It rebuilds the current
availability-aware sklearn V2 predictions in memory, attaches leak-safe route
labels, and slices performance by high-revenue scope.
"""

from __future__ import annotations

import argparse
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd

try:
    from .feature_matrix import DEFAULT_TARGET_STARTS, build_feature_matrix
    from .route_labels import ROUTE_ORDER, ROUTE_VERSION, add_route_labels
    from .routed_audit import PHASE6_BEST_MODEL, _score_phase6_rows
    from .scorecard import DB_PATH, ScorecardConfig
except ImportError:  # Allows direct script execution.
    from feature_matrix import DEFAULT_TARGET_STARTS, build_feature_matrix
    from route_labels import ROUTE_ORDER, ROUTE_VERSION, add_route_labels
    from routed_audit import PHASE6_BEST_MODEL, _score_phase6_rows
    from scorecard import DB_PATH, ScorecardConfig


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REPORT = PROJECT_ROOT / "active_docs" / "ITER5P_V2_PHASE8G_HIGH_REVENUE_BENCHMARK.md"

PHASE8E_CONTROL = "sk_blend_post_bf_safe"
PHASE8E_CONTROL_HIT20 = 0.242
PHASE8E_CONTROL_WMAPE = 0.556
PHASE8E_CONTROL_PHANTOM = 0.444

REVENUE_SCOPES = [
    ("top_100", 100),
    ("top_500", 500),
    ("top_1000", 1000),
    ("top_5000", 5000),
    ("full_headline", None),
]

ORDERED_MODELS = [
    "median_naive",
    "post_bf_safe_naive",
    "sk_hgb_poisson",
    "sk_hgb_squared",
    "sk_extra_trees",
    "sk_blend_median",
    "sk_blend_post_bf_safe",
]

REGULAR_ROUTES = {"available_regular", "proxy_available_regular"}


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


def _metrics(rows: pd.DataFrame) -> dict[str, object]:
    scored = rows[rows["quantity_scored"] == 1]
    zero_actual = rows[rows["actual_units"] == 0]
    actual_units = float(scored["actual_units"].sum())
    actual_revenue = float(rows["actual_revenue"].sum())
    abs_error = float(scored["abs_error"].sum())
    signed_error = float(scored["signed_error"].sum())
    return {
        "rows": int(len(rows)),
        "scored": int(len(scored)),
        "zero_actual": int(len(zero_actual)),
        "actual_units": actual_units,
        "actual_revenue": actual_revenue,
        "pred_units": float(scored["pred_units"].sum()),
        "hit20": float(scored["hit20"].mean()) if not scored.empty else None,
        "hit30": float(scored["hit30"].mean()) if not scored.empty else None,
        "wmape": abs_error / actual_units if actual_units > 0 else None,
        "bias": signed_error / actual_units if actual_units > 0 else None,
        "phantom_rate": float(zero_actual["phantom"].mean()) if len(zero_actual) else None,
    }


def _scope_mask(rows: pd.DataFrame, rank_limit: int | None) -> pd.Series:
    if rank_limit is None:
        return pd.Series(True, index=rows.index)
    return pd.to_numeric(rows["revenue_rank"], errors="coerce") <= rank_limit


def _scope_label(scope_name: str) -> str:
    return {
        "top_100": "Top 100",
        "top_500": "Top 500",
        "top_1000": "Top 1000",
        "top_5000": "Top 5000",
        "full_headline": "Full headline",
    }.get(scope_name, scope_name)


def _append_matrix_columns(score_rows: pd.DataFrame, matrix: pd.DataFrame) -> pd.DataFrame:
    if score_rows.empty:
        return score_rows

    cols = [
        "sku_id",
        "target_start",
        "revenue_rank",
        "trailing_52w_revenue",
        "trailing_52w_pos_units",
        "avg_units_per_4w_52",
        "primary_route",
        "availability_confidence",
        "intermittency_bucket",
        "calendar_route_context",
        "sku_bf_contamination_context",
        "route_signal_status",
        "combined_stock_observed_prev_month",
        "store_or_supplier_available_before_target",
        "likely_true_stockout_before_target",
    ]
    available_cols = [
        col
        for col in cols
        if col in matrix.columns and (col in {"sku_id", "target_start"} or col not in score_rows.columns)
    ]
    enrich = matrix[available_cols].drop_duplicates(["sku_id", "target_start"])
    return score_rows.merge(enrich, on=["sku_id", "target_start"], how="left")


def _model_scope_rows(score_rows: pd.DataFrame) -> list[list[str]]:
    rows: list[list[str]] = []
    model_order = {name: idx for idx, name in enumerate(ORDERED_MODELS)}
    for scope_name, rank_limit in REVENUE_SCOPES:
        scoped = score_rows[_scope_mask(score_rows, rank_limit)]
        for model_name, group in sorted(
            scoped.groupby("model_name", dropna=False),
            key=lambda item: model_order.get(str(item[0]), 99),
        ):
            metrics = _metrics(group)
            rows.append(
                [
                    _scope_label(scope_name),
                    str(model_name),
                    f"{metrics['rows']:,}",
                    f"{metrics['scored']:,}",
                    _fmt_num(metrics["actual_revenue"], 0),
                    _fmt_num(metrics["actual_units"]),
                    _fmt_pct(metrics["hit20"]),
                    _fmt_pct(metrics["hit30"]),
                    _fmt_pct(metrics["wmape"]),
                    _fmt_pct(metrics["bias"]),
                    _fmt_pct(metrics["phantom_rate"]),
                ]
            )
    return rows


def _control_scope_rows(best_rows: pd.DataFrame) -> list[list[str]]:
    rows: list[list[str]] = []
    for scope_name, rank_limit in REVENUE_SCOPES:
        scoped = best_rows[_scope_mask(best_rows, rank_limit)]
        metrics = _metrics(scoped)
        rows.append(
            [
                _scope_label(scope_name),
                f"{metrics['rows']:,}",
                f"{metrics['scored']:,}",
                _fmt_num(metrics["actual_revenue"], 0),
                _fmt_num(metrics["actual_units"]),
                _fmt_pct(metrics["hit20"]),
                _fmt_pct(metrics["hit20"] - PHASE8E_CONTROL_HIT20 if metrics["hit20"] is not None else None),
                _fmt_pct(metrics["wmape"]),
                _fmt_pct(metrics["bias"]),
                _fmt_pct(metrics["phantom_rate"]),
            ]
        )
    return rows


def _group_rows(
    best_rows: pd.DataFrame,
    group_col: str,
    order: list[str] | None = None,
    min_scored: int = 0,
) -> list[list[str]]:
    rows: list[list[str]] = []
    for scope_name, rank_limit in REVENUE_SCOPES:
        scoped = best_rows[_scope_mask(best_rows, rank_limit)]
        grouped = scoped.groupby(group_col, dropna=False)
        keys = list(grouped.groups)
        if order:
            keys = [key for key in order if key in grouped.groups] + [key for key in keys if key not in order]
        for key in keys:
            group = grouped.get_group(key)
            metrics = _metrics(group)
            if metrics["scored"] < min_scored:
                continue
            rows.append(
                [
                    _scope_label(scope_name),
                    str(key),
                    f"{metrics['rows']:,}",
                    f"{metrics['scored']:,}",
                    _fmt_num(metrics["actual_revenue"], 0),
                    _fmt_num(metrics["actual_units"]),
                    _fmt_pct(metrics["hit20"]),
                    _fmt_pct(metrics["hit30"]),
                    _fmt_pct(metrics["wmape"]),
                    _fmt_pct(metrics["bias"]),
                    _fmt_pct(metrics["phantom_rate"]),
                ]
            )
    return rows


def _clean_regular_mask(rows: pd.DataFrame) -> pd.Series:
    return (
        rows["primary_route"].isin(REGULAR_ROUTES)
        & (rows["calendar_route_context"] == "normal_calendar")
    )


def _clean_regular_rows(score_rows: pd.DataFrame) -> list[list[str]]:
    rows: list[list[str]] = []
    clean = score_rows[_clean_regular_mask(score_rows)]
    model_order = {name: idx for idx, name in enumerate(ORDERED_MODELS)}
    for scope_name, rank_limit in REVENUE_SCOPES:
        scoped = clean[_scope_mask(clean, rank_limit)]
        for model_name, group in sorted(
            scoped.groupby("model_name", dropna=False),
            key=lambda item: model_order.get(str(item[0]), 99),
        ):
            metrics = _metrics(group)
            if metrics["scored"] == 0:
                continue
            rows.append(
                [
                    _scope_label(scope_name),
                    str(model_name),
                    f"{metrics['rows']:,}",
                    f"{metrics['scored']:,}",
                    _fmt_num(metrics["actual_revenue"], 0),
                    _fmt_num(metrics["actual_units"]),
                    _fmt_pct(metrics["hit20"]),
                    _fmt_pct(metrics["hit30"]),
                    _fmt_pct(metrics["wmape"]),
                    _fmt_pct(metrics["bias"]),
                    _fmt_pct(metrics["phantom_rate"]),
                ]
            )
    return rows


def _best_clean_regular_rows(score_rows: pd.DataFrame) -> list[list[str]]:
    rows: list[list[str]] = []
    clean = score_rows[_clean_regular_mask(score_rows)]
    for scope_name, rank_limit in REVENUE_SCOPES:
        scoped = clean[_scope_mask(clean, rank_limit)]
        candidates: list[tuple[float, float, str, dict[str, object]]] = []
        for model_name, group in scoped.groupby("model_name", dropna=False):
            metrics = _metrics(group)
            if metrics["scored"] == 0 or metrics["hit20"] is None:
                continue
            wmape = float(metrics["wmape"]) if metrics["wmape"] is not None else 999.0
            candidates.append((float(metrics["hit20"]), -wmape, str(model_name), metrics))
        if not candidates:
            continue
        hit20, _, model_name, metrics = sorted(candidates, reverse=True)[0]
        rows.append(
            [
                _scope_label(scope_name),
                model_name,
                f"{metrics['rows']:,}",
                f"{metrics['scored']:,}",
                _fmt_num(metrics["actual_revenue"], 0),
                _fmt_num(metrics["actual_units"]),
                _fmt_pct(hit20),
                _fmt_pct(metrics["wmape"]),
                _fmt_pct(metrics["bias"]),
                _fmt_pct(metrics["phantom_rate"]),
            ]
        )
    return rows


def _window_clean_rows(best_rows: pd.DataFrame) -> list[list[str]]:
    rows: list[list[str]] = []
    scoped = best_rows[_clean_regular_mask(best_rows) & _scope_mask(best_rows, 1000)]
    for target_start, group in scoped.groupby("target_start", dropna=False):
        metrics = _metrics(group)
        rows.append(
            [
                str(target_start),
                f"{metrics['rows']:,}",
                f"{metrics['scored']:,}",
                _fmt_num(metrics["actual_revenue"], 0),
                _fmt_pct(metrics["hit20"]),
                _fmt_pct(metrics["wmape"]),
                _fmt_pct(metrics["bias"]),
                _fmt_pct(metrics["phantom_rate"]),
            ]
        )
    return rows


def build_report(matrix: pd.DataFrame, score_rows: pd.DataFrame, skipped: list[str]) -> str:
    best = score_rows[score_rows["model_name"] == PHASE8E_CONTROL].copy()
    headline_metrics = _metrics(best)
    clean_top1000 = best[_clean_regular_mask(best) & _scope_mask(best, 1000)]
    clean_top1000_metrics = _metrics(clean_top1000)

    if clean_top1000_metrics["hit20"] is None:
        decision = "The clean top-1000 regular slice has no scored rows, so Phase 8G-C cannot target it yet."
    elif clean_top1000_metrics["hit20"] >= 0.55:
        decision = (
            "The clean top-1000 regular slice is already near the first-win band. "
            "Phase 8G-C should focus on stabilizing and promoting this route-specific path."
        )
    elif clean_top1000_metrics["hit20"] >= 0.40:
        decision = (
            "The clean top-1000 regular slice is materially better than the headline benchmark, "
            "but still below the 55-65% first-win band. Phase 8G-C should train a route-specific model here."
        )
    else:
        decision = (
            "The clean top-1000 regular slice is not yet strong enough. Before heavy modeling, inspect whether "
            "route labels are too strict or high-revenue regular SKUs are still campaign/stock contaminated."
        )

    return "\n".join(
        [
            "# Iteration 5P - V2 Phase 8G-A High-Revenue Benchmark",
            "",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"Route version: `{ROUTE_VERSION}`",
            "",
            "## Phase Checkpoint",
            "",
            "Phase completed: Phase 8G-A - high-revenue benchmark and route baseline.",
            "",
            "What changed: no model behavior changed. The current V2 sklearn predictions were rebuilt in memory, routed, and sliced by high-revenue scope.",
            "",
            "Accuracy rerun: diagnostic only. This report is the baseline for deciding the first route-specific modeling target.",
            "",
            _table(
                ["Metric", "Phase 8E safer control", "Phase 8G-A reproduction"],
                [
                    ["Best model", PHASE8E_CONTROL, PHASE8E_CONTROL],
                    ["Hit +/-20", _fmt_pct(PHASE8E_CONTROL_HIT20), _fmt_pct(headline_metrics["hit20"])],
                    ["WMAPE", _fmt_pct(PHASE8E_CONTROL_WMAPE), _fmt_pct(headline_metrics["wmape"])],
                    ["Phantom rate", _fmt_pct(PHASE8E_CONTROL_PHANTOM), _fmt_pct(headline_metrics["phantom_rate"])],
                ],
            ),
            "",
            "## Control By Revenue Scope",
            "",
            _table(
                [
                    "Scope",
                    "Rows",
                    "Qty scored",
                    "Actual revenue",
                    "Actual units",
                    "Hit +/-20",
                    "Delta vs 24.2%",
                    "WMAPE",
                    "Bias",
                    "Phantom rate",
                ],
                _control_scope_rows(best),
            ),
            "",
            "## All Models By Revenue Scope",
            "",
            _table(
                [
                    "Scope",
                    "Model",
                    "Rows",
                    "Qty scored",
                    "Actual revenue",
                    "Actual units",
                    "Hit +/-20",
                    "Hit +/-30",
                    "WMAPE",
                    "Bias",
                    "Phantom rate",
                ],
                _model_scope_rows(score_rows),
            ),
            "",
            "## Route Split For Control",
            "",
            _table(
                [
                    "Scope",
                    "Route",
                    "Rows",
                    "Qty scored",
                    "Actual revenue",
                    "Actual units",
                    "Hit +/-20",
                    "Hit +/-30",
                    "WMAPE",
                    "Bias",
                    "Phantom rate",
                ],
                _group_rows(best, "primary_route", order=ROUTE_ORDER, min_scored=1),
            ),
            "",
            "## Availability Split For Control",
            "",
            _table(
                [
                    "Scope",
                    "Availability",
                    "Rows",
                    "Qty scored",
                    "Actual revenue",
                    "Actual units",
                    "Hit +/-20",
                    "Hit +/-30",
                    "WMAPE",
                    "Bias",
                    "Phantom rate",
                ],
                _group_rows(best, "availability_confidence", min_scored=1),
            ),
            "",
            "## Campaign Bucket Split For Control",
            "",
            _table(
                [
                    "Scope",
                    "Campaign bucket",
                    "Rows",
                    "Qty scored",
                    "Actual revenue",
                    "Actual units",
                    "Hit +/-20",
                    "Hit +/-30",
                    "WMAPE",
                    "Bias",
                    "Phantom rate",
                ],
                _group_rows(best, "campaign_bucket", min_scored=1),
            ),
            "",
            "## Clean Regular High-Revenue Slice",
            "",
            "Definition: route is `available_regular` or `proxy_available_regular`, and target calendar is normal. This is forecast-time-safe; target-window campaign buckets remain diagnostic only.",
            "",
            _table(
                [
                    "Scope",
                    "Model",
                    "Rows",
                    "Qty scored",
                    "Actual revenue",
                    "Actual units",
                    "Hit +/-20",
                    "Hit +/-30",
                    "WMAPE",
                    "Bias",
                    "Phantom rate",
                ],
                _clean_regular_rows(score_rows),
            ),
            "",
            "## Best Current Model On Clean Regular Slice",
            "",
            _table(
                [
                    "Scope",
                    "Best current model",
                    "Rows",
                    "Qty scored",
                    "Actual revenue",
                    "Actual units",
                    "Hit +/-20",
                    "WMAPE",
                    "Bias",
                    "Phantom rate",
                ],
                _best_clean_regular_rows(score_rows),
            ),
            "",
            "## Top-1000 Clean Regular Window Details",
            "",
            _table(
                ["Target start", "Rows", "Qty scored", "Actual revenue", "Hit +/-20", "WMAPE", "Bias", "Phantom rate"],
                _window_clean_rows(best),
            ),
            "",
            "## Decision Gate",
            "",
            decision,
            "",
            "## Skipped Windows",
            "",
            ", ".join(f"`{window}`" for window in skipped) if skipped else "None.",
            "",
            "## Notes",
            "",
            "- Forecast V2 only; no old-engine path is used.",
            f"- Matrix rows built/routed: {len(matrix):,}.",
            f"- Score rows benchmarked across all models: {len(score_rows):,}.",
            "- Revenue scopes use cutoff-time `revenue_rank` from the V2 regime labels.",
            "- Route labels and availability features are derived only from pre-target feature matrix data.",
            "- Current snapshot rotation data remains excluded from historical backtests.",
        ]
    ) + "\n"


def run_benchmark(
    conn: sqlite3.Connection,
    target_starts: list[str],
    min_train_windows: int,
    random_state: int,
    config: ScorecardConfig | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    config = config or ScorecardConfig()
    matrix = build_feature_matrix(conn, target_starts=target_starts, population="headline", config=config)
    routed_matrix = add_route_labels(matrix)
    score_rows, skipped = _score_phase6_rows(
        routed_matrix,
        target_starts=target_starts,
        min_train_windows=min_train_windows,
        random_state=random_state,
        config=config,
    )
    score_rows = _append_matrix_columns(score_rows, routed_matrix)
    return routed_matrix, score_rows, skipped


def main() -> None:
    parser = argparse.ArgumentParser(description="Run forecast v2 Phase 8G-A high-revenue benchmark.")
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--target-start", action="append", default=None)
    parser.add_argument("--min-train-windows", type=int, default=4)
    parser.add_argument("--random-state", type=int, default=42)
    args = parser.parse_args()

    target_starts = args.target_start or DEFAULT_TARGET_STARTS
    config = ScorecardConfig()
    conn = sqlite3.connect(args.db)
    try:
        matrix, score_rows, skipped = run_benchmark(
            conn,
            target_starts=target_starts,
            min_train_windows=args.min_train_windows,
            random_state=args.random_state,
            config=config,
        )
    finally:
        conn.close()

    report = build_report(matrix, score_rows, skipped)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report, encoding="utf-8")
    print(report)
    print(f"Wrote {args.report}")


if __name__ == "__main__":
    main()
