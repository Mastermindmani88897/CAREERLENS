"""
Phase 17 Semantic Retrieval Test Suite.
Tests:
1. Authenticated retrieval with valid embeddings.
2. Correct ordering using controlled known vectors.
3. Correct raw cosine similarity values ([-1.0, 1.0], no artificial clamping to 0).
4. Empty eligible opportunity dataset.
5. Missing candidate profile (HTTP 404).
6. Candidate with insufficient professional content (HTTP 400).
7. Missing candidate embedding (on-demand generation).
8. Stale candidate embedding (on-demand regeneration upon child modification).
9. Failed regeneration when no valid prior vector exists (HTTP 400).
10. Failed regeneration when prior valid vector exists (preservation fallback, HTTP 200).
11. NULL opportunity embeddings excluded.
12. Inactive opportunities excluded.
13. Deterministic tie-breaking.
14. Pagination and maximum page-size boundaries.
15. JOB, INTERNSHIP, and HACKATHON filters.
16. Work-mode, employment-type, and location filters.
17. Cross-user isolation.
18. Unauthenticated access rejected (HTTP 401).
19. Vector fields absent from API responses.
20. Invalid filters rejected (HTTP 422).
21. Opportunity-discovery API regression test (/api/v1/opportunities/).
22. Embedding service rejection of empty text before inference.
"""

import uuid
from datetime import UTC, date, datetime, timedelta
from unittest.mock import patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate import CandidateProfile, Skill
from app.models.enums import (
    EmploymentType,
    OpportunitySource,
    OpportunityType,
    SkillProficiency,
    SkillSource,
    WorkMode,
)
from app.models.opportunity import Opportunity
from app.models.user import User
from app.services.embeddings import generate_candidate_profile_embedding
from tests.helpers.auth import create_authenticated_headers, create_test_user


def make_unit_vector(index: int, dimension: int = 384, sign: float = 1.0) -> list[float]:
    """Generate a 384-dimensional unit vector with sign at the specified index."""
    vec = [0.0] * dimension
    vec[index] = sign
    return vec


def fresh_timestamp() -> datetime:
    """Return a timestamp slightly in future to prevent microsecond commit staleness."""
    return datetime.now(UTC) + timedelta(minutes=5)


