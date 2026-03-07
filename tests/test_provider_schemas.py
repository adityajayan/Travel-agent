"""Tests for M8 normalized provider schemas (INV-14).

Validates that all providers (mock and real) return correct Pydantic models
and that the model_dump() output contains PolicyEngine-compatible field names.
"""
import pytest

from providers.mock.flight_provider import MockFlightProvider
from providers.mock.hotel_provider import MockHotelProvider
from providers.mock.transport_provider import MockTransportProvider
from providers.mock.activity_provider import MockActivityProvider
from providers.schemas import (
    NormalizedFlightResult,
    NormalizedHotelResult,
    NormalizedTransportResult,
    NormalizedActivityResult,
    NormalizedBookingConfirmation,
    PriceVerification,
    HoldResult,
    CancellationPolicy,
)


# ── Flight Schema Tests ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_flight_search_returns_normalized_schema():
    provider = MockFlightProvider()
    results = await provider.search_flights("JFK", "CDG", "2025-06-01", passengers=1)
    assert len(results) >= 1

    first = results[0]
    # Validate it can be parsed back into the Pydantic model
    model = NormalizedFlightResult(**first)
    assert model.flight_id == "FL001"
    assert model.origin == "JFK"
    assert model.destination == "CDG"
    assert model.estimated_cost > 0
    assert model.cabin_class == "economy"
    assert model.duration_minutes > 0
    assert model.provider != ""


@pytest.mark.asyncio
async def test_flight_search_contains_policy_engine_fields():
    """PolicyEngine expects 'estimated_cost', 'cabin_class', 'duration_minutes'."""
    provider = MockFlightProvider()
    results = await provider.search_flights("JFK", "CDG", "2025-06-01")
    first = results[0]
    assert "estimated_cost" in first
    assert "cabin_class" in first
    assert "duration_minutes" in first


@pytest.mark.asyncio
async def test_flight_booking_returns_normalized_confirmation():
    provider = MockFlightProvider()
    result = await provider.book_flight("FL001", {"name": "Test"}, "tok")
    model = NormalizedBookingConfirmation(**result)
    assert model.booking_reference.startswith("MOCK-")
    assert model.domain == "flight"
    assert model.status == "confirmed"
    assert model.amount > 0


# ── Hotel Schema Tests ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_hotel_search_returns_normalized_schema():
    provider = MockHotelProvider()
    results = await provider.search_hotels("Paris", "2025-06-01", "2025-06-05")
    assert len(results) >= 1

    first = results[0]
    model = NormalizedHotelResult(**first)
    assert model.hotel_id == "HTL001"
    assert model.cost_per_night > 0
    assert model.star_rating > 0
    assert model.provider != ""


@pytest.mark.asyncio
async def test_hotel_search_contains_policy_engine_fields():
    """PolicyEngine expects 'cost_per_night', 'star_rating'."""
    provider = MockHotelProvider()
    results = await provider.search_hotels("Paris", "2025-06-01", "2025-06-05")
    first = results[0]
    assert "cost_per_night" in first
    assert "star_rating" in first


@pytest.mark.asyncio
async def test_hotel_booking_returns_normalized_confirmation():
    provider = MockHotelProvider()
    result = await provider.book_hotel("HTL001", {"name": "Test"}, "tok")
    model = NormalizedBookingConfirmation(**result)
    assert model.domain == "hotel"
    assert model.status == "confirmed"


# ── Transport Schema Tests ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_transport_search_returns_normalized_schema():
    provider = MockTransportProvider()
    results = await provider.search_transport("Airport", "City", "2025-06-01")
    assert len(results) >= 1

    first = results[0]
    model = NormalizedTransportResult(**first)
    assert model.transport_id == "TRN001"
    assert model.estimated_cost > 0
    assert model.provider != ""


@pytest.mark.asyncio
async def test_transport_search_contains_policy_engine_fields():
    """PolicyEngine expects 'estimated_cost'."""
    provider = MockTransportProvider()
    results = await provider.search_transport("A", "B", "2025-06-01")
    first = results[0]
    assert "estimated_cost" in first


