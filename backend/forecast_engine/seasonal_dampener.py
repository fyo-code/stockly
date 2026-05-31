"""Seasonal SKU detection + monthly multiplier dampening (Iter 3 Fix #4).

Many A-tier SKUs are seasonal accessories whose Dec peak gets extrapolated by
methods that don't see calendar context. Iter 2 root cause: SKUs like
JRLZEUSPEARL (1489% off) and KBGD02 (688% off) were over-predicted because
upstream methods averaged their full-year history without accounting for the
fact that the prediction window is off-season.

This module:
  1. Builds a monthly-share profile per SKU-store from training data.
  2. Flags a SKU as seasonal if the coefficient of variation across the 12
     monthly multipliers exceeds SEASONAL_CV_THRESHOLD.
  3. For seasonal SKUs, dampens the ensemble forecast by the average monthly
     multiplier across the prediction window.

Non-seasonal SKUs are untouched (multiplier ≈ 1 anyway).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np
import pandas as pd


log = logging.getLogger(__name__)


# --- Configuration ---

SEASONAL_CV_THRESHOLD = 0.5     # CV across monthly multipliers above this → SKU is seasonal
MULTIPLIER_FLOOR = 0.20         # never dampen below 20% of original (avoid zeros from sparse months)
MULTIPLIER_CEIL = 3.0           # never amplify beyond 3x (avoid blow-ups from outlier months)
MIN_MONTHS_OBSERVED = 6         # need at least 6 distinct calendar months of history


# --- Profile ---


@dataclass(frozen=True)
class MonthlyProfile:
    multipliers: dict[int, float]   # month (1-12) -> multiplier
    cv: float
    is_seasonal: bool
    months_observed: int


def _profile_for_series(monthly_totals: pd.Series) -> MonthlyProfile:
    """monthly_totals: Series indexed by month (1-12) with summed history sales."""
    if len(monthly_totals) < MIN_MONTHS_OBSERVED or monthly_totals.sum() == 0:
        return MonthlyProfile(
            multipliers={m: 1.0 for m in range(1, 13)},
            cv=0.0,
            is_seasonal=False,
            months_observed=int(len(monthly_totals)),
        )

    overall_avg = float(monthly_totals.mean())
    if overall_avg == 0:
        return MonthlyProfile(
            multipliers={m: 1.0 for m in range(1, 13)},
            cv=0.0,
            is_seasonal=False,
            months_observed=int(len(monthly_totals)),
        )

    multipliers: dict[int, float] = {}
    for m in range(1, 13):
        if m in monthly_totals.index:
            raw = float(monthly_totals.loc[m]) / overall_avg
            clipped = float(np.clip(raw, MULTIPLIER_FLOOR, MULTIPLIER_CEIL))
        else:
            # Month never appeared in history — neutral, not zero.
            clipped = 1.0
        multipliers[m] = clipped

    values = np.array(list(multipliers.values()), dtype=float)
    mean = values.mean()
    cv = float(values.std(ddof=1) / mean) if mean > 0 else 0.0
    is_seasonal = cv > SEASONAL_CV_THRESHOLD

    return MonthlyProfile(
        multipliers=multipliers,
        cv=cv,
        is_seasonal=is_seasonal,
        months_observed=int(len(monthly_totals)),
    )


def compute_monthly_profiles(
    weekly: pd.DataFrame,
    sku_col: str = "sku_id",
    store_col: str = "store_id",
    date_col: str = "week_start_date",
    sales_col: str = "net_sold",
) -> dict[tuple[str, str], MonthlyProfile]:
    """Build a MonthlyProfile per SKU-store from training weekly data."""
    df = weekly[[sku_col, store_col, date_col, sales_col]].copy()
    if not pd.api.types.is_datetime64_any_dtype(df[date_col]):
        df[date_col] = pd.to_datetime(df[date_col])
    df["_month"] = df[date_col].dt.month

    profiles: dict[tuple[str, str], MonthlyProfile] = {}
    grouped = df.groupby([sku_col, store_col, "_month"])[sales_col].sum().reset_index()

    for (sku, store), g in grouped.groupby([sku_col, store_col]):
        monthly_totals = g.set_index("_month")[sales_col]
        profiles[(str(sku), str(store))] = _profile_for_series(monthly_totals)

    return profiles


# --- Dampening ---


def _prediction_weeks(weekly: pd.DataFrame, date_col: str = "week_start_date") -> list[pd.Timestamp]:
    """Eight Monday-anchored weeks following the last training week."""
    if not pd.api.types.is_datetime64_any_dtype(weekly[date_col]):
        last = pd.to_datetime(weekly[date_col]).max()
    else:
        last = weekly[date_col].max()
    return [last + pd.Timedelta(weeks=i) for i in range(1, 9)]


def _window_multiplier(profile: MonthlyProfile, weeks: list[pd.Timestamp]) -> float:
    """Average multiplier across the months touched by the given weeks."""
    if not weeks:
        return 1.0
    vals = [profile.multipliers.get(int(w.month), 1.0) for w in weeks]
    return float(np.mean(vals))


def apply_seasonal_dampening(
    ensemble_list: list[dict],
    weekly: pd.DataFrame,
    sku_col: str = "sku_id",
    store_col: str = "store_id",
    date_col: str = "week_start_date",
) -> list[dict]:
    """Multiply 4w/8w forecasts and CIs by the average monthly multiplier
    across the prediction window for SKUs flagged seasonal.

    Mutates and returns the same list for efficiency. Non-seasonal SKUs and
    SKUs without a profile are untouched.
    """
    profiles = compute_monthly_profiles(
        weekly, sku_col=sku_col, store_col=store_col, date_col=date_col
    )
    pred_weeks = _prediction_weeks(weekly, date_col=date_col)
    weeks_4w = pred_weeks[:4]
    weeks_8w = pred_weeks[:8]

    n_dampened = 0
    n_seasonal = sum(1 for p in profiles.values() if p.is_seasonal)

    for r in ensemble_list:
        key = (str(r.get("sku_id", "")), str(r.get("store_id", "")))
        profile = profiles.get(key)
        if profile is None or not profile.is_seasonal:
            continue

        mult_4w = _window_multiplier(profile, weeks_4w)
        mult_8w = _window_multiplier(profile, weeks_8w)

        for field, mult in (
            ("forecast_4w", mult_4w),
            ("confidence_low_4w", mult_4w),
            ("confidence_high_4w", mult_4w),
            ("forecast_8w", mult_8w),
            ("confidence_low_8w", mult_8w),
            ("confidence_high_8w", mult_8w),
        ):
            if field in r and r[field] is not None:
                r[field] = round(float(r[field]) * mult, 1)

        r["seasonal_dampening_applied"] = True
        r["seasonal_multiplier_4w"] = round(mult_4w, 3)
        r["seasonal_multiplier_8w"] = round(mult_8w, 3)
        r["seasonal_cv"] = round(profile.cv, 3)
        n_dampened += 1

    log.info(
        "Seasonal dampening: %d SKUs flagged seasonal (CV>%.2f), %d ensemble rows adjusted "
        "for prediction window starting %s.",
        n_seasonal, SEASONAL_CV_THRESHOLD, n_dampened,
        pred_weeks[0].strftime("%Y-%m-%d") if pred_weeks else "n/a",
    )

    return ensemble_list
