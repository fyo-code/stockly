# Iteration 5B — V2 Feature Matrix Audit

## Snapshot Coverage

| Target start | Rows | Qty scored rows | Actual units | Median naive units |
| --- | --- | --- | --- | --- |
| 2024-04-29 | 1,981 | 771 | 11,686.7 | 13,281.0 |
| 2024-05-27 | 2,028 | 891 | 14,044.9 | 12,234.8 |
| 2024-07-01 | 2,100 | 889 | 12,879.0 | 13,689.7 |
| 2024-07-29 | 2,143 | 951 | 12,770.5 | 12,346.9 |
| 2024-08-26 | 2,204 | 1,207 | 17,497.7 | 13,298.3 |
| 2024-09-23 | 2,265 | 1,175 | 17,724.8 | 15,414.3 |
| 2024-10-28 | 2,287 | 1,628 | 34,014.2 | 17,188.5 |
| 2024-11-25 | 2,327 | 822 | 14,041.8 | 23,550.8 |
| 2024-12-30 | 2,345 | 907 | 13,437.0 | 17,106.3 |
| 2025-01-27 | 2,303 | 1,073 | 14,534.5 | 16,567.0 |
| 2025-02-24 | 2,296 | 977 | 14,505.2 | 13,536.4 |
| 2025-03-24 | 2,279 | 1,056 | 15,869.9 | 14,547.9 |

## Feature Counts

| Feature group | Count |
| --- | --- |
| Numeric | 48 |
| Categorical | 5 |
| Total rows | 26,558 |

## Notes

- Each row is one SKU and one 4-week target window.
- Features use only data before `target_start`.
- The default population is `forecastable_revenue_movers` only.
