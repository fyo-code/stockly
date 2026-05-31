"""Phase 7E target cleanup and data action audit for forecast engine v2."""

from __future__ import annotations

import argparse
import sqlite3
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from .analog_model_candidates import CONTROL_MODEL, run_analog_candidates
    from .feature_matrix import DEFAULT_TARGET_STARTS
    from .route_labels import ROUTE_ORDER, ROUTE_VERSION
    from .scorecard import DB_PATH, ScorecardConfig
except ImportError:  # Allows direct script execution.
    from analog_model_candidates import CONTROL_MODEL, run_analog_candidates
    from feature_matrix import DEFAULT_TARGET_STARTS
    from route_labels import ROUTE_ORDER, ROUTE_VERSION
    from scorecard import DB_PATH, ScorecardConfig


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REPORT = PROJECT_ROOT / "active_docs" / "ITER5I_V2_TARGET_CLEANUP_AUDIT.md"

ARTIFACT_TOKENS = (
    "PALET",
    "TRANSPORT",
    "LIVRARE",
    "MONTAJ",
    "AMBAL",
    "SERVICI",
    "TAXA",
    "GARANTIE",
    "AVANS",
)
CAMPAIGN_ROUTES = {"bf_campaign_sensitive", "seasonal_active", "seasonal_quiet"}
AVAILABILITY_GAP_VALUES = {"proxy_available", "stock_unobserved", "availability_unknown"}
LIFECYCLE_ROUTES = {"sparse_intermittent", "lifecycle_decline", "stock_constrained"}


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


def _metrics(group: pd.DataFrame) -> dict[str, object]:
    scored = group[group["quantity_scored"] == 1]
    actual_sum = float(scored["actual_units"].sum())
    zero_actual = group[group["actual_units"] == 0]
    return {
        "rows": int(len(group)),
        "scored": int(len(scored)),
        "actual_units": actual_sum,
        "pred_units": float(scored["pred_units"].sum()) if not scored.empty else 0.0,
        "actual_revenue": float(group["actual_revenue"].sum()),
        "abs_error": float(scored["abs_error"].sum()),
        "hit20": float(scored["hit20"].mean()) if not scored.empty else None,
        "hit30": float(scored["hit30"].mean()) if not scored.empty else None,
        "wmape": float(scored["abs_error"].sum() / actual_sum) if actual_sum > 0 else None,
        "bias": float(scored["signed_error"].sum() / actual_sum) if actual_sum > 0 else None,
        "phantom_rate": float(zero_actual["phantom"].mean()) if len(zero_actual) else None,
        "under20_rate": float(scored["under20"].mean()) if not scored.empty else None,
        "over20_rate": float(scored["over20"].mean()) if not scored.empty else None,
    }


def _clean_text(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value).upper()


def _has_artifact_token(row: pd.Series) -> bool:
    text = " ".join(
        [
            _clean_text(row.get("sku_id")),
            _clean_text(row.get("category_norm")),
            _clean_text(row.get("product_family_v2")),
        ]
    )
    return any(token in text for token in ARTIFACT_TOKENS)


def _cleanup_label(row: pd.Series) -> str:
    if _has_artifact_token(row):
        return "artifact_or_non_retail_review"
    route = str(row.get("primary_route", ""))
    availability = str(row.get("availability_confidence", ""))
    under_signal = row.get("under20_rate", row.get("under20", 0.0))
    over_signal = row.get("over20_rate", row.get("over20", 0.0))
    if route in CAMPAIGN_ROUTES:
        return "campaign_calendar_required"
    if route in LIFECYCLE_ROUTES:
        return "lifecycle_or_stock_policy"
    if availability in AVAILABILITY_GAP_VALUES:
        return "stock_availability_required"
    if float(under_signal or 0.0) >= 0.50:
        return "underprediction_review"
    if float(over_signal or 0.0) >= 0.50:
        return "overprediction_review"
    return "keep_in_headline_benchmark"


def _recommended_action(label: str) -> str:
    return {
        "artifact_or_non_retail_review": "Confirm whether these are true sellable products; exclude from headline KPI if they are pallets/services/logistics artifacts.",
        "campaign_calendar_required": "Get campaign membership and exact campaign windows; model these separately from normal replenishment demand.",
        "lifecycle_or_stock_policy": "Separate lifecycle/stock-constrained demand from normal forecast misses; need first/last availability and collection status.",
        "stock_availability_required": "Get monthly store and supplier stock, reservations, receipts, and availability status for these SKU families.",
        "underprediction_review": "Check missing campaign, stock-in, or SKU-code-continuity signal; current model is too conservative here.",
        "overprediction_review": "Check discontinuation, stockout, campaign end, or one-off history; current model keeps demand alive too long.",
        "keep_in_headline_benchmark": "Keep in the current benchmark; this slice is not the main cleanup blocker.",
    }.get(label, "Review manually.")


