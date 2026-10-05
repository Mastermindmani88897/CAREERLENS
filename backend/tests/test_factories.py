"""
Unit tests for CareerLens test data factories.
Verifies that all 14 entity factories build valid in-memory models
and successfully persist to the PostgreSQL test database with correct foreign keys and constraints.
"""

import uuid

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
    ApplicationStatus,
    EducationLevel,
    EligibilityStatus,
    EmploymentType,
    OpportunitySource,
    SkillCategory,
    SkillProficiency,
    WorkMode,
)
from app.models.opportunity import Opportunity, OpportunitySkill
from app.models.tracking import (
    Application,
    ApplicationStatusHistory,
    InterviewPrep,
    Match,
)
from app.models.user import User
from tests.factories import (
    ApplicationFactory,
    ApplicationStatusHistoryFactory,
    CandidateProfileFactory,
    CertificationFactory,
    EducationFactory,
    ExperienceFactory,
    InterviewPrepFactory,
    MatchFactory,
    OpportunityFactory,
    OpportunitySkillFactory,
    ProjectFactory,
    ResumeFactory,
    SkillFactory,
    UserFactory,
)

# =============================================================================
# 1. IN-MEMORY BUILD() TESTS
# =============================================================================


def test_user_factory_build():
    """Verify UserFactory builds valid User instances in-memory."""
    user = UserFactory.build(email="custom_user@example.com")
    assert isinstance(user, User)
    assert user.email == "custom_user@example.com"
    assert user.is_active is True
    assert user.is_admin is False
    assert user.hashed_password.startswith("$2b$") or user.hashed_password.startswith("$2a$")


def test_candidate_profile_factory_build():
    """Verify CandidateProfileFactory builds valid instances with overrides."""
    user_id = uuid.uuid4()
    profile = CandidateProfileFactory.build(
        user_id=user_id,
        full_name="Custom Candidate",
        preferred_work_mode=WorkMode.REMOTE,
    )
    assert isinstance(profile, CandidateProfile)
    assert profile.user_id == user_id
    assert profile.full_name == "Custom Candidate"
    assert profile.preferred_work_mode == WorkMode.REMOTE


def test_sub_entity_factories_build():
    """Verify sub-entity factories build valid in-memory models."""
    profile_id = uuid.uuid4()

    resume = ResumeFactory.build(candidate_profile_id=profile_id)
    assert isinstance(resume, Resume)
    assert resume.candidate_profile_id == profile_id
    assert resume.file_type == "pdf"

    skill = SkillFactory.build(
        candidate_profile_id=profile_id,
        skill_name="Python",
        category=SkillCategory.TECHNICAL,
    )
    assert isinstance(skill, Skill)
    assert skill.skill_name == "Python"

    edu = EducationFactory.build(
        candidate_profile_id=profile_id,
        education_level=EducationLevel.MASTER,
    )
    assert isinstance(edu, Education)
    assert edu.education_level == EducationLevel.MASTER

    exp = ExperienceFactory.build(
        candidate_profile_id=profile_id,
        employment_type=EmploymentType.CONTRACT,
    )
    assert isinstance(exp, Experience)
    assert exp.employment_type == EmploymentType.CONTRACT

    proj = ProjectFactory.build(candidate_profile_id=profile_id)
    assert isinstance(proj, Project)

    cert = CertificationFactory.build(candidate_profile_id=profile_id)
    assert isinstance(cert, Certification)


def test_opportunity_and_tracking_factories_build():
    """Verify Opportunity, Match, Application, and InterviewPrep build in-memory."""
    opp = OpportunityFactory.build(source=OpportunitySource.MANUAL)
    assert isinstance(opp, Opportunity)
    assert opp.source == OpportunitySource.MANUAL
    assert len(opp.job_embedding) == 384

    opp_skill = OpportunitySkillFactory.build(opportunity_id=opp.id)
    assert isinstance(opp_skill, OpportunitySkill)

    match = MatchFactory.build()
    assert isinstance(match, Match)
    assert match.eligibility_status == EligibilityStatus.ELIGIBLE

    app = ApplicationFactory.build(status=ApplicationStatus.OFFER)
    assert isinstance(app, Application)
    assert app.status == ApplicationStatus.OFFER

    history = ApplicationStatusHistoryFactory.build()
    assert isinstance(history, ApplicationStatusHistory)

    prep = InterviewPrepFactory.build()
    assert isinstance(prep, InterviewPrep)
    assert len(prep.content["technical_questions"]) > 0


# =============================================================================
# 2. PERSISTENCE CREATE() TESTS WITH DATABASE SESSION
# =============================================================================


@pytest.mark.asyncio
async def test_factories_persist_user_and_candidate_profile(db_session: AsyncSession):
    """Verify User and CandidateProfile factories persist to database with relational link."""
    user = await UserFactory.create(db_session)
    profile = await CandidateProfileFactory.create(db_session, user_id=user.id)

    # Query back to verify persistence
    stmt = select(CandidateProfile).where(CandidateProfile.id == profile.id)
    res = await db_session.execute(stmt)
    persisted = res.scalar_one()

    assert persisted.id == profile.id
    assert persisted.user_id == user.id
    assert persisted.full_name == profile.full_name


@pytest.mark.asyncio
async def test_factories_persist_candidate_sub_entities(db_session: AsyncSession):
    """Verify Resume, Skill, Education, Experience, Project, and Certification persist."""
    user = await UserFactory.create(db_session)
    profile = await CandidateProfileFactory.create(db_session, user_id=user.id)

    resume = await ResumeFactory.create(db_session, candidate_profile_id=profile.id)
    skill = await SkillFactory.create(
        db_session,
        candidate_profile_id=profile.id,
        skill_name=f"FastAPI_{uuid.uuid4().hex[:6]}",
        proficiency_level=SkillProficiency.EXPERT,
    )
    edu = await EducationFactory.create(db_session, candidate_profile_id=profile.id)
    exp = await ExperienceFactory.create(db_session, candidate_profile_id=profile.id)
    proj = await ProjectFactory.create(db_session, candidate_profile_id=profile.id)
    cert = await CertificationFactory.create(db_session, candidate_profile_id=profile.id)

    assert resume.id is not None
    assert skill.id is not None
    assert edu.id is not None
    assert exp.id is not None
    assert proj.id is not None
    assert cert.id is not None


@pytest.mark.asyncio
async def test_factories_persist_opportunity_and_tracking(db_session: AsyncSession):
    """Verify Opportunity, OpportunitySkill, Match, Application, and History persist."""
    user = await UserFactory.create(db_session)
    profile = await CandidateProfileFactory.create(db_session, user_id=user.id)
    opp = await OpportunityFactory.create(db_session)

    opp_skill = await OpportunitySkillFactory.create(db_session, opportunity_id=opp.id)
    match = await MatchFactory.create(
        db_session, candidate_profile_id=profile.id, opportunity_id=opp.id
    )
    application = await ApplicationFactory.create(
        db_session, candidate_profile_id=profile.id, opportunity_id=opp.id
    )
    history = await ApplicationStatusHistoryFactory.create(
        db_session, application_id=application.id
    )
    prep = await InterviewPrepFactory.create(
        db_session, candidate_profile_id=profile.id, opportunity_id=opp.id
    )

    assert opp.id is not None
    assert opp_skill.id is not None
    assert match.id is not None
    assert application.id is not None
    assert history.id is not None
    assert prep.id is not None
