"""POST /trips/parse — natural-language trip parsing via Claude."""

import json
import logging
from datetime import date

from fastapi import APIRouter, Depends

import anthropic

from api.schemas import ParsedTripParams, ParseTripRequest, ParseTripResponse
from core.auth import CurrentUser, get_current_user
from core.config import settings

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
