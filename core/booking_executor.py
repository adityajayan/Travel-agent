"""Execute provider bookings after Stripe payment is confirmed."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from sqlalchemy import select

from core.audit_logger import AuditLogger
from core.event_bus import EventBus
from core.trip_lifecycle import TripStatus, transition_trip
from db.models import Booking, Trip
from providers.factory import get_provider

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def execute_paid_bookings(
    trip_id: str,
    payment_intent_id: str,
    db: "AsyncSession",
) -> None:
    """Book all confirmed items with providers after payment.

    Called from the Stripe webhook handler after checkout.session.completed.
    On full success → trip transitions to complete.
    On any failure → trip transitions to failed.
    """
    result = await db.execute(select(Trip).where(Trip.id == trip_id))
    trip = result.scalar_one_or_none()
    if not trip:
        logger.error("execute_paid_bookings: trip %s not found", trip_id)
        return

    booking_result = await db.execute(
        select(Booking).where(
            Booking.trip_id == trip_id,
            Booking.status == "confirmed",
        )
    )
    bookings = booking_result.scalars().all()

    if not bookings:
        logger.warning("No confirmed bookings to execute for trip %s", trip_id)
        await transition_trip(trip, TripStatus.COMPLETE, db)
        return

    bus = EventBus.get_or_create(trip_id)
    audit_logger = AuditLogger(db)
    failed_bookings = []
    successful_bookings = []

    for booking in bookings:
        try:
            provider = get_provider(booking.domain)
            details = booking.details or {}

            await bus.emit({
                "type": "booking_progress",
                "domain": booking.domain,
                "provider": booking.provider,
                "status": "executing",
                "message": f"Booking {booking.domain} with {booking.provider}...",
            })

            result = await provider.book(
                item_id=details.get("item_id", booking.id),
                details=details,
                payment_token=payment_intent_id,
            )

            booking.booking_reference = result.get("booking_reference", "")
            successful_bookings.append(booking)

            await bus.emit({
                "type": "booking_progress",
                "domain": booking.domain,
                "provider": booking.provider,
                "status": "confirmed",
                "booking_reference": booking.booking_reference,
            })

            logger.info(
                "Booked %s for trip %s: ref=%s",
                booking.domain, trip_id, booking.booking_reference,
            )

        except Exception as exc:
            logger.error(
                "Failed to book %s for trip %s: %s",
                booking.domain, trip_id, exc,
            )
            booking.status = "cancelled"
            failed_bookings.append((booking, str(exc)))

            await bus.emit({
                "type": "booking_progress",
                "domain": booking.domain,
                "provider": booking.provider,
                "status": "failed",
                "error": str(exc),
            })

    await db.commit()

    if failed_bookings:
        # Some bookings failed — mark trip as failed
        await transition_trip(trip, TripStatus.FAILED, db)
        failed_domains = [b.domain for b, _ in failed_bookings]
        await bus.emit({
            "type": "trip_failed",
            "message": f"Booking failed for: {', '.join(failed_domains)}. "
                       f"Refund will be processed for failed items.",
        })
    else:
        # All bookings succeeded
        await transition_trip(trip, TripStatus.COMPLETE, db)

        # Send trip summary email
        if trip.user_id:
            try:
                from sqlalchemy import select as sa_select
                from db.models import User
                user_result = await db.execute(sa_select(User).where(User.id == trip.user_id))
                user = user_result.scalar_one_or_none()
                if user:
                    from core.email import send_trip_summary
                    send_trip_summary(user.email, trip, successful_bookings)
            except Exception as exc:
                logger.warning("Failed to send trip summary email: %s", exc)

        await bus.emit({
            "type": "trip_completed",
            "summary": {
                "status": "complete",
                "bookings": [
                    {
                        "domain": b.domain,
                        "provider": b.provider,
                        "booking_reference": b.booking_reference,
                        "amount": b.amount,
                    }
                    for b in successful_bookings
                ],
                "total_spent": trip.total_spent,
            },
        })
