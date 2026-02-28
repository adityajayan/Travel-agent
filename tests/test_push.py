"""Tests for M6 Item 5 — Push Notification endpoints."""
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from api.main import app


@pytest_asyncio.fixture
async def push_client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client


# ── Subscribe / Unsubscribe ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_push_subscribe(push_client):
    resp = await push_client.post("/push/subscribe", json={
        "endpoint": "https://push.example.com/sub/abc123",
        "keys": {"p256dh": "test-key", "auth": "test-auth"},
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "subscribed"


@pytest.mark.asyncio
async def test_push_unsubscribe(push_client):
    # Subscribe first
    await push_client.post("/push/subscribe", json={
        "endpoint": "https://push.example.com/sub/xyz",
        "keys": {"p256dh": "k", "auth": "a"},
    })
    resp = await push_client.post("/push/unsubscribe", json={
        "endpoint": "https://push.example.com/sub/xyz",
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "unsubscribed"


@pytest.mark.asyncio
async def test_push_unsubscribe_unknown_endpoint(push_client):
    resp = await push_client.post("/push/unsubscribe", json={
        "endpoint": "https://push.example.com/sub/nope",
    })
    assert resp.status_code == 200  # Idempotent


# ── Send without VAPID keys → 501 ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_push_send_without_vapid_returns_501(push_client):
    resp = await push_client.post("/push/send", json={
        "title": "Test",
        "body": "Hello",
    })
    assert resp.status_code == 501
    assert "VAPID" in resp.json()["detail"]
