"""Romanian calendar features for demand forecasting.

Computes Orthodox Easter (Meeus algorithm), public holidays, salary cycles,
and market season flags. All dates are deterministic — no external API needed.
"""

from datetime import date, timedelta
from typing import NamedTuple

from .config import (
    CONSTRUCTION_SEASON,
    EVENT_INFLUENCE_DAYS,
    EVENT_MULTIPLIERS,
    FIXED_HOLIDAYS,
    SALARY_DAYS,
    SALARY_INFLUENCE_DAYS,
    SALARY_MULTIPLIER,
    SUMMER_LULL,
)


class CalendarFeatures(NamedTuple):
    """Calendar-derived features for a single date."""
    is_holiday: bool
    holiday_name: str | None
    event_multiplier: float
    is_construction_season: bool
    is_summer_lull: bool
    is_salary_period: bool
    season_multiplier: float
    salary_multiplier: float
    combined_multiplier: float


class HolidayEntry(NamedTuple):
    """A single holiday with its date and event key."""
    date: date
    name: str
    event_key: str


def orthodox_easter(year: int) -> date:
    """Calculate Orthodox Easter date for a given year.

    Uses the Meeus Julian algorithm then converts to Gregorian calendar.
    Orthodox Easter follows the Julian calendar for the paschal computation
    and then maps the result to the Gregorian calendar.

    Args:
        year: The year to compute Easter for.

    Returns:
        A date object for Orthodox Easter Sunday.
    """
    a = year % 4
    b = year % 7
    c = year % 19
    d = (19 * c + 15) % 30
    e = (2 * a + 4 * b - d + 34) % 7
    month = (d + e + 114) // 31
    day = ((d + e + 114) % 31) + 1

    # Julian calendar date
    julian_easter = date(year, month, day)

    # Convert Julian to Gregorian: add offset days
    # For 1900-2099 the offset is 13 days
    # For 2100-2199 it becomes 14 days
    if year < 2100:
        gregorian_offset = 13
    elif year < 2200:
        gregorian_offset = 14
    else:
        gregorian_offset = 15

    return julian_easter + timedelta(days=gregorian_offset)


def get_holidays_for_year(year: int) -> list[HolidayEntry]:
    """Get all Romanian holidays and retail events for a given year.

    Returns fixed-date holidays plus Easter-dependent movable holidays.

    Args:
        year: The calendar year.

    Returns:
        Sorted list of HolidayEntry objects.
    """
    holidays: list[HolidayEntry] = []

    # Fixed-date holidays
    holiday_display_names = {
        "new_year_1": "New Year's Day",
        "new_year_2": "New Year (Day 2)",
        "unification_day": "Unification Day",
        "labour_day": "Labour Day",
        "childrens_day": "Children's Day",
        "assumption_of_mary": "Assumption of Mary",
        "st_andrew": "St. Andrew's Day",
        "national_day": "National Day",
        "christmas_1": "Christmas Day",
        "christmas_2": "Christmas (Day 2)",
        "womens_day": "Women's Day",
    }

    for key, (month, day) in FIXED_HOLIDAYS.items():
        holidays.append(HolidayEntry(
            date=date(year, month, day),
            name=holiday_display_names.get(key, key),
            event_key=_map_holiday_to_event_key(key),
        ))

    # Easter-dependent movable holidays
    easter = orthodox_easter(year)

    easter_holidays = [
        (easter - timedelta(days=2), "Good Friday", "orthodox_easter"),
        (easter, "Orthodox Easter", "orthodox_easter"),
        (easter + timedelta(days=1), "Easter Monday", "easter_monday"),
        (easter + timedelta(days=49), "Rusalii (Pentecost Saturday)", "rusalii"),
        (easter + timedelta(days=50), "Rusalii (Pentecost Sunday)", "rusalii"),
    ]

    for holiday_date, name, event_key in easter_holidays:
        holidays.append(HolidayEntry(
            date=holiday_date,
            name=name,
            event_key=event_key,
        ))

    # Black Friday — last Friday of November
    bf_date = _last_friday_of_november(year)
    holidays.append(HolidayEntry(
        date=bf_date,
        name="Black Friday",
        event_key="black_friday",
    ))

    return sorted(holidays, key=lambda h: h.date)


