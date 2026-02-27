import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import HumanApproval


class ApprovalRequiredError(Exception):
    """Raised when a booking action requires human approval."""

    def __init__(self, approval_id: str, message: str):
        self.approval_id = approval_id
        super().__init__(message)


class ApprovalRejectedError(Exception):
    """Raised when a booking action was rejected by a human."""


class ApprovalGate:
    """Enforces that book_* / cancel_* tools never proceed without an approved HumanApproval record."""

    def __init__(self, db: AsyncSession):
        self.db = db
        # M3: set by BaseAgent._dispatch_tool() before a book_* call when soft violations exist
        self._pending_soft_violations: list = []

    async def check(self, trip_id: str, domain: str, action: str, details: dict) -> str:
        """Layer-1 check.

        - If an approved record exists  → return approval_id (proceed).
        - If a rejected record exists   → raise ApprovalRejectedError.
        - Otherwise                     → create pending record and raise ApprovalRequiredError.
        """
        # Check for existing approved record
        result = await self.db.execute(
            select(HumanApproval).where(
                HumanApproval.trip_id == trip_id,
                HumanApproval.domain == domain,
                HumanApproval.action == action,
                HumanApproval.status == "approved",
            )
        )
        approved = result.scalar_one_or_none()
        if approved:
            return approved.id

        # Check for rejected record
        result = await self.db.execute(
            select(HumanApproval).where(
                HumanApproval.trip_id == trip_id,
                HumanApproval.domain == domain,
                HumanApproval.action == action,
                HumanApproval.status == "rejected",
            )
        )
        rejected = result.scalar_one_or_none()
        if rejected:
            raise ApprovalRejectedError(
                f"Action '{action}' was rejected for trip {trip_id}"
            )

        # Check for existing pending record
        result = await self.db.execute(
            select(HumanApproval).where(
                HumanApproval.trip_id == trip_id,
                HumanApproval.domain == domain,
                HumanApproval.action == action,
                HumanApproval.status == "pending",
            )
        )
        pending = result.scalar_one_or_none()
        if pending:
            raise ApprovalRequiredError(
                approval_id=pending.id,
                message=f"Approval already pending for '{action}'. ID: {pending.id}",
            )

        # Create a new pending approval (attach any pending SOFT violation context)
        violations_snapshot = self._pending_soft_violations or None
        self._pending_soft_violations = []  # consume and clear
        approval = HumanApproval(
            id=str(uuid.uuid4()),
            trip_id=trip_id,
            domain=domain,
            action=action,
            details=details,
            status="pending",
            policy_violations_json=violations_snapshot,
        )
        self.db.add(approval)
        await self.db.commit()

        raise ApprovalRequiredError(
            approval_id=approval.id,
            message=f"Approval required for '{action}'. Approval ID: {approval.id}",
        )

    async def verify_approved(self, approval_id: str) -> bool:
        """Layer-2 check – verify the specific approval record is approved."""
        result = await self.db.execute(
            select(HumanApproval).where(HumanApproval.id == approval_id)
        )
        approval = result.scalar_one_or_none()
        if not approval:
            return False
        return approval.status == "approved"

    async def decide(self, approval_id: str, approved: bool) -> HumanApproval:
        """Record a human decision on a pending approval."""
        result = await self.db.execute(
            select(HumanApproval).where(HumanApproval.id == approval_id)
        )
        approval = result.scalar_one_or_none()
        if not approval:
            raise ValueError(f"Approval {approval_id} not found")

        approval.status = "approved" if approved else "rejected"
        approval.decided_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(approval)
        return approval
