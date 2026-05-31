"""Phase 8G-C campaign-field audit for forecast engine v2.

This audit adds and checks forecast-time-safe campaign history features built
from CAMPANIE / CAMPANIE BF raw fields. It does not train or score a new model.
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from .feature_matrix import DEFAULT_TARGET_STARTS, build_feature_matrix
    from .route_labels import add_route_labels
    from .scorecard import DB_PATH, ScorecardConfig
except ImportError:  # Allows direct script execution.
    from feature_matrix import DEFAULT_TARGET_STARTS, build_feature_matrix
    from route_labels import add_route_labels
    from scorecard import DB_PATH, ScorecardConfig


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REPORT = PROJECT_ROOT / "active_docs" / "ITER5R_V2_PHASE8G_CAMPAIGN_FIELD_AUDIT.md"

REVENUE_SCOPES = [
    ("top_100", 100),
    ("top_500", 500),
    ("top_1000", 1000),
]

REGULAR_ROUTES = {"available_regular", "proxy_available_regular"}


def _fmt_pct(value: object) -> str:
    if value is None or pd.isna(value):
        return "-"
    return f"{float(value) * 100:.1f}%"


def _fmt_num(value: object, digits: int = 1) -> str:
    if value is None or pd.isna(value):
        return "-"
    return f"{float(value):,.{digits}f}"


def _fmt_int(value: object) -> str:
    if value is None or pd.isna(value):
        return "-"
    return f"{int(value):,}"


def _table(headers: list[str], rows: list[list[str]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(lines)


def _scope_label(scope_name: str) -> str:
    return {
        "top_100": "Top 100",
        "top_500": "Top 500",
        "top_1000": "Top 1000",
        "top_5000": "Top 5000",
        "full_headline": "Full headline",
    }.get(scope_name, scope_name)


def _scope_mask(rows: pd.DataFrame, rank_limit: int | None) -> pd.Series:
    if rank_limit is None:
        return pd.Series(True, index=rows.index)
    return pd.to_numeric(rows["revenue_rank"], errors="coerce") <= rank_limit


def _safe_ratio(num: float, denom: float) -> float | None:
    if abs(float(denom)) <= 1e-9:
        return None
    return float(num) / float(denom)


def _scored_target_starts(target_starts: list[str], min_train_windows: int) -> list[str]:
    ordered = sorted(target_starts, key=lambda value: pd.Timestamp(value))
    return ordered[min_train_windows:]


def _raw_group_rows(
    conn: sqlite3.Connection,
    column_name: str,
    range_start: str,
    range_end: str,
    limit: int = 20,
) -> list[list[str]]:
    query = f"""
        SELECT
            COALESCE(NULLIF(TRIM(CAST({column_name} AS TEXT)), ''), '(blank)') AS value,
            COUNT(*) AS row_count,
            SUM(net_units) AS net_units,
            SUM(net_revenue) AS net_revenue,
            MIN(sale_date) AS first_date,
            MAX(sale_date) AS last_date
        FROM raw_sales_transactions_v2
        WHERE is_non_product = 0
            AND sale_date >= ?
            AND sale_date < ?
        GROUP BY value
        ORDER BY row_count DESC
        LIMIT ?
    """
    rows = pd.read_sql_query(query, conn, params=(range_start, range_end, limit))
    return [
        [
            str(row["value"]),
            _fmt_int(row["row_count"]),
            _fmt_num(row["net_units"]),
            _fmt_num(row["net_revenue"], 0),
            str(row["first_date"]),
            str(row["last_date"]),
        ]
        for _, row in rows.iterrows()
    ]


def _scope_feature_rows(matrix: pd.DataFrame) -> list[list[str]]:
    rows: list[list[str]] = []
    for scope_name, rank_limit in REVENUE_SCOPES:
        scoped = matrix[_scope_mask(matrix, rank_limit)].copy()
        if scoped.empty:
            continue
        hist_units = float(scoped["pos_units_13w"].sum())
        hist_revenue = float(scoped["revenue_13w"].sum())
        campaign_units = float(scoped["campaign_units_13w"].sum())
        campaign_revenue = float(scoped["campaign_revenue_13w"].sum())
        non_bf_campaign_units = float(scoped["non_bf_campaign_units_13w"].sum())
        campaign_rows = scoped[scoped["campaign_txn_13w"] > 0]
        rows.append(
            [
                _scope_label(scope_name),
                _fmt_int(len(scoped)),
                _fmt_int(scoped["sku_id"].nunique()),
                _fmt_num(scoped["actual_net_revenue_4w"].sum(), 0),
                _fmt_num(scoped["actual_pos_units_4w"].sum()),
                _fmt_pct(len(campaign_rows) / len(scoped)),
                _fmt_pct(float((scoped["non_bf_campaign_txn_13w"] > 0).mean())),
                _fmt_pct(float((scoped["bf_txn_13w"] > 0).mean())),
                _fmt_pct(float((scoped["days_since_campaign_txn"] <= 28).mean())),
                _fmt_pct(_safe_ratio(campaign_units, hist_units)),
                _fmt_pct(_safe_ratio(non_bf_campaign_units, hist_units)),
                _fmt_pct(_safe_ratio(campaign_revenue, hist_revenue)),
                _fmt_pct(campaign_rows["avg_campaign_discount_13w"].mean() if not campaign_rows.empty else None),
                _fmt_pct(campaign_rows["max_campaign_discount_13w"].max() if not campaign_rows.empty else None),
            ]
        )
    return rows


def _target_campaign_bucket(row: pd.Series) -> str:
    if row.get("bf_observed_txn_count", 0) > 0:
        return "bf_observed"
    if row.get("bf_inferred_txn_count", 0) > 0:
        return "bf_inferred"
    if row.get("unknown_campaign_label_txn_count", 0) > 0:
        return "unknown_campaign_label"
    if row.get("campaign_observed_txn_count", 0) > 0:
        return "campaign_observed_non_bf"
    return "non_campaign"


def _target_bucket_rows(matrix: pd.DataFrame, rank_limit: int = 1000) -> list[list[str]]:
    scoped = matrix[_scope_mask(matrix, rank_limit)].copy()
    if scoped.empty:
        return []
    scoped["target_campaign_bucket"] = scoped.apply(_target_campaign_bucket, axis=1)
    total_rows = len(scoped)
    total_revenue = float(scoped["actual_net_revenue_4w"].sum())
    rows: list[list[str]] = []
    for bucket, group in scoped.groupby("target_campaign_bucket", dropna=False):
        revenue = float(group["actual_net_revenue_4w"].sum())
        rows.append(
            [
                str(bucket),
                _fmt_int(len(group)),
                _fmt_pct(len(group) / total_rows),
                _fmt_num(revenue, 0),
                _fmt_pct(_safe_ratio(revenue, total_revenue)),
                _fmt_num(group["actual_pos_units_4w"].sum()),
                _fmt_pct(float((group["campaign_txn_13w"] > 0).mean())),
                _fmt_pct(float((group["days_since_campaign_txn"] <= 28).mean())),
            ]
        )
    return sorted(rows, key=lambda row: float(row[2].strip("%")) if row[2] != "-" else -1, reverse=True)


def _route_rows(matrix: pd.DataFrame) -> list[list[str]]:
    if "primary_route" not in matrix.columns:
        return []
    rows: list[list[str]] = []
    for route, group in matrix.groupby("primary_route", dropna=False):
        if group.empty:
            continue
        rows.append(
            [
                str(route),
                _fmt_int(len(group)),
                _fmt_int(group["sku_id"].nunique()),
                _fmt_num(group["actual_net_revenue_4w"].sum(), 0),
                _fmt_pct(float((group["campaign_txn_13w"] > 0).mean())),
                _fmt_pct(float((group["non_bf_campaign_txn_13w"] > 0).mean())),
                _fmt_pct(float((group["days_since_campaign_txn"] <= 28).mean())),
                _fmt_pct(_safe_ratio(float(group["campaign_units_13w"].sum()), float(group["pos_units_13w"].sum()))),
            ]
        )
    return sorted(rows, key=lambda row: int(row[1].replace(",", "")), reverse=True)


def _top_campaign_sku_rows(matrix: pd.DataFrame, limit: int = 25) -> list[list[str]]:
    top1000 = matrix[_scope_mask(matrix, 1000)].copy()
    if top1000.empty:
        return []
    grouped = (
        top1000.groupby(["sku_id", "category_norm", "product_family_v2"], dropna=False)
        .agg(
            rows=("sku_id", "size"),
            revenue_rank=("revenue_rank", "min"),
            actual_revenue=("actual_net_revenue_4w", "sum"),
            actual_units=("actual_pos_units_4w", "sum"),
            hist_units=("pos_units_13w", "sum"),
            campaign_units=("campaign_units_13w", "sum"),
            non_bf_campaign_units=("non_bf_campaign_units_13w", "sum"),
            campaign_txn=("campaign_txn_13w", "sum"),
            recent_campaign_rows=("days_since_campaign_txn", lambda s: int((s <= 28).sum())),
        )
        .reset_index()
    )
    grouped["campaign_unit_share"] = np.where(
        grouped["hist_units"].abs() > 1e-9,
        grouped["campaign_units"] / grouped["hist_units"],
        0.0,
    )
    grouped = grouped.sort_values(["campaign_units", "actual_revenue"], ascending=False).head(limit)
    return [
        [
            str(row["sku_id"]),
            _fmt_num(row["revenue_rank"], 0),
            str(row["category_norm"]),
            str(row["product_family_v2"]),
            _fmt_int(row["rows"]),
            _fmt_num(row["actual_revenue"], 0),
            _fmt_num(row["actual_units"]),
            _fmt_num(row["campaign_units"]),
            _fmt_num(row["non_bf_campaign_units"]),
            _fmt_pct(row["campaign_unit_share"]),
            _fmt_num(row["campaign_txn"], 0),
            _fmt_int(row["recent_campaign_rows"]),
        ]
        for _, row in grouped.iterrows()
    ]


def run_audit(
    conn: sqlite3.Connection,
    target_starts: list[str],
    min_train_windows: int,
    revenue_rank_limit: int,
    config: ScorecardConfig | None = None,
) -> tuple[pd.DataFrame, dict[str, list[list[str]]], list[str]]:
    config = config or ScorecardConfig()
    scored_starts = _scored_target_starts(target_starts, min_train_windows)
    if not scored_starts:
        return pd.DataFrame(), {}, scored_starts
    frames: list[pd.DataFrame] = []
    for target_start in scored_starts:
        print(f"Building campaign audit matrix for {target_start}...", file=sys.stderr, flush=True)
        frames.append(
            build_feature_matrix(
                conn,
                target_starts=[target_start],
                population="headline",
                config=config,
                revenue_rank_limit=revenue_rank_limit,
            )
        )
    matrix = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    matrix = add_route_labels(matrix)
    print("Building raw campaign summaries...", file=sys.stderr, flush=True)
    raw_range_start = (pd.Timestamp(scored_starts[0]) - pd.Timedelta(weeks=52)).strftime("%Y-%m-%d")
    raw_range_end = scored_starts[-1]
    raw_specs = {
        "campaign_status": "campaign_signal_status",
        "campaign_source": "campaign_signal_source",
        "bf_status": "bf_signal_status",
        "bf_source": "bf_signal_source",
        "campaign_raw": "campaign_raw",
        "campaign_bf_raw": "campaign_bf_raw",
    }
    raw_tables = {}
    for table_name, column_name in raw_specs.items():
        print(f"Summarizing raw {column_name}...", file=sys.stderr, flush=True)
        raw_tables[table_name] = _raw_group_rows(conn, column_name, raw_range_start, raw_range_end)
    return matrix, raw_tables, scored_starts


def build_report(matrix: pd.DataFrame, raw_tables: dict[str, list[list[str]]], scored_starts: list[str]) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if matrix.empty:
        return "\n".join(
            [
                "# Iteration 5R - Forecast V2 Phase 8G-C Campaign Field Audit",
                "",
                f"Generated: {now}",
                "",
                "## Verdict",
                "",
                "- No scored target windows were available for this audit configuration.",
                "- Increase `--target-start` count or lower `--min-train-windows`.",
            ]
        ) + "\n"
    top1000 = matrix[_scope_mask(matrix, 1000)].copy()
    clean_top1000 = top1000[
        top1000["primary_route"].isin(REGULAR_ROUTES)
        & (top1000["calendar_route_context"] == "normal_calendar")
    ]
    clean_campaign_rate = float((clean_top1000["campaign_txn_13w"] > 0).mean()) if not clean_top1000.empty else None

    return "\n".join(
        [
            "# Iteration 5R - Forecast V2 Phase 8G-C Campaign Field Audit",
            "",
            f"Generated: {now}",
            "",
            "## Verdict",
            "",
            "- Phase 8G-C is implemented as forecast-time-safe campaign history features, not target-window campaign leakage.",
            "- CAMPANIE / CAMPANIE BF fields are useful now as historical SKU behavior: recent campaign exposure, BF exposure, campaign unit share, non-BF campaign share, and campaign discount memory.",
            "- Product/program labels are excluded from campaign exposure features and kept as a separate product-program signal.",
            "- Non-BF campaign features exclude rows flagged as BF campaigns, not just rows inside BF timing windows.",
            "- They do not fully solve future promotion uncertainty unless a future campaign calendar/assortment plan is supplied. Target-window campaign bucket remains diagnostic only.",
            f"- In the clean Top 1000 regular slice, { _fmt_pct(clean_campaign_rate) } of rows still have campaign history in the previous 13 weeks, so the 32.3% 8G-A win is not a campaign-free problem.",
            "",
            "## Feature Coverage By Revenue Scope",
            "",
            _table(
                [
                    "Scope",
                    "Rows",
                    "SKUs",
                    "Actual revenue",
                    "Actual units",
                    "Any campaign 13w",
                    "Non-BF campaign 13w",
                    "BF txn 13w",
                    "Campaign <=28d",
                    "Campaign unit share",
                    "Non-BF campaign unit share",
                    "Campaign revenue share",
                    "Avg campaign discount",
                    "Max campaign discount",
                ],
                _scope_feature_rows(matrix),
            ),
            "",
            "## Top 1000 Target-Window Campaign Diagnostic",
            "",
            "This section uses actual target-window labels only to explain what the model is trying to hit. These labels are not used as predictive features.",
            "",
            _table(
                [
                    "Target bucket",
                    "Rows",
                    "Row share",
                    "Actual revenue",
                    "Revenue share",
                    "Actual units",
                    "Had campaign 13w",
                    "Campaign <=28d",
                ],
                _target_bucket_rows(matrix, rank_limit=1000),
            ),
            "",
            "## Route Coverage",
            "",
            _table(
                [
                    "Route",
                    "Rows",
                    "SKUs",
                    "Actual revenue",
                    "Any campaign 13w",
                    "Non-BF campaign 13w",
                    "Campaign <=28d",
                    "Campaign unit share",
                ],
                _route_rows(matrix),
            ),
            "",
            "## Top Top-1000 Campaign-Heavy SKUs",
            "",
            _table(
                [
                    "SKU",
                    "Revenue rank",
                    "Category",
                    "Family",
                    "Rows",
                    "Actual revenue",
                    "Actual units",
                    "Campaign units 13w",
                    "Non-BF campaign units 13w",
                    "Campaign unit share",
                    "Campaign txn 13w",
                    "Recent campaign rows",
                ],
                _top_campaign_sku_rows(matrix),
            ),
            "",
            "## Raw CAMPANIE Signal Status",
            "",
            _table(["Value", "Rows", "Net units", "Net revenue", "First date", "Last date"], raw_tables["campaign_status"]),
            "",
            "## Raw CAMPANIE Signal Source",
            "",
            _table(["Value", "Rows", "Net units", "Net revenue", "First date", "Last date"], raw_tables["campaign_source"]),
            "",
            "## Raw CAMPANIE BF Signal Status",
            "",
            _table(["Value", "Rows", "Net units", "Net revenue", "First date", "Last date"], raw_tables["bf_status"]),
            "",
            "## Raw CAMPANIE BF Signal Source",
            "",
            _table(["Value", "Rows", "Net units", "Net revenue", "First date", "Last date"], raw_tables["bf_source"]),
            "",
            "## Top Raw CAMPANIE Labels",
            "",
            _table(["Value", "Rows", "Net units", "Net revenue", "First date", "Last date"], raw_tables["campaign_raw"]),
            "",
            "## Top Raw CAMPANIE BF Labels",
            "",
            _table(["Value", "Rows", "Net units", "Net revenue", "First date", "Last date"], raw_tables["campaign_bf_raw"]),
            "",
            "## Notes",
            "",
            "- Forecast V2 only; no old-engine path is used.",
            f"- Scored target windows audited: {', '.join(scored_starts)}.",
            f"- Feature matrix rows audited: {len(matrix):,}.",
            f"- Max revenue rank audited: {_fmt_num(matrix['revenue_rank'].max(), 0) if not matrix.empty else '-'}.",
            "- Campaign history features query only raw sales where `sale_date < target_start`.",
            "- CAMPANIE BF duration remains represented through BF timing/window features; generic CAMPANIE labels become historical participation features.",
            "- Current snapshot rotation data remains excluded from historical backtests.",
        ]
    ) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run forecast v2 Phase 8G-C campaign-field audit.")
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--target-start", action="append", default=None)
    parser.add_argument("--min-train-windows", type=int, default=4)
    parser.add_argument("--revenue-rank-limit", type=int, default=1000)
    args = parser.parse_args()

    target_starts = args.target_start or DEFAULT_TARGET_STARTS
    config = ScorecardConfig()
    conn = sqlite3.connect(args.db)
    try:
        matrix, raw_tables, scored_starts = run_audit(
            conn,
            target_starts=target_starts,
            min_train_windows=args.min_train_windows,
            revenue_rank_limit=args.revenue_rank_limit,
            config=config,
        )
    finally:
        conn.close()

    report = build_report(matrix, raw_tables, scored_starts)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report, encoding="utf-8")
    print(report)
    print(f"Wrote {args.report}")


if __name__ == "__main__":
    main()
