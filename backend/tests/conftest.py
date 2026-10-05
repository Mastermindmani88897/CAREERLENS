"""
CareerLens Centralized Pytest Configuration and Reusable Test Fixtures.
Adheres to Phase 9 Testing Foundation.
Provides test database safety enforcement, async sessions, HTTP clients,
authentication helpers, and reusable model fixtures.
"""

import os
from collections.abc import AsyncGenerator, Generator

import pytest

# Enforce test environment before importing application components
os.environ["ENVIRONMENT"] = "test"

from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import async_session_factory
from app.main import app
from app.models.candidate import CandidateProfile
from app.models.opportunity import Opportunity
from app.models.user import User
from tests.factories.candidate_factory import CandidateProfileFactory
from tests.factories.opportunity_factory import OpportunityFactory
from tests.helpers.auth import create_authenticated_headers, create_test_user

# Ensure settings recognizes test environment
settings.ENVIRONMENT = "test"


@pytest.fixture(scope="session", autouse=True)
def enforce_test_database_safety() -> None:
    """
    CRITICAL TEST SAFETY GUARD:
    Guarantees that test suites can ONLY execute against a database whose name
    contains 'test' (e.g. careerlens_test). Aborts test execution immediately
    if configured against development or production databases.
    """
    url = settings.effective_database_url
    db_name = url.rsplit("/", 1)[-1].split("?")[0]
    if "test" not in db_name.lower():
        raise RuntimeError(
            f"SAFETY ABORT: Test suite attempted to run against non-test database: '{db_name}'. "
            "Tests must target an isolated test database (e.g. careerlens_test)."
        )


@pytest.fixture(scope="session")
def client() -> Generator[TestClient, None, None]:
    """Synchronous FastAPI TestClient fixture with lifespan execution."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Asynchronous HTTP test client using httpx and ASGITransport."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Yield an isolated async database session connected to careerlens_test.
    Rolls back any uncommitted transactions upon test exit to maintain state isolation.
    """
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.rollback()
            await session.close()


@pytest.fixture
async def authenticated_user(db_session: AsyncSession) -> tuple[User, str]:
    """
    Create and persist a test User entity in the test database.
    Yields (user_instance, plaintext_password).
    """
    user, plain_password = await create_test_user(db_session)
    await db_session.commit()
    return user, plain_password


@pytest.fixture
async def auth_headers(authenticated_user: tuple[User, str]) -> dict[str, str]:
    """Generate valid Bearer Authorization headers for the authenticated_user fixture."""
    user, _ = authenticated_user
    return create_authenticated_headers(user.id)


@pytest.fixture
def authenticated_client(auth_headers: dict[str, str]) -> Generator[TestClient, None, None]:
    """Synchronous TestClient pre-configured with valid Authorization headers."""
    with TestClient(app, headers=auth_headers) as tc:
        yield tc


@pytest.fixture
async def sample_candidate_profile(
    db_session: AsyncSession, authenticated_user: tuple[User, str]
) -> CandidateProfile:
    """Create and persist a sample CandidateProfile linked to authenticated_user."""
    user, _ = authenticated_user
    profile = await CandidateProfileFactory.create(db_session, user_id=user.id)
    await db_session.commit()
    return profile


@pytest.fixture
async def sample_opportunity(db_session: AsyncSession) -> Opportunity:
    """Create and persist a sample Opportunity entity."""
    opp = await OpportunityFactory.create(db_session)
    await db_session.commit()
    return opp
