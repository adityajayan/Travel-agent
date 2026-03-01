"""Intent extraction and smart defaults engine.

Heuristic extractors parse natural-language trip goals into structured params.
Smart defaults fill in gaps using city-level reference data so agents can
proceed without interrogating the user.
"""
import calendar
import re
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional

from core.param_tracking import ParamSource, TrackedParam, TrackedParams


# ── City-level reference data ────────────────────────────────────────────────

CITY_BUDGET_PROFILES: dict[str, dict] = {
    "tokyo":        {"flight_rt": 900,  "hotel_night": 180, "best_months": [3, 4, 10, 11],  "default_nights": 7, "country": "Japan"},
    "paris":        {"flight_rt": 700,  "hotel_night": 200, "best_months": [4, 5, 6, 9, 10], "default_nights": 5, "country": "France"},
    "london":       {"flight_rt": 600,  "hotel_night": 220, "best_months": [5, 6, 7, 9],     "default_nights": 5, "country": "UK"},
    "new york":     {"flight_rt": 300,  "hotel_night": 250, "best_months": [4, 5, 9, 10],    "default_nights": 4, "country": "USA"},
    "bangkok":      {"flight_rt": 700,  "hotel_night": 80,  "best_months": [11, 12, 1, 2],   "default_nights": 7, "country": "Thailand"},
    "rome":         {"flight_rt": 650,  "hotel_night": 170, "best_months": [4, 5, 9, 10],    "default_nights": 5, "country": "Italy"},
    "barcelona":    {"flight_rt": 600,  "hotel_night": 160, "best_months": [5, 6, 9, 10],    "default_nights": 5, "country": "Spain"},
    "amsterdam":    {"flight_rt": 550,  "hotel_night": 190, "best_months": [4, 5, 6, 9],     "default_nights": 4, "country": "Netherlands"},
    "dubai":        {"flight_rt": 800,  "hotel_night": 200, "best_months": [11, 12, 1, 2, 3],"default_nights": 5, "country": "UAE"},
    "singapore":    {"flight_rt": 850,  "hotel_night": 170, "best_months": [2, 3, 7, 8],     "default_nights": 5, "country": "Singapore"},
    "sydney":       {"flight_rt": 1100, "hotel_night": 200, "best_months": [9, 10, 11, 3, 4],"default_nights": 7, "country": "Australia"},
    "cancun":       {"flight_rt": 400,  "hotel_night": 150, "best_months": [12, 1, 2, 3, 4], "default_nights": 5, "country": "Mexico"},
    "bali":         {"flight_rt": 900,  "hotel_night": 80,  "best_months": [4, 5, 6, 9, 10], "default_nights": 7, "country": "Indonesia"},
    "lisbon":       {"flight_rt": 550,  "hotel_night": 140, "best_months": [5, 6, 9, 10],    "default_nights": 5, "country": "Portugal"},
    "istanbul":     {"flight_rt": 600,  "hotel_night": 100, "best_months": [4, 5, 9, 10],    "default_nights": 5, "country": "Turkey"},
    "san francisco":{"flight_rt": 250,  "hotel_night": 280, "best_months": [9, 10, 4, 5],    "default_nights": 4, "country": "USA"},
    "los angeles":  {"flight_rt": 250,  "hotel_night": 220, "best_months": [3, 4, 5, 9, 10], "default_nights": 4, "country": "USA"},
    "chicago":      {"flight_rt": 200,  "hotel_night": 200, "best_months": [5, 6, 9, 10],    "default_nights": 4, "country": "USA"},
    "miami":        {"flight_rt": 250,  "hotel_night": 200, "best_months": [11, 12, 1, 2, 3],"default_nights": 4, "country": "USA"},
    "hawaii":       {"flight_rt": 500,  "hotel_night": 250, "best_months": [4, 5, 9, 10],    "default_nights": 7, "country": "USA"},
}