# -----------------------------------------------------------------------------
# 1. AUTHENTICATED RETRIEVAL WITH VALID EMBEDDINGS
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_authenticated_retrieval_success(
    async_client: AsyncClient,
    db_session: AsyncSession,
    authenticated_user: tuple[User, str],
    auth_headers: dict[str, str],
) -> None:
    """Authenticated candidate with valid embedding retrieves active opportunities."""
    user, _ = authenticated_user
    vec_candidate = make_unit_vector(0)
    loc_city = f"AuthCity_{uuid.uuid4().hex[:6]}"

    profile = CandidateProfile(
        user_id=user.id,
        full_name="Alex Rivera",
        headline="Senior Systems Architect",
        summary="Expert in distributed systems and cloud infrastructure.",
        profile_embedding=vec_candidate,
        embedding_updated_at=fresh_timestamp(),
    )
    db_session.add(profile)

    opp = Opportunity(
        title="Distributed Systems Lead",
        company="Apex Cloud",
        description="Lead large-scale backend infrastructure.",
        opportunity_type=OpportunityType.JOB,
        employment_type=EmploymentType.FULLTIME,
        work_mode=WorkMode.REMOTE,
        location_city=loc_city,
        source=OpportunitySource.MANUAL,
        is_active=True,
        job_embedding=vec_candidate,
        embedding_updated_at=fresh_timestamp(),
    )
    db_session.add(opp)
    await db_session.commit()

    response = await async_client.get(
        f"/api/v1/recommendations/?location={loc_city}",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    item = data["items"][0]
    assert item["title"] == "Distributed Systems Lead"
    assert "semantic_similarity" in item
    assert item["semantic_similarity"] == pytest.approx(1.0, abs=1e-3)


# -----------------------------------------------------------------------------
# 2. CONTROLLED VECTOR RANKING ORDER & 3. RAW SIMILARITY VALUES ([-1, 1])
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_controlled_vector_ordering_and_raw_similarity_range(
    async_client: AsyncClient,
    db_session: AsyncSession,
    authenticated_user: tuple[User, str],
    auth_headers: dict[str, str],
) -> None:
    """
    Test controlled vectors produce exact raw cosine similarity without 0-clamping:
    - Opp A: identical vector -> raw similarity = 1.0
    - Opp B: orthogonal vector -> raw similarity = 0.0
    - Opp C: opposite vector -> raw similarity = -1.0
    """
    user, _ = authenticated_user
    vec_cand = make_unit_vector(0)
    loc_city = f"VectorCity_{uuid.uuid4().hex[:6]}"

    profile = CandidateProfile(
        user_id=user.id,
        full_name="Vector Tester",
        headline="Vector Math Evaluator",
        summary="Evaluation of pgvector cosine similarity correctness.",
        profile_embedding=vec_cand,
        embedding_updated_at=fresh_timestamp(),
    )
    db_session.add(profile)

    opp_identical = Opportunity(
        title="Identical Vector Job",
        company="MatchCorp",
        description="Identical alignment.",
        opportunity_type=OpportunityType.JOB,
        employment_type=EmploymentType.FULLTIME,
        work_mode=WorkMode.REMOTE,
        location_city=loc_city,
        source=OpportunitySource.MANUAL,
        is_active=True,
        job_embedding=make_unit_vector(0, sign=1.0),
        embedding_updated_at=fresh_timestamp(),
    )
    opp_orthogonal = Opportunity(
        title="Orthogonal Vector Job",
        company="NeutralCorp",
        description="Orthogonal alignment.",
        opportunity_type=OpportunityType.JOB,
        employment_type=EmploymentType.FULLTIME,
        work_mode=WorkMode.REMOTE,
        location_city=loc_city,
        source=OpportunitySource.MANUAL,
        is_active=True,
        job_embedding=make_unit_vector(1, sign=1.0),
        embedding_updated_at=fresh_timestamp(),
    )
    opp_opposite = Opportunity(
        title="Opposite Vector Job",
        company="InverseCorp",
        description="Opposite alignment.",
        opportunity_type=OpportunityType.JOB,
        employment_type=EmploymentType.FULLTIME,
        work_mode=WorkMode.REMOTE,
        location_city=loc_city,
        source=OpportunitySource.MANUAL,
        is_active=True,
        job_embedding=make_unit_vector(0, sign=-1.0),
        embedding_updated_at=fresh_timestamp(),
    )
    db_session.add_all([opp_identical, opp_orthogonal, opp_opposite])
    await db_session.commit()

    response = await async_client.get(
        f"/api/v1/recommendations/?location={loc_city}&page_size=10",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 3
    titles = [item["title"] for item in data["items"]]

    # Verify descending semantic order: identical (1.0) -> orthogonal (0.0) -> opposite (-1.0)
    assert titles == [
        "Identical Vector Job",
        "Orthogonal Vector Job",
        "Opposite Vector Job",
    ]

    # Verify exact raw cosine similarities across full [-1.0, 1.0] range
    scores = {item["title"]: item["semantic_similarity"] for item in data["items"]}
    assert scores["Identical Vector Job"] == pytest.approx(1.0, abs=1e-3)
    assert scores["Orthogonal Vector Job"] == pytest.approx(0.0, abs=1e-3)
    assert scores["Opposite Vector Job"] == pytest.approx(-1.0, abs=1e-3)


# -----------------------------------------------------------------------------
# 4. EMPTY ELIGIBLE OPPORTUNITY DATASET
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_empty_opportunity_dataset_returns_empty_list(
    async_client: AsyncClient,
    db_session: AsyncSession,
    authenticated_user: tuple[User, str],
    auth_headers: dict[str, str],
) -> None:
    """When no eligible opportunities exist, returns HTTP 200 with items=[] and total=0."""
    user, _ = authenticated_user
    profile = CandidateProfile(
        user_id=user.id,
        full_name="Lone Candidate",
        headline="Software Engineer",
        summary="Looking for opportunities.",
        profile_embedding=make_unit_vector(5),
        embedding_updated_at=fresh_timestamp(),
    )
    db_session.add(profile)
    await db_session.commit()

    response = await async_client.get(
        "/api/v1/recommendations/?location=NonexistentCityXYZ123",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["total_pages"] == 0
    assert data["page"] == 1


# -----------------------------------------------------------------------------
# 5. MISSING CANDIDATE PROFILE
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_missing_candidate_profile_returns_404(
    async_client: AsyncClient,
    authenticated_user: tuple[User, str],
    auth_headers: dict[str, str],
) -> None:
    """User without a CandidateProfile receives HTTP 404 with an actionable message."""
    response = await async_client.get("/api/v1/recommendations/", headers=auth_headers)
    assert response.status_code == 404
    detail = response.json()["detail"]
    assert "Candidate profile not found" in detail


# -----------------------------------------------------------------------------
# 6. INSUFFICIENT PROFESSIONAL CONTENT
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_insufficient_professional_content_returns_400(
    async_client: AsyncClient,
    db_session: AsyncSession,
    authenticated_user: tuple[User, str],
    auth_headers: dict[str, str],
) -> None:
    """Candidate with only full_name and no professional data receives HTTP 400."""
    user, _ = authenticated_user
    profile = CandidateProfile(
        user_id=user.id,
        full_name="Empty Profile Candidate",
        headline=None,
        summary=None,
        profile_embedding=None,
        embedding_updated_at=None,
    )
    db_session.add(profile)
    await db_session.commit()

    response = await async_client.get("/api/v1/recommendations/", headers=auth_headers)
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert "insufficient content" in detail.lower()


# -----------------------------------------------------------------------------
# 7. MISSING CANDIDATE EMBEDDING (ON-DEMAND GENERATION)
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_missing_candidate_embedding_regenerates_on_demand(
    async_client: AsyncClient,
    db_session: AsyncSession,
    authenticated_user: tuple[User, str],
    auth_headers: dict[str, str],
) -> None:
    """Candidate with valid content but NULL embedding triggers on-demand generation."""
    user, _ = authenticated_user
    loc_city = f"GenerateCity_{uuid.uuid4().hex[:6]}"

    profile = CandidateProfile(
        user_id=user.id,
        full_name="Python Specialist",
        headline="Python Backend Developer",
        summary="Specializing in FastAPI, SQLAlchemy, and PostgreSQL architectures.",
        profile_embedding=None,
        embedding_updated_at=None,
    )
    db_session.add(profile)
    await db_session.commit()

    opp = Opportunity(
        title="FastAPI Engineer",
        company="ModernWeb",
        description="Build async APIs with Python and PostgreSQL.",
        opportunity_type=OpportunityType.JOB,
        employment_type=EmploymentType.FULLTIME,
        work_mode=WorkMode.REMOTE,
        location_city=loc_city,
        source=OpportunitySource.MANUAL,
        is_active=True,
        job_embedding=make_unit_vector(0),
        embedding_updated_at=fresh_timestamp(),
    )
    db_session.add(opp)
    await db_session.commit()

    response = await async_client.get(
        f"/api/v1/recommendations/?location={loc_city}",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1

    # Verify profile now has a persisted embedding in DB
    await db_session.refresh(profile)
    assert profile.profile_embedding is not None
    assert len(profile.profile_embedding) == 384


# -----------------------------------------------------------------------------
# 8. STALE CANDIDATE EMBEDDING (ON-DEMAND REGENERATION)
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stale_candidate_embedding_triggers_regeneration(
    async_client: AsyncClient,
    db_session: AsyncSession,
    authenticated_user: tuple[User, str],
    auth_headers: dict[str, str],
) -> None:
    """Candidate profile with stale embedding (new skill added) updates before query."""
    user, _ = authenticated_user
    old_vector = make_unit_vector(10)
    old_time = datetime(2025, 1, 1, tzinfo=UTC)
    loc_city = f"StaleCity_{uuid.uuid4().hex[:6]}"

    profile = CandidateProfile(
        user_id=user.id,
        full_name="Stale Candidate",
        headline="Backend Engineer",
        summary="Working on backend systems.",
        profile_embedding=old_vector,
        embedding_updated_at=old_time,
    )
    db_session.add(profile)
    await db_session.commit()

    # Add new skill with recent timestamp (stale trigger)
    skill = Skill(
        candidate_profile_id=profile.id,
        skill_name="Kubernetes",
        proficiency_level=SkillProficiency.EXPERT,
        source=SkillSource.MANUAL,
        created_at=datetime.now(UTC),
    )
    db_session.add(skill)
    await db_session.commit()

    opp = Opportunity(
        title="DevOps Architect",
        company="KubeCorp",
        description="Kubernetes orchestration.",
        opportunity_type=OpportunityType.JOB,
        employment_type=EmploymentType.FULLTIME,
        work_mode=WorkMode.REMOTE,
        location_city=loc_city,
        source=OpportunitySource.MANUAL,
        is_active=True,
        job_embedding=make_unit_vector(0),
        embedding_updated_at=fresh_timestamp(),
    )
    db_session.add(opp)
    await db_session.commit()

    response = await async_client.get(
        f"/api/v1/recommendations/?location={loc_city}",
        headers=auth_headers,
    )
    assert response.status_code == 200

    # Verify embedding updated past old_time
    await db_session.refresh(profile)
    assert profile.embedding_updated_at > old_time


# -----------------------------------------------------------------------------
# 9. FAILED REGENERATION WHEN NO VALID PRIOR VECTOR EXISTS
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_failed_regeneration_no_prior_vector_returns_400(
    async_client: AsyncClient,
    db_session: AsyncSession,
    authenticated_user: tuple[User, str],
    auth_headers: dict[str, str],
) -> None:
    """If generation fails and candidate has no prior vector, returns HTTP 400."""
    user, _ = authenticated_user
    profile = CandidateProfile(
        user_id=user.id,
        full_name="Broken Model Candidate",
        headline="AI Engineer",
        summary="Researching algorithms.",
        profile_embedding=None,
        embedding_updated_at=None,
    )
    db_session.add(profile)
    await db_session.commit()

    with patch(
        "app.services.recommendation_service.generate_candidate_profile_embedding",
        return_value=None,
    ):
        response = await async_client.get("/api/v1/recommendations/", headers=auth_headers)
        assert response.status_code == 400
        detail = response.json()["detail"]
        assert "embedding could not be generated" in detail.lower()


# -----------------------------------------------------------------------------
# 10. FAILED REGENERATION WHEN PRIOR VALID VECTOR EXISTS (PRESERVATION)
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_failed_regeneration_preserves_prior_valid_vector(
    async_client: AsyncClient,
    db_session: AsyncSession,
    authenticated_user: tuple[User, str],
    auth_headers: dict[str, str],
) -> None:
    """If stale regeneration fails, existing vector is safely preserved and used."""
    user, _ = authenticated_user
    valid_prior_vector = make_unit_vector(2)
    old_time = datetime(2025, 1, 1, tzinfo=UTC)
    loc_city = f"PreserveCity_{uuid.uuid4().hex[:6]}"

    profile = CandidateProfile(
        user_id=user.id,
        full_name="Preserved Candidate",
        headline="Software Engineer",
        summary="Maintaining systems.",
        profile_embedding=valid_prior_vector,
        embedding_updated_at=old_time,
    )
    db_session.add(profile)

    opp = Opportunity(
        title="Preserved Opportunity",
        company="StableTech",
        description="Stable infrastructure.",
        opportunity_type=OpportunityType.JOB,
        employment_type=EmploymentType.FULLTIME,
        work_mode=WorkMode.REMOTE,
        location_city=loc_city,
        source=OpportunitySource.MANUAL,
        is_active=True,
        job_embedding=valid_prior_vector,
        embedding_updated_at=fresh_timestamp(),
    )
    db_session.add(opp)
    await db_session.commit()

    # Simulate generation failure while profile is stale
    with patch(
        "app.services.recommendation_service.generate_candidate_profile_embedding",
        return_value=None,
    ):
        response = await async_client.get(
            f"/api/v1/recommendations/?location={loc_city}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["semantic_similarity"] == pytest.approx(1.0, abs=1e-3)


# -----------------------------------------------------------------------------
# 11. NULL OPPORTUNITY EMBEDDINGS EXCLUDED
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_null_opportunity_embeddings_excluded(
    async_client: AsyncClient,
    db_session: AsyncSession,
    authenticated_user: tuple[User, str],
    auth_headers: dict[str, str],
) -> None:
    """Opportunities with NULL job_embedding are strictly excluded."""
    user, _ = authenticated_user
    loc_city = f"NullExcludeCity_{uuid.uuid4().hex[:6]}"

    profile = CandidateProfile(
        user_id=user.id,
        full_name="Filter Candidate",
        headline="Full Stack Developer",
        summary="Full stack applications.",
        profile_embedding=make_unit_vector(3),
        embedding_updated_at=fresh_timestamp(),
    )
    db_session.add(profile)

    opp_embedded = Opportunity(
        title="Embedded Job",
        company="VectorCorp",
        description="Has vector.",
        opportunity_type=OpportunityType.JOB,
        employment_type=EmploymentType.FULLTIME,
        work_mode=WorkMode.REMOTE,
        location_city=loc_city,
        source=OpportunitySource.MANUAL,
        is_active=True,
        job_embedding=make_unit_vector(3),
        embedding_updated_at=fresh_timestamp(),
    )
    opp_null_vector = Opportunity(
        title="Unembedded Job",
        company="NoVectorCorp",
        description="Missing vector.",
        opportunity_type=OpportunityType.JOB,
        employment_type=EmploymentType.FULLTIME,
        work_mode=WorkMode.REMOTE,
        location_city=loc_city,
        source=OpportunitySource.MANUAL,
        is_active=True,
        job_embedding=None,
        embedding_updated_at=None,
    )
    db_session.add_all([opp_embedded, opp_null_vector])
    await db_session.commit()

    response = await async_client.get(
        f"/api/v1/recommendations/?location={loc_city}",
        headers=auth_headers,
    )
    assert response.status_code == 200
    titles = [item["title"] for item in response.json()["items"]]
    assert "Embedded Job" in titles
    assert "Unembedded Job" not in titles


# -----------------------------------------------------------------------------
# 12. INACTIVE OPPORTUNITIES EXCLUDED
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_inactive_opportunities_excluded(
    async_client: AsyncClient,
    db_session: AsyncSession,
    authenticated_user: tuple[User, str],
    auth_headers: dict[str, str],
) -> None:
    """Inactive opportunities (is_active=False) are never returned."""
    user, _ = authenticated_user
    vec = make_unit_vector(4)
    loc_city = f"ActiveCity_{uuid.uuid4().hex[:6]}"

    profile = CandidateProfile(
        user_id=user.id,
        full_name="Active Filter Tester",
        headline="Engineer",
        summary="Active matching only.",
        profile_embedding=vec,
        embedding_updated_at=fresh_timestamp(),
    )
    db_session.add(profile)

    opp_active = Opportunity(
        title="Active Listing Visible",
        company="OpenCorp",
        description="Active position.",
        opportunity_type=OpportunityType.JOB,
        employment_type=EmploymentType.FULLTIME,
        work_mode=WorkMode.REMOTE,
        location_city=loc_city,
        source=OpportunitySource.MANUAL,
        is_active=True,
        job_embedding=vec,
        embedding_updated_at=fresh_timestamp(),
    )
    opp_inactive = Opportunity(
        title="Inactive Listing Hidden",
        company="ClosedCorp",
        description="Closed position.",
        opportunity_type=OpportunityType.JOB,
        employment_type=EmploymentType.FULLTIME,
        work_mode=WorkMode.REMOTE,
        location_city=loc_city,
        source=OpportunitySource.MANUAL,
        is_active=False,
        job_embedding=vec,
        embedding_updated_at=fresh_timestamp(),
    )
    db_session.add_all([opp_active, opp_inactive])
    await db_session.commit()

    response = await async_client.get(
        f"/api/v1/recommendations/?location={loc_city}",
        headers=auth_headers,
    )
    assert response.status_code == 200
    titles = [item["title"] for item in response.json()["items"]]
    assert "Active Listing Visible" in titles
    assert "Inactive Listing Hidden" not in titles


# -----------------------------------------------------------------------------
# 13. DETERMINISTIC TIE-BREAKING
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_deterministic_tie_breaking(
    async_client: AsyncClient,
    db_session: AsyncSession,
    authenticated_user: tuple[User, str],
    auth_headers: dict[str, str],
) -> None:
    """
    Identical vectors break ties deterministically:
    posted_date DESC -> created_at DESC -> id ASC.
    """
    user, _ = authenticated_user
    shared_vec = make_unit_vector(5)
    loc_city = f"TieCity_{uuid.uuid4().hex[:6]}"

    profile = CandidateProfile(
        user_id=user.id,
        full_name="Tie Break Tester",
        headline="Evaluation Lead",
        summary="Testing sorting stability.",
        profile_embedding=shared_vec,
        embedding_updated_at=fresh_timestamp(),
    )
    db_session.add(profile)

    # Opportunity 1: Newer posted_date (2026-10-10)
    opp_newer = Opportunity(
        title="Newer Posted Tie",
        company="TieCorp A",
        description="Same vector, newer posted_date.",
        opportunity_type=OpportunityType.JOB,
        employment_type=EmploymentType.FULLTIME,
        work_mode=WorkMode.REMOTE,
        location_city=loc_city,
        source=OpportunitySource.MANUAL,
        posted_date=date(2026, 10, 10),
        is_active=True,
        job_embedding=shared_vec,
        embedding_updated_at=fresh_timestamp(),
    )
    # Opportunity 2: Older posted_date (2026-10-01)
    opp_older = Opportunity(
        title="Older Posted Tie",
        company="TieCorp B",
        description="Same vector, older posted_date.",
        opportunity_type=OpportunityType.JOB,
        employment_type=EmploymentType.FULLTIME,
        work_mode=WorkMode.REMOTE,
        location_city=loc_city,
        source=OpportunitySource.MANUAL,
        posted_date=date(2026, 10, 1),
        is_active=True,
        job_embedding=shared_vec,
        embedding_updated_at=fresh_timestamp(),
    )
    db_session.add_all([opp_older, opp_newer])
    await db_session.commit()

    response = await async_client.get(
        f"/api/v1/recommendations/?location={loc_city}",
        headers=auth_headers,
    )
    assert response.status_code == 200
    titles = [item["title"] for item in response.json()["items"]]
    assert len(titles) == 2
    assert titles == ["Newer Posted Tie", "Older Posted Tie"]


# -----------------------------------------------------------------------------
# 14. PAGINATION AND MAXIMUM PAGE-SIZE BOUNDARIES
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pagination_and_bounds_validation(
    async_client: AsyncClient,
    db_session: AsyncSession,
    authenticated_user: tuple[User, str],
    auth_headers: dict[str, str],
) -> None:
    """Validates offset/limit pagination and rejects invalid bounds (page=0, page_size=101)."""
    user, _ = authenticated_user
    vec = make_unit_vector(6)
    loc_city = f"PagingCity_{uuid.uuid4().hex[:6]}"

    profile = CandidateProfile(
        user_id=user.id,
        full_name="Paging Tester",
        headline="Paging Lead",
        summary="Validating pagination bounds.",
        profile_embedding=vec,
        embedding_updated_at=fresh_timestamp(),
    )
    db_session.add(profile)

    # Insert 5 opportunities
    for i in range(5):
        opp = Opportunity(
            title=f"Page Job {i}",
            company=f"Company {i}",
            description="Pagination item.",
            opportunity_type=OpportunityType.JOB,
            employment_type=EmploymentType.FULLTIME,
            work_mode=WorkMode.REMOTE,
            location_city=loc_city,
            source=OpportunitySource.MANUAL,
            is_active=True,
            job_embedding=vec,
            embedding_updated_at=fresh_timestamp(),
        )
        db_session.add(opp)
    await db_session.commit()

    # Page 1 with page_size=2
    res_p1 = await async_client.get(
        f"/api/v1/recommendations/?location={loc_city}&page=1&page_size=2",
        headers=auth_headers,
    )
    assert res_p1.status_code == 200
    data_p1 = res_p1.json()
    assert len(data_p1["items"]) == 2
    assert data_p1["page"] == 1
    assert data_p1["page_size"] == 2
    assert data_p1["total"] == 5
    assert data_p1["total_pages"] == 3

    # Page 2 with page_size=2
    res_p2 = await async_client.get(
        f"/api/v1/recommendations/?location={loc_city}&page=2&page_size=2",
        headers=auth_headers,
    )
    assert res_p2.status_code == 200
    data_p2 = res_p2.json()
    assert len(data_p2["items"]) == 2
    assert data_p2["page"] == 2

    # Reject page_size = 0
    res_zero = await async_client.get("/api/v1/recommendations/?page_size=0", headers=auth_headers)
    assert res_zero.status_code == 422

    # Reject page_size = 101 (> 100 limit)
    res_over = await async_client.get(
        "/api/v1/recommendations/?page_size=101",
        headers=auth_headers,
    )
    assert res_over.status_code == 422


# -----------------------------------------------------------------------------
# 15. OPPORTUNITY TYPE FILTERS (JOB, INTERNSHIP, HACKATHON)
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_opportunity_type_filters(
    async_client: AsyncClient,
    db_session: AsyncSession,
    authenticated_user: tuple[User, str],
    auth_headers: dict[str, str],
) -> None:
    """Filtering by opportunity_type returns matching items without changing score."""
    user, _ = authenticated_user
    vec = make_unit_vector(7)
    loc_city = f"TypeCity_{uuid.uuid4().hex[:6]}"

    profile = CandidateProfile(
        user_id=user.id,
        full_name="Type Tester",
        headline="Student & Engineer",
        summary="Participates in jobs and hackathons.",
        profile_embedding=vec,
        embedding_updated_at=fresh_timestamp(),
    )
    db_session.add(profile)

    opp_job = Opportunity(
        title="Fulltime Role",
        company="JobCorp",
        description="Fulltime job.",
        opportunity_type=OpportunityType.JOB,
        employment_type=EmploymentType.FULLTIME,
        work_mode=WorkMode.REMOTE,
        location_city=loc_city,
        source=OpportunitySource.MANUAL,
        is_active=True,
        job_embedding=vec,
        embedding_updated_at=fresh_timestamp(),
    )
    opp_intern = Opportunity(
        title="Summer Internship",
        company="InternCorp",
        description="Internship role.",
        opportunity_type=OpportunityType.INTERNSHIP,
        employment_type=EmploymentType.INTERNSHIP,
        work_mode=WorkMode.REMOTE,
        location_city=loc_city,
        source=OpportunitySource.MANUAL,
        is_active=True,
        job_embedding=vec,
        embedding_updated_at=fresh_timestamp(),
    )
    opp_hack = Opportunity(
        title="AI Hackathon 2026",
        company="HackCorp",
        description="48-hour build sprint.",
        opportunity_type=OpportunityType.HACKATHON,
        employment_type=EmploymentType.CONTRACT,
        work_mode=WorkMode.REMOTE,
        location_city=loc_city,
        source=OpportunitySource.MANUAL,
        is_active=True,
        job_embedding=vec,
        embedding_updated_at=fresh_timestamp(),
    )
    db_session.add_all([opp_job, opp_intern, opp_hack])
    await db_session.commit()

    # Filter for internship only
    res = await async_client.get(
        f"/api/v1/recommendations/?location={loc_city}&opportunity_type=internship",
        headers=auth_headers,
    )
    assert res.status_code == 200
    items = res.json()["items"]
    assert len(items) == 1
    assert items[0]["title"] == "Summer Internship"

    # Filter for hackathon only
    res_hack = await async_client.get(
        f"/api/v1/recommendations/?location={loc_city}&opportunity_type=hackathon",
        headers=auth_headers,
    )
    assert res_hack.status_code == 200
    items_hack = res_hack.json()["items"]
    assert len(items_hack) == 1
    assert items_hack[0]["title"] == "AI Hackathon 2026"


# -----------------------------------------------------------------------------
# 16. WORK-MODE, EMPLOYMENT-TYPE, AND LOCATION FILTERS
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_work_mode_employment_type_and_location_filters(
    async_client: AsyncClient,
    db_session: AsyncSession,
    authenticated_user: tuple[User, str],
    auth_headers: dict[str, str],
) -> None:
    """Validates work_mode, employment_type, and location substring filters."""
    user, _ = authenticated_user
    vec = make_unit_vector(8)
    loc_unique = f"FilterCity_{uuid.uuid4().hex[:6]}"

    profile = CandidateProfile(
        user_id=user.id,
        full_name="Filter Evaluator",
        headline="Remote Specialist",
        summary="Remote contracts.",
        profile_embedding=vec,
        embedding_updated_at=fresh_timestamp(),
    )
    db_session.add(profile)

    opp_target = Opportunity(
        title="Remote Contract Target",
        company="TargetCorp",
        description="Target contract.",
        opportunity_type=OpportunityType.JOB,
        employment_type=EmploymentType.CONTRACT,
        work_mode=WorkMode.REMOTE,
        location_city=loc_unique,
        location_country="India",
        source=OpportunitySource.MANUAL,
        is_active=True,
        job_embedding=vec,
        embedding_updated_at=fresh_timestamp(),
    )
    opp_other = Opportunity(
        title="Onsite Fulltime Other",
        company="OtherCorp",
        description="Other position.",
        opportunity_type=OpportunityType.JOB,
        employment_type=EmploymentType.FULLTIME,
        work_mode=WorkMode.ONSITE,
        location_city=loc_unique,
        location_country="India",
        source=OpportunitySource.MANUAL,
        is_active=True,
        job_embedding=vec,
        embedding_updated_at=fresh_timestamp(),
    )
    db_session.add_all([opp_target, opp_other])
    await db_session.commit()

    res = await async_client.get(
        f"/api/v1/recommendations/?work_mode=remote&employment_type=contract&location={loc_unique}",
        headers=auth_headers,
    )
    assert res.status_code == 200
    items = res.json()["items"]
    assert len(items) == 1
    assert items[0]["title"] == "Remote Contract Target"


# -----------------------------------------------------------------------------
# 17. CROSS-USER ISOLATION
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cross_user_isolation(
    async_client: AsyncClient,
    db_session: AsyncSession,
    authenticated_user: tuple[User, str],
) -> None:
    """User A and User B receive recommendations tailored to their distinct profiles."""
    user_a, _ = authenticated_user
    user_b, _ = await create_test_user(db_session)
    await db_session.commit()

    headers_a = create_authenticated_headers(user_a.id)
    headers_b = create_authenticated_headers(user_b.id)
    loc_city = f"IsolationCity_{uuid.uuid4().hex[:6]}"

    # User A aligned with index 0 (Python backend)
    # User B aligned with index 1 (React frontend)
    profile_a = CandidateProfile(
        user_id=user_a.id,
        full_name="User Alpha",
        headline="Python Backend Engineer",
        summary="Backend architecture.",
        profile_embedding=make_unit_vector(0),
        embedding_updated_at=fresh_timestamp(),
    )
    profile_b = CandidateProfile(
        user_id=user_b.id,
        full_name="User Beta",
        headline="React Frontend Specialist",
        summary="Frontend UI architecture.",
        profile_embedding=make_unit_vector(1),
        embedding_updated_at=fresh_timestamp(),
    )
    db_session.add_all([profile_a, profile_b])

    opp_py = Opportunity(
        title="Python Backend Job",
        company="PyCorp",
        description="Python development.",
        opportunity_type=OpportunityType.JOB,
        employment_type=EmploymentType.FULLTIME,
        work_mode=WorkMode.REMOTE,
        location_city=loc_city,
        source=OpportunitySource.MANUAL,
        is_active=True,
        job_embedding=make_unit_vector(0),
        embedding_updated_at=fresh_timestamp(),
    )
    opp_react = Opportunity(
        title="React Frontend Job",
        company="ReactCorp",
        description="React UI development.",
        opportunity_type=OpportunityType.JOB,
        employment_type=EmploymentType.FULLTIME,
        work_mode=WorkMode.REMOTE,
        location_city=loc_city,
        source=OpportunitySource.MANUAL,
        is_active=True,
        job_embedding=make_unit_vector(1),
        embedding_updated_at=fresh_timestamp(),
    )
    db_session.add_all([opp_py, opp_react])
    await db_session.commit()

    # User A query
    res_a = await async_client.get(
        f"/api/v1/recommendations/?location={loc_city}",
        headers=headers_a,
    )
    assert res_a.status_code == 200
    items_a = res_a.json()["items"]
    assert items_a[0]["title"] == "Python Backend Job"
    assert items_a[0]["semantic_similarity"] == pytest.approx(1.0, abs=1e-3)

    # User B query
    res_b = await async_client.get(
        f"/api/v1/recommendations/?location={loc_city}",
        headers=headers_b,
    )
    assert res_b.status_code == 200
    items_b = res_b.json()["items"]
    assert items_b[0]["title"] == "React Frontend Job"
    assert items_b[0]["semantic_similarity"] == pytest.approx(1.0, abs=1e-3)


# -----------------------------------------------------------------------------
# 18. UNAUTHENTICATED ACCESS REJECTED (HTTP 401)
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unauthenticated_request_rejected(async_client: AsyncClient) -> None:
    """Accessing recommendations without authentication header returns HTTP 401."""
    response = await async_client.get("/api/v1/recommendations/")
    assert response.status_code == 401


# -----------------------------------------------------------------------------
# 19. VECTOR FIELDS ABSENT FROM API RESPONSES
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_vector_fields_absent_from_api_responses(
    async_client: AsyncClient,
    db_session: AsyncSession,
    authenticated_user: tuple[User, str],
    auth_headers: dict[str, str],
) -> None:
    """Verifies response JSON never contains raw vectors or internal timestamps."""
    user, _ = authenticated_user
    vec = make_unit_vector(9)
    loc_city = f"PrivacyCity_{uuid.uuid4().hex[:6]}"

    profile = CandidateProfile(
        user_id=user.id,
        full_name="Privacy Tester",
        headline="Privacy Advocate",
        summary="Checking vector leakage.",
        profile_embedding=vec,
        embedding_updated_at=fresh_timestamp(),
    )
    db_session.add(profile)

    opp = Opportunity(
        title="Privacy Job",
        company="SecureCorp",
        description="Secure positions.",
        opportunity_type=OpportunityType.JOB,
        employment_type=EmploymentType.FULLTIME,
        work_mode=WorkMode.REMOTE,
        location_city=loc_city,
        source=OpportunitySource.MANUAL,
        is_active=True,
        job_embedding=vec,
        embedding_updated_at=fresh_timestamp(),
    )
    db_session.add(opp)
    await db_session.commit()

    response = await async_client.get(
        f"/api/v1/recommendations/?location={loc_city}",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) >= 1
    item = data["items"][0]

    assert "job_embedding" not in item
    assert "profile_embedding" not in item
    assert "embedding_updated_at" not in item


# -----------------------------------------------------------------------------
# 20. INVALID FILTERS REJECTED (HTTP 422)
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_invalid_filter_parameters_rejected(
    async_client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """Invalid enum values or out-of-bounds parameters return HTTP 422."""
    # Invalid opportunity_type enum
    res1 = await async_client.get(
        "/api/v1/recommendations/?opportunity_type=invalid_type",
        headers=auth_headers,
    )
    assert res1.status_code == 422

    # Invalid work_mode enum
    res2 = await async_client.get(
        "/api/v1/recommendations/?work_mode=space_station",
        headers=auth_headers,
    )
    assert res2.status_code == 422

    # Negative page
    res3 = await async_client.get("/api/v1/recommendations/?page=0", headers=auth_headers)
    assert res3.status_code == 422


# -----------------------------------------------------------------------------
# 21. EXISTING DISCOVERY ENDPOINTS REGRESSION CHECK
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_existing_opportunity_discovery_unaffected(
    async_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Existing public discovery endpoint /api/v1/opportunities/ remains functional."""
    opp = Opportunity(
        title="Public Discovery Role",
        company="OpenSource Labs",
        description="Publicly discoverable.",
        opportunity_type=OpportunityType.JOB,
        employment_type=EmploymentType.FULLTIME,
        work_mode=WorkMode.REMOTE,
        source=OpportunitySource.MANUAL,
        is_active=True,
    )
    db_session.add(opp)
    await db_session.commit()

    response = await async_client.get("/api/v1/opportunities/")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert any(it["title"] == "Public Discovery Role" for it in data["items"])


# -----------------------------------------------------------------------------
# 22. EMPTY NORMALIZED TEXT REJECTION IN EMBEDDING SERVICE
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_empty_candidate_profile_rejected_before_model_inference(
    db_session: AsyncSession,
    authenticated_user: tuple[User, str],
) -> None:
    """Embedding service safely returns None for empty profile text without crashing."""
    user, _ = authenticated_user
    empty_profile = CandidateProfile(
        user_id=user.id,
        full_name="No Content Candidate",
        headline=None,
        summary=None,
        profile_embedding=None,
        embedding_updated_at=None,
    )
    db_session.add(empty_profile)
    await db_session.commit()

    result = await generate_candidate_profile_embedding(
        db_session,
        empty_profile.id,
        commit=True,
    )
    assert result is None
    await db_session.refresh(empty_profile)
    assert empty_profile.profile_embedding is None
