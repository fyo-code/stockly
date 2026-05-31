"""Phase 8G-B stock coverage audit for forecast engine v2.

This audit explains whether high-revenue V2 rows have usable historical store
and supplier stock context before target windows. It does not train or score a
new model.
"""

from __future__ import annotations

import argparse
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd

try:
    from .feature_matrix import DEFAULT_TARGET_STARTS, _previous_stock_months
    from .regime_labels import RULE_VERSION
    from .scorecard import DB_PATH
except ImportError:  # Allows direct script execution.
    from feature_matrix import DEFAULT_TARGET_STARTS, _previous_stock_months
    from regime_labels import RULE_VERSION
    from scorecard import DB_PATH


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REPORT = PROJECT_ROOT / "active_docs" / "ITER5Q_V2_PHASE8G_STOCK_COVERAGE_AUDIT.md"

REVENUE_SCOPES = [
    ("top_100", 100),
    ("top_500", 500),
    ("top_1000", 1000),
    ("top_5000", 5000),
    ("full_headline", None),
]


def _date(value: pd.Timestamp) -> str:
    return value.strftime("%Y-%m-%d")


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


def _scored_target_starts(target_starts: list[str], min_train_windows: int) -> list[str]:
    ordered = sorted(target_starts, key=lambda value: pd.Timestamp(value))
    return ordered[min_train_windows:]


def _load_labels(conn: sqlite3.Connection, target_starts: list[str]) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for target_start in target_starts:
        start = pd.Timestamp(target_start)
        as_of_week = _date(start - pd.Timedelta(weeks=1))
        labels = pd.read_sql_query(
            """
            SELECT
                sku_id,
                category_norm,
                product_family_v2,
                revenue_rank,
                revenue_bucket,
                volume_bucket,
                trailing_52w_revenue,
                trailing_52w_pos_units,
                avg_units_per_4w_52
            FROM forecast_v2_regime_labels
            WHERE as_of_week = ?
                AND rule_version = ?
                AND headline_eligible = 1
            """,
            conn,
            params=(as_of_week, RULE_VERSION),
        )
        labels["target_start"] = target_start
        labels["as_of_week"] = as_of_week
        labels["prev_stock_month"] = _previous_stock_months(target_start, months=1)[0]
        frames.append(labels)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def _load_store_prev(conn: sqlite3.Connection, months: list[str]) -> pd.DataFrame:
    if not months:
        return pd.DataFrame()
    placeholders = ", ".join("?" for _ in months)
    return pd.read_sql_query(
        f"""
        SELECT
            sku_id,
            stock_month AS prev_stock_month,
            SUM(stock_qty) AS store_prev_qty,
            COUNT(DISTINCT store_id) AS store_prev_stores_observed,
            COUNT(DISTINCT CASE WHEN stock_qty > 0 THEN store_id END) AS store_prev_stores_positive
        FROM stock_monthly_store_v2
        WHERE stock_month IN ({placeholders})
        GROUP BY sku_id, stock_month
        """,
        conn,
        params=months,
    )


def _load_supplier_prev(conn: sqlite3.Connection, months: list[str]) -> pd.DataFrame:
    if not months:
        return pd.DataFrame()
    placeholders = ", ".join("?" for _ in months)
    return pd.read_sql_query(
        f"""
        SELECT
            sku_id,
            stock_month AS prev_stock_month,
            SUM(supplier_stock_qty) AS supplier_prev_qty,
            COUNT(DISTINCT supplier_key) AS supplier_prev_suppliers_observed,
            COUNT(DISTINCT CASE WHEN supplier_stock_qty > 0 THEN supplier_key END) AS supplier_prev_suppliers_positive
        FROM stock_monthly_supplier_v2
        WHERE stock_month IN ({placeholders})
            AND mapping_confidence = 'exact_unique'
            AND sku_id IS NOT NULL
        GROUP BY sku_id, stock_month
        """,
        conn,
        params=months,
    )


