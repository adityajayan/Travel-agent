"""WebSocket and SSE streaming endpoints (M6 Item 2).

- ws:///trips/{id}/stream — WebSocket, pushes events as they happen
- GET /trips/{id}/events — SSE fallback for environments where WebSocket is blocked
"""
import asyncio
import json
import logging
from typing import Optional

import jwt
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse

from core.config import settings
from core.event_bus import EventBus

logger = logging.getLogger(__name__)

router = APIRouter(tags=["streaming"])


def _validate_ws_token(token: Optional[str]) -> bool:
    """Validate JWT for WebSocket connection (INV-12)."""
    if not settings.auth_secret:
        return True  # No auth configured

    if not token:
        return False

    try:
        jwt.decode(token, settings.auth_secret, algorithms=["HS256"])
        return True
    except Exception:
        return False


@router.websocket("/trips/{trip_id}/stream")
async def trip_websocket(
    websocket: WebSocket,
    trip_id: str,
    token: Optional[str] = Query(None),
):
    """WebSocket endpoint for real-time trip event streaming."""
    # Authenticate via query param token or first message
    if not _validate_ws_token(token):
        # Try to get token from first message
        await websocket.accept()
        try:
            first_msg = await asyncio.wait_for(websocket.receive_text(), timeout=5.0)
            try:
                data = json.loads(first_msg)
                token = data.get("token")
            except json.JSONDecodeError:
                token = first_msg

            if not _validate_ws_token(token):
                await websocket.send_json({"type": "error", "message": "Authentication failed"})
                await websocket.close(code=4001)
                return
        except asyncio.TimeoutError:
            await websocket.send_json({"type": "error", "message": "Authentication timeout"})
            await websocket.close(code=4001)
            return
    else:
        await websocket.accept()

    # Subscribe to the trip's event bus
    bus = EventBus.get_or_create(trip_id)
    bus.subscribe()

    try:
        while True:
            event = await bus.consume(timeout=30.0)
            if event is None:
                # Send heartbeat to keep connection alive
                try:
                    await websocket.send_json({"type": "heartbeat"})
                except Exception:
                    break
                continue

            try:
                await websocket.send_json(event)
            except Exception:
                break

            # If trip is done, close gracefully
            if event.get("type") in ("trip_completed", "trip_failed"):
                break

    except WebSocketDisconnect:
        logger.debug("WebSocket client disconnected for trip %s", trip_id)
    finally:
        bus.unsubscribe()


@router.get("/trips/{trip_id}/events")
async def trip_events_sse(trip_id: str):
    """SSE fallback endpoint — streams same events as WebSocket."""

    async def event_stream():
        bus = EventBus.get_or_create(trip_id)
        bus.subscribe()
        try:
            while True:
                event = await bus.consume(timeout=30.0)
                if event is None:
                    yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
                    continue

                yield f"data: {json.dumps(event)}\n\n"

                if event.get("type") in ("trip_completed", "trip_failed"):
                    break
        finally:
            bus.unsubscribe()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
