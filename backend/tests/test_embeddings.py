"""
Phase 16 Embedding Foundation Test Suite.
Tests:
- Embedding provider (model loading, dimension 384, CPU, input validation, batching)
- Deterministic text normalization (field inclusion, whitespace, strict PII exclusion)
- Candidate profile embedding lifecycle (generation, persistence, stale detection, sync)
- Opportunity embedding lifecycle (generation, persistence, batching, ingestion, failure)
- Security (vector exclusion from API response schemas, no public embedding endpoint)
"""

import uuid
from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate import (
    CandidateProfile,
    Certification,
    Education,
    Experience,
    Project,
    Resume,
    Skill,
)
from app.models.enums import (
    EducationLevel,
    EmploymentType,
    OpportunitySource,
    OpportunityType,
    SkillProficiency,
    SkillSource,
    WorkMode,
)
from app.models.opportunity import Opportunity, OpportunitySkill
from app.models.user import User
from app.schemas.candidate_profile import (
    CertificationCreate,
    EducationCreate,
    ExperienceCreate,
    ProfileCreate,
    ProfileDetailResponse,
    ProfileResponse,
    ProfileUpdate,
    ProjectCreate,
    SkillCreate,
)
from app.schemas.opportunity import OpportunityDetailResponse, OpportunityResponse
from app.services.embeddings.base import BaseEmbeddingProvider
from app.services.embeddings.embedding_service import (
    generate_candidate_profile_embedding,
    generate_opportunity_embedding,
    generate_opportunity_embeddings_batch,
    get_embedding_provider,
    is_candidate_embedding_stale,
    is_opportunity_embedding_stale,
    set_embedding_provider,
)
from app.services.embeddings.local_provider import LocalSentenceTransformersProvider
from app.services.embeddings.text_normalizer import (
    build_candidate_embedding_text,
    build_opportunity_embedding_text,
    normalize_whitespace,
)
from app.services.opportunity_ingest_service import ingest_raw_records
from app.services.profile_service import (
    add_certification,
    add_education,
    add_experience,
    add_project,
    add_skill,
    create_candidate_profile,
    update_candidate_profile,
)
from app.services.profile_sync_service import sync_profile_from_resume
from tests.factories.opportunity_factory import OpportunityFactory

# =============================================================================
# A. EMBEDDING PROVIDER TESTS
# =============================================================================


def test_provider_initialization_and_properties():
    """Verify provider instantiates with expected model name and 384 dimension."""
    provider = LocalSentenceTransformersProvider()
    assert provider.dimension == 384
    assert provider.model_name == "sentence-transformers/all-MiniLM-L6-v2"
    assert issubclass(LocalSentenceTransformersProvider, BaseEmbeddingProvider)


def test_provider_embed_text_dimension_and_determinism():
    """Verify single text embedding produces 384 float vector deterministically on CPU."""
    provider = LocalSentenceTransformersProvider()
    text = "Senior Python Backend Engineer with FastAPI and PostgreSQL expertise."
    vec1 = provider.embed_text(text)
    vec2 = provider.embed_text(text)

    assert isinstance(vec1, list)
    assert len(vec1) == 384
    assert all(isinstance(x, float) for x in vec1)
    # Deterministic output check
    assert vec1 == vec2


def test_provider_empty_and_whitespace_input():
    """Verify empty and whitespace inputs return a safe 384-dimensional zero vector."""
    provider = LocalSentenceTransformersProvider()
    empty_vec = provider.embed_text("")
    assert len(empty_vec) == 384
    assert all(x == 0.0 for x in empty_vec)

    ws_vec = provider.embed_text("   \n\t  ")
    assert len(ws_vec) == 384
    assert all(x == 0.0 for x in ws_vec)


def test_provider_invalid_type_raises_type_error():
    """Verify invalid input types raise TypeError."""
    provider = LocalSentenceTransformersProvider()
    with pytest.raises(TypeError):
        provider.embed_text(None)  # type: ignore

    with pytest.raises(TypeError):
        provider.embed_text(12345)  # type: ignore

    with pytest.raises(TypeError):
        provider.embed_batch("not a list")  # type: ignore

    with pytest.raises(TypeError):
        provider.embed_batch(["valid", 123])  # type: ignore


