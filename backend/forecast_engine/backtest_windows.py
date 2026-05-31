"""Windowed backtester — runs the engine across 6 train/predict windows
sliced from existing data.

Methodology fix introduced for Iter 4: every algorithm change must be
validated across multiple windows, not just Mar-Apr 2025 (which is now the
hold-out, not the tuning target).

For each window:
  1. Filter weekly_demand to week_start <= cutoff   → training set.
  2. Filter to A-tier SKUs (uses existing abc_tiers — control variable).
  3. Call run_all_methods (already in backtesting.py).
  4. Score against weekly_demand in [predict_start, predict_end].
  5. Compute same-period-prior-year naive baseline from weekly_demand.

Outputs:
  - active_docs/ITER4_BACKTEST_WINDOWS.csv         per-window per-method scores
  - active_docs/ITER4_BACKTEST_SUMMARY.md          human-readable summary

Run from backend/ with:
    python3 forecast_engine/backtest_windows.py [--label run_name]
"""

from __future__ import annotations

import argparse
import logging
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


log = logging.getLogger("backtest_windows")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


REPO_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = REPO_ROOT / "backend" / "data" / "supply_chain.db"
OUT_DIR = REPO_ROOT / "active_docs"
PER_WINDOW_CSV = OUT_DIR / "ITER4_BACKTEST_WINDOWS.csv"
SUMMARY_MD = OUT_DIR / "ITER4_BACKTEST_SUMMARY.md"

METHOD_NAMES = [
    "ets", "anomaly_adjusted", "multi_scale_lag", "calendar_events",
    "category_relative", "naive_seasonal", "crostons",
]

# Sub-tier slices for B.5 scoring (name, top_n revenue rank cutoff; None=all A-tier)
TIER_SLICES: list[tuple[str, int | None]] = [
    ("top100", 100),
    ("top1000", 1000),
    ("top5000", 5000),
    ("full_a", None),
]


@dataclass(frozen=True)
class Window:
    label: str
    cutoff: str           # last training week (inclusive)
    predict_start: str    # first prediction week (Monday)
    predict_end: str      # last day in 8w prediction window (inclusive)
    naive_start: str      # same-period prior year, first prediction week
    naive_end: str        # same-period prior year, last day


WINDOWS: list[Window] = [
    Window("W1_MayJun24", "2024-04-28", "2024-04-29", "2024-06-23", "2023-04-24", "2023-06-18"),
    Window("W2_JulAug24", "2024-06-30", "2024-07-01", "2024-08-25", "2023-07-03", "2023-08-27"),
    Window("W3_SepOct24", "2024-08-25", "2024-08-26", "2024-10-20", "2023-08-28", "2023-10-22"),
    Window("W4_NovDec24", "2024-10-27", "2024-10-28", "2024-12-22", "2023-10-30", "2023-12-24"),
    Window("W5_JanFeb25", "2024-12-29", "2024-12-30", "2025-02-23", "2023-12-25", "2024-02-18"),
    Window("W6_MarApr25", "2025-02-23", "2025-02-24", "2025-04-20", "2024-02-26", "2024-04-21"),
]
# Note: cutoffs are Sunday-end-of-week so the first prediction week (Monday)
# is exactly cutoff+1 day. Matches the engine's W-MON week convention.


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_a_tier_weekly_filtered(db_path: Path, cutoff: str) -> tuple[pd.DataFrame, set[str]]:
    """Read A-tier weekly_demand rows with week_start <= cutoff.

    Mirrors backtesting.load_a_tier_weekly but with a date filter so a single
    function can serve all 6 windows.
    """
    conn = sqlite3.connect(str(db_path))
    try:
        df = pd.read_sql_query(
            """
            SELECT w.sku_id, w.store_id, w.category, w.week_start,
                   w.units_sold, w.units_returned, w.revenue, w.num_transactions
            FROM weekly_demand w
            JOIN abc_tiers a ON w.sku_id = a.sku_id
            WHERE a.tier = 'A' AND w.week_start <= ?
            ORDER BY w.sku_id, w.store_id, w.week_start
            """,
            conn, params=(cutoff,),
        )
    finally:
        conn.close()

    df["week_start_date"] = pd.to_datetime(df["week_start"])
    df["net_sold"] = (df["units_sold"] - df["units_returned"]).clip(lower=0)
    a_tier = set(df["sku_id"].astype(str).str.strip())
    return df, a_tier


