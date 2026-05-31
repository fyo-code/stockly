"""Phase 8G-O guarded campaign/BF calibration for forecast v2."""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from .phase8g_route_specific_model import _metrics, _scope_mask, _table
    from .route_labels import ROUTE_VERSION
    from .scorecard import ScorecardConfig
    from .sklearn_direct_model import HIGH_REVENUE_CHAMPION_MODEL
except ImportError:  # Allows direct script execution.
    from phase8g_route_specific_model import _metrics, _scope_mask, _table
    from route_labels import ROUTE_VERSION
    from scorecard import ScorecardConfig
    from sklearn_direct_model import HIGH_REVENUE_CHAMPION_MODEL


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT_SCORE_ROWS = PROJECT_ROOT / "active_docs" / "ITER5AC_V2_PHASE8G_N_SCORE_ROWS.csv"
DEFAULT_REPORT = PROJECT_ROOT / "active_docs" / "ITER5AD_V2_PHASE8G_O_GUARDED_CAMPAIGN_CALIBRATION.md"
DEFAULT_SCORE_ROWS_CSV = PROJECT_ROOT / "active_docs" / "ITER5AD_V2_PHASE8G_O_SCORE_ROWS.csv"

CHAMPION = HIGH_REVENUE_CHAMPION_MODEL
CONTROL = "sk_blend_post_bf_safe"
REVENUE_SCOPES = [100, 250, 500, 750, 1000]
REGULAR_ROUTES = {"available_regular", "proxy_available_regular"}
PRIMARY_CANDIDATES = [
    "8go_pre_bf_bfc_lift_130",
    "8go_pre_bf_bfc_lift_140",
    "8go_pre_bf_bfc_lift_150",
    "8go_pre_bf_bfc_lift_160",
    "8go_pre_bf_bfc_lift_180",
    "8go_pre_bf_bfc_lift_200",
    "8go_pre_bf_bfc_lift_150_floor5",
    "8go_pre_bf_bfc_lift_180_floor5",
    "8go_nonpost_ex_decjan_lift_150",
    "8go_nonpost_ex_decjan_lift_180",
]
ORDERED_MODELS = [CONTROL, CHAMPION, *PRIMARY_CANDIDATES]
MONITOR_WINDOWS = ["2024-10-28", "2024-11-25", "2024-12-30", "2025-01-27", "2025-03-24"]


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


def _load_base_rows(path: Path) -> pd.DataFrame:
    rows = pd.read_csv(path)
    required = {CHAMPION, CONTROL}
    present = set(rows["model_name"].dropna().astype(str).unique())
    missing = sorted(required - present)
    if missing:
        raise ValueError(f"Score rows missing required models: {missing}")
    return rows[rows["model_name"].isin(required)].copy()


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


def _pre_bf_mask(rows: pd.DataFrame, pred: np.ndarray, floor: float = 3.0) -> pd.Series:
    return (
        (rows["primary_route"].astype(str) == "bf_campaign_sensitive")
        & (rows["calendar_route_context"].astype(str) == "pre_bf_window")
        & (pd.Series(pred, index=rows.index) >= floor)
    )


def _nonpost_ex_decjan_mask(rows: pd.DataFrame, pred: np.ndarray, floor: float = 3.0) -> pd.Series:
    target_month = pd.to_datetime(rows["target_start"]).dt.month
    return (
        (rows["primary_route"].astype(str) == "bf_campaign_sensitive")
        & (rows["calendar_route_context"].astype(str) != "post_bf_window")
        & (~target_month.isin([12, 1]))
        & (pd.Series(pred, index=rows.index) >= floor)
    )


