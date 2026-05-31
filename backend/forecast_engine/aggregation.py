"""Ensemble Aggregation Engine — combines 6 forecasting methods into one prediction.

This is the central combiner for the Forecast Engine. It takes outputs from all
6 independent methods (ETS, LightGBM, Category-Relative, Anomaly-Adjusted,
Multi-Scale Lag, Calendar Events) and produces a single ensemble forecast per
SKU-store pair.

Aggregation strategy:
- **Median** (default) — robust to outliers from any single method failing badly.
- **Trimmed mean** — drops highest and lowest, averages the rest. Less sensitive
  to extremes but still uses more signal than median.
- **Equal-weight mean** — simple average. Not recommended unless all methods
  are known to be well-calibrated.

Disagreement scoring:
- Coefficient of Variation (CV = std / mean) across method point forecasts.
- LOW:  CV < 0.15  — methods broadly agree
- MEDIUM: 0.15 ≤ CV < 0.30  — some divergence, investigate
- HIGH: CV ≥ 0.30  — methods strongly disagree, forecast is uncertain

Confidence intervals:
- Ensemble CI is the union of individual method CIs: min(all lows), max(all highs).
  This is conservative but honest — the true uncertainty includes all methods' views.
"""

from datetime import datetime, timezone
from typing import Union

import numpy as np

from .data_models import (
    ETSResult,
    LGBMResult,
    CategoryRelativeResult,
    AnomalyAdjustedResult,
    MultiScaleLagResult,
    CalendarResult,
    MethodBreakdown,
    EnsembleForecastResult,
)


# Type alias for any method result
MethodResult = Union[
    ETSResult,
    LGBMResult,
    CategoryRelativeResult,
    AnomalyAdjustedResult,
    MultiScaleLagResult,
    CalendarResult,
]

# All recognised method names
ALL_METHOD_NAMES = [
    "ets",
    "lightgbm",
    "category_relative",
    "anomaly_adjusted",
    "multi_scale_lag",
    "calendar_events",
    "crostons",
    "naive_seasonal",
]

# Disagreement thresholds (CV)
CV_LOW = 0.15
CV_MEDIUM = 0.30


# --- Aggregation functions ---


def aggregate_median(values: list[float]) -> float:
    """Median of a list of floats. Returns 0.0 for empty list."""
    if not values:
        return 0.0
    return float(np.median(values))


def aggregate_trimmed_mean(values: list[float]) -> float:
    """Trimmed mean — drop highest and lowest, average the rest.

    With fewer than 3 values, falls back to simple median.
    """
    if len(values) < 3:
        return aggregate_median(values)
    sorted_vals = sorted(values)
    trimmed = sorted_vals[1:-1]
    return float(np.mean(trimmed))


def aggregate_equal_weight(values: list[float]) -> float:
    """Simple arithmetic mean. Returns 0.0 for empty list."""
    if not values:
        return 0.0
    return float(np.mean(values))


def aggregate_weighted(
    values_by_method: dict[str, float],
    weights: dict[str, float],
) -> float:
    """Weighted MEDIAN across method outputs.

    Iter 4 Phase B.2: keep every method voting (median ensemble's accuracy
    depends on having lots of votes — archival hypotheses B.1a and B.1b
    both regressed by 4-6 of 6 windows). Bad methods get a small weight,
    good methods get a big one. Smooth version of archival.

    Why weighted MEDIAN, not weighted MEAN:
        Weighted mean (first attempt at B.2) regressed badly on windows
        where one method posted an extreme outlier (e.g. Cat-Rel 221%
        WMAPE on W5). Even at small weights, the outlier dragged the
        mean. The median ensemble's killer feature is robustness to
        outliers — every value past the centre is ignored. Weighted median
        keeps that robustness while letting accurate methods lean the
        ensemble in their direction.

    Algorithm:
        1. Sort method outputs by value.
        2. Walk left-to-right accumulating weights.
        3. The weighted median is the value where the cumulative weight
           crosses half the total weight (linearly interpolated when the
           crossing falls between two adjacent values).

    Args:
        values_by_method: dict of method_name -> point forecast from that
            method. Only methods present here contribute.
        weights: dict of method_name -> weight. Methods missing from this
            dict fall back to weight=0 (excluded).

    Returns:
        Weighted median. Falls back to plain median if no method has a
        positive weight.
    """
    if not values_by_method:
        return 0.0

    pairs: list[tuple[float, float]] = []
    for method_name, value in values_by_method.items():
        w = float(weights.get(method_name, 0.0))
        if w <= 0.0:
            continue
        pairs.append((float(value), w))

    if not pairs:
        return aggregate_median(list(values_by_method.values()))

    pairs.sort(key=lambda p: p[0])
    total = sum(w for _, w in pairs)
    target = total / 2.0

    cumulative = 0.0
    for i, (value, w) in enumerate(pairs):
        cumulative += w
        if cumulative >= target:
            # Standard weighted median: interpolate between this value and
            # the previous one when the half-weight crossing lands between
            # samples (i.e. cumulative_before exactly equals target).
            cumulative_before = cumulative - w
            if i > 0 and abs(cumulative_before - target) < 1e-12:
                return (pairs[i - 1][0] + value) / 2.0
            return value

    return pairs[-1][0]  # numerical safety; should not reach here


