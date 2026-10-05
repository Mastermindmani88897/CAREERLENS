"""
Integration tests verifying the testing foundation infrastructure.
Validates async HTTP client, authenticated client fixtures, auth helpers,
and sample model fixtures against live FastAPI endpoints and test database.
"""

from fastapi.testclient import TestClient
from httpx import AsyncClient

from app.models.candidate import CandidateProfile
from app.models.opportunity import Opportunity
from app.models.user import User
from tests.helpers.auth import create_authenticated_headers, login_test_user

# =============================================================================
# 1. ASYNC HTTP TEST CLIENT INTEGRATION
# =============================================================================


async def test_async_client_health_check(async_client: AsyncClient):
    """Verify async_client makes non-blocking HTTP requests to health endpoints."""
    response = await async_client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["app"] == "CareerLens"

    alias_response = await async_client.get("/health")
    assert alias_response.status_code == 200


# =============================================================================
# 2. AUTHENTICATED CLIENT FIXTURE INTEGRATION
# =============================================================================


def test_authenticated_client_fixture_accesses_protected_me(
    authenticated_client: TestClient,
    authenticated_user: tuple[User, str],
):
    """Verify authenticated_client automatically carries valid Authorization Bearer header."""
    user, _ = authenticated_user
    response = authenticated_client.get("/api/v1/auth/me")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(user.id)
    assert data["email"] == user.email
    assert data["is_active"] is True
    assert "hashed_password" not in data


def test_auth_helpers_login_flow(client: TestClient, authenticated_user: tuple[User, str]):
    """Verify login_test_user helper executes authentication and retrieves token."""
    user, plain_password = authenticated_user
    token = login_test_user(client, user.email, plain_password)
    assert token is not None
    assert len(token) > 20

    # Use generated token to query /auth/me
    headers = create_authenticated_headers(user.id)
    resp = client.get("/api/v1/auth/me", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == str(user.id)


# =============================================================================
# 3. SAMPLE MODEL FIXTURES INTEGRATION
# =============================================================================


def test_sample_candidate_profile_fixture(
    sample_candidate_profile: CandidateProfile,
    authenticated_user: tuple[User, str],
):
    """Verify sample_candidate_profile fixture links properly to authenticated_user."""
    user, _ = authenticated_user
    assert sample_candidate_profile.id is not None
    assert sample_candidate_profile.user_id == user.id
    assert sample_candidate_profile.full_name is not None


def test_sample_opportunity_fixture(sample_opportunity: Opportunity):
    """Verify sample_opportunity fixture persists an active opportunity with vector embedding."""
    assert sample_opportunity.id is not None
    assert sample_opportunity.is_active is True
    assert len(sample_opportunity.job_embedding) == 384
    assert len(sample_opportunity.required_skills) > 0
