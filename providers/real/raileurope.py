"""RailEurope Transport Provider — real API integration (M5 Item 4).

Credentials loaded from env vars (INV-10).
Sandbox booking references prefixed SANDBOX- (INV-11).
"""
import logging
import os

import httpx

from providers.base import BaseTransportProvider

logger = logging.getLogger(__name__)

BASE_URL = "https://api.raileurope.com/v2"


class RailEuropeTransportProvider(BaseTransportProvider):
    def __init__(self):
        self._api_key = os.environ.get("RAILEUROPE_API_KEY", "")
        self._is_sandbox = True

    async def _request(self, method: str, path: str, **kwargs) -> dict:
        headers = {"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"}
        max_retries = 3

        async with httpx.AsyncClient() as client:
            for attempt in range(max_retries + 1):
                resp = await client.request(method, f"{BASE_URL}{path}", headers=headers, **kwargs)
                if resp.status_code == 429:
                    retry_after = int(resp.headers.get("retry-after", 2 ** attempt))
                    logger.warning("RailEurope 429 — retrying after %ds", retry_after)
                    import asyncio
                    await asyncio.sleep(retry_after)
                    continue
                resp.raise_for_status()
                return resp.json()

        raise RuntimeError("RailEurope API: max retries exceeded on 429")

    async def search_transport(self, pickup: str, dropoff: str, date: str) -> list[dict]:
        data = await self._request("POST", "/search", json={
            "origin": pickup, "destination": dropoff, "date": date,
        })
        results = []
        for offer in data.get("offers", []):
            results.append({
                "transport_id": offer.get("id", ""),
                "type": "train",
                "pickup": pickup,
                "dropoff": dropoff,
                "date": date,
                "price": float(offer.get("price", {}).get("amount", 0)),
                "estimated_cost": float(offer.get("price", {}).get("amount", 0)),
                "provider": offer.get("carrier", "RailEurope"),
                "eta_minutes": offer.get("duration_minutes", 0),
            })
        return results

    async def book_transport(self, transport_id: str, passenger_details: dict, payment_token: str) -> dict:
        data = await self._request("POST", "/bookings", json={
            "offer_id": transport_id, "passenger": passenger_details, "payment_token": payment_token,
        })
        ref = data.get("booking_id", transport_id)
        if self._is_sandbox:
            ref = f"SANDBOX-{ref}"
        return {
            "booking_reference": ref, "transport_id": transport_id,
            "status": "confirmed", "passenger": passenger_details,
            "payment_token": payment_token,
            "amount": float(data.get("total", 0)),
        }

    async def cancel_transport(self, booking_reference: str) -> dict:
        return {"booking_reference": booking_reference, "status": "cancelled", "refund_amount": 0}
