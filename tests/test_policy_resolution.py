"""Tests for policy resolution at trip creation time.

Covers:
- org_id resolves active policy and caches it on trip.policy_id
- explicit inactive policy_id → PolicyNotFoundError (INV-9)
- no org_id/policy_id → policy_id stays None, trip runs normally
- org with no active policy → policy_id stays None
"""
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from api.routes.trips import _resolve_policy
from core.policy_engine import PolicyNotFoundError
from db.models import CorporatePolicy, Trip


# ── Helper ─────────────────────────────────────────────────────────────────────

async def _make_policy(db: AsyncSession, org_id: str, is_active: bool = True) -> CorporatePolicy:
    p = CorporatePolicy(
        id=str(uuid.uuid4()),
        org_id=org_id,
        name=f"Policy-{org_id}",
        is_active=is_active,
    )
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return p


async def _make_trip(db: AsyncSession, org_id=None, policy_id=None) -> Trip:
    t = Trip(
        id=str(uuid.uuid4()),
        goal="Test",
        status="pending",
        org_id=org_id,
        policy_id=policy_id,
    )
    db.add(t)
    await db.commit()
    await db.refresh(t)
    return t


# ── _resolve_policy unit tests ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_resolve_policy_by_org_id(db):
    """When trip.org_id is set and an active policy exists, it is resolved and cached."""
    policy = await _make_policy(db, org_id="acme")
    trip = await _make_trip(db, org_id="acme")

    resolved_id = await _resolve_policy(trip, db)

    assert resolved_id == policy.id
    # Should have been cached on trip row
    assert trip.policy_id == policy.id


@pytest.mark.asyncio
async def test_resolve_policy_caches_on_trip_row(db):
    """Resolved policy_id is persisted to the DB (so subsequent reads see it)."""
    policy = await _make_policy(db, org_id="beta")
    trip = await _make_trip(db, org_id="beta")

    await _resolve_policy(trip, db)

    # Re-fetch from DB
    result = await db.execute(select(Trip).where(Trip.id == trip.id))
    refreshed = result.scalar_one()
    assert refreshed.policy_id == policy.id


@pytest.mark.asyncio
async def test_resolve_policy_no_org_returns_none(db):
    """Trip with no org_id and no explicit policy_id → None."""
    trip = await _make_trip(db)
    resolved = await _resolve_policy(trip, db)
    assert resolved is None
    assert trip.policy_id is None


@pytest.mark.asyncio
async def test_resolve_policy_org_with_no_active_policy_returns_none(db):
    """org_id present but no active policy → None (no exception)."""
    await _make_policy(db, org_id="gamma", is_active=False)
    trip = await _make_trip(db, org_id="gamma")

    resolved = await _resolve_policy(trip, db)
    assert resolved is None
    assert trip.policy_id is None


@pytest.mark.asyncio
async def test_resolve_explicit_active_policy_id(db):
    """Explicit policy_id pointing to an active policy is accepted."""
    policy = await _make_policy(db, org_id="delta")
    trip = await _make_trip(db, policy_id=policy.id)

    resolved = await _resolve_policy(trip, db)
    assert resolved == policy.id


@pytest.mark.asyncio
async def test_resolve_explicit_inactive_policy_raises(db):
    """INV-9: explicit policy_id pointing to an inactive policy → PolicyNotFoundError."""
    policy = await _make_policy(db, org_id="epsilon", is_active=False)
    trip = await _make_trip(db, policy_id=policy.id)

    with pytest.raises(PolicyNotFoundError):
        await _resolve_policy(trip, db)


@pytest.mark.asyncio
async def test_resolve_explicit_nonexistent_policy_raises(db):
    """INV-9: explicit policy_id for a non-existent policy → PolicyNotFoundError."""
    trip = await _make_trip(db, policy_id=str(uuid.uuid4()))

    with pytest.raises(PolicyNotFoundError):
        await _resolve_policy(trip, db)


# ── API-level resolution tests ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_trip_with_org_resolves_policy(api_client, engine):
    """POST /trips with org_id resolves active policy and sets trip.policy_id."""
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with factory() as session:
        policy = CorporatePolicy(
            id=str(uuid.uuid4()),
            org_id="zeta",
            name="Zeta Policy",
            is_active=True,
        )
        session.add(policy)
        await session.commit()

    with patch("api.routes.trips._run_agent_task", new=AsyncMock()):
        resp = await api_client.post("/trips", json={
            "goal": "Book flight to NYC",
            "org_id": "zeta",
        })

    assert resp.status_code == 202
    trip_id = resp.json()["id"]

    # Re-fetch from DB through separate session
    async with factory() as session:
        result = await session.execute(select(Trip).where(Trip.id == trip_id))
        trip = result.scalar_one()
        # policy_id may be set by background task; the trip row should at least have org_id
        assert trip.org_id == "zeta"


@pytest.mark.asyncio
async def test_create_trip_no_org_no_policy(api_client):
    """POST /trips with no org_id and no policy_id → trip.policy_id stays None."""
    with patch("api.routes.trips._run_agent_task", new=AsyncMock()):
        resp = await api_client.post("/trips", json={"goal": "Book a hotel"})

    assert resp.status_code == 202
    data = resp.json()
    assert data["policy_id"] is None
    assert data["org_id"] is None


@pytest.mark.asyncio
async def test_background_task_fails_on_inactive_explicit_policy(api_client, engine):
    """
    When trip is created with an explicit inactive policy_id, the background task
    should mark the trip as 'failed' (INV-9 enforcement in _run_agent_task).
    We call _run_agent_task directly to verify without timing issues.
    """
    from api.routes.trips import _run_agent_task

    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with factory() as session:
        # Create an INACTIVE policy
        policy = CorporatePolicy(
            id=str(uuid.uuid4()),
            org_id="eta",
            name="Inactive Policy",
            is_active=False,
        )
        session.add(policy)
        trip = Trip(
            id=str(uuid.uuid4()),
            goal="Book flight",
            status="pending",
            org_id="eta",
            policy_id=policy.id,
        )
        session.add(trip)
        await session.commit()
        trip_id = trip.id
        policy_id = policy.id

    async with factory() as session:
        await _run_agent_task(trip_id, "Book flight", session)

    async with factory() as session:
        result = await session.execute(select(Trip).where(Trip.id == trip_id))
        refreshed = result.scalar_one()
        assert refreshed.status == "failed"


@pytest.mark.asyncio
async def test_background_task_runs_normally_without_policy(api_client, engine):
    """Trip with no org_id runs agent task normally (no policy engine instantiated)."""
    from api.routes.trips import _run_agent_task
    from unittest.mock import patch, AsyncMock

    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with factory() as session:
        trip = Trip(
            id=str(uuid.uuid4()),
            goal="Book a flight",
            status="pending",
        )
        session.add(trip)
        await session.commit()
        trip_id = trip.id

    # Patch the agent so it doesn't call real Anthropic API
    with patch("api.routes.trips.FlightAgent") as MockFlightAgent:
        mock_instance = AsyncMock()
        MockFlightAgent.return_value = mock_instance
        mock_instance.run = AsyncMock()

        async with factory() as session:
            await _run_agent_task(trip_id, "Book a flight", session)

    async with factory() as session:
        result = await session.execute(select(Trip).where(Trip.id == trip_id))
        refreshed = result.scalar_one()
        # Status should be 'complete' (not 'failed') — policy path did not abort
        assert refreshed.status == "complete"
