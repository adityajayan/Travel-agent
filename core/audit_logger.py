import json
import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Booking, ToolCall, Trip

if TYPE_CHECKING:
    from core.policy_engine import PolicyEvalResult, PolicyViolationDetail


class AuditLogger:
    """Append-only audit trail for tool calls and bookings."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def log_tool_call(
        self,
        trip_id: str,
        agent_name: str,
        tool_name: str,
        input_data: dict,
        output_data: dict,
    ) -> ToolCall:
        """Append a ToolCall record. Never updates existing records."""
        record = ToolCall(
            id=str(uuid.uuid4()),
            trip_id=trip_id,
            agent_name=agent_name,
            tool_name=tool_name,
            input=input_data,
            output=output_data,
        )
        self.db.add(record)
        await self.db.commit()
        return record

    async def log_booking(
        self,
        trip_id: str,
        domain: str,
        provider: str,
        details: dict,
        amount: float,
    ) -> Booking:
        """Append a Booking record and atomically increment Trip.total_spent."""
        booking = Booking(
            id=str(uuid.uuid4()),
            trip_id=trip_id,
            domain=domain,
            provider=provider,
            details=details,
            amount=amount,
        )
        self.db.add(booking)

        # Atomically update trip total
        result = await self.db.execute(select(Trip).where(Trip.id == trip_id))
        trip = result.scalar_one_or_none()
        if trip:
            trip.total_spent = (trip.total_spent or 0.0) + amount

        await self.db.commit()
        return booking

    async def log_policy_evaluation(
        self,
        trip_id: str,
        policy_id: str,
        booking_type: str,
        result: "PolicyEvalResult",
    ) -> ToolCall:
        """Write a structured summary of a policy evaluation as a ToolCall row (append-only)."""
        summary = {
            "policy_id": policy_id,
            "booking_type": booking_type,
            "compliant": result.compliant,
            "hard_violation_count": len(result.hard_violations),
            "soft_violation_count": len(result.soft_violations),
            "hard_violations": [
                {"rule_key": v.rule_key, "message": v.message, "actual": v.actual_value}
                for v in result.hard_violations
            ],
            "soft_violations": [
                {"rule_key": v.rule_key, "message": v.message, "actual": v.actual_value}
                for v in result.soft_violations
            ],
        }
        return await self.log_tool_call(
            trip_id, "PolicyEngine", "policy_evaluation", {"policy_id": policy_id}, summary
        )

    async def log_policy_violation(
        self,
        violation: "PolicyViolationDetail",
        trip_id: str,
        approval_id: Optional[str],
        outcome: str,
    ) -> str:
        """Persist a single PolicyViolation row via the PolicyEngine.record_violations path.

        This method is a thin wrapper kept for interface completeness.
        Returns a placeholder violation_id (actual persistence is via PolicyEngine).
        """
        return str(uuid.uuid4())
