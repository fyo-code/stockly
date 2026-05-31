# Worker 2 — Architecture & Integration Review

## Status
- Current: Complete
- Started: 2026-04-09T12:03:57Z
- Completed: 2026-04-09T12:05:10Z
- Note: Worker completed analysis but could not write file (permission issue). Conductor extracted findings from transcript summary.

## Findings

### Missing Type Exports
- **[File: backend/forecast_engine/__init__.py:22-29]** — `__all__` does not export any TypedDicts from data_models.py (`RawSalesTransaction`, `CleanedSalesTransaction`, `WeeklyDemand`, `ForecastOutput`, `EnsembleWeights`). Breaks the type API contract — callers must import from submodule directly. Severity: CRITICAL.

### Missing Weekly Aggregation Function
- **[File: backend/forecast_engine/]** — `WeeklyDemand` TypedDict is defined in data_models.py but no public function produces it. Aggregation logic exists only in test_phase_1a.py, not in the package. Severity: CRITICAL.

### Missing Return Type Annotations
- **[File: backend/forecast_engine/ingestion.py]** — `load_sales_data()` and `validate_sales_data()` lack return type annotations. Severity: HIGH.
- **[File: backend/forecast_engine/cleaning.py]** — `clean_sales_data()`, `detect_promotional_spikes()`, `detect_stockouts()` lack return type annotations. Severity: HIGH.

### No Defensive Column Checks in Anomaly Detection
- **[File: backend/forecast_engine/cleaning.py]** — `detect_promotional_spikes()` and `detect_stockouts()` assume `net_sold` column exists. If called before `clean_sales_data()`, raises KeyError with no useful message. Severity: HIGH.

### Implicit Column Dependencies
- **[File: backend/forecast_engine/cleaning.py]** — Functions depend on specific column names (`net_sold`, `sku_id`, `store_id`) but these dependencies are not documented or validated. Severity: MEDIUM.

### Double Validation Logic
- **[File: backend/forecast_engine/ingestion.py]** — Validation happens in both `load_sales_data()` and `validate_sales_data()`. Unclear which is authoritative. Severity: MEDIUM.

### Inconsistent Timezone Handling
- **[File: backend/forecast_engine/cleaning.py]** — Cleaning functions don't enforce UTC timezone that ingestion sets. Severity: MEDIUM.

### No Pipeline Composition Function
- **[File: backend/forecast_engine/__init__.py]** — No `run_pipeline()` or similar function to chain ingestion → cleaning → aggregation. Callers must manually sequence. Severity: MEDIUM.

### Implicit Ordering Requirement
- **[File: backend/forecast_engine/cleaning.py]** — Must call `clean_sales_data()` before `detect_promotional_spikes()` or `detect_stockouts()`. Not enforced or documented. Severity: MEDIUM.

### No Error Propagation Strategy
- **[File: backend/forecast_engine/]** — Some functions print errors, some return booleans, some raise exceptions. No consistent error handling pattern. Severity: MEDIUM.

### Missing Data Lineage
- **[File: backend/forecast_engine/cleaning.py]** — Rows dropped during cleaning are not logged or tracked. Severity: MEDIUM.

## Summary
- CRITICAL: 2
- HIGH: 3
- MEDIUM: 7
- LOW: 0
- INFO: 0

## Recommendations

1. **Export TypedDicts** — Add all data_models types to `__init__.py` `__all__` list. File: `__init__.py:22`
2. **Create `aggregate_to_weekly()` function** — Extract aggregation logic from test_phase_1a.py into cleaning.py or a new aggregation.py module.
3. **Add return type annotations** — All 5 public functions need `-> pd.DataFrame` or `-> bool` annotations.
4. **Add defensive column checks** — `detect_promotional_spikes()` and `detect_stockouts()` should validate required columns exist before processing.
5. **Document column dependencies** — Each function's docstring should list required input columns.
6. **Consolidate validation** — Choose one validation entry point (recommend `validate_sales_data()`) and have `load_sales_data()` call it.
7. **Enforce UTC in cleaning** — Add timezone check at start of cleaning functions.

## Confidence
Medium — Worker completed full analysis of all 5 files and produced detailed findings, but output was extracted from transcript summary rather than structured result file. Findings are substantive and well-evidenced.
