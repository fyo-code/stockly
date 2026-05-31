# Worker 4 — System Design Audit

## Status
- Current: Complete
- Started: 2026-04-09T12:04:00Z
- Completed: 2026-04-09T12:05:45Z
- Note: Worker completed analysis but could not write file (permission issue). Conductor extracted findings from transcript.

## Findings

### Incomplete Data Models vs Documentation
- **[File: backend/forecast_engine/data_models.py:1-60]** — PROGRESS.md line 317 claims `BacktestMetrics`, `EnsembleForecasts`, `ScenarioSimulation`, `ForecastEngineConfig` exist, but the file only contains 5 TypedDicts (`RawSalesTransaction`, `CleanedSalesTransaction`, `WeeklyDemand`, `ForecastOutput`, `EnsembleWeights`). Documentation/code discrepancy. Severity: HIGH.

### No Scaffolding for 6 Forecasting Methods
- **[File: backend/forecast_engine/__init__.py:1-30]** — Current package is flat (ingestion, cleaning, models). No `methods/` subdirectory, no base class/protocol for forecast methods, no factory pattern. Adding 6 independent methods (ETS, LightGBM, Category-Relative, Anomaly-Adjusted, Multi-Scale Lag, Calendar Events) to flat structure will create package debt. Severity: HIGH.

### Ensemble Orchestration Missing
- **[File: backend/forecast_engine/]** — No `ensemble.py` or `aggregate_forecasts()` function. `EnsembleWeights` TypedDict exists but is never used. The "median aggregation of 6 methods" architecture has zero implementation scaffolding. Severity: HIGH.

### ForecastEngineConfig Missing
- **[File: backend/forecast_engine/data_models.py]** — Claimed in PROGRESS.md but not in code. Hyperparameters currently hardcoded in function signatures (`threshold=2.5`, `window=13`, `min_consecutive_weeks=2`). Prevents reproducible configuration. Severity: HIGH.

### Package Structure Not Optimized for Methods
- **[File: backend/forecast_engine/__init__.py:15-29]** — Should have `forecast_engine/methods/` subdirectory. Current flat structure becomes unwieldy at 6+ method modules. Severity: MEDIUM.

### Anomaly Detection Mixed with Cleaning
- **[File: backend/forecast_engine/cleaning.py]** — `detect_promotional_spikes()` and `detect_stockouts()` are anomaly detection, not data cleaning. Should be in separate `anomaly.py` module for clarity. Severity: MEDIUM.

### No Method Interface/Protocol
- **[File: backend/forecast_engine/]** — No `ForecastMethod` Protocol or ABC defining the contract each of the 6 methods must implement (fit, predict, backtest). Each method will invent its own interface. Severity: MEDIUM.

### No Backtest Infrastructure
- **[File: backend/forecast_engine/]** — Phase 1H requires backtesting but there's no `backtest.py`, no `BacktestMetrics` type (claimed but missing), no train/test split utilities. Severity: MEDIUM.

## Summary
- CRITICAL: 0
- HIGH: 4
- MEDIUM: 4
- LOW: 0
- INFO: 0

## Recommendations

1. **Add missing TypedDicts to data_models.py** — Create `BacktestMetrics`, `EnsembleForecasts`, `ScenarioSimulation`, `ForecastEngineConfig` as documented.
2. **Create `methods/` subdirectory** — Structure: `forecast_engine/methods/__init__.py`, `methods/base.py` (Protocol), `methods/ets.py` (Phase 1B), etc.
3. **Define ForecastMethod Protocol** — `class ForecastMethod(Protocol): def fit(self, data: pd.DataFrame) -> None: ... def predict(self, periods: int) -> pd.DataFrame: ...`
4. **Create ensemble.py** — Even if empty, scaffold the `aggregate_forecasts()` function with the median aggregation approach.
5. **Extract anomaly detection** — Move `detect_promotional_spikes()` and `detect_stockouts()` to `anomaly.py`.
6. **Create ForecastEngineConfig** — Replace hardcoded parameters with a config TypedDict that all methods read.

## Confidence
Medium — Worker read all 4 forecast_engine files and PROGRESS.md. Findings are well-structured and cross-reference documentation vs code. Output extracted from transcript.
