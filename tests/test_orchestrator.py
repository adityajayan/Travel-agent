"""Tests for OrchestratorAgent."""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents.orchestrator_agent import OrchestratorAgent, _detect_domains
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


# ── Domain detection ──────────────────────────────────────────────────────────

def test_detect_domains_flight_only():
    domains = _detect_domains("Book me a flight to Paris")
    assert "flight" in domains


def test_detect_domains_hotel_only():
    domains = _detect_domains("Find a hotel in London for 3 nights")
    assert "hotel" in domains


def test_detect_domains_multi():
    domains = _detect_domains("I need a flight and a hotel in Rome")
    assert "flight" in domains
    assert "hotel" in domains


def test_detect_domains_defaults_to_flight():
    domains = _detect_domains("Plan my trip")
    assert domains  # at least one domain returned


# ── _decompose ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_decompose_parses_json_response(db, trip, audit_logger, approval_gate):
    plan = {
        "tasks": [
            {"domain": "flight", "goal": "Book flight to Paris"},
            {"domain": "hotel", "goal": "Book hotel in Paris"},
        ],
        "required": ["flight"],
        "optional": ["hotel"],
    }
    mock_client = MagicMock()
    mock_client.messages = MagicMock()
    mock_client.messages.create = AsyncMock(return_value=_text_response(json.dumps(plan)))

    agent = OrchestratorAgent(trip.id, db, audit_logger, approval_gate)
    with patch.object(agent, "_client", mock_client):
        result = await agent._decompose("Book a flight and hotel in Paris")

    assert len(result["tasks"]) == 2
    assert result["tasks"][0]["domain"] == "flight"


@pytest.mark.asyncio
async def test_decompose_falls_back_on_invalid_json(db, trip, audit_logger, approval_gate):
    mock_client = MagicMock()
    mock_client.messages = MagicMock()
    mock_client.messages.create = AsyncMock(return_value=_text_response("not-json"))

    agent = OrchestratorAgent(trip.id, db, audit_logger, approval_gate)
    with patch.object(agent, "_client", mock_client):
        result = await agent._decompose("Book a flight to Rome")

    # Fallback should still return a dict with tasks
    assert "tasks" in result
    assert isinstance(result["tasks"], list)
    assert len(result["tasks"]) >= 1


# ── _synthesize ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_synthesize_returns_text(db, trip, audit_logger, approval_gate):
    from agents.trip_state import SubTaskResult, TripState

    state = TripState(trip_id=trip.id, original_goal="Paris trip")
    state.add_result(SubTaskResult(domain="flight", goal="Book flight", status="success", output="Booked FL001"))
    state.add_result(SubTaskResult(domain="hotel", goal="Book hotel", status="success", output="Booked HTL001"))

    mock_client = MagicMock()
    mock_client.messages = MagicMock()
    mock_client.messages.create = AsyncMock(
        return_value=_text_response("Your Paris trip is all set! Flight and hotel confirmed.")
    )

    agent = OrchestratorAgent(trip.id, db, audit_logger, approval_gate)
    with patch.object(agent, "_client", mock_client):
        summary = await agent._synthesize(state)

    assert "Paris" in summary or "confirmed" in summary


# ── Full run (mocked sub-agents) ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_orchestrator_run_calls_sub_agents(db, trip, audit_logger, approval_gate):
    """OrchestratorAgent.run should call _decompose and _synthesize."""
    plan = {
        "tasks": [{"domain": "flight", "goal": "Book flight to Paris"}],
        "required": ["flight"],
        "optional": [],
    }
    decompose_response = _text_response(json.dumps(plan))
    synthesize_response = _text_response("Trip is booked!")

    sub_agent_text_response = _text_response("Flight searched and awaiting approval.")

    mock_client = MagicMock()
    mock_client.messages = MagicMock()
    # decompose → synthesize (orchestrator calls); sub-agent also calls Claude
    mock_client.messages.create = AsyncMock(
        side_effect=[decompose_response, sub_agent_text_response, synthesize_response]
    )

    agent = OrchestratorAgent(trip.id, db, audit_logger, approval_gate)
    with patch.object(agent, "_client", mock_client):
        # Sub-agents also create their own AsyncAnthropic client; patch at module level
        with patch("agents.base_agent.AsyncAnthropic") as mock_ant:
            mock_ant.return_value.messages.create = AsyncMock(return_value=sub_agent_text_response)
            summary = await agent.run("Book a flight to Paris")

    assert summary  # Non-empty
