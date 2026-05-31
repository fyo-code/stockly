# Iteration 5N — V2 Phase 8E Availability Feature Matrix Audit

## Snapshot Coverage

| Target start | Rows | Qty scored rows | Actual units | Median naive units |
| --- | --- | --- | --- | --- |
| 2024-04-29 | 2,375 | 938 | 15,352.1 | 17,083.9 |
| 2024-05-27 | 2,434 | 1,057 | 17,445.4 | 15,919.2 |
| 2024-07-01 | 2,501 | 1,061 | 15,998.3 | 16,801.6 |
| 2024-07-29 | 2,536 | 1,149 | 15,978.3 | 15,357.3 |
| 2024-08-26 | 2,602 | 1,424 | 21,799.2 | 16,602.6 |
| 2024-09-23 | 2,623 | 1,367 | 21,494.0 | 19,143.3 |
| 2024-10-28 | 2,630 | 1,858 | 40,437.9 | 21,298.9 |
| 2024-11-25 | 2,692 | 989 | 19,076.3 | 29,008.6 |
| 2024-12-30 | 2,659 | 1,078 | 16,203.2 | 21,171.5 |
| 2025-01-27 | 2,638 | 1,231 | 18,494.0 | 20,193.9 |
| 2025-02-24 | 2,605 | 1,123 | 18,089.2 | 16,924.2 |
| 2025-03-24 | 2,596 | 1,205 | 19,360.9 | 17,833.5 |

## Feature Counts

| Feature group | Count |
| --- | --- |
| Numeric | 111 |
| Categorical | 10 |
| Total rows | 30,891 |

## Stock Feature Coverage

| Target start | Rows with store stock history | Store stock coverage | Store in-stock | Store likely stockout | Rows with supplier stock history | Supplier stock coverage | Supplier positive | Store or supplier available | Likely true stockout |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2024-04-29 | 59 | 2.5% | 56 | 3 | 1,842 | 77.6% | 1,404 | 1,414 | 280 |
| 2024-05-27 | 62 | 2.5% | 59 | 1 | 1,898 | 78.0% | 1,456 | 1,470 | 301 |
| 2024-07-01 | 66 | 2.6% | 64 | 0 | 1,936 | 77.4% | 1,466 | 1,477 | 261 |
| 2024-07-29 | 67 | 2.6% | 65 | 0 | 1,979 | 78.0% | 1,524 | 1,534 | 255 |
| 2024-08-26 | 67 | 2.6% | 67 | 0 | 2,037 | 78.3% | 1,641 | 1,652 | 262 |
| 2024-09-23 | 66 | 2.5% | 64 | 2 | 2,046 | 78.0% | 1,674 | 1,683 | 288 |
| 2024-10-28 | 68 | 2.6% | 64 | 3 | 2,062 | 78.4% | 1,683 | 1,690 | 322 |
| 2024-11-25 | 75 | 2.8% | 71 | 2 | 2,135 | 79.3% | 1,775 | 1,785 | 313 |
| 2024-12-30 | 66 | 2.5% | 64 | 2 | 2,117 | 79.6% | 1,751 | 1,759 | 357 |
| 2025-01-27 | 60 | 2.3% | 56 | 2 | 2,105 | 79.8% | 1,683 | 1,694 | 365 |
| 2025-02-24 | 60 | 2.3% | 58 | 1 | 2,102 | 80.7% | 1,642 | 1,652 | 319 |
| 2025-03-24 | 60 | 2.3% | 58 | 0 | 2,095 | 80.7% | 1,643 | 1,651 | 313 |

## Notes

- Each row is one SKU and one 4-week target window.
- Features use only data before `target_start`.
- Monthly store and supplier stock features use only completed months before each `target_start`; current snapshot files are excluded from historical backtests.
- Supplier stock features use only `exact_unique` product-name-to-SKU mappings. Ambiguous and unmapped supplier rows are excluded from official feature values.
- The default population is `forecastable_revenue_movers` only.