def _load_store_history_to_cutoff(conn: sqlite3.Connection, labels: pd.DataFrame) -> pd.DataFrame:
    rows: list[pd.DataFrame] = []
    for target_start, group in labels.groupby("target_start"):
        prev_month = str(group["prev_stock_month"].iloc[0])
        skus = sorted(group["sku_id"].unique())
        if not skus:
            continue
        placeholders = ", ".join("?" for _ in skus)
        history = pd.read_sql_query(
            f"""
            SELECT
                sku_id,
                COUNT(DISTINCT stock_month) AS store_any_months,
                COUNT(DISTINCT store_id) AS store_any_stores,
                MIN(stock_month) AS store_first_month,
                MAX(stock_month) AS store_last_month,
                SUM(CASE WHEN stock_qty > 0 THEN 1 ELSE 0 END) AS store_positive_records
            FROM stock_monthly_store_v2
            WHERE stock_month <= ?
                AND sku_id IN ({placeholders})
            GROUP BY sku_id
            """,
            conn,
            params=[prev_month, *skus],
        )
        history["target_start"] = target_start
        rows.append(history)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def _load_supplier_history_to_cutoff(conn: sqlite3.Connection, labels: pd.DataFrame) -> pd.DataFrame:
    rows: list[pd.DataFrame] = []
    for target_start, group in labels.groupby("target_start"):
        prev_month = str(group["prev_stock_month"].iloc[0])
        skus = sorted(group["sku_id"].unique())
        if not skus:
            continue
        placeholders = ", ".join("?" for _ in skus)
        history = pd.read_sql_query(
            f"""
            SELECT
                sku_id,
                COUNT(DISTINCT stock_month) AS supplier_any_months,
                COUNT(DISTINCT supplier_key) AS supplier_any_suppliers,
                MIN(stock_month) AS supplier_first_month,
                MAX(stock_month) AS supplier_last_month,
                SUM(CASE WHEN supplier_stock_qty > 0 THEN 1 ELSE 0 END) AS supplier_positive_records
            FROM stock_monthly_supplier_v2
            WHERE stock_month <= ?
                AND mapping_confidence = 'exact_unique'
                AND sku_id IS NOT NULL
                AND sku_id IN ({placeholders})
            GROUP BY sku_id
            """,
            conn,
            params=[prev_month, *skus],
        )
        history["target_start"] = target_start
        rows.append(history)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def _load_actuals(conn: sqlite3.Connection, labels: pd.DataFrame) -> pd.DataFrame:
    rows: list[pd.DataFrame] = []
    for target_start in sorted(labels["target_start"].unique()):
        start = pd.Timestamp(target_start)
        end = start + pd.Timedelta(weeks=4)
        actuals = pd.read_sql_query(
            """
            SELECT
                sku_id,
                SUM(CASE WHEN net_units > 0 THEN net_units ELSE 0 END) AS actual_pos_units_4w,
                SUM(net_revenue) AS actual_net_revenue_4w
            FROM weekly_chain_demand_v2
            WHERE week_start >= ?
                AND week_start < ?
            GROUP BY sku_id
            """,
            conn,
            params=(_date(start), _date(end)),
        )
        actuals["target_start"] = target_start
        rows.append(actuals)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def _load_recent_store_sales(conn: sqlite3.Connection, labels: pd.DataFrame) -> pd.DataFrame:
    """Return recent store breadth for label rows.

    This is computed per target window so the audit can see whether SKUs with no
    store stock context still had store-level sales before the forecast date.
    """
    all_skus = sorted(labels["sku_id"].unique())
    if not all_skus:
        return pd.DataFrame()

    rows: list[pd.DataFrame] = []
    placeholders = ", ".join("?" for _ in all_skus)
    for target_start in sorted(labels["target_start"].unique()):
        start = pd.Timestamp(target_start)
        start_13 = start - pd.Timedelta(weeks=13)
        start_52 = start - pd.Timedelta(weeks=52)
        history = pd.read_sql_query(
            f"""
            SELECT
                sku_id,
                COUNT(DISTINCT CASE WHEN week_start >= ? AND net_units > 0 THEN store_id END) AS selling_stores_13w,
                COUNT(DISTINCT CASE WHEN net_units > 0 THEN store_id END) AS selling_stores_52w,
                SUM(CASE WHEN week_start >= ? AND net_units > 0 THEN net_units ELSE 0 END) AS store_pos_units_13w,
                SUM(CASE WHEN net_units > 0 THEN net_units ELSE 0 END) AS store_pos_units_52w
            FROM weekly_store_demand_v2
            WHERE week_start >= ?
                AND week_start < ?
                AND sku_id IN ({placeholders})
            GROUP BY sku_id
            """,
            conn,
            params=[_date(start_13), _date(start_13), _date(start_52), _date(start), *all_skus],
        )
        history["target_start"] = target_start
        rows.append(history)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def _load_source_files(conn: sqlite3.Connection) -> pd.DataFrame:
    return pd.read_sql_query(
        """
        SELECT
            file_name,
            source_kind,
            feature_scope,
            rows_seen,
            records_inserted,
            records_skipped,
            stores_seen,
            skus_seen,
            first_stock_month,
            last_stock_month
        FROM stock_source_files_v2
        ORDER BY source_kind, file_name
        """,
        conn,
    )


