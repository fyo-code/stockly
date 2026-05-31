"""Forecast v2 stock ingestion.

This module keeps stock data separate from sales ingestion. Monthly store stock
is historical and can be used in walk-forward backtests. Snapshot/rotation files
are preserved for current/future forecasting context, but marked current-only
unless a real historical as-of date is present in the source.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sqlite3
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterable

try:
    from .ingestion import clean_text, normalize_store, null_if_empty, parse_date, parse_float
    from .regime_labels import RULE_VERSION
except ImportError:  # Allows direct script execution.
    from ingestion import clean_text, normalize_store, null_if_empty, parse_date, parse_float
    from regime_labels import RULE_VERSION


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "backend" / "data" / "supply_chain.db"
DEFAULT_INPUT = PROJECT_ROOT / "stock_related_data"
DEFAULT_REPORT = PROJECT_ROOT / "active_docs" / "ITER5C_V2_STOCK_INGESTION.md"

MONTH_MAP = {
    "IANUARIE": 1,
    "FEBRUARIE": 2,
    "MARTIE": 3,
    "APRILIE": 4,
    "MAI": 5,
    "IUNIE": 6,
    "IULIE": 7,
    "AUGUST": 8,
    "SEPTEMBRIE": 9,
    "OCTOMBRIE": 10,
    "NOIEMBRIE": 11,
    "DECEMBRIE": 12,
}
MONTH_STOCK_RE = re.compile(r"^(.+?)\s+(20\d{2})/STOC$", re.IGNORECASE)
DEFAULT_TARGET_STARTS = [
    "2024-04-29",
    "2024-05-27",
    "2024-07-01",
    "2024-07-29",
    "2024-08-26",
    "2024-09-23",
    "2024-10-28",
    "2024-11-25",
    "2024-12-30",
    "2025-01-27",
    "2025-02-24",
    "2025-03-24",
]

STORE_NAME_HINTS = {
    "BANEASA": "MOBEXPERT BANEASA SRL",
    "BRASOV": "M & D RETAIL BRASOV SRL",
    "PIPERA": "M & D RETAIL PIPERA SRL",
    "PANTELIMON": "M & D RETAIL PANTELIMON SRL",
    "PANTE": "M & D RETAIL PANTELIMON SRL",
    "MILITARI": "M & D RETAIL MILITARI SRL",
    "TIMISOARA": "M & D RETAIL TIM SRL",
    "SIBIU": "M & D RETAIL SIBIU SRL",
    "PLOIESTI": "M & D RETAIL PLOIESTI SRL",
    "CONSTANTA": "M & D RETAIL CONSTANTA SRL",
    "IASI": "M & D RETAIL IASI SRL",
    "ORADEA": "M & D RETAIL ORADEA SRL",
    "CRAIOVA": "M & D RETAIL CRAIOVA SRL",
}


@dataclass(frozen=True)
class StockImportStats:
    file_name: str
    source_kind: str
    rows_seen: int = 0
    records_inserted: int = 0
    records_skipped: int = 0
    stores_seen: int = 0
    skus_seen: int = 0
    first_stock_month: str | None = None
    last_stock_month: str | None = None
    feature_scope: str = "historical_backtest"


def strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def read_csv_rows(path: Path) -> Iterable[tuple[int, dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as f:
        sample = f.read(8192)
        f.seek(0)
        try:
            delimiter = csv.Sniffer().sniff(sample, delimiters=",;\t|").delimiter
        except csv.Error:
            delimiter = ","
        reader = csv.DictReader(f, delimiter=delimiter)
        reader.fieldnames = [clean_text(field) for field in (reader.fieldnames or [])]
        for row_num, row in enumerate(reader, start=2):
            yield row_num, {clean_text(key): clean_text(value) for key, value in row.items() if key is not None}


def csv_header(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as f:
        sample = f.read(8192)
        f.seek(0)
        try:
            delimiter = csv.Sniffer().sniff(sample, delimiters=",;\t|").delimiter
        except csv.Error:
            delimiter = ","
        reader = csv.reader(f, delimiter=delimiter)
        return [clean_text(field) for field in next(reader, [])]


def month_start_from_column(column: str) -> str | None:
    match = MONTH_STOCK_RE.match(clean_text(column))
    if not match:
        return None
    month_name = strip_accents(match.group(1)).upper().strip()
    month_name = re.sub(r"[^A-Z]+", " ", month_name).strip().split(" ")[0]
    month = MONTH_MAP.get(month_name)
    if month is None:
        return None
    return f"{int(match.group(2)):04d}-{month:02d}-01"


def stock_month_columns(header: list[str]) -> dict[str, str]:
    return {column: month for column in header if (month := month_start_from_column(column))}


def discover_stock_files(input_path: Path) -> tuple[list[Path], list[Path]]:
    files = [input_path] if input_path.is_file() else sorted(input_path.glob("*.csv"))
    names = {path.name for path in files}
    monthly: list[Path] = []
    snapshots: list[Path] = []
    for path in files:
        header = csv_header(path)
        if stock_month_columns(header):
            if path.name == "stock monthly brasov.csv" and "brasov 22-25 stoc magazin.csv" in names:
                continue
            monthly.append(path)
        else:
            snapshots.append(path)
    return monthly, snapshots


def existing_sales_stores(conn: sqlite3.Connection) -> set[str]:
    try:
        rows = conn.execute("SELECT DISTINCT store_id FROM raw_sales_transactions_v2").fetchall()
    except sqlite3.OperationalError:
        return set()
    return {str(row[0]) for row in rows}


def ensure_stock_tables(conn: sqlite3.Connection, rebuild: bool = False) -> None:
    if rebuild:
        conn.executescript(
            """
            DROP TABLE IF EXISTS stock_monthly_store_v2;
            DROP TABLE IF EXISTS stock_snapshot_store_v2;
            DROP TABLE IF EXISTS stock_source_files_v2;
            """
        )
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS stock_source_files_v2 (
            source_file TEXT PRIMARY KEY,
            file_name TEXT NOT NULL,
            source_kind TEXT NOT NULL,
            feature_scope TEXT NOT NULL,
            imported_at TEXT NOT NULL,
            rows_seen INTEGER NOT NULL DEFAULT 0,
            records_inserted INTEGER NOT NULL DEFAULT 0,
            records_skipped INTEGER NOT NULL DEFAULT 0,
            stores_seen INTEGER NOT NULL DEFAULT 0,
            skus_seen INTEGER NOT NULL DEFAULT 0,
            first_stock_month TEXT,
            last_stock_month TEXT
        );

        CREATE TABLE IF NOT EXISTS stock_monthly_store_v2 (
            sku_id TEXT NOT NULL,
            store_id TEXT NOT NULL,
            store_type TEXT NOT NULL,
            stock_month TEXT NOT NULL,
            stock_qty REAL NOT NULL,
            stock_signal_status TEXT NOT NULL,
            source_file TEXT NOT NULL,
            source_row_count INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            PRIMARY KEY (sku_id, store_id, stock_month, source_file)
        );

        CREATE INDEX IF NOT EXISTS idx_stock_monthly_sku_month
            ON stock_monthly_store_v2(sku_id, stock_month);
        CREATE INDEX IF NOT EXISTS idx_stock_monthly_store_month
            ON stock_monthly_store_v2(store_id, stock_month);

        CREATE TABLE IF NOT EXISTS stock_snapshot_store_v2 (
            snapshot_key TEXT PRIMARY KEY,
            source_file TEXT NOT NULL,
            source_row_number INTEGER NOT NULL,
            snapshot_date TEXT,
            feature_scope TEXT NOT NULL,
            store_id TEXT NOT NULL,
            store_type TEXT NOT NULL,
            sku_id TEXT NOT NULL,
            product_name TEXT,
            category_raw TEXT,
            class_raw TEXT,
            subclass_raw TEXT,
            substil_raw TEXT,
            campaign_raw TEXT,
            collection_age_bucket TEXT,
            stock_entry_date TEXT,
            stock_age_days REAL,
            supplier_available_qty REAL,
            available_store_qty REAL,
            total_store_qty REAL,
            sellable_store_qty REAL,
            outlet_available_qty REAL,
            position_stock_qty REAL,
            reserved_qty REAL,
            reserved_value REAL,
            rotation_m12 REAL,
            months_stock_supplier REAL,
            months_stock_general REAL,
            avg_sales_metric REAL,
            last_supplier_network_sale_date TEXT,
            raw_row_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_stock_snapshot_sku
            ON stock_snapshot_store_v2(sku_id, store_id);
        """
    )
    conn.commit()


