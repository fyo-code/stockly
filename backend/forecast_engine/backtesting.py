"""Backtesting / Walk-Forward Validation for Forecast Engine.

Iteration 2 workflow:
  1. Load weekly_demand from DB (training period: all 2024)
  2. Filter to A-tier SKUs (from abc_tiers table)
  3. Run all 7 methods + ensemble aggregation
  4. Save predictions to CSV
  5. When actuals are provided, compute accuracy metrics:
     - WMAPE (Weighted Mean Absolute Percentage Error)
     - Hit rate ±20% (% of SKUs within 20% of actual)
     - Bias (systematic over/under prediction)
     - Naïve seasonal baseline comparison

Usage:
    # Generate predictions (train on all 2024, predict Jan-Feb 2025)
    cd "Supply-Inventory v1.0"
    PYTHONPATH=backend python3 backend/forecast_engine/backtesting.py predict

    # Score predictions against actuals
    PYTHONPATH=backend python3 backend/forecast_engine/backtesting.py score \
        --actuals path/to/jan_feb_2025_actuals.csv

    # Run both: predict + score in one shot
    PYTHONPATH=backend python3 backend/forecast_engine/backtesting.py run \
        --actuals path/to/jan_feb_2025_actuals.csv
"""

import argparse
import csv
import logging
import sqlite3
import sys
import time
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
log = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DB_PATH = PROJECT_ROOT / "backend" / "data" / "supply_chain.db"
PREDICTIONS_DIR = PROJECT_ROOT / "backend" / "data" / "predictions"


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_a_tier_weekly(db_path: str) -> tuple[pd.DataFrame, set[str]]:
    """Load weekly_demand filtered to A-tier SKUs.

    Returns (weekly_df, a_tier_sku_ids).
    The DataFrame has columns expected by forecast methods:
        sku_id, store_id, week_start_date, net_sold, category
    """
    conn = sqlite3.connect(db_path)
    try:
        # Get A-tier SKU list
        a_tier_skus = pd.read_sql(
            "SELECT sku_id, demand_pattern FROM abc_tiers WHERE tier = 'A'",
            conn,
        )
        a_tier_ids = set(a_tier_skus["sku_id"].tolist())
        log.info(f"A-tier SKUs: {len(a_tier_ids):,}")

        # Load weekly demand for A-tier only
        weekly = pd.read_sql("SELECT * FROM weekly_demand", conn)
        weekly = weekly[weekly["sku_id"].isin(a_tier_ids)].copy()

        # Rename and compute columns to match method interfaces
        weekly["net_sold"] = (weekly["units_sold"] - weekly["units_returned"]).clip(lower=0)
        weekly.rename(columns={"week_start": "week_start_date"}, inplace=True)
        weekly["week_start_date"] = pd.to_datetime(weekly["week_start_date"])

        log.info(
            f"Loaded {len(weekly):,} weekly rows for {weekly['sku_id'].nunique():,} "
            f"A-tier SKUs, {weekly['store_id'].nunique()} store(s)"
        )
        log.info(
            f"Date range: {weekly['week_start_date'].min().date()} → "
            f"{weekly['week_start_date'].max().date()}"
        )

        return weekly, a_tier_ids
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Prediction engine — runs all 7 methods + ensemble
# ---------------------------------------------------------------------------

