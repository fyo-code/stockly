# Iteration 5K — V2 Phase 8B Baneasa 2022 Sales Ingestion

Generated: 2026-05-20 20:05

## Phase Checkpoint

Phase completed: Phase 8B — Baneasa 2022 sales ingestion

What changed: `baneasa_sales22.csv` was imported into v2 raw sales tables, weekly store demand and weekly chain demand were rebuilt, and stale forecast score/regime tables were invalidated.

Accuracy rerun: no. This phase changes the sales foundation, so old persisted score rows are stale. The model will be rerun after stock/supplier availability features are added.

| Baseline metric | Current control before Phase 8B |
| --- | --- |
| Best model | sk_blend_post_bf_safe |
| Hit +/-20 | 24.1% |
| Hit +/-30 | 35.3% |
| WMAPE | 56.1% |
| Phantom rate | 48.1% |

## Source Import Result

| File | Seen | Inserted | Duplicate | Filtered | DATA fallback | Fallback % | Missing date | Missing SKU | Missing store | Date range |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baneasa_sales22.csv | 233,245 | 233,052 | 193 | 0 | 115,891 | 49.7% | 0 | 0 | 233,245 | 2018-10-24..2022-12-31 |

## Baneasa Store-Year Coverage

| Year | Rows | SKUs | Net units | Net revenue | Fallback rows | Fallback % | Return rows |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2018 | 2 | 2 | -2.0 | -1,044.2 | 0 | 0.0% | 2 |
| 2019 | 3 | 3 | -1.0 | 2,607.9 | 0 | 0.0% | 2 |
| 2020 | 26 | 26 | 3.0 | -3,306.0 | 0 | 0.0% | 13 |
| 2021 | 3,441 | 2,505 | 6,935.5 | 5,397,976.6 | 0 | 0.0% | 183 |
| 2022 | 229,310 | 32,914 | 436,183.0 | 148,458,427.9 | 115,883 | 50.5% | 4,923 |
| 2023 | 3,085 | 2,294 | 5,884.2 | 6,689,399.2 | 0 | 0.0% | 130 |
| 2024 | 104,303 | 28,692 | 217,223.0 | 128,416,223.6 | 0 | 0.0% | 114 |
| 2025 | 85,913 | 26,584 | 179,747.4 | 107,069,820.0 | 0 | 0.0% | 2 |

## Source Conservation Check

| Layer | Rows | SKUs | Gross units | Returned units | Net units | Gross revenue | Returned revenue | Net revenue | Non-product rows |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| raw source rows | 233,052 | 33,827 | 451,257.0 | 8,398.6 | 442,858.4 | 160,158,355.7 | 6,501,015.5 | 153,657,340.2 | 298 |
| Baneasa weekly 2022 window | - | - | 444,638.3 | 7,917.4 | 436,720.9 | 154,901,764.5 | 6,095,238.7 | 148,806,525.7 | - |

## Decision

Phase 8B is usable. Baneasa 2022 is now part of the v2 sales foundation, with high but expected invoice-date fallback usage. Proceed next to Phase 8C monthly store stock ingestion.

## Notes

- The file does not include `MAGAZIN`; the importer now infers Baneasa from the filename for single-store exports.
- Old forecast score/regime tables were cleared because the demand foundation changed.
- No model accuracy improvement is claimed until the official rerun after Phase 8E/8G.
