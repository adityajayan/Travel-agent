"""Tests for GET/POST /trips/{id}/chat endpoints."""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from db.models import Trip, TripChatMessage


@pytest.mark.asyncio
async def test_get_chat_history_empty(api_client):
    """Chat history for a new trip is empty."""
    with patch("api.routes.trips._run_agent_task", new=AsyncMock()):
        create_resp = await api_client.post("/trips", json={"goal": "Trip to Bali"})
    trip_id = create_resp.json()["id"]

    resp = await api_client.get(f"/trips/{trip_id}/chat")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_get_chat_history_not_found(api_client):
    """Chat history for non-existent trip returns 404."""
    resp = await api_client.get(f"/trips/{uuid.uuid4()}/chat")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_send_chat_message(api_client):
    """Sending a chat message stores it and returns an assistant response."""
    with patch("api.routes.trips._run_agent_task", new=AsyncMock()):
        create_resp = await api_client.post("/trips", json={"goal": "Trip to London"})
    trip_id = create_resp.json()["id"]

    # The Claude API call will fail in tests (no key), so the fallback response is used
    resp = await api_client.post(
        f"/trips/{trip_id}/chat",
        json={"message": "What hotels are booked?"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["role"] == "assistant"
    assert data["trip_id"] == trip_id
    assert len(data["content"]) > 0


@pytest.mark.asyncio
async def test_chat_history_after_message(api_client):
    """After sending a message, history includes both user and assistant messages."""
    with patch("api.routes.trips._run_agent_task", new=AsyncMock()):
        create_resp = await api_client.post("/trips", json={"goal": "Trip to Berlin"})
    trip_id = create_resp.json()["id"]

    await api_client.post(
        f"/trips/{trip_id}/chat",
        json={"message": "Tell me about my trip"},
    )

    resp = await api_client.get(f"/trips/{trip_id}/chat")
    assert resp.status_code == 200
    messages = resp.json()
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "Tell me about my trip"
    assert messages[1]["role"] == "assistant"


@pytest.mark.asyncio
async def test_send_chat_to_nonexistent_trip(api_client):
    """Sending a chat to a non-existent trip returns 404."""
    resp = await api_client.post(
        f"/trips/{uuid.uuid4()}/chat",
        json={"message": "Hello"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_chat_message_with_existing_history(api_client, engine):
    """Multiple messages build up a conversation history."""
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    trip_id = str(uuid.uuid4())

    async with factory() as session:
        session.add(Trip(id=trip_id, goal="Trip to Tokyo", status="complete", total_spent=1500.0))
        session.add(TripChatMessage(
            id=str(uuid.uuid4()), trip_id=trip_id, role="user", content="First message",
        ))
        session.add(TripChatMessage(
            id=str(uuid.uuid4()), trip_id=trip_id, role="assistant", content="First reply",
        ))
        await session.commit()

    # Send another message
    resp = await api_client.post(
        f"/trips/{trip_id}/chat",
        json={"message": "Second message"},
    )
    assert resp.status_code == 200

    # Check full history
    history_resp = await api_client.get(f"/trips/{trip_id}/chat")
    messages = history_resp.json()
    assert len(messages) == 4  # 2 existing + user + assistant
