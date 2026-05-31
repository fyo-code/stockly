"""
Forecast Engine API routes.

Endpoints:
  POST /api/forecast/refresh                      — run all 6 methods, cache results
  GET  /api/forecast/sku/{sku_id}                 — single SKU ensemble + breakdown
  GET  /api/forecast/category/{category_id}       — all SKUs in a category
  GET  /api/forecast/method/{method_name}/comparison  — one method across all SKUs

Cache strategy: results live in _forecast_cache (module-level dict).
Call POST /api/forecast/refresh to populate. GET endpoints return 503 if cache is empty.
"""

import logging
import warnings
from datetime import datetime, timezone
from typing import Any, Optional

import pandas as pd
from fastapi import APIRouter, HTTPException

from db import get_conn

warnings.filterwarnings("ignore")

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/forecast", tags=["forecast"])

# --- In-memory cache ---
# Populated by POST /api/forecast/refresh
# Key: (sku_id, store_id) → EnsembleForecastResult
_forecast_cache: dict[tuple[str, str], dict] = {}
_cache_generated_at: Optional[str] = None
_sku_meta: dict[str, dict] = {}  # sku_id → {sku_name, category}


def _require_cache():
    """Raise 503 if cache is empty."""
    if not _forecast_cache:
        raise HTTPException(
            status_code=503,
            detail="Forecast cache is empty. Call POST /api/forecast/refresh first.",
        )


