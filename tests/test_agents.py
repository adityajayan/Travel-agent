"""Tests for specialist agents (FlightAgent, HotelAgent, TransportAgent, ActivityAgent).

Claude is mocked so no real API calls are made.
"""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents.flight_agent import FlightAgent
from agents.hotel_agent import HotelAgent
from agents.transport_agent import TransportAgent
from agents.activity_agent import ActivityAgent
from core.approval_gate import ApprovalGate, ApprovalRequiredError
from core.audit_logger import AuditLogger
from db.models import HumanApproval


def _make_text_response(text: str):
    """Return a mock Anthropic response that ends with text."""
    block = MagicMock()
    block.type = "text"
    block.text = text
    response = MagicMock()
    response.stop_reason = "end_turn"
    response.content = [block]
    return response


def _make_tool_use_response(tool_name: str, tool_input: dict, tool_use_id: str = "tu_001"):
    """Return a mock Anthropic response that requests a tool call."""
    tool_block = MagicMock()
    tool_block.type = "tool_use"
    tool_block.id = tool_use_id
    tool_block.name = tool_name
    tool_block.input = tool_input

    response = MagicMock()
    response.stop_reason = "tool_use"
    response.content = [tool_block]
    return response


# ── FlightAgent ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_flight_agent_has_only_flight_tools(db, trip, audit_logger, approval_gate):
    agent = FlightAgent(trip.id, db, audit_logger, approval_gate)
    tool_names = agent.tool_registry.tool_names()
    assert set(tool_names) == {"search_flights", "book_flight", "cancel_flight"}
    # Must NOT have hotel / transport / activity tools
    assert "search_hotels" not in tool_names
    assert "search_transport" not in tool_names
    assert "search_activities" not in tool_names


@pytest.mark.asyncio
async def test_flight_agent_run_search_then_end(db, trip, audit_logger, approval_gate):
    """Agent calls search_flights, gets result, then Claude ends the turn."""
    search_response = _make_tool_use_response(
        "search_flights", {"origin": "JFK", "destination": "CDG", "date": "2025-06-01"}
    )
    final_response = _make_text_response("I found 2 flights for you.")

    mock_client = MagicMock()
    mock_client.messages = MagicMock()
    mock_client.messages.create = AsyncMock(side_effect=[search_response, final_response])

    agent = FlightAgent(trip.id, db, audit_logger, approval_gate)
    with patch.object(agent, "_client", mock_client):
        output = await agent.run("Find me a flight from JFK to CDG on 2025-06-01")

    assert "flight" in output.lower() or "found" in output.lower()
    # Tool call should be logged
    assert mock_client.messages.create.call_count == 2


@pytest.mark.asyncio
async def test_book_flight_without_approval_raises(db, trip, audit_logger, approval_gate):
    """Calling the book_flight tool handler directly must raise ApprovalRequiredError."""
    agent = FlightAgent(trip.id, db, audit_logger, approval_gate)
    with pytest.raises(ApprovalRequiredError):
        await agent._book_flight("FL001", "Alice", "mock-token")


@pytest.mark.asyncio
async def test_book_flight_with_approval_succeeds(db, trip, audit_logger, approval_gate):
    """book_flight proceeds (and logs a Booking) when approval is pre-approved."""
    # Insert approved record
    approval = HumanApproval(
        id=str(uuid.uuid4()),
        trip_id=trip.id,
        domain="flight",
        action="book_flight:FL001",
        details={},
        status="approved",
    )
    db.add(approval)
    await db.commit()

    agent = FlightAgent(trip.id, db, audit_logger, approval_gate)
    result = await agent._book_flight("FL001", "Alice", "mock-token")

    assert result["status"] == "confirmed"
    # Booking must be logged (total_spent updated)
    await db.refresh(trip)
    assert trip.total_spent > 0


@pytest.mark.asyncio
async def test_flight_agent_pending_approval_logged(db, trip, audit_logger, approval_gate):
    """When book_flight raises ApprovalRequiredError the agent logs it and keeps running."""
    book_response = _make_tool_use_response(
        "book_flight", {"flight_id": "FL001", "passenger_name": "Alice"}
    )
    final_response = _make_text_response("Awaiting your approval to book the flight.")

    mock_client = MagicMock()
    mock_client.messages = MagicMock()
    mock_client.messages.create = AsyncMock(side_effect=[book_response, final_response])

    agent = FlightAgent(trip.id, db, audit_logger, approval_gate)
    with patch.object(agent, "_client", mock_client):
        output = await agent.run("Book flight FL001 for Alice")

    assert agent._pending_approval_id is not None


# ── HotelAgent ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_hotel_agent_has_only_hotel_tools(db, trip, audit_logger, approval_gate):
    agent = HotelAgent(trip.id, db, audit_logger, approval_gate)
    tool_names = agent.tool_registry.tool_names()
    assert set(tool_names) == {"search_hotels", "book_hotel", "cancel_hotel"}
    assert "search_flights" not in tool_names


@pytest.mark.asyncio
async def test_book_hotel_without_approval_raises(db, trip, audit_logger, approval_gate):
    agent = HotelAgent(trip.id, db, audit_logger, approval_gate)
    with pytest.raises(ApprovalRequiredError):
        await agent._book_hotel("HTL001", "Bob", "mock-token")


@pytest.mark.asyncio
async def test_book_hotel_with_approval_succeeds(db, trip, audit_logger, approval_gate):
    approval = HumanApproval(
        id=str(uuid.uuid4()),
        trip_id=trip.id,
        domain="hotel",
        action="book_hotel:HTL001",
        details={},
        status="approved",
    )
    db.add(approval)
    await db.commit()

    agent = HotelAgent(trip.id, db, audit_logger, approval_gate)
    result = await agent._book_hotel("HTL001", "Bob", "mock-token")
    assert result["status"] == "confirmed"


# ── TransportAgent ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_transport_agent_has_only_transport_tools(db, trip, audit_logger, approval_gate):
    agent = TransportAgent(trip.id, db, audit_logger, approval_gate)
    tool_names = agent.tool_registry.tool_names()
    assert set(tool_names) == {"search_transport", "book_transport", "cancel_transport"}


@pytest.mark.asyncio
async def test_book_transport_without_approval_raises(db, trip, audit_logger, approval_gate):
    agent = TransportAgent(trip.id, db, audit_logger, approval_gate)
    with pytest.raises(ApprovalRequiredError):
        await agent._book_transport("TRN001", "Carol", "mock-token")


# ── ActivityAgent ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_activity_agent_has_only_activity_tools(db, trip, audit_logger, approval_gate):
    agent = ActivityAgent(trip.id, db, audit_logger, approval_gate)
    tool_names = agent.tool_registry.tool_names()
    assert set(tool_names) == {"search_activities", "book_activity", "cancel_activity"}


@pytest.mark.asyncio
async def test_book_activity_without_approval_raises(db, trip, audit_logger, approval_gate):
    agent = ActivityAgent(trip.id, db, audit_logger, approval_gate)
    with pytest.raises(ApprovalRequiredError):
        await agent._book_activity("ACT001", "Dave", "mock-token")
