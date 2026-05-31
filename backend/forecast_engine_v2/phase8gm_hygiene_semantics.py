"""Phase 8G-M discount hygiene and stock-semantics validation."""

from __future__ import annotations

import argparse
import sqlite3
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from .feature_matrix import DEFAULT_TARGET_STARTS, NUMERIC_FEATURES, build_feature_matrix
    from .route_labels import ROUTE_VERSION
    from .scorecard import DB_PATH, ScorecardConfig
    from .sklearn_direct_model import HIGH_REVENUE_CHAMPION_MODEL, run_sklearn_models
except ImportError:  # Allows direct script execution.
    from feature_matrix import DEFAULT_TARGET_STARTS, NUMERIC_FEATURES, build_feature_matrix
    from route_labels import ROUTE_VERSION
    from scorecard import DB_PATH, ScorecardConfig
    from sklearn_direct_model import HIGH_REVENUE_CHAMPION_MODEL, run_sklearn_models


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REPORT = PROJECT_ROOT / "active_docs" / "ITER5AB_V2_PHASE8G_M_HYGIENE_SEMANTICS.md"
DEFAULT_SCORE_ROWS_CSV = PROJECT_ROOT / "active_docs" / "ITER5AB_V2_PHASE8G_M_SCORE_ROWS.csv"
CONTROL_MODEL = "sk_blend_post_bf_safe"
PREVIOUS_CHAMPION_HIT20 = 0.253
PREVIOUS_CHAMPION_WMAPE = 0.510
PREVIOUS_CHAMPION_PHANTOM = 0.410


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


def _delta(candidate: object, baseline: object) -> float | None:
    if candidate is None or baseline is None or pd.isna(candidate) or pd.isna(baseline):
        return None
    return float(candidate) - float(baseline)


def _scalar(conn: sqlite3.Connection, sql: str) -> tuple[object, ...]:
    return conn.execute(sql).fetchone()


def _raw_audit(conn: sqlite3.Connection) -> dict[str, tuple[object, ...]]:
    return {
        "discount_raw": _scalar(
            conn,
            """
            SELECT
                COUNT(*),
                SUM(CASE WHEN discount_pct IS NULL THEN 1 ELSE 0 END),
                SUM(CASE WHEN discount_pct >= 0 AND discount_pct <= 1 THEN 1 ELSE 0 END),
                SUM(CASE WHEN discount_pct > 1 AND discount_pct < 1e308 THEN 1 ELSE 0 END),
                SUM(CASE WHEN discount_pct >= 1e308 THEN 1 ELSE 0 END),
                MAX(CASE WHEN discount_pct > 0 AND discount_pct < 1e308 THEN discount_pct END)
            FROM raw_sales_transactions_v2
            WHERE is_non_product = 0
            """,
        ),
        "discount_weekly": _scalar(
            conn,
            """
            SELECT
                COUNT(*),
                SUM(CASE WHEN avg_discount_pct > 1 AND avg_discount_pct < 1e308 THEN 1 ELSE 0 END),
                SUM(CASE WHEN max_discount_pct > 1 AND max_discount_pct < 1e308 THEN 1 ELSE 0 END),
                SUM(CASE WHEN avg_discount_pct >= 1e308 THEN 1 ELSE 0 END),
                SUM(CASE WHEN max_discount_pct >= 1e308 THEN 1 ELSE 0 END)
            FROM weekly_chain_demand_v2
            """,
        ),
        "returns": _scalar(
            conn,
            """
            SELECT
                SUM(CASE WHEN quantity > 0 THEN quantity ELSE 0 END),
                SUM(CASE WHEN quantity < 0 THEN ABS(quantity) ELSE 0 END),
                SUM(CASE WHEN quantity < 0 THEN 1 ELSE 0 END),
                SUM(CASE WHEN quantity < 0 AND line_value > 0 THEN 1 ELSE 0 END),
                SUM(CASE WHEN quantity < 0 AND line_value < 0 THEN 1 ELSE 0 END)
            FROM raw_sales_transactions_v2
            WHERE is_non_product = 0
            """,
        ),
    }


