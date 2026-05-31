# Iteration 5I — V2 Target Cleanup Audit

Generated: 2026-05-19 23:49
Route version: `v2_routes_2026_05_17`

## Phase Checkpoint

Phase completed: Phase 7E — Target cleanup and data action checklist

What changed: no production model behavior changed. This phase reuses the current control predictions and classifies the biggest error groups into cleanup/data-action buckets.

Accuracy rerun: diagnostic only. Rebuilt the Phase 7C/7D measurement set using `35` analog neighbors, then evaluated the unchanged control model.

| Metric | Current headline control | After artifact-token review only | Delta |
| --- | --- | --- | --- |
| Model | sk_blend_post_bf_safe | sk_blend_post_bf_safe | - |
| Qty scored | 10,275 | 10,253 | - |
| Hit +/-20 | 24.1% | 24.1% | -0.0pp |
| Hit +/-30 | 35.3% | 35.3% | - |
| WMAPE | 56.1% | 56.2% | - |
| Phantom rate | 48.1% | 48.1% | - |

## Artifact-Token Candidate Impact

This is not an automatic exclusion. It flags rows whose SKU/family/category text looks operational or non-retail, especially pallet/service/logistics-like items.

| Slice | Rows | Qty scored | Actual units | Abs error | Hit +/-20 | WMAPE | Phantom rate |
| --- | --- | --- | --- | --- | --- | --- | --- |
| artifact_token_candidates | 24 | 22 | 5,058.0 | 2,649.9 | 40.9% | 52.4% | 100.0% |
| remaining_headline | 21,021 | 10,253 | 156,938.5 | 88,230.8 | 24.1% | 56.2% | 48.1% |

## Cleanup Bucket Summary

| Cleanup bucket | Rows | Qty scored | Revenue share | Hit +/-20 | Hit +/-30 | WMAPE | Bias | Phantom rate | Abs error share |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| artifact_or_non_retail_review | 24 | 22 | 0.1% | 40.9% | 40.9% | 52.4% | -17.8% | 100.0% | 2.9% |
| campaign_calendar_required | 9,986 | 4,950 | 52.8% | 21.4% | 31.9% | 61.8% | -14.0% | 55.9% | 55.4% |
| stock_availability_required | 5,256 | 3,478 | 31.4% | 29.7% | 42.7% | 47.0% | -2.3% | 64.7% | 29.6% |
| lifecycle_or_stock_policy | 5,700 | 1,782 | 15.5% | 20.1% | 29.8% | 60.8% | -36.6% | 34.3% | 12.0% |
| underprediction_review | 16 | 16 | 0.1% | 0.0% | 18.8% | 38.9% | -38.9% | - | 0.1% |
| overprediction_review | 11 | 11 | 0.0% | 0.0% | 36.4% | 54.4% | 54.4% | - | 0.0% |
| keep_in_headline_benchmark | 52 | 16 | 0.1% | 100.0% | 100.0% | 6.8% | -3.1% | 81.2% | 0.0% |

## Route Summary

| Route | Rows | Qty scored | Revenue share | Hit +/-20 | Hit +/-30 | WMAPE | Bias | Phantom rate | Abs error share |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| stock_constrained | 53 | 19 | 0.1% | 10.5% | 21.1% | 57.6% | -19.8% | 34.8% | 0.1% |
| bf_campaign_sensitive | 9,947 | 4,948 | 52.7% | 21.4% | 31.9% | 61.9% | -14.6% | 56.2% | 57.0% |
| seasonal_active | 47 | 12 | 0.1% | 33.3% | 33.3% | 72.3% | -37.0% | 38.1% | 0.1% |
| seasonal_quiet | 4 | 0 | 0.0% | - | - | - | - | 0.0% | 0.0% |
| sparse_intermittent | 5,380 | 1,630 | 14.6% | 19.8% | 29.4% | 60.1% | -42.7% | 32.8% | 10.2% |
| lifecycle_decline | 267 | 133 | 0.8% | 25.6% | 35.3% | 65.3% | 1.9% | 75.5% | 1.7% |
| available_regular | 77 | 43 | 0.1% | 37.2% | 53.5% | 29.9% | -10.3% | 78.6% | 0.1% |
| proxy_available_regular | 5,268 | 3,490 | 31.5% | 29.7% | 42.7% | 46.7% | -2.4% | 64.7% | 30.8% |
| availability_unknown | 2 | 0 | 0.0% | - | - | - | - | 100.0% | 0.0% |

