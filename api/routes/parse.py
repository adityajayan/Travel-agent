"""POST /trips/parse — natural-language trip parsing via Claude."""

import calendar
import json
import logging
import math
from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query

import anthropic

from api.schemas import (
    DateSuggestion,
    DateSuggestRequest,
    DateSuggestResponse,
    NearestCityResponse,
    ParsedTripParams,
    ParseTripRequest,
    ParseTripResponse,
)
from core.auth import CurrentUser, get_current_user
from core.config import settings
from core.intent import CITY_BUDGET_PROFILES, DEFAULT_PROFILE

router = APIRouter(prefix="/trips", tags=["trips"])
logger = logging.getLogger(__name__)

PARSE_SYSTEM_PROMPT = """\
You are a travel request parser. Extract structured travel parameters from the
user's natural language input. Today's date is {today}.

Rules:
1. Extract all travel parameters you can identify.
2. Resolve relative dates to ISO format (YYYY-MM-DD):
   - "next month" → 1st of the next calendar month
   - "this weekend" → the coming Saturday
   - "mid-April" → April 15
   - "in June" → June 15 of the current or next year (whichever is soonest in the future)
3. Infer domains needed:
   - If the destination requires air travel, include "flight"
   - If dates span multiple nights, include "hotel"
   - If they mention tours/museums/sightseeing, include "activity"
   - If they mention taxi/transfer/train/car, include "transport"
   - If no specific domain is mentioned but a distant destination is given, default to ["flight", "hotel"]
4. Generate a clean "goal_text" summary that a travel agent system can process.
5. Set "confidence" between 0.0 and 1.0 based on how unambiguous the request is.
6. Add notes to "clarification_needed" for anything ambiguous (e.g. "Departure city not specified").
7. If something is not mentioned, leave it as null (not a guess).

Respond with ONLY valid JSON matching this exact structure (no markdown, no preamble):
{{
  "parsed": {{
    "destinations": ["city names"],
    "origin": "city or null",
    "departure_date": "YYYY-MM-DD or null",
    "return_date": "YYYY-MM-DD or null",
    "duration_days": number_or_null,
    "budget_total": number_or_null,
    "budget_currency": "USD",
    "travelers": {{ "adults": 1, "children": 0 }},
    "domains": ["flight", "hotel", ...],
    "flight_preferences": {{
      "cabin_class": "economy/business/first/premium_economy or null",
      "airline": "name or null",
      "nonstop": true_false_or_null,
      "seat_preference": "aisle/window or null"
    }},
    "hotel_preferences": {{
      "type": "hotel/boutique/hostel/airbnb/resort or null",
      "star_rating": number_or_null,
      "amenities": [],
      "location_notes": "string or null",
      "budget_per_night": number_or_null
    }},
    "activity_preferences": [],
    "notes": "string or null"
  }},
  "goal_text": "clean summary for the orchestrator",
  "confidence": 0.85,
  "clarification_needed": ["list of ambiguous items"]
}}"""


