# Iteration 5B — V2 Feature Matrix Audit

## Snapshot Coverage

| Target start | Rows | Qty scored rows | Actual units | Median naive units |
| --- | --- | --- | --- | --- |
| 2024-04-29 | 2,375 | 938 | 15,352.1 | 17,083.9 |

## Feature Counts

| Feature group | Count |
| --- | --- |
| Numeric | 66 |
| Categorical | 7 |
| Total rows | 2,375 |

## Stock Feature Coverage

| Target start | Rows with stock history | Stock coverage | In-stock before target | Likely stockout | Avg observed stores |
| --- | --- | --- | --- | --- | --- |
| 2024-04-29 | 59 | 2.5% | 56 | 3 | 0.12 |

## Notes

- Each row is one SKU and one 4-week target window.
- Features use only data before `target_start`.
- Monthly stock features use the previous completed month before each `target_start`; current snapshot files are excluded from historical backtests.
- The default population is `forecastable_revenue_movers` only.
