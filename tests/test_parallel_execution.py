"""Tests for M4 Item 2 — Parallel Sub-Task Execution in OrchestratorAgent."""
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents.orchestrator_agent import OrchestratorAgent
from agents.trip_state import BookingRecord, TripState
from core.approval_gate import ApprovalGate
from core.audit_logger import AuditLogger


def _text_response(text: str):
    block = MagicMock()
    block.type = "text"
    block.text = text
    resp = MagicMock()
    resp.stop_reason = "end_turn"
    resp.content = [block]
    return resp


# ── Parallel happy path ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_parallel_happy_path_3_sub_agents(db, trip, audit_logger, approval_gate):
    """3 sub-agents (hotel, transport, activity) complete concurrently after flight."""
    plan = {
        "tasks": [
            {"domain": "flight", "goal": "Book flight to Paris"},
            {"domain": "hotel", "goal": "Book hotel in Paris"},
            {"domain": "transport", "goal": "Book taxi in Paris"},
            {"domain": "activity", "goal": "Book tour in Paris"},
        ],
        "required": ["flight"],
        "optional": ["hotel", "transport", "activity"],
    }
    decompose_resp = _text_response(json.dumps(plan))
    synth_resp = _text_response("All booked!")

    mock_client = MagicMock()
    mock_client.messages = MagicMock()
    mock_client.messages.create = AsyncMock(
        side_effect=[decompose_resp, synth_resp]
    )

    async def mock_run_sub(domain, sub_goal):
        return f"{domain} done."

    agent = OrchestratorAgent(trip.id, db, audit_logger, approval_gate)
    with patch.object(agent, "_client", mock_client):
        with patch.object(agent, "_run_sub_agent", side_effect=mock_run_sub):
            summary = await agent.run("Book flight, hotel, taxi and tour in Paris")

    assert summary == "All booked!"
    state = agent._state
    assert len(state.sub_results) == 4
    assert all(r.status == "success" for r in state.sub_results)


# ── One optional task fails, others complete ─────────────────────────────────

@pytest.mark.asyncio
async def test_optional_task_fails_others_complete(db, trip, audit_logger, approval_gate):
    """One optional sub-agent fails, the others complete successfully."""
    plan = {
        "tasks": [
            {"domain": "flight", "goal": "Book flight"},
            {"domain": "hotel", "goal": "Book hotel"},
            {"domain": "activity", "goal": "Book tour"},
        ],
        "required": ["flight"],
        "optional": ["hotel", "activity"],
    }
    decompose_resp = _text_response(json.dumps(plan))
    sub_resp_ok = _text_response("Done.")
    synth_resp = _text_response("Partially booked.")

    call_count = 0

    async def mock_run_sub_agent(domain, sub_goal):
        nonlocal call_count
        call_count += 1
        if domain == "activity":
            raise RuntimeError("Activity provider down")
        return "Done."

    mock_client = MagicMock()
    mock_client.messages = MagicMock()
    mock_client.messages.create = AsyncMock(
        side_effect=[decompose_resp, sub_resp_ok, synth_resp]
    )

    agent = OrchestratorAgent(trip.id, db, audit_logger, approval_gate)
    with patch.object(agent, "_client", mock_client):
        with patch.object(agent, "_run_sub_agent", side_effect=mock_run_sub_agent):
            summary = await agent.run("Flight, hotel and tour")

    state = agent._state
    # Flight: success, Hotel: success, Activity: skipped (after 2 attempts)
    flight_results = [r for r in state.sub_results if r.domain == "flight"]
    hotel_results = [r for r in state.sub_results if r.domain == "hotel"]
    activity_results = [r for r in state.sub_results if r.domain == "activity"]

    assert len(flight_results) == 1 and flight_results[0].status == "success"
    assert len(hotel_results) == 1 and hotel_results[0].status == "success"
    assert len(activity_results) == 1 and activity_results[0].status == "skipped"


# ── Required task fails → trip marked failed ─────────────────────────────────

@pytest.mark.asyncio
async def test_required_task_fails_trip_marked_failed(db, trip, audit_logger, approval_gate):
    """Required flight task fails → trip marked failed."""
    plan = {
        "tasks": [
            {"domain": "flight", "goal": "Book flight"},
            {"domain": "hotel", "goal": "Book hotel"},
        ],
        "required": ["flight", "hotel"],
        "optional": [],
    }
    decompose_resp = _text_response(json.dumps(plan))

    async def mock_run_sub_agent(domain, sub_goal):
        if domain == "flight":
            raise RuntimeError("Flight booking failed")
        return "Done."

    mock_client = MagicMock()
    mock_client.messages = MagicMock()
    mock_client.messages.create = AsyncMock(
        side_effect=[decompose_resp]
    )

    agent = OrchestratorAgent(trip.id, db, audit_logger, approval_gate)
    with patch.object(agent, "_client", mock_client):
        with patch.object(agent, "_run_sub_agent", side_effect=mock_run_sub_agent):
            with pytest.raises(RuntimeError, match="Flight booking failed"):
                await agent.run("Flight and hotel")

    # Verify trip is marked failed
    from sqlalchemy import select
    from db.models import Trip
    result = await db.execute(select(Trip).where(Trip.id == trip.id))
    t = result.scalar_one()
    assert t.status == "failed"


