"""Tests for core/intent.py — intent extraction, smart defaults, and budget tiers."""
from datetime import date, timedelta
from unittest.mock import patch

import pytest

from core.intent import (
    BudgetTier,
    CITY_BUDGET_PROFILES,
    DEFAULT_PROFILE,
    _extract_budget,
    _extract_cabin_class,
    _extract_dates,
    _extract_destination,
    _extract_duration,
    _extract_origin,
    _extract_passengers,
    _get_city_profile,
    _infer_trip_purpose,
    _is_domestic,
    _next_best_month,
    extract_and_infer,
    generate_budget_tiers,
)
from core.param_tracking import ParamSource, TrackedParam, TrackedParams


# ── _extract_destination ─────────────────────────────────────────────────────

class TestExtractDestination:
    def test_known_city_tokyo(self):
        assert _extract_destination("I want to fly to Tokyo") == "Tokyo"

    def test_known_city_new_york(self):
        assert _extract_destination("Plan a trip to new york for me") == "New York"

    def test_known_city_san_francisco(self):
        assert _extract_destination("Visit San Francisco next month") == "San Francisco"

    def test_pattern_to_city(self):
        assert _extract_destination("Book me a flight to Paris") == "Paris"

    def test_pattern_in_city(self):
        result = _extract_destination("I want to stay in Barcelona for a week")
        assert result == "Barcelona"

    def test_no_destination(self):
        assert _extract_destination("I need a vacation") is None


# ── _extract_origin ──────────────────────────────────────────────────────────

class TestExtractOrigin:
    def test_from_city(self):
        assert _extract_origin("Flying from London to Paris") == "London"

    def test_departing_city(self):
        assert _extract_origin("Departing Chicago to NYC") == "Chicago"

    def test_no_origin(self):
        assert _extract_origin("Plan a trip to Tokyo") is None


# ── _extract_budget ──────────────────────────────────────────────────────────

class TestExtractBudget:
    def test_dollar_sign(self):
        assert _extract_budget("My budget is $5000") == 5000.0

    def test_dollar_with_comma(self):
        assert _extract_budget("Budget of $5,000") == 5000.0

    def test_under_amount(self):
        assert _extract_budget("Under $3000") == 3000.0

    def test_dollars_word(self):
        assert _extract_budget("2000 dollars for the trip") == 2000.0

    def test_no_budget(self):
        assert _extract_budget("Plan a trip to Paris") is None


# ── _extract_duration ────────────────────────────────────────────────────────

class TestExtractDuration:
    def test_days(self):
        assert _extract_duration("5 days in Paris") == 5

    def test_nights(self):
        assert _extract_duration("3 nights in Rome") == 3

    def test_week_number(self):
        assert _extract_duration("2 weeks in Bali") == 14

    def test_a_week(self):
        assert _extract_duration("Spend a week in Tokyo") == 7

    def test_weekend(self):
        assert _extract_duration("Weekend trip to Chicago") == 2

    def test_no_duration(self):
        assert _extract_duration("Trip to Paris") is None


# ── _extract_dates ───────────────────────────────────────────────────────────

class TestExtractDates:
    def test_iso_dates_pair(self):
        check_in, check_out = _extract_dates("Travel 2026-06-01 to 2026-06-10")
        assert check_in == "2026-06-01"
        assert check_out == "2026-06-10"

    def test_single_iso_date(self):
        check_in, check_out = _extract_dates("Departing 2026-07-15")
        assert check_in == "2026-07-15"
        assert check_out is None

    def test_next_month(self):
        check_in, check_out = _extract_dates("Travel next month")
        assert check_in is not None
        assert check_out is None
        # Should be the 1st of next month
        parsed = date.fromisoformat(check_in)
        today = date.today()
        if today.month == 12:
            assert parsed.month == 1
            assert parsed.year == today.year + 1
        else:
            assert parsed.month == today.month + 1

    def test_month_name(self):
        # "in April" should parse to a future April
        check_in, check_out = _extract_dates("Travel in April")
        assert check_in is not None
        parsed = date.fromisoformat(check_in)
        assert parsed.month == 4
        assert parsed.day == 15  # mid-month default

    def test_no_dates(self):
        check_in, check_out = _extract_dates("Trip to Paris")
        assert check_in is None
        assert check_out is None


# ── _extract_passengers ──────────────────────────────────────────────────────

class TestExtractPassengers:
    def test_number_passengers(self):
        assert _extract_passengers("2 passengers to Tokyo") == 2

    def test_couple(self):
        assert _extract_passengers("My partner and I want to visit Paris") == 2

    def test_family_of(self):
        assert _extract_passengers("Family of 4 to Cancun") == 4

    def test_no_passengers(self):
        assert _extract_passengers("Trip to Rome") is None


# ── _extract_cabin_class ─────────────────────────────────────────────────────

