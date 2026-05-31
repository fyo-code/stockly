"""Phase 8D supplier monthly stock ingestion and SKU mapping."""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

try:
    from .ingestion import clean_text, parse_float
    from .stock_ingestion import (
        DB_PATH,
        DEFAULT_TARGET_STARTS,
        MONTH_MAP,
        StockImportStats,
        ensure_stock_tables,
        previous_stock_month,
        read_csv_rows,
        record_source_file,
        headline_or_proxy_skus,
    )
except ImportError:  # Allows direct script execution.
    from ingestion import clean_text, parse_float
    from stock_ingestion import (
        DB_PATH,
        DEFAULT_TARGET_STARTS,
        MONTH_MAP,
        StockImportStats,
        ensure_stock_tables,
        previous_stock_month,
        read_csv_rows,
        record_source_file,
        headline_or_proxy_skus,
    )


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = PROJECT_ROOT / "new_stock_data_20may"
DEFAULT_REPORT = PROJECT_ROOT / "active_docs" / "ITER5M_V2_PHASE8D_SUPPLIER_STOCK.md"
PHASE_FILES = [
    "supplier_stock_22.csv",
    "supplier_stock_23.csv",
    "supplier_stock_24.csv",
    "supplier_stock_25.csv",
]
MONTH_LABEL_RE = re.compile(r"^(.+?)\s+(20\d{2})$", re.IGNORECASE)
BASELINE_HIT20 = 0.241
BASELINE_HIT30 = 0.353
BASELINE_WMAPE = 0.561
BASELINE_PHANTOM = 0.481


@dataclass(frozen=True)
class SupplierImportStats:
    file_name: str
    rows_seen: int
    records_inserted: int
    records_skipped: int
    suppliers_seen: int
    products_seen: int
    exact_unique_rows: int
    ambiguous_rows: int
    unmapped_rows: int
    mapped_skus_seen: int
    zero_stock_rows: int
    negative_stock_rows: int
    negative_value_rows: int
    first_stock_month: str | None
    last_stock_month: str | None


def strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def norm_key(value: object) -> str:
    if value is None:
        return ""
    text = strip_accents(str(value)).upper().strip()
    text = re.sub(r"\s+", " ", text)
    return text


def month_from_label(value: object) -> str | None:
    if value is None:
        return None
    text = strip_accents(str(value)).upper().strip()
    match = MONTH_LABEL_RE.match(text)
    if not match:
        return None
    month_name = re.sub(r"[^A-Z]+", " ", match.group(1)).strip().split(" ")[0]
    month = MONTH_MAP.get(month_name)
    if month is None:
        return None
    return f"{int(match.group(2)):04d}-{month:02d}-01"


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


