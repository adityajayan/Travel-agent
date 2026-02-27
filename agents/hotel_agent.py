from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from core.approval_gate import ApprovalGate
from core.audit_logger import AuditLogger
from agents.base_agent import BaseAgent
from providers.base import BaseHotelProvider
from providers.mock.hotel_provider import MockHotelProvider
from tools.registry import ToolRegistry

SEARCH_HOTELS_DEF = {
    "name": "search_hotels",
    "description": "Search for available hotels in a destination.",
    "input_schema": {
        "type": "object",
        "properties": {
            "destination": {"type": "string"},
            "check_in": {"type": "string", "description": "Check-in date YYYY-MM-DD"},
            "check_out": {"type": "string", "description": "Check-out date YYYY-MM-DD"},
            "guests": {"type": "integer", "default": 1},
        },
        "required": ["destination", "check_in", "check_out"],
    },
}

BOOK_HOTEL_DEF = {
    "name": "book_hotel",
    "description": "Book a hotel room. Requires prior human approval.",
    "input_schema": {
        "type": "object",
        "properties": {
            "hotel_id": {"type": "string"},
            "guest_name": {"type": "string"},
            "payment_token": {"type": "string"},
        },
        "required": ["hotel_id", "guest_name"],
    },
}

CANCEL_HOTEL_DEF = {
    "name": "cancel_hotel",
    "description": "Cancel a hotel booking. Requires prior human approval.",
    "input_schema": {
        "type": "object",
        "properties": {
            "booking_reference": {"type": "string"},
        },
        "required": ["booking_reference"],
    },
}


class HotelAgent(BaseAgent):
    def __init__(
        self,
        trip_id: str,
        db: AsyncSession,
        audit_logger: AuditLogger,
        approval_gate: ApprovalGate,
        provider: Optional[BaseHotelProvider] = None,
        policy_engine: Optional[object] = None,
    ):
        self.provider = provider or MockHotelProvider()
        registry = ToolRegistry()
        registry.register(SEARCH_HOTELS_DEF, self._search_hotels)
        registry.register(BOOK_HOTEL_DEF, self._book_hotel)
        registry.register(CANCEL_HOTEL_DEF, self._cancel_hotel)
        super().__init__("HotelAgent", trip_id, db, registry, audit_logger, approval_gate, policy_engine)

    async def _search_hotels(
        self, destination: str, check_in: str, check_out: str, guests: int = 1
    ) -> list[dict]:
        return await self.provider.search_hotels(destination, check_in, check_out, guests)

    async def _book_hotel(
        self, hotel_id: str, guest_name: str, payment_token: str = "mock-token"
    ) -> dict:
        approval_id = await self.approval_gate.check(
            self.trip_id,
            "hotel",
            f"book_hotel:{hotel_id}",
            {"hotel_id": hotel_id, "guest_name": guest_name},
        )
        if not await self.approval_gate.verify_approved(approval_id):
            raise ValueError("Approval verification failed (layer 2)")

        result = await self.provider.book_hotel(
            hotel_id, {"name": guest_name}, payment_token
        )
        await self.audit_logger.log_booking(
            self.trip_id, "hotel", "mock", result, result.get("amount", 0.0)
        )
        return result

    async def _cancel_hotel(self, booking_reference: str) -> dict:
        approval_id = await self.approval_gate.check(
            self.trip_id,
            "hotel",
            f"cancel_hotel:{booking_reference}",
            {"booking_reference": booking_reference},
        )
        if not await self.approval_gate.verify_approved(approval_id):
            raise ValueError("Approval verification failed (layer 2)")

        return await self.provider.cancel_hotel(booking_reference)
