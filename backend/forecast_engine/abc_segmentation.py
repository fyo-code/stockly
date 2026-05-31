"""
ABC Segmentation for Mobexpert SKUs.

Classifies SKUs into A/B/C tiers by cumulative revenue contribution:
  A = top 80% of revenue (~5% of SKUs)
  B = 80–95% of revenue (~15% of SKUs)
  C = 95–100% of revenue (~80% of SKUs)

Also classifies demand pattern:
  SMOOTH  = ≤40% zero-weeks (consistent weekly sales)
  LUMPY   = >40% zero-weeks (intermittent demand)

Usage:
    python3 backend/forecast_engine/abc_segmentation.py
"""

import sqlite3
import logging
from pathlib import Path
from typing import Tuple

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s"
)
log = logging.getLogger(__name__)

# Thresholds
A_THRESHOLD = 0.80
B_THRESHOLD = 0.95
LUMPY_ZERO_WEEK_PCT = 0.80  # >80% zero-weeks = truly intermittent for furniture retail

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DB_PATH = PROJECT_ROOT / "backend" / "data" / "supply_chain.db"


def run_abc_segmentation(db_path: str) -> Tuple[int, int, int]:
    """
    Run ABC + demand pattern classification on all SKUs in weekly_demand.

    Creates/replaces abc_tiers table with columns:
      sku_id, category, tier (A/B/C), demand_pattern (SMOOTH/LUMPY),
      total_revenue, total_units, pct_revenue, cumulative_pct,
      num_weeks_active, num_weeks_zero, zero_week_pct

    Returns (a_count, b_count, c_count).
    """
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()

        # Drop and recreate
        cursor.execute("DROP TABLE IF EXISTS abc_tiers")
        cursor.execute("""
            CREATE TABLE abc_tiers (
                sku_id            TEXT PRIMARY KEY,
                category          TEXT NOT NULL,
                tier              TEXT NOT NULL,
                demand_pattern    TEXT NOT NULL,
                total_revenue     REAL NOT NULL,
                total_units       INTEGER NOT NULL,
                pct_revenue       REAL NOT NULL,
                cumulative_pct    REAL NOT NULL,
                num_weeks_active  INTEGER NOT NULL,
                num_weeks_zero    INTEGER NOT NULL,
                zero_week_pct     REAL NOT NULL
            )
        """)

        # Get total weeks in dataset
        total_weeks = cursor.execute(
            "SELECT COUNT(DISTINCT week_start) FROM weekly_demand"
        ).fetchone()[0]
        log.info(f"Total weeks in dataset: {total_weeks}")

        # Compute per-SKU revenue and activity
        cursor.execute("""
            SELECT
                sku_id,
                category,
                SUM(revenue) AS total_revenue,
                SUM(units_sold) - SUM(units_returned) AS total_units,
                COUNT(DISTINCT week_start) AS weeks_active
            FROM weekly_demand
            GROUP BY sku_id, category
            ORDER BY total_revenue DESC
        """)
        sku_rows = cursor.fetchall()

        # Total revenue for percentage calculation
        grand_total = sum(row[2] for row in sku_rows)
        log.info(f"Grand total revenue: {grand_total:,.2f} RON across {len(sku_rows):,} SKUs")

        # Classify
        cumulative = 0.0
        a_count = b_count = c_count = 0
        batch = []

        for sku_id, category, revenue, units, weeks_active in sku_rows:
            pct = revenue / grand_total if grand_total > 0 else 0
            cumulative += pct

            # ABC tier
            if cumulative <= A_THRESHOLD:
                tier = "A"
                a_count += 1
            elif cumulative <= B_THRESHOLD:
                tier = "B"
                b_count += 1
            else:
                tier = "C"
                c_count += 1

            # Demand pattern: weeks with zero net sales
            weeks_zero = total_weeks - weeks_active
            zero_pct = weeks_zero / total_weeks if total_weeks > 0 else 0
            pattern = "LUMPY" if zero_pct > LUMPY_ZERO_WEEK_PCT else "SMOOTH"

            batch.append((
                sku_id, category, tier, pattern,
                revenue, units, pct, cumulative,
                weeks_active, weeks_zero, zero_pct
            ))

        cursor.executemany("""
            INSERT INTO abc_tiers
            (sku_id, category, tier, demand_pattern,
             total_revenue, total_units, pct_revenue, cumulative_pct,
             num_weeks_active, num_weeks_zero, zero_week_pct)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, batch)

        # Create index for fast tier lookups
        cursor.execute("CREATE INDEX idx_abc_tier ON abc_tiers(tier)")
        cursor.execute("CREATE INDEX idx_abc_pattern ON abc_tiers(demand_pattern)")

        conn.commit()

        log.info(f"✓ ABC segmentation complete: A={a_count:,}, B={b_count:,}, C={c_count:,}")

        # Print summary stats
        for tier_name in ("A", "B", "C"):
            stats = cursor.execute("""
                SELECT
                    COUNT(*),
                    SUM(total_revenue),
                    SUM(CASE WHEN demand_pattern = 'SMOOTH' THEN 1 ELSE 0 END),
                    SUM(CASE WHEN demand_pattern = 'LUMPY' THEN 1 ELSE 0 END)
                FROM abc_tiers WHERE tier = ?
            """, (tier_name,)).fetchone()
            count, rev, smooth, lumpy = stats
            log.info(
                f"  {tier_name}: {count:,} SKUs, {rev:,.0f} RON "
                f"({rev/grand_total*100:.1f}%), "
                f"Smooth={smooth:,}, Lumpy={lumpy:,}"
            )

        # Category breakdown for A-tier
        log.info("\n  A-tier by category:")
        a_cats = cursor.execute("""
            SELECT category, COUNT(*), SUM(total_revenue)
            FROM abc_tiers WHERE tier = 'A'
            GROUP BY category ORDER BY SUM(total_revenue) DESC
        """).fetchall()
        for cat, count, rev in a_cats:
            log.info(f"    {cat:<35} {count:>5} SKUs  {rev:>12,.0f} RON")

        return a_count, b_count, c_count

    finally:
        conn.close()


if __name__ == "__main__":
    import sys
    db = sys.argv[1] if len(sys.argv) > 1 else str(DB_PATH)
    a, b, c = run_abc_segmentation(db)
    total = a + b + c
    print(f"\nABC Summary:")
    print(f"  A-tier: {a:,} SKUs ({a/total*100:.1f}%)")
    print(f"  B-tier: {b:,} SKUs ({b/total*100:.1f}%)")
    print(f"  C-tier: {c:,} SKUs ({c/total*100:.1f}%)")
    print(f"  Total:  {total:,} SKUs")