class TestExtractCabinClass:
    def test_business_class(self):
        assert _extract_cabin_class("Business class flight to London") == "business"

    def test_first_class(self):
        assert _extract_cabin_class("First class to Dubai") == "first"

    def test_economy(self):
        assert _extract_cabin_class("Economy flight to Paris") == "economy"

    def test_premium_economy(self):
        assert _extract_cabin_class("Premium economy to Tokyo") == "premium_economy"

    def test_no_class(self):
        assert _extract_cabin_class("Flight to Paris") is None

    def test_business_trip_not_business_class(self):
        # "business trip" should NOT match as business class
        result = _extract_cabin_class("Business trip to Chicago")
        assert result is None or result != "business"


# ── _infer_trip_purpose ──────────────────────────────────────────────────────

class TestInferTripPurpose:
    def test_business_keywords(self):
        assert _infer_trip_purpose("Business trip to NYC") == "business"
        assert _infer_trip_purpose("Conference in Chicago") == "business"

    def test_leisure_keywords(self):
        assert _infer_trip_purpose("Vacation in Bali") == "leisure"
        assert _infer_trip_purpose("Honeymoon in Paris") == "leisure"

    def test_no_purpose(self):
        assert _infer_trip_purpose("Trip to Rome") is None


# ── Utility functions ────────────────────────────────────────────────────────

class TestUtilities:
    def test_get_city_profile_known(self):
        profile = _get_city_profile("Tokyo")
        assert profile["country"] == "Japan"
        assert profile["flight_rt"] == 900

    def test_get_city_profile_unknown(self):
        profile = _get_city_profile("Timbuktu")
        assert profile == DEFAULT_PROFILE

    def test_get_city_profile_none(self):
        assert _get_city_profile(None) == DEFAULT_PROFILE

    def test_is_domestic_us_city(self):
        assert _is_domestic("New York") is True
        assert _is_domestic("Miami") is True

    def test_is_domestic_international(self):
        assert _is_domestic("Tokyo") is False
        assert _is_domestic("Paris") is False

    def test_is_domestic_none(self):
        assert _is_domestic(None) is False

    def test_next_best_month_returns_future_date(self):
        result = _next_best_month([3, 4, 10, 11])
        assert result > date.today()
        assert result.month in [3, 4, 10, 11]


# ── extract_and_infer (integration) ──────────────────────────────────────────

class TestExtractAndInfer:
    def test_full_request(self):
        """Fully specified request → all USER_STATED."""
        tp = extract_and_infer(
            "Flying from London to Tokyo on 2026-06-01 for 10 days, 2 passengers, business class, $5000 budget"
        )
        assert tp.destination_city.value == "Tokyo"
        assert tp.destination_city.source == ParamSource.USER_STATED
        assert tp.departure_city.value == "London"
        assert tp.departure_city.source == ParamSource.USER_STATED
        assert tp.duration_nights.value == 10
        assert tp.duration_nights.source == ParamSource.USER_STATED
        assert tp.num_travelers.value == 2
        assert tp.num_travelers.source == ParamSource.USER_STATED
        assert tp.cabin_class.value == "business"
        assert tp.cabin_class.source == ParamSource.USER_STATED
        assert tp.total_budget.value == 5000.0
        assert tp.total_budget.source == ParamSource.USER_STATED
        assert tp.check_in_date.value == "2026-06-01"
        assert tp.check_in_date.source == ParamSource.USER_STATED

    def test_minimal_request_infers_defaults(self):
        """Destination only → smart defaults for everything else."""
        tp = extract_and_infer("Trip to Paris")
        assert tp.destination_city.value == "Paris"
        assert tp.destination_city.source == ParamSource.USER_STATED

        # Inferred defaults
        assert tp.duration_nights.source == ParamSource.INFERRED_DEFAULT
        assert tp.duration_nights.value == 5  # Paris default_nights

        assert tp.num_travelers.source == ParamSource.INFERRED_DEFAULT
        assert tp.num_travelers.value == 1

        assert tp.cabin_class.source == ParamSource.INFERRED_DEFAULT
        assert tp.cabin_class.value == "economy"

        assert tp.check_in_date.source == ParamSource.INFERRED_DEFAULT
        assert tp.check_in_date.value is not None

        assert tp.trip_purpose.source == ParamSource.INFERRED_DEFAULT
        assert tp.trip_purpose.value == "leisure"

        # No budget → total_budget should be None
        assert tp.total_budget is None

    def test_business_trip_defaults(self):
        """Business trip triggers shorter duration and sooner dates."""
        tp = extract_and_infer("Business trip to Chicago")
        assert tp.trip_purpose.value == "business"
        assert tp.duration_nights.value == 3  # business default

    def test_domestic_trip_defaults(self):
        """US city → domestic defaults."""
        tp = extract_and_infer("Vacation to Miami")
        assert tp.duration_nights.value == 4  # domestic leisure default

    def test_user_budget_passthrough(self):
        """user_budget parameter works when goal has no $ amount."""
        tp = extract_and_infer("Trip to Tokyo", user_budget=3000.0)
        assert tp.total_budget.value == 3000.0
        assert tp.flight_budget is not None
        assert tp.hotel_budget is not None
        # 40% of 3000 * 1 passenger = 1200
        assert tp.flight_budget.value == 1200.0
        # 50% of 3000 = 1500
        assert tp.hotel_budget.value == 1500.0

    def test_checkout_derived_from_checkin_and_duration(self):
        """check_out_date = check_in_date + duration_nights."""
        tp = extract_and_infer("Trip to Paris on 2026-06-01 for 5 days")
        assert tp.check_out_date.value == "2026-06-06"
        assert tp.check_out_date.source == ParamSource.INFERRED_DEFAULT

    def test_to_context_dict_three_sections(self):
        """to_context_dict returns user_stated, system_inferred, missing_params."""
        tp = extract_and_infer("Trip to Tokyo")
        ctx = tp.to_context_dict()
        assert "user_stated" in ctx
        assert "system_inferred" in ctx
        assert "missing_params" in ctx
        assert "destination_city" in ctx["user_stated"]


