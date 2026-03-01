"""Read-only planning tools for underspecified trip requests.

These tools help agents present options instead of asking questions.
They are NOT in APPROVAL_REQUIRED_TOOLS — they don't spend money.
"""
from dataclasses import asdict
from datetime import date, timedelta

from core.intent import generate_budget_tiers, _get_city_profile


# ── Tool definitions (Anthropic API format) ──────────────────────────────────

SUGGEST_TRIP_OPTIONS_DEF = {
    "name": "suggest_trip_options",
    "description": (
        "Generate Budget / Comfortable / Premium tier options for a trip when "
        "the user hasn't specified a budget. Use this to show concrete price "
        "ranges instead of asking 'what's your budget?'. Returns 3 tiers with "
        "estimated costs for flights, hotels, and total."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "destination": {
                "type": "string",
                "description": "Destination city name",
            },
            "duration_nights": {
                "type": "integer",
                "description": "Number of nights for the stay",
                "default": 5,
            },
            "num_passengers": {
                "type": "integer",
                "description": "Number of travelers",
                "default": 1,
            },
        },
        "required": ["destination"],
    },
}

SUGGEST_ALTERNATIVE_DATES_DEF = {
    "name": "suggest_alternative_dates",
    "description": (
        "Suggest alternative travel dates that could give better prices or "
        "experiences. Use when search results are expensive or mediocre, "
        "or when the user might be flexible on dates. Returns date alternatives "
        "with estimated savings and seasonal notes."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "destination": {
                "type": "string",
                "description": "Destination city name",
            },
            "original_date": {
                "type": "string",
                "description": "Original travel date in YYYY-MM-DD format",
            },
            "duration_nights": {
                "type": "integer",
                "description": "Number of nights",
                "default": 5,
            },
        },
        "required": ["destination", "original_date"],
    },
}


# ── Tool handlers ────────────────────────────────────────────────────────────

async def suggest_trip_options(
    destination: str,
    duration_nights: int = 5,
    num_passengers: int = 1,
) -> list[dict]:
    """Generate 3 budget tiers for the destination."""
    tiers = generate_budget_tiers(destination, duration_nights, num_passengers)
    return [asdict(tier) for tier in tiers]


async def suggest_alternative_dates(
    destination: str,
    original_date: str,
    duration_nights: int = 5,
) -> list[dict]:
    """Suggest date shifts that could improve results.

    In mock mode, returns synthetic suggestions based on city profile data.
    With real APIs later, this would call flexible-date search endpoints.
    """
    profile = _get_city_profile(destination)
    best_months = profile.get("best_months", list(range(1, 13)))

    try:
        orig = date.fromisoformat(original_date)
    except ValueError:
        return [{"error": f"Invalid date format: {original_date}"}]

    alternatives = []

    # ±3 days shifts
    for delta in [-3, -2, 2, 3]:
        alt_date = orig + timedelta(days=delta)
        in_best = alt_date.month in best_months
        savings_pct = 12 if in_best else 5
        alternatives.append({
            "check_in": alt_date.isoformat(),
            "check_out": (alt_date + timedelta(days=duration_nights)).isoformat(),
            "savings_estimate_pct": savings_pct,
            "note": (
                f"{'Peak season' if in_best else 'Off-peak'} for {destination}. "
                f"Estimated {savings_pct}% savings vs original date."
            ),
            "is_best_season": in_best,
        })

    # Best-month suggestion if original isn't in best months
    if orig.month not in best_months and best_months:
        best_month = best_months[0]
        year = orig.year if best_month >= orig.month else orig.year + 1
        best_date = date(year, best_month, 15)
        alternatives.append({
            "check_in": best_date.isoformat(),
            "check_out": (best_date + timedelta(days=duration_nights)).isoformat(),
            "savings_estimate_pct": 20,
            "note": (
                f"Best value season for {destination}. "
                f"Estimated 20% savings and optimal weather/activities."
            ),
            "is_best_season": True,
        })

    return alternatives
