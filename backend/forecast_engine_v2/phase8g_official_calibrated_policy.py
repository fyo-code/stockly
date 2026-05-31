"""Phase 8G-K official validation for the calibrated high-revenue policy."""

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
        HIGH_REVENUE_CALIBRATED_MODEL,
        HIGH_REVENUE_CALIBRATED_SOURCE,
        HIGH_REVENUE_CALIBRATED_VERSION,
        HIGH_REVENUE_CHAMPION_MODEL,
        HIGH_REVENUE_CHAMPION_VERSION,
        run_sklearn_models,
    )
except ImportError:  # Allows direct script execution.
    from feature_matrix import DEFAULT_TARGET_STARTS
    from route_labels import ROUTE_ORDER, ROUTE_VERSION
    from scorecard import DB_PATH, ScorecardConfig
    from sklearn_direct_model import (
        HIGH_REVENUE_CALIBRATED_MODEL,
        HIGH_REVENUE_CALIBRATED_SOURCE,
        HIGH_REVENUE_CALIBRATED_VERSION,
        HIGH_REVENUE_CHAMPION_MODEL,
        HIGH_REVENUE_CHAMPION_VERSION,
        run_sklearn_models,
    )


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REPORT = PROJECT_ROOT / "active_docs" / "ITER5Z_V2_PHASE8G_OFFICIAL_CALIBRATED_POLICY.md"
DEFAULT_SCORE_ROWS_CSV = PROJECT_ROOT / "active_docs" / "ITER5Z_V2_PHASE8G_OFFICIAL_CALIBRATED_SCORE_ROWS.csv"
CONTROL_MODEL = "sk_blend_post_bf_safe"
REVENUE_SCOPES = [100, 250, 500, 750, 1000]
REGULAR_ROUTES = {"available_regular", "proxy_available_regular"}
STRESS_WINDOW = "2024-11-25"
NON_STRESS_MONITOR_WINDOW = "2025-03-24"


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


def _scope_mask(rows: pd.DataFrame, rank_limit: int) -> pd.Series:
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


def _model_mask(score_rows: pd.DataFrame, model_name: str, mask: pd.Series) -> pd.DataFrame:
    return score_rows[(score_rows["model_name"] == model_name) & mask].copy()


def _compare_row(score_rows: pd.DataFrame, candidate_model: str, baseline_model: str, label: str, mask: pd.Series) -> list[str]:
    baseline = _metrics(_model_mask(score_rows, baseline_model, mask))
    candidate = _metrics(_model_mask(score_rows, candidate_model, mask))
    return [
        label,
        f"{candidate['rows']:,}",
        f"{candidate['scored']:,}",
        _fmt_num(candidate["actual_revenue"], 0),
        _fmt_pct(baseline["hit20"]),
        _fmt_pct(candidate["hit20"]),
        _fmt_pp(_delta(candidate["hit20"], baseline["hit20"])),
        _fmt_pct(baseline["hit30"]),
        _fmt_pct(candidate["hit30"]),
        _fmt_pct(baseline["wmape"]),
        _fmt_pct(candidate["wmape"]),
        _fmt_pp(_delta(candidate["wmape"], baseline["wmape"])),
        _fmt_pct(baseline["bias"]),
        _fmt_pct(candidate["bias"]),
        _fmt_pp(_delta(candidate["bias"], baseline["bias"])),
        _fmt_pct(baseline["phantom_rate"]),
        _fmt_pct(candidate["phantom_rate"]),
        _fmt_pp(_delta(candidate["phantom_rate"], baseline["phantom_rate"])),
    ]


def _aggregate_rows(score_rows: pd.DataFrame) -> list[list[str]]:
    rows: list[list[str]] = []
    control = _model_metrics(score_rows, CONTROL_MODEL)
    order = {
        CONTROL_MODEL: 0,
        HIGH_REVENUE_CHAMPION_MODEL: 1,
        HIGH_REVENUE_CALIBRATED_MODEL: 2,
        "sk_extra_trees": 3,
        "sk_hgb_squared": 4,
        "post_bf_safe_naive": 5,
        "median_naive": 6,
    }
    for model_name, group in sorted(score_rows.groupby("model_name"), key=lambda item: order.get(str(item[0]), 99)):
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


def _scope_rows(score_rows: pd.DataFrame, candidate_model: str, baseline_model: str) -> list[list[str]]:
    return [
        _compare_row(score_rows, candidate_model, baseline_model, f"Top {rank_limit}", _scope_mask(score_rows, rank_limit))
        for rank_limit in REVENUE_SCOPES
    ]


