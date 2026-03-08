"""Tests for M8 cancellation flow (INV-16).

Tests cancellation policy retrieval, approval gate routing, and refund logging.
"""
import uuid

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from core.approval_gate import ApprovalGate, ApprovalRequiredError
from core.audit_logger import AuditLogger
from db.models import Base, HumanApproval, Trip
from providers.mock.flight_provider import MockFlightProvider
from providers.mock.hotel_provider import MockHotelProvider
from providers.mock.transport_provider import MockTransportProvider
from providers.mock.activity_provider import MockActivityProvider
from providers.schemas import CancellationPolicy

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def engine():
    eng = create_async_engine(TEST_DB_URL, echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def db(engine) -> AsyncSession:
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as session:
        yield session


@pytest_asyncio.fixture
async def trip(db) -> Trip:
    t = Trip(id=str(uuid.uuid4()), goal="Test trip", status="planning")
    db.add(t)
    await db.commit()
    await db.refresh(t)
    return t


# ── Cancellation Policy Retrieval ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_flight_cancellation_policy():
    """Mock flight provider returns cancellation policy."""
    provider = MockFlightProvider()
    policy = await provider.get_cancellation_policy("MOCK-FL001-BKG")
    assert isinstance(policy, CancellationPolicy)
    assert policy.booking_reference == "MOCK-FL001-BKG"
    assert policy.refundable is True
    assert policy.provider == "MockAir"


@pytest.mark.asyncio
async def test_hotel_cancellation_policy():
    """Mock hotel provider returns cancellation policy."""
    provider = MockHotelProvider()
    policy = await provider.get_cancellation_policy("MOCK-HTL001-BKG")
    assert isinstance(policy, CancellationPolicy)
    assert policy.refundable is True
    assert policy.provider == "MockHotels"


@pytest.mark.asyncio
async def test_transport_cancellation_policy():
    """Mock transport provider returns cancellation policy."""
    provider = MockTransportProvider()
    policy = await provider.get_cancellation_policy("MOCK-TRN001-BKG")
    assert isinstance(policy, CancellationPolicy)
    assert policy.refundable is True


@pytest.mark.asyncio
async def test_activity_cancellation_policy():
    """Mock activity provider returns cancellation policy."""
    provider = MockActivityProvider()
    policy = await provider.get_cancellation_policy("MOCK-ACT001-BKG")
    assert isinstance(policy, CancellationPolicy)
    assert policy.refundable is True


# ── Cancellation Through Approval Gate (INV-16) ─────────────────────────────

@pytest.mark.asyncio
async def test_cancellation_requires_approval(db, trip):
    """Cancellation through approval gate creates pending approval (INV-16)."""
    provider = MockFlightProvider()
    gate = ApprovalGate(db)
    gate._provider = provider

    with pytest.raises(ApprovalRequiredError) as exc_info:
        await gate.check_cancellation(
            trip.id, "flight", "MOCK-FL001-BKG"
        )

    # Verify the approval was created with cancellation details
    result = await db.execute(
        select(HumanApproval).where(HumanApproval.id == exc_info.value.approval_id)
    )
    approval = result.scalar_one()
    assert approval.status == "pending"
    assert approval.domain == "flight"
    assert "cancel_flight" in approval.action
    # Should contain refund/fee breakdown
    assert approval.details["refundable"] is True
    assert "refund_amount" in approval.details
    assert "cancellation_fee" in approval.details


@pytest.mark.asyncio
async def test_cancellation_approval_contains_policy_text(db, trip):
    """Cancellation approval details include policy text."""
    provider = MockHotelProvider()
    gate = ApprovalGate(db)
    gate._provider = provider

    with pytest.raises(ApprovalRequiredError) as exc_info:
        await gate.check_cancellation(
            trip.id, "hotel", "MOCK-HTL001-BKG"
        )

    result = await db.execute(
        select(HumanApproval).where(HumanApproval.id == exc_info.value.approval_id)
    )
    approval = result.scalar_one()
    assert "policy_text" in approval.details
    assert len(approval.details["policy_text"]) > 0


@pytest.mark.asyncio
async def test_cancellation_proceeds_after_approval(db, trip):
    """After approval, cancellation proceeds."""
    provider = MockFlightProvider()
    gate = ApprovalGate(db)
    gate._provider = provider

    # Create pre-approved record
    approval = HumanApproval(
        id=str(uuid.uuid4()),
        trip_id=trip.id,
        domain="flight",
        action="cancel_flight:MOCK-FL001-BKG",
        details={"booking_reference": "MOCK-FL001-BKG"},
        status="approved",
    )
    db.add(approval)
    await db.commit()

    # check_cancellation should return approval_id (not raise)
    approval_id = await gate.check_cancellation(
        trip.id, "flight", "MOCK-FL001-BKG"
    )
    assert approval_id == approval.id


@pytest.mark.asyncio
async def test_cancellation_no_provider_skips_policy_fetch(db, trip):
    """Without a provider, cancellation still works but without policy details."""
    gate = ApprovalGate(db)
    gate._provider = None

    with pytest.raises(ApprovalRequiredError):
        await gate.check_cancellation(
            trip.id, "flight", "BKG-001"
        )

    # Verify approval was created without policy details
    result = await db.execute(
        select(HumanApproval).where(
            HumanApproval.trip_id == trip.id,
            HumanApproval.status == "pending",
        )
    )
    approval = result.scalar_one()
    assert "booking_reference" in approval.details
    assert "refundable" not in approval.details


# ── Audit Logging for Cancellation ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_cancellation_audit_logging(db, trip):
    """Cancellation events are logged to audit trail."""
    audit = AuditLogger(db)

    # Log a cancellation event
    await audit.log_tool_call(
        trip.id,
        "FlightAgent",
        "cancel_flight",
        {"booking_reference": "MOCK-FL001-BKG"},
        {
            "status": "cancelled",
            "original_amount": 299.99,
            "refund_amount": 299.99,
            "cancellation_fee": 0,
            "reason": "User requested cancellation",
        },
    )

    # Verify it was logged
    from db.models import ToolCall
    result = await db.execute(
        select(ToolCall).where(
            ToolCall.trip_id == trip.id,
            ToolCall.tool_name == "cancel_flight",
        )
    )
    record = result.scalar_one()
    assert record.output["status"] == "cancelled"
    assert record.output["refund_amount"] == 299.99
