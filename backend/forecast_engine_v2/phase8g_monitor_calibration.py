"""Phase 8G-J monitored-caveat calibration candidates for forecast v2."""

from __future__ import annotations

import argparse
import sqlite3
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from .feature_matrix import DEFAULT_TARGET_STARTS
    from .feature_matrix_cache import DEFAULT_CACHE_DIR
    from .phase8g_combined_route_model import PHASE8GF_COMBINED, PHASE8GF_GUARDED, run_phase8gf
    from .phase8g_route_specific_model import PHASE8E_CONTROL, _chronological, _metrics, _scope_mask, _table
    from .route_labels import ROUTE_VERSION
    from .scorecard import DB_PATH, ScorecardConfig
except ImportError:  # Allows direct script execution.
    from feature_matrix import DEFAULT_TARGET_STARTS
    from feature_matrix_cache import DEFAULT_CACHE_DIR
    from phase8g_combined_route_model import PHASE8GF_COMBINED, PHASE8GF_GUARDED, run_phase8gf
    from phase8g_route_specific_model import PHASE8E_CONTROL, _chronological, _metrics, _scope_mask, _table
    from route_labels import ROUTE_VERSION
    from scorecard import DB_PATH, ScorecardConfig


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REPORT = PROJECT_ROOT / "active_docs" / "ITER5Y_V2_PHASE8G_MONITOR_CALIBRATION.md"

PHASE8GJ_BFC_LIFT_110 = "8gj_bfc_nonpost_lift_110"
PHASE8GJ_BFC_LIFT_120 = "8gj_bfc_nonpost_lift_120"
PHASE8GJ_BFC_LIFT_130 = "8gj_bfc_nonpost_lift_130"
PHASE8GJ_BFC_LIFT_140 = "8gj_bfc_nonpost_lift_140"
PHASE8GJ_BFC_LIFT_150 = "8gj_bfc_nonpost_lift_150"
PHASE8GJ_REGULAR_BLEND_10 = "8gj_regular_control_blend_10"
PHASE8GJ_REGULAR_BLEND_25 = "8gj_regular_control_blend_25"
PHASE8GJ_REGULAR_BLEND_40 = "8gj_regular_control_blend_40"

ORDERED_MODELS = [
    PHASE8E_CONTROL,
    PHASE8GF_COMBINED,
    PHASE8GF_GUARDED,
    PHASE8GJ_REGULAR_BLEND_10,
    PHASE8GJ_REGULAR_BLEND_25,
    PHASE8GJ_REGULAR_BLEND_40,
    PHASE8GJ_BFC_LIFT_110,
    PHASE8GJ_BFC_LIFT_120,
    PHASE8GJ_BFC_LIFT_130,
    PHASE8GJ_BFC_LIFT_140,
    PHASE8GJ_BFC_LIFT_150,
]
REGULAR_ROUTES = {"available_regular", "proxy_available_regular"}
PRIMARY_SCOPE = 1000
REVENUE_SCOPES = [100, 250, 500, 750, 1000]
STRESS_WINDOW = "2024-11-25"


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


def _regular_mask(rows: pd.DataFrame) -> pd.Series:
    return rows["primary_route"].isin(REGULAR_ROUTES)


def _bfc_nonpost_lift_mask(rows: pd.DataFrame, pred: np.ndarray) -> pd.Series:
    return (
        (rows["primary_route"] == "bf_campaign_sensitive")
        & (rows["calendar_route_context"] != "post_bf_window")
        & (pd.Series(pred, index=rows.index) >= 3.0)
    )


