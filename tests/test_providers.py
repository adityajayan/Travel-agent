"""Tests for mock providers — updated for M8 normalized schemas."""
import pytest

from providers.mock.flight_provider import MockFlightProvider
from providers.mock.hotel_provider import MockHotelProvider
from providers.mock.transport_provider import MockTransportProvider
from providers.mock.activity_provider import MockActivityProvider


@pytest.mark.asyncio
async def test_flight_search_returns_results():
    provider = MockFlightProvider()
    results = await provider.search_flights("JFK", "CDG", "2025-06-01", passengers=2)
    assert len(results) >= 1
    first = results[0]
    assert first["origin"] == "JFK"
    assert first["destination"] == "CDG"
    assert first["estimated_cost"] > 0
    assert "flight_id" in first
    # M8: Normalized schema fields
    assert "cabin_class" in first
    assert "duration_minutes" in first
    assert "provider" in first


@pytest.mark.asyncio
async def test_flight_booking_returns_confirmation():
    provider = MockFlightProvider()
    result = await provider.book_flight("FL001", {"name": "Alice"}, "mock-token")
    assert result["status"] == "confirmed"
    assert "booking_reference" in result
    assert result["domain"] == "flight"


@pytest.mark.asyncio
async def test_flight_cancel_returns_cancelled():
    provider = MockFlightProvider()
    result = await provider.cancel_flight("MOCK-FL001-BKG")
    assert result["status"] == "cancelled"
    assert result["booking_reference"] == "MOCK-FL001-BKG"


@pytest.mark.asyncio
async def test_hotel_search_returns_results():
    provider = MockHotelProvider()
    results = await provider.search_hotels("Paris", "2025-06-01", "2025-06-05", guests=2)
    assert len(results) >= 1
    first = results[0]
    assert first["destination"] == "Paris"
    assert first["cost_per_night"] > 0
    # M8: PolicyEngine-compatible fields
    assert "star_rating" in first


@pytest.mark.asyncio
async def test_hotel_booking_returns_confirmation():
    provider = MockHotelProvider()
    result = await provider.book_hotel("HTL001", {"name": "Bob"}, "mock-token")
    assert result["status"] == "confirmed"
    assert result["domain"] == "hotel"


@pytest.mark.asyncio
async def test_transport_search_returns_results():
    provider = MockTransportProvider()
    results = await provider.search_transport("CDG Airport", "Paris Centre", "2025-06-01")
    assert len(results) >= 1
    assert results[0]["pickup"] == "CDG Airport"
    assert results[0]["estimated_cost"] > 0


@pytest.mark.asyncio
async def test_transport_booking_returns_confirmation():
    provider = MockTransportProvider()
    result = await provider.book_transport("TRN001", {"name": "Carol"}, "mock-token")
    assert result["status"] == "confirmed"
    assert result["domain"] == "transport"


@pytest.mark.asyncio
async def test_activity_search_returns_results():
    provider = MockActivityProvider()
    results = await provider.search_activities("Paris", "2025-06-02", participants=1)
    assert len(results) >= 1
    assert "activity_id" in results[0]
    assert results[0]["estimated_cost"] > 0


@pytest.mark.asyncio
async def test_activity_booking_returns_confirmation():
    provider = MockActivityProvider()
    result = await provider.book_activity("ACT001", {"name": "Dave"}, "mock-token")
    assert result["status"] == "confirmed"
    assert result["domain"] == "activity"
