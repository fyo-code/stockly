"""Phase 8G-F combined high-revenue route candidates for forecast v2."""

from __future__ import annotations

import argparse
import sqlite3
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from .feature_matrix import DEFAULT_TARGET_STARTS
    from .feature_matrix_cache import DEFAULT_CACHE_DIR, load_or_build_feature_matrix
    from .phase8g_campaign_sensitive_model import (
        _augment_campaign_predictions,
        _bf_calendar_mask,
        _post_bf_stress_mask,
    )
    from .phase8g_route_specific_model import (
        PHASE8E_CONTROL,
        _campaign_mask,
        _chronological,
        _metrics,
        _prediction_map,
        _regular_mask,
        _route_cols,
        _route_rows,
        _scope_compare_rows,
        _scope_mask,
        _table,
        _window_rows,
    )
    from .route_labels import ROUTE_VERSION, add_route_labels
    from .scorecard import DB_PATH, ScorecardConfig, score_model_predictions_fast
    from .sklearn_direct_model import (
        _actuals_for_score,
        _baseline_predictions,
        _labels_for_score,
        _prediction_frame,
    )
except ImportError:  # Allows direct script execution.
    from feature_matrix import DEFAULT_TARGET_STARTS
    from feature_matrix_cache import DEFAULT_CACHE_DIR, load_or_build_feature_matrix
    from phase8g_campaign_sensitive_model import _augment_campaign_predictions, _bf_calendar_mask, _post_bf_stress_mask
    from phase8g_route_specific_model import (
        PHASE8E_CONTROL,
        _campaign_mask,
        _chronological,
        _metrics,
        _prediction_map,
        _regular_mask,
        _route_cols,
        _route_rows,
        _scope_compare_rows,
        _scope_mask,
        _table,
        _window_rows,
    )
    from route_labels import ROUTE_VERSION, add_route_labels
    from scorecard import DB_PATH, ScorecardConfig, score_model_predictions_fast
    from sklearn_direct_model import _actuals_for_score, _baseline_predictions, _labels_for_score, _prediction_frame


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REPORT = PROJECT_ROOT / "active_docs" / "ITER5U_V2_PHASE8G_COMBINED_ROUTE_MODEL.md"

PHASE8GD_BEST = "8gd_regular_global_extra"
PHASE8GE_BEST = "8ge_post_bf_hard_safe"
PHASE8GF_COMBINED = "8gf_regular_plus_post_bf_safe"
PHASE8GF_BF_CALENDAR = "8gf_regular_plus_bf_calendar_safe"
PHASE8GF_GUARDED = "8gf_guarded_regular_plus_post_bf_safe"

ORDERED_MODELS = [
    "median_naive",
    "post_bf_safe_naive",
    "sk_hgb_squared",
    "sk_extra_trees",
    PHASE8E_CONTROL,
    PHASE8GD_BEST,
    PHASE8GE_BEST,
    PHASE8GF_COMBINED,
    PHASE8GF_BF_CALENDAR,
    PHASE8GF_GUARDED,
]
PREDICTION_MODELS = [model for model in ORDERED_MODELS if model != "median_naive"]


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


def _guarded_regular_mask(frame: pd.DataFrame) -> pd.Series:
    """Regular route, excluding rows with strong campaign/BF recent history."""

    regular = _regular_mask(frame)
    campaign = _campaign_mask(frame)
    return regular & ~campaign