def _critical_rows(score_rows: pd.DataFrame, candidate_model: str, baseline_model: str) -> list[list[str]]:
    primary_route = score_rows.get("primary_route", pd.Series("", index=score_rows.index)).astype(str)
    campaign_txn_13w = pd.to_numeric(score_rows.get("campaign_txn_13w", 0), errors="coerce").fillna(0)
    bf_txn_13w = pd.to_numeric(score_rows.get("bf_txn_13w", 0), errors="coerce").fillna(0)
    target_post_bf = pd.to_numeric(score_rows.get("target_is_post_bf_4w", 0), errors="coerce").fillna(0)
    bf_unit_share_4w = pd.to_numeric(score_rows.get("bf_unit_share_4w", 0), errors="coerce").fillna(0)
    slices = [
        ("Available/proxy regular", primary_route.isin(REGULAR_ROUTES)),
        ("Available regular", primary_route == "available_regular"),
        ("BF/campaign-sensitive route", primary_route == "bf_campaign_sensitive"),
        ("Any campaign/BF history 13w", (campaign_txn_13w > 0) | (bf_txn_13w > 0)),
        ("Post-BF stress rows", (target_post_bf == 1) & (bf_unit_share_4w > 0)),
        (f"{STRESS_WINDOW} stress window", score_rows["target_start"].astype(str) == STRESS_WINDOW),
        (f"{NON_STRESS_MONITOR_WINDOW} monitor window", score_rows["target_start"].astype(str) == NON_STRESS_MONITOR_WINDOW),
    ]
    return [_compare_row(score_rows, candidate_model, baseline_model, label, mask) for label, mask in slices]


def _window_rows(score_rows: pd.DataFrame, candidate_model: str, baseline_model: str) -> list[list[str]]:
    rows: list[list[str]] = []
    for target_start in sorted(score_rows["target_start"].dropna().astype(str).unique()):
        rows.append(_compare_row(score_rows, candidate_model, baseline_model, target_start, score_rows["target_start"].astype(str) == target_start))
    return rows


def _zero_actual_rows(score_rows: pd.DataFrame) -> list[list[str]]:
    candidate = _model_metrics(score_rows, HIGH_REVENUE_CALIBRATED_MODEL)
    rows: list[list[str]] = []
    for model_name in [CONTROL_MODEL, HIGH_REVENUE_CHAMPION_MODEL, "sk_extra_trees", "sk_hgb_squared", "post_bf_safe_naive", "median_naive"]:
        baseline = _model_metrics(score_rows, model_name)
        rows.append(
            [
                model_name,
                f"{baseline['zero_rows']:,}",
                _fmt_pct(baseline["phantom_rate"]),
                _fmt_pct(candidate["phantom_rate"]),
                _fmt_pp(_delta(candidate["phantom_rate"], baseline["phantom_rate"])),
                _fmt_num(baseline["zero_pred_units"], 1),
                _fmt_num(candidate["zero_pred_units"], 1),
                _fmt_num(baseline["zero_avg_pred_units"], 2),
                _fmt_num(candidate["zero_avg_pred_units"], 2),
            ]
        )
    return rows


def _max_non_stress_wmape_regression(score_rows: pd.DataFrame) -> tuple[str | None, float | None]:
    worst_window: str | None = None
    worst_delta: float | None = None
    for target_start in sorted(score_rows["target_start"].dropna().astype(str).unique()):
        if target_start == STRESS_WINDOW:
            continue
        baseline = _metrics(
            _model_mask(score_rows, HIGH_REVENUE_CHAMPION_MODEL, score_rows["target_start"].astype(str) == target_start)
        )
        candidate = _metrics(
            _model_mask(score_rows, HIGH_REVENUE_CALIBRATED_MODEL, score_rows["target_start"].astype(str) == target_start)
        )
        delta = _delta(candidate["wmape"], baseline["wmape"])
        if delta is None:
            continue
        if worst_delta is None or delta > worst_delta:
            worst_delta = delta
            worst_window = target_start
    return worst_window, worst_delta


