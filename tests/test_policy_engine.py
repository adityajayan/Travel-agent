"""Unit tests for PolicyEngine.evaluate() — one test per rule_key, plus edge cases."""
import uuid
from datetime import date, timedelta

import pytest

from core.policy_engine import PolicyEngine, PolicyEvalResult, PolicyNotFoundError
from db.models import CorporatePolicy, PolicyRule


# ── Helpers ───────────────────────────────────────────────────────────────────

def _policy(db, org_id="test-org"):
    p = CorporatePolicy(
        id=str(uuid.uuid4()), org_id=org_id, name="Test Policy", is_active=True
    )
    db.add(p)
    return p


def _rule(db, policy_id, rule_key, operator, value, severity="hard",
          booking_type="flight", message="Policy violation"):
    r = PolicyRule(
        id=str(uuid.uuid4()),
        policy_id=policy_id,
        booking_type=booking_type,
        rule_key=rule_key,
        operator=operator,
        value=value,
        severity=severity,
        message=message,
        is_enabled=True,
    )
    db.add(r)
    return r


# ── load_policy ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_load_policy_success(db, trip):
    p = _policy(db)
    await db.commit()

    engine = PolicyEngine(db)
    loaded = await engine.load_policy(p.id)
    assert loaded.id == p.id
    assert engine._policy is not None


@pytest.mark.asyncio
async def test_load_policy_inactive_raises(db, trip):
    p = CorporatePolicy(
        id=str(uuid.uuid4()), org_id="acme", name="Old Policy", is_active=False
    )
    db.add(p)
    await db.commit()

    engine = PolicyEngine(db)
    with pytest.raises(PolicyNotFoundError):
        await engine.load_policy(p.id)


@pytest.mark.asyncio
async def test_load_policy_missing_raises(db):
    engine = PolicyEngine(db)
    with pytest.raises(PolicyNotFoundError):
        await engine.load_policy("nonexistent-id")


# ── max_flight_cost ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_max_flight_cost_compliant(db, trip):
    p = _policy(db)
    _rule(db, p.id, "max_flight_cost", "lte", {"amount": 800.0}, severity="hard")
    await db.commit()

    engine = PolicyEngine(db)
    await engine.load_policy(p.id)
    result = await engine.evaluate("flight", {"estimated_cost": 700.0})
    assert result.compliant
    assert not result.is_hard_blocked


@pytest.mark.asyncio
async def test_max_flight_cost_hard_violation(db, trip):
    p = _policy(db)
    _rule(db, p.id, "max_flight_cost", "lte", {"amount": 800.0}, severity="hard")
    await db.commit()

    engine = PolicyEngine(db)
    await engine.load_policy(p.id)
    result = await engine.evaluate("flight", {"estimated_cost": 1200.0})
    assert result.is_hard_blocked
    assert result.hard_violations[0].rule_key == "max_flight_cost"


@pytest.mark.asyncio
async def test_max_flight_cost_soft_violation(db, trip):
    p = _policy(db)
    _rule(db, p.id, "max_flight_cost", "lte", {"amount": 800.0}, severity="soft")
    await db.commit()

    engine = PolicyEngine(db)
    await engine.load_policy(p.id)
    result = await engine.evaluate("flight", {"estimated_cost": 900.0})
    assert not result.is_hard_blocked
    assert len(result.soft_violations) == 1


@pytest.mark.asyncio
async def test_max_flight_cost_missing_field_skips(db, trip):
    """Missing estimated_cost → rule skipped, no false positive."""
    p = _policy(db)
    _rule(db, p.id, "max_flight_cost", "lte", {"amount": 800.0}, severity="hard")
    await db.commit()

    engine = PolicyEngine(db)
    await engine.load_policy(p.id)
    result = await engine.evaluate("flight", {})  # no estimated_cost
    assert result.compliant


# ── allowed_cabin_classes ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_allowed_cabin_classes_compliant(db, trip):
    p = _policy(db)
    _rule(db, p.id, "allowed_cabin_classes", "in",
          {"classes": ["economy", "business"]}, severity="hard")
    await db.commit()

    engine = PolicyEngine(db)
    await engine.load_policy(p.id)
    result = await engine.evaluate("flight", {"cabin_class": "economy"})
    assert result.compliant


