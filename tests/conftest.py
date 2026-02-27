"""Shared pytest fixtures for the travel-agent test suite."""
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from api.main import app
from core.approval_gate import ApprovalGate
from core.audit_logger import AuditLogger
from db.database import get_db
from db.models import Base, Trip

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def engine():
    eng = create_async_engine(TEST_DB_URL, echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def db(engine) -> AsyncSession:
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as session:
        yield session


@pytest_asyncio.fixture
async def audit_logger(db):
    return AuditLogger(db)


@pytest_asyncio.fixture
async def approval_gate(db):
    return ApprovalGate(db)


@pytest_asyncio.fixture
async def trip(db) -> Trip:
    """Insert a Trip row and return it."""
    t = Trip(id=str(uuid.uuid4()), goal="Test trip", status="pending")
    db.add(t)
    await db.commit()
    await db.refresh(t)
    return t


# ── API test client ────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def api_client(engine):
    """AsyncClient wired to FastAPI with an in-memory DB override."""
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async def override_get_db():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client
    app.dependency_overrides.clear()
