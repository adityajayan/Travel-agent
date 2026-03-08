"""Tests for M8 fare hold & price re-verification (INV-13).

Tests price verification flow, price change detection, and re-approval trigger.
"""
import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from core.approval_gate import ApprovalGate, ApprovalRequiredError, PriceChangedError
from db.models import Base, HumanApproval, Trip
from providers.mock.flight_provider import MockFlightProvider
from providers.schemas import PriceVerification, HoldResult, CancellationPolicy

from datetime import datetime, timezone


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


class PriceChangingFlightProvider(MockFlightProvider):
    """A mock provider that reports a price change on verify_price."""

    def __init__(self, new_price: float, original_price: float = 299.99):
        super().__init__()
        self._new_price = new_price
        self._original_price = original_price

    async def verify_price(self, item_id: str, original_price: float) -> PriceVerification:
        pct = abs(self._new_price - original_price) / original_price * 100 if original_price > 0 else 0
        return PriceVerification(
            item_id=item_id,
            current_price=self._new_price,
            original_price=original_price,
            price_changed=abs(self._new_price - original_price) > 0.01,
            pct_change=round(pct, 2),
            verified_at=datetime.now(timezone.utc),
        )


# ── Price Verification Tests ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_verify_price_unchanged(db, trip):
    """When price hasn't changed, verify_price reports no change."""
    provider = MockFlightProvider()
    gate = ApprovalGate(db)
    gate._provider = provider

    result = await gate.verify_price_before_approval(
        trip.id, "flight", "book_flight:FL001", "FL001", 299.99,
        {"flight_id": "FL001"},
    )
    assert result["price_changed"] is False
    assert result["current_price"] == 299.99


@pytest.mark.asyncio
async def test_verify_price_changed_within_threshold(db, trip):
    """Price changed < 5% — no re-approval needed."""
    provider = PriceChangingFlightProvider(new_price=310.00)  # ~3.3% increase
    gate = ApprovalGate(db)
    gate._provider = provider
    gate._price_threshold_pct = 5.0

    # Create an approved record first
    approval = HumanApproval(
        id=str(uuid.uuid4()),
        trip_id=trip.id,
        domain="flight",
        action="book_flight:FL001",
        details={"flight_id": "FL001", "verified_price": 299.99},
        status="approved",
    )
    db.add(approval)
    await db.commit()

    # verify_price_after_approval should NOT raise
    await gate.verify_price_after_approval(approval.id, "FL001", 299.99)


@pytest.mark.asyncio
async def test_verify_price_changed_beyond_threshold_triggers_reapproval(db, trip):
    """Price changed > 5% — triggers PriceChangedError with new approval (INV-13)."""
    provider = PriceChangingFlightProvider(new_price=350.00)  # ~16.7% increase
    gate = ApprovalGate(db)
    gate._provider = provider
    gate._price_threshold_pct = 5.0

    # Create an approved record
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

    with pytest.raises(PriceChangedError) as exc_info:
        await gate.verify_price_after_approval(approval.id, "FL001", 299.99)

    assert exc_info.value.original_price == 299.99
    assert exc_info.value.current_price == 350.00
    assert exc_info.value.pct_change > 5.0
    # New approval ID should be different
    assert exc_info.value.approval_id != approval.id


@pytest.mark.asyncio
async def test_verify_price_no_provider_skips_verification(db, trip):
    """When no provider is set, verification is skipped gracefully."""
    gate = ApprovalGate(db)
    gate._provider = None

    result = await gate.verify_price_before_approval(
        trip.id, "flight", "book_flight:FL001", "FL001", 299.99,
        {"flight_id": "FL001"},
    )
    assert result["price_changed"] is False


@pytest.mark.asyncio
async def test_verify_price_after_approval_no_provider_noop(db, trip):
    """When no provider is set, post-approval verification is a no-op."""
    gate = ApprovalGate(db)
    gate._provider = None

    # Should not raise
    await gate.verify_price_after_approval("some-id", "FL001", 299.99)


# ── Hold Fare Tests ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_default_hold_fare_not_supported():
    """Default hold_fare returns unsupported."""
    provider = MockFlightProvider()
    result = await provider.hold_fare("FL001")
    assert isinstance(result, HoldResult)
    assert result.supported is False


@pytest.mark.asyncio
async def test_mock_provider_verify_price():
    """Mock providers return unchanged price."""
    provider = MockFlightProvider()
    result = await provider.verify_price("FL001", 299.99)
    assert isinstance(result, PriceVerification)
    assert result.price_changed is False
    assert result.current_price == 299.99
    assert result.original_price == 299.99
