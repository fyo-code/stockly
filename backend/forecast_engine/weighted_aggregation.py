"""Iter 4 Phase B.2 — derive per-method weights from windowed backtest results.

Why this exists:
    Iter 4 Phase B.1 tried to improve the median ensemble by archiving methods
    that scored poorly on a single window (Iter 3 / Mar-Apr 2025). Both archival
    hypotheses (B.1a: archive ETS+MSL; B.1b: archive AA+CatRel) regressed the
    engine on 4-6 of 6 windows. The lesson: a median ensemble is robust because
    every method is a vote, and removing votes — even from objectively bad
    methods — concentrates the median onto a smaller pool that drifts.

    Weighted aggregation keeps every method voting but multiplies each method's
    point forecast by a weight derived from its windowed accuracy. Bad methods
    can still nudge the ensemble (preserving robustness), but they cannot
    dominate it.

Weight formula:
    raw_weight  = max(0, 1 - WMAPE) ** 2
    floored     = max(raw_weight, FLOOR)
    normalised  = floored / sum(all floored)

Squaring (1 - WMAPE) accentuates good methods and zeroes anything ≥ 100% WMAPE
(worse than trivial guessing). The 0.05 floor prevents the ensemble from
collapsing onto one method on windows where it happens to be much stronger.

Hold-out:
    Per the plan, weights are derived from windows 1-5 only. Window 6 (Mar-Apr
    2025) is held out so we don't tune on the same window we'll then claim a
    win on.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


DEFAULT_FLOOR = 0.05

# Windows whose per-method WMAPE we use for weight derivation. W6 (Mar-Apr 2025)
# is held out — see module docstring.
TRAIN_WINDOWS = [
    "W1_MayJun24",
    "W2_JulAug24",
    "W3_SepOct24",
    "W4_NovDec24",
    "W5_JanFeb25",
]

# All methods that may participate in the ensemble. Keep aligned with
# config.ENABLED_METHODS keys. If a method is disabled in config, it just
# won't appear in the per-window CSV and gets weight=0 here.
METHOD_NAMES = [
    "ets",
    "anomaly_adjusted",
    "multi_scale_lag",
    "calendar_events",
    "category_relative",
    "naive_seasonal",
    "crostons",
]


def derive_weights_from_per_window_csv(
    per_window_csv: Path,
    train_windows: list[str] | None = None,
    floor: float = DEFAULT_FLOOR,
) -> dict[str, float]:
    """Read the windowed backtester's per-window CSV, compute per-method weights.

    Args:
        per_window_csv: Path to a CSV produced by `backtest_windows.main` —
            expects columns `window` and `<method>_wmape` for each method.
        train_windows: List of window labels to include in the mean. Defaults
            to W1-W5 (W6 held out).
        floor: Minimum weight per method, applied before renormalisation.

    Returns:
        dict of method_name -> weight, summing (approximately) to 1.0.
    """
    train_windows = train_windows or TRAIN_WINDOWS
    df = pd.read_csv(per_window_csv)
    df = df[df["window"].isin(train_windows)]

    means: dict[str, float] = {}
    for method in METHOD_NAMES:
        col = f"{method}_wmape"
        if col not in df.columns:
            continue
        vals = df[col].dropna()
        if vals.empty:
            continue
        means[method] = float(vals.mean())

    raw: dict[str, float] = {}
    for method, wmape in means.items():
        # WMAPE is on 0..inf scale (1.0 = 100%). Methods worse than naive
        # get weight 0 before flooring, then floored to FLOOR so they retain
        # a small voice.
        raw_weight = max(0.0, 1.0 - wmape) ** 2
        raw[method] = max(raw_weight, floor)

    total = sum(raw.values())
    if total <= 0:
        # All methods are catastrophically bad — fall back to equal weights so
        # we still produce a forecast.
        n = max(len(raw), 1)
        return {m: 1.0 / n for m in raw}

    return {m: w / total for m, w in raw.items()}


def write_weights_json(weights: dict[str, float], out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(weights, indent=2, sort_keys=True), encoding="utf-8")
    return out_path


def _format_weight_table(weights: dict[str, float], means: dict[str, float] | None = None) -> str:
    rows = ["| Method | Mean WMAPE | Weight |", "|---|---:|---:|"]
    for m in sorted(weights, key=lambda k: -weights[k]):
        mean_str = f"{means[m]*100:.1f}%" if means and m in means else "—"
        rows.append(f"| {m} | {mean_str} | {weights[m]:.4f} |")
    return "\n".join(rows)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--per-window-csv", required=True,
                        help="Path to ITER4_BACKTEST_WINDOWS_iter3_baseline.csv (or equivalent).")
    parser.add_argument("--out", required=True, help="Output JSON path for the derived weights.")
    parser.add_argument("--floor", type=float, default=DEFAULT_FLOOR)
    parser.add_argument("--train-windows", nargs="*", default=None,
                        help="Override TRAIN_WINDOWS list.")
    args = parser.parse_args()

    csv_path = Path(args.per_window_csv)
    out_path = Path(args.out)
    weights = derive_weights_from_per_window_csv(
        csv_path,
        train_windows=args.train_windows,
        floor=args.floor,
    )

    # Recompute means for display
    df = pd.read_csv(csv_path)
    if args.train_windows:
        df = df[df["window"].isin(args.train_windows)]
    else:
        df = df[df["window"].isin(TRAIN_WINDOWS)]
    means = {
        m: float(df[f"{m}_wmape"].dropna().mean())
        for m in METHOD_NAMES
        if f"{m}_wmape" in df.columns and df[f"{m}_wmape"].notna().any()
    }

    print(f"Source: {csv_path}")
    print(f"Train windows: {args.train_windows or TRAIN_WINDOWS}")
    print(f"Floor: {args.floor}")
    print()
    print(_format_weight_table(weights, means))
    print()

    write_weights_json(weights, out_path)
    print(f"Wrote weights to {out_path}")
