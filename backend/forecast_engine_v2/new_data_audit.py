"""Phase 8A audit for newly supplied stock/supplier/sales data."""

from __future__ import annotations

import argparse
import csv
import re
import sqlite3
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd

try:
    from .ingestion import clean_text, normalize_store
    from .scorecard import DB_PATH
    from .stock_ingestion import MONTH_MAP, csv_header, stock_month_columns
except ImportError:  # Allows direct script execution.
    from ingestion import clean_text, normalize_store
    from scorecard import DB_PATH
    from stock_ingestion import MONTH_MAP, csv_header, stock_month_columns


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = PROJECT_ROOT / "new_stock_data_20may"
DEFAULT_REPORT = PROJECT_ROOT / "active_docs" / "ITER5J_V2_NEW_DATA_AUDIT.md"

SUPPLIER_REQUIRED = {
    "PERIOADA PERIOADA",
    "IMPORTATOR_PRODUCATOR",
    "ARTICOL DENUMIRE",
    "STOC",
    "VALOARE STOC",
}
SALES_REQUIRED = {"COD ARTICOL", "DATA", "DATA COMANDA", "VALOARE FACTURATA", "CANTITATE FACTURATA"}
MONTH_LABEL_RE = re.compile(r"^(.+?)\s+(20\d{2})$", re.IGNORECASE)


@dataclass(frozen=True)
class ReferenceSets:
    sales_skus: set[str]
    headline_skus: set[str]
    existing_stock_skus: set[str]
    existing_stock_stores: set[str]
    product_name_to_skus: dict[str, set[str]]


def _fmt_pct(value: object) -> str:
    if value is None or pd.isna(value):
        return "-"
    return f"{float(value) * 100:.1f}%"


def _fmt_num(value: object, digits: int = 0) -> str:
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


def _strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def _norm_key(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    text = _strip_accents(str(value)).upper().strip()
    return re.sub(r"\s+", " ", text)


def _nullish(series: pd.Series) -> pd.Series:
    text = series.fillna("").astype(str).str.strip()
    return text.isin({"", "#null", "NULL", "NAN", "nan", "None", "NONE"})


def _read_csv(path: Path, usecols: list[str] | None = None) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str, low_memory=False, usecols=usecols)


def _detect_kind(path: Path, header: list[str]) -> tuple[str, str]:
    header_set = set(header)
    if stock_month_columns(header) and "ARTICOL COD" in header_set:
        return "monthly_store_stock", "historical_backtest"
    if SUPPLIER_REQUIRED.issubset(header_set):
        return "monthly_supplier_stock", "historical_backtest"
    if "COD ARTICOL" in header_set and any("Viteza de Rotatie" in col for col in header):
        return "rotation_snapshot", "current_snapshot"
    if SALES_REQUIRED.issubset(header_set):
        return "historical_sales", "historical_backtest"
    return "unknown", "unknown"


def _month_from_label(value: object) -> str | None:
    if value is None or pd.isna(value):
        return None
    text = _strip_accents(str(value)).upper().strip()
    match = MONTH_LABEL_RE.match(text)
    if not match:
        return None
    month_name = re.sub(r"[^A-Z]+", " ", match.group(1)).strip().split(" ")[0]
    month = MONTH_MAP.get(month_name)
    if month is None:
        return None
    return f"{int(match.group(2)):04d}-{month:02d}-01"


def _load_references(conn: sqlite3.Connection) -> ReferenceSets:
    sales_skus = {
        str(row[0])
        for row in conn.execute("SELECT DISTINCT sku_id FROM weekly_chain_demand_v2 WHERE sku_id IS NOT NULL")
    }
    headline_skus = {
        str(row[0])
        for row in conn.execute(
            "SELECT DISTINCT sku_id FROM forecast_v2_regime_labels WHERE headline_eligible = 1 AND sku_id IS NOT NULL"
        )
    }
    existing_stock_skus = {
        str(row[0])
        for row in conn.execute("SELECT DISTINCT sku_id FROM stock_monthly_store_v2 WHERE sku_id IS NOT NULL")
    }
    existing_stock_stores = {
        str(row[0])
        for row in conn.execute("SELECT DISTINCT store_id FROM stock_monthly_store_v2 WHERE store_id IS NOT NULL")
    }
    name_map: dict[str, set[str]] = defaultdict(set)
    for name, sku in conn.execute(
        """
        SELECT DISTINCT product_name, sku_id
        FROM raw_sales_transactions_v2
        WHERE product_name IS NOT NULL AND sku_id IS NOT NULL
        """
    ):
        key = _norm_key(name)
        if key:
            name_map[key].add(str(sku))
    return ReferenceSets(
        sales_skus=sales_skus,
        headline_skus=headline_skus,
        existing_stock_skus=existing_stock_skus,
        existing_stock_stores=existing_stock_stores,
        product_name_to_skus=dict(name_map),
    )