def run_all_methods(
    weekly: pd.DataFrame,
    aggregation: str = "median",
    weights: dict[str, float] | None = None,
    biases: dict[str, float] | None = None,
) -> list[dict]:
    """Run all 7 forecasting methods and ensemble on A-tier weekly data.

    Iter 4 Phase B.2: pass aggregation="weighted" + per-method weights to use
    weighted aggregation instead of median. Weights derived from per-method
    windowed WMAPE — see weighted_aggregation.derive_weights_from_summary.

    Iter 4 Phase B.6: pass biases (dict of method_name -> bias_capped) to
    apply multiplicative bias correction before ensemble aggregation.

    Returns list of EnsembleForecastResult dicts.
    """
    from forecast_engine.methods.ets_model import forecast_all_skus
    from forecast_engine.methods.anomaly_adjusted import forecast_all_skus_anomaly_adjusted
    from forecast_engine.methods.multi_scale_lag import forecast_all_skus_multi_scale_lag
    from forecast_engine.methods.calendar_events import forecast_all_skus_calendar_events
    from forecast_engine.aggregation import EnsembleForecaster
    from forecast_engine.config import (
        ENABLED_METHODS,
        RECENCY_FILTER_ENABLED,
        RECENCY_FILTER_WEEKS,
    )

    results_by_method: dict[str, list] = {}

    disabled = [m for m, on in ENABLED_METHODS.items() if not on]
    if disabled:
        log.info(f"Archived methods (excluded from ensemble): {', '.join(disabled)}")

    # Iter 3 Fix #5: Recency filter — drop SKUs silent for the last N weeks
    # before forecasting. Silent SKUs are re-attached as zero-forecasts at the
    # end so downstream consumers can distinguish "silent" from "missing".
    silent_keys: list[tuple[str, str]] = []
    if RECENCY_FILTER_ENABLED:
        from forecast_engine.recency_filter import split_active_silent
        log.info(f"Applying recency filter ({RECENCY_FILTER_WEEKS}w window)...")
        weekly, silent_keys = split_active_silent(weekly, weeks=RECENCY_FILTER_WEEKS)

    # Method 1: ETS
    if ENABLED_METHODS.get("ets", True):
        log.info("Running Method 1: ETS...")
        t0 = time.time()
        results_by_method["ets"] = forecast_all_skus(weekly)
        log.info(f"  ETS done: {len(results_by_method['ets']):,} results in {time.time()-t0:.1f}s")

    # Method 4: Anomaly-Adjusted
    if ENABLED_METHODS.get("anomaly_adjusted", True):
        log.info("Running Method 4: Anomaly-Adjusted...")
        t0 = time.time()
        results_by_method["anomaly_adjusted"] = forecast_all_skus_anomaly_adjusted(weekly)
        log.info(f"  AA done: {len(results_by_method['anomaly_adjusted']):,} results in {time.time()-t0:.1f}s")

    # Method 5: Multi-Scale Lag
    if ENABLED_METHODS.get("multi_scale_lag", True):
        log.info("Running Method 5: Multi-Scale Lag...")
        t0 = time.time()
        results_by_method["multi_scale_lag"] = forecast_all_skus_multi_scale_lag(weekly)
        log.info(f"  MSL done: {len(results_by_method['multi_scale_lag']):,} results in {time.time()-t0:.1f}s")

    # Method 6: Calendar Events
    if ENABLED_METHODS.get("calendar_events", True):
        log.info("Running Method 6: Calendar Events...")
        t0 = time.time()
        results_by_method["calendar_events"] = forecast_all_skus_calendar_events(weekly)
        log.info(f"  Cal done: {len(results_by_method['calendar_events']):,} results in {time.time()-t0:.1f}s")

    # Method 2: LightGBM (may fail if not enough data)
    if ENABLED_METHODS.get("lightgbm", True):
        try:
            from forecast_engine.methods.lgbm_model import forecast_all_skus_lgbm
            log.info("Running Method 2: LightGBM...")
            t0 = time.time()
            lgbm_results, training_info = forecast_all_skus_lgbm(
                weekly, category_col="category"
            )
            results_by_method["lightgbm"] = lgbm_results
            log.info(f"  LGBM done: {len(lgbm_results):,} results in {time.time()-t0:.1f}s")
        except Exception as e:
            log.warning(f"  LightGBM skipped: {e}")
    else:
        log.info("  LightGBM ARCHIVED via ENABLED_METHODS — skipping.")

    # Method 3: Category-Relative
    if ENABLED_METHODS.get("category_relative", True):
        try:
            from forecast_engine.methods.category_relative import forecast_all_skus_category_relative
            log.info("Running Method 3: Category-Relative...")
            t0 = time.time()
            cat_results = forecast_all_skus_category_relative(
                weekly, category_col="category"
            )
            results_by_method["category_relative"] = cat_results
            log.info(f"  CatRel done: {len(cat_results):,} results in {time.time()-t0:.1f}s")
        except Exception as e:
            log.warning(f"  Category-Relative skipped: {e}")

    # Method 8: Naive Seasonal (same-period-last-year baseline — Iter 3 Fix #3)
    if ENABLED_METHODS.get("naive_seasonal", True):
        try:
            from forecast_engine.methods.naive_seasonal import forecast_all_skus_naive_seasonal
            log.info("Running Method 8: Naive Seasonal (same-period-last-year)...")
            t0 = time.time()
            naive_results = forecast_all_skus_naive_seasonal(weekly)
            results_by_method["naive_seasonal"] = naive_results
            log.info(f"  NaiveSeasonal done: {len(naive_results):,} results in {time.time()-t0:.1f}s")
        except Exception as e:
            log.warning(f"  Naive Seasonal skipped: {e}")

    # Method 7: Croston's (intermittent demand only)
    if ENABLED_METHODS.get("crostons", True):
        try:
            from forecast_engine.methods.crostons import forecast_all_skus_crostons
            log.info("Running Method 7: Croston's (intermittent demand)...")
            t0 = time.time()
            crostons_results = forecast_all_skus_crostons(weekly)
            if crostons_results:
                results_by_method["crostons"] = crostons_results
            log.info(f"  Crostons done: {len(crostons_results):,} results in {time.time()-t0:.1f}s")
        except Exception as e:
            log.warning(f"  Croston's skipped: {e}")

    # Iter 4 Phase B.3 — per-category method routing. Drop method outputs for
    # SKUs in categories where the method has been shown to hurt the median
    # ensemble (e.g. Anomaly-Adjusted on ACCESORII). The ensemble combiner
    # then sees only the allowed methods per SKU and produces its median
    # over a smaller, category-appropriate pool.
    from forecast_engine.category_routing import (
        select_methods_for_category,
        routing_label_for_category,
    )
    sku_to_category: dict[str, str] = (
        weekly.dropna(subset=["sku_id", "category"])
              .drop_duplicates(subset=["sku_id"])
              .set_index("sku_id")["category"]
              .astype(str)
              .to_dict()
    )
    routing_applied: dict[tuple[str, str], str] = {}
    routing_drop_count = 0
    for method_name in list(results_by_method.keys()):
        kept: list = []
        for r in results_by_method[method_name]:
            sku = str(r.get("sku_id", "")).strip()
            store = str(r.get("store_id", "")).strip()
            cat = sku_to_category.get(sku)
            allowed = select_methods_for_category(cat)
            if method_name in allowed:
                kept.append(r)
            else:
                routing_drop_count += 1
            routing_applied.setdefault((sku, store), routing_label_for_category(cat))
        results_by_method[method_name] = kept
    if routing_drop_count > 0:
        log.info(
            f"Per-category routing: dropped {routing_drop_count:,} method outputs "
            f"across {sum(1 for v in routing_applied.values() if v != 'default'):,} routed SKUs."
        )

    # Iter 4 Phase B.6 — bias correction before ensemble.
    # Subtract each method's systematic signed error (derived from W1-W5)
    # so the median aggregates zero-mean-error predictions.
    if biases:
        from forecast_engine.bias_correction import apply_bias_correction
        results_by_method = apply_bias_correction(results_by_method, biases)
        log.info("Bias correction applied to %d methods.", len(biases))

    # Ensemble aggregation
    log.info(f"Running ensemble aggregation across {len(results_by_method)} methods...")
    t0 = time.time()
    forecaster = EnsembleForecaster(aggregation=aggregation, weights=weights or {})
    if aggregation == "weighted":
        log.info(f"  Aggregation: WEIGHTED. Weights: {weights}")
    else:
        log.info(f"  Aggregation: {aggregation}")
    ensemble_list = forecaster.produce_batch_forecasts(results_by_method)
    log.info(f"  Ensemble done: {len(ensemble_list):,} forecasts in {time.time()-t0:.1f}s")

    # Stamp routing label and bias correction flag on each ensemble result (B.4).
    bias_applied = bool(biases)
    for r in ensemble_list:
        key = (str(r.get("sku_id", "")).strip(), str(r.get("store_id", "")).strip())
        r["category_routing_applied"] = routing_applied.get(key, "default")
        r["bias_correction_applied"] = bias_applied

    # Iter 3 Fix #4: Seasonal SKU dampening — applied AFTER ensemble so every
    # method's contribution is reweighted consistently for the prediction window.
    from forecast_engine.config import SEASONAL_DAMPENING_ENABLED
    if SEASONAL_DAMPENING_ENABLED:
        from forecast_engine.seasonal_dampener import apply_seasonal_dampening
        log.info("Applying seasonal dampening...")
        t0 = time.time()
        ensemble_list = apply_seasonal_dampening(ensemble_list, weekly)
        log.info(f"  Dampening done in {time.time()-t0:.1f}s")

    # Re-attach silent SKUs as zero-forecast rows so they remain in the output
    # (flagged) instead of disappearing — supports downstream auditing.
    if silent_keys:
        from forecast_engine.recency_filter import silent_zero_forecasts
        ensemble_list.extend(silent_zero_forecasts(silent_keys, weeks=RECENCY_FILTER_WEEKS))
        log.info(f"  Re-attached {len(silent_keys):,} silent SKUs as zero-forecasts.")

    return ensemble_list


