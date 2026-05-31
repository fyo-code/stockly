# Iter 4 — Promo Lift Analysis

Read-only diagnostic. Lift = mean YoY ratio (promo weeks) ÷ mean YoY ratio (non-promo weeks).
Prior year: same week −364 days. Min events for estimate: 30. CI: 95% bootstrap (1000 resamples).

**Scope:** Baneasa store only. Promo flags are store-level signals, not global Mobexpert rules.

| Category | Promo events | Non-promo events | Lift | 95% CI | Note |
|---|---:|---:|---:|---|---|
| ACCESORII | 3 | 545 | unknown | — | insufficient data (<30 promo events) |
| ALTELE | 0 | 0 | unknown | — | insufficient data (<30 promo events) |
| CANAPELE SI FOTOLII | 0 | 89 | unknown | — | insufficient data (<30 promo events) |
| MOBILIER BAIE SI SANITARE | 0 | 36 | unknown | — | insufficient data (<30 promo events) |
| MOBILIER BUCATARII | 0 | 7 | unknown | — | insufficient data (<30 promo events) |
| MOBILIER DE CASA | 178 | 484 | 1.104 | [0.948, 1.298] |  |
| MOBILIER OFFICE | 0 | 22 | unknown | — | insufficient data (<30 promo events) |
| MOBILIER TERASA SI GRADINA | 0 | 114 | unknown | — | insufficient data (<30 promo events) |
| PATURI TAPITATE | 0 | 34 | unknown | — | insufficient data (<30 promo events) |
| SALTELE SI SOMIERE | 0 | 217 | unknown | — | insufficient data (<30 promo events) |

## Interpretation

- Lift > 1 → promo weeks sell more than expected from prior-year baseline.
- Lift < 1 → promo weeks under-perform prior-year baseline (possible: campaigns on slow-moving items).
- 'unknown' → fewer than 30 promo events; estimate would be unreliable.

## Iter 4 usage

This is a diagnostic only. Lift values are not fed into method predictions in Iter 4.
Iter 5 will use this to calibrate promo multipliers inside individual methods.