def record_source_file(conn: sqlite3.Connection, path: Path, stats: StockImportStats) -> None:
    conn.execute(
        """
        INSERT OR REPLACE INTO stock_source_files_v2 (
            source_file, file_name, source_kind, feature_scope, imported_at,
            rows_seen, records_inserted, records_skipped, stores_seen, skus_seen,
            first_stock_month, last_stock_month
        ) VALUES (?, ?, ?, ?, datetime('now'), ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            str(path),
            stats.file_name,
            stats.source_kind,
            stats.feature_scope,
            stats.rows_seen,
            stats.records_inserted,
            stats.records_skipped,
            stats.stores_seen,
            stats.skus_seen,
            stats.first_stock_month,
            stats.last_stock_month,
        ),
    )


def import_monthly_file(conn: sqlite3.Connection, path: Path, allowed_stores: set[str]) -> StockImportStats:
    header = csv_header(path)
    month_cols = stock_month_columns(header)
    insert_sql = """
        INSERT INTO stock_monthly_store_v2 (
            sku_id, store_id, store_type, stock_month, stock_qty,
            stock_signal_status, source_file, source_row_count, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, 1, datetime('now'))
        ON CONFLICT(sku_id, store_id, stock_month, source_file)
        DO UPDATE SET
            stock_qty = stock_qty + excluded.stock_qty,
            source_row_count = source_row_count + 1
    """
    rows_seen = records_inserted = records_skipped = 0
    stores: set[str] = set()
    skus: set[str] = set()
    first_month: str | None = None
    last_month: str | None = None
    batch: list[tuple[object, ...]] = []

    for _, row in read_csv_rows(path):
        if not any(row.values()):
            continue
        rows_seen += 1
        sku_id = null_if_empty(row.get("ARTICOL COD")) or null_if_empty(row.get("COD ARTICOL"))
        raw_store = null_if_empty(row.get("MAGAZIN"))
        if not sku_id or not raw_store:
            records_skipped += len(month_cols)
            continue
        store_id, store_type = normalize_store(raw_store)
        if store_id not in allowed_stores:
            records_skipped += len(month_cols)
            continue
        stores.add(store_id)
        skus.add(sku_id)
        for column, stock_month in month_cols.items():
            stock_qty = parse_float(row.get(column))
            if stock_qty is None:
                records_skipped += 1
                continue
            first_month = stock_month if first_month is None or stock_month < first_month else first_month
            last_month = stock_month if last_month is None or stock_month > last_month else last_month
            batch.append((sku_id, store_id, store_type, stock_month, stock_qty, "observed", str(path)))
            records_inserted += 1
            if len(batch) >= 10000:
                conn.executemany(insert_sql, batch)
                batch.clear()

    if batch:
        conn.executemany(insert_sql, batch)
    return StockImportStats(
        file_name=path.name,
        source_kind="monthly_store_stock",
        rows_seen=rows_seen,
        records_inserted=records_inserted,
        records_skipped=records_skipped,
        stores_seen=len(stores),
        skus_seen=len(skus),
        first_stock_month=first_month,
        last_stock_month=last_month,
        feature_scope="historical_backtest",
    )


def infer_store_from_snapshot(path: Path, row: dict[str, str]) -> tuple[str, str]:
    raw_store = null_if_empty(row.get("NUME MAGAZIN")) or null_if_empty(row.get("MAGAZIN"))
    if raw_store:
        return normalize_store(raw_store)
    searchable = " ".join([path.name, " ".join(row.keys())]).upper()
    for token, raw in STORE_NAME_HINTS.items():
        if token in searchable:
            return normalize_store(raw)
    return "unknown_store", "unknown"


def first_float(row: dict[str, str], names: list[str]) -> float | None:
    for name in names:
        value = parse_float(row.get(name))
        if value is not None:
            return value
    return None


def find_column_value(row: dict[str, str], includes: list[str], excludes: list[str] | None = None) -> float | None:
    excludes = excludes or []
    for key, value in row.items():
        key_norm = strip_accents(key).upper()
        if all(token in key_norm for token in includes) and not any(token in key_norm for token in excludes):
            parsed = parse_float(value)
            if parsed is not None:
                return parsed
    return None


def snapshot_key(path: Path, row_num: int, sku_id: str, store_id: str) -> str:
    raw = f"{path}|{row_num}|{sku_id}|{store_id}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def import_snapshot_file(conn: sqlite3.Connection, path: Path, allowed_stores: set[str]) -> StockImportStats:
    insert_sql = """
        INSERT OR REPLACE INTO stock_snapshot_store_v2 (
            snapshot_key, source_file, source_row_number, snapshot_date, feature_scope,
            store_id, store_type, sku_id, product_name, category_raw, class_raw,
            subclass_raw, substil_raw, campaign_raw, collection_age_bucket,
            stock_entry_date, stock_age_days, supplier_available_qty,
            available_store_qty, total_store_qty, sellable_store_qty,
            outlet_available_qty, position_stock_qty, reserved_qty, reserved_value,
            rotation_m12, months_stock_supplier, months_stock_general,
            avg_sales_metric, last_supplier_network_sale_date, raw_row_json, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
    """
    rows_seen = records_inserted = records_skipped = 0
    stores: set[str] = set()
    skus: set[str] = set()
    snapshot_date = date.today().isoformat()
    batch: list[tuple[object, ...]] = []

    for row_num, row in read_csv_rows(path):
        if not any(row.values()):
            continue
        rows_seen += 1
        sku_id = null_if_empty(row.get("COD ARTICOL")) or null_if_empty(row.get("ARTICOL COD"))
        store_id, store_type = infer_store_from_snapshot(path, row)
        if not sku_id or store_id not in allowed_stores:
            records_skipped += 1
            continue
        stores.add(store_id)
        skus.add(sku_id)
        supplier_available = first_float(row, ["STOC DISPONIBIL FURNIZOR", "Stoc Disponibil Cantitativ Furnizor"])
        available_store = find_column_value(row, ["STOC DISPONIBIL", "CANTITATIV"], ["FURNIZOR", "OUTLET"])
        outlet_available = find_column_value(row, ["STOC DISPONIBIL", "OUTLET"])
        total_store = first_float(row, ["CANTSTOC"]) or find_column_value(row, ["STOC TOTAL", "CANTITATIV"])
        position_stock = find_column_value(row, ["STOC TOTAL", "POZITIE"])
        sellable = first_float(row, ["Cantitate Stoc Disponibil Vandabil Magazine"])
        reserved_qty = first_float(row, ["Cantitate Stoc Rezervat"])
        reserved_value = first_float(row, ["Valoare Stoc Rezervat"])
        stock_entry_date = parse_date(row.get("DATA INTRARE STOC"))
        last_supplier_network_sale_date = parse_date(row.get("ULTIMA VANZARE FURNIZOR_RETEA (data aviz)"))
        payload = (
            snapshot_key(path, row_num, sku_id, store_id),
            str(path),
            row_num,
            snapshot_date,
            "current_snapshot",
            store_id,
            store_type,
            sku_id,
            null_if_empty(row.get("DENUMIRE ARTICOL")),
            null_if_empty(row.get("CATEGORIE")),
            null_if_empty(row.get("CLASA")),
            null_if_empty(row.get("SUBCLASA")),
            null_if_empty(row.get("SUBSTIL")),
            null_if_empty(row.get("CAMPANIE")),
            null_if_empty(row.get("VECHIME IN COLECTIE")),
            stock_entry_date,
            first_float(row, ["NR ZILE STOC"]),
            supplier_available,
            available_store,
            total_store,
            sellable,
            outlet_available,
            position_stock,
            reserved_qty,
            reserved_value,
            first_float(row, ["Viteza de Rotatie Stoc Magazine (M12)"]),
            first_float(row, ["LUNI STOC FURNIZOR"]),
            first_float(row, ["LUNI STOC GENERAL"]),
            first_float(row, ["MEDIU VANZARE", "Vanzari Cantitative Magazine 2024 (client final)"]),
            last_supplier_network_sale_date,
            json.dumps(row, ensure_ascii=False, sort_keys=True),
        )
        batch.append(payload)
        records_inserted += 1
        if len(batch) >= 5000:
            conn.executemany(insert_sql, batch)
            batch.clear()

    if batch:
        conn.executemany(insert_sql, batch)
    return StockImportStats(
        file_name=path.name,
        source_kind="stock_snapshot",
        rows_seen=rows_seen,
        records_inserted=records_inserted,
        records_skipped=records_skipped,
        stores_seen=len(stores),
        skus_seen=len(skus),
        feature_scope="current_snapshot",
    )


def previous_stock_month(target_start: str) -> str:
    start = datetime.strptime(target_start, "%Y-%m-%d").date()
    first_of_month = start.replace(day=1)
    previous_day = first_of_month.fromordinal(first_of_month.toordinal() - 1)
    return previous_day.replace(day=1).strftime("%Y-%m-%d")


def table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


def headline_or_proxy_skus(conn: sqlite3.Connection, target_start: str) -> tuple[set[str], str]:
    start = datetime.strptime(target_start, "%Y-%m-%d").date()
    as_of_week = (start - timedelta(days=7)).strftime("%Y-%m-%d")
    if table_exists(conn, "forecast_v2_regime_labels"):
        rows = conn.execute(
            """
            SELECT sku_id
            FROM forecast_v2_regime_labels
            WHERE as_of_week = ? AND rule_version = ? AND headline_eligible = 1
            """,
            (as_of_week, RULE_VERSION),
        ).fetchall()
        if rows:
            return {str(row[0]) for row in rows}, "cached_headline"

    load_start = (start - timedelta(days=7) - timedelta(weeks=52)).strftime("%Y-%m-%d")
    rows = conn.execute(
        """
        SELECT sku_id
        FROM weekly_chain_demand_v2
        WHERE week_start >= ? AND week_start <= ?
        GROUP BY sku_id
        HAVING
            SUM(CASE WHEN net_units > 0 THEN 1 ELSE 0 END) >= 12
            AND SUM(CASE WHEN net_units > 0 THEN net_units ELSE 0 END) >= 26
            AND SUM(net_revenue) > 0
        """,
        (load_start, as_of_week),
    ).fetchall()
    return {str(row[0]) for row in rows}, "fast_forecastable_proxy"


def _fmt_num(value: object, digits: int = 1) -> str:
    if value is None:
        return "-"
    if isinstance(value, int):
        return f"{value:,}"
    try:
        return f"{float(value):,.{digits}f}"
    except (TypeError, ValueError):
        return str(value)


def _fmt_pct(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value * 100:.1f}%"


def _table(headers: list[str], rows: list[list[str]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(lines)


def monthly_stock_context_coverage(conn: sqlite3.Connection, target_starts: list[str]) -> list[list[str]]:
    rows: list[list[str]] = []
    try:
        conn.execute("SELECT 1 FROM weekly_chain_demand_v2 LIMIT 1").fetchone()
    except sqlite3.OperationalError:
        return rows
    for target_start in target_starts:
        label_skus, population_source = headline_or_proxy_skus(conn, target_start)
        if not label_skus:
            rows.append([target_start, previous_stock_month(target_start), population_source, "0", "0", "-"])
            continue
        month = previous_stock_month(target_start)
        stocked = {
            row[0]
            for row in conn.execute(
                "SELECT DISTINCT sku_id FROM stock_monthly_store_v2 WHERE stock_month = ?",
                (month,),
            ).fetchall()
        }
        overlap = len(label_skus & stocked)
        rows.append(
            [
                target_start,
                month,
                population_source,
                _fmt_num(len(label_skus), 0),
                _fmt_num(overlap, 0),
                _fmt_pct(overlap / len(label_skus) if label_skus else None),
            ]
        )
    return rows


def build_report(conn: sqlite3.Connection, target_starts: list[str]) -> str:
    source_rows = []
    for row in conn.execute(
        """
        SELECT file_name, source_kind, feature_scope, rows_seen, records_inserted,
               records_skipped, stores_seen, skus_seen, first_stock_month, last_stock_month
        FROM stock_source_files_v2
        ORDER BY source_kind, file_name
        """
    ):
        source_rows.append(
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

    monthly_rows = []
    for row in conn.execute(
        """
        SELECT store_id, stock_month, COUNT(*) AS records, COUNT(DISTINCT sku_id) AS skus,
               SUM(CASE WHEN stock_qty = 0 THEN 1 ELSE 0 END) AS zero_records,
               SUM(CASE WHEN stock_qty < 0 THEN 1 ELSE 0 END) AS negative_records,
               SUM(stock_qty) AS stock_qty
        FROM stock_monthly_store_v2
        GROUP BY store_id, stock_month
        ORDER BY store_id, stock_month
        """
    ):
        monthly_rows.append(
            [
                str(row[0]),
                str(row[1]),
                _fmt_num(row[2], 0),
                _fmt_num(row[3], 0),
                _fmt_num(row[4], 0),
                _fmt_num(row[5], 0),
                _fmt_num(row[6]),
            ]
        )

    overlap_rows = []
    try:
        sales_skus = conn.execute(
            "SELECT COUNT(DISTINCT sku_id) FROM raw_sales_transactions_v2 WHERE is_non_product = 0"
        ).fetchone()[0]
        stock_skus = conn.execute("SELECT COUNT(DISTINCT sku_id) FROM stock_monthly_store_v2").fetchone()[0]
        overlap = conn.execute(
            """
            SELECT COUNT(DISTINCT s.sku_id)
            FROM stock_monthly_store_v2 s
            JOIN raw_sales_transactions_v2 r ON r.sku_id = s.sku_id
            WHERE r.is_non_product = 0
            """
        ).fetchone()[0]
        overlap_rows.append(
            [
                _fmt_num(sales_skus, 0),
                _fmt_num(stock_skus, 0),
                _fmt_num(overlap, 0),
                _fmt_pct(overlap / sales_skus if sales_skus else None),
            ]
        )
    except sqlite3.OperationalError:
        overlap_rows.append(["-", "-", "-", "-"])

    snapshot_rows = []
    for row in conn.execute(
        """
        SELECT store_id, feature_scope, COUNT(*) AS records, COUNT(DISTINCT sku_id) AS skus,
               SUM(CASE WHEN stock_age_days IS NULL THEN 1 ELSE 0 END) AS missing_age,
               SUM(CASE WHEN rotation_m12 IS NULL THEN 1 ELSE 0 END) AS missing_rotation,
               SUM(CASE WHEN supplier_available_qty IS NULL THEN 1 ELSE 0 END) AS missing_supplier
        FROM stock_snapshot_store_v2
        GROUP BY store_id, feature_scope
        ORDER BY store_id, feature_scope
        """
    ):
        records = row[2] or 0
        snapshot_rows.append(
            [
                str(row[0]),
                str(row[1]),
                _fmt_num(records, 0),
                _fmt_num(row[3], 0),
                _fmt_pct((row[4] or 0) / records if records else None),
                _fmt_pct((row[5] or 0) / records if records else None),
                _fmt_pct((row[6] or 0) / records if records else None),
            ]
        )

    context_rows = monthly_stock_context_coverage(conn, target_starts)
    return "\n".join(
        [
            "# Iteration 5C — V2 Stock Ingestion",
            "",
            "## Source Files",
            "",
            _table(
                ["File", "Kind", "Feature scope", "Rows", "Records", "Skipped", "Stores", "SKUs", "Month range"],
                source_rows,
            ),
            "",
            "## Monthly Store Stock Coverage",
            "",
            _table(
                ["Store", "Stock month", "Records", "SKUs", "Zero records", "Negative records", "Stock qty"],
                monthly_rows,
            ),
            "",
            "## SKU Overlap With Sales",
            "",
            _table(["Sales SKUs", "Monthly stock SKUs", "Overlap SKUs", "Overlap % of sales SKUs"], overlap_rows),
            "",
            "## Headline SKU-Window Stock Context",
            "",
            _table(
                ["Target start", "Previous stock month", "Population source", "SKUs", "With stock context", "Coverage"],
                context_rows,
            ),
            "",
            "## Snapshot / Stock-Age Coverage",
            "",
            _table(
                [
                    "Store",
                    "Feature scope",
                    "Records",
                    "SKUs",
                    "Missing stock age",
                    "Missing rotation",
                    "Missing supplier stock",
                ],
                snapshot_rows,
            ),
            "",
            "## Historical Safety",
            "",
            "- `stock_monthly_store_v2` is treated as historical end-of-month stock and can be used for walk-forward backtests.",
            "- `stock_snapshot_store_v2` is marked `current_snapshot`; it is preserved for future/current forecasts and diagnostics, but not used as historical backtest input.",
            "- Craiova stock is skipped unless Craiova sales exist in `raw_sales_transactions_v2`.",
            "",
            "## Accuracy Report",
            "",
            "Accuracy not re-run. Phases 2 and 3 ingest stock context only; accuracy will be re-measured after stock features are added to the feature matrix.",
        ]
    ) + "\n"


def import_stock_sources(
    input_path: Path = DEFAULT_INPUT,
    db_path: Path = DB_PATH,
    rebuild: bool = False,
    report_path: Path = DEFAULT_REPORT,
    target_starts: list[str] | None = None,
    report_only: bool = False,
) -> None:
    monthly_files, snapshot_files = discover_stock_files(input_path)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    try:
        ensure_stock_tables(conn, rebuild=rebuild)
        if not report_only:
            allowed_stores = existing_sales_stores(conn)
            if not allowed_stores:
                allowed_stores = {normalize_store(raw)[0] for raw in STORE_NAME_HINTS.values()}

            for path in monthly_files:
                stats = import_monthly_file(conn, path, allowed_stores)
                record_source_file(conn, path, stats)
                conn.commit()
            for path in snapshot_files:
                stats = import_snapshot_file(conn, path, allowed_stores)
                record_source_file(conn, path, stats)
                conn.commit()

        report = build_report(conn, target_starts or DEFAULT_TARGET_STARTS)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(report, encoding="utf-8")
        print(report)
        print(f"Wrote {report_path}")
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Import forecast v2 stock CSVs.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--rebuild", action="store_true")
    parser.add_argument("--report-only", action="store_true")
    parser.add_argument("--target-start", action="append", default=None)
    args = parser.parse_args()
    import_stock_sources(
        input_path=args.input,
        db_path=args.db,
        rebuild=args.rebuild,
        report_path=args.report,
        target_starts=args.target_start,
        report_only=args.report_only,
    )


if __name__ == "__main__":
    main()