def get_calendar_features(target_date: date) -> CalendarFeatures:
    """Compute all calendar-derived features for a single date.

    Checks holidays (including influence windows), market seasons,
    and salary cycles. Returns a combined multiplier that accounts
    for all overlapping effects.

    Args:
        target_date: The date to compute features for.

    Returns:
        CalendarFeatures with all flags and multipliers.
    """
    year = target_date.year
    # Check holidays from current year and adjacent years (for cross-year windows)
    all_holidays = (
        get_holidays_for_year(year - 1)
        + get_holidays_for_year(year)
        + get_holidays_for_year(year + 1)
    )

    # Find the strongest event multiplier affecting this date
    best_multiplier = 1.0
    matched_holiday_name: str | None = None

    for holiday in all_holidays:
        event_key = holiday.event_key
        influence = EVENT_INFLUENCE_DAYS.get(event_key, {"before": 0, "after": 0})
        window_start = holiday.date - timedelta(days=influence["before"])
        window_end = holiday.date + timedelta(days=influence["after"])

        if window_start <= target_date <= window_end:
            multiplier = EVENT_MULTIPLIERS.get(event_key, 1.0)
            if multiplier > best_multiplier:
                best_multiplier = multiplier
                matched_holiday_name = holiday.name

    is_holiday = best_multiplier > 1.0

    # Market season flags
    month = target_date.month
    is_construction = month in CONSTRUCTION_SEASON["months"]
    is_summer_lull = month in SUMMER_LULL["months"]

    season_multiplier = 1.0
    if is_construction:
        season_multiplier *= CONSTRUCTION_SEASON["multiplier"]
    if is_summer_lull:
        season_multiplier *= SUMMER_LULL["multiplier"]

    # Salary cycle
    day_of_month = target_date.day
    is_salary = any(
        abs(day_of_month - sd) <= SALARY_INFLUENCE_DAYS
        for sd in SALARY_DAYS
    )
    sal_mult = SALARY_MULTIPLIER if is_salary else 1.0

    # Combined: event × season × salary
    combined = best_multiplier * season_multiplier * sal_mult

    return CalendarFeatures(
        is_holiday=is_holiday,
        holiday_name=matched_holiday_name,
        event_multiplier=best_multiplier,
        is_construction_season=is_construction,
        is_summer_lull=is_summer_lull,
        is_salary_period=is_salary,
        season_multiplier=season_multiplier,
        salary_multiplier=sal_mult,
        combined_multiplier=round(combined, 4),
    )


def get_week_calendar_features(week_start: date) -> CalendarFeatures:
    """Compute calendar features for a full week (Mon-Sun).

    Takes the maximum event multiplier across all 7 days of the week,
    and uses the week's midpoint for season/salary flags.

    Args:
        week_start: Monday of the target week.

    Returns:
        CalendarFeatures representing the week.
    """
    days = [week_start + timedelta(days=i) for i in range(7)]
    day_features = [get_calendar_features(d) for d in days]

    # Take the strongest event across the week
    best_idx = max(range(7), key=lambda i: day_features[i].event_multiplier)
    best = day_features[best_idx]

    # Use midpoint (Thursday) for season/salary flags
    mid = day_features[3]

    combined = best.event_multiplier * mid.season_multiplier * mid.salary_multiplier

    return CalendarFeatures(
        is_holiday=best.is_holiday,
        holiday_name=best.holiday_name,
        event_multiplier=best.event_multiplier,
        is_construction_season=mid.is_construction_season,
        is_summer_lull=mid.is_summer_lull,
        is_salary_period=any(df.is_salary_period for df in day_features),
        season_multiplier=mid.season_multiplier,
        salary_multiplier=mid.salary_multiplier,
        combined_multiplier=round(combined, 4),
    )


def _last_friday_of_november(year: int) -> date:
    """Find the last Friday of November for a given year."""
    # Start from November 30 and walk backward
    d = date(year, 11, 30)
    while d.weekday() != 4:  # 4 = Friday
        d -= timedelta(days=1)
    return d


def _map_holiday_to_event_key(holiday_key: str) -> str:
    """Map a fixed holiday config key to its event multiplier key."""
    mapping = {
        "new_year_1": "new_year",
        "new_year_2": "new_year",
        "christmas_1": "christmas",
        "christmas_2": "christmas",
        "national_day": "national_day",
        "womens_day": "womens_day",
        "labour_day": "labour_day",
    }
    return mapping.get(holiday_key, "")