def _recompute_rows(rows: pd.DataFrame, pred: np.ndarray, model_name: str, config: ScorecardConfig) -> pd.DataFrame:
    output = rows.copy()
    output["model_name"] = model_name
    output["pred_units"] = np.clip(pred.astype(float), 0.0, None)
    output["abs_error"] = (output["pred_units"] - output["actual_units"]).abs()
    output["signed_error"] = output["pred_units"] - output["actual_units"]
    output["quantity_scored"] = (output["actual_units"] >= config.material_units_threshold).astype(int)
    output["abs_pct_error"] = np.where(
        output["quantity_scored"] == 1,
        output["abs_error"] / output["actual_units"],
        np.nan,
    )
    output["hit20"] = np.where(output["quantity_scored"] == 1, (output["abs_pct_error"] <= 0.20).astype(int), np.nan)
    output["hit30"] = np.where(output["quantity_scored"] == 1, (output["abs_pct_error"] <= 0.30).astype(int), np.nan)
    output["under20"] = np.where(
        output["quantity_scored"] == 1,
        (output["pred_units"] < 0.80 * output["actual_units"]).astype(int),
        np.nan,
    )
    output["over20"] = np.where(
        output["quantity_scored"] == 1,
        (output["pred_units"] > 1.20 * output["actual_units"]).astype(int),
        np.nan,
    )
    output["phantom"] = ((output["actual_units"] == 0) & (output["pred_units"] >= config.phantom_threshold)).astype(int)
    output["pred_sale"] = (output["pred_units"] >= config.sale_threshold).astype(int)
    return output


def _candidate_rows(score_rows: pd.DataFrame, config: ScorecardConfig) -> pd.DataFrame:
    champion = score_rows[score_rows["model_name"] == PHASE8GF_COMBINED].copy()
    control = score_rows[score_rows["model_name"] == PHASE8E_CONTROL][["sku_id", "target_start", "pred_units"]].rename(
        columns={"pred_units": "control_pred_units"}
    )
    base = champion.merge(control, on=["sku_id", "target_start"], how="left")
    champion_pred = base["pred_units"].to_numpy(dtype=float)
    control_pred = base["control_pred_units"].fillna(base["pred_units"]).to_numpy(dtype=float)
    candidates: list[pd.DataFrame] = []

    for model_name, weight in [
        (PHASE8GJ_REGULAR_BLEND_10, 0.10),
        (PHASE8GJ_REGULAR_BLEND_25, 0.25),
        (PHASE8GJ_REGULAR_BLEND_40, 0.40),
    ]:
        pred = champion_pred.copy()
        mask = _regular_mask(base).to_numpy(dtype=bool)
        pred[mask] = ((1.0 - weight) * champion_pred[mask]) + (weight * control_pred[mask])
        candidates.append(_recompute_rows(base, pred, model_name, config))

    for model_name, lift in [
        (PHASE8GJ_BFC_LIFT_110, 1.10),
        (PHASE8GJ_BFC_LIFT_120, 1.20),
        (PHASE8GJ_BFC_LIFT_130, 1.30),
        (PHASE8GJ_BFC_LIFT_140, 1.40),
        (PHASE8GJ_BFC_LIFT_150, 1.50),
    ]:
        pred = champion_pred.copy()
        mask = _bfc_nonpost_lift_mask(base, champion_pred).to_numpy(dtype=bool)
        pred[mask] = pred[mask] * lift
        candidates.append(_recompute_rows(base, pred, model_name, config))

    return pd.concat(candidates, ignore_index=True)