def _matrix_audit(matrix: pd.DataFrame) -> dict[str, object]:
    numeric = matrix[[col for col in NUMERIC_FEATURES if col in matrix.columns]].apply(pd.to_numeric, errors="coerce")
    values = numeric.to_numpy(dtype=float)
    discount_cols = [col for col in matrix.columns if "discount" in col and col in NUMERIC_FEATURES]
    discount_values = matrix[discount_cols].apply(pd.to_numeric, errors="coerce") if discount_cols else pd.DataFrame()
    return {
        "rows": int(len(matrix)),
        "numeric_cols": int(numeric.shape[1]),
        "nonfinite_numeric_cells": int((~np.isfinite(values)).sum()) if values.size else 0,
        "discount_cols": len(discount_cols),
        "discount_over_one_cells": int((discount_values > 1).sum().sum()) if not discount_values.empty else 0,
        "discount_max": None if discount_values.empty else float(discount_values.max().max()),
        "return_rate_13w_max": float(pd.to_numeric(matrix.get("return_rate_units_13w", 0), errors="coerce").max()),
        "return_rate_52w_max": float(pd.to_numeric(matrix.get("return_rate_units_52w", 0), errors="coerce").max()),
    }


def _metrics(rows: pd.DataFrame) -> dict[str, object]:
    scored = rows[rows["quantity_scored"] == 1]
    zero_actual = rows[rows["actual_units"] == 0]
    actual_sum = float(scored["actual_units"].sum())
    return {
        "rows": int(len(rows)),
        "scored": int(len(scored)),
        "hit20": float(scored["hit20"].mean()) if not scored.empty else None,
        "hit30": float(scored["hit30"].mean()) if not scored.empty else None,
        "wmape": float(scored["abs_error"].sum() / actual_sum) if actual_sum > 0 else None,
        "bias": float(scored["signed_error"].sum() / actual_sum) if actual_sum > 0 else None,
        "phantom_rate": float(zero_actual["phantom"].mean()) if len(zero_actual) else None,
    }


def _model_metrics(score_rows: pd.DataFrame, model_name: str) -> dict[str, object]:
    return _metrics(score_rows[score_rows["model_name"] == model_name].copy())


def _aggregate_rows(score_rows: pd.DataFrame) -> list[list[str]]:
    control = _model_metrics(score_rows, CONTROL_MODEL)
    rows: list[list[str]] = []
    for model_name in [CONTROL_MODEL, HIGH_REVENUE_CHAMPION_MODEL, "sk_extra_trees", "post_bf_safe_naive", "median_naive"]:
        metrics = _model_metrics(score_rows, model_name)
        rows.append(
            [
                model_name,
                f"{metrics['rows']:,}",
                f"{metrics['scored']:,}",
                _fmt_pct(metrics["hit20"]),
                _fmt_pp(_delta(metrics["hit20"], control["hit20"])),
                _fmt_pct(metrics["hit30"]),
                _fmt_pct(metrics["wmape"]),
                _fmt_pct(metrics["bias"]),
                _fmt_pct(metrics["phantom_rate"]),
            ]
        )
    return rows


def _window_rows(score_rows: pd.DataFrame) -> list[list[str]]:
    rows: list[list[str]] = []
    for target_start in sorted(score_rows["target_start"].dropna().astype(str).unique()):
        scoped = score_rows[score_rows["target_start"].astype(str) == target_start]
        control = _model_metrics(scoped, CONTROL_MODEL)
        champion = _model_metrics(scoped, HIGH_REVENUE_CHAMPION_MODEL)
        rows.append(
            [
                target_start,
                f"{champion['scored']:,}",
                _fmt_pct(control["hit20"]),
                _fmt_pct(champion["hit20"]),
                _fmt_pp(_delta(champion["hit20"], control["hit20"])),
                _fmt_pct(control["wmape"]),
                _fmt_pct(champion["wmape"]),
                _fmt_pp(_delta(champion["wmape"], control["wmape"])),
                _fmt_pct(champion["phantom_rate"]),
            ]
        )
    return rows