@pytest.mark.asyncio
async def test_allowed_cabin_classes_violation(db, trip):
    p = _policy(db)
    _rule(db, p.id, "allowed_cabin_classes", "in",
          {"classes": ["economy"]}, severity="hard")
    await db.commit()

    engine = PolicyEngine(db)
    await engine.load_policy(p.id)
    result = await engine.evaluate("flight", {"cabin_class": "first"})
    assert result.is_hard_blocked


@pytest.mark.asyncio
async def test_allowed_cabin_classes_defaults_to_economy(db, trip):
    """Missing cabin_class should default to 'economy' and be allowed."""
    p = _policy(db)
    _rule(db, p.id, "allowed_cabin_classes", "in",
          {"classes": ["economy", "business"]}, severity="hard")
    await db.commit()

    engine = PolicyEngine(db)
    await engine.load_policy(p.id)
    result = await engine.evaluate("flight", {})  # cabin_class absent
    assert result.compliant


# ── require_advance_booking_days ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_require_advance_booking_days_compliant(db, trip):
    p = _policy(db)
    _rule(db, p.id, "require_advance_booking_days", "gte", {"days": 14}, severity="soft")
    await db.commit()

    engine = PolicyEngine(db)
    await engine.load_policy(p.id)
    future_date = (date.today() + timedelta(days=20)).isoformat()
    result = await engine.evaluate("flight", {"departure_date": future_date})
    assert result.compliant


@pytest.mark.asyncio
async def test_require_advance_booking_days_violation(db, trip):
    p = _policy(db)
    _rule(db, p.id, "require_advance_booking_days", "gte", {"days": 14}, severity="soft")
    await db.commit()

    engine = PolicyEngine(db)
    await engine.load_policy(p.id)
    soon = (date.today() + timedelta(days=5)).isoformat()
    result = await engine.evaluate("flight", {"departure_date": soon})
    assert len(result.soft_violations) == 1


# ── max_hotel_cost_per_night ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_max_hotel_cost_per_night_violation(db, trip):
    p = _policy(db)
    _rule(db, p.id, "max_hotel_cost_per_night", "lte", {"amount": 200.0},
          severity="hard", booking_type="hotel")
    await db.commit()

    engine = PolicyEngine(db)
    await engine.load_policy(p.id)
    result = await engine.evaluate("hotel", {"cost_per_night": 350.0})
    assert result.is_hard_blocked


@pytest.mark.asyncio
async def test_max_hotel_cost_per_night_compliant(db, trip):
    p = _policy(db)
    _rule(db, p.id, "max_hotel_cost_per_night", "lte", {"amount": 200.0},
          severity="hard", booking_type="hotel")
    await db.commit()

    engine = PolicyEngine(db)
    await engine.load_policy(p.id)
    result = await engine.evaluate("hotel", {"cost_per_night": 150.0})
    assert result.compliant


# ── max_hotel_stay_total ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_max_hotel_stay_total_violation(db, trip):
    p = _policy(db)
    _rule(db, p.id, "max_hotel_stay_total", "lte", {"amount": 1000.0},
          severity="soft", booking_type="hotel")
    await db.commit()

    engine = PolicyEngine(db)
    await engine.load_policy(p.id)
    # 7 nights × 200 = 1400 > 1000
    result = await engine.evaluate("hotel", {"cost_per_night": 200.0, "nights": 7})
    assert len(result.soft_violations) == 1


# ── preferred_vendors_only ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_preferred_vendors_only_violation(db, trip):
    p = _policy(db)
    _rule(db, p.id, "preferred_vendors_only", "in",
          {"vendors": ["Delta", "United"]}, severity="hard", booking_type="any")
    await db.commit()

    engine = PolicyEngine(db)
    await engine.load_policy(p.id)
    result = await engine.evaluate("flight", {"provider": "Ryanair"})
    assert result.is_hard_blocked


