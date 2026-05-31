# Iteration 5O — V2 Phase 8F Rotation Snapshot Ingestion

Generated: 2026-05-21 23:39

## Phase Checkpoint

Phase completed: Phase 8F — rotation snapshot ingestion for current/future diagnostics.

Snapshot date assigned: `2026-05-21`. These files do not contain historical as-of dates, so every row is marked `current_snapshot` and must not be used in official historical backtests.

Accuracy rerun: no. Current-only rotation snapshots can support diagnostics and future forecast enrichment, but they are not leak-safe historical training inputs.

## Import Result

| File | Store | Rows | Inserted | Skipped | SKUs | Sales overlap | Sales overlap % | Headline overlap | Prior rows removed |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| viteza rotatie stock constanta.csv | constanta | 52,251 | 52,251 | 0 | 52,251 | 42,663 | 81.7% | 3,342 | 0 |
| viteza rotatie stock militari.csv | militari | 52,783 | 52,783 | 0 | 52,783 | 43,215 | 81.9% | 3,337 | 0 |
| viteza rotatie stock pipera.csv | pipera | 55,323 | 55,323 | 0 | 55,323 | 44,179 | 79.9% | 3,385 | 0 |
| viteza rotatie stock sibiu.csv | sibiu | 50,699 | 50,699 | 0 | 50,699 | 41,838 | 82.5% | 3,314 | 0 |

## Snapshot Quality

| File | Missing months-of-stock | Missing all rotation metrics | Positive available rows | Positive available % | Positive total rows | Positive total % |
| --- | --- | --- | --- | --- | --- | --- |
| viteza rotatie stock constanta.csv | 26.3% | 5.3% | 18,515 | 35.4% | 19,308 | 37.0% |
| viteza rotatie stock militari.csv | 27.0% | 6.3% | 18,869 | 35.7% | 19,450 | 36.8% |
| viteza rotatie stock pipera.csv | 30.4% | 10.6% | 26,115 | 47.2% | 26,636 | 48.1% |
| viteza rotatie stock sibiu.csv | 24.0% | 2.4% | 14,808 | 29.2% | 15,001 | 29.6% |

## Store Summary

| Store | Records | SKUs | Missing months-of-stock | Missing store M12 rotation | Positive available | Positive total |
| --- | --- | --- | --- | --- | --- | --- |
| constanta | 52,251 | 52,251 | 26.3% | 15.4% | 18,515 | 19,308 |
| militari | 52,783 | 52,783 | 27.0% | 16.2% | 18,869 | 19,450 |
| pipera | 55,323 | 55,323 | 30.4% | 20.1% | 26,115 | 26,636 |
| sibiu | 50,699 | 50,699 | 24.0% | 12.8% | 14,808 | 15,001 |

## Table Summary

| Table | Records | SKUs | Stores | Feature scope |
| --- | --- | --- | --- | --- |
| stock_rotation_snapshot_v2 | 211,056 | 61,121 | 4 | current_snapshot |

## Historical Safety

- These rotation files are useful for current/future forecasts and operational diagnostics.
- They are not used in Phase 8E or any official historical scorecard because the export has no historical as-of month/date.
- If future exports include monthly historical rotation or an as-of date per snapshot, we can create separate historical-safe features.

## Accuracy Report

Accuracy not re-run. Official Phase 8E best raw hit +/-20 remains 24.6%; safer blend remains hit +/-20 24.2%, WMAPE 55.6%, phantom 44.4%.
