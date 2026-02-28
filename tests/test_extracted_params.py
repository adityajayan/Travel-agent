"""Tests for M4 Item 1 — Typed ExtractedParams Dataclass."""
import dataclasses
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents.orchestrator_agent import OrchestratorAgent, _extract_params_from_plan
from agents.trip_state import TripState
from core.state import ExtractedParams


# ── ExtractedParams field access & defaults ──────────────────────────────────

def test_extracted_params_defaults():
    p = ExtractedParams()
    assert p.arrival_city is None
    assert p.arrival_airport is None
    assert p.departure_city is None
    assert p.departure_airport is None
    assert p.check_in_date is None
    assert p.check_out_date is None
    assert p.destination_city is None
    assert p.travel_dates == []
    assert p.num_travelers == 1


def test_extracted_params_field_access():
    p = ExtractedParams(
        arrival_city="Paris",
        arrival_airport="CDG",
        departure_city="London",
        departure_airport="LHR",
        check_in_date="2026-06-01",
        check_out_date="2026-06-05",
        destination_city="Paris",
        travel_dates=["2026-06-01", "2026-06-02"],
        num_travelers=3,
    )
    assert p.arrival_city == "Paris"
    assert p.arrival_airport == "CDG"
    assert p.departure_city == "London"
    assert p.departure_airport == "LHR"
    assert p.check_in_date == "2026-06-01"
    assert p.check_out_date == "2026-06-05"
    assert p.destination_city == "Paris"
    assert p.travel_dates == ["2026-06-01", "2026-06-02"]
    assert p.num_travelers == 3


# ── Serialization to dict ────────────────────────────────────────────────────

def test_extracted_params_serialization_to_dict():
    p = ExtractedParams(arrival_city="Tokyo", num_travelers=2)
    d = dataclasses.asdict(p)
    assert isinstance(d, dict)
    assert d["arrival_city"] == "Tokyo"
    assert d["num_travelers"] == 2
    assert d["departure_city"] is None
    assert d["travel_dates"] == []


def test_extracted_params_to_dict_method():
    p = ExtractedParams(destination_city="Rome", travel_dates=["2026-07-01"])
    d = p.to_dict()
    assert d["destination_city"] == "Rome"
    assert d["travel_dates"] == ["2026-07-01"]
    assert d["num_travelers"] == 1


def test_extracted_params_serialization_roundtrip():
    original = ExtractedParams(
        arrival_city="Berlin",
        check_in_date="2026-08-01",
        check_out_date="2026-08-04",
        num_travelers=4,
    )
    d = dataclasses.asdict(original)
    restored = ExtractedParams(**d)
    assert restored == original


# ── TripState integration ────────────────────────────────────────────────────

def test_trip_state_default_extracted_params():
    state = TripState(trip_id="t1", original_goal="test")
    assert isinstance(state.extracted_params, ExtractedParams)
    assert state.extracted_params.arrival_city is None
    assert state.extracted_params.num_travelers == 1


def test_trip_state_with_extracted_params():
    params = ExtractedParams(arrival_city="NYC", departure_city="LAX")
    state = TripState(trip_id="t2", original_goal="fly", extracted_params=params)
    assert state.extracted_params.arrival_city == "NYC"
    assert state.extracted_params.departure_city == "LAX"


def test_trip_state_to_context_dict_includes_params():
    params = ExtractedParams(arrival_city="Sydney", num_travelers=2)
    state = TripState(trip_id="t3", original_goal="trip to Sydney", extracted_params=params)
    ctx = state.to_context_dict()
    assert "extracted_params" in ctx
    assert ctx["extracted_params"]["arrival_city"] == "Sydney"
    assert ctx["extracted_params"]["num_travelers"] == 2


def test_trip_state_to_context_dict_serializes_flat():
    state = TripState(trip_id="t4", original_goal="test")
    ctx = state.to_context_dict()
    assert isinstance(ctx["extracted_params"], dict)
    # Should be JSON-serializable
    json.dumps(ctx)


# ── _extract_params_from_plan ────────────────────────────────────────────────

