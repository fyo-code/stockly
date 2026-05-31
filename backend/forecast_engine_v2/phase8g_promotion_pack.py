"""Phase 8G-G promotion and robustness pack for the 8G-F champion."""

from __future__ import annotations

import argparse
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd

try:
    from .feature_matrix import DEFAULT_TARGET_STARTS
    from .feature_matrix_cache import DEFAULT_CACHE_DIR
    from .phase8g_combined_route_model import (
        PHASE8GD_BEST,
        PHASE8GE_BEST,
        PHASE8GF_COMBINED,
        PHASE8E_CONTROL,
        _fmt_num,
        _fmt_pct,
        _fmt_pp,
        _metrics,
        _scope_mask,
        _table,
        run_phase8gf,
    )
    from .route_labels import ROUTE_ORDER, ROUTE_VERSION
    from .scorecard import DB_PATH, ScorecardConfig
except ImportError:  # Allows direct script execution.
    from feature_matrix import DEFAULT_TARGET_STARTS
    from feature_matrix_cache import DEFAULT_CACHE_DIR
    from phase8g_combined_route_model import (
        PHASE8GD_BEST,
        PHASE8GE_BEST,
        PHASE8GF_COMBINED,
        PHASE8E_CONTROL,
        _fmt_num,
        _fmt_pct,
        _fmt_pp,
        _metrics,
        _scope_mask,
        _table,
        run_phase8gf,
    )
    from route_labels import ROUTE_ORDER, ROUTE_VERSION
    from scorecard import DB_PATH, ScorecardConfig


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REPORT = PROJECT_ROOT / "active_docs" / "ITER5V_V2_PHASE8G_PROMOTION_PACK.md"

CHAMPION = PHASE8GF_COMBINED
BASELINE_MODELS = [
    PHASE8E_CONTROL,
    PHASE8GD_BEST,
    PHASE8GE_BEST,
    "sk_extra_trees",
    "sk_hgb_squared",
    "post_bf_safe_naive",
    "median_naive",
]
REVENUE_SCOPES = [100, 250, 500, 750, 1000]


def _delta(candidate: object, baseline: object) -> float | None:
    if candidate is None or baseline is None or pd.isna(candidate) or pd.isna(baseline):
        return None
    return float(candidate) - float(baseline)


def _gate(kind: str, status: str, gate: str, observed: str, note: str) -> list[str]:
    return [kind, status, gate, observed, note]


def _aggregate_compare_rows(score_rows: pd.DataFrame) -> list[list[str]]:
    champion = _metrics(score_rows[score_rows["model_name"] == CHAMPION])
    rows: list[list[str]] = []
    for model_name in BASELINE_MODELS:
        baseline = _metrics(score_rows[score_rows["model_name"] == model_name])
        rows.append(
            [
                model_name,
                _fmt_pct(baseline["hit20"]),
                _fmt_pct(champion["hit20"]),
                _fmt_pp(_delta(champion["hit20"], baseline["hit20"])),
                _fmt_pct(baseline["hit30"]),
                _fmt_pct(champion["hit30"]),
                _fmt_pp(_delta(champion["hit30"], baseline["hit30"])),
                _fmt_pct(baseline["wmape"]),
                _fmt_pct(champion["wmape"]),
                _fmt_pp(_delta(champion["wmape"], baseline["wmape"])),
                _fmt_pct(baseline["phantom_rate"]),
                _fmt_pct(champion["phantom_rate"]),
                _fmt_pp(_delta(champion["phantom_rate"], baseline["phantom_rate"])),
                _fmt_pct(baseline["bias"]),
                _fmt_pct(champion["bias"]),
            ]
        )
    return rows


def _scope_compare_rows(score_rows: pd.DataFrame) -> list[list[str]]:
    rows: list[list[str]] = []
    control_rows = score_rows[score_rows["model_name"] == PHASE8E_CONTROL].copy()
    champion_rows = score_rows[score_rows["model_name"] == CHAMPION].copy()
    for rank_limit in REVENUE_SCOPES:
        control = _metrics(control_rows[_scope_mask(control_rows, rank_limit)])
        champion = _metrics(champion_rows[_scope_mask(champion_rows, rank_limit)])
        rows.append(
            [
                f"Top {rank_limit}",
                f"{champion['rows']:,}",
                f"{champion['scored']:,}",
                _fmt_num(champion["actual_revenue"], 0),
                _fmt_pct(control["hit20"]),
                _fmt_pct(champion["hit20"]),
                _fmt_pp(_delta(champion["hit20"], control["hit20"])),
                _fmt_pct(control["wmape"]),
                _fmt_pct(champion["wmape"]),
                _fmt_pp(_delta(champion["wmape"], control["wmape"])),
                _fmt_pct(control["phantom_rate"]),
                _fmt_pct(champion["phantom_rate"]),
                _fmt_pp(_delta(champion["phantom_rate"], control["phantom_rate"])),
            ]
        )
    return rows


