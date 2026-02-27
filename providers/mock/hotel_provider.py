from providers.base import BaseHotelProvider


class MockHotelProvider(BaseHotelProvider):
    async def search_hotels(
        self, destination: str, check_in: str, check_out: str, guests: int = 1
    ) -> list[dict]:
        return [
            {
                "hotel_id": "HTL001",
                "name": "Mock Grand Hotel",
                "destination": destination,
                "check_in": check_in,
                "check_out": check_out,
                "price_per_night": 150.00,
                "total_price": 150.00 * 1,
                "rating": 4.5,
                "rooms_available": 8,
            },
            {
                "hotel_id": "HTL002",
                "name": "Budget Inn",
                "destination": destination,
                "check_in": check_in,
                "check_out": check_out,
                "price_per_night": 79.99,
                "total_price": 79.99 * 1,
                "rating": 3.5,
                "rooms_available": 12,
            },
        ]

    async def book_hotel(
        self, hotel_id: str, guest_details: dict, payment_token: str
    ) -> dict:
        return {
            "booking_reference": f"MOCK-{hotel_id}-BKG",
            "hotel_id": hotel_id,
            "status": "confirmed",
            "guest": guest_details,
            "payment_token": payment_token,
            "amount": 150.00,
        }

    async def cancel_hotel(self, booking_reference: str) -> dict:
        return {
            "booking_reference": booking_reference,
            "status": "cancelled",
            "refund_amount": 150.00,
        }
