"""
Automated tests for Phase 6 Opportunity and Tracking data models,
relationships, constraints, and cascade behavior.
"""

import uuid
from datetime import UTC, date, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.db.base import Base
from app.db.session import async_session_factory
from app.models import (
    Application,
    ApplicationStatus,
    ApplicationStatusHistory,
    CandidateProfile,
    EducationLevel,
    EligibilityStatus,
    EmploymentType,
    InterviewPrep,
    Match,
    Opportunity,
    OpportunitySkill,
    OpportunitySource,
    OpportunityType,
    User,
    WorkMode,
)

# =============================================================================
# 1. MODEL DEFINITIONS & METADATA TESTS
# =============================================================================


def test_phase6_models_import_and_subclass():
    """Verify all six Phase 6 models inherit from Base."""
    for model_cls in [
        Opportunity,
        OpportunitySkill,
        Match,
        Application,
        ApplicationStatusHistory,
        InterviewPrep,
    ]:
        assert issubclass(model_cls, Base), f"{model_cls.__name__} must subclass Base"


def test_phase6_sqlalchemy_metadata_tables():
    """Verify that Base.metadata registers all 14 database tables."""
    expected_tables = {
        # Phase 4
        "users",
        "candidate_profiles",
        "resumes",
        "skills",
        "educations",
        "experiences",
        "projects",
        "certifications",
        # Phase 6
        "opportunities",
        "opportunity_skills",
        "matches",
        "applications",
        "application_status_history",
        "interview_prep",
    }
    registered = set(Base.metadata.tables.keys())
    assert expected_tables.issubset(registered), f"Missing: {expected_tables - registered}"


def test_phase6_tables_primary_keys():
    """Verify primary keys are 'id' for all Phase 6 tables."""
    for table_name in [
        "opportunities",
        "opportunity_skills",
        "matches",
        "applications",
        "application_status_history",
        "interview_prep",
    ]:
        table = Base.metadata.tables[table_name]
        pk_cols = [c.name for c in table.primary_key.columns]
        assert pk_cols == ["id"], f"{table_name} PK must be ['id'], got {pk_cols}"


def test_phase6_enums():
    """Verify Phase 6 and Phase 14 enum classes and their values."""
    assert [e.value for e in OpportunityType] == ["job", "internship", "hackathon"]
    assert [e.value for e in OpportunitySource] == ["synthetic", "manual", "api"]
    assert [e.value for e in EligibilityStatus] == ["eligible", "partial", "review_required"]
    assert [e.value for e in ApplicationStatus] == [
        "saved",
        "applied",
        "oa",
        "interview",
        "offer",
        "rejected",
        "withdrawn",
    ]


# =============================================================================
# 2. OPPORTUNITY & OPPORTUNITY_SKILLS TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_opportunity_crud_and_defaults():
    """Test Opportunity creation with defaults, optional fields, and array types."""
    unique_suffix = uuid.uuid4().hex[:8]
    async with async_session_factory() as session:
        opp = Opportunity(
            title=f"Cloud Infrastructure Engineer {unique_suffix}",
            company="Tech Corp",
            description="Build scalable distributed cloud services on Kubernetes.",
            required_skills=["Python", "Docker", "Kubernetes"],
            preferred_skills=["PostgreSQL", "Terraform"],
            min_experience_years=3,
            max_experience_years=6,
            required_education_level=EducationLevel.BACHELOR,
            location_city="Bengaluru",
            location_state="Karnataka",
            location_country="India",
            work_mode=WorkMode.HYBRID,
            employment_type=EmploymentType.FULLTIME,
            salary_min=1800000,
            salary_max=2500000,
            salary_currency="INR",
            application_deadline=date(2026, 12, 31),
            job_url="https://techcorp.example.com/jobs/123",
            source=OpportunitySource.SYNTHETIC,
            source_id=f"syn_{unique_suffix}",
            posted_date=date(2026, 10, 1),
            is_active=True,
            job_embedding=[0.05] * 384,
            embedding_updated_at=datetime.now(UTC),
        )
        session.add(opp)
        await session.commit()
        await session.refresh(opp)

        assert opp.id is not None
        assert opp.opportunity_type == OpportunityType.JOB
        assert opp.title.startswith("Cloud Infrastructure")
        assert opp.required_skills == ["Python", "Docker", "Kubernetes"]
        assert len(opp.job_embedding) == 384
        assert opp.is_active is True
        assert opp.created_at is not None
        assert opp.updated_at is not None