def build_report(
    raw_audit: dict[str, tuple[object, ...]],
    matrix_audit: dict[str, object],
    score_rows: pd.DataFrame,
    skipped: list[str],
    score_rows_csv: Path,
) -> str:
    raw_discount = raw_audit["discount_raw"]
    weekly_discount = raw_audit["discount_weekly"]
    returns = raw_audit["returns"]
    gross_units = float(returns[0] or 0.0)
    returned_units = float(returns[1] or 0.0)
    control = _model_metrics(score_rows, CONTROL_MODEL)
    champion = _model_metrics(score_rows, HIGH_REVENUE_CHAMPION_MODEL)
    hit_delta_prev = _delta(champion["hit20"], PREVIOUS_CHAMPION_HIT20)
    wmape_delta_prev = _delta(champion["wmape"], PREVIOUS_CHAMPION_WMAPE)
    phantom_delta_prev = _delta(champion["phantom_rate"], PREVIOUS_CHAMPION_PHANTOM)
    success = (
        int(matrix_audit["nonfinite_numeric_cells"]) == 0
        and int(matrix_audit["discount_over_one_cells"]) == 0
    )
    decision = "HYGIENE_PASS_KEEP_CHAMPION_BASELINE" if success else "HYGIENE_FAIL_FIX_BEFORE_NEXT_PHASE"

    return "\n".join(
        [
            "# Iteration 5AB - V2 Phase 8G-M Hygiene And Business Semantics",
            "",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"Route version: `{ROUTE_VERSION}`",
            "",
            "## Decision",
            "",
            f"Decision: `{decision}`.",
            "",
            "Discount features now exclude non-finite values and finite values above fraction scale. Stock-derived route wording is reframed as stock-position / fulfillment context, not can-sell availability. The gross positive demand target remains unchanged, while returns stay available as diagnostic features.",
            "",
            "## Raw Data Hygiene",
            "",
            _table(
                ["Area", "Rows / units", "Invalid/anomalous", "Action"],
                [
                    [
                        "Raw discount rows",
                        f"{int(raw_discount[0] or 0):,}",
                        f"{int(raw_discount[3] or 0):,} finite >1; {int(raw_discount[4] or 0):,} infinite; max finite {_fmt_num(raw_discount[5])}",
                        "Excluded from model discount features unless later database evidence proves a percent-scale convention.",
                    ],
                    [
                        "Weekly discount aggregates",
                        f"{int(weekly_discount[0] or 0):,}",
                        f"{int(weekly_discount[1] or 0):,} avg >1; {int(weekly_discount[2] or 0):,} max >1; {int(weekly_discount[3] or 0):,}/{int(weekly_discount[4] or 0):,} avg/max infinite",
                        "Sanitized in the feature builder so old DB aggregates cannot poison model inputs.",
                    ],
                    [
                        "Returns",
                        f"{_fmt_num(returned_units, 1)} returned units",
                        f"{_fmt_pct(returned_units / gross_units if gross_units else None)} of gross positive units; {int(returns[3] or 0):,} negative-qty positive-value rows",
                        "Kept separate from gross demand target; return-rate features remain diagnostics/context.",
                    ],
                ],
            ),
            "",
            "## Feature Matrix Hygiene",
            "",
            _table(
                ["Check", "Observed", "Status"],
                [
                    ["Rows", f"{int(matrix_audit['rows']):,}", "INFO"],
                    ["Numeric feature columns", f"{int(matrix_audit['numeric_cols']):,}", "INFO"],
                    ["Non-finite numeric cells", f"{int(matrix_audit['nonfinite_numeric_cells']):,}", "PASS" if int(matrix_audit["nonfinite_numeric_cells"]) == 0 else "FAIL"],
                    ["Discount feature cells > 1", f"{int(matrix_audit['discount_over_one_cells']):,}", "PASS" if int(matrix_audit["discount_over_one_cells"]) == 0 else "FAIL"],
                    ["Max discount feature value", _fmt_pct(matrix_audit["discount_max"]), "PASS"],
                    ["Max 13w / 52w return rate", f"{_fmt_pct(matrix_audit['return_rate_13w_max'])} / {_fmt_pct(matrix_audit['return_rate_52w_max'])}", "INFO"],
                ],
            ),
            "",
            "## Official Top 1000 Rerun",
            "",
            _table(
                ["Metric", "Previous champion", "Cleaned champion", "Delta"],
                [
                    ["Hit +/-20", _fmt_pct(PREVIOUS_CHAMPION_HIT20), _fmt_pct(champion["hit20"]), _fmt_pp(hit_delta_prev)],
                    ["WMAPE", _fmt_pct(PREVIOUS_CHAMPION_WMAPE), _fmt_pct(champion["wmape"]), _fmt_pp(wmape_delta_prev)],
                    ["Phantom", _fmt_pct(PREVIOUS_CHAMPION_PHANTOM), _fmt_pct(champion["phantom_rate"]), _fmt_pp(phantom_delta_prev)],
                ],
            ),
            "",
            _table(
                ["Model", "Rows", "Qty scored", "Hit +/-20", "Delta vs control", "Hit +/-30", "WMAPE", "Bias", "Phantom"],
                _aggregate_rows(score_rows),
            ),
            "",
            "## Window Check",
            "",
            _table(
                ["Target start", "Qty scored", "Control hit +/-20", "Champion hit +/-20", "Hit delta", "Control WMAPE", "Champion WMAPE", "WMAPE delta", "Champion phantom"],
                _window_rows(score_rows),
            ),
            "",
            "## Interpretation",
            "",
            "- Phase 8G-M is a correctness phase, not a promotion phase.",
            "- If the cleaned champion does not materially improve, the cleaned feature path still becomes the baseline for 8G-N because it removes known bad discount math.",
            "- Current stock features remain usable only as stock-position / fulfillment context. They must not be described as proof that an SKU could or could not sell.",
            "- The target remains positive sold units because returns represent post-sale behavior, not missing demand.",
            "",
            "## Outputs",
            "",
            f"- Score rows: `{score_rows_csv}`.",
            f"- Skipped windows: {', '.join(f'`{item}`' for item in skipped) if skipped else 'None'}.",
        ]
    ) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Phase 8G-M hygiene and semantics validation.")
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--score-rows-csv", type=Path, default=DEFAULT_SCORE_ROWS_CSV)
    parser.add_argument("--target-start", action="append", default=None)
    parser.add_argument("--min-train-windows", type=int, default=4)
    parser.add_argument("--random-state", type=int, default=42)
    parser.add_argument("--revenue-rank-limit", type=int, default=1000)
    args = parser.parse_args()

    config = ScorecardConfig()
    target_starts = args.target_start or DEFAULT_TARGET_STARTS
    conn = sqlite3.connect(args.db)
    try:
        print("8G-M: auditing raw discount/return semantics...", flush=True)
        raw_audit = _raw_audit(conn)
        print("8G-M: building cleaned Top 1000 feature matrix...", flush=True)
        matrix = build_feature_matrix(
            conn,
            target_starts=target_starts,
            population="headline",
            config=config,
            revenue_rank_limit=args.revenue_rank_limit,
        )
        matrix_audit = _matrix_audit(matrix)
        print("8G-M: running official Top 1000 champion comparison...", flush=True)
        _, _, _, skipped, score_rows = run_sklearn_models(
            conn,
            target_starts=target_starts,
            min_train_windows=args.min_train_windows,
            random_state=args.random_state,
            revenue_rank_limit=args.revenue_rank_limit,
            high_revenue_policy="champion",
            config=config,
            include_score_rows=True,
            feature_matrix=matrix,
        )
    finally:
        conn.close()

    args.score_rows_csv.parent.mkdir(parents=True, exist_ok=True)
    score_rows.to_csv(args.score_rows_csv, index=False)
    report = build_report(raw_audit, matrix_audit, score_rows, skipped, args.score_rows_csv)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report, encoding="utf-8")
    print(report)
    print(f"Wrote {args.report}")


if __name__ == "__main__":
    main()
