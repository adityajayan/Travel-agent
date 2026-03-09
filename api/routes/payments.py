"""Stripe payment routes for trip checkout."""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import CurrentUser, get_current_user
from core.config import settings
from core.trip_lifecycle import TripStatus, transition_trip
from db.database import get_db
from db.models import Booking, Payment, Trip

logger = logging.getLogger(__name__)

router = APIRouter(tags=["payments"])


class CheckoutResponse(BaseModel):
    checkout_url: str
    session_id: str


class PaymentStatusResponse(BaseModel):
    trip_id: str
    payment_status: str
    stripe_session_id: Optional[str] = None


@router.post("/trips/{trip_id}/checkout", response_model=CheckoutResponse)
async def create_checkout_session(
    trip_id: str,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    """Create a Stripe Checkout Session for a trip's approved items."""
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=503, detail="Payments not configured")

    import stripe
    stripe.api_key = settings.stripe_secret_key

    # Load trip
    result = await db.execute(select(Trip).where(Trip.id == trip_id))
    trip = result.scalar_one_or_none()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    if trip.status != TripStatus.REVIEW:
        raise HTTPException(
            status_code=400,
            detail=f"Trip must be in 'review' status to checkout (current: {trip.status})",
        )

    # Fetch confirmed bookings
    booking_result = await db.execute(
        select(Booking).where(
            Booking.trip_id == trip_id,
            Booking.status == "confirmed",
        )
    )
    bookings = booking_result.scalars().all()
    if not bookings:
        raise HTTPException(status_code=400, detail="No confirmed bookings to pay for")

    # Build Stripe line items
    line_items = []
    for b in bookings:
        details = b.details or {}
        name = details.get("name", details.get("hotel_name", f"{b.domain.capitalize()} booking"))
        line_items.append({
            "price_data": {
                "currency": "usd",
                "unit_amount": int(b.amount * 100),  # cents
                "product_data": {
                    "name": str(name),
                    "description": f"{b.domain.capitalize()} via {b.provider}",
                },
            },
            "quantity": 1,
        })

    # Add service fee
    if settings.service_fee_cents > 0:
        line_items.append({
            "price_data": {
                "currency": "usd",
                "unit_amount": settings.service_fee_cents,
                "product_data": {
                    "name": "Concierge Service Fee",
                    "description": "Trip planning and booking service",
                },
            },
            "quantity": 1,
        })

    total_cents = sum(item["price_data"]["unit_amount"] * item["quantity"] for item in line_items)

    # Create Stripe Checkout Session
    success_url = f"{settings.frontend_url}/payment/success?trip_id={trip_id}&session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{settings.frontend_url}/payment/cancel?trip_id={trip_id}"

    checkout_session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=line_items,
        mode="payment",
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            "trip_id": trip_id,
            "user_id": user.user_id,
        },
    )

    # Record payment
    payment = Payment(
        id=str(uuid.uuid4()),
        trip_id=trip_id,
        user_id=user.user_id if user.user_id != "anonymous" else None,
        stripe_checkout_session_id=checkout_session.id,
        amount_cents=total_cents,
        currency="usd",
        status="pending",
    )
    db.add(payment)

    # Transition trip to payment_pending
    await transition_trip(trip, TripStatus.PAYMENT_PENDING, db, commit=False)
    await db.commit()

    return CheckoutResponse(
        checkout_url=checkout_session.url,
        session_id=checkout_session.id,
    )


@router.get("/trips/{trip_id}/payment-status", response_model=PaymentStatusResponse)
async def get_payment_status(
    trip_id: str,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    """Check payment status for a trip."""
    result = await db.execute(select(Trip).where(Trip.id == trip_id))
    trip = result.scalar_one_or_none()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    payment_result = await db.execute(
        select(Payment)
        .where(Payment.trip_id == trip_id)
        .order_by(Payment.created_at.desc())
    )
    payment = payment_result.scalar_one_or_none()

    return PaymentStatusResponse(
        trip_id=trip_id,
        payment_status=trip.payment_status,
        stripe_session_id=payment.stripe_checkout_session_id if payment else None,
    )


@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Handle Stripe webhook events."""
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=503, detail="Payments not configured")

    import stripe
    stripe.api_key = settings.stripe_secret_key

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        if settings.stripe_webhook_secret:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.stripe_webhook_secret,
            )
        else:
            # Dev mode — parse without signature verification
            import json
            event = stripe.Event.construct_from(json.loads(payload), stripe.api_key)
    except (ValueError, stripe.error.SignatureVerificationError) as e:
        logger.warning("Stripe webhook signature verification failed: %s", e)
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        session_id = session["id"]
        trip_id = session.get("metadata", {}).get("trip_id")
        payment_intent_id = session.get("payment_intent")

        if not trip_id:
            logger.warning("Stripe webhook: no trip_id in session metadata")
            return JSONResponse(content={"status": "ignored"})

        # Update payment record
        payment_result = await db.execute(
            select(Payment).where(Payment.stripe_checkout_session_id == session_id)
        )
        payment = payment_result.scalar_one_or_none()
        if payment:
            payment.status = "paid"
            payment.stripe_payment_intent_id = payment_intent_id
            payment.paid_at = datetime.now(timezone.utc)

        # Update trip
        trip_result = await db.execute(select(Trip).where(Trip.id == trip_id))
        trip = trip_result.scalar_one_or_none()
        if trip:
            trip.payment_status = "paid"
            if trip.status == TripStatus.PAYMENT_PENDING:
                await transition_trip(trip, TripStatus.BOOKING, db, commit=False)

        await db.commit()

        # Execute bookings with providers
        if trip:
            from core.booking_executor import execute_paid_bookings
            try:
                await execute_paid_bookings(trip_id, payment_intent_id or "", db)
            except Exception as exc:
                logger.error("Booking execution failed for trip %s: %s", trip_id, exc)

    return JSONResponse(content={"status": "ok"})
