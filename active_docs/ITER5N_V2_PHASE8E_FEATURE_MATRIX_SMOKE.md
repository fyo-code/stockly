# Iteration 5N — V2 Phase 8E Availability Feature Matrix Audit

## Snapshot Coverage

| Target start | Rows | Qty scored rows | Actual units | Median naive units |
| --- | --- | --- | --- | --- |
| 2024-04-29 | 2,375 | 938 | 15,352.1 | 17,083.9 |

## Feature Counts

| Feature group | Count |
| --- | --- |
| Numeric | 111 |
| Categorical | 10 |
| Total rows | 2,375 |

## Stock Feature Coverage

| Target start | Rows with store stock history | Store stock coverage | Store in-stock | Store likely stockout | Rows with supplier stock history | Supplier stock coverage | Supplier positive | Store or supplier available | Likely true stockout |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2024-04-29 | 59 | 2.5% | 56 | 3 | 1,842 | 77.6% | 1,404 | 1,414 | 280 |

## Notes

- Each row is one SKU and one 4-week target window.
- Features use only data before `target_start`.
- Monthly store and supplier stock features use only completed months before each `target_start`; current snapshot files are excluded from historical backtests.
- Supplier stock features use only `exact_unique` product-name-to-SKU mappings. Ambiguous and unmapped supplier rows are excluded from official feature values.
- The default population is `forecastable_revenue_movers` only.