@pytest.mark.asyncio
async def test_transport_booking_returns_normalized_confirmation():
    provider = MockTransportProvider()
    result = await provider.book_transport("TRN001", {"name": "Test"}, "tok")
    model = NormalizedBookingConfirmation(**result)
    assert model.domain == "transport"
    assert model.status == "confirmed"


# ── Activity Schema Tests ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_activity_search_returns_normalized_schema():
    provider = MockActivityProvider()
    results = await provider.search_activities("Paris", "2025-06-01")
    assert len(results) >= 1

    first = results[0]
    model = NormalizedActivityResult(**first)
    assert model.activity_id == "ACT001"
    assert model.estimated_cost > 0
    assert model.provider != ""


@pytest.mark.asyncio
async def test_activity_search_contains_policy_engine_fields():
    """PolicyEngine expects 'estimated_cost'."""
    provider = MockActivityProvider()
    results = await provider.search_activities("Paris", "2025-06-01")
    first = results[0]
    assert "estimated_cost" in first


@pytest.mark.asyncio
async def test_activity_booking_returns_normalized_confirmation():
    provider = MockActivityProvider()
    result = await provider.book_activity("ACT001", {"name": "Test"}, "tok")
    model = NormalizedBookingConfirmation(**result)
    assert model.domain == "activity"
    assert model.status == "confirmed"


# ── Schema Validation Tests ───────────────────────────────────────────────────

def test_price_verification_model():
    from datetime import datetime, timezone
    pv = PriceVerification(
        item_id="FL001",
        current_price=300.00,
        original_price=290.00,
        price_changed=True,
        pct_change=3.45,
        verified_at=datetime.now(timezone.utc),
    )
    d = pv.model_dump()
    assert d["price_changed"] is True
    assert d["pct_change"] == 3.45


def test_hold_result_model():
    from datetime import datetime, timezone
    hr = HoldResult(
        hold_id="HOLD-123",
        item_id="FL001",
        verified_price=500.0,
        expires_at=datetime.now(timezone.utc),
        provider="Amadeus",
        supported=True,
    )
    assert hr.supported is True
    assert hr.hold_id == "HOLD-123"


def test_cancellation_policy_model():
    cp = CancellationPolicy(
        booking_reference="BKG-001",
        refundable=True,
        refund_amount=250.0,
        cancellation_fee=25.0,
        policy_text="Refundable minus fee",
        provider="TestProvider",
    )
    assert cp.refundable is True
    assert cp.refund_amount == 250.0


def test_unsupported_hold_result():
    from datetime import datetime, timezone
    hr = HoldResult(
        item_id="FL001",
        expires_at=datetime.now(timezone.utc),
        supported=False,
    )
    assert hr.supported is False
    assert hr.hold_id == ""


# ── verify_price / get_cancellation_policy on mock providers ──────────────────

@pytest.mark.asyncio
async def test_mock_flight_verify_price():
    provider = MockFlightProvider()
    result = await provider.verify_price("FL001", 299.99)
    assert isinstance(result, PriceVerification)
    assert result.price_changed is False
    assert result.current_price == 299.99


@pytest.mark.asyncio
async def test_mock_hotel_get_cancellation_policy():
    provider = MockHotelProvider()
    result = await provider.get_cancellation_policy("MOCK-HTL001-BKG")
    assert isinstance(result, CancellationPolicy)
    assert result.refundable is True


@pytest.mark.asyncio
async def test_mock_transport_verify_price():
    provider = MockTransportProvider()
    result = await provider.verify_price("TRN001", 45.00)
    assert isinstance(result, PriceVerification)
    assert result.price_changed is False


@pytest.mark.asyncio
async def test_mock_activity_get_cancellation_policy():
    provider = MockActivityProvider()
    result = await provider.get_cancellation_policy("MOCK-ACT001-BKG")
    assert isinstance(result, CancellationPolicy)
    assert result.refundable is True
