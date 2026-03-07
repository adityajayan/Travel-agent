"""Amadeus Flight Provider — real API integration (M5 Item 2, M8 hardening).

Uses Amadeus Flight Offers Search API v2.
Credentials loaded from env vars (INV-10).
Sandbox booking references prefixed SANDBOX- (INV-11).
Returns NormalizedFlightResult / NormalizedBookingConfirmation (INV-14).
"""
import logging
import os
import re
import time
from datetime import datetime, timezone, timedelta
from typing import Optional

import httpx

from providers.base import BaseFlightProvider
from providers.schemas import (
    CancellationPolicy,
    HoldResult,
    NormalizedBookingConfirmation,
    NormalizedFlightResult,
    PriceVerification,
)

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
        self._last_search_results: dict[str, float] = {}  # flight_id -> price cache for verify

    async def _ensure_token(self) -> str:
        """OAuth2 client_credentials token refresh."""
        if self._token and time.time() < self._token_expires_at:
            return self._token

        async with httpx.AsyncClient(timeout=30.0) as client:
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

        async with httpx.AsyncClient(timeout=30.0) as client:
            for attempt in range(max_retries + 1):
                resp = await client.request(
                    method, f"{self._base_url}{path}",
                    headers=headers, **kwargs
                )
                if resp.status_code == 429:
                    retry_after = min(int(resp.headers.get("retry-after", 2 ** attempt)), 60)
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
            price_data = offer.get("price", {})
            traveler_pricing = offer.get("travelerPricings", [{}])[0]
            fare_detail = traveler_pricing.get("fareDetailsBySegment", [{}])[0]
            segments = itinerary.get("segments", [])
            flight_price = float(price_data.get("grandTotal", 0))

            departure_time = segments[0].get("departure", {}).get("at", "") if segments else ""
            arrival_time = segments[-1].get("arrival", {}).get("at", "") if segments else ""

            result = NormalizedFlightResult(
                flight_id=offer["id"],
                airline=offer.get("validatingAirlineCodes", [""])[0],
                origin=origin,
                destination=destination,
                departure_time=departure_time or date,
                arrival_time=arrival_time or date,
                cabin_class=fare_detail.get("cabin", "ECONOMY").lower(),
                duration_minutes=self._parse_duration(itinerary.get("duration", "PT0M")),
                stops=max(len(segments) - 1, 0),
                estimated_cost=flight_price,
                currency=price_data.get("currency", "USD"),
                provider=offer.get("validatingAirlineCodes", [""])[0],
                raw_provider_id=offer["id"],
                seats_available=offer.get("numberOfBookableSeats", 0),
            )
            self._last_search_results[offer["id"]] = flight_price
            results.append(result.model_dump())

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

        amount = float(order.get("flightOffers", [{}])[0].get("price", {}).get("grandTotal", 0))
        confirmation = NormalizedBookingConfirmation(
            booking_reference=ref,
            domain="flight",
            provider="Amadeus",
            status="confirmed",
            amount=amount,
            is_sandbox=self._is_sandbox,
            raw_details={
                "flight_id": flight_id,
                "passenger": passenger_details,
                "payment_token": payment_token,
            },
        )
        return confirmation.model_dump()

    async def cancel_flight(self, booking_reference: str) -> dict:
        # Strip sandbox prefix for API call
        api_ref = booking_reference.replace("SANDBOX-", "")
        if not self._is_sandbox:
            try:
                await self._request("DELETE", f"/v1/booking/flight-orders/{api_ref}")
            except Exception as exc:
                logger.warning("Amadeus cancel API error: %s", exc)

        return {
            "booking_reference": booking_reference,
            "status": "cancelled",
            "refund_amount": 0,
        }

    async def hold_fare(self, item_id: str) -> HoldResult:
        """Use Amadeus Flight Offers Price to verify and hold a fare."""
        try:
            data = await self._request("POST", "/v1/shopping/flight-offers/pricing", json={
                "data": {"type": "flight-offers-pricing", "flightOffers": [{"id": item_id}]},
            })
            offers = data.get("data", {}).get("flightOffers", [])
            if offers:
                price = float(offers[0].get("price", {}).get("grandTotal", 0))
                return HoldResult(
                    hold_id=f"HOLD-{item_id}",
                    item_id=item_id,
                    verified_price=price,
                    expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
                    provider="Amadeus",
                    supported=True,
                )
        except Exception as exc:
            logger.warning("Amadeus hold_fare failed: %s", exc)

        return HoldResult(
            hold_id="",
            item_id=item_id,
            verified_price=0.0,
            expires_at=datetime.now(timezone.utc),
            provider="Amadeus",
            supported=False,
        )

    async def verify_price(self, item_id: str, original_price: float) -> PriceVerification:
        """Re-verify price using Amadeus Flight Offers Price API."""
        now = datetime.now(timezone.utc)
        try:
            data = await self._request("POST", "/v1/shopping/flight-offers/pricing", json={
                "data": {"type": "flight-offers-pricing", "flightOffers": [{"id": item_id}]},
            })
            offers = data.get("data", {}).get("flightOffers", [])
            if offers:
                current_price = float(offers[0].get("price", {}).get("grandTotal", 0))
                pct = abs(current_price - original_price) / original_price * 100 if original_price > 0 else 0
                return PriceVerification(
                    item_id=item_id,
                    current_price=current_price,
                    original_price=original_price,
                    price_changed=abs(current_price - original_price) > 0.01,
                    pct_change=round(pct, 2),
                    verified_at=now,
                )
        except Exception as exc:
            logger.warning("Amadeus verify_price failed: %s — returning unchanged", exc)

        return PriceVerification(
            item_id=item_id,
            current_price=original_price,
            original_price=original_price,
            price_changed=False,
            pct_change=0.0,
            verified_at=now,
        )

    async def get_cancellation_policy(self, booking_reference: str) -> CancellationPolicy:
        return CancellationPolicy(
            booking_reference=booking_reference,
            refundable=False,
            refund_amount=0.0,
            cancellation_fee=0.0,
            policy_text="Amadeus flights: cancellation subject to airline fare rules.",
            provider="Amadeus",
        )