## Top Family Cleanup List

| Family | Category | Route | Availability | Cleanup bucket | SKUs | Rows | Actual units | Pred units | Abs error | Hit +/-20 | Under >20 | Over >20 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| QUALITY CERAMIC | ACCESORII | proxy_available_regular | proxy_available | stock_availability_required | 42 | 219 | 13,786.0 | 12,980.1 | 8,580.6 | 14.6% | 39.7% | 45.7% |
| ACCESORII | ACCESORII | bf_campaign_sensitive | proxy_available | campaign_calendar_required | 112 | 298 | 11,448.6 | 11,316.6 | 6,274.6 | 20.5% | 41.6% | 37.9% |
| 9914200 SUNRISE | MOBILIER DE CASA | bf_campaign_sensitive | proxy_available | campaign_calendar_required | 33 | 176 | 3,792.0 | 3,866.9 | 2,889.0 | 19.3% | 31.8% | 48.9% |
| KINGBEST | ACCESORII | proxy_available_regular | proxy_available | stock_availability_required | 11 | 53 | 4,349.0 | 3,465.1 | 2,736.8 | 17.0% | 60.4% | 22.6% |
| PALETI | MOBILIER OFFICE | proxy_available_regular | proxy_available | artifact_or_non_retail_review | 3 | 22 | 5,058.0 | 4,155.4 | 2,649.9 | 40.9% | 27.3% | 31.8% |
| OSRAM | ACCESORII | bf_campaign_sensitive | proxy_available | campaign_calendar_required | 6 | 28 | 4,410.0 | 4,614.0 | 2,295.0 | 14.3% | 32.1% | 53.6% |
| 9910147 LINEA MEX - PAREX | MOBILIER DE CASA | bf_campaign_sensitive | proxy_available | campaign_calendar_required | 23 | 150 | 3,130.0 | 2,788.4 | 1,850.2 | 20.0% | 42.7% | 37.3% |
| OUT001 OUTLET - OUTDOOR | MOBILIER TERASA SI GRADINA | proxy_available_regular | stock_unobserved | stock_availability_required | 32 | 107 | 2,585.0 | 1,325.5 | 1,668.6 | 18.7% | 62.6% | 18.7% |
| 02521 MURES MEX - DRESSING COMPACT | MOBILIER DE CASA | bf_campaign_sensitive | proxy_available | campaign_calendar_required | 34 | 208 | 3,486.0 | 3,702.2 | 1,626.4 | 29.8% | 34.6% | 35.6% |
| 9915210 CE FURNITURE A.I. | MOBILIER DE CASA | bf_campaign_sensitive | proxy_available | campaign_calendar_required | 15 | 84 | 2,027.0 | 1,678.9 | 1,564.8 | 19.0% | 36.9% | 44.0% |
| STUDIO - MURES MEX | MOBILIER OFFICE | proxy_available_regular | proxy_available | stock_availability_required | 12 | 58 | 1,221.0 | 1,025.2 | 965.8 | 13.8% | 34.5% | 51.7% |
| ROLL SERVICE | ACCESORII | bf_campaign_sensitive | proxy_available | campaign_calendar_required | 4 | 15 | 2,096.4 | 1,989.3 | 920.3 | 33.3% | 33.3% | 33.3% |
| 9919916 U-LIKE-LINEA | MOBILIER DE CASA | bf_campaign_sensitive | proxy_available | campaign_calendar_required | 10 | 61 | 1,539.0 | 1,445.5 | 918.6 | 19.7% | 34.4% | 45.9% |
| LINEA-CLASIC PROD MEX - JAZZ | MOBILIER DE CASA | bf_campaign_sensitive | proxy_available | campaign_calendar_required | 31 | 135 | 1,608.0 | 1,278.2 | 906.7 | 20.7% | 50.4% | 28.9% |
| KAVA | ACCESORII | bf_campaign_sensitive | stock_unobserved | campaign_calendar_required | 50 | 191 | 1,680.0 | 1,176.6 | 901.2 | 25.1% | 55.5% | 19.4% |
| 9919970 GF - LINEA | MOBILIER DE CASA | bf_campaign_sensitive | proxy_available | campaign_calendar_required | 9 | 49 | 1,105.0 | 773.1 | 861.4 | 18.4% | 42.9% | 38.8% |
| MURES MEX - WAVE | MOBILIER DE CASA | bf_campaign_sensitive | proxy_available | campaign_calendar_required | 25 | 110 | 1,546.0 | 1,674.3 | 816.2 | 28.2% | 30.9% | 40.9% |
| 02523 MURES MEX - RING | MOBILIER DE CASA | proxy_available_regular | proxy_available | stock_availability_required | 9 | 67 | 1,470.0 | 1,811.6 | 812.9 | 23.9% | 25.4% | 50.7% |
| 9918550 ANJI - AIONESCU | MOBILIER DE CASA | bf_campaign_sensitive | proxy_available | campaign_calendar_required | 10 | 57 | 1,241.0 | 1,203.1 | 758.6 | 21.1% | 31.6% | 47.4% |
| 9910120 LINEA MEX - MCASIA - AIONESCU | MOBILIER DE CASA | bf_campaign_sensitive | proxy_available | campaign_calendar_required | 14 | 73 | 1,239.0 | 1,150.8 | 734.9 | 19.2% | 37.0% | 43.8% |
| 00125 ERGO MEX - RPC | MOBILIER OFFICE | proxy_available_regular | proxy_available | stock_availability_required | 7 | 22 | 850.0 | 481.8 | 720.5 | 9.1% | 59.1% | 31.8% |
| WELLMAX | ACCESORII | bf_campaign_sensitive | proxy_available | campaign_calendar_required | 2 | 15 | 922.0 | 1,114.8 | 720.5 | 6.7% | 40.0% | 53.3% |
| RIAN HENG - FAUSTO | MOBILIER DE CASA | bf_campaign_sensitive | proxy_available | campaign_calendar_required | 2 | 12 | 703.0 | 377.0 | 687.7 | 41.7% | 41.7% | 16.7% |
| LUCEA LIGHTING | ACCESORII | bf_campaign_sensitive | proxy_available | campaign_calendar_required | 29 | 165 | 1,524.0 | 1,423.0 | 669.0 | 34.5% | 32.1% | 33.3% |
| ORIZONTTE | ACCESORII | bf_campaign_sensitive | proxy_available | campaign_calendar_required | 45 | 172 | 1,533.0 | 1,236.4 | 662.6 | 29.7% | 47.7% | 22.7% |