def test_provider_batch_embedding_consistency():
    """Verify batch embedding preserves order, handles empty batches, and matches single results."""
    provider = LocalSentenceTransformersProvider()

    # Empty batch returns empty list
    assert provider.embed_batch([]) == []

    texts = [
        "Machine Learning Engineer specializing in NLP",
        "React frontend architect with Tailwind CSS",
        "   ",  # whitespace element
    ]
    batch_vecs = provider.embed_batch(texts)

    assert len(batch_vecs) == 3
    assert len(batch_vecs[0]) == 384
    assert len(batch_vecs[1]) == 384
    assert len(batch_vecs[2]) == 384
    assert all(x == 0.0 for x in batch_vecs[2])

    # Compare batch result with single embed result (within floating point precision)
    single_0 = provider.embed_text(texts[0])
    for b_val, s_val in zip(batch_vecs[0], single_0, strict=False):
        assert pytest.approx(b_val, abs=1e-5) == s_val


# =============================================================================
# B. TEXT NORMALIZATION TESTS
# =============================================================================


def test_normalize_whitespace_helper():
    """Verify normalize_whitespace compresses multiple spaces, tabs, and newlines."""
    assert normalize_whitespace("  hello   world  \n\t  test  ") == "hello world test"
    assert normalize_whitespace("") == ""
    assert normalize_whitespace(None) == ""


def test_opportunity_embedding_text_builder_deterministic():
    """Verify build_opportunity_embedding_text constructs normalized deterministic text."""
    opp = Opportunity(
        id=uuid.uuid4(),
        title="  Staff   Software   Engineer  ",
        company="TechCorp Solutions",
        opportunity_type=OpportunityType.JOB,
        employment_type=EmploymentType.FULLTIME,
        work_mode=WorkMode.HYBRID,
        location_city="Bengaluru",
        location_country="India",
        min_experience_years=3,
        max_experience_years=6,
        required_education_level=EducationLevel.BACHELOR,
        description="We are looking for an experienced engineer to build high-scale APIs.",
    )
    skills = [
        OpportunitySkill(skill_name="Python", is_required=True),
        OpportunitySkill(skill_name="AWS", is_required=False),
        OpportunitySkill(skill_name="FastAPI", is_required=True),
    ]

    text = build_opportunity_embedding_text(opp, skills)

    assert "Role: Staff Software Engineer" in text
    assert "Company: TechCorp Solutions" in text
    assert "Type: job" in text
    assert "Employment: fulltime" in text
    assert "Work Mode: hybrid" in text
    assert "Experience: 3-6 years" in text
    assert "Education: bachelor" in text
    assert "Required Skills: FastAPI, Python" in text  # sorted deterministically
    assert "Preferred Skills: AWS" in text
    assert "Description: We are looking for an experienced engineer" in text

    # Verify ID is not present
    assert str(opp.id) not in text


def test_candidate_embedding_text_builder_excludes_pii_and_sensitive_data():
    """
    Verify build_candidate_embedding_text constructs normalized profile capability text
    while strictly omitting full_name, email, phone, compensation, URLs, and secrets.
    """
    profile = CandidateProfile(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        full_name="John Doe",
        headline="Senior Backend Engineer",
        summary="Specializing in scalable distributed systems and Python microservices.",
        phone="+91 9876543210",
        location_city="Pune",
        preferred_salary_min=1500000,
        preferred_salary_max=2500000,
        preferred_salary_currency="INR",
        linkedin_url="https://linkedin.com/in/johndoe",
        github_url="https://github.com/johndoe",
    )
    skills = [
        Skill(skill_name="Docker", proficiency_level=SkillProficiency.ADVANCED),
        Skill(skill_name="Python", proficiency_level=SkillProficiency.EXPERT),
    ]
    experiences = [
        Experience(
            title="Senior Engineer",
            company="CloudTech",
            description="Designed async queue consumers.",
            skills_used=["Python", "Kafka"],
            start_date=date(2021, 1, 1),
        )
    ]
    educations = [
        Education(
            degree="B.Tech",
            field_of_study="Computer Science",
            institution="IIT Bombay",
        )
    ]
    projects = [
        Project(
            title="Vector Indexer",
            technologies=["Python", "pgvector"],
            description="High-throughput vector indexing pipeline.",
        )
    ]
    certifications = [
        Certification(
            name="AWS Solutions Architect",
            issuing_organization="Amazon Web Services",
        )
    ]

    text = build_candidate_embedding_text(
        profile,
        skills=skills,
        experiences=experiences,
        educations=educations,
        projects=projects,
        certifications=certifications,
    )

    # Allowed professional attributes
    assert "Title: Senior Backend Engineer" in text
    assert "Summary: Specializing in scalable distributed systems" in text
    assert "Skills: Docker (advanced), Python (expert)" in text
    assert "Senior Engineer at CloudTech" in text
    assert "B.Tech in Computer Science from IIT Bombay" in text
    assert "Vector Indexer (pgvector, Python)" in text
    assert "AWS Solutions Architect (Amazon Web Services)" in text

    # Strictly excluded PII, credentials, compensation, and IDs
    assert "John Doe" not in text
    assert "+91 9876543210" not in text
    assert "1500000" not in text
    assert "2500000" not in text
    assert "linkedin.com" not in text
    assert "github.com" not in text
    assert str(profile.id) not in text
    assert str(profile.user_id) not in text