# ---------------------------------------------------------------------------
# Save predictions to CSV
# ---------------------------------------------------------------------------

def save_predictions(
    ensemble_list: list[dict],
    output_path: Path,
    iteration: str = "iter2",
) -> Path:
    """Save ensemble predictions to CSV for later scoring."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    rows = []
    for r in ensemble_list:
        breakdown = r.get("method_breakdown", {})
        row = {
            "sku_id": r["sku_id"],
            "store_id": r["store_id"],
            "ensemble_forecast_4w": r["forecast_4w"],
            "ensemble_forecast_8w": r["forecast_8w"],
            "ensemble_ci_low_4w": r["confidence_low_4w"],
            "ensemble_ci_high_4w": r["confidence_high_4w"],
            "methods_succeeded": r["methods_succeeded"],
            "methods_failed": r["methods_failed"],
            "disagreement_4w": r["method_disagreement_4w"],
            "disagreement_8w": r["method_disagreement_8w"],
            # Audit flags
            "silent_filter_applied": r.get("silent_filter_applied", False),
            "seasonal_dampening_applied": r.get("seasonal_dampening_applied", False),
            "seasonal_multiplier_4w": r.get("seasonal_multiplier_4w", None),
            "seasonal_multiplier_8w": r.get("seasonal_multiplier_8w", None),
            "category_routing_applied": r.get("category_routing_applied", "default"),
            "bias_correction_applied": r.get("bias_correction_applied", False),
            "promo_flag_4w": r.get("promo_flag_4w", False),
            "promo_flag_8w": r.get("promo_flag_8w", False),
        }
        # Add per-method forecasts
        for method_name, mb in breakdown.items():
            row[f"{method_name}_4w"] = mb["forecast_4w"]
            row[f"{method_name}_8w"] = mb["forecast_8w"]
            row[f"{method_name}_error"] = mb.get("error", "")
        rows.append(row)

    df = pd.DataFrame(rows)
    df.to_csv(output_path, index=False)
    log.info(f"Predictions saved: {output_path} ({len(df):,} rows)")
    return output_path


# ---------------------------------------------------------------------------
# Scoring engine — compare predictions vs actuals
# ---------------------------------------------------------------------------

def load_actuals(actuals_path: str) -> pd.DataFrame:
    """Load actuals CSV and compute 4w and 8w actual totals per SKU.

    Expected CSV columns (Mobexpert format):
        COD ARTICOL, DATA COMANDA, CANTITATE FACTURATA, VALOARE FACTURATA
    Or pre-processed format:
        sku_id, week_start, units_sold

    Returns DataFrame with: sku_id, actual_4w, actual_8w
    """
    df = pd.read_csv(actuals_path)

    # Detect format
    if "COD ARTICOL" in df.columns:
        # Raw Mobexpert format
        from forecast_engine.ingestion_mobexpert import parse_mobexpert_date, safe_float, safe_int
        log.info("Detected raw Mobexpert format for actuals")

        # Parse dates
        df["sale_date"] = df["DATA COMANDA"].apply(parse_mobexpert_date)
        df = df.dropna(subset=["sale_date"])
        df["sale_date"] = pd.to_datetime(df["sale_date"])
        df["sku_id"] = df["COD ARTICOL"].astype(str).str.strip()
        df["units"] = df["CANTITATE FACTURATA"].apply(lambda x: safe_float(str(x), 0.0))

        # Filter to May-Jun 2025 (the Iter 4 prediction window)
        df = df[(df["sale_date"] >= "2025-05-01") & (df["sale_date"] <= "2025-06-30")]

        # Week alignment (Monday start)
        df["week_start"] = df["sale_date"] - pd.to_timedelta(
            df["sale_date"].dt.weekday, unit="D"
        )

        # Aggregate to weekly
        weekly = df.groupby(["sku_id", "week_start"])["units"].sum().reset_index()

        # Determine 4w and 8w boundaries from May 5 (first full prediction week)
        min_week = pd.Timestamp("2025-05-05")
        week_4_cutoff = min_week + pd.Timedelta(weeks=4)
        week_8_cutoff = min_week + pd.Timedelta(weeks=8)

        actual_4w = (
            weekly[weekly["week_start"] < week_4_cutoff]
            .groupby("sku_id")["units"].sum()
            .reset_index()
            .rename(columns={"units": "actual_4w"})
        )
        actual_8w = (
            weekly[weekly["week_start"] < week_8_cutoff]
            .groupby("sku_id")["units"].sum()
            .reset_index()
            .rename(columns={"units": "actual_8w"})
        )

        actuals = actual_4w.merge(actual_8w, on="sku_id", how="outer").fillna(0)

    elif "sku_id" in df.columns and "actual_4w" in df.columns:
        # Pre-processed format
        actuals = df[["sku_id", "actual_4w", "actual_8w"]].copy()
    else:
        raise ValueError(
            f"Unrecognized actuals format. Columns: {list(df.columns)}. "
            "Expected Mobexpert raw format (COD ARTICOL, ...) or "
            "pre-processed (sku_id, actual_4w, actual_8w)."
        )

    actuals["sku_id"] = actuals["sku_id"].astype(str).str.strip()
    log.info(f"Actuals loaded: {len(actuals):,} SKUs")
    return actuals


def score_predictions(
    predictions_path: str,
    actuals: pd.DataFrame,
    horizon: str = "4w",
) -> dict:
    """Score predictions against actuals.

    Metrics:
        WMAPE — Weighted Mean Absolute Percentage Error
        Hit Rate ±20% — % of SKUs where |error| ≤ 20% of actual
        Bias — mean signed error (positive = over-predicting)
        MAE — Mean Absolute Error (units)

    Returns dict with overall metrics + per-method breakdown.
    """
    pred_col = f"ensemble_forecast_{horizon}"
    actual_col = f"actual_{horizon}"

    preds = pd.read_csv(predictions_path)
    preds["sku_id"] = preds["sku_id"].astype(str).str.strip()

    # Merge
    merged = preds.merge(actuals, on="sku_id", how="inner")
    log.info(f"Matched {len(merged):,} SKUs for scoring ({horizon})")

    if len(merged) == 0:
        log.error("No SKUs matched between predictions and actuals!")
        return {"error": "No matching SKUs"}

    predicted = merged[pred_col].values
    actual = merged[actual_col].values

    # Filter out zero-actual SKUs for percentage metrics (can't divide by 0)
    nonzero_mask = actual > 0
    actual_nz = actual[nonzero_mask]
    predicted_nz = predicted[nonzero_mask]

    # WMAPE = sum(|actual - predicted|) / sum(actual)
    abs_errors = np.abs(actual_nz - predicted_nz)
    wmape = float(abs_errors.sum() / actual_nz.sum()) if actual_nz.sum() > 0 else 0.0

    # Hit rate ±20%: % of SKUs where |predicted - actual| / actual <= 0.20
    pct_errors = abs_errors / actual_nz
    hit_rate_20 = float((pct_errors <= 0.20).sum() / len(pct_errors)) if len(pct_errors) > 0 else 0.0

    # Hit rate ±30% (secondary)
    hit_rate_30 = float((pct_errors <= 0.30).sum() / len(pct_errors)) if len(pct_errors) > 0 else 0.0

    # Bias = mean((predicted - actual) / actual), positive = over-predicting
    signed_pct_errors = (predicted_nz - actual_nz) / actual_nz
    bias = float(signed_pct_errors.mean())

    # MAE (units)
    mae = float(abs_errors.mean())

    # Median APE (less sensitive to outliers than WMAPE)
    median_ape = float(np.median(pct_errors)) if len(pct_errors) > 0 else 0.0

    # Zero-actual SKUs where we predicted > 0 (phantom demand)
    zero_actual_predicted = int(((actual == 0) & (predicted > 0)).sum())

    results = {
        "horizon": horizon,
        "total_skus_matched": len(merged),
        "nonzero_actual_skus": int(nonzero_mask.sum()),
        "zero_actual_skus": int((~nonzero_mask).sum()),
        "wmape": round(wmape * 100, 1),  # as percentage
        "hit_rate_20pct": round(hit_rate_20 * 100, 1),
        "hit_rate_30pct": round(hit_rate_30 * 100, 1),
        "bias_pct": round(bias * 100, 1),
        "mae_units": round(mae, 1),
        "median_ape_pct": round(median_ape * 100, 1),
        "phantom_demand_skus": zero_actual_predicted,
    }

    # Per-method scoring
    method_columns = [c for c in preds.columns if c.endswith(f"_{horizon}") and c != pred_col
                      and not c.endswith("_ci_low_" + horizon) and not c.endswith("_ci_high_" + horizon)]

    method_scores = {}
    for method_col in method_columns:
        method_name = method_col.replace(f"_{horizon}", "")
        if method_col not in merged.columns:
            continue
        m_predicted = merged[method_col].values
        m_abs_errors = np.abs(actual_nz - m_predicted[nonzero_mask])
        m_wmape = float(m_abs_errors.sum() / actual_nz.sum()) if actual_nz.sum() > 0 else 0.0
        m_pct_errors = m_abs_errors / actual_nz
        m_hit_rate = float((m_pct_errors <= 0.20).sum() / len(m_pct_errors)) if len(m_pct_errors) > 0 else 0.0
        method_scores[method_name] = {
            "wmape": round(m_wmape * 100, 1),
            "hit_rate_20pct": round(m_hit_rate * 100, 1),
        }

    results["per_method"] = method_scores
    return results


def compute_naive_baseline(
    actuals: pd.DataFrame,
    db_path: str,
    horizon: str = "4w",
) -> dict:
    """Naïve seasonal baseline: same-month-last-year.

    For Jan-Feb 2025 predictions, uses Jan-Feb 2024 actuals as the 'forecast'.
    This is what Mobexpert buyers currently do — the engine must beat this.
    """
    actual_col = f"actual_{horizon}"
    weeks = 4 if horizon == "4w" else 8

    conn = sqlite3.connect(db_path)
    try:
        # Get Jan-Feb 2024 weekly data for A-tier SKUs
        baseline_query = """
            SELECT sku_id, SUM(units_sold - units_returned) as baseline_units
            FROM weekly_demand
            WHERE sku_id IN (SELECT sku_id FROM abc_tiers WHERE tier = 'A')
              AND week_start >= '2024-01-01'
              AND week_start < '2024-03-01'
            GROUP BY sku_id
        """
        baseline = pd.read_sql(baseline_query, conn)

        if horizon == "4w":
            # First 4 weeks of Jan only
            baseline_query_4w = """
                SELECT sku_id, SUM(units_sold - units_returned) as baseline_units
                FROM weekly_demand
                WHERE sku_id IN (SELECT sku_id FROM abc_tiers WHERE tier = 'A')
                  AND week_start >= '2024-01-01'
                  AND week_start < '2024-01-29'
                GROUP BY sku_id
            """
            baseline = pd.read_sql(baseline_query_4w, conn)
    finally:
        conn.close()

    baseline["sku_id"] = baseline["sku_id"].astype(str).str.strip()

    # Merge with actuals
    merged = actuals.merge(baseline, on="sku_id", how="inner")
    if len(merged) == 0:
        return {"error": "No matching SKUs for baseline"}

    actual = merged[actual_col].values
    predicted = merged["baseline_units"].values.clip(min=0)

    nonzero_mask = actual > 0
    actual_nz = actual[nonzero_mask]
    predicted_nz = predicted[nonzero_mask]

    abs_errors = np.abs(actual_nz - predicted_nz)
    wmape = float(abs_errors.sum() / actual_nz.sum()) if actual_nz.sum() > 0 else 0.0
    pct_errors = abs_errors / actual_nz
    hit_rate = float((pct_errors <= 0.20).sum() / len(pct_errors)) if len(pct_errors) > 0 else 0.0

    return {
        "baseline": "same_month_last_year",
        "horizon": horizon,
        "skus_matched": len(merged),
        "wmape": round(wmape * 100, 1),
        "hit_rate_20pct": round(hit_rate * 100, 1),
    }


# ---------------------------------------------------------------------------
# Main CLI
# ---------------------------------------------------------------------------

def cmd_predict(args):
    """Generate predictions for A-tier SKUs."""
    db_path = str(args.db or DB_PATH)
    iteration = getattr(args, "iteration", None) or "iter2"
    weekly, a_tier_ids = load_a_tier_weekly(db_path)

    ensemble_list = run_all_methods(weekly)

    # Save
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = PREDICTIONS_DIR / f"{iteration}_predictions_{timestamp}.csv"
    save_predictions(ensemble_list, output_path, iteration=iteration)

    # Also save a "latest" symlink-style copy
    latest_path = PREDICTIONS_DIR / f"{iteration}_predictions_latest.csv"
    save_predictions(ensemble_list, latest_path, iteration=iteration)

    # Summary stats
    succeeded = sum(1 for r in ensemble_list if r["methods_succeeded"] > 0)
    high_disagree = sum(1 for r in ensemble_list if r["method_disagreement_4w"] == "HIGH")
    avg_methods = np.mean([r["methods_succeeded"] for r in ensemble_list])

    print(f"\n{'='*60}")
    print(f"{iteration.upper()} — PREDICTION SUMMARY")
    print(f"{'='*60}")
    print(f"  A-tier SKUs forecasted:  {len(ensemble_list):,}")
    print(f"  With ≥1 method:          {succeeded:,}")
    print(f"  Avg methods per SKU:     {avg_methods:.1f}")
    print(f"  HIGH disagreement (4w):  {high_disagree:,} ({high_disagree/len(ensemble_list)*100:.1f}%)")
    print(f"\n  Predictions saved to: {output_path}")
    print(f"  Latest copy at:       {latest_path}")


def cmd_score(args):
    """Score predictions against actuals."""
    predictions_path = args.predictions or str(PREDICTIONS_DIR / "iter2_predictions_latest.csv")
    if not Path(predictions_path).exists():
        print(f"ERROR: Predictions file not found: {predictions_path}")
        print("Run 'predict' first.")
        sys.exit(1)

    actuals = load_actuals(args.actuals)
    db_path = str(args.db or DB_PATH)

    print(f"\n{'='*60}")
    print(f"ITERATION 2 — ACCURACY REPORT")
    print(f"{'='*60}")

    for horizon in ["4w", "8w"]:
        results = score_predictions(predictions_path, actuals, horizon=horizon)
        if "error" in results:
            print(f"\n  {horizon}: {results['error']}")
            continue

        print(f"\n  --- {horizon.upper()} Horizon ---")
        print(f"  SKUs matched:      {results['total_skus_matched']:,}")
        print(f"  Non-zero actual:   {results['nonzero_actual_skus']:,}")
        print(f"  WMAPE:             {results['wmape']:.1f}%")
        print(f"  Hit Rate ±20%:     {results['hit_rate_20pct']:.1f}%")
        print(f"  Hit Rate ±30%:     {results['hit_rate_30pct']:.1f}%")
        print(f"  Bias:              {results['bias_pct']:+.1f}%")
        print(f"  MAE (units):       {results['mae_units']:.1f}")
        print(f"  Median APE:        {results['median_ape_pct']:.1f}%")
        print(f"  Phantom demand:    {results['phantom_demand_skus']:,} SKUs")

        if results.get("per_method"):
            print(f"\n  Per-method breakdown ({horizon}):")
            for method, scores in sorted(results["per_method"].items()):
                print(f"    {method:<25} WMAPE={scores['wmape']:>5.1f}%  Hit±20%={scores['hit_rate_20pct']:>5.1f}%")

    # Naïve baseline
    print(f"\n  --- Naïve Baseline (Same Month Last Year) ---")
    for horizon in ["4w", "8w"]:
        baseline = compute_naive_baseline(actuals, db_path, horizon=horizon)
        if "error" in baseline:
            print(f"  {horizon}: {baseline['error']}")
        else:
            print(f"  {horizon}: WMAPE={baseline['wmape']:.1f}%, Hit±20%={baseline['hit_rate_20pct']:.1f}%")


def cmd_run(args):
    """Predict + score in one shot."""
    cmd_predict(args)
    if args.actuals:
        cmd_score(args)
    else:
        print("\n  No actuals provided — skipping scoring.")


def main():
    parser = argparse.ArgumentParser(description="Forecast Engine Backtesting")
    parser.add_argument("--db", type=str, help="Path to SQLite database")
    subparsers = parser.add_subparsers(dest="command")

    # predict
    p_predict = subparsers.add_parser("predict", help="Generate predictions")
    p_predict.add_argument("--iteration", default="iter2",
                           help="Iteration tag for output filenames (e.g. iter2, iter3)")
    p_predict.set_defaults(func=cmd_predict)

    # score
    p_score = subparsers.add_parser("score", help="Score predictions against actuals")
    p_score.add_argument("--actuals", required=True, help="Path to actuals CSV")
    p_score.add_argument("--predictions", help="Path to predictions CSV (default: latest)")
    p_score.set_defaults(func=cmd_score)

    # run (predict + score)
    p_run = subparsers.add_parser("run", help="Predict + score in one shot")
    p_run.add_argument("--actuals", help="Path to actuals CSV (optional)")
    p_run.set_defaults(func=cmd_run)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