## Top SKU Cleanup List

| SKU | Family | Category | Route | Cleanup bucket | Windows | Actual units | Pred units | Abs error | Hit +/-20 | Data needed |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| JRL796 | ACCESORII | ACCESORII | bf_campaign_sensitive | campaign_calendar_required | 8 | 5,195.4 | 4,823.1 | 2,362.0 | 12.5% | campaign calendar, SKU campaign membership, campaign start/end, discount mechanics |
| PALETMIC | PALETI | MOBILIER OFFICE | proxy_available_regular | artifact_or_non_retail_review | 7 | 2,633.0 | 2,032.3 | 1,634.9 | 28.6% | product master type, service/logistics flags, SKU business owner |
| QCIP33-02E019 | QUALITY CERAMIC | ACCESORII | proxy_available_regular | stock_availability_required | 8 | 1,271.0 | 1,070.1 | 999.4 | 12.5% | store monthly stock, supplier monthly stock, reserved stock, NIR/receipts, replenishment orders |
| OSM2451 | OSRAM | ACCESORII | bf_campaign_sensitive | campaign_calendar_required | 8 | 2,050.0 | 2,099.0 | 986.8 | 37.5% | campaign calendar, SKU campaign membership, campaign start/end, discount mechanics |
| QCIP33-04E019 | QUALITY CERAMIC | ACCESORII | proxy_available_regular | stock_availability_required | 8 | 1,181.0 | 1,074.1 | 952.4 | 0.0% | store monthly stock, supplier monthly stock, reserved stock, NIR/receipts, replenishment orders |
| OSM4981 | OSRAM | ACCESORII | bf_campaign_sensitive | campaign_calendar_required | 8 | 1,680.0 | 1,586.7 | 886.7 | 0.0% | campaign calendar, SKU campaign membership, campaign start/end, discount mechanics |
| PALETMARE | PALETI | MOBILIER OFFICE | proxy_available_regular | artifact_or_non_retail_review | 7 | 1,998.0 | 1,699.2 | 881.3 | 28.6% | product master type, service/logistics flags, SKU business owner |
| QCIP33-03E019 | QUALITY CERAMIC | ACCESORII | proxy_available_regular | stock_availability_required | 8 | 960.0 | 786.7 | 764.2 | 0.0% | store monthly stock, supplier monthly stock, reserved stock, NIR/receipts, replenishment orders |
| RHF06 | RIAN HENG - FAUSTO | MOBILIER DE CASA | bf_campaign_sensitive | campaign_calendar_required | 8 | 615.0 | 357.0 | 618.1 | 25.0% | campaign calendar, SKU campaign membership, campaign start/end, discount mechanics |
| SNR25 | 9914200 SUNRISE | MOBILIER DE CASA | bf_campaign_sensitive | campaign_calendar_required | 8 | 534.0 | 523.7 | 611.6 | 0.0% | campaign calendar, SKU campaign membership, campaign start/end, discount mechanics |
| QCIP33-33E019 | QUALITY CERAMIC | ACCESORII | proxy_available_regular | stock_availability_required | 8 | 884.0 | 1,032.9 | 605.6 | 12.5% | store monthly stock, supplier monthly stock, reserved stock, NIR/receipts, replenishment orders |
| KBGD01 | KINGBEST | ACCESORII | bf_campaign_sensitive | campaign_calendar_required | 8 | 685.0 | 703.3 | 573.8 | 12.5% | campaign calendar, SKU campaign membership, campaign start/end, discount mechanics |
| ESLLEDNL22G9NF | ESL | ACCESORII | proxy_available_regular | stock_availability_required | 7 | 1,407.0 | 1,035.4 | 569.9 | 0.0% | store monthly stock, supplier monthly stock, reserved stock, NIR/receipts, replenishment orders |
| KBGD03 | KINGBEST | ACCESORII | bf_campaign_sensitive | campaign_calendar_required | 8 | 583.0 | 572.6 | 561.8 | 0.0% | campaign calendar, SKU campaign membership, campaign start/end, discount mechanics |
| QCIP313002 | QUALITY CERAMIC | ACCESORII | proxy_available_regular | stock_availability_required | 8 | 720.0 | 553.6 | 517.5 | 12.5% | store monthly stock, supplier monthly stock, reserved stock, NIR/receipts, replenishment orders |
| WVE20062 | WELLMAX | ACCESORII | bf_campaign_sensitive | campaign_calendar_required | 7 | 380.0 | 729.4 | 504.3 | 0.0% | campaign calendar, SKU campaign membership, campaign start/end, discount mechanics |
| QCIP313006 | QUALITY CERAMIC | ACCESORII | proxy_available_regular | stock_availability_required | 8 | 728.0 | 648.4 | 483.9 | 0.0% | store monthly stock, supplier monthly stock, reserved stock, NIR/receipts, replenishment orders |
| KBGD02 | KINGBEST | ACCESORII | bf_campaign_sensitive | campaign_calendar_required | 6 | 621.0 | 500.8 | 474.5 | 0.0% | campaign calendar, SKU campaign membership, campaign start/end, discount mechanics |
| JRL799 | ROLL SERVICE | ACCESORII | bf_campaign_sensitive | campaign_calendar_required | 8 | 669.5 | 1,013.4 | 469.4 | 25.0% | campaign calendar, SKU campaign membership, campaign start/end, discount mechanics |
| QCIP309006A | QUALITY CERAMIC | ACCESORII | bf_campaign_sensitive | campaign_calendar_required | 8 | 929.0 | 1,017.1 | 441.8 | 37.5% | campaign calendar, SKU campaign membership, campaign start/end, discount mechanics |
| QCIP3004 | ACCESORII | ACCESORII | proxy_available_regular | stock_availability_required | 8 | 692.0 | 797.4 | 427.1 | 25.0% | store monthly stock, supplier monthly stock, reserved stock, NIR/receipts, replenishment orders |
| OSM2482 | ACCESORII | ACCESORII | bf_campaign_sensitive | campaign_calendar_required | 8 | 801.0 | 618.5 | 398.4 | 25.0% | campaign calendar, SKU campaign membership, campaign start/end, discount mechanics |
| SNR10 | 9914200 SUNRISE | MOBILIER DE CASA | bf_campaign_sensitive | campaign_calendar_required | 8 | 434.0 | 511.6 | 394.5 | 12.5% | campaign calendar, SKU campaign membership, campaign start/end, discount mechanics |
| SNR06 | 9914200 SUNRISE | MOBILIER DE CASA | bf_campaign_sensitive | campaign_calendar_required | 8 | 429.0 | 490.5 | 385.7 | 25.0% | campaign calendar, SKU campaign membership, campaign start/end, discount mechanics |
| QCIP313004 | QUALITY CERAMIC | ACCESORII | bf_campaign_sensitive | campaign_calendar_required | 7 | 522.0 | 294.5 | 380.3 | 0.0% | campaign calendar, SKU campaign membership, campaign start/end, discount mechanics |
| KBSV01 | KINGBEST | ACCESORII | proxy_available_regular | stock_availability_required | 8 | 864.0 | 557.4 | 364.1 | 25.0% | store monthly stock, supplier monthly stock, reserved stock, NIR/receipts, replenishment orders |
| QCIP309002A | ACCESORII | ACCESORII | bf_campaign_sensitive | campaign_calendar_required | 8 | 756.0 | 779.2 | 358.3 | 25.0% | campaign calendar, SKU campaign membership, campaign start/end, discount mechanics |
| ACF03 | MY HOME - OTILIA | MOBILIER DE CASA | bf_campaign_sensitive | campaign_calendar_required | 7 | 396.0 | 240.4 | 357.5 | 14.3% | campaign calendar, SKU campaign membership, campaign start/end, discount mechanics |
| KBSV05 | KINGBEST | ACCESORII | proxy_available_regular | stock_availability_required | 8 | 753.0 | 501.3 | 347.9 | 25.0% | store monthly stock, supplier monthly stock, reserved stock, NIR/receipts, replenishment orders |
| MH04 | MY HOME - LIRA | MOBILIER DE CASA | bf_campaign_sensitive | campaign_calendar_required | 8 | 631.0 | 441.1 | 341.8 | 12.5% | campaign calendar, SKU campaign membership, campaign start/end, discount mechanics |
| DILIRMA01 | ACCESORII | ACCESORII | sparse_intermittent | lifecycle_or_stock_policy | 8 | 386.5 | 229.9 | 338.2 | 12.5% | collection age, active/discontinued flag, first stock date, last stock date, monthly stock |
| GFF13 | 9919970 GF - LINEA | MOBILIER DE CASA | bf_campaign_sensitive | campaign_calendar_required | 8 | 345.0 | 230.4 | 333.2 | 25.0% | campaign calendar, SKU campaign membership, campaign start/end, discount mechanics |
| OSM8514 | OSRAM | ACCESORII | bf_campaign_sensitive | campaign_calendar_required | 8 | 564.0 | 824.9 | 315.9 | 25.0% | campaign calendar, SKU campaign membership, campaign start/end, discount mechanics |
| TPW51392GY | OUT001 OUTLET - OUTDOOR | MOBILIER TERASA SI GRADINA | bf_campaign_sensitive | campaign_calendar_required | 6 | 440.0 | 156.8 | 309.5 | 0.0% | campaign calendar, SKU campaign membership, campaign start/end, discount mechanics |
| VAYOTELLO5 | VAY | ACCESORII | bf_campaign_sensitive | campaign_calendar_required | 8 | 417.1 | 584.5 | 300.8 | 25.0% | campaign calendar, SKU campaign membership, campaign start/end, discount mechanics |
| RING2MANAU | 02523 MURES MEX - RING | MOBILIER DE CASA | bf_campaign_sensitive | campaign_calendar_required | 8 | 468.0 | 611.4 | 300.0 | 25.0% | campaign calendar, SKU campaign membership, campaign start/end, discount mechanics |
| WINVOILEWHITE | WINBRELLA - PERDELE | ACCESORII | proxy_available_regular | stock_availability_required | 5 | 414.3 | 219.6 | 297.9 | 0.0% | store monthly stock, supplier monthly stock, reserved stock, NIR/receipts, replenishment orders |
| MH08 | MY HOME - EDITH | MOBILIER DE CASA | bf_campaign_sensitive | campaign_calendar_required | 6 | 306.0 | 180.6 | 296.9 | 16.7% | campaign calendar, SKU campaign membership, campaign start/end, discount mechanics |
| OTTOTETNG10002001 | 00125 ERGO MEX - RPC | MOBILIER OFFICE | proxy_available_regular | stock_availability_required | 7 | 295.0 | 175.1 | 294.9 | 14.3% | store monthly stock, supplier monthly stock, reserved stock, NIR/receipts, replenishment orders |
| QCIP309004A | QUALITY CERAMIC | ACCESORII | bf_campaign_sensitive | campaign_calendar_required | 8 | 592.0 | 597.5 | 289.3 | 25.0% | campaign calendar, SKU campaign membership, campaign start/end, discount mechanics |

