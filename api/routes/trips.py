import logging
import uuid
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import CurrentUser, get_current_user

from agents.activity_agent import ActivityAgent
from agents.flight_agent import FlightAgent
from agents.hotel_agent import HotelAgent
from agents.orchestrator_agent import OrchestratorAgent, _detect_domains
from agents.transport_agent import TransportAgent
from api.schemas import (
    BookingOut, BudgetBreakdown, ChatMessageIn, ChatMessageOut,
    ClarificationResponse, ItineraryDay, ItineraryItem,
    PolicyReportResponse, PolicyViolationRowOut, TripCreate, TripItinerary,
    TripRead, UpdateItineraryItemRequest,
)
from core.approval_gate import ApprovalGate
from core.audit_logger import AuditLogger
from core.event_bus import EventBus
from core.intent import extract_and_infer
from core.policy_engine import PolicyEngine, PolicyNotFoundError
from db.database import get_db
from db.models import Booking, CorporatePolicy, HumanApproval, PolicyViolation, Trip, TripChatMessage

router = APIRouter(prefix="/trips", tags=["trips"])
logger = logging.getLogger(__name__)


async def _resolve_policy(trip: Trip, db: AsyncSession) -> Optional[str]:
    """Resolve and cache the effective policy_id for a trip.

    - If trip.policy_id is already set, validate it (INV-9: inactive → PolicyNotFoundError).
    - If trip.org_id is set, look up the active policy for that org.
    - Returns None if no policy applies.
    """
    if trip.policy_id:
        result = await db.execute(
            select(CorporatePolicy).where(CorporatePolicy.id == trip.policy_id)
        )
        policy = result.scalar_one_or_none()
        if not policy or not policy.is_active:
            raise PolicyNotFoundError(
                f"Explicit policy_id '{trip.policy_id}' is inactive or not found (INV-9)."
            )
        return trip.policy_id

    if trip.org_id:
        result = await db.execute(
            select(CorporatePolicy).where(
                CorporatePolicy.org_id == trip.org_id,
                CorporatePolicy.is_active == True,  # noqa: E712
            )
        )
        policy = result.scalar_one_or_none()
        if policy:
            trip.policy_id = policy.id
            await db.commit()
            return policy.id

    return None


