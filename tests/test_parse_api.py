"""Tests for POST /trips/parse endpoint.

Verifies that:
  - Natural language inputs produce structured ParseTripResponse output
  - Relative dates are resolved to ISO format
  - Domains are inferred correctly
  - Confidence values are reasonable
  - Edge cases (minimal input, ambiguous input) are handled gracefully
  - The heuristic fallback triggers when Claude returns invalid JSON
"""
from __future__ import annotations

import json
from datetime import date
from unittest.mock import MagicMock, patch

import pytest
import pytest_asyncio

from api.schemas import ParseTripResponse


# ── Helpers ──────────────────────────────────────────────────────────────────

def _mock_claude_response(parsed_data: dict) -> MagicMock:
    """Build a mock Anthropic messages.create() return value."""
    content_block = MagicMock()
    content_block.text = json.dumps(parsed_data)
    message = MagicMock()
    message.content = [content_block]
    return message


def _make_parse_result(
    destinations: list[str],
    domains: list[str] | None = None,
    departure_date: str | None = None,
    return_date: str | None = None,
    duration_days: int | None = None,
    budget_total: float | None = None,
    origin: str | None = None,
    cabin_class: str | None = None,
    hotel_type: str | None = None,
    adults: int = 1,
    children: int = 0,
    confidence: float = 0.85,
    clarification_needed: list[str] | None = None,
    goal_text: str = "test goal",
) -> dict:
    """Construct a valid Claude JSON response for the parse endpoint."""
    return {
        "parsed": {
            "destinations": destinations,
            "origin": origin,
            "departure_date": departure_date,
            "return_date": return_date,
            "duration_days": duration_days,
            "budget_total": budget_total,
            "budget_currency": "USD",
            "travelers": {"adults": adults, "children": children},
            "domains": domains or ["flight"],
            "flight_preferences": {
                "cabin_class": cabin_class,
                "airline": None,
                "nonstop": None,
                "seat_preference": None,
            },
            "hotel_preferences": {
                "type": hotel_type,
                "star_rating": None,
                "amenities": [],
                "location_notes": None,
                "budget_per_night": None,
            },
            "activity_preferences": [],
            "notes": None,
        },
        "goal_text": goal_text,
        "confidence": confidence,
        "clarification_needed": clarification_needed or [],
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 1.  SCHEMA VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════

class TestParseSchemaValidation:
    """Verify request validation and response structure."""

    @pytest.mark.asyncio
    async def test_rejects_too_short_text(self, api_client):
        res = await api_client.post("/trips/parse", json={"text": "hi"})
        assert res.status_code == 422

    @pytest.mark.asyncio
    async def test_rejects_missing_text(self, api_client):
        res = await api_client.post("/trips/parse", json={})
        assert res.status_code == 422

    @pytest.mark.asyncio
    async def test_accepts_valid_text(self, api_client):
        data = _make_parse_result(["Tokyo"], domains=["flight", "hotel"], duration_days=10)
        mock_response = _mock_claude_response(data)

        with patch("api.routes.parse.anthropic") as mock_anthropic:
            mock_anthropic.Anthropic.return_value.messages.create.return_value = mock_response
            res = await api_client.post(
                "/trips/parse",
                json={"text": "10 day trip to Tokyo with flights and hotel"},
            )
        assert res.status_code == 200
        body = res.json()
        assert "parsed" in body
        assert "goal_text" in body
        assert "confidence" in body
        assert "raw_input" in body
        assert body["raw_input"] == "10 day trip to Tokyo with flights and hotel"


# ═══════════════════════════════════════════════════════════════════════════════
# 2.  RELATIVE DATE RESOLUTION
# ═══════════════════════════════════════════════════════════════════════════════

class TestParseDateResolution:
    """Claude should resolve relative dates to ISO format in its response."""

    @pytest.mark.asyncio
    async def test_next_month_resolved(self, api_client):
        data = _make_parse_result(
            ["Tokyo"],
            domains=["flight", "hotel"],
            departure_date="2026-04-01",
            return_date="2026-04-11",
            duration_days=10,
            goal_text="10-day trip to Tokyo departing April 2026",
        )
        mock_response = _mock_claude_response(data)

        with patch("api.routes.parse.anthropic") as mock_anthropic:
            mock_anthropic.Anthropic.return_value.messages.create.return_value = mock_response
            res = await api_client.post(
                "/trips/parse",
                json={"text": "Trip to Tokyo next month for 10 days"},
            )
        body = res.json()
        assert body["parsed"]["departure_date"] == "2026-04-01"
        assert body["parsed"]["return_date"] == "2026-04-11"
        assert body["parsed"]["duration_days"] == 10

    @pytest.mark.asyncio
    async def test_month_name_resolved(self, api_client):
        data = _make_parse_result(
            ["Paris"],
            domains=["flight", "hotel"],
            departure_date="2026-06-15",
            duration_days=14,
            goal_text="2-week trip to Paris in June",
        )
        mock_response = _mock_claude_response(data)

        with patch("api.routes.parse.anthropic") as mock_anthropic:
            mock_anthropic.Anthropic.return_value.messages.create.return_value = mock_response
            res = await api_client.post(
                "/trips/parse",
                json={"text": "2 week trip to Paris in June"},
            )
        body = res.json()
        assert body["parsed"]["departure_date"] == "2026-06-15"
        assert body["parsed"]["duration_days"] == 14


# ═══════════════════════════════════════════════════════════════════════════════
# 3.  DOMAIN INFERENCE
# ═══════════════════════════════════════════════════════════════════════════════

class TestParseDomainInference:
    """Verify domains are correctly inferred from natural language."""

    @pytest.mark.asyncio
    async def test_flight_and_hotel_inferred(self, api_client):
        data = _make_parse_result(
            ["Tokyo"],
            domains=["flight", "hotel"],
            goal_text="Trip to Tokyo with flights and hotel",
        )
        mock_response = _mock_claude_response(data)

        with patch("api.routes.parse.anthropic") as mock_anthropic:
            mock_anthropic.Anthropic.return_value.messages.create.return_value = mock_response
            res = await api_client.post(
                "/trips/parse",
                json={"text": "I need flights and a hotel in Tokyo for a week"},
            )
        domains = res.json()["parsed"]["domains"]
        assert "flight" in domains
        assert "hotel" in domains

    @pytest.mark.asyncio
    async def test_hotel_only(self, api_client):
        data = _make_parse_result(
            ["San Francisco"],
            domains=["hotel"],
            hotel_type="hotel",
            goal_text="Hotel near Union Square in SF for 3 nights",
        )
        mock_response = _mock_claude_response(data)

        with patch("api.routes.parse.anthropic") as mock_anthropic:
            mock_anthropic.Anthropic.return_value.messages.create.return_value = mock_response
            res = await api_client.post(
                "/trips/parse",
                json={"text": "Book a hotel in SF near Union Square for 3 nights"},
            )
        domains = res.json()["parsed"]["domains"]
        assert "hotel" in domains

    @pytest.mark.asyncio
    async def test_all_domains(self, api_client):
        data = _make_parse_result(
            ["Tokyo"],
            domains=["flight", "hotel", "transport", "activity"],
            goal_text="Full trip to Tokyo",
        )
        mock_response = _mock_claude_response(data)

        with patch("api.routes.parse.anthropic") as mock_anthropic:
            mock_anthropic.Anthropic.return_value.messages.create.return_value = mock_response
            res = await api_client.post(
                "/trips/parse",
                json={"text": "Fly to Tokyo, book a hotel, arrange airport transfer, and find tours"},
            )
        domains = res.json()["parsed"]["domains"]
        assert set(domains) == {"flight", "hotel", "transport", "activity"}


# ═══════════════════════════════════════════════════════════════════════════════
# 4.  CONFIDENCE AND CLARIFICATION
# ═══════════════════════════════════════════════════════════════════════════════

class TestParseConfidence:
    """Confidence and clarification_needed values should be sensible."""

    @pytest.mark.asyncio
    async def test_high_confidence_for_detailed_request(self, api_client):
        data = _make_parse_result(
            ["Tokyo"],
            domains=["flight", "hotel"],
            departure_date="2026-06-01",
            return_date="2026-06-11",
            duration_days=10,
            budget_total=5000,
            origin="New York",
            cabin_class="business",
            confidence=0.95,
            goal_text="10-day business class trip from NYC to Tokyo, $5000 budget",
        )
        mock_response = _mock_claude_response(data)

        with patch("api.routes.parse.anthropic") as mock_anthropic:
            mock_anthropic.Anthropic.return_value.messages.create.return_value = mock_response
            res = await api_client.post(
                "/trips/parse",
                json={"text": "Business class flight from JFK to Tokyo, 10 days starting June 1, budget $5000"},
            )
        body = res.json()
        assert body["confidence"] >= 0.9

    @pytest.mark.asyncio
    async def test_clarification_for_ambiguous_request(self, api_client):
        data = _make_parse_result(
            ["London"],
            domains=["flight"],
            confidence=0.6,
            clarification_needed=["Departure city not specified", "Travel dates not specified"],
            goal_text="Find cheap flights to London",
        )
        mock_response = _mock_claude_response(data)

        with patch("api.routes.parse.anthropic") as mock_anthropic:
            mock_anthropic.Anthropic.return_value.messages.create.return_value = mock_response
            res = await api_client.post(
                "/trips/parse",
                json={"text": "Find me the cheapest flight to London"},
            )
        body = res.json()
        assert body["confidence"] < 0.8
        assert len(body["clarification_needed"]) > 0


# ═══════════════════════════════════════════════════════════════════════════════
# 5.  HEURISTIC FALLBACK
# ═══════════════════════════════════════════════════════════════════════════════

class TestParseFallback:
    """When Claude returns invalid JSON, the endpoint falls back to the
    heuristic parser from core.intent."""

    @pytest.mark.asyncio
    async def test_fallback_on_invalid_json(self, api_client):
        content_block = MagicMock()
        content_block.text = "Sorry, I can't parse that request properly."
        message = MagicMock()
        message.content = [content_block]

        with patch("api.routes.parse.anthropic") as mock_anthropic:
            mock_anthropic.Anthropic.return_value.messages.create.return_value = message
            res = await api_client.post(
                "/trips/parse",
                json={"text": "Trip to Paris for 5 days"},
            )
        assert res.status_code == 200
        body = res.json()
        # Fallback should still extract Paris
        assert "Paris" in body["parsed"]["destinations"]
        assert body["confidence"] == 0.5
        assert any("fallback" in c.lower() for c in body["clarification_needed"])


# ═══════════════════════════════════════════════════════════════════════════════
# 6.  COMPLEX END-TO-END PATTERNS
# ═══════════════════════════════════════════════════════════════════════════════

class TestParseComplexPatterns:
    """Real-world-style queries with multiple parameters."""

    @pytest.mark.asyncio
    async def test_family_vacation(self, api_client):
        data = _make_parse_result(
            ["Rome", "Florence"],
            domains=["flight", "hotel", "activity"],
            departure_date="2026-07-10",
            return_date="2026-07-20",
            duration_days=10,
            adults=2,
            children=2,
            hotel_type="boutique",
            confidence=0.85,
            goal_text="10-day family vacation to Rome and Florence in July, boutique hotels, 2 adults 2 kids",
        )
        mock_response = _mock_claude_response(data)

        with patch("api.routes.parse.anthropic") as mock_anthropic:
            mock_anthropic.Anthropic.return_value.messages.create.return_value = mock_response
            res = await api_client.post(
                "/trips/parse",
                json={"text": "Family vacation to Italy in July, 2 adults 2 kids, we like boutique hotels and want to see Rome and Florence"},
            )
        body = res.json()
        parsed = body["parsed"]
        assert "Rome" in parsed["destinations"]
        assert "Florence" in parsed["destinations"]
        assert parsed["travelers"]["adults"] == 2
        assert parsed["travelers"]["children"] == 2
        assert parsed["hotel_preferences"]["type"] == "boutique"
        assert "activity" in parsed["domains"]

    @pytest.mark.asyncio
    async def test_business_trip(self, api_client):
        data = _make_parse_result(
            ["Chicago"],
            domains=["flight", "hotel"],
            departure_date="2026-04-09",
            return_date="2026-04-11",
            duration_days=2,
            hotel_type="hotel",
            cabin_class=None,
            confidence=0.80,
            clarification_needed=["Interpreted 'Wednesday to Friday' as Apr 9-11"],
            goal_text="Business trip to Chicago, Wed-Fri, budget hotel near downtown",
        )
        mock_response = _mock_claude_response(data)

        with patch("api.routes.parse.anthropic") as mock_anthropic:
            mock_anthropic.Anthropic.return_value.messages.create.return_value = mock_response
            res = await api_client.post(
                "/trips/parse",
                json={"text": "Plan a weekend trip to Chicago for a client meeting, Wednesday to Friday, budget hotel near downtown"},
            )
        body = res.json()
        assert body["parsed"]["destinations"] == ["Chicago"]
        assert body["parsed"]["duration_days"] == 2
        assert len(body["clarification_needed"]) > 0

    @pytest.mark.asyncio
    async def test_markdown_fenced_json_stripped(self, api_client):
        """Claude sometimes wraps JSON in markdown fences — verify they're stripped."""
        data = _make_parse_result(["Bali"], domains=["flight", "hotel"], duration_days=7)
        fenced = "```json\n" + json.dumps(data) + "\n```"

        content_block = MagicMock()
        content_block.text = fenced
        message = MagicMock()
        message.content = [content_block]

        with patch("api.routes.parse.anthropic") as mock_anthropic:
            mock_anthropic.Anthropic.return_value.messages.create.return_value = message
            res = await api_client.post(
                "/trips/parse",
                json={"text": "Week-long trip to Bali with flights and hotel"},
            )
        assert res.status_code == 200
        assert res.json()["parsed"]["destinations"] == ["Bali"]
