"""Phase 7D error decomposition and oracle ceiling analysis."""

from __future__ import annotations

import argparse
import sqlite3
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from .analog_model_candidates import CONTROL_MODEL, run_analog_candidates
    from .feature_matrix import DEFAULT_TARGET_STARTS
    from .route_labels import ROUTE_ORDER, ROUTE_VERSION
    from .scorecard import DB_PATH, ScorecardConfig
except ImportError:  # Allows direct script execution.
    from analog_model_candidates import CONTROL_MODEL, run_analog_candidates
    from feature_matrix import DEFAULT_TARGET_STARTS
    from route_labels import ROUTE_ORDER, ROUTE_VERSION
    from scorecard import DB_PATH, ScorecardConfig


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REPORT = PROJECT_ROOT / "active_docs" / "ITER5H_V2_ERROR_DECOMPOSITION.md"
BASE_MODEL_POOL = [
    "median_naive",
    "post_bf_safe_naive",
    "sk_hgb_poisson",
    "sk_hgb_squared",
    "sk_extra_trees",
    "sk_blend_median",
    CONTROL_MODEL,
]
ANALOG_MODEL_POOL = [
    "analog_regular_units",
    "analog_regular_ratio",
    "analog_regular_residual",
    "analog_regular_blend",
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
    zero_actual = group[group["actual_units"] == 0]
    return {
        "rows": int(len(group)),
        "scored": int(len(scored)),
        "actual_units": actual_sum,
        "actual_revenue": float(group["actual_revenue"].sum()),
        "abs_error": float(scored["abs_error"].sum()),
        "hit20": float(scored["hit20"].mean()) if not scored.empty else None,
        "hit30": float(scored["hit30"].mean()) if not scored.empty else None,
        "wmape": float(scored["abs_error"].sum() / actual_sum) if actual_sum > 0 else None,
        "bias": float(scored["signed_error"].sum() / actual_sum) if actual_sum > 0 else None,
        "phantom_rate": float(zero_actual["phantom"].mean()) if len(zero_actual) else None,
        "under20_rate": float(scored["under20"].mean()) if not scored.empty else None,
        "over20_rate": float(scored["over20"].mean()) if not scored.empty else None,
    }


def _oracle_rows(score_rows: pd.DataFrame, model_names: list[str], oracle_name: str) -> pd.DataFrame:
    pool = score_rows[score_rows["model_name"].isin(model_names)].copy()
    if pool.empty:
        return pool
    idx = pool.groupby(["run_id", "sku_id"], dropna=False)["abs_error"].idxmin()
    oracle = pool.loc[idx].copy()
    oracle["model_name"] = oracle_name
    return oracle


def _model_rows(score_rows: pd.DataFrame, model_names: list[str], control_hit20: float | None) -> list[list[str]]:
    rows = []
    for model_name in model_names:
        group = score_rows[score_rows["model_name"] == model_name]
        if group.empty:
            continue
        metrics = _metrics(group)
        delta = None if control_hit20 is None or metrics["hit20"] is None else float(metrics["hit20"]) - control_hit20
        rows.append(
            [
                model_name,
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


def _slice_rows(control_rows: pd.DataFrame, group_col: str, order: list[str] | None = None) -> list[list[str]]:
    total_abs_error = float(control_rows[control_rows["quantity_scored"] == 1]["abs_error"].sum())
    total_revenue = float(control_rows["actual_revenue"].sum())
    grouped = control_rows.groupby(group_col, dropna=False)
    keys = list(grouped.groups)
    if order:
        keys = [key for key in order if key in grouped.groups] + [key for key in keys if key not in order]
    rows = []
    for key in keys:
        group = grouped.get_group(key)
        metrics = _metrics(group)
        abs_error_share = metrics["abs_error"] / total_abs_error if total_abs_error else None
        revenue_share = metrics["actual_revenue"] / total_revenue if total_revenue else None
        rows.append(
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
                _fmt_pct(abs_error_share),
            ]
        )
    return rows


def _window_rows(control_rows: pd.DataFrame) -> list[list[str]]:
    rows = []
    for target_start, group in control_rows.groupby("target_start", dropna=False):
        metrics = _metrics(group)
        rows.append(
            [
                str(target_start),
                f"{metrics['scored']:,}",
                _fmt_num(metrics["actual_units"]),
                _fmt_pct(metrics["hit20"]),
                _fmt_pct(metrics["hit30"]),
                _fmt_pct(metrics["wmape"]),
                _fmt_pct(metrics["bias"]),
                _fmt_pct(metrics["phantom_rate"]),
                _fmt_num(metrics["abs_error"]),
            ]
        )
    return rows


def _error_band_rows(control_rows: pd.DataFrame) -> list[list[str]]:
    scored = control_rows[control_rows["quantity_scored"] == 1].copy()
    if scored.empty:
        return []
    scored["error_band"] = pd.cut(
        scored["abs_pct_error"],
        bins=[-np.inf, 0.20, 0.30, 0.50, 1.00, np.inf],
        labels=["hit_0_20", "near_20_30", "miss_30_50", "miss_50_100", "miss_100_plus"],
    )
    total_rows = len(scored)
    total_abs_error = float(scored["abs_error"].sum())
    rows = []
    for band, group in scored.groupby("error_band", observed=False):
        rows.append(
            [
                str(band),
                f"{len(group):,}",
                _fmt_pct(len(group) / total_rows if total_rows else None),
                _fmt_num(float(group["actual_units"].sum())),
                _fmt_num(float(group["abs_error"].sum())),
                _fmt_pct(float(group["abs_error"].sum()) / total_abs_error if total_abs_error else None),
            ]
        )
    return rows


def _direction_rows(control_rows: pd.DataFrame) -> list[list[str]]:
    scored = control_rows[control_rows["quantity_scored"] == 1].copy()
    if scored.empty:
        return []
    conditions = [
        scored["hit20"] == 1,
        scored["under20"] == 1,
        scored["over20"] == 1,
    ]
    scored["direction"] = np.select(conditions, ["hit_20", "under_by_20_plus", "over_by_20_plus"], default="other_miss")
    rows = []
    total_abs_error = float(scored["abs_error"].sum())
    for direction, group in scored.groupby("direction", dropna=False):
        rows.append(
            [
                str(direction),
                f"{len(group):,}",
                _fmt_pct(len(group) / len(scored)),
                _fmt_num(float(group["actual_units"].sum())),
                _fmt_num(float(group["abs_error"].sum())),
                _fmt_pct(float(group["abs_error"].sum()) / total_abs_error if total_abs_error else None),
            ]
        )
    rows.sort(key=lambda row: row[0])
    return rows


def _oracle_gain_by_route(score_rows: pd.DataFrame) -> list[list[str]]:
    control = score_rows[score_rows["model_name"] == CONTROL_MODEL].copy()
    oracle = _oracle_rows(score_rows, BASE_MODEL_POOL + ANALOG_MODEL_POOL, "oracle_all_tested")
    if oracle.empty:
        return []
    rows = []
    for route in [route for route in ROUTE_ORDER if route in set(control["primary_route"])]:
        control_metrics = _metrics(control[control["primary_route"] == route])
        oracle_metrics = _metrics(oracle[oracle["primary_route"] == route])
        delta = None
        if control_metrics["hit20"] is not None and oracle_metrics["hit20"] is not None:
            delta = float(oracle_metrics["hit20"]) - float(control_metrics["hit20"])
        rows.append(
            [
                route,
                f"{control_metrics['scored']:,}",
                _fmt_pct(control_metrics["hit20"]),
                _fmt_pct(oracle_metrics["hit20"]),
                _fmt_pp(delta),
                _fmt_pct(control_metrics["wmape"]),
                _fmt_pct(oracle_metrics["wmape"]),
            ]
        )
    return rows


def _top_error_rows(control_rows: pd.DataFrame, limit: int = 20) -> list[list[str]]:
    scored = control_rows[control_rows["quantity_scored"] == 1].copy()
    if scored.empty:
        return []
    grouped = (
        scored.groupby("sku_id", as_index=False)
        .agg(
            windows=("target_start", "nunique"),
            actual_units=("actual_units", "sum"),
            pred_units=("pred_units", "sum"),
            abs_error=("abs_error", "sum"),
            hit20=("hit20", "mean"),
            primary_route=("primary_route", lambda s: s.mode().iloc[0] if not s.mode().empty else "unknown"),
            category_norm=("category_norm", lambda s: s.mode().iloc[0] if not s.mode().empty else "unknown"),
            product_family_v2=("product_family_v2", lambda s: s.mode().iloc[0] if not s.mode().empty else "unknown"),
        )
        .sort_values("abs_error", ascending=False)
        .head(limit)
    )
    return [
        [
            str(row["sku_id"]),
            str(row["primary_route"]),
            str(row["category_norm"]),
            str(row["product_family_v2"]),
            f"{int(row['windows'])}",
            _fmt_num(row["actual_units"]),
            _fmt_num(row["pred_units"]),
            _fmt_num(row["abs_error"]),
            _fmt_pct(row["hit20"]),
        ]
        for _, row in grouped.iterrows()
    ]


def build_report(
    score_rows: pd.DataFrame,
    skipped: list[str],
    target_starts: list[str],
    k_neighbors: int,
) -> str:
    oracle_base = _oracle_rows(score_rows, BASE_MODEL_POOL, "oracle_base_models")
    oracle_all = _oracle_rows(score_rows, BASE_MODEL_POOL + ANALOG_MODEL_POOL, "oracle_all_tested")
    analysis_rows = pd.concat([score_rows, oracle_base, oracle_all], ignore_index=True)
    control = analysis_rows[analysis_rows["model_name"] == CONTROL_MODEL].copy()
    control_metrics = _metrics(control)
    control_hit20 = None if control_metrics["hit20"] is None else float(control_metrics["hit20"])
    oracle_all_metrics = _metrics(oracle_all)
    oracle_gap = None
    if control_hit20 is not None and oracle_all_metrics["hit20"] is not None:
        oracle_gap = float(oracle_all_metrics["hit20"]) - control_hit20

    if oracle_all_metrics["hit20"] is not None and oracle_all_metrics["hit20"] < 0.50:
        decision = (
            "Even the tested-model oracle is below 50% hit +/-20, so the immediate blocker is not just model selection among current candidates. "
            "The next work should focus on data/target decomposition and missing availability signals before another small model wrapper."
        )
    elif oracle_all_metrics["hit20"] is not None and oracle_gap is not None and oracle_gap > 0.15:
        decision = (
            "The oracle gap is large, so better model routing or candidate selection could still matter. "
            "However, route-specific specialists and analog matching already failed, so the next candidate must use a materially different objective."
        )
    else:
        decision = (
            "The oracle gap is limited, so more wrappers around the same candidate family are unlikely to unlock the target."
        )

    return "\n".join(
        [
            "# Iteration 5H — V2 Error Decomposition And Oracle Ceiling",
            "",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"Route version: `{ROUTE_VERSION}`",
            "",
            "## Phase Checkpoint",
            "",
            "Phase completed: Phase 7D — Error decomposition / oracle ceiling",
            "",
            "What changed: no production model behavior changed. This phase measures where the current control fails and how high accuracy could go if we could perfectly choose among already-tested candidates.",
            "",
            f"Accuracy rerun: yes. Rebuilt the Phase 7C measurement set using `{k_neighbors}` analog neighbors, then added oracle rows in memory.",
            "",
            _table(
                ["Metric", "Current control", "Oracle all tested", "Oracle gap"],
                [
                    ["Model", CONTROL_MODEL, "oracle_all_tested", "-"],
                    ["Hit +/-20", _fmt_pct(control_metrics["hit20"]), _fmt_pct(oracle_all_metrics["hit20"]), _fmt_pp(oracle_gap)],
                    ["Hit +/-30", _fmt_pct(control_metrics["hit30"]), _fmt_pct(oracle_all_metrics["hit30"]), "-"],
                    ["WMAPE", _fmt_pct(control_metrics["wmape"]), _fmt_pct(oracle_all_metrics["wmape"]), "-"],
                    ["Phantom rate", _fmt_pct(control_metrics["phantom_rate"]), _fmt_pct(oracle_all_metrics["phantom_rate"]), "-"],
                ],
            ),
            "",
            "## Model And Oracle Ceiling",
            "",
            _table(
                ["Model", "Rows", "Qty scored", "Hit +/-20", "Delta vs control", "Hit +/-30", "WMAPE", "Bias", "Phantom rate"],
                _model_rows(
                    analysis_rows,
                    BASE_MODEL_POOL + ANALOG_MODEL_POOL + ["oracle_base_models", "oracle_all_tested"],
                    control_hit20,
                ),
            ),
            "",
            "## Error By Route",
            "",
            _table(
                [
                    "Route",
                    "Rows",
                    "Qty scored",
                    "Revenue share",
                    "Actual units",
                    "Hit +/-20",
                    "Hit +/-30",
                    "WMAPE",
                    "Bias",
                    "Phantom rate",
                    "Abs error share",
                ],
                _slice_rows(control, "primary_route", ROUTE_ORDER),
            ),
            "",
            "## Oracle Gain By Route",
            "",
            _table(
                ["Route", "Qty scored", "Control hit +/-20", "Oracle hit +/-20", "Delta", "Control WMAPE", "Oracle WMAPE"],
                _oracle_gain_by_route(analysis_rows),
            ),
            "",
            "## Error By Availability",
            "",
            _table(
                [
                    "Availability",
                    "Rows",
                    "Qty scored",
                    "Revenue share",
                    "Actual units",
                    "Hit +/-20",
                    "Hit +/-30",
                    "WMAPE",
                    "Bias",
                    "Phantom rate",
                    "Abs error share",
                ],
                _slice_rows(control, "availability_confidence"),
            ),
            "",
            "## Error By Intermittency",
            "",
            _table(
                [
                    "Intermittency",
                    "Rows",
                    "Qty scored",
                    "Revenue share",
                    "Actual units",
                    "Hit +/-20",
                    "Hit +/-30",
                    "WMAPE",
                    "Bias",
                    "Phantom rate",
                    "Abs error share",
                ],
                _slice_rows(control, "intermittency_bucket"),
            ),
            "",
            "## Error By Window",
            "",
            _table(
                ["Target start", "Qty scored", "Actual units", "Hit +/-20", "Hit +/-30", "WMAPE", "Bias", "Phantom rate", "Abs error"],
                _window_rows(control),
            ),
            "",
            "## Error Bands",
            "",
            _table(
                ["Band", "Rows", "Row share", "Actual units", "Abs error", "Abs error share"],
                _error_band_rows(control),
            ),
            "",
            "## Error Direction",
            "",
            _table(
                ["Direction", "Rows", "Row share", "Actual units", "Abs error", "Abs error share"],
                _direction_rows(control),
            ),
            "",
            "## Top SKU Error Concentration",
            "",
            _table(
                ["SKU", "Route", "Category", "Family", "Windows", "Actual units", "Pred units", "Abs error", "Hit +/-20"],
                _top_error_rows(control),
            ),
            "",
            "## Decision",
            "",
            decision,
            "",
            "## Skipped Windows",
            "",
            ", ".join(f"`{window}`" for window in skipped) if skipped else "None.",
            "",
            "## Notes",
            "",
            f"- Requested target windows: {', '.join(target_starts)}.",
            "- Oracle rows are diagnostic only and use actual outcomes to select the best tested prediction per SKU-window.",
            "- Current snapshot stock remains excluded from historical backtests.",
            "- This report should guide whether the next phase is data acquisition, target-population cleanup, or a new objective.",
            "",
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run forecast v2 error decomposition and oracle ceiling.")
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--target-start", action="append", default=None)
    parser.add_argument("--min-train-windows", type=int, default=4)
    parser.add_argument("--random-state", type=int, default=42)
    parser.add_argument("--k-neighbors", type=int, default=35)
    args = parser.parse_args()

    target_starts = args.target_start or DEFAULT_TARGET_STARTS
    config = ScorecardConfig()
    conn = sqlite3.connect(args.db)
    try:
        _, score_rows, _, skipped, _ = run_analog_candidates(
            conn,
            target_starts=target_starts,
            min_train_windows=args.min_train_windows,
            random_state=args.random_state,
            k_neighbors=args.k_neighbors,
            config=config,
        )
    finally:
        conn.close()

    report = build_report(score_rows, skipped, target_starts, args.k_neighbors)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report, encoding="utf-8")
    print(report)
    print(f"Wrote {args.report}")


if __name__ == "__main__":
    main()
