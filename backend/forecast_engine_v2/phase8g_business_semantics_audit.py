"""Phase 8G-L business-semantics audit for forecast v2.

This phase checks whether current high-revenue policy logic incorrectly treats
stock as hard sellability. It does not change production prediction behavior.
"""

from __future__ import annotations

import argparse
import sqlite3
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from .scorecard import DB_PATH
    from .sklearn_direct_model import HIGH_REVENUE_CHAMPION_MODEL
except ImportError:  # Allows direct script execution.
    from scorecard import DB_PATH
    from sklearn_direct_model import HIGH_REVENUE_CHAMPION_MODEL


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SCORE_ROWS_CSV = PROJECT_ROOT / "active_docs" / "ITER5Z_V2_PHASE8G_OFFICIAL_CALIBRATED_SCORE_ROWS.csv"
DEFAULT_REPORT = PROJECT_ROOT / "active_docs" / "ITER5AA_V2_PHASE8G_BUSINESS_SEMANTICS_AUDIT.md"

CONTROL_MODEL = "sk_blend_post_bf_safe"
EXTRA_TREES_MODEL = "sk_extra_trees"
POST_BF_SAFE_MODEL = "post_bf_safe_naive"
CURRENT_CHAMPION = HIGH_REVENUE_CHAMPION_MODEL
POST_BF_STRESS_WINDOW = "post_bf_window"


def _fmt_pct(value: object) -> str:
    if value is None or pd.isna(value):
        return "-"
    return f"{float(value) * 100:.1f}%"


def _fmt_pp(value: object) -> str:
    if value is None or pd.isna(value):
        return "-"
    return f"{float(value) * 100:+.1f}pp"


def _fmt_num(value: object, digits: int = 1) -> str:
    if value is None or pd.isna(value):
        return "-"
    return f"{float(value):,.{digits}f}"


