"""Phase 8F rotation snapshot ingestion for current/future diagnostics."""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

try:
    from .ingestion import clean_text, normalize_store, parse_float
    from .stock_ingestion import DB_PATH, StockImportStats, ensure_stock_tables, read_csv_rows, record_source_file
except ImportError:  # Allows direct script execution.
    from ingestion import clean_text, normalize_store, parse_float
    from stock_ingestion import DB_PATH, StockImportStats, ensure_stock_tables, read_csv_rows, record_source_file


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = PROJECT_ROOT / "new_stock_data_20may"
DEFAULT_REPORT = PROJECT_ROOT / "active_docs" / "ITER5O_V2_PHASE8F_ROTATION_SNAPSHOT.md"
PHASE_FILES = [
    "viteza rotatie stock constanta.csv",
    "viteza rotatie stock militari.csv",
    "viteza rotatie stock pipera.csv",
    "viteza rotatie stock sibiu.csv",
]
STORE_HINTS = {
    "constanta": "M & D RETAIL CONSTANTA SRL",
    "militari": "M & D RETAIL MILITARI SRL",
    "pipera": "M & D RETAIL PIPERA SRL",
    "sibiu": "M & D RETAIL SIBIU SRL",
}
ROTATION_COLUMNS = {
    "Nr Luni de Stoc (Stoc/vz medie lunara)": "months_of_stock",
    "Viteza de Rotatie Generala Stoc_Vanzari (consolidat Importatori + Magazine)": "rotation_general_stock_sales",
    "Viteza de Rotatie Stoc Consolidata (Importatori + Magazine)": "rotation_consolidated_stock",
    "Viteza de Rotatie Stoc_Vanzari Totale Furnizor": "rotation_supplier_total_stock_sales",
    "Viteza de Rotatie Stoc Furnizor": "rotation_supplier_stock",
    "Viteza de Rotatie Stoc_Vanzari Magazine": "rotation_store_stock_sales",
    "Viteza de Rotatie Stoc Magazine (M12)": "rotation_store_m12",
}


@dataclass(frozen=True)
class RotationStats:
    file_name: str
    rows_seen: int
    records_inserted: int
    records_skipped: int
    store_id: str
    skus_seen: int
    sales_overlap_skus: int
    headline_overlap_skus: int
    missing_months_stock: int
    missing_any_rotation: int
    positive_available_rows: int
    positive_total_rows: int


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


def infer_store_from_file(path: Path) -> tuple[str, str]:
    name = path.name.lower()
    for token, raw_store in STORE_HINTS.items():
        if token in name:
            return normalize_store(raw_store)
    return "unknown_store", "unknown"


def _column_by_pattern(row: dict[str, str], *patterns: str) -> str | None:
    for key in row:
        key_norm = key.upper()
        if all(pattern.upper() in key_norm for pattern in patterns):
            return key
    return None


