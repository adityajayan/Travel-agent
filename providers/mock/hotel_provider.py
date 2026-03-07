from datetime import datetime, timezone

from providers.base import BaseHotelProvider
from providers.schemas import (
    NormalizedBookingConfirmation,
    NormalizedHotelResult,
    PriceVerification,
    CancellationPolicy,
)


class MockHotelProvider(BaseHotelProvider):
    """Mock hotel provider returning normalized Pydantic models (INV-14)."""

    async def search_hotels(
        self, destination: str, check_in: str, check_out: str, guests: int = 1
    ) -> list[dict]:
        results = [
            NormalizedHotelResult(
                hotel_id="HTL001",
                name="Mock Grand Hotel",
                destination=destination,
                check_in=check_in,
                check_out=check_out,
                cost_per_night=150.00,
                total_price=150.00,
                star_rating=4.0,
                rating_score=4.5,
                provider="MockHotels",
                raw_provider_id="HTL001",
                rooms_available=8,
            ),
            NormalizedHotelResult(
                hotel_id="HTL002",
                name="Budget Inn",
                destination=destination,
                check_in=check_in,
                check_out=check_out,
                cost_per_night=79.99,
                total_price=79.99,
                star_rating=3.0,
                rating_score=3.5,
                provider="MockHotels",
                raw_provider_id="HTL002",
                rooms_available=12,
            ),
        ]
        return [r.model_dump() for r in results]

    async def book_hotel(
        self, hotel_id: str, guest_details: dict, payment_token: str
    ) -> dict:
        confirmation = NormalizedBookingConfirmation(
            booking_reference=f"MOCK-{hotel_id}-BKG",
            domain="hotel",
            provider="MockHotels",
            status="confirmed",
            amount=150.00,
            is_sandbox=True,
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
            "refund_amount": 150.00,
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
            refund_amount=150.00,
            cancellation_fee=0.0,
            policy_text="Full refund available for mock bookings.",
            provider="MockHotels",
        )
