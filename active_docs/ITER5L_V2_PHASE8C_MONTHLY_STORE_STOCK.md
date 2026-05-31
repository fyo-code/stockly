# Iteration 5L — V2 Phase 8C Monthly Store Stock Ingestion

Generated: 2026-05-21 09:14

## Phase Checkpoint

Phase completed: Phase 8C — complete monthly store stock coverage for Constanta, Iasi, and Oradea.

What changed: the three missing wide monthly store-stock files from `new_stock_data_20may/` were imported into `stock_monthly_store_v2` as historical end-of-month stock. The runner deletes any previous rows for the same source files before import, so reruns do not double-count stock.

Accuracy rerun: no. This phase only adds historical stock context. Accuracy will be re-measured after Phase 8E joins store/supplier availability into the feature matrix.

| Baseline metric | Current official control before Phase 8C |
| --- | --- |
| Best model | sk_blend_post_bf_safe |
| Hit +/-20 | 24.1% |
| Hit +/-30 | 35.3% |
| WMAPE | 56.1% |
| Phantom rate | 48.1% |

## Import Result

| File | Rows | Records inserted | Records skipped | Stores | SKUs | Month range | Prior rows removed |
| --- | --- | --- | --- | --- | --- | --- | --- |
| const_magazin_stock.csv | 4,752 | 67,639 | 160,457 | 1 | 4,752 | 2022-01-01..2025-12-01 | 0 |
| iasi_magazin_stock.csv | 4,705 | 52,890 | 172,950 | 1 | 4,705 | 2022-01-01..2025-12-01 | 0 |
| oradea_magazin_stock.csv | 3,048 | 36,942 | 109,362 | 1 | 3,048 | 2022-01-01..2025-12-01 | 0 |

## Recorded Source Files

| File | Kind | Feature scope | Rows | Records | Skipped | Stores | SKUs | Month range |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| const_magazin_stock.csv | monthly_store_stock | historical_backtest | 4,752 | 67,639 | 160,457 | 1 | 4,752 | 2022-01-01..2025-12-01 |
| iasi_magazin_stock.csv | monthly_store_stock | historical_backtest | 4,705 | 52,890 | 172,950 | 1 | 4,705 | 2022-01-01..2025-12-01 |
| oradea_magazin_stock.csv | monthly_store_stock | historical_backtest | 3,048 | 36,942 | 109,362 | 1 | 3,048 | 2022-01-01..2025-12-01 |

## Store Coverage Delta

| Store | Records before | Records after | Record delta | SKUs before | SKUs after | SKU delta | Months | Month range | Zero records | Negative records |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| constanta | 0 | 67,639 | 67,639 | 0 | 4,752 | 4,752 | 48 | 2022-01-01..2025-12-01 | 14,107 | 0 |
| iasi | 0 | 52,890 | 52,890 | 0 | 4,705 | 4,705 | 48 | 2022-01-01..2025-12-01 | 8,557 | 0 |
| oradea | 0 | 36,942 | 36,942 | 0 | 3,048 | 3,048 | 48 | 2022-01-01..2025-12-01 | 4,155 | 0 |

## Total Monthly Store Stock Delta

| Table | Records before | Records after | Record delta | SKUs before | SKUs after | SKU delta | Stores after | Month range after |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| monthly_store_stock | 549,677 | 707,148 | 157,471 | 12,636 | 13,351 | 715 | 11 | 2022-01-01..2025-12-01 |

## Source SKU Overlap With Sales

| File | Stock SKUs | Overlap with sales SKUs | Overlap % of stock SKUs |
| --- | --- | --- | --- |
| const_magazin_stock.csv | 4,752 | 4,238 | 89.2% |
| iasi_magazin_stock.csv | 4,705 | 4,464 | 94.9% |
| oradea_magazin_stock.csv | 3,048 | 2,939 | 96.4% |

## Target-Window Stock Context Coverage

Because Phase 8B invalidated cached regime labels, this table uses the fast forecastable proxy until the next model rebuild regenerates official labels.

| Target start | Previous stock month | Population source | SKUs | With stock context | Coverage |
| --- | --- | --- | --- | --- | --- |
| 2024-04-29 | 2024-03-01 | fast_forecastable_proxy | 4,603 | 143 | 3.1% |
| 2024-05-27 | 2024-04-01 | fast_forecastable_proxy | 4,725 | 136 | 2.9% |
| 2024-07-01 | 2024-06-01 | fast_forecastable_proxy | 4,829 | 146 | 3.0% |
| 2024-07-29 | 2024-06-01 | fast_forecastable_proxy | 4,921 | 155 | 3.1% |
| 2024-08-26 | 2024-07-01 | fast_forecastable_proxy | 5,036 | 156 | 3.1% |
| 2024-09-23 | 2024-08-01 | fast_forecastable_proxy | 5,160 | 156 | 3.0% |
| 2024-10-28 | 2024-09-01 | fast_forecastable_proxy | 5,233 | 154 | 2.9% |
| 2024-11-25 | 2024-10-01 | fast_forecastable_proxy | 5,365 | 165 | 3.1% |
| 2024-12-30 | 2024-11-01 | fast_forecastable_proxy | 5,371 | 167 | 3.1% |
| 2025-01-27 | 2024-12-01 | fast_forecastable_proxy | 5,449 | 157 | 2.9% |
| 2025-02-24 | 2025-01-01 | fast_forecastable_proxy | 5,459 | 172 | 3.2% |
| 2025-03-24 | 2025-02-01 | fast_forecastable_proxy | 5,469 | 175 | 3.2% |

## Historical Safety

- These files are monthly store stock and are marked `historical_backtest`.
- They are treated as end-of-month stock snapshots.
- Feature usage must still lag the target window; the model should only use the latest completed stock month before the forecast start.
- No supplier-stock or rotation-snapshot files were ingested in this phase.

## Accuracy Report

Accuracy not re-run. Official baseline remains `sk_blend_post_bf_safe`: hit +/-20 = 24.1%, hit +/-30 = 35.3%, WMAPE = 56.1%, phantom rate = 48.1%.
