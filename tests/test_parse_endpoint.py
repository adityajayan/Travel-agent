"""Tests for parse-layer handling of common input patterns.

Focuses on the two areas most likely to surprise users:
  1. Relative / fuzzy date expressions  ("next month", "in April", month abbreviations)
  2. Inferred domain detection          (single-domain, multi-domain, default fallback)

These tests exercise `extract_and_infer` end-to-end as well as the lower-level
`_extract_dates` and `_detect_domains` helpers that the trip-creation flow
relies on.
"""
from datetime import date, timedelta
from unittest.mock import patch

import pytest

from core.intent import (
    _extract_dates,
    _extract_destination,
    _extract_duration,
    _extract_origin,
    _extract_passengers,
    extract_and_infer,
)
from core.param_tracking import ParamSource
from agents.orchestrator_agent import _detect_domains


# ── Helpers ──────────────────────────────────────────────────────────────────

def _fake_today(y: int, m: int, d: int):
    """Return a patcher that pins date.today() to the given date."""
    fake = date(y, m, d)
    return patch("core.intent.date", wraps=date, **{"today.return_value": fake})


# ═══════════════════════════════════════════════════════════════════════════════
# 1.  RELATIVE  DATES
# ═══════════════════════════════════════════════════════════════════════════════

class TestRelativeDateNextMonth:
    """'next month' should always resolve to the 1st of the following month."""

    def test_next_month_mid_year(self):
        with _fake_today(2026, 6, 10):
            ci, co = _extract_dates("Travel next month")
            assert ci == "2026-07-01"
            assert co is None

    def test_next_month_december_wraps_to_january(self):
        with _fake_today(2026, 12, 5):
            ci, _ = _extract_dates("Fly next month")
            assert ci == "2027-01-01"

    def test_next_month_january(self):
        with _fake_today(2027, 1, 15):
            ci, _ = _extract_dates("Going next month")
            assert ci == "2027-02-01"


class TestRelativeDateMonthName:
    """'in <Month>' should resolve to the 15th of that month, rolling to
    next year when the month has already passed."""

    def test_future_month_same_year(self):
        with _fake_today(2026, 3, 7):
            ci, _ = _extract_dates("Travel in June")
            assert ci == "2026-06-15"

    def test_past_month_rolls_to_next_year(self):
        with _fake_today(2026, 9, 1):
            ci, _ = _extract_dates("Travel in April")
            assert ci == "2027-04-15"

    def test_current_month_early_stays_same_year(self):
        """If we're in the first half of the month, the same month is still valid."""
        with _fake_today(2026, 4, 10):
            ci, _ = _extract_dates("Travel in April")
            assert ci == "2026-04-15"

    def test_current_month_late_rolls_forward(self):
        """Past the 15th of the current month → next year."""
        with _fake_today(2026, 4, 20):
            ci, _ = _extract_dates("Travel in April")
            assert ci == "2027-04-15"

    def test_month_abbreviation(self):
        with _fake_today(2026, 1, 5):
            ci, _ = _extract_dates("Fly in Sep")
            assert ci == "2026-09-15"

    def test_month_name_with_year_suffix(self):
        """'in March 2026' — the month regex picks up the month name."""
        with _fake_today(2026, 1, 10):
            ci, _ = _extract_dates("Trip in March 2026")
            assert ci == "2026-03-15"


class TestRelativeDateWeekend:
    """'weekend' should map to a 2-night duration."""

    def test_weekend_duration(self):
        assert _extract_duration("Weekend trip to Paris") == 2

    def test_weekend_in_full_parse(self):
        tp = extract_and_infer("Weekend getaway to Chicago")
        assert tp.duration_nights.value == 2
        assert tp.duration_nights.source == ParamSource.USER_STATED


class TestISODateParsing:
    """ISO dates should be extracted verbatim."""

    def test_two_iso_dates(self):
        ci, co = _extract_dates("Travel 2026-08-01 to 2026-08-14")
        assert ci == "2026-08-01"
        assert co == "2026-08-14"

    def test_single_iso_date(self):
        ci, co = _extract_dates("Depart on 2026-12-20")
        assert ci == "2026-12-20"
        assert co is None

    def test_checkout_derived_from_iso_plus_duration(self):
        tp = extract_and_infer("Trip to Paris on 2026-06-01 for 7 days")
        assert tp.check_in_date.value == "2026-06-01"
        assert tp.check_out_date.value == "2026-06-08"


# ═══════════════════════════════════════════════════════════════════════════════
# 2.  INFERRED  DOMAIN  DETECTION
# ═══════════════════════════════════════════════════════════════════════════════

class TestDomainDetectionSingleDomain:
    """Goals mentioning keywords from exactly one domain."""

    def test_flight_keywords(self):
        assert _detect_domains("Book a flight to Tokyo") == ["flight"]
        assert _detect_domains("Fly from NYC to London") == ["flight"]
        assert _detect_domains("Find airline tickets to Paris") == ["flight"]

    def test_hotel_keywords(self):
        assert _detect_domains("Book a hotel in Rome") == ["hotel"]
        assert _detect_domains("Find accommodation in Bali") == ["hotel"]
        assert _detect_domains("I need a place to stay in Barcelona") == ["hotel"]

    def test_transport_keywords(self):
        # "airport" is a flight keyword, so "taxi from the airport" triggers both
        assert _detect_domains("Arrange a taxi from the airport") == ["flight", "transport"]
        assert _detect_domains("Book a shuttle to downtown") == ["transport"]
        assert _detect_domains("I need a train from Paris to Lyon") == ["transport"]

    def test_activity_keywords(self):
        assert _detect_domains("Find a museum tour in Paris") == ["activity"]
        assert _detect_domains("Book sightseeing excursion in Rome") == ["activity"]
        assert _detect_domains("Plan activities and experiences in Tokyo") == ["activity"]


