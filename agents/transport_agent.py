from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from core.approval_gate import ApprovalGate
from core.audit_logger import AuditLogger
from agents.base_agent import BaseAgent
from providers.base import BaseTransportProvider
from providers.mock.transport_provider import MockTransportProvider
from tools.registry import ToolRegistry

SEARCH_TRANSPORT_DEF = {
    "name": "search_transport",
    "description": "Search for ground transport options between two locations.",
    "input_schema": {
        "type": "object",
        "properties": {
            "pickup": {"type": "string"},
            "dropoff": {"type": "string"},
            "date": {"type": "string", "description": "Date YYYY-MM-DD"},
        },
        "required": ["pickup", "dropoff", "date"],
    },
}

BOOK_TRANSPORT_DEF = {
    "name": "book_transport",
    "description": "Book a transport option. Requires prior human approval.",
    "input_schema": {
        "type": "object",
        "properties": {
            "transport_id": {"type": "string"},
            "passenger_name": {"type": "string"},
            "payment_token": {"type": "string"},
        },
        "required": ["transport_id", "passenger_name"],
    },
}

CANCEL_TRANSPORT_DEF = {
    "name": "cancel_transport",
    "description": "Cancel a transport booking. Requires prior human approval.",
    "input_schema": {
        "type": "object",
        "properties": {
            "booking_reference": {"type": "string"},
        },
        "required": ["booking_reference"],
    },
}


class TransportAgent(BaseAgent):
    def __init__(
        self,
        trip_id: str,
        db: AsyncSession,
        audit_logger: AuditLogger,
        approval_gate: ApprovalGate,
        provider: Optional[BaseTransportProvider] = None,
        policy_engine: Optional[object] = None,
    ):
        self.provider = provider or MockTransportProvider()
        registry = ToolRegistry()
        registry.register(SEARCH_TRANSPORT_DEF, self._search_transport)
        registry.register(BOOK_TRANSPORT_DEF, self._book_transport)
        registry.register(CANCEL_TRANSPORT_DEF, self._cancel_transport)
        super().__init__("TransportAgent", trip_id, db, registry, audit_logger, approval_gate, policy_engine)

    async def _search_transport(self, pickup: str, dropoff: str, date: str) -> list[dict]:
        return await self.provider.search_transport(pickup, dropoff, date)

    async def _book_transport(
        self, transport_id: str, passenger_name: str, payment_token: str = "mock-token"
    ) -> dict:
        approval_id = await self.approval_gate.check(
            self.trip_id,
            "transport",
            f"book_transport:{transport_id}",
            {"transport_id": transport_id, "passenger_name": passenger_name},
        )
        if not await self.approval_gate.verify_approved(approval_id):
            raise ValueError("Approval verification failed (layer 2)")

        result = await self.provider.book_transport(
            transport_id, {"name": passenger_name}, payment_token
        )
        await self.audit_logger.log_booking(
            self.trip_id, "transport", "mock", result, result.get("amount", 0.0)
        )
        return result

    async def _cancel_transport(self, booking_reference: str) -> dict:
        approval_id = await self.approval_gate.check(
            self.trip_id,
            "transport",
            f"cancel_transport:{booking_reference}",
            {"booking_reference": booking_reference},
        )
        if not await self.approval_gate.verify_approved(approval_id):
            raise ValueError("Approval verification failed (layer 2)")

        return await self.provider.cancel_transport(booking_reference)