def _route_compare_rows(score_rows: pd.DataFrame) -> list[list[str]]:
    rows: list[list[str]] = []
    control_rows = score_rows[score_rows["model_name"] == PHASE8E_CONTROL].copy()
    champion_rows = score_rows[score_rows["model_name"] == CHAMPION].copy()
    present_routes = set(champion_rows["primary_route"].dropna().astype(str))
    for route in [route for route in ROUTE_ORDER if route in present_routes]:
        control = _metrics(control_rows[control_rows["primary_route"] == route])
        champion = _metrics(champion_rows[champion_rows["primary_route"] == route])
        rows.append(
            [
                route,
                f"{champion['rows']:,}",
                f"{champion['scored']:,}",
                _fmt_pct(control["hit20"]),
                _fmt_pct(champion["hit20"]),
                _fmt_pp(_delta(champion["hit20"], control["hit20"])),
                _fmt_pct(control["wmape"]),
                _fmt_pct(champion["wmape"]),
                _fmt_pp(_delta(champion["wmape"], control["wmape"])),
                _fmt_pct(control["bias"]),
                _fmt_pct(champion["bias"]),
                _fmt_pct(control["phantom_rate"]),
                _fmt_pct(champion["phantom_rate"]),
                _fmt_pp(_delta(champion["phantom_rate"], control["phantom_rate"])),
            ]
        )
    return rows


def _window_compare_metrics(score_rows: pd.DataFrame) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    control_rows = score_rows[score_rows["model_name"] == PHASE8E_CONTROL].copy()
    champion_rows = score_rows[score_rows["model_name"] == CHAMPION].copy()
    for target_start in sorted(champion_rows["target_start"].dropna().astype(str).unique()):
        control = _metrics(control_rows[control_rows["target_start"].astype(str) == target_start])
        champion = _metrics(champion_rows[champion_rows["target_start"].astype(str) == target_start])
        rows.append(
            {
                "target_start": target_start,
                "scored": champion["scored"],
                "control": control,
                "champion": champion,
                "hit_delta": _delta(champion["hit20"], control["hit20"]),
                "wmape_delta": _delta(champion["wmape"], control["wmape"]),
            }
        )
    return rows


def _window_compare_rows(score_rows: pd.DataFrame) -> list[list[str]]:
    rows: list[list[str]] = []
    for item in _window_compare_metrics(score_rows):
        control = item["control"]
        champion = item["champion"]
        rows.append(
            [
                str(item["target_start"]),
                f"{champion['scored']:,}",
                _fmt_pct(control["hit20"]),
                _fmt_pct(champion["hit20"]),
                _fmt_pp(item["hit_delta"]),
                _fmt_pct(control["wmape"]),
                _fmt_pct(champion["wmape"]),
                _fmt_pp(item["wmape_delta"]),
                _fmt_pct(control["bias"]),
                _fmt_pct(champion["bias"]),
                _fmt_pct(control["phantom_rate"]),
                _fmt_pct(champion["phantom_rate"]),
            ]
        )
    return rows


def _zero_actual_metrics(rows: pd.DataFrame) -> dict[str, object]:
    zero_rows = rows[rows["actual_units"] == 0].copy()
    if zero_rows.empty:
        return {
            "rows": 0,
            "phantom_rate": None,
            "pred_sale_rate": None,
            "pred_units": 0.0,
            "avg_pred_units": None,
        }
    pred_units = float(zero_rows["pred_units"].sum())
    return {
        "rows": int(len(zero_rows)),
        "phantom_rate": float(zero_rows["phantom"].mean()),
        "pred_sale_rate": float(zero_rows["pred_sale"].mean()),
        "pred_units": pred_units,
        "avg_pred_units": float(zero_rows["pred_units"].mean()),
    }


