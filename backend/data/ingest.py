"""
CSV ingestion pipeline.
Reads the 4 CSV files from data_samples/, validates, and loads into SQLite.
Run once to seed the database. Safe to re-run — clears and reloads.
"""

import csv
import logging
import os
import sqlite3
from datetime import date, datetime
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

ROOT        = Path(__file__).parent.parent.parent
DATA_DIR    = ROOT / "data_samples"
SCHEMA_FILE = Path(__file__).parent / "schema.sql"
DB_PATH     = Path(__file__).parent / "supply_chain.db"


# ── Helpers ────────────────────────────────────────────────────────────────────

def parse_date(val: str) -> str | None:
    """Normalise date string to ISO format YYYY-MM-DD. Returns None on failure."""
    if not val or not val.strip():
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(val.strip(), fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    log.warning("Unrecognised date format: %s", val)
    return None


def safe_int(val: str, default: int = 0) -> int:
    try:
        return int(float(val)) if val and val.strip() else default
    except (ValueError, TypeError):
        return default


def safe_float(val: str, default: float = 0.0) -> float:
    try:
        return float(val) if val and val.strip() else default
    except (ValueError, TypeError):
        return default


def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(f"Missing CSV: {path}")
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


# ── Loaders ────────────────────────────────────────────────────────────────────

def load_suppliers(conn: sqlite3.Connection, rows: list[dict]) -> int:
    conn.execute("DELETE FROM suppliers")
    data = []
    for r in rows:
        sid = r.get("supplier_id", "").strip()
        if not sid:
            continue
        data.append((
            sid,
            r.get("supplier_name", "").strip(),
            r.get("country", "").strip(),
            safe_int(r.get("default_return_window_days", "90"), 90),
            r.get("preferred_language", "").strip() or None,
        ))
    conn.executemany(
        "INSERT INTO suppliers VALUES (?,?,?,?,?)", data
    )
    return len(data)


def load_skus_and_stores(
    conn: sqlite3.Connection,
    sales_rows: list[dict],
    inventory_rows: list[dict],
) -> tuple[int, int]:
    """Extract unique SKUs (with supplier_id from inventory) and stores from sales rows."""
    conn.execute("DELETE FROM skus")
    conn.execute("DELETE FROM stores")

    # Build supplier_id lookup from inventory (sku_id → supplier_id)
    sku_supplier: dict[str, str] = {}
    for r in inventory_rows:
        sid = r.get("sku_id", "").strip()
        sup = r.get("supplier_id", "").strip()
        if sid and sup:
            sku_supplier[sid] = sup

    skus: dict[str, tuple] = {}
    stores: set[str] = set()

    for r in sales_rows:
        sid = r.get("sku_id", "").strip()
        store = r.get("store_id", "").strip()
        if store:
            stores.add(store)
        if not sid or sid in skus:
            continue
        supplier_id = sku_supplier.get(sid)
        if not supplier_id:
            continue  # skip SKU if no supplier mapping found
        skus[sid] = (
            sid,
            r.get("sku_name", "").strip(),
            r.get("category", "").strip(),
            supplier_id,
            safe_float(r.get("selling_price_lei", "0")),
            safe_float(r.get("purchase_cost_lei", "0")),
        )

    conn.executemany("INSERT OR IGNORE INTO skus VALUES (?,?,?,?,?,?)", list(skus.values()))
    conn.executemany(
        "INSERT OR IGNORE INTO stores(store_id) VALUES (?)",
        [(s,) for s in stores if s]
    )
    return len(skus), len(stores)


def load_sales(conn: sqlite3.Connection, rows: list[dict]) -> int:
    conn.execute("DELETE FROM sales")
    data = []
    skipped = 0
    for r in rows:
        sku_id = r.get("sku_id", "").strip()
        store_id = r.get("store_id", "").strip()
        sale_date = parse_date(r.get("sale_date", ""))
        if not sku_id or not store_id or not sale_date:
            skipped += 1
            continue
        units_sold = safe_int(r.get("units_sold", "0"))
        units_returned = safe_int(r.get("units_returned", "0"))
        # Guard: returns can't exceed sales
        units_returned = min(units_returned, units_sold)
        data.append((
            sku_id, store_id, sale_date,
            units_sold, units_returned,
            r.get("return_reason", "").strip() or None,
            safe_float(r.get("selling_price_lei", "0")),
            safe_float(r.get("purchase_cost_lei", "0")),
        ))
    if skipped:
        log.warning("Skipped %d sales rows (missing required fields)", skipped)
    conn.executemany(
        "INSERT INTO sales(sku_id,store_id,sale_date,units_sold,units_returned,"
        "return_reason,selling_price_lei,purchase_cost_lei) VALUES (?,?,?,?,?,?,?,?)",
        data
    )
    return len(data)


def load_inventory(conn: sqlite3.Connection, rows: list[dict]) -> int:
    conn.execute("DELETE FROM inventory")
    data = []
    skipped = 0
    for r in rows:
        sku_id = r.get("sku_id", "").strip()
        store_id = r.get("store_id", "").strip()
        if not sku_id or not store_id:
            skipped += 1
            continue
        data.append((
            sku_id, store_id,
            safe_int(r.get("units_in_stock", "0")),
            parse_date(r.get("last_delivery_date", "")),
            r.get("supplier_id", "").strip() or None,
        ))
    if skipped:
        log.warning("Skipped %d inventory rows (missing required fields)", skipped)
    conn.executemany(
        "INSERT OR REPLACE INTO inventory(sku_id,store_id,units_in_stock,"
        "last_delivery_date,supplier_id) VALUES (?,?,?,?,?)",
        data
    )
    return len(data)


def load_supplier_orders(conn: sqlite3.Connection, rows: list[dict]) -> int:
    conn.execute("DELETE FROM supplier_orders")
    data = []
    skipped = 0
    for r in rows:
        order_id = r.get("order_id", "").strip()
        supplier_id = r.get("supplier_id", "").strip()
        sku_id = r.get("sku_id", "").strip()
        order_date = parse_date(r.get("order_date", ""))
        promised = parse_date(r.get("promised_delivery_date", ""))
        if not all([order_id, supplier_id, sku_id, order_date, promised]):
            skipped += 1
            continue
        data.append((
            order_id, supplier_id, sku_id,
            order_date, promised,
            parse_date(r.get("actual_delivery_date", "")),
            safe_int(r.get("units_ordered", "0")),
            safe_int(r.get("units_delivered", "0")) or None,
        ))
    if skipped:
        log.warning("Skipped %d order rows (missing required fields)", skipped)
    conn.executemany(
        "INSERT OR IGNORE INTO supplier_orders VALUES (?,?,?,?,?,?,?,?)",
        data
    )
    return len(data)


# ── Main ───────────────────────────────────────────────────────────────────────

def run_ingest(db_path: Path = DB_PATH, data_dir: Path = DATA_DIR) -> None:
    log.info("Connecting to database: %s", db_path)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")

    # Apply schema
    with open(SCHEMA_FILE) as f:
        conn.executescript(f.read())
    log.info("Schema applied")

    try:
        # Load in dependency order
        suppliers = read_csv(data_dir / "suppliers.csv")
        n = load_suppliers(conn, suppliers)
        log.info("Suppliers: %d loaded", n)

        # SKUs and stores — need both sales and inventory to get supplier mapping
        sales_raw = read_csv(data_dir / "sales_data.csv")
        inventory_raw = read_csv(data_dir / "inventory_data.csv")
        n_skus, n_stores = load_skus_and_stores(conn, sales_raw, inventory_raw)
        log.info("SKUs: %d | Stores: %d", n_skus, n_stores)

        n = load_sales(conn, sales_raw)
        log.info("Sales rows: %d loaded", n)

        n = load_inventory(conn, inventory_raw)
        log.info("Inventory rows: %d loaded", n)

        orders_raw = read_csv(data_dir / "supplier_orders.csv")
        n = load_supplier_orders(conn, orders_raw)
        log.info("Supplier orders: %d loaded", n)

        conn.commit()
        log.info("Ingest complete. Database: %s", db_path)

    except Exception as e:
        conn.rollback()
        log.error("Ingest failed: %s", e)
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    run_ingest()
