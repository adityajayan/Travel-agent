from providers.base import BaseActivityProvider


class MockActivityProvider(BaseActivityProvider):
    async def search_activities(
        self, destination: str, date: str, participants: int = 1
    ) -> list[dict]:
        return [
            {
                "activity_id": "ACT001",
                "name": "City Walking Tour",
                "destination": destination,
                "date": date,
                "price": round(35.00 * participants, 2),
                "duration_hours": 3,
                "spots_available": 20,
            },
            {
                "activity_id": "ACT002",
                "name": "Museum Visit",
                "destination": destination,
                "date": date,
                "price": round(25.00 * participants, 2),
                "duration_hours": 2,
                "spots_available": 50,
            },
        ]

    async def book_activity(
        self, activity_id: str, participant_details: dict, payment_token: str
    ) -> dict:
        return {
            "booking_reference": f"MOCK-{activity_id}-BKG",
            "activity_id": activity_id,
            "status": "confirmed",
            "participant": participant_details,
            "payment_token": payment_token,
            "amount": 35.00,
        }

    async def cancel_activity(self, booking_reference: str) -> dict:
        return {
            "booking_reference": booking_reference,
            "status": "cancelled",
            "refund_amount": 35.00,
        }
