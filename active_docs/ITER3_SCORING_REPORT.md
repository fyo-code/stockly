# Iter 3 Scoring Report — Mar–Apr 2025

_Generated 2026-04-25. Predictions: `iter3_predictions_latest.csv`. Actuals: `sales_2025_Mar_Apr_chronological.csv`._

## Population

- Iter 3 predicted SKUs: **6,358** (same A-tier set as Iter 2)
- SKUs that appeared in Mar–Apr 2025 actuals (any sales): **1,803** (28.4% of predicted)
- SKUs with non-zero actual_4w (scoring set): **1,103**
- Phantom (predicted >0, actual ==0): **655** SKUs, sum predicted = **2,230** units

## Headline (4w horizon)

| Metric | Iter 3 Engine | Naive baseline | Iter 2 (reference) |
|---|---:|---:|---:|
| WMAPE | **84.9%** | 124.4% | 121.1% |
| Hit rate ±20% | **21.4%** | 16.8% | 14.1% |
| Hit rate ±30% | **25.5%** | 18.6% | 20.5% |
| Bias | **+57.3%** | +61.7% | +84.4% |
| MAE (units) | 2.47 | 3.62 | — |

**Engine beats naive on 58.9% of SKUs** (ties: 7.6%, naive wins: 33.5%).

**Engine WMAPE is 39.5 pp BETTER than naive** (31.7% relative improvement).

## Per-method scoreboard (4w, on rows where method produced a number)

| Method | n SKUs | WMAPE | Hit ±20% | Bias | Win rate vs naive | Mean pred |
|---|---:|---:|---:|---:|---:|---:|
| **Ensemble (median)** | 1,103 | **84.9%** | **21.4%** | +57.3% | **58.9%** | 3.43 |
| _Naive baseline_ | 1,103 | _124.4%_ | _16.8%_ | +61.7% | _—_ | 4.52 |
| ets | 1,103 | 191.7% | 16.0% | +185.9% | 47.6% | 7.05 |
| anomaly_adjusted | 749 | 114.4% | 1.3% | -48.0% | 32.4% | 1.27 |
| multi_scale_lag | 1,103 | 135.2% | 16.1% | +150.9% | 51.0% | 5.96 |
| calendar_events | 1,103 | 81.1% | 24.0% | +37.4% | 65.5% | 3.06 |
| category_relative | 1,103 | 92.3% | 9.2% | +26.1% | 37.9% | 3.17 |
| naive_seasonal | 1,103 | 88.1% | 23.0% | +37.1% | 59.5% | 3.24 |
| crostons | 354 | 61.6% | 36.4% | -10.8% | 57.3% | 1.50 |

## Per-category breakdown (4w, categories with ≥5 SKUs in scoring set)

| Category | SKUs | Σ actual | Engine WMAPE | Naive WMAPE | Engine wins % | Engine hit ±20% |
|---|---:|---:|---:|---:|---:|---:|
| ACCESORII | 209 | 1,166 | 77% | 153% | 66% | 22% |
| MOBILIER DE CASA | 321 | 745 | 77% | 100% | 56% | 21% |
| #null | 200 | 404 | 109% | 138% | 57% | 18% |
| MOBILIER DE CASA - MIC MOBILIER | 75 | 330 | 70% | 79% | 53% | 19% |
| SALTELE SI SOMIERE | 57 | 171 | 136% | 133% | 60% | 14% |
| CANAPELE SI FOTOLII | 96 | 150 | 73% | 87% | 56% | 22% |
| MOBILIER CASA | 38 | 66 | 70% | 102% | 63% | 32% |
| PATURI TAPITATE | 30 | 48 | 73% | 104% | 70% | 37% |
| MOBILIER OFFICE | 24 | 40 | 230% | 158% | 33% | 21% |
| MOBILIER TERASA SI GRADINA, INDOOR, ACCESORII | 13 | 34 | 93% | 121% | 54% | 8% |
| MOBILIER BAIE SI SANITARE | 24 | 27 | 44% | 93% | 67% | 42% |
| MOBILIER TERASA SI GRADINA | 7 | 17 | 102% | 141% | 71% | 14% |

## Top 20 most-accurate SKUs (engine within X% of actual, actual ≥3 units)