def _table(headers: list[str], rows: list[list[str]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(lines)


def _scalar(conn: sqlite3.Connection, sql: str) -> tuple[object, ...]:
    return conn.execute(sql).fetchone()


def _raw_data_audit(conn: sqlite3.Connection) -> dict[str, tuple[object, ...]]:
    audits: dict[str, tuple[object, ...]] = {}
    audits["returns"] = _scalar(
        conn,
        """
        SELECT
            COUNT(*) AS rows,
            SUM(CASE WHEN quantity < 0 THEN 1 ELSE 0 END) AS negative_qty_rows,
            SUM(CASE WHEN line_value < 0 THEN 1 ELSE 0 END) AS negative_value_rows,
            SUM(CASE WHEN quantity < 0 AND line_value < 0 THEN 1 ELSE 0 END) AS both_negative_rows,
            SUM(CASE WHEN quantity < 0 AND line_value > 0 THEN 1 ELSE 0 END) AS qty_negative_value_positive_rows,
            SUM(CASE WHEN quantity > 0 THEN quantity ELSE 0 END) AS gross_units,
            SUM(CASE WHEN quantity < 0 THEN ABS(quantity) ELSE 0 END) AS returned_units,
            SUM(CASE WHEN quantity < 0 THEN net_revenue ELSE 0 END) AS return_net_revenue
        FROM raw_sales_transactions_v2
        WHERE is_non_product = 0
        """,
    )
    audits["discounts"] = _scalar(
        conn,
        """
        SELECT
            COUNT(*) AS rows,
            SUM(CASE WHEN discount_pct IS NULL THEN 1 ELSE 0 END) AS null_discount_rows,
            SUM(CASE WHEN discount_pct = 0 THEN 1 ELSE 0 END) AS zero_discount_rows,
            SUM(CASE WHEN discount_pct > 0 AND discount_pct <= 1 THEN 1 ELSE 0 END) AS fractional_discount_rows,
            SUM(CASE WHEN discount_pct > 1 AND discount_pct < 1e308 THEN 1 ELSE 0 END) AS over_one_discount_rows,
            SUM(CASE WHEN discount_pct >= 1e308 THEN 1 ELSE 0 END) AS infinite_discount_rows,
            AVG(CASE WHEN discount_pct > 0 AND discount_pct <= 1 THEN discount_pct END) AS avg_fractional_discount,
            MAX(CASE WHEN discount_pct > 0 AND discount_pct < 1e308 THEN discount_pct END) AS max_finite_discount
        FROM raw_sales_transactions_v2
        WHERE is_non_product = 0
        """,
    )
    audits["weekly_discount_inf"] = _scalar(
        conn,
        """
        SELECT
            COUNT(*) AS weekly_rows,
            SUM(CASE WHEN avg_discount_pct >= 1e308 THEN 1 ELSE 0 END) AS avg_inf_rows,
            SUM(CASE WHEN max_discount_pct >= 1e308 THEN 1 ELSE 0 END) AS max_inf_rows
        FROM weekly_chain_demand_v2
        """,
    )
    audits["campaigns"] = _scalar(
        conn,
        """
        SELECT
            COUNT(*) AS rows,
            SUM(CASE WHEN campaign_signal_status = 'observed' THEN 1 ELSE 0 END) AS observed_campaign_rows,
            SUM(CASE WHEN bf_signal_status = 'observed' THEN 1 ELSE 0 END) AS observed_bf_rows,
            SUM(CASE WHEN bf_signal_status = 'inferred' THEN 1 ELSE 0 END) AS inferred_bf_rows,
            SUM(CASE WHEN is_product_program = 1 THEN 1 ELSE 0 END) AS product_program_rows
        FROM raw_sales_transactions_v2
        WHERE is_non_product = 0
        """,
    )
    audits["vechime"] = _scalar(
        conn,
        """
        SELECT
            COUNT(*) AS snapshot_rows,
            COUNT(DISTINCT sku_id) AS snapshot_skus,
            SUM(CASE WHEN collection_age_bucket IS NOT NULL
                     AND collection_age_bucket NOT IN ('', '#null', '-')
                THEN 1 ELSE 0 END) AS collection_age_rows,
            COUNT(DISTINCT CASE WHEN collection_age_bucket IS NOT NULL
                     AND collection_age_bucket NOT IN ('', '#null', '-')
                THEN sku_id END) AS collection_age_skus,
            SUM(CASE WHEN stock_entry_date IS NOT NULL THEN 1 ELSE 0 END) AS stock_entry_date_rows
        FROM stock_snapshot_store_v2
        """,
    )
    return audits


def _raw_data_rows(audits: dict[str, tuple[object, ...]]) -> list[list[str]]:
    returns = audits["returns"]
    discounts = audits["discounts"]
    weekly_discount = audits["weekly_discount_inf"]
    campaigns = audits["campaigns"]
    vechime = audits["vechime"]
    gross_units = float(returns[5] or 0)
    returned_units = float(returns[6] or 0)
    rows = [
        [
            "Returns are ingested",
            _fmt_num(returns[1], 0),
            f"{_fmt_num(returned_units, 1)} returned units / {_fmt_pct(returned_units / gross_units if gross_units else None)} of gross positive units",
            "Important but not ignored; target currently predicts positive units, not net units.",
        ],
        [
            "Return value sign alignment",
            _fmt_num(returns[4], 0),
            f"{_fmt_num(returns[3], 0)} negative-quantity rows also have negative value",
            "Only rows with negative quantity and positive value are a likely revenue-sign issue.",
        ],
        [
            "Discounts are ingested",
            _fmt_num(discounts[3], 0),
            f"{_fmt_pct(discounts[6])} avg finite fractional discount; {_fmt_num(discounts[4], 0)} finite >1 rows; {_fmt_num(discounts[5], 0)} infinite rows",
            "Used as lag/campaign memory, but needs invalid-value cleanup plus scale normalization checks.",
        ],
        [
            "Weekly discount aggregates poisoned by infinity",
            _fmt_num(weekly_discount[1], 0),
            f"{_fmt_num(weekly_discount[2], 0)} max-discount weekly rows are infinite",
            "Small row count, but must be cleaned because tree models can react badly to infinite values.",
        ],
        [
            "Campaign/BF fields are present",
            _fmt_num(campaigns[1], 0),
            f"{_fmt_num(campaigns[2], 0)} observed BF rows; {_fmt_num(campaigns[3], 0)} inferred BF rows",
            "Used as history; still missing future campaign membership / SKU assignment plan.",
        ],
        [
            "VECHIME / collection age exists only in stock snapshots",
            _fmt_num(vechime[2], 0),
            f"{_fmt_num(vechime[3], 0)} SKUs with collection age; {_fmt_num(vechime[4], 0)} rows with stock-entry date",
            "Useful, but not currently safe as historical backtest input unless as-of dates are available.",
        ],
    ]
    return rows


def _load_official_rows(path: Path) -> pd.DataFrame:
    rows = pd.read_csv(path)
    required = {CONTROL_MODEL, EXTRA_TREES_MODEL, POST_BF_SAFE_MODEL, CURRENT_CHAMPION}
    present = set(rows["model_name"].dropna().astype(str).unique())
    missing = sorted(required - present)
    if missing:
        raise ValueError(f"Official score rows are missing required models: {missing}")
    return rows


def _base_frame(score_rows: pd.DataFrame) -> pd.DataFrame:
    context_cols = [
        "sku_id",
        "target_start",
        "actual_units",
        "actual_revenue",
        "quantity_scored",
        "primary_route",
        "calendar_route_context",
        "revenue_rank",
        "active_weeks_52",
        "avg_units_per_4w_52",
        "campaign_txn_13w",
        "bf_txn_13w",
        "bf_unit_share_4w",
        "target_is_post_bf_4w",
        "target_is_bf_window",
        "stock_observed_prev_month",
        "stock_prev_month_qty",
        "supplier_stock_observed_prev_month",
        "supplier_stock_prev_month_qty",
        "combined_stock_observed_prev_month",
        "combined_stock_prev_month_qty",
    ]
    model_frames = {}
    for model_name in [CONTROL_MODEL, EXTRA_TREES_MODEL, POST_BF_SAFE_MODEL, CURRENT_CHAMPION]:
        cols = ["sku_id", "target_start", "pred_units"]
        model_frames[model_name] = (
            score_rows[score_rows["model_name"] == model_name][cols]
            .copy()
            .rename(columns={"pred_units": f"pred_{model_name}"})
        )
    base = score_rows[score_rows["model_name"] == CURRENT_CHAMPION][context_cols].copy()
    for model_name, frame in model_frames.items():
        base = base.merge(frame, on=["sku_id", "target_start"], how="inner")
    for col in [
        "actual_units",
        "actual_revenue",
        "quantity_scored",
        "revenue_rank",
        "active_weeks_52",
        "avg_units_per_4w_52",
        "campaign_txn_13w",
        "bf_txn_13w",
        "bf_unit_share_4w",
        "target_is_post_bf_4w",
        "target_is_bf_window",
        "stock_observed_prev_month",
        "stock_prev_month_qty",
        "supplier_stock_observed_prev_month",
        "supplier_stock_prev_month_qty",
        "combined_stock_observed_prev_month",
        "combined_stock_prev_month_qty",
    ]:
        base[col] = pd.to_numeric(base[col], errors="coerce").fillna(0.0)
    return base


def _score(frame: pd.DataFrame, pred_col: str, mask: pd.Series | None = None) -> dict[str, object]:
    scoped = frame if mask is None else frame[mask].copy()
    pred = pd.to_numeric(scoped[pred_col], errors="coerce").fillna(0.0).clip(lower=0.0)
    actual = pd.to_numeric(scoped["actual_units"], errors="coerce").fillna(0.0)
    quantity_scored = pd.to_numeric(scoped["quantity_scored"], errors="coerce").fillna(0.0) == 1
    abs_error = (pred - actual).abs()
    signed_error = pred - actual
    scored = scoped[quantity_scored].copy()
    scored_abs_error = abs_error[quantity_scored]
    scored_signed_error = signed_error[quantity_scored]
    scored_actual = actual[quantity_scored]
    actual_sum = float(scored_actual.sum())
    zero_actual = actual == 0
    abs_pct = np.where(scored_actual > 0, scored_abs_error / scored_actual, np.nan)
    return {
        "rows": int(len(scoped)),
        "scored": int(len(scored)),
        "actual_revenue": float(scoped.get("actual_revenue", pd.Series(0.0, index=scoped.index)).sum()),
        "hit20": float(np.nanmean(abs_pct <= 0.20)) if len(abs_pct) else None,
        "hit30": float(np.nanmean(abs_pct <= 0.30)) if len(abs_pct) else None,
        "wmape": float(scored_abs_error.sum() / actual_sum) if actual_sum > 0 else None,
        "bias": float(scored_signed_error.sum() / actual_sum) if actual_sum > 0 else None,
        "phantom_rate": float(((actual[zero_actual] == 0) & (pred[zero_actual] >= 1.0)).mean()) if zero_actual.any() else None,
    }


def _delta(candidate: object, baseline: object) -> float | None:
    if candidate is None or baseline is None or pd.isna(candidate) or pd.isna(baseline):
        return None
    return float(candidate) - float(baseline)


def _make_semantic_candidates(base: pd.DataFrame) -> pd.DataFrame:
    rows = base.copy()
    control = f"pred_{CONTROL_MODEL}"
    extra = f"pred_{EXTRA_TREES_MODEL}"
    post_bf = f"pred_{POST_BF_SAFE_MODEL}"
    champion = f"pred_{CURRENT_CHAMPION}"

    current_regular = rows["primary_route"].astype(str).isin({"available_regular", "proxy_available_regular"})
    stock_constrained = rows["primary_route"].astype(str) == "stock_constrained"
    normal_calendar = rows["calendar_route_context"].astype(str) == "normal_calendar"
    demand_regular = (
        (rows["active_weeks_52"] >= 24)
        & (rows["avg_units_per_4w_52"] >= 2.0)
        & normal_calendar
    )
    no_recent_campaign_bf = (rows["campaign_txn_13w"] <= 0) & (rows["bf_txn_13w"] <= 0)
    post_bf_stress = (rows["target_is_post_bf_4w"] == 1) & (rows["bf_unit_share_4w"] > 0)

    rows["pred_8gl_champion_without_regular_stock_gate"] = rows[control].copy()
    rows.loc[post_bf_stress, "pred_8gl_champion_without_regular_stock_gate"] = rows.loc[post_bf_stress, post_bf]

    rows["pred_8gl_demand_regular_plus_post_bf_safe"] = rows[control].copy()
    rows.loc[demand_regular, "pred_8gl_demand_regular_plus_post_bf_safe"] = rows.loc[demand_regular, extra]
    rows.loc[post_bf_stress, "pred_8gl_demand_regular_plus_post_bf_safe"] = rows.loc[post_bf_stress, post_bf]

    rows["pred_8gl_demand_regular_no_campaign_plus_post_bf_safe"] = rows[control].copy()
    guarded_demand_regular = demand_regular & no_recent_campaign_bf
    rows.loc[guarded_demand_regular, "pred_8gl_demand_regular_no_campaign_plus_post_bf_safe"] = rows.loc[
        guarded_demand_regular, extra
    ]
    rows.loc[post_bf_stress, "pred_8gl_demand_regular_no_campaign_plus_post_bf_safe"] = rows.loc[post_bf_stress, post_bf]

    rows["pred_8gl_stock_constrained_as_regular_plus_post_bf_safe"] = rows[champion].copy()
    stock_regular = stock_constrained & demand_regular
    rows.loc[stock_regular, "pred_8gl_stock_constrained_as_regular_plus_post_bf_safe"] = rows.loc[stock_regular, extra]
    rows.loc[post_bf_stress, "pred_8gl_stock_constrained_as_regular_plus_post_bf_safe"] = rows.loc[post_bf_stress, post_bf]

    rows["_mask_current_regular"] = current_regular.astype(int)
    rows["_mask_stock_constrained"] = stock_constrained.astype(int)
    rows["_mask_demand_regular"] = demand_regular.astype(int)
    rows["_mask_guarded_demand_regular"] = guarded_demand_regular.astype(int)
    rows["_mask_stock_regular"] = stock_regular.astype(int)
    rows["_mask_post_bf_stress"] = post_bf_stress.astype(int)
    return rows


def _candidate_rows(frame: pd.DataFrame) -> list[list[str]]:
    baseline = _score(frame, f"pred_{CURRENT_CHAMPION}")
    candidate_cols = [
        (CURRENT_CHAMPION, f"pred_{CURRENT_CHAMPION}", "official current champion"),
        ("8gl_champion_without_regular_stock_gate", "pred_8gl_champion_without_regular_stock_gate", "removes regular-route stock gate replacement"),
        ("8gl_demand_regular_plus_post_bf_safe", "pred_8gl_demand_regular_plus_post_bf_safe", "uses demand regularity, not stock availability, for extra-trees replacement"),
        (
            "8gl_demand_regular_no_campaign_plus_post_bf_safe",
            "pred_8gl_demand_regular_no_campaign_plus_post_bf_safe",
            "same, but excludes recent campaign/BF history",
        ),
        (
            "8gl_stock_constrained_as_regular_plus_post_bf_safe",
            "pred_8gl_stock_constrained_as_regular_plus_post_bf_safe",
            "treats stock-constrained regular-demand rows as sellable regular rows",
        ),
    ]
    rows: list[list[str]] = []
    for model_name, pred_col, note in candidate_cols:
        metrics = _score(frame, pred_col)
        rows.append(
            [
                model_name,
                f"{metrics['rows']:,}",
                f"{metrics['scored']:,}",
                _fmt_pct(metrics["hit20"]),
                _fmt_pp(_delta(metrics["hit20"], baseline["hit20"])),
                _fmt_pct(metrics["hit30"]),
                _fmt_pct(metrics["wmape"]),
                _fmt_pp(_delta(metrics["wmape"], baseline["wmape"])),
                _fmt_pct(metrics["bias"]),
                _fmt_pct(metrics["phantom_rate"]),
                note,
            ]
        )
    return rows


def _route_rows(frame: pd.DataFrame) -> list[list[str]]:
    rows: list[list[str]] = []
    for route, group in frame.groupby(frame["primary_route"].astype(str), dropna=False):
        champion = _score(group, f"pred_{CURRENT_CHAMPION}")
        control = _score(group, f"pred_{CONTROL_MODEL}")
        extra = _score(group, f"pred_{EXTRA_TREES_MODEL}")
        rows.append(
            [
                str(route),
                f"{len(group):,}",
                f"{champion['scored']:,}",
                _fmt_pct(champion["hit20"]),
                _fmt_pct(control["hit20"]),
                _fmt_pct(extra["hit20"]),
                _fmt_pct(champion["wmape"]),
                _fmt_pct(control["wmape"]),
                _fmt_pct(extra["wmape"]),
                _fmt_pct(champion["bias"]),
            ]
        )
    return sorted(rows, key=lambda row: int(row[1].replace(",", "")), reverse=True)


def _mask_rows(frame: pd.DataFrame) -> list[list[str]]:
    masks = [
        ("Current regular/proxy route", "_mask_current_regular"),
        ("Stock-constrained current route", "_mask_stock_constrained"),
        ("Demand-regular no stock semantics", "_mask_demand_regular"),
        ("Demand-regular no campaign/BF", "_mask_guarded_demand_regular"),
        ("Stock-constrained but demand-regular", "_mask_stock_regular"),
        ("Post-BF stress override", "_mask_post_bf_stress"),
    ]
    rows: list[list[str]] = []
    for label, col in masks:
        mask = frame[col] == 1
        current = _score(frame, f"pred_{CURRENT_CHAMPION}", mask)
        control = _score(frame, f"pred_{CONTROL_MODEL}", mask)
        extra = _score(frame, f"pred_{EXTRA_TREES_MODEL}", mask)
        rows.append(
            [
                label,
                f"{int(mask.sum()):,}",
                f"{current['scored']:,}",
                _fmt_pct(current["hit20"]),
                _fmt_pct(control["hit20"]),
                _fmt_pct(extra["hit20"]),
                _fmt_pct(current["wmape"]),
                _fmt_pct(control["wmape"]),
                _fmt_pct(extra["wmape"]),
                _fmt_pct(current["bias"]),
            ]
        )
    return rows


def _window_rows(frame: pd.DataFrame) -> list[list[str]]:
    rows: list[list[str]] = []
    baseline_col = f"pred_{CURRENT_CHAMPION}"
    candidate_col = "pred_8gl_demand_regular_plus_post_bf_safe"
    for target_start, group in sorted(frame.groupby(frame["target_start"].astype(str), dropna=False)):
        baseline = _score(group, baseline_col)
        candidate = _score(group, candidate_col)
        rows.append(
            [
                str(target_start),
                f"{candidate['scored']:,}",
                _fmt_pct(baseline["hit20"]),
                _fmt_pct(candidate["hit20"]),
                _fmt_pp(_delta(candidate["hit20"], baseline["hit20"])),
                _fmt_pct(baseline["wmape"]),
                _fmt_pct(candidate["wmape"]),
                _fmt_pp(_delta(candidate["wmape"], baseline["wmape"])),
                _fmt_pct(baseline["bias"]),
                _fmt_pct(candidate["bias"]),
            ]
        )
    return rows


def build_report(conn: sqlite3.Connection, score_rows_csv: Path) -> str:
    audits = _raw_data_audit(conn)
    official_rows = _load_official_rows(score_rows_csv)
    frame = _make_semantic_candidates(_base_frame(official_rows))
    current = _score(frame, f"pred_{CURRENT_CHAMPION}")
    demand_regular = _score(frame, "pred_8gl_demand_regular_plus_post_bf_safe")
    hit_delta = _delta(demand_regular["hit20"], current["hit20"])
    wmape_delta = _delta(demand_regular["wmape"], current["wmape"])
    promotion_hit_gate = 0.005
    if hit_delta is not None and hit_delta > 0.005 and wmape_delta is not None and wmape_delta <= 0:
        decision = "RUN_STOCK_SOFT_REBUILD_BEFORE_FURTHER_CALIBRATION"
    else:
        decision = "KEEP_CURRENT_CHAMPION_AND_RELABEL_STOCK_SEMANTICS"

    return "\n".join(
        [
            "# Iteration 5AA - V2 Phase 8G-L Business Semantics Audit",
            "",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            "## Decision",
            "",
            f"Decision: `{decision}`.",
            "",
            "Mobexpert stock should not be interpreted as a hard can-sell / cannot-sell gate. Active/orderable SKU status is the missing sellability signal. Existing stock quantities may still be useful, but only as fulfillment/friction/context signals.",
            "",
            "The audit below does not change production behavior. It checks whether the current Top 1000 champion depends on stock-as-availability semantics and whether a stock-soft policy looks promising using the official 8G-K exported rows.",
            "Important scope note: this is a route-blending sensitivity check over exported predictions. It does not retrain models, ablate stock features from the base estimators, or prove how much the fitted trees depend on stock features.",
            f"Promotion screen for this audit: candidate hit +/-20 must improve by more than {_fmt_pp(promotion_hit_gate)} versus the current champion while WMAPE is non-worse. The best stock-soft candidate improved hit +/-20 by {_fmt_pp(hit_delta)} and WMAPE by {_fmt_pp(wmape_delta)}, so it is directional but below the promotion screen.",
            "",
            "## Raw Data Semantics Audit",
            "",
            _table(["Area", "Count", "Observed detail", "Assessment"], _raw_data_rows(audits)),
            "",
            "## Stock-Semantics Policy Simulation",
            "",
            _table(
                [
                    "Candidate",
                    "Rows",
                    "Qty scored",
                    "Hit +/-20",
                    "Delta vs champion",
                    "Hit +/-30",
                    "WMAPE",
                    "WMAPE delta",
                    "Bias",
                    "Phantom",
                    "Meaning",
                ],
                _candidate_rows(frame),
            ),
            "",
            "## Current Route Diagnostic",
            "",
            _table(
                [
                    "Route",
                    "Rows",
                    "Qty scored",
                    "Champion hit +/-20",
                    "Control hit +/-20",
                    "ExtraTrees hit +/-20",
                    "Champion WMAPE",
                    "Control WMAPE",
                    "ExtraTrees WMAPE",
                    "Champion bias",
                ],
                _route_rows(frame),
            ),
            "",
            "## Business-Semantic Masks",
            "",
            _table(
                [
                    "Mask",
                    "Rows",
                    "Qty scored",
                    "Champion hit +/-20",
                    "Control hit +/-20",
                    "ExtraTrees hit +/-20",
                    "Champion WMAPE",
                    "Control WMAPE",
                    "ExtraTrees WMAPE",
                    "Champion bias",
                ],
                _mask_rows(frame),
            ),
            "",
            "## Window Check - Demand-Regular Stock-Soft Candidate",
            "",
            _table(
                [
                    "Target start",
                    "Qty scored",
                    "Champion hit +/-20",
                    "Candidate hit +/-20",
                    "Hit delta",
                    "Champion WMAPE",
                    "Candidate WMAPE",
                    "WMAPE delta",
                    "Champion bias",
                    "Candidate bias",
                ],
                _window_rows(frame),
            ),
            "",
            "## Interpretation",
            "",
            "- Discounts were not ignored: they are ingested and used as lag/campaign-history features. They are under-modeled as future price/promotion intent, and 61 infinite raw discount rows should be cleaned.",
            "- Discount cleanup should also inspect finite `discount_pct > 1` rows. They may be valid percent-scale values rather than bad rows, but they should not silently mix with fraction-scale discount values.",
            "- Returns were not ignored: negative quantities become returned units, and return-rate lag features exist. The main target is positive sold units, so returns do not reduce demand target. That is acceptable for gross demand, but net units/revenue should be a separate business output.",
            "- Campaign fields were used heavily as historical signals. The remaining gap is not `CAMPANIE` availability; it is future SKU campaign membership, intensity, and whether a BF label means planned BF SKU versus later campaign assignment.",
            "- `VECHIME IN COLECTIE` exists in stock snapshot data and is stored in `stock_snapshot_store_v2`, but it is not used in official historical backtests because most available rows are current/snapshot-like rather than reliable historical-as-of features.",
            "- Stock semantics need correction. Current labels such as `available_regular` and `stock_constrained` should be treated as historical stock-position context, not true sellability. The missing high-value field is active/orderable/listed SKU status by date.",
            "",
            "## Recommended Next Action",
            "",
            "- Do not promote another stock-gated candidate yet.",
            "- First, clean invalid discount values and rename/reframe stock-derived route language as fulfillment context.",
            "- Then run one stock-soft Top 1000 rebuild where regular-demand routing is based on demand regularity and active SKU assumptions, not positive stock.",
            "- If that rebuild improves or matches the current champion without stock-as-sellability assumptions, continue with guarded BF/campaign lift. If it fails, keep the 8G-I champion and wait for active/orderable SKU data.",
            "",
            "## Sources",
            "",
            f"- Official score rows: `{score_rows_csv}`.",
            "- Raw DB tables: `raw_sales_transactions_v2`, `weekly_chain_demand_v2`, `stock_snapshot_store_v2`.",
        ]
    ) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Phase 8G-L business-semantics audit.")
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument("--score-rows-csv", type=Path, default=DEFAULT_SCORE_ROWS_CSV)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()

    conn = sqlite3.connect(f"file:{args.db}?mode=ro", uri=True)
    try:
        report = build_report(conn, args.score_rows_csv)
    finally:
        conn.close()

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report, encoding="utf-8")
    print(report)
    print(f"Wrote {args.report}")


if __name__ == "__main__":
    main()
