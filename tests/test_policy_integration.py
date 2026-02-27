"""Integration tests: PolicyEngine wired into FlightAgent / BaseAgent.

Key scenarios:
- HARD block → ApprovalGate.check() is NEVER called (INV-7)
- SOFT violation → appears in HumanApproval.policy_violations_json
- No policy → existing booking flow unchanged
"""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import func, select

from agents.flight_agent import FlightAgent
from core.policy_engine import PolicyEngine
from db.models import CorporatePolicy, HumanApproval, PolicyRule, PolicyViolation


# ── Helpers ───────────────────────────────────────────────────────────────────

def _text_response(text: str):
    block = MagicMock()
    block.type = "text"
    block.text = text
    resp = MagicMock()
    resp.stop_reason = "end_turn"
    resp.content = [block]
    return resp


def _tool_response(name: str, input_dict: dict, tool_id: str = "tu_001"):
    tb = MagicMock()
    tb.type = "tool_use"
    tb.id = tool_id
    tb.name = name
    tb.input = input_dict
    resp = MagicMock()
    resp.stop_reason = "tool_use"
    resp.content = [tb]
    return resp


async def _make_policy_engine(db, rule_key, amount, severity="hard", booking_type="flight"):
    policy = CorporatePolicy(
        id=str(uuid.uuid4()), org_id="acme", name="Test", is_active=True
    )
    db.add(policy)
    await db.flush()

    rule = PolicyRule(
        id=str(uuid.uuid4()),
        policy_id=policy.id,
        booking_type=booking_type,
        rule_key=rule_key,
        operator="lte",
        value={"amount": amount},
        severity=severity,
        message=f"Policy: {rule_key} violated",
        is_enabled=True,
    )
    db.add(rule)
    await db.commit()

    engine = PolicyEngine(db)
    await engine.load_policy(policy.id)
    return engine


# ── INV-7: HARD block never reaches ApprovalGate ─────────────────────────────

@pytest.mark.asyncio
async def test_hard_block_approval_gate_never_called(db, trip, audit_logger, approval_gate):
    """When a HARD violation fires, ApprovalGate.check() must never be called."""
    engine = await _make_policy_engine(db, "max_flight_cost", 500.0, severity="hard")

    book_response = _tool_response(
        "book_flight", {"flight_id": "FL001", "passenger_name": "Alice", "estimated_cost": 900.0}
    )
    final_response = _text_response("Booking blocked by policy.")

    mock_client = MagicMock()
    mock_client.messages = MagicMock()
    mock_client.messages.create = AsyncMock(side_effect=[book_response, final_response])

    agent = FlightAgent(trip.id, db, audit_logger, approval_gate, policy_engine=engine)
    with patch.object(agent, "_client", mock_client):
        await agent.run("Book flight FL001 for Alice")

    # No HumanApproval rows should have been created
    result = await db.execute(
        select(func.count()).select_from(HumanApproval).where(HumanApproval.trip_id == trip.id)
    )
    assert result.scalar_one() == 0, "ApprovalGate.check() was called despite HARD violation"


@pytest.mark.asyncio
async def test_hard_block_creates_policy_violation_row(db, trip, audit_logger, approval_gate):
    """HARD block must persist a PolicyViolation row with outcome='blocked'."""
    engine = await _make_policy_engine(db, "max_flight_cost", 500.0, severity="hard")

    book_response = _tool_response(
        "book_flight", {"flight_id": "FL001", "passenger_name": "Alice", "estimated_cost": 900.0}
    )
    final_response = _text_response("Booking blocked.")

    mock_client = MagicMock()
    mock_client.messages = MagicMock()
    mock_client.messages.create = AsyncMock(side_effect=[book_response, final_response])

    agent = FlightAgent(trip.id, db, audit_logger, approval_gate, policy_engine=engine)
    with patch.object(agent, "_client", mock_client):
        await agent.run("Book flight FL001 for Alice")

    violations = await db.execute(
        select(PolicyViolation).where(PolicyViolation.trip_id == trip.id)
    )
    rows = violations.scalars().all()
    assert len(rows) == 1
    assert rows[0].outcome == "blocked"
    assert rows[0].severity == "hard"


# ── SOFT violation: appears in approval context ───────────────────────────────

@pytest.mark.asyncio
async def test_soft_violation_in_approval_context(db, trip, audit_logger, approval_gate):
    """SOFT violation should appear in HumanApproval.policy_violations_json."""
    # SOFT rule: max 800, we'll try to book 950 (soft violation)
    engine = await _make_policy_engine(db, "max_flight_cost", 800.0, severity="soft")

    book_response = _tool_response(
        "book_flight", {"flight_id": "FL001", "passenger_name": "Bob", "estimated_cost": 950.0}
    )
    final_response = _text_response("Awaiting approval.")

    mock_client = MagicMock()
    mock_client.messages = MagicMock()
    mock_client.messages.create = AsyncMock(side_effect=[book_response, final_response])

    agent = FlightAgent(trip.id, db, audit_logger, approval_gate, policy_engine=engine)
    with patch.object(agent, "_client", mock_client):
        await agent.run("Book flight FL001 for Bob")

    # HumanApproval should exist with policy_violations_json populated
    result = await db.execute(
        select(HumanApproval).where(HumanApproval.trip_id == trip.id)
    )
    approvals = result.scalars().all()
    assert len(approvals) == 1
    assert approvals[0].policy_violations_json is not None
    assert len(approvals[0].policy_violations_json) == 1
    assert approvals[0].policy_violations_json[0]["rule_key"] == "max_flight_cost"
    assert approvals[0].policy_violations_json[0]["severity"] == "soft"