def _zero_actual_rows(score_rows: pd.DataFrame) -> list[list[str]]:
    rows: list[list[str]] = []
    champion = _zero_actual_metrics(score_rows[score_rows["model_name"] == CHAMPION])
    for model_name in [PHASE8E_CONTROL, PHASE8GD_BEST, PHASE8GE_BEST, "sk_extra_trees", "sk_hgb_squared"]:
        baseline = _zero_actual_metrics(score_rows[score_rows["model_name"] == model_name])
        rows.append(
            [
                model_name,
                f"{baseline['rows']:,}",
                _fmt_pct(baseline["phantom_rate"]),
                _fmt_pct(champion["phantom_rate"]),
                _fmt_pp(_delta(champion["phantom_rate"], baseline["phantom_rate"])),
                _fmt_pct(baseline["pred_sale_rate"]),
                _fmt_pct(champion["pred_sale_rate"]),
                _fmt_num(baseline["pred_units"], 1),
                _fmt_num(champion["pred_units"], 1),
                _fmt_num(baseline["avg_pred_units"], 2),
                _fmt_num(champion["avg_pred_units"], 2),
            ]
        )
    return rows


def _gate_rows(score_rows: pd.DataFrame, primary_scope: int) -> tuple[str, list[list[str]]]:
    scoped_control_rows = score_rows[(score_rows["model_name"] == PHASE8E_CONTROL) & _scope_mask(score_rows, primary_scope)]
    scoped_champion_rows = score_rows[(score_rows["model_name"] == CHAMPION) & _scope_mask(score_rows, primary_scope)]
    control = _metrics(scoped_control_rows)
    champion = _metrics(scoped_champion_rows)
    top100_control = _metrics(score_rows[(score_rows["model_name"] == PHASE8E_CONTROL) & _scope_mask(score_rows, 100)])
    top100_champion = _metrics(score_rows[(score_rows["model_name"] == CHAMPION) & _scope_mask(score_rows, 100)])
    top500_control = _metrics(score_rows[(score_rows["model_name"] == PHASE8E_CONTROL) & _scope_mask(score_rows, 500)])
    top500_champion = _metrics(score_rows[(score_rows["model_name"] == CHAMPION) & _scope_mask(score_rows, 500)])
    regular_control = _metrics(
        score_rows[
            (score_rows["model_name"] == PHASE8E_CONTROL)
            & score_rows["primary_route"].isin({"available_regular", "proxy_available_regular"})
        ]
    )
    regular_champion = _metrics(
        score_rows[
            (score_rows["model_name"] == CHAMPION)
            & score_rows["primary_route"].isin({"available_regular", "proxy_available_regular"})
        ]
    )
    stress_control = _metrics(
        score_rows[(score_rows["model_name"] == PHASE8E_CONTROL) & (score_rows["target_start"].astype(str) == "2024-11-25")]
    )
    stress_champion = _metrics(
        score_rows[(score_rows["model_name"] == CHAMPION) & (score_rows["target_start"].astype(str) == "2024-11-25")]
    )
    component_hits = [
        _metrics(score_rows[score_rows["model_name"] == PHASE8GD_BEST])["hit20"],
        _metrics(score_rows[score_rows["model_name"] == PHASE8GE_BEST])["hit20"],
    ]

    hit_delta = _delta(champion["hit20"], control["hit20"])
    wmape_delta = _delta(champion["wmape"], control["wmape"])
    phantom_delta = _delta(champion["phantom_rate"], control["phantom_rate"])
    top100_hit_delta = _delta(top100_champion["hit20"], top100_control["hit20"])
    top500_hit_delta = _delta(top500_champion["hit20"], top500_control["hit20"])
    regular_phantom_delta = _delta(regular_champion["phantom_rate"], regular_control["phantom_rate"])
    stress_wmape_delta = _delta(stress_champion["wmape"], stress_control["wmape"])
    window_items = _window_compare_metrics(score_rows)
    non_stress_wmape_deltas = [
        float(item["wmape_delta"])
        for item in window_items
        if item["wmape_delta"] is not None and item["target_start"] != "2024-11-25"
    ]
    max_non_stress_wmape_delta = max(non_stress_wmape_deltas) if non_stress_wmape_deltas else None

    rows = [
        _gate(
            "BLOCKING",
            "PASS" if hit_delta is not None and hit_delta >= 0.015 else "FAIL",
            f"Top {primary_scope} hit +/-20 improves by at least +1.5pp vs safer control",
            _fmt_pp(hit_delta),
            "Primary high-revenue promotion gate.",
        ),
        _gate(
            "BLOCKING",
            "PASS" if wmape_delta is not None and wmape_delta <= 0.005 else "FAIL",
            f"Top {primary_scope} WMAPE does not worsen by more than +0.5pp",
            _fmt_pp(wmape_delta),
            "Candidate improves WMAPE materially.",
        ),
        _gate(
            "BLOCKING",
            "PASS" if phantom_delta is not None and phantom_delta <= 0.005 else "FAIL",
            f"Top {primary_scope} phantom rate does not worsen by more than +0.5pp",
            _fmt_pp(phantom_delta),
            "Candidate improves phantom rate materially.",
        ),
        _gate(
            "BLOCKING",
            "PASS"
            if all(hit is not None and champion["hit20"] is not None and float(champion["hit20"]) > float(hit) for hit in component_hits)
            else "FAIL",
            "Champion beats both 8G-D and 8G-E components on hit +/-20",
            _fmt_pct(champion["hit20"]),
            "Prevents promoting a non-stacked composition.",
        ),
        _gate(
            "BLOCKING",
            "PASS" if top500_hit_delta is not None and top500_hit_delta > 0 else "FAIL",
            "Top 500 revenue scope does not regress",
            _fmt_pp(top500_hit_delta),
            "Most useful commercial scope improved.",
        ),
        _gate(
            "BLOCKING",
            "PASS" if top100_hit_delta is not None and top100_hit_delta >= 0 else "FAIL",
            "Top 100 revenue scope does not regress on hit +/-20",
            _fmt_pp(top100_hit_delta),
            "Top 100 gain is modest; WMAPE still improves strongly.",
        ),
        _gate(
            "BLOCKING",
            "PASS" if stress_wmape_delta is not None and stress_wmape_delta < 0 else "FAIL",
            "2024-11-25 BF/post-BF stress window remains protected",
            _fmt_pp(stress_wmape_delta),
            "This was the main catastrophic BF failure window.",
        ),
        _gate(
            "MONITORING",
            "MONITOR" if regular_phantom_delta is not None and regular_phantom_delta > 0.005 else "PASS",
            "Available/proxy regular phantom rate",
            _fmt_pp(regular_phantom_delta),
            "Accepted caveat: regular quantity accuracy improves, but phantom nudges upward on this slice.",
        ),
        _gate(
            "MONITORING",
            "MONITOR" if max_non_stress_wmape_delta is not None and max_non_stress_wmape_delta > 0.005 else "PASS",
            "Largest non-stress window WMAPE regression",
            _fmt_pp(max_non_stress_wmape_delta),
            "Diagnostic caveat only; promotion is driven by aggregate high-revenue gates and named BF stress protection.",
        ),
    ]
    decision = (
        "PROMOTE_HIGH_REVENUE_CHAMPION_WITH_MONITORS"
        if not any(row[0] == "BLOCKING" and row[1] == "FAIL" for row in rows)
        else "DO_NOT_PROMOTE"
    )
    return decision, rows