def _policy_check_rows(no_policy_rows: pd.DataFrame, candidate_rows: pd.DataFrame, guard_passed: bool) -> list[list[str]]:
    no_policy_candidate_present = bool((no_policy_rows["model_name"] == HIGH_REVENUE_CALIBRATED_MODEL).any())
    candidate_present = bool((candidate_rows["model_name"] == HIGH_REVENUE_CALIBRATED_MODEL).any())
    champion_present = bool((candidate_rows["model_name"] == HIGH_REVENUE_CHAMPION_MODEL).any())
    no_policy_control = _model_metrics(no_policy_rows, CONTROL_MODEL)
    candidate_control = _model_metrics(candidate_rows, CONTROL_MODEL)
    return [
        ["Default policy emits calibrated candidate", "no", "yes" if no_policy_candidate_present else "no", "PASS" if not no_policy_candidate_present else "FAIL"],
        ["Candidate policy emits calibrated candidate", "yes", "yes" if candidate_present else "no", "PASS" if candidate_present else "FAIL"],
        ["Candidate policy also emits 8G-I champion for comparison", "yes", "yes" if champion_present else "no", "PASS" if champion_present else "FAIL"],
        ["Candidate policy blocked without Top 1000-or-lower rank scope", "yes", "yes" if guard_passed else "no", "PASS" if guard_passed else "FAIL"],
        [
            "Same-run control hit +/-20 unchanged by policy flag",
            "0.0pp delta",
            _fmt_pp(_delta(candidate_control["hit20"], no_policy_control["hit20"])),
            "PASS" if abs(_delta(candidate_control["hit20"], no_policy_control["hit20"]) or 0.0) < 1e-12 else "FAIL",
        ],
    ]


def _gate_rows(score_rows: pd.DataFrame) -> tuple[str, list[list[str]]]:
    control = _model_metrics(score_rows, CONTROL_MODEL)
    champion = _model_metrics(score_rows, HIGH_REVENUE_CHAMPION_MODEL)
    candidate = _model_metrics(score_rows, HIGH_REVENUE_CALIBRATED_MODEL)
    top100_control = _metrics(_model_mask(score_rows, CONTROL_MODEL, _scope_mask(score_rows, 100)))
    top100_candidate = _metrics(_model_mask(score_rows, HIGH_REVENUE_CALIBRATED_MODEL, _scope_mask(score_rows, 100)))
    top500_control = _metrics(_model_mask(score_rows, CONTROL_MODEL, _scope_mask(score_rows, 500)))
    top500_candidate = _metrics(_model_mask(score_rows, HIGH_REVENUE_CALIBRATED_MODEL, _scope_mask(score_rows, 500)))
    stress_control = _metrics(_model_mask(score_rows, CONTROL_MODEL, score_rows["target_start"].astype(str) == STRESS_WINDOW))
    stress_candidate = _metrics(_model_mask(score_rows, HIGH_REVENUE_CALIBRATED_MODEL, score_rows["target_start"].astype(str) == STRESS_WINDOW))
    worst_window, worst_non_stress_wmape = _max_non_stress_wmape_regression(score_rows)
    checks = [
        ("Top 1000 hit +/-20", ">= +1.5pp vs control", _delta(candidate["hit20"], control["hit20"]), 0.015, "min"),
        ("Top 1000 WMAPE", "<= +0.5pp vs control", _delta(candidate["wmape"], control["wmape"]), 0.005, "max"),
        ("Top 1000 phantom", "<= +0.5pp vs control", _delta(candidate["phantom_rate"], control["phantom_rate"]), 0.005, "max"),
        ("Top 500 hit +/-20", ">= 0.0pp vs control", _delta(top500_candidate["hit20"], top500_control["hit20"]), 0.0, "min"),
        ("Top 100 hit +/-20", ">= 0.0pp vs control", _delta(top100_candidate["hit20"], top100_control["hit20"]), 0.0, "min"),
        (f"{STRESS_WINDOW} WMAPE", "< control", _delta(stress_candidate["wmape"], stress_control["wmape"]), 0.0, "lt"),
        ("Candidate hit +/-20 vs 8G-I", "> 8G-I", _delta(candidate["hit20"], champion["hit20"]), 0.0, "min_strict"),
        ("Candidate WMAPE vs 8G-I", "<= 8G-I", _delta(candidate["wmape"], champion["wmape"]), 0.0, "max"),
        (f"Largest non-stress WMAPE regression vs 8G-I ({worst_window or '-'})", "<= +2.0pp", worst_non_stress_wmape, 0.020, "max"),
    ]
    rows: list[list[str]] = []
    passes: list[bool] = []
    for label, requirement, observed, threshold, mode in checks:
        if observed is None:
            passed = False
        elif mode == "min":
            passed = observed >= threshold
        elif mode == "min_strict":
            passed = observed > threshold
        elif mode == "max":
            passed = observed <= threshold
        else:
            passed = observed < threshold
        passes.append(passed)
        rows.append([label, requirement, _fmt_pp(observed), "PASS" if passed else "FAIL"])
    decision = "PROMOTE_CALIBRATED_WITH_MONITORS" if all(passes) else "KEEP_8G_I_CHAMPION"
    return decision, rows