def _data_needed(label: str) -> str:
    return {
        "artifact_or_non_retail_review": "product master type, service/logistics flags, SKU business owner",
        "campaign_calendar_required": "campaign calendar, SKU campaign membership, campaign start/end, discount mechanics",
        "lifecycle_or_stock_policy": "collection age, active/discontinued flag, first stock date, last stock date, monthly stock",
        "stock_availability_required": "store monthly stock, supplier monthly stock, reserved stock, NIR/receipts, replenishment orders",
        "underprediction_review": "campaign membership, receipts, store breadth, supplier stock, SKU predecessor/successor mapping",
        "overprediction_review": "discontinuation date, stockout status, campaign end, reserved/cancelled orders",
        "keep_in_headline_benchmark": "none beyond normal sales/detail fields",
    }.get(label, "manual review")


def _control_rows(score_rows: pd.DataFrame) -> pd.DataFrame:
    control = score_rows[score_rows["model_name"] == CONTROL_MODEL].copy()
    if control.empty:
        return control
    control["cleanup_label"] = control.apply(_cleanup_label, axis=1)
    control["error_direction"] = np.select(
        [
            control["quantity_scored"].eq(1) & control["hit20"].eq(1),
            control["quantity_scored"].eq(1) & control["under20"].eq(1),
            control["quantity_scored"].eq(1) & control["over20"].eq(1),
        ],
        ["hit_20", "under_by_20_plus", "over_by_20_plus"],
        default="not_quantity_scored_or_other",
    )
    return control


def _slice_rows(control: pd.DataFrame, group_col: str, order: list[str] | None = None) -> list[list[str]]:
    total_abs_error = float(control[control["quantity_scored"] == 1]["abs_error"].sum())
    total_revenue = float(control["actual_revenue"].sum())
    grouped = control.groupby(group_col, dropna=False)
    keys = list(grouped.groups)
    if order:
        keys = [key for key in order if key in grouped.groups] + [key for key in keys if key not in order]
    rows = []
    for key in keys:
        group = grouped.get_group(key)
        metrics = _metrics(group)
        rows.append(
            [
                str(key),
                f"{metrics['rows']:,}",
                f"{metrics['scored']:,}",
                _fmt_pct(metrics["actual_revenue"] / total_revenue if total_revenue else None),
                _fmt_pct(metrics["hit20"]),
                _fmt_pct(metrics["hit30"]),
                _fmt_pct(metrics["wmape"]),
                _fmt_pct(metrics["bias"]),
                _fmt_pct(metrics["phantom_rate"]),
                _fmt_pct(metrics["abs_error"] / total_abs_error if total_abs_error else None),
            ]
        )
    return rows


def _artifact_recheck(control: pd.DataFrame) -> dict[str, object]:
    artifact = control[control.apply(_has_artifact_token, axis=1)].copy()
    metrics = _metrics(artifact)
    total = _metrics(control)
    residual = control.drop(index=artifact.index)
    residual_metrics = _metrics(residual)
    return {
        "artifact": metrics,
        "residual": residual_metrics,
        "hit20_delta": None
        if total["hit20"] is None or residual_metrics["hit20"] is None
        else float(residual_metrics["hit20"]) - float(total["hit20"]),
    }


def _family_cleanup_rows(control: pd.DataFrame, limit: int = 25) -> list[list[str]]:
    scored = control[control["quantity_scored"] == 1].copy()
    if scored.empty:
        return []
    grouped = (
        scored.groupby(["product_family_v2", "category_norm"], as_index=False)
        .agg(
            rows=("sku_id", "size"),
            skus=("sku_id", "nunique"),
            windows=("target_start", "nunique"),
            actual_units=("actual_units", "sum"),
            pred_units=("pred_units", "sum"),
            actual_revenue=("actual_revenue", "sum"),
            abs_error=("abs_error", "sum"),
            hit20=("hit20", "mean"),
            hit30=("hit30", "mean"),
            under20_rate=("under20", "mean"),
            over20_rate=("over20", "mean"),
            primary_route=("primary_route", lambda s: s.mode().iloc[0] if not s.mode().empty else "unknown"),
            availability_confidence=(
                "availability_confidence",
                lambda s: s.mode().iloc[0] if not s.mode().empty else "unknown",
            ),
        )
        .sort_values("abs_error", ascending=False)
        .head(limit)
    )
    rows = []
    for _, row in grouped.iterrows():
        label = _cleanup_label(row)
        rows.append(
            [
                str(row["product_family_v2"]),
                str(row["category_norm"]),
                str(row["primary_route"]),
                str(row["availability_confidence"]),
                label,
                f"{int(row['skus']):,}",
                f"{int(row['rows']):,}",
                _fmt_num(row["actual_units"]),
                _fmt_num(row["pred_units"]),
                _fmt_num(row["abs_error"]),
                _fmt_pct(row["hit20"]),
                _fmt_pct(row["under20_rate"]),
                _fmt_pct(row["over20_rate"]),
            ]
        )
    return rows


