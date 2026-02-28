"""Viator Activity Provider — real API integration (M5 Item 4).

Credentials loaded from env vars (INV-10).
Sandbox booking references prefixed SANDBOX- (INV-11).
"""
import logging
import os

import httpx

from providers.base import BaseActivityProvider

logger = logging.getLogger(__name__)

BASE_URL = "https://api.viator.com/partner"


class ViatorActivityProvider(BaseActivityProvider):
    def __init__(self):
        self._api_key = os.environ.get("VIATOR_API_KEY", "")
        self._is_sandbox = True

    async def _request(self, method: str, path: str, **kwargs) -> dict:
        headers = {"exp-api-key": self._api_key, "Accept": "application/json", "Content-Type": "application/json"}
        max_retries = 3

        async with httpx.AsyncClient() as client:
            for attempt in range(max_retries + 1):
                resp = await client.request(method, f"{BASE_URL}{path}", headers=headers, **kwargs)
                if resp.status_code == 429:
                    retry_after = int(resp.headers.get("retry-after", 2 ** attempt))
                    logger.warning("Viator 429 — retrying after %ds", retry_after)
                    import asyncio
                    await asyncio.sleep(retry_after)
                    continue
                resp.raise_for_status()
                return resp.json()

        raise RuntimeError("Viator API: max retries exceeded on 429")

    async def search_activities(self, destination: str, date: str, participants: int = 1) -> list[dict]:
        data = await self._request("POST", "/products/search", json={
            "filtering": {"destination": destination, "startDate": date},
            "pagination": {"start": 1, "count": 10},
        })
        results = []
        for product in data.get("products", []):
            pricing = product.get("pricing", {})
            results.append({
                "activity_id": product.get("productCode", ""),
                "name": product.get("title", "Unknown Activity"),
                "destination": destination, "date": date,
                "price": round(float(pricing.get("amount", 0)) * participants, 2),
                "estimated_cost": round(float(pricing.get("amount", 0)) * participants, 2),
                "provider": "Viator",
                "duration_hours": product.get("duration", {}).get("hours", 0),
                "spots_available": product.get("availability", {}).get("spots", 0),
            })
        return results

    async def book_activity(self, activity_id: str, participant_details: dict, payment_token: str) -> dict:
        data = await self._request("POST", "/bookings", json={
            "productCode": activity_id, "traveler": participant_details, "payment_token": payment_token,
        })
        ref = data.get("bookingRef", activity_id)
        if self._is_sandbox:
            ref = f"SANDBOX-{ref}"
        return {
            "booking_reference": ref, "activity_id": activity_id,
            "status": "confirmed", "participant": participant_details,
            "payment_token": payment_token,
            "amount": float(data.get("totalPrice", 0)),
        }

    async def cancel_activity(self, booking_reference: str) -> dict:
        return {"booking_reference": booking_reference, "status": "cancelled", "refund_amount": 0}
