# Iteration 5Q - V2 Phase 8G-B Stock Coverage Audit

Generated: 2026-05-22 11:20

## Phase Checkpoint

Phase completed: Phase 8G-B - high-revenue store/supplier stock coverage audit.

What changed: no model behavior changed. This report audits whether high-revenue V2 rows have usable historical store and supplier stock context.

Target windows audited: 2024-08-26, 2024-09-23, 2024-10-28, 2024-11-25, 2024-12-30, 2025-01-27, 2025-02-24, 2025-03-24.

## Executive Read

| Top-1000 metric | Value |
| --- | --- |
| Rows | 5,346 |
| Unique SKUs | 945 |
| Store prev-month observed | 0.4% |
| Store any historical observed | 0.4% |
| Supplier prev-month observed | 70.6% |
| Combined prev-month observed | 70.6% |
| Rows with store sales history but no store prev-month stock | 5,324 |

## Coverage By Revenue Scope

| Scope | Rows | Unique SKUs | Actual target revenue | Store prev obs | Store prev obs % | Store prev positive | Store any obs | Store any obs % | Supplier prev obs | Supplier prev obs % | Supplier prev positive | Combined prev obs | Combined prev obs % | Sold stores/no store prev |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Top 100 | 475 | 96 | 19,774,645 | 0 | 0.0% | 0 | 0 | 0.0% | 340 | 71.6% | 287 | 340 | 71.6% | 475 |
| Top 500 | 2,866 | 513 | 59,034,164 | 0 | 0.0% | 0 | 0 | 0.0% | 2,016 | 70.3% | 1,738 | 2,016 | 70.3% | 2,866 |
| Top 1000 | 5,346 | 945 | 79,136,333 | 22 | 0.4% | 22 | 22 | 0.4% | 3,774 | 70.6% | 3,287 | 3,776 | 70.6% | 5,324 |
| Top 5000 | 15,762 | 2,661 | 116,777,217 | 263 | 1.7% | 259 | 263 | 1.7% | 11,208 | 71.1% | 10,052 | 11,219 | 71.2% | 15,499 |
| Full headline | 21,045 | 3,543 | 123,302,226 | 514 | 2.4% | 502 | 522 | 2.5% | 15,026 | 71.4% | 13,492 | 15,083 | 71.7% | 20,531 |

## Top-1000 Coverage By Target Window

| Target start | Rows | Unique SKUs | Store prev obs % | Store any obs % | Supplier prev obs % | Combined prev obs % | Actual target revenue |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2024-08-26 | 705 | 705 | 0.6% | 0.6% | 66.4% | 66.4% | 10,378,783 |
| 2024-09-23 | 700 | 700 | 0.4% | 0.4% | 67.9% | 67.9% | 10,174,878 |
| 2024-10-28 | 688 | 688 | 0.3% | 0.3% | 70.1% | 70.1% | 20,478,496 |
| 2024-11-25 | 684 | 684 | 0.6% | 0.6% | 72.2% | 72.2% | 5,426,480 |
| 2024-12-30 | 661 | 661 | 0.5% | 0.5% | 72.6% | 72.6% | 7,688,500 |
| 2025-01-27 | 646 | 646 | 0.5% | 0.5% | 71.7% | 71.8% | 9,089,493 |
| 2025-02-24 | 641 | 641 | 0.3% | 0.3% | 70.7% | 70.8% | 8,005,057 |
| 2025-03-24 | 621 | 621 | 0.2% | 0.2% | 73.9% | 73.9% | 7,894,646 |

## Top High-Revenue SKUs Missing Prev-Month Store Stock

