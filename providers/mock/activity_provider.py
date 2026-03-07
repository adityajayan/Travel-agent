from datetime import datetime, timezone

from providers.base import BaseActivityProvider
from providers.schemas import (
    NormalizedActivityResult,
    NormalizedBookingConfirmation,
    PriceVerification,
    CancellationPolicy,
)


class MockActivityProvider(BaseActivityProvider):
    """Mock activity provider returning normalized Pydantic models (INV-14)."""

    async def search_activities(
        self, destination: str, date: str, participants: int = 1
    ) -> list[dict]:
        results = [
            NormalizedActivityResult(
                activity_id="ACT001",
                name="City Walking Tour",
                destination=destination,
                date=date,
                estimated_cost=round(35.00 * participants, 2),
                duration_hours=3,
                duration_minutes=180,
                provider="MockActivities",
                raw_provider_id="ACT001",
                spots_available=20,
            ),
            NormalizedActivityResult(
                activity_id="ACT002",
                name="Museum Visit",
                destination=destination,
                date=date,
                estimated_cost=round(25.00 * participants, 2),
                duration_hours=2,
                duration_minutes=120,
                provider="MockActivities",
                raw_provider_id="ACT002",
                spots_available=50,
            ),
        ]
        return [r.model_dump() for r in results]

    async def book_activity(
        self, activity_id: str, participant_details: dict, payment_token: str
    ) -> dict:
        confirmation = NormalizedBookingConfirmation(
            booking_reference=f"MOCK-{activity_id}-BKG",
            domain="activity",
            provider="MockActivities",
            status="confirmed",
            amount=35.00,
            is_sandbox=True,
            raw_details={
                "activity_id": activity_id,
                "participant": participant_details,
                "payment_token": payment_token,
            },
        )
        return confirmation.model_dump()

    async def cancel_activity(self, booking_reference: str) -> dict:
        return {
            "booking_reference": booking_reference,
            "status": "cancelled",
            "refund_amount": 35.00,
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
            refund_amount=35.00,
            cancellation_fee=0.0,
            policy_text="Full refund available for mock bookings.",
            provider="MockActivities",
        )
