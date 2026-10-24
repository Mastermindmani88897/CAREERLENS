"""
Backend API test suite for Phase 21 Application Tracking and Status Transitions.

Tests cover:
  - Application creation and saving (POST /api/v1/applications/)
  - Duplicate application prevention (409 Conflict)
  - Inactive/missing opportunity validation (422 / 404)
  - Permitted status transitions and audit history logging
  - Prohibited status transition rejection (422 Unprocessable Entity)
  - Application listing with status filter and search
  - Candidate ownership and isolation enforcement
  - Application deletion
"""

import uuid
from datetime import date

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.models.candidate import CandidateProfile
from app.models.enums import ApplicationStatus
from app.models.opportunity import Opportunity
from app.models.tracking import Application, ApplicationStatusHistory
from app.models.user import User
from app.core.security import create_access_token
from tests.factories import CandidateProfileFactory, OpportunityFactory, UserFactory


@pytest.fixture
async def candidate_user(db_session: AsyncSession) -> tuple[User, CandidateProfile, str]:
    """Create a user with an associated candidate profile and valid JWT token."""
    user = await UserFactory.create(db_session, email=f"candidate_{uuid.uuid4().hex[:8]}@example.com")
    profile = await CandidateProfileFactory.create(db_session, user_id=user.id)
    await db_session.commit()
    token = create_access_token(subject=str(user.id))
    return user, profile, token


@pytest.fixture
async def other_candidate(db_session: AsyncSession) -> tuple[User, CandidateProfile, str]:
    """Create a second distinct candidate user for ownership isolation tests."""
    user = await UserFactory.create(db_session, email=f"other_{uuid.uuid4().hex[:8]}@example.com")
    profile = await CandidateProfileFactory.create(db_session, user_id=user.id)
    await db_session.commit()
    token = create_access_token(subject=str(user.id))
    return user, profile, token


@pytest.fixture
async def active_opportunity(db_session: AsyncSession) -> Opportunity:
    """Create an active opportunity for application tracking."""
    opp = await OpportunityFactory.create(
        db_session,
        title="Senior Platform Engineer",
        company="GlobalTech Cloud",
        is_active=True,
    )
    await db_session.commit()
    return opp


@pytest.fixture
async def inactive_opportunity(db_session: AsyncSession) -> Opportunity:
    """Create an inactive opportunity."""
    opp = await OpportunityFactory.create(
        db_session,
        title="Deprecated Role",
        company="OldCo",
        is_active=False,
    )
    await db_session.commit()
    return opp


@pytest.mark.asyncio
class TestApplicationCreation:
    """Tests for POST /api/v1/applications/"""

    async def test_create_saved_application_success(
        self,
        db_session: AsyncSession,
        candidate_user: tuple[User, CandidateProfile, str],
        active_opportunity: Opportunity,
    ) -> None:
        _, profile, token = candidate_user
        headers = {"Authorization": f"Bearer {token}"}

        payload = {
            "opportunity_id": str(active_opportunity.id),
            "status": "saved",
            "notes": "Bookmarked for later application.",
        }

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.post("/api/v1/applications/", json=payload, headers=headers)

        assert res.status_code == 201
        data = res.json()
        assert data["opportunity_id"] == str(active_opportunity.id)
        assert data["status"] == "saved"
        assert data["notes"] == "Bookmarked for later application."
        assert data["opportunity"]["title"] == "Senior Platform Engineer"
        assert data["opportunity"]["company"] == "GlobalTech Cloud"
        assert len(data["status_history"]) == 1
        assert data["status_history"][0]["status"] == "saved"

    async def test_create_applied_application_defaults_applied_date(
        self,
        db_session: AsyncSession,
        candidate_user: tuple[User, CandidateProfile, str],
        active_opportunity: Opportunity,
    ) -> None:
        _, profile, token = candidate_user
        headers = {"Authorization": f"Bearer {token}"}

        payload = {
            "opportunity_id": str(active_opportunity.id),
            "status": "applied",
        }

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.post("/api/v1/applications/", json=payload, headers=headers)

        assert res.status_code == 201
        data = res.json()
        assert data["status"] == "applied"
        assert data["applied_date"] == str(date.today())

    async def test_duplicate_application_rejected_with_409(
        self,
        db_session: AsyncSession,
        candidate_user: tuple[User, CandidateProfile, str],
        active_opportunity: Opportunity,
    ) -> None:
        _, profile, token = candidate_user
        headers = {"Authorization": f"Bearer {token}"}

        payload = {"opportunity_id": str(active_opportunity.id), "status": "saved"}

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res1 = await ac.post("/api/v1/applications/", json=payload, headers=headers)
            assert res1.status_code == 201

            # Duplicate submission
            res2 = await ac.post("/api/v1/applications/", json=payload, headers=headers)
            assert res2.status_code == 409
            assert "already exists" in res2.json()["detail"]

    async def test_inactive_opportunity_rejected_with_422(
        self,
        db_session: AsyncSession,
        candidate_user: tuple[User, CandidateProfile, str],
        inactive_opportunity: Opportunity,
    ) -> None:
        _, profile, token = candidate_user
        headers = {"Authorization": f"Bearer {token}"}

        payload = {"opportunity_id": str(inactive_opportunity.id)}

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.post("/api/v1/applications/", json=payload, headers=headers)

        assert res.status_code == 422
        assert "inactive" in res.json()["detail"].lower()