| SKU | Category | Family | Windows | Best rank | Actual target revenue | Actual units | Store any windows | Supplier obs windows | Supplier positive windows | Max selling stores 52w | Max store units 52w |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| MFNEWYORK180200 | SALTELE SI SOMIERE | MFSERTA05 SOFT MEX CONFORT - SERTA NEW YORK | 8 | 1 | 1,072,158 | 192.0 | 0 | 8 | 7 | 11 | 282.0 |
| 46COMFORTPLUS160200 | SALTELE SI SOMIERE | SOFT MEX CONFORT - COMFORT PLUS 2023 | 8 | 5 | 869,211 | 369.0 | 0 | 8 | 5 | 11 | 543.0 |
| MFNEWYORK160200 | SALTELE SI SOMIERE | MFSERTA05 SOFT MEX CONFORT - SERTA NEW YORK | 8 | 2 | 750,159 | 152.0 | 0 | 8 | 6 | 11 | 274.0 |
| 46COMFORT160200 | SALTELE SI SOMIERE | SOFT MEX CONFORT - COMFORT 2023 | 8 | 3 | 708,118 | 361.0 | 0 | 8 | 5 | 11 | 649.0 |
| EVR6100 | MOBILIER TERASA SI GRADINA | MM21019 LETRIGHT - MOBILIER GRADINA | 8 | 8 | 688,860 | 144.0 | 0 | 8 | 6 | 11 | 254.0 |
| DMI02 | CANAPELE SI FOTOLII | DM ITALIAN SOFA - TOKYO | 8 | 13 | 559,349 | 155.0 | 0 | 8 | 6 | 11 | 218.0 |
| MFCHICAGO160200 | SALTELE SI SOMIERE | MFSERTA01 SOFT MEX CONFORT - SERTA CHICAGO | 8 | 15 | 520,260 | 178.0 | 0 | 0 | 0 | 11 | 265.0 |
| DMI01 | CANAPELE SI FOTOLII | DM ITALIAN SOFA - TOKYO | 8 | 11 | 518,835 | 146.0 | 0 | 8 | 7 | 11 | 238.0 |
| CTAC0888904 | CANAPELE SI FOTOLII | COTTA - SHANE | 8 | 10 | 515,416 | 94.0 | 0 | 8 | 6 | 11 | 161.0 |
| FPD034 | PATURI TAPITATE | FPD - DREAMER | 8 | 33 | 489,249 | 179.0 | 0 | 8 | 8 | 11 | 252.0 |
| SMS664AB | MOBILIER DE CASA | MOBILIER DE CASA - DORMITOARE | 7 | 43 | 443,081 | 46.0 | 0 | 0 | 0 | 11 | 67.0 |
| ZY86 | CANAPELE SI FOTOLII | ZOY - JAMISON | 8 | 17 | 422,519 | 88.0 | 0 | 7 | 6 | 11 | 158.0 |
| CTAC0888902 | CANAPELE SI FOTOLII | COTTA - SHANE | 8 | 24 | 411,034 | 74.0 | 0 | 0 | 0 | 11 | 101.0 |
| 46COMFORT160200EUROTOP | SALTELE SI SOMIERE | SOFT MEX CONFORT - COMFORT EUROTOP 2023 | 8 | 36 | 387,632 | 176.0 | 0 | 8 | 4 | 11 | 240.0 |
| SMS761AB | MOBILIER DE CASA | LINEA-CLASIC PROD MEX - JAZZ | 8 | 28 | 382,491 | 125.0 | 0 | 8 | 8 | 11 | 176.0 |
| MFCHICAGO180200 | SALTELE SI SOMIERE | MFSERTA01 SOFT MEX CONFORT - SERTA CHICAGO | 8 | 21 | 380,917 | 114.0 | 0 | 8 | 8 | 11 | 181.0 |
| CTAMM32101G | CANAPELE SI FOTOLII | COTTA - MONZA | 8 | 38 | 367,429 | 70.0 | 0 | 8 | 7 | 10 | 87.0 |
| SMS635AB | MOBILIER DE CASA | LINEA-CLASIC PROD MEX - JAZZ | 8 | 55 | 366,680 | 60.0 | 0 | 8 | 8 | 11 | 80.0 |
| 46MAVI160200HARD | SALTELE SI SOMIERE | SOFT MEX CONFORT - OUTLET | 8 | 27 | 355,177 | 258.0 | 0 | 8 | 4 | 11 | 410.0 |
| SMS769CDAB | MOBILIER DE CASA | LINEA-CLASIC PROD MEX - JAZZ | 8 | 30 | 344,840 | 87.0 | 0 | 0 | 0 | 11 | 138.0 |
| DMI043 | CANAPELE SI FOTOLII | DM ITALIAN SOFA - FAIREN | 8 | 58 | 343,842 | 115.0 | 0 | 8 | 8 | 11 | 154.0 |
| RING01CAR92 | MOBILIER DE CASA | 02523 MURES MEX - RING | 8 | 22 | 340,612 | 134.0 | 0 | 8 | 8 | 11 | 230.0 |
| FPD026 | PATURI TAPITATE | FPD - SHEFFIELD | 8 | 61 | 335,761 | 150.0 | 0 | 8 | 7 | 11 | 209.0 |
| FPD033 | PATURI TAPITATE | FPD - MURRAY | 8 | 78 | 330,549 | 129.0 | 0 | 8 | 7 | 11 | 162.0 |
| SMS688AB | MOBILIER DE CASA | LINEA-CLASIC PROD MEX - JAZZ | 7 | 57 | 308,965 | 83.0 | 0 | 0 | 0 | 11 | 133.0 |
| SMS619AB | MOBILIER DE CASA | LINEA-CLASIC PROD MEX - JAZZ | 7 | 74 | 302,628 | 198.0 | 0 | 0 | 0 | 11 | 289.0 |
| KARP078 | CANAPELE SI FOTOLII | KARPITOS - LINCOLN | 8 | 39 | 300,988 | 80.0 | 0 | 0 | 0 | 10 | 112.0 |
| CTAC08889010 | CANAPELE SI FOTOLII | COTTA - SHANE | 8 | 92 | 290,936 | 52.0 | 0 | 7 | 5 | 10 | 65.0 |
| KUL01 | MOBILIER DE CASA | LINEA MEX - RAUCH KOLN | 8 | 117 | 275,544 | 66.0 | 0 | 8 | 8 | 11 | 85.0 |
| U26800906MC | CANAPELE SI FOTOLII | ITALSOFA - BOLOGNA | 8 | 65 | 272,613 | 65.0 | 0 | 8 | 8 | 11 | 90.0 |