| SKU | Category | Actual | Engine | %err | Naive | Naive %err |
|---|---|---:|---:|---:|---:|---:|
| DSDBL0021CR | ACCESORII | 4 | 4.0 | 0.0% | 1.0 | 75.0% |
| KBSV01 | ACCESORII | 24 | 24.0 | 0.0% | 24.0 | 0.0% |
| MESEPVROGR080 | #null | 3 | 3.0 | 0.0% | 0.0 | 100.0% |
| SMS15AB | MOBILIER DE CASA | 3 | 3.0 | 0.0% | 4.0 | 33.3% |
| SRN01 | MOBILIER DE CASA | 3 | 3.0 | 0.0% | 5.0 | 66.7% |
| SRN03 | MOBILIER DE CASA | 3 | 3.0 | 0.0% | 4.0 | 33.3% |
| PRX827WH | MOBILIER DE CASA - MIC MOBILIER | 14 | 13.9 | 0.7% | 0.0 | 100.0% |
| JEN06 | MOBILIER DE CASA | 7 | 6.9 | 1.4% | 0.0 | 100.0% |
| MCA136 | MOBILIER DE CASA - MIC MOBILIER | 8 | 8.2 | 2.5% | 2.0 | 75.0% |
| 46COMO160200PT | SALTELE SI SOMIERE | 3 | 3.1 | 3.3% | 6.0 | 100.0% |
| ZFF01 | MOBILIER DE CASA | 3 | 3.1 | 3.3% | 3.0 | 0.0% |
| CEF06 | MOBILIER DE CASA - MIC MOBILIER | 12 | 12.5 | 4.2% | 2.0 | 83.3% |
| DMI043 | CANAPELE SI FOTOLII | 6 | 5.7 | 5.0% | 8.0 | 33.3% |
| QCIP3333F019 | ACCESORII | 6 | 6.3 | 5.0% | 28.0 | 366.7% |
| SMS619AG | MOBILIER DE CASA | 6 | 5.7 | 5.0% | 0.0 | 100.0% |
| EHFD7222 | MOBILIER DE CASA | 4 | 4.2 | 5.0% | 0.0 | 100.0% |
| GFF15 | MOBILIER DE CASA - MIC MOBILIER | 4 | 3.8 | 5.0% | 0.0 | 100.0% |
| PRX827G | MOBILIER DE CASA - MIC MOBILIER | 8 | 8.4 | 5.0% | 4.0 | 50.0% |
| U26800906MC | CANAPELE SI FOTOLII | 3 | 3.2 | 6.7% | 1.0 | 66.7% |
| WNN0628WT | MOBILIER DE CASA | 3 | 2.8 | 6.7% | 0.0 | 100.0% |

## Top 20 worst absolute errors (largest |engine − actual| in units)

| SKU | Category | Actual | Engine | abs err | Naive | Naive |err| |
|---|---|---:|---:|---:|---:|---:|
| DILIRMA02 | ACCESORII | 18 | 125.1 | 107.5 | 10.0 | 7.6 |
| MFSET4BUCSOMBASICH25CM | SALTELE SI SOMIERE | 9 | 89.1 | 80.1 | 63.0 | 54.0 |
| ESLLEDNL22G9NF | ACCESORII | 10 | 84.9 | 74.9 | 78.0 | 68.0 |
| JRL674002STOC | ACCESORII | 86 | 42.4 | 43.5 | 110.0 | 24.1 |
| HGD7000GY | #null | 3 | 42.5 | 39.5 | 2.0 | 1.0 |
| ITDREAMYMP | #null | 4 | 41.2 | 37.2 | 54.0 | 50.0 |
| QCIP309006A | ACCESORII | 40 | 3.2 | 36.8 | 148.0 | 108.0 |
| DILIRMA01 | ACCESORII | 45 | 9.0 | 36.2 | 0.0 | 45.2 |
| MFSOMIERABASIC090190 | SALTELE SI SOMIERE | 6 | 39.3 | 33.3 | 50.0 | 44.0 |
| MGDW776BLK | #null | 2 | 31.2 | 29.2 | 0.0 | 2.0 |
| WINVOILEWHITE | ACCESORII | 41 | 13.6 | 27.4 | 10.0 | 31.0 |
| QCIP313002 | ACCESORII | 40 | 15.8 | 24.2 | 73.0 | 33.0 |
| LSI07 | MOBILIER DE CASA - MIC MOBILIER | 6 | 30.1 | 24.1 | 0.0 | 6.0 |
| QCIP33-03E019 | ACCESORII | 24 | 2.0 | 22.0 | 45.0 | 21.0 |
| VAYOTELLO4 | ACCESORII | 37 | 16.2 | 20.4 | 158.0 | 121.4 |
| MZCGZ06120 | #null | 26 | 5.7 | 20.3 | 64.0 | 38.0 |
| ULK018 | MOBILIER DE CASA - MIC MOBILIER | 24 | 4.2 | 19.8 | 20.0 | 4.0 |
| QCIP3004 | ACCESORII | 7 | 26.7 | 19.7 | 42.0 | 35.0 |
| QCH2-02P04N | ACCESORII | 11 | 30.4 | 19.4 | 53.0 | 42.0 |
| QCIP309002A | ACCESORII | 22 | 2.8 | 19.2 | 28.0 | 6.0 |
