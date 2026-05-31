"""Forecast v2 multi-store Mobexpert ingestion.

This module is intentionally isolated from the legacy `sales` and
`weekly_demand` tables. It imports the richer multi-store CSV exports into v2
tables, preserving optional fields while normalizing the core transaction
shape used by the rebuild plan.

Usage:
    PYTHONPATH=backend python3 backend/forecast_engine_v2/ingestion.py \
        --input "9 stores full info ( pipera not full)" --rebuild

    PYTHONPATH=backend python3 backend/forecast_engine_v2/ingestion.py \
        --input "9 stores full info ( pipera not full)" --dry-run
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import logging
import math
import re
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterable

try:
    from .feature_signals import classify_campaign_signals
    from .hierarchy_normalizer import normalize_hierarchy
except ImportError:  # Allows direct script execution.
    from feature_signals import classify_campaign_signals
    from hierarchy_normalizer import normalize_hierarchy


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
log = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "backend" / "data" / "supply_chain.db"
DEFAULT_INPUT = PROJECT_ROOT / "9 stores full info ( pipera not full)"
DEFAULT_IMPORT_REPORT = PROJECT_ROOT / "active_docs" / "ITER5C_V2_IMPORT_VALIDATION.md"


STORE_MAP = {
    "M & D RETAIL CONSTANTA SRL": ("constanta", "hyperstore"),
    "M & D RETAIL BRASOV SRL": ("brasov", "hyperstore"),
    "M & D RETAIL PIPERA SRL": ("pipera", "hyperstore"),
    "M & D RETAIL PANTELIMON SRL": ("pantelemon", "hyperstore"),
    "MOBEXPERT BANEASA SRL": ("baneasa", "hyperstore"),
    "M & D RETAIL MILITARI SRL": ("militari", "hyperstore"),
    "M & D RETAIL SIBIU SRL": ("sibiu", "hyperstore"),
    "M & D RETAIL ORADEA SRL": ("oradea", "smaller_store"),
    "M & D RETAIL PLOIESTI SRL": ("ploiesti", "smaller_store"),
    "M & D RETAIL IASI SRL": ("iasi", "hybrid"),
    "M & D RETAIL TIM SRL": ("timisoara", "smaller_store"),
}
STORE_FILE_HINTS = {
    "BANEASA": "MOBEXPERT BANEASA SRL",
    "BRASOV": "M & D RETAIL BRASOV SRL",
    "CONSTANTA": "M & D RETAIL CONSTANTA SRL",
    "IASI": "M & D RETAIL IASI SRL",
    "MILITARI": "M & D RETAIL MILITARI SRL",
    "ORADEA": "M & D RETAIL ORADEA SRL",
    "PANTELIMON": "M & D RETAIL PANTELIMON SRL",
    "PANTE": "M & D RETAIL PANTELIMON SRL",
    "PIPERA": "M & D RETAIL PIPERA SRL",
    "PLOIESTI": "M & D RETAIL PLOIESTI SRL",
    "SIBIU": "M & D RETAIL SIBIU SRL",
    "TIMISOARA": "M & D RETAIL TIM SRL",
}

SERVICE_KEYWORDS = ("transport", "livrare", "montaj", "servicii")
DISCOUNT_ACCOUNTING_MARKERS = (
    "clasa discount",
    "subclasa discount",
    "puncte m&you",
    "puncte utilizate",
)
DIMENSION_RE = re.compile(
    r"(?P<dim>\d+(?:[.,]\d+)?(?:\s*[xX]\s*\d+(?:[.,]\d+)?){1,2})\s*(?:cm)?",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ImportStats:
    rows_seen: int = 0
    rows_inserted: int = 0
    rows_duplicate: int = 0
    rows_filtered: int = 0
    rows_invoice_date_fallback: int = 0
    rows_missing_effective_sale_date: int = 0
    rows_missing_sku: int = 0
    rows_missing_store: int = 0
    first_sale_date: str | None = None
    last_sale_date: str | None = None


def clean_text(value: object) -> str:
    """Normalize CSV cell text without changing semantic values."""
    if value is None:
        return ""
    return str(value).replace("\ufeff", "").strip().strip('"').strip()


def null_if_empty(value: object) -> str | None:
    value_clean = clean_text(value)
    if value_clean == "" or value_clean.lower() == "#null":
        return None
    return value_clean


def parse_float(value: object) -> float | None:
    value_clean = clean_text(value)
    if value_clean == "" or value_clean.lower() == "#null":
        return None
    try:
        return float(value_clean.replace(",", "."))
    except ValueError:
        return None


def normalize_discount_pct(value: float | None) -> float | None:
    """Keep only fraction-scale discounts that are safe for model features."""
    if value is None:
        return None
    discount = abs(value)
    if not math.isfinite(discount):
        return None
    if discount > 1.0:
        return None
    return discount


def parse_date(value: object) -> str | None:
    value_clean = clean_text(value)
    if value_clean == "" or value_clean.lower() == "#null":
        return None
    for fmt in ("%d.%m.%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value_clean, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def parse_yes_no_flag(value: object) -> int | None:
    value_clean = clean_text(value).upper()
    if value_clean in {"", "#NULL"}:
        return None
    if value_clean in {"DA", "YES", "Y", "TRUE", "1"}:
        return 1
    if value_clean in {"NU", "NO", "N", "FALSE", "0"}:
        return 0
    return None


def date_diff_days(start_date: str | None, end_date: str | None) -> int | None:
    if not start_date or not end_date:
        return None
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
    except ValueError:
        return None
    return (end - start).days


def week_start_monday(value: str) -> str:
    parsed = datetime.strptime(value, "%Y-%m-%d").date()
    return (parsed - timedelta(days=parsed.weekday())).strftime("%Y-%m-%d")


def normalize_store(raw_store: str | None) -> tuple[str, str]:
    raw = clean_text(raw_store).upper()
    for known, normalized in STORE_MAP.items():
        if raw == known.upper():
            return normalized

    # Fallback keeps unknown stores usable but obvious in audit output.
    slug = re.sub(r"[^a-z0-9]+", "_", raw.lower()).strip("_")
    return slug or "unknown_store", "unknown"


def infer_store_from_file(path: Path) -> str | None:
    """Infer store only for single-store exports that omit MAGAZIN."""
    name = path.stem.upper()
    for token, store_raw in STORE_FILE_HINTS.items():
        if token in name:
            return store_raw
    return None


def read_csv_rows(path: Path) -> Iterable[tuple[int, dict[str, str]]]:
    """Yield normalized-header rows from a CSV with sniffed delimiter."""
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
            cleaned = {
                clean_text(key): clean_text(value)
                for key, value in row.items()
                if key is not None
            }
            yield row_num, cleaned


def is_non_product_row(row: dict[str, str]) -> bool:
    """Identify services/accounting rows that should not become product demand."""
    fields = [
        row.get("CATEGORIE", ""),
        row.get("CLASA", ""),
        row.get("SUBCLASA", ""),
        row.get("DENUMIRE ARTICOL", ""),
        row.get("COD ARTICOL", ""),
    ]
    combined = " ".join(clean_text(field).lower() for field in fields)
    sku = clean_text(row.get("COD ARTICOL", "")).upper()

    if any(keyword in combined for keyword in SERVICE_KEYWORDS):
        return True
    if any(marker in combined for marker in DISCOUNT_ACCOUNTING_MARKERS):
        return True
    if sku.startswith("DISCOUNT") or sku in {"PUNCTE", "LMPM"}:
        return True
    return False


def extract_dimensions(product_name: str | None) -> str | None:
    if not product_name:
        return None
    matches = [match.group("dim").replace(" ", "").replace(",", ".") for match in DIMENSION_RE.finditer(product_name)]
    return "|".join(matches) if matches else None


def transaction_key(row: dict[str, object]) -> str:
    """Stable dedupe key for the same transaction line across source files."""
    fields = [
        row.get("store_id"),
        row.get("invoice_id"),
        row.get("order_id"),
        row.get("sku_id"),
        row.get("sale_date"),
        row.get("line_value"),
        row.get("quantity"),
        row.get("product_name"),
    ]
    raw_key = "|".join("" if value is None else str(value) for value in fields)
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def normalize_row(path: Path, row_num: int, row: dict[str, str]) -> dict[str, object] | None:
    """Map all known source schemas into the v2 transaction shape."""
    order_date = parse_date(row.get("DATA COMANDA"))
    invoice_date = parse_date(row.get("DATA"))
    sale_date = order_date or invoice_date
    sale_date_source = "order_date" if order_date else "invoice_date_fallback"
    sku_id = null_if_empty(row.get("COD ARTICOL"))
    store_raw = null_if_empty(row.get("MAGAZIN")) or infer_store_from_file(path)
    if not sale_date or not sku_id or not store_raw:
        return None

    quantity = parse_float(row.get("CANTITATE FACTURATA")) or 0.0
    line_value = parse_float(row.get("VALOARE FACTURATA")) or 0.0
    store_id, store_type = normalize_store(store_raw)
    category_raw = null_if_empty(row.get("CATEGORIE"))
    class_raw = null_if_empty(row.get("CLASA"))
    subclass_raw = null_if_empty(row.get("SUBCLASA"))
    group_raw = (
        null_if_empty(row.get("GRUPA_PRODUSE"))
        or null_if_empty(row.get("GRUPA"))
        or null_if_empty(row.get("GRUPA DIRECTII_LICITATII"))
    )
    raion_raw = null_if_empty(row.get("RAION"))
    product_name = null_if_empty(row.get("DENUMIRE ARTICOL"))
    explicit_dimensions = null_if_empty(row.get("DIMENSIUNI"))
    name_dimensions = extract_dimensions(product_name)
    product_dimensions_raw = explicit_dimensions or name_dimensions
    product_dimensions_source = (
        "dimensiuni_field" if explicit_dimensions else "product_name" if name_dimensions else "unknown"
    )
    campaign_raw = null_if_empty(row.get("CAMPANIE"))
    campaign_bf_raw = null_if_empty(row.get("CAMPANIE BF"))
    campaign_selected_raw = null_if_empty(row.get("CAMPANIE SELECTATA"))
    discount_raw = parse_float(row.get("Reducere %"))
    discount_pct = normalize_discount_pct(discount_raw)
    hierarchy = normalize_hierarchy(
        category_raw=category_raw,
        class_raw=class_raw,
        subclass_raw=subclass_raw,
        group_raw=group_raw,
        raion_raw=raion_raw,
        product_name=product_name,
    )
    campaign_signals = classify_campaign_signals(
        sale_date=sale_date,
        raw_campaign=campaign_raw,
        raw_bf=campaign_bf_raw,
        discount_pct=discount_pct,
    )
    supplier_name = null_if_empty(row.get("FURNIZOR"))
    supplier_ext = null_if_empty(row.get("FURNIZOR EXT"))
    supplier_id = null_if_empty(row.get("ID FURNIZOR"))
    supplier_signal_status = "observed" if any((supplier_name, supplier_ext, supplier_id)) else "unknown"
    loyalty_points_raw = null_if_empty(row.get("FACTURA INCLUDE PUNCTE M_YOU UTILIZATE"))
    loyalty_points_used = parse_yes_no_flag(loyalty_points_raw)
    is_return = int(quantity < 0 or line_value < 0)
    is_non_product = int(is_non_product_row(row))
    gross_units = max(quantity, 0.0)
    returned_units = abs(quantity) if quantity < 0 else 0.0
    net_units = gross_units - returned_units
    gross_revenue = max(line_value, 0.0)
    returned_revenue = abs(line_value) if line_value < 0 else 0.0
    net_revenue = gross_revenue - returned_revenue

    normalized = {
        "source_file": str(path),
        "source_row_number": row_num,
        "sale_date": sale_date,
        "sale_date_source": sale_date_source,
        "order_date": order_date,
        "invoice_date": invoice_date,
        "invoice_lag_days": date_diff_days(order_date, invoice_date),
        "used_invoice_date_fallback": int(sale_date_source == "invoice_date_fallback"),
        "week_start": week_start_monday(sale_date),
        "store_raw": store_raw,
        "store_id": store_id,
        "store_type": store_type,
        "sku_id": sku_id,
        "product_name": product_name,
        "product_dimensions_raw": product_dimensions_raw,
        "product_dimensions_source": product_dimensions_source,
        "product_dimensions_signal_status": "observed" if product_dimensions_raw else "unknown",
        "category_raw": category_raw,
        "category_norm": hierarchy.category_norm,
        "category_source": hierarchy.category_source,
        "category_signal_status": hierarchy.category_signal_status,
        "product_family_v2": hierarchy.product_family_v2,
        "product_family_source": hierarchy.product_family_source,
        "product_family_signal_status": hierarchy.product_family_signal_status,
        "class_raw": class_raw,
        "subclass_raw": subclass_raw,
        "group_raw": group_raw,
        "raion_raw": raion_raw,
        "campaign_raw": campaign_raw,
        "campaign_bf_raw": campaign_bf_raw,
        "campaign_selected_raw": campaign_selected_raw,
        "campaign_signal_source": campaign_signals.campaign_signal_source,
        "campaign_signal_status": campaign_signals.campaign_signal_status,
        "bf_signal_source": campaign_signals.bf_signal_source,
        "bf_signal_status": campaign_signals.bf_signal_status,
        "is_bf_campaign": campaign_signals.is_bf_campaign,
        "is_bf_timing": campaign_signals.is_bf_timing,
        "is_bf_observed": campaign_signals.is_bf_observed,
        "is_bf_inferred": campaign_signals.is_bf_inferred,
        "is_product_program": campaign_signals.is_product_program,
        "discount_pct": discount_pct,
        "supplier_name": supplier_name,
        "supplier_ext": supplier_ext,
        "supplier_id": supplier_id,
        "supplier_signal_source": "supplier_fields" if supplier_signal_status == "observed" else "unknown",
        "supplier_signal_status": supplier_signal_status,
        "loyalty_points_used": loyalty_points_used,
        "loyalty_points_raw": loyalty_points_raw,
        "order_id": null_if_empty(row.get("ID COMANDA")),
        "invoice_id": null_if_empty(row.get("ID FACTURA")),
        "client_id": null_if_empty(row.get("ID CLIENT")),
        "client_specific": null_if_empty(row.get("CLIENT SPECIFIC")),
        "export_year": null_if_empty(row.get("AN")),
        "order_number": null_if_empty(row.get("NR COMANDA")),
        "quantity": quantity,
        "line_value": line_value,
        "gross_units": gross_units,
        "returned_units": returned_units,
        "net_units": net_units,
        "gross_revenue": gross_revenue,
        "returned_revenue": returned_revenue,
        "net_revenue": net_revenue,
        "is_return": is_return,
        "is_non_product": is_non_product,
        "raw_row_json": json.dumps(row, ensure_ascii=False, sort_keys=True),
    }
    normalized["transaction_key"] = transaction_key(normalized)
    return normalized


def rebuild_tables(conn: sqlite3.Connection) -> None:
    """Drop and recreate v2 ingestion/aggregation tables."""
    conn.executescript(
        """
        DROP TABLE IF EXISTS forecast_v2_scorecard_slices;
        DROP TABLE IF EXISTS forecast_v2_score_rows;
        DROP TABLE IF EXISTS forecast_v2_actuals_4w;
        DROP TABLE IF EXISTS forecast_v2_predictions;
        DROP TABLE IF EXISTS forecast_v2_score_runs;
        DROP TABLE IF EXISTS forecast_v2_regime_labels;
        DROP TABLE IF EXISTS weekly_chain_demand_v2;
        DROP TABLE IF EXISTS weekly_store_demand_v2;
        DROP TABLE IF EXISTS store_week_coverage_v2;
        DROP TABLE IF EXISTS raw_sales_transactions_v2;
        DROP TABLE IF EXISTS source_files_v2;

        CREATE TABLE source_files_v2 (
            source_file TEXT PRIMARY KEY,
            file_name TEXT NOT NULL,
            file_size INTEGER NOT NULL,
            modified_at TEXT,
            imported_at TEXT NOT NULL,
            status TEXT NOT NULL,
            rows_seen INTEGER NOT NULL DEFAULT 0,
            rows_inserted INTEGER NOT NULL DEFAULT 0,
            rows_duplicate INTEGER NOT NULL DEFAULT 0,
            rows_filtered INTEGER NOT NULL DEFAULT 0,
            rows_invoice_date_fallback INTEGER NOT NULL DEFAULT 0,
            rows_missing_effective_sale_date INTEGER NOT NULL DEFAULT 0,
            rows_missing_sku INTEGER NOT NULL DEFAULT 0,
            rows_missing_store INTEGER NOT NULL DEFAULT 0,
            first_sale_date TEXT,
            last_sale_date TEXT
        );

        CREATE TABLE raw_sales_transactions_v2 (
            transaction_key TEXT PRIMARY KEY,
            source_file TEXT NOT NULL,
            source_row_number INTEGER NOT NULL,
            sale_date TEXT NOT NULL,
            sale_date_source TEXT NOT NULL DEFAULT 'order_date',
            order_date TEXT,
            invoice_date TEXT,
            invoice_lag_days INTEGER,
            used_invoice_date_fallback INTEGER NOT NULL DEFAULT 0,
            week_start TEXT NOT NULL,
            store_raw TEXT NOT NULL,
            store_id TEXT NOT NULL,
            store_type TEXT NOT NULL,
            sku_id TEXT NOT NULL,
            product_name TEXT,
            product_dimensions_raw TEXT,
            product_dimensions_source TEXT NOT NULL DEFAULT 'unknown',
            product_dimensions_signal_status TEXT NOT NULL DEFAULT 'unknown',
            category_raw TEXT,
            category_norm TEXT,
            category_source TEXT NOT NULL DEFAULT 'unknown',
            category_signal_status TEXT NOT NULL DEFAULT 'unknown',
            product_family_v2 TEXT,
            product_family_source TEXT NOT NULL DEFAULT 'unknown',
            product_family_signal_status TEXT NOT NULL DEFAULT 'unknown',
            class_raw TEXT,
            subclass_raw TEXT,
            group_raw TEXT,
            raion_raw TEXT,
            campaign_raw TEXT,
            campaign_bf_raw TEXT,
            campaign_selected_raw TEXT,
            campaign_signal_source TEXT NOT NULL DEFAULT 'unknown',
            campaign_signal_status TEXT NOT NULL DEFAULT 'unknown',
            bf_signal_source TEXT NOT NULL DEFAULT 'unknown',
            bf_signal_status TEXT NOT NULL DEFAULT 'unknown',
            is_bf_campaign INTEGER NOT NULL DEFAULT 0,
            is_bf_timing INTEGER NOT NULL DEFAULT 0,
            is_bf_observed INTEGER NOT NULL DEFAULT 0,
            is_bf_inferred INTEGER NOT NULL DEFAULT 0,
            is_product_program INTEGER NOT NULL DEFAULT 0,
            discount_pct REAL,
            supplier_name TEXT,
            supplier_ext TEXT,
            supplier_id TEXT,
            supplier_signal_source TEXT NOT NULL DEFAULT 'unknown',
            supplier_signal_status TEXT NOT NULL DEFAULT 'unknown',
            loyalty_points_used INTEGER,
            loyalty_points_raw TEXT,
            order_id TEXT,
            invoice_id TEXT,
            client_id TEXT,
            client_specific TEXT,
            export_year TEXT,
            order_number TEXT,
            quantity REAL NOT NULL,
            line_value REAL NOT NULL,
            gross_units REAL NOT NULL,
            returned_units REAL NOT NULL,
            net_units REAL NOT NULL,
            gross_revenue REAL NOT NULL,
            returned_revenue REAL NOT NULL,
            net_revenue REAL NOT NULL,
            is_return INTEGER NOT NULL DEFAULT 0,
            is_non_product INTEGER NOT NULL DEFAULT 0,
            raw_row_json TEXT NOT NULL
        );

        CREATE INDEX idx_raw_v2_sku_date ON raw_sales_transactions_v2(sku_id, sale_date);
        CREATE INDEX idx_raw_v2_date_source ON raw_sales_transactions_v2(sale_date_source, sale_date);
        CREATE INDEX idx_raw_v2_store_date ON raw_sales_transactions_v2(store_id, sale_date);
        CREATE INDEX idx_raw_v2_week ON raw_sales_transactions_v2(week_start);
        CREATE INDEX idx_raw_v2_category ON raw_sales_transactions_v2(category_norm);
        CREATE INDEX idx_raw_v2_category_source ON raw_sales_transactions_v2(category_signal_status, category_source);
        CREATE INDEX idx_raw_v2_bf_signal ON raw_sales_transactions_v2(bf_signal_status, bf_signal_source);

        CREATE TABLE weekly_store_demand_v2 (
            sku_id TEXT NOT NULL,
            store_id TEXT NOT NULL,
            store_type TEXT NOT NULL,
            week_start TEXT NOT NULL,
            category_norm TEXT,
            category_source TEXT,
            category_signal_status TEXT,
            product_family_v2 TEXT,
            product_family_source TEXT,
            product_family_signal_status TEXT,
            gross_units REAL NOT NULL,
            returned_units REAL NOT NULL,
            net_units REAL NOT NULL,
            gross_revenue REAL NOT NULL,
            returned_revenue REAL NOT NULL,
            net_revenue REAL NOT NULL,
            num_transactions INTEGER NOT NULL,
            num_return_lines INTEGER NOT NULL,
            avg_discount_pct REAL,
            max_discount_pct REAL,
            bf_transaction_count INTEGER NOT NULL,
            bf_observed_transaction_count INTEGER NOT NULL,
            bf_inferred_transaction_count INTEGER NOT NULL,
            online_transaction_count INTEGER NOT NULL,
            outlet_transaction_count INTEGER NOT NULL,
            PRIMARY KEY (sku_id, store_id, week_start)
        );

        CREATE TABLE weekly_chain_demand_v2 (
            sku_id TEXT NOT NULL,
            week_start TEXT NOT NULL,
            category_norm TEXT,
            category_source TEXT,
            category_signal_status TEXT,
            product_family_v2 TEXT,
            product_family_source TEXT,
            product_family_signal_status TEXT,
            gross_units REAL NOT NULL,
            returned_units REAL NOT NULL,
            net_units REAL NOT NULL,
            gross_revenue REAL NOT NULL,
            returned_revenue REAL NOT NULL,
            net_revenue REAL NOT NULL,
            num_transactions INTEGER NOT NULL,
            num_stores_selling INTEGER NOT NULL,
            num_hyperstores_selling INTEGER NOT NULL,
            num_smaller_stores_selling INTEGER NOT NULL,
            avg_discount_pct REAL,
            max_discount_pct REAL,
            bf_transaction_count INTEGER NOT NULL,
            bf_observed_transaction_count INTEGER NOT NULL,
            bf_inferred_transaction_count INTEGER NOT NULL,
            online_transaction_count INTEGER NOT NULL,
            outlet_transaction_count INTEGER NOT NULL,
            PRIMARY KEY (sku_id, week_start)
        );

        CREATE TABLE store_week_coverage_v2 (
            store_id TEXT NOT NULL,
            store_type TEXT NOT NULL,
            week_start TEXT NOT NULL,
            has_source_coverage INTEGER NOT NULL,
            transaction_count INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (store_id, week_start)
        );
        """
    )
    conn.commit()


INSERT_COLUMNS = [
    "transaction_key", "source_file", "source_row_number", "sale_date",
    "sale_date_source", "order_date", "invoice_date", "invoice_lag_days",
    "used_invoice_date_fallback", "week_start",
    "store_raw", "store_id", "store_type", "sku_id", "product_name",
    "product_dimensions_raw", "product_dimensions_source",
    "product_dimensions_signal_status", "category_raw", "category_norm",
    "category_source", "category_signal_status", "product_family_v2",
    "product_family_source", "product_family_signal_status", "class_raw",
    "subclass_raw", "group_raw", "raion_raw", "campaign_raw", "campaign_bf_raw",
    "campaign_selected_raw",
    "campaign_signal_source", "campaign_signal_status", "bf_signal_source",
    "bf_signal_status", "is_bf_campaign", "is_bf_timing", "is_bf_observed",
    "is_bf_inferred", "is_product_program", "discount_pct", "supplier_name",
    "supplier_ext", "supplier_id", "supplier_signal_source",
    "supplier_signal_status", "loyalty_points_used", "loyalty_points_raw",
    "order_id", "invoice_id", "client_id",
    "client_specific", "export_year", "order_number", "quantity", "line_value",
    "gross_units", "returned_units", "net_units", "gross_revenue",
    "returned_revenue", "net_revenue", "is_return", "is_non_product", "raw_row_json",
]


def discover_csv_files(input_path: Path) -> list[Path]:
    if input_path.is_file():
        return [input_path]
    files = sorted(input_path.glob("*.csv"))
    file_names = {path.name for path in files}
    preferred_pipera = {
        "pip 22 more detailed.csv",
        "23 pip more detail+date.csv",
        "24 pip more detail.csv",
        "25 pip more detail.csv",
    }
    legacy_pipera = {
        "pip 22.csv",
        "pip 23.csv",
        "pip 24.csv",
        "pipera_25.csv",
    }
    if preferred_pipera & file_names:
        files = [path for path in files if path.name not in legacy_pipera]
    return files


def import_file(conn: sqlite3.Connection, path: Path, dry_run: bool = False) -> ImportStats:
    """Import one CSV into raw_sales_transactions_v2."""
    rows_seen = rows_inserted = rows_duplicate = rows_filtered = 0
    rows_invoice_date_fallback = 0
    rows_missing_effective_sale_date = rows_missing_sku = rows_missing_store = 0
    first_sale_date: str | None = None
    last_sale_date: str | None = None
    placeholders = ", ".join("?" for _ in INSERT_COLUMNS)
    insert_sql = (
        f"INSERT OR IGNORE INTO raw_sales_transactions_v2 "
        f"({', '.join(INSERT_COLUMNS)}) VALUES ({placeholders})"
    )

    batch: list[tuple] = []
    for row_num, raw_row in read_csv_rows(path):
        if not any(raw_row.values()):
            continue
        rows_seen += 1
        if not (parse_date(raw_row.get("DATA COMANDA")) or parse_date(raw_row.get("DATA"))):
            rows_missing_effective_sale_date += 1
        if not null_if_empty(raw_row.get("COD ARTICOL")):
            rows_missing_sku += 1
        if not null_if_empty(raw_row.get("MAGAZIN")):
            rows_missing_store += 1
        normalized = normalize_row(path, row_num, raw_row)
        if normalized is None:
            rows_filtered += 1
            continue
        sale_date = str(normalized["sale_date"])
        first_sale_date = sale_date if first_sale_date is None or sale_date < first_sale_date else first_sale_date
        last_sale_date = sale_date if last_sale_date is None or sale_date > last_sale_date else last_sale_date
        if dry_run:
            rows_inserted += 1
            rows_invoice_date_fallback += int(normalized.get("used_invoice_date_fallback", 0) or 0)
            continue
        batch.append(tuple(normalized.get(col) for col in INSERT_COLUMNS))
        rows_invoice_date_fallback += int(normalized.get("used_invoice_date_fallback", 0) or 0)
        if len(batch) >= 5000:
            before = conn.total_changes
            conn.executemany(insert_sql, batch)
            inserted = conn.total_changes - before
            rows_inserted += inserted
            rows_duplicate += len(batch) - inserted
            batch.clear()

    if batch and not dry_run:
        before = conn.total_changes
        conn.executemany(insert_sql, batch)
        inserted = conn.total_changes - before
        rows_inserted += inserted
        rows_duplicate += len(batch) - inserted

    return ImportStats(
        rows_seen=rows_seen,
        rows_inserted=rows_inserted,
        rows_duplicate=rows_duplicate,
        rows_filtered=rows_filtered,
        rows_invoice_date_fallback=rows_invoice_date_fallback,
        rows_missing_effective_sale_date=rows_missing_effective_sale_date,
        rows_missing_sku=rows_missing_sku,
        rows_missing_store=rows_missing_store,
        first_sale_date=first_sale_date,
        last_sale_date=last_sale_date,
    )


def record_source_file(conn: sqlite3.Connection, path: Path, stats: ImportStats, status: str) -> None:
    stat = path.stat()
    conn.execute(
        """
        INSERT OR REPLACE INTO source_files_v2 (
            source_file, file_name, file_size, modified_at, imported_at, status,
            rows_seen, rows_inserted, rows_duplicate, rows_filtered,
            rows_invoice_date_fallback, rows_missing_effective_sale_date,
            rows_missing_sku, rows_missing_store, first_sale_date, last_sale_date
        ) VALUES (?, ?, ?, ?, datetime('now'), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            str(path),
            path.name,
            stat.st_size,
            datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
            status,
            stats.rows_seen,
            stats.rows_inserted,
            stats.rows_duplicate,
            stats.rows_filtered,
            stats.rows_invoice_date_fallback,
            stats.rows_missing_effective_sale_date,
            stats.rows_missing_sku,
            stats.rows_missing_store,
            stats.first_sale_date,
            stats.last_sale_date,
        ),
    )