def _monitor_rows(score_rows: pd.DataFrame) -> list[list[str]]:
    primary_route = score_rows.get("primary_route", pd.Series("", index=score_rows.index)).astype(str)
    worst_window, _ = _max_non_stress_wmape_regression(score_rows)
    rows = [
        _compare_row(score_rows, HIGH_REVENUE_CALIBRATED_MODEL, HIGH_REVENUE_CHAMPION_MODEL, "All Top 1000", pd.Series(True, index=score_rows.index)),
        _compare_row(score_rows, HIGH_REVENUE_CALIBRATED_MODEL, HIGH_REVENUE_CHAMPION_MODEL, "Available/proxy regular", primary_route.isin(REGULAR_ROUTES)),
        _compare_row(score_rows, HIGH_REVENUE_CALIBRATED_MODEL, HIGH_REVENUE_CHAMPION_MODEL, "Available regular", primary_route == "available_regular"),
        _compare_row(score_rows, HIGH_REVENUE_CALIBRATED_MODEL, HIGH_REVENUE_CHAMPION_MODEL, "BF/campaign-sensitive route", primary_route == "bf_campaign_sensitive"),
        _compare_row(
            score_rows,
            HIGH_REVENUE_CALIBRATED_MODEL,
            HIGH_REVENUE_CHAMPION_MODEL,
            f"{NON_STRESS_MONITOR_WINDOW} monitor window",
            score_rows["target_start"].astype(str) == NON_STRESS_MONITOR_WINDOW,
        ),
        _compare_row(
            score_rows,
            HIGH_REVENUE_CALIBRATED_MODEL,
            HIGH_REVENUE_CHAMPION_MODEL,
            f"{worst_window or '-'} largest non-stress WMAPE regression",
            score_rows["target_start"].astype(str) == (worst_window or ""),
        ),
        _compare_row(
            score_rows,
            HIGH_REVENUE_CALIBRATED_MODEL,
            HIGH_REVENUE_CHAMPION_MODEL,
            f"{STRESS_WINDOW} stress window",
            score_rows["target_start"].astype(str) == STRESS_WINDOW,
        ),
    ]
    return rows