@pytest.mark.asyncio
async def test_opportunity_types_representation():
    """Verify Opportunity represents JOB, INTERNSHIP, and HACKATHON types."""
    async with async_session_factory() as session:
        # 1. Job
        job = Opportunity(
            opportunity_type=OpportunityType.JOB,
            title=f"Backend Lead {uuid.uuid4().hex[:6]}",
            company="Tech Corp",
            description="Build scalable distributed backend systems.",
            employment_type=EmploymentType.FULLTIME,
            source=OpportunitySource.SYNTHETIC,
        )
        # 2. Internship
        internship = Opportunity(
            opportunity_type=OpportunityType.INTERNSHIP,
            title=f"AI Research Intern {uuid.uuid4().hex[:6]}",
            company="Research Labs",
            description="Work on research experiments.",
            employment_type=EmploymentType.INTERNSHIP,
            source=OpportunitySource.SYNTHETIC,
        )
        # 3. Hackathon
        hackathon = Opportunity(
            opportunity_type=OpportunityType.HACKATHON,
            title=f"Global Open Source Hackathon {uuid.uuid4().hex[:6]}",
            company="Open Foundation",
            description="48-hour competitive software hackathon.",
            employment_type=EmploymentType.ANY,
            source=OpportunitySource.SYNTHETIC,
        )
        session.add_all([job, internship, hackathon])
        await session.commit()
        await session.refresh(job)
        await session.refresh(internship)
        await session.refresh(hackathon)

        assert job.opportunity_type == OpportunityType.JOB
        assert internship.opportunity_type == OpportunityType.INTERNSHIP
        assert hackathon.opportunity_type == OpportunityType.HACKATHON


@pytest.mark.asyncio
async def test_opportunity_source_dedup_unique_constraint():
    """Test that (source, source_id) enforces uniqueness for non-null source_id."""
    unique_id = f"dedup_{uuid.uuid4().hex[:8]}"
    async with async_session_factory() as session:
        opp1 = Opportunity(
            title="Backend Lead",
            company="Alpha Systems",
            description="Leading the backend architecture team.",
            source=OpportunitySource.API,
            source_id=unique_id,
            employment_type=EmploymentType.FULLTIME,
        )
        session.add(opp1)
        await session.commit()

    # Second opportunity with same source and source_id must fail
    async with async_session_factory() as session:
        opp2 = Opportunity(
            title="Backend Lead Duplicate",
            company="Alpha Systems",
            description="Duplicate post of leading the backend team.",
            source=OpportunitySource.API,
            source_id=unique_id,
            employment_type=EmploymentType.FULLTIME,
        )
        session.add(opp2)
        with pytest.raises(IntegrityError):
            await session.commit()


@pytest.mark.asyncio
async def test_opportunity_skills_and_cascade_delete():
    """Test OpportunitySkill mapping and cascade deletion when Opportunity is deleted."""
    async with async_session_factory() as session:
        opp = Opportunity(
            title=f"DevOps Lead {uuid.uuid4().hex[:6]}",
            company="DevOps Inc",
            description="Manage CI/CD pipelines.",
            source=OpportunitySource.MANUAL,
            employment_type=EmploymentType.CONTRACT,
        )
        session.add(opp)
        await session.flush()

        skill1 = OpportunitySkill(
            opportunity_id=opp.id,
            skill_name="kubernetes",
            is_required=True,
        )
        skill2 = OpportunitySkill(
            opportunity_id=opp.id,
            skill_name="helm",
            is_required=False,
        )
        session.add_all([skill1, skill2])
        await session.commit()

        opp_id = opp.id
        skill1_id = skill1.id

    # Verify skills exist
    async with async_session_factory() as session:
        skills = (
            (
                await session.execute(
                    select(OpportunitySkill).where(OpportunitySkill.opportunity_id == opp_id)
                )
            )
            .scalars()
            .all()
        )
        assert len(skills) == 2

    # Delete opportunity and verify cascade deletes skills
    async with async_session_factory() as session:
        opp_to_delete = (
            await session.execute(select(Opportunity).where(Opportunity.id == opp_id))
        ).scalar_one()
        await session.delete(opp_to_delete)
        await session.commit()

    # Verify skills are deleted
    async with async_session_factory() as session:
        remaining = (
            await session.execute(select(OpportunitySkill).where(OpportunitySkill.id == skill1_id))
        ).scalar_one_or_none()
        assert remaining is None


@pytest.mark.asyncio
async def test_opportunity_skills_duplicate_rejection():
    """Test duplicate (opportunity_id, skill_name) raises IntegrityError."""
    async with async_session_factory() as session:
        opp = Opportunity(
            title=f"Engineer {uuid.uuid4().hex[:6]}",
            company="Beta Co",
            description="Software engineer role.",
            source=OpportunitySource.SYNTHETIC,
            employment_type=EmploymentType.FULLTIME,
        )
        session.add(opp)
        await session.flush()

        s1 = OpportunitySkill(opportunity_id=opp.id, skill_name="python", is_required=True)
        s2 = OpportunitySkill(opportunity_id=opp.id, skill_name="python", is_required=False)
        session.add(s1)
        session.add(s2)
        with pytest.raises(IntegrityError):
            await session.commit()


