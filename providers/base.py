from abc import ABC, abstractmethod


class BaseFlightProvider(ABC):
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


class BaseHotelProvider(ABC):
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


class BaseTransportProvider(ABC):
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


class BaseActivityProvider(ABC):
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
