"""EventBus for real-time agent event streaming (M6 Item 2).

One asyncio.Queue per active trip — agents push, WebSocket handler consumes.
Connection drops must not crash the agent — silently discards if no subscribers.
"""
import asyncio
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class EventBus:
    """Per-trip event queue for real-time streaming."""

    _buses: Dict[str, "EventBus"] = {}
    # Per-trip response queues for clarification answers from the user
    _response_queues: Dict[str, asyncio.Queue] = {}

    def __init__(self, trip_id: str):
        self.trip_id = trip_id
        self._queue: asyncio.Queue = asyncio.Queue()
        self._subscribers: int = 0

    @classmethod
    def get_or_create(cls, trip_id: str) -> "EventBus":
        if trip_id not in cls._buses:
            cls._buses[trip_id] = cls(trip_id)
        return cls._buses[trip_id]

    @classmethod
    def remove(cls, trip_id: str) -> None:
        cls._buses.pop(trip_id, None)

    def subscribe(self) -> None:
        self._subscribers += 1

    def unsubscribe(self) -> None:
        self._subscribers = max(0, self._subscribers - 1)
        if self._subscribers == 0:
            # Clean up queue
            while not self._queue.empty():
                try:
                    self._queue.get_nowait()
                except asyncio.QueueEmpty:
                    break

    async def emit(self, event: Dict[str, Any]) -> None:
        """Push event to queue. Silently discards if no subscribers."""
        if self._subscribers > 0:
            try:
                self._queue.put_nowait(event)
            except asyncio.QueueFull:
                logger.warning("EventBus queue full for trip %s — dropping event", self.trip_id)

    async def consume(self, timeout: float = 30.0) -> Optional[Dict[str, Any]]:
        """Consume next event. Returns None on timeout."""
        try:
            return await asyncio.wait_for(self._queue.get(), timeout=timeout)
        except asyncio.TimeoutError:
            return None

    @classmethod
    def get_response_queue(cls, trip_id: str) -> asyncio.Queue:
        """Get or create a response queue for receiving clarification answers."""
        if trip_id not in cls._response_queues:
            cls._response_queues[trip_id] = asyncio.Queue()
        return cls._response_queues[trip_id]

    @classmethod
    def remove_response_queue(cls, trip_id: str) -> None:
        cls._response_queues.pop(trip_id, None)

    async def send_response(self, response: Dict[str, Any]) -> None:
        """Push a user response (e.g. clarification answers) into the response queue."""
        queue = self.get_response_queue(self.trip_id)
        await queue.put(response)

    async def wait_for_response(self, timeout: float = 300.0) -> Optional[Dict[str, Any]]:
        """Wait for a user response. Returns None on timeout (5 min default)."""
        queue = self.get_response_queue(self.trip_id)
        try:
            return await asyncio.wait_for(queue.get(), timeout=timeout)
        except asyncio.TimeoutError:
            return None