@router.post("/parse", response_model=ParseTripResponse)
async def parse_trip_goal(
    body: ParseTripRequest,
    user: CurrentUser = Depends(get_current_user),
):
    """Parse natural language trip request into structured parameters using Claude."""
    today = date.today().isoformat()
    system_prompt = PARSE_SYSTEM_PROMPT.format(today=today)

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        system=system_prompt,
        messages=[{"role": "user", "content": body.text}],
    )

    raw_text = message.content[0].text.strip()

    # Strip markdown fences if Claude wraps the JSON
    if raw_text.startswith("```"):
        lines = raw_text.split("\n")
        # Remove first and last fence lines
        lines = [l for l in lines if not l.strip().startswith("```")]
        raw_text = "\n".join(lines)

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError:
        logger.error("Claude returned invalid JSON for parse: %s", raw_text[:200])
        # Return a minimal fallback using heuristic parser
        from core.intent import extract_and_infer
        from agents.orchestrator_agent import _detect_domains

        tp = extract_and_infer(body.text)
        dest = tp.destination_city.value if tp.destination_city else None
        domains = _detect_domains(body.text)
        return ParseTripResponse(
            parsed=ParsedTripParams(
                destinations=[dest] if dest else [],
                origin=tp.departure_city.value if tp.departure_city else None,
                departure_date=tp.check_in_date.value if tp.check_in_date else None,
                return_date=tp.check_out_date.value if tp.check_out_date else None,
                duration_days=tp.duration_nights.value if tp.duration_nights else None,
                budget_total=tp.total_budget.value if tp.total_budget else None,
                domains=domains,
            ),
            goal_text=body.text,
            confidence=0.5,
            clarification_needed=["Parse used heuristic fallback — review all fields"],
            raw_input=body.text,
        )

    parsed = ParsedTripParams.model_validate(data.get("parsed", {}))
    return ParseTripResponse(
        parsed=parsed,
        goal_text=data.get("goal_text", body.text),
        confidence=min(max(data.get("confidence", 0.7), 0.0), 1.0),
        clarification_needed=data.get("clarification_needed", []),
        raw_input=body.text,
    )


# ── Date Suggestions ─────────────────────────────────────────────────────────

# Season descriptions per destination for richer labels
_SEASON_REASONS: dict[str, dict[str, str]] = {
    "tokyo": {3: "Cherry blossom season", 4: "Cherry blossom season", 10: "Autumn foliage", 11: "Autumn foliage"},
    "paris": {4: "Spring blooms", 5: "Spring blooms", 6: "Long summer days", 9: "Mild autumn", 10: "Mild autumn"},
    "bali": {4: "Dry season begins", 5: "Dry season", 6: "Dry season", 9: "Dry season", 10: "Dry season"},
    "cancun": {12: "Dry season", 1: "Dry season", 2: "Peak winter sun", 3: "Spring break", 4: "Shoulder season"},
    "bangkok": {11: "Cool dry season", 12: "Cool dry season", 1: "Cool dry season", 2: "Cool dry season"},
}


