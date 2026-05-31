"""Iter 2 post-mortem — attribute every prediction error to an Iter 3 fix.

For each Iter 2 SKU with actuals, classifies the error by which (if any) of
the 5 Iter 3 fixes would have addressed it. Errors that no fix explains form
the **residual** — the honest measure of how much further work is needed
beyond the 5 fixes.

Outputs:
  - active_docs/ITER2_POST_MORTEM_attribution.csv  (per-SKU rows)
  - active_docs/ITER2_POST_MORTEM.md               (report + decision)

Usage:
    python -m forecast_engine.post_mortem_iter2

Run from inside `backend/` with the venv active.
"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd


log = logging.getLogger("post_mortem_iter2")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]
PRED_PATH = REPO_ROOT / "backend" / "data" / "predictions" / "iter2_predictions_latest.csv"
ACTUALS_PATH = REPO_ROOT / "sales_2025_Jan_Feb_chronological.csv"
DB_PATH = REPO_ROOT / "backend" / "data" / "supply_chain.db"
OUT_DIR = REPO_ROOT / "active_docs"
ATTRIBUTION_CSV = OUT_DIR / "ITER2_POST_MORTEM_attribution.csv"
REPORT_MD = OUT_DIR / "ITER2_POST_MORTEM.md"


# ---------------------------------------------------------------------------
# Tag thresholds — match Iter 3 fix definitions
# ---------------------------------------------------------------------------

LGBM_DRAG_RATIO = 2.0          # LGBM >= 2x median of non-LGBM methods
AA_COLLAPSE_THRESHOLD = 0.5    # anomaly_adjusted prediction <= 0.5 units
LUMPY_ZERO_PCT = 0.80          # matches abc_segmentation LUMPY definition
SEASONAL_CV_THRESHOLD = 0.5    # matches seasonal_dampener
SEASONAL_LOW_MULT = 0.7        # prediction-window multiplier under this = off-season
SEASONAL_OVERPRED_RATIO = 1.5  # ensemble >= 1.5x naive
SILENT_LOOKBACK_WEEKS = 10     # matches recency_filter
NAIVE_WIN_RATIO = 0.5          # naive error < ensemble error * 0.5
RESIDUAL_PCT_ERROR_FLOOR = 0.30  # only count residual if WMAPE-style error > 30%

# Prediction-window months for Iter 2 (Jan, Feb 2025)
PRED_MONTHS = [1, 2]

# Naive baseline lookup window (Jan-Feb 2024 = same calendar period one year prior)
NAIVE_WINDOW_START = "2024-01-01"
NAIVE_WINDOW_END = "2024-02-28"

# Recency window for silent_phantom: last 10 weeks of Iter 2 training (cutoff 2024-12-30)
SILENT_WINDOW_START = "2024-10-21"  # 10 weeks before 2024-12-30
SILENT_WINDOW_END = "2024-12-30"


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def _parse_mobexpert_date(value: str) -> pd.Timestamp | None:
    """Parse Mobexpert DATA COMANDA in DD.MM.YYYY format."""
    try:
        return pd.to_datetime(str(value), format="%d.%m.%Y", errors="raise")
    except Exception:
        return None


def load_actuals_jan_feb_2025() -> pd.DataFrame:
    """Replicates `backtesting.load_actuals` for the Mobexpert raw format,
    inlined to avoid triggering forecast_engine/__init__.py (which eagerly
    imports method modules whose deps aren't installed in this venv)."""
    df = pd.read_csv(ACTUALS_PATH)
    df["sale_date"] = df["DATA COMANDA"].apply(_parse_mobexpert_date)
    df = df.dropna(subset=["sale_date"])
    df["sku_id"] = df["COD ARTICOL"].astype(str).str.strip()

    def _safe_float(v):
        try:
            return float(str(v).replace(",", "."))
        except Exception:
            return 0.0

    df["units"] = df["CANTITATE FACTURATA"].apply(_safe_float)
    df = df[(df["sale_date"] >= "2025-01-01") & (df["sale_date"] <= "2025-02-28")]
    df["week_start"] = df["sale_date"] - pd.to_timedelta(
        df["sale_date"].dt.weekday, unit="D"
    )
    weekly = df.groupby(["sku_id", "week_start"])["units"].sum().reset_index()
    min_week = weekly["week_start"].min()
    cutoff_4w = min_week + pd.Timedelta(weeks=4)
    cutoff_8w = min_week + pd.Timedelta(weeks=8)
    actual_4w = (
        weekly[weekly["week_start"] < cutoff_4w]
        .groupby("sku_id")["units"].sum().reset_index()
        .rename(columns={"units": "actual_4w"})
    )
    actual_8w = (
        weekly[weekly["week_start"] < cutoff_8w]
        .groupby("sku_id")["units"].sum().reset_index()
        .rename(columns={"units": "actual_8w"})
    )
    actuals = actual_4w.merge(actual_8w, on="sku_id", how="outer").fillna(0)
    actuals["sku_id"] = actuals["sku_id"].astype(str).str.strip()
    log.info("Actuals loaded: %d SKUs", len(actuals))
    return actuals


def load_sku_features(sku_ids: list[str]) -> pd.DataFrame:
    """Pull per-SKU diagnostic features from the DB.

    Returns columns:
      sku_id, category, demand_pattern, zero_week_pct,
      naive_4w, naive_8w, last_10w_units, monthly_cv,
      pred_window_multiplier
    """
    if not sku_ids:
        return pd.DataFrame()

    conn = sqlite3.connect(str(DB_PATH))
    try:
        # Single batch read; filter in pandas to avoid huge IN clauses.
        abc = pd.read_sql_query(
            "SELECT sku_id, category, demand_pattern, zero_week_pct FROM abc_tiers WHERE tier='A'",
            conn,
        )
        wd = pd.read_sql_query(
            "SELECT sku_id, week_start, units_sold FROM weekly_demand",
            conn,
            parse_dates=["week_start"],
        )
    finally:
        conn.close()

    abc["sku_id"] = abc["sku_id"].astype(str).str.strip()
    wd["sku_id"] = wd["sku_id"].astype(str).str.strip()

    sku_set = set(sku_ids)
    abc = abc[abc["sku_id"].isin(sku_set)].copy()
    wd = wd[wd["sku_id"].isin(sku_set)].copy()

    # --- Naive baseline: same-period-last-year (Jan-Feb 2024) ---
    naive_window = wd[
        (wd["week_start"] >= NAIVE_WINDOW_START) & (wd["week_start"] <= NAIVE_WINDOW_END)
    ].copy()
    naive_window = naive_window.sort_values(["sku_id", "week_start"])
    # 4w = first 4 weeks, 8w = first 8 weeks (same logic as load_actuals)
    naive_4w_rows = []
    naive_8w_rows = []
    for sku, g in naive_window.groupby("sku_id"):
        g = g.sort_values("week_start")
        units = g["units_sold"].tolist()
        naive_4w_rows.append({"sku_id": sku, "naive_4w": float(sum(units[:4]))})
        naive_8w_rows.append({"sku_id": sku, "naive_8w": float(sum(units[:8]))})
    naive_4w = pd.DataFrame(naive_4w_rows) if naive_4w_rows else pd.DataFrame(columns=["sku_id", "naive_4w"])
    naive_8w = pd.DataFrame(naive_8w_rows) if naive_8w_rows else pd.DataFrame(columns=["sku_id", "naive_8w"])

    # --- Last 10 weeks of training: silent_phantom signal ---
    silent_window = wd[
        (wd["week_start"] >= SILENT_WINDOW_START) & (wd["week_start"] <= SILENT_WINDOW_END)
    ]
    last_10w = (
        silent_window.groupby("sku_id")["units_sold"].sum()
        .reset_index().rename(columns={"units_sold": "last_10w_units"})
    )

    # --- Monthly CV + prediction-window multiplier (mirrors seasonal_dampener) ---
    wd_2024 = wd[(wd["week_start"] >= "2024-01-01") & (wd["week_start"] <= "2024-12-31")].copy()
    wd_2024["month"] = wd_2024["week_start"].dt.month
    monthly = (
        wd_2024.groupby(["sku_id", "month"])["units_sold"].sum().reset_index()
    )

    cv_rows = []
    for sku, g in monthly.groupby("sku_id"):
        totals = g.set_index("month")["units_sold"].reindex(range(1, 13), fill_value=0)
        overall_avg = float(totals.mean())
        if overall_avg <= 0:
            cv_rows.append({"sku_id": sku, "monthly_cv": 0.0, "pred_window_multiplier": 1.0})
            continue
        mults = (totals / overall_avg).clip(lower=0.20, upper=3.0)
        # CV across the 12 monthly multipliers
        cv = float(mults.std(ddof=1) / mults.mean()) if mults.mean() > 0 else 0.0
        # Average multiplier across the prediction window months
        pred_mult = float(mults.loc[PRED_MONTHS].mean())
        cv_rows.append({"sku_id": sku, "monthly_cv": cv, "pred_window_multiplier": pred_mult})
    cv_df = pd.DataFrame(cv_rows) if cv_rows else pd.DataFrame(columns=["sku_id", "monthly_cv", "pred_window_multiplier"])

    # --- Merge ---
    feat = abc.merge(naive_4w, on="sku_id", how="left") \
              .merge(naive_8w, on="sku_id", how="left") \
              .merge(last_10w, on="sku_id", how="left") \
              .merge(cv_df, on="sku_id", how="left")
    feat["naive_4w"] = feat["naive_4w"].fillna(0.0)
    feat["naive_8w"] = feat["naive_8w"].fillna(0.0)
    feat["last_10w_units"] = feat["last_10w_units"].fillna(0.0)
    feat["monthly_cv"] = feat["monthly_cv"].fillna(0.0)
    feat["pred_window_multiplier"] = feat["pred_window_multiplier"].fillna(1.0)

    return feat


# ---------------------------------------------------------------------------
# Tagging
# ---------------------------------------------------------------------------

METHOD_COLS_4W = [
    "ets_4w", "anomaly_adjusted_4w", "multi_scale_lag_4w",
    "calendar_events_4w", "lightgbm_4w", "category_relative_4w", "crostons_4w",
]


def _tag_row(row: pd.Series) -> tuple[str, list[str]]:
    """Return (primary_tag, all_tags). Priority order chosen so that the most
    diagnostically-clear tag wins when multiple fire."""
    tags: list[str] = []

    actual = float(row["actual_4w"])
    ensemble = float(row["ensemble_forecast_4w"])
    abs_err = abs(ensemble - actual)
    pct_err = abs_err / actual if actual > 0 else float("inf")

    # silent_phantom — most decisive: SKU shouldn't have been forecast at all
    if row["last_10w_units"] <= 0:
        tags.append("silent_phantom")

    # aa_collapse — Anomaly-Adjusted predicted ~0 on a LUMPY SKU
    aa = row.get("anomaly_adjusted_4w")
    if aa is not None and not pd.isna(aa):
        if float(aa) <= AA_COLLAPSE_THRESHOLD and float(row["zero_week_pct"]) > LUMPY_ZERO_PCT:
            tags.append("aa_collapse")

    # lgbm_drag — LGBM is the highest method AND >= 2x median of non-LGBM
    lgbm = row.get("lightgbm_4w")
    if lgbm is not None and not pd.isna(lgbm):
        non_lgbm_vals = []
        for col in METHOD_COLS_4W:
            if col == "lightgbm_4w":
                continue
            v = row.get(col)
            if v is not None and not pd.isna(v) and float(v) > 0:
                non_lgbm_vals.append(float(v))
        if non_lgbm_vals:
            non_lgbm_median = float(np.median(non_lgbm_vals))
            non_lgbm_max = float(np.max(non_lgbm_vals))
            if float(lgbm) >= non_lgbm_max and non_lgbm_median > 0 and float(lgbm) >= LGBM_DRAG_RATIO * non_lgbm_median:
                tags.append("lgbm_drag")

    # seasonal_extrapolation — seasonal SKU, off-season window, ensemble overshoots naive
    cv = float(row.get("monthly_cv", 0.0))
    pred_mult = float(row.get("pred_window_multiplier", 1.0))
    naive = float(row.get("naive_4w", 0.0))
    if cv > SEASONAL_CV_THRESHOLD and pred_mult < SEASONAL_LOW_MULT and naive > 0 and ensemble >= SEASONAL_OVERPRED_RATIO * naive:
        tags.append("seasonal_extrapolation")

    # naive_would_have_won — naive error noticeably smaller than ensemble error
    if actual > 0:
        naive_err = abs(naive - actual)
        if naive_err < abs_err * NAIVE_WIN_RATIO:
            tags.append("naive_would_have_won")

    # residual — only if NO fix-tag fired AND error is meaningful
    if not tags and pct_err > RESIDUAL_PCT_ERROR_FLOOR:
        tags.append("residual")
    elif not tags:
        tags.append("within_tolerance")  # error < 30%, no tag fires — counts as already-OK

    # Priority order for "primary"
    priority = [
        "silent_phantom", "aa_collapse", "lgbm_drag",
        "seasonal_extrapolation", "naive_would_have_won",
        "residual", "within_tolerance",
    ]
    primary = next((t for t in priority if t in tags), tags[0])
    return primary, tags


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    log.info("Loading Iter 2 predictions: %s", PRED_PATH)
    preds = pd.read_csv(PRED_PATH)
    preds["sku_id"] = preds["sku_id"].astype(str).str.strip()
    log.info("  %d predicted SKUs", len(preds))

    log.info("Loading actuals (Jan-Feb 2025)")
    actuals = load_actuals_jan_feb_2025()

    merged = preds.merge(actuals, on="sku_id", how="inner")
    merged = merged[merged["actual_4w"] > 0].reset_index(drop=True)
    log.info("  %d SKUs matched with non-zero actuals", len(merged))

    log.info("Loading per-SKU features from DB")
    features = load_sku_features(merged["sku_id"].tolist())
    merged = merged.merge(features, on="sku_id", how="left")

    log.info("Tagging errors")
    tags = merged.apply(_tag_row, axis=1)
    merged["primary_tag"] = [t[0] for t in tags]
    merged["all_tags"] = [";".join(t[1]) for t in tags]

    merged["abs_error_4w"] = (merged["ensemble_forecast_4w"] - merged["actual_4w"]).abs()
    merged["pct_error_4w"] = merged["abs_error_4w"] / merged["actual_4w"].replace(0, np.nan)
    # WMAPE contribution = abs_error (since denominator is sum of actuals across population)
    merged["weighted_error"] = merged["abs_error_4w"]

    # --- Write per-SKU CSV ---
    keep_cols = [
        "sku_id", "store_id", "category", "demand_pattern",
        "actual_4w", "ensemble_forecast_4w", "abs_error_4w", "pct_error_4w",
        "primary_tag", "all_tags",
        "naive_4w", "last_10w_units", "zero_week_pct",
        "monthly_cv", "pred_window_multiplier",
    ] + METHOD_COLS_4W
    keep_cols = [c for c in keep_cols if c in merged.columns]
    merged.sort_values("weighted_error", ascending=False)[keep_cols].to_csv(
        ATTRIBUTION_CSV, index=False
    )
    log.info("Wrote %s (%d rows)", ATTRIBUTION_CSV, len(merged))

    # --- Aggregate stats for the report ---
    total_actual = float(merged["actual_4w"].sum())
    total_abs_err = float(merged["abs_error_4w"].sum())
    overall_wmape = total_abs_err / total_actual if total_actual > 0 else 0.0

    by_tag = (
        merged.groupby("primary_tag")
        .agg(
            n_skus=("sku_id", "count"),
            total_abs_error=("abs_error_4w", "sum"),
            mean_pct_error=("pct_error_4w", "mean"),
        )
        .sort_values("total_abs_error", ascending=False)
    )
    by_tag["pct_of_total_error"] = by_tag["total_abs_error"] / total_abs_err

    # Residual category breakdown
    residual = merged[merged["primary_tag"] == "residual"]
    residual_by_cat = (
        residual.groupby("category")
        .agg(n=("sku_id", "count"), total_abs_error=("abs_error_4w", "sum"))
        .sort_values("total_abs_error", ascending=False)
        .head(10)
    )
    residual_by_pattern = (
        residual.groupby("demand_pattern")
        .agg(n=("sku_id", "count"), total_abs_error=("abs_error_4w", "sum"))
        .sort_values("total_abs_error", ascending=False)
    )

    residual_share = float(by_tag["pct_of_total_error"].get("residual", 0.0))

    if residual_share < 0.15:
        decision = ("**GO** — residual below 15% of weighted error. Iter 3 fixes are aimed at the "
                    "right failure modes. Run Iter 3 prediction.")
    elif residual_share <= 0.40:
        decision = (f"**GO with caveat** — residual at {residual_share:.1%} of weighted error. "
                    "Run Iter 3, but use the residual category breakdown below as input to Iter 4 "
                    "planning (likely candidates: weighted ensemble, category routing).")
    else:
        decision = (f"**HOLD** — residual at {residual_share:.1%} of weighted error. The 5 fixes don't "
                    "address the dominant errors. Reconsider before running Iter 3.")

    # --- Write report ---
    lines: list[str] = []
    lines.append("# Iter 2 Post-Mortem — Error Attribution to Iter 3 Fixes")
    lines.append("")
    lines.append(f"_Generated by `forecast_engine/post_mortem_iter2.py`._")
    lines.append("")
    lines.append("## Decision")
    lines.append("")
    lines.append(decision)
    lines.append("")
    lines.append("## Population")
    lines.append("")
    lines.append(f"- Iter 2 predicted SKUs: **{len(preds):,}**")
    lines.append(f"- SKUs with non-zero Jan–Feb 2025 actuals (scored): **{len(merged):,}**")
    lines.append(f"- Aggregate WMAPE on this set: **{overall_wmape*100:.1f}%**")
    lines.append(f"- Total |error| (units): **{total_abs_err:,.0f}**")
    lines.append("")
    lines.append("## Error attribution by primary tag")
    lines.append("")
    lines.append("Each scored SKU is tagged by the dominant cause of its error. Priority order: "
                 "`silent_phantom > aa_collapse > lgbm_drag > seasonal_extrapolation > "
                 "naive_would_have_won > residual > within_tolerance`. A SKU may match multiple "
                 "tags; `all_tags` in the CSV preserves them.")
    lines.append("")
    lines.append("| Tag | SKUs | Σ\\|error\\| | % of total error | Mean % error | Maps to fix |")
    lines.append("|---|---:|---:|---:|---:|---|")
    fix_map = {
        "silent_phantom": "Fix #5 (recency filter)",
        "aa_collapse": "Fix #2 (AA SMOOTH-only)",
        "lgbm_drag": "Fix #1 (LightGBM archived)",
        "seasonal_extrapolation": "Fix #4 (seasonal dampening)",
        "naive_would_have_won": "Fix #3 (naive_seasonal in ensemble)",
        "residual": "— (none)",
        "within_tolerance": "— (already accurate)",
    }
    for tag, row in by_tag.iterrows():
        lines.append(
            f"| `{tag}` | {int(row['n_skus']):,} | {row['total_abs_error']:,.0f} | "
            f"{row['pct_of_total_error']*100:.1f}% | {row['mean_pct_error']*100:.0f}% | "
            f"{fix_map.get(str(tag), '?')} |"
        )
    lines.append("")
    lines.append("## Residual deep-dive")
    lines.append("")
    lines.append(f"_{len(residual):,} SKUs flagged residual, contributing "
                 f"{residual_share*100:.1f}% of total weighted error._")
    lines.append("")
    if not residual_by_cat.empty:
        lines.append("### Residual by category (top 10)")
        lines.append("")
        lines.append("| Category | SKUs | Σ\\|error\\| |")
        lines.append("|---|---:|---:|")
        for cat, row in residual_by_cat.iterrows():
            lines.append(f"| {cat} | {int(row['n']):,} | {row['total_abs_error']:,.0f} |")
        lines.append("")
    if not residual_by_pattern.empty:
        lines.append("### Residual by demand pattern")
        lines.append("")
        lines.append("| Pattern | SKUs | Σ\\|error\\| |")
        lines.append("|---|---:|---:|")
        for pat, row in residual_by_pattern.iterrows():
            lines.append(f"| {pat} | {int(row['n']):,} | {row['total_abs_error']:,.0f} |")
        lines.append("")
    lines.append("## What this means")
    lines.append("")
    lines.append("- Tags below `residual` are errors **explained** by an Iter 3 fix — the fix should "
                 "remove or reduce them in Iter 3.")
    lines.append("- `residual` is the **honest gap**: SKUs where none of the 5 fixes apply yet the "
                 "prediction was >30% off. If clustered by category, the next move is a Mobexpert-"
                 "specific category layer. If diffuse, we likely need richer inputs (promo calendar, "
                 "supplier delivery dates) rather than smarter algorithms.")
    lines.append("- `within_tolerance` SKUs were already <30% off. Don't optimise here.")
    lines.append("")
    lines.append(f"_Per-SKU attribution CSV: `{ATTRIBUTION_CSV.relative_to(REPO_ROOT)}`._")

    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")
    log.info("Wrote %s", REPORT_MD)

    # Console summary
    print()
    print("=" * 70)
    print("Iter 2 Post-Mortem — Tag Distribution")
    print("=" * 70)
    print(by_tag[["n_skus", "total_abs_error", "pct_of_total_error"]].to_string())
    print()
    print(f"Residual share: {residual_share*100:.1f}% of weighted error")
    print(decision)


if __name__ == "__main__":
    main()