def classify_disagreement(values: list[float]) -> str:
    """Classify method disagreement level based on coefficient of variation.

    Args:
        values: List of point forecasts from different methods.

    Returns:
        "LOW", "MEDIUM", or "HIGH".
    """
    if len(values) < 2:
        return "LOW"

    mean = np.mean(values)
    if mean == 0:
        return "LOW"

    cv = float(np.std(values, ddof=1) / mean)

    if cv < CV_LOW:
        return "LOW"
    if cv < CV_MEDIUM:
        return "MEDIUM"
    return "HIGH"


# --- Core combiner ---


def _extract_breakdown(result: MethodResult) -> MethodBreakdown:
    """Extract the standard fields from any method result into a MethodBreakdown."""
    return MethodBreakdown(
        forecast_4w=result["forecast_4w"],
        forecast_8w=result["forecast_8w"],
        confidence_low_4w=result["confidence_low_4w"],
        confidence_high_4w=result["confidence_high_4w"],
        confidence_low_8w=result["confidence_low_8w"],
        confidence_high_8w=result["confidence_high_8w"],
        error=result.get("error"),
    )


def combine_methods(
    method_results: dict[str, MethodResult],
    aggregation: str = "median",
    weights: dict[str, float] | None = None,
) -> EnsembleForecastResult:
    """Combine multiple method results into a single ensemble forecast.

    Args:
        method_results: Dict mapping method name → its result dict.
            Only methods with error=None contribute to the ensemble.
            Example: {"ets": ETSResult, "lightgbm": LGBMResult, ...}
        aggregation: One of "median", "trimmed_mean", "equal_weight", "weighted".
        weights: Required when aggregation="weighted". Dict of method_name ->
            weight. Methods absent get weight 0. Renormalised over methods
            that succeeded for the SKU at hand.

    Returns:
        EnsembleForecastResult with combined forecast, CIs, breakdown,
        and disagreement scoring.
    """
    use_weighted = aggregation == "weighted"
    if use_weighted and not weights:
        # Fall back rather than raise — keeps the engine robust if a caller
        # forgets to pass weights. Logged via the aggregation_method field.
        aggregation = "median"
        use_weighted = False

    agg_fn = {
        "median": aggregate_median,
        "trimmed_mean": aggregate_trimmed_mean,
        "equal_weight": aggregate_equal_weight,
    }.get(aggregation, aggregate_median)

    # Separate successful vs failed
    succeeded: dict[str, MethodResult] = {}
    failed: dict[str, MethodResult] = {}
    breakdown: dict[str, MethodBreakdown] = {}

    sku_id = ""
    store_id = ""

    for method_name, result in method_results.items():
        breakdown[method_name] = _extract_breakdown(result)

        if not sku_id:
            sku_id = result.get("sku_id", "")
        if not store_id:
            store_id = result.get("store_id", "")

        if result.get("error") is None:
            succeeded[method_name] = result
        else:
            failed[method_name] = result

    # Collect point forecasts and CIs from successful methods
    forecasts_4w = [r["forecast_4w"] for r in succeeded.values()]
    forecasts_8w = [r["forecast_8w"] for r in succeeded.values()]
    ci_lows_4w = [r["confidence_low_4w"] for r in succeeded.values()]
    ci_highs_4w = [r["confidence_high_4w"] for r in succeeded.values()]
    ci_lows_8w = [r["confidence_low_8w"] for r in succeeded.values()]
    ci_highs_8w = [r["confidence_high_8w"] for r in succeeded.values()]

    # Aggregate point forecasts
    if use_weighted:
        values_4w_by_method = {m: r["forecast_4w"] for m, r in succeeded.items()}
        values_8w_by_method = {m: r["forecast_8w"] for m, r in succeeded.items()}
        ensemble_4w = aggregate_weighted(values_4w_by_method, weights or {})
        ensemble_8w = aggregate_weighted(values_8w_by_method, weights or {})
    else:
        ensemble_4w = agg_fn(forecasts_4w)
        ensemble_8w = agg_fn(forecasts_8w)

    # Confidence intervals: union (conservative)
    ensemble_ci_low_4w = min(ci_lows_4w) if ci_lows_4w else 0.0
    ensemble_ci_high_4w = max(ci_highs_4w) if ci_highs_4w else 0.0
    ensemble_ci_low_8w = min(ci_lows_8w) if ci_lows_8w else 0.0
    ensemble_ci_high_8w = max(ci_highs_8w) if ci_highs_8w else 0.0

    # Disagreement
    disagree_4w = classify_disagreement(forecasts_4w)
    disagree_8w = classify_disagreement(forecasts_8w)

    return EnsembleForecastResult(
        sku_id=sku_id,
        store_id=store_id,
        forecast_4w=round(ensemble_4w, 1),
        forecast_8w=round(ensemble_8w, 1),
        confidence_low_4w=round(ensemble_ci_low_4w, 1),
        confidence_high_4w=round(ensemble_ci_high_4w, 1),
        confidence_low_8w=round(ensemble_ci_low_8w, 1),
        confidence_high_8w=round(ensemble_ci_high_8w, 1),
        method_breakdown=breakdown,
        methods_succeeded=len(succeeded),
        methods_failed=len(failed),
        method_disagreement_4w=disagree_4w,
        method_disagreement_8w=disagree_8w,
        aggregation_method=aggregation,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )


# --- Ensemble orchestrator ---


class EnsembleForecaster:
    """Orchestrates all 6 methods and combines into ensemble forecasts.

    This class does NOT run the individual forecasters — it takes their
    pre-computed results and combines them. The caller is responsible for
    running each method (Methods 1-6) and passing results here.

    This keeps the aggregation logic cleanly separated from method execution,
    and allows the caller to run methods in parallel if desired.
    """

    def __init__(
        self,
        aggregation: str = "median",
        weights: dict[str, float] | None = None,
    ):
        self._aggregation = aggregation
        self._weights = weights or {}

    def produce_final_forecast(
        self,
        method_results: dict[str, MethodResult],
    ) -> EnsembleForecastResult:
        """Produce ensemble forecast from pre-computed method results.

        Args:
            method_results: Dict mapping method name → result.
                At minimum 1 method must succeed for a non-zero forecast.

        Returns:
            EnsembleForecastResult.
        """
        return combine_methods(
            method_results,
            aggregation=self._aggregation,
            weights=self._weights,
        )

    def produce_batch_forecasts(
        self,
        all_method_results: dict[str, list[MethodResult]],
    ) -> list[EnsembleForecastResult]:
        """Produce ensemble forecasts for all SKU-store pairs.

        Expects each method to return results in the same order (same set of
        SKU-store pairs). Groups by (sku_id, store_id), then combines.

        Args:
            all_method_results: Dict mapping method name → list of results.
                Example: {"ets": [r1, r2, ...], "lightgbm": [r1, r2, ...], ...}

        Returns:
            List of EnsembleForecastResult, one per SKU-store pair.
        """
        # Index each method's results by (sku_id, store_id)
        indexed: dict[str, dict[tuple[str, str], MethodResult]] = {}
        all_keys: set[tuple[str, str]] = set()

        for method_name, results_list in all_method_results.items():
            method_index: dict[tuple[str, str], MethodResult] = {}
            for r in results_list:
                key = (r["sku_id"], r["store_id"])
                method_index[key] = r
                all_keys.add(key)
            indexed[method_name] = method_index

        # Produce ensemble for each SKU-store pair
        ensemble_results: list[EnsembleForecastResult] = []

        for sku_store_key in sorted(all_keys):
            per_method: dict[str, MethodResult] = {}
            for method_name, method_index in indexed.items():
                if sku_store_key in method_index:
                    per_method[method_name] = method_index[sku_store_key]

            ensemble = combine_methods(
                per_method,
                aggregation=self._aggregation,
                weights=self._weights,
            )
            ensemble_results.append(ensemble)

        return ensemble_results