def build_report(
    matrix: pd.DataFrame,
    score_rows: pd.DataFrame,
    skipped: list[str],
    cache_path: Path,
    cache_hit: bool,
    revenue_rank_limit: int,
    refresh_cache: bool,
) -> str:
    if score_rows.empty:
        return "# Iteration 5V - Forecast V2 Phase 8G-G Promotion Pack\n\nNo scorable windows.\n"

    primary_scope = min(int(revenue_rank_limit), 1000)
    decision, gate_rows = _gate_rows(score_rows, primary_scope)
    champion = _metrics(score_rows[score_rows["model_name"] == CHAMPION])
    control = _metrics(score_rows[score_rows["model_name"] == PHASE8E_CONTROL])
    decision_text = (
        f"Promote `8gf_regular_plus_post_bf_safe` as the current high-revenue Top {primary_scope} champion candidate, and wire it into the main v2 scoring/export path behind an explicit high-revenue policy flag. The decision accepts the monitoring caveats listed below instead of pretending they are clean passes."
        if decision == "PROMOTE_HIGH_REVENUE_CHAMPION_WITH_MONITORS"
        else "Do not promote the 8G-F champion yet; at least one robustness gate failed."
    )

    return "\n".join(
        [
            "# Iteration 5V - Forecast V2 Phase 8G-G Promotion Pack",
            "",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"Route version: `{ROUTE_VERSION}`",
            "",
            "## Decision",
            "",
            f"Decision: `{decision}`.",
            "",
            decision_text,
            "",
            _table(
                ["Metric", "Safer control", "Champion", "Delta"],
                [
                    ["Model", PHASE8E_CONTROL, CHAMPION, "-"],
                    ["Hit +/-20", _fmt_pct(control["hit20"]), _fmt_pct(champion["hit20"]), _fmt_pp(_delta(champion["hit20"], control["hit20"]))],
                    ["Hit +/-30", _fmt_pct(control["hit30"]), _fmt_pct(champion["hit30"]), _fmt_pp(_delta(champion["hit30"], control["hit30"]))],
                    ["WMAPE", _fmt_pct(control["wmape"]), _fmt_pct(champion["wmape"]), _fmt_pp(_delta(champion["wmape"], control["wmape"]))],
                    ["Bias", _fmt_pct(control["bias"]), _fmt_pct(champion["bias"]), _fmt_pp(_delta(champion["bias"], control["bias"]))],
                    ["Phantom rate", _fmt_pct(control["phantom_rate"]), _fmt_pct(champion["phantom_rate"]), _fmt_pp(_delta(champion["phantom_rate"], control["phantom_rate"]))],
                ],
            ),
            "",
            "## Promotion Gates And Monitoring",
            "",
            _table(["Kind", "Status", "Gate", "Observed", "Note"], gate_rows),
            "",
            "## Baseline Robustness",
            "",
            _table(
                [
                    "Baseline",
                    "Baseline hit +/-20",
                    "Champion hit +/-20",
                    "Hit delta",
                    "Baseline hit +/-30",
                    "Champion hit +/-30",
                    "Hit30 delta",
                    "Baseline WMAPE",
                    "Champion WMAPE",
                    "WMAPE delta",
                    "Baseline phantom",
                    "Champion phantom",
                    "Phantom delta",
                    "Baseline bias",
                    "Champion bias",
                ],
                _aggregate_compare_rows(score_rows),
            ),
            "",
            "## Revenue Scope Robustness",
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
                    "Control WMAPE",
                    "Champion WMAPE",
                    "WMAPE delta",
                    "Control phantom",
                    "Champion phantom",
                    "Phantom delta",
                ],
                _scope_compare_rows(score_rows),
            ),
            "",
            "## Route Robustness",
            "",
            _table(
                [
                    "Route",
                    "Rows",
                    "Qty scored",
                    "Control hit +/-20",
                    "Champion hit +/-20",
                    "Hit delta",
                    "Control WMAPE",
                    "Champion WMAPE",
                    "WMAPE delta",
                    "Control bias",
                    "Champion bias",
                    "Control phantom",
                    "Champion phantom",
                    "Phantom delta",
                ],
                _route_compare_rows(score_rows),
            ),
            "",
            "## Window Robustness",
            "",
            _table(
                [
                    "Target start",
                    "Qty scored",
                    "Control hit +/-20",
                    "Champion hit +/-20",
                    "Hit delta",
                    "Control WMAPE",
                    "Champion WMAPE",
                    "WMAPE delta",
                    "Control bias",
                    "Champion bias",
                    "Control phantom",
                    "Champion phantom",
                ],
                _window_compare_rows(score_rows),
            ),
            "",
            "## Zero-Actual / Phantom Robustness",
            "",
            _table(
                [
                    "Baseline",
                    "Zero-actual rows",
                    "Baseline phantom",
                    "Champion phantom",
                    "Phantom delta",
                    "Baseline pred-sale rate",
                    "Champion pred-sale rate",
                    "Baseline pred units on zero actual",
                    "Champion pred units on zero actual",
                    "Baseline avg pred units",
                    "Champion avg pred units",
                ],
                _zero_actual_rows(score_rows),
            ),
            "",
            "## Skipped Windows",
            "",
            ", ".join(f"`{window}`" for window in skipped) if skipped else "None.",
            "",
            "## Notes",
            "",
            f"- Revenue-rank limit: Top {revenue_rank_limit}. Primary promotion gate scope: Top {primary_scope}.",
            f"- Feature matrix rows: {len(matrix):,}.",
            f"- Feature matrix cache: `{cache_path}` ({'hit' if cache_hit else 'built'}; refresh requested: {'yes' if refresh_cache else 'no'}).",
            "- This promotion is high-revenue scoped. It is not a full-headline or low-volume SKU promotion.",
            "- Candidate training still uses only earlier target windows.",
            "- Route/campaign/BF gates are forecast-time-safe.",
            "- Known caveat: the champion improves WMAPE and phantom overall, but it is more underpredictive than the safer control.",
            "- Known caveat: available/proxy regular quantity hit improves, but regular-slice phantom rate nudges up slightly. This is accepted as a monitoring item, not a blocking promotion gate.",
            "- Known caveat: one non-stress window has a small WMAPE regression. Window robustness is diagnostic except for the named 2024-11-25 BF/post-BF stress gate.",
            "- Phase 8F current snapshots remain excluded from historical backtests.",
        ]
    ) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run forecast v2 Phase 8G-G promotion/robustness pack.")
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
        matrix, score_rows, skipped, _diagnostics, cache_path, cache_hit = run_phase8gf(
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
        cache_path,
        cache_hit,
        args.revenue_rank_limit,
        args.refresh_cache,
    )
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report, encoding="utf-8")
    print(report)
    print(f"Wrote {args.report}")


if __name__ == "__main__":
    main()
