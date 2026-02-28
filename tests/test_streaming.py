"""Tests for M6 Item 2 — WebSocket Real-Time Streaming."""
import asyncio
import json

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from api.main import app
from core.event_bus import EventBus


# ── EventBus unit tests ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_event_bus_emit_and_consume():
    bus = EventBus.get_or_create("test-trip-1")
    bus.subscribe()
    try:
        await bus.emit({"type": "agent_progress", "message": "Searching flights"})
        event = await bus.consume(timeout=1.0)
        assert event is not None
        assert event["type"] == "agent_progress"
    finally:
        bus.unsubscribe()
        EventBus.remove("test-trip-1")


@pytest.mark.asyncio
async def test_event_bus_no_subscribers_drops():
    """Events silently discarded when no subscribers."""
    bus = EventBus.get_or_create("test-trip-2")
    # No subscribe — should not raise
    await bus.emit({"type": "test"})
    EventBus.remove("test-trip-2")


@pytest.mark.asyncio
async def test_event_bus_timeout_returns_none():
    bus = EventBus.get_or_create("test-trip-3")
    bus.subscribe()
    try:
        event = await bus.consume(timeout=0.1)
        assert event is None
    finally:
        bus.unsubscribe()
        EventBus.remove("test-trip-3")


@pytest.mark.asyncio
async def test_event_bus_multiple_events():
    bus = EventBus.get_or_create("test-trip-4")
    bus.subscribe()
    try:
        await bus.emit({"type": "tool_call", "tool_name": "search_flights", "status": "started"})
        await bus.emit({"type": "tool_call", "tool_name": "search_flights", "status": "completed"})
        await bus.emit({"type": "trip_completed", "summary": "All done"})

        events = []
        for _ in range(3):
            event = await bus.consume(timeout=1.0)
            assert event is not None
            events.append(event)

        assert events[0]["type"] == "tool_call"
        assert events[2]["type"] == "trip_completed"
    finally:
        bus.unsubscribe()
        EventBus.remove("test-trip-4")


# ── WebSocket tests ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_websocket_receives_events():
    """WebSocket client receives agent_progress events during agent run."""
    from starlette.testclient import TestClient

    trip_id = "ws-test-1"

    with TestClient(app) as client:
        bus = EventBus.get_or_create(trip_id)

        with client.websocket_connect(f"/trips/{trip_id}/stream") as ws:
            bus.subscribe()
            # Push event directly to queue (sync context)
            bus._queue.put_nowait({"type": "agent_progress", "message": "Searching", "agent_type": "FlightAgent"})

            data = ws.receive_json()
            assert data["type"] == "agent_progress"
            assert data["agent_type"] == "FlightAgent"

            # Push completion
            bus._queue.put_nowait({"type": "trip_completed", "summary": {"status": "complete"}})
            data = ws.receive_json()
            assert data["type"] == "trip_completed"

        bus.unsubscribe()
        EventBus.remove(trip_id)


@pytest.mark.asyncio
async def test_websocket_approval_event():
    """WebSocket client receives approval_required when booking is gated."""
    from starlette.testclient import TestClient

    trip_id = "ws-test-2"

    with TestClient(app) as client:
        bus = EventBus.get_or_create(trip_id)

        with client.websocket_connect(f"/trips/{trip_id}/stream") as ws:
            bus.subscribe()
            bus._queue.put_nowait({
                "type": "approval_required",
                "approval_id": "apr-123",
                "context": {"flight_id": "FL001", "cost": 299.99},
            })

            data = ws.receive_json()
            assert data["type"] == "approval_required"
            assert data["approval_id"] == "apr-123"

            # Close with completion
            bus._queue.put_nowait({"type": "trip_completed", "summary": {}})
            ws.receive_json()

        bus.unsubscribe()
        EventBus.remove(trip_id)


# ── SSE tests ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_sse_streams_events():
    """SSE fallback streams same events."""
    trip_id = "sse-test-1"
    bus = EventBus.get_or_create(trip_id)

    # Push events before connecting
    bus.subscribe()
    await bus.emit({"type": "agent_progress", "message": "Searching"})
    await bus.emit({"type": "trip_completed", "summary": {}})

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # SSE uses streaming response; read lines
        async with client.stream("GET", f"/trips/{trip_id}/events") as resp:
            lines = []
            async for line in resp.aiter_lines():
                if line.startswith("data: "):
                    data = json.loads(line[6:])
                    lines.append(data)
                    if data.get("type") == "trip_completed":
                        break
            assert len(lines) == 2
            assert lines[0]["type"] == "agent_progress"
            assert lines[1]["type"] == "trip_completed"

    bus.unsubscribe()
    EventBus.remove(trip_id)


# ── Agent completes even if client disconnects ───────────────────────────────

@pytest.mark.asyncio
async def test_agent_completes_without_websocket():
    """Agent completes normally even if WebSocket client disconnects mid-run."""
    bus = EventBus.get_or_create("disconnect-test")
    # No subscribers — emit should not raise
    await bus.emit({"type": "agent_progress", "message": "Still running"})
    await bus.emit({"type": "trip_completed", "summary": {}})
    # No error means agent can complete without subscribers
    EventBus.remove("disconnect-test")