# =============================================================================
# C. CANDIDATE EMBEDDINGS LIFECYCLE TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_candidate_profile_embedding_generation_and_persistence(
    db_session: AsyncSession,
    authenticated_user: tuple[User, str],
):
    """Verify candidate embedding is generated, has length 384, and is persisted in DB."""
    user, _ = authenticated_user
    profile = CandidateProfile(
        user_id=user.id,
        full_name="Alice Smith",
        headline="AI Research Engineer",
        summary="Building retrieval systems and dense embeddings.",
    )
    db_session.add(profile)
    await db_session.commit()
    await db_session.refresh(profile)

    skill = Skill(
        candidate_profile_id=profile.id,
        skill_name="PyTorch",
        proficiency_level=SkillProficiency.ADVANCED,
        source=SkillSource.MANUAL,
    )
    db_session.add(skill)
    await db_session.commit()

    # Generate embedding
    vector = await generate_candidate_profile_embedding(db_session, profile.id, commit=True)

    assert vector is not None
    assert len(vector) == 384
    assert all(isinstance(x, float) for x in vector)

    # Re-query from database
    stmt = select(CandidateProfile).where(CandidateProfile.id == profile.id)
    refreshed = (await db_session.execute(stmt)).scalar_one()

    assert refreshed.profile_embedding is not None
    assert len(refreshed.profile_embedding) == 384
    assert refreshed.embedding_updated_at is not None
    assert isinstance(refreshed.embedding_updated_at, datetime)


def test_candidate_embedding_stale_detection_scenarios():
    """Verify stale detection across NULL embeddings, updated profile, and child modifications."""
    now = datetime.now(UTC)
    old_time = now - timedelta(hours=2)
    recent_time = now - timedelta(minutes=10)

    # 1. Null embedding is stale
    p1 = CandidateProfile(
        profile_embedding=None,
        embedding_updated_at=None,
        updated_at=now,
    )
    assert is_candidate_embedding_stale(p1) is True

    # 2. Embedding timestamp exists, profile.updated_at is older -> FRESH
    p2 = CandidateProfile(
        profile_embedding=[0.1] * 384,
        embedding_updated_at=now,
        updated_at=old_time,
    )
    assert is_candidate_embedding_stale(p2) is False

    # 3. profile.updated_at is more recent than embedding timestamp -> STALE
    p3 = CandidateProfile(
        profile_embedding=[0.1] * 384,
        embedding_updated_at=old_time,
        updated_at=now,
    )
    assert is_candidate_embedding_stale(p3) is True

    # 4. Child skill created after embedding timestamp -> STALE
    p4 = CandidateProfile(
        profile_embedding=[0.1] * 384,
        embedding_updated_at=old_time,
        updated_at=old_time - timedelta(hours=1),
    )
    new_skill = Skill(
        skill_name="Kubernetes",
        created_at=recent_time,
    )
    assert is_candidate_embedding_stale(p4, skills=[new_skill]) is True

    # 5. Child education created after embedding timestamp -> STALE
    new_edu = Education(
        institution="Stanford",
        degree="MS",
        created_at=recent_time,
    )
    assert is_candidate_embedding_stale(p4, educations=[new_edu]) is True

    # 6. Child experience created after embedding timestamp -> STALE
    new_exp = Experience(
        title="Lead",
        company="Tech",
        created_at=recent_time,
    )
    assert is_candidate_embedding_stale(p4, experiences=[new_exp]) is True

    # 7. Child project created after embedding timestamp -> STALE
    new_proj = Project(
        title="Search Engine",
        created_at=recent_time,
    )
    assert is_candidate_embedding_stale(p4, projects=[new_proj]) is True

    # 8. Child certification created after embedding timestamp -> STALE
    new_cert = Certification(
        name="CKA",
        issuing_organization="Linux Foundation",
        created_at=recent_time,
    )
    assert is_candidate_embedding_stale(p4, certifications=[new_cert]) is True


