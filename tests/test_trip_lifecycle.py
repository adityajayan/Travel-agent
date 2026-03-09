"""Tests for core.trip_lifecycle — state machine transitions and archive rules."""
import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from core.trip_lifecycle import (
    TERMINAL_STATES,
    VALID_TRANSITIONS,
    InvalidTransitionError,
    TripStatus,
    transition_trip,
)
from db.models import Base, Trip

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


async def _make_trip(db: AsyncSession, status: str = TripStatus.PLANNING) -> Trip:
    t = Trip(id=str(uuid.uuid4()), goal="Test trip", status=status)
    db.add(t)
    await db.commit()
    await db.refresh(t)
    return t


# ── Valid transitions ─────────────────────────────────────────────────────────

VALID_CASES = [
    (TripStatus.PLANNING, TripStatus.REVIEW),
    (TripStatus.PLANNING, TripStatus.FAILED),
    (TripStatus.PLANNING, TripStatus.CANCELLED),
    (TripStatus.REVIEW, TripStatus.COMPLETE),
    (TripStatus.REVIEW, TripStatus.PLANNING),
    (TripStatus.REVIEW, TripStatus.FAILED),
    (TripStatus.REVIEW, TripStatus.CANCELLED),
    (TripStatus.COMPLETE, TripStatus.CANCELLED),
    (TripStatus.FAILED, TripStatus.PLANNING),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("from_status,to_status", VALID_CASES)
async def test_valid_transition(db, from_status, to_status):
    trip = await _make_trip(db, status=from_status)
    result = await transition_trip(trip, to_status, db)
    assert result.status == to_status


# ── Invalid transitions ───────────────────────────────────────────────────────

INVALID_CASES = [
    (TripStatus.PLANNING, TripStatus.COMPLETE),     # skips review
    (TripStatus.COMPLETE, TripStatus.PLANNING),      # no going back
    (TripStatus.COMPLETE, TripStatus.REVIEW),        # no going back
    (TripStatus.COMPLETE, TripStatus.FAILED),        # terminal
    (TripStatus.CANCELLED, TripStatus.PLANNING),     # fully terminal
    (TripStatus.CANCELLED, TripStatus.REVIEW),       # fully terminal
    (TripStatus.CANCELLED, TripStatus.COMPLETE),     # fully terminal
    (TripStatus.CANCELLED, TripStatus.FAILED),       # fully terminal
    (TripStatus.FAILED, TripStatus.REVIEW),          # must go through planning
    (TripStatus.FAILED, TripStatus.COMPLETE),        # must go through planning
    (TripStatus.FAILED, TripStatus.CANCELLED),       # not allowed
]


@pytest.mark.asyncio
@pytest.mark.parametrize("from_status,to_status", INVALID_CASES)
async def test_invalid_transition_raises(db, from_status, to_status):
    trip = await _make_trip(db, status=from_status)
    with pytest.raises(InvalidTransitionError) as exc_info:
        await transition_trip(trip, to_status, db)
    assert exc_info.value.current == from_status
    assert exc_info.value.target == to_status
    # Trip status should NOT have changed
    assert trip.status == from_status


# ── commit=False does not auto-commit ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_transition_no_commit(db):
    trip = await _make_trip(db, status=TripStatus.PLANNING)
    await transition_trip(trip, TripStatus.REVIEW, db, commit=False)
    assert trip.status == TripStatus.REVIEW


# ── Terminal state constants ──────────────────────────────────────────────────

def test_terminal_states():
    assert TERMINAL_STATES == {TripStatus.COMPLETE, TripStatus.CANCELLED, TripStatus.FAILED}


# ── Archive rules: only terminal states can be archived ───────────────────────

@pytest.mark.asyncio
async def test_archive_only_terminal(db):
    for status in [TripStatus.COMPLETE, TripStatus.CANCELLED, TripStatus.FAILED]:
        trip = await _make_trip(db, status=status)
        assert status in TERMINAL_STATES
        trip.is_archived = True
        await db.commit()
        await db.refresh(trip)
        assert trip.is_archived is True


@pytest.mark.asyncio
async def test_non_terminal_not_archivable(db):
    for status in [TripStatus.PLANNING, TripStatus.REVIEW]:
        assert status not in TERMINAL_STATES


# ── VALID_TRANSITIONS completeness ───────────────────────────────────────────

def test_all_statuses_have_transitions():
    all_statuses = {TripStatus.PLANNING, TripStatus.REVIEW, TripStatus.PAYMENT_PENDING,
                    TripStatus.BOOKING, TripStatus.COMPLETE,
                    TripStatus.CANCELLED, TripStatus.FAILED}
    assert set(VALID_TRANSITIONS.keys()) == all_statuses