## Pentaho Data Checklist

| Priority | Cube | Why it matters | Must-have fields |
| --- | --- | --- | --- |
| 1 | `iz_audit_stoc_lunar_sc_mex` | Monthly store stock by SKU/store/month | SKU code, store, month/end date, stock qty/value, available qty if present |
| 2 | `iz_audit_stoc_lunar_sc_fzmex` | Monthly supplier/importer stock by SKU/month | SKU code, supplier/importer, month/end date, stock qty/value, available qty |
| 3 | `Stocuri Magazine_zile vechime` | Store stock age and availability snapshot | SKU code, store, stock qty, days in stock, collection age, available/reserved qty |
| 4 | `Stocuri Importatori_zile vechime` | Supplier stock age and supplier availability | SKU code, supplier, available supplier stock, days in stock, collection age |
| 5 | `Raport Comenzi` / `Raport Comenzi YTD` | Order timing and order/invoice lag | Order date, invoice date, status, SKU, store, quantity, cancellations/returns if available |
| 6 | `DGA_YTD_VZ_MAG_SI_OUTLET` / `Vanzari Magazine Arhiva` | Detailed sales history and campaign fields | DATA COMANDA, DATA, SKU, store, campaign, campaign BF, discount, revenue, quantity |
| 7 | `ART_RAP` | Product master and SKU lifecycle | SKU status, category/class/subclass, supplier, dimensions, collection/line age, active/discontinued flags |
| 8 | `Comenzi Aprovizionare Furnizor vs Receptii` / `IZ_NIR_M10_ACH_CAT` | Receipts and replenishment lead-time signals | SKU, supplier, order date, receipt date, received qty, expected qty, store/warehouse destination |
| 9 | `Articole rezervate` | Reserved stock and demand already committed | SKU, store, reserved qty/value, reservation/order date, status |
| 10 | `Management Livrari` | Delivery delay signal for invoice fallback noise | SKU/order, delivery dates, delivery status, store, custom/long-lead indicators if present |