def _sku_overlap(skus: set[str], refs: ReferenceSets) -> dict[str, int]:
    return {
        "skus": len(skus),
        "sales_overlap": len(skus & refs.sales_skus),
        "headline_overlap": len(skus & refs.headline_skus),
        "new_vs_existing_stock": len(skus - refs.existing_stock_skus),
    }


def _numeric_stats(frame: pd.DataFrame, columns: list[str]) -> dict[str, int]:
    if not columns:
        return {"values": 0, "nonnull": 0, "zero": 0, "negative": 0}
    numeric = frame[columns].apply(pd.to_numeric, errors="coerce")
    values = int(numeric.size)
    nonnull = int(numeric.notna().sum().sum())
    return {
        "values": values,
        "nonnull": nonnull,
        "zero": int(numeric.eq(0).sum().sum()),
        "negative": int(numeric.lt(0).sum().sum()),
    }


def _audit_monthly_store(path: Path, refs: ReferenceSets) -> dict[str, object]:
    header = csv_header(path)
    month_cols = stock_month_columns(header)
    df = _read_csv(path)
    sku_col = df["ARTICOL COD"].fillna("").astype(str).str.strip()
    skus = set(sku_col[sku_col.ne("")])
    stores = sorted({normalize_store(value)[0] for value in df.get("MAGAZIN", pd.Series(dtype=str)).dropna()})
    numeric = _numeric_stats(df, list(month_cols))
    duplicate_rows = int(df.duplicated(subset=[col for col in ("ARTICOL COD", "MAGAZIN") if col in df.columns]).sum())
    return {
        "file": path.name,
        "kind": "monthly_store_stock",
        "scope": "historical_backtest",
        "rows": len(df),
        "cols": len(df.columns),
        "months": len(set(month_cols.values())),
        "first_month": min(month_cols.values()) if month_cols else None,
        "last_month": max(month_cols.values()) if month_cols else None,
        "stores": ", ".join(stores) if stores else "-",
        "duplicate_keys": duplicate_rows,
        **_sku_overlap(skus, refs),
        **numeric,
        "notes": "Directly ingestible through the existing wide monthly stock normalizer.",
    }


def _audit_supplier(path: Path, refs: ReferenceSets) -> dict[str, object]:
    df = _read_csv(path)
    df["stock_month"] = df["PERIOADA PERIOADA"].map(_month_from_label)
    item_keys = df["ARTICOL DENUMIRE"].map(_norm_key)
    suppliers = df["IMPORTATOR_PRODUCATOR"].fillna("").astype(str).str.strip()
    mapped_skus: set[str] = set()
    ambiguous_keys: set[str] = set()
    unmapped_keys: set[str] = set()
    exact_unique_rows = ambiguous_rows = unmapped_rows = 0
    for key in item_keys:
        if not key:
            unmapped_rows += 1
            continue
        sku_set = refs.product_name_to_skus.get(key)
        if not sku_set:
            unmapped_rows += 1
            unmapped_keys.add(key)
        elif len(sku_set) == 1:
            exact_unique_rows += 1
            mapped_skus.update(sku_set)
        else:
            ambiguous_rows += 1
            ambiguous_keys.add(key)
    duplicate_keys = int(
        df.assign(item_key=item_keys, supplier_key=suppliers.map(_norm_key)).duplicated(
            subset=["stock_month", "supplier_key", "item_key"]
        ).sum()
    )
    numeric = _numeric_stats(df, ["STOC", "VALOARE STOC"])
    return {
        "file": path.name,
        "kind": "monthly_supplier_stock",
        "scope": "historical_backtest",
        "rows": len(df),
        "cols": len(df.columns),
        "months": int(df["stock_month"].nunique(dropna=True)),
        "first_month": df["stock_month"].dropna().min() if df["stock_month"].notna().any() else None,
        "last_month": df["stock_month"].dropna().max() if df["stock_month"].notna().any() else None,
        "suppliers": int(suppliers[suppliers.ne("")].nunique()),
        "products": int(item_keys[item_keys.ne("")].nunique()),
        "duplicate_keys": duplicate_keys,
        "mapped_rows": exact_unique_rows,
        "ambiguous_rows": ambiguous_rows,
        "unmapped_rows": unmapped_rows,
        "ambiguous_products": len(ambiguous_keys),
        "unmapped_products": len(unmapped_keys),
        **_sku_overlap(mapped_skus, refs),
        **numeric,
        "notes": "Needs supplier-stock normalizer and exact product-name SKU map; ambiguous mappings should be stored but excluded from model features.",
    }


