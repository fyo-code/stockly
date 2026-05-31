"""Phase 8C monthly store stock ingestion for the new stock package."""

from __future__ import annotations

import argparse
import sqlite3
from datetime import datetime
from pathlib import Path

try:
    from .stock_ingestion import (
        DB_PATH,
        DEFAULT_TARGET_STARTS,
        StockImportStats,
        ensure_stock_tables,
        existing_sales_stores,
        import_monthly_file,
        monthly_stock_context_coverage,
        normalize_store,
        record_source_file,
    )
except ImportError:  # Allows direct script execution.
    from stock_ingestion import (
        DB_PATH,
        DEFAULT_TARGET_STARTS,
        StockImportStats,
        ensure_stock_tables,
        existing_sales_stores,
        import_monthly_file,
        monthly_stock_context_coverage,
        normalize_store,
        record_source_file,
    )


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = PROJECT_ROOT / "new_stock_data_20may"
DEFAULT_REPORT = PROJECT_ROOT / "active_docs" / "ITER5L_V2_PHASE8C_MONTHLY_STORE_STOCK.md"
PHASE_FILES = [
    "const_magazin_stock.csv",
    "iasi_magazin_stock.csv",
    "oradea_magazin_stock.csv",
]
PHASE_STORES = ["constanta", "iasi", "oradea"]
BASELINE_HIT20 = 0.241
BASELINE_HIT30 = 0.353
BASELINE_WMAPE = 0.561
BASELINE_PHANTOM = 0.481


def _fmt_num(value: object, digits: int = 1) -> str:
    if value is None:
        return "-"
    if isinstance(value, int):
        return f"{value:,}"
    try:
        return f"{float(value):,.{digits}f}"
    except (TypeError, ValueError):
        return str(value)


def _fmt_pct(value: object) -> str:
    if value is None:
        return "-"
    return f"{float(value) * 100:.1f}%"


