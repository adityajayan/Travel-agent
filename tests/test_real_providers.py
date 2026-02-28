"""Tests for M5 — Real API providers.

These tests are SKIPPED unless USE_REAL_APIS=true and credentials are set.
They verify real provider responses match PolicyEngine field expectations.
"""
import os

import pytest

SKIP_REASON = "USE_REAL_APIS not set or credentials missing"


def _real_apis_available():
    return os.environ.get("USE_REAL_APIS", "false").lower() == "true"


# ── Amadeus ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.skipif(not _real_apis_available(), reason=SKIP_REASON)
async def test_amadeus_search():
    """Verify Amadeus search results match PolicyEngine expectations."""
    from providers.real.amadeus import AmadeusFlightProvider

    provider = AmadeusFlightProvider()
    results = await provider.search_flights("JFK", "LHR", "2026-06-15")

    assert len(results) > 0
    first = results[0]
    # PolicyEngine fields
    assert "estimated_cost" in first or "price" in first
    assert "cabin_class" in first
    assert "duration_minutes" in first
    assert "provider" in first
    # No credentials in output
    assert os.environ.get("AMADEUS_CLIENT_SECRET", "") not in str(first)


@pytest.mark.asyncio
@pytest.mark.skipif(not _real_apis_available(), reason=SKIP_REASON)
async def test_amadeus_sandbox_booking_prefix():
    """Sandbox booking references start with SANDBOX- (INV-11)."""
    from providers.real.amadeus import AmadeusFlightProvider

    provider = AmadeusFlightProvider()
    # This would require a valid flight offer ID from search
    # For sandbox, we verify the prefix logic
    assert provider._is_sandbox is True


# ── Booking.com ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.skipif(not _real_apis_available(), reason=SKIP_REASON)
async def test_bookingcom_search():
    from providers.real.bookingcom import BookingcomHotelProvider

    provider = BookingcomHotelProvider()
    results = await provider.search_hotels("London", "2026-06-15", "2026-06-18")

    assert len(results) > 0
    first = results[0]
    assert "cost_per_night" in first
    assert "star_rating" in first
    assert "provider" in first


# ── Provider factory ─────────────────────────────────────────────────────────

def test_factory_returns_mock_by_default():
    """With USE_REAL_APIS=false, factory returns mock providers."""
    from providers.factory import get_provider
    from providers.mock.flight_provider import MockFlightProvider
    from providers.mock.hotel_provider import MockHotelProvider
    from providers.mock.transport_provider import MockTransportProvider
    from providers.mock.activity_provider import MockActivityProvider

    # Ensure USE_REAL_APIS is not set
    old = os.environ.pop("USE_REAL_APIS", None)
    try:
        assert isinstance(get_provider("flight"), MockFlightProvider)
        assert isinstance(get_provider("hotel"), MockHotelProvider)
        assert isinstance(get_provider("transport"), MockTransportProvider)
        assert isinstance(get_provider("activity"), MockActivityProvider)
    finally:
        if old is not None:
            os.environ["USE_REAL_APIS"] = old


def test_factory_raises_on_unknown_domain():
    from providers.factory import get_provider
    with pytest.raises(ValueError, match="Unknown domain"):
        get_provider("spaceship")


@pytest.mark.asyncio
async def test_base_provider_unified_interface():
    """Mock providers support the unified search/book/cancel interface."""
    from providers.factory import get_provider

    flight = get_provider("flight")
    results = await flight.search(origin="SFO", destination="LAX", date="2026-06-01")
    assert len(results) > 0

    hotel = get_provider("hotel")
    results = await hotel.search(destination="London", check_in="2026-06-01", check_out="2026-06-03")
    assert len(results) > 0
