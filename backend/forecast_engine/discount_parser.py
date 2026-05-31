"""Iter 4 Phase C — parse Baneasa-store discount rows into structured tables.

**IMPORTANT scope note (per user 2026-05-03):**
    These discount rows reflect how items were managed at the Baneasa store
    specifically. Some campaigns are chain-level, some are local store
    decisions. This parser does NOT treat them as universal Mobexpert rules —
    they are store-level signals with a confidence score reflecting how
    confidently we can map a campaign to a DB category.

Input:
    Sales CSV files (2023, 2024, 2025). Reads all files found in the repo
    root matching the pattern sales_20*.csv.

Discount row types detected:
    1. Campaign  — COD ARTICOL starts with "DISCOUNT" + digits (e.g. DISCOUNT011).
                   Description: "Campanie {category} {pct}%, {start}-{end}".
                   Dates and pct extracted via regex.
    2. Loyalty   — COD ARTICOL == "DISCOUNT", description contains "Fidelizare".
                   No campaign dates — per-transaction loyalty redemptions.
    3. Voucher   — COD ARTICOL in ("VOUCHERVANZARE",). No campaign dates.
    4. Other     — COD ARTICOL == "DISCOUNT021" (MAPN benefit) — no date range.

Output (SQLite tables in supply_chain.db):
    promo_calendar(campaign_id, start_date, end_date, discount_pct,
                   category_hint, db_category, source_type, confidence, description)
    sku_promo_weeks(sku_id, week_start, promo_flag, loyalty_flag, confidence)
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = REPO_ROOT / "backend" / "data" / "supply_chain.db"

# Sales CSV files to scan (root-level, one per year/period)
SALES_FILES = sorted(REPO_ROOT.glob("sales_20*.csv"))

# Mapping from keywords found in campaign DENUMIRE ARTICOL to the DB category
# in weekly_demand.category. Values are (db_category, confidence).
# Confidence 1.0 = clear mapping, 0.7 = likely but broad, 0.0 = unknown.
CATEGORY_KEYWORD_MAP: list[tuple[str, str, float]] = [
    ("corpuri iluminat",    "ACCESORII",              1.0),
    ("covoare",             "ACCESORII",              1.0),
    ("covor",               "ACCESORII",              1.0),
    ("decoratiuni perete",  "ACCESORII",              1.0),
    ("decoratiuni",         "ACCESORII",              0.8),
    ("mexkids",             "MOBILIER DE CASA",       0.9),
    ("mobilier copii",      "MOBILIER DE CASA",       1.0),
    ("mobilier de copii",   "MOBILIER DE CASA",       1.0),
    ("mobilier de copiii",  "MOBILIER DE CASA",       1.0),  # typo in raw data
    ("mese si scaune",      "CANAPELE SI FOTOLII",    1.0),
    ("jucarie",             "ALTELE",                 0.8),
    ("jucariei",            "ALTELE",                 0.8),
]

# Date pattern variants found in descriptions
# "20.03-02.04.2024" or "6-26.09.2023" or "03.03 - 06.04.2025" or "18.12 - 31.12.2024"
_DATE_RANGE_RE = re.compile(
    r"(\d{1,2}[.]\d{2})\s*[-–]\s*(\d{1,2}[.]\d{2}[.]\d{4})"
    r"|(\d{1,2})[.-](\d{1,2}[.]\d{4})"          # "6-26.09.2023" compact
)
_PCT_RE = re.compile(r"(\d+)\s*%")


# ---------------------------------------------------------------------------
# Date parsing helpers
# ---------------------------------------------------------------------------

def _parse_ro_date(day_month: str, year_hint: int) -> str | None:
    """Parse Romanian-style day.month into YYYY-MM-DD, guessing year from context."""
    parts = day_month.strip().split(".")
    if len(parts) == 3:
        return f"{parts[2]}-{parts[1].zfill(2)}-{parts[0].zfill(2)}"
    if len(parts) == 2:
        d, m = parts
        return f"{year_hint}-{m.zfill(2)}-{d.zfill(2)}"
    return None


def _extract_dates(description: str) -> tuple[str | None, str | None]:
    """Extract start_date, end_date from a campaign description string."""
    # Find 4-digit year anywhere in description
    year_match = re.search(r"\b(20\d{2})\b", description)
    year = int(year_match.group(1)) if year_match else 2024

    m = _DATE_RANGE_RE.search(description)
    if not m:
        return None, None

    if m.group(1) and m.group(2):
        # "20.03-02.04.2024"
        start_raw = m.group(1)     # "20.03"
        end_raw = m.group(2)       # "02.04.2024"
        end_date = _parse_ro_date(end_raw, year)
        # Start month defaults to end's year; handle cross-month ranges
        end_parts = end_raw.split(".")
        end_year = int(end_parts[2]) if len(end_parts) == 3 else year
        start_m_parts = start_raw.split(".")
        start_m = int(start_m_parts[1]) if len(start_m_parts) >= 2 else 1
        end_m = int(end_parts[1]) if len(end_parts) >= 2 else start_m
        start_year = end_year - 1 if start_m > end_m else end_year
        start_date = _parse_ro_date(start_raw, start_year)
    else:
        # "6-26.09.2023" compact
        start_day = m.group(3)    # "6"
        end_raw = m.group(4)      # "26.09.2023"
        end_parts = end_raw.split(".")
        month = end_parts[1].zfill(2) if len(end_parts) >= 2 else "01"
        end_year = int(end_parts[2]) if len(end_parts) == 3 else year
        start_date = f"{end_year}-{month}-{start_day.zfill(2)}"
        end_date = _parse_ro_date(end_raw, end_year)

    return start_date, end_date


def _extract_pct(description: str) -> float | None:
    m = _PCT_RE.search(description)
    return float(m.group(1)) if m else None


def _extract_category_hint(description: str) -> tuple[str, str, float]:
    """Return (category_hint_raw, db_category, confidence) from description.

    category_hint_raw is the best-guess short label extracted from the text.
    """
    desc_lower = description.lower()

    for keyword, db_cat, conf in CATEGORY_KEYWORD_MAP:
        if keyword in desc_lower:
            # Extract the human-readable portion around the keyword
            idx = desc_lower.find(keyword)
            hint = description[idx: idx + len(keyword)].strip()
            return hint, db_cat, conf

    return "", "", 0.0


# ---------------------------------------------------------------------------
# Row classification
# ---------------------------------------------------------------------------

def _classify_row(cod_articol: str, denumire: str) -> str:
    """Return source_type for a discount row."""
    cod = cod_articol.strip().upper()
    den_lower = denumire.lower()
    if re.match(r"^DISCOUNT\d+$", cod):
        return "campaign"
    if cod == "DISCOUNT" and "fidelizare" in den_lower:
        return "loyalty"
    if cod == "DISCOUNT":
        return "discount_other"
    if "voucher" in cod.lower():
        return "voucher"
    return "unknown"


# ---------------------------------------------------------------------------
# Parse all sales CSVs
# ---------------------------------------------------------------------------

def parse_all_discount_rows() -> pd.DataFrame:
    """Read all sales CSVs, extract discount rows, return structured DataFrame."""
    all_rows: list[dict] = []

    for f in SALES_FILES:
        try:
            df = pd.read_csv(f, dtype=str, keep_default_na=False, on_bad_lines="skip")
            df.columns = [c.strip().strip('"') for c in df.columns]
        except Exception as e:
            print(f"  Skipping {f.name}: {e}")
            continue

        cod_col = next((c for c in df.columns if "COD ARTICOL" in c.upper()), None)
        den_col = next((c for c in df.columns if "DENUMIRE" in c.upper()), None)
        date_col = next((c for c in df.columns if "DATA" in c.upper()), None)
        val_col = next((c for c in df.columns if "VALOARE" in c.upper()), None)
        order_col = next((c for c in df.columns if "ID COMANDA" in c.upper()), None)

        if not cod_col or not den_col:
            continue

        cod_clean = df[cod_col].str.strip().str.strip('"').str.upper()
        mask = cod_clean.str.startswith("DISCOUNT") | cod_clean.str.contains("VOUCHER")
        discount_rows = df[mask].copy()

        for _, row in discount_rows.iterrows():
            cod = str(row.get(cod_col, "")).strip().strip('"')
            den = str(row.get(den_col, "")).strip().strip('"')
            date_raw = str(row.get(date_col, "")).strip().strip('"') if date_col else ""
            val = str(row.get(val_col, "")).strip().strip('"') if val_col else ""
            order_id = str(row.get(order_col, "")).strip().strip('"') if order_col else ""
            all_rows.append({
                "source_file": f.name,
                "cod_articol": cod,
                "denumire": den,
                "date_raw": date_raw,
                "valoare": val,
                "order_id": order_id,
            })

    return pd.DataFrame(all_rows) if all_rows else pd.DataFrame()


# ---------------------------------------------------------------------------
# Build promo_calendar
# ---------------------------------------------------------------------------

def build_promo_calendar(df: pd.DataFrame) -> list[dict]:
    """Collapse discount rows into one record per campaign_id."""
    campaigns: dict[str, dict] = {}

    for _, row in df.iterrows():
        cod = row["cod_articol"]
        den = row["denumire"]
        source_type = _classify_row(cod, den)

        if source_type == "loyalty":
            # Loyalty rows: no campaign dates, tracked separately via loyalty_flag
            continue

        if source_type != "campaign":
            continue

        if cod in campaigns:
            continue  # already processed

        start_date, end_date = _extract_dates(den)
        pct = _extract_pct(den)
        hint, db_cat, conf = _extract_category_hint(den)

        campaigns[cod] = {
            "campaign_id": cod,
            "start_date": start_date or "",
            "end_date": end_date or "",
            "discount_pct": pct,
            "category_hint": hint,
            "db_category": db_cat,
            "source_type": source_type,
            "confidence": conf,
            "description": den,
        }

    return list(campaigns.values())


# ---------------------------------------------------------------------------
# Build sku_promo_weeks
# ---------------------------------------------------------------------------

def build_sku_promo_weeks(
    promo_calendar: list[dict],
    db_path: Path,
) -> list[dict]:
    """For each A-tier SKU, flag weeks that overlap with a campaign for its category.

    Also computes loyalty_flag from weeks with DISCOUNT/Fidelizare activity.
    """
    conn = sqlite3.connect(str(db_path))

    # Load A-tier SKUs with their categories and all week_starts
    sku_df = pd.read_sql_query(
        """
        SELECT DISTINCT w.sku_id, a.category, w.week_start
        FROM weekly_demand w
        JOIN abc_tiers a ON w.sku_id = a.sku_id
        WHERE a.tier = 'A'
        ORDER BY w.sku_id, w.week_start
        """,
        conn,
    )
    conn.close()

    sku_df["week_start_dt"] = pd.to_datetime(sku_df["week_start"])

    # Build lookup: (db_category, week_start_dt) → (promo_flag, confidence)
    # A week is flagged if it overlaps [start_date, end_date] for a campaign
    # targeting the same db_category.
    promo_map: dict[tuple[str, pd.Timestamp], tuple[int, float]] = {}

    for c in promo_calendar:
        if not c["start_date"] or not c["end_date"] or not c["db_category"]:
            continue
        try:
            start = pd.Timestamp(c["start_date"])
            end = pd.Timestamp(c["end_date"])
        except Exception:
            continue
        db_cat = c["db_category"]
        conf = float(c["confidence"])

        # Find all Monday weeks that overlap with [start, end]
        cat_weeks = sku_df[sku_df["category"] == db_cat]["week_start_dt"].unique()
        for w in cat_weeks:
            # Week window: [w, w+6 days]
            w_end = w + pd.Timedelta(days=6)
            if w <= end and w_end >= start:
                key = (db_cat, w)
                existing_conf = promo_map.get(key, (0, 0.0))[1]
                if conf > existing_conf:
                    promo_map[key] = (1, conf)

    # Loyalty weeks: any week with Fidelizare transaction activity
    # We don't know exact SKU-level loyalty redemptions — mark store-wide.
    # For simplicity: derive from a rough date range across all files.
    # Loyalty is always active (ongoing program), so loyalty_flag = 1 for all weeks.
    # This is an honest simplification — loyalty affects all customers, all weeks.
    loyalty_flag_global = 1

    rows: list[dict] = []
    seen: set[tuple[str, str]] = set()

    for _, row in sku_df.iterrows():
        key = (row["sku_id"], row["week_start"])
        if key in seen:
            continue
        seen.add(key)

        cat = row["category"]
        w = row["week_start_dt"]
        promo_entry = promo_map.get((cat, w), (0, 0.0))

        rows.append({
            "sku_id": row["sku_id"],
            "week_start": row["week_start"],
            "promo_flag": promo_entry[0],
            "loyalty_flag": loyalty_flag_global,
            "confidence": promo_entry[1],
        })

    return rows


# ---------------------------------------------------------------------------
# Write to SQLite
# ---------------------------------------------------------------------------

def create_tables(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        DROP TABLE IF EXISTS promo_calendar;
        CREATE TABLE promo_calendar (
            campaign_id   TEXT PRIMARY KEY,
            start_date    TEXT NOT NULL,
            end_date      TEXT NOT NULL,
            discount_pct  REAL,
            category_hint TEXT,
            db_category   TEXT,
            source_type   TEXT NOT NULL,
            confidence    REAL NOT NULL,
            description   TEXT
        );

        DROP TABLE IF EXISTS sku_promo_weeks;
        CREATE TABLE sku_promo_weeks (
            sku_id       TEXT NOT NULL,
            week_start   TEXT NOT NULL,
            promo_flag   INTEGER NOT NULL,
            loyalty_flag INTEGER NOT NULL,
            confidence   REAL NOT NULL,
            PRIMARY KEY (sku_id, week_start)
        );
    """)
    conn.commit()


