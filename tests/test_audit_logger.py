"""Tests for AuditLogger – append-only invariant and total_spent tracking."""
import pytest
from sqlalchemy import func, select

from core.audit_logger import AuditLogger
from db.models import Booking, ToolCall, Trip


@pytest.mark.asyncio
async def test_log_tool_call_creates_record(db, trip):
    logger = AuditLogger(db)
    record = await logger.log_tool_call(
        trip.id, "FlightAgent", "search_flights",
        {"origin": "JFK", "destination": "CDG"},
        {"results": [{"flight_id": "FL001"}]},
    )
    assert record.id
    assert record.tool_name == "search_flights"
    assert record.agent_name == "FlightAgent"


@pytest.mark.asyncio
async def test_log_tool_call_is_append_only(db, trip):
    """Logging the same tool twice creates two separate records, never updates."""
    logger = AuditLogger(db)
    r1 = await logger.log_tool_call(trip.id, "FlightAgent", "search_flights", {}, {})
    r2 = await logger.log_tool_call(trip.id, "FlightAgent", "search_flights", {}, {})

    assert r1.id != r2.id  # different records

    result = await db.execute(
        select(func.count()).select_from(ToolCall).where(ToolCall.trip_id == trip.id)
    )
    count = result.scalar_one()
    assert count == 2


@pytest.mark.asyncio
async def test_log_booking_creates_record(db, trip):
    logger = AuditLogger(db)
    booking = await logger.log_booking(
        trip.id, "flight", "mock",
        {"booking_reference": "MOCK-FL001-BKG"},
        299.99,
    )
    assert booking.id
    assert booking.domain == "flight"
    assert booking.amount == 299.99


@pytest.mark.asyncio
async def test_log_booking_increments_total_spent(db, trip):
    logger = AuditLogger(db)

    await logger.log_booking(trip.id, "flight", "mock", {}, 299.99)
    await logger.log_booking(trip.id, "hotel", "mock", {}, 150.00)

    await db.refresh(trip)
    assert abs(trip.total_spent - 449.99) < 0.01


@pytest.mark.asyncio
async def test_log_booking_append_only(db, trip):
    """Two bookings → two rows, neither overwrites the other."""
    logger = AuditLogger(db)
    b1 = await logger.log_booking(trip.id, "flight", "mock", {"ref": "A"}, 100.0)
    b2 = await logger.log_booking(trip.id, "hotel", "mock", {"ref": "B"}, 200.0)

    assert b1.id != b2.id

    result = await db.execute(
        select(func.count()).select_from(Booking).where(Booking.trip_id == trip.id)
    )
    assert result.scalar_one() == 2
