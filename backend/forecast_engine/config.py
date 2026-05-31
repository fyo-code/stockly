"""Hardcoded event multipliers and market cycle definitions for Romanian retail."""


# --- Ensemble Method Toggles ---
# Controls which forecasting methods participate in the ensemble.
# Archive a method (keep code, exclude from ensemble) by setting to False.
#
# LightGBM archived on 2026-04-24 (Iteration 3, Fix #1):
# Global model catastrophically over-predicted in Iter 2 (+306% bias, WMAPE 332.8%).
# Reintroduce when multi-store data is available and a Tweedie objective +
# zero-inflation classifier is added (see PROGRESS.md Iter 3 structural changes).
ENABLED_METHODS = {
    "ets": False,               # ARCHIVED Iter 5: live May-Jun 2025 data showed 145.2% WMAPE, +94.4% bias. Backtesting masked this because the May-Jun inflection point wasn't in any historical window. Bias cap of ±30% was nowhere near enough to absorb ~120%+ raw over-prediction.
    "anomaly_adjusted": True,   # Iter 4 B.1b archival REJECTED — restored. Bad alone (98.6% WMAPE) but pulling votes hurt the median ensemble (78.1% → 83.7%). Will be downweighted via Phase B.2 instead.
    "multi_scale_lag": True,    # Iter 4 B.1a archival REJECTED — restored
    "calendar_events": True,
    "lightgbm": False,  # ARCHIVED — see note above
    "category_relative": True,  # Iter 4 B.1b archival REJECTED — restored. Worst method (111.7% WMAPE) but archival regressed engine. Will be downweighted via Phase B.2 instead.
    "crostons": True,
    "naive_seasonal": True,  # Iter 3 Fix #3: same-month-last-year baseline
}


# --- Seasonal Dampening (Iter 3 Fix #4) ---
# Post-ensemble step: detect seasonal SKUs from training history and dampen
# their predictions by the avg monthly multiplier across the prediction window.
SEASONAL_DAMPENING_ENABLED = True


# --- Recency Filter (Iter 3 Fix #5) ---
# Pre-forecast step: drop SKUs that have been silent (zero net_sold) across
# the last N weeks of training. Avoids phantom predictions for inactive SKUs.
# Sits in the middle of the agreed 8-12 week range.
RECENCY_FILTER_ENABLED = True
RECENCY_FILTER_WEEKS = 10



# --- Event Multipliers ---
# Source: FORECAST_ENGINE_PHASE1_PLAN.md Method 6
# These are starting estimates — will be refined empirically during backtest phase.

EVENT_MULTIPLIERS = {
    "orthodox_easter": 1.40,
    "christmas": 1.60,
    "black_friday": 1.35,
    "womens_day": 1.25,       # March 8
    "national_day": 1.20,     # December 1
    "new_year": 1.15,         # Jan 1-2
    "labour_day": 1.05,       # May 1
    "easter_monday": 1.20,    # Day after Easter
    "rusalii": 1.10,          # Pentecost (Easter + 49/50 days)
}

# How many days before/after an event the multiplier effect applies
EVENT_INFLUENCE_DAYS = {
    "orthodox_easter": {"before": 7, "after": 2},
    "christmas": {"before": 14, "after": 7},
    "black_friday": {"before": 3, "after": 3},
    "womens_day": {"before": 5, "after": 1},
    "national_day": {"before": 3, "after": 1},
    "new_year": {"before": 3, "after": 2},
    "labour_day": {"before": 1, "after": 1},
    "easter_monday": {"before": 0, "after": 1},
    "rusalii": {"before": 1, "after": 1},
}


# --- Market Cycles ---
# Monthly multipliers for seasonal market patterns

CONSTRUCTION_SEASON = {
    "months": [4, 5, 6, 7, 8, 9],  # April through September
    "multiplier": 1.15,
}

SUMMER_LULL = {
    "months": [7, 8],  # July-August
    "multiplier": 0.80,
}


# --- Salary Cycle ---
# Romanians typically receive salary around 10th and 25th
SALARY_DAYS = [10, 25]
SALARY_INFLUENCE_DAYS = 2  # days before and after salary day with elevated spending
SALARY_MULTIPLIER = 1.10


# --- Fixed Romanian Public Holidays (month, day) ---
FIXED_HOLIDAYS = {
    "new_year_1": (1, 1),
    "new_year_2": (1, 2),
    "unification_day": (1, 24),    # Unification of Romanian Principalities
    "labour_day": (5, 1),
    "childrens_day": (6, 1),
    "assumption_of_mary": (8, 15), # Dormition of the Mother of God
    "st_andrew": (11, 30),
    "national_day": (12, 1),       # Great Union Day
    "christmas_1": (12, 25),
    "christmas_2": (12, 26),
    "womens_day": (3, 8),          # Not official public holiday but major retail event
}
