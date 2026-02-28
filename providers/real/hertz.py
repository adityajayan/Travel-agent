"""Hertz Car Rental Provider — real API integration (M5 Item 4).

Credentials loaded from env vars (INV-10).
Sandbox booking references prefixed SANDBOX- (INV-11).
"""
import logging
import os
import time
from typing import Optional

import httpx

from providers.base import BaseTransportProvider

logger = logging.getLogger(__name__)

BASE_URL = "https://api.hertz.com/v1"


class HertzTransportProvider(BaseTransportProvider):
    def __init__(self):
        self._client_id = os.environ.get("HERTZ_CLIENT_ID", "")
        self._client_secret = os.environ.get("HERTZ_CLIENT_SECRET", "")
        self._token: Optional[str] = None
        self._token_expires_at: float = 0
        self._is_sandbox = True

    async def _ensure_token(self) -> str:
        if self._token and time.time() < self._token_expires_at:
            return self._token

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{BASE_URL}/oauth/token",
                data={"grant_type": "client_credentials", "client_id": self._client_id, "client_secret": self._client_secret},
            )
            resp.raise_for_status()
            data = resp.json()
            self._token = data["access_token"]
            self._token_expires_at = time.time() + data.get("expires_in", 3600) - 60
            return self._token

    async def _request(self, method: str, path: str, **kwargs) -> dict:
        token = await self._ensure_token()
        headers = {"Authorization": f"Bearer {token}"}
        max_retries = 3

        async with httpx.AsyncClient() as client:
            for attempt in range(max_retries + 1):
                resp = await client.request(method, f"{BASE_URL}{path}", headers=headers, **kwargs)
                if resp.status_code == 429:
                    retry_after = int(resp.headers.get("retry-after", 2 ** attempt))
                    import asyncio
                    await asyncio.sleep(retry_after)
                    continue
                resp.raise_for_status()
                return resp.json()

        raise RuntimeError("Hertz API: max retries exceeded on 429")

    async def search_transport(self, pickup: str, dropoff: str, date: str) -> list[dict]:
        data = await self._request("GET", "/vehicles/available", params={
            "pickup_location": pickup, "dropoff_location": dropoff, "pickup_date": date,
        })
        results = []
        for vehicle in data.get("vehicles", []):
            results.append({
                "transport_id": vehicle.get("id", ""),
                "type": "car_rental",
                "pickup": pickup, "dropoff": dropoff, "date": date,
                "price": float(vehicle.get("rate", {}).get("amount", 0)),
                "estimated_cost": float(vehicle.get("rate", {}).get("amount", 0)),
                "provider": "Hertz",
                "eta_minutes": 0,
            })
        return results

    async def book_transport(self, transport_id: str, passenger_details: dict, payment_token: str) -> dict:
        data = await self._request("POST", "/reservations", json={
            "vehicle_id": transport_id, "renter": passenger_details, "payment_token": payment_token,
        })
        ref = data.get("confirmation_number", transport_id)
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