def run_phase8gj(
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
    matrix, score_rows, skipped, diagnostics, cache_path, cache_hit = run_phase8gf(
        conn,
        target_starts=target_starts,
        min_train_windows=min_train_windows,
        random_state=random_state,
        revenue_rank_limit=revenue_rank_limit,
        cache_dir=cache_dir,
        refresh_cache=refresh_cache,
        config=config,
    )
    candidate_rows = _candidate_rows(score_rows, config)
    score_rows = pd.concat([score_rows, candidate_rows], ignore_index=True)
    return matrix, score_rows, skipped, diagnostics, cache_path, cache_hit


def _model_rows(score_rows: pd.DataFrame) -> list[list[str]]:
    rows: list[list[str]] = []
    control = _metrics(score_rows[score_rows["model_name"] == PHASE8E_CONTROL])
    champion = _metrics(score_rows[score_rows["model_name"] == PHASE8GF_COMBINED])
    order = {name: idx for idx, name in enumerate(ORDERED_MODELS)}
    for model_name, group in sorted(score_rows.groupby("model_name"), key=lambda item: order.get(str(item[0]), 999)):
        if str(model_name) not in ORDERED_MODELS:
            continue
        metrics = _metrics(group)
        rows.append(
            [
                str(model_name),
                f"{metrics['rows']:,}",
                f"{metrics['scored']:,}",
                _fmt_pct(metrics["hit20"]),
                _fmt_pp(_delta(metrics["hit20"], control["hit20"])),
                _fmt_pp(_delta(metrics["hit20"], champion["hit20"])),
                _fmt_pct(metrics["hit30"]),
                _fmt_pct(metrics["wmape"]),
                _fmt_pp(_delta(metrics["wmape"], champion["wmape"])),
                _fmt_pct(metrics["bias"]),
                _fmt_pp(_delta(metrics["bias"], champion["bias"])),
                _fmt_pct(metrics["phantom_rate"]),
                _fmt_pp(_delta(metrics["phantom_rate"], champion["phantom_rate"])),
            ]
        )
    return rows


def _compare_row(score_rows: pd.DataFrame, model_name: str, baseline_model: str, label: str, mask: pd.Series) -> list[str]:
    baseline = _metrics(score_rows[(score_rows["model_name"] == baseline_model) & mask])
    candidate = _metrics(score_rows[(score_rows["model_name"] == model_name) & mask])
    return [
        label,
        f"{candidate['rows']:,}",
        f"{candidate['scored']:,}",
        _fmt_num(candidate["actual_revenue"], 0),
        _fmt_pct(baseline["hit20"]),
        _fmt_pct(candidate["hit20"]),
        _fmt_pp(_delta(candidate["hit20"], baseline["hit20"])),
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


def _scope_rows(score_rows: pd.DataFrame, model_name: str) -> list[list[str]]:
    return [
        _compare_row(score_rows, model_name, PHASE8E_CONTROL, f"Top {rank_limit}", _scope_mask(score_rows, rank_limit))
        for rank_limit in REVENUE_SCOPES
    ]


def _monitor_rows(score_rows: pd.DataFrame, model_name: str) -> list[list[str]]:
    champion = PHASE8GF_COMBINED
    primary_route = score_rows.get("primary_route", pd.Series("", index=score_rows.index)).astype(str)
    rows = [
        _compare_row(score_rows, model_name, champion, "All Top 1000", pd.Series(True, index=score_rows.index)),
        _compare_row(score_rows, model_name, champion, "Available/proxy regular", primary_route.isin(REGULAR_ROUTES)),
        _compare_row(score_rows, model_name, champion, "Available regular", primary_route == "available_regular"),
        _compare_row(score_rows, model_name, champion, "BF/campaign-sensitive route", primary_route == "bf_campaign_sensitive"),
        _compare_row(score_rows, model_name, champion, "2025-03-24 window", score_rows["target_start"].astype(str) == "2025-03-24"),
        _compare_row(score_rows, model_name, champion, f"{STRESS_WINDOW} stress", score_rows["target_start"].astype(str) == STRESS_WINDOW),
    ]
    return rows


def _gate_rows(score_rows: pd.DataFrame, model_name: str) -> tuple[bool, list[list[str]]]:
    control = _metrics(score_rows[score_rows["model_name"] == PHASE8E_CONTROL])
    candidate = _metrics(score_rows[score_rows["model_name"] == model_name])
    top100_control = _metrics(score_rows[(score_rows["model_name"] == PHASE8E_CONTROL) & _scope_mask(score_rows, 100)])
    top100_candidate = _metrics(score_rows[(score_rows["model_name"] == model_name) & _scope_mask(score_rows, 100)])
    top500_control = _metrics(score_rows[(score_rows["model_name"] == PHASE8E_CONTROL) & _scope_mask(score_rows, 500)])
    top500_candidate = _metrics(score_rows[(score_rows["model_name"] == model_name) & _scope_mask(score_rows, 500)])
    stress_control = _metrics(score_rows[(score_rows["model_name"] == PHASE8E_CONTROL) & (score_rows["target_start"].astype(str) == STRESS_WINDOW)])
    stress_candidate = _metrics(score_rows[(score_rows["model_name"] == model_name) & (score_rows["target_start"].astype(str) == STRESS_WINDOW)])
    checks = [
        ("Top 1000 hit +/-20", ">= +1.5pp vs control", _delta(candidate["hit20"], control["hit20"]), 0.015, "min"),
        ("Top 1000 WMAPE", "<= +0.5pp vs control", _delta(candidate["wmape"], control["wmape"]), 0.005, "max"),
        ("Top 1000 phantom", "<= +0.5pp vs control", _delta(candidate["phantom_rate"], control["phantom_rate"]), 0.005, "max"),
        ("Top 500 hit +/-20", ">= 0.0pp vs control", _delta(top500_candidate["hit20"], top500_control["hit20"]), 0.0, "min"),
        ("Top 100 hit +/-20", ">= 0.0pp vs control", _delta(top100_candidate["hit20"], top100_control["hit20"]), 0.0, "min"),
        (f"{STRESS_WINDOW} WMAPE", "< control", _delta(stress_candidate["wmape"], stress_control["wmape"]), 0.0, "lt"),
    ]
    rows: list[list[str]] = []
    passes: list[bool] = []
    for label, requirement, observed, threshold, mode in checks:
        if observed is None:
            passed = False
        elif mode == "min":
            passed = observed >= threshold
        elif mode == "max":
            passed = observed <= threshold
        else:
            passed = observed < threshold
        passes.append(passed)
        rows.append([label, requirement, _fmt_pp(observed), "PASS" if passed else "FAIL"])
    return all(passes), rows


def _best_candidate(score_rows: pd.DataFrame) -> str:
    champion = _metrics(score_rows[score_rows["model_name"] == PHASE8GF_COMBINED])
    best_model = PHASE8GF_COMBINED
    best_key = (-999.0, 999.0, -999.0)
    for model_name in ORDERED_MODELS:
        if not str(model_name).startswith("8gj_"):
            continue
        metrics = _metrics(score_rows[score_rows["model_name"] == model_name])
        hit_delta = _delta(metrics["hit20"], champion["hit20"])
        wmape_delta = _delta(metrics["wmape"], champion["wmape"])
        bias_improvement = _delta(metrics["bias"], champion["bias"])
        if hit_delta is None or wmape_delta is None or bias_improvement is None:
            continue
        key = (hit_delta, -max(wmape_delta, 0.0), bias_improvement)
        if key > best_key:
            best_key = key
            best_model = model_name
    return best_model


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
        return "# Iteration 5Y - Forecast V2 Phase 8G-J Monitor Calibration\n\nNo scorable windows.\n"

    best_model = _best_candidate(score_rows)
    best = _metrics(score_rows[score_rows["model_name"] == best_model])
    champion = _metrics(score_rows[score_rows["model_name"] == PHASE8GF_COMBINED])
    gates_pass, gate_rows = _gate_rows(score_rows, best_model)
    decision = "RESEARCH_CANDIDATE_FOR_OFFICIAL_VALIDATION" if gates_pass and best_model != PHASE8GF_COMBINED else "KEEP_8G_I_CHAMPION"
    verdict = (
        f"`{best_model}` is a promising monitored-caveat research candidate. It was selected on the known Phase 8G validation windows, so it must not replace the official champion until it is wired and rerun through the official 8G-I validation/export path."
        if decision == "RESEARCH_CANDIDATE_FOR_OFFICIAL_VALIDATION"
        else "No calibration candidate beat the official 8G-I champion under the current gates."
    )

    return "\n".join(
        [
            "# Iteration 5Y - V2 Phase 8G-J Monitor Calibration",
            "",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"Route version: `{ROUTE_VERSION}`",
            "",
            "## Decision",
            "",
            f"Decision: `{decision}`.",
            "",
            verdict,
            "",
            _table(
                ["Metric", "8G-I champion", "Best 8G-J candidate", "Delta vs champion"],
                [
                    ["Model", PHASE8GF_COMBINED, best_model, "-"],
                    ["Hit +/-20", _fmt_pct(champion["hit20"]), _fmt_pct(best["hit20"]), _fmt_pp(_delta(best["hit20"], champion["hit20"]))],
                    ["Hit +/-30", _fmt_pct(champion["hit30"]), _fmt_pct(best["hit30"]), _fmt_pp(_delta(best["hit30"], champion["hit30"]))],
                    ["WMAPE", _fmt_pct(champion["wmape"]), _fmt_pct(best["wmape"]), _fmt_pp(_delta(best["wmape"], champion["wmape"]))],
                    ["Bias", _fmt_pct(champion["bias"]), _fmt_pct(best["bias"]), _fmt_pp(_delta(best["bias"], champion["bias"]))],
                    ["Phantom", _fmt_pct(champion["phantom_rate"]), _fmt_pct(best["phantom_rate"]), _fmt_pp(_delta(best["phantom_rate"], champion["phantom_rate"]))],
                ],
            ),
            "",
            "## Pre-Official Gate Replay",
            "",
            _table(["Gate", "Required", "Observed", "Status"], gate_rows),
            "",
            "## Candidate Results",
            "",
            _table(
                [
                    "Model",
                    "Rows",
                    "Qty scored",
                    "Hit +/-20",
                    "Delta vs control",
                    "Delta vs 8G-I",
                    "Hit +/-30",
                    "WMAPE",
                    "WMAPE delta vs 8G-I",
                    "Bias",
                    "Bias delta vs 8G-I",
                    "Phantom",
                    "Phantom delta vs 8G-I",
                ],
                _model_rows(score_rows),
            ),
            "",
            f"## Revenue Scope Replay - {best_model}",
            "",
            _table(
                [
                    "Scope",
                    "Rows",
                    "Qty scored",
                    "Actual revenue",
                    "Baseline hit +/-20",
                    "Candidate hit +/-20",
                    "Hit delta",
                    "Baseline WMAPE",
                    "Candidate WMAPE",
                    "WMAPE delta",
                    "Baseline bias",
                    "Candidate bias",
                    "Bias delta",
                    "Baseline phantom",
                    "Candidate phantom",
                    "Phantom delta",
                ],
                _scope_rows(score_rows, best_model),
            ),
            "",
            f"## Monitor Replay - {best_model} vs 8G-I Champion",
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
                _monitor_rows(score_rows, best_model),
            ),
            "",
            "## Skipped Windows",
            "",
            ", ".join(f"`{window}`" for window in skipped) if skipped else "None.",
            "",
            "## Notes",
            "",
            f"- Revenue-rank limit: Top {revenue_rank_limit}.",
            f"- Feature matrix rows: {len(matrix):,}.",
            f"- Feature matrix cache: `{cache_path}` ({'hit' if cache_hit else 'built'}; refresh requested: {'yes' if refresh_cache else 'no'}).",
            "- 8G-J is a high-revenue research calibration phase, not official wiring.",
            "- Candidate selection is validation-window tuning on the known Phase 8G backtest windows, not independent future holdout evidence.",
            "- The gate table is a pre-official replay over research score rows. It is not a substitute for wiring the candidate into `sklearn_direct_model.py` and rerunning the official 8G-I validation/export path.",
            "- The BF/campaign lift candidates multiply only `bf_campaign_sensitive` rows outside post-BF calendar context when the champion prediction is at least 3 units.",
            "- The regular-control blend candidates were tested to reduce regular phantom risk, but they did not fix the phantom monitor because most zero-actual regular predictions stayed above the sale threshold.",
            "- The best candidate improves underprediction and BF/campaign-sensitive accuracy, but it does not solve the regular phantom monitor or the 2025-03-24 WMAPE regression.",
            "- Any promotion must be wired into `sklearn_direct_model.py` and rerun through the official 8G-I validation/export path before replacing the current champion.",
        ]
    ) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run forecast v2 Phase 8G-J monitored-caveat calibration.")
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--target-start", action="append", default=None)
    parser.add_argument("--min-train-windows", type=int, default=4)
    parser.add_argument("--random-state", type=int, default=42)
    parser.add_argument("--revenue-rank-limit", type=int, default=PRIMARY_SCOPE)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    parser.add_argument("--refresh-cache", action="store_true")
    args = parser.parse_args()

    if args.revenue_rank_limit != PRIMARY_SCOPE:
        raise ValueError("Phase 8G-J is scoped to the official Top 1000 high-revenue champion only")

    config = ScorecardConfig()
    conn = sqlite3.connect(args.db)
    try:
        matrix, score_rows, skipped, _diagnostics, cache_path, cache_hit = run_phase8gj(
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

    report = build_report(matrix, score_rows, skipped, cache_path, cache_hit, args.revenue_rank_limit, args.refresh_cache)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report, encoding="utf-8")
    print(report)
    print(f"Wrote {args.report}")


if __name__ == "__main__":
    main()