def _coverage_frame(conn: sqlite3.Connection, target_starts: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    labels = _load_labels(conn, target_starts)
    months = sorted(labels["prev_stock_month"].dropna().unique())
    store_prev = _load_store_prev(conn, months)
    supplier_prev = _load_supplier_prev(conn, months)
    store_any = _load_store_history_to_cutoff(conn, labels)
    supplier_any = _load_supplier_history_to_cutoff(conn, labels)
    actuals = _load_actuals(conn, labels)
    recent_sales = _load_recent_store_sales(conn, labels)

    frame = labels.merge(store_prev, on=["sku_id", "prev_stock_month"], how="left")
    frame = frame.merge(supplier_prev, on=["sku_id", "prev_stock_month"], how="left")
    frame = frame.merge(store_any, on=["sku_id", "target_start"], how="left")
    frame = frame.merge(supplier_any, on=["sku_id", "target_start"], how="left")
    frame = frame.merge(actuals, on=["sku_id", "target_start"], how="left")
    frame = frame.merge(recent_sales, on=["sku_id", "target_start"], how="left")

    frame["store_prev_observed"] = frame["store_prev_qty"].notna().astype(int)
    frame["supplier_prev_observed"] = frame["supplier_prev_qty"].notna().astype(int)

    numeric_cols = [
        "store_prev_qty",
        "store_prev_stores_observed",
        "store_prev_stores_positive",
        "supplier_prev_qty",
        "supplier_prev_suppliers_observed",
        "supplier_prev_suppliers_positive",
        "store_any_months",
        "store_any_stores",
        "store_positive_records",
        "supplier_any_months",
        "supplier_any_suppliers",
        "supplier_positive_records",
        "actual_pos_units_4w",
        "actual_net_revenue_4w",
        "selling_stores_13w",
        "selling_stores_52w",
        "store_pos_units_13w",
        "store_pos_units_52w",
    ]
    for col in numeric_cols:
        if col in frame.columns:
            frame[col] = pd.to_numeric(frame[col], errors="coerce").fillna(0.0)

    frame["store_prev_positive"] = (frame["store_prev_qty"].fillna(0.0) > 0).astype(int)
    frame["supplier_prev_positive"] = (frame["supplier_prev_qty"].fillna(0.0) > 0).astype(int)
    frame["combined_prev_observed"] = (
        (frame["store_prev_observed"] == 1) | (frame["supplier_prev_observed"] == 1)
    ).astype(int)
    frame["combined_prev_positive"] = (
        (frame["store_prev_positive"] == 1) | (frame["supplier_prev_positive"] == 1)
    ).astype(int)
    frame["store_any_observed"] = (frame["store_any_months"] > 0).astype(int)
    frame["supplier_any_observed"] = (frame["supplier_any_months"] > 0).astype(int)
    frame["sold_in_store_history"] = (frame["selling_stores_52w"] > 0).astype(int)

    source_files = _load_source_files(conn)
    return frame, source_files


def _coverage_metrics(rows: pd.DataFrame) -> dict[str, object]:
    total = int(len(rows))
    unique_skus = int(rows["sku_id"].nunique()) if total else 0

    def count(col: str) -> int:
        return int((rows[col] == 1).sum()) if total and col in rows.columns else 0

    def pct(col: str) -> float | None:
        return count(col) / total if total else None

    return {
        "rows": total,
        "unique_skus": unique_skus,
        "actual_revenue": float(rows["actual_net_revenue_4w"].sum()) if total else 0.0,
        "store_prev_observed": count("store_prev_observed"),
        "store_prev_observed_pct": pct("store_prev_observed"),
        "store_prev_positive": count("store_prev_positive"),
        "store_any_observed": count("store_any_observed"),
        "store_any_observed_pct": pct("store_any_observed"),
        "supplier_prev_observed": count("supplier_prev_observed"),
        "supplier_prev_observed_pct": pct("supplier_prev_observed"),
        "supplier_prev_positive": count("supplier_prev_positive"),
        "combined_prev_observed": count("combined_prev_observed"),
        "combined_prev_observed_pct": pct("combined_prev_observed"),
        "combined_prev_positive": count("combined_prev_positive"),
        "sold_no_store_prev": int(((rows["sold_in_store_history"] == 1) & (rows["store_prev_observed"] == 0)).sum())
        if total
        else 0,
    }


def _coverage_rows(frame: pd.DataFrame) -> list[list[str]]:
    rows: list[list[str]] = []
    for scope_name, rank_limit in REVENUE_SCOPES:
        scoped = frame[_scope_mask(frame, rank_limit)]
        metrics = _coverage_metrics(scoped)
        rows.append(
            [
                _scope_label(scope_name),
                _fmt_int(metrics["rows"]),
                _fmt_int(metrics["unique_skus"]),
                _fmt_num(metrics["actual_revenue"], 0),
                _fmt_int(metrics["store_prev_observed"]),
                _fmt_pct(metrics["store_prev_observed_pct"]),
                _fmt_int(metrics["store_prev_positive"]),
                _fmt_int(metrics["store_any_observed"]),
                _fmt_pct(metrics["store_any_observed_pct"]),
                _fmt_int(metrics["supplier_prev_observed"]),
                _fmt_pct(metrics["supplier_prev_observed_pct"]),
                _fmt_int(metrics["supplier_prev_positive"]),
                _fmt_int(metrics["combined_prev_observed"]),
                _fmt_pct(metrics["combined_prev_observed_pct"]),
                _fmt_int(metrics["sold_no_store_prev"]),
            ]
        )
    return rows


def _month_rows(frame: pd.DataFrame) -> list[list[str]]:
    rows: list[list[str]] = []
    top1000 = frame[_scope_mask(frame, 1000)].copy()
    for target_start, group in top1000.groupby("target_start"):
        metrics = _coverage_metrics(group)
        rows.append(
            [
                str(target_start),
                _fmt_int(metrics["rows"]),
                _fmt_int(metrics["unique_skus"]),
                _fmt_pct(metrics["store_prev_observed_pct"]),
                _fmt_pct(metrics["store_any_observed_pct"]),
                _fmt_pct(metrics["supplier_prev_observed_pct"]),
                _fmt_pct(metrics["combined_prev_observed_pct"]),
                _fmt_num(metrics["actual_revenue"], 0),
            ]
        )
    return rows


def _top_missing_rows(frame: pd.DataFrame, limit: int = 30) -> list[list[str]]:
    top1000 = frame[_scope_mask(frame, 1000) & (frame["store_prev_observed"] == 0)].copy()
    if top1000.empty:
        return []
    agg = (
        top1000.groupby(["sku_id", "category_norm", "product_family_v2"], dropna=False)
        .agg(
            windows=("target_start", "nunique"),
            best_rank=("revenue_rank", "min"),
            avg_rank=("revenue_rank", "mean"),
            avg_trailing_revenue=("trailing_52w_revenue", "mean"),
            actual_revenue=("actual_net_revenue_4w", "sum"),
            actual_units=("actual_pos_units_4w", "sum"),
            store_any_windows=("store_any_observed", "sum"),
            supplier_prev_windows=("supplier_prev_observed", "sum"),
            supplier_positive_windows=("supplier_prev_positive", "sum"),
            max_selling_stores_52w=("selling_stores_52w", "max"),
            max_store_units_52w=("store_pos_units_52w", "max"),
        )
        .reset_index()
        .sort_values(["actual_revenue", "avg_trailing_revenue"], ascending=[False, False])
        .head(limit)
    )
    rows: list[list[str]] = []
    for _, row in agg.iterrows():
        rows.append(
            [
                str(row["sku_id"]),
                str(row["category_norm"]),
                str(row["product_family_v2"]),
                _fmt_int(row["windows"]),
                _fmt_num(row["best_rank"], 0),
                _fmt_num(row["actual_revenue"], 0),
                _fmt_num(row["actual_units"]),
                _fmt_int(row["store_any_windows"]),
                _fmt_int(row["supplier_prev_windows"]),
                _fmt_int(row["supplier_positive_windows"]),
                _fmt_num(row["max_selling_stores_52w"], 0),
                _fmt_num(row["max_store_units_52w"]),
            ]
        )
    return rows


def _source_rows(source_files: pd.DataFrame) -> list[list[str]]:
    rows: list[list[str]] = []
    if source_files.empty:
        return rows
    for _, row in source_files.iterrows():
        rows.append(
            [
                str(row["file_name"]),
                str(row["source_kind"]),
                str(row["feature_scope"]),
                _fmt_int(row["rows_seen"]),
                _fmt_int(row["records_inserted"]),
                _fmt_int(row["records_skipped"]),
                _fmt_int(row["stores_seen"]),
                _fmt_int(row["skus_seen"]),
                str(row["first_stock_month"] or "-"),
                str(row["last_stock_month"] or "-"),
            ]
        )
    return rows


def _decision(frame: pd.DataFrame) -> str:
    top1000 = frame[_scope_mask(frame, 1000)]
    if top1000.empty:
        return "No top-1000 rows were available for this audit."
    metrics = _coverage_metrics(top1000)
    store_prev_pct = float(metrics["store_prev_observed_pct"] or 0.0)
    store_any_pct = float(metrics["store_any_observed_pct"] or 0.0)
    supplier_prev_pct = float(metrics["supplier_prev_observed_pct"] or 0.0)

    if store_prev_pct < 0.05 and supplier_prev_pct >= 0.50:
        return (
            "Do not block route-specific modeling on monthly store stock. For top-1000 revenue rows, "
            "store previous-month coverage is too weak, while supplier coverage is strong enough to remain "
            "the primary availability signal. Treat store stock as a narrow high-confidence signal and use 8G-B "
            "missing-SKU output to investigate mapping/source coverage separately."
        )
    if store_any_pct > store_prev_pct * 3 and store_prev_pct < 0.20:
        return (
            "Store stock exists for many high-revenue SKUs somewhere in history but is often missing in the "
            "previous completed month. Audit month coverage and source-file gaps before using store stock as a gate."
        )
    return (
        "Store stock has enough coverage to be used as a meaningful route feature, but supplier stock should still "
        "remain part of combined availability."
    )


def build_report(frame: pd.DataFrame, source_files: pd.DataFrame, target_starts: list[str]) -> str:
    top1000 = frame[_scope_mask(frame, 1000)]
    top1000_metrics = _coverage_metrics(top1000)
    return "\n".join(
        [
            "# Iteration 5Q - V2 Phase 8G-B Stock Coverage Audit",
            "",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            "## Phase Checkpoint",
            "",
            "Phase completed: Phase 8G-B - high-revenue store/supplier stock coverage audit.",
            "",
            "What changed: no model behavior changed. This report audits whether high-revenue V2 rows have usable historical store and supplier stock context.",
            "",
            f"Target windows audited: {', '.join(target_starts)}.",
            "",
            "## Executive Read",
            "",
            _table(
                ["Top-1000 metric", "Value"],
                [
                    ["Rows", _fmt_int(top1000_metrics["rows"])],
                    ["Unique SKUs", _fmt_int(top1000_metrics["unique_skus"])],
                    ["Store prev-month observed", _fmt_pct(top1000_metrics["store_prev_observed_pct"])],
                    ["Store any historical observed", _fmt_pct(top1000_metrics["store_any_observed_pct"])],
                    ["Supplier prev-month observed", _fmt_pct(top1000_metrics["supplier_prev_observed_pct"])],
                    ["Combined prev-month observed", _fmt_pct(top1000_metrics["combined_prev_observed_pct"])],
                    ["Rows with store sales history but no store prev-month stock", _fmt_int(top1000_metrics["sold_no_store_prev"])],
                ],
            ),
            "",
            "## Coverage By Revenue Scope",
            "",
            _table(
                [
                    "Scope",
                    "Rows",
                    "Unique SKUs",
                    "Actual target revenue",
                    "Store prev obs",
                    "Store prev obs %",
                    "Store prev positive",
                    "Store any obs",
                    "Store any obs %",
                    "Supplier prev obs",
                    "Supplier prev obs %",
                    "Supplier prev positive",
                    "Combined prev obs",
                    "Combined prev obs %",
                    "Sold stores/no store prev",
                ],
                _coverage_rows(frame),
            ),
            "",
            "## Top-1000 Coverage By Target Window",
            "",
            _table(
                [
                    "Target start",
                    "Rows",
                    "Unique SKUs",
                    "Store prev obs %",
                    "Store any obs %",
                    "Supplier prev obs %",
                    "Combined prev obs %",
                    "Actual target revenue",
                ],
                _month_rows(frame),
            ),
            "",
            "## Top High-Revenue SKUs Missing Prev-Month Store Stock",
            "",
            _table(
                [
                    "SKU",
                    "Category",
                    "Family",
                    "Windows",
                    "Best rank",
                    "Actual target revenue",
                    "Actual units",
                    "Store any windows",
                    "Supplier obs windows",
                    "Supplier positive windows",
                    "Max selling stores 52w",
                    "Max store units 52w",
                ],
                _top_missing_rows(frame),
            ),
            "",
            "## Stock Source Files",
            "",
            _table(
                [
                    "File",
                    "Kind",
                    "Scope",
                    "Rows seen",
                    "Records inserted",
                    "Records skipped",
                    "Stores",
                    "SKUs",
                    "First month",
                    "Last month",
                ],
                _source_rows(source_files),
            ),
            "",
            "## Decision Gate",
            "",
            _decision(frame),
            "",
            "## Notes",
            "",
            "- Forecast V2 only; no old-engine path is used.",
            "- Coverage uses the same scored target windows as Phase 8G-A by default.",
            "- Store stock coverage means an exact SKU/store/month row exists in `stock_monthly_store_v2` for the previous completed stock month.",
            "- Supplier coverage uses only `exact_unique` supplier product-name-to-SKU mappings.",
            "- Current rotation snapshots remain excluded from historical backtests.",
        ]
    ) + "\n"


def run_audit(
    conn: sqlite3.Connection,
    target_starts: list[str],
    min_train_windows: int,
) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    scored_starts = _scored_target_starts(target_starts, min_train_windows)
    frame, source_files = _coverage_frame(conn, scored_starts)
    return frame, source_files, scored_starts


def main() -> None:
    parser = argparse.ArgumentParser(description="Run forecast v2 Phase 8G-B stock coverage audit.")
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--target-start", action="append", default=None)
    parser.add_argument("--min-train-windows", type=int, default=4)
    args = parser.parse_args()

    target_starts = args.target_start or DEFAULT_TARGET_STARTS
    conn = sqlite3.connect(args.db)
    try:
        frame, source_files, scored_starts = run_audit(
            conn,
            target_starts=target_starts,
            min_train_windows=args.min_train_windows,
        )
    finally:
        conn.close()

    report = build_report(frame, source_files, scored_starts)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report, encoding="utf-8")
    print(report)
    print(f"Wrote {args.report}")


if __name__ == "__main__":
    main()