@pytest.mark.asyncio
async def test_preferred_vendors_only_compliant(db, trip):
    p = _policy(db)
    _rule(db, p.id, "preferred_vendors_only", "in",
          {"vendors": ["Delta", "United"]}, severity="hard", booking_type="any")
    await db.commit()

    engine = PolicyEngine(db)
    await engine.load_policy(p.id)
    result = await engine.evaluate("flight", {"provider": "Delta"})
    assert result.compliant


# ── max_total_trip_spend ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_max_total_trip_spend_accumulation(db, trip):
    """Two bookings individually OK but together exceed max → second is blocked."""
    p = _policy(db)
    _rule(db, p.id, "max_total_trip_spend", "lte",
          {"amount": 3000.0}, severity="hard", booking_type="any")
    await db.commit()

    engine = PolicyEngine(db)
    await engine.load_policy(p.id)

    # First booking: 1500, total = 1500 → OK
    r1 = await engine.evaluate("flight", {"estimated_cost": 1500.0}, trip_total_spent=0.0)
    assert r1.compliant

    # Second booking: 1600, total = 3100 → HARD block
    r2 = await engine.evaluate("hotel", {"estimated_cost": 1600.0}, trip_total_spent=1500.0)
    assert r2.is_hard_blocked
    assert r2.hard_violations[0].rule_key == "max_total_trip_spend"


# ── Multi-rule policy ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_multi_rule_all_violations_returned(db, trip):
    """All violations are collected — both HARD and SOFT returned in result."""
    p = _policy(db)
    _rule(db, p.id, "max_flight_cost", "lte", {"amount": 500.0}, severity="hard")
    _rule(db, p.id, "allowed_cabin_classes", "in", {"classes": ["economy"]}, severity="soft")
    await db.commit()

    engine = PolicyEngine(db)
    await engine.load_policy(p.id)
    result = await engine.evaluate("flight", {"estimated_cost": 700.0, "cabin_class": "business"})
    assert result.is_hard_blocked
    assert len(result.hard_violations) == 1
    assert len(result.soft_violations) == 1


# ── record_violations ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_record_violations_creates_rows(db, trip):
    from db.models import PolicyViolation
    from sqlalchemy import select as sa_select, func

    p = _policy(db)
    _rule(db, p.id, "max_flight_cost", "lte", {"amount": 500.0}, severity="hard")
    await db.commit()

    engine = PolicyEngine(db)
    await engine.load_policy(p.id)
    result = await engine.evaluate("flight", {"estimated_cost": 900.0})
    assert result.is_hard_blocked

    ids = await engine.record_violations(result, trip.id, None, "blocked", "flight")
    assert len(ids) == 1

    count = await db.execute(
        sa_select(func.count()).select_from(PolicyViolation).where(
            PolicyViolation.trip_id == trip.id
        )
    )
    assert count.scalar_one() == 1


@pytest.mark.asyncio
async def test_record_violations_append_only(db, trip):
    """Calling record_violations twice creates two separate rows (INV-8)."""
    from db.models import PolicyViolation
    from sqlalchemy import select as sa_select, func

    p = _policy(db)
    _rule(db, p.id, "max_flight_cost", "lte", {"amount": 500.0}, severity="hard")
    await db.commit()

    engine = PolicyEngine(db)
    await engine.load_policy(p.id)
    result = await engine.evaluate("flight", {"estimated_cost": 900.0})

    await engine.record_violations(result, trip.id, None, "blocked", "flight")
    await engine.record_violations(result, trip.id, None, "blocked", "flight")

    count = await db.execute(
        sa_select(func.count()).select_from(PolicyViolation).where(
            PolicyViolation.trip_id == trip.id
        )
    )
    assert count.scalar_one() == 2  # two separate rows


# ── No policy ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_evaluate_without_loaded_policy_returns_compliant(db):
    """Engine with no loaded policy always returns compliant."""
    engine = PolicyEngine(db)
    result = await engine.evaluate("flight", {"estimated_cost": 99999.0})
    assert result.compliant
    assert not result.is_hard_blocked
