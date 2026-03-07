"""Tests for GET /trips/{id}/itinerary and PATCH /trips/{id}/itinerary/items/{id}."""
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from db.models import Booking, HumanApproval, Trip


@pytest.mark.asyncio
async def test_get_itinerary_not_found(api_client):
    resp = await api_client.get(f"/trips/{uuid.uuid4()}/itinerary")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_itinerary_empty_trip(api_client):
    """A trip with no bookings returns a valid but empty itinerary."""
    with patch("api.routes.trips._run_agent_task", new=AsyncMock()):
        create_resp = await api_client.post("/trips", json={"goal": "Trip to Tokyo"})
    trip_id = create_resp.json()["id"]

    resp = await api_client.get(f"/trips/{trip_id}/itinerary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["trip_id"] == trip_id
    assert data["title"] == "Trip to Tokyo"
    assert data["status"] == "pending"
    assert data["days"] == []
    assert data["budget"]["allocated"] == 0


@pytest.mark.asyncio
async def test_get_itinerary_with_bookings(api_client, engine):
    """Itinerary groups bookings, calculates budget, and maps statuses."""
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    trip_id = str(uuid.uuid4())

    async with factory() as session:
        session.add(Trip(
            id=trip_id, goal="5 days in Paris", status="complete",
            total_spent=2150.0, total_budget=3000.0,
        ))
        session.add(Booking(
            id=str(uuid.uuid4()), trip_id=trip_id, domain="flight",
            provider="United", amount=1200.0,
            details={"origin": "SFO", "destination": "CDG", "airline": "United"},
        ))
        session.add(Booking(
            id=str(uuid.uuid4()), trip_id=trip_id, domain="hotel",
            provider="Hilton", amount=950.0,
            details={"hotel_name": "Hilton Paris Opera", "room_type": "Deluxe King"},
        ))
        await session.commit()

    resp = await api_client.get(f"/trips/{trip_id}/itinerary")
    assert resp.status_code == 200
    data = resp.json()

    assert data["trip_id"] == trip_id
    assert data["status"] == "complete"
    assert len(data["days"]) >= 1

    # Check budget breakdown
    budget = data["budget"]
    assert budget["total"] == 3000.0
    assert budget["allocated"] == 2150.0
    assert budget["remaining"] == 850.0
    assert "flight" in budget["by_category"]
    assert "hotel" in budget["by_category"]
    assert budget["by_category"]["flight"] == 1200.0
    assert budget["by_category"]["hotel"] == 950.0

    # Check items exist
    all_items = []
    for day in data["days"]:
        all_items.extend(day["items"])
    assert len(all_items) == 2

    types = {item["type"] for item in all_items}
    assert "flight" in types
    assert "hotel" in types


@pytest.mark.asyncio
async def test_get_itinerary_with_pending_approval(api_client, engine):
    """Items with pending approvals show awaiting_approval status."""
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    trip_id = str(uuid.uuid4())
    approval_id = str(uuid.uuid4())

    async with factory() as session:
        session.add(Trip(id=trip_id, goal="Trip to Rome", status="awaiting_approval"))
        session.add(Booking(
            id=str(uuid.uuid4()), trip_id=trip_id, domain="flight",
            provider="Alitalia", amount=800.0, details={},
        ))
        session.add(HumanApproval(
            id=approval_id, trip_id=trip_id, domain="flight",
            action="book_flight", status="pending", details={},
        ))
        await session.commit()

    resp = await api_client.get(f"/trips/{trip_id}/itinerary")
    assert resp.status_code == 200
    data = resp.json()

    items = data["days"][0]["items"]
    flight_item = next(i for i in items if i["type"] == "flight")
    assert flight_item["status"] == "awaiting_approval"
    assert flight_item["approval_id"] == approval_id


@pytest.mark.asyncio
async def test_patch_itinerary_item_approve(api_client, engine):
    """Approving an item via the artifact view works."""
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    trip_id = str(uuid.uuid4())
    booking_id = str(uuid.uuid4())
    approval_id = str(uuid.uuid4())

    async with factory() as session:
        session.add(Trip(id=trip_id, goal="Test trip", status="awaiting_approval"))
        session.add(Booking(
            id=booking_id, trip_id=trip_id, domain="hotel",
            provider="Marriott", amount=500.0, details={},
        ))
        session.add(HumanApproval(
            id=approval_id, trip_id=trip_id, domain="hotel",
            action="book_hotel", status="pending", details={},
        ))
        await session.commit()

    resp = await api_client.patch(
        f"/trips/{trip_id}/itinerary/items/{booking_id}",
        json={"action": "approve"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"


@pytest.mark.asyncio
async def test_patch_itinerary_item_reject(api_client, engine):
    """Rejecting an item via the artifact view works."""
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    trip_id = str(uuid.uuid4())
    booking_id = str(uuid.uuid4())
    approval_id = str(uuid.uuid4())

    async with factory() as session:
        session.add(Trip(id=trip_id, goal="Test trip", status="awaiting_approval"))
        session.add(Booking(
            id=booking_id, trip_id=trip_id, domain="flight",
            provider="Delta", amount=700.0, details={},
        ))
        session.add(HumanApproval(
            id=approval_id, trip_id=trip_id, domain="flight",
            action="book_flight", status="pending", details={},
        ))
        await session.commit()

    resp = await api_client.patch(
        f"/trips/{trip_id}/itinerary/items/{booking_id}",
        json={"action": "reject"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "rejected"


@pytest.mark.asyncio
async def test_patch_itinerary_item_not_found(api_client):
    """Patching a non-existent trip returns 404."""
    resp = await api_client.patch(
        f"/trips/{uuid.uuid4()}/itinerary/items/{uuid.uuid4()}",
        json={"action": "approve"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_patch_itinerary_item_invalid_action(api_client, engine):
    """An unknown action returns 400."""
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    trip_id = str(uuid.uuid4())
    booking_id = str(uuid.uuid4())

    async with factory() as session:
        session.add(Trip(id=trip_id, goal="Test", status="complete"))
        session.add(Booking(
            id=booking_id, trip_id=trip_id, domain="flight",
            provider="AA", amount=100.0, details={},
        ))
        await session.commit()

    resp = await api_client.patch(
        f"/trips/{trip_id}/itinerary/items/{booking_id}",
        json={"action": "invalid_action"},
    )
    # Either 400 (no pending approval) or 400 (unknown action)
    assert resp.status_code == 400
