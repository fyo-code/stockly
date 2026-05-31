"""Phase 8B Baneasa 2022 sales ingestion and validation report."""

from __future__ import annotations

import argparse
import sqlite3
from datetime import datetime
from pathlib import Path

try:
    from .ingestion import DB_PATH, import_sources
except ImportError:  # Allows direct script execution.
    from ingestion import DB_PATH, import_sources


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = PROJECT_ROOT / "new_stock_data_20may" / "baneasa_sales22.csv"
DEFAULT_REPORT = PROJECT_ROOT / "active_docs" / "ITER5K_V2_PHASE8B_BANEASA_2022_INGESTION.md"
BASELINE_HIT20 = 0.241
BASELINE_HIT30 = 0.353
BASELINE_WMAPE = 0.561
BASELINE_PHANTOM = 0.481


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


def _source_row(conn: sqlite3.Connection, source_path: Path) -> dict[str, object]:
    row = conn.execute(
        """
        SELECT
            file_name, rows_seen, rows_inserted, rows_duplicate, rows_filtered,
            rows_invoice_date_fallback, rows_missing_effective_sale_date,
            rows_missing_sku, rows_missing_store, first_sale_date, last_sale_date
        FROM source_files_v2
        WHERE source_file = ?
        """,
        (str(source_path),),
    ).fetchone()
    if row is None:
        raise RuntimeError(f"No source_files_v2 row found for {source_path}")
    keys = [
        "file_name",
        "rows_seen",
        "rows_inserted",
        "rows_duplicate",
        "rows_filtered",
        "rows_invoice_date_fallback",
        "rows_missing_effective_sale_date",
        "rows_missing_sku",
        "rows_missing_store",
        "first_sale_date",
        "last_sale_date",
    ]
    return dict(zip(keys, row))


def _store_year_rows(conn: sqlite3.Connection) -> list[list[str]]:
    rows = []
    for row in conn.execute(
        """
        SELECT
            substr(sale_date, 1, 4) AS sale_year,
            COUNT(*) AS rows,
            COUNT(DISTINCT sku_id) AS skus,
            SUM(net_units) AS net_units,
            SUM(net_revenue) AS net_revenue,
            SUM(used_invoice_date_fallback) AS fallback_rows,
            SUM(is_return) AS return_rows
        FROM raw_sales_transactions_v2
        WHERE store_id = 'baneasa' AND is_non_product = 0
        GROUP BY sale_year
        ORDER BY sale_year
        """
    ):
        sale_year, rows_count, skus, net_units, net_revenue, fallback_rows, return_rows = row
        rows.append(
            [
                str(sale_year),
                _fmt_num(rows_count, 0),
                _fmt_num(skus, 0),
                _fmt_num(net_units),
                _fmt_num(net_revenue),
                _fmt_num(fallback_rows or 0, 0),
                _fmt_pct((fallback_rows or 0) / rows_count if rows_count else None),
                _fmt_num(return_rows or 0, 0),
            ]
        )
    return rows


def _source_conservation_rows(conn: sqlite3.Connection, source_path: Path) -> list[list[str]]:
    raw = conn.execute(
        """
        SELECT
            COUNT(*), COUNT(DISTINCT sku_id),
            SUM(gross_units), SUM(returned_units), SUM(net_units),
            SUM(gross_revenue), SUM(returned_revenue), SUM(net_revenue),
            SUM(is_non_product)
        FROM raw_sales_transactions_v2
        WHERE source_file = ?
        """,
        (str(source_path),),
    ).fetchone()
    weekly_store = conn.execute(
        """
        SELECT
            SUM(gross_units), SUM(returned_units), SUM(net_units),
            SUM(gross_revenue), SUM(returned_revenue), SUM(net_revenue)
        FROM weekly_store_demand_v2
        WHERE store_id = 'baneasa'
          AND week_start BETWEEN '2021-12-27' AND '2023-01-02'
        """
    ).fetchone()
    return [
        [
            "raw source rows",
            _fmt_num(raw[0] or 0, 0),
            _fmt_num(raw[1] or 0, 0),
            _fmt_num(raw[2]),
            _fmt_num(raw[3]),
            _fmt_num(raw[4]),
            _fmt_num(raw[5]),
            _fmt_num(raw[6]),
            _fmt_num(raw[7]),
            _fmt_num(raw[8] or 0, 0),
        ],
        [
            "Baneasa weekly 2022 window",
            "-",
            "-",
            _fmt_num(weekly_store[0]),
            _fmt_num(weekly_store[1]),
            _fmt_num(weekly_store[2]),
            _fmt_num(weekly_store[3]),
            _fmt_num(weekly_store[4]),
            _fmt_num(weekly_store[5]),
            "-",
        ],
    ]


