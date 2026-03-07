"""Tests for M8 multi-provider fallback (INV-15).

Simulates primary provider failure and verifies fallback executes correctly.
"""
import pytest

from providers.cache import ProviderCache
from providers.fallback import FallbackProvider, AllProvidersFailedError
from providers.mock.flight_provider import MockFlightProvider
from providers.mock.hotel_provider import MockHotelProvider


class FailingFlightProvider(MockFlightProvider):
    """A mock flight provider that always fails on search."""

    async def search_flights(self, origin, destination, date, passengers=1):
        raise RuntimeError("Primary provider unavailable")


class FailingHotelProvider(MockHotelProvider):
    """A mock hotel provider that always fails on search."""

    async def search_hotels(self, destination, check_in, check_out, guests=1):
        raise ConnectionError("Hotel API timeout")


@pytest.mark.asyncio
async def test_fallback_uses_primary_when_available():
    """Primary provider succeeds — no fallback needed."""
    primary = MockFlightProvider()
    fallback_provider = MockFlightProvider()
    cache = ProviderCache()  # No Redis — no-op cache

    fb = FallbackProvider(
        providers=[primary, fallback_provider],
        cache=cache,
        domain="flight",
    )

    results = await fb.search(
        origin="JFK", destination="CDG", date="2025-06-01", passengers=1
    )
    assert len(results) >= 1
    assert results[0]["flight_id"] == "FL001"


@pytest.mark.asyncio
async def test_fallback_switches_to_secondary_on_primary_failure():
    """Primary fails — fallback provider serves the request."""
    primary = FailingFlightProvider()
    secondary = MockFlightProvider()
    cache = ProviderCache()

    fb = FallbackProvider(
        providers=[primary, secondary],
        cache=cache,
        domain="flight",
    )

    results = await fb.search(
        origin="JFK", destination="CDG", date="2025-06-01", passengers=1
    )
    assert len(results) >= 1
    assert results[0]["flight_id"] == "FL001"


@pytest.mark.asyncio
async def test_all_providers_fail_raises_error():
    """All providers fail — raises AllProvidersFailedError."""
    primary = FailingFlightProvider()
    secondary = FailingFlightProvider()
    cache = ProviderCache()

    fb = FallbackProvider(
        providers=[primary, secondary],
        cache=cache,
        domain="flight",
    )

    with pytest.raises(AllProvidersFailedError) as exc_info:
        await fb.search(
            origin="JFK", destination="CDG", date="2025-06-01", passengers=1
        )
    assert exc_info.value.domain == "flight"
    assert len(exc_info.value.errors) == 2


@pytest.mark.asyncio
async def test_fallback_hotel_secondary():
    """Hotel fallback works when primary fails."""
    primary = FailingHotelProvider()
    secondary = MockHotelProvider()
    cache = ProviderCache()

    fb = FallbackProvider(
        providers=[primary, secondary],
        cache=cache,
        domain="hotel",
    )

    results = await fb.search(
        destination="Paris", check_in="2025-06-01", check_out="2025-06-05", guests=1
    )
    assert len(results) >= 1
    assert results[0]["hotel_id"] == "HTL001"


@pytest.mark.asyncio
async def test_fallback_delegates_book_to_primary():
    """Book always uses primary provider (no fallback for bookings)."""
    primary = MockFlightProvider()
    secondary = MockFlightProvider()
    cache = ProviderCache()

    fb = FallbackProvider(
        providers=[primary, secondary],
        cache=cache,
        domain="flight",
    )

    result = await fb.book("FL001", {"name": "Alice"}, "mock-token")
    assert result["status"] == "confirmed"


@pytest.mark.asyncio
async def test_fallback_delegates_cancel_to_primary():
    """Cancel always uses primary provider."""
    primary = MockFlightProvider()
    cache = ProviderCache()

    fb = FallbackProvider(
        providers=[primary],
        cache=cache,
        domain="flight",
    )

    result = await fb.cancel("MOCK-FL001-BKG")
    assert result["status"] == "cancelled"


@pytest.mark.asyncio
async def test_fallback_delegates_verify_price():
    """verify_price delegates to primary provider."""
    primary = MockFlightProvider()
    cache = ProviderCache()

    fb = FallbackProvider(
        providers=[primary],
        cache=cache,
        domain="flight",
    )

    result = await fb.verify_price("FL001", 299.99)
    assert result.price_changed is False
    assert result.current_price == 299.99


@pytest.mark.asyncio
async def test_fallback_delegates_get_cancellation_policy():
    """get_cancellation_policy delegates to primary provider."""
    primary = MockFlightProvider()
    cache = ProviderCache()

    fb = FallbackProvider(
        providers=[primary],
        cache=cache,
        domain="flight",
    )

    result = await fb.get_cancellation_policy("MOCK-FL001-BKG")
    assert result.refundable is True


@pytest.mark.asyncio
async def test_fallback_getattr_delegates_domain_methods():
    """Domain-specific methods like search_flights delegate via __getattr__."""
    primary = MockFlightProvider()
    cache = ProviderCache()

    fb = FallbackProvider(
        providers=[primary],
        cache=cache,
        domain="flight",
    )

    results = await fb.search_flights("JFK", "CDG", "2025-06-01")
    assert len(results) >= 1
