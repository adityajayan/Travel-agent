"""Tests for tools/planning_tools.py — read-only planning tools."""
import pytest

from agents.base_agent import APPROVAL_REQUIRED_TOOLS
from tools.planning_tools import (
    SUGGEST_ALTERNATIVE_DATES_DEF,
    SUGGEST_TRIP_OPTIONS_DEF,
    suggest_alternative_dates,
    suggest_trip_options,
)


# ── Tool definitions ─────────────────────────────────────────────────────────

class TestToolDefinitions:
    def test_suggest_trip_options_def_schema(self):
        assert SUGGEST_TRIP_OPTIONS_DEF["name"] == "suggest_trip_options"
        props = SUGGEST_TRIP_OPTIONS_DEF["input_schema"]["properties"]
        assert "destination" in props
        assert "duration_nights" in props
        assert "num_passengers" in props
        assert SUGGEST_TRIP_OPTIONS_DEF["input_schema"]["required"] == ["destination"]

    def test_suggest_alternative_dates_def_schema(self):
        assert SUGGEST_ALTERNATIVE_DATES_DEF["name"] == "suggest_alternative_dates"
        props = SUGGEST_ALTERNATIVE_DATES_DEF["input_schema"]["properties"]
        assert "destination" in props
        assert "original_date" in props
        assert "duration_nights" in props
        assert set(SUGGEST_ALTERNATIVE_DATES_DEF["input_schema"]["required"]) == {
            "destination", "original_date"
        }


# ── Planning tools NOT in APPROVAL_REQUIRED_TOOLS ────────────────────────────

class TestToolsNotApprovalRequired:
    def test_suggest_trip_options_not_approval_required(self):
        assert "suggest_trip_options" not in APPROVAL_REQUIRED_TOOLS

    def test_suggest_alternative_dates_not_approval_required(self):
        assert "suggest_alternative_dates" not in APPROVAL_REQUIRED_TOOLS


# ── suggest_trip_options output ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_suggest_trip_options_returns_three_tiers():
    result = await suggest_trip_options("Tokyo", 5, 1)
    assert len(result) == 3
    assert result[0]["name"] == "budget"
    assert result[1]["name"] == "comfortable"
    assert result[2]["name"] == "premium"


@pytest.mark.asyncio
async def test_suggest_trip_options_tiers_are_dicts():
    result = await suggest_trip_options("Paris", 5, 1)
    for tier in result:
        assert isinstance(tier, dict)
        assert "name" in tier
        assert "label" in tier
        assert "estimated_total" in tier
        assert "estimated_flight_cost" in tier
        assert "estimated_hotel_per_night" in tier


@pytest.mark.asyncio
async def test_suggest_trip_options_budget_ordering():
    result = await suggest_trip_options("London", 5, 1)
    assert result[0]["estimated_total"] < result[1]["estimated_total"]
    assert result[1]["estimated_total"] < result[2]["estimated_total"]


@pytest.mark.asyncio
async def test_suggest_trip_options_default_params():
    """Calling with only destination should use defaults."""
    result = await suggest_trip_options("Rome")
    assert len(result) == 3


@pytest.mark.asyncio
async def test_suggest_trip_options_unknown_city():
    """Unknown city should still return 3 tiers using default profile."""
    result = await suggest_trip_options("Timbuktu")
    assert len(result) == 3


# ── suggest_alternative_dates output ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_suggest_alternative_dates_returns_alternatives():
    result = await suggest_alternative_dates("Tokyo", "2026-06-15", 5)
    assert len(result) >= 4  # at least ±3 day shifts
    for alt in result:
        assert "check_in" in alt
        assert "check_out" in alt
        assert "savings_estimate_pct" in alt
        assert "note" in alt
        assert "is_best_season" in alt


@pytest.mark.asyncio
async def test_suggest_alternative_dates_invalid_date():
    result = await suggest_alternative_dates("Tokyo", "not-a-date", 5)
    assert len(result) == 1
    assert "error" in result[0]


@pytest.mark.asyncio
async def test_suggest_alternative_dates_best_month_suggestion():
    """If original date is NOT in best months, should include a best-month suggestion."""
    # Tokyo best_months = [3, 4, 10, 11]; June is not a best month
    result = await suggest_alternative_dates("Tokyo", "2026-06-15", 5)
    best_season_items = [a for a in result if a.get("is_best_season") and a["savings_estimate_pct"] == 20]
    assert len(best_season_items) >= 1


@pytest.mark.asyncio
async def test_suggest_alternative_dates_in_best_month():
    """If original date IS in best month, no extra best-month suggestion."""
    # Tokyo best_months = [3, 4, 10, 11]; October is a best month
    result = await suggest_alternative_dates("Tokyo", "2026-10-15", 5)
    # Should only have the ±3 day shifts (4 items), no extra best-month item
    best_month_extras = [a for a in result if a["savings_estimate_pct"] == 20]
    assert len(best_month_extras) == 0


@pytest.mark.asyncio
async def test_suggest_alternative_dates_checkout_matches_duration():
    result = await suggest_alternative_dates("Paris", "2026-05-01", 7)
    for alt in result:
        from datetime import date
        ci = date.fromisoformat(alt["check_in"])
        co = date.fromisoformat(alt["check_out"])
        assert (co - ci).days == 7


# ── Tools registered in agents ───────────────────────────────────────────────

class TestToolRegistration:
    def test_flight_agent_has_planning_tools(self):
        """FlightAgent should register suggest_trip_options and suggest_alternative_dates."""
        from unittest.mock import MagicMock, AsyncMock
        from agents.flight_agent import FlightAgent

        agent = FlightAgent(
            trip_id="test",
            db=MagicMock(),
            audit_logger=MagicMock(),
            approval_gate=MagicMock(),
        )
        tool_names = agent.tool_registry.tool_names()
        assert "suggest_trip_options" in tool_names
        assert "suggest_alternative_dates" in tool_names

    def test_hotel_agent_has_planning_tools(self):
        """HotelAgent should register suggest_trip_options and suggest_alternative_dates."""
        from unittest.mock import MagicMock
        from agents.hotel_agent import HotelAgent

        agent = HotelAgent(
            trip_id="test",
            db=MagicMock(),
            audit_logger=MagicMock(),
            approval_gate=MagicMock(),
        )
        tool_names = agent.tool_registry.tool_names()
        assert "suggest_trip_options" in tool_names
        assert "suggest_alternative_dates" in tool_names