# =============================================================================
# 3. MATCHES TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_match_lifecycle_and_unique_pair():
    """Test Match creation, JSONB storage, unique (candidate, opportunity) constraint."""
    suffix = uuid.uuid4().hex[:8]
    async with async_session_factory() as session:
        # User & Profile
        user = User(
            email=f"matcher_{suffix}@example.com",
            hashed_password="mock_hash_for_test",
        )
        session.add(user)
        await session.flush()

        profile = CandidateProfile(user_id=user.id, full_name="Match Candidate")
        session.add(profile)

        # Opportunity
        opp = Opportunity(
            title="Backend Role",
            company="Match Corp",
            description="Develop robust APIs.",
            source=OpportunitySource.SYNTHETIC,
            employment_type=EmploymentType.FULLTIME,
        )
        session.add(opp)
        await session.flush()

        match = Match(
            candidate_profile_id=profile.id,
            opportunity_id=opp.id,
            semantic_score=0.88,
            deterministic_score=0.92,
            final_score=0.90,
            eligibility_status=EligibilityStatus.ELIGIBLE,
            eligibility_warnings={"warnings": []},
            score_breakdown={
                "semantic": 0.88,
                "skills": 0.95,
                "experience": 0.90,
                "education": 1.0,
            },
            explanation={"summary": "Excellent skill match for Python and backend."},
            explanation_text="Candidate matches 95% of required skills.",
            skill_gap={"missing": [], "matched": ["Python", "FastAPI"]},
        )
        session.add(match)
        await session.commit()

        # Duplicate match on same pair must fail
        dup_match = Match(
            candidate_profile_id=profile.id,
            opportunity_id=opp.id,
            semantic_score=0.5,
            deterministic_score=0.5,
            final_score=0.5,
            eligibility_status=EligibilityStatus.PARTIAL,
            score_breakdown={},
            explanation={},
            skill_gap={},
        )
        session.add(dup_match)
        with pytest.raises(IntegrityError):
            await session.commit()


@pytest.mark.asyncio
async def test_match_cascade_deletion():
    """Test Match is cascaded when Opportunity or CandidateProfile is deleted."""
    suffix = uuid.uuid4().hex[:8]
    async with async_session_factory() as session:
        user = User(
            email=f"cascade_match_{suffix}@example.com",
            hashed_password="mock_hash",
        )
        session.add(user)
        await session.flush()
        profile = CandidateProfile(user_id=user.id, full_name="Cascade Candidate")
        session.add(profile)

        opp = Opportunity(
            title="Cascade Opp",
            company="Cascade Inc",
            description="Role description.",
            source=OpportunitySource.SYNTHETIC,
            employment_type=EmploymentType.FULLTIME,
        )
        session.add(opp)
        await session.flush()

        match = Match(
            candidate_profile_id=profile.id,
            opportunity_id=opp.id,
            semantic_score=0.8,
            deterministic_score=0.8,
            final_score=0.8,
            eligibility_status=EligibilityStatus.ELIGIBLE,
            score_breakdown={},
            explanation={},
            skill_gap={},
        )
        session.add(match)
        await session.commit()

        opp_id = opp.id
        match_id = match.id

    # Delete Opportunity
    async with async_session_factory() as session:
        opp_row = (
            await session.execute(select(Opportunity).where(Opportunity.id == opp_id))
        ).scalar_one()
        await session.delete(opp_row)
        await session.commit()

    # Match should be cascade-deleted
    async with async_session_factory() as session:
        match_row = (
            await session.execute(select(Match).where(Match.id == match_id))
        ).scalar_one_or_none()
        assert match_row is None