# ── Sequential dependency: flight before hotel ───────────────────────────────

@pytest.mark.asyncio
async def test_sequential_dependency_flight_before_hotel(db, trip, audit_logger, approval_gate):
    """Flight completes before hotel starts (hotel is in parallel tier)."""
    plan = {
        "tasks": [
            {"domain": "flight", "goal": "Book flight"},
            {"domain": "hotel", "goal": "Book hotel"},
        ],
        "required": ["flight"],
        "optional": ["hotel"],
    }
    decompose_resp = _text_response(json.dumps(plan))
    sub_resp = _text_response("Done.")
    synth_resp = _text_response("All done!")

    execution_order = []

    original_run_sub_agent = OrchestratorAgent._run_sub_agent

    async def mock_run_sub_agent(self_agent, domain, sub_goal):
        execution_order.append(("start", domain))
        await asyncio.sleep(0.01)  # small delay to observe ordering
        execution_order.append(("end", domain))
        return "Done."

    mock_client = MagicMock()
    mock_client.messages = MagicMock()
    mock_client.messages.create = AsyncMock(
        side_effect=[decompose_resp, synth_resp]
    )

    agent = OrchestratorAgent(trip.id, db, audit_logger, approval_gate)
    with patch.object(agent, "_client", mock_client):
        with patch.object(OrchestratorAgent, "_run_sub_agent", mock_run_sub_agent):
            await agent.run("Flight and hotel")

    # Flight must start and end before hotel starts
    flight_end_idx = execution_order.index(("end", "flight"))
    hotel_start_idx = execution_order.index(("start", "hotel"))
    assert flight_end_idx < hotel_start_idx


# ── TripState lock prevents race conditions ──────────────────────────────────

@pytest.mark.asyncio
async def test_trip_state_lock_prevents_race_conditions():
    """Concurrent safe_add_booking calls don't lose data."""
    state = TripState(trip_id="t-race", original_goal="test")

    async def add_booking(n):
        record = BookingRecord(domain="flight", provider="mock", details={}, amount=100.0)
        await state.safe_add_booking(record)

    # Run 10 concurrent booking additions
    await asyncio.gather(*[add_booking(i) for i in range(10)])

    assert len(state.bookings) == 10
    assert state.total_spent == 1000.0


@pytest.mark.asyncio
async def test_trip_state_safe_add_booking():
    """safe_add_booking appends record and updates total_spent atomically."""
    state = TripState(trip_id="t-safe", original_goal="test")
    record = BookingRecord(domain="hotel", provider="mock", details={"id": "HTL1"}, amount=250.0)
    await state.safe_add_booking(record)

    assert len(state.bookings) == 1
    assert state.bookings[0].domain == "hotel"
    assert state.bookings[0].amount == 250.0
    assert state.total_spent == 250.0


# ── Parallel tasks don't cancel siblings on failure ──────────────────────────

@pytest.mark.asyncio
async def test_parallel_optional_failure_doesnt_cancel_siblings(db, trip, audit_logger, approval_gate):
    """Optional task failure in parallel doesn't cancel sibling tasks."""
    plan = {
        "tasks": [
            {"domain": "flight", "goal": "Book flight"},
            {"domain": "hotel", "goal": "Book hotel"},
            {"domain": "transport", "goal": "Book transport"},
            {"domain": "activity", "goal": "Book activity"},
        ],
        "required": ["flight"],
        "optional": ["hotel", "transport", "activity"],
    }
    decompose_resp = _text_response(json.dumps(plan))
    synth_resp = _text_response("Done!")

    completed_domains = []

    async def mock_run_sub_agent(domain, sub_goal):
        if domain == "transport":
            raise RuntimeError("Transport unavailable")
        await asyncio.sleep(0.01)
        completed_domains.append(domain)
        return "Done."

    mock_client = MagicMock()
    mock_client.messages = MagicMock()
    mock_client.messages.create = AsyncMock(
        side_effect=[decompose_resp, synth_resp]
    )

    agent = OrchestratorAgent(trip.id, db, audit_logger, approval_gate)
    with patch.object(agent, "_client", mock_client):
        with patch.object(agent, "_run_sub_agent", side_effect=mock_run_sub_agent):
            await agent.run("Full trip")

    state = agent._state
    # Hotel and activity should complete even though transport failed
    assert "hotel" in completed_domains
    assert "activity" in completed_domains
    transport_results = [r for r in state.sub_results if r.domain == "transport"]
    assert len(transport_results) == 1
    assert transport_results[0].status == "skipped"
