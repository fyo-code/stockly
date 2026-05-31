# Iteration 5R - Forecast V2 Phase 8G-C Campaign Field Audit

Generated: 2026-05-23 17:49:24

## Verdict

- Phase 8G-C is implemented as forecast-time-safe campaign history features, not target-window campaign leakage.
- CAMPANIE / CAMPANIE BF fields are useful now as historical SKU behavior: recent campaign exposure, BF exposure, campaign unit share, non-BF campaign share, and campaign discount memory.
- Product/program labels are excluded from campaign exposure features and kept as a separate product-program signal.
- Non-BF campaign features exclude rows flagged as BF campaigns, not just rows inside BF timing windows.
- They do not fully solve future promotion uncertainty unless a future campaign calendar/assortment plan is supplied. Target-window campaign bucket remains diagnostic only.
- In the clean Top 1000 regular slice, 70.7% of rows still have campaign history in the previous 13 weeks, so the 32.3% 8G-A win is not a campaign-free problem.

## Feature Coverage By Revenue Scope

| Scope | Rows | SKUs | Actual revenue | Actual units | Any campaign 13w | Non-BF campaign 13w | BF txn 13w | Campaign <=28d | Campaign unit share | Non-BF campaign unit share | Campaign revenue share | Avg campaign discount | Max campaign discount |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Top 100 | 475 | 96 | 19,774,645 | 5,967.0 | 75.2% | 28.0% | 33.7% | 68.4% | 47.5% | 20.6% | 53.7% | 14.7% | 73.0% |
| Top 500 | 2,866 | 513 | 59,034,164 | 28,991.2 | 66.9% | 30.8% | 35.7% | 57.6% | 42.3% | 17.5% | 47.7% | 15.8% | 89.6% |
| Top 1000 | 5,346 | 945 | 79,136,333 | 51,818.2 | 69.1% | 30.8% | 35.3% | 58.1% | 44.3% | 19.0% | 48.9% | 16.2% | 89.6% |

## Top 1000 Target-Window Campaign Diagnostic

This section uses actual target-window labels only to explain what the model is trying to hit. These labels are not used as predictive features.

| Target bucket | Rows | Row share | Actual revenue | Revenue share | Actual units | Had campaign 13w | Campaign <=28d |
| --- | --- | --- | --- | --- | --- | --- | --- |
| campaign_observed_non_bf | 2,324 | 43.5% | 33,955,447 | 42.9% | 18,584.1 | 95.3% | 82.8% |
| non_campaign | 1,999 | 37.4% | 15,932,737 | 20.1% | 12,220.3 | 36.2% | 23.8% |
| bf_observed | 503 | 9.4% | 18,157,755 | 22.9% | 14,006.3 | 73.4% | 68.4% |
| unknown_campaign_label | 406 | 7.6% | 8,778,009 | 11.1% | 5,677.0 | 75.1% | 71.9% |
| bf_inferred | 114 | 2.1% | 2,312,385 | 2.9% | 1,330.5 | 73.7% | 59.6% |

## Route Coverage

| Route | Rows | SKUs | Actual revenue | Any campaign 13w | Non-BF campaign 13w | Campaign <=28d | Campaign unit share |
| --- | --- | --- | --- | --- | --- | --- | --- |
| bf_campaign_sensitive | 2,134 | 755 | 33,838,656 | 72.3% | 32.4% | 59.8% | 44.4% |
| available_regular | 986 | 408 | 15,441,693 | 70.6% | 36.0% | 66.7% | 40.2% |
| stock_constrained | 886 | 346 | 15,083,936 | 61.5% | 27.1% | 50.2% | 50.1% |
| sparse_intermittent | 738 | 372 | 6,724,248 | 67.2% | 28.9% | 49.3% | 40.8% |
| proxy_available_regular | 476 | 177 | 7,208,670 | 70.8% | 20.2% | 63.7% | 41.7% |
| availability_unknown | 67 | 49 | 318,482 | 64.2% | 41.8% | 41.8% | 51.5% |
| lifecycle_decline | 49 | 47 | 425,637 | 63.3% | 40.8% | 49.0% | 56.4% |
| seasonal_active | 9 | 5 | 93,282 | 66.7% | 44.4% | 55.6% | 70.2% |
| seasonal_quiet | 1 | 1 | 1,728 | 0.0% | 0.0% | 0.0% | - |

