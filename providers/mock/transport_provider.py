from providers.base import BaseTransportProvider


class MockTransportProvider(BaseTransportProvider):
    async def search_transport(
        self, pickup: str, dropoff: str, date: str
    ) -> list[dict]:
        return [
            {
                "transport_id": "TRN001",
                "type": "taxi",
                "pickup": pickup,
                "dropoff": dropoff,
                "date": date,
                "price": 45.00,
                "eta_minutes": 10,
            },
            {
                "transport_id": "TRN002",
                "type": "shuttle",
                "pickup": pickup,
                "dropoff": dropoff,
                "date": date,
                "price": 25.00,
                "eta_minutes": 30,
            },
        ]

    async def book_transport(
        self, transport_id: str, passenger_details: dict, payment_token: str
    ) -> dict:
        return {
            "booking_reference": f"MOCK-{transport_id}-BKG",
            "transport_id": transport_id,
            "status": "confirmed",
            "passenger": passenger_details,
            "payment_token": payment_token,
            "amount": 45.00,
        }

    async def cancel_transport(self, booking_reference: str) -> dict:
        return {
            "booking_reference": booking_reference,
            "status": "cancelled",
            "refund_amount": 45.00,
        }