def _table(headers: list[str], rows: list[list[str]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(lines)


def _source_keys(conn: sqlite3.Connection, path: Path) -> set[str]:
    keys = {str(path)}
    rows = conn.execute(
        "SELECT source_file FROM stock_source_files_v2 WHERE file_name = ?",
        (path.name,),
    ).fetchall()
    keys.update(str(row[0]) for row in rows)
    return keys


def _delete_previous_source_rows(conn: sqlite3.Connection, path: Path) -> int:
    deleted = 0
    for source_key in _source_keys(conn, path):
        before = conn.total_changes
        conn.execute("DELETE FROM stock_monthly_store_v2 WHERE source_file = ?", (source_key,))
        conn.execute("DELETE FROM stock_source_files_v2 WHERE source_file = ?", (source_key,))
        deleted += conn.total_changes - before
    return deleted


def _store_summary(conn: sqlite3.Connection, stores: list[str]) -> dict[str, dict[str, object]]:
    summary = {
        store: {
            "records": 0,
            "skus": 0,
            "months": 0,
            "first_month": None,
            "last_month": None,
            "zero_records": 0,
            "negative_records": 0,
            "stock_qty": None,
        }
        for store in stores
    }
    placeholders = ",".join("?" for _ in stores)
    rows = conn.execute(
        f"""
        SELECT
            store_id,
            COUNT(*) AS records,
            COUNT(DISTINCT sku_id) AS skus,
            COUNT(DISTINCT stock_month) AS months,
            MIN(stock_month) AS first_month,
            MAX(stock_month) AS last_month,
            SUM(CASE WHEN stock_qty = 0 THEN 1 ELSE 0 END) AS zero_records,
            SUM(CASE WHEN stock_qty < 0 THEN 1 ELSE 0 END) AS negative_records,
            SUM(stock_qty) AS stock_qty
        FROM stock_monthly_store_v2
        WHERE store_id IN ({placeholders})
        GROUP BY store_id
        """,
        stores,
    ).fetchall()
    for row in rows:
        summary[str(row[0])] = {
            "records": row[1] or 0,
            "skus": row[2] or 0,
            "months": row[3] or 0,
            "first_month": row[4],
            "last_month": row[5],
            "zero_records": row[6] or 0,
            "negative_records": row[7] or 0,
            "stock_qty": row[8],
        }
    return summary


def _total_stock_summary(conn: sqlite3.Connection) -> dict[str, object]:
    row = conn.execute(
        """
        SELECT
            COUNT(*) AS records,
            COUNT(DISTINCT sku_id) AS skus,
            COUNT(DISTINCT store_id) AS stores,
            COUNT(DISTINCT stock_month) AS months,
            MIN(stock_month) AS first_month,
            MAX(stock_month) AS last_month
        FROM stock_monthly_store_v2
        """
    ).fetchone()
    return {
        "records": row[0] or 0,
        "skus": row[1] or 0,
        "stores": row[2] or 0,
        "months": row[3] or 0,
        "first_month": row[4],
        "last_month": row[5],
    }


def _source_overlap_rows(conn: sqlite3.Connection, paths: list[Path]) -> list[list[str]]:
    sales_skus = {
        str(row[0])
        for row in conn.execute(
            """
            SELECT DISTINCT sku_id
            FROM raw_sales_transactions_v2
            WHERE sku_id IS NOT NULL AND is_non_product = 0
            """
        )
    }
    rows: list[list[str]] = []
    for path in paths:
        stock_skus = {
            str(row[0])
            for row in conn.execute(
                """
                SELECT DISTINCT sku_id
                FROM stock_monthly_store_v2
                WHERE source_file = ?
                """,
                (str(path),),
            )
        }
        overlap = len(stock_skus & sales_skus)
        rows.append(
            [
                path.name,
                _fmt_num(len(stock_skus), 0),
                _fmt_num(overlap, 0),
                _fmt_pct(overlap / len(stock_skus) if stock_skus else None),
            ]
        )
    return rows


def _import_rows(stats_by_path: list[tuple[Path, StockImportStats, int]]) -> list[list[str]]:
    rows: list[list[str]] = []
    for path, stats, deleted_rows in stats_by_path:
        rows.append(
            [
                path.name,
                _fmt_num(stats.rows_seen, 0),
                _fmt_num(stats.records_inserted, 0),
                _fmt_num(stats.records_skipped, 0),
                _fmt_num(stats.stores_seen, 0),
                _fmt_num(stats.skus_seen, 0),
                f"{stats.first_stock_month or '-'}..{stats.last_stock_month or '-'}",
                _fmt_num(deleted_rows, 0),
            ]
        )
    return rows


def _coverage_delta_rows(
    before: dict[str, dict[str, object]],
    after: dict[str, dict[str, object]],
) -> list[list[str]]:
    rows: list[list[str]] = []
    for store in PHASE_STORES:
        before_row = before[store]
        after_row = after[store]
        records_delta = int(after_row["records"] or 0) - int(before_row["records"] or 0)
        sku_delta = int(after_row["skus"] or 0) - int(before_row["skus"] or 0)
        rows.append(
            [
                store,
                _fmt_num(before_row["records"], 0),
                _fmt_num(after_row["records"], 0),
                _fmt_num(records_delta, 0),
                _fmt_num(before_row["skus"], 0),
                _fmt_num(after_row["skus"], 0),
                _fmt_num(sku_delta, 0),
                _fmt_num(after_row["months"], 0),
                f"{after_row['first_month'] or '-'}..{after_row['last_month'] or '-'}",
                _fmt_num(after_row["zero_records"], 0),
                _fmt_num(after_row["negative_records"], 0),
            ]
        )
    return rows


def _total_delta_rows(before: dict[str, object], after: dict[str, object]) -> list[list[str]]:
    return [
        [
            "monthly_store_stock",
            _fmt_num(before["records"], 0),
            _fmt_num(after["records"], 0),
            _fmt_num(int(after["records"] or 0) - int(before["records"] or 0), 0),
            _fmt_num(before["skus"], 0),
            _fmt_num(after["skus"], 0),
            _fmt_num(int(after["skus"] or 0) - int(before["skus"] or 0), 0),
            _fmt_num(after["stores"], 0),
            f"{after['first_month'] or '-'}..{after['last_month'] or '-'}",
        ]
    ]


def _source_file_rows(conn: sqlite3.Connection, paths: list[Path]) -> list[list[str]]:
    rows: list[list[str]] = []
    for path in paths:
        row = conn.execute(
            """
            SELECT file_name, source_kind, feature_scope, rows_seen, records_inserted,
                   records_skipped, stores_seen, skus_seen, first_stock_month, last_stock_month
            FROM stock_source_files_v2
            WHERE source_file = ?
            """,
            (str(path),),
        ).fetchone()
        if not row:
            continue
        rows.append(
            [
                str(row[0]),
                str(row[1]),
                str(row[2]),
                _fmt_num(row[3], 0),
                _fmt_num(row[4], 0),
                _fmt_num(row[5], 0),
                _fmt_num(row[6], 0),
                _fmt_num(row[7], 0),
                f"{row[8] or '-'}..{row[9] or '-'}",
            ]
        )
    return rows


def build_report(
    conn: sqlite3.Connection,
    paths: list[Path],
    stats_by_path: list[tuple[Path, StockImportStats, int]],
    before_stores: dict[str, dict[str, object]],
    after_stores: dict[str, dict[str, object]],
    before_total: dict[str, object],
    after_total: dict[str, object],
) -> str:
    return "\n".join(
        [
            "# Iteration 5L — V2 Phase 8C Monthly Store Stock Ingestion",
            "",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            "## Phase Checkpoint",
            "",
            "Phase completed: Phase 8C — complete monthly store stock coverage for Constanta, Iasi, and Oradea.",
            "",
            "What changed: the three missing wide monthly store-stock files from `new_stock_data_20may/` were imported into `stock_monthly_store_v2` as historical end-of-month stock. The runner deletes any previous rows for the same source files before import, so reruns do not double-count stock.",
            "",
            "Accuracy rerun: no. This phase only adds historical stock context. Accuracy will be re-measured after Phase 8E joins store/supplier availability into the feature matrix.",
            "",
            _table(
                ["Baseline metric", "Current official control before Phase 8C"],
                [
                    ["Best model", "sk_blend_post_bf_safe"],
                    ["Hit +/-20", _fmt_pct(BASELINE_HIT20)],
                    ["Hit +/-30", _fmt_pct(BASELINE_HIT30)],
                    ["WMAPE", _fmt_pct(BASELINE_WMAPE)],
                    ["Phantom rate", _fmt_pct(BASELINE_PHANTOM)],
                ],
            ),
            "",
            "## Import Result",
            "",
            _table(
                [
                    "File",
                    "Rows",
                    "Records inserted",
                    "Records skipped",
                    "Stores",
                    "SKUs",
                    "Month range",
                    "Prior rows removed",
                ],
                _import_rows(stats_by_path),
            ),
            "",
            "## Recorded Source Files",
            "",
            _table(
                ["File", "Kind", "Feature scope", "Rows", "Records", "Skipped", "Stores", "SKUs", "Month range"],
                _source_file_rows(conn, paths),
            ),
            "",
            "## Store Coverage Delta",
            "",
            _table(
                [
                    "Store",
                    "Records before",
                    "Records after",
                    "Record delta",
                    "SKUs before",
                    "SKUs after",
                    "SKU delta",
                    "Months",
                    "Month range",
                    "Zero records",
                    "Negative records",
                ],
                _coverage_delta_rows(before_stores, after_stores),
            ),
            "",
            "## Total Monthly Store Stock Delta",
            "",
            _table(
                [
                    "Table",
                    "Records before",
                    "Records after",
                    "Record delta",
                    "SKUs before",
                    "SKUs after",
                    "SKU delta",
                    "Stores after",
                    "Month range after",
                ],
                _total_delta_rows(before_total, after_total),
            ),
            "",
            "## Source SKU Overlap With Sales",
            "",
            _table(
                ["File", "Stock SKUs", "Overlap with sales SKUs", "Overlap % of stock SKUs"],
                _source_overlap_rows(conn, paths),
            ),
            "",
            "## Target-Window Stock Context Coverage",
            "",
            "Because Phase 8B invalidated cached regime labels, this table uses the fast forecastable proxy until the next model rebuild regenerates official labels.",
            "",
            _table(
                ["Target start", "Previous stock month", "Population source", "SKUs", "With stock context", "Coverage"],
                monthly_stock_context_coverage(conn, DEFAULT_TARGET_STARTS),
            ),
            "",
            "## Historical Safety",
            "",
            "- These files are monthly store stock and are marked `historical_backtest`.",
            "- They are treated as end-of-month stock snapshots.",
            "- Feature usage must still lag the target window; the model should only use the latest completed stock month before the forecast start.",
            "- No supplier-stock or rotation-snapshot files were ingested in this phase.",
            "",
            "## Accuracy Report",
            "",
            "Accuracy not re-run. Official baseline remains `sk_blend_post_bf_safe`: hit +/-20 = 24.1%, hit +/-30 = 35.3%, WMAPE = 56.1%, phantom rate = 48.1%.",
        ]
    ) + "\n"


def run_phase8c(input_dir: Path = DEFAULT_INPUT, db_path: Path = DB_PATH, report_path: Path = DEFAULT_REPORT) -> None:
    paths = [(input_dir / file_name).resolve() for file_name in PHASE_FILES]
    missing = [str(path) for path in paths if not path.exists()]
    if missing:
        raise FileNotFoundError("Missing Phase 8C input files: " + ", ".join(missing))

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    try:
        ensure_stock_tables(conn, rebuild=False)
        allowed_stores = existing_sales_stores(conn)
        if not allowed_stores:
            allowed_stores = {normalize_store(store)[0] for store in PHASE_STORES}

        before_stores = _store_summary(conn, PHASE_STORES)
        before_total = _total_stock_summary(conn)

        stats_by_path: list[tuple[Path, StockImportStats, int]] = []
        for path in paths:
            deleted_rows = _delete_previous_source_rows(conn, path)
            stats = import_monthly_file(conn, path, allowed_stores)
            record_source_file(conn, path, stats)
            conn.commit()
            stats_by_path.append((path, stats, deleted_rows))

        after_stores = _store_summary(conn, PHASE_STORES)
        after_total = _total_stock_summary(conn)
        report = build_report(conn, paths, stats_by_path, before_stores, after_stores, before_total, after_total)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(report, encoding="utf-8")
        print(report)
        print(f"Wrote {report_path}")
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Import Forecast V2 Phase 8C monthly store stock files.")
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    run_phase8c(input_dir=args.input_dir, db_path=args.db, report_path=args.report)


if __name__ == "__main__":
    main()