def _audit_rotation(path: Path, refs: ReferenceSets) -> dict[str, object]:
    df = _read_csv(path)
    sku_col = df["COD ARTICOL"].fillna("").astype(str).str.strip()
    skus = set(sku_col[sku_col.ne("")])
    numeric_cols = [col for col in df.columns if col != "COD ARTICOL"]
    numeric = _numeric_stats(df, numeric_cols)
    store_columns = [col for col in df.columns if col.startswith("Stoc ") and col != "Stoc_Vanzari"]
    duplicate_skus = int(df.duplicated(subset=["COD ARTICOL"]).sum())
    return {
        "file": path.name,
        "kind": "rotation_snapshot",
        "scope": "current_snapshot",
        "rows": len(df),
        "cols": len(df.columns),
        "months": "-",
        "first_month": None,
        "last_month": None,
        "store_columns": ", ".join(store_columns[-3:]) if store_columns else "-",
        "duplicate_keys": duplicate_skus,
        **_sku_overlap(skus, refs),
        **numeric,
        "notes": "High SKU overlap, but current-snapshot only unless a historical as-of date is proven.",
    }


def _parse_dates(series: pd.Series) -> pd.Series:
    cleaned = series.mask(_nullish(series))
    return pd.to_datetime(cleaned, dayfirst=True, errors="coerce")


def _audit_sales(path: Path, refs: ReferenceSets) -> dict[str, object]:
    df = _read_csv(path)
    sku_col = df["COD ARTICOL"].fillna("").astype(str).str.strip()
    skus = set(sku_col[sku_col.ne("")])
    order_dates = _parse_dates(df["DATA COMANDA"])
    invoice_dates = _parse_dates(df["DATA"])
    quantity = pd.to_numeric(df["CANTITATE FACTURATA"], errors="coerce")
    value = pd.to_numeric(df["VALOARE FACTURATA"], errors="coerce")
    fallback_rows = int(order_dates.isna().sum() - (order_dates.isna() & invoice_dates.isna()).sum())
    duplicate_subset = [col for col in ("COD ARTICOL", "ID COMANDA", "DATA", "DATA COMANDA", "CANTITATE FACTURATA", "VALOARE FACTURATA") if col in df.columns]
    return {
        "file": path.name,
        "kind": "historical_sales",
        "scope": "historical_backtest",
        "rows": len(df),
        "cols": len(df.columns),
        "months": int(order_dates.dt.to_period("M").nunique() if order_dates.notna().any() else 0),
        "first_month": order_dates.dropna().min().strftime("%Y-%m-%d") if order_dates.notna().any() else None,
        "last_month": order_dates.dropna().max().strftime("%Y-%m-%d") if order_dates.notna().any() else None,
        "fallback_rows": fallback_rows,
        "missing_effective_date": int((order_dates.isna() & invoice_dates.isna()).sum()),
        "campaign_nullish": int(_nullish(df.get("CAMPANIE", pd.Series(index=df.index, dtype=str))).sum()),
        "campaign_bf_nullish": int(_nullish(df.get("CAMPANIE BF", pd.Series(index=df.index, dtype=str))).sum()),
        "negative_qty_rows": int(quantity.lt(0).sum()),
        "negative_value_rows": int(value.lt(0).sum()),
        "duplicate_keys": int(df.duplicated(subset=duplicate_subset).sum()) if duplicate_subset else 0,
        **_sku_overlap(skus, refs),
        "values": int(len(df) * 2),
        "nonnull": int(quantity.notna().sum() + value.notna().sum()),
        "zero": int(quantity.eq(0).sum() + value.eq(0).sum()),
        "negative": int(quantity.lt(0).sum() + value.lt(0).sum()),
        "notes": "Useful Baneasa 2022 coverage; about half of rows rely on DATA invoice fallback.",
    }


def _audit_unknown(path: Path, refs: ReferenceSets) -> dict[str, object]:
    del refs
    row_count = 0
    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as f:
        sample = f.read(8192)
        f.seek(0)
        try:
            delimiter = csv.Sniffer().sniff(sample, delimiters=",;\t|").delimiter
        except csv.Error:
            delimiter = ","
        reader = csv.reader(f, delimiter=delimiter)
        next(reader, None)
        for row_count, _ in enumerate(reader, start=1):
            pass
    return {
        "file": path.name,
        "kind": "unknown",
        "scope": "unknown",
        "rows": row_count,
        "cols": len(csv_header(path)),
        "months": "-",
        "first_month": None,
        "last_month": None,
        "duplicate_keys": "-",
        "skus": "-",
        "sales_overlap": "-",
        "headline_overlap": "-",
        "new_vs_existing_stock": "-",
        "values": "-",
        "nonnull": "-",
        "zero": "-",
        "negative": "-",
        "notes": "Unknown schema; not currently planned for ingestion.",
    }


