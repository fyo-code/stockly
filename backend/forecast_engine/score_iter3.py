"""Iter 3 scoring — actuals (Mar-Apr 2025) vs predictions vs naive baseline.

Outputs:
  - active_docs/ITER3_SCORING_REPORT.md
  - active_docs/ITER3_per_sku_scores.csv  (per-SKU detail for follow-up)
"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd


log = logging.getLogger("score_iter3")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


REPO_ROOT = Path(__file__).resolve().parents[2]
PRED_PATH = REPO_ROOT / "backend" / "data" / "predictions" / "iter3_predictions_latest.csv"
ACTUALS_PATH = REPO_ROOT / "sales_2025_Mar_Apr_chronological.csv"
DB_PATH = REPO_ROOT / "backend" / "data" / "supply_chain.db"
OUT_DIR = REPO_ROOT / "active_docs"
REPORT_MD = OUT_DIR / "ITER3_SCORING_REPORT.md"
PER_SKU_CSV = OUT_DIR / "ITER3_per_sku_scores.csv"

PRED_WINDOW_START = pd.Timestamp("2025-03-01")
PRED_WINDOW_END = pd.Timestamp("2025-04-30")

# Naive baseline = same period one year prior (Mar-Apr 2024)
NAIVE_WINDOW_START = pd.Timestamp("2024-03-01")
NAIVE_WINDOW_END = pd.Timestamp("2024-04-30")

METHOD_NAMES = [
    "ets", "anomaly_adjusted", "multi_scale_lag", "calendar_events",
    "category_relative", "naive_seasonal", "crostons",
]


def _parse_date(v):
    try:
        return pd.to_datetime(str(v), format="%d.%m.%Y", errors="raise")
    except Exception:
        return None


def _safe_float(v):
    try:
        return float(str(v).replace(",", "."))
    except Exception:
        return 0.0


def load_actuals_mar_apr_2025() -> pd.DataFrame:
    df = pd.read_csv(ACTUALS_PATH)
    df["sale_date"] = df["DATA COMANDA"].apply(_parse_date)
    df = df.dropna(subset=["sale_date"])
    df["sku_id"] = df["COD ARTICOL"].astype(str).str.strip()
    df["category"] = df["CATEGORIE"].astype(str).str.strip()
    df["units"] = df["CANTITATE FACTURATA"].apply(_safe_float)
    df = df[(df["sale_date"] >= PRED_WINDOW_START) & (df["sale_date"] <= PRED_WINDOW_END)]
    df["week_start"] = df["sale_date"] - pd.to_timedelta(df["sale_date"].dt.weekday, unit="D")

    # Build a category lookup (most-frequent per sku for safety)
    sku_cat = (
        df.groupby(["sku_id", "category"]).size().reset_index(name="n")
        .sort_values(["sku_id", "n"], ascending=[True, False])
        .drop_duplicates("sku_id")[["sku_id", "category"]]
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
    actuals = actuals.merge(sku_cat, on="sku_id", how="left")
    actuals["sku_id"] = actuals["sku_id"].astype(str).str.strip()
    log.info("Mar-Apr 2025 actuals: %d unique SKUs", len(actuals))
    log.info("  4w window: %s → %s", min_week.date(), (cutoff_4w - pd.Timedelta(days=1)).date())
    log.info("  8w window: %s → %s", min_week.date(), (cutoff_8w - pd.Timedelta(days=1)).date())
    return actuals


def load_naive_baseline_from_db(sku_ids: list[str]) -> pd.DataFrame:
    """Naive = same period 1 year prior (Mar-Apr 2024) from weekly_demand."""
    conn = sqlite3.connect(str(DB_PATH))
    try:
        wd = pd.read_sql_query(
            "SELECT sku_id, week_start, units_sold, units_returned FROM weekly_demand "
            "WHERE week_start >= ? AND week_start <= ?",
            conn, params=(str(NAIVE_WINDOW_START.date()), str(NAIVE_WINDOW_END.date())),
            parse_dates=["week_start"],
        )
    finally:
        conn.close()
    wd["sku_id"] = wd["sku_id"].astype(str).str.strip()
    wd["net"] = (wd["units_sold"] - wd["units_returned"]).clip(lower=0)
    sku_set = set(sku_ids)
    wd = wd[wd["sku_id"].isin(sku_set)]

    if wd.empty:
        return pd.DataFrame(columns=["sku_id", "naive_4w", "naive_8w"])

    rows = []
    for sku, g in wd.groupby("sku_id"):
        g = g.sort_values("week_start")
        units = g["net"].tolist()
        rows.append({
            "sku_id": sku,
            "naive_4w": float(sum(units[:4])),
            "naive_8w": float(sum(units[:8])),
        })
    return pd.DataFrame(rows)


def metrics(predicted: np.ndarray, actual: np.ndarray) -> dict:
    """Compute WMAPE, hit rate ±20%, hit rate ±30%, bias, MAE on a SKU set
    where actual > 0 (filter applied by caller)."""
    if len(actual) == 0 or actual.sum() <= 0:
        return {"n": int(len(actual)), "wmape": float("nan"), "hit20": float("nan"),
                "hit30": float("nan"), "bias": float("nan"), "mae": float("nan")}
    abs_err = np.abs(actual - predicted)
    wmape = abs_err.sum() / actual.sum()
    pct = abs_err / actual
    return {
        "n": int(len(actual)),
        "wmape": float(wmape),
        "hit20": float((pct <= 0.20).mean()),
        "hit30": float((pct <= 0.30).mean()),
        "bias": float(((predicted - actual) / actual).mean()),
        "mae": float(abs_err.mean()),
    }


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    log.info("Loading Iter 3 predictions: %s", PRED_PATH)
    preds = pd.read_csv(PRED_PATH)
    preds["sku_id"] = preds["sku_id"].astype(str).str.strip()
    log.info("  %d Iter 3 predicted SKUs", len(preds))

    log.info("Loading Mar-Apr 2025 actuals")
    actuals = load_actuals_mar_apr_2025()

    log.info("Computing naive baseline (Mar-Apr 2024 from DB)")
    naive = load_naive_baseline_from_db(preds["sku_id"].tolist())

    merged = preds.merge(actuals, on="sku_id", how="inner")
    merged = merged.merge(naive, on="sku_id", how="left")
    merged["naive_4w"] = merged["naive_4w"].fillna(0.0)
    merged["naive_8w"] = merged["naive_8w"].fillna(0.0)
    log.info("  %d SKUs joined (Iter 3 predicted ∩ has Mar-Apr 2025 actuals)", len(merged))

    nz = merged[merged["actual_4w"] > 0].copy()
    log.info("  %d SKUs with non-zero actual_4w (scoring set)", len(nz))

    # Phantom SKUs: predicted >0 but actual==0
    phantom = merged[(merged["actual_4w"] == 0) & (merged["ensemble_forecast_4w"] > 0)]
    log.info("  Phantom (predicted>0, actual=0): %d SKUs, sum predicted = %.0f",
             len(phantom), phantom["ensemble_forecast_4w"].sum())

    actual = nz["actual_4w"].values
    ensemble = nz["ensemble_forecast_4w"].values
    naive_4w = nz["naive_4w"].values

    # ---- Headline ----
    eng_m = metrics(ensemble, actual)
    naive_m = metrics(naive_4w, actual)

    # Head-to-head: per-SKU win rate of ensemble vs naive
    ens_err = np.abs(ensemble - actual)
    naive_err = np.abs(naive_4w - actual)
    eng_beats_naive = float((ens_err < naive_err).mean())
    eng_ties_naive = float((ens_err == naive_err).mean())

    # ---- Per-method ----
    method_results = {}
    for m in METHOD_NAMES:
        col = f"{m}_4w"
        if col not in nz.columns:
            method_results[m] = None
            continue
        # use only rows where method produced a number (and treat NaN as not-attempted)
        sub = nz[nz[col].notna()].copy()
        if sub.empty:
            method_results[m] = None
            continue
        a = sub["actual_4w"].values
        p = sub[col].values
        n = sub["naive_4w"].values
        m_metrics = metrics(p, a)
        # Win rate vs naive on the subset where method ran
        m_err = np.abs(p - a)
        n_err_sub = np.abs(n - a)
        m_metrics["win_rate_vs_naive"] = float((m_err < n_err_sub).mean())
        # Aggregate prediction tendency
        m_metrics["mean_pred"] = float(p.mean())
        m_metrics["sum_pred"] = float(p.sum())
        method_results[m] = m_metrics

    # ---- Per-category breakdown ----
    nz["category"] = nz["category"].fillna("(unknown)")
    cat_rows = []
    for cat, g in nz.groupby("category"):
        if len(g) < 5:
            continue
        a = g["actual_4w"].values
        e = g["ensemble_forecast_4w"].values
        n_b = g["naive_4w"].values
        em = metrics(e, a)
        nm = metrics(n_b, a)
        e_err = np.abs(e - a)
        n_err = np.abs(n_b - a)
        cat_rows.append({
            "category": cat,
            "n_skus": len(g),
            "sum_actual": float(a.sum()),
            "wmape_engine": em["wmape"],
            "wmape_naive": nm["wmape"],
            "engine_beats_naive_pct": float((e_err < n_err).mean()),
            "hit20_engine": em["hit20"],
            "hit20_naive": nm["hit20"],
        })
    cat_df = pd.DataFrame(cat_rows).sort_values("sum_actual", ascending=False)

    # ---- Per-SKU detail ----
    nz["abs_err_4w"] = (nz["ensemble_forecast_4w"] - nz["actual_4w"]).abs()
    nz["pct_err_4w"] = nz["abs_err_4w"] / nz["actual_4w"]
    nz["naive_abs_err_4w"] = (nz["naive_4w"] - nz["actual_4w"]).abs()
    nz["engine_beats_naive"] = nz["abs_err_4w"] < nz["naive_abs_err_4w"]

    # Extremely accurate (low pct error) — among SKUs with material actual
    material = nz[nz["actual_4w"] >= 3]
    top_accurate = material.nsmallest(20, "pct_err_4w")
    top_off = nz.nlargest(20, "abs_err_4w")  # by units, not pct, to avoid 1-unit-actuals dominating

    # Persist per-SKU scores
    keep = ["sku_id", "category", "actual_4w", "ensemble_forecast_4w",
            "abs_err_4w", "pct_err_4w", "naive_4w", "naive_abs_err_4w",
            "engine_beats_naive"] + [f"{m}_4w" for m in METHOD_NAMES if f"{m}_4w" in nz.columns]
    nz.sort_values("abs_err_4w", ascending=False)[keep].to_csv(PER_SKU_CSV, index=False)
    log.info("Wrote %s", PER_SKU_CSV)

    # ---- Build report ----
    L: list[str] = []
    L.append("# Iter 3 Scoring Report — Mar–Apr 2025")
    L.append("")
    L.append(f"_Generated 2026-04-25. Predictions: `{PRED_PATH.name}`. Actuals: `{ACTUALS_PATH.name}`._")
    L.append("")
    L.append("## Population")
    L.append("")
    L.append(f"- Iter 3 predicted SKUs: **{len(preds):,}** (same A-tier set as Iter 2)")
    L.append(f"- SKUs that appeared in Mar–Apr 2025 actuals (any sales): **{len(merged):,}** ({len(merged)/len(preds)*100:.1f}% of predicted)")
    L.append(f"- SKUs with non-zero actual_4w (scoring set): **{len(nz):,}**")
    L.append(f"- Phantom (predicted >0, actual ==0): **{len(phantom):,}** SKUs, sum predicted = **{phantom['ensemble_forecast_4w'].sum():,.0f}** units")
    L.append("")
    L.append("## Headline (4w horizon)")
    L.append("")
    L.append("| Metric | Iter 3 Engine | Naive baseline | Iter 2 (reference) |")
    L.append("|---|---:|---:|---:|")
    L.append(f"| WMAPE | **{eng_m['wmape']*100:.1f}%** | {naive_m['wmape']*100:.1f}% | 121.1% |")
    L.append(f"| Hit rate ±20% | **{eng_m['hit20']*100:.1f}%** | {naive_m['hit20']*100:.1f}% | 14.1% |")
    L.append(f"| Hit rate ±30% | **{eng_m['hit30']*100:.1f}%** | {naive_m['hit30']*100:.1f}% | 20.5% |")
    L.append(f"| Bias | **{eng_m['bias']*100:+.1f}%** | {naive_m['bias']*100:+.1f}% | +84.4% |")
    L.append(f"| MAE (units) | {eng_m['mae']:.2f} | {naive_m['mae']:.2f} | — |")
    L.append("")
    L.append(f"**Engine beats naive on {eng_beats_naive*100:.1f}% of SKUs** "
             f"(ties: {eng_ties_naive*100:.1f}%, naive wins: {(1-eng_beats_naive-eng_ties_naive)*100:.1f}%).")
    delta = naive_m['wmape'] - eng_m['wmape']
    if delta > 0:
        L.append(f"")
        L.append(f"**Engine WMAPE is {delta*100:.1f} pp BETTER than naive** "
                 f"({(delta/naive_m['wmape'])*100:.1f}% relative improvement).")
    else:
        L.append(f"")
        L.append(f"**Engine WMAPE is {abs(delta)*100:.1f} pp WORSE than naive.**")
    L.append("")

    L.append("## Per-method scoreboard (4w, on rows where method produced a number)")
    L.append("")
    L.append("| Method | n SKUs | WMAPE | Hit ±20% | Bias | Win rate vs naive | Mean pred |")
    L.append("|---|---:|---:|---:|---:|---:|---:|")
    L.append(f"| **Ensemble (median)** | {eng_m['n']:,} | **{eng_m['wmape']*100:.1f}%** | "
             f"**{eng_m['hit20']*100:.1f}%** | {eng_m['bias']*100:+.1f}% | "
             f"**{eng_beats_naive*100:.1f}%** | {ensemble.mean():.2f} |")
    L.append(f"| _Naive baseline_ | {naive_m['n']:,} | _{naive_m['wmape']*100:.1f}%_ | "
             f"_{naive_m['hit20']*100:.1f}%_ | {naive_m['bias']*100:+.1f}% | _—_ | {naive_4w.mean():.2f} |")
    for m, r in method_results.items():
        if r is None:
            L.append(f"| {m} | — | — | — | — | — | — |")
            continue
        L.append(f"| {m} | {r['n']:,} | {r['wmape']*100:.1f}% | {r['hit20']*100:.1f}% | "
                 f"{r['bias']*100:+.1f}% | {r['win_rate_vs_naive']*100:.1f}% | {r['mean_pred']:.2f} |")
    L.append("")

    L.append("## Per-category breakdown (4w, categories with ≥5 SKUs in scoring set)")
    L.append("")
    L.append("| Category | SKUs | Σ actual | Engine WMAPE | Naive WMAPE | Engine wins % | Engine hit ±20% |")
    L.append("|---|---:|---:|---:|---:|---:|---:|")
    for _, r in cat_df.iterrows():
        L.append(f"| {r['category']} | {int(r['n_skus']):,} | {r['sum_actual']:,.0f} | "
                 f"{r['wmape_engine']*100:.0f}% | {r['wmape_naive']*100:.0f}% | "
                 f"{r['engine_beats_naive_pct']*100:.0f}% | {r['hit20_engine']*100:.0f}% |")
    L.append("")

    L.append("## Top 20 most-accurate SKUs (engine within X% of actual, actual ≥3 units)")
    L.append("")
    L.append("| SKU | Category | Actual | Engine | %err | Naive | Naive %err |")
    L.append("|---|---|---:|---:|---:|---:|---:|")
    for _, r in top_accurate.iterrows():
        npct = abs(r["naive_4w"] - r["actual_4w"]) / r["actual_4w"] if r["actual_4w"] > 0 else 0
        L.append(f"| {r['sku_id']} | {r['category']} | {r['actual_4w']:.0f} | "
                 f"{r['ensemble_forecast_4w']:.1f} | {r['pct_err_4w']*100:.1f}% | "
                 f"{r['naive_4w']:.1f} | {npct*100:.1f}% |")
    L.append("")

    L.append("## Top 20 worst absolute errors (largest |engine − actual| in units)")
    L.append("")
    L.append("| SKU | Category | Actual | Engine | abs err | Naive | Naive |err| |")
    L.append("|---|---|---:|---:|---:|---:|---:|")
    for _, r in top_off.iterrows():
        L.append(f"| {r['sku_id']} | {r['category']} | {r['actual_4w']:.0f} | "
                 f"{r['ensemble_forecast_4w']:.1f} | {r['abs_err_4w']:.1f} | "
                 f"{r['naive_4w']:.1f} | {r['naive_abs_err_4w']:.1f} |")
    L.append("")

    REPORT_MD.write_text("\n".join(L), encoding="utf-8")
    log.info("Wrote %s", REPORT_MD)

    # Console
    print()
    print("=" * 70)
    print("ITER 3 SCORING — HEADLINE")
    print("=" * 70)
    print(f"  Scoring SKUs (actual_4w > 0):   {len(nz):,}")
    print(f"  Engine WMAPE:                   {eng_m['wmape']*100:.1f}%")
    print(f"  Naive  WMAPE:                   {naive_m['wmape']*100:.1f}%")
    print(f"  Engine hit ±20%:                {eng_m['hit20']*100:.1f}%")
    print(f"  Naive  hit ±20%:                {naive_m['hit20']*100:.1f}%")
    print(f"  Engine bias:                    {eng_m['bias']*100:+.1f}%")
    print(f"  Engine beats naive on SKU:      {eng_beats_naive*100:.1f}%")
    print()


if __name__ == "__main__":
    main()
