from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from core.approval_gate import ApprovalGate
from core.audit_logger import AuditLogger
from agents.base_agent import BaseAgent
from providers.base import BaseActivityProvider
from providers.mock.activity_provider import MockActivityProvider
from tools.registry import ToolRegistry

SEARCH_ACTIVITIES_DEF = {
    "name": "search_activities",
    "description": "Search for activities and experiences at a destination.",
    "input_schema": {
        "type": "object",
        "properties": {
            "destination": {"type": "string"},
            "date": {"type": "string", "description": "Date YYYY-MM-DD"},
            "participants": {"type": "integer", "default": 1},
        },
        "required": ["destination", "date"],
    },
}

BOOK_ACTIVITY_DEF = {
    "name": "book_activity",
    "description": "Book an activity. Requires prior human approval.",
    "input_schema": {
        "type": "object",
        "properties": {
            "activity_id": {"type": "string"},
            "participant_name": {"type": "string"},
            "payment_token": {"type": "string"},
        },
        "required": ["activity_id", "participant_name"],
    },
}

CANCEL_ACTIVITY_DEF = {
    "name": "cancel_activity",
    "description": "Cancel an activity booking. Requires prior human approval.",
    "input_schema": {
        "type": "object",
        "properties": {
            "booking_reference": {"type": "string"},
        },
        "required": ["booking_reference"],
    },
}


class ActivityAgent(BaseAgent):
    def __init__(
        self,
        trip_id: str,
        db: AsyncSession,
        audit_logger: AuditLogger,
        approval_gate: ApprovalGate,
        provider: Optional[BaseActivityProvider] = None,
        policy_engine: Optional[object] = None,
    ):
        self.provider = provider or MockActivityProvider()
        registry = ToolRegistry()
        registry.register(SEARCH_ACTIVITIES_DEF, self._search_activities)
        registry.register(BOOK_ACTIVITY_DEF, self._book_activity)
        registry.register(CANCEL_ACTIVITY_DEF, self._cancel_activity)
        super().__init__("ActivityAgent", trip_id, db, registry, audit_logger, approval_gate, policy_engine)

    async def _search_activities(
        self, destination: str, date: str, participants: int = 1
    ) -> list[dict]:
        return await self.provider.search_activities(destination, date, participants)

    async def _book_activity(
        self, activity_id: str, participant_name: str, payment_token: str = "mock-token"
    ) -> dict:
        approval_id = await self.approval_gate.check(
            self.trip_id,
            "activity",
            f"book_activity:{activity_id}",
            {"activity_id": activity_id, "participant_name": participant_name},
        )
        if not await self.approval_gate.verify_approved(approval_id):
            raise ValueError("Approval verification failed (layer 2)")

        result = await self.provider.book_activity(
            activity_id, {"name": participant_name}, payment_token
        )
        await self.audit_logger.log_booking(
            self.trip_id, "activity", "mock", result, result.get("amount", 0.0)
        )
        return result

    async def _cancel_activity(self, booking_reference: str) -> dict:
        approval_id = await self.approval_gate.check(
            self.trip_id,
            "activity",
            f"cancel_activity:{booking_reference}",
            {"booking_reference": booking_reference},
        )
        if not await self.approval_gate.verify_approved(approval_id):
            raise ValueError("Approval verification failed (layer 2)")

        return await self.provider.cancel_activity(booking_reference)
