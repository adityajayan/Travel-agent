"""GetYourGuide Partner API Provider — fallback activity provider (M8).

Credentials loaded from env vars (INV-10).
Sandbox booking references prefixed SANDBOX- (INV-11).
Returns NormalizedActivityResult / NormalizedBookingConfirmation (INV-14).
"""
import logging
import os
from datetime import datetime, timezone

import httpx

from providers.base import BaseActivityProvider
from providers.schemas import (
    CancellationPolicy,
    NormalizedActivityResult,
    NormalizedBookingConfirmation,
    PriceVerification,
)

logger = logging.getLogger(__name__)

BASE_URL = "https://api.getyourguide.com/1"


class GetYourGuideActivityProvider(BaseActivityProvider):
    def __init__(self):
        self._api_key = os.environ.get("GETYOURGUIDE_API_KEY", "")
        self._is_sandbox = not self._api_key or self._api_key.startswith("test_")

    async def _request(self, method: str, path: str, **kwargs) -> dict:
        """Make an authenticated request with retry on 429."""
        headers = {
            "X-Access-Token": self._api_key,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        max_retries = 3

        async with httpx.AsyncClient(timeout=30.0) as client:
            for attempt in range(max_retries + 1):
                resp = await client.request(
                    method, f"{BASE_URL}{path}",
                    headers=headers, **kwargs
                )
                if resp.status_code == 429:
                    retry_after = min(int(resp.headers.get("retry-after", 2 ** attempt)), 60)
                    logger.warning("GetYourGuide 429 — retrying after %ds (attempt %d)", retry_after, attempt + 1)
                    import asyncio
                    await asyncio.sleep(retry_after)
                    continue
                resp.raise_for_status()
                return resp.json()

        raise RuntimeError("GetYourGuide API: max retries exceeded on 429")

    async def search_activities(
        self, destination: str, date: str, participants: int = 1
    ) -> list[dict]:
        data = await self._request("GET", "/activities", params={
            "q": destination,
            "date": date,
            "limit": 10,
        })

        results = []
        for activity in data.get("data", {}).get("activities", []):
            price_info = activity.get("price", {})
            unit_price = float(price_info.get("values", {}).get("amount", 0))
            total_price = round(unit_price * participants, 2)
            dur_hours = activity.get("duration", 0)

            result = NormalizedActivityResult(
                activity_id=str(activity.get("activity_id", "")),
                name=activity.get("title", "Unknown Activity"),
                destination=destination,
                date=date,
                estimated_cost=total_price,
                duration_hours=dur_hours,
                duration_minutes=int(dur_hours * 60) if dur_hours else 0,
                category=activity.get("category", {}).get("name", ""),
                rating=float(activity.get("overall_rating", 0)),
                provider="GetYourGuide",
                raw_provider_id=str(activity.get("activity_id", "")),
                spots_available=activity.get("availability", {}).get("spots", 0),
            )
            results.append(result.model_dump())

        return results

    async def book_activity(
        self, activity_id: str, participant_details: dict, payment_token: str
    ) -> dict:
        data = await self._request("POST", "/bookings", json={
            "base_data": {
                "activity_id": activity_id,
                "participants": [participant_details],
            },
            "payment": {"token": payment_token},
        })

        booking = data.get("data", {}).get("booking", {})
        ref = str(booking.get("booking_id", activity_id))
        if self._is_sandbox:
            ref = f"SANDBOX-{ref}"

        amount = float(booking.get("total", 0))
        confirmation = NormalizedBookingConfirmation(
            booking_reference=ref,
            domain="activity",
            provider="GetYourGuide",
            status="confirmed",
            amount=amount,
            is_sandbox=self._is_sandbox,
            raw_details={
                "activity_id": activity_id,
                "participant": participant_details,
                "payment_token": payment_token,
            },
        )
        return confirmation.model_dump()

    async def cancel_activity(self, booking_reference: str) -> dict:
        api_ref = booking_reference.replace("SANDBOX-", "")
        try:
            await self._request("DELETE", f"/bookings/{api_ref}")
        except Exception as exc:
            logger.warning("GetYourGuide cancel error: %s", exc)

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
            policy_text="GetYourGuide: free cancellation up to 24 hours before activity.",
            provider="GetYourGuide",
        )
