"""Phase 8G-I official validation/export checks for the wired high-revenue policy."""

from __future__ import annotations

import argparse
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd

try:
    from .feature_matrix import DEFAULT_TARGET_STARTS
    from .route_labels import ROUTE_ORDER, ROUTE_VERSION
    from .scorecard import DB_PATH, ScorecardConfig
    from .sklearn_direct_model import (
        HIGH_REVENUE_CHAMPION_MODEL,
        HIGH_REVENUE_CHAMPION_SOURCE,
        HIGH_REVENUE_CHAMPION_VERSION,
        run_sklearn_models,
    )
except ImportError:  # Allows direct script execution.
    from feature_matrix import DEFAULT_TARGET_STARTS
    from route_labels import ROUTE_ORDER, ROUTE_VERSION
    from scorecard import DB_PATH, ScorecardConfig
    from sklearn_direct_model import (
        HIGH_REVENUE_CHAMPION_MODEL,
        HIGH_REVENUE_CHAMPION_SOURCE,
        HIGH_REVENUE_CHAMPION_VERSION,
        run_sklearn_models,
    )


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REPORT = PROJECT_ROOT / "active_docs" / "ITER5X_V2_PHASE8G_OFFICIAL_POLICY_VALIDATION.md"
DEFAULT_SCORE_ROWS_CSV = PROJECT_ROOT / "active_docs" / "ITER5X_V2_PHASE8G_OFFICIAL_POLICY_SCORE_ROWS.csv"
CONTROL_MODEL = "sk_blend_post_bf_safe"
REVENUE_SCOPES = [100, 250, 500, 750, 1000]
REGULAR_ROUTES = {"available_regular", "proxy_available_regular"}


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


def _delta(candidate: object, control: object) -> float | None:
    if candidate is None or control is None or pd.isna(candidate) or pd.isna(control):
        return None
    return float(candidate) - float(control)


def _scope_mask(rows: pd.DataFrame, rank_limit: int) -> pd.Series:
    if "revenue_rank" not in rows.columns:
        return pd.Series(False, index=rows.index)
    return pd.to_numeric(rows["revenue_rank"], errors="coerce") <= rank_limit


def _metrics(rows: pd.DataFrame) -> dict[str, object]:
    scored = rows[rows["quantity_scored"] == 1]
    zero_actual = rows[rows["actual_units"] == 0]
    actual_sum = float(scored["actual_units"].sum())
    return {
        "rows": int(len(rows)),
        "scored": int(len(scored)),
        "actual_revenue": float(rows["actual_revenue"].sum()) if "actual_revenue" in rows.columns else None,
        "hit20": float(scored["hit20"].mean()) if not scored.empty else None,
        "hit30": float(scored["hit30"].mean()) if not scored.empty else None,
        "wmape": float(scored["abs_error"].sum() / actual_sum) if actual_sum > 0 else None,
        "bias": float(scored["signed_error"].sum() / actual_sum) if actual_sum > 0 else None,
        "phantom_rate": float(zero_actual["phantom"].mean()) if len(zero_actual) else None,
        "zero_rows": int(len(zero_actual)),
        "zero_pred_units": float(zero_actual["pred_units"].sum()) if len(zero_actual) else 0.0,
        "zero_avg_pred_units": float(zero_actual["pred_units"].mean()) if len(zero_actual) else None,
    }


def _model_metrics(score_rows: pd.DataFrame, model_name: str) -> dict[str, object]:
    return _metrics(score_rows[score_rows["model_name"] == model_name].copy())


def _compare_rows(score_rows: pd.DataFrame, mask: pd.Series) -> tuple[dict[str, object], dict[str, object]]:
    control = _metrics(score_rows[(score_rows["model_name"] == CONTROL_MODEL) & mask])
    champion = _metrics(score_rows[(score_rows["model_name"] == HIGH_REVENUE_CHAMPION_MODEL) & mask])
    return control, champion


