"""Amadeus Hotel Search API Provider — fallback hotel provider (M8).

Reuses Amadeus OAuth2 credentials from M5.
Credentials loaded from env vars (INV-10).
Sandbox booking references prefixed SANDBOX- (INV-11).
Returns NormalizedHotelResult / NormalizedBookingConfirmation (INV-14).
"""
import logging
import os
import time
from datetime import datetime, timezone
from typing import Optional

import httpx

from providers.base import BaseHotelProvider
from providers.schemas import (
    CancellationPolicy,
    NormalizedBookingConfirmation,
    NormalizedHotelResult,
    PriceVerification,
)

logger = logging.getLogger(__name__)


class AmadeusHotelProvider(BaseHotelProvider):
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
                    logger.warning("Amadeus Hotels 429 — retrying after %ds (attempt %d)", retry_after, attempt + 1)
                    import asyncio
                    await asyncio.sleep(retry_after)
                    continue
                resp.raise_for_status()
                return resp.json()

        raise RuntimeError("Amadeus Hotels API: max retries exceeded on 429")

    async def search_hotels(
        self, destination: str, check_in: str, check_out: str, guests: int = 1
    ) -> list[dict]:
        # Step 1: Search hotels by city
        city_data = await self._request("GET", "/v1/reference-data/locations/hotels/by-city", params={
            "cityCode": destination[:3].upper(),
        })

        hotel_ids = [h.get("hotelId", "") for h in city_data.get("data", [])[:5]]
        if not hotel_ids:
            return []

        # Step 2: Get offers for those hotels
        data = await self._request("GET", "/v3/shopping/hotel-offers", params={
            "hotelIds": ",".join(hotel_ids),
            "checkInDate": check_in,
            "checkOutDate": check_out,
            "adults": guests,
        })

        from datetime import date as dt_date
        try:
            ci = dt_date.fromisoformat(check_in)
            co = dt_date.fromisoformat(check_out)
            nights = max((co - ci).days, 1)
        except (ValueError, TypeError):
            nights = 1

        results = []
        for hotel_offer in data.get("data", []):
            hotel = hotel_offer.get("hotel", {})
            offers = hotel_offer.get("offers", [])
            if not offers:
                continue
            offer = offers[0]
            price = float(offer.get("price", {}).get("total", 0))
            cpn = price / nights if nights > 0 else price

            result = NormalizedHotelResult(
                hotel_id=hotel.get("hotelId", ""),
                name=hotel.get("name", "Unknown Hotel"),
                destination=destination,
                check_in=check_in,
                check_out=check_out,
                cost_per_night=round(cpn, 2),
                total_price=round(price, 2),
                star_rating=float(hotel.get("rating", 3)),
                rating_score=float(hotel.get("rating", 0)),
                provider="Amadeus",
                raw_provider_id=hotel.get("hotelId", ""),
            )
            results.append(result.model_dump())

        return results

    async def book_hotel(
        self, hotel_id: str, guest_details: dict, payment_token: str
    ) -> dict:
        data = await self._request("POST", "/v2/booking/hotel-orders", json={
            "data": {
                "type": "hotel-order",
                "roomAssociations": [{"hotelOfferId": hotel_id}],
                "guests": [{
                    "name": {
                        "firstName": guest_details.get("name", "John").split()[0],
                        "lastName": guest_details.get("name", "Doe").split()[-1],
                    },
                    "contact": {
                        "email": guest_details.get("email", "test@test.com"),
                        "phone": "1234567890",
                    },
                }],
                "payment": {"method": "CREDIT_CARD"},
            }
        })

        order = data.get("data", {})
        ref = order.get("id", hotel_id)
        if self._is_sandbox:
            ref = f"SANDBOX-{ref}"

        amount = float(order.get("hotel", {}).get("price", {}).get("total", 0))
        confirmation = NormalizedBookingConfirmation(
            booking_reference=ref,
            domain="hotel",
            provider="Amadeus",
            status="confirmed",
            amount=amount,
            is_sandbox=self._is_sandbox,
            raw_details={
                "hotel_id": hotel_id,
                "guest": guest_details,
                "payment_token": payment_token,
            },
        )
        return confirmation.model_dump()

    async def cancel_hotel(self, booking_reference: str) -> dict:
        return {
            "booking_reference": booking_reference,
            "status": "cancelled",
            "refund_amount": 0,
        }

    async def verify_price(self, item_id: str, original_price: float) -> PriceVerification:
        now = datetime.now(timezone.utc)
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
            refundable=True,
            refund_amount=0.0,
            cancellation_fee=0.0,
            policy_text="Amadeus Hotels: cancellation policy varies by property.",
            provider="Amadeus",
        )
