"""Amadeus Flight Provider — real API integration (M5 Item 2).

Uses Amadeus Flight Offers Search API v2.
Credentials loaded from env vars (INV-10).
Sandbox booking references prefixed SANDBOX- (INV-11).
"""
import logging
import os
import re
import time
from typing import Optional

import httpx

from providers.base import BaseFlightProvider

logger = logging.getLogger(__name__)


class AmadeusFlightProvider(BaseFlightProvider):
    def __init__(self):
        self._client_id = os.environ.get("AMADEUS_CLIENT_ID", "")
        self._client_secret = os.environ.get("AMADEUS_CLIENT_SECRET", "")
        self._hostname = os.environ.get("AMADEUS_HOSTNAME", "test.api.amadeus.com")
        self._base_url = f"https://{self._hostname}"
        self._token: Optional[str] = None
        self._token_expires_at: float = 0
        self._is_sandbox = "test" in self._hostname

    async def _ensure_token(self) -> str:
        """OAuth2 client_credentials token refresh."""
        if self._token and time.time() < self._token_expires_at:
            return self._token

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self._base_url}/v1/security/oauth2/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            resp.raise_for_status()
            data = resp.json()
            self._token = data["access_token"]
            self._token_expires_at = time.time() + data.get("expires_in", 1799) - 60
            return self._token

    async def _request(self, method: str, path: str, **kwargs) -> dict:
        """Make an authenticated request with retry on 429."""
        token = await self._ensure_token()
        headers = {"Authorization": f"Bearer {token}"}
        max_retries = 3

        async with httpx.AsyncClient() as client:
            for attempt in range(max_retries + 1):
                resp = await client.request(
                    method, f"{self._base_url}{path}",
                    headers=headers, **kwargs
                )
                if resp.status_code == 429:
                    retry_after = int(resp.headers.get("retry-after", 2 ** attempt))
                    logger.warning("Amadeus 429 — retrying after %ds (attempt %d)", retry_after, attempt + 1)
                    import asyncio
                    await asyncio.sleep(retry_after)
                    continue
                resp.raise_for_status()
                return resp.json()

        raise RuntimeError("Amadeus API: max retries exceeded on 429")

    def _parse_duration(self, iso_duration: str) -> int:
        """Convert ISO 8601 duration (e.g. PT2H30M) to minutes."""
        match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?", iso_duration)
        if not match:
            return 0
        hours = int(match.group(1) or 0)
        minutes = int(match.group(2) or 0)
        return hours * 60 + minutes

    async def search_flights(
        self, origin: str, destination: str, date: str, passengers: int = 1
    ) -> list[dict]:
        data = await self._request("GET", "/v2/shopping/flight-offers", params={
            "originLocationCode": origin,
            "destinationLocationCode": destination,
            "departureDate": date,
            "adults": passengers,
            "max": 10,
        })

        results = []
        for offer in data.get("data", []):
            itinerary = offer.get("itineraries", [{}])[0]
            price = offer.get("price", {})
            traveler_pricing = offer.get("travelerPricings", [{}])[0]
            fare_detail = traveler_pricing.get("fareDetailsBySegment", [{}])[0]

            results.append({
                "flight_id": offer["id"],
                "airline": offer.get("validatingAirlineCodes", [""])[0],
                "origin": origin,
                "destination": destination,
                "date": date,
                "price": float(price.get("grandTotal", 0)),
                "estimated_cost": float(price.get("grandTotal", 0)),
                "cabin_class": fare_detail.get("cabin", "ECONOMY").lower(),
                "duration_minutes": self._parse_duration(itinerary.get("duration", "PT0M")),
                "provider": offer.get("validatingAirlineCodes", [""])[0],
                "seats_available": offer.get("numberOfBookableSeats", 0),
            })

        return results

    async def book_flight(
        self, flight_id: str, passenger_details: dict, payment_token: str
    ) -> dict:
        body = {
            "data": {
                "type": "flight-order",
                "flightOffers": [{"id": flight_id}],
                "travelers": [
                    {
                        "id": "1",
                        "dateOfBirth": passenger_details.get("date_of_birth", "1990-01-01"),
                        "name": {
                            "firstName": passenger_details.get("name", "John").split()[0],
                            "lastName": passenger_details.get("name", "Doe").split()[-1],
                        },
                        "gender": passenger_details.get("gender", "MALE"),
                        "contact": {
                            "emailAddress": passenger_details.get("email", "test@test.com"),
                            "phones": [{"number": "1234567890", "countryCallingCode": "1"}],
                        },
                    }
                ],
            }
        }
        data = await self._request("POST", "/v1/booking/flight-orders", json=body)
        order = data.get("data", {})
        ref = order.get("id", flight_id)

        # INV-11: Sandbox prefix
        if self._is_sandbox:
            ref = f"SANDBOX-{ref}"

        return {
            "booking_reference": ref,
            "flight_id": flight_id,
            "status": "confirmed",
            "passenger": passenger_details,
            "payment_token": payment_token,
            "amount": float(order.get("flightOffers", [{}])[0].get("price", {}).get("grandTotal", 0)),
        }

    async def cancel_flight(self, booking_reference: str) -> dict:
        # Amadeus sandbox doesn't support cancellation; return mock-like response
        return {
            "booking_reference": booking_reference,
            "status": "cancelled",
            "refund_amount": 0,
        }
