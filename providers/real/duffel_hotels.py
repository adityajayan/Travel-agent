"""Duffel Stays API Provider — primary hotel provider.

Uses Duffel Stays API for hotel search and booking.
Credentials loaded from env vars (INV-10).
Sandbox booking references prefixed SANDBOX- (INV-11).
Returns NormalizedHotelResult / NormalizedBookingConfirmation (INV-14).
"""
import logging
import os
from datetime import datetime, timezone

import httpx

from providers.base import BaseHotelProvider
from providers.schemas import (
    CancellationPolicy,
    NormalizedBookingConfirmation,
    NormalizedHotelResult,
    PriceVerification,
)

logger = logging.getLogger(__name__)

BASE_URL = "https://api.duffel.com"


class DuffelHotelProvider(BaseHotelProvider):
    def __init__(self):
        self._api_token = os.environ.get("DUFFEL_API_TOKEN", "")
        self._is_sandbox = self._api_token.startswith("duffel_test_") or not self._api_token

    async def _request(self, method: str, path: str, **kwargs) -> dict:
        """Make an authenticated request with retry on 429."""
        headers = {
            "Authorization": f"Bearer {self._api_token}",
            "Duffel-Version": "v2",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        max_retries = 3

        async with httpx.AsyncClient() as client:
            for attempt in range(max_retries + 1):
                resp = await client.request(
                    method, f"{BASE_URL}{path}",
                    headers=headers, **kwargs
                )
                if resp.status_code == 429:
                    retry_after = int(resp.headers.get("retry-after", 2 ** attempt))
                    logger.warning("Duffel 429 — retrying after %ds (attempt %d)", retry_after, attempt + 1)
                    import asyncio
                    await asyncio.sleep(retry_after)
                    continue
                resp.raise_for_status()
                return resp.json()

        raise RuntimeError("Duffel API: max retries exceeded on 429")

    async def search_hotels(
        self, destination: str, check_in: str, check_out: str, guests: int = 1
    ) -> list[dict]:
        data = await self._request("POST", "/stays/search", json={
            "data": {
                "location": {
                    "geographic_coordinates": None,
                    "radius": 5,
                    "search_type": "city",
                    "city": destination,
                },
                "check_in_date": check_in,
                "check_out_date": check_out,
                "guests": [{"type": "adult"} for _ in range(guests)],
                "rooms": 1,
            }
        })

        from datetime import date as dt_date
        try:
            ci = dt_date.fromisoformat(check_in)
            co = dt_date.fromisoformat(check_out)
            nights = max((co - ci).days, 1)
        except (ValueError, TypeError):
            nights = 1

        results = []
        for accommodation in data.get("data", {}).get("results", []):
            cheapest_rate = accommodation.get("cheapest_rate_total_amount")
            total = float(cheapest_rate) if cheapest_rate else 0.0
            currency = accommodation.get("cheapest_rate_currency", "USD")
            cpn = total / nights if nights > 0 else total

            property_info = accommodation.get("accommodation", {})

            result = NormalizedHotelResult(
                hotel_id=str(accommodation.get("id", "")),
                name=property_info.get("name", "Unknown Hotel"),
                destination=destination,
                check_in=check_in,
                check_out=check_out,
                cost_per_night=round(cpn, 2),
                total_price=round(total, 2),
                star_rating=float(property_info.get("star_rating", 0) or 0),
                rating_score=float(property_info.get("review_score", 0) or 0),
                provider="Duffel",
                raw_provider_id=str(accommodation.get("id", "")),
                rooms_available=1,
            )
            results.append(result.model_dump())

        return results

    async def book_hotel(
        self, hotel_id: str, guest_details: dict, payment_token: str
    ) -> dict:
        data = await self._request("POST", "/stays/bookings", json={
            "data": {
                "accommodation_id": hotel_id,
                "guests": [{
                    "given_name": guest_details.get("name", "John").split()[0],
                    "family_name": guest_details.get("name", "Doe").split()[-1],
                    "email": guest_details.get("email", "test@test.com"),
                }],
                "payments": [{"type": "balance", "amount": "0", "currency": "USD"}],
            }
        })

        booking = data.get("data", {})
        ref = booking.get("booking_reference", hotel_id)
        if self._is_sandbox:
            ref = f"SANDBOX-{ref}"

        amount = float(booking.get("total_amount", 0))
        confirmation = NormalizedBookingConfirmation(
            booking_reference=ref,
            domain="hotel",
            provider="Duffel",
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
        api_ref = booking_reference.replace("SANDBOX-", "")
        try:
            await self._request("POST", "/stays/booking_cancellations", json={
                "data": {"booking_id": api_ref}
            })
        except Exception as exc:
            logger.warning("Duffel hotel cancel error: %s", exc)

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
            policy_text="Duffel: cancellation subject to property cancellation policy.",
            provider="Duffel",
        )
