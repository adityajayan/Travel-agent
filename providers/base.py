"""Base provider ABCs for all travel domains (M5)."""
from abc import ABC, abstractmethod


class BaseProvider(ABC):
    """Unified provider interface for all domains."""

    @abstractmethod
    async def search(self, **params) -> list[dict]:
        pass

    @abstractmethod
    async def get_details(self, item_id: str) -> dict:
        pass

    @abstractmethod
    async def book(self, item_id: str, details: dict, payment_token: str) -> dict:
        pass

    @abstractmethod
    async def cancel(self, booking_reference: str) -> dict:
        pass


class BaseFlightProvider(BaseProvider):
    """Flight-specific provider with convenience methods."""

    async def search(self, **params) -> list[dict]:
        return await self.search_flights(
            origin=params["origin"],
            destination=params["destination"],
            date=params["date"],
            passengers=params.get("passengers", 1),
        )

    async def get_details(self, item_id: str) -> dict:
        return {"flight_id": item_id, "status": "available"}

    async def book(self, item_id: str, details: dict, payment_token: str) -> dict:
        return await self.book_flight(item_id, details, payment_token)

    async def cancel(self, booking_reference: str) -> dict:
        return await self.cancel_flight(booking_reference)

    @abstractmethod
    async def search_flights(
        self, origin: str, destination: str, date: str, passengers: int = 1
    ) -> list[dict]:
        pass

    @abstractmethod
    async def book_flight(
        self, flight_id: str, passenger_details: dict, payment_token: str
    ) -> dict:
        pass

    @abstractmethod
    async def cancel_flight(self, booking_reference: str) -> dict:
        pass


class BaseHotelProvider(BaseProvider):
    """Hotel-specific provider with convenience methods."""

    async def search(self, **params) -> list[dict]:
        return await self.search_hotels(
            destination=params["destination"],
            check_in=params["check_in"],
            check_out=params["check_out"],
            guests=params.get("guests", 1),
        )

    async def get_details(self, item_id: str) -> dict:
        return {"hotel_id": item_id, "status": "available"}

    async def book(self, item_id: str, details: dict, payment_token: str) -> dict:
        return await self.book_hotel(item_id, details, payment_token)

    async def cancel(self, booking_reference: str) -> dict:
        return await self.cancel_hotel(booking_reference)

    @abstractmethod
    async def search_hotels(
        self, destination: str, check_in: str, check_out: str, guests: int = 1
    ) -> list[dict]:
        pass

    @abstractmethod
    async def book_hotel(
        self, hotel_id: str, guest_details: dict, payment_token: str
    ) -> dict:
        pass

    @abstractmethod
    async def cancel_hotel(self, booking_reference: str) -> dict:
        pass


class BaseTransportProvider(BaseProvider):
    """Transport-specific provider with convenience methods."""

    async def search(self, **params) -> list[dict]:
        return await self.search_transport(
            pickup=params["pickup"],
            dropoff=params["dropoff"],
            date=params["date"],
        )

    async def get_details(self, item_id: str) -> dict:
        return {"transport_id": item_id, "status": "available"}

    async def book(self, item_id: str, details: dict, payment_token: str) -> dict:
        return await self.book_transport(item_id, details, payment_token)

    async def cancel(self, booking_reference: str) -> dict:
        return await self.cancel_transport(booking_reference)

    @abstractmethod
    async def search_transport(
        self, pickup: str, dropoff: str, date: str
    ) -> list[dict]:
        pass

    @abstractmethod
    async def book_transport(
        self, transport_id: str, passenger_details: dict, payment_token: str
    ) -> dict:
        pass

    @abstractmethod
    async def cancel_transport(self, booking_reference: str) -> dict:
        pass


class BaseActivityProvider(BaseProvider):
    """Activity-specific provider with convenience methods."""

    async def search(self, **params) -> list[dict]:
        return await self.search_activities(
            destination=params["destination"],
            date=params["date"],
            participants=params.get("participants", 1),
        )

    async def get_details(self, item_id: str) -> dict:
        return {"activity_id": item_id, "status": "available"}

    async def book(self, item_id: str, details: dict, payment_token: str) -> dict:
        return await self.book_activity(item_id, details, payment_token)

    async def cancel(self, booking_reference: str) -> dict:
        return await self.cancel_activity(booking_reference)

    @abstractmethod
    async def search_activities(
        self, destination: str, date: str, participants: int = 1
    ) -> list[dict]:
        pass

    @abstractmethod
    async def book_activity(
        self, activity_id: str, participant_details: dict, payment_token: str
    ) -> dict:
        pass

    @abstractmethod
    async def cancel_activity(self, booking_reference: str) -> dict:
        pass