def _augment_combined_predictions(eval_frame: pd.DataFrame, pred_map: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    output = _augment_campaign_predictions(eval_frame, pred_map)
    regular_eval = _regular_mask(eval_frame).to_numpy(dtype=bool)
    guarded_regular_eval = _guarded_regular_mask(eval_frame).to_numpy(dtype=bool)
    post_bf_eval = _post_bf_stress_mask(eval_frame).to_numpy(dtype=bool)
    bf_calendar_eval = _bf_calendar_mask(eval_frame).to_numpy(dtype=bool)

    pred = output[PHASE8GD_BEST].copy()
    pred[post_bf_eval] = output[PHASE8GE_BEST][post_bf_eval]
    output[PHASE8GF_COMBINED] = np.clip(pred, 0.0, None)

    pred = output[PHASE8GD_BEST].copy()
    pred[bf_calendar_eval] = output["post_bf_safe_naive"][bf_calendar_eval]
    output[PHASE8GF_BF_CALENDAR] = np.clip(pred, 0.0, None)

    pred = output[PHASE8E_CONTROL].copy()
    pred[guarded_regular_eval] = output["sk_extra_trees"][guarded_regular_eval]
    pred[post_bf_eval] = output[PHASE8GE_BEST][post_bf_eval]
    output[PHASE8GF_GUARDED] = np.clip(pred, 0.0, None)

    output["_8gf_regular_rows"] = regular_eval.astype(float)
    output["_8gf_guarded_regular_rows"] = guarded_regular_eval.astype(float)
    output["_8gf_post_bf_rows"] = post_bf_eval.astype(float)
    output["_8gf_bf_calendar_rows"] = bf_calendar_eval.astype(float)
    return output


def run_phase8gf(
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
    matrix, cache_path, cache_hit = load_or_build_feature_matrix(
        conn,
        target_starts=target_starts,
        population="headline",
        config=config,
        revenue_rank_limit=revenue_rank_limit,
        cache_dir=cache_dir,
        refresh=refresh_cache,
    )
    matrix = add_route_labels(matrix)
    all_score_rows: list[pd.DataFrame] = []
    skipped: list[str] = []
    diagnostics: list[dict[str, object]] = []

    for target_start in target_starts:
        train = matrix[pd.to_datetime(matrix["target_start"]) < pd.Timestamp(target_start)].copy()
        eval_frame = matrix[matrix["target_start"] == target_start].copy()
        if train["target_start"].nunique() < min_train_windows or eval_frame.empty:
            skipped.append(target_start)
            continue

        pred_map, _ = _prediction_map(train, eval_frame, random_state, config)
        pred_map = _augment_combined_predictions(eval_frame, pred_map)
        predictions = [
            _prediction_frame(model_name, eval_frame, pred_map[model_name])
            for model_name in PREDICTION_MODELS
            if model_name in pred_map
        ]
        score_rows, _ = score_model_predictions_fast(
            _labels_for_score(eval_frame),
            pd.concat(predictions, ignore_index=True),
            _actuals_for_score(eval_frame),
            f"phase8gf_combined_route_{target_start}",
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
                "regular_rows": int(_regular_mask(eval_frame).sum()),
                "guarded_regular_rows": int(_guarded_regular_mask(eval_frame).sum()),
                "campaign_rows": int(_campaign_mask(eval_frame).sum()),
                "post_bf_stress_rows": int(_post_bf_stress_mask(eval_frame).sum()),
                "bf_calendar_rows": int(_bf_calendar_mask(eval_frame).sum()),
            }
        )

    score_rows = pd.concat(all_score_rows, ignore_index=True) if all_score_rows else pd.DataFrame()
    return matrix, score_rows, skipped, diagnostics, cache_path, cache_hit


def _model_rows(score_rows: pd.DataFrame, control_hit20: float | None) -> list[list[str]]:
    rows: list[list[str]] = []
    order = {name: idx for idx, name in enumerate(ORDERED_MODELS)}
    for model_name, group in sorted(
        score_rows.groupby("model_name", dropna=False),
        key=lambda item: order.get(str(item[0]), 99),
    ):
        metrics = _metrics(group)
        delta = None if metrics["hit20"] is None or control_hit20 is None else float(metrics["hit20"]) - control_hit20
        rows.append(
            [
                str(model_name),
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


def _comparison_rows(score_rows: pd.DataFrame, candidate_model: str) -> list[list[str]]:
    rows: list[list[str]] = []
    candidate_rows = score_rows[score_rows["model_name"] == candidate_model].copy()
    for baseline_model in [PHASE8E_CONTROL, PHASE8GD_BEST, PHASE8GE_BEST]:
        baseline_rows = score_rows[score_rows["model_name"] == baseline_model].copy()
        baseline = _metrics(baseline_rows)
        candidate = _metrics(candidate_rows)
        hit_delta = None if baseline["hit20"] is None or candidate["hit20"] is None else float(candidate["hit20"]) - float(baseline["hit20"])
        wmape_delta = None if baseline["wmape"] is None or candidate["wmape"] is None else float(candidate["wmape"]) - float(baseline["wmape"])
        phantom_delta = (
            None
            if baseline["phantom_rate"] is None or candidate["phantom_rate"] is None
            else float(candidate["phantom_rate"]) - float(baseline["phantom_rate"])
        )
        rows.append(
            [
                baseline_model,
                _fmt_pct(baseline["hit20"]),
                _fmt_pct(candidate["hit20"]),
                _fmt_pp(hit_delta),
                _fmt_pct(baseline["wmape"]),
                _fmt_pct(candidate["wmape"]),
                _fmt_pp(wmape_delta),
                _fmt_pct(baseline["phantom_rate"]),
                _fmt_pct(candidate["phantom_rate"]),
                _fmt_pp(phantom_delta),
            ]
        )
    return rows


def _critical_slice_rows(score_rows: pd.DataFrame, candidate_model: str) -> list[list[str]]:
    rows: list[list[str]] = []
    control_rows = score_rows[score_rows["model_name"] == PHASE8E_CONTROL].copy()
    candidate_rows = score_rows[score_rows["model_name"] == candidate_model].copy()
    slices = [
        ("Top 1000", lambda df: _scope_mask(df, 1000)),
        ("Available/proxy regular", lambda df: df["primary_route"].isin({"available_regular", "proxy_available_regular"})),
        ("BF/campaign-sensitive route", lambda df: df["primary_route"] == "bf_campaign_sensitive"),
        ("Any campaign/BF history", lambda df: (pd.to_numeric(df.get("campaign_txn_13w", 0), errors="coerce").fillna(0) > 0)
         | (pd.to_numeric(df.get("bf_txn_13w", 0), errors="coerce").fillna(0) > 0)),
        ("2024-11-25 stress", lambda df: df["target_start"].astype(str) == "2024-11-25"),
    ]
    for label, mask_fn in slices:
        control = _metrics(control_rows[mask_fn(control_rows)])
        candidate = _metrics(candidate_rows[mask_fn(candidate_rows)])
        hit_delta = None if control["hit20"] is None or candidate["hit20"] is None else float(candidate["hit20"]) - float(control["hit20"])
        wmape_delta = None if control["wmape"] is None or candidate["wmape"] is None else float(candidate["wmape"]) - float(control["wmape"])
        rows.append(
            [
                label,
                f"{candidate['rows']:,}",
                f"{candidate['scored']:,}",
                _fmt_pct(control["hit20"]),
                _fmt_pct(candidate["hit20"]),
                _fmt_pp(hit_delta),
                _fmt_pct(control["wmape"]),
                _fmt_pct(candidate["wmape"]),
                _fmt_pp(wmape_delta),
                _fmt_pct(control["bias"]),
                _fmt_pct(candidate["bias"]),
                _fmt_pct(control["phantom_rate"]),
                _fmt_pct(candidate["phantom_rate"]),
            ]
        )
    return rows


def _diagnostic_rows(diagnostics: list[dict[str, object]]) -> list[list[str]]:
    return [
        [
            str(row["target_start"]),
            str(row["train_windows"]),
            f"{int(row['eval_rows']):,}",
            f"{int(row['regular_rows']):,}",
            f"{int(row['guarded_regular_rows']):,}",
            f"{int(row['campaign_rows']):,}",
            f"{int(row['bf_calendar_rows']):,}",
            f"{int(row['post_bf_stress_rows']):,}",
        ]
        for row in diagnostics
    ]


def build_report(
    matrix: pd.DataFrame,
    score_rows: pd.DataFrame,
    skipped: list[str],
    diagnostics: list[dict[str, object]],
    cache_path: Path,
    cache_hit: bool,
    revenue_rank_limit: int,
) -> str:
    if score_rows.empty:
        return "# Iteration 5U - Forecast V2 Phase 8G-F Combined Route Model\n\nNo scorable windows.\n"

    control = _metrics(score_rows[score_rows["model_name"] == PHASE8E_CONTROL])
    control_hit20 = None if control["hit20"] is None else float(control["hit20"])
    candidates = []
    for model_name, group in score_rows.groupby("model_name", dropna=False):
        if not str(model_name).startswith("8gf_"):
            continue
        metrics = _metrics(group)
        candidates.append({"model_name": str(model_name), **metrics})
    candidates.sort(
        key=lambda row: (
            -1.0 if row["hit20"] is None else float(row["hit20"]),
            -1.0 if row["hit30"] is None else float(row["hit30"]),
            float("-inf") if row["wmape"] is None else -float(row["wmape"]),
        ),
        reverse=True,
    )
    best_model = str(candidates[0]["model_name"]) if candidates else PHASE8E_CONTROL
    best = _metrics(score_rows[score_rows["model_name"] == best_model])
    hit_delta = None if best["hit20"] is None or control["hit20"] is None else float(best["hit20"]) - float(control["hit20"])
    wmape_delta = None if best["wmape"] is None or control["wmape"] is None else float(best["wmape"]) - float(control["wmape"])
    phantom_delta = (
        None
        if best["phantom_rate"] is None or control["phantom_rate"] is None
        else float(best["phantom_rate"]) - float(control["phantom_rate"])
    )
    beats_individuals = all(
        best["hit20"] is not None
        and _metrics(score_rows[score_rows["model_name"] == model])["hit20"] is not None
        and float(best["hit20"]) > float(_metrics(score_rows[score_rows["model_name"] == model])["hit20"])
        for model in [PHASE8GD_BEST, PHASE8GE_BEST]
    )
    if (
        hit_delta is not None
        and hit_delta >= 0.015
        and (wmape_delta is None or wmape_delta <= 0.005)
        and (phantom_delta is None or phantom_delta <= 0.005)
        and beats_individuals
    ):
        verdict = "Phase 8G-F produced a promotable combined Top 1000 candidate under the current gates."
    elif beats_individuals and hit_delta is not None and hit_delta > 0:
        verdict = "Phase 8G-F stacked the partial route wins, but the gain is still below the promotion gate."
    elif hit_delta is not None and hit_delta > 0:
        verdict = "Phase 8G-F improved over the safer blend, but did not beat both individual 8G-D/8G-E components."
    else:
        verdict = "Phase 8G-F did not improve over the safer blend."

    return "\n".join(
        [
            "# Iteration 5U - Forecast V2 Phase 8G-F Combined Route Model",
            "",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"Route version: `{ROUTE_VERSION}`",
            "",
            "## Verdict",
            "",
            verdict,
            "",
            _table(
                ["Metric", "Top 1000 control", "8G-D component", "8G-E component", "Best 8G-F combined"],
                [
                    ["Best model", PHASE8E_CONTROL, PHASE8GD_BEST, PHASE8GE_BEST, best_model],
                    [
                        "Hit +/-20",
                        _fmt_pct(control["hit20"]),
                        _fmt_pct(_metrics(score_rows[score_rows["model_name"] == PHASE8GD_BEST])["hit20"]),
                        _fmt_pct(_metrics(score_rows[score_rows["model_name"] == PHASE8GE_BEST])["hit20"]),
                        _fmt_pct(best["hit20"]),
                    ],
                    ["Delta hit +/-20", "-", "-", "-", _fmt_pp(hit_delta)],
                    [
                        "Hit +/-30",
                        _fmt_pct(control["hit30"]),
                        _fmt_pct(_metrics(score_rows[score_rows["model_name"] == PHASE8GD_BEST])["hit30"]),
                        _fmt_pct(_metrics(score_rows[score_rows["model_name"] == PHASE8GE_BEST])["hit30"]),
                        _fmt_pct(best["hit30"]),
                    ],
                    [
                        "WMAPE",
                        _fmt_pct(control["wmape"]),
                        _fmt_pct(_metrics(score_rows[score_rows["model_name"] == PHASE8GD_BEST])["wmape"]),
                        _fmt_pct(_metrics(score_rows[score_rows["model_name"] == PHASE8GE_BEST])["wmape"]),
                        _fmt_pct(best["wmape"]),
                    ],
                    [
                        "Bias",
                        _fmt_pct(control["bias"]),
                        _fmt_pct(_metrics(score_rows[score_rows["model_name"] == PHASE8GD_BEST])["bias"]),
                        _fmt_pct(_metrics(score_rows[score_rows["model_name"] == PHASE8GE_BEST])["bias"]),
                        _fmt_pct(best["bias"]),
                    ],
                    [
                        "Phantom rate",
                        _fmt_pct(control["phantom_rate"]),
                        _fmt_pct(_metrics(score_rows[score_rows["model_name"] == PHASE8GD_BEST])["phantom_rate"]),
                        _fmt_pct(_metrics(score_rows[score_rows["model_name"] == PHASE8GE_BEST])["phantom_rate"]),
                        _fmt_pct(best["phantom_rate"]),
                    ],
                ],
            ),
            "",
            "## Aggregate Model Results",
            "",
            _table(
                ["Model", "Rows", "Qty scored", "Hit +/-20", "Delta vs control", "Hit +/-30", "WMAPE", "Bias", "Phantom rate"],
                _model_rows(score_rows, control_hit20),
            ),
            "",
            f"## Direct Component Comparison - {best_model}",
            "",
            _table(
                [
                    "Baseline",
                    "Baseline hit +/-20",
                    "Candidate hit +/-20",
                    "Hit delta",
                    "Baseline WMAPE",
                    "Candidate WMAPE",
                    "WMAPE delta",
                    "Baseline phantom",
                    "Candidate phantom",
                    "Phantom delta",
                ],
                _comparison_rows(score_rows, best_model),
            ),
            "",
            f"## Revenue Scope Deltas - {best_model}",
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
                    "Control WMAPE",
                    "Candidate WMAPE",
                    "WMAPE delta",
                    "Control phantom",
                    "Candidate phantom",
                    "Phantom delta",
                ],
                _scope_compare_rows(score_rows, best_model),
            ),
            "",
            f"## Critical Slice Deltas - {best_model}",
            "",
            _table(
                [
                    "Slice",
                    "Rows",
                    "Qty scored",
                    "Control hit +/-20",
                    "Candidate hit +/-20",
                    "Hit delta",
                    "Control WMAPE",
                    "Candidate WMAPE",
                    "WMAPE delta",
                    "Control bias",
                    "Candidate bias",
                    "Control phantom",
                    "Candidate phantom",
                ],
                _critical_slice_rows(score_rows, best_model),
            ),
            "",
            f"## Route Scores - {best_model}",
            "",
            _table(
                ["Route", "Rows", "Qty scored", "Hit +/-20", "Hit +/-30", "WMAPE", "Bias", "Phantom rate"],
                _route_rows(score_rows, best_model),
            ),
            "",
            f"## Window Scores - {best_model}",
            "",
            _table(
                ["Target start", "Qty scored", "Hit +/-20", "Hit +/-30", "WMAPE", "Bias", "Phantom rate"],
                _window_rows(score_rows, best_model),
            ),
            "",
            "## Combination Diagnostics",
            "",
            _table(
                [
                    "Target start",
                    "Train windows",
                    "Eval rows",
                    "Regular rows",
                    "Guarded regular rows",
                    "Campaign rows",
                    "BF-calendar rows",
                    "Post-BF stress rows",
                ],
                _diagnostic_rows(diagnostics),
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
            f"- Feature matrix cache: `{cache_path}` ({'hit' if cache_hit else 'built'}).",
            "- `8gf_regular_plus_post_bf_safe` uses the 8G-D regular extra-trees replacement, then overrides post-BF stress rows with the 8G-E hard-safe fallback.",
            "- `8gf_regular_plus_bf_calendar_safe` is a broader BF-calendar guard; it is expected to be safer only if broad campaign windows are overpredicted.",
            "- `8gf_guarded_regular_plus_post_bf_safe` only applies the regular extra-trees replacement on regular rows without campaign/BF history.",
            "- All model training uses only earlier target windows.",
            "- Route and campaign gates are forecast-time-safe; target-window campaign buckets are not model features.",
            "- Phase 8F current snapshots remain excluded from historical backtests.",
        ]
    ) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run forecast v2 Phase 8G-F combined route candidates.")
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
        matrix, score_rows, skipped, diagnostics, cache_path, cache_hit = run_phase8gf(
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

    report = build_report(matrix, score_rows, skipped, diagnostics, cache_path, cache_hit, args.revenue_rank_limit)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report, encoding="utf-8")
    print(report)
    print(f"Wrote {args.report}")


if __name__ == "__main__":
    main()