def _sku_cleanup_rows(control: pd.DataFrame, limit: int = 40) -> list[list[str]]:
    scored = control[control["quantity_scored"] == 1].copy()
    if scored.empty:
        return []
    grouped = (
        scored.groupby("sku_id", as_index=False)
        .agg(
            rows=("target_start", "nunique"),
            actual_units=("actual_units", "sum"),
            pred_units=("pred_units", "sum"),
            actual_revenue=("actual_revenue", "sum"),
            abs_error=("abs_error", "sum"),
            hit20=("hit20", "mean"),
            under20_rate=("under20", "mean"),
            over20_rate=("over20", "mean"),
            primary_route=("primary_route", lambda s: s.mode().iloc[0] if not s.mode().empty else "unknown"),
            category_norm=("category_norm", lambda s: s.mode().iloc[0] if not s.mode().empty else "unknown"),
            product_family_v2=("product_family_v2", lambda s: s.mode().iloc[0] if not s.mode().empty else "unknown"),
            availability_confidence=(
                "availability_confidence",
                lambda s: s.mode().iloc[0] if not s.mode().empty else "unknown",
            ),
        )
        .sort_values("abs_error", ascending=False)
        .head(limit)
    )
    rows = []
    for _, row in grouped.iterrows():
        label = _cleanup_label(row)
        rows.append(
            [
                str(row["sku_id"]),
                str(row["product_family_v2"]),
                str(row["category_norm"]),
                str(row["primary_route"]),
                label,
                f"{int(row['rows'])}",
                _fmt_num(row["actual_units"]),
                _fmt_num(row["pred_units"]),
                _fmt_num(row["abs_error"]),
                _fmt_pct(row["hit20"]),
                _data_needed(label),
            ]
        )
    return rows


def _cube_checklist_rows() -> list[list[str]]:
    return [
        [
            "1",
            "`iz_audit_stoc_lunar_sc_mex`",
            "Monthly store stock by SKU/store/month",
            "SKU code, store, month/end date, stock qty/value, available qty if present",
        ],
        [
            "2",
            "`iz_audit_stoc_lunar_sc_fzmex`",
            "Monthly supplier/importer stock by SKU/month",
            "SKU code, supplier/importer, month/end date, stock qty/value, available qty",
        ],
        [
            "3",
            "`Stocuri Magazine_zile vechime`",
            "Store stock age and availability snapshot",
            "SKU code, store, stock qty, days in stock, collection age, available/reserved qty",
        ],
        [
            "4",
            "`Stocuri Importatori_zile vechime`",
            "Supplier stock age and supplier availability",
            "SKU code, supplier, available supplier stock, days in stock, collection age",
        ],
        [
            "5",
            "`Raport Comenzi` / `Raport Comenzi YTD`",
            "Order timing and order/invoice lag",
            "Order date, invoice date, status, SKU, store, quantity, cancellations/returns if available",
        ],
        [
            "6",
            "`DGA_YTD_VZ_MAG_SI_OUTLET` / `Vanzari Magazine Arhiva`",
            "Detailed sales history and campaign fields",
            "DATA COMANDA, DATA, SKU, store, campaign, campaign BF, discount, revenue, quantity",
        ],
        [
            "7",
            "`ART_RAP`",
            "Product master and SKU lifecycle",
            "SKU status, category/class/subclass, supplier, dimensions, collection/line age, active/discontinued flags",
        ],
        [
            "8",
            "`Comenzi Aprovizionare Furnizor vs Receptii` / `IZ_NIR_M10_ACH_CAT`",
            "Receipts and replenishment lead-time signals",
            "SKU, supplier, order date, receipt date, received qty, expected qty, store/warehouse destination",
        ],
        [
            "9",
            "`Articole rezervate`",
            "Reserved stock and demand already committed",
            "SKU, store, reserved qty/value, reservation/order date, status",
        ],
        [
            "10",
            "`Management Livrari`",
            "Delivery delay signal for invoice fallback noise",
            "SKU/order, delivery dates, delivery status, store, custom/long-lead indicators if present",
        ],
    ]


