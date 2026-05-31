# Iteration 5M — V2 Phase 8D Supplier Monthly Stock Ingestion

Generated: 2026-05-21 09:47

## Phase Checkpoint

Phase completed: Phase 8D — supplier monthly stock ingestion and confidence-controlled SKU mapping.

What changed: supplier stock files for 2022-2025 were normalized into `stock_monthly_supplier_v2`; product-name mappings were stored in `supplier_stock_sku_map_v2` with `exact_unique`, `ambiguous`, or `unmapped` confidence. Only `exact_unique` rows should be used as model features in Phase 8E.

Accuracy rerun: no. This phase only adds supplier availability data. Accuracy will be re-measured after Phase 8E joins supplier and combined stock features into the model matrix.

| Baseline metric | Current official control before Phase 8D |
| --- | --- |
| Best model | sk_blend_post_bf_safe |
| Hit +/-20 | 24.1% |
| Hit +/-30 | 35.3% |
| WMAPE | 56.1% |
| Phantom rate | 48.1% |

## Import Result

| File | Rows | Rows processed | Skipped | Suppliers | Products | Mapped SKUs | Exact rows | Ambiguous rows | Unmapped rows | Month range | Prior rows removed |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| supplier_stock_22.csv | 440,424 | 440,424 | 0 | 12 | 61,129 | 38,444 | 280,775 | 9,503 | 150,146 | 2022-01-01..2022-12-01 | 0 |
| supplier_stock_23.csv | 440,773 | 440,773 | 0 | 12 | 62,779 | 39,011 | 280,837 | 9,738 | 150,198 | 2023-01-01..2023-12-01 | 0 |
| supplier_stock_24.csv | 459,912 | 459,912 | 0 | 12 | 65,208 | 41,855 | 295,688 | 10,333 | 153,891 | 2024-01-01..2024-12-01 | 0 |
| supplier_stock_25.csv | 481,333 | 481,333 | 0 | 12 | 65,196 | 39,190 | 300,741 | 9,569 | 171,023 | 2025-01-01..2025-12-01 | 0 |

## Mapping Summary

Supplier-stock table now contains `1,821,659` unique supplier/month/product records across `124,992` supplier product-name keys. Exact unique mappings cover `76,858` SKUs. Duplicate source rows for the same supplier/month/product key are aggregated into one table record.

| Mapping confidence | Product keys | Exact SKUs | Candidate SKU links | Raw sales name variants |
| --- | --- | --- | --- | --- |
| exact_unique | 76,858 | 76,858 | 76,858 | 76,859 |
| ambiguous | 1,819 | 0 | 4,654 | 1,936 |
| unmapped | 46,315 | 0 | 0 | 0 |

## Supplier Stock By Year

| Year | Records | Suppliers | Products | Exact SKUs | Exact rows % | Ambiguous rows % | Unmapped rows % | Zero-stock rows % | Negative stock rows | Negative value rows | Total stock qty |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2022 | 440,231 | 12 | 61,129 | 38,444 | 63.8% | 2.1% | 34.1% | 29.4% | 0 | 32,745 | 39,244,070.9 |
| 2023 | 440,622 | 12 | 62,779 | 39,011 | 63.7% | 2.2% | 34.1% | 29.9% | 0 | 32,769 | 40,127,894.5 |
| 2024 | 459,660 | 12 | 65,208 | 41,855 | 64.3% | 2.2% | 33.5% | 28.7% | 0 | 32,861 | 55,035,153.0 |
| 2025 | 481,146 | 12 | 65,196 | 39,190 | 62.5% | 2.0% | 35.5% | 26.5% | 0 | 32,907 | 55,561,497.7 |

## Target-Window Supplier Stock Context

Because Phase 8B invalidated cached regime labels, this table uses the fast forecastable proxy until the next model rebuild regenerates official labels. `Observed` means an exact SKU mapping exists for the previous completed supplier stock month; `Positive` means that mapped supplier stock quantity is greater than zero.

