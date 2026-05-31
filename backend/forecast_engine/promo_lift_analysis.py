"""Iter 4 Phase D — read-only promo lift diagnostic.

For each category that has ≥30 promo-flagged SKU-weeks in sku_promo_weeks,
compute:

    lift = mean_yoy_ratio(promo_weeks) / mean_yoy_ratio(non_promo_weeks)

where yoy_ratio for a given SKU-week = units_sold(this_week) / units_sold(same_week_prior_year).

Prior-year equivalent: week_start − 364 days (exactly 52 weeks).
SKU-weeks where the prior-year observation is missing are excluded.

95% CI: bootstrap (1000 resamples) on the lift estimate.
Categories with <30 promo SKU-week events → lift = "unknown".

Output: active_docs/ITER4_PROMO_LIFT_ANALYSIS.md
"""

from __future__ import annotations

import random
import sqlite3
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = REPO_ROOT / "backend" / "data" / "supply_chain.db"
OUT_PATH = REPO_ROOT / "active_docs" / "ITER4_PROMO_LIFT_ANALYSIS.md"

MIN_EVENTS = 30
N_BOOTSTRAP = 1000
CI_LEVEL = 0.95


def _bootstrap_ci(
    values: list[float],
    n: int = N_BOOTSTRAP,
    ci: float = CI_LEVEL,
) -> tuple[float, float]:
    random.seed(42)
    means = [
        sum(random.choices(values, k=len(values))) / len(values)
        for _ in range(n)
    ]
    means.sort()
    lo = means[int((1 - ci) / 2 * n)]
    hi = means[int((1 + ci) / 2 * n)]
    return lo, hi


def compute_lift(db_path: Path) -> list[dict]:
    conn = sqlite3.connect(str(db_path))

    demand = pd.read_sql_query(
        """
        SELECT w.sku_id, w.week_start, w.units_sold, a.category
        FROM weekly_demand w
        JOIN abc_tiers a ON w.sku_id = a.sku_id
        WHERE a.tier = 'A'
        """,
        conn,
    )
    promo = pd.read_sql_query(
        "SELECT sku_id, week_start, promo_flag FROM sku_promo_weeks",
        conn,
    )
    conn.close()

    demand["week_start_dt"] = pd.to_datetime(demand["week_start"])
    promo["week_start_dt"] = pd.to_datetime(promo["week_start"])

    demand = demand.merge(promo[["sku_id", "week_start_dt", "promo_flag"]], on=["sku_id", "week_start_dt"], how="left")
    demand["promo_flag"] = demand["promo_flag"].fillna(0).astype(int)

    # Build lookup: (sku_id, week_start_dt) → units_sold
    demand_idx = demand.set_index(["sku_id", "week_start_dt"])["units_sold"]

    results: list[dict] = []
    for category, grp in demand.groupby("category"):
        promo_ratios: list[float] = []
        non_promo_ratios: list[float] = []

        for _, row in grp.iterrows():
            prior_week = row["week_start_dt"] - pd.Timedelta(days=364)
            try:
                prior_units = demand_idx.loc[(row["sku_id"], prior_week)]
            except KeyError:
                continue
            if prior_units == 0:
                continue
            ratio = row["units_sold"] / prior_units
            if row["promo_flag"] == 1:
                promo_ratios.append(ratio)
            else:
                non_promo_ratios.append(ratio)

        promo_n = len(promo_ratios)
        non_promo_n = len(non_promo_ratios)

        if promo_n < MIN_EVENTS:
            results.append({
                "category": category,
                "promo_events": promo_n,
                "non_promo_events": non_promo_n,
                "lift": None,
                "ci_low": None,
                "ci_high": None,
                "note": f"insufficient data (<{MIN_EVENTS} promo events)",
            })
            continue

        mean_promo = sum(promo_ratios) / promo_n
        mean_non_promo = sum(non_promo_ratios) / non_promo_n if non_promo_n > 0 else None

        if mean_non_promo is None or mean_non_promo == 0:
            results.append({
                "category": category,
                "promo_events": promo_n,
                "non_promo_events": non_promo_n,
                "lift": None,
                "ci_low": None,
                "ci_high": None,
                "note": "no non-promo events or zero non-promo baseline",
            })
            continue

        lift = mean_promo / mean_non_promo

        # Bootstrap CI on lift: resample promo and non-promo independently
        random.seed(42)
        lift_samples: list[float] = []
        for _ in range(N_BOOTSTRAP):
            p_sample = random.choices(promo_ratios, k=promo_n)
            np_sample = random.choices(non_promo_ratios, k=non_promo_n)
            np_mean = sum(np_sample) / non_promo_n
            if np_mean == 0:
                continue
            lift_samples.append((sum(p_sample) / promo_n) / np_mean)

        lift_samples.sort()
        alpha = (1 - CI_LEVEL) / 2
        ci_lo = lift_samples[int(alpha * len(lift_samples))]
        ci_hi = lift_samples[int((1 - alpha) * len(lift_samples))]

        results.append({
            "category": category,
            "promo_events": promo_n,
            "non_promo_events": non_promo_n,
            "lift": round(lift, 3),
            "ci_low": round(ci_lo, 3),
            "ci_high": round(ci_hi, 3),
            "note": "",
        })

    results.sort(key=lambda r: r["category"])
    return results


def _format_md(results: list[dict]) -> str:
    lines = [
        "# Iter 4 — Promo Lift Analysis",
        "",
        "Read-only diagnostic. Lift = mean YoY ratio (promo weeks) ÷ mean YoY ratio (non-promo weeks).",
        f"Prior year: same week −364 days. Min events for estimate: {MIN_EVENTS}. CI: {int(CI_LEVEL*100)}% bootstrap ({N_BOOTSTRAP} resamples).",
        "",
        "**Scope:** Baneasa store only. Promo flags are store-level signals, not global Mobexpert rules.",
        "",
        "| Category | Promo events | Non-promo events | Lift | 95% CI | Note |",
        "|---|---:|---:|---:|---|---|",
    ]
    for r in results:
        lift_str = f"{r['lift']:.3f}" if r["lift"] is not None else "unknown"
        ci_str = f"[{r['ci_low']:.3f}, {r['ci_high']:.3f}]" if r["ci_low"] is not None else "—"
        lines.append(
            f"| {r['category']} | {r['promo_events']:,} | {r['non_promo_events']:,} "
            f"| {lift_str} | {ci_str} | {r['note']} |"
        )
    lines += [
        "",
        "## Interpretation",
        "",
        "- Lift > 1 → promo weeks sell more than expected from prior-year baseline.",
        "- Lift < 1 → promo weeks under-perform prior-year baseline (possible: campaigns on slow-moving items).",
        "- 'unknown' → fewer than 30 promo events; estimate would be unreliable.",
        "",
        "## Iter 4 usage",
        "",
        "This is a diagnostic only. Lift values are not fed into method predictions in Iter 4.",
        "Iter 5 will use this to calibrate promo multipliers inside individual methods.",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    print("Computing promo lift by category...")
    results = compute_lift(DB_PATH)

    for r in results:
        lift_str = f"{r['lift']:.3f}" if r["lift"] is not None else "unknown"
        print(f"  {r['category']:30} promo={r['promo_events']:4d} non-promo={r['non_promo_events']:5d} lift={lift_str}  {r['note']}")

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(_format_md(results), encoding="utf-8")
    print(f"\nWrote {OUT_PATH}")


if __name__ == "__main__":
    main()
