import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import HumanApproval

logger = logging.getLogger(__name__)


class ApprovalRequiredError(Exception):
    """Raised when a booking action requires human approval."""

    def __init__(self, approval_id: str, message: str):
        self.approval_id = approval_id
        super().__init__(message)


class ApprovalRejectedError(Exception):
    """Raised when a booking action was rejected by a human."""


class PriceChangedError(Exception):
    """Raised when price changed beyond threshold after approval (INV-13)."""

    def __init__(self, approval_id: str, original_price: float, current_price: float, pct_change: float):
        self.approval_id = approval_id
        self.original_price = original_price
        self.current_price = current_price
        self.pct_change = pct_change
        super().__init__(
            f"Price changed {pct_change:.1f}% (${original_price:.2f} → ${current_price:.2f}). "
            f"New approval required. ID: {approval_id}"
        )


class ApprovalGate:
    """Enforces that book_* / cancel_* tools never proceed without an approved HumanApproval record.

    M8: Integrates price re-verification before and after approval (INV-13).
    M8: Routes cancellation through approval with refund/fee breakdown (INV-16).
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        # M3: set by BaseAgent._dispatch_tool() before a book_* call when soft violations exist
        self._pending_soft_violations: list = []
        # M8: provider reference for price verification
        self._provider = None
        # M8: price change threshold (percentage)
        self._price_threshold_pct: float = 5.0

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

    async def verify_price_before_approval(
        self,
        trip_id: str,
        domain: str,
        action: str,
        item_id: str,
        original_price: float,
        details: dict,
    ) -> dict:
        """M8 (INV-13): Verify price before creating approval request.

        Calls provider.verify_price() and attaches verified price to approval context.
        Returns the price verification result dict.
        """
        if self._provider is None:
            return {"price_changed": False, "current_price": original_price}

        try:
            verification = await self._provider.verify_price(item_id, original_price)
            details["verified_price"] = verification.current_price
            details["price_verified_at"] = verification.verified_at.isoformat()
            details["price_changed"] = verification.price_changed
            if verification.price_changed:
                details["price_pct_change"] = verification.pct_change
            return verification.model_dump()
        except Exception as exc:
            logger.warning("Price verification failed: %s — proceeding with original price", exc)
            return {"price_changed": False, "current_price": original_price}

    async def verify_price_after_approval(
        self,
        approval_id: str,
        item_id: str,
        approved_price: float,
    ) -> None:
        """M8 (INV-13): Re-verify price after approval, before booking.

        If price changed > threshold, invalidates approval and raises PriceChangedError
        with a new approval request at the updated price.
        """
        if self._provider is None:
            return

        try:
            verification = await self._provider.verify_price(item_id, approved_price)
        except Exception as exc:
            logger.warning("Post-approval price verification failed: %s — proceeding", exc)
            return

        if not verification.price_changed:
            return

        if verification.pct_change <= self._price_threshold_pct:
            logger.info(
                "Price changed %.1f%% (within threshold %.1f%%) — proceeding",
                verification.pct_change,
                self._price_threshold_pct,
            )
            return

        # Price changed beyond threshold — get the original approval to create a new one
        result = await self.db.execute(
            select(HumanApproval).where(HumanApproval.id == approval_id)
        )
        original = result.scalar_one_or_none()
        if not original:
            return

        # Create new approval with updated price
        updated_details = dict(original.details or {})
        updated_details["original_approved_price"] = approved_price
        updated_details["updated_price"] = verification.current_price
        updated_details["price_change_pct"] = verification.pct_change
        updated_details["price_reverify_reason"] = (
            f"Price changed {verification.pct_change:.1f}% since approval"
        )

        new_approval = HumanApproval(
            id=str(uuid.uuid4()),
            trip_id=original.trip_id,
            domain=original.domain,
            action=original.action,
            details=updated_details,
            status="pending",
        )
        self.db.add(new_approval)
        await self.db.commit()

        raise PriceChangedError(
            approval_id=new_approval.id,
            original_price=approved_price,
            current_price=verification.current_price,
            pct_change=verification.pct_change,
        )

    async def check_cancellation(
        self,
        trip_id: str,
        domain: str,
        booking_reference: str,
        cancellation_details: Optional[dict] = None,
    ) -> str:
        """M8 (INV-16): Route cancellation through approval with refund/fee breakdown.

        Fetches cancellation policy from provider, attaches it to approval context.
        """
        details = {"booking_reference": booking_reference}

        # Fetch cancellation policy if provider available
        if self._provider is not None:
            try:
                policy = await self._provider.get_cancellation_policy(booking_reference)
                details["refundable"] = policy.refundable
                details["refund_amount"] = policy.refund_amount
                details["cancellation_fee"] = policy.cancellation_fee
                details["policy_text"] = policy.policy_text
            except Exception as exc:
                logger.warning("Failed to fetch cancellation policy: %s", exc)
                details["policy_fetch_error"] = str(exc)

        if cancellation_details:
            details.update(cancellation_details)

        return await self.check(
            trip_id,
            domain,
            f"cancel_{domain}:{booking_reference}",
            details,
        )