DEFAULT_PROFILE = {
    "flight_rt": 600, "hotel_night": 150, "best_months": list(range(1, 13)),
    "default_nights": 5, "country": "Unknown",
}

# Domestic = same country as assumed origin (USA)
US_CITIES = {k for k, v in CITY_BUDGET_PROFILES.items() if v["country"] == "USA"}

MONTH_NAMES = {
    name.lower(): i
    for i, name in enumerate(calendar.month_name)
    if name
}
MONTH_ABBREVS = {
    name.lower(): i
    for i, name in enumerate(calendar.month_abbr)
    if name
}


# ── Heuristic extractors ─────────────────────────────────────────────────────

def _extract_destination(goal: str) -> Optional[str]:
    """Match 'to/in/visit <City>' patterns first, then fall back to known cities."""
    goal_lower = goal.lower()

    # First try directional patterns — "to Paris", "in Tokyo", "visit Rome"
    # This correctly handles "from London to Tokyo" by picking the *to* city.
    patterns = [
        r"(?:to|in|visit|visiting|explore|exploring)\s+([A-Z][a-zA-Z\s]{2,20}?)(?:\s+(?:for|with|on|and|from|,|\.)|$)",
    ]
    for pattern in patterns:
        m = re.search(pattern, goal)
        if m:
            candidate = m.group(1).strip()
            # Check if it matches a known city (case-insensitive)
            if candidate.lower() in CITY_BUDGET_PROFILES:
                return candidate.lower().title()
            return candidate

    # Fall back: scan for known cities (longest first to handle "new york" before "york")
    for city in sorted(CITY_BUDGET_PROFILES.keys(), key=len, reverse=True):
        if city in goal_lower:
            return city.title()
    return None


