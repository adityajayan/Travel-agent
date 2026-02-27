from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from core.approval_gate import ApprovalGate, ApprovalRequiredError
from core.audit_logger import AuditLogger
from agents.base_agent import BaseAgent
from providers.base import BaseFlightProvider
from providers.mock.flight_provider import MockFlightProvider
from tools.registry import ToolRegistry

SEARCH_FLIGHTS_DEF = {
    "name": "search_flights",
    "description": "Search for available flights between two cities on a given date.",
    "input_schema": {
        "type": "object",
        "properties": {
            "origin": {"type": "string", "description": "IATA code or city name of origin"},
            "destination": {"type": "string", "description": "IATA code or city name of destination"},
            "date": {"type": "string", "description": "Travel date in YYYY-MM-DD format"},
            "passengers": {"type": "integer", "description": "Number of passengers", "default": 1},
        },
        "required": ["origin", "destination", "date"],
    },
}

BOOK_FLIGHT_DEF = {
    "name": "book_flight",
    "description": "Book a specific flight. Requires prior human approval.",
    "input_schema": {
        "type": "object",
        "properties": {
            "flight_id": {"type": "string", "description": "Flight ID from search results"},
            "passenger_name": {"type": "string", "description": "Full name of the passenger"},
            "payment_token": {"type": "string", "description": "Payment token (use 'mock-token' in testing)"},
        },
        "required": ["flight_id", "passenger_name"],
    },
}

CANCEL_FLIGHT_DEF = {
    "name": "cancel_flight",
    "description": "Cancel a previously booked flight. Requires prior human approval.",
    "input_schema": {
        "type": "object",
        "properties": {
            "booking_reference": {"type": "string", "description": "Booking reference to cancel"},
        },
        "required": ["booking_reference"],
    },
}


class FlightAgent(BaseAgent):
    def __init__(
        self,
        trip_id: str,
        db: AsyncSession,
        audit_logger: AuditLogger,
        approval_gate: ApprovalGate,
        provider: Optional[BaseFlightProvider] = None,
        policy_engine: Optional[object] = None,
    ):
        self.provider = provider or MockFlightProvider()
        registry = ToolRegistry()
        registry.register(SEARCH_FLIGHTS_DEF, self._search_flights)
        registry.register(BOOK_FLIGHT_DEF, self._book_flight)
        registry.register(CANCEL_FLIGHT_DEF, self._cancel_flight)
        super().__init__("FlightAgent", trip_id, db, registry, audit_logger, approval_gate, policy_engine)

    # --- tool handlers ---

    async def _search_flights(
        self, origin: str, destination: str, date: str, passengers: int = 1
    ) -> list[dict]:
        return await self.provider.search_flights(origin, destination, date, passengers)

    async def _book_flight(
        self,
        flight_id: str,
        passenger_name: str,
        payment_token: str = "mock-token",
    ) -> dict:
        # Layer 1 – will raise ApprovalRequiredError if not yet approved
        approval_id = await self.approval_gate.check(
            self.trip_id,
            "flight",
            f"book_flight:{flight_id}",
            {"flight_id": flight_id, "passenger_name": passenger_name},
        )
        # Layer 2 – verify the specific record
        if not await self.approval_gate.verify_approved(approval_id):
            raise ValueError("Approval verification failed (layer 2)")

        result = await self.provider.book_flight(
            flight_id, {"name": passenger_name}, payment_token
        )
        await self.audit_logger.log_booking(
            self.trip_id, "flight", "mock", result, result.get("amount", 0.0)
        )
        return result

    async def _cancel_flight(self, booking_reference: str) -> dict:
        # Layer 1
        approval_id = await self.approval_gate.check(
            self.trip_id,
            "flight",
            f"cancel_flight:{booking_reference}",
            {"booking_reference": booking_reference},
        )
        # Layer 2
        if not await self.approval_gate.verify_approved(approval_id):
            raise ValueError("Approval verification failed (layer 2)")

        result = await self.provider.cancel_flight(booking_reference)
        return result
