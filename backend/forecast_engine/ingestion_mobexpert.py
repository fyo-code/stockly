"""
Mobexpert CSV ingestion pipeline — Full 2024 data.

Reads Mobexpert CSV exports and loads sales data into SQLite with:
- Null-date filtering
- Service/discount/transport filtering
- Zero-revenue filtering
- Category normalization (58 variants → 10 canonical)
- Weekly aggregation for forecasting

Usage:
    python3 backend/forecast_engine/ingestion_mobexpert.py sales_2024_and_nulls.csv [--rebuild]

    --rebuild: Drop and recreate tables before ingesting (fresh start)
"""

import csv
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

from category_normalizer import normalize_category

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s"
)
log = logging.getLogger(__name__)


# -------------------------------------------------------------------
# Parsing helpers
# -------------------------------------------------------------------

def parse_mobexpert_date(date_str: str) -> Optional[str]:
    """Parse DD.MM.YYYY to ISO YYYY-MM-DD. Returns None for #null or invalid."""
    if not date_str or date_str.strip() == "#null":
        return None
    try:
        return datetime.strptime(date_str.strip(), "%d.%m.%Y").strftime("%Y-%m-%d")
    except ValueError:
        log.warning(f"Invalid date format: {date_str}")
        return None


def safe_float(val: str, default: float = 0.0) -> float:
    if not val or val.strip() in ("#null", ""):
        return default
    try:
        return float(val.strip().replace(",", "."))
    except (ValueError, AttributeError):
        return default


def safe_int(val: str, default: int = 0) -> int:
    if not val or val.strip() in ("#null", ""):
        return default
    try:
        return int(float(val.strip().replace(",", ".")))
    except (ValueError, AttributeError):
        return default


# -------------------------------------------------------------------
# Filters (must match data_integrity_check.py exactly)
# -------------------------------------------------------------------

SERVICE_KEYWORDS = ["transport", "livrare", "montaj", "discount", "servicii"]


def is_service_row(categorie: str, clasa: str) -> bool:
    """Check if row is service/discount/transport — not a physical product."""
    combined = ((categorie or "") + " " + (clasa or "")).lower()
    return any(kw in combined for kw in SERVICE_KEYWORDS)


# -------------------------------------------------------------------
# Schema
# -------------------------------------------------------------------

def rebuild_tables(conn: sqlite3.Connection):
    """Drop and recreate sales-related tables for fresh ingestion."""
    log.info("Rebuilding tables: sales, skus, suppliers, weekly_demand")
    conn.executescript("""
        DROP TABLE IF EXISTS weekly_demand;
        DROP TABLE IF EXISTS sales;
        DROP TABLE IF EXISTS skus;
        DROP TABLE IF EXISTS suppliers;
        DROP TABLE IF EXISTS stores;

        CREATE TABLE stores (
            store_id   TEXT PRIMARY KEY,
            store_name TEXT
        );

        CREATE TABLE suppliers (
            supplier_id                TEXT PRIMARY KEY,
            supplier_name              TEXT NOT NULL,
            country                    TEXT NOT NULL DEFAULT 'Romania',
            default_return_window_days INTEGER NOT NULL DEFAULT 90,
            preferred_language         TEXT
        );

        CREATE TABLE skus (
            sku_id             TEXT PRIMARY KEY,
            sku_name           TEXT NOT NULL,
            category           TEXT NOT NULL,
            supplier_id        TEXT NOT NULL REFERENCES suppliers(supplier_id),
            selling_price_lei  REAL NOT NULL DEFAULT 0.0,
            purchase_cost_lei  REAL NOT NULL DEFAULT 0.0
        );

        CREATE TABLE sales (
            id                 INTEGER PRIMARY KEY AUTOINCREMENT,
            sku_id             TEXT NOT NULL REFERENCES skus(sku_id),
            store_id           TEXT NOT NULL,
            sale_date          TEXT NOT NULL,
            units_sold         INTEGER NOT NULL DEFAULT 0,
            units_returned     INTEGER NOT NULL DEFAULT 0,
            selling_price_lei  REAL NOT NULL,
            purchase_cost_lei  REAL NOT NULL DEFAULT 0.0
        );

        CREATE TABLE weekly_demand (
            sku_id         TEXT NOT NULL,
            store_id       TEXT NOT NULL,
            category       TEXT NOT NULL,
            week_start     TEXT NOT NULL,
            units_sold     INTEGER NOT NULL DEFAULT 0,
            units_returned INTEGER NOT NULL DEFAULT 0,
            revenue        REAL NOT NULL DEFAULT 0.0,
            num_transactions INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (sku_id, store_id, week_start)
        );

        CREATE INDEX idx_sales_sku ON sales(sku_id);
        CREATE INDEX idx_sales_date ON sales(sale_date);
        CREATE INDEX idx_weekly_sku ON weekly_demand(sku_id);
        CREATE INDEX idx_weekly_category ON weekly_demand(category);
    """)
    conn.commit()


