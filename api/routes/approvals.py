import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas import ApprovalDecide, ApprovalRead
from core.approval_gate import ApprovalGate
from core.auth import CurrentUser, get_current_user
from core.trip_lifecycle import InvalidTransitionError, TripStatus, transition_trip
from db.database import get_db
from db.models import HumanApproval, Trip

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/approvals", tags=["approvals"])


@router.get("/{approval_id}", response_model=ApprovalRead)
async def get_approval(
    approval_id: str,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    result = await db.execute(
        select(HumanApproval).where(HumanApproval.id == approval_id)
    )
    approval = result.scalar_one_or_none()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")
    return approval


@router.get("", response_model=list[ApprovalRead])
async def list_approvals(
    trip_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    query = select(HumanApproval)
    if trip_id:
        query = query.where(HumanApproval.trip_id == trip_id)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/{approval_id}/decide", response_model=ApprovalRead)
async def decide_approval(
    approval_id: str,
    body: ApprovalDecide,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    gate = ApprovalGate(db)
    try:
        approval = await gate.decide(approval_id, body.approved)
    except ValueError:
        raise HTTPException(status_code=404, detail="Approval not found")

    # After approval decision, check if trip should transition
    trip_result = await db.execute(
        select(Trip).where(Trip.id == approval.trip_id)
    )
    trip = trip_result.scalar_one_or_none()

    if trip and trip.status == TripStatus.REVIEW:
        # Check if all approvals are resolved (none still pending)
        pending_result = await db.execute(
            select(HumanApproval).where(
                HumanApproval.trip_id == approval.trip_id,
                HumanApproval.status == "pending",
            )
        )
        remaining_pending = pending_result.scalar_one_or_none()

        if remaining_pending is None:
            # All resolved — transition to complete
            try:
                await transition_trip(trip, TripStatus.COMPLETE, db)
            except InvalidTransitionError:
                logger.warning("Could not transition trip %s to complete", trip.id)

    return approval