@pytest.mark.asyncio
async def test_candidate_profile_update_regenerates_embedding(
    db_session: AsyncSession,
    authenticated_user: tuple[User, str],
):
    """Verify profile updates in profile_service trigger embedding regeneration."""
    user, _ = authenticated_user
    from app.schemas.candidate_profile import ProfileCreate

    # Create profile
    profile = await create_candidate_profile(
        db_session,
        user,
        ProfileCreate(
            full_name="Bob Miller",
            headline="Junior Developer",
            summary="Learning web development.",
        ),
    )

    stmt = select(CandidateProfile).where(CandidateProfile.id == profile.id)
    p_db = (await db_session.execute(stmt)).scalar_one()
    initial_updated_at = p_db.embedding_updated_at
    assert p_db.profile_embedding is not None

    # Update profile headline
    await update_candidate_profile(
        db_session,
        user,
        ProfileUpdate(headline="Full Stack Developer"),
    )

    refreshed = (await db_session.execute(stmt)).scalar_one()
    assert refreshed.headline == "Full Stack Developer"
    assert refreshed.profile_embedding is not None
    assert refreshed.embedding_updated_at is not None
    assert refreshed.embedding_updated_at >= initial_updated_at


@pytest.mark.asyncio
async def test_child_entity_creation_regenerates_candidate_embedding(
    db_session: AsyncSession,
    authenticated_user: tuple[User, str],
):
    """Verify adding child entities (skill, edu, exp, proj, cert) updates candidate embedding."""
    user, _ = authenticated_user
    profile = await create_candidate_profile(
        db_session,
        user,
        ProfileCreate(
            full_name="Carol White",
            headline="Software Engineer",
            summary="Generalist backend engineer.",
        ),
    )
    assert profile.profile_embedding is not None
    t0 = profile.embedding_updated_at

    # 1. Add skill
    await add_skill(
        db_session,
        profile.id,
        SkillCreate(skill_name="Go", proficiency_level=SkillProficiency.INTERMEDIATE),
    )
    stmt = select(CandidateProfile).where(CandidateProfile.id == profile.id)
    p1 = (await db_session.execute(stmt)).scalar_one()
    assert p1.embedding_updated_at >= t0
    t1 = p1.embedding_updated_at

    # 2. Add education
    await add_education(
        db_session,
        profile.id,
        EducationCreate(
            institution="MIT",
            degree="BS",
            field_of_study="Computer Science",
            education_level=EducationLevel.BACHELOR,
        ),
    )
    p2 = (await db_session.execute(stmt)).scalar_one()
    assert p2.embedding_updated_at >= t1
    t2 = p2.embedding_updated_at

    # 3. Add experience
    await add_experience(
        db_session,
        profile.id,
        ExperienceCreate(
            company="Globex",
            title="Backend Dev",
            start_date=date(2022, 1, 1),
        ),
    )
    p3 = (await db_session.execute(stmt)).scalar_one()
    assert p3.embedding_updated_at >= t2
    t3 = p3.embedding_updated_at

    # 4. Add project
    await add_project(
        db_session,
        profile.id,
        ProjectCreate(
            title="Distributed Key-Value Store",
            technologies=["Go", "Raft"],
        ),
    )
    p4 = (await db_session.execute(stmt)).scalar_one()
    assert p4.embedding_updated_at >= t3
    t4 = p4.embedding_updated_at

    # 5. Add certification
    await add_certification(
        db_session,
        profile.id,
        CertificationCreate(
            name="GCP Cloud Architect",
            issuing_organization="Google Cloud",
        ),
    )
    p5 = (await db_session.execute(stmt)).scalar_one()
    assert p5.embedding_updated_at >= t4
    assert is_candidate_embedding_stale(p5) is False