def _load_weekly_demand(conn) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load raw sales from DB and aggregate to weekly demand."""
    sales_df = pd.read_sql(
        "SELECT sku_id, store_id, sale_date, units_sold, units_returned FROM sales",
        conn,
    )
    skus_df = pd.read_sql(
        "SELECT sku_id, sku_name, category FROM skus",
        conn,
    )

    # Compute net_sold
    sales_df["units_returned"] = sales_df["units_returned"].fillna(0).astype(int)
    sales_df["net_sold"] = (sales_df["units_sold"] - sales_df["units_returned"]).clip(lower=0)
    sales_df["sale_date"] = pd.to_datetime(sales_df["sale_date"])

    # Align to Monday (ISO week start)
    sales_df["week_start_date"] = sales_df["sale_date"] - pd.to_timedelta(
        sales_df["sale_date"].dt.weekday, unit="D"
    )

    weekly = (
        sales_df.groupby(["sku_id", "store_id", "week_start_date"])["net_sold"]
        .sum()
        .reset_index()
    )

    return weekly, skus_df


def _run_all_methods(weekly: pd.DataFrame, skus_df: pd.DataFrame) -> dict[tuple[str, str], dict]:
    """Run all 6 forecasting methods + ensemble aggregation.

    Returns dict: (sku_id, store_id) → EnsembleForecastResult.
    """
    from forecast_engine.methods.ets_model import forecast_all_skus
    from forecast_engine.methods.anomaly_adjusted import forecast_all_skus_anomaly_adjusted
    from forecast_engine.methods.multi_scale_lag import forecast_all_skus_multi_scale_lag
    from forecast_engine.methods.calendar_events import forecast_all_skus_calendar_events
    from forecast_engine.aggregation import EnsembleForecaster

    # Build category lookup for category_relative method
    category_lookup = dict(zip(skus_df["sku_id"], skus_df["category"]))
    weekly_with_cat = weekly.copy()
    weekly_with_cat["category"] = weekly_with_cat["sku_id"].map(category_lookup)

    log.info("Running Method 1: ETS")
    ets_results = forecast_all_skus(weekly)

    log.info("Running Method 4: Anomaly-Adjusted")
    aa_results = forecast_all_skus_anomaly_adjusted(weekly)

    log.info("Running Method 5: Multi-Scale Lag")
    msl_results = forecast_all_skus_multi_scale_lag(weekly)

    log.info("Running Method 6: Calendar Events")
    cal_results = forecast_all_skus_calendar_events(weekly)

    # Methods 2 (LightGBM) and 3 (Category-Relative) are run separately
    # because LightGBM requires significant training time and category_relative
    # requires category column — both are included when available.
    lgbm_results = []
    try:
        from forecast_engine.methods.lgbm_model import forecast_all_skus_lgbm
        log.info("Running Method 2: LightGBM")
        lgbm_results, _ = forecast_all_skus_lgbm(weekly_with_cat)
    except Exception as e:
        log.warning(f"LightGBM skipped: {e}")

    cat_results = []
    try:
        from forecast_engine.methods.category_relative import forecast_all_skus_category_relative
        log.info("Running Method 3: Category-Relative")
        cat_results = forecast_all_skus_category_relative(
            weekly_with_cat,
            category_col="category",
        )
    except Exception as e:
        log.warning(f"Category-Relative skipped: {e}")

    # Method 7: Croston's for intermittent demand (>80% zero-weeks)
    crostons_results = []
    try:
        from forecast_engine.methods.crostons import forecast_all_skus_crostons
        log.info("Running Method 7: Croston's (intermittent demand)")
        crostons_results = forecast_all_skus_crostons(weekly)
    except Exception as e:
        log.warning(f"Croston's skipped: {e}")

    # Index all results by (sku_id, store_id)
    all_method_results: dict[str, list] = {
        "ets": ets_results,
        "anomaly_adjusted": aa_results,
        "multi_scale_lag": msl_results,
        "calendar_events": cal_results,
    }
    if lgbm_results:
        all_method_results["lightgbm"] = lgbm_results
    if cat_results:
        all_method_results["category_relative"] = cat_results
    if crostons_results:
        all_method_results["crostons"] = crostons_results

    # Ensemble
    log.info("Running ensemble aggregation")
    forecaster = EnsembleForecaster(aggregation="median")
    ensemble_list = forecaster.produce_batch_forecasts(all_method_results)

    return {(r["sku_id"], r["store_id"]): r for r in ensemble_list}


# --- Endpoints ---


@router.post("/refresh")
def refresh_forecasts():
    """Run all 6 forecasting methods across all SKUs and cache results.

    This is the main computation trigger. Call weekly (or manually).
    Returns summary of how many SKU-store pairs were forecasted.
    """
    global _forecast_cache, _cache_generated_at, _sku_meta

    conn = get_conn()
    try:
        weekly, skus_df = _load_weekly_demand(conn)
    finally:
        conn.close()

    # Build sku metadata cache
    _sku_meta = {
        row["sku_id"]: {"sku_name": row["sku_name"], "category": row["category"]}
        for _, row in skus_df.iterrows()
    }

    log.info(f"Forecast refresh: {weekly['sku_id'].nunique()} SKUs, "
             f"{weekly['store_id'].nunique()} stores")

    _forecast_cache = _run_all_methods(weekly, skus_df)
    _cache_generated_at = datetime.now(timezone.utc).isoformat()

    skus_succeeded = sum(1 for r in _forecast_cache.values() if r["methods_succeeded"] > 0)
    skus_all_failed = sum(1 for r in _forecast_cache.values() if r["methods_succeeded"] == 0)

    return {
        "status": "ok",
        "generated_at": _cache_generated_at,
        "sku_store_pairs_forecasted": len(_forecast_cache),
        "skus_with_at_least_one_method": skus_succeeded,
        "skus_all_methods_failed": skus_all_failed,
    }


@router.get("/sku/{sku_id}")
def get_sku_forecast(sku_id: str):
    """Return ensemble forecast + per-method breakdown for a single SKU.

    Returns all store results for the SKU. Each entry shows:
    - Ensemble forecast (4w and 8w) with confidence interval
    - Per-method breakdown with individual forecasts
    - Disagreement level across methods
    """
    _require_cache()

    sku_results = [
        r for (sid, _), r in _forecast_cache.items() if sid == sku_id
    ]

    if not sku_results:
        raise HTTPException(status_code=404, detail=f"SKU '{sku_id}' not found in forecast cache.")

    meta = _sku_meta.get(sku_id, {})

    return {
        "sku_id": sku_id,
        "sku_name": meta.get("sku_name"),
        "category": meta.get("category"),
        "generated_at": _cache_generated_at,
        "forecasts": sku_results,
    }


@router.get("/category/{category_id}")
def get_category_forecast(category_id: str):
    """Return ensemble forecasts for all SKUs in a category.

    Results sorted by forecast_4w descending (highest demand first).
    """
    _require_cache()

    # Find all sku_ids in this category
    skus_in_cat = {
        sku_id for sku_id, meta in _sku_meta.items()
        if meta.get("category", "").lower() == category_id.lower()
    }

    if not skus_in_cat:
        raise HTTPException(
            status_code=404,
            detail=f"Category '{category_id}' not found or has no SKUs.",
        )

    results = []
    for (sku_id, store_id), r in _forecast_cache.items():
        if sku_id in skus_in_cat:
            meta = _sku_meta.get(sku_id, {})
            results.append({
                "sku_id": sku_id,
                "sku_name": meta.get("sku_name"),
                "store_id": store_id,
                "forecast_4w": r["forecast_4w"],
                "forecast_8w": r["forecast_8w"],
                "confidence_low_4w": r["confidence_low_4w"],
                "confidence_high_4w": r["confidence_high_4w"],
                "methods_succeeded": r["methods_succeeded"],
                "method_disagreement_4w": r["method_disagreement_4w"],
            })

    results.sort(key=lambda x: x["forecast_4w"], reverse=True)

    return {
        "category": category_id,
        "sku_count": len(skus_in_cat),
        "result_count": len(results),
        "generated_at": _cache_generated_at,
        "forecasts": results,
    }


@router.get("/method/{method_name}/comparison")
def get_method_comparison(method_name: str):
    """Compare a single method's forecast across all SKUs.

    Valid method names: ets, lightgbm, category_relative, anomaly_adjusted,
    multi_scale_lag, calendar_events.

    Returns sorted by forecast_4w descending. Errors included for transparency.
    """
    _require_cache()

    valid_methods = [
        "ets", "lightgbm", "category_relative",
        "anomaly_adjusted", "multi_scale_lag", "calendar_events",
        "crostons",
    ]

    if method_name not in valid_methods:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown method '{method_name}'. Valid: {valid_methods}",
        )

    results = []
    for (sku_id, store_id), ensemble in _forecast_cache.items():
        breakdown = ensemble.get("method_breakdown", {})
        method_data = breakdown.get(method_name)
        if method_data is None:
            continue

        meta = _sku_meta.get(sku_id, {})
        results.append({
            "sku_id": sku_id,
            "sku_name": meta.get("sku_name"),
            "store_id": store_id,
            "category": meta.get("category"),
            "forecast_4w": method_data["forecast_4w"],
            "forecast_8w": method_data["forecast_8w"],
            "confidence_low_4w": method_data["confidence_low_4w"],
            "confidence_high_4w": method_data["confidence_high_4w"],
            "error": method_data.get("error"),
        })

    succeeded = [r for r in results if r["error"] is None]
    failed = [r for r in results if r["error"] is not None]
    succeeded.sort(key=lambda x: x["forecast_4w"], reverse=True)

    return {
        "method": method_name,
        "generated_at": _cache_generated_at,
        "total_skus": len(results),
        "succeeded": len(succeeded),
        "failed": len(failed),
        "results": succeeded + failed,
    }
