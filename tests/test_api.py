"""Integration tests for the FastAPI routes."""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from db.models import HumanApproval, Trip


# ── /trips ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_trip_returns_202(api_client):
    with patch("api.routes.trips._run_agent_task", new=AsyncMock()):
        resp = await api_client.post("/trips", json={"goal": "Fly me to Paris"})
    assert resp.status_code == 202
    data = resp.json()
    assert data["status"] == "pending"
    assert data["goal"] == "Fly me to Paris"
    assert "id" in data


@pytest.mark.asyncio
async def test_get_trip_not_found(api_client):
    resp = await api_client.get(f"/trips/{uuid.uuid4()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_trip_found(api_client):
    with patch("api.routes.trips._run_agent_task", new=AsyncMock()):
        create_resp = await api_client.post("/trips", json={"goal": "Hotel in Rome"})
    trip_id = create_resp.json()["id"]

    get_resp = await api_client.get(f"/trips/{trip_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == trip_id


@pytest.mark.asyncio
async def test_list_trips(api_client):
    with patch("api.routes.trips._run_agent_task", new=AsyncMock()):
        await api_client.post("/trips", json={"goal": "Trip A"})
        await api_client.post("/trips", json={"goal": "Trip B"})

    resp = await api_client.get("/trips")
    assert resp.status_code == 200
    assert len(resp.json()) >= 2


# ── /approvals ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_approval_not_found(api_client):
    resp = await api_client.get(f"/approvals/{uuid.uuid4()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_decide_approval_approve(api_client, engine):
    """Create a pending approval in DB, then approve via API."""
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    trip_id = str(uuid.uuid4())
    approval_id = str(uuid.uuid4())

    async with factory() as session:
        session.add(Trip(id=trip_id, goal="Test", status="pending"))
        session.add(
            HumanApproval(
                id=approval_id,
                trip_id=trip_id,
                domain="flight",
                action="book_flight:FL001",
                details={},
                status="pending",
            )
        )
        await session.commit()

    resp = await api_client.post(
        f"/approvals/{approval_id}/decide", json={"approved": True}
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"


@pytest.mark.asyncio
async def test_decide_approval_reject(api_client, engine):
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    trip_id = str(uuid.uuid4())
    approval_id = str(uuid.uuid4())

    async with factory() as session:
        session.add(Trip(id=trip_id, goal="Test", status="pending"))
        session.add(
            HumanApproval(
                id=approval_id,
                trip_id=trip_id,
                domain="hotel",
                action="book_hotel:HTL001",
                details={},
                status="pending",
            )
        )
        await session.commit()

    resp = await api_client.post(
        f"/approvals/{approval_id}/decide", json={"approved": False}
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "rejected"


@pytest.mark.asyncio
async def test_decide_approval_not_found(api_client):
    resp = await api_client.post(
        f"/approvals/{uuid.uuid4()}/decide", json={"approved": True}
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_approvals_by_trip(api_client, engine):
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    trip_id = str(uuid.uuid4())

    async with factory() as session:
        session.add(Trip(id=trip_id, goal="Test", status="pending"))
        session.add(
            HumanApproval(
                id=str(uuid.uuid4()),
                trip_id=trip_id,
                domain="flight",
                action="book_flight:FL001",
                details={},
                status="pending",
            )
        )
        await session.commit()

    resp = await api_client.get(f"/approvals?trip_id={trip_id}")
    assert resp.status_code == 200
    approvals = resp.json()
    assert len(approvals) == 1
    assert approvals[0]["trip_id"] == trip_id
