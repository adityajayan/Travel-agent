from providers.base import BaseFlightProvider


class MockFlightProvider(BaseFlightProvider):
    async def search_flights(
        self, origin: str, destination: str, date: str, passengers: int = 1
    ) -> list[dict]:
        return [
            {
                "flight_id": "FL001",
                "airline": "Mock Air",
                "origin": origin,
                "destination": destination,
                "date": date,
                "departure_time": "09:00",
                "arrival_time": "11:00",
                "price": round(299.99 * passengers, 2),
                "seats_available": 10,
            },
            {
                "flight_id": "FL002",
                "airline": "Budget Wings",
                "origin": origin,
                "destination": destination,
                "date": date,
                "departure_time": "14:00",
                "arrival_time": "16:30",
                "price": round(199.99 * passengers, 2),
                "seats_available": 5,
            },
        ]

    async def book_flight(
        self, flight_id: str, passenger_details: dict, payment_token: str
    ) -> dict:
        return {
            "booking_reference": f"MOCK-{flight_id}-BKG",
            "flight_id": flight_id,
            "status": "confirmed",
            "passenger": passenger_details,
            "payment_token": payment_token,
            "amount": 299.99,
        }

    async def cancel_flight(self, booking_reference: str) -> dict:
        return {
            "booking_reference": booking_reference,
            "status": "cancelled",
            "refund_amount": 299.99,
        }
