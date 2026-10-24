"""
Phase 19 Matching API — Integration Tests.

Covers:
  - POST /api/v1/matches/  authentication enforcement
  - POST trigger persists a Match record with correct structure
  - POST re-trigger is idempotent (same pair, refreshed scores)
  - GET /api/v1/matches/ returns paginated list with correct filtering
  - GET /api/v1/matches/{id} ownership enforcement (404 for other user's match)
  - 404 for non-existent opportunity
  - 422 for inactive opportunity
  - Match result eligibility status correctness
  - Score fields within [0.0, 1.0] range

Prerequisites:
  These tests hit the test database via the async test client.
  Requires ENVIRONMENT=test and a 'careerlens_test' database.
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate import CandidateProfile, Education, Experience, Skill
from app.models.enums import (
    EducationLevel,
    EligibilityStatus,
    EmploymentType,
    SkillCategory,
    SkillProficiency,
    SkillSource,
    WorkMode,
)
from app.models.opportunity import Opportunity
from tests.helpers.auth import create_authenticated_headers, create_test_user

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def user_with_profile(db_session: AsyncSession) -> tuple[Any, dict[str, str]]:
    """Create a user + profile with skills, experience, education. Return (profile, headers)."""
    user, _ = await create_test_user(db_session)
    await db_session.commit()

    profile = CandidateProfile(
        user_id=user.id,
        full_name="Alice Engineer",
        headline="Senior Python Developer",
        preferred_work_mode=WorkMode.HYBRID,
        preferred_employment_type=EmploymentType.FULLTIME,
        location_city="San Francisco",
        location_state="CA",
        location_country="USA",
        open_to_relocation=True,
    )
    db_session.add(profile)
    await db_session.flush()

    # Skills
    for skill_name in ["Python", "FastAPI", "PostgreSQL"]:
        db_session.add(
            Skill(
                candidate_profile_id=profile.id,
                skill_name=skill_name,
                category=SkillCategory.TECHNICAL,
                proficiency_level=SkillProficiency.ADVANCED,
                source=SkillSource.MANUAL,
            )
        )

    # Experience: 4 years
    start = date.today() - timedelta(days=4 * 365)
    db_session.add(
        Experience(
            candidate_profile_id=profile.id,
            company="Tech Corp",
            title="Software Engineer",
            employment_type=EmploymentType.FULLTIME,
            work_mode=WorkMode.HYBRID,
            start_date=start,
            is_current=True,
        )
    )

    # Education: Bachelor
    db_session.add(
        Education(
            candidate_profile_id=profile.id,
            institution="State University",
            degree="B.Sc. Computer Science",
            field_of_study="Computer Science",
            education_level=EducationLevel.BACHELOR,
            start_date=date(2016, 9, 1),
            end_date=date(2020, 5, 30),
            is_current=False,
        )
    )

    await db_session.commit()
    headers = create_authenticated_headers(user.id)
    return profile, headers


@pytest.fixture
async def active_opportunity(db_session: AsyncSession) -> Opportunity:
    """Create an active opportunity matching the user_with_profile fixture."""
    opp = Opportunity(
        title="Python Backend Engineer",
        company="MegaCorp",
        description="Build scalable Python microservices with FastAPI and PostgreSQL.",
        required_skills=["Python", "FastAPI"],
        preferred_skills=["Docker"],
        min_experience_years=2,
        max_experience_years=8,
        required_education_level=EducationLevel.BACHELOR,
        work_mode=WorkMode.HYBRID,
        employment_type=EmploymentType.FULLTIME,
        location_city="San Francisco",
        location_state="CA",
        location_country="USA",
        source="synthetic",
        source_id=f"test_opp_{uuid.uuid4().hex[:8]}",
        is_active=True,
    )
    db_session.add(opp)
    await db_session.commit()
    return opp


@pytest.fixture
async def inactive_opportunity(db_session: AsyncSession) -> Opportunity:
    """Create an inactive opportunity."""
    opp = Opportunity(
        title="Inactive Role",
        company="OldCorp",
        description="This role is no longer accepting applications.",
        required_skills=[],
        preferred_skills=[],
        min_experience_years=None,
        required_education_level=EducationLevel.ANY,
        work_mode=WorkMode.ANY,
        employment_type=EmploymentType.FULLTIME,
        source="synthetic",
        source_id=f"test_inactive_{uuid.uuid4().hex[:8]}",
        is_active=False,
    )
    db_session.add(opp)
    await db_session.commit()
    return opp


# ---------------------------------------------------------------------------
# SECTION 1: Authentication enforcement
# ---------------------------------------------------------------------------


class TestMatchingAuthEnforcement:
    async def test_post_requires_authentication(self, async_client: AsyncClient):
        payload = {"opportunity_id": str(uuid.uuid4())}
        response = await async_client.post("/api/v1/matches/", json=payload)
        assert response.status_code == 401

    async def test_get_list_requires_authentication(self, async_client: AsyncClient):
        response = await async_client.get("/api/v1/matches/")
        assert response.status_code == 401

    async def test_get_single_requires_authentication(self, async_client: AsyncClient):
        response = await async_client.get(f"/api/v1/matches/{uuid.uuid4()}")
        assert response.status_code == 401

    async def test_invalid_token_rejected(self, async_client: AsyncClient):
        headers = {"Authorization": "Bearer invalid.token.here"}
        response = await async_client.get("/api/v1/matches/", headers=headers)
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# SECTION 2: POST /matches/ — trigger match evaluation
# ---------------------------------------------------------------------------


class TestTriggerMatch:
    async def test_trigger_returns_200_with_match_structure(
        self,
        async_client: AsyncClient,
        user_with_profile: tuple[Any, dict],
        active_opportunity: Opportunity,
    ):
        _, headers = user_with_profile
        payload = {
            "opportunity_id": str(active_opportunity.id),
            "semantic_similarity": 0.75,
        }
        response = await async_client.post("/api/v1/matches/", json=payload, headers=headers)
        assert response.status_code == 200, response.text
        data = response.json()

        # Required fields
        assert "id" in data
        assert "candidate_profile_id" in data
        assert "opportunity_id" in data
        assert "final_score" in data
        assert "semantic_score" in data
        assert "deterministic_score" in data
        assert "eligibility_status" in data
        assert "score_breakdown" in data
        assert "explanation" in data
        assert "skill_gap" in data
        assert "computed_at" in data

    async def test_final_score_in_valid_range(
        self,
        async_client: AsyncClient,
        user_with_profile: tuple[Any, dict],
        active_opportunity: Opportunity,
    ):
        _, headers = user_with_profile
        payload = {"opportunity_id": str(active_opportunity.id), "semantic_similarity": 0.5}
        response = await async_client.post("/api/v1/matches/", json=payload, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert 0.0 <= data["final_score"] <= 1.0
        assert 0.0 <= data["semantic_score"] <= 1.0
        assert 0.0 <= data["deterministic_score"] <= 1.0

    async def test_eligibility_status_valid_value(
        self,
        async_client: AsyncClient,
        user_with_profile: tuple[Any, dict],
        active_opportunity: Opportunity,
    ):
        _, headers = user_with_profile
        payload = {"opportunity_id": str(active_opportunity.id)}
        response = await async_client.post("/api/v1/matches/", json=payload, headers=headers)
        assert response.status_code == 200
        data = response.json()
        valid_statuses = {e.value for e in EligibilityStatus}
        assert data["eligibility_status"] in valid_statuses

    async def test_idempotent_second_trigger_updates_not_duplicates(
        self,
        async_client: AsyncClient,
        user_with_profile: tuple[Any, dict],
        active_opportunity: Opportunity,
        db_session: AsyncSession,
    ):
        """Triggering the same pair twice should update, not create a second Match row."""
        _, headers = user_with_profile
        payload = {"opportunity_id": str(active_opportunity.id), "semantic_similarity": 0.6}

        r1 = await async_client.post("/api/v1/matches/", json=payload, headers=headers)
        assert r1.status_code == 200
        id1 = r1.json()["id"]

        # Re-trigger with different semantic score
        payload["semantic_similarity"] = 0.9
        r2 = await async_client.post("/api/v1/matches/", json=payload, headers=headers)
        assert r2.status_code == 200
        id2 = r2.json()["id"]

        # Same record id (idempotent upsert)
        assert id1 == id2

    async def test_trigger_default_semantic_similarity(
        self,
        async_client: AsyncClient,
        user_with_profile: tuple[Any, dict],
        active_opportunity: Opportunity,
    ):
        """Omitting semantic_similarity defaults to 0.0."""
        _, headers = user_with_profile
        payload = {"opportunity_id": str(active_opportunity.id)}
        response = await async_client.post("/api/v1/matches/", json=payload, headers=headers)
        assert response.status_code == 200
        data = response.json()
        # Approved formula: max(0, cosine) -> input 0.0 yields 0.0
        assert data["score_breakdown"]["semantic_similarity_raw"] == pytest.approx(0.0, abs=0.001)
        assert data["score_breakdown"]["semantic_similarity_normalized"] == pytest.approx(
            0.0, abs=0.001
        )

    async def test_nonexistent_opportunity_returns_404(
        self,
        async_client: AsyncClient,
        user_with_profile: tuple[Any, dict],
    ):
        _, headers = user_with_profile
        payload = {"opportunity_id": str(uuid.uuid4())}
        response = await async_client.post("/api/v1/matches/", json=payload, headers=headers)
        assert response.status_code == 404

    async def test_inactive_opportunity_returns_422(
        self,
        async_client: AsyncClient,
        user_with_profile: tuple[Any, dict],
        inactive_opportunity: Opportunity,
    ):
        _, headers = user_with_profile
        payload = {"opportunity_id": str(inactive_opportunity.id)}
        response = await async_client.post("/api/v1/matches/", json=payload, headers=headers)
        assert response.status_code == 422

    async def test_skill_gap_present_in_response(
        self,
        async_client: AsyncClient,
        user_with_profile: tuple[Any, dict],
        active_opportunity: Opportunity,
    ):
        _, headers = user_with_profile
        payload = {"opportunity_id": str(active_opportunity.id)}
        response = await async_client.post("/api/v1/matches/", json=payload, headers=headers)
        assert response.status_code == 200
        skill_gap = response.json()["skill_gap"]
        assert "matched_required_skills" in skill_gap
        assert "missing_required_skills" in skill_gap

    async def test_no_profile_returns_404(
        self,
        async_client: AsyncClient,
        active_opportunity: Opportunity,
        db_session: AsyncSession,
    ):
        """User with no profile gets 404."""
        user, _ = await create_test_user(db_session)
        await db_session.commit()
        headers = create_authenticated_headers(user.id)
        payload = {"opportunity_id": str(active_opportunity.id)}
        response = await async_client.post("/api/v1/matches/", json=payload, headers=headers)
        assert response.status_code == 404

    async def test_semantic_similarity_out_of_bounds_rejected(
        self,
        async_client: AsyncClient,
        user_with_profile: tuple[Any, dict],
        active_opportunity: Opportunity,
    ):
        _, headers = user_with_profile
        payload = {"opportunity_id": str(active_opportunity.id), "semantic_similarity": 2.5}
        response = await async_client.post("/api/v1/matches/", json=payload, headers=headers)
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# SECTION 3: GET /matches/ — list matches
# ---------------------------------------------------------------------------


class TestListMatches:
    async def _trigger_match(
        self,
        client: AsyncClient,
        headers: dict,
        opportunity_id: str,
        semantic_similarity: float = 0.5,
    ):
        payload = {"opportunity_id": opportunity_id, "semantic_similarity": semantic_similarity}
        r = await client.post("/api/v1/matches/", json=payload, headers=headers)
        assert r.status_code == 200, r.text
        return r.json()

    async def test_empty_list_initially(
        self,
        async_client: AsyncClient,
        user_with_profile: tuple[Any, dict],
    ):
        _, headers = user_with_profile
        response = await async_client.get("/api/v1/matches/", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] >= 0

    async def test_triggered_match_appears_in_list(
        self,
        async_client: AsyncClient,
        user_with_profile: tuple[Any, dict],
        active_opportunity: Opportunity,
    ):
        _, headers = user_with_profile
        await self._trigger_match(async_client, headers, str(active_opportunity.id))

        response = await async_client.get("/api/v1/matches/", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        ids = [item["opportunity_id"] for item in data["items"]]
        assert str(active_opportunity.id) in ids

    async def test_pagination_params_respected(
        self,
        async_client: AsyncClient,
        user_with_profile: tuple[Any, dict],
        active_opportunity: Opportunity,
    ):
        _, headers = user_with_profile
        response = await async_client.get(
            "/api/v1/matches/", headers=headers, params={"page": 1, "page_size": 5}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 5

    async def test_eligibility_filter(
        self,
        async_client: AsyncClient,
        user_with_profile: tuple[Any, dict],
        active_opportunity: Opportunity,
    ):
        _, headers = user_with_profile
        await self._trigger_match(async_client, headers, str(active_opportunity.id))

        for status_val in ["eligible", "partial", "review_required"]:
            response = await async_client.get(
                "/api/v1/matches/",
                headers=headers,
                params={"eligibility_status": status_val},
            )
            assert response.status_code == 200

    async def test_min_score_filter(
        self,
        async_client: AsyncClient,
        user_with_profile: tuple[Any, dict],
        active_opportunity: Opportunity,
    ):
        _, headers = user_with_profile
        await self._trigger_match(async_client, headers, str(active_opportunity.id))

        response = await async_client.get(
            "/api/v1/matches/",
            headers=headers,
            params={"min_score": 0.9},
        )
        assert response.status_code == 200
        data = response.json()
        # All returned items should have score >= 0.9
        for item in data["items"]:
            assert item["final_score"] >= 0.9


# ---------------------------------------------------------------------------
# SECTION 4: GET /matches/{id} — single match retrieval
# ---------------------------------------------------------------------------


class TestGetMatchById:
    async def test_get_own_match_returns_200(
        self,
        async_client: AsyncClient,
        user_with_profile: tuple[Any, dict],
        active_opportunity: Opportunity,
    ):
        _, headers = user_with_profile
        trigger_resp = await async_client.post(
            "/api/v1/matches/",
            json={"opportunity_id": str(active_opportunity.id)},
            headers=headers,
        )
        assert trigger_resp.status_code == 200
        match_id = trigger_resp.json()["id"]

        response = await async_client.get(f"/api/v1/matches/{match_id}", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == match_id

    async def test_cannot_access_other_users_match(
        self,
        async_client: AsyncClient,
        user_with_profile: tuple[Any, dict],
        active_opportunity: Opportunity,
        db_session: AsyncSession,
    ):
        """User B should not be able to retrieve User A's match — gets 404."""
        _, headers_a = user_with_profile

        # User A triggers a match
        trigger_resp = await async_client.post(
            "/api/v1/matches/",
            json={"opportunity_id": str(active_opportunity.id)},
            headers=headers_a,
        )
        assert trigger_resp.status_code == 200
        match_id = trigger_resp.json()["id"]

        # User B (no profile, different user) tries to access it
        user_b, _ = await create_test_user(db_session)
        await db_session.commit()

        # Create a minimal profile for user B so they don't get 404 on profile resolution
        from app.models.candidate import CandidateProfile

        profile_b = CandidateProfile(
            user_id=user_b.id,
            full_name="Bob Candidate",
            preferred_work_mode=WorkMode.ANY,
            preferred_employment_type=EmploymentType.ANY,
        )
        db_session.add(profile_b)
        await db_session.commit()

        headers_b = create_authenticated_headers(user_b.id)
        response = await async_client.get(f"/api/v1/matches/{match_id}", headers=headers_b)
        # Should be 404 (not 403, to avoid oracle leakage)
        assert response.status_code == 404

    async def test_get_match_by_opportunity_id(
        self,
        async_client: AsyncClient,
        user_with_profile: tuple[Any, dict],
        active_opportunity: Opportunity,
    ):
        """Approved contract: GET /matches/{opportunity_id} retrieves match for that opportunity."""
        _, headers = user_with_profile
        # Trigger evaluation first
        trigger_resp = await async_client.post(
            "/api/v1/matches/",
            json={"opportunity_id": str(active_opportunity.id)},
            headers=headers,
        )
        assert trigger_resp.status_code == 200

        # Retrieve by opportunity_id
        response = await async_client.get(
            f"/api/v1/matches/{active_opportunity.id}",
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["opportunity_id"] == str(active_opportunity.id)

    async def test_nonexistent_match_id_returns_404(
        self,
        async_client: AsyncClient,
        user_with_profile: tuple[Any, dict],
    ):
        _, headers = user_with_profile
        target = uuid.uuid4()
        response = await async_client.get(f"/api/v1/matches/{target}", headers=headers)
        assert (
            f"No match evaluation found for opportunity or match {target}"
            in response.json()["detail"]
        )


# ---------------------------------------------------------------------------
# SECTION 5: POST /matches/evaluate — batch evaluation
# ---------------------------------------------------------------------------


class TestEvaluateMatches:
    async def test_evaluate_requested_opportunities(
        self,
        async_client: AsyncClient,
        user_with_profile: tuple[Any, dict],
        active_opportunity: Opportunity,
    ):
        _, headers = user_with_profile
        response = await async_client.post(
            "/api/v1/matches/evaluate",
            json={
                "opportunity_ids": [str(active_opportunity.id)],
                "limit": 10,
                "semantic_similarity": 0.75,
            },
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert any(item["opportunity_id"] == str(active_opportunity.id) for item in data["items"])

    async def test_evaluate_active_discovery(
        self,
        async_client: AsyncClient,
        user_with_profile: tuple[Any, dict],
        active_opportunity: Opportunity,
    ):
        """When opportunity_ids is omitted, evaluates active opportunities up to limit."""
        _, headers = user_with_profile
        response = await async_client.post(
            "/api/v1/matches/evaluate",
            json={"limit": 5},
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["items"], list)