def build_report(
    no_policy_rows: pd.DataFrame,
    candidate_rows: pd.DataFrame,
    no_policy_skipped: list[str],
    candidate_skipped: list[str],
    guard_passed: bool,
    revenue_rank_limit: int,
    score_rows_csv: Path | None,
) -> str:
    decision, gate_rows = _gate_rows(candidate_rows)
    control = _model_metrics(candidate_rows, CONTROL_MODEL)
    champion = _model_metrics(candidate_rows, HIGH_REVENUE_CHAMPION_MODEL)
    candidate = _model_metrics(candidate_rows, HIGH_REVENUE_CALIBRATED_MODEL)
    decision_note = (
        "The calibrated candidate passes the official gates, but remains high-revenue Top 1000 scoped and monitored rather than a clean global model."
        if decision == "PROMOTE_CALIBRATED_WITH_MONITORS"
        else "The calibrated candidate improves the aggregate score, but fails the window-stability gate; keep the 8G-I champion as the official high-revenue policy for now."
    )
    return "\n".join(
        [
            "# Iteration 5Z - V2 Phase 8G-K Official Calibrated Policy Validation",
            "",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"Route version: `{ROUTE_VERSION}`",
            "",
            "## Decision",
            "",
            f"Decision: `{decision}`.",
            "",
            f"This is official rolling backtest/export validation through the main sklearn path. {decision_note}",
            "",
            _table(
                ["Metric", "Official control", "8G-I champion", "8G-K calibrated", "8G-K vs 8G-I"],
                [
                    ["Model", CONTROL_MODEL, HIGH_REVENUE_CHAMPION_MODEL, HIGH_REVENUE_CALIBRATED_MODEL, "-"],
                    ["Hit +/-20", _fmt_pct(control["hit20"]), _fmt_pct(champion["hit20"]), _fmt_pct(candidate["hit20"]), _fmt_pp(_delta(candidate["hit20"], champion["hit20"]))],
                    ["Hit +/-30", _fmt_pct(control["hit30"]), _fmt_pct(champion["hit30"]), _fmt_pct(candidate["hit30"]), _fmt_pp(_delta(candidate["hit30"], champion["hit30"]))],
                    ["WMAPE", _fmt_pct(control["wmape"]), _fmt_pct(champion["wmape"]), _fmt_pct(candidate["wmape"]), _fmt_pp(_delta(candidate["wmape"], champion["wmape"]))],
                    ["Bias", _fmt_pct(control["bias"]), _fmt_pct(champion["bias"]), _fmt_pct(candidate["bias"]), _fmt_pp(_delta(candidate["bias"], champion["bias"]))],
                    ["Phantom", _fmt_pct(control["phantom_rate"]), _fmt_pct(champion["phantom_rate"]), _fmt_pct(candidate["phantom_rate"]), _fmt_pp(_delta(candidate["phantom_rate"], champion["phantom_rate"]))],
                ],
            ),
            "",
            "## Policy Safety Checks",
            "",
            _table(["Check", "Expected", "Observed", "Status"], _policy_check_rows(no_policy_rows, candidate_rows, guard_passed)),
            "",
            "## Promotion Gates",
            "",
            _table(["Gate", "Required", "Observed", "Status"], gate_rows),
            "",
            "## Required Monitors",
            "",
            _table(
                [
                    "Monitor",
                    "Rows",
                    "Qty scored",
                    "Actual revenue",
                    "8G-I hit +/-20",
                    "8G-K hit +/-20",
                    "Hit delta",
                    "8G-I hit +/-30",
                    "8G-K hit +/-30",
                    "8G-I WMAPE",
                    "8G-K WMAPE",
                    "WMAPE delta",
                    "8G-I bias",
                    "8G-K bias",
                    "Bias delta",
                    "8G-I phantom",
                    "8G-K phantom",
                    "Phantom delta",
                ],
                _monitor_rows(candidate_rows),
            ),
            "",
            "## Official Aggregate Models",
            "",
            _table(
                ["Model", "Rows", "Qty scored", "Hit +/-20", "Delta vs control", "Hit +/-30", "WMAPE", "Bias", "Phantom"],
                _aggregate_rows(candidate_rows),
            ),
            "",
            "## Revenue Scope Validation - Candidate vs Control",
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
                    "Control hit +/-30",
                    "Candidate hit +/-30",
                    "Control WMAPE",
                    "Candidate WMAPE",
                    "WMAPE delta",
                    "Control bias",
                    "Candidate bias",
                    "Bias delta",
                    "Control phantom",
                    "Candidate phantom",
                    "Phantom delta",
                ],
                _scope_rows(candidate_rows, HIGH_REVENUE_CALIBRATED_MODEL, CONTROL_MODEL),
            ),
            "",
            "## Critical Slice Validation - Candidate vs 8G-I",
            "",
            _table(
                [
                    "Slice",
                    "Rows",
                    "Qty scored",
                    "Actual revenue",
                    "8G-I hit +/-20",
                    "Candidate hit +/-20",
                    "Hit delta",
                    "8G-I hit +/-30",
                    "Candidate hit +/-30",
                    "8G-I WMAPE",
                    "Candidate WMAPE",
                    "WMAPE delta",
                    "8G-I bias",
                    "Candidate bias",
                    "Bias delta",
                    "8G-I phantom",
                    "Candidate phantom",
                    "Phantom delta",
                ],
                _critical_rows(candidate_rows, HIGH_REVENUE_CALIBRATED_MODEL, HIGH_REVENUE_CHAMPION_MODEL),
            ),
            "",
            "## Route Validation - Candidate vs 8G-I",
            "",
            _table(
                [
                    "Route",
                    "Rows",
                    "Qty scored",
                    "Actual revenue",
                    "8G-I hit +/-20",
                    "Candidate hit +/-20",
                    "Hit delta",
                    "8G-I hit +/-30",
                    "Candidate hit +/-30",
                    "8G-I WMAPE",
                    "Candidate WMAPE",
                    "WMAPE delta",
                    "8G-I bias",
                    "Candidate bias",
                    "Bias delta",
                    "8G-I phantom",
                    "Candidate phantom",
                    "Phantom delta",
                ],
                [
                    _compare_row(candidate_rows, HIGH_REVENUE_CALIBRATED_MODEL, HIGH_REVENUE_CHAMPION_MODEL, route, candidate_rows["primary_route"].astype(str) == route)
                    for route in [route for route in ROUTE_ORDER if route in set(candidate_rows["primary_route"].dropna().astype(str))]
                ],
            ),
            "",
            "## Window Validation - Candidate vs 8G-I",
            "",
            _table(
                [
                    "Target start",
                    "Rows",
                    "Qty scored",
                    "Actual revenue",
                    "8G-I hit +/-20",
                    "Candidate hit +/-20",
                    "Hit delta",
                    "8G-I hit +/-30",
                    "Candidate hit +/-30",
                    "8G-I WMAPE",
                    "Candidate WMAPE",
                    "WMAPE delta",
                    "8G-I bias",
                    "Candidate bias",
                    "Bias delta",
                    "8G-I phantom",
                    "Candidate phantom",
                    "Phantom delta",
                ],
                _window_rows(candidate_rows, HIGH_REVENUE_CALIBRATED_MODEL, HIGH_REVENUE_CHAMPION_MODEL),
            ),
            "",
            "## Zero-Actual / Phantom Export Check",
            "",
            _table(
                [
                    "Baseline",
                    "Zero-actual rows",
                    "Baseline phantom",
                    "Candidate phantom",
                    "Phantom delta",
                    "Baseline pred units on zero actual",
                    "Candidate pred units on zero actual",
                    "Baseline avg pred units",
                    "Candidate avg pred units",
                ],
                _zero_actual_rows(candidate_rows),
            ),
            "",
            "## Export Metadata",
            "",
            f"- Revenue-rank limit: Top {revenue_rank_limit}.",
            f"- 8G-I champion model/version: `{HIGH_REVENUE_CHAMPION_MODEL}` / `{HIGH_REVENUE_CHAMPION_VERSION}`.",
            f"- 8G-K calibrated model/version: `{HIGH_REVENUE_CALIBRATED_MODEL}` / `{HIGH_REVENUE_CALIBRATED_VERSION}`.",
            f"- 8G-K prediction source: `{HIGH_REVENUE_CALIBRATED_SOURCE}`.",
            f"- Official score-row CSV: `{score_rows_csv}`." if score_rows_csv else "- Official score-row CSV: not written.",
            f"- Default-policy skipped windows: {', '.join(f'`{item}`' for item in no_policy_skipped) if no_policy_skipped else 'None'}.",
            f"- Candidate-policy skipped windows: {', '.join(f'`{item}`' for item in candidate_skipped) if candidate_skipped else 'None'}.",
            "- The default v2 sklearn path remains `--high-revenue-policy none`.",
            "- The calibrated path requires `--high-revenue-policy bfc_lift_150 --revenue-rank-limit 1000`.",
            "- This is official rolling backtest validation on the known Phase 8G target windows, not independent future holdout validation.",
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
            high_revenue_policy="bfc_lift_150",
            config=config,
            include_score_rows=True,
        )
    except ValueError:
        return True
    return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Phase 8G-K official calibrated high-revenue policy validation.")
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--score-rows-csv", type=Path, default=DEFAULT_SCORE_ROWS_CSV)
    parser.add_argument("--target-start", action="append", default=None)
    parser.add_argument("--min-train-windows", type=int, default=4)
    parser.add_argument("--random-state", type=int, default=42)
    parser.add_argument("--revenue-rank-limit", type=int, default=1000)
    args = parser.parse_args()

    if args.revenue_rank_limit != 1000:
        raise ValueError("Phase 8G-K validates the official Top 1000 policy scope: revenue_rank_limit must be exactly 1000")

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
        _, _, _, candidate_skipped, candidate_rows = _run_official(
            conn,
            target_starts=target_starts,
            min_train_windows=args.min_train_windows,
            random_state=args.random_state,
            revenue_rank_limit=args.revenue_rank_limit,
            high_revenue_policy="bfc_lift_150",
            config=config,
        )
    finally:
        conn.close()

    if args.score_rows_csv:
        args.score_rows_csv.parent.mkdir(parents=True, exist_ok=True)
        candidate_rows.to_csv(args.score_rows_csv, index=False)

    report = build_report(
        no_policy_rows=no_policy_rows,
        candidate_rows=candidate_rows,
        no_policy_skipped=no_policy_skipped,
        candidate_skipped=candidate_skipped,
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