@pytest.mark.asyncio
async def test_resume_sync_triggers_candidate_embedding_generation(
    db_session: AsyncSession,
    authenticated_user: tuple[User, str],
):
    """Verify resume-to-profile sync pipeline automatically triggers candidate profile embedding."""
    user, _ = authenticated_user
    profile = await create_candidate_profile(
        db_session,
        user,
        ProfileCreate(
            full_name="Dave Miller",
            headline="Data Engineer",
        ),
    )

    resume = Resume(
        candidate_profile_id=profile.id,
        filename="dave_resume.pdf",
        file_path="uploads/dave_resume.pdf",
        file_type="pdf",
        file_size_bytes=1024,
        raw_text="Dave Miller Data Engineer PySpark Snowflake",
        parsed_json={
            "status": "parsed",
            "skills": [{"skill": "PySpark"}, {"skill": "Snowflake"}],
            "experiences": [
                {
                    "title": "Data Engineer",
                    "company": "DataStream",
                    "start_date": "2021-01",
                }
            ],
        },
    )
    db_session.add(resume)
    await db_session.commit()
    await db_session.refresh(resume)

    # Sync resume to profile
    sync_res = await sync_profile_from_resume(db_session, user, resume.id)
    assert sync_res.skills_added >= 1

    stmt = select(CandidateProfile).where(CandidateProfile.id == profile.id)
    refreshed = (await db_session.execute(stmt)).scalar_one()

    assert refreshed.profile_embedding is not None
    assert len(refreshed.profile_embedding) == 384
    assert refreshed.embedding_updated_at is not None
    assert is_candidate_embedding_stale(refreshed) is False


# =============================================================================
# D. OPPORTUNITY EMBEDDINGS LIFECYCLE TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_opportunity_embedding_generation_and_persistence(
    db_session: AsyncSession,
):
    """Verify Opportunity embedding generation, 384 dimension, and timestamp persistence."""
    opp = OpportunityFactory.build(
        title="Cloud Architect",
        company="Enterprise Cloud Inc",
        work_mode=WorkMode.REMOTE,
        job_embedding=None,
        embedding_updated_at=None,
    )
    db_session.add(opp)
    await db_session.commit()

    vec = await generate_opportunity_embedding(db_session, opp.id, commit=True)

    assert vec is not None
    assert len(vec) == 384

    stmt = select(Opportunity).where(Opportunity.id == opp.id)
    refreshed = (await db_session.execute(stmt)).scalar_one()

    assert refreshed.job_embedding is not None
    assert len(refreshed.job_embedding) == 384
    assert refreshed.embedding_updated_at is not None
    assert is_opportunity_embedding_stale(refreshed) is False


@pytest.mark.asyncio
async def test_opportunity_batch_embedding_generation(db_session: AsyncSession):
    """Verify generate_opportunity_embeddings_batch embeds multiple opportunities."""
    opp1 = OpportunityFactory.build(
        title="DevOps Engineer",
        company="ScaleTech",
        job_embedding=None,
        embedding_updated_at=None,
    )
    opp2 = OpportunityFactory.build(
        title="Data Analyst",
        company="DataMetrics",
        job_embedding=None,
        embedding_updated_at=None,
    )
    db_session.add_all([opp1, opp2])
    await db_session.commit()

    count = await generate_opportunity_embeddings_batch(
        db_session,
        [opp1.id, opp2.id],
        commit=True,
    )

    assert count == 2

    res = await db_session.execute(
        select(Opportunity).where(Opportunity.id.in_([opp1.id, opp2.id]))
    )
    opps = list(res.scalars().all())
    for o in opps:
        assert o.job_embedding is not None
        assert len(o.job_embedding) == 384
        assert o.embedding_updated_at is not None