def _next_month_in_list(months: list[int], skip_months: int = 0) -> date:
    """Return the 15th of the next upcoming month from the list, skipping skip_months."""
    today = date.today()
    found = 0
    for offset in range(0, 24):
        candidate_month = ((today.month - 1 + offset) % 12) + 1
        candidate_year = today.year + ((today.month - 1 + offset) // 12)
        if candidate_month in months:
            d = date(candidate_year, candidate_month, 15)
            if d > today + timedelta(days=7):
                if found >= skip_months:
                    return d
                found += 1
    return today + timedelta(days=14)


@router.post("/parse/suggest-dates", response_model=DateSuggestResponse)
async def suggest_dates(
    body: DateSuggestRequest,
    user: CurrentUser = Depends(get_current_user),
):
    """Return smart travel date suggestions for a destination."""
    dest_key = body.destination.lower().strip()
    profile = CITY_BUDGET_PROFILES.get(dest_key, DEFAULT_PROFILE)
    best_months = profile.get("best_months", list(range(1, 13)))
    duration = body.duration_days

    suggestions: list[DateSuggestion] = []

    # 1. Best season
    best_date = _next_month_in_list(best_months)
    month_name = calendar.month_name[best_date.month]
    reason_map = _SEASON_REASONS.get(dest_key, {})
    reason = reason_map.get(best_date.month, f"Best weather in {month_name}")
    dep = best_date
    ret = dep + timedelta(days=duration)
    suggestions.append(DateSuggestion(
        label=f"{dep.strftime('%b %d')}–{ret.strftime('%b %d')}",
        reason=reason,
        departure_date=dep.isoformat(),
        return_date=ret.isoformat(),
    ))

    # 2. Alternative season (next best month after the first)
    alt_date = _next_month_in_list(best_months, skip_months=1)
    if alt_date.month != best_date.month:
        alt_month_name = calendar.month_name[alt_date.month]
        alt_reason = reason_map.get(alt_date.month, f"Great weather in {alt_month_name}")
        dep2 = alt_date
        ret2 = dep2 + timedelta(days=duration)
        suggestions.append(DateSuggestion(
            label=f"{dep2.strftime('%b %d')}–{ret2.strftime('%b %d')}",
            reason=alt_reason,
            departure_date=dep2.isoformat(),
            return_date=ret2.isoformat(),
        ))

    # 3. Soonest (2 weeks from now)
    soon = date.today() + timedelta(days=14)
    ret_soon = soon + timedelta(days=duration)
    suggestions.append(DateSuggestion(
        label=f"{soon.strftime('%b %d')}–{ret_soon.strftime('%b %d')}",
        reason="Soonest available",
        departure_date=soon.isoformat(),
        return_date=ret_soon.isoformat(),
    ))

    return DateSuggestResponse(suggestions=suggestions)


# ── Nearest City (Geolocation) ───────────────────────────────────────────────

_CITY_COORDS: dict[str, tuple[float, float]] = {
    "tokyo": (35.6762, 139.6503),
    "paris": (48.8566, 2.3522),
    "london": (51.5074, -0.1278),
    "new york": (40.7128, -74.0060),
    "bangkok": (13.7563, 100.5018),
    "rome": (41.9028, 12.4964),
    "barcelona": (41.3874, 2.1686),
    "amsterdam": (52.3676, 4.9041),
    "dubai": (25.2048, 55.2708),
    "singapore": (1.3521, 103.8198),
    "sydney": (-33.8688, 151.2093),
    "cancun": (21.1619, -86.8515),
    "bali": (-8.3405, 115.0920),
    "lisbon": (38.7223, -9.1393),
    "istanbul": (41.0082, 28.9784),
    "san francisco": (37.7749, -122.4194),
    "los angeles": (34.0522, -118.2437),
    "chicago": (41.8781, -87.6298),
    "miami": (25.7617, -80.1918),
    "hawaii": (21.3069, -157.8583),
    # Additional major departure cities
    "seattle": (47.6062, -122.3321),
    "boston": (42.3601, -71.0589),
    "washington dc": (38.9072, -77.0369),
    "dallas": (32.7767, -96.7970),
    "houston": (29.7604, -95.3698),
    "denver": (39.7392, -104.9903),
    "atlanta": (33.7490, -84.3880),
    "phoenix": (33.4484, -112.0740),
    "philadelphia": (39.9526, -75.1652),
    "minneapolis": (44.9778, -93.2650),
    "detroit": (42.3314, -83.0458),
    "portland": (45.5152, -122.6784),
    "toronto": (43.6532, -79.3832),
    "vancouver": (49.2827, -123.1207),
    "montreal": (45.5017, -73.5673),
}

_CITY_COUNTRIES: dict[str, str] = {
    **{k: v["country"] for k, v in CITY_BUDGET_PROFILES.items()},
    "seattle": "USA", "boston": "USA", "washington dc": "USA",
    "dallas": "USA", "houston": "USA", "denver": "USA",
    "atlanta": "USA", "phoenix": "USA", "philadelphia": "USA",
    "minneapolis": "USA", "detroit": "USA", "portland": "USA",
    "toronto": "Canada", "vancouver": "Canada", "montreal": "Canada",
}


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distance in km between two lat/lon points."""
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


@router.get("/parse/nearest-city", response_model=NearestCityResponse)
async def nearest_city(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    user: CurrentUser = Depends(get_current_user),
):
    """Return the nearest known city to the given coordinates."""
    best_city = "new york"
    best_dist = float("inf")
    for city, (clat, clon) in _CITY_COORDS.items():
        d = _haversine(lat, lon, clat, clon)
        if d < best_dist:
            best_dist = d
            best_city = city
    # Title-case the city name
    display_name = best_city.replace("dc", "DC").title()
    country = _CITY_COUNTRIES.get(best_city, "Unknown")
    return NearestCityResponse(city=display_name, country=country)