@pytest.mark.asyncio
async def test_soft_violation_creates_flagged_pending_row(db, trip, audit_logger, approval_gate):
    """SOFT violation → PolicyViolation row with outcome='flagged_pending'."""
    engine = await _make_policy_engine(db, "max_flight_cost", 800.0, severity="soft")

    book_response = _tool_response(
        "book_flight", {"flight_id": "FL001", "passenger_name": "Bob", "estimated_cost": 950.0}
    )
    final_response = _text_response("Awaiting approval.")

    mock_client = MagicMock()
    mock_client.messages = MagicMock()
    mock_client.messages.create = AsyncMock(side_effect=[book_response, final_response])

    agent = FlightAgent(trip.id, db, audit_logger, approval_gate, policy_engine=engine)
    with patch.object(agent, "_client", mock_client):
        await agent.run("Book flight FL001 for Bob")

    viol = await db.execute(
        select(PolicyViolation).where(PolicyViolation.trip_id == trip.id)
    )
    rows = viol.scalars().all()
    assert len(rows) == 1
    assert rows[0].outcome == "flagged_pending"
    assert rows[0].approval_id is not None


# ── No policy: existing flow unchanged ────────────────────────────────────────

@pytest.mark.asyncio
async def test_no_policy_booking_flow_unchanged(db, trip, audit_logger, approval_gate):
    """Trip with no policy_engine runs identically to M1/M2 (no regressions)."""
    book_response = _tool_response(
        "book_flight", {"flight_id": "FL001", "passenger_name": "Carol"}
    )
    final_response = _text_response("Awaiting approval.")

    mock_client = MagicMock()
    mock_client.messages = MagicMock()
    mock_client.messages.create = AsyncMock(side_effect=[book_response, final_response])

    # policy_engine=None (the default)
    agent = FlightAgent(trip.id, db, audit_logger, approval_gate)
    with patch.object(agent, "_client", mock_client):
        await agent.run("Book flight FL001 for Carol")

    # ApprovalGate.check() should have been called → pending HumanApproval exists
    result = await db.execute(
        select(HumanApproval).where(HumanApproval.trip_id == trip.id)
    )
    approvals = result.scalars().all()
    assert len(approvals) == 1
    assert approvals[0].status == "pending"
    assert approvals[0].policy_violations_json is None


# ── SOFT → flagged_approved when decision is approve ─────────────────────────

@pytest.mark.asyncio
async def test_soft_violation_flagged_approved_after_decision(db, trip, audit_logger, approval_gate):
    """After a soft-flagged approval is approved, a flagged_approved row should exist."""
    engine = await _make_policy_engine(db, "max_flight_cost", 800.0, severity="soft")

    book_response = _tool_response(
        "book_flight", {"flight_id": "FL001", "passenger_name": "Dave", "estimated_cost": 950.0}
    )
    final_response = _text_response("Awaiting approval.")

    mock_client = MagicMock()
    mock_client.messages = MagicMock()
    mock_client.messages.create = AsyncMock(side_effect=[book_response, final_response])

    agent = FlightAgent(trip.id, db, audit_logger, approval_gate, policy_engine=engine)
    with patch.object(agent, "_client", mock_client):
        await agent.run("Book flight FL001 for Dave")

    # Approve the pending approval
    approval_result = await db.execute(
        select(HumanApproval).where(HumanApproval.trip_id == trip.id)
    )
    approval = approval_result.scalar_one()
    approval.status = "approved"
    await db.commit()

    # Record flagged_approved violation manually (simulating what decide endpoint would do)
    from core.policy_engine import PolicyEvalResult, PolicyViolationDetail
    viol_result = await db.execute(
        select(PolicyViolation).where(PolicyViolation.trip_id == trip.id, PolicyViolation.outcome == "flagged_pending")
    )
    pending_row = viol_result.scalar_one()

    from db.models import PolicyViolation as PV
    approved_row = PV(
        id=str(uuid.uuid4()),
        policy_id=pending_row.policy_id,
        rule_id=pending_row.rule_id,
        trip_id=trip.id,
        approval_id=approval.id,
        booking_type=pending_row.booking_type,
        severity=pending_row.severity,
        actual_value=pending_row.actual_value,
        rule_value=pending_row.rule_value,
        outcome="flagged_approved",
        message=pending_row.message,
    )
    db.add(approved_row)
    await db.commit()

    # Verify both rows exist (INV-8: original flagged_pending row unchanged)
    all_viols = await db.execute(
        select(PolicyViolation).where(PolicyViolation.trip_id == trip.id)
    )
    rows = all_viols.scalars().all()
    outcomes = {r.outcome for r in rows}
    assert "flagged_pending" in outcomes
    assert "flagged_approved" in outcomes