@pytest.mark.asyncio
async def test_opportunity_ingestion_triggers_embedding_generation(db_session: AsyncSession):
    """Verify raw opportunity ingestion pipeline automatically generates job_embedding."""
    from app.schemas.opportunity import RawOpportunityRow

    unique_source_id = f"emb-test-{uuid.uuid4().hex[:8]}"
    raw_row = RawOpportunityRow(
        title="MLOps Specialist",
        company="AI Vanguard",
        description="Deploying model pipelines at scale.",
        opportunity_type=OpportunityType.JOB,
        employment_type="fulltime",
        work_mode=WorkMode.REMOTE,
        source=OpportunitySource.MANUAL,
        source_id=unique_source_id,
        required_skills="Docker, Kubernetes, Python",
        is_active=True,
    )

    result = await ingest_raw_records(db_session, [raw_row])
    assert result.created == 1

    stmt = select(Opportunity).where(Opportunity.source_id == unique_source_id)
    opp = (await db_session.execute(stmt)).scalar_one()

    assert opp.job_embedding is not None
    assert len(opp.job_embedding) == 384
    assert opp.embedding_updated_at is not None


@pytest.mark.asyncio
async def test_opportunity_embedding_safe_failure_handling(db_session: AsyncSession):
    """
    Verify embedding generation failures are safely handled:
    primary opportunity record is retained and embedding remains NULL.
    """
    opp = OpportunityFactory.build(
        title="Frontend Specialist",
        company="UI Labs",
        job_embedding=None,
        embedding_updated_at=None,
    )
    db_session.add(opp)
    await db_session.commit()

    # Create a failing provider mock
    class FailingProvider(BaseEmbeddingProvider):
        @property
        def dimension(self) -> int:
            return 384

        @property
        def model_name(self) -> str:
            return "failing-model"

        def embed_text(self, text: str) -> list[float]:
            raise RuntimeError("Simulated inference GPU/CPU out of memory error")

        def embed_batch(self, texts: list[str]) -> list[list[float]]:
            raise RuntimeError("Simulated batch inference error")

    original_provider = get_embedding_provider()
    set_embedding_provider(FailingProvider())
    try:
        # Should not raise exception
        vec = await generate_opportunity_embedding(db_session, opp.id, commit=True)
        assert vec is None

        # Opportunity still safely stored in database
        stmt = select(Opportunity).where(Opportunity.id == opp.id)
        refreshed = (await db_session.execute(stmt)).scalar_one()
        assert refreshed.title == "Frontend Specialist"
        assert refreshed.job_embedding is None
        assert refreshed.embedding_updated_at is None
        assert is_opportunity_embedding_stale(refreshed) is True
    finally:
        set_embedding_provider(original_provider)


# =============================================================================
# E. SECURITY TESTS
# =============================================================================


def test_vectors_excluded_from_api_response_schemas():
    """Verify that Pydantic response models strictly omit embedding vectors and timestamps."""
    profile_schema_fields = ProfileResponse.model_fields.keys()
    assert "profile_embedding" not in profile_schema_fields
    assert "embedding_updated_at" not in profile_schema_fields

    detail_profile_fields = ProfileDetailResponse.model_fields.keys()
    assert "profile_embedding" not in detail_profile_fields
    assert "embedding_updated_at" not in detail_profile_fields

    opportunity_fields = OpportunityResponse.model_fields.keys()
    assert "job_embedding" not in opportunity_fields
    assert "embedding_updated_at" not in opportunity_fields

    opportunity_detail_fields = OpportunityDetailResponse.model_fields.keys()
    assert "job_embedding" not in opportunity_detail_fields
    assert "embedding_updated_at" not in opportunity_detail_fields


@pytest.mark.asyncio
async def test_no_public_embedding_endpoint_exists(async_client):
    """Verify that there is no public arbitrary embedding generation API endpoint."""
    resp = await async_client.post("/api/v1/embeddings", json={"text": "hello world"})
    assert resp.status_code in (404, 405)

    resp2 = await async_client.get("/api/v1/embeddings")
    assert resp2.status_code in (404, 405)
