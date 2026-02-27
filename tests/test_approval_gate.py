"""Tests for ApprovalGate – verifying the two-layer booking enforcement invariant."""
import uuid

import pytest

from core.approval_gate import (
    ApprovalGate,
    ApprovalRequiredError,
    ApprovalRejectedError,
)
from db.models import HumanApproval


@pytest.mark.asyncio
async def test_check_creates_pending_record_and_raises(db, trip):
    gate = ApprovalGate(db)
    with pytest.raises(ApprovalRequiredError) as exc_info:
        await gate.check(trip.id, "flight", "book_flight:FL001", {"flight_id": "FL001"})

    approval_id = exc_info.value.approval_id
    assert approval_id  # should be a non-empty string

    # DB record should exist and be pending
    approval = await db.get(HumanApproval, approval_id)
    assert approval is not None
    assert approval.status == "pending"
    assert approval.domain == "flight"
    assert approval.action == "book_flight:FL001"


@pytest.mark.asyncio
async def test_check_returns_id_when_approved(db, trip):
    gate = ApprovalGate(db)

    # Pre-insert approved record
    approval = HumanApproval(
        id=str(uuid.uuid4()),
        trip_id=trip.id,
        domain="flight",
        action="book_flight:FL001",
        details={"flight_id": "FL001"},
        status="approved",
    )
    db.add(approval)
    await db.commit()

    # Should not raise; should return the approval_id
    returned_id = await gate.check(trip.id, "flight", "book_flight:FL001", {})
    assert returned_id == approval.id


@pytest.mark.asyncio
async def test_check_raises_rejected_when_rejected(db, trip):
    gate = ApprovalGate(db)

    rejected = HumanApproval(
        id=str(uuid.uuid4()),
        trip_id=trip.id,
        domain="hotel",
        action="book_hotel:HTL001",
        details={},
        status="rejected",
    )
    db.add(rejected)
    await db.commit()

    with pytest.raises(ApprovalRejectedError):
        await gate.check(trip.id, "hotel", "book_hotel:HTL001", {})


@pytest.mark.asyncio
async def test_verify_approved_returns_false_for_pending(db, trip):
    gate = ApprovalGate(db)

    approval = HumanApproval(
        id=str(uuid.uuid4()),
        trip_id=trip.id,
        domain="flight",
        action="book_flight:FL001",
        details={},
        status="pending",
    )
    db.add(approval)
    await db.commit()

    assert not await gate.verify_approved(approval.id)


@pytest.mark.asyncio
async def test_verify_approved_returns_true_for_approved(db, trip):
    gate = ApprovalGate(db)

    approval = HumanApproval(
        id=str(uuid.uuid4()),
        trip_id=trip.id,
        domain="flight",
        action="book_flight:FL001",
        details={},
        status="approved",
    )
    db.add(approval)
    await db.commit()

    assert await gate.verify_approved(approval.id)


@pytest.mark.asyncio
async def test_verify_approved_returns_false_for_nonexistent(db):
    gate = ApprovalGate(db)
    assert not await gate.verify_approved("nonexistent-id")


@pytest.mark.asyncio
async def test_decide_approve(db, trip):
    gate = ApprovalGate(db)

    approval = HumanApproval(
        id=str(uuid.uuid4()),
        trip_id=trip.id,
        domain="flight",
        action="book_flight:FL001",
        details={},
        status="pending",
    )
    db.add(approval)
    await db.commit()

    updated = await gate.decide(approval.id, approved=True)
    assert updated.status == "approved"
    assert updated.decided_at is not None


@pytest.mark.asyncio
async def test_decide_reject(db, trip):
    gate = ApprovalGate(db)

    approval = HumanApproval(
        id=str(uuid.uuid4()),
        trip_id=trip.id,
        domain="flight",
        action="book_flight:FL001",
        details={},
        status="pending",
    )
    db.add(approval)
    await db.commit()

    updated = await gate.decide(approval.id, approved=False)
    assert updated.status == "rejected"


@pytest.mark.asyncio
async def test_decide_raises_for_nonexistent(db):
    gate = ApprovalGate(db)
    with pytest.raises(ValueError, match="not found"):
        await gate.decide("bad-id", approved=True)


@pytest.mark.asyncio
async def test_repeated_check_reuses_pending_record(db, trip):
    """Second call without approving should raise with the same approval_id."""
    gate = ApprovalGate(db)

    with pytest.raises(ApprovalRequiredError) as exc1:
        await gate.check(trip.id, "flight", "book_flight:FL001", {})

    with pytest.raises(ApprovalRequiredError) as exc2:
        await gate.check(trip.id, "flight", "book_flight:FL001", {})

    assert exc1.value.approval_id == exc2.value.approval_id
