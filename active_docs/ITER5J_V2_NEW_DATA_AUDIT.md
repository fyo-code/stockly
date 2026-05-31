# Iteration 5J — V2 New Data Audit

Generated: 2026-05-20 19:51
Input folder: `/Users/fyodorgolovin/Downloads/Supply-Inventory v1.0 codex/new_stock_data_20may`

## Phase Checkpoint

Phase completed: Phase 8A — New data validation and manifest

What changed: no forecast tables, model behavior, or sales/stock ingestion tables were changed. This is a read-only validation report for the new files.

Accuracy rerun: no. This phase validates data only, so hit +/-20 remains at the Phase 7E control baseline of 24.1%.

## Reference Population

| Reference | Count |
| --- | --- |
| sales SKUs in `weekly_chain_demand_v2` | 110,512 |
| headline SKUs in current regime labels | 3,857 |
| SKUs already in monthly store stock | 12,636 |
| stores already in monthly store stock | 8 |
| normalized product names available for supplier mapping | 105,450 |

## File Manifest

| File | Kind | Feature scope | Rows | SKUs | Sales overlap | Headline overlap | First period | Last period | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baneasa_sales22.csv | historical_sales | historical_backtest | 233,245 | 33,827 | 28,855 | 2,371 | 2018-10-24 | 2022-12-31 | Useful Baneasa 2022 coverage; about half of rows rely on DATA invoice fallback. |
| const_magazin_stock.csv | monthly_store_stock | historical_backtest | 4,752 | 4,752 | 4,228 | 117 | 2022-01-01 | 2025-12-01 | Directly ingestible through the existing wide monthly stock normalizer. |
| iasi_magazin_stock.csv | monthly_store_stock | historical_backtest | 4,705 | 4,705 | 4,450 | 116 | 2022-01-01 | 2025-12-01 | Directly ingestible through the existing wide monthly stock normalizer. |
| oradea_magazin_stock.csv | monthly_store_stock | historical_backtest | 3,048 | 3,048 | 2,934 | 110 | 2022-01-01 | 2025-12-01 | Directly ingestible through the existing wide monthly stock normalizer. |
| supplier_stock_22.csv | monthly_supplier_stock | historical_backtest | 440,424 | 36,267 | 36,262 | 2,045 | 2022-01-01 | 2022-12-01 | Needs supplier-stock normalizer and exact product-name SKU map; ambiguous mappings should be stored but excluded from model features. |
| supplier_stock_23.csv | monthly_supplier_stock | historical_backtest | 440,773 | 38,544 | 38,534 | 2,797 | 2023-01-01 | 2023-12-01 | Needs supplier-stock normalizer and exact product-name SKU map; ambiguous mappings should be stored but excluded from model features. |
| supplier_stock_24.csv | monthly_supplier_stock | historical_backtest | 459,912 | 41,663 | 41,631 | 3,089 | 2024-01-01 | 2024-12-01 | Needs supplier-stock normalizer and exact product-name SKU map; ambiguous mappings should be stored but excluded from model features. |
| supplier_stock_25.csv | monthly_supplier_stock | historical_backtest | 481,333 | 39,034 | 38,998 | 2,656 | 2025-01-01 | 2025-12-01 | Needs supplier-stock normalizer and exact product-name SKU map; ambiguous mappings should be stored but excluded from model features. |
| viteza rotatie stock constanta.csv | rotation_snapshot | current_snapshot | 52,251 | 52,251 | 42,470 | 3,342 | - | - | High SKU overlap, but current-snapshot only unless a historical as-of date is proven. |
| viteza rotatie stock militari.csv | rotation_snapshot | current_snapshot | 52,783 | 52,783 | 43,009 | 3,337 | - | - | High SKU overlap, but current-snapshot only unless a historical as-of date is proven. |
| viteza rotatie stock pipera.csv | rotation_snapshot | current_snapshot | 55,323 | 55,323 | 43,954 | 3,385 | - | - | High SKU overlap, but current-snapshot only unless a historical as-of date is proven. |
| viteza rotatie stock sibiu.csv | rotation_snapshot | current_snapshot | 50,699 | 50,699 | 41,679 | 3,314 | - | - | High SKU overlap, but current-snapshot only unless a historical as-of date is proven. |