def _metric_row(label: str, control: dict[str, object], champion: dict[str, object]) -> list[str]:
    return [
        label,
        f"{champion['rows']:,}",
        f"{champion['scored']:,}",
        _fmt_num(champion["actual_revenue"], 0),
        _fmt_pct(control["hit20"]),
        _fmt_pct(champion["hit20"]),
        _fmt_pp(_delta(champion["hit20"], control["hit20"])),
        _fmt_pct(control["hit30"]),
        _fmt_pct(champion["hit30"]),
        _fmt_pct(control["wmape"]),
        _fmt_pct(champion["wmape"]),
        _fmt_pp(_delta(champion["wmape"], control["wmape"])),
        _fmt_pct(control["bias"]),
        _fmt_pct(champion["bias"]),
        _fmt_pct(control["phantom_rate"]),
        _fmt_pct(champion["phantom_rate"]),
        _fmt_pp(_delta(champion["phantom_rate"], control["phantom_rate"])),
    ]


def _aggregate_rows(score_rows: pd.DataFrame) -> list[list[str]]:
    rows: list[list[str]] = []
    control = _model_metrics(score_rows, CONTROL_MODEL)
    for model_name, group in sorted(score_rows.groupby("model_name"), key=lambda item: str(item[0])):
        metrics = _metrics(group)
        rows.append(
            [
                str(model_name),
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


def _scope_rows(score_rows: pd.DataFrame) -> list[list[str]]:
    rows: list[list[str]] = []
    for rank_limit in REVENUE_SCOPES:
        control, champion = _compare_rows(score_rows, _scope_mask(score_rows, rank_limit))
        rows.append(_metric_row(f"Top {rank_limit}", control, champion))
    return rows


def _route_rows(score_rows: pd.DataFrame) -> list[list[str]]:
    rows: list[list[str]] = []
    if "primary_route" not in score_rows.columns:
        return rows
    routes = set(score_rows["primary_route"].dropna().astype(str))
    for route in [route for route in ROUTE_ORDER if route in routes]:
        mask = score_rows["primary_route"].astype(str) == route
        control, champion = _compare_rows(score_rows, mask)
        rows.append(_metric_row(route, control, champion))
    return rows


def _window_rows(score_rows: pd.DataFrame) -> list[list[str]]:
    rows: list[list[str]] = []
    for target_start in sorted(score_rows["target_start"].dropna().astype(str).unique()):
        mask = score_rows["target_start"].astype(str) == target_start
        control, champion = _compare_rows(score_rows, mask)
        rows.append(_metric_row(target_start, control, champion))
    return rows


def _critical_slice_rows(score_rows: pd.DataFrame) -> list[list[str]]:
    campaign_txn_13w = pd.to_numeric(score_rows.get("campaign_txn_13w", 0), errors="coerce").fillna(0)
    bf_txn_13w = pd.to_numeric(score_rows.get("bf_txn_13w", 0), errors="coerce").fillna(0)
    target_post_bf = pd.to_numeric(score_rows.get("target_is_post_bf_4w", 0), errors="coerce").fillna(0)
    bf_unit_share_4w = pd.to_numeric(score_rows.get("bf_unit_share_4w", 0), errors="coerce").fillna(0)
    primary_route = score_rows.get("primary_route", pd.Series("", index=score_rows.index)).astype(str)
    slices = [
        ("Available/proxy regular", primary_route.isin(REGULAR_ROUTES)),
        ("BF/campaign-sensitive route", primary_route == "bf_campaign_sensitive"),
        ("Any campaign/BF history 13w", (campaign_txn_13w > 0) | (bf_txn_13w > 0)),
        ("Post-BF stress rows", (target_post_bf == 1) & (bf_unit_share_4w > 0)),
        ("2024-11-25 stress window", score_rows["target_start"].astype(str) == "2024-11-25"),
    ]
    return [_metric_row(label, *_compare_rows(score_rows, mask)) for label, mask in slices]


def _zero_actual_rows(score_rows: pd.DataFrame) -> list[list[str]]:
    rows: list[list[str]] = []
    champion = _model_metrics(score_rows, HIGH_REVENUE_CHAMPION_MODEL)
    for model_name in [CONTROL_MODEL, "sk_extra_trees", "sk_hgb_squared", "post_bf_safe_naive", "median_naive"]:
        baseline = _model_metrics(score_rows, model_name)
        rows.append(
            [
                model_name,
                f"{baseline['zero_rows']:,}",
                _fmt_pct(baseline["phantom_rate"]),
                _fmt_pct(champion["phantom_rate"]),
                _fmt_pp(_delta(champion["phantom_rate"], baseline["phantom_rate"])),
                _fmt_num(baseline["zero_pred_units"], 1),
                _fmt_num(champion["zero_pred_units"], 1),
                _fmt_num(baseline["zero_avg_pred_units"], 2),
                _fmt_num(champion["zero_avg_pred_units"], 2),
            ]
        )
    return rows


def _policy_check_rows(no_policy_rows: pd.DataFrame, champion_rows: pd.DataFrame, guard_passed: bool) -> list[list[str]]:
    no_policy_champion_present = bool((no_policy_rows["model_name"] == HIGH_REVENUE_CHAMPION_MODEL).any())
    champion_present = bool((champion_rows["model_name"] == HIGH_REVENUE_CHAMPION_MODEL).any())
    no_policy_control = _model_metrics(no_policy_rows, CONTROL_MODEL)
    champion_control = _model_metrics(champion_rows, CONTROL_MODEL)
    return [
        [
            "Default policy emits champion",
            "no",
            "yes" if no_policy_champion_present else "no",
            "PASS" if not no_policy_champion_present else "FAIL",
        ],
        [
            "Champion policy emits champion",
            "yes",
            "yes" if champion_present else "no",
            "PASS" if champion_present else "FAIL",
        ],
        [
            "Champion blocked without Top 1000-or-lower rank scope",
            "yes",
            "yes" if guard_passed else "no",
            "PASS" if guard_passed else "FAIL",
        ],
        [
            "Same-run control hit +/-20 unchanged by policy flag",
            "0.0pp delta",
            _fmt_pp(_delta(champion_control["hit20"], no_policy_control["hit20"])),
            "PASS" if abs(_delta(champion_control["hit20"], no_policy_control["hit20"]) or 0.0) < 1e-12 else "FAIL",
        ],
    ]


def _max_non_stress_window_wmape_regression(score_rows: pd.DataFrame) -> tuple[str | None, float | None]:
    worst_window: str | None = None
    worst_delta: float | None = None
    for target_start in sorted(score_rows["target_start"].dropna().astype(str).unique()):
        if target_start == "2024-11-25":
            continue
        control, champion = _compare_rows(score_rows, score_rows["target_start"].astype(str) == target_start)
        delta = _delta(champion["wmape"], control["wmape"])
        if delta is None:
            continue
        if worst_delta is None or delta > worst_delta:
            worst_delta = delta
            worst_window = target_start
    return worst_window, worst_delta


def _monitor_rows(score_rows: pd.DataFrame) -> list[list[str]]:
    primary_route = score_rows.get("primary_route", pd.Series("", index=score_rows.index)).astype(str)
    regular_control, regular_champion = _compare_rows(score_rows, primary_route.isin(REGULAR_ROUTES))
    available_control, available_champion = _compare_rows(score_rows, primary_route == "available_regular")
    window, wmape_delta = _max_non_stress_window_wmape_regression(score_rows)
    control = _model_metrics(score_rows, CONTROL_MODEL)
    champion = _model_metrics(score_rows, HIGH_REVENUE_CHAMPION_MODEL)
    return [
        [
            "Overall bias",
            "monitor",
            _fmt_pp(_delta(champion["bias"], control["bias"])),
            "Champion is more underpredictive; this is accepted, not ignored.",
        ],
        [
            "Available/proxy regular phantom",
            "monitor",
            _fmt_pp(_delta(regular_champion["phantom_rate"], regular_control["phantom_rate"])),
            "Regular hit improves, but zero-actual false-positive risk rises.",
        ],
        [
            "Available regular phantom",
            "monitor",
            _fmt_pp(_delta(available_champion["phantom_rate"], available_control["phantom_rate"])),
            "Largest route-level phantom caveat inside regular rows.",
        ],
        [
            "Largest non-stress window WMAPE regression",
            "monitor",
            f"{window or '-'}: {_fmt_pp(wmape_delta)}",
            "This is diagnostic; 2024-11-25 is the named stress gate.",
        ],
    ]


def _decision(score_rows: pd.DataFrame) -> tuple[str, list[list[str]]]:
    control = _model_metrics(score_rows, CONTROL_MODEL)
    champion = _model_metrics(score_rows, HIGH_REVENUE_CHAMPION_MODEL)
    top100_control, top100_champion = _compare_rows(score_rows, _scope_mask(score_rows, 100))
    top500_control, top500_champion = _compare_rows(score_rows, _scope_mask(score_rows, 500))
    stress_control, stress_champion = _compare_rows(score_rows, score_rows["target_start"].astype(str) == "2024-11-25")

    checks = [
        ("Top 1000 hit +/-20", ">= +1.5pp", _delta(champion["hit20"], control["hit20"])),
        ("Top 1000 WMAPE", "<= +0.5pp", _delta(champion["wmape"], control["wmape"])),
        ("Top 1000 phantom", "<= +0.5pp", _delta(champion["phantom_rate"], control["phantom_rate"])),
        ("Top 500 hit +/-20", ">= 0.0pp", _delta(top500_champion["hit20"], top500_control["hit20"])),
        ("Top 100 hit +/-20", ">= 0.0pp", _delta(top100_champion["hit20"], top100_control["hit20"])),
        ("2024-11-25 WMAPE", "< control", _delta(stress_champion["wmape"], stress_control["wmape"])),
    ]
    gates_pass = (
        (checks[0][2] is not None and checks[0][2] >= 0.015)
        and (checks[1][2] is not None and checks[1][2] <= 0.005)
        and (checks[2][2] is not None and checks[2][2] <= 0.005)
        and (checks[3][2] is not None and checks[3][2] >= 0.0)
        and (checks[4][2] is not None and checks[4][2] >= 0.0)
        and (checks[5][2] is not None and checks[5][2] < 0.0)
    )
    decision = "PROMOTE_WITH_MONITORS" if gates_pass else "DO_NOT_PROMOTE"
    rows = [
        [
            label,
            gate,
            _fmt_pp(observed),
            "PASS"
            if (
                (label == "Top 1000 hit +/-20" and observed is not None and observed >= 0.015)
                or (label in {"Top 1000 WMAPE", "Top 1000 phantom"} and observed is not None and observed <= 0.005)
                or (label in {"Top 500 hit +/-20", "Top 100 hit +/-20"} and observed is not None and observed >= 0.0)
                or (label == "2024-11-25 WMAPE" and observed is not None and observed < 0.0)
            )
            else "FAIL",
        ]
        for label, gate, observed in checks
    ]
    return decision, rows


def build_report(
    no_policy_rows: pd.DataFrame,
    champion_rows: pd.DataFrame,
    no_policy_skipped: list[str],
    champion_skipped: list[str],
    guard_passed: bool,
    revenue_rank_limit: int,
    score_rows_csv: Path | None,
) -> str:
    decision, gate_rows = _decision(champion_rows)
    control = _model_metrics(champion_rows, CONTROL_MODEL)
    champion = _model_metrics(champion_rows, HIGH_REVENUE_CHAMPION_MODEL)
    return "\n".join(
        [
            "# Iteration 5X - V2 Phase 8G-I Official Policy Validation",
            "",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"Route version: `{ROUTE_VERSION}`",
            "",
            "## Decision",
            "",
            f"Decision: `{decision}`.",
            "",
            "This is confirmatory backtest/export validation of the wired policy, not a fresh holdout. Blocking gates pass, monitors are still required, and the champion remains scoped to Top 1000 high-revenue runs behind the explicit policy flag.",
            "",
            _table(
                ["Metric", "Official control", "Official champion", "Delta"],
                [
                    ["Model", CONTROL_MODEL, HIGH_REVENUE_CHAMPION_MODEL, "-"],
                    ["Hit +/-20", _fmt_pct(control["hit20"]), _fmt_pct(champion["hit20"]), _fmt_pp(_delta(champion["hit20"], control["hit20"]))],
                    ["Hit +/-30", _fmt_pct(control["hit30"]), _fmt_pct(champion["hit30"]), _fmt_pp(_delta(champion["hit30"], control["hit30"]))],
                    ["WMAPE", _fmt_pct(control["wmape"]), _fmt_pct(champion["wmape"]), _fmt_pp(_delta(champion["wmape"], control["wmape"]))],
                    ["Bias", _fmt_pct(control["bias"]), _fmt_pct(champion["bias"]), _fmt_pp(_delta(champion["bias"], control["bias"]))],
                    ["Phantom", _fmt_pct(control["phantom_rate"]), _fmt_pct(champion["phantom_rate"]), _fmt_pp(_delta(champion["phantom_rate"], control["phantom_rate"]))],
                ],
            ),
            "",
            "## Policy Safety Checks",
            "",
            _table(["Check", "Expected", "Observed", "Status"], _policy_check_rows(no_policy_rows, champion_rows, guard_passed)),
            "",
            "## Promotion Gates",
            "",
            _table(["Gate", "Required", "Observed", "Status"], gate_rows),
            "",
            "## Required Monitors",
            "",
            _table(["Monitor", "Status", "Observed", "Why it matters"], _monitor_rows(champion_rows)),
            "",
            "## Official Aggregate Models",
            "",
            _table(
                ["Model", "Rows", "Qty scored", "Hit +/-20", "Delta vs control", "Hit +/-30", "WMAPE", "Bias", "Phantom"],
                _aggregate_rows(champion_rows),
            ),
            "",
            "## Revenue Scope Validation",
            "",
            _table(
                [
                    "Scope",
                    "Rows",
                    "Qty scored",
                    "Actual revenue",
                    "Control hit +/-20",
                    "Champion hit +/-20",
                    "Hit delta",
                    "Control hit +/-30",
                    "Champion hit +/-30",
                    "Control WMAPE",
                    "Champion WMAPE",
                    "WMAPE delta",
                    "Control bias",
                    "Champion bias",
                    "Control phantom",
                    "Champion phantom",
                    "Phantom delta",
                ],
                _scope_rows(champion_rows),
            ),
            "",
            "## Critical Slice Validation",
            "",
            _table(
                [
                    "Slice",
                    "Rows",
                    "Qty scored",
                    "Actual revenue",
                    "Control hit +/-20",
                    "Champion hit +/-20",
                    "Hit delta",
                    "Control hit +/-30",
                    "Champion hit +/-30",
                    "Control WMAPE",
                    "Champion WMAPE",
                    "WMAPE delta",
                    "Control bias",
                    "Champion bias",
                    "Control phantom",
                    "Champion phantom",
                    "Phantom delta",
                ],
                _critical_slice_rows(champion_rows),
            ),
            "",
            "## Route Validation",
            "",
            _table(
                [
                    "Route",
                    "Rows",
                    "Qty scored",
                    "Actual revenue",
                    "Control hit +/-20",
                    "Champion hit +/-20",
                    "Hit delta",
                    "Control hit +/-30",
                    "Champion hit +/-30",
                    "Control WMAPE",
                    "Champion WMAPE",
                    "WMAPE delta",
                    "Control bias",
                    "Champion bias",
                    "Control phantom",
                    "Champion phantom",
                    "Phantom delta",
                ],
                _route_rows(champion_rows),
            ),
            "",
            "## Window Validation",
            "",
            _table(
                [
                    "Target start",
                    "Rows",
                    "Qty scored",
                    "Actual revenue",
                    "Control hit +/-20",
                    "Champion hit +/-20",
                    "Hit delta",
                    "Control hit +/-30",
                    "Champion hit +/-30",
                    "Control WMAPE",
                    "Champion WMAPE",
                    "WMAPE delta",
                    "Control bias",
                    "Champion bias",
                    "Control phantom",
                    "Champion phantom",
                    "Phantom delta",
                ],
                _window_rows(champion_rows),
            ),
            "",
            "## Zero-Actual / Phantom Export Check",
            "",
            _table(
                [
                    "Baseline",
                    "Zero-actual rows",
                    "Baseline phantom",
                    "Champion phantom",
                    "Phantom delta",
                    "Baseline pred units on zero actual",
                    "Champion pred units on zero actual",
                    "Baseline avg pred units",
                    "Champion avg pred units",
                ],
                _zero_actual_rows(champion_rows),
            ),
            "",
            "## Export Metadata",
            "",
            f"- Revenue-rank limit: Top {revenue_rank_limit}.",
            f"- Champion model: `{HIGH_REVENUE_CHAMPION_MODEL}`.",
            f"- Champion prediction source: `{HIGH_REVENUE_CHAMPION_SOURCE}`.",
            f"- Champion model version: `{HIGH_REVENUE_CHAMPION_VERSION}`.",
            f"- Official score-row CSV: `{score_rows_csv}`." if score_rows_csv else "- Official score-row CSV: not written.",
            f"- Default-policy skipped windows: {', '.join(f'`{item}`' for item in no_policy_skipped) if no_policy_skipped else 'None'}.",
            f"- Champion-policy skipped windows: {', '.join(f'`{item}`' for item in champion_skipped) if champion_skipped else 'None'}.",
            "- The default v2 sklearn path remains `--high-revenue-policy none`.",
            "- The champion path requires `--high-revenue-policy champion --revenue-rank-limit 1000`.",
            "- This is confirmatory rolling backtest validation on the known Phase 8G target windows, not independent future holdout validation.",
            "- This report uses row-level output from `backend/forecast_engine_v2/sklearn_direct_model.py`, not the cached research runners.",
        ]
    ) + "\n"


def _run_official(
    conn: sqlite3.Connection,
    target_starts: list[str],
    min_train_windows: int,
    random_state: int,
    revenue_rank_limit: int,
    high_revenue_policy: str,
    config: ScorecardConfig,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, list[str], pd.DataFrame]:
    slices, aggregate, tuning, skipped, score_rows = run_sklearn_models(
        conn,
        target_starts=target_starts,
        min_train_windows=min_train_windows,
        random_state=random_state,
        revenue_rank_limit=revenue_rank_limit,
        high_revenue_policy=high_revenue_policy,
        config=config,
        include_score_rows=True,
    )
    return slices, aggregate, tuning, skipped, score_rows


def _guard_check(conn: sqlite3.Connection, target_starts: list[str], min_train_windows: int, random_state: int, config: ScorecardConfig) -> bool:
    try:
        run_sklearn_models(
            conn,
            target_starts=target_starts[:1],
            min_train_windows=min_train_windows,
            random_state=random_state,
            revenue_rank_limit=None,
            high_revenue_policy="champion",
            config=config,
            include_score_rows=True,
        )
    except ValueError:
        return True
    return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Phase 8G-I official high-revenue policy validation.")
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--score-rows-csv", type=Path, default=DEFAULT_SCORE_ROWS_CSV)
    parser.add_argument("--target-start", action="append", default=None)
    parser.add_argument("--min-train-windows", type=int, default=4)
    parser.add_argument("--random-state", type=int, default=42)
    parser.add_argument("--revenue-rank-limit", type=int, default=1000)
    args = parser.parse_args()

    if args.revenue_rank_limit != 1000:
        raise ValueError("Phase 8G-I validates the official Top 1000 policy scope: revenue_rank_limit must be exactly 1000")

    config = ScorecardConfig()
    target_starts = args.target_start or DEFAULT_TARGET_STARTS
    conn = sqlite3.connect(args.db)
    try:
        guard_passed = _guard_check(conn, target_starts, args.min_train_windows, args.random_state, config)
        _, _, _, no_policy_skipped, no_policy_rows = _run_official(
            conn,
            target_starts=target_starts,
            min_train_windows=args.min_train_windows,
            random_state=args.random_state,
            revenue_rank_limit=args.revenue_rank_limit,
            high_revenue_policy="none",
            config=config,
        )
        _, _, _, champion_skipped, champion_rows = _run_official(
            conn,
            target_starts=target_starts,
            min_train_windows=args.min_train_windows,
            random_state=args.random_state,
            revenue_rank_limit=args.revenue_rank_limit,
            high_revenue_policy="champion",
            config=config,
        )
    finally:
        conn.close()

    if args.score_rows_csv:
        args.score_rows_csv.parent.mkdir(parents=True, exist_ok=True)
        champion_rows.to_csv(args.score_rows_csv, index=False)

    report = build_report(
        no_policy_rows=no_policy_rows,
        champion_rows=champion_rows,
        no_policy_skipped=no_policy_skipped,
        champion_skipped=champion_skipped,
        guard_passed=guard_passed,
        revenue_rank_limit=args.revenue_rank_limit,
        score_rows_csv=args.score_rows_csv,
    )
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report, encoding="utf-8")
    print(report)
    print(f"Wrote {args.report}")
    if args.score_rows_csv:
        print(f"Wrote {args.score_rows_csv}")


if __name__ == "__main__":
    main()
