# Iteration 5A — V2 Regime Labels Audit

Generated: 2026-05-11 16:48
As-of week: `2025-12-29`
Rule version: `v2_regime_2026_05_11`

## Summary

| Regime | SKUs | Trailing 52w revenue | Revenue share | Trailing 52w units |
| --- | --- | --- | --- | --- |
| forecastable_revenue_movers | 2,115 | 147,949,066.01 | 35.1% | 197,087.2 |
| seasonal_revenue_movers | 698 | 17,065,562.24 | 4.0% | 10,231.6 |
| active_movers | 1,016 | 4,296,201.63 | 1.0% | 75,765.1 |
| sparse_revenue_items | 5,981 | 172,559,598.75 | 40.9% | 133,320.9 |
| long_tail_active | 38,418 | 80,092,037.35 | 19.0% | 266,493.9 |
| dormant | 52,281 | 146.23 | 0.0% | 0.0 |

## Top-80 Revenue Set

| Metric | Value |
| --- | --- |
| Top-80 SKUs | 8,794 |
| Top-80 revenue | 337,574,227.00 |
| Top-80 cutoff revenue | 9,745.45 |
| Headline forecastable SKUs | 2,115 |
| Business target SKUs | 2,813 |

## Revenue Buckets

| Bucket | SKUs | Trailing 52w revenue |
| --- | --- | --- |
| 1001_5000 | 4,000 | 137,036,111.73 |
| 101_500 | 400 | 62,942,812.28 |
| 501_1000 | 500 | 43,976,659.30 |
| no_revenue | 52,276 | -163.31 |
| outside_80pct | 39,439 | 84,388,548.52 |
| rest_to_80pct | 3,794 | 50,906,432.36 |
| top_100 | 100 | 42,712,211.33 |

## Notes

- Labels use only `weekly_chain_demand_v2.week_start <= as_of_week`.
- Movement uses clipped positive units so return-only weeks do not create false activity.
- `headline_eligible` currently means `forecastable_revenue_movers`; seasonal movers are tracked as business-target eligible but scored separately.