def _candidate_rows(score_rows: pd.DataFrame, config: ScorecardConfig) -> pd.DataFrame:
    champion = score_rows[score_rows["model_name"] == CHAMPION].copy()
    champion_pred = champion["pred_units"].to_numpy(dtype=float)
    candidates: list[pd.DataFrame] = []
    specs = [
        ("8go_pre_bf_bfc_lift_130", 1.30, "pre_bf", 3.0),
        ("8go_pre_bf_bfc_lift_140", 1.40, "pre_bf", 3.0),
        ("8go_pre_bf_bfc_lift_150", 1.50, "pre_bf", 3.0),
        ("8go_pre_bf_bfc_lift_160", 1.60, "pre_bf", 3.0),
        ("8go_pre_bf_bfc_lift_180", 1.80, "pre_bf", 3.0),
        ("8go_pre_bf_bfc_lift_200", 2.00, "pre_bf", 3.0),
        ("8go_pre_bf_bfc_lift_150_floor5", 1.50, "pre_bf", 5.0),
        ("8go_pre_bf_bfc_lift_180_floor5", 1.80, "pre_bf", 5.0),
        ("8go_nonpost_ex_decjan_lift_150", 1.50, "nonpost_ex_decjan", 3.0),
        ("8go_nonpost_ex_decjan_lift_180", 1.80, "nonpost_ex_decjan", 3.0),
    ]
    for model_name, lift, mask_kind, floor in specs:
        pred = champion_pred.copy()
        if mask_kind == "pre_bf":
            mask = _pre_bf_mask(champion, pred, floor=floor).to_numpy(dtype=bool)
        else:
            mask = _nonpost_ex_decjan_mask(champion, pred, floor=floor).to_numpy(dtype=bool)
        pred[mask] = pred[mask] * lift
        rows = _recompute_rows(champion, pred, model_name, config)
        rows["calibration_rows_touched"] = int(mask.sum())
        candidates.append(rows)
    return pd.concat(candidates, ignore_index=True)


def run_phase8go(score_rows_csv: Path, config: ScorecardConfig | None = None) -> pd.DataFrame:
    config = config or ScorecardConfig()
    base = _load_base_rows(score_rows_csv)
    candidates = _candidate_rows(base, config)
    return pd.concat([base, candidates], ignore_index=True)


def _model_metrics(score_rows: pd.DataFrame, model_name: str) -> dict[str, object]:
    return _metrics(score_rows[score_rows["model_name"] == model_name].copy())


def _max_non_stress_wmape_regression(score_rows: pd.DataFrame, model_name: str) -> tuple[str | None, float | None]:
    worst_window: str | None = None
    worst_delta: float | None = None
    for target_start in sorted(score_rows["target_start"].dropna().astype(str).unique()):
        if target_start == "2024-11-25":
            continue
        mask = score_rows["target_start"].astype(str) == target_start
        champion = _metrics(score_rows[(score_rows["model_name"] == CHAMPION) & mask])
        candidate = _metrics(score_rows[(score_rows["model_name"] == model_name) & mask])
        delta = _delta(candidate["wmape"], champion["wmape"])
        if delta is None:
            continue
        if worst_delta is None or delta > worst_delta:
            worst_delta = delta
            worst_window = target_start
    return worst_window, worst_delta


def _gate_rows(score_rows: pd.DataFrame, model_name: str) -> tuple[str, list[list[str]], bool]:
    champion = _model_metrics(score_rows, CHAMPION)
    candidate = _model_metrics(score_rows, model_name)
    worst_window, worst_wmape_delta = _max_non_stress_wmape_regression(score_rows, model_name)
    hit_delta = _delta(candidate["hit20"], champion["hit20"])
    wmape_delta = _delta(candidate["wmape"], champion["wmape"])
    bias_delta = _delta(candidate["bias"], champion["bias"])
    phantom_delta = _delta(candidate["phantom_rate"], champion["phantom_rate"])
    hit_gate = hit_delta is not None and (
        hit_delta >= 0.010
        or (hit_delta >= 0.005 and wmape_delta is not None and wmape_delta <= -0.010 and bias_delta is not None and bias_delta > 0)
    )
    checks = [
        ("Hit +/-20 vs champion", ">= +1.0pp, or >= +0.5pp with WMAPE/bias improvement", hit_delta, hit_gate),
        ("WMAPE vs champion", "<= 0.0pp", wmape_delta, wmape_delta is not None and wmape_delta <= 0.0),
        ("Bias vs champion", "> 0.0pp is improvement", bias_delta, bias_delta is not None and bias_delta > 0.0),
        ("Phantom vs champion", "<= 0.0pp", phantom_delta, phantom_delta is not None and phantom_delta <= 0.0),
        (
            f"Largest non-stress WMAPE regression ({worst_window or '-'})",
            "<= +2.0pp",
            worst_wmape_delta,
            worst_wmape_delta is not None and worst_wmape_delta <= 0.020,
        ),
    ]
    rows = [[label, requirement, _fmt_pp(observed), "PASS" if passed else "FAIL"] for label, requirement, observed, passed in checks]
    passed = all(item[3] == "PASS" for item in rows)
    decision = "PROMOTE_GUARDED_CAMPAIGN_CANDIDATE" if passed else "KEEP_CURRENT_CHAMPION"
    return decision, rows, passed