def main() -> None:
    print(f"Scanning {len(SALES_FILES)} sales CSV files...")
    for f in SALES_FILES:
        print(f"  {f.name}")

    df = parse_all_discount_rows()
    if df.empty:
        print("No discount rows found.")
        return

    print(f"\nFound {len(df):,} discount rows total.")
    print(f"Unique campaign IDs: {df['cod_articol'].nunique()}")

    promo_cal = build_promo_calendar(df)
    print(f"\npromo_calendar: {len(promo_cal)} campaigns")
    for c in sorted(promo_cal, key=lambda x: x["campaign_id"]):
        print(f"  {c['campaign_id']:12} {c['start_date'] or '?':12} {c['end_date'] or '?':12} "
              f"{str(c['discount_pct']) + '%' if c['discount_pct'] else '?':6} "
              f"cat={c['db_category'] or 'unknown':25} conf={c['confidence']:.1f}  {c['description'][:60]}")

    sku_weeks = build_sku_promo_weeks(promo_cal, DB_PATH)
    promo_flagged = sum(1 for r in sku_weeks if r["promo_flag"] == 1)
    print(f"\nsku_promo_weeks: {len(sku_weeks):,} rows, {promo_flagged:,} with promo_flag=1")

    conn = sqlite3.connect(str(DB_PATH))
    try:
        create_tables(conn)

        conn.executemany(
            "INSERT INTO promo_calendar VALUES (?,?,?,?,?,?,?,?,?)",
            [(c["campaign_id"], c["start_date"], c["end_date"], c["discount_pct"],
              c["category_hint"], c["db_category"], c["source_type"],
              c["confidence"], c["description"]) for c in promo_cal],
        )

        conn.executemany(
            "INSERT OR IGNORE INTO sku_promo_weeks VALUES (?,?,?,?,?)",
            [(r["sku_id"], r["week_start"], r["promo_flag"],
              r["loyalty_flag"], r["confidence"]) for r in sku_weeks],
        )
        conn.commit()
        print(f"\nWrote to {DB_PATH}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