def _fmt_pct(num: float, denom: float) -> str:
    if denom == 0:
        return "-"
    return f"{num / denom * 100:.1f}%"


def _fmt_num(value: object, digits: int = 1) -> str:
    if value is None:
        return "-"
    if isinstance(value, int):
        return f"{value:,}"
    try:
        return f"{float(value):,.{digits}f}"
    except (TypeError, ValueError):
        return str(value)


def _table(headers: list[str], rows: list[list[str]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(lines)


def build_import_validation_report(conn: sqlite3.Connection) -> str:
    source_rows = []
    for row in conn.execute(
        """
        SELECT
            file_name, rows_seen, rows_inserted, rows_duplicate, rows_filtered,
            rows_invoice_date_fallback, rows_missing_effective_sale_date,
            rows_missing_sku, rows_missing_store, first_sale_date, last_sale_date
        FROM source_files_v2
        ORDER BY file_name
        """
    ):
        (
            file_name,
            rows_seen,
            rows_inserted,
            rows_duplicate,
            rows_filtered,
            rows_invoice_date_fallback,
            rows_missing_effective_sale_date,
            rows_missing_sku,
            rows_missing_store,
            first_sale_date,
            last_sale_date,
        ) = row
        source_rows.append(
            [
                file_name,
                _fmt_num(rows_seen, 0),
                _fmt_num(rows_inserted, 0),
                _fmt_num(rows_duplicate, 0),
                _fmt_num(rows_filtered, 0),
                _fmt_num(rows_invoice_date_fallback, 0),
                _fmt_pct(rows_invoice_date_fallback, rows_inserted or 0),
                _fmt_num(rows_missing_effective_sale_date, 0),
                _fmt_num(rows_missing_sku, 0),
                _fmt_num(rows_missing_store, 0),
                f"{first_sale_date or '-'}..{last_sale_date or '-'}",
            ]
        )

    store_year_rows = []
    for row in conn.execute(
        """
        SELECT
            store_id,
            substr(sale_date, 1, 4) AS sale_year,
            COUNT(*) AS rows,
            COUNT(DISTINCT sku_id) AS skus,
            SUM(net_units) AS net_units,
            SUM(net_revenue) AS net_revenue,
            SUM(used_invoice_date_fallback) AS invoice_fallback_rows
        FROM raw_sales_transactions_v2
        WHERE is_non_product = 0
        GROUP BY store_id, sale_year
        ORDER BY store_id, sale_year
        """
    ):
        store_id, sale_year, rows, skus, net_units, net_revenue, fallback_rows = row
        store_year_rows.append(
            [
                store_id,
                sale_year,
                _fmt_num(rows, 0),
                _fmt_num(skus, 0),
                _fmt_num(net_units),
                _fmt_num(net_revenue),
                _fmt_num(fallback_rows or 0, 0),
                _fmt_pct(fallback_rows or 0, rows or 0),
            ]
        )

    date_source_rows = []
    for row in conn.execute(
        """
        SELECT sale_date_source, COUNT(*), SUM(net_units), SUM(net_revenue)
        FROM raw_sales_transactions_v2
        WHERE is_non_product = 0
        GROUP BY sale_date_source
        ORDER BY sale_date_source
        """
    ):
        source, rows, net_units, net_revenue = row
        date_source_rows.append([source, _fmt_num(rows, 0), _fmt_num(net_units), _fmt_num(net_revenue)])

    raw = conn.execute(
        """
        SELECT
            COUNT(*), COUNT(DISTINCT transaction_key), COUNT(DISTINCT sku_id),
            SUM(gross_units), SUM(returned_units), SUM(net_units),
            SUM(gross_revenue), SUM(returned_revenue), SUM(net_revenue)
        FROM raw_sales_transactions_v2
        WHERE is_non_product = 0
        """
    ).fetchone()
    weekly_store = conn.execute(
        """
        SELECT SUM(gross_units), SUM(returned_units), SUM(net_units),
               SUM(gross_revenue), SUM(returned_revenue), SUM(net_revenue)
        FROM weekly_store_demand_v2
        """
    ).fetchone()
    weekly_chain = conn.execute(
        """
        SELECT SUM(gross_units), SUM(returned_units), SUM(net_units),
               SUM(gross_revenue), SUM(returned_revenue), SUM(net_revenue)
        FROM weekly_chain_demand_v2
        """
    ).fetchone()

    source_total = conn.execute(
        """
        SELECT SUM(rows_seen), SUM(rows_inserted), SUM(rows_duplicate), SUM(rows_filtered),
               SUM(rows_invoice_date_fallback), SUM(rows_missing_effective_sale_date)
        FROM source_files_v2
        """
    ).fetchone()
    non_product_count = conn.execute(
        "SELECT COUNT(*) FROM raw_sales_transactions_v2 WHERE is_non_product = 1"
    ).fetchone()[0]

    conservation_rows = [
        [
            "raw_sales_transactions_v2",
            _fmt_num(raw[3]),
            _fmt_num(raw[4]),
            _fmt_num(raw[5]),
            _fmt_num(raw[6]),
            _fmt_num(raw[7]),
            _fmt_num(raw[8]),
        ],
        [
            "weekly_store_demand_v2",
            _fmt_num(weekly_store[0]),
            _fmt_num(weekly_store[1]),
            _fmt_num(weekly_store[2]),
            _fmt_num(weekly_store[3]),
            _fmt_num(weekly_store[4]),
            _fmt_num(weekly_store[5]),
        ],
        [
            "weekly_chain_demand_v2",
            _fmt_num(weekly_chain[0]),
            _fmt_num(weekly_chain[1]),
            _fmt_num(weekly_chain[2]),
            _fmt_num(weekly_chain[3]),
            _fmt_num(weekly_chain[4]),
            _fmt_num(weekly_chain[5]),
        ],
    ]

    return "\n".join(
        [
            "# Iteration 5C — V2 Sales Import Validation",
            "",
            "## Summary",
            "",
            _table(
                ["Metric", "Value"],
                [
                    ["Rows seen", _fmt_num(source_total[0] or 0, 0)],
                    ["Rows inserted", _fmt_num(source_total[1] or 0, 0)],
                    ["Duplicate transaction lines", _fmt_num(source_total[2] or 0, 0)],
                    ["Rows filtered", _fmt_num(source_total[3] or 0, 0)],
                    ["Rows using `DATA` fallback", _fmt_num(source_total[4] or 0, 0)],
                    ["Rows missing effective sale date", _fmt_num(source_total[5] or 0, 0)],
                    ["Non-product rows excluded from demand", _fmt_num(non_product_count, 0)],
                    ["Distinct product SKUs", _fmt_num(raw[2] or 0, 0)],
                ],
            ),
            "",
            "## Source Files",
            "",
            _table(
                [
                    "File",
                    "Seen",
                    "Inserted",
                    "Duplicate",
                    "Filtered",
                    "DATA fallback",
                    "Fallback %",
                    "Missing date",
                    "Missing SKU",
                    "Missing store",
                    "Date range",
                ],
                source_rows,
            ),
            "",
            "## Date Source",
            "",
            _table(["Sale date source", "Rows", "Net units", "Net revenue"], date_source_rows),
            "",
            "## Store / Year Coverage",
            "",
            _table(
                ["Store", "Year", "Rows", "SKUs", "Net units", "Net revenue", "Fallback rows", "Fallback %"],
                store_year_rows,
            ),
            "",
            "## Raw To Weekly Conservation",
            "",
            _table(
                ["Table", "Gross units", "Returned units", "Net units", "Gross revenue", "Returned revenue", "Net revenue"],
                conservation_rows,
            ),
            "",
            "## Accuracy Report",
            "",
            "Accuracy not re-run. Phase 1 changes only ingestion and validation; model inputs will be rerun after stock-aware features are added.",
        ]
    ) + "\n"


def build_weekly_tables(conn: sqlite3.Connection) -> None:
    """Refresh weekly store and chain tables from imported raw transactions."""
    conn.executescript(
        """
        DELETE FROM weekly_store_demand_v2;
        DELETE FROM weekly_chain_demand_v2;

        INSERT INTO weekly_store_demand_v2 (
            sku_id, store_id, store_type, week_start, category_norm,
            category_source, category_signal_status,
            product_family_v2, product_family_source, product_family_signal_status,
            gross_units, returned_units, net_units,
            gross_revenue, returned_revenue, net_revenue,
            num_transactions, num_return_lines,
            avg_discount_pct, max_discount_pct, bf_transaction_count,
            bf_observed_transaction_count, bf_inferred_transaction_count,
            online_transaction_count, outlet_transaction_count
        )
        SELECT
            sku_id,
            store_id,
            store_type,
            week_start,
            MAX(category_norm) AS category_norm,
            MAX(category_source) AS category_source,
            MAX(category_signal_status) AS category_signal_status,
            MAX(product_family_v2) AS product_family_v2,
            MAX(product_family_source) AS product_family_source,
            MAX(product_family_signal_status) AS product_family_signal_status,
            SUM(gross_units),
            SUM(returned_units),
            SUM(net_units),
            SUM(gross_revenue),
            SUM(returned_revenue),
            SUM(net_revenue),
            COUNT(*),
            SUM(is_return),
            AVG(discount_pct),
            MAX(discount_pct),
            SUM(CASE WHEN is_bf_timing = 1 THEN 1 ELSE 0 END),
            SUM(CASE WHEN is_bf_observed = 1 THEN 1 ELSE 0 END),
            SUM(CASE WHEN is_bf_inferred = 1 THEN 1 ELSE 0 END),
            SUM(CASE WHEN UPPER(COALESCE(raion_raw, '')) = 'ONLINE' THEN 1 ELSE 0 END),
            SUM(CASE WHEN UPPER(COALESCE(raion_raw, '')) = 'OUTLET' THEN 1 ELSE 0 END)
        FROM raw_sales_transactions_v2
        WHERE is_non_product = 0
        GROUP BY sku_id, store_id, store_type, week_start;

        INSERT INTO weekly_chain_demand_v2 (
            sku_id, week_start, category_norm,
            category_source, category_signal_status,
            product_family_v2, product_family_source, product_family_signal_status,
            gross_units, returned_units, net_units,
            gross_revenue, returned_revenue, net_revenue,
            num_transactions, num_stores_selling,
            num_hyperstores_selling, num_smaller_stores_selling,
            avg_discount_pct, max_discount_pct, bf_transaction_count,
            bf_observed_transaction_count, bf_inferred_transaction_count,
            online_transaction_count, outlet_transaction_count
        )
        SELECT
            sku_id,
            week_start,
            MAX(category_norm) AS category_norm,
            MAX(category_source) AS category_source,
            MAX(category_signal_status) AS category_signal_status,
            MAX(product_family_v2) AS product_family_v2,
            MAX(product_family_source) AS product_family_source,
            MAX(product_family_signal_status) AS product_family_signal_status,
            SUM(gross_units),
            SUM(returned_units),
            SUM(net_units),
            SUM(gross_revenue),
            SUM(returned_revenue),
            SUM(net_revenue),
            SUM(num_transactions),
            COUNT(DISTINCT CASE WHEN net_units > 0 THEN store_id END),
            COUNT(DISTINCT CASE WHEN net_units > 0 AND store_type = 'hyperstore' THEN store_id END),
            COUNT(DISTINCT CASE WHEN net_units > 0 AND store_type = 'smaller_store' THEN store_id END),
            AVG(avg_discount_pct),
            MAX(max_discount_pct),
            SUM(bf_transaction_count),
            SUM(bf_observed_transaction_count),
            SUM(bf_inferred_transaction_count),
            SUM(online_transaction_count),
            SUM(outlet_transaction_count)
        FROM weekly_store_demand_v2
        GROUP BY sku_id, week_start;
        """
    )
    conn.commit()


def build_store_coverage(conn: sqlite3.Connection) -> None:
    """Build store-week coverage from each store's observed date range."""
    conn.execute("DELETE FROM store_week_coverage_v2")
    ranges = conn.execute(
        """
        SELECT store_id, store_type, MIN(week_start), MAX(week_start)
        FROM raw_sales_transactions_v2
        GROUP BY store_id, store_type
        """
    ).fetchall()
    counts = {
        (store_id, week_start): count
        for store_id, week_start, count in conn.execute(
            """
            SELECT store_id, week_start, COUNT(*)
            FROM raw_sales_transactions_v2
            GROUP BY store_id, week_start
            """
        ).fetchall()
    }

    rows: list[tuple[str, str, str, int, int]] = []
    for store_id, store_type, min_week, max_week in ranges:
        current = datetime.strptime(min_week, "%Y-%m-%d").date()
        end = datetime.strptime(max_week, "%Y-%m-%d").date()
        while current <= end:
            week = current.strftime("%Y-%m-%d")
            rows.append((store_id, store_type, week, 1, counts.get((store_id, week), 0)))
            current += timedelta(days=7)

    conn.executemany(
        """
        INSERT INTO store_week_coverage_v2 (
            store_id, store_type, week_start, has_source_coverage, transaction_count
        ) VALUES (?, ?, ?, ?, ?)
        """,
        rows,
    )
    conn.commit()


def import_sources(
    input_path: Path,
    db_path: Path = DB_PATH,
    rebuild: bool = False,
    dry_run: bool = False,
    report_path: Path | None = DEFAULT_IMPORT_REPORT,
) -> None:
    files = discover_csv_files(input_path)
    if not files:
        raise FileNotFoundError(f"No CSV files found at {input_path}")

    log.info("Forecast v2 import source: %s", input_path)
    log.info("CSV files discovered: %d", len(files))

    if dry_run:
        total = ImportStats()
        for path in files:
            stats = import_file(sqlite3.connect(":memory:"), path, dry_run=True)
            total = ImportStats(
                rows_seen=total.rows_seen + stats.rows_seen,
                rows_inserted=total.rows_inserted + stats.rows_inserted,
                rows_duplicate=0,
                rows_filtered=total.rows_filtered + stats.rows_filtered,
                rows_invoice_date_fallback=(
                    total.rows_invoice_date_fallback + stats.rows_invoice_date_fallback
                ),
                rows_missing_effective_sale_date=(
                    total.rows_missing_effective_sale_date + stats.rows_missing_effective_sale_date
                ),
                rows_missing_sku=total.rows_missing_sku + stats.rows_missing_sku,
                rows_missing_store=total.rows_missing_store + stats.rows_missing_store,
            )
            log.info(
                "DRY %s — rows=%d parseable=%d filtered=%d invoice_fallback=%d missing_date=%d dates=%s..%s",
                path.name, stats.rows_seen, stats.rows_inserted,
                stats.rows_filtered, stats.rows_invoice_date_fallback,
                stats.rows_missing_effective_sale_date,
                stats.first_sale_date, stats.last_sale_date,
            )
        log.info(
            "DRY RUN TOTAL — rows=%d parseable=%d filtered=%d invoice_fallback=%d missing_date=%d",
            total.rows_seen, total.rows_inserted, total.rows_filtered,
            total.rows_invoice_date_fallback, total.rows_missing_effective_sale_date,
        )
        return

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    try:
        if rebuild:
            rebuild_tables(conn)
        else:
            # Ensure tables exist in a fresh DB without dropping existing v2 data.
            existing = conn.execute(
                """
                SELECT name FROM sqlite_master
                WHERE type='table' AND name='raw_sales_transactions_v2'
                """
            ).fetchone()
            if existing is None:
                rebuild_tables(conn)

        totals = ImportStats()
        for path in files:
            log.info("Importing %s", path.name)
            stats = import_file(conn, path)
            record_source_file(conn, path, stats, "imported")
            conn.commit()
            totals = ImportStats(
                rows_seen=totals.rows_seen + stats.rows_seen,
                rows_inserted=totals.rows_inserted + stats.rows_inserted,
                rows_duplicate=totals.rows_duplicate + stats.rows_duplicate,
                rows_filtered=totals.rows_filtered + stats.rows_filtered,
                rows_invoice_date_fallback=(
                    totals.rows_invoice_date_fallback + stats.rows_invoice_date_fallback
                ),
                rows_missing_effective_sale_date=(
                    totals.rows_missing_effective_sale_date + stats.rows_missing_effective_sale_date
                ),
                rows_missing_sku=totals.rows_missing_sku + stats.rows_missing_sku,
                rows_missing_store=totals.rows_missing_store + stats.rows_missing_store,
            )
            log.info(
                "  rows=%d inserted=%d duplicate=%d filtered=%d invoice_fallback=%d missing_date=%d dates=%s..%s",
                stats.rows_seen, stats.rows_inserted, stats.rows_duplicate,
                stats.rows_filtered, stats.rows_invoice_date_fallback,
                stats.rows_missing_effective_sale_date,
                stats.first_sale_date, stats.last_sale_date,
            )

        log.info("Building weekly v2 tables...")
        build_weekly_tables(conn)
        build_store_coverage(conn)

        raw_count = conn.execute("SELECT COUNT(*) FROM raw_sales_transactions_v2").fetchone()[0]
        weekly_store = conn.execute("SELECT COUNT(*) FROM weekly_store_demand_v2").fetchone()[0]
        weekly_chain = conn.execute("SELECT COUNT(*) FROM weekly_chain_demand_v2").fetchone()[0]
        log.info(
            "V2 import complete — raw=%d weekly_store=%d weekly_chain=%d "
            "seen=%d inserted=%d duplicate=%d filtered=%d invoice_fallback=%d missing_date=%d",
            raw_count, weekly_store, weekly_chain,
            totals.rows_seen, totals.rows_inserted, totals.rows_duplicate,
            totals.rows_filtered, totals.rows_invoice_date_fallback,
            totals.rows_missing_effective_sale_date,
        )
        if report_path is not None:
            report = build_import_validation_report(conn)
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(report, encoding="utf-8")
            log.info("Wrote %s", report_path)
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Import multi-store Mobexpert CSVs into v2 tables.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="CSV file or folder of CSV files.")
    parser.add_argument("--db", type=Path, default=DB_PATH, help="SQLite database path.")
    parser.add_argument("--report", type=Path, default=DEFAULT_IMPORT_REPORT, help="Validation report path.")
    parser.add_argument("--rebuild", action="store_true", help="Drop and recreate v2 tables before import.")
    parser.add_argument("--dry-run", action="store_true", help="Parse files and report counts without writing DB.")
    args = parser.parse_args()

    import_sources(args.input, db_path=args.db, rebuild=args.rebuild, dry_run=args.dry_run, report_path=args.report)


if __name__ == "__main__":
    main()