## Top Top-1000 Campaign-Heavy SKUs

| SKU | Revenue rank | Category | Family | Rows | Actual revenue | Actual units | Campaign units 13w | Non-BF campaign units 13w | Campaign unit share | Campaign txn 13w | Recent campaign rows |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| MH04 | 114 | MOBILIER DE CASA | MY HOME - LIRA | 8 | 217,230 | 631.0 | 1,392.0 | 1,062.0 | 72.9% | 270 | 8 |
| SNR10 | 667 | MOBILIER DE CASA | 9914200 SUNRISE | 8 | 71,953 | 434.0 | 1,316.0 | 944.0 | 83.0% | 394 | 8 |
| RHF06 | 145 | MOBILIER DE CASA | RIAN HENG - FAUSTO | 8 | 228,837 | 615.0 | 1,262.0 | 0.0 | 82.5% | 222 | 7 |
| BL13CT101 | 136 | ACCESORII | BILLERBECK | 8 | 204,589 | 549.0 | 1,104.0 | 0.0 | 60.4% | 611 | 8 |
| ACF03 | 431 | MOBILIER DE CASA | MY HOME - OTILIA | 7 | 100,390 | 310.0 | 1,075.0 | 817.0 | 86.1% | 252 | 6 |
| VAYOTELLO5 | 492 | ACCESORII | VAY | 8 | 50,917 | 417.1 | 992.2 | 0.0 | 64.1% | 61 | 6 |
| RHF32 | 462 | MOBILIER DE CASA | 9917052 RHENG LINEA - AIONESCU | 6 | 100,654 | 489.0 | 959.0 | 815.0 | 71.1% | 184 | 6 |
| WAVEPICAU | 524 | MOBILIER DE CASA | MURES MEX - WAVE | 8 | 71,775 | 379.0 | 905.0 | 0.0 | 73.6% | 557 | 8 |
| CEF14 | 408 | MOBILIER DE CASA | 9915210 CE FURNITURE A.I. | 8 | 44,247 | 184.0 | 871.0 | 751.0 | 83.8% | 233 | 6 |
| PRX827G | 699 | MOBILIER DE CASA | 9910147 LINEA MEX - PAREX | 8 | 75,391 | 289.0 | 849.0 | 609.0 | 79.6% | 212 | 7 |
| 46MAVI160200HARD | 27 | SALTELE SI SOMIERE | SOFT MEX CONFORT - OUTLET | 8 | 355,177 | 258.0 | 799.0 | 0.0 | 90.5% | 766 | 8 |
| ULK037 | 230 | CANAPELE SI FOTOLII | ULIKE - MERO | 8 | 147,537 | 258.0 | 772.0 | 556.0 | 87.5% | 213 | 8 |
| 46COMFORT160200 | 3 | SALTELE SI SOMIERE | SOFT MEX CONFORT - COMFORT 2023 | 8 | 708,118 | 361.0 | 754.0 | 661.0 | 63.8% | 728 | 8 |
| PRX827WH | 662 | MOBILIER DE CASA | 9910147 LINEA MEX - PAREX | 8 | 95,297 | 344.0 | 745.0 | 586.0 | 70.5% | 211 | 8 |
| 46COMFORTPLUS160200 | 5 | SALTELE SI SOMIERE | SOFT MEX CONFORT - COMFORT PLUS 2023 | 8 | 869,211 | 369.0 | 711.0 | 621.0 | 63.9% | 684 | 8 |
| MH08 | 779 | MOBILIER DE CASA | MY HOME - EDITH | 6 | 18,589 | 56.0 | 697.0 | 0.0 | 79.2% | 156 | 5 |
| SNR25 | 404 | MOBILIER DE CASA | 9914200 SUNRISE | 6 | 79,743 | 460.0 | 678.0 | 507.0 | 38.7% | 224 | 6 |
| SYW04 | 218 | MOBILIER DE CASA | 9918610 SYNERGY LINEA | 8 | 172,796 | 270.0 | 650.0 | 512.0 | 77.3% | 632 | 8 |
| JKB10 | 823 | MOBILIER DE CASA | FORTE - JACKOB | 8 | 69,071 | 221.0 | 613.0 | 0.0 | 87.3% | 385 | 8 |
| STL31 | 785 | MOBILIER DE CASA | 9914650 STARLIGHT | 5 | 20,148 | 67.0 | 590.0 | 569.0 | 91.8% | 72 | 5 |
| CEF07 | 628 | MOBILIER DE CASA | 9915210 CE FURNITURE A.I. | 6 | 86,442 | 270.0 | 583.0 | 439.0 | 64.8% | 199 | 6 |
| MCA117 | 472 | MOBILIER DE CASA | 9910120 LINEA MEX - MCASIA - AIONESCU | 8 | 101,984 | 207.0 | 581.0 | 479.0 | 89.0% | 122 | 8 |
| ULK018 | 710 | MOBILIER DE CASA | 9919916 U-LIKE-LINEA | 8 | 68,967 | 236.0 | 572.0 | 464.0 | 67.4% | 189 | 8 |
| ANJI11 | 716 | MOBILIER DE CASA | 9918550 ANJI - AIONESCU | 8 | 80,866 | 297.0 | 538.0 | 424.0 | 67.1% | 240 | 8 |
| CEF20 | 122 | MOBILIER DE CASA | 9915210 CE FURNITURE A.I. | 8 | 180,108 | 165.0 | 536.0 | 359.0 | 86.9% | 559 | 6 |