async def _run_agent_task(trip_id: str, goal: str, db: AsyncSession) -> None:
    """Background task: resolve policy, pick agent, run it. Never silently fails (invariant)."""
    audit_logger = AuditLogger(db)
    approval_gate = ApprovalGate(db)

    result = await db.execute(select(Trip).where(Trip.id == trip_id))
    trip = result.scalar_one_or_none()
    if not trip:
        return

    trip.status = "running"
    await db.commit()

    try:
        # ── M3: Policy resolution (INV-9: fail early if explicit policy is inactive) ──
        policy_engine: Optional[PolicyEngine] = None
        try:
            policy_id = await _resolve_policy(trip, db)
            if policy_id:
                policy_engine = PolicyEngine(db)
                await policy_engine.load_policy(policy_id)
        except PolicyNotFoundError as exc:
            logger.error("Policy resolution failed for trip %s: %s", trip_id, exc)
            trip.status = "failed"
            await db.commit()
            bus = EventBus.get_or_create(trip_id)
            await bus.emit({"type": "trip_failed", "message": str(exc)})
            return

        # ── Smart defaults: extract and infer parameters ─────────────────────────
        tracked_params = extract_and_infer(goal, trip.total_budget)
        logger.info(
            "Trip %s params: stated=%s inferred=%s missing=%s",
            trip_id,
            list(tracked_params.stated_params().keys()),
            list(tracked_params.inferred_params().keys()),
            tracked_params.missing_params(),
        )

        # Emit smart defaults event so the frontend can display assumptions
        bus = EventBus.get_or_create(trip_id)
        dest = tracked_params.destination_city
        dest_city = dest.value if dest else None
        budget_tiers = None
        if dest_city and tracked_params.duration_nights:
            from core.intent import generate_budget_tiers
            num_pax = tracked_params.num_travelers.value if tracked_params.num_travelers else 1
            tiers = generate_budget_tiers(
                dest_city,
                tracked_params.duration_nights.value,
                num_pax,
            )
            budget_tiers = [
                {
                    "name": t.name,
                    "label": t.label,
                    "flight_description": t.flight_description,
                    "hotel_description": t.hotel_description,
                    "estimated_flight_cost": t.estimated_flight_cost,
                    "estimated_hotel_per_night": t.estimated_hotel_per_night,
                    "estimated_total": t.estimated_total,
                }
                for t in tiers
            ]
        await bus.emit({
            "type": "smart_defaults",
            "stated": tracked_params.stated_params(),
            "inferred": {
                k: {"value": v["value"], "reason": v["reason"], "confidence": v["confidence"]}
                for k, v in tracked_params.inferred_params().items()
            },
            "budget_tiers": budget_tiers,
        })

        # ── Agent selection and run ─────────────────────────────────────────────────
        # Build context summary from tracked params for agent goal enrichment
        param_context = tracked_params.to_context_dict()
        enriched_goal = goal
        inferred = param_context.get("system_inferred", {})
        if inferred:
            assumptions = "; ".join(
                f"{k.replace('_', ' ')}: {v['value']} ({v['reason']})"
                for k, v in inferred.items()
            )
            enriched_goal = f"{goal}\n\n[System defaults applied: {assumptions}]"

        domains = _detect_domains(goal)
        if len(domains) >= 2:
            agent = OrchestratorAgent(trip_id, db, audit_logger, approval_gate,
                                     tracked_params=tracked_params)
        elif domains[0] == "hotel":
            agent = HotelAgent(trip_id, db, audit_logger, approval_gate, policy_engine=policy_engine)
        elif domains[0] == "transport":
            agent = TransportAgent(trip_id, db, audit_logger, approval_gate, policy_engine=policy_engine)
        elif domains[0] == "activity":
            agent = ActivityAgent(trip_id, db, audit_logger, approval_gate, policy_engine=policy_engine)
        else:
            agent = FlightAgent(trip_id, db, audit_logger, approval_gate, policy_engine=policy_engine)

        narrative = await agent.run(enriched_goal)

        await db.refresh(trip)
        if trip.status == "running":
            trip.status = "complete"
            trip.summary_text = narrative
            await db.commit()

        # Fetch bookings to include in completion event
        booking_result = await db.execute(
            select(Booking).where(Booking.trip_id == trip_id)
        )
        bookings = booking_result.scalars().all()
        bookings_data = [
            {
                "domain": b.domain,
                "provider": b.provider,
                "details": b.details,
                "amount": b.amount,
            }
            for b in bookings
        ]

        bus = EventBus.get_or_create(trip_id)
        await bus.emit({
            "type": "trip_completed",
            "summary": {
                "status": "complete",
                "narrative": narrative,
                "bookings": bookings_data,
                "total_spent": trip.total_spent,
            },
        })

    except Exception as exc:
        logger.error("Agent task failed for trip %s: %s", trip_id, exc)
        await db.refresh(trip)
        trip.status = "failed"
        await db.commit()
        bus = EventBus.get_or_create(trip_id)
        await bus.emit({"type": "trip_failed", "message": "An internal error occurred while processing your trip."})


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("", response_model=TripRead, status_code=202)
async def create_trip(
    body: TripCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    # Use authenticated user_id instead of trusting client-supplied value
    effective_user_id = user.user_id if user.user_id != "anonymous" else body.user_id
    trip = Trip(
        id=str(uuid.uuid4()),
        goal=body.goal,
        status="pending",
        user_id=effective_user_id,
        total_budget=body.total_budget,
        org_id=body.org_id,
        policy_id=body.policy_id,
    )
    db.add(trip)
    await db.commit()
    await db.refresh(trip)

    background_tasks.add_task(_run_agent_task, trip.id, body.goal, db)
    return TripRead(
        id=trip.id,
        goal=trip.goal,
        status=trip.status,
        total_spent=trip.total_spent,
        user_id=trip.user_id,
        total_budget=trip.total_budget,
        org_id=trip.org_id,
        policy_id=trip.policy_id,
        created_at=trip.created_at,
        summary_text=trip.summary_text,
        bookings=[],
    )


@router.get("/{trip_id}", response_model=TripRead)
async def get_trip(
    trip_id: str,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    result = await db.execute(select(Trip).where(Trip.id == trip_id))
    trip = result.scalar_one_or_none()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    booking_result = await db.execute(
        select(Booking).where(Booking.trip_id == trip_id)
    )
    bookings = booking_result.scalars().all()

    return TripRead(
        id=trip.id,
        goal=trip.goal,
        status=trip.status,
        total_spent=trip.total_spent,
        user_id=trip.user_id,
        total_budget=trip.total_budget,
        org_id=trip.org_id,
        policy_id=trip.policy_id,
        created_at=trip.created_at,
        summary_text=trip.summary_text,
        bookings=[BookingOut.model_validate(b) for b in bookings],
    )


@router.get("", response_model=list[TripRead])
async def list_trips(
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    result = await db.execute(select(Trip))
    trips = result.scalars().all()
    return [
        TripRead(
            id=t.id,
            goal=t.goal,
            status=t.status,
            total_spent=t.total_spent,
            user_id=t.user_id,
            total_budget=t.total_budget,
            org_id=t.org_id,
            policy_id=t.policy_id,
            created_at=t.created_at,
            summary_text=t.summary_text,
            bookings=[],
        )
        for t in trips
    ]


@router.post("/{trip_id}/clarify")
async def submit_clarification(
    trip_id: str,
    body: ClarificationResponse,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    """Receive user answers to clarifying questions and forward to the waiting agent."""
    result = await db.execute(select(Trip).where(Trip.id == trip_id))
    trip = result.scalar_one_or_none()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    bus = EventBus.get_or_create(trip_id)
    await bus.send_response({
        "request_id": body.request_id,
        "answers": body.answers,
    })
    return {"status": "ok"}


@router.patch("/{trip_id}")
async def update_trip(
    trip_id: str,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    """Cancel a running trip."""
    result = await db.execute(select(Trip).where(Trip.id == trip_id))
    trip = result.scalar_one_or_none()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    if trip.status in ("complete", "failed", "cancelled"):
        raise HTTPException(status_code=400, detail=f"Trip already {trip.status}")

    trip.status = "cancelled"
    await db.commit()
    bus = EventBus.get_or_create(trip_id)
    await bus.emit({"type": "trip_failed", "message": "Trip cancelled by user"})
    return {"status": "cancelled"}


@router.get("/{trip_id}/policy-report", response_model=PolicyReportResponse)
async def get_policy_report(
    trip_id: str,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    """Return all PolicyViolation rows for a trip — useful for audit and finance review."""
    result = await db.execute(select(Trip).where(Trip.id == trip_id))
    trip = result.scalar_one_or_none()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    viol_result = await db.execute(
        select(PolicyViolation)
        .where(PolicyViolation.trip_id == trip_id)
        .order_by(PolicyViolation.recorded_at)
    )
    violations = viol_result.scalars().all()

    return PolicyReportResponse(
        trip_id=trip_id,
        policy_id=trip.policy_id,
        violations=[PolicyViolationRowOut.model_validate(v) for v in violations],
    )


# ── Itinerary Endpoint ────────────────────────────────────────────────────────

def _booking_to_itinerary_item(
    booking: Booking,
    approval: Optional[HumanApproval] = None,
) -> ItineraryItem:
    """Convert a Booking row + optional approval into an ItineraryItem."""
    details = booking.details or {}
    domain = booking.domain

    # Build human-friendly title/subtitle based on domain
    if domain == "flight":
        origin = details.get("origin", details.get("departure_city", ""))
        dest = details.get("destination", details.get("arrival_city", ""))
        title = f"{origin} → {dest}" if origin and dest else f"Flight booking"
        airline = details.get("airline", "")
        flight_num = details.get("flight_number", "")
        stops = details.get("stops", "")
        subtitle_parts = [p for p in [airline, flight_num, stops] if p]
        subtitle = " · ".join(str(s) for s in subtitle_parts) if subtitle_parts else booking.provider
    elif domain == "hotel":
        hotel_name = details.get("hotel_name", details.get("name", "Hotel"))
        title = str(hotel_name)
        room_type = details.get("room_type", "")
        subtitle = str(room_type) if room_type else booking.provider
    elif domain == "transport":
        transport_type = details.get("type", details.get("transport_type", "Transfer"))
        pickup = details.get("pickup", details.get("origin", ""))
        dropoff = details.get("dropoff", details.get("destination", ""))
        title = f"{transport_type}: {pickup} → {dropoff}" if pickup and dropoff else str(transport_type)
        subtitle = booking.provider
    else:  # activity
        activity_name = details.get("name", details.get("activity_name", "Activity"))
        title = str(activity_name)
        subtitle = details.get("description", booking.provider) or booking.provider

    time_str = str(details.get("time", details.get("departure_time", details.get("check_in", ""))))
    nights = details.get("nights")
    per_night = domain == "hotel" and nights is not None

    # Determine status
    if approval and approval.status == "pending":
        status = "awaiting_approval"
    elif approval and approval.status == "rejected":
        status = "rejected"
    else:
        status = "confirmed"

    return ItineraryItem(
        id=booking.id,
        type=domain,
        status=status,
        title=title,
        subtitle=str(subtitle),
        time=time_str,
        cost=booking.amount,
        details=str(details) if details else None,
        per_night=per_night,
        nights=int(nights) if nights is not None else None,
        provider=booking.provider,
        approval_id=approval.id if approval and approval.status == "pending" else None,
    )


@router.get("/{trip_id}/itinerary", response_model=TripItinerary)
async def get_trip_itinerary(
    trip_id: str,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    """Assemble trip data into a structured itinerary for the artifact view."""
    result = await db.execute(select(Trip).where(Trip.id == trip_id))
    trip = result.scalar_one_or_none()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    # Fetch bookings
    booking_result = await db.execute(
        select(Booking).where(Booking.trip_id == trip_id).order_by(Booking.created_at)
    )
    bookings = booking_result.scalars().all()

    # Fetch approvals keyed by domain+action for matching
    approval_result = await db.execute(
        select(HumanApproval).where(HumanApproval.trip_id == trip_id)
    )
    approvals = approval_result.scalars().all()
    approval_map: dict[str, HumanApproval] = {}
    for a in approvals:
        # Match approvals to bookings by domain
        approval_map[a.domain] = a

    # Build itinerary items
    items: list[ItineraryItem] = []
    budget_by_category: dict[str, float] = {}
    for booking in bookings:
        approval = approval_map.get(booking.domain)
        item = _booking_to_itinerary_item(booking, approval)
        items.append(item)
        budget_by_category[booking.domain] = budget_by_category.get(booking.domain, 0) + booking.amount

    # Group items into days by creation order (since bookings may not have explicit dates)
    # For now, create a single "Day 1" with all items, or group by date if available
    days: list[ItineraryDay] = []
    if items:
        # Try to group by date from booking details
        day_groups: dict[str, list[ItineraryItem]] = {}
        for item in items:
            # Use "Day 1" as default grouping
            day_key = "Day 1"
            if day_key not in day_groups:
                day_groups[day_key] = []
            day_groups[day_key].append(item)

        # Extract destination from goal
        goal_parts = trip.goal.split()
        city = goal_parts[-1] if goal_parts else "Destination"

        for i, (day_label, day_items) in enumerate(day_groups.items()):
            days.append(ItineraryDay(
                date=f"Day {i + 1}",
                label=day_label,
                city=city,
                items=day_items,
            ))

    # Budget breakdown
    total_budget = trip.total_budget or 0
    allocated = trip.total_spent or 0
    budget = BudgetBreakdown(
        total=total_budget,
        allocated=allocated,
        remaining=max(total_budget - allocated, 0),
        by_category=budget_by_category,
    )

    # Build subtitle
    subtitle = trip.status.capitalize()
    if trip.created_at:
        subtitle = f"Created {trip.created_at.strftime('%b %d, %Y')}"

    return TripItinerary(
        trip_id=trip.id,
        title=trip.goal,
        subtitle=subtitle,
        status=trip.status,
        narrative=trip.summary_text,
        days=days,
        budget=budget,
    )


@router.patch("/{trip_id}/itinerary/items/{item_id}")
async def update_itinerary_item(
    trip_id: str,
    item_id: str,
    body: UpdateItineraryItemRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    """Inline approve/reject from the artifact view."""
    # Verify the trip exists
    result = await db.execute(select(Trip).where(Trip.id == trip_id))
    trip = result.scalar_one_or_none()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    # Find the booking
    booking_result = await db.execute(
        select(Booking).where(Booking.id == item_id, Booking.trip_id == trip_id)
    )
    booking = booking_result.scalar_one_or_none()
    if not booking:
        raise HTTPException(status_code=404, detail="Item not found")

    # Find a pending approval for this booking's domain
    approval_result = await db.execute(
        select(HumanApproval).where(
            HumanApproval.trip_id == trip_id,
            HumanApproval.domain == booking.domain,
            HumanApproval.status == "pending",
        )
    )
    approval = approval_result.scalar_one_or_none()

    if body.action in ("approve", "reject"):
        if not approval:
            raise HTTPException(status_code=400, detail="No pending approval for this item")

        from core.approval_gate import ApprovalGate
        gate = ApprovalGate(db)
        await gate.decide(approval.id, body.action == "approve")
        return {"status": "approved" if body.action == "approve" else "rejected", "item_id": item_id}

    elif body.action == "request_alternatives":
        return {"status": "alternatives_requested", "item_id": item_id, "notes": body.notes}

    raise HTTPException(status_code=400, detail=f"Unknown action: {body.action}")


# ── Trip Chat Endpoints ───────────────────────────────────────────────────────

@router.get("/{trip_id}/chat", response_model=list[ChatMessageOut])
async def get_chat_history(
    trip_id: str,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    """Get chat history for a trip."""
    result = await db.execute(select(Trip).where(Trip.id == trip_id))
    trip = result.scalar_one_or_none()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    messages_result = await db.execute(
        select(TripChatMessage)
        .where(TripChatMessage.trip_id == trip_id)
        .order_by(TripChatMessage.created_at)
    )
    messages = messages_result.scalars().all()
    return [ChatMessageOut.model_validate(m) for m in messages]


@router.post("/{trip_id}/chat", response_model=ChatMessageOut)
async def send_chat_message(
    trip_id: str,
    body: ChatMessageIn,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    """Send a message in trip chat and get an AI response."""
    result = await db.execute(select(Trip).where(Trip.id == trip_id))
    trip = result.scalar_one_or_none()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    # Save user message
    user_msg = TripChatMessage(
        id=str(uuid.uuid4()),
        trip_id=trip_id,
        role="user",
        content=body.message,
    )
    db.add(user_msg)
    await db.commit()

    # Fetch bookings for context
    booking_result = await db.execute(
        select(Booking).where(Booking.trip_id == trip_id)
    )
    bookings = booking_result.scalars().all()
    bookings_summary = ", ".join(
        f"{b.domain}: ${b.amount:.0f} via {b.provider}" for b in bookings
    ) or "No bookings yet"

    # Fetch recent chat history for context
    history_result = await db.execute(
        select(TripChatMessage)
        .where(TripChatMessage.trip_id == trip_id)
        .order_by(TripChatMessage.created_at)
    )
    history = history_result.scalars().all()

    # Build AI response using Claude
    try:
        from anthropic import AsyncAnthropic

        client = AsyncAnthropic()
        system_prompt = (
            f"You are Concierge, an AI travel assistant. You are discussing trip '{trip.goal}' "
            f"(status: {trip.status}). Current bookings: {bookings_summary}. "
            f"Total spent: ${trip.total_spent:.2f}. "
            f"{'Budget: $' + str(trip.total_budget) + '. ' if trip.total_budget else ''}"
            f"{'Trip summary: ' + trip.summary_text + '. ' if trip.summary_text else ''}"
            f"Help the user review, modify, or understand their trip. If the user asks to change "
            f"something (swap hotel, find cheaper flights), explain what you'd change and confirm "
            f"before making modifications. Be concise and helpful."
        )

        messages = []
        for msg in history:
            messages.append({"role": msg.role, "content": msg.content})

        response = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=system_prompt,
            messages=messages,
        )
        assistant_content = response.content[0].text
    except Exception as exc:
        logger.warning("Chat AI call failed: %s", exc)
        # Fallback response
        assistant_content = (
            f"I'm Concierge, your travel assistant for this trip. "
            f"Your trip '{trip.goal}' is currently {trip.status}. "
            f"I can help you review your itinerary, suggest changes, or answer questions about your bookings. "
            f"What would you like to know?"
        )

    # Save assistant message
    assistant_msg = TripChatMessage(
        id=str(uuid.uuid4()),
        trip_id=trip_id,
        role="assistant",
        content=assistant_content,
    )
    db.add(assistant_msg)
    await db.commit()
    await db.refresh(assistant_msg)

    return ChatMessageOut.model_validate(assistant_msg)
