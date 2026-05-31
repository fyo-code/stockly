"""Observed/inferred/unknown feature signal helpers for forecast v2."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime, timedelta


BF_RE = re.compile(r"\bBF\b|BLACK[_ ]?FRIDAY", re.IGNORECASE)
YEAR_RE = re.compile(r"\b(20\d{2})\b")
BF_WINDOW_RE = re.compile(r"\[(\d{1,2})\s*-\s*(\d{1,2})\s+([^\]]+)\]", re.IGNORECASE)

KNOWN_BF_WINDOWS = {
    2022: (date(2022, 11, 9), date(2022, 11, 20)),
    2023: (date(2023, 11, 6), date(2023, 11, 19)),
    2024: (date(2024, 11, 4), date(2024, 11, 24)),
    2025: (date(2025, 11, 3), date(2025, 11, 23)),
}

MONTH_MAP = {
    "IANUARIE": 1,
    "FEBRUARIE": 2,
    "MARTIE": 3,
    "APRILIE": 4,
    "MAI": 5,
    "IUNIE": 6,
    "IULIE": 7,
    "AUGUST": 8,
    "SEPTEMBRIE": 9,
    "OCTOMBRIE": 10,
    "NOIEMBRIE": 11,
    "DECEMBRIE": 12,
}


@dataclass(frozen=True)
class CampaignSignals:
    is_bf_campaign: int
    is_bf_timing: int
    is_bf_observed: int
    is_bf_inferred: int
    is_product_program: int
    campaign_signal_status: str
    campaign_signal_source: str
    bf_signal_status: str
    bf_signal_source: str


def clean_text(value: object) -> str:
    if value is None:
        return ""
    return str(value).replace("\ufeff", "").strip().strip('"').strip()


def _parse_iso_date(value: str) -> date | None:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def _last_friday_of_november(year: int) -> date:
    current = date(year, 11, 30)
    while current.weekday() != 4:
        current -= timedelta(days=1)
    return current


def _bf_window_for_year(year: int) -> tuple[date, date]:
    if year in KNOWN_BF_WINDOWS:
        return KNOWN_BF_WINDOWS[year]
    bf_day = _last_friday_of_november(year)
    return bf_day - timedelta(days=4), bf_day + timedelta(days=2)


def _campaign_years(value: str) -> set[int]:
    return {int(match) for match in YEAR_RE.findall(value)}


def _strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def _parse_bf_window(value: str, sale_year: int | None) -> tuple[date, date] | None:
    match = BF_WINDOW_RE.search(value)
    if not match:
        return None
    years = _campaign_years(value)
    year = next(iter(sorted(years)), None) or sale_year
    if year is None:
        return None

    start_day = int(match.group(1))
    end_day = int(match.group(2))
    month_name = _strip_accents(match.group(3)).upper().strip()
    month_name = re.sub(r"[^A-Z]+", " ", month_name).strip().split(" ")[0]
    month = MONTH_MAP.get(month_name)
    if month is None:
        return None

    try:
        return date(year, month, start_day), date(year, month, end_day)
    except ValueError:
        return None


def classify_campaign_signals(
    sale_date: str,
    raw_campaign: object = None,
    raw_bf: object = None,
    discount_pct: float | None = None,
) -> CampaignSignals:
    """Classify campaign/BF fields without confusing missing with false.

    `CAMPANIE BF` is direct evidence. Generic `CAMPANIE` values are treated
    cautiously because historic BF labels can remain attached to later sales.
    Calendar inference marks rows sold during known BF windows when direct
    campaign timing is absent.
    """
    campaign = clean_text(raw_campaign)
    bf = clean_text(raw_bf)
    parsed_date = _parse_iso_date(sale_date)
    sale_year = parsed_date.year if parsed_date else None
    campaign_has_bf = bool(campaign and BF_RE.search(campaign))
    bf_has_bf = bool(bf and BF_RE.search(bf))
    campaign_years = _campaign_years(campaign)
    bf_years = _campaign_years(bf)

    is_product_program = int(
        any(token in campaign.upper() for token in ("FABRO", "FABRICAT IN ROMANIA", "PATSPRING"))
    )
    campaign_signal_status = "observed" if campaign else "unknown"
    campaign_signal_source = "campaign_raw" if campaign else "unknown"

    if bf_has_bf:
        parsed_window = _parse_bf_window(bf, sale_year)
        if parsed_date and parsed_window is not None:
            start, end = parsed_window
            if start <= parsed_date <= end:
                return CampaignSignals(
                    is_bf_campaign=1,
                    is_bf_timing=1,
                    is_bf_observed=1,
                    is_bf_inferred=0,
                    is_product_program=is_product_program,
                    campaign_signal_status=campaign_signal_status,
                    campaign_signal_source=campaign_signal_source,
                    bf_signal_status="observed",
                    bf_signal_source="campaign_bf_raw",
                )
            return CampaignSignals(
                is_bf_campaign=1,
                is_bf_timing=0,
                is_bf_observed=0,
                is_bf_inferred=0,
                is_product_program=is_product_program,
                campaign_signal_status=campaign_signal_status,
                campaign_signal_source=campaign_signal_source,
                bf_signal_status="unknown",
                bf_signal_source="campaign_bf_outside_timing_window",
            )

        if parsed_date and sale_year is not None:
            start, end = _bf_window_for_year(sale_year)
            if start <= parsed_date <= end:
                return CampaignSignals(
                    is_bf_campaign=1,
                    is_bf_timing=1,
                    is_bf_observed=0,
                    is_bf_inferred=1,
                    is_product_program=is_product_program,
                    campaign_signal_status=campaign_signal_status,
                    campaign_signal_source=campaign_signal_source,
                    bf_signal_status="inferred",
                    bf_signal_source="campaign_bf_raw_calendar_window",
                )

        return CampaignSignals(
            is_bf_campaign=1,
            is_bf_timing=0,
            is_bf_observed=0,
            is_bf_inferred=0,
            is_product_program=is_product_program,
            campaign_signal_status=campaign_signal_status,
            campaign_signal_source=campaign_signal_source,
            bf_signal_status="unknown",
            bf_signal_source="campaign_bf_without_timing_evidence",
        )

    if parsed_date and sale_year is not None:
        start, end = _bf_window_for_year(sale_year)
        if start <= parsed_date <= end:
            source = "inferred_calendar_window"
            if campaign_has_bf and (not campaign_years or sale_year in campaign_years):
                source = "inferred_current_year_campaign_and_calendar"
            elif discount_pct is not None and discount_pct >= 0.10:
                source = "inferred_calendar_discount"
            return CampaignSignals(
                is_bf_campaign=int(campaign_has_bf),
                is_bf_timing=1,
                is_bf_observed=0,
                is_bf_inferred=1,
                is_product_program=is_product_program,
                campaign_signal_status=campaign_signal_status,
                campaign_signal_source=campaign_signal_source,
                bf_signal_status="inferred",
                bf_signal_source=source,
            )

    # Keep BF-like labels visible, but do not treat historic labels as current
    # BF timing when sale-date evidence is absent.
    is_current_year_bf_label = bool(
        campaign_has_bf and sale_year is not None and (not campaign_years or sale_year in campaign_years)
    )
    if is_current_year_bf_label:
        return CampaignSignals(
            is_bf_campaign=1,
            is_bf_timing=0,
            is_bf_observed=0,
            is_bf_inferred=0,
            is_product_program=is_product_program,
            campaign_signal_status=campaign_signal_status,
            campaign_signal_source=campaign_signal_source,
            bf_signal_status="unknown",
            bf_signal_source="campaign_label_without_timing_evidence",
        )

    return CampaignSignals(
        is_bf_campaign=int(campaign_has_bf or bool(bf_years)),
        is_bf_timing=0,
        is_bf_observed=0,
        is_bf_inferred=0,
        is_product_program=is_product_program,
        campaign_signal_status=campaign_signal_status,
        campaign_signal_source=campaign_signal_source,
        bf_signal_status="unknown",
        bf_signal_source="unknown",
    )