def ensure_rotation_table(conn: sqlite3.Connection, rebuild: bool = False) -> None:
    ensure_stock_tables(conn, rebuild=False)
    if rebuild:
        conn.execute("DROP TABLE IF EXISTS stock_rotation_snapshot_v2")
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS stock_rotation_snapshot_v2 (
            snapshot_key TEXT PRIMARY KEY,
            source_file TEXT NOT NULL,
            source_row_number INTEGER NOT NULL,
            snapshot_date TEXT NOT NULL,
            feature_scope TEXT NOT NULL,
            store_id TEXT NOT NULL,
            store_type TEXT NOT NULL,
            sku_id TEXT NOT NULL,
            months_of_stock REAL,
            rotation_general_stock_sales REAL,
            rotation_consolidated_stock REAL,
            rotation_supplier_total_stock_sales REAL,
            rotation_supplier_stock REAL,
            rotation_store_stock_sales REAL,
            rotation_store_m12 REAL,
            store_stock_position_qty REAL,
            store_stock_total_qty REAL,
            store_stock_available_qty REAL,
            raw_row_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(source_file, source_row_number)
        );

        CREATE INDEX IF NOT EXISTS idx_stock_rotation_snapshot_sku_store
            ON stock_rotation_snapshot_v2(sku_id, store_id);
        CREATE INDEX IF NOT EXISTS idx_stock_rotation_snapshot_scope
            ON stock_rotation_snapshot_v2(feature_scope, snapshot_date);
        """
    )
    conn.commit()


def _delete_previous_source_rows(conn: sqlite3.Connection, path: Path) -> int:
    source_keys = {str(path)}
    rows = conn.execute(
        "SELECT source_file FROM stock_source_files_v2 WHERE file_name = ?",
        (path.name,),
    ).fetchall()
    source_keys.update(str(row[0]) for row in rows)
    deleted = 0
    for source_key in source_keys:
        before = conn.total_changes
        conn.execute("DELETE FROM stock_rotation_snapshot_v2 WHERE source_file = ?", (source_key,))
        conn.execute("DELETE FROM stock_source_files_v2 WHERE source_file = ?", (source_key,))
        deleted += conn.total_changes - before
    return deleted


def _snapshot_key(path: Path, row_num: int, sku_id: str, store_id: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", path.name)
    return f"{safe}:{row_num}:{store_id}:{sku_id}"


def _reference_skus(conn: sqlite3.Connection) -> tuple[set[str], set[str]]:
    sales = {
        str(row[0])
        for row in conn.execute(
            """
            SELECT DISTINCT sku_id
            FROM raw_sales_transactions_v2
            WHERE sku_id IS NOT NULL AND is_non_product = 0
            """
        )
    }
    headline = {
        str(row[0])
        for row in conn.execute(
            """
            SELECT DISTINCT sku_id
            FROM forecast_v2_regime_labels
            WHERE sku_id IS NOT NULL AND headline_eligible = 1
            """
        )
    }
    return sales, headline


def import_rotation_file(
    conn: sqlite3.Connection,
    path: Path,
    sales_skus: set[str],
    headline_skus: set[str],
    snapshot_date: str,
) -> RotationStats:
    store_id, store_type = infer_store_from_file(path)
    insert_sql = """
        INSERT OR REPLACE INTO stock_rotation_snapshot_v2 (
            snapshot_key, source_file, source_row_number, snapshot_date, feature_scope,
            store_id, store_type, sku_id, months_of_stock,
            rotation_general_stock_sales, rotation_consolidated_stock,
            rotation_supplier_total_stock_sales, rotation_supplier_stock,
            rotation_store_stock_sales, rotation_store_m12,
            store_stock_position_qty, store_stock_total_qty, store_stock_available_qty,
            raw_row_json, created_at
        ) VALUES (?, ?, ?, ?, 'current_snapshot', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
    """
    rows_seen = records_inserted = records_skipped = 0
    missing_months_stock = missing_any_rotation = 0
    positive_available_rows = positive_total_rows = 0
    skus: set[str] = set()
    batch: list[tuple[object, ...]] = []

    for row_num, row in read_csv_rows(path):
        if not any(row.values()):
            continue
        rows_seen += 1
        sku_id = clean_text(row.get("COD ARTICOL"))
        if not sku_id:
            records_skipped += 1
            continue
        skus.add(sku_id)
        position_col = _column_by_pattern(row, "STOC TOTAL", "POZITIE")
        total_col = _column_by_pattern(row, "STOC TOTAL", "CANTITATIV")
        available_col = _column_by_pattern(row, "STOC DISPONIBIL", "CANTITATIV")
        months_of_stock = parse_float(row.get("Nr Luni de Stoc (Stoc/vz medie lunara)"))
        rotations = {field: parse_float(row.get(source)) for source, field in ROTATION_COLUMNS.items()}
        position_qty = parse_float(row.get(position_col)) if position_col else None
        total_qty = parse_float(row.get(total_col)) if total_col else None
        available_qty = parse_float(row.get(available_col)) if available_col else None
        if months_of_stock is None:
            missing_months_stock += 1
        if all(value is None for value in rotations.values()):
            missing_any_rotation += 1
        if available_qty is not None and available_qty > 0:
            positive_available_rows += 1
        if total_qty is not None and total_qty > 0:
            positive_total_rows += 1
        batch.append(
            (
                _snapshot_key(path, row_num, sku_id, store_id),
                str(path),
                row_num,
                snapshot_date,
                store_id,
                store_type,
                sku_id,
                months_of_stock,
                rotations["rotation_general_stock_sales"],
                rotations["rotation_consolidated_stock"],
                rotations["rotation_supplier_total_stock_sales"],
                rotations["rotation_supplier_stock"],
                rotations["rotation_store_stock_sales"],
                rotations["rotation_store_m12"],
                position_qty,
                total_qty,
                available_qty,
                json.dumps(row, ensure_ascii=False, sort_keys=True),
            )
        )
        records_inserted += 1
        if len(batch) >= 10000:
            conn.executemany(insert_sql, batch)
            batch.clear()

    if batch:
        conn.executemany(insert_sql, batch)
    return RotationStats(
        file_name=path.name,
        rows_seen=rows_seen,
        records_inserted=records_inserted,
        records_skipped=records_skipped,
        store_id=store_id,
        skus_seen=len(skus),
        sales_overlap_skus=len(skus & sales_skus),
        headline_overlap_skus=len(skus & headline_skus),
        missing_months_stock=missing_months_stock,
        missing_any_rotation=missing_any_rotation,
        positive_available_rows=positive_available_rows,
        positive_total_rows=positive_total_rows,
    )


def _source_stats(stats: RotationStats) -> StockImportStats:
    return StockImportStats(
        file_name=stats.file_name,
        source_kind="rotation_snapshot",
        rows_seen=stats.rows_seen,
        records_inserted=stats.records_inserted,
        records_skipped=stats.records_skipped,
        stores_seen=1,
        skus_seen=stats.skus_seen,
        feature_scope="current_snapshot",
    )


def import_rows(stats_by_path: list[tuple[Path, RotationStats, int]]) -> list[list[str]]:
    rows: list[list[str]] = []
    for path, stats, deleted in stats_by_path:
        rows.append(
            [
                path.name,
                stats.store_id,
                _fmt_num(stats.rows_seen, 0),
                _fmt_num(stats.records_inserted, 0),
                _fmt_num(stats.records_skipped, 0),
                _fmt_num(stats.skus_seen, 0),
                _fmt_num(stats.sales_overlap_skus, 0),
                _fmt_pct(stats.sales_overlap_skus / stats.skus_seen if stats.skus_seen else None),
                _fmt_num(stats.headline_overlap_skus, 0),
                _fmt_num(deleted, 0),
            ]
        )
    return rows


def quality_rows(stats_by_path: list[tuple[Path, RotationStats, int]]) -> list[list[str]]:
    rows: list[list[str]] = []
    for path, stats, _ in stats_by_path:
        rows.append(
            [
                path.name,
                _fmt_pct(stats.missing_months_stock / stats.rows_seen if stats.rows_seen else None),
                _fmt_pct(stats.missing_any_rotation / stats.rows_seen if stats.rows_seen else None),
                _fmt_num(stats.positive_available_rows, 0),
                _fmt_pct(stats.positive_available_rows / stats.rows_seen if stats.rows_seen else None),
                _fmt_num(stats.positive_total_rows, 0),
                _fmt_pct(stats.positive_total_rows / stats.rows_seen if stats.rows_seen else None),
            ]
        )
    return rows


def store_summary_rows(conn: sqlite3.Connection) -> list[list[str]]:
    rows: list[list[str]] = []
    for row in conn.execute(
        """
        SELECT
            store_id,
            COUNT(*) AS records,
            COUNT(DISTINCT sku_id) AS skus,
            SUM(CASE WHEN months_of_stock IS NULL THEN 1 ELSE 0 END) AS missing_months,
            SUM(CASE WHEN rotation_store_m12 IS NULL THEN 1 ELSE 0 END) AS missing_store_m12,
            SUM(CASE WHEN store_stock_available_qty > 0 THEN 1 ELSE 0 END) AS positive_available,
            SUM(CASE WHEN store_stock_total_qty > 0 THEN 1 ELSE 0 END) AS positive_total
        FROM stock_rotation_snapshot_v2
        GROUP BY store_id
        ORDER BY store_id
        """
    ):
        records = row[1] or 0
        rows.append(
            [
                str(row[0]),
                _fmt_num(records, 0),
                _fmt_num(row[2], 0),
                _fmt_pct((row[3] or 0) / records if records else None),
                _fmt_pct((row[4] or 0) / records if records else None),
                _fmt_num(row[5] or 0, 0),
                _fmt_num(row[6] or 0, 0),
            ]
        )
    return rows


def build_report(
    conn: sqlite3.Connection,
    stats_by_path: list[tuple[Path, RotationStats, int]],
    snapshot_date: str,
) -> str:
    total_records = conn.execute("SELECT COUNT(*) FROM stock_rotation_snapshot_v2").fetchone()[0]
    total_skus = conn.execute("SELECT COUNT(DISTINCT sku_id) FROM stock_rotation_snapshot_v2").fetchone()[0]
    total_stores = conn.execute("SELECT COUNT(DISTINCT store_id) FROM stock_rotation_snapshot_v2").fetchone()[0]
    return "\n".join(
        [
            "# Iteration 5O — V2 Phase 8F Rotation Snapshot Ingestion",
            "",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            "## Phase Checkpoint",
            "",
            "Phase completed: Phase 8F — rotation snapshot ingestion for current/future diagnostics.",
            "",
            f"Snapshot date assigned: `{snapshot_date}`. These files do not contain historical as-of dates, so every row is marked `current_snapshot` and must not be used in official historical backtests.",
            "",
            "Accuracy rerun: no. Current-only rotation snapshots can support diagnostics and future forecast enrichment, but they are not leak-safe historical training inputs.",
            "",
            "## Import Result",
            "",
            _table(
                [
                    "File",
                    "Store",
                    "Rows",
                    "Inserted",
                    "Skipped",
                    "SKUs",
                    "Sales overlap",
                    "Sales overlap %",
                    "Headline overlap",
                    "Prior rows removed",
                ],
                import_rows(stats_by_path),
            ),
            "",
            "## Snapshot Quality",
            "",
            _table(
                [
                    "File",
                    "Missing months-of-stock",
                    "Missing all rotation metrics",
                    "Positive available rows",
                    "Positive available %",
                    "Positive total rows",
                    "Positive total %",
                ],
                quality_rows(stats_by_path),
            ),
            "",
            "## Store Summary",
            "",
            _table(
                [
                    "Store",
                    "Records",
                    "SKUs",
                    "Missing months-of-stock",
                    "Missing store M12 rotation",
                    "Positive available",
                    "Positive total",
                ],
                store_summary_rows(conn),
            ),
            "",
            "## Table Summary",
            "",
            _table(
                ["Table", "Records", "SKUs", "Stores", "Feature scope"],
                [["stock_rotation_snapshot_v2", _fmt_num(total_records, 0), _fmt_num(total_skus, 0), _fmt_num(total_stores, 0), "current_snapshot"]],
            ),
            "",
            "## Historical Safety",
            "",
            "- These rotation files are useful for current/future forecasts and operational diagnostics.",
            "- They are not used in Phase 8E or any official historical scorecard because the export has no historical as-of month/date.",
            "- If future exports include monthly historical rotation or an as-of date per snapshot, we can create separate historical-safe features.",
            "",
            "## Accuracy Report",
            "",
            "Accuracy not re-run. Official Phase 8E best raw hit +/-20 remains 24.6%; safer blend remains hit +/-20 24.2%, WMAPE 55.6%, phantom 44.4%.",
        ]
    ) + "\n"


def run_phase8f(input_dir: Path = DEFAULT_INPUT, db_path: Path = DB_PATH, report_path: Path = DEFAULT_REPORT) -> None:
    paths = [(input_dir / file_name).resolve() for file_name in PHASE_FILES]
    missing = [str(path) for path in paths if not path.exists()]
    if missing:
        raise FileNotFoundError("Missing Phase 8F input files: " + ", ".join(missing))
    snapshot_date = date.today().isoformat()

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA busy_timeout=60000")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    try:
        ensure_rotation_table(conn, rebuild=False)
        sales_skus, headline_skus = _reference_skus(conn)
        stats_by_path: list[tuple[Path, RotationStats, int]] = []
        for path in paths:
            deleted = _delete_previous_source_rows(conn, path)
            stats = import_rotation_file(conn, path, sales_skus, headline_skus, snapshot_date)
            record_source_file(conn, path, _source_stats(stats))
            conn.commit()
            stats_by_path.append((path, stats, deleted))

        report = build_report(conn, stats_by_path, snapshot_date)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(report, encoding="utf-8")
        print(report)
        print(f"Wrote {report_path}")
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Import Forecast V2 Phase 8F rotation snapshot files.")
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    run_phase8f(input_dir=args.input_dir, db_path=args.db, report_path=args.report)


if __name__ == "__main__":
    main()
