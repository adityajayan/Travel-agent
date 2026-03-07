from datetime import datetime, timezone

from providers.base import BaseTransportProvider
from providers.schemas import (
    NormalizedBookingConfirmation,
    NormalizedTransportResult,
    PriceVerification,
    CancellationPolicy,
)


class MockTransportProvider(BaseTransportProvider):
    """Mock transport provider returning normalized Pydantic models (INV-14)."""

    async def search_transport(
        self, pickup: str, dropoff: str, date: str
    ) -> list[dict]:
        results = [
            NormalizedTransportResult(
                transport_id="TRN001",
                type="taxi",
                pickup=pickup,
                dropoff=dropoff,
                date=date,
                estimated_cost=45.00,
                eta_minutes=10,
                provider="MockTransport",
                raw_provider_id="TRN001",
            ),
            NormalizedTransportResult(
                transport_id="TRN002",
                type="shuttle",
                pickup=pickup,
                dropoff=dropoff,
                date=date,
                estimated_cost=25.00,
                eta_minutes=30,
                provider="MockTransport",
                raw_provider_id="TRN002",
            ),
        ]
        return [r.model_dump() for r in results]

    async def book_transport(
        self, transport_id: str, passenger_details: dict, payment_token: str
    ) -> dict:
        confirmation = NormalizedBookingConfirmation(
            booking_reference=f"MOCK-{transport_id}-BKG",
            domain="transport",
            provider="MockTransport",
            status="confirmed",
            amount=45.00,
            is_sandbox=True,
            raw_details={
                "transport_id": transport_id,
                "passenger": passenger_details,
                "payment_token": payment_token,
            },
        )
        return confirmation.model_dump()

    async def cancel_transport(self, booking_reference: str) -> dict:
        return {
            "booking_reference": booking_reference,
            "status": "cancelled",
            "refund_amount": 45.00,
        }

    async def verify_price(self, item_id: str, original_price: float) -> PriceVerification:
        return PriceVerification(
            item_id=item_id,
            current_price=original_price,
            original_price=original_price,
            price_changed=False,
            pct_change=0.0,
            verified_at=datetime.now(timezone.utc),
        )

    async def get_cancellation_policy(self, booking_reference: str) -> CancellationPolicy:
        return CancellationPolicy(
            booking_reference=booking_reference,
            refundable=True,
            refund_amount=45.00,
            cancellation_fee=0.0,
            policy_text="Full refund available for mock bookings.",
            provider="MockTransport",
        )