def ensure_supplier_tables(conn: sqlite3.Connection, rebuild: bool = False) -> None:
    ensure_stock_tables(conn, rebuild=False)
    if rebuild:
        conn.executescript(
            """
            DROP TABLE IF EXISTS stock_monthly_supplier_v2;
            DROP TABLE IF EXISTS supplier_stock_sku_map_v2;
            """
        )
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS supplier_stock_sku_map_v2 (
            product_name_key TEXT PRIMARY KEY,
            supplier_product_name TEXT NOT NULL,
            mapping_confidence TEXT NOT NULL,
            sku_id TEXT,
            candidate_sku_count INTEGER NOT NULL,
            candidate_skus_json TEXT NOT NULL,
            raw_sales_name_count INTEGER NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_supplier_stock_map_confidence
            ON supplier_stock_sku_map_v2(mapping_confidence);
        CREATE INDEX IF NOT EXISTS idx_supplier_stock_map_sku
            ON supplier_stock_sku_map_v2(sku_id);

        CREATE TABLE IF NOT EXISTS stock_monthly_supplier_v2 (
            stock_month TEXT NOT NULL,
            supplier_name TEXT NOT NULL,
            supplier_key TEXT NOT NULL,
            product_name_key TEXT NOT NULL,
            supplier_product_name TEXT NOT NULL,
            sku_id TEXT,
            mapping_confidence TEXT NOT NULL,
            supplier_stock_qty REAL NOT NULL,
            supplier_stock_value REAL,
            source_file TEXT NOT NULL,
            source_row_count INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            PRIMARY KEY (stock_month, supplier_key, product_name_key, source_file)
        );

        CREATE INDEX IF NOT EXISTS idx_stock_supplier_sku_month
            ON stock_monthly_supplier_v2(sku_id, stock_month);
        CREATE INDEX IF NOT EXISTS idx_stock_supplier_month_confidence
            ON stock_monthly_supplier_v2(stock_month, mapping_confidence);
        CREATE INDEX IF NOT EXISTS idx_stock_supplier_product_key
            ON stock_monthly_supplier_v2(product_name_key);
        """
    )
    conn.commit()


def load_sales_name_map(conn: sqlite3.Connection) -> tuple[dict[str, set[str]], dict[str, int]]:
    name_to_skus: dict[str, set[str]] = {}
    name_variants: dict[str, set[str]] = {}
    for product_name, sku_id in conn.execute(
        """
        SELECT DISTINCT product_name, sku_id
        FROM raw_sales_transactions_v2
        WHERE product_name IS NOT NULL
          AND sku_id IS NOT NULL
          AND is_non_product = 0
        """
    ):
        key = norm_key(product_name)
        if not key:
            continue
        name_to_skus.setdefault(key, set()).add(str(sku_id))
        name_variants.setdefault(key, set()).add(str(product_name))
    return name_to_skus, {key: len(names) for key, names in name_variants.items()}


def mapping_for_key(
    product_name_key: str,
    name_to_skus: dict[str, set[str]],
) -> tuple[str, str | None, list[str]]:
    candidates = sorted(name_to_skus.get(product_name_key, set()))
    if len(candidates) == 1:
        return "exact_unique", candidates[0], candidates
    if candidates:
        return "ambiguous", None, candidates
    return "unmapped", None, []


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
        conn.execute("DELETE FROM stock_monthly_supplier_v2 WHERE source_file = ?", (source_key,))
        conn.execute("DELETE FROM stock_source_files_v2 WHERE source_file = ?", (source_key,))
        deleted += conn.total_changes - before
    return deleted


def _insert_mapping_rows(
    conn: sqlite3.Connection,
    rows: list[tuple[str, str, str, str | None, int, str, int]],
) -> None:
    if not rows:
        return
    conn.executemany(
        """
        INSERT INTO supplier_stock_sku_map_v2 (
            product_name_key, supplier_product_name, mapping_confidence, sku_id,
            candidate_sku_count, candidate_skus_json, raw_sales_name_count, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
        ON CONFLICT(product_name_key) DO UPDATE SET
            supplier_product_name = excluded.supplier_product_name,
            mapping_confidence = excluded.mapping_confidence,
            sku_id = excluded.sku_id,
            candidate_sku_count = excluded.candidate_sku_count,
            candidate_skus_json = excluded.candidate_skus_json,
            raw_sales_name_count = excluded.raw_sales_name_count,
            created_at = datetime('now')
        """,
        rows,
    )


def import_supplier_file(
    conn: sqlite3.Connection,
    path: Path,
    name_to_skus: dict[str, set[str]],
    name_variant_counts: dict[str, int],
    mapped_keys_seen: set[str],
) -> SupplierImportStats:
    insert_stock_sql = """
        INSERT INTO stock_monthly_supplier_v2 (
            stock_month, supplier_name, supplier_key, product_name_key,
            supplier_product_name, sku_id, mapping_confidence, supplier_stock_qty,
            supplier_stock_value, source_file, source_row_count, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, datetime('now'))
        ON CONFLICT(stock_month, supplier_key, product_name_key, source_file)
        DO UPDATE SET
            supplier_stock_qty = supplier_stock_qty + excluded.supplier_stock_qty,
            supplier_stock_value = COALESCE(supplier_stock_value, 0) + COALESCE(excluded.supplier_stock_value, 0),
            source_row_count = source_row_count + 1
    """
    rows_seen = records_inserted = records_skipped = 0
    exact_unique_rows = ambiguous_rows = unmapped_rows = 0
    zero_stock_rows = negative_stock_rows = negative_value_rows = 0
    suppliers: set[str] = set()
    products: set[str] = set()
    mapped_skus: set[str] = set()
    first_month: str | None = None
    last_month: str | None = None
    stock_batch: list[tuple[object, ...]] = []
    map_batch: list[tuple[str, str, str, str | None, int, str, int]] = []

    for _, row in read_csv_rows(path):
        if not any(row.values()):
            continue
        rows_seen += 1
        stock_month = month_from_label(row.get("PERIOADA PERIOADA"))
        supplier_name = clean_text(row.get("IMPORTATOR_PRODUCATOR"))
        supplier_key = norm_key(supplier_name)
        product_name = clean_text(row.get("ARTICOL DENUMIRE"))
        product_name_key = norm_key(product_name)
        stock_qty = parse_float(row.get("STOC"))
        stock_value = parse_float(row.get("VALOARE STOC"))
        if not stock_month or not supplier_key or not product_name_key or stock_qty is None:
            records_skipped += 1
            continue

        mapping_confidence, sku_id, candidates = mapping_for_key(product_name_key, name_to_skus)
        if mapping_confidence == "exact_unique":
            exact_unique_rows += 1
            if sku_id:
                mapped_skus.add(sku_id)
        elif mapping_confidence == "ambiguous":
            ambiguous_rows += 1
        else:
            unmapped_rows += 1

        if product_name_key not in mapped_keys_seen:
            mapped_keys_seen.add(product_name_key)
            map_batch.append(
                (
                    product_name_key,
                    product_name,
                    mapping_confidence,
                    sku_id,
                    len(candidates),
                    json.dumps(candidates, ensure_ascii=False),
                    name_variant_counts.get(product_name_key, 0),
                )
            )
            if len(map_batch) >= 5000:
                _insert_mapping_rows(conn, map_batch)
                map_batch.clear()

        suppliers.add(supplier_key)
        products.add(product_name_key)
        if stock_qty == 0:
            zero_stock_rows += 1
        if stock_qty < 0:
            negative_stock_rows += 1
        if stock_value is not None and stock_value < 0:
            negative_value_rows += 1
        first_month = stock_month if first_month is None or stock_month < first_month else first_month
        last_month = stock_month if last_month is None or stock_month > last_month else last_month
        stock_batch.append(
            (
                stock_month,
                supplier_name,
                supplier_key,
                product_name_key,
                product_name,
                sku_id,
                mapping_confidence,
                stock_qty,
                stock_value,
                str(path),
            )
        )
        records_inserted += 1
        if len(stock_batch) >= 20000:
            conn.executemany(insert_stock_sql, stock_batch)
            stock_batch.clear()

    if map_batch:
        _insert_mapping_rows(conn, map_batch)
    if stock_batch:
        conn.executemany(insert_stock_sql, stock_batch)

    return SupplierImportStats(
        file_name=path.name,
        rows_seen=rows_seen,
        records_inserted=records_inserted,
        records_skipped=records_skipped,
        suppliers_seen=len(suppliers),
        products_seen=len(products),
        exact_unique_rows=exact_unique_rows,
        ambiguous_rows=ambiguous_rows,
        unmapped_rows=unmapped_rows,
        mapped_skus_seen=len(mapped_skus),
        zero_stock_rows=zero_stock_rows,
        negative_stock_rows=negative_stock_rows,
        negative_value_rows=negative_value_rows,
        first_stock_month=first_month,
        last_stock_month=last_month,
    )


def _source_file_stats(stats: SupplierImportStats) -> StockImportStats:
    return StockImportStats(
        file_name=stats.file_name,
        source_kind="monthly_supplier_stock",
        rows_seen=stats.rows_seen,
        records_inserted=stats.records_inserted,
        records_skipped=stats.records_skipped,
        stores_seen=stats.suppliers_seen,
        skus_seen=stats.mapped_skus_seen,
        first_stock_month=stats.first_stock_month,
        last_stock_month=stats.last_stock_month,
        feature_scope="historical_backtest",
    )


def source_rows(stats_by_path: list[tuple[Path, SupplierImportStats, int]]) -> list[list[str]]:
    rows: list[list[str]] = []
    for path, stats, deleted_rows in stats_by_path:
        rows.append(
            [
                path.name,
                _fmt_num(stats.rows_seen, 0),
                _fmt_num(stats.records_inserted, 0),
                _fmt_num(stats.records_skipped, 0),
                _fmt_num(stats.suppliers_seen, 0),
                _fmt_num(stats.products_seen, 0),
                _fmt_num(stats.mapped_skus_seen, 0),
                _fmt_num(stats.exact_unique_rows, 0),
                _fmt_num(stats.ambiguous_rows, 0),
                _fmt_num(stats.unmapped_rows, 0),
                f"{stats.first_stock_month or '-'}..{stats.last_stock_month or '-'}",
                _fmt_num(deleted_rows, 0),
            ]
        )
    return rows


def mapping_summary_rows(conn: sqlite3.Connection) -> list[list[str]]:
    rows: list[list[str]] = []
    for row in conn.execute(
        """
        SELECT
            mapping_confidence,
            COUNT(*) AS product_keys,
            COUNT(DISTINCT sku_id) AS exact_skus,
            SUM(candidate_sku_count) AS candidate_sku_links,
            SUM(raw_sales_name_count) AS raw_name_variants
        FROM supplier_stock_sku_map_v2
        GROUP BY mapping_confidence
        ORDER BY
            CASE mapping_confidence
                WHEN 'exact_unique' THEN 1
                WHEN 'ambiguous' THEN 2
                ELSE 3
            END
        """
    ):
        rows.append(
            [
                str(row[0]),
                _fmt_num(row[1], 0),
                _fmt_num(row[2], 0),
                _fmt_num(row[3], 0),
                _fmt_num(row[4], 0),
            ]
        )
    return rows


def year_summary_rows(conn: sqlite3.Connection) -> list[list[str]]:
    rows: list[list[str]] = []
    for row in conn.execute(
        """
        SELECT
            substr(stock_month, 1, 4) AS stock_year,
            COUNT(*) AS records,
            COUNT(DISTINCT supplier_key) AS suppliers,
            COUNT(DISTINCT product_name_key) AS products,
            COUNT(DISTINCT CASE WHEN mapping_confidence = 'exact_unique' THEN sku_id END) AS exact_skus,
            SUM(CASE WHEN mapping_confidence = 'exact_unique' THEN 1 ELSE 0 END) AS exact_rows,
            SUM(CASE WHEN mapping_confidence = 'ambiguous' THEN 1 ELSE 0 END) AS ambiguous_rows,
            SUM(CASE WHEN mapping_confidence = 'unmapped' THEN 1 ELSE 0 END) AS unmapped_rows,
            SUM(CASE WHEN supplier_stock_qty = 0 THEN 1 ELSE 0 END) AS zero_rows,
            SUM(CASE WHEN supplier_stock_qty < 0 THEN 1 ELSE 0 END) AS negative_stock_rows,
            SUM(CASE WHEN supplier_stock_value < 0 THEN 1 ELSE 0 END) AS negative_value_rows,
            SUM(supplier_stock_qty) AS total_stock_qty
        FROM stock_monthly_supplier_v2
        GROUP BY stock_year
        ORDER BY stock_year
        """
    ):
        records = row[1] or 0
        rows.append(
            [
                str(row[0]),
                _fmt_num(records, 0),
                _fmt_num(row[2], 0),
                _fmt_num(row[3], 0),
                _fmt_num(row[4], 0),
                _fmt_pct((row[5] or 0) / records if records else None),
                _fmt_pct((row[6] or 0) / records if records else None),
                _fmt_pct((row[7] or 0) / records if records else None),
                _fmt_pct((row[8] or 0) / records if records else None),
                _fmt_num(row[9] or 0, 0),
                _fmt_num(row[10] or 0, 0),
                _fmt_num(row[11]),
            ]
        )
    return rows


def target_coverage_rows(conn: sqlite3.Connection, target_starts: list[str]) -> list[list[str]]:
    rows: list[list[str]] = []
    for target_start in target_starts:
        label_skus, population_source = headline_or_proxy_skus(conn, target_start)
        month = previous_stock_month(target_start)
        supplier_skus = {
            str(row[0])
            for row in conn.execute(
                """
                SELECT DISTINCT sku_id
                FROM stock_monthly_supplier_v2
                WHERE stock_month = ?
                  AND mapping_confidence = 'exact_unique'
                  AND sku_id IS NOT NULL
                """,
                (month,),
            ).fetchall()
        }
        positive_supplier_skus = {
            str(row[0])
            for row in conn.execute(
                """
                SELECT DISTINCT sku_id
                FROM stock_monthly_supplier_v2
                WHERE stock_month = ?
                  AND mapping_confidence = 'exact_unique'
                  AND sku_id IS NOT NULL
                  AND supplier_stock_qty > 0
                """,
                (month,),
            ).fetchall()
        }
        observed_overlap = len(label_skus & supplier_skus)
        positive_overlap = len(label_skus & positive_supplier_skus)
        rows.append(
            [
                target_start,
                month,
                population_source,
                _fmt_num(len(label_skus), 0),
                _fmt_num(observed_overlap, 0),
                _fmt_pct(observed_overlap / len(label_skus) if label_skus else None),
                _fmt_num(positive_overlap, 0),
                _fmt_pct(positive_overlap / len(label_skus) if label_skus else None),
            ]
        )
    return rows


def top_ambiguous_rows(conn: sqlite3.Connection, limit: int = 8) -> list[list[str]]:
    rows: list[list[str]] = []
    for row in conn.execute(
        """
        SELECT
            supplier_product_name,
            candidate_sku_count,
            substr(candidate_skus_json, 1, 90) AS candidates
        FROM supplier_stock_sku_map_v2
        WHERE mapping_confidence = 'ambiguous'
        ORDER BY candidate_sku_count DESC, supplier_product_name
        LIMIT ?
        """,
        (limit,),
    ):
        rows.append([str(row[0])[:80], _fmt_num(row[1], 0), str(row[2])])
    return rows


def build_report(
    conn: sqlite3.Connection,
    stats_by_path: list[tuple[Path, SupplierImportStats, int]],
) -> str:
    total_records = conn.execute("SELECT COUNT(*) FROM stock_monthly_supplier_v2").fetchone()[0]
    exact_skus = conn.execute(
        """
        SELECT COUNT(DISTINCT sku_id)
        FROM stock_monthly_supplier_v2
        WHERE mapping_confidence = 'exact_unique' AND sku_id IS NOT NULL
        """
    ).fetchone()[0]
    total_products = conn.execute("SELECT COUNT(*) FROM supplier_stock_sku_map_v2").fetchone()[0]
    return "\n".join(
        [
            "# Iteration 5M — V2 Phase 8D Supplier Monthly Stock Ingestion",
            "",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            "## Phase Checkpoint",
            "",
            "Phase completed: Phase 8D — supplier monthly stock ingestion and confidence-controlled SKU mapping.",
            "",
            "What changed: supplier stock files for 2022-2025 were normalized into `stock_monthly_supplier_v2`; product-name mappings were stored in `supplier_stock_sku_map_v2` with `exact_unique`, `ambiguous`, or `unmapped` confidence. Only `exact_unique` rows should be used as model features in Phase 8E.",
            "",
            "Accuracy rerun: no. This phase only adds supplier availability data. Accuracy will be re-measured after Phase 8E joins supplier and combined stock features into the model matrix.",
            "",
            _table(
                ["Baseline metric", "Current official control before Phase 8D"],
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
                    "Rows processed",
                    "Skipped",
                    "Suppliers",
                    "Products",
                    "Mapped SKUs",
                    "Exact rows",
                    "Ambiguous rows",
                    "Unmapped rows",
                    "Month range",
                    "Prior rows removed",
                ],
                source_rows(stats_by_path),
            ),
            "",
            "## Mapping Summary",
            "",
            f"Supplier-stock table now contains `{_fmt_num(total_records, 0)}` unique supplier/month/product records across `{_fmt_num(total_products, 0)}` supplier product-name keys. Exact unique mappings cover `{_fmt_num(exact_skus, 0)}` SKUs. Duplicate source rows for the same supplier/month/product key are aggregated into one table record.",
            "",
            _table(
                ["Mapping confidence", "Product keys", "Exact SKUs", "Candidate SKU links", "Raw sales name variants"],
                mapping_summary_rows(conn),
            ),
            "",
            "## Supplier Stock By Year",
            "",
            _table(
                [
                    "Year",
                    "Records",
                    "Suppliers",
                    "Products",
                    "Exact SKUs",
                    "Exact rows %",
                    "Ambiguous rows %",
                    "Unmapped rows %",
                    "Zero-stock rows %",
                    "Negative stock rows",
                    "Negative value rows",
                    "Total stock qty",
                ],
                year_summary_rows(conn),
            ),
            "",
            "## Target-Window Supplier Stock Context",
            "",
            "Because Phase 8B invalidated cached regime labels, this table uses the fast forecastable proxy until the next model rebuild regenerates official labels. `Observed` means an exact SKU mapping exists for the previous completed supplier stock month; `Positive` means that mapped supplier stock quantity is greater than zero.",
            "",
            _table(
                [
                    "Target start",
                    "Previous stock month",
                    "Population source",
                    "SKUs",
                    "Observed supplier stock",
                    "Observed coverage",
                    "Positive supplier stock",
                    "Positive coverage",
                ],
                target_coverage_rows(conn, DEFAULT_TARGET_STARTS),
            ),
            "",
            "## Ambiguous Mapping Examples",
            "",
            _table(["Supplier product name", "Candidate SKU count", "Candidate SKUs preview"], top_ambiguous_rows(conn)),
            "",
            "## Historical Safety",
            "",
            "- Supplier files are treated as historical monthly supplier stock.",
            "- Phase 8E must only use stock months before the target window.",
            "- Exact unique mappings are feature-safe for the first model pass.",
            "- Ambiguous and unmapped rows are stored for review and coverage reporting, but excluded from official historical features until resolved.",
            "",
            "## Accuracy Report",
            "",
            "Accuracy not re-run. Official baseline remains `sk_blend_post_bf_safe`: hit +/-20 = 24.1%, hit +/-30 = 35.3%, WMAPE = 56.1%, phantom rate = 48.1%.",
        ]
    ) + "\n"


def run_phase8d(input_dir: Path = DEFAULT_INPUT, db_path: Path = DB_PATH, report_path: Path = DEFAULT_REPORT) -> None:
    paths = [(input_dir / file_name).resolve() for file_name in PHASE_FILES]
    missing = [str(path) for path in paths if not path.exists()]
    if missing:
        raise FileNotFoundError("Missing Phase 8D input files: " + ", ".join(missing))

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA busy_timeout=60000")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    try:
        ensure_supplier_tables(conn, rebuild=False)
        conn.execute("DELETE FROM supplier_stock_sku_map_v2")
        conn.commit()

        name_to_skus, name_variant_counts = load_sales_name_map(conn)
        mapped_keys_seen: set[str] = set()
        stats_by_path: list[tuple[Path, SupplierImportStats, int]] = []
        for path in paths:
            deleted_rows = _delete_previous_source_rows(conn, path)
            stats = import_supplier_file(conn, path, name_to_skus, name_variant_counts, mapped_keys_seen)
            record_source_file(conn, path, _source_file_stats(stats))
            conn.commit()
            stats_by_path.append((path, stats, deleted_rows))

        report = build_report(conn, stats_by_path)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(report, encoding="utf-8")
        print(report)
        print(f"Wrote {report_path}")
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Import Forecast V2 Phase 8D supplier monthly stock files.")
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    run_phase8d(input_dir=args.input_dir, db_path=args.db, report_path=args.report)


if __name__ == "__main__":
    main()
