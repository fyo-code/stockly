"""Iter 4 Phase B.6 — apply per-method relative bias correction to method outputs.

Correction formula:
    p_corrected = p / (1 + bias_capped)

where bias_capped is the W1-W5 mean relative bias for that method, clamped
to ±CAP (default 0.30). See derive_biases.py for how biases are derived.

Why multiplicative (not additive):
    The per-window CSV stores mean((p-a)/a) — relative bias. Correcting
    additively would require knowing the absolute scale, which varies by SKU.
    Multiplicative correction is scale-invariant and consistent with how the
    bias was measured.

Clipping after correction:
    Corrected predictions are clipped to ≥ 0. A negative prediction is
    nonsensical and would drag the median down if any method produces one
    after an aggressive upward correction on a near-zero predictor.
"""

from __future__ import annotations

import json
from pathlib import Path


def load_biases(biases_json: Path) -> dict[str, float]:
    """Load the bias JSON produced by derive_biases.py.

    Returns dict of method_name -> bias_capped (the correction-ready value).
    """
    data = json.loads(biases_json.read_text(encoding="utf-8"))
    return {m: float(v["bias_capped"]) for m, v in data.items()}


def apply_bias_correction(
    results_by_method: dict[str, list[dict]],
    biases: dict[str, float],
) -> dict[str, list[dict]]:
    """Apply multiplicative bias correction to all method results in-place.

    Args:
        results_by_method: dict of method_name -> list of result dicts,
            each with forecast_4w, forecast_8w, confidence_low/high fields.
        biases: dict of method_name -> bias_capped (from load_biases).
            Methods absent from biases are left uncorrected.

    Returns:
        The same dict, mutated in-place (results are modified directly).
    """
    for method_name, results in results_by_method.items():
        bias = biases.get(method_name, 0.0)
        if bias == 0.0:
            continue

        denom_4w = 1.0 + bias
        denom_8w = 1.0 + bias

        if abs(denom_4w) < 1e-6:
            continue

        for r in results:
            if r.get("error") is not None:
                continue
            r["forecast_4w"] = max(0.0, r["forecast_4w"] / denom_4w)
            r["forecast_8w"] = max(0.0, r["forecast_8w"] / denom_8w)
            r["confidence_low_4w"] = max(0.0, r["confidence_low_4w"] / denom_4w)
            r["confidence_high_4w"] = max(0.0, r["confidence_high_4w"] / denom_4w)
            r["confidence_low_8w"] = max(0.0, r["confidence_low_8w"] / denom_8w)
            r["confidence_high_8w"] = max(0.0, r["confidence_high_8w"] / denom_8w)

    return results_by_method
