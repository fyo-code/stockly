# Iteration 5A — Forecast V2 Import Validation

Generated: 2026-05-11

## Import Result

Imported all CSVs from `9 stores full info ( pipera not full)` into isolated v2 tables under the existing SQLite database.

New code location:

- `backend/forecast_engine_v2/ingestion.py`
- `backend/forecast_engine_v2/__init__.py`

The legacy `backend/forecast_engine/` package and legacy `sales` / `weekly_demand` tables were not overwritten.

## Row Counts

| Layer | Rows | Date range | Distinct SKUs | Stores |
|---|---:|---|---:|---:|
| `raw_sales_transactions_v2` | 1,405,858 | 2018-01-03 -> 2025-12-31 | 100,623 | 10 |
| `weekly_store_demand_v2` | 1,123,300 | 2018-01-01 -> 2025-12-29 | 100,509 | 10 |
| `weekly_chain_demand_v2` | 876,325 | 2018-01-01 -> 2025-12-29 | 100,509 | - |

Source files:

- Files discovered: 32
- Rows scanned: 2,800,288
- Rows inserted: 1,405,858
- Duplicate transaction lines skipped: 3
- Rows filtered before raw import due missing required transaction fields: 1,394,427

## Conservation Checks

The v2 weekly tables conserve product-row net units and net revenue exactly.

| Check | Raw/source | Aggregated |
|---|---:|---:|
| Raw product rows -> weekly store net units | 2,609,477.56 | 2,609,477.56 |
| Weekly store -> weekly chain net units | 2,609,477.56 | 2,609,477.56 |
| Raw product rows -> weekly store net revenue | 1,634,120,498.75 | 1,634,120,498.75 |
| Weekly store -> weekly chain net revenue | 1,634,120,498.75 | 1,634,120,498.75 |

## Store Coverage

| Store | Type | Rows | Date range | Distinct SKUs | Net units | Net revenue |
|---|---|---:|---|---:|---:|---:|
| baneasa | hyperstore | 193,329 | 2019-02-10 -> 2025-12-31 | 41,876 | 402,871.6 | 242,251,473.00 |
| brasov | hyperstore | 127,854 | 2020-05-17 -> 2025-12-31 | 34,358 | 194,972.9 | 127,638,524.41 |
| constanta | hyperstore | 149,787 | 2021-01-30 -> 2025-12-31 | 35,373 | 230,040.7 | 177,644,279.08 |
| iasi | hybrid | 146,764 | 2020-01-20 -> 2025-12-31 | 38,198 | 247,694.8 | 166,204,759.10 |
| oradea | smaller_store | 72,603 | 2018-01-03 -> 2025-12-31 | 25,858 | 113,689.3 | 70,131,019.64 |
| pantelemon | hyperstore | 146,207 | 2020-02-17 -> 2025-12-31 | 34,467 | 210,687.3 | 142,654,706.31 |
| pipera | hyperstore | 287,429 | 2020-06-04 -> 2025-12-31 | 57,734 | 872,693.9 | 464,390,948.82 |
| ploiesti | smaller_store | 41,277 | 2021-12-03 -> 2025-12-30 | 14,999 | 76,225.8 | 49,283,640.48 |
| sibiu | hyperstore | 96,429 | 2018-09-30 -> 2025-12-31 | 29,158 | 145,308.2 | 92,410,212.96 |
| timisoara | smaller_store | 69,847 | 2021-02-15 -> 2025-12-31 | 22,763 | 115,293.0 | 101,510,934.95 |

## Feature Availability

| Feature | Rows |
|---|---:|
| Parsed product dimensions from `DENUMIRE ARTICOL` | 199,352 |
| Black Friday timing flag from `CAMPANIE BF` | 66,138 |
| Non-zero discount depth | 747,758 |
| `RAION = ONLINE` | 465,271 |
| `RAION = OUTLET` | 20,582 |

## Product vs Non-Product Rows

| `is_non_product` | Rows | Net units | Net revenue |
|---:|---:|---:|---:|
| 0 | 1,331,526 | 2,609,477.6 | 1,634,120,498.75 |
| 1 | 74,332 | 263,377.8 | -3,642,544.21 |

Weekly demand tables use `is_non_product = 0`.

## Category Normalization Warning

Update 2026-05-11: this warning was addressed by the v2 hierarchy normalizer and signal audit. See `active_docs/ITER5A_V2_HIERARCHY_SIGNAL_AUDIT.md`. Unknown category revenue is now 1,143,859.33 lei, about 0.07% of product revenue.

The legacy category normalizer leaves a large `NECUNOSCUT` bucket on the richer v2 data:

| Category | Distinct SKUs | Net revenue | Net units |
|---|---:|---:|---:|
| MOBILIER DE CASA | 14,914 | 544,962,528.60 | 628,327.0 |
| CANAPELE SI FOTOLII | 7,518 | 245,295,218.86 | 77,934.0 |
| ACCESORII | 49,693 | 223,099,630.27 | 1,201,572.7 |
| NECUNOSCUT | 26,308 | 182,456,072.27 | 364,568.5 |
| MOBILIER TERASA SI GRADINA | 3,080 | 122,841,019.05 | 98,423.5 |
| SALTELE SI SOMIERE | 2,022 | 90,857,169.13 | 56,544.0 |
| MOBILIER BUCATARII | 7,493 | 70,693,132.63 | 22,403.5 |
| MOBILIER OFFICE | 4,484 | 70,680,249.08 | 91,545.9 |
| PATURI TAPITATE | 2,892 | 46,836,547.30 | 21,024.0 |
| MOBILIER BAIE SI SANITARE | 2,135 | 27,795,853.20 | 36,869.0 |
| ALTELE | 950 | 8,603,078.36 | 10,265.3 |

This does not block chain-demand creation, but it should be fixed before model training because category/class hierarchy is a major feature group.

## Next Required Step

Build the v2 hierarchy/category audit and normalization pass:

1. Inspect raw `CATEGORIE`, `CLASA`, `SUBCLASA`, `GRUPA`, and `RAION` values that fall into `NECUNOSCUT`.
2. Add v2-specific hierarchy normalization without modifying the frozen legacy normalizer.
3. Rebuild v2 import/weekly tables after improving category coverage.
4. Then build regime labels and the v2 scorecard.