## Raw CAMPANIE Signal Status

| Value | Rows | Net units | Net revenue | First date | Last date |
| --- | --- | --- | --- | --- | --- |
| unknown | 482,308 | 1,213,660.6 | 527,142,093 | 2023-08-28 | 2025-03-23 |
| observed | 324,071 | 496,423.7 | 342,503,617 | 2023-08-28 | 2025-03-23 |

## Raw CAMPANIE Signal Source

| Value | Rows | Net units | Net revenue | First date | Last date |
| --- | --- | --- | --- | --- | --- |
| unknown | 482,308 | 1,213,660.6 | 527,142,093 | 2023-08-28 | 2025-03-23 |
| campaign_raw | 324,071 | 496,423.7 | 342,503,617 | 2023-08-28 | 2025-03-23 |

## Raw CAMPANIE BF Signal Status

| Value | Rows | Net units | Net revenue | First date | Last date |
| --- | --- | --- | --- | --- | --- |
| unknown | 687,400 | 1,471,390.0 | 742,628,682 | 2023-08-28 | 2025-03-23 |
| observed | 59,754 | 94,228.5 | 32,104,666 | 2023-11-06 | 2024-11-24 |
| inferred | 59,225 | 144,465.8 | 94,912,361 | 2023-11-06 | 2024-11-24 |

## Raw CAMPANIE BF Signal Source

| Value | Rows | Net units | Net revenue | First date | Last date |
| --- | --- | --- | --- | --- | --- |
| unknown | 646,873 | 1,393,565.9 | 708,178,814 | 2023-08-28 | 2025-03-23 |
| campaign_bf_raw | 59,754 | 94,228.5 | 32,104,666 | 2023-11-06 | 2024-11-24 |
| inferred_calendar_discount | 37,641 | 50,684.1 | 53,769,712 | 2023-11-06 | 2024-11-24 |
| campaign_label_without_timing_evidence | 27,773 | 54,205.0 | 13,458,530 | 2023-08-28 | 2025-03-23 |
| inferred_calendar_window | 18,929 | 89,729.8 | 39,884,373 | 2023-11-06 | 2024-11-24 |
| campaign_bf_outside_timing_window | 12,754 | 23,619.0 | 20,991,337 | 2023-08-28 | 2025-02-17 |
| inferred_current_year_campaign_and_calendar | 2,655 | 4,052.0 | 1,258,276 | 2023-11-06 | 2024-11-24 |

## Top Raw CAMPANIE Labels

