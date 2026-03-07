"""Base provider ABCs for all travel domains (M5, M8)."""
from abc import ABC, abstractmethod
from datetime import datetime, timezone

from providers.schemas import CancellationPolicy, HoldResult, PriceVerification


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

    async def hold_fare(self, item_id: str) -> HoldResult:
        """Attempt to hold/lock a fare. Default: not supported."""
        return HoldResult(
            hold_id="",
            item_id=item_id,
            verified_price=0.0,
            expires_at=datetime.now(timezone.utc),
            provider="",
            supported=False,
        )

    async def verify_price(self, item_id: str, original_price: float) -> PriceVerification:
        """Re-verify current price for an item. Default: returns unchanged."""
        now = datetime.now(timezone.utc)
        return PriceVerification(
            item_id=item_id,
            current_price=original_price,
            original_price=original_price,
            price_changed=False,
            pct_change=0.0,
            verified_at=now,
        )

    async def get_cancellation_policy(self, booking_reference: str) -> CancellationPolicy:
        """Get cancellation terms for a booking. Default: non-refundable."""
        return CancellationPolicy(
            booking_reference=booking_reference,
            refundable=False,
            refund_amount=0.0,
            cancellation_fee=0.0,
            policy_text="No refund policy available.",
            provider="",
        )


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
