"""
Phase 22: Comprehensive End-to-End Integration and User Acceptance Backend Test Suite.

Validates complete candidate workflows across:
  1. Registration, JWT Authentication, and Session Lifecycle
  2. Candidate Profile Creation, Skills, Experience, and Education Synchronization
  3. Opportunity Discovery, Keyword Search, Work Mode Filters, and Detail Ingestion
  4. Hybrid Match Evaluation, Idempotency, Score Verification, and Eligibility
  5. Application Creation, Duplicate Prevention (409), and Full Lifecycle Transitions
  6. Permitted Transitions Matrix, History Audit Logging, and Terminal State Enforcement
  7. Ownership Isolation and Cross-User Data Protection
  8. Boundary Conditions: Inactive Opportunities, Missing Profiles, Invalid Transitions
"""

from __future__ import annotations

import uuid
from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.models.enums import (
    EducationLevel,
    EligibilityStatus,
    EmploymentType,
    WorkMode,
)
from app.models.opportunity import Opportunity
from tests.factories import CandidateProfileFactory, OpportunityFactory, UserFactory

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Test Workflow 1: Authentication, Registration, and Session Lifecycle
# ---------------------------------------------------------------------------


class TestE2EAuthLifecycle:
    """Verifies user registration, login, JWT validation, and invalid credential handling."""

    async def test_complete_auth_flow(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        user_email = f"e2e_user_{uuid.uuid4().hex[:8]}@example.com"
        user_password = "SecurePassword123!"

        # 1. Register new user
        reg_payload = {"email": user_email, "password": user_password}
        reg_res = await async_client.post("/api/v1/auth/register", json=reg_payload)
        assert reg_res.status_code == 201
        reg_data = reg_res.json()
        assert reg_data["email"] == user_email.lower()
        assert "id" in reg_data

        # 2. Duplicate registration rejection (409 Conflict)
        dup_res = await async_client.post("/api/v1/auth/register", json=reg_payload)
        assert dup_res.status_code == 409

        # 3. Authenticate / Login to receive JWT
        login_payload = {"email": user_email, "password": user_password}
        login_res = await async_client.post(
            "/api/v1/auth/login",
            json=login_payload,
        )
        assert login_res.status_code == 200
        token_data = login_res.json()
        assert "access_token" in token_data
        token = token_data["access_token"]
        assert token_data["token_type"] == "bearer"

        # 4. Access protected profile endpoint with Bearer token
        headers = {"Authorization": f"Bearer {token}"}
        me_res = await async_client.get("/api/v1/profiles/me", headers=headers)
        # Profile is automatically initialized/retrieved for authenticated user
        assert me_res.status_code == 200
        assert me_res.json()["user_id"] == reg_data["id"]

        # 5. Invalid token rejection -> 401 Unauthorized
        bad_headers = {"Authorization": "Bearer invalid.token.payload"}
        bad_res = await async_client.get("/api/v1/profiles/me", headers=bad_headers)
        assert bad_res.status_code == 401


# ---------------------------------------------------------------------------
# Test Workflow 2: Profile Creation, Updates, and Skill Management
# ---------------------------------------------------------------------------


class TestE2EProfileManagement:
    """Verifies candidate profile initialization and enrichment."""

    async def test_profile_creation_and_enrichment(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        user = await UserFactory.create(
            db_session, email=f"candidate_{uuid.uuid4().hex[:8]}@example.com"
        )
        await db_session.commit()
        token = create_access_token(subject=str(user.id))
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Create candidate profile
        profile_payload = {
            "full_name": "Devon Systems",
            "headline": "Lead Backend & Distributed Systems Engineer",
            "location_city": "Bengaluru",
            "location_state": "KA",
            "location_country": "India",
            "preferred_salary_min": 3500000,
            "preferred_salary_currency": "INR",
        }

        create_res = await async_client.post(
            "/api/v1/profiles",
            json=profile_payload,
            headers=headers,
        )
        assert create_res.status_code == 201
        profile_data = create_res.json()
        assert profile_data["full_name"] == "Devon Systems"

        # Add skill sub-resource
        skill_res = await async_client.post(
            "/api/v1/profiles/me/skills",
            json={"skill_name": "Python", "years_of_experience": 8},
            headers=headers,
        )
        assert skill_res.status_code == 201

        # Add experience sub-resource
        exp_res = await async_client.post(
            "/api/v1/profiles/me/experience",
            json={
                "company": "CloudScale Ltd",
                "title": "Senior Backend Engineer",
                "start_date": "2021-01-01",
                "description": "High-throughput microservices using FastAPI and PostgreSQL.",
            },
            headers=headers,
        )
        assert exp_res.status_code == 201

        # Add education sub-resource
        edu_res = await async_client.post(
            "/api/v1/profiles/me/education",
            json={
                "institution": "National Institute of Technology",
                "degree": "Bachelor of Technology",
                "field_of_study": "Computer Science",
                "start_date": "2015-08-01",
                "end_date": "2019-05-30",
            },
            headers=headers,
        )
        assert edu_res.status_code == 201

        # 2. Retrieve profile via GET /me
        get_res = await async_client.get("/api/v1/profiles/me", headers=headers)
        assert get_res.status_code == 200
        full_profile = get_res.json()
        assert full_profile["headline"] == "Lead Backend & Distributed Systems Engineer"
        assert len(full_profile["skills"]) == 1
        assert len(full_profile["experiences"]) == 1
        assert len(full_profile["educations"]) == 1


# ---------------------------------------------------------------------------
# Test Workflow 3: Full Opportunity Matching & Hybrid Scoring Verification
# ---------------------------------------------------------------------------


class TestE2EMatchingWorkflow:
    """Verifies opportunity retrieval, hybrid evaluation, scoring weights, and eligibility."""

    async def test_opportunity_discovery_and_matching(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        # Create candidate with profile
        user = await UserFactory.create(
            db_session, email=f"match_candidate_{uuid.uuid4().hex[:8]}@example.com"
        )
        await CandidateProfileFactory.create(
            db_session,
            user_id=user.id,
            full_name="Jane Architect",
            location_city="San Francisco",
            location_country="USA",
        )

        # Create active opportunity
        opp = Opportunity(
            title="Senior Python Cloud Engineer",
            company="Enterprise Nexus",
            description="Scalable cloud microservices with Python, FastAPI, and Docker.",
            required_skills=["Python", "FastAPI"],
            preferred_skills=["Docker", "PostgreSQL"],
            min_experience_years=3,
            max_experience_years=8,
            required_education_level=EducationLevel.BACHELOR,
            work_mode=WorkMode.HYBRID,
            employment_type=EmploymentType.FULLTIME,
            location_city="San Francisco",
            location_state="CA",
            location_country="USA",
            source="manual",
            source_id=f"e2e_opp_{uuid.uuid4().hex[:8]}",
            is_active=True,
        )
        db_session.add(opp)
        await db_session.commit()

        token = create_access_token(subject=str(user.id))
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Discover opportunity via public endpoint
        opp_list_res = await async_client.get("/api/v1/opportunities/?search=Python")
        assert opp_list_res.status_code == 200
        assert opp_list_res.json()["total"] >= 1

        # 2. Fetch opportunity detail
        detail_res = await async_client.get(f"/api/v1/opportunities/{opp.id}")
        assert detail_res.status_code == 200
        assert detail_res.json()["title"] == "Senior Python Cloud Engineer"

        # 3. Trigger hybrid match evaluation
        match_payload = {"opportunity_id": str(opp.id), "semantic_similarity": 0.85}
        match_res = await async_client.post(
            "/api/v1/matches/",
            json=match_payload,
            headers=headers,
        )
        assert match_res.status_code == 200
        match_data = match_res.json()

        # Verify response structure and score ranges [0.0, 1.0]
        assert 0.0 <= match_data["final_score"] <= 1.0
        assert 0.0 <= match_data["semantic_score"] <= 1.0
        assert 0.0 <= match_data["deterministic_score"] <= 1.0
        assert 0.0 <= match_data["score_breakdown"]["skill_overlap"]["score"] <= 1.0
        assert 0.0 <= match_data["score_breakdown"]["experience"]["score"] <= 1.0
        assert 0.0 <= match_data["score_breakdown"]["education"]["score"] <= 1.0
        assert match_data["score_breakdown"]["weights"]["semantic_similarity"] == 0.35
        assert match_data["score_breakdown"]["weights"]["skill_overlap"] == 0.25
        assert match_data["eligibility_status"] in [s.value for s in EligibilityStatus]
        assert isinstance(match_data["skill_gap"]["missing_required_skills"], list)

        # 4. Idempotent re-evaluation
        match_res_2 = await async_client.post(
            "/api/v1/matches/",
            json=match_payload,
            headers=headers,
        )
        assert match_res_2.status_code == 200
        assert match_res_2.json()["id"] == match_data["id"]

        # 5. Inactive opportunity evaluation rejection (422)
        inactive_opp = await OpportunityFactory.create(
            db_session, title="Deprecated Role", is_active=False
        )
        await db_session.commit()

        bad_match_res = await async_client.post(
            "/api/v1/matches/",
            json={"opportunity_id": str(inactive_opp.id)},
            headers=headers,
        )
        assert bad_match_res.status_code == 422


# ---------------------------------------------------------------------------
# Test Workflow 4: Complete Application Tracking Lifecycle & Status Machine
# ---------------------------------------------------------------------------


class TestE2EApplicationTrackingLifecycle:
    """
    Verifies complete application tracking lifecycle:
    save, apply, transitions, audit, and termination.
    """

    async def test_full_application_lifecycle_and_audit(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        user = await UserFactory.create(
            db_session, email=f"app_user_{uuid.uuid4().hex[:8]}@example.com"
        )
        await CandidateProfileFactory.create(db_session, user_id=user.id)
        opp = await OpportunityFactory.create(
            db_session,
            title="Principal Reliability Engineer",
            company="CloudOps Global",
            is_active=True,
        )
        await db_session.commit()

        token = create_access_token(subject=str(user.id))
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Step 1: Save application
        create_res = await async_client.post(
            "/api/v1/applications/",
            json={
                "opportunity_id": str(opp.id),
                "status": "saved",
                "notes": "Saved for weekend review.",
            },
            headers=headers,
        )
        assert create_res.status_code == 201
        app_data = create_res.json()
        app_id = app_data["id"]
        assert app_data["status"] == "saved"
        assert app_data["opportunity"]["title"] == "Principal Reliability Engineer"
        assert len(app_data["status_history"]) == 1
        assert app_data["status_history"][0]["status"] == "saved"

        # 2. Step 2: Duplicate application prevention (409 Conflict)
        dup_res = await async_client.post(
            "/api/v1/applications/",
            json={"opportunity_id": str(opp.id), "status": "saved"},
            headers=headers,
        )
        assert dup_res.status_code == 409
        assert "already exists" in dup_res.json()["detail"].lower()

        # 3. Step 3: Permitted transition: SAVED -> APPLIED
        trans_res_1 = await async_client.patch(
            f"/api/v1/applications/{app_id}/status",
            json={"status": "applied", "notes": "Applied on company careers portal."},
            headers=headers,
        )
        assert trans_res_1.status_code == 200
        assert trans_res_1.json()["status"] == "applied"
        assert trans_res_1.json()["applied_date"] == str(date.today())

        # 4. Step 4: Permitted transition: APPLIED -> OA (Online Assessment)
        trans_res_2 = await async_client.patch(
            f"/api/v1/applications/{app_id}/status",
            json={"status": "oa", "notes": "Completed CodeSignal assessment."},
            headers=headers,
        )
        assert trans_res_2.status_code == 200
        assert trans_res_2.json()["status"] == "oa"

        # 5. Step 5: Permitted transition: OA -> INTERVIEW
        trans_res_3 = await async_client.patch(
            f"/api/v1/applications/{app_id}/status",
            json={
                "status": "interview",
                "notes": "Passed screen, invited to system design interview.",
            },
            headers=headers,
        )
        assert trans_res_3.status_code == 200
        assert trans_res_3.json()["status"] == "interview"

        # 6. Step 6: Permitted transition: INTERVIEW -> OFFER
        trans_res_4 = await async_client.patch(
            f"/api/v1/applications/{app_id}/status",
            json={"status": "offer", "notes": "Received written offer letter."},
            headers=headers,
        )
        assert trans_res_4.status_code == 200
        assert trans_res_4.json()["status"] == "offer"

        # 7. Step 7: Permitted transition: OFFER -> WITHDRAWN (Terminal)
        trans_res_5 = await async_client.patch(
            f"/api/v1/applications/{app_id}/status",
            json={"status": "withdrawn", "notes": "Accepted another offer."},
            headers=headers,
        )
        assert trans_res_5.status_code == 200
        assert trans_res_5.json()["status"] == "withdrawn"

        # 8. Step 8: Prohibited transition from Terminal state (WITHDRAWN -> INTERVIEW) -> 422
        bad_trans = await async_client.patch(
            f"/api/v1/applications/{app_id}/status",
            json={"status": "interview"},
            headers=headers,
        )
        assert bad_trans.status_code == 422
        assert "Invalid status transition" in bad_trans.json()["detail"]

        # 9. Verify full audit trail has 6 recorded events
        detail_res = await async_client.get(f"/api/v1/applications/{app_id}", headers=headers)
        assert detail_res.status_code == 200
        history = detail_res.json()["status_history"]
        assert len(history) == 6
        expected_statuses = ["saved", "applied", "oa", "interview", "offer", "withdrawn"]
        assert [h["status"] for h in history] == expected_statuses


# ---------------------------------------------------------------------------
# Test Workflow 5: Candidate Ownership and Unauthorized Access Protection
# ---------------------------------------------------------------------------


class TestE2ECandidateOwnershipIsolation:
    """
    Verifies strict security boundaries:
    Candidate A cannot access or manipulate Candidate B's data.
    """

    async def test_cross_candidate_isolation(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        # Candidate A
        user_a = await UserFactory.create(
            db_session, email=f"user_a_{uuid.uuid4().hex[:8]}@example.com"
        )
        await CandidateProfileFactory.create(db_session, user_id=user_a.id)

        # Candidate B
        user_b = await UserFactory.create(
            db_session, email=f"user_b_{uuid.uuid4().hex[:8]}@example.com"
        )
        await CandidateProfileFactory.create(db_session, user_id=user_b.id)

        opp = await OpportunityFactory.create(
            db_session, title="Site Reliability Engineer", is_active=True
        )
        await db_session.commit()

        token_a = create_access_token(subject=str(user_a.id))
        token_b = create_access_token(subject=str(user_b.id))
        headers_a = {"Authorization": f"Bearer {token_a}"}
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # Candidate A creates an application
        res_a = await async_client.post(
            "/api/v1/applications/",
            json={"opportunity_id": str(opp.id), "status": "applied"},
            headers=headers_a,
        )
        assert res_a.status_code == 201
        app_a_id = res_a.json()["id"]

        # Candidate B attempts to GET Candidate A's application -> 404 (does not leak existence)
        get_b = await async_client.get(f"/api/v1/applications/{app_a_id}", headers=headers_b)
        assert get_b.status_code == 404

        # Candidate B attempts to mutate Candidate A's status -> 404
        patch_b = await async_client.patch(
            f"/api/v1/applications/{app_a_id}/status",
            json={"status": "offer"},
            headers=headers_b,
        )
        assert patch_b.status_code == 404

        # Candidate B attempts to delete Candidate A's application -> 404
        delete_b = await async_client.delete(f"/api/v1/applications/{app_a_id}", headers=headers_b)
        assert delete_b.status_code == 404

        # Candidate B listing applications returns 0 applications
        list_b = await async_client.get("/api/v1/applications/", headers=headers_b)
        assert list_b.status_code == 200
        assert list_b.json()["total"] == 0