def test_extract_params_from_plan_with_explicit_params():
    plan = {
        "tasks": [{"domain": "flight", "goal": "Book flight to Paris"}],
        "required": ["flight"],
        "optional": [],
        "extracted_params": {
            "arrival_city": "Paris",
            "arrival_airport": "CDG",
            "departure_city": "London",
            "check_in_date": "2026-06-01",
            "num_travelers": 2,
        },
    }
    params = _extract_params_from_plan(plan)
    assert params.arrival_city == "Paris"
    assert params.arrival_airport == "CDG"
    assert params.departure_city == "London"
    assert params.check_in_date == "2026-06-01"
    assert params.num_travelers == 2


def test_extract_params_from_plan_infers_destination():
    plan = {
        "tasks": [{"domain": "flight", "goal": "Book flight to Rome"}],
        "required": ["flight"],
        "optional": [],
    }
    params = _extract_params_from_plan(plan)
    assert params.destination_city == "Rome"
    assert params.arrival_city == "Rome"


def test_extract_params_from_plan_no_tasks():
    plan = {"tasks": [], "required": [], "optional": []}
    params = _extract_params_from_plan(plan)
    assert params.destination_city is None
    assert params.num_travelers == 1


# ── OrchestratorAgent populates and propagates ExtractedParams ───────────────

def _text_response(text: str):
    block = MagicMock()
    block.type = "text"
    block.text = text
    resp = MagicMock()
    resp.stop_reason = "end_turn"
    resp.content = [block]
    return resp


@pytest.mark.asyncio
async def test_orchestrator_populates_extracted_params(db, trip, audit_logger, approval_gate):
    """OrchestratorAgent.run populates ExtractedParams from decomposed plan."""
    plan = {
        "tasks": [{"domain": "flight", "goal": "Book flight to Chicago"}],
        "required": ["flight"],
        "optional": [],
        "extracted_params": {
            "arrival_city": "Chicago",
            "destination_city": "Chicago",
        },
    }
    decompose_response = _text_response(json.dumps(plan))
    sub_agent_text_response = _text_response("Flight searched.")
    synthesize_response = _text_response("Trip complete!")

    mock_client = MagicMock()
    mock_client.messages = MagicMock()
    mock_client.messages.create = AsyncMock(
        side_effect=[decompose_response, sub_agent_text_response, synthesize_response]
    )

    agent = OrchestratorAgent(trip.id, db, audit_logger, approval_gate)
    with patch.object(agent, "_client", mock_client):
        with patch("agents.base_agent.AsyncAnthropic") as mock_ant:
            mock_ant.return_value.messages.create = AsyncMock(return_value=sub_agent_text_response)
            await agent.run("Book a flight to Chicago")

    assert agent._state is not None
    assert agent._state.extracted_params.arrival_city == "Chicago"
    assert agent._state.extracted_params.destination_city == "Chicago"


@pytest.mark.asyncio
async def test_orchestrator_propagates_params_to_sub_agents(db, trip, audit_logger, approval_gate):
    """OrchestratorAgent passes ExtractedParams via TripState to sub-agents."""
    plan = {
        "tasks": [
            {"domain": "flight", "goal": "Book flight to Paris"},
            {"domain": "hotel", "goal": "Book hotel in Paris"},
        ],
        "required": ["flight", "hotel"],
        "optional": [],
        "extracted_params": {
            "arrival_city": "Paris",
            "destination_city": "Paris",
            "check_in_date": "2026-07-01",
            "check_out_date": "2026-07-05",
        },
    }
    decompose_response = _text_response(json.dumps(plan))
    sub_agent_text_response = _text_response("Done.")
    synthesize_response = _text_response("Trip to Paris booked!")

    mock_client = MagicMock()
    mock_client.messages = MagicMock()
    mock_client.messages.create = AsyncMock(
        side_effect=[decompose_response, sub_agent_text_response, sub_agent_text_response, synthesize_response]
    )

    agent = OrchestratorAgent(trip.id, db, audit_logger, approval_gate)
    with patch.object(agent, "_client", mock_client):
        with patch("agents.base_agent.AsyncAnthropic") as mock_ant:
            mock_ant.return_value.messages.create = AsyncMock(return_value=sub_agent_text_response)
            summary = await agent.run("Book flight and hotel in Paris")

    # Verify the state has extracted params set
    state = agent._state
    assert state.extracted_params.arrival_city == "Paris"
    assert state.extracted_params.check_in_date == "2026-07-01"
    assert state.extracted_params.check_out_date == "2026-07-05"

    # Verify to_context_dict includes params
    ctx = state.to_context_dict()
    assert ctx["extracted_params"]["arrival_city"] == "Paris"
