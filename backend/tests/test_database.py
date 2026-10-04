"""
Tests for CareerLens PostgreSQL database foundation and pgvector extension.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Column, Integer, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.base import Base
from app.db.session import async_session_factory, check_db_health, engine, get_db


@pytest.mark.asyncio
async def test_database_connection():
    """Verify that an async connection can be established to PostgreSQL."""
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT 1;"))
        assert result.scalar() == 1


@pytest.mark.asyncio
async def test_pgvector_extension_installed():
    """Verify that the pgvector extension is installed and available in the database."""
    async with async_session_factory() as session:
        result = await session.execute(
            text("SELECT extversion FROM pg_extension WHERE extname = 'vector';")
        )
        version = result.scalar()
        assert version is not None, "pgvector extension is not installed in the database"
        assert len(version) > 0


@pytest.mark.asyncio
async def test_pgvector_similarity_operations():
    """Verify that vector distance calculations function correctly in PostgreSQL."""
    async with async_session_factory() as session:
        # L2 Distance: ||[1,2,3] - [3,2,1]|| = sqrt(4 + 0 + 4) = sqrt(8) ~ 2.8284
        result = await session.execute(
            text("SELECT '[1,2,3]'::vector <-> '[3,2,1]'::vector AS dist;")
        )
        l2_dist = result.scalar()
        assert l2_dist is not None
        assert abs(l2_dist - 2.828427) < 0.001

        # Cosine Distance: 1 - dot / (||a|| * ||b||)
        # dot([1,0], [0,1]) = 0 -> cosine distance = 1.0
        cos_result = await session.execute(
            text("SELECT '[1,0]'::vector <=> '[0,1]'::vector AS cos_dist;")
        )
        cos_dist = cos_result.scalar()
        assert cos_dist is not None
        assert abs(cos_dist - 1.0) < 0.001


@pytest.mark.asyncio
async def test_get_db_session_dependency():
    """Verify that the get_db generator yields an active AsyncSession and commits/closes."""
    gen = get_db()
    session = await anext(gen)
    try:
        assert isinstance(session, AsyncSession)
        assert session.is_active
        res = await session.execute(text("SELECT 42;"))
        assert res.scalar() == 42
    finally:
        try:
            await anext(gen)
        except StopAsyncIteration:
            pass


@pytest.mark.asyncio
async def test_check_db_health_helper():
    """Verify that the check_db_health utility correctly inspects DB and pgvector."""
    health = await check_db_health()
    assert health["database"] == "connected"
    assert health["pgvector_installed"] is True
    assert health["pgvector_version"] is not None
    assert health["pgvector_operational"] is True


def test_db_health_endpoint_v1(client: TestClient):
    """Verify GET /api/v1/health/db returns 200 with operational pgvector status."""
    response = client.get("/api/v1/health/db")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["app"] == settings.PROJECT_NAME
    assert data["database"] == "connected"
    assert data["pgvector_installed"] is True
    assert data["pgvector_operational"] is True
    assert "pgvector_version" in data


def test_db_health_endpoint_root_alias(client: TestClient):
    """Verify GET /health/db root alias returns 200 and expected payload."""
    response = client.get("/health/db")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["pgvector_installed"] is True


def test_declarative_base_model_subclassing():
    """Verify that models can subclass Base cleanly without errors."""

    class SampleModel(Base):
        __tablename__ = "sample_test_model"
        id = Column(Integer, primary_key=True)

    assert SampleModel.__tablename__ == "sample_test_model"