# -------------------------------------------------------------------
# Ingestion
# -------------------------------------------------------------------

def ingest_mobexpert_csv(
    csv_path: str,
    db_path: str,
    store_name: str = "Baneasa Store",
    rebuild: bool = False,
    sku_filter: Optional[set] = None,
) -> Tuple[int, int]:
    """
    Ingest Mobexpert CSV into SQLite.

    Returns (rows_inserted, rows_filtered).
    """
    csv_file = Path(csv_path)
    if not csv_file.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA journal_mode=WAL")

    try:
        if rebuild:
            rebuild_tables(conn)

        cursor = conn.cursor()
        store_id = store_name.replace(" ", "_").lower()
        cursor.execute(
            "INSERT OR IGNORE INTO stores (store_id, store_name) VALUES (?, ?)",
            (store_id, store_name)
        )

        log.info(f"Reading CSV: {csv_path}")
        if sku_filter:
            log.info(f"SKU filter: {len(sku_filter)} SKUs")

        rows_inserted = 0
        rows_filtered = 0
        skus_seen = {}       # sku_id → (category, supplier_id, supplier_name)
        suppliers_seen = {}  # supplier_id → supplier_name
        batch_sales = []
        BATCH_SIZE = 5000

        with open(csv_file, newline="", encoding="utf-8") as f:
            lines = [l for l in f.readlines() if l.strip()]
            reader = csv.DictReader(iter(lines))

            for row in reader:
                date_str = row.get("DATA COMANDA", "").strip()
                sku_id = row.get("COD ARTICOL", "").strip()
                categorie = row.get("CATEGORIE", "").strip()
                clasa = row.get("CLASA", "").strip()
                supplier_name = row.get("FURNIZOR", "").strip()
                supplier_id = row.get("ID FURNIZOR", "").strip()
                quantity = safe_int(row.get("CANTITATE FACTURATA", "0"))
                value = safe_float(row.get("VALOARE FACTURATA", "0"))

                # Filter: null dates
                sale_date = parse_mobexpert_date(date_str)
                if sale_date is None:
                    rows_filtered += 1
                    continue

                # Filter: no SKU
                if not sku_id:
                    rows_filtered += 1
                    continue

                # Filter: SKU filter (if provided)
                if sku_filter and sku_id not in sku_filter:
                    rows_filtered += 1
                    continue

                # Filter: service/discount/transport
                if is_service_row(categorie, clasa):
                    rows_filtered += 1
                    continue

                # Filter: zero revenue (but keep returns)
                if value == 0.0 and quantity >= 0:
                    rows_filtered += 1
                    continue

                # Normalize category
                normalized_cat = normalize_category(categorie, clasa)

                # Ensure supplier exists
                if not supplier_id or supplier_id == "#null":
                    supplier_id = "UNKNOWN"
                    supplier_name = supplier_name or "UNKNOWN"

                if supplier_id not in suppliers_seen:
                    suppliers_seen[supplier_id] = supplier_name or supplier_id
                    cursor.execute(
                        "INSERT OR IGNORE INTO suppliers (supplier_id, supplier_name) VALUES (?, ?)",
                        (supplier_id, suppliers_seen[supplier_id])
                    )

                # Ensure SKU exists (first occurrence sets category)
                if sku_id not in skus_seen:
                    skus_seen[sku_id] = (normalized_cat, supplier_id)
                    cursor.execute(
                        "INSERT OR IGNORE INTO skus (sku_id, sku_name, category, supplier_id) VALUES (?, ?, ?, ?)",
                        (sku_id, sku_id, normalized_cat, supplier_id)
                    )

                # Queue sales row
                batch_sales.append((
                    sku_id,
                    store_id,
                    sale_date,
                    abs(quantity) if quantity > 0 else 0,
                    abs(quantity) if quantity < 0 else 0,
                    abs(value),
                    0.0,
                ))
                rows_inserted += 1

                # Flush batch
                if len(batch_sales) >= BATCH_SIZE:
                    cursor.executemany(
                        """INSERT INTO sales
                           (sku_id, store_id, sale_date, units_sold, units_returned, selling_price_lei, purchase_cost_lei)
                           VALUES (?, ?, ?, ?, ?, ?, ?)""",
                        batch_sales
                    )
                    batch_sales.clear()

        # Flush remaining
        if batch_sales:
            cursor.executemany(
                """INSERT INTO sales
                   (sku_id, store_id, sale_date, units_sold, units_returned, selling_price_lei, purchase_cost_lei)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                batch_sales
            )

        conn.commit()
        log.info(f"✓ Sales ingestion: {rows_inserted:,} inserted, {rows_filtered:,} filtered")
        log.info(f"  SKUs: {len(skus_seen):,}, Suppliers: {len(suppliers_seen):,}")

        return rows_inserted, rows_filtered

    finally:
        conn.close()


# -------------------------------------------------------------------
# Weekly aggregation
# -------------------------------------------------------------------

def aggregate_to_weekly(db_path: str):
    """
    Aggregate daily sales into weekly demand (Monday-start weeks).

    Conservation law: SUM(weekly units/revenue) == SUM(sales units/revenue)
    """
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()

        # Clear existing weekly data
        cursor.execute("DELETE FROM weekly_demand")

        # Aggregate: group by sku, store, week (Monday start)
        # date(sale_date, 'weekday 0', '-6 days') computes the Monday of each week
        cursor.execute("""
            INSERT INTO weekly_demand (sku_id, store_id, category, week_start, units_sold, units_returned, revenue, num_transactions)
            SELECT
                s.sku_id,
                s.store_id,
                sk.category,
                date(s.sale_date, 'weekday 1', '-7 days') AS week_start,
                SUM(s.units_sold),
                SUM(s.units_returned),
                SUM(s.selling_price_lei),
                COUNT(*) AS num_transactions
            FROM sales s
            JOIN skus sk ON s.sku_id = sk.sku_id
            GROUP BY s.sku_id, s.store_id, sk.category, week_start
        """)

        weekly_rows = cursor.execute("SELECT COUNT(*) FROM weekly_demand").fetchone()[0]
        weekly_skus = cursor.execute("SELECT COUNT(DISTINCT sku_id) FROM weekly_demand").fetchone()[0]
        weekly_weeks = cursor.execute("SELECT COUNT(DISTINCT week_start) FROM weekly_demand").fetchone()[0]

        # Verify conservation
        sales_units = cursor.execute("SELECT SUM(units_sold) - SUM(units_returned) FROM sales").fetchone()[0] or 0
        weekly_units = cursor.execute("SELECT SUM(units_sold) - SUM(units_returned) FROM weekly_demand").fetchone()[0] or 0
        sales_revenue = cursor.execute("SELECT SUM(selling_price_lei) FROM sales").fetchone()[0] or 0.0
        weekly_revenue = cursor.execute("SELECT SUM(revenue) FROM weekly_demand").fetchone()[0] or 0.0

        conn.commit()

        log.info(f"✓ Weekly aggregation: {weekly_rows:,} rows, {weekly_skus:,} SKUs, {weekly_weeks} weeks")
        log.info(f"  Conservation check — units: sales={sales_units:,}, weekly={weekly_units:,}, match={sales_units == weekly_units}")
        log.info(f"  Conservation check — revenue: sales={sales_revenue:,.2f}, weekly={weekly_revenue:,.2f}, match={abs(sales_revenue - weekly_revenue) < 0.01}")

        if sales_units != weekly_units:
            log.error(f"  ✗ UNIT CONSERVATION FAILED: diff={weekly_units - sales_units}")
        if abs(sales_revenue - weekly_revenue) > 0.01:
            log.error(f"  ✗ REVENUE CONSERVATION FAILED: diff={weekly_revenue - sales_revenue:.2f}")

    finally:
        conn.close()


# -------------------------------------------------------------------
# Main
# -------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python ingestion_mobexpert.py <csv_path> [--rebuild] [--skip-weekly]")
        sys.exit(1)

    csv_path = sys.argv[1]
    do_rebuild = "--rebuild" in sys.argv
    skip_weekly = "--skip-weekly" in sys.argv
    db_path = "backend/data/supply_chain.db"

    try:
        inserted, filtered = ingest_mobexpert_csv(
            csv_path, db_path, rebuild=do_rebuild
        )
        print(f"\nIngestion Summary:")
        print(f"  Inserted: {inserted:,}")
        print(f"  Filtered: {filtered:,}")
        print(f"  Total:    {inserted + filtered:,}")

        if not skip_weekly:
            print("\nAggregating to weekly demand...")
            aggregate_to_weekly(db_path)

        print("\nDone.")

    except Exception as e:
        log.error(f"Failed: {e}", exc_info=True)
        sys.exit(1)
