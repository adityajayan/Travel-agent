"""Trip status state machine — single source of truth for valid transitions."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession
    from db.models import Trip

logger = logging.getLogger(__name__)


class TripStatus:
    PLANNING = "planning"
    REVIEW = "review"
    COMPLETE = "complete"
    CANCELLED = "cancelled"
    FAILED = "failed"


VALID_TRANSITIONS: dict[str, set[str]] = {
    TripStatus.PLANNING: {TripStatus.REVIEW, TripStatus.FAILED, TripStatus.CANCELLED},
    TripStatus.REVIEW: {TripStatus.COMPLETE, TripStatus.PLANNING, TripStatus.FAILED, TripStatus.CANCELLED},
    TripStatus.COMPLETE: {TripStatus.CANCELLED},
    TripStatus.CANCELLED: set(),
    TripStatus.FAILED: {TripStatus.PLANNING},
}

TERMINAL_STATES = {TripStatus.COMPLETE, TripStatus.CANCELLED, TripStatus.FAILED}


class InvalidTransitionError(Exception):
    def __init__(self, current: str, target: str) -> None:
        self.current = current
        self.target = target
        allowed = [s for s in VALID_TRANSITIONS.get(current, set())]
        super().__init__(
            f"Cannot transition from '{current}' to '{target}'. "
            f"Allowed: {allowed}"
        )


async def transition_trip(
    trip: "Trip",
    target_status: str,
    db: "AsyncSession",
    *,
    commit: bool = True,
) -> "Trip":
    """Validate and execute a trip status transition.

    Raises InvalidTransitionError if the transition is not allowed.
    """
    current = trip.status
    allowed = VALID_TRANSITIONS.get(current, set())

    if target_status not in allowed:
        raise InvalidTransitionError(current, target_status)

    old_status = trip.status
    trip.status = target_status

    if commit:
        await db.commit()
        await db.refresh(trip)

    logger.info("Trip %s: %s → %s", trip.id, old_status, target_status)
    return trip
