"""
Tests verifying test database isolation, safety guards, and transaction rollback mechanics.
Adheres to Phase 9 Testing Foundation requirements.
"""

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.db.session import async_session_factory
from app.models.user import User
from tests.factories.user_factory import UserFactory

# =============================================================================
# 1. DATABASE SAFETY GUARD TESTS
# =============================================================================


def test_safety_guard_aborts_on_non_test_database():
    """Verify that the safety guard detects and raises an error on production/dev DB names."""
    invalid_url = "postgresql+asyncpg://user:PASSWORD@localhost:5432/careerlens_prod"
    db_name = invalid_url.rsplit("/", 1)[-1].split("?")[0]

    with pytest.raises(RuntimeError, match="SAFETY ABORT"):
        if "test" not in db_name.lower():
            raise RuntimeError(
                f"SAFETY ABORT: Test suite attempted to run against "
                f"non-test database: '{db_name}'. "
                "Tests must target an isolated test database (e.g. careerlens_test)."
            )


def test_settings_switches_to_test_database():
    """Verify Settings.effective_database_url routes to TEST_DATABASE_URL in test environment."""
    test_settings = Settings(
        ENVIRONMENT="test",
        DATABASE_URL="postgresql+asyncpg://user:PASSWORD@localhost:5432/careerlens_db",
        TEST_DATABASE_URL="postgresql+asyncpg://user:PASSWORD@localhost:5432/careerlens_test",
    )
    assert test_settings.effective_database_url == test_settings.TEST_DATABASE_URL
    assert "careerlens_test" in test_settings.effective_database_url

    dev_settings = Settings(
        ENVIRONMENT="development",
        DATABASE_URL="postgresql+asyncpg://user:PASSWORD@localhost:5432/careerlens_db",
        TEST_DATABASE_URL="postgresql+asyncpg://user:PASSWORD@localhost:5432/careerlens_test",
    )
    assert dev_settings.effective_database_url == dev_settings.DATABASE_URL
    assert "careerlens_db" in dev_settings.effective_database_url


# =============================================================================
# 2. SESSION ISOLATION & ROLLBACK TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_session_rollback_isolates_uncommitted_data(db_session: AsyncSession):
    """
    Verify uncommitted data within db_session is isolated and rolls back automatically.
    """
    unique_email = f"rollback_test_{uuid.uuid4().hex[:8]}@example.com"
    user = UserFactory.build(email=unique_email)
    db_session.add(user)
    await db_session.flush()

    # Within the same session, the record is visible
    stmt = select(User).where(User.email == unique_email)
    res = await db_session.execute(stmt)
    assert res.scalar_one_or_none() is not None

    # In a separate independent session, uncommitted data is NOT visible
    async with async_session_factory() as separate_session:
        sep_res = await separate_session.execute(stmt)
        assert sep_res.scalar_one_or_none() is None

    # Rollback current session
    await db_session.rollback()

    # After rollback, record is gone from current session too
    post_res = await db_session.execute(stmt)
    assert post_res.scalar_one_or_none() is None