def _invalidate_forecast_outputs(conn: sqlite3.Connection) -> None:
    """Remove derived forecast outputs that are stale after sales ingestion."""
    for table in [
        "forecast_v2_scorecard_slices",
        "forecast_v2_score_rows",
        "forecast_v2_actuals_4w",
        "forecast_v2_predictions",
        "forecast_v2_score_runs",
        "forecast_v2_regime_labels",
    ]:
        exists = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name = ?",
            (table,),
        ).fetchone()
        if exists:
            conn.execute(f"DELETE FROM {table}")
    conn.commit()


def build_report(conn: sqlite3.Connection, source_path: Path) -> str:
    source = _source_row(conn, source_path)
    fallback_rate = (
        source["rows_invoice_date_fallback"] / source["rows_inserted"]
        if source["rows_inserted"]
        else None
    )
    return "\n".join(
        [
            "# Iteration 5K — V2 Phase 8B Baneasa 2022 Sales Ingestion",
            "",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            "## Phase Checkpoint",
            "",
            "Phase completed: Phase 8B — Baneasa 2022 sales ingestion",
            "",
            "What changed: `baneasa_sales22.csv` was imported into v2 raw sales tables, weekly store demand and weekly chain demand were rebuilt, and stale forecast score/regime tables were invalidated.",
            "",
            "Accuracy rerun: no. This phase changes the sales foundation, so old persisted score rows are stale. The model will be rerun after stock/supplier availability features are added.",
            "",
            _table(
                ["Baseline metric", "Current control before Phase 8B"],
                [
                    ["Best model", "sk_blend_post_bf_safe"],
                    ["Hit +/-20", _fmt_pct(BASELINE_HIT20)],
                    ["Hit +/-30", _fmt_pct(BASELINE_HIT30)],
                    ["WMAPE", _fmt_pct(BASELINE_WMAPE)],
                    ["Phantom rate", _fmt_pct(BASELINE_PHANTOM)],
                ],
            ),
            "",
            "## Source Import Result",
            "",
            _table(
                ["File", "Seen", "Inserted", "Duplicate", "Filtered", "DATA fallback", "Fallback %", "Missing date", "Missing SKU", "Missing store", "Date range"],
                [
                    [
                        str(source["file_name"]),
                        _fmt_num(source["rows_seen"], 0),
                        _fmt_num(source["rows_inserted"], 0),
                        _fmt_num(source["rows_duplicate"], 0),
                        _fmt_num(source["rows_filtered"], 0),
                        _fmt_num(source["rows_invoice_date_fallback"], 0),
                        _fmt_pct(fallback_rate),
                        _fmt_num(source["rows_missing_effective_sale_date"], 0),
                        _fmt_num(source["rows_missing_sku"], 0),
                        _fmt_num(source["rows_missing_store"], 0),
                        f"{source['first_sale_date']}..{source['last_sale_date']}",
                    ]
                ],
            ),
            "",
            "## Baneasa Store-Year Coverage",
            "",
            _table(
                ["Year", "Rows", "SKUs", "Net units", "Net revenue", "Fallback rows", "Fallback %", "Return rows"],
                _store_year_rows(conn),
            ),
            "",
            "## Source Conservation Check",
            "",
            _table(
                ["Layer", "Rows", "SKUs", "Gross units", "Returned units", "Net units", "Gross revenue", "Returned revenue", "Net revenue", "Non-product rows"],
                _source_conservation_rows(conn, source_path),
            ),
            "",
            "## Decision",
            "",
            "Phase 8B is usable. Baneasa 2022 is now part of the v2 sales foundation, with high but expected invoice-date fallback usage. Proceed next to Phase 8C monthly store stock ingestion.",
            "",
            "## Notes",
            "",
            "- The file does not include `MAGAZIN`; the importer now infers Baneasa from the filename for single-store exports.",
            "- Old forecast score/regime tables were cleared because the demand foundation changed.",
            "- No model accuracy improvement is claimed until the official rerun after Phase 8E/8G.",
            "",
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Phase 8B Baneasa 2022 ingestion.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()

    import_sources(args.input, db_path=args.db, rebuild=False, dry_run=False, report_path=None)

    conn = sqlite3.connect(args.db)
    try:
        _invalidate_forecast_outputs(conn)
        report = build_report(conn, args.input)
    finally:
        conn.close()

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report, encoding="utf-8")
    print(report)
    print(f"Wrote {args.report}")


if __name__ == "__main__":
    main()