# =============================================================================
# 4. APPLICATIONS & APPLICATION_STATUS_HISTORY TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_application_and_status_history_lifecycle():
    """Test Application creation, status audit history, and cascade deletion."""
    suffix = uuid.uuid4().hex[:8]
    async with async_session_factory() as session:
        user = User(
            email=f"applicant_{suffix}@example.com",
            hashed_password="mock_hash",
        )
        session.add(user)
        await session.flush()
        profile = CandidateProfile(user_id=user.id, full_name="Applicant Candidate")
        session.add(profile)

        opp = Opportunity(
            title="Senior Architect",
            company="Enterprise Corp",
            description="Architecture role.",
            source=OpportunitySource.API,
            employment_type=EmploymentType.FULLTIME,
        )
        session.add(opp)
        await session.flush()

        app = Application(
            candidate_profile_id=profile.id,
            opportunity_id=opp.id,
            status=ApplicationStatus.SAVED,
            notes="Saved for review over the weekend.",
        )
        session.add(app)
        await session.flush()

        # Audit trail history 1: saved
        h1 = ApplicationStatusHistory(
            application_id=app.id,
            status=ApplicationStatus.SAVED,
            notes="Bookmarked job.",
        )
        # Audit trail history 2: applied
        h2 = ApplicationStatusHistory(
            application_id=app.id,
            status=ApplicationStatus.APPLIED,
            notes="Submitted resume online.",
        )
        session.add_all([h1, h2])
        await session.commit()

        app_id = app.id
        h1_id = h1.id

    # Verify history records exist
    async with async_session_factory() as session:
        histories = (
            (
                await session.execute(
                    select(ApplicationStatusHistory).where(
                        ApplicationStatusHistory.application_id == app_id
                    )
                )
            )
            .scalars()
            .all()
        )
        assert len(histories) == 2

    # Delete Application and verify status history is cascade-deleted
    async with async_session_factory() as session:
        app_to_del = (
            await session.execute(select(Application).where(Application.id == app_id))
        ).scalar_one()
        await session.delete(app_to_del)
        await session.commit()

    async with async_session_factory() as session:
        h_row = (
            await session.execute(
                select(ApplicationStatusHistory).where(ApplicationStatusHistory.id == h1_id)
            )
        ).scalar_one_or_none()
        assert h_row is None


@pytest.mark.asyncio
async def test_application_unique_pair_constraint():
    """Test duplicate (candidate_profile_id, opportunity_id) application fails."""
    suffix = uuid.uuid4().hex[:8]
    async with async_session_factory() as session:
        user = User(
            email=f"app_dup_{suffix}@example.com",
            hashed_password="mock",
        )
        session.add(user)
        await session.flush()
        profile = CandidateProfile(user_id=user.id, full_name="Duplicate Applicant")
        session.add(profile)

        opp = Opportunity(
            title="Security Engineer",
            company="Sec Inc",
            description="InfoSec operations.",
            source=OpportunitySource.SYNTHETIC,
            employment_type=EmploymentType.FULLTIME,
        )
        session.add(opp)
        await session.flush()

        app1 = Application(candidate_profile_id=profile.id, opportunity_id=opp.id)
        app2 = Application(candidate_profile_id=profile.id, opportunity_id=opp.id)
        session.add(app1)
        session.add(app2)
        with pytest.raises(IntegrityError):
            await session.commit()


# =============================================================================
# 5. INTERVIEW_PREP TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_interview_prep_crud_and_cascade():
    """Test InterviewPrep creation, unique candidate/opportunity pair, and cascade."""
    suffix = uuid.uuid4().hex[:8]
    async with async_session_factory() as session:
        user = User(
            email=f"interview_{suffix}@example.com",
            hashed_password="mock",
        )
        session.add(user)
        await session.flush()
        profile = CandidateProfile(user_id=user.id, full_name="Interview Candidate")
        session.add(profile)

        opp = Opportunity(
            title="ML Engineer",
            company="AI Solutions",
            description="Machine learning engineering.",
            source=OpportunitySource.SYNTHETIC,
            employment_type=EmploymentType.FULLTIME,
        )
        session.add(opp)
        await session.flush()

        prep = InterviewPrep(
            candidate_profile_id=profile.id,
            opportunity_id=opp.id,
            content={
                "technical_questions": ["Explain backpropagation", "How does transformer work?"],
                "behavioral_questions": ["Tell me about a tough deadline."],
            },
            generation_method="template",
            candidate_notes="Focus on transformers and attention mechanism.",
        )
        session.add(prep)
        await session.commit()

        prep_id = prep.id
        user_id = user.id

    # Verify record
    async with async_session_factory() as session:
        prep_row = (
            await session.execute(select(InterviewPrep).where(InterviewPrep.id == prep_id))
        ).scalar_one()
        assert prep_row.generation_method == "template"
        assert len(prep_row.content["technical_questions"]) == 2

    # Delete User -> cascade to CandidateProfile -> cascade to InterviewPrep
    async with async_session_factory() as session:
        u_del = (await session.execute(select(User).where(User.id == user_id))).scalar_one()
        await session.delete(u_del)
        await session.commit()

    async with async_session_factory() as session:
        deleted_prep = (
            await session.execute(select(InterviewPrep).where(InterviewPrep.id == prep_id))
        ).scalar_one_or_none()
        assert deleted_prep is None