## Stock Source Files

| File | Kind | Scope | Rows seen | Records inserted | Records skipped | Stores | SKUs | First month | Last month |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| brasov 22-25 stoc magazin.csv | monthly_store_stock | historical_backtest | 4,547 | 57,319 | 160,937 | 1 | 4,547 | 2022-01-01 | 2025-12-01 |
| const_magazin_stock.csv | monthly_store_stock | historical_backtest | 4,752 | 67,639 | 160,457 | 1 | 4,752 | 2022-01-01 | 2025-12-01 |
| iasi_magazin_stock.csv | monthly_store_stock | historical_backtest | 4,705 | 52,890 | 172,950 | 1 | 4,705 | 2022-01-01 | 2025-12-01 |
| oradea_magazin_stock.csv | monthly_store_stock | historical_backtest | 3,048 | 36,942 | 109,362 | 1 | 3,048 | 2022-01-01 | 2025-12-01 |
| pipera sibiu stock magazin monthly.csv | monthly_store_stock | historical_backtest | 10,420 | 157,577 | 342,583 | 2 | 7,505 | 2022-01-01 | 2025-12-01 |
| stoc magazin ban ploiesti pante craiova.csv | monthly_store_stock | historical_backtest | 15,804 | 205,771 | 552,821 | 3 | 9,783 | 2022-01-01 | 2025-12-01 |
| stock magazin mil tim.csv | monthly_store_stock | historical_backtest | 7,687 | 129,010 | 239,966 | 2 | 6,551 | 2022-01-01 | 2025-12-01 |
| supplier_stock_22.csv | monthly_supplier_stock | historical_backtest | 440,424 | 440,424 | 0 | 12 | 38,444 | 2022-01-01 | 2022-12-01 |
| supplier_stock_23.csv | monthly_supplier_stock | historical_backtest | 440,773 | 440,773 | 0 | 12 | 39,011 | 2023-01-01 | 2023-12-01 |
| supplier_stock_24.csv | monthly_supplier_stock | historical_backtest | 459,912 | 459,912 | 0 | 12 | 41,855 | 2024-01-01 | 2024-12-01 |
| supplier_stock_25.csv | monthly_supplier_stock | historical_backtest | 481,333 | 481,333 | 0 | 12 | 39,190 | 2025-01-01 | 2025-12-01 |
| viteza rotatie stock constanta.csv | rotation_snapshot | current_snapshot | 52,251 | 52,251 | 0 | 1 | 52,251 | nan | nan |
| viteza rotatie stock militari.csv | rotation_snapshot | current_snapshot | 52,783 | 52,783 | 0 | 1 | 52,783 | nan | nan |
| viteza rotatie stock pipera.csv | rotation_snapshot | current_snapshot | 55,323 | 55,323 | 0 | 1 | 55,323 | nan | nan |
| viteza rotatie stock sibiu.csv | rotation_snapshot | current_snapshot | 50,699 | 50,699 | 0 | 1 | 50,699 | nan | nan |
| baneasa_stoc_history.csv | stock_snapshot | current_snapshot | 44,031 | 44,031 | 0 | 1 | 44,031 | nan | nan |
| brasov stoc snapshots.csv | stock_snapshot | current_snapshot | 71,410 | 71,410 | 0 | 1 | 71,410 | nan | nan |
| pipera stock entrance snapshots.csv | stock_snapshot | current_snapshot | 72,462 | 72,462 | 0 | 1 | 72,462 | nan | nan |
| stoc entrance pante +viteza rotatie.csv | stock_snapshot | current_snapshot | 71,356 | 71,356 | 0 | 1 | 71,356 | nan | nan |
| stoc_brasov.csv | stock_snapshot | current_snapshot | 13,987 | 13,987 | 0 | 1 | 9,325 | nan | nan |
| vechime stoc brasov.csv | stock_snapshot | current_snapshot | 13,596 | 13,596 | 0 | 1 | 9,317 | nan | nan |

## Decision Gate

Do not block route-specific modeling on monthly store stock. For top-1000 revenue rows, store previous-month coverage is too weak, while supplier coverage is strong enough to remain the primary availability signal. Treat store stock as a narrow high-confidence signal and use 8G-B missing-SKU output to investigate mapping/source coverage separately.

## Notes

- Forecast V2 only; no old-engine path is used.
- Coverage uses the same scored target windows as Phase 8G-A by default.
- Store stock coverage means an exact SKU/store/month row exists in `stock_monthly_store_v2` for the previous completed stock month.
- Supplier coverage uses only `exact_unique` supplier product-name-to-SKU mappings.
- Current rotation snapshots remain excluded from historical backtests.
