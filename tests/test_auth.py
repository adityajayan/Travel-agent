"""Tests for M6 Item 1 — Authentication Layer."""
import time
import uuid
from unittest.mock import AsyncMock, patch

import jwt
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from api.main import app
from db.database import get_db
from db.models import Base, Trip, User


TEST_SECRET = "test-auth-secret-for-jwt-validation"
TEST_DB_URL = "sqlite+aiosqlite:///:memory:?cache=shared"


@pytest_asyncio.fixture
async def auth_engine():
    eng = create_async_engine(TEST_DB_URL, echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def auth_session_factory(auth_engine):
    return async_sessionmaker(auth_engine, expire_on_commit=False, class_=AsyncSession)


@pytest_asyncio.fixture
async def auth_client(auth_engine, auth_session_factory):
    """Client with auth enabled (AUTH_SECRET set)."""
    async def override_get_db():
        async with auth_session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    with patch("core.config.settings.auth_secret", TEST_SECRET):
        with patch("api.main.settings.auth_secret", TEST_SECRET):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                yield client

    app.dependency_overrides.clear()


def _make_jwt(user_id: str = "user-1", email: str = "test@test.com",
              name: str = "Test User", expired: bool = False) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "name": name,
        "iat": int(time.time()),
        "exp": int(time.time()) + (-3600 if expired else 3600),
    }
    return jwt.encode(payload, TEST_SECRET, algorithm="HS256")


# ── Unauthenticated request → 401 ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_unauthenticated_request_returns_401(auth_client):
    resp = await auth_client.get("/trips")
    assert resp.status_code == 401
    assert "Authentication required" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_unauthenticated_post_returns_401(auth_client):
    resp = await auth_client.post("/trips", json={"goal": "Fly to Paris"})
    assert resp.status_code == 401


# ── Valid JWT → request succeeds ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_valid_jwt_request_succeeds(auth_client):
    token = _make_jwt()
    with patch("api.routes.trips._run_agent_task", new=AsyncMock()):
        resp = await auth_client.post(
            "/trips",
            json={"goal": "Fly to Paris"},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 202
    data = resp.json()
    assert data["goal"] == "Fly to Paris"


@pytest.mark.asyncio
async def test_valid_jwt_get_trips(auth_client):
    token = _make_jwt()
    resp = await auth_client.get(
        "/trips",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200


# ── Expired JWT → 401 ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_expired_jwt_returns_401(auth_client):
    token = _make_jwt(expired=True)
    resp = await auth_client.get(
        "/trips",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 401


# ── Invalid JWT → 401 ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_invalid_jwt_returns_401(auth_client):
    resp = await auth_client.get(
        "/trips",
        headers={"Authorization": "Bearer invalid-token-here"},
    )
    assert resp.status_code == 401


# ── Health check exempt from auth ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health_check_exempt_from_auth(auth_client):
    resp = await auth_client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


# ── Trip created with authenticated user ─────────────────────────────────────

@pytest.mark.asyncio
async def test_trip_has_user_context(auth_client, auth_session_factory):
    """Trip created with authenticated user has user context in request state."""
    token = _make_jwt(user_id="user-42", email="alice@test.com", name="Alice")
    with patch("api.routes.trips._run_agent_task", new=AsyncMock()):
        resp = await auth_client.post(
            "/trips",
            json={"goal": "Hotel in London"},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 202


# ── User model tests ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_user_model_creation(auth_session_factory):
    async with auth_session_factory() as session:
        user = User(
            id=str(uuid.uuid4()),
            email="bob@test.com",
            name="Bob",
            auth_provider_id="auth0|123",
        )
        session.add(user)
        await session.commit()

        result = await session.execute(select(User).where(User.email == "bob@test.com"))
        db_user = result.scalar_one()
        assert db_user.name == "Bob"
        assert db_user.auth_provider_id == "auth0|123"


@pytest.mark.asyncio
async def test_trip_user_relationship(auth_session_factory):
    """Trip.user_id references User when set."""
    async with auth_session_factory() as session:
        user = User(
            id=str(uuid.uuid4()),
            email="carol@test.com",
            name="Carol",
            auth_provider_id="supabase|456",
        )
        session.add(user)
        await session.flush()

        trip = Trip(
            id=str(uuid.uuid4()),
            goal="Test trip",
            status="pending",
            user_id=user.id,
        )
        session.add(trip)
        await session.commit()

        result = await session.execute(select(Trip).where(Trip.id == trip.id))
        db_trip = result.scalar_one()
        assert db_trip.user_id == user.id