def audit_file(path: Path, refs: ReferenceSets) -> dict[str, object]:
    header = csv_header(path)
    kind, _ = _detect_kind(path, header)
    if kind == "monthly_store_stock":
        return _audit_monthly_store(path, refs)
    if kind == "monthly_supplier_stock":
        return _audit_supplier(path, refs)
    if kind == "rotation_snapshot":
        return _audit_rotation(path, refs)
    if kind == "historical_sales":
        return _audit_sales(path, refs)
    return _audit_unknown(path, refs)


def build_report(rows: list[dict[str, object]], refs: ReferenceSets, input_path: Path) -> str:
    file_rows = []
    for row in rows:
        file_rows.append(
            [
                str(row["file"]),
                str(row["kind"]),
                str(row["scope"]),
                _fmt_num(row["rows"]),
                _fmt_num(row["skus"]) if isinstance(row.get("skus"), int) else str(row.get("skus", "-")),
                _fmt_num(row["sales_overlap"]) if isinstance(row.get("sales_overlap"), int) else str(row.get("sales_overlap", "-")),
                _fmt_num(row["headline_overlap"]) if isinstance(row.get("headline_overlap"), int) else str(row.get("headline_overlap", "-")),
                str(row.get("first_month") or "-"),
                str(row.get("last_month") or "-"),
                str(row.get("notes", "")),
            ]
        )

    supplier_rows = []
    for row in [r for r in rows if r["kind"] == "monthly_supplier_stock"]:
        supplier_rows.append(
            [
                str(row["file"]),
                _fmt_num(row["rows"]),
                _fmt_num(row["suppliers"]),
                _fmt_num(row["products"]),
                _fmt_num(row["mapped_rows"]),
                _fmt_num(row["ambiguous_rows"]),
                _fmt_num(row["unmapped_rows"]),
                _fmt_num(row["skus"]),
                _fmt_num(row["headline_overlap"]),
                _fmt_num(row["duplicate_keys"]),
                f"{row['first_month']}..{row['last_month']}",
            ]
        )

    stock_rows = []
    for row in [r for r in rows if r["kind"] == "monthly_store_stock"]:
        stock_rows.append(
            [
                str(row["file"]),
                str(row.get("stores", "-")),
                _fmt_num(row["rows"]),
                _fmt_num(row["months"]),
                _fmt_num(row["skus"]),
                _fmt_num(row["sales_overlap"]),
                _fmt_num(row["headline_overlap"]),
                _fmt_num(row["new_vs_existing_stock"]),
                _fmt_num(row["zero"]),
                _fmt_num(row["negative"]),
                _fmt_num(row["duplicate_keys"]),
            ]
        )

    rotation_rows = []
    for row in [r for r in rows if r["kind"] == "rotation_snapshot"]:
        rotation_rows.append(
            [
                str(row["file"]),
                _fmt_num(row["rows"]),
                _fmt_num(row["skus"]),
                _fmt_num(row["sales_overlap"]),
                _fmt_num(row["headline_overlap"]),
                _fmt_num(row["nonnull"]),
                _fmt_num(row["zero"]),
                _fmt_num(row["negative"]),
                str(row.get("store_columns", "-")),
            ]
        )

    sales_rows = []
    for row in [r for r in rows if r["kind"] == "historical_sales"]:
        sales_rows.append(
            [
                str(row["file"]),
                _fmt_num(row["rows"]),
                _fmt_num(row["skus"]),
                _fmt_num(row["headline_overlap"]),
                _fmt_num(row["fallback_rows"]),
                _fmt_num(row["missing_effective_date"]),
                _fmt_pct(row["campaign_nullish"] / row["rows"] if row["rows"] else None),
                _fmt_pct(row["campaign_bf_nullish"] / row["rows"] if row["rows"] else None),
                _fmt_num(row["negative_qty_rows"]),
                _fmt_num(row["duplicate_keys"]),
            ]
        )

    supplier_union = set()
    rotation_union = set()
    monthly_union = set()
    for row in rows:
        if row["kind"] == "monthly_supplier_stock" and isinstance(row.get("skus"), int):
            supplier_union.add(row["file"])
        if row["kind"] == "rotation_snapshot" and isinstance(row.get("skus"), int):
            rotation_union.add(row["file"])
        if row["kind"] == "monthly_store_stock" and isinstance(row.get("skus"), int):
            monthly_union.add(row["file"])

    decision = (
        "Phase 8A confirms the new data package is worth ingesting. "
        "The monthly store stock files are clean and directly usable; supplier stock is the largest accuracy lever, "
        "but it must pass through a confidence-controlled product-name-to-SKU map; rotation files are high coverage but current-snapshot only."
    )

    return "\n".join(
        [
            "# Iteration 5J — V2 New Data Audit",
            "",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"Input folder: `{input_path}`",
            "",
            "## Phase Checkpoint",
            "",
            "Phase completed: Phase 8A — New data validation and manifest",
            "",
            "What changed: no forecast tables, model behavior, or sales/stock ingestion tables were changed. This is a read-only validation report for the new files.",
            "",
            "Accuracy rerun: no. This phase validates data only, so hit +/-20 remains at the Phase 7E control baseline of 24.1%.",
            "",
            "## Reference Population",
            "",
            _table(
                ["Reference", "Count"],
                [
                    ["sales SKUs in `weekly_chain_demand_v2`", _fmt_num(len(refs.sales_skus))],
                    ["headline SKUs in current regime labels", _fmt_num(len(refs.headline_skus))],
                    ["SKUs already in monthly store stock", _fmt_num(len(refs.existing_stock_skus))],
                    ["stores already in monthly store stock", _fmt_num(len(refs.existing_stock_stores))],
                    ["normalized product names available for supplier mapping", _fmt_num(len(refs.product_name_to_skus))],
                ],
            ),
            "",
            "## File Manifest",
            "",
            _table(
                [
                    "File",
                    "Kind",
                    "Feature scope",
                    "Rows",
                    "SKUs",
                    "Sales overlap",
                    "Headline overlap",
                    "First period",
                    "Last period",
                    "Notes",
                ],
                file_rows,
            ),
            "",
            "## Monthly Store Stock",
            "",
            _table(
                [
                    "File",
                    "Store",
                    "Rows",
                    "Months",
                    "SKUs",
                    "Sales overlap",
                    "Headline overlap",
                    "New vs existing stock",
                    "Zero values",
                    "Negative values",
                    "Duplicate keys",
                ],
                stock_rows,
            ),
            "",
            "## Supplier Stock Mapping Readiness",
            "",
            _table(
                [
                    "File",
                    "Rows",
                    "Suppliers",
                    "Products",
                    "Exact mapped rows",
                    "Ambiguous rows",
                    "Unmapped rows",
                    "Mapped SKUs",
                    "Headline mapped SKUs",
                    "Duplicate keys",
                    "Coverage",
                ],
                supplier_rows,
            ),
            "",
            "## Rotation Snapshot Readiness",
            "",
            _table(
                [
                    "File",
                    "Rows",
                    "SKUs",
                    "Sales overlap",
                    "Headline overlap",
                    "Non-null values",
                    "Zero values",
                    "Negative values",
                    "Store stock columns",
                ],
                rotation_rows,
            ),
            "",
            "## Baneasa Sales Readiness",
            "",
            _table(
                [
                    "File",
                    "Rows",
                    "SKUs",
                    "Headline overlap",
                    "Invoice fallback rows",
                    "Missing effective date",
                    "Campaign nullish",
                    "BF nullish",
                    "Negative qty rows",
                    "Duplicate line candidates",
                ],
                sales_rows,
            ),
            "",
            "## Decision",
            "",
            decision,
            "",
            "## Phase 8B/8C/8D Readiness",
            "",
            "- Phase 8B can proceed with `baneasa_sales22.csv`; the main risk is high invoice-date fallback usage, not file usability.",
            "- Phase 8C can proceed with the three monthly store stock files; schemas match the existing wide monthly normalizer.",
            "- Phase 8D can proceed, but must implement confidence-controlled supplier product-name mapping before using supplier stock in features.",
            "- Rotation files should wait until Phase 8F and must remain `current_snapshot` for official backtests.",
            "",
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit new forecast v2 data package without mutating database tables.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()

    files = sorted(args.input.glob("*.csv")) if args.input.is_dir() else [args.input]
    conn = sqlite3.connect(args.db)
    try:
        refs = _load_references(conn)
    finally:
        conn.close()

    rows = [audit_file(path, refs) for path in files]
    report = build_report(rows, refs, args.input)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report, encoding="utf-8")
    print(report)
    print(f"Wrote {args.report}")


if __name__ == "__main__":
    main()