def _extract_origin(goal: str) -> Optional[str]:
    """Pattern 'from/leaving/departing <City>'."""
    patterns = [
        r"(?:from|leaving|departing|depart|flying from|out of)\s+([A-Za-z][a-zA-Z\s]{2,20}?)(?:\s+(?:to|for|on|and|,|\.)|$)",
    ]
    for pattern in patterns:
        m = re.search(pattern, goal, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return None


def _extract_budget(goal: str) -> Optional[float]:
    """Patterns like '$5000', 'under 3000', 'budget of 2k'."""
    patterns = [
        r"\$\s?([\d,]+(?:\.\d{1,2})?)\s?k?\b",                       # $5000, $5,000, $5k
        r"(?:budget|spend|spending|under|max|maximum|up\s+to)\s+\$?\s?([\d,]+(?:\.\d{1,2})?)\s?k?\b",
        r"([\d,]+(?:\.\d{1,2})?)\s?(?:dollars|usd)\b",
    ]
    for pattern in patterns:
        m = re.search(pattern, goal, re.IGNORECASE)
        if m:
            raw = m.group(1).replace(",", "")
            value = float(raw)
            # Check for "k" suffix
            full_match = m.group(0).lower()
            if full_match.rstrip().endswith("k"):
                value *= 1000
            return value
    return None


def _extract_duration(goal: str) -> Optional[int]:
    """'10 days', '2 weeks', 'a week', 'weekend', '3 nights'."""
    goal_lower = goal.lower()
    if "weekend" in goal_lower:
        return 2
    # X days/nights
    m = re.search(r"(\d+)\s*(?:day|night)s?\b", goal_lower)
    if m:
        return int(m.group(1))
    # X weeks
    m = re.search(r"(\d+)\s*weeks?\b", goal_lower)
    if m:
        return int(m.group(1)) * 7
    # "a week"
    if re.search(r"\ba\s+week\b", goal_lower):
        return 7
    return None


def _extract_dates(goal: str) -> tuple[Optional[str], Optional[str]]:
    """ISO dates, month names ('in April'), 'next month'.

    Returns (check_in_date, check_out_date) as ISO strings or None.
    """
    # ISO dates: 2026-03-15
    iso_dates = re.findall(r"\b(\d{4}-\d{2}-\d{2})\b", goal)
    if len(iso_dates) >= 2:
        return iso_dates[0], iso_dates[1]
    if len(iso_dates) == 1:
        return iso_dates[0], None

    goal_lower = goal.lower()

    # "next month"
    if "next month" in goal_lower:
        today = date.today()
        if today.month == 12:
            start = date(today.year + 1, 1, 1)
        else:
            start = date(today.year, today.month + 1, 1)
        return start.isoformat(), None

    # Month names: "in April", "in March 2026"
    for month_name, month_num in {**MONTH_NAMES, **MONTH_ABBREVS}.items():
        if month_num == 0:
            continue
        pattern = rf"\b(?:in\s+)?{re.escape(month_name)}\b"
        if re.search(pattern, goal_lower):
            today = date.today()
            year = today.year
            # If the month is in the past this year, use next year
            if month_num < today.month:
                year += 1
            elif month_num == today.month and today.day > 15:
                year += 1
            # Default to the 15th of the month (mid-month)
            start = date(year, month_num, 15)
            return start.isoformat(), None

    return None, None


def _extract_passengers(goal: str) -> Optional[int]:
    """'2 passengers', 'couple', 'my partner and I', 'family of 4'."""
    goal_lower = goal.lower()

    m = re.search(r"(\d+)\s*(?:passenger|people|person|traveler|adult)s?\b", goal_lower)
    if m:
        return int(m.group(1))

    m = re.search(r"(?:family|group)\s+of\s+(\d+)", goal_lower)
    if m:
        return int(m.group(1))

    if any(w in goal_lower for w in ["couple", "partner and i", "partner and me", "my partner", "two of us"]):
        return 2

    return None


def _extract_cabin_class(goal: str) -> Optional[str]:
    """'business class', 'first class', 'economy'."""
    goal_lower = goal.lower()
    if "first class" in goal_lower:
        return "first"
    if "business class" in goal_lower or "business" in goal_lower.split():
        # Distinguish "business class" from "business trip"
        if "business class" in goal_lower:
            return "business"
    if "premium economy" in goal_lower:
        return "premium_economy"
    if "economy" in goal_lower:
        return "economy"
    return None


def _infer_trip_purpose(goal: str) -> Optional[str]:
    """business keywords vs leisure keywords."""
    goal_lower = goal.lower()
    business_kw = ["business trip", "conference", "meeting", "client visit", "corporate", "work trip"]
    leisure_kw = ["vacation", "holiday", "honeymoon", "getaway", "sightseeing", "leisure", "explore", "relaxing"]
    if any(kw in goal_lower for kw in business_kw):
        return "business"
    if any(kw in goal_lower for kw in leisure_kw):
        return "leisure"
    return None


def _get_city_profile(city: Optional[str]) -> dict:
    """Look up city reference data, fallback to DEFAULT_PROFILE."""
    if not city:
        return DEFAULT_PROFILE
    return CITY_BUDGET_PROFILES.get(city.lower(), DEFAULT_PROFILE)


def _is_domestic(city: Optional[str]) -> bool:
    if not city:
        return False
    return city.lower() in US_CITIES


def _next_best_month(best_months: list[int]) -> date:
    """Return the 15th of the next upcoming best month."""
    today = date.today()
    for offset in range(0, 13):
        candidate_month = ((today.month - 1 + offset) % 12) + 1
        candidate_year = today.year + ((today.month - 1 + offset) // 12)
        if candidate_month in best_months:
            d = date(candidate_year, candidate_month, 15)
            if d > today + timedelta(days=7):  # at least a week out
                return d
    # Fallback: 2 weeks from now
    return today + timedelta(days=14)


# ── Main entry point ─────────────────────────────────────────────────────────

def extract_and_infer(goal: str, user_budget: Optional[float] = None) -> TrackedParams:
    """Parse goal text into TrackedParams with provenance on every field.

    Every value gets tagged with USER_STATED or INFERRED_DEFAULT plus a reason.
    """
    tp = TrackedParams()
    profile = DEFAULT_PROFILE

    # ── Destination ──────────────────────────────────────────────────────────
    dest = _extract_destination(goal)
    if dest:
        tp.destination_city = TrackedParam(
            value=dest, source=ParamSource.USER_STATED, reason="Mentioned in request"
        )
        profile = _get_city_profile(dest)

    # ── Origin ───────────────────────────────────────────────────────────────
    origin = _extract_origin(goal)
    if origin:
        tp.departure_city = TrackedParam(
            value=origin, source=ParamSource.USER_STATED, reason="Mentioned in request"
        )

    # ── Trip purpose ─────────────────────────────────────────────────────────
    purpose = _infer_trip_purpose(goal)
    if purpose:
        tp.trip_purpose = TrackedParam(
            value=purpose, source=ParamSource.USER_STATED, confidence=0.8,
            reason=f"Keywords suggest {purpose} trip",
        )
    else:
        tp.trip_purpose = TrackedParam(
            value="leisure", source=ParamSource.INFERRED_DEFAULT, confidence=0.6,
            reason="No business keywords detected — assuming leisure",
        )
        purpose = "leisure"

    # ── Duration ─────────────────────────────────────────────────────────────
    duration = _extract_duration(goal)
    if duration is not None:
        tp.duration_nights = TrackedParam(
            value=duration, source=ParamSource.USER_STATED, reason="Mentioned in request"
        )
    else:
        domestic = _is_domestic(dest)
        if purpose == "business":
            default_nights = 3
            reason = "Business trip default: 3 nights"
        elif domestic:
            default_nights = 4
            reason = "Domestic leisure default: 4 nights"
        else:
            default_nights = profile.get("default_nights", 5)
            reason = f"International leisure default for {dest or 'destination'}: {default_nights} nights"
        tp.duration_nights = TrackedParam(
            value=default_nights, source=ParamSource.INFERRED_DEFAULT,
            confidence=0.5, reason=reason,
        )
        duration = default_nights

    # ── Dates ────────────────────────────────────────────────────────────────
    check_in, check_out = _extract_dates(goal)
    if check_in:
        tp.check_in_date = TrackedParam(
            value=check_in, source=ParamSource.USER_STATED, reason="Mentioned in request"
        )
    else:
        best_months = profile.get("best_months", list(range(1, 13)))
        if purpose == "business":
            default_date = (date.today() + timedelta(days=14)).isoformat()
            reason = "Business default: 2 weeks from now"
        else:
            best_date = _next_best_month(best_months)
            default_date = best_date.isoformat()
            month_name = calendar.month_name[best_date.month]
            reason = f"Best value season for {dest or 'destination'}: {month_name}"
        tp.check_in_date = TrackedParam(
            value=default_date, source=ParamSource.INFERRED_DEFAULT,
            confidence=0.4, reason=reason,
        )
        check_in = default_date

    if check_out:
        tp.check_out_date = TrackedParam(
            value=check_out, source=ParamSource.USER_STATED, reason="Mentioned in request"
        )
    elif check_in and duration:
        co = date.fromisoformat(check_in) + timedelta(days=duration)
        tp.check_out_date = TrackedParam(
            value=co.isoformat(), source=ParamSource.INFERRED_DEFAULT,
            confidence=0.5, reason=f"Derived from check-in + {duration} nights",
        )

    # ── Passengers ───────────────────────────────────────────────────────────
    passengers = _extract_passengers(goal)
    if passengers is not None:
        tp.num_travelers = TrackedParam(
            value=passengers, source=ParamSource.USER_STATED, reason="Mentioned in request"
        )
    else:
        tp.num_travelers = TrackedParam(
            value=1, source=ParamSource.INFERRED_DEFAULT, confidence=0.6,
            reason="Default: 1 traveler",
        )
        passengers = 1

    # ── Cabin class ──────────────────────────────────────────────────────────
    cabin = _extract_cabin_class(goal)
    if cabin:
        tp.cabin_class = TrackedParam(
            value=cabin, source=ParamSource.USER_STATED, reason="Mentioned in request"
        )
    else:
        tp.cabin_class = TrackedParam(
            value="economy", source=ParamSource.INFERRED_DEFAULT, confidence=0.7,
            reason="Default: economy class",
        )

    # ── Budget ───────────────────────────────────────────────────────────────
    budget = _extract_budget(goal) or user_budget
    if budget is not None:
        tp.total_budget = TrackedParam(
            value=budget, source=ParamSource.USER_STATED, reason="Mentioned in request"
        )
        # Budget splitting: 40% flights, 50% hotels, 10% buffer
        tp.flight_budget = TrackedParam(
            value=round(budget * 0.4 * passengers, 2),
            source=ParamSource.INFERRED_DEFAULT, confidence=0.6,
            reason="40% of total budget allocated to flights",
        )
        tp.hotel_budget = TrackedParam(
            value=round(budget * 0.5, 2),
            source=ParamSource.INFERRED_DEFAULT, confidence=0.6,
            reason="50% of total budget allocated to hotels",
        )
    # If no budget: leave total_budget as None → agents should present tiers

    return tp


# ── Budget tier generator ────────────────────────────────────────────────────

@dataclass
class BudgetTier:
    name: str
    label: str
    flight_description: str
    hotel_description: str
    estimated_flight_cost: float
    estimated_hotel_per_night: float
    estimated_total: float


def generate_budget_tiers(
    destination: str,
    duration_nights: int,
    num_passengers: int = 1,
) -> list[BudgetTier]:
    """Generate 3 budget tiers for a destination.

    Returns Budget / Comfortable / Premium tiers using city reference data.
    """
    profile = _get_city_profile(destination)
    base_flight = profile["flight_rt"]
    base_hotel = profile["hotel_night"]

    tiers = []

    # Budget tier: 60% of median
    budget_flight = round(base_flight * 0.6)
    budget_hotel = round(base_hotel * 0.6)
    budget_total = round((budget_flight * num_passengers) + (budget_hotel * duration_nights))
    tiers.append(BudgetTier(
        name="budget",
        label="Budget",
        flight_description="Economy class, connecting flights, flexible timing",
        hotel_description="3-star hotel or well-rated hostel/guesthouse",
        estimated_flight_cost=budget_flight * num_passengers,
        estimated_hotel_per_night=budget_hotel,
        estimated_total=budget_total,
    ))

    # Comfortable tier: median
    comfort_flight = base_flight
    comfort_hotel = base_hotel
    comfort_total = round((comfort_flight * num_passengers) + (comfort_hotel * duration_nights))
    tiers.append(BudgetTier(
        name="comfortable",
        label="Comfortable",
        flight_description="Economy or premium economy, direct flights preferred",
        hotel_description="4-star hotel, central location, good amenities",
        estimated_flight_cost=comfort_flight * num_passengers,
        estimated_hotel_per_night=comfort_hotel,
        estimated_total=comfort_total,
    ))

    # Premium tier: 2.5x median flights, 2x median hotels
    premium_flight = round(base_flight * 2.5)
    premium_hotel = round(base_hotel * 2.0)
    premium_total = round((premium_flight * num_passengers) + (premium_hotel * duration_nights))
    tiers.append(BudgetTier(
        name="premium",
        label="Premium",
        flight_description="Business class, direct flights, flexible tickets",
        hotel_description="5-star hotel or luxury boutique, premium location",
        estimated_flight_cost=premium_flight * num_passengers,
        estimated_hotel_per_night=premium_hotel,
        estimated_total=premium_total,
    ))

    return tiers