| Target start | Previous stock month | Population source | SKUs | Observed supplier stock | Observed coverage | Positive supplier stock | Positive coverage |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2024-04-29 | 2024-03-01 | fast_forecastable_proxy | 4,603 | 3,017 | 65.5% | 2,673 | 58.1% |
| 2024-05-27 | 2024-04-01 | fast_forecastable_proxy | 4,725 | 3,114 | 65.9% | 2,768 | 58.6% |
| 2024-07-01 | 2024-06-01 | fast_forecastable_proxy | 4,829 | 3,073 | 63.6% | 2,814 | 58.3% |
| 2024-07-29 | 2024-06-01 | fast_forecastable_proxy | 4,921 | 3,214 | 65.3% | 2,945 | 59.8% |
| 2024-08-26 | 2024-07-01 | fast_forecastable_proxy | 5,036 | 3,380 | 67.1% | 3,109 | 61.7% |
| 2024-09-23 | 2024-08-01 | fast_forecastable_proxy | 5,160 | 3,542 | 68.6% | 3,188 | 61.8% |
| 2024-10-28 | 2024-09-01 | fast_forecastable_proxy | 5,233 | 3,618 | 69.1% | 3,248 | 62.1% |
| 2024-11-25 | 2024-10-01 | fast_forecastable_proxy | 5,365 | 3,794 | 70.7% | 3,378 | 63.0% |
| 2024-12-30 | 2024-11-01 | fast_forecastable_proxy | 5,371 | 3,808 | 70.9% | 3,333 | 62.1% |
| 2025-01-27 | 2024-12-01 | fast_forecastable_proxy | 5,449 | 3,764 | 69.1% | 3,343 | 61.4% |
| 2025-02-24 | 2025-01-01 | fast_forecastable_proxy | 5,459 | 3,722 | 68.2% | 3,276 | 60.0% |
| 2025-03-24 | 2025-02-01 | fast_forecastable_proxy | 5,469 | 3,750 | 68.6% | 3,319 | 60.7% |

## Ambiguous Mapping Examples

| Supplier product name | Candidate SKU count | Candidate SKUs preview |
| --- | --- | --- |
| Dulap | 69 | ["BRASOVL403", "CAIANUMIC17", "HARGHITA13", "HARGHITA14", "HUSI42", "HUSI43", "HUSI44", "H |
| Catedra | 41 | ["BUNTESTI04", "CAIANUMIC10", "CAIANUMIC15", "CAIANUMIC2", "CEAHLAU115", "GRADINI12", "HAR |
| Cuier | 34 | ["BUNTESTI08", "CAIANUMIC18", "CAIANUMIC7", "GRADINI112", "GRADINI15", "NICSENI18", "ORAST |
| Dulap pentru depozitarea materialelor didactice | 33 | ["AI05", "BEREZENIL26", "BEREZENIL36", "GRADINI111", "GRADINI14", "LUGOJL19", "LUGOJL29",  |
| BIBLIOTECA | 30 | ["BRASOVL709", "HUSI05", "HUSI06", "HUSI07", "HUSI08", "HUSI09", "QSMBANE0002", "SCL1536", |
| Bucatarie Giorgia | 29 | ["LAN08CTA2024", "LAN101MIL24", "LAN103MIL23", "LAN1047MIL", "LAN10585BV", "LAN108MIL22",  |
| Scaun profesor | 28 | ["AI10", "BRASOVL801", "BRASOVL802", "BRASOVL903", "CAIANUMIC11", "CAIANUMIC16", "CAIANUMI |
| Material textil VELVET 280cm diverse culori | 26 | ["SA22001", "SA22002", "SA22004", "SA22005", "SA22006", "SA22007", "SA22009", "SA22010", " |

## Historical Safety

- Supplier files are treated as historical monthly supplier stock.
- Phase 8E must only use stock months before the target window.
- Exact unique mappings are feature-safe for the first model pass.
- Ambiguous and unmapped rows are stored for review and coverage reporting, but excluded from official historical features until resolved.

## Accuracy Report

Accuracy not re-run. Official baseline remains `sk_blend_post_bf_safe`: hit +/-20 = 24.1%, hit +/-30 = 35.3%, WMAPE = 56.1%, phantom rate = 48.1%.