def load_actuals_from_db(db_path: Path, predict_start: str, predict_end: str) -> pd.DataFrame:
    """Aggregate actuals from weekly_demand for the prediction window.

    Returns DataFrame with [sku_id, actual_4w, actual_8w].
    """
    conn = sqlite3.connect(str(db_path))
    try:
        df = pd.read_sql_query(
            """
            SELECT sku_id, week_start, units_sold, units_returned
            FROM weekly_demand
            WHERE week_start >= ? AND week_start <= ?
            ORDER BY sku_id, week_start
            """,
            conn, params=(predict_start, predict_end),
        )
    finally:
        conn.close()

    if df.empty:
        return pd.DataFrame(columns=["sku_id", "actual_4w", "actual_8w"])

    df["sku_id"] = df["sku_id"].astype(str).str.strip()
    df["net"] = (df["units_sold"] - df["units_returned"]).clip(lower=0)

    rows: list[dict] = []
    for sku, g in df.groupby("sku_id"):
        units = g.sort_values("week_start")["net"].tolist()
        rows.append({
            "sku_id": sku,
            "actual_4w": float(sum(units[:4])),
            "actual_8w": float(sum(units[:8])),
        })
    return pd.DataFrame(rows)


def load_naive_baseline(db_path: Path, naive_start: str, naive_end: str,
                        sku_ids: set[str]) -> pd.DataFrame:
    """Same-period-prior-year sales from weekly_demand → naive_4w / naive_8w."""
    conn = sqlite3.connect(str(db_path))
    try:
        df = pd.read_sql_query(
            """
            SELECT sku_id, week_start, units_sold, units_returned
            FROM weekly_demand
            WHERE week_start >= ? AND week_start <= ?
            ORDER BY sku_id, week_start
            """,
            conn, params=(naive_start, naive_end),
        )
    finally:
        conn.close()

    if df.empty:
        return pd.DataFrame(columns=["sku_id", "naive_4w", "naive_8w"])

    df["sku_id"] = df["sku_id"].astype(str).str.strip()
    df = df[df["sku_id"].isin(sku_ids)]
    df["net"] = (df["units_sold"] - df["units_returned"]).clip(lower=0)

    rows: list[dict] = []
    for sku, g in df.groupby("sku_id"):
        units = g.sort_values("week_start")["net"].tolist()
        rows.append({
            "sku_id": sku,
            "naive_4w": float(sum(units[:4])),
            "naive_8w": float(sum(units[:8])),
        })
    return pd.DataFrame(rows)


def load_revenue_ranks(db_path: Path) -> dict[str, int]:
    """Return sku_id → revenue rank (1 = highest) for all A-tier SKUs."""
    conn = sqlite3.connect(str(db_path))
    try:
        df = pd.read_sql_query(
            "SELECT sku_id FROM abc_tiers WHERE tier='A' ORDER BY total_revenue DESC",
            conn,
        )
    finally:
        conn.close()
    return {str(s).strip(): i + 1 for i, s in enumerate(df["sku_id"])}


# ---------------------------------------------------------------------------
# Scoring helpers
# ---------------------------------------------------------------------------

def score_one(predicted: np.ndarray, actual: np.ndarray) -> dict:
    """Compute metrics on rows where actual > 0."""
    mask = actual > 0
    a = actual[mask]
    p = predicted[mask]
    if len(a) == 0 or a.sum() <= 0:
        return {"n": 0, "wmape": float("nan"), "hit20": float("nan"),
                "hit30": float("nan"), "bias": float("nan"), "mae": float("nan")}
    abs_err = np.abs(a - p)
    pct = abs_err / a
    return {
        "n": int(len(a)),
        "wmape": float(abs_err.sum() / a.sum()),
        "hit20": float((pct <= 0.20).mean()),
        "hit30": float((pct <= 0.30).mean()),
        "bias": float(((p - a) / a).mean()),
        "mae": float(abs_err.mean()),
    }


def winrate_vs_naive(predicted: np.ndarray, naive: np.ndarray, actual: np.ndarray) -> float:
    mask = actual > 0
    if mask.sum() == 0:
        return float("nan")
    p_err = np.abs(predicted[mask] - actual[mask])
    n_err = np.abs(naive[mask] - actual[mask])
    return float((p_err < n_err).mean())


# ---------------------------------------------------------------------------
# Per-window run
# ---------------------------------------------------------------------------