def _best_candidate(score_rows: pd.DataFrame) -> str:
    champion = _model_metrics(score_rows, CHAMPION)
    best_model = CHAMPION
    best_key = (-999.0, 999.0, -999.0, 999.0)
    for model_name in PRIMARY_CANDIDATES:
        metrics = _model_metrics(score_rows, model_name)
        hit_delta = _delta(metrics["hit20"], champion["hit20"])
        wmape_delta = _delta(metrics["wmape"], champion["wmape"])
        bias_delta = _delta(metrics["bias"], champion["bias"])
        phantom_delta = _delta(metrics["phantom_rate"], champion["phantom_rate"])
        if hit_delta is None or wmape_delta is None or bias_delta is None or phantom_delta is None:
            continue
        _, _, passes = _gate_rows(score_rows, model_name)
        gate_bonus = 1.0 if passes else 0.0
        key = (gate_bonus, hit_delta, -max(wmape_delta, 0.0), bias_delta, -max(phantom_delta, 0.0))
        if key > best_key:
            best_key = key
            best_model = model_name
    return best_model


def _model_rows(score_rows: pd.DataFrame) -> list[list[str]]:
    champion = _model_metrics(score_rows, CHAMPION)
    order = {name: idx for idx, name in enumerate(ORDERED_MODELS)}
    rows: list[list[str]] = []
    for model_name, group in sorted(score_rows.groupby("model_name"), key=lambda item: order.get(str(item[0]), 999)):
        if model_name not in ORDERED_MODELS:
            continue
        metrics = _metrics(group)
        rows.append(
            [
                str(model_name),
                f"{metrics['rows']:,}",
                f"{metrics['scored']:,}",
                _fmt_pct(metrics["hit20"]),
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


def _compare_row(score_rows: pd.DataFrame, model_name: str, label: str, mask: pd.Series) -> list[str]:
    champion = _metrics(score_rows[(score_rows["model_name"] == CHAMPION) & mask])
    candidate = _metrics(score_rows[(score_rows["model_name"] == model_name) & mask])
    return [
        label,
        f"{candidate['rows']:,}",
        f"{candidate['scored']:,}",
        _fmt_num(candidate["actual_revenue"], 0),
        _fmt_pct(champion["hit20"]),
        _fmt_pct(candidate["hit20"]),
        _fmt_pp(_delta(candidate["hit20"], champion["hit20"])),
        _fmt_pct(champion["wmape"]),
        _fmt_pct(candidate["wmape"]),
        _fmt_pp(_delta(candidate["wmape"], champion["wmape"])),
        _fmt_pct(champion["bias"]),
        _fmt_pct(candidate["bias"]),
        _fmt_pp(_delta(candidate["bias"], champion["bias"])),
        _fmt_pct(champion["phantom_rate"]),
        _fmt_pct(candidate["phantom_rate"]),
        _fmt_pp(_delta(candidate["phantom_rate"], champion["phantom_rate"])),
    ]


def _scope_rows(score_rows: pd.DataFrame, model_name: str) -> list[list[str]]:
    return [
        _compare_row(score_rows, model_name, f"Top {rank_limit}", _scope_mask(score_rows, rank_limit))
        for rank_limit in REVENUE_SCOPES
    ]


def _slice_rows(score_rows: pd.DataFrame, model_name: str) -> list[list[str]]:
    primary_route = score_rows.get("primary_route", pd.Series("", index=score_rows.index)).astype(str)
    context = score_rows.get("calendar_route_context", pd.Series("", index=score_rows.index)).astype(str)
    campaign_txn_13w = pd.to_numeric(score_rows.get("campaign_txn_13w", 0), errors="coerce").fillna(0)
    bf_txn_13w = pd.to_numeric(score_rows.get("bf_txn_13w", 0), errors="coerce").fillna(0)
    slices = [
        ("Available/proxy regular", primary_route.isin(REGULAR_ROUTES)),
        ("BF/campaign-sensitive route", primary_route == "bf_campaign_sensitive"),
        ("Pre-BF BF/campaign-sensitive", (primary_route == "bf_campaign_sensitive") & (context == "pre_bf_window")),
        ("Normal-calendar BF/campaign-sensitive", (primary_route == "bf_campaign_sensitive") & (context == "normal_calendar")),
        ("Any campaign/BF history 13w", (campaign_txn_13w > 0) | (bf_txn_13w > 0)),
        ("2024-11-25 stress window", score_rows["target_start"].astype(str) == "2024-11-25"),
        ("2024-12-30 failed 8G-K window", score_rows["target_start"].astype(str) == "2024-12-30"),
        ("2025-01-27 guard window", score_rows["target_start"].astype(str) == "2025-01-27"),
    ]
    return [_compare_row(score_rows, model_name, label, mask) for label, mask in slices]


def _window_rows(score_rows: pd.DataFrame, model_name: str) -> list[list[str]]:
    rows: list[list[str]] = []
    for target_start in sorted(score_rows["target_start"].dropna().astype(str).unique()):
        rows.append(_compare_row(score_rows, model_name, target_start, score_rows["target_start"].astype(str) == target_start))
    return rows


def build_report(score_rows: pd.DataFrame, input_score_rows: Path, output_score_rows: Path) -> str:
    best_model = _best_candidate(score_rows)
    decision, gate_rows, passes = _gate_rows(score_rows, best_model)
    champion = _model_metrics(score_rows, CHAMPION)
    best = _model_metrics(score_rows, best_model)
    touched = int(
        score_rows.loc[score_rows["model_name"] == best_model, "calibration_rows_touched"].dropna().max()
        if "calibration_rows_touched" in score_rows.columns
        else 0
    )
    note = (
        "The guarded candidate clears the phase gates by lifting only pre-BF BF/campaign-sensitive rows and leaving the 2024-12-30 / 2025-01-27 normal-calendar rows untouched."
        if passes
        else "No guarded campaign/BF candidate cleared the phase gates."
    )
    return "\n".join(
        [
            "# Iteration 5AD - V2 Phase 8G-O Guarded Campaign/BF Calibration",
            "",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"Route version: `{ROUTE_VERSION}`",
            "",
            "## Decision",
            "",
            f"Decision: `{decision}`.",
            "",
            note,
            "",
            _table(
                ["Metric", "Current champion", "Best guarded candidate", "Delta"],
                [
                    ["Model", CHAMPION, best_model, "-"],
                    ["Calibration rows touched", "-", f"{touched:,}", "-"],
                    ["Hit +/-20", _fmt_pct(champion["hit20"]), _fmt_pct(best["hit20"]), _fmt_pp(_delta(best["hit20"], champion["hit20"]))],
                    ["Hit +/-30", _fmt_pct(champion["hit30"]), _fmt_pct(best["hit30"]), _fmt_pp(_delta(best["hit30"], champion["hit30"]))],
                    ["WMAPE", _fmt_pct(champion["wmape"]), _fmt_pct(best["wmape"]), _fmt_pp(_delta(best["wmape"], champion["wmape"]))],
                    ["Bias", _fmt_pct(champion["bias"]), _fmt_pct(best["bias"]), _fmt_pp(_delta(best["bias"], champion["bias"]))],
                    ["Phantom", _fmt_pct(champion["phantom_rate"]), _fmt_pct(best["phantom_rate"]), _fmt_pp(_delta(best["phantom_rate"], champion["phantom_rate"]))],
                ],
            ),
            "",
            "## Promotion Gates",
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
                    "Delta vs champion",
                    "Hit +/-30",
                    "WMAPE",
                    "WMAPE delta",
                    "Bias",
                    "Bias delta",
                    "Phantom",
                    "Phantom delta",
                ],
                _model_rows(score_rows),
            ),
            "",
            f"## Revenue Scope Validation - {best_model}",
            "",
            _table(
                [
                    "Scope",
                    "Rows",
                    "Qty scored",
                    "Actual revenue",
                    "Champion hit +/-20",
                    "Candidate hit +/-20",
                    "Hit delta",
                    "Champion WMAPE",
                    "Candidate WMAPE",
                    "WMAPE delta",
                    "Champion bias",
                    "Candidate bias",
                    "Bias delta",
                    "Champion phantom",
                    "Candidate phantom",
                    "Phantom delta",
                ],
                _scope_rows(score_rows, best_model),
            ),
            "",
            f"## Critical Slice Validation - {best_model}",
            "",
            _table(
                [
                    "Slice",
                    "Rows",
                    "Qty scored",
                    "Actual revenue",
                    "Champion hit +/-20",
                    "Candidate hit +/-20",
                    "Hit delta",
                    "Champion WMAPE",
                    "Candidate WMAPE",
                    "WMAPE delta",
                    "Champion bias",
                    "Candidate bias",
                    "Bias delta",
                    "Champion phantom",
                    "Candidate phantom",
                    "Phantom delta",
                ],
                _slice_rows(score_rows, best_model),
            ),
            "",
            f"## Window Validation - {best_model}",
            "",
            _table(
                [
                    "Target start",
                    "Rows",
                    "Qty scored",
                    "Actual revenue",
                    "Champion hit +/-20",
                    "Candidate hit +/-20",
                    "Hit delta",
                    "Champion WMAPE",
                    "Candidate WMAPE",
                    "WMAPE delta",
                    "Champion bias",
                    "Candidate bias",
                    "Bias delta",
                    "Champion phantom",
                    "Candidate phantom",
                    "Phantom delta",
                ],
                _window_rows(score_rows, best_model),
            ),
            "",
            "## Interpretation",
            "",
            "- This phase deliberately avoids the broad 8G-K non-post-BF lift that overcorrected 2024-12-30 and 2025-01-27.",
            "- The best candidate is still validation-window calibration on known Phase 8G windows, not independent future holdout evidence.",
            "- The business interpretation is narrow: SKUs already classified as BF/campaign-sensitive need stronger pre-BF demand lift, but not automatic normal-calendar December/January lift.",
            "- This candidate should go to the final promotion pack before replacing the official high-revenue policy.",
            "",
            "## Outputs",
            "",
            f"- Input score rows: `{input_score_rows}`.",
            f"- Output score rows: `{output_score_rows}`.",
        ]
    ) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Phase 8G-O guarded campaign/BF calibration.")
    parser.add_argument("--score-rows-csv", type=Path, default=DEFAULT_INPUT_SCORE_ROWS)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--output-score-rows-csv", type=Path, default=DEFAULT_SCORE_ROWS_CSV)
    args = parser.parse_args()

    score_rows = run_phase8go(args.score_rows_csv, config=ScorecardConfig())
    args.output_score_rows_csv.parent.mkdir(parents=True, exist_ok=True)
    score_rows.to_csv(args.output_score_rows_csv, index=False)
    report = build_report(score_rows, args.score_rows_csv, args.output_score_rows_csv)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report, encoding="utf-8")
    print(report)
    print(f"Wrote {args.report}")


if __name__ == "__main__":
    main()
