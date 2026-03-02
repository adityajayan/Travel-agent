import logging
import uuid
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agents.activity_agent import ActivityAgent
from agents.flight_agent import FlightAgent
from agents.hotel_agent import HotelAgent
from agents.orchestrator_agent import OrchestratorAgent, _detect_domains
from agents.transport_agent import TransportAgent
from api.schemas import BookingOut, ClarificationResponse, PolicyReportResponse, PolicyViolationRowOut, TripCreate, TripRead
from core.approval_gate import ApprovalGate
from core.audit_logger import AuditLogger
from core.event_bus import EventBus
from core.intent import extract_and_infer
from core.policy_engine import PolicyEngine, PolicyNotFoundError
from db.database import get_db
from db.models import Booking, CorporatePolicy, PolicyViolation, Trip

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
        await bus.emit({"type": "trip_failed", "message": str(exc)})


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("", response_model=TripRead, status_code=202)
async def create_trip(
    body: TripCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    trip = Trip(
        id=str(uuid.uuid4()),
        goal=body.goal,
        status="pending",
        user_id=body.user_id,
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
async def get_trip(trip_id: str, db: AsyncSession = Depends(get_db)):
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
async def list_trips(db: AsyncSession = Depends(get_db)):
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
async def update_trip(trip_id: str, db: AsyncSession = Depends(get_db)):
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
async def get_policy_report(trip_id: str, db: AsyncSession = Depends(get_db)):
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
