"""
Phase 19 Matching Persistence — Tests.

Covers:
  - upsert_match creates a new Match record correctly
  - upsert_match updates an existing record (idempotent)
  - compute_and_persist_match end-to-end DB integration
  - Match fields are correctly stored and retrievable
  - Correct handling of eligibility_warnings (None vs list)
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta

import pytest
from sqlalchemy import select
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
from app.models.tracking import Match
from app.services.matching_service import compute_and_persist_match, upsert_match
from tests.helpers.auth import create_test_user

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def db_profile_with_skills(db_session: AsyncSession) -> CandidateProfile:
    """Profile with skills, experience, education persisted in the test DB."""
    user, _ = await create_test_user(db_session)
    await db_session.flush()

    profile = CandidateProfile(
        user_id=user.id,
        full_name="Persistence Test Candidate",
        preferred_work_mode=WorkMode.HYBRID,
        preferred_employment_type=EmploymentType.FULLTIME,
        location_city="Austin",
        location_state="TX",
        location_country="USA",
        open_to_relocation=False,
    )
    db_session.add(profile)
    await db_session.flush()

    db_session.add(
        Skill(
            candidate_profile_id=profile.id,
            skill_name="Python",
            category=SkillCategory.TECHNICAL,
            proficiency_level=SkillProficiency.ADVANCED,
            source=SkillSource.MANUAL,
        )
    )
    start = date.today() - timedelta(days=3 * 365)
    db_session.add(
        Experience(
            candidate_profile_id=profile.id,
            company="Test Co",
            title="Dev",
            employment_type=EmploymentType.FULLTIME,
            work_mode=WorkMode.HYBRID,
            start_date=start,
            is_current=True,
        )
    )
    db_session.add(
        Education(
            candidate_profile_id=profile.id,
            institution="University",
            degree="B.Sc.",
            field_of_study="CS",
            education_level=EducationLevel.BACHELOR,
            start_date=date(2016, 9, 1),
            end_date=date(2020, 6, 1),
            is_current=False,
        )
    )
    await db_session.commit()
    await db_session.refresh(profile)
    return profile


@pytest.fixture
async def db_opportunity(db_session: AsyncSession) -> Opportunity:
    """A simple active opportunity for persistence tests."""
    opp = Opportunity(
        title="Persistence Test Role",
        company="TestCorp",
        description="A role for testing persistence.",
        required_skills=["Python"],
        preferred_skills=["Docker"],
        min_experience_years=1,
        max_experience_years=5,
        required_education_level=EducationLevel.BACHELOR,
        work_mode=WorkMode.HYBRID,
        employment_type=EmploymentType.FULLTIME,
        source="synthetic",
        source_id=f"persist_{uuid.uuid4().hex[:8]}",
        is_active=True,
    )
    db_session.add(opp)
    await db_session.commit()
    return opp


# ---------------------------------------------------------------------------
# Tests: upsert_match
# ---------------------------------------------------------------------------


class TestUpsertMatch:
    def _sample_match_data(self) -> dict:
        return {
            "semantic_score": 0.75,
            "deterministic_score": 0.80,
            "final_score": 0.79,
            "eligibility_status": EligibilityStatus.ELIGIBLE,
            "eligibility_warnings": None,
            "score_breakdown": {
                "skill_overlap": {"score": 0.85},
                "experience": {"score": 0.90},
            },
            "explanation": {"strengths": ["Good Python skills"], "gaps": []},
            "skill_gap": {
                "matched_required_skills": ["python"],
                "missing_required_skills": [],
                "matched_preferred_skills": [],
                "missing_preferred_skills": ["docker"],
            },
        }

    async def test_creates_new_match_record(
        self,
        db_session: AsyncSession,
        db_profile_with_skills: CandidateProfile,
        db_opportunity: Opportunity,
    ):
        match_data = self._sample_match_data()
        match = await upsert_match(
            db=db_session,
            profile_id=db_profile_with_skills.id,
            opportunity_id=db_opportunity.id,
            match_data=match_data,
            commit=True,
        )
        assert match.id is not None
        assert match.candidate_profile_id == db_profile_with_skills.id
        assert match.opportunity_id == db_opportunity.id
        assert match.final_score == pytest.approx(0.79, abs=0.001)
        assert match.eligibility_status == EligibilityStatus.ELIGIBLE

    async def test_upsert_updates_existing_match(
        self,
        db_session: AsyncSession,
        db_profile_with_skills: CandidateProfile,
        db_opportunity: Opportunity,
    ):
        """Second upsert for same pair should update, not insert."""
        match_data = self._sample_match_data()
        match1 = await upsert_match(
            db=db_session,
            profile_id=db_profile_with_skills.id,
            opportunity_id=db_opportunity.id,
            match_data=match_data,
            commit=True,
        )

        # Update with different score
        match_data["final_score"] = 0.55
        match_data["eligibility_status"] = EligibilityStatus.PARTIAL
        match2 = await upsert_match(
            db=db_session,
            profile_id=db_profile_with_skills.id,
            opportunity_id=db_opportunity.id,
            match_data=match_data,
            commit=True,
        )

        assert match1.id == match2.id  # Same record
        assert match2.final_score == pytest.approx(0.55, abs=0.001)
        assert match2.eligibility_status == EligibilityStatus.PARTIAL

    async def test_match_uniqueness_enforced_in_db(
        self,
        db_session: AsyncSession,
        db_profile_with_skills: CandidateProfile,
        db_opportunity: Opportunity,
    ):
        """DB unique constraint: only one match per (profile_id, opportunity_id)."""
        match_data = self._sample_match_data()
        await upsert_match(
            db=db_session,
            profile_id=db_profile_with_skills.id,
            opportunity_id=db_opportunity.id,
            match_data=match_data,
            commit=True,
        )

        # Count matches for this pair
        stmt = select(Match).where(
            Match.candidate_profile_id == db_profile_with_skills.id,
            Match.opportunity_id == db_opportunity.id,
        )
        result = await db_session.execute(stmt)
        rows = result.scalars().all()
        assert len(rows) == 1

    async def test_eligibility_warnings_stored_as_none(
        self,
        db_session: AsyncSession,
        db_profile_with_skills: CandidateProfile,
        db_opportunity: Opportunity,
    ):
        match_data = self._sample_match_data()
        match_data["eligibility_warnings"] = None
        match = await upsert_match(
            db=db_session,
            profile_id=db_profile_with_skills.id,
            opportunity_id=db_opportunity.id,
            match_data=match_data,
        )
        await db_session.commit()
        await db_session.refresh(match)
        assert match.eligibility_warnings is None

    async def test_eligibility_warnings_stored_as_list(
        self,
        db_session: AsyncSession,
        db_profile_with_skills: CandidateProfile,
        db_opportunity: Opportunity,
    ):
        match_data = self._sample_match_data()
        match_data["eligibility_warnings"] = ["Experience gap: 1.5 years below requirement"]
        match_data["eligibility_status"] = EligibilityStatus.PARTIAL
        match = await upsert_match(
            db=db_session,
            profile_id=db_profile_with_skills.id,
            opportunity_id=db_opportunity.id,
            match_data=match_data,
        )
        await db_session.commit()
        await db_session.refresh(match)
        assert isinstance(match.eligibility_warnings, list)
        assert len(match.eligibility_warnings) == 1


# ---------------------------------------------------------------------------
# Tests: compute_and_persist_match
# ---------------------------------------------------------------------------


class TestComputeAndPersistMatch:
    async def test_end_to_end_creates_match(
        self,
        db_session: AsyncSession,
        db_profile_with_skills: CandidateProfile,
        db_opportunity: Opportunity,
    ):
        """Full pipeline: compute scores then persist to DB."""
        # Load relationships
        from sqlalchemy import select as sa_select
        from sqlalchemy.orm import selectinload

        stmt = (
            sa_select(CandidateProfile)
            .options(
                selectinload(CandidateProfile.skills),
                selectinload(CandidateProfile.experiences),
                selectinload(CandidateProfile.educations),
            )
            .where(CandidateProfile.id == db_profile_with_skills.id)
        )
        result = await db_session.execute(stmt)
        profile = result.scalar_one()

        from sqlalchemy.orm import selectinload as si

        from app.models.opportunity import Opportunity as OppModel

        opp_stmt = (
            sa_select(OppModel).options(si(OppModel.skills)).where(OppModel.id == db_opportunity.id)
        )
        opp_result = await db_session.execute(opp_stmt)
        opportunity = opp_result.scalar_one()

        match = await compute_and_persist_match(
            db=db_session,
            profile=profile,
            opportunity=opportunity,
            semantic_similarity=0.7,
            commit=True,
        )

        assert match.id is not None
        assert match.candidate_profile_id == profile.id
        assert match.opportunity_id == opportunity.id
        assert 0.0 <= match.final_score <= 1.0
        assert match.eligibility_status in list(EligibilityStatus)
        assert isinstance(match.score_breakdown, dict)
        assert isinstance(match.skill_gap, dict)
        assert isinstance(match.explanation, dict)

    async def test_compute_persist_idempotent(
        self,
        db_session: AsyncSession,
        db_profile_with_skills: CandidateProfile,
        db_opportunity: Opportunity,
    ):
        """Two calls for same pair should yield same record id."""
        from sqlalchemy import select as sa_select
        from sqlalchemy.orm import selectinload

        stmt = (
            sa_select(CandidateProfile)
            .options(
                selectinload(CandidateProfile.skills),
                selectinload(CandidateProfile.experiences),
                selectinload(CandidateProfile.educations),
            )
            .where(CandidateProfile.id == db_profile_with_skills.id)
        )
        result = await db_session.execute(stmt)
        profile = result.scalar_one()

        from app.models.opportunity import Opportunity as OppModel

        opp_stmt = (
            sa_select(OppModel)
            .options(selectinload(OppModel.skills))
            .where(OppModel.id == db_opportunity.id)
        )
        opp_result = await db_session.execute(opp_stmt)
        opportunity = opp_result.scalar_one()

        m1 = await compute_and_persist_match(
            db=db_session, profile=profile, opportunity=opportunity, semantic_similarity=0.5
        )
        await db_session.commit()

        m2 = await compute_and_persist_match(
            db=db_session, profile=profile, opportunity=opportunity, semantic_similarity=0.8
        )
        await db_session.commit()

        assert m1.id == m2.id
