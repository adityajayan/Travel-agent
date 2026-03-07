from providers.base import BaseFlightProvider
from providers.schemas import (
    NormalizedBookingConfirmation,
    NormalizedFlightResult,
    PriceVerification,
    CancellationPolicy,
)
from datetime import datetime, timezone


class MockFlightProvider(BaseFlightProvider):
    """Mock flight provider returning normalized Pydantic models (INV-14)."""

    async def search_flights(
        self, origin: str, destination: str, date: str, passengers: int = 1
    ) -> list[dict]:
        results = [
            NormalizedFlightResult(
                flight_id="FL001",
                airline="Mock Air",
                origin=origin,
                destination=destination,
                departure_time="09:00",
                arrival_time="11:00",
                duration_minutes=120,
                stops=0,
                cabin_class="economy",
                estimated_cost=round(299.99 * passengers, 2),
                provider="MockAir",
                raw_provider_id="FL001",
                seats_available=10,
            ),
            NormalizedFlightResult(
                flight_id="FL002",
                airline="Budget Wings",
                origin=origin,
                destination=destination,
                departure_time="14:00",
                arrival_time="16:30",
                duration_minutes=150,
                stops=0,
                cabin_class="economy",
                estimated_cost=round(199.99 * passengers, 2),
                provider="BudgetWings",
                raw_provider_id="FL002",
                seats_available=5,
            ),
        ]
        return [r.model_dump() for r in results]

    async def book_flight(
        self, flight_id: str, passenger_details: dict, payment_token: str
    ) -> dict:
        confirmation = NormalizedBookingConfirmation(
            booking_reference=f"MOCK-{flight_id}-BKG",
            domain="flight",
            provider="MockAir",
            status="confirmed",
            amount=299.99,
            is_sandbox=True,
            raw_details={
                "flight_id": flight_id,
                "passenger": passenger_details,
                "payment_token": payment_token,
            },
        )
        return confirmation.model_dump()

    async def cancel_flight(self, booking_reference: str) -> dict:
        return {
            "booking_reference": booking_reference,
            "status": "cancelled",
            "refund_amount": 299.99,
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
            refund_amount=299.99,
            cancellation_fee=0.0,
            policy_text="Full refund available for mock bookings.",
            provider="MockAir",
        )
