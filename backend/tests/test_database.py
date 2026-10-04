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


@pytest.mark.asyncio
async def test_careerlens_user_least_privilege():
    """Verify that careerlens_user role adheres to least-privilege (NOCREATEDB, NOSUPERUSER)."""
    async with async_session_factory() as session:
        result = await session.execute(
            text(
                "SELECT rolname, rolsuper, rolcreatedb, rolcreaterole, rolcanlogin "
                "FROM pg_roles WHERE rolname = 'careerlens_user';"
            )
        )
        row = result.mappings().one()
        assert row["rolname"] == "careerlens_user"
        assert row["rolcanlogin"] is True, "User should be able to log in"
        assert row["rolcreatedb"] is False, "Least privilege violated: CREATEDB must be False"
        assert row["rolsuper"] is False, "Least privilege violated: SUPERUSER must be False"
        assert row["rolcreaterole"] is False, "Least privilege violated: CREATEROLE must be False"


def test_alembic_infrastructure_configuration():
    """Verify that Alembic configuration files and directory structure exist and are valid."""
    from pathlib import Path

    from alembic.config import Config

    from alembic import command

    backend_dir = Path(__file__).resolve().parent.parent
    ini_path = backend_dir / "alembic.ini"
    alembic_dir = backend_dir / "alembic"
    versions_dir = alembic_dir / "versions"

    assert ini_path.exists(), "alembic.ini must exist in backend root"
    assert alembic_dir.exists(), "alembic migration directory must exist"
    assert (alembic_dir / "env.py").exists(), "alembic/env.py must exist"
    assert versions_dir.exists(), "alembic/versions directory must exist"

    # Verify Alembic can read configuration and inspect heads without error
    alembic_cfg = Config(str(ini_path))
    # command.heads should run without raising any exceptions
    command.heads(alembic_cfg)


@pytest.mark.asyncio
async def test_phase3_boundary_no_application_models():
    """Verify that Phase 4 application models and tables do NOT exist yet."""
    phase4_tables = {
        "users",
        "candidate_profiles",
        "resumes",
        "skills",
        "educations",
        "experiences",
        "projects",
        "certifications",
        "opportunities",
        "opportunity_skills",
        "matches",
        "applications",
        "application_status_history",
        "interview_prep",
    }
    async with async_session_factory() as session:
        result = await session.execute(
            text("SELECT tablename FROM pg_tables WHERE schemaname = 'public';")
        )
        existing_tables = {row[0] for row in result.fetchall()}
        intersection = phase4_tables.intersection(existing_tables)
        assert not intersection, f"Phase 4 tables exist prematurely: {intersection}"