# ── TrackedParam provenance ──────────────────────────────────────────────────

class TestTrackedParamProvenance:
    def test_stated_params_only_returns_stated(self):
        tp = TrackedParams(
            destination_city=TrackedParam("Tokyo", ParamSource.USER_STATED),
            cabin_class=TrackedParam("economy", ParamSource.INFERRED_DEFAULT, reason="default"),
        )
        stated = tp.stated_params()
        assert "destination_city" in stated
        assert "cabin_class" not in stated

    def test_inferred_params_only_returns_inferred(self):
        tp = TrackedParams(
            destination_city=TrackedParam("Tokyo", ParamSource.USER_STATED),
            cabin_class=TrackedParam("economy", ParamSource.INFERRED_DEFAULT, confidence=0.7, reason="default"),
        )
        inferred = tp.inferred_params()
        assert "cabin_class" in inferred
        assert "destination_city" not in inferred
        assert inferred["cabin_class"]["confidence"] == 0.7

    def test_missing_params_returns_none_fields(self):
        tp = TrackedParams(
            destination_city=TrackedParam("Tokyo", ParamSource.USER_STATED),
        )
        missing = tp.missing_params()
        assert "departure_city" in missing
        assert "destination_city" not in missing

    def test_to_flat_dict(self):
        tp = TrackedParams(
            destination_city=TrackedParam("Tokyo", ParamSource.USER_STATED),
            cabin_class=TrackedParam("economy", ParamSource.INFERRED_DEFAULT),
        )
        flat = tp.to_flat_dict()
        assert flat["destination_city"] == "Tokyo"
        assert flat["cabin_class"] == "economy"

    def test_tracked_param_to_dict(self):
        param = TrackedParam("Paris", ParamSource.USER_STATED, confidence=1.0, reason="stated")
        d = param.to_dict()
        assert d["value"] == "Paris"
        assert d["source"] == "user_stated"
        assert d["confidence"] == 1.0


# ── generate_budget_tiers ────────────────────────────────────────────────────

class TestBudgetTiers:
    def test_returns_three_tiers(self):
        tiers = generate_budget_tiers("Tokyo", 5, 1)
        assert len(tiers) == 3
        assert tiers[0].name == "budget"
        assert tiers[1].name == "comfortable"
        assert tiers[2].name == "premium"

    def test_budget_is_cheapest(self):
        tiers = generate_budget_tiers("Paris", 5, 1)
        assert tiers[0].estimated_total < tiers[1].estimated_total
        assert tiers[1].estimated_total < tiers[2].estimated_total

    def test_uses_city_profile(self):
        tiers = generate_budget_tiers("Tokyo", 5, 1)
        # Tokyo has flight_rt=900, hotel_night=180
        # Budget: 0.6 * 900 = 540 flight, 0.6 * 180 = 108 hotel
        assert tiers[0].estimated_flight_cost == 540.0
        assert tiers[0].estimated_hotel_per_night == 108

    def test_unknown_city_uses_default(self):
        tiers = generate_budget_tiers("Timbuktu", 5, 1)
        assert len(tiers) == 3
        # Should use DEFAULT_PROFILE flight_rt=600
        assert tiers[1].estimated_flight_cost == 600.0  # comfortable = median

    def test_multiple_passengers_scales_flights(self):
        tiers_1 = generate_budget_tiers("Paris", 5, 1)
        tiers_2 = generate_budget_tiers("Paris", 5, 2)
        # Flight cost doubles, hotel cost stays same
        assert tiers_2[1].estimated_flight_cost == tiers_1[1].estimated_flight_cost * 2
        assert tiers_2[1].estimated_hotel_per_night == tiers_1[1].estimated_hotel_per_night

    def test_longer_duration_increases_total(self):
        tiers_5 = generate_budget_tiers("Paris", 5, 1)
        tiers_10 = generate_budget_tiers("Paris", 10, 1)
        assert tiers_10[1].estimated_total > tiers_5[1].estimated_total