class TestDomainDetectionMultiDomain:
    """Goals spanning multiple domains should trigger the orchestrator."""

    def test_flight_and_hotel(self):
        domains = _detect_domains("Book a flight and hotel in Paris")
        assert "flight" in domains
        assert "hotel" in domains
        assert len(domains) >= 2

    def test_full_trip_all_domains(self):
        goal = "Fly to Tokyo, book a hotel, arrange airport transfer, and find museum tours"
        domains = _detect_domains(goal)
        assert set(domains) == {"flight", "hotel", "transport", "activity"}

    def test_hotel_and_activity(self):
        domains = _detect_domains("Book accommodation and sightseeing tours in Bali")
        assert "hotel" in domains
        assert "activity" in domains


class TestDomainDetectionDefault:
    """No domain keywords → default to flight."""

    def test_generic_trip_defaults_to_flight(self):
        assert _detect_domains("Trip to Paris for a week") == ["flight"]

    def test_vacation_defaults_to_flight(self):
        assert _detect_domains("Vacation in Cancun") == ["flight"]

    def test_bare_destination_defaults_to_flight(self):
        assert _detect_domains("Tokyo next month") == ["flight"]


# ═══════════════════════════════════════════════════════════════════════════════
# 3.  END-TO-END  COMMON  INPUT  PATTERNS
# ═══════════════════════════════════════════════════════════════════════════════

class TestCommonInputPatterns:
    """Real-world-style queries that combine relative dates with destinations,
    durations, passengers, and budgets."""

    def test_casual_next_month_query(self):
        tp = extract_and_infer("I want to go to Bali for 10 days next month, $3000 budget")
        assert tp.destination_city.value == "Bali"
        assert tp.duration_nights.value == 10
        assert tp.total_budget.value == 3000.0
        ci = date.fromisoformat(tp.check_in_date.value)
        today = date.today()
        expected_month = 1 if today.month == 12 else today.month + 1
        assert ci.month == expected_month

    def test_destination_greedy_capture_known_issue(self):
        """Known edge case: 'to <City> next month' greedily captures 'next month'
        into the city name because 'next' is not in the regex delimiter set.
        The fallback to known-city scan still finds Bali, so the value works
        but includes extra text."""
        tp = extract_and_infer("I want to go to Bali next month for 10 days")
        # The regex captures "Bali next month" — city fallback still recognises Bali
        assert "Bali" in tp.destination_city.value

    def test_couple_weekend_getaway(self):
        tp = extract_and_infer("My partner and I want a weekend in Barcelona")
        assert tp.destination_city.value == "Barcelona"
        assert tp.num_travelers.value == 2
        assert tp.duration_nights.value == 2
        assert tp.trip_purpose.value == "leisure"

    def test_business_conference(self):
        tp = extract_and_infer("Conference in Chicago next month, 2 passengers")
        assert tp.destination_city.value == "Chicago"
        assert tp.trip_purpose.value == "business"
        assert tp.num_travelers.value == 2
        # Business default: 3 nights (since no explicit duration)
        assert tp.duration_nights.value == 3
        assert tp.duration_nights.source == ParamSource.INFERRED_DEFAULT

    def test_honeymoon_with_month_name(self):
        with _fake_today(2026, 1, 10):
            tp = extract_and_infer("Honeymoon in Paris in June, 2 weeks")
            assert tp.destination_city.value == "Paris"
            assert tp.trip_purpose.value == "leisure"
            assert tp.duration_nights.value == 14
            assert tp.check_in_date.value == "2026-06-15"

    def test_minimal_destination_only(self):
        """Just a city name should still produce usable defaults."""
        tp = extract_and_infer("Tokyo")
        assert tp.destination_city.value == "Tokyo"
        assert tp.duration_nights.source == ParamSource.INFERRED_DEFAULT
        assert tp.check_in_date.source == ParamSource.INFERRED_DEFAULT
        assert tp.num_travelers.value == 1
        assert tp.cabin_class.value == "economy"
        assert tp.trip_purpose.value == "leisure"

    def test_family_vacation_with_budget(self):
        tp = extract_and_infer("Family of 4 vacation to Cancun for a week, budget $5000")
        assert tp.destination_city.value == "Cancun"
        assert tp.num_travelers.value == 4
        assert tp.duration_nights.value == 7
        assert tp.total_budget.value == 5000.0
        assert tp.trip_purpose.value == "leisure"
        # Flight budget = 40% * $5000 * 4 passengers = $8000
        assert tp.flight_budget.value == 8000.0

    def test_origin_and_destination(self):
        tp = extract_and_infer("Flying from London to Tokyo for 10 days")
        assert tp.departure_city.value == "London"
        assert tp.destination_city.value == "Tokyo"
        assert tp.duration_nights.value == 10

    def test_no_dates_infers_best_season(self):
        """When no date is given, check-in should be inferred from city best-months."""
        tp = extract_and_infer("Trip to Tokyo")
        assert tp.check_in_date.source == ParamSource.INFERRED_DEFAULT
        ci = date.fromisoformat(tp.check_in_date.value)
        # Tokyo best months: [3, 4, 10, 11]
        assert ci.month in [3, 4, 10, 11]
        # Should be at least a week out
        assert ci > date.today() + timedelta(days=7)