def run_window(
    window: Window,
    label: str,
    aggregation: str = "median",
    weights: dict[str, float] | None = None,
    biases: dict[str, float] | None = None,
) -> dict:
    """Run engine on training data, score against actuals + naive baseline.

    Returns a dict of per-method + ensemble metrics for this window.
    """
    log.info("=" * 70)
    log.info("Window %s — train≤%s, predict %s..%s",
             window.label, window.cutoff, window.predict_start, window.predict_end)

    weekly, a_tier_set = load_a_tier_weekly_filtered(DB_PATH, window.cutoff)
    if weekly.empty:
        log.warning("No training data for window %s — skipping", window.label)
        return {"window": window.label, "skipped": True}
    log.info("  Training set: %d rows, %d A-tier SKUs", len(weekly), weekly["sku_id"].nunique())

    # Adapter: backtesting.run_all_methods expects columns (sku_id, store_id,
    # category, week_start_date, net_sold). Already prepared above.
    sys.path.insert(0, str(REPO_ROOT / "backend"))
    from forecast_engine.backtesting import run_all_methods  # noqa: E402

    ensemble_list = run_all_methods(weekly, aggregation=aggregation, weights=weights, biases=biases)
    log.info("  Engine produced %d ensemble forecasts", len(ensemble_list))

    # Build a per-SKU DataFrame including all per-method predictions (these
    # are the breakdown fields run_all_methods stores in each ensemble dict).
    rows: list[dict] = []
    for r in ensemble_list:
        row = {
            "sku_id": str(r.get("sku_id", "")).strip(),
            "ensemble_4w": float(r.get("forecast_4w", 0.0)),
            "ensemble_8w": float(r.get("forecast_8w", 0.0)),
        }
        # method_breakdown: dict[method_name → MethodBreakdown(forecast_4w,
        # forecast_8w, ...)]. Pull each method's prediction.
        breakdown = r.get("method_breakdown", {})
        for m in METHOD_NAMES:
            mb = breakdown.get(m)
            if mb is not None:
                row[f"{m}_4w"] = float(mb.get("forecast_4w", float("nan")))
                row[f"{m}_8w"] = float(mb.get("forecast_8w", float("nan")))
            else:
                row[f"{m}_4w"] = float("nan")
                row[f"{m}_8w"] = float("nan")
        rows.append(row)
    preds = pd.DataFrame(rows)

    actuals = load_actuals_from_db(DB_PATH, window.predict_start, window.predict_end)
    naive = load_naive_baseline(DB_PATH, window.naive_start, window.naive_end, a_tier_set)
    log.info("  Actuals: %d SKUs;  Naive baseline rows: %d", len(actuals), len(naive))

    merged = preds.merge(actuals, on="sku_id", how="inner")
    merged = merged.merge(naive, on="sku_id", how="left")
    merged["naive_4w"] = merged["naive_4w"].fillna(0.0)
    merged["naive_8w"] = merged["naive_8w"].fillna(0.0)
    nz = merged[merged["actual_4w"] > 0].copy()
    log.info("  Joined: %d, scoring set (actual_4w > 0): %d", len(merged), len(nz))

    if len(nz) == 0:
        return {"window": window.label, "skipped": True, "reason": "no scoring rows"}

    actual = nz["actual_4w"].values
    ensemble = nz["ensemble_4w"].values
    naive_v = nz["naive_4w"].values

    eng = score_one(ensemble, actual)
    naive_m = score_one(naive_v, actual)
    eng_winrate = winrate_vs_naive(ensemble, naive_v, actual)

    out = {
        "window": window.label,
        "label": label,
        "cutoff": window.cutoff,
        "predict_start": window.predict_start,
        "predict_end": window.predict_end,
        "n_scored": eng["n"],
        "engine_wmape": eng["wmape"],
        "engine_hit20": eng["hit20"],
        "engine_hit30": eng["hit30"],
        "engine_bias": eng["bias"],
        "engine_mae": eng["mae"],
        "naive_wmape": naive_m["wmape"],
        "naive_hit20": naive_m["hit20"],
        "naive_bias": naive_m["bias"],
        "engine_winrate_vs_naive": eng_winrate,
    }

    # Per-method scoring on rows where method produced a number
    for m in METHOD_NAMES:
        col = f"{m}_4w"
        if col not in nz.columns:
            continue
        sub = nz[nz[col].notna()]
        if sub.empty:
            for k in ("n", "wmape", "hit20", "bias", "winrate_vs_naive"):
                out[f"{m}_{k}"] = float("nan")
            continue
        a = sub["actual_4w"].values
        p = sub[col].values
        n = sub["naive_4w"].values
        s = score_one(p, a)
        out[f"{m}_n"] = s["n"]
        out[f"{m}_wmape"] = s["wmape"]
        out[f"{m}_hit20"] = s["hit20"]
        out[f"{m}_bias"] = s["bias"]
        out[f"{m}_winrate_vs_naive"] = winrate_vs_naive(p, n, a)

    log.info("  → engine WMAPE %.1f%%, naive WMAPE %.1f%%, win-rate %.1f%%",
             eng["wmape"]*100, naive_m["wmape"]*100, eng_winrate*100)

    # B.5 — sub-tier scoring slices
    rev_ranks = load_revenue_ranks(DB_PATH)
    nz_r = nz.copy()
    nz_r["_rank"] = nz_r["sku_id"].map(rev_ranks)
    for slice_name, top_n in TIER_SLICES:
        sub = nz_r[nz_r["_rank"] <= top_n] if top_n is not None else nz_r
        if sub.empty:
            out[f"tier_{slice_name}_n"] = 0
            out[f"tier_{slice_name}_wmape"] = float("nan")
            out[f"tier_{slice_name}_hit20"] = float("nan")
        else:
            s = score_one(sub["ensemble_4w"].values, sub["actual_4w"].values)
            out[f"tier_{slice_name}_n"] = s["n"]
            out[f"tier_{slice_name}_wmape"] = s["wmape"]
            out[f"tier_{slice_name}_hit20"] = s["hit20"]

    return out


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(
    label: str = "iter4_baseline",
    aggregation: str = "median",
    weights: dict[str, float] | None = None,
    biases: dict[str, float] | None = None,
) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    if aggregation == "weighted":
        log.info("Run mode: WEIGHTED aggregation. Weights: %s", weights)
    else:
        log.info("Run mode: %s aggregation", aggregation)
    if biases:
        log.info("Bias correction enabled for methods: %s", list(biases.keys()))

    results: list[dict] = []
    for w in WINDOWS:
        try:
            results.append(run_window(w, label, aggregation=aggregation, weights=weights, biases=biases))
        except Exception as e:  # noqa: BLE001
            log.exception("Window %s failed: %s", w.label, e)
            results.append({"window": w.label, "label": label, "error": str(e)})

    df = pd.DataFrame(results)
    df.to_csv(PER_WINDOW_CSV, index=False)
    log.info("Wrote %s", PER_WINDOW_CSV)

    # Summary
    L: list[str] = []
    L.append(f"# Windowed Backtest — `{label}`")
    L.append("")
    L.append(f"_Generated by `backtest_windows.py`. 6 train/predict windows from existing DB data._")
    L.append("")
    L.append("## Per-window engine vs naive (4w horizon)")
    L.append("")
    L.append("| Window | Cutoff | n | Engine WMAPE | Naive WMAPE | Δ (pp) | Engine hit ±20% | Win rate vs naive |")
    L.append("|---|---|---:|---:|---:|---:|---:|---:|")
    valid = [r for r in results if "error" not in r and not r.get("skipped")]
    for r in valid:
        delta = (r["naive_wmape"] - r["engine_wmape"]) * 100
        L.append(f"| {r['window']} | {r['cutoff']} | {r['n_scored']:,} | "
                 f"{r['engine_wmape']*100:.1f}% | {r['naive_wmape']*100:.1f}% | "
                 f"{delta:+.1f} | {r['engine_hit20']*100:.1f}% | {r['engine_winrate_vs_naive']*100:.1f}% |")
    L.append("")

    if valid:
        means = pd.DataFrame(valid)[["engine_wmape", "naive_wmape", "engine_hit20",
                                     "engine_hit30", "engine_bias", "engine_winrate_vs_naive"]].mean()
        L.append(f"**6-window mean (engine):** WMAPE {means['engine_wmape']*100:.1f}%, "
                 f"hit ±20% {means['engine_hit20']*100:.1f}%, bias {means['engine_bias']*100:+.1f}%, "
                 f"win-rate vs naive {means['engine_winrate_vs_naive']*100:.1f}%.")
        L.append(f"**6-window mean (naive):** WMAPE {means['naive_wmape']*100:.1f}%.")
        L.append("")

        # Iter 4 acceptance gate marker (vs Iter 3's 84.9% / 21.4% / 31.7% rel improvement)
        n_better_than_naive = sum(1 for r in valid if r["engine_wmape"] < r["naive_wmape"])
        L.append(f"**Engine beats naive on {n_better_than_naive} of {len(valid)} windows.**")
        L.append("")

    L.append("## Per-method WMAPE across windows")
    L.append("")
    L.append("| Method | " + " | ".join(r["window"] for r in valid) + " | Mean |")
    L.append("|---|" + "---:|" * (len(valid) + 1))
    for m in METHOD_NAMES:
        cells = []
        vals = []
        for r in valid:
            v = r.get(f"{m}_wmape")
            if v is None or (isinstance(v, float) and np.isnan(v)):
                cells.append("—")
            else:
                cells.append(f"{v*100:.1f}%")
                vals.append(v)
        mean = (sum(vals) / len(vals) * 100) if vals else float("nan")
        cells.append(f"{mean:.1f}%" if vals else "—")
        L.append(f"| {m} | " + " | ".join(cells) + " |")
    L.append("")

    L.append("## Per-method win-rate vs naive across windows")
    L.append("")
    L.append("| Method | " + " | ".join(r["window"] for r in valid) + " | Mean |")
    L.append("|---|" + "---:|" * (len(valid) + 1))
    for m in METHOD_NAMES:
        cells = []
        vals = []
        for r in valid:
            v = r.get(f"{m}_winrate_vs_naive")
            if v is None or (isinstance(v, float) and np.isnan(v)):
                cells.append("—")
            else:
                cells.append(f"{v*100:.0f}%")
                vals.append(v)
        mean = (sum(vals) / len(vals) * 100) if vals else float("nan")
        cells.append(f"{mean:.0f}%" if vals else "—")
        L.append(f"| {m} | " + " | ".join(cells) + " |")
    L.append("")

    # B.5 — sub-tier WMAPE slices
    L.append("## Sub-tier WMAPE slices (6-window mean)")
    L.append("")
    slice_labels = {"top100": "Top 100", "top1000": "Top 1,000", "top5000": "Top 5,000", "full_a": "Full A-tier"}
    L.append("| Tier slice | Mean n | Mean WMAPE | Mean hit ±20% |")
    L.append("|---|---:|---:|---:|")
    for slice_name, _ in TIER_SLICES:
        ns, wmapes, hit20s = [], [], []
        for r in valid:
            n = r.get(f"tier_{slice_name}_n", 0)
            w = r.get(f"tier_{slice_name}_wmape", float("nan"))
            h = r.get(f"tier_{slice_name}_hit20", float("nan"))
            ns.append(n)
            if not (isinstance(w, float) and np.isnan(w)):
                wmapes.append(w)
            if not (isinstance(h, float) and np.isnan(h)):
                hit20s.append(h)
        mean_n = int(sum(ns) / len(ns)) if ns else 0
        mean_wmape = f"{sum(wmapes)/len(wmapes)*100:.1f}%" if wmapes else "—"
        mean_hit20 = f"{sum(hit20s)/len(hit20s)*100:.1f}%" if hit20s else "—"
        L.append(f"| {slice_labels[slice_name]} | {mean_n:,} | {mean_wmape} | {mean_hit20} |")
    L.append("")

    SUMMARY_MD.write_text("\n".join(L), encoding="utf-8")
    log.info("Wrote %s", SUMMARY_MD)

    # Console
    print()
    print("=" * 70)
    print(f"Backtest summary — label: {label}")
    print("=" * 70)
    for r in valid:
        delta = (r["naive_wmape"] - r["engine_wmape"]) * 100
        print(f"  {r['window']:<12} engine {r['engine_wmape']*100:5.1f}%  "
              f"naive {r['naive_wmape']*100:5.1f}%  Δ {delta:+5.1f}pp  "
              f"hit20 {r['engine_hit20']*100:5.1f}%  win {r['engine_winrate_vs_naive']*100:5.1f}%")
    if valid:
        n_beat = sum(1 for r in valid if r["engine_wmape"] < r["naive_wmape"])
        print(f"\n  Engine beats naive on {n_beat}/{len(valid)} windows")


if __name__ == "__main__":
    import json as _json

    parser = argparse.ArgumentParser()
    parser.add_argument("--label", default="iter4_baseline")
    parser.add_argument("--aggregation", default="median",
                        choices=["median", "trimmed_mean", "equal_weight", "weighted"])
    parser.add_argument("--weights-json",
                        help="Path to JSON with method_name -> weight. Required if aggregation=weighted.")
    parser.add_argument("--biases-json",
                        help="Path to JSON produced by derive_biases.py. Enables B.6 bias correction.")
    args = parser.parse_args()

    weights: dict[str, float] | None = None
    if args.aggregation == "weighted":
        if not args.weights_json:
            raise SystemExit("--weights-json is required when --aggregation=weighted")
        with open(args.weights_json) as f:
            weights = {k: float(v) for k, v in _json.load(f).items()}

    biases: dict[str, float] | None = None
    if args.biases_json:
        with open(args.biases_json) as f:
            raw = _json.load(f)
        biases = {m: float(v["bias_capped"]) for m, v in raw.items()}

    main(args.label, aggregation=args.aggregation, weights=weights, biases=biases)