## KPI Treatment Recommendation

- Keep the current headline control as the continuity benchmark until exclusions are approved.
- Create a separate `artifact_or_non_retail_review` slice; do not silently remove it.
- Report BF/campaign-sensitive demand separately until actual campaign calendars and membership are available.
- Treat stock-unobserved and proxy-available rows as lower-confidence forecast rows, not proof of model failure or model success.
- Main future KPI should become available forecastable retail SKU demand, with excluded/censored volume reported beside it.

## Decision

Phase 7E confirms that target cleanup alone is not enough to unlock the model. Even after removing obvious artifact-token candidates, the hit +/-20 slice stays below 40%, so the next real step is data acquisition: stock, campaign membership/calendar, SKU lifecycle, and receipts.

## Skipped Windows

`2024-04-29`, `2024-05-27`, `2024-07-01`, `2024-07-29`

## Notes

- Requested target windows: 2024-04-29, 2024-05-27, 2024-07-01, 2024-07-29, 2024-08-26, 2024-09-23, 2024-10-28, 2024-11-25, 2024-12-30, 2025-01-27, 2025-02-24, 2025-03-24.
- Artifact-token logic is deliberately conservative and only uses SKU/family/category text. It is a review queue, not a final rule.
- Snapshot stock files remain excluded from historical training unless they carry valid historical as-of dates.
- Next model work should wait until the top cleanup buckets are resolved or the requested Pentaho stock/campaign/lifecycle data is loaded.