| Value | Rows | Net units | Net revenue | First date | Last date |
| --- | --- | --- | --- | --- | --- |
| (blank) | 482,308 | 1,213,660.6 | 527,142,093 | 2023-08-28 | 2025-03-23 |
| BF 2022 PROMOTII | 96,985 | 117,892.8 | 113,158,045 | 2023-08-28 | 2025-03-23 |
| 2023_BLACK_FRIDAY PROMO | 33,320 | 64,906.0 | 16,496,977 | 2023-08-28 | 2025-03-23 |
| BF2025 | 31,388 | 50,350.0 | 4,939,722 | 2023-08-28 | 2025-03-23 |
| BF 2021 promotii | 21,050 | 33,837.2 | 11,229,628 | 2023-08-28 | 2025-03-23 |
| . | 17,483 | 20,932.0 | 30,087,370 | 2023-08-28 | 2025-03-23 |
| BF2024 | 14,737 | 34,719.0 | 13,479,038 | 2023-08-28 | 2025-03-23 |
| SUMMERSALE2025 | 8,133 | 8,062.0 | 16,093,782 | 2023-08-28 | 2025-03-23 |
| BF 2022 MAGAZIN | 7,202 | 10,034.4 | 930,064 | 2023-08-28 | 2025-03-23 |
| APARTAMENTE2025 | 6,588 | 6,369.0 | 21,278,198 | 2023-08-28 | 2025-03-23 |
| BF 2022 PLIANT | 6,058 | 7,315.0 | 14,764,101 | 2023-08-28 | 2025-03-23 |
| BF 2021 magazin | 5,320 | 5,886.4 | 6,025,686 | 2023-08-28 | 2025-03-23 |
| COVOARE_07_25 | 5,179 | 5,821.0 | 4,830,559 | 2023-08-28 | 2025-03-23 |
| SL 1_2019/promotii | 5,038 | 19,609.0 | 727,147 | 2023-08-28 | 2025-03-23 |
| MO1_2022 promotii | 4,586 | 4,858.0 | 6,458,384 | 2023-08-28 | 2025-03-23 |
| MEGAOCAZII2024 | 4,219 | 4,199.0 | 8,844,093 | 2023-08-28 | 2025-03-23 |
| FABRO_01_26 | 4,138 | 13,473.0 | 8,377,736 | 2023-08-28 | 2025-03-23 |
| NOUTATI | 3,746 | 16,131.0 | 740,164 | 2023-08-28 | 2025-03-22 |
| BF 2020 promotii | 3,482 | 4,515.0 | 1,755,119 | 2023-08-28 | 2025-03-23 |
| DEDICATE SALE 2025 | 3,317 | 3,135.0 | 8,345,937 | 2023-08-28 | 2025-03-23 |

## Top Raw CAMPANIE BF Labels

| Value | Rows | Net units | Net revenue | First date | Last date |
| --- | --- | --- | --- | --- | --- |
| (blank) | 733,871 | 1,592,236.8 | 816,549,706 | 2023-08-28 | 2025-03-23 |
| BF 2024  [04-24 NOIEMBRIE] | 42,473 | 71,396.1 | 33,533,208 | 2023-10-12 | 2024-11-24 |
| BF 2023  [06-19 NOIEMBRIE] | 30,022 | 46,454.4 | 19,584,765 | 2023-08-28 | 2023-11-19 |
| BF 2025  [03-23 NOIEMBRIE] | 13 | -3.0 | -21,969 | 2024-01-22 | 2025-02-17 |

## Notes

- Forecast V2 only; no old-engine path is used.
- Scored target windows audited: 2024-08-26, 2024-09-23, 2024-10-28, 2024-11-25, 2024-12-30, 2025-01-27, 2025-02-24, 2025-03-24.
- Feature matrix rows audited: 5,346.
- Max revenue rank audited: 1,000.
- Campaign history features query only raw sales where `sale_date < target_start`.
- CAMPANIE BF duration remains represented through BF timing/window features; generic CAMPANIE labels become historical participation features.
- Current snapshot rotation data remains excluded from historical backtests.
