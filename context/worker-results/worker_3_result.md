# Worker 3 — Data Pipeline Correctness Review

## Status
- Current: Complete
- Started: 2026-04-09T12:03:57Z
- Completed: 2026-04-09T12:05:30Z
- Note: Worker completed analysis but could not write file (permission issue). Conductor extracted findings from transcript.

## Findings

### Missing Weekly Aggregation Before Anomaly Detection
- **[File: backend/forecast_engine/cleaning.py]** — `detect_promotional_spikes()` uses a 13-week rolling average and `detect_stockouts()` looks for consecutive "weeks" of zero sales. But functions operate on raw transaction-level data (daily), not weekly aggregated data. This produces mathematically incorrect results — the rolling window covers 13 rows (days), not 13 weeks. Severity: CRITICAL.

### Date Format Handling Mismatch
- **[File: backend/forecast_engine/ingestion.py]** — `load_sales_data()` uses `pd.to_datetime()` with `errors='coerce'` (silently converts bad dates to NaT), but `validate_sales_data()` separately checks for null dates and prints errors. Dates that ingestion silently coerces to NaT are then caught by validation as failures — inconsistent behavior. Severity: HIGH.

### Silent Numeric Coercion
- **[File: backend/forecast_engine/ingestion.py]** — `pd.to_numeric(errors='coerce')` silently converts non-numeric values to NaN, which are then dropped. No notification to the user about data loss. On messy Pentaho exports, this could silently drop significant data. Severity: HIGH.

### Validation Errors Printed to Stdout
- **[File: backend/forecast_engine/ingestion.py]** — `validate_sales_data()` uses `print()` for error messages instead of raising exceptions or using logging. In production, these messages are lost. Severity: MEDIUM.

### No Data Lineage for Dropped Rows
- **[File: backend/forecast_engine/cleaning.py]** — Rows dropped during cleaning (NaN fill, clip to 0) have no audit trail. On real data, you can't tell what was modified. Severity: MEDIUM.

### Type Safety Edge Case
- **[File: backend/forecast_engine/cleaning.py]** — `.astype(int)` conversion could fail on NaN values that survive the cleaning pipeline. Severity: LOW.

## Summary
- CRITICAL: 1
- HIGH: 2
- MEDIUM: 2
- LOW: 1
- INFO: 0

## Recommendations

1. **Add weekly aggregation step before anomaly detection** — Create `aggregate_to_weekly()` that groups by sku_id, store_id, week and sums net_sold. Call this before `detect_promotional_spikes()` and `detect_stockouts()`. File: `cleaning.py`
2. **Unify date handling** — Either raise on bad dates in ingestion OR silently coerce, but not both. Recommend: coerce + log count of coerced dates. File: `ingestion.py`
3. **Log data loss from numeric coercion** — After `pd.to_numeric(errors='coerce')`, count NaN values created and log a warning. File: `ingestion.py`
4. **Replace print() with logging or exceptions** — Use `logging.warning()` for non-fatal issues, raise `ValueError` for fatal validation failures. File: `ingestion.py`
5. **Add cleaning audit log** — Return or log a dict of modifications made: rows dropped, values clipped, NaN filled. File: `cleaning.py`

## Confidence
Medium — Worker completed thorough line-by-line review of all 3 files. The CRITICAL finding about weekly aggregation is well-reasoned. Output extracted from transcript rather than structured file, but findings are substantive.