@pytest.mark.asyncio
class TestStatusTransitions:
    """Tests for PATCH /api/v1/applications/{id}/status and state machine rules."""

    async def test_permitted_transition_lifecycle(
        self,
        db_session: AsyncSession,
        candidate_user: tuple[User, CandidateProfile, str],
        active_opportunity: Opportunity,
    ) -> None:
        _, profile, token = candidate_user
        headers = {"Authorization": f"Bearer {token}"}

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            # 1. Start at SAVED
            res = await ac.post(
                "/api/v1/applications/",
                json={"opportunity_id": str(active_opportunity.id), "status": "saved"},
                headers=headers,
            )
            app_id = res.json()["id"]

            # 2. Transition SAVED -> APPLIED (permitted)
            res_applied = await ac.patch(
                f"/api/v1/applications/{app_id}/status",
                json={"status": "applied", "notes": "Submitted application via career page."},
                headers=headers,
            )
            assert res_applied.status_code == 200
            assert res_applied.json()["status"] == "applied"
            assert res_applied.json()["applied_date"] == str(date.today())

            # 3. Transition APPLIED -> OA (permitted)
            res_oa = await ac.patch(
                f"/api/v1/applications/{app_id}/status",
                json={"status": "oa", "notes": "Received 90-min HackerRank challenge."},
                headers=headers,
            )
            assert res_oa.status_code == 200
            assert res_oa.json()["status"] == "oa"

            # 4. Transition OA -> INTERVIEW (permitted)
            res_interview = await ac.patch(
                f"/api/v1/applications/{app_id}/status",
                json={"status": "interview", "notes": "Invited to round 1 technical interview."},
                headers=headers,
            )
            assert res_interview.status_code == 200
            assert res_interview.json()["status"] == "interview"

            # 5. Transition INTERVIEW -> OFFER (permitted)
            res_offer = await ac.patch(
                f"/api/v1/applications/{app_id}/status",
                json={"status": "offer", "notes": "Received written offer letter."},
                headers=headers,
            )
            assert res_offer.status_code == 200
            assert res_offer.json()["status"] == "offer"

            # Check full status history contains 5 audit entries
            detail_res = await ac.get(f"/api/v1/applications/{app_id}", headers=headers)
            assert detail_res.status_code == 200
            history = detail_res.json()["status_history"]
            assert len(history) == 5
            statuses = [h["status"] for h in history]
            assert statuses == ["saved", "applied", "oa", "interview", "offer"]

    async def test_prohibited_transition_rejected_with_422(
        self,
        db_session: AsyncSession,
        candidate_user: tuple[User, CandidateProfile, str],
        active_opportunity: Opportunity,
    ) -> None:
        _, profile, token = candidate_user
        headers = {"Authorization": f"Bearer {token}"}

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.post(
                "/api/v1/applications/",
                json={"opportunity_id": str(active_opportunity.id), "status": "saved"},
                headers=headers,
            )
            app_id = res.json()["id"]

            # Direct jump from SAVED -> OFFER is invalid
            bad_res = await ac.patch(
                f"/api/v1/applications/{app_id}/status",
                json={"status": "offer"},
                headers=headers,
            )
            assert bad_res.status_code == 422
            assert "Invalid status transition" in bad_res.json()["detail"]

    async def test_terminal_state_rejection(
        self,
        db_session: AsyncSession,
        candidate_user: tuple[User, CandidateProfile, str],
        active_opportunity: Opportunity,
    ) -> None:
        _, profile, token = candidate_user
        headers = {"Authorization": f"Bearer {token}"}

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.post(
                "/api/v1/applications/",
                json={"opportunity_id": str(active_opportunity.id), "status": "applied"},
                headers=headers,
            )
            app_id = res.json()["id"]

            # Move to REJECTED (terminal)
            rej_res = await ac.patch(
                f"/api/v1/applications/{app_id}/status",
                json={"status": "rejected"},
                headers=headers,
            )
            assert rej_res.status_code == 200
            assert rej_res.json()["status"] == "rejected"

            # Attempting transition from REJECTED -> INTERVIEW must fail
            after_rej = await ac.patch(
                f"/api/v1/applications/{app_id}/status",
                json={"status": "interview"},
                headers=headers,
            )
            assert after_rej.status_code == 422
            assert "Invalid status transition" in after_rej.json()["detail"]


