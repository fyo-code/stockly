"""Iter 4 Phase B.6 — derive per-method relative bias from windowed backtest results.

Reads the baseline per-window CSV produced by backtest_windows.py.
Computes the mean relative signed error for each method across training
windows W1–W5 (W6 held out), applies a magnitude cap, and writes the
result to a JSON file consumed by bias_correction.py.

Bias definition:
    bias_m = mean over W1-W5 of:  mean_window((predicted - actual) / actual)

This is the mean of each window's already-aggregated relative bias.
The per-window column name in the CSV is {method}_bias.

Correction formula (applied in bias_correction.py):
    p_corrected = p / (1 + bias_m_capped)

Cap:
    |bias_m| is clamped to CAP (default 0.30) before use. Methods with
    bias above 100% WMAPE are still over-corrected without the cap; the cap
    prevents unstable corrections on noisy windows where a single window
    biases the mean heavily.

Hold-out:
    W6 (Mar–Apr 2025) is excluded. Same discipline as the weight derivation
    in B.2. We derive biases only on W1–W5, then evaluate on all 6 windows.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


DEFAULT_CAP = 0.30

TRAIN_WINDOWS = [
    "W1_MayJun24",
    "W2_JulAug24",
    "W3_SepOct24",
    "W4_NovDec24",
    "W5_JanFeb25",
]

METHOD_NAMES = [
    "ets",
    "anomaly_adjusted",
    "multi_scale_lag",
    "calendar_events",
    "category_relative",
    "naive_seasonal",
    "crostons",
]


def derive_biases(
    per_window_csv: Path,
    train_windows: list[str] | None = None,
    cap: float = DEFAULT_CAP,
) -> dict[str, dict[str, float]]:
    """Compute per-method bias from windowed backtest CSV.

    Args:
        per_window_csv: CSV produced by backtest_windows.main. Must contain
            columns {method}_bias for each method.
        train_windows: Windows to include. Defaults to W1-W5.
        cap: Magnitude cap on |bias|. Values outside [-cap, +cap] are
            clamped before use.

    Returns:
        dict of method_name -> {"bias_4w": float, "bias_capped_4w": float}.
        The same value is used for 4w and 8w horizons because the per-window
        CSV only stores one bias per method (4-week horizon). A separate
        8-week bias column does not exist in the baseline CSV; using the 4w
        value for both is a known simplification — update when 8w-specific
        bias data is available.
    """
    train_windows = train_windows or TRAIN_WINDOWS
    df = pd.read_csv(per_window_csv)
    df = df[df["window"].isin(train_windows)]

    result: dict[str, dict[str, float]] = {}
    for method in METHOD_NAMES:
        col = f"{method}_bias"
        if col not in df.columns:
            continue
        vals = df[col].dropna()
        if vals.empty:
            continue
        raw = float(vals.mean())
        capped = max(-cap, min(cap, raw))
        result[method] = {
            "bias_raw": round(raw, 4),
            "bias_capped": round(capped, 4),
        }

    return result


def write_biases_json(biases: dict[str, dict[str, float]], out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(biases, indent=2, sort_keys=True), encoding="utf-8")
    return out_path


def _format_bias_table(biases: dict[str, dict[str, float]]) -> str:
    rows = ["| Method | Raw bias (W1-W5 mean) | Capped bias | Correction |"]
    rows.append("|---|---:|---:|---|")
    for m in sorted(biases):
        raw = biases[m]["bias_raw"]
        capped = biases[m]["bias_capped"]
        was_capped = abs(raw) > abs(capped) + 0.001
        correction = 1.0 / (1.0 + capped) if (1.0 + capped) != 0 else float("nan")
        direction = "reduce" if capped > 0 else "increase"
        pct = abs(1 - correction) * 100
        cap_note = f" (capped from {raw:+.2f})" if was_capped else ""
        rows.append(f"| {m} | {raw:+.3f} | {capped:+.3f}{cap_note} | {direction} by {pct:.0f}% |")
    return "\n".join(rows)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--per-window-csv", required=True,
                        help="Path to ITER4_BACKTEST_WINDOWS_iter3_baseline.csv (or equivalent).")
    parser.add_argument("--out", required=True,
                        help="Output JSON path for derived biases.")
    parser.add_argument("--cap", type=float, default=DEFAULT_CAP,
                        help="Magnitude cap on |bias| (default 0.30).")
    parser.add_argument("--train-windows", nargs="*", default=None)
    args = parser.parse_args()

    csv_path = Path(args.per_window_csv)
    out_path = Path(args.out)

    biases = derive_biases(csv_path, train_windows=args.train_windows, cap=args.cap)

    print(f"Source: {csv_path}")
    print(f"Train windows: {args.train_windows or TRAIN_WINDOWS}")
    print(f"Cap: ±{args.cap}")
    print()
    print(_format_bias_table(biases))
    print()

    write_biases_json(biases, out_path)
    print(f"Wrote biases to {out_path}")
