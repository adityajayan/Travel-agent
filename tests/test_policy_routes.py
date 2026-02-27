"""API-level tests for policy CRUD routes and policy-report endpoint."""
import uuid
from unittest.mock import AsyncMock, patch

import pytest

from db.models import CorporatePolicy, PolicyRule, PolicyViolation, Trip


# ── POST /policies ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_policy(api_client):
    resp = await api_client.post("/policies", json={
        "org_id": "acme",
        "name": "Standard 2025",
        "is_active": True,
        "rules": [
            {
                "booking_type": "flight",
                "rule_key": "max_flight_cost",
                "operator": "lte",
                "value": {"amount": 800.0},
                "severity": "hard",
                "message": "Flight cost exceeds policy limit",
            }
        ],
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["org_id"] == "acme"
    assert data["is_active"] is True
    assert len(data["rules"]) == 1
    assert data["rules"][0]["rule_key"] == "max_flight_cost"


@pytest.mark.asyncio
async def test_create_policy_409_on_duplicate_active(api_client):
    """Creating a second active policy for the same org should return 409."""
    payload = {
        "org_id": "acme-corp",
        "name": "Policy A",
        "is_active": True,
        "rules": [],
    }
    r1 = await api_client.post("/policies", json=payload)
    assert r1.status_code == 201

    payload["name"] = "Policy B"
    r2 = await api_client.post("/policies", json=payload)
    assert r2.status_code == 409


@pytest.mark.asyncio
async def test_create_inactive_policy_no_conflict(api_client):
    """Creating an inactive policy never conflicts."""
    payload = {"org_id": "beta", "name": "Active", "is_active": True, "rules": []}
    await api_client.post("/policies", json=payload)

    payload2 = {"org_id": "beta", "name": "Inactive", "is_active": False, "rules": []}
    r2 = await api_client.post("/policies", json=payload2)
    assert r2.status_code == 201


# ── GET /policies ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_policies_by_org(api_client):
    await api_client.post("/policies", json={"org_id": "gamma", "name": "P1", "is_active": True, "rules": []})
    await api_client.post("/policies", json={"org_id": "gamma", "name": "P2", "is_active": False, "rules": []})
    await api_client.post("/policies", json={"org_id": "delta", "name": "Other", "is_active": True, "rules": []})

    resp = await api_client.get("/policies?org_id=gamma")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    orgs = {p["org_id"] for p in data}
    assert orgs == {"gamma"}


@pytest.mark.asyncio
async def test_get_policy_not_found(api_client):
    resp = await api_client.get(f"/policies/{uuid.uuid4()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_policy_found(api_client):
    create_resp = await api_client.post("/policies", json={
        "org_id": "epsilon", "name": "Test Policy", "is_active": True, "rules": []
    })
    policy_id = create_resp.json()["id"]

    get_resp = await api_client.get(f"/policies/{policy_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == policy_id


# ── PATCH /policies/{id} ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_patch_policy_deactivate(api_client):
    r = await api_client.post("/policies", json={
        "org_id": "zeta", "name": "Active Policy", "is_active": True, "rules": []
    })
    policy_id = r.json()["id"]

    patch_resp = await api_client.patch(f"/policies/{policy_id}", json={"is_active": False})
    assert patch_resp.status_code == 200
    assert patch_resp.json()["is_active"] is False


@pytest.mark.asyncio
async def test_patch_policy_activate_409(api_client):
    """Activating a policy when another is already active for same org → 409."""
    r1 = await api_client.post("/policies", json={"org_id": "eta", "name": "P1", "is_active": True, "rules": []})
    r2 = await api_client.post("/policies", json={"org_id": "eta", "name": "P2", "is_active": False, "rules": []})
    p2_id = r2.json()["id"]

    patch_resp = await api_client.patch(f"/policies/{p2_id}", json={"is_active": True})
    assert patch_resp.status_code == 409


# ── DELETE /policies/{id} ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_delete_policy_soft_deletes(api_client):
    r = await api_client.post("/policies", json={
        "org_id": "theta", "name": "Delete Me", "is_active": True, "rules": []
    })
    policy_id = r.json()["id"]

    del_resp = await api_client.delete(f"/policies/{policy_id}")
    assert del_resp.status_code == 204

    # Verify soft-deleted (is_active = False)
    get_resp = await api_client.get(f"/policies/{policy_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["is_active"] is False


# ── PATCH /policies/{id}/rules/{rule_id} ─────────────────────────────────────

@pytest.mark.asyncio
async def test_patch_rule_toggle_disabled(api_client):
    create = await api_client.post("/policies", json={
        "org_id": "iota", "name": "Rule Test", "is_active": True,
        "rules": [{
            "booking_type": "flight", "rule_key": "max_flight_cost",
            "operator": "lte", "value": {"amount": 800.0},
            "severity": "hard", "message": "Too expensive",
        }],
    })
    policy = create.json()
    rule_id = policy["rules"][0]["id"]
    policy_id = policy["id"]

    patch_resp = await api_client.patch(
        f"/policies/{policy_id}/rules/{rule_id}", json={"is_enabled": False}
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["is_enabled"] is False


# ── GET /trips/{id}/policy-report ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_policy_report_empty(api_client):
    with patch("api.routes.trips._run_agent_task", new=AsyncMock()):
        r = await api_client.post("/trips", json={"goal": "Book flight"})
    trip_id = r.json()["id"]

    report = await api_client.get(f"/trips/{trip_id}/policy-report")
    assert report.status_code == 200
    data = report.json()
    assert data["trip_id"] == trip_id
    assert data["violations"] == []


@pytest.mark.asyncio
async def test_policy_report_with_violations(api_client, engine):
    """Violations written to DB appear in the report."""
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    trip_id = str(uuid.uuid4())
    policy_id = str(uuid.uuid4())
    rule_id = str(uuid.uuid4())

    async with factory() as session:
        session.add(Trip(id=trip_id, goal="Test", status="failed"))
        session.add(CorporatePolicy(id=policy_id, org_id="test", name="P", is_active=True))
        session.add(PolicyRule(
            id=rule_id, policy_id=policy_id, booking_type="flight",
            rule_key="max_flight_cost", operator="lte",
            value={"amount": 500.0}, severity="hard",
            message="Too expensive", is_enabled=True,
        ))
        session.add(PolicyViolation(
            id=str(uuid.uuid4()), policy_id=policy_id, rule_id=rule_id,
            trip_id=trip_id, approval_id=None, booking_type="flight",
            severity="hard", actual_value={"estimated_cost": 900.0},
            rule_value={"amount": 500.0}, outcome="blocked",
            message="Too expensive",
        ))
        await session.commit()

    report = await api_client.get(f"/trips/{trip_id}/policy-report")
    assert report.status_code == 200
    data = report.json()
    assert len(data["violations"]) == 1
    assert data["violations"][0]["outcome"] == "blocked"
    assert data["violations"][0]["severity"] == "hard"


@pytest.mark.asyncio
async def test_policy_report_trip_not_found(api_client):
    resp = await api_client.get(f"/trips/{uuid.uuid4()}/policy-report")
    assert resp.status_code == 404