## Monthly Store Stock

| File | Store | Rows | Months | SKUs | Sales overlap | Headline overlap | New vs existing stock | Zero values | Negative values | Duplicate keys |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| const_magazin_stock.csv | constanta | 4,752 | 48 | 4,752 | 4,228 | 117 | 366 | 14,107 | 0 | 0 |
| iasi_magazin_stock.csv | iasi | 4,705 | 48 | 4,705 | 4,450 | 116 | 246 | 8,557 | 0 | 0 |
| oradea_magazin_stock.csv | oradea | 3,048 | 48 | 3,048 | 2,934 | 110 | 128 | 4,155 | 0 | 0 |

## Supplier Stock Mapping Readiness

| File | Rows | Suppliers | Products | Exact mapped rows | Ambiguous rows | Unmapped rows | Mapped SKUs | Headline mapped SKUs | Duplicate keys | Coverage |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| supplier_stock_22.csv | 440,424 | 12 | 61,129 | 273,777 | 8,831 | 157,816 | 36,267 | 2,045 | 193 | 2022-01-01..2022-12-01 |
| supplier_stock_23.csv | 440,773 | 12 | 62,779 | 278,604 | 9,206 | 152,963 | 38,544 | 2,797 | 151 | 2023-01-01..2023-12-01 |
| supplier_stock_24.csv | 459,912 | 12 | 65,208 | 294,591 | 9,868 | 155,453 | 41,663 | 3,089 | 252 | 2024-01-01..2024-12-01 |
| supplier_stock_25.csv | 481,333 | 12 | 65,196 | 300,084 | 9,136 | 172,113 | 39,034 | 2,656 | 187 | 2025-01-01..2025-12-01 |

## Rotation Snapshot Readiness

| File | Rows | SKUs | Sales overlap | Headline overlap | Non-null values | Zero values | Negative values | Store stock columns |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| viteza rotatie stock constanta.csv | 52,251 | 52,251 | 42,470 | 3,342 | 332,333 | 6,829 | 569 | Stoc Total POZITIE Constanta, Stoc Total Cantitativ Constanta, Stoc Disponibil Cantitativ Constanta |
| viteza rotatie stock militari.csv | 52,783 | 52,783 | 43,009 | 3,337 | 332,108 | 6,010 | 569 | Stoc Total POZITIE Militari, Stoc Disponibil Cantitativ Militari, Stoc Total Cantitativ Militari |
| viteza rotatie stock pipera.csv | 55,323 | 55,323 | 43,954 | 3,385 | 353,402 | 8,455 | 569 | Stoc Total POZITIE Pipera, Stoc Disponibil Cantitativ Pipera, Stoc Total Cantitativ Pipera |
| viteza rotatie stock sibiu.csv | 50,699 | 50,699 | 41,679 | 3,314 | 320,065 | 5,574 | 569 | Stoc Total POZITIE Sibiu, Stoc Disponibil Cantitativ Sibiu, Stoc Total Cantitativ Sibiu |

## Baneasa Sales Readiness

| File | Rows | SKUs | Headline overlap | Invoice fallback rows | Missing effective date | Campaign nullish | BF nullish | Negative qty rows | Duplicate line candidates |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baneasa_sales22.csv | 233,245 | 33,827 | 2,371 | 115,891 | 0 | 30.1% | 93.6% | 4,993 | 0 |

## Decision

Phase 8A confirms the new data package is worth ingesting. The monthly store stock files are clean and directly usable; supplier stock is the largest accuracy lever, but it must pass through a confidence-controlled product-name-to-SKU map; rotation files are high coverage but current-snapshot only.

## Phase 8B/8C/8D Readiness

- Phase 8B can proceed with `baneasa_sales22.csv`; the main risk is high invoice-date fallback usage, not file usability.
- Phase 8C can proceed with the three monthly store stock files; schemas match the existing wide monthly normalizer.
- Phase 8D can proceed, but must implement confidence-controlled supplier product-name mapping before using supplier stock in features.
- Rotation files should wait until Phase 8F and must remain `current_snapshot` for official backtests.