def _decision(control_metrics: dict[str, object], artifact_recheck: dict[str, object]) -> str:
    residual_metrics = artifact_recheck["residual"]
    if residual_metrics["hit20"] is not None and float(residual_metrics["hit20"]) < 0.40:
        return (
            "Phase 7E confirms that target cleanup alone is not enough to unlock the model. "
            "Even after removing obvious artifact-token candidates, the hit +/-20 slice stays below 40%, "
            "so the next real step is data acquisition: stock, campaign membership/calendar, SKU lifecycle, and receipts."
        )
    if control_metrics["hit20"] is not None and float(control_metrics["hit20"]) < 0.40:
        return (
            "Target cleanup materially helps, but the current headline definition still needs formal business exclusions "
            "before the result can be treated as the main KPI."
        )
    return "The cleaned target slice is strong enough to resume model-candidate work."


def build_report(score_rows: pd.DataFrame, skipped: list[str], target_starts: list[str], k_neighbors: int) -> str:
    control = _control_rows(score_rows)
    if control.empty:
        return "\n".join(
            [
                "# Iteration 5I — V2 Target Cleanup Audit",
                "",
                f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                f"Route version: `{ROUTE_VERSION}`",
                "",
                "Accuracy rerun: no scorable control rows.",
                "",
            ]
        )

    control_metrics = _metrics(control)
    artifact_recheck = _artifact_recheck(control)
    artifact_metrics = artifact_recheck["artifact"]
    residual_metrics = artifact_recheck["residual"]
    decision = _decision(control_metrics, artifact_recheck)

    return "\n".join(
        [
            "# Iteration 5I — V2 Target Cleanup Audit",
            "",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"Route version: `{ROUTE_VERSION}`",
            "",
            "## Phase Checkpoint",
            "",
            "Phase completed: Phase 7E — Target cleanup and data action checklist",
            "",
            "What changed: no production model behavior changed. This phase reuses the current control predictions and classifies the biggest error groups into cleanup/data-action buckets.",
            "",
            f"Accuracy rerun: diagnostic only. Rebuilt the Phase 7C/7D measurement set using `{k_neighbors}` analog neighbors, then evaluated the unchanged control model.",
            "",
            _table(
                ["Metric", "Current headline control", "After artifact-token review only", "Delta"],
                [
                    ["Model", CONTROL_MODEL, CONTROL_MODEL, "-"],
                    ["Qty scored", f"{control_metrics['scored']:,}", f"{residual_metrics['scored']:,}", "-"],
                    [
                        "Hit +/-20",
                        _fmt_pct(control_metrics["hit20"]),
                        _fmt_pct(residual_metrics["hit20"]),
                        _fmt_pp(artifact_recheck["hit20_delta"]),
                    ],
                    ["Hit +/-30", _fmt_pct(control_metrics["hit30"]), _fmt_pct(residual_metrics["hit30"]), "-"],
                    ["WMAPE", _fmt_pct(control_metrics["wmape"]), _fmt_pct(residual_metrics["wmape"]), "-"],
                    ["Phantom rate", _fmt_pct(control_metrics["phantom_rate"]), _fmt_pct(residual_metrics["phantom_rate"]), "-"],
                ],
            ),
            "",
            "## Artifact-Token Candidate Impact",
            "",
            "This is not an automatic exclusion. It flags rows whose SKU/family/category text looks operational or non-retail, especially pallet/service/logistics-like items.",
            "",
            _table(
                ["Slice", "Rows", "Qty scored", "Actual units", "Abs error", "Hit +/-20", "WMAPE", "Phantom rate"],
                [
                    [
                        "artifact_token_candidates",
                        f"{artifact_metrics['rows']:,}",
                        f"{artifact_metrics['scored']:,}",
                        _fmt_num(artifact_metrics["actual_units"]),
                        _fmt_num(artifact_metrics["abs_error"]),
                        _fmt_pct(artifact_metrics["hit20"]),
                        _fmt_pct(artifact_metrics["wmape"]),
                        _fmt_pct(artifact_metrics["phantom_rate"]),
                    ],
                    [
                        "remaining_headline",
                        f"{residual_metrics['rows']:,}",
                        f"{residual_metrics['scored']:,}",
                        _fmt_num(residual_metrics["actual_units"]),
                        _fmt_num(residual_metrics["abs_error"]),
                        _fmt_pct(residual_metrics["hit20"]),
                        _fmt_pct(residual_metrics["wmape"]),
                        _fmt_pct(residual_metrics["phantom_rate"]),
                    ],
                ],
            ),
            "",
            "## Cleanup Bucket Summary",
            "",
            _table(
                [
                    "Cleanup bucket",
                    "Rows",
                    "Qty scored",
                    "Revenue share",
                    "Hit +/-20",
                    "Hit +/-30",
                    "WMAPE",
                    "Bias",
                    "Phantom rate",
                    "Abs error share",
                ],
                _slice_rows(
                    control,
                    "cleanup_label",
                    [
                        "artifact_or_non_retail_review",
                        "campaign_calendar_required",
                        "stock_availability_required",
                        "lifecycle_or_stock_policy",
                        "underprediction_review",
                        "overprediction_review",
                        "keep_in_headline_benchmark",
                    ],
                ),
            ),
            "",
            "## Route Summary",
            "",
            _table(
                [
                    "Route",
                    "Rows",
                    "Qty scored",
                    "Revenue share",
                    "Hit +/-20",
                    "Hit +/-30",
                    "WMAPE",
                    "Bias",
                    "Phantom rate",
                    "Abs error share",
                ],
                _slice_rows(control, "primary_route", ROUTE_ORDER),
            ),
            "",
            "## Top Family Cleanup List",
            "",
            _table(
                [
                    "Family",
                    "Category",
                    "Route",
                    "Availability",
                    "Cleanup bucket",
                    "SKUs",
                    "Rows",
                    "Actual units",
                    "Pred units",
                    "Abs error",
                    "Hit +/-20",
                    "Under >20",
                    "Over >20",
                ],
                _family_cleanup_rows(control),
            ),
            "",
            "## Top SKU Cleanup List",
            "",
            _table(
                [
                    "SKU",
                    "Family",
                    "Category",
                    "Route",
                    "Cleanup bucket",
                    "Windows",
                    "Actual units",
                    "Pred units",
                    "Abs error",
                    "Hit +/-20",
                    "Data needed",
                ],
                _sku_cleanup_rows(control),
            ),
            "",
            "## Pentaho Data Checklist",
            "",
            _table(["Priority", "Cube", "Why it matters", "Must-have fields"], _cube_checklist_rows()),
            "",
            "## KPI Treatment Recommendation",
            "",
            "- Keep the current headline control as the continuity benchmark until exclusions are approved.",
            "- Create a separate `artifact_or_non_retail_review` slice; do not silently remove it.",
            "- Report BF/campaign-sensitive demand separately until actual campaign calendars and membership are available.",
            "- Treat stock-unobserved and proxy-available rows as lower-confidence forecast rows, not proof of model failure or model success.",
            "- Main future KPI should become available forecastable retail SKU demand, with excluded/censored volume reported beside it.",
            "",
            "## Decision",
            "",
            decision,
            "",
            "## Skipped Windows",
            "",
            ", ".join(f"`{window}`" for window in skipped) if skipped else "None.",
            "",
            "## Notes",
            "",
            f"- Requested target windows: {', '.join(target_starts)}.",
            "- Artifact-token logic is deliberately conservative and only uses SKU/family/category text. It is a review queue, not a final rule.",
            "- Snapshot stock files remain excluded from historical training unless they carry valid historical as-of dates.",
            "- Next model work should wait until the top cleanup buckets are resolved or the requested Pentaho stock/campaign/lifecycle data is loaded.",
            "",
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run forecast v2 target cleanup and data action audit.")
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--target-start", action="append", default=None)
    parser.add_argument("--min-train-windows", type=int, default=4)
    parser.add_argument("--random-state", type=int, default=42)
    parser.add_argument("--k-neighbors", type=int, default=35)
    args = parser.parse_args()

    target_starts = args.target_start or DEFAULT_TARGET_STARTS
    config = ScorecardConfig()
    conn = sqlite3.connect(args.db)
    try:
        _, score_rows, _, skipped, _ = run_analog_candidates(
            conn,
            target_starts=target_starts,
            min_train_windows=args.min_train_windows,
            random_state=args.random_state,
            k_neighbors=args.k_neighbors,
            config=config,
        )
    finally:
        conn.close()

    report = build_report(score_rows, skipped, target_starts, args.k_neighbors)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report, encoding="utf-8")
    print(report)
    print(f"Wrote {args.report}")


if __name__ == "__main__":
    main()