@pytest.mark.asyncio
class TestApplicationListingAndOwnership:
    """Tests for GET /api/v1/applications/ and ownership isolation."""

    async def test_list_and_filter_applications(
        self,
        db_session: AsyncSession,
        candidate_user: tuple[User, CandidateProfile, str],
    ) -> None:
        _, profile, token = candidate_user
        headers = {"Authorization": f"Bearer {token}"}

        opp1 = await OpportunityFactory.create(db_session, title="Frontend Developer", is_active=True)
        opp2 = await OpportunityFactory.create(db_session, title="DevOps Engineer", is_active=True)
        await db_session.commit()

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            await ac.post(
                "/api/v1/applications/",
                json={"opportunity_id": str(opp1.id), "status": "saved"},
                headers=headers,
            )
            await ac.post(
                "/api/v1/applications/",
                json={"opportunity_id": str(opp2.id), "status": "applied"},
                headers=headers,
            )

            # List all
            all_res = await ac.get("/api/v1/applications/", headers=headers)
            assert all_res.status_code == 200
            assert all_res.json()["total"] == 2

            # Filter by status=applied
            applied_res = await ac.get("/api/v1/applications/?status=applied", headers=headers)
            assert applied_res.status_code == 200
            assert applied_res.json()["total"] == 1
            assert applied_res.json()["items"][0]["opportunity"]["title"] == "DevOps Engineer"

            # Search by keyword
            search_res = await ac.get("/api/v1/applications/?search=frontend", headers=headers)
            assert search_res.status_code == 200
            assert search_res.json()["total"] == 1
            assert search_res.json()["items"][0]["opportunity"]["title"] == "Frontend Developer"

    async def test_candidate_ownership_isolation(
        self,
        db_session: AsyncSession,
        candidate_user: tuple[User, CandidateProfile, str],
        other_candidate: tuple[User, CandidateProfile, str],
        active_opportunity: Opportunity,
    ) -> None:
        _, _, token1 = candidate_user
        _, _, token2 = other_candidate

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            # Candidate 1 creates application
            res1 = await ac.post(
                "/api/v1/applications/",
                json={"opportunity_id": str(active_opportunity.id), "status": "saved"},
                headers={"Authorization": f"Bearer {token1}"},
            )
            app1_id = res1.json()["id"]

            # Candidate 2 cannot view Candidate 1's application
            get_res = await ac.get(
                f"/api/v1/applications/{app1_id}",
                headers={"Authorization": f"Bearer {token2}"},
            )
            assert get_res.status_code == 404

            # Candidate 2 cannot update status of Candidate 1's application
            patch_res = await ac.patch(
                f"/api/v1/applications/{app1_id}/status",
                json={"status": "applied"},
                headers={"Authorization": f"Bearer {token2}"},
            )
            assert patch_res.status_code == 404

            # Candidate 2 cannot delete Candidate 1's application
            del_res = await ac.delete(
                f"/api/v1/applications/{app1_id}",
                headers={"Authorization": f"Bearer {token2}"},
            )
            assert del_res.status_code == 404

    async def test_get_transitions_matrix(
        self,
        candidate_user: tuple[User, CandidateProfile, str],
    ) -> None:
        _, _, token = candidate_user
        headers = {"Authorization": f"Bearer {token}"}

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.get("/api/v1/applications/transitions", headers=headers)

        assert res.status_code == 200
        matrix = res.json()
        assert "saved" in matrix
        assert "applied" in matrix["saved"]
        assert "withdrawn" in matrix["saved"]
        assert "offer" not in matrix["saved"]
        assert matrix["rejected"] == []
        assert matrix["withdrawn"] == []
