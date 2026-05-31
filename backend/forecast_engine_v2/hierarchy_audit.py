"""Audit forecast v2 hierarchy and feature-signal coverage."""

from __future__ import annotations

import argparse
import sqlite3
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "backend" / "data" / "supply_chain.db"
DEFAULT_OUTPUT = PROJECT_ROOT / "active_docs" / "ITER5A_V2_HIERARCHY_SIGNAL_AUDIT.md"


def _rows(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
    conn.row_factory = sqlite3.Row
    return conn.execute(sql, params).fetchall()


def _fmt_num(value: object, digits: int = 0) -> str:
    if value is None:
        return "-"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if digits == 0:
        return f"{number:,.0f}"
    return f"{number:,.{digits}f}"


def _md_table(headers: list[str], rows: list[list[object]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(cell) for cell in row) + " |")
    return "\n".join(lines)


def build_report(conn: sqlite3.Connection) -> str:
    total = _rows(
        conn,
        """
        SELECT
            COUNT(*) AS rows,
            COUNT(DISTINCT sku_id) AS skus,
            SUM(net_units) AS units,
            SUM(net_revenue) AS revenue
        FROM raw_sales_transactions_v2
        WHERE is_non_product = 0
        """,
    )[0]
    unknown = _rows(
        conn,
        """
        SELECT
            COUNT(*) AS rows,
            COUNT(DISTINCT sku_id) AS skus,
            SUM(net_units) AS units,
            SUM(net_revenue) AS revenue
        FROM raw_sales_transactions_v2
        WHERE is_non_product = 0 AND category_norm = 'NECUNOSCUT'
        """,
    )[0]

    category_rows = _rows(
        conn,
        """
        SELECT category_norm, COUNT(DISTINCT sku_id) AS skus, SUM(net_revenue) AS revenue, SUM(net_units) AS units
        FROM raw_sales_transactions_v2
        WHERE is_non_product = 0
        GROUP BY category_norm
        ORDER BY revenue DESC
        """,
    )
    category_source_rows = _rows(
        conn,
        """
        SELECT category_signal_status, category_source, COUNT(*) AS rows, SUM(net_revenue) AS revenue
        FROM raw_sales_transactions_v2
        WHERE is_non_product = 0
        GROUP BY category_signal_status, category_source
        ORDER BY revenue DESC
        """,
    )
    unknown_by_store = _rows(
        conn,
        """
        SELECT store_id, COUNT(*) AS rows, COUNT(DISTINCT sku_id) AS skus, SUM(net_revenue) AS revenue
        FROM raw_sales_transactions_v2
        WHERE is_non_product = 0 AND category_norm = 'NECUNOSCUT'
        GROUP BY store_id
        ORDER BY revenue DESC
        """,
    )
    remaining_unknown = _rows(
        conn,
        """
        SELECT
            COALESCE(group_raw, '#null') AS group_raw,
            COALESCE(category_raw, '#null') AS category_raw,
            COALESCE(class_raw, '#null') AS class_raw,
            COALESCE(subclass_raw, '#null') AS subclass_raw,
            COALESCE(raion_raw, '#null') AS raion_raw,
            COUNT(*) AS rows,
            SUM(net_revenue) AS revenue
        FROM raw_sales_transactions_v2
        WHERE is_non_product = 0 AND category_norm = 'NECUNOSCUT'
        GROUP BY group_raw, category_raw, class_raw, subclass_raw, raion_raw
        ORDER BY revenue DESC
        LIMIT 40
        """,
    )
    family_rows = _rows(
        conn,
        """
        SELECT product_family_v2, category_norm, COUNT(DISTINCT sku_id) AS skus, SUM(net_revenue) AS revenue
        FROM raw_sales_transactions_v2
        WHERE is_non_product = 0
        GROUP BY product_family_v2, category_norm
        ORDER BY revenue DESC
        LIMIT 30
        """,
    )
    signal_rows = _rows(
        conn,
        """
        SELECT bf_signal_status, bf_signal_source, COUNT(*) AS rows, SUM(net_revenue) AS revenue
        FROM raw_sales_transactions_v2
        WHERE is_non_product = 0
        GROUP BY bf_signal_status, bf_signal_source
        ORDER BY rows DESC
        """,
    )
    optional_signal_rows = _rows(
        conn,
        """
        SELECT 'dimensions' AS feature, product_dimensions_signal_status AS status, product_dimensions_source AS source, COUNT(*) AS rows
        FROM raw_sales_transactions_v2
        WHERE is_non_product = 0
        GROUP BY product_dimensions_signal_status, product_dimensions_source
        UNION ALL
        SELECT 'campaign', campaign_signal_status, campaign_signal_source, COUNT(*)
        FROM raw_sales_transactions_v2
        WHERE is_non_product = 0
        GROUP BY campaign_signal_status, campaign_signal_source
        UNION ALL
        SELECT 'supplier', supplier_signal_status, supplier_signal_source, COUNT(*)
        FROM raw_sales_transactions_v2
        WHERE is_non_product = 0
        GROUP BY supplier_signal_status, supplier_signal_source
        ORDER BY feature, rows DESC
        """,
    )
    conservation = _rows(
        conn,
        """
        SELECT
            (SELECT SUM(net_units) FROM raw_sales_transactions_v2 WHERE is_non_product = 0) AS raw_units,
            (SELECT SUM(net_units) FROM weekly_store_demand_v2) AS store_units,
            (SELECT SUM(net_units) FROM weekly_chain_demand_v2) AS chain_units,
            (SELECT SUM(net_revenue) FROM raw_sales_transactions_v2 WHERE is_non_product = 0) AS raw_revenue,
            (SELECT SUM(net_revenue) FROM weekly_store_demand_v2) AS store_revenue,
            (SELECT SUM(net_revenue) FROM weekly_chain_demand_v2) AS chain_revenue
        """
    )[0]

    unknown_revenue_pct = 0.0
    if total["revenue"]:
        unknown_revenue_pct = float(unknown["revenue"] or 0) / float(total["revenue"]) * 100

    lines = [
        "# Iteration 5A — V2 Hierarchy And Signal Audit",
        "",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "## Summary",
        "",
        _md_table(
            ["Metric", "Value"],
            [
                ["Product rows", _fmt_num(total["rows"])],
                ["Distinct SKUs", _fmt_num(total["skus"])],
                ["Net units", _fmt_num(total["units"], 1)],
                ["Net revenue", _fmt_num(total["revenue"], 2)],
                ["Unknown category rows", _fmt_num(unknown["rows"])],
                ["Unknown category SKUs", _fmt_num(unknown["skus"])],
                ["Unknown category revenue", _fmt_num(unknown["revenue"], 2)],
                ["Unknown category revenue share", f"{unknown_revenue_pct:.2f}%"],
            ],
        ),
        "",
        "## Category Distribution",
        "",
        _md_table(
            ["Category", "Distinct SKUs", "Net revenue", "Net units"],
            [
                [row["category_norm"], _fmt_num(row["skus"]), _fmt_num(row["revenue"], 2), _fmt_num(row["units"], 1)]
                for row in category_rows
            ],
        ),
        "",
        "## Category Signal Sources",
        "",
        _md_table(
            ["Status", "Source", "Rows", "Net revenue"],
            [
                [row["category_signal_status"], row["category_source"], _fmt_num(row["rows"]), _fmt_num(row["revenue"], 2)]
                for row in category_source_rows
            ],
        ),
        "",
        "## Unknown Category By Store",
        "",
        _md_table(
            ["Store", "Rows", "Distinct SKUs", "Net revenue"],
            [
                [row["store_id"], _fmt_num(row["rows"]), _fmt_num(row["skus"]), _fmt_num(row["revenue"], 2)]
                for row in unknown_by_store
            ],
        ),
        "",
        "## Top Product Families",
        "",
        _md_table(
            ["Product family", "Category", "Distinct SKUs", "Net revenue"],
            [
                [row["product_family_v2"], row["category_norm"], _fmt_num(row["skus"]), _fmt_num(row["revenue"], 2)]
                for row in family_rows
            ],
        ),
        "",
        "## Black Friday Signal Sources",
        "",
        _md_table(
            ["Status", "Source", "Rows", "Net revenue"],
            [
                [row["bf_signal_status"], row["bf_signal_source"], _fmt_num(row["rows"]), _fmt_num(row["revenue"], 2)]
                for row in signal_rows
            ],
        ),
        "",
        "## Optional Metadata Signal Sources",
        "",
        _md_table(
            ["Feature", "Status", "Source", "Rows"],
            [
                [row["feature"], row["status"], row["source"], _fmt_num(row["rows"])]
                for row in optional_signal_rows
            ],
        ),
        "",
        "## Remaining Unknown Raw Combinations",
        "",
        _md_table(
            ["GRUPA", "CATEGORIE", "CLASA", "SUBCLASA", "RAION", "Rows", "Net revenue"],
            [
                [
                    row["group_raw"],
                    row["category_raw"],
                    row["class_raw"],
                    row["subclass_raw"],
                    row["raion_raw"],
                    _fmt_num(row["rows"]),
                    _fmt_num(row["revenue"], 2),
                ]
                for row in remaining_unknown
            ],
        ),
        "",
        "## Conservation Checks",
        "",
        _md_table(
            ["Check", "Raw/source", "Aggregated"],
            [
                ["Raw product rows -> weekly store net units", _fmt_num(conservation["raw_units"], 2), _fmt_num(conservation["store_units"], 2)],
                ["Weekly store -> weekly chain net units", _fmt_num(conservation["store_units"], 2), _fmt_num(conservation["chain_units"], 2)],
                ["Raw product rows -> weekly store net revenue", _fmt_num(conservation["raw_revenue"], 2), _fmt_num(conservation["store_revenue"], 2)],
                ["Weekly store -> weekly chain net revenue", _fmt_num(conservation["store_revenue"], 2), _fmt_num(conservation["chain_revenue"], 2)],
            ],
        ),
        "",
        "## Interpretation",
        "",
        "- Category, campaign/BF, dimensions, and supplier fields now expose observed/inferred/unknown signal status.",
        "- Remaining unknown hierarchy rows should be reviewed before model training only if their revenue share is still material.",
        "- Inferred BF rows are calendar/timing features for lower-detail data; directly observed `CAMPANIE BF` rows remain separated in scorecards through `bf_signal_status` and observed/inferred counts.",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit forecast v2 hierarchy and feature signal coverage.")
    parser.add_argument("--db", type=Path, default=DB_PATH, help="SQLite database path.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Markdown report path.")
    args = parser.parse_args()

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    try:
        report = build_report(conn)
    finally:
        conn.close()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report, encoding="utf-8")
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()

